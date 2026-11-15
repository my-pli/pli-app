"""Owned emulator pixels and input. Encoding happens on the host, once per source."""
import asyncio, contextlib, json, os, struct, time, uuid
from collections import deque
from pathlib import Path
import grpc
from PIL import Image
from google.protobuf.empty_pb2 import Empty
from emulator_proto import emulator_controller_pb2 as pb
from emulator_proto import emulator_controller_pb2_grpc as rpc
from runtime_context import DeviceContext

# Keyframe every 1.6 s with a VBV cap: no I-frame bursts on remote links, late joiners
# replay at most one GOP from the cache.
GOP = 48


class DisplayUnavailable(RuntimeError):
    pass

class PublicDisplay:
    def __init__(self, context=None):
        self.context = context or DeviceContext('public')
        if self.context.profile != 'public':
            raise ValueError('Only the isolated public AVD may be streamed')
        self.channel = self.stub = None
        self.pid = None
        self.geometry = None
        self.display_checked=0.;self.native_size=None
        self.geometry_revision = 0
        self.source_sequence = 0
        self.last_read = 0.0
        self.latest = None
        self.pointers = {}
        self.input_lock = asyncio.Lock()
        self.journal = self.context.state_dir / 'held-pointers.json'
        self.metrics = {'captures': 0, 'readMs': deque(maxlen=300)}

    async def connect(self):
        pid = self.context.assert_owned()
        if self.stub is not None and pid == self.pid:
            return
        if self.channel:
            await self.channel.close()
        discovery = Path('/run/user') / str(os.getuid()) / 'avd/running' / f'pid_{pid}.ini'
        fields = {}
        for line in discovery.read_text().splitlines():
            if '=' in line:
                k, v = line.split('=', 1); fields[k.strip()] = v.strip()
        port = int(fields.get('grpc.port', self.context.grpc_port))
        token = fields.get('grpc.token')
        if not token:
            raise DisplayUnavailable('PUBLIC_GRPC_AUTH_UNAVAILABLE')
        self.auth = (('authorization', 'Bearer ' + token),)
        self.channel = grpc.aio.insecure_channel(f'127.0.0.1:{port}', options=[('grpc.max_receive_message_length', 32*1024*1024)])
        self.stub = rpc.EmulatorControllerStub(self.channel)
        self.pid = pid
        self.latest = None
        self.geometry = None
        self.native_size=None;self.display_checked=0.
        await self.release_recorded()

    async def region(self, bounds, width=1440):
        """Crop one window (native display coordinates) without touching the Pleos touch geometry.

        Used for the app surface so the app never has to redraw itself in software for viewers.
        """
        await self.connect()
        if self.native_size is None:
            await self.screenshot()
        nw, nh = self.native_size
        left, top, right, bottom = bounds
        if not (0 <= left < right <= nw and 0 <= top < bottom <= nh):
            raise DisplayUnavailable('APP_BOUNDS_INVALID')
        height = round(width * nh / nw)
        image = await self.stub.getScreenshot(pb.ImageFormat(format=pb.ImageFormat.RGB888, display=0, width=width, height=height), metadata=self.auth, timeout=3)
        w, h = image.format.width, image.format.height
        if not w or not h or len(image.image) != w * h * 3:
            raise DisplayUnavailable('PUBLIC_DISPLAY_INACTIVE')
        sx, sy = w / nw, h / nh
        box = (round(left * sx), round(top * sy), round(right * sx), round(bottom * sy))
        box = (box[0], box[1], box[0] + (box[2] - box[0]) // 2 * 2, box[1] + (box[3] - box[1]) // 2 * 2)
        crop = Image.frombytes('RGB', (w, h), bytes(image.image)).crop(box)
        self.metrics['captures'] += 1
        return crop.tobytes(), crop.width, crop.height

    async def screenshot(self, width=1280):
        await self.connect()
        began = time.monotonic()
        if self.native_size is None or time.monotonic()-self.display_checked>.5:
            configurations=await self.stub.getDisplayConfigurations(Empty(),metadata=self.auth,timeout=2)
            display=next((d for d in configurations.displays if d.display==0),None)
            if display is None or not display.width or not display.height:raise DisplayUnavailable('PUBLIC_GEOMETRY_UNAVAILABLE')
            self.native_size=(display.width,display.height);self.display_checked=time.monotonic()
        image = await self.stub.getScreenshot(pb.ImageFormat(format=pb.ImageFormat.RGB888, display=0,width=width,height=round(width*self.native_size[1]/self.native_size[0])), metadata=self.auth, timeout=3)
        w, h = image.format.width, image.format.height
        nw,nh=self.native_size
        if (w>h)!=(nw>nh):nw,nh=nh,nw
        rotation=image.format.rotation.rotation
        if not w or not h or len(image.image) != w*h*3:
            raise DisplayUnavailable('PUBLIC_DISPLAY_INACTIVE')
        # This pinned emulator's RGB888 output is top-down (verified against ADB).
        # The bundled proto's bottom-up comment does not match its implementation.
        pixels = bytes(image.image)
        if w>width:
            resized=Image.frombytes('RGB',(w,h),pixels)
            resized.thumbnail((width,round(width*9/16)))
            w,h=resized.size;pixels=resized.tobytes()
        geometry = (w,h,nw,nh,rotation)
        if geometry != self.geometry:
            await self.release_all()
            self.geometry = geometry; self.geometry_revision += 1
        self.source_sequence += 1; self.last_read = time.monotonic()
        self.metrics['captures'] += 1; self.metrics['readMs'].append((self.last_read-began)*1000)
        meta = {'source':'pleos','sourceSeq':self.source_sequence,'geometryRevision':self.geometry_revision,
                'width':w,'height':h,'nativeWidth':nw,'nativeHeight':nh,'display':0,
                'sourceTimestampUs':image.timestampUs,'captureMono':self.last_read}
        self.latest = (pixels,meta)
        return pixels,meta

    def _save_pointers(self):
        data = {'serverPid':os.getpid(),'emulatorPid':self.pid,'profile':'public',
                'pointers':self.pointers,'updatedAt':time.time()}
        temp = self.journal.with_suffix('.tmp'); temp.write_text(json.dumps(data)); temp.replace(self.journal)

    async def release_recorded(self):
        try:
            old=json.loads(self.journal.read_text())
            if old.get('emulatorPid') != self.pid:
                self.journal.unlink(missing_ok=True); return
            for key in old.get('pointers',{}):
                await self.stub.sendTouch(pb.TouchEvent(display=0,touches=[pb.Touch(identifier=int(key),x=0,y=0,pressure=0)]),metadata=self.auth,timeout=2)
            self.pointers={};self._save_pointers()
        except FileNotFoundError:pass

    async def release_all(self):
        if not self.stub:return
        for key in list(self.pointers):
            await self.stub.sendTouch(pb.TouchEvent(display=0,touches=[pb.Touch(identifier=int(key),x=0,y=0,pressure=0)]),metadata=self.auth,timeout=2)
            self.pointers.pop(key,None)
        self._save_pointers()

    async def touch(self, data):
        async with self.input_lock:
            await self.connect()
            finishing=data.get('phase') in {'up','cancel'}
            try:journal_owner=json.loads(self.journal.read_text()).get('serverPid')
            except (OSError,ValueError):journal_owner=None
            if journal_owner!=os.getpid():
                await self.release_all()
                if data.get('phase')=='move':raise DisplayUnavailable('POINTER_OWNERSHIP_RESET')
            if self.geometry is None or (not finishing and time.monotonic()-self.last_read>1):
                raise DisplayUnavailable('FRAME_STALE')
            if not finishing and data.get('geometryRevision') != self.geometry_revision:
                raise ValueError('GEOMETRY_CHANGED')
            phase=data.get('phase');pointer=data.get('pointerId',0)
            if type(pointer) is not int or not 0<=pointer<10 or phase not in {'down','move','up','cancel'}:
                raise ValueError('INVALID_POINTER')
            import math
            u,v=data.get('x'),data.get('y')
            if any(type(n) not in (int,float) or not math.isfinite(n) or not 0<=n<=1 for n in (u,v)):
                raise ValueError('INVALID_COORDINATE')
            _,_,nw,nh,_=self.geometry;x=round(u*(nw-1));y=round(v*(nh-1));key=str(pointer)
            if phase=='down':
                self.pointers[key]={'x':x,'y':y};self._save_pointers()
            elif phase=='move' and key not in self.pointers:raise ValueError('POINTER_NOT_DOWN')
            await self.stub.sendTouch(pb.TouchEvent(display=0,touches=[pb.Touch(identifier=pointer,x=x,y=y,pressure=0 if phase in {'up','cancel'} else 1)]),metadata=self.auth,timeout=2)
            if phase in {'up','cancel'}:self.pointers.pop(key,None);self._save_pointers()
            return {'ok':True,'x':x,'y':y,'geometryRevision':self.geometry_revision}

    async def close(self):
        with contextlib.suppress(Exception):await self.release_all()
        if self.channel:await self.channel.close()

class EncodedSource:
    """A bounded host encoder shared by viewers. Slow viewers never queue old frames."""
    def __init__(self, getter, name):
        self.getter=getter;self.name=name;self.task=None;self.process=None;self.init=b''
        self.gop=[];self.subscribers=set();self.generation='';self.error=None
        self.frame_count=0;self.last_publish=0.;self.last_source=None
        self.meta_queue=asyncio.Queue(maxsize=32)

    async def subscribe(self):
        if not self.task or self.task.done():self.task=asyncio.create_task(self.run())
        queue=asyncio.Queue(maxsize=40)
        self.subscribers.add(queue)
        if self.init:
            queue.put_nowait(('init',self.init,{'generation':self.generation,'source':self.name}))
            for item in self.gop:queue.put_nowait(item)
        return queue

    def unsubscribe(self,queue):self.subscribers.discard(queue)

    def broadcast(self,item):
        for q in list(self.subscribers):
            try:q.put_nowait(item)
            except asyncio.QueueFull:
                self.subscribers.discard(q)
                while not q.empty():q.get_nowait()
                q.put_nowait(('error',b'',{'code':'SLOW_VIEWER'}))

    async def _box(self,reader):
        header=await reader.readexactly(8);size,kind=struct.unpack('>I4s',header)
        if size==1:
            extended=await reader.readexactly(8);size=struct.unpack('>Q',extended)[0];header+=extended
        if not len(header)<=size<=8*1024*1024:raise DisplayUnavailable('INVALID_ENCODER_BOX')
        return kind,header+await reader.readexactly(size-len(header))

    async def _encode_input(self,first):
        latest=first
        async def capture():
            nonlocal latest
            while True:
                began=time.monotonic();candidate=await self.getter()
                if (candidate[1]['width'],candidate[1]['height'])!=(first[1]['width'],first[1]['height']):raise DisplayUnavailable('GEOMETRY_CHANGED')
                if self.name=='pleos' and candidate[1].get('geometryRevision')!=first[1].get('geometryRevision'):raise DisplayUnavailable('GEOMETRY_CHANGED')
                if first[1].get('deviceBootCount')is not None and candidate[1].get('deviceBootCount')!=first[1].get('deviceBootCount'):raise DisplayUnavailable('DEVICE_BOOT_CHANGED')
                latest=candidate
                await asyncio.sleep(max(.001,1/30-(time.monotonic()-began)))
        capture_task=asyncio.create_task(capture());index=0;started=time.monotonic()
        try:
            while self.process.returncode is None:
                if capture_task.done():await capture_task
                pixels,meta=latest
                if time.monotonic()-meta['captureMono']>1:raise DisplayUnavailable('CAPTURE_STALE')
                stamp={**meta,'generation':self.generation,'encoderPtsUs':round(index*1e6/30),'source':self.name}
                await self.meta_queue.put(stamp)
                self.process.stdin.write(pixels);await self.process.stdin.drain();index+=1
                await asyncio.sleep(max(0,started+index/30-time.monotonic()))
        finally:
            capture_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):await capture_task

    async def run(self):
        idle_since=None
        while True:
            if not self.subscribers:
                idle_since=idle_since or time.monotonic()
                if time.monotonic()-idle_since>5:return
                await asyncio.sleep(.1);continue
            idle_since=None;writer=None
            try:
                first=await self.getter();w,h=first[1]['width'],first[1]['height']
                if w%2 or h%2:raise DisplayUnavailable('ENCODER_REQUIRES_EVEN_GEOMETRY')
                self.generation=uuid.uuid4().hex;self.init=b'';self.gop=[]
                self.meta_queue=asyncio.Queue(maxsize=32)
                self.process=await asyncio.create_subprocess_exec('ffmpeg','-nostdin','-hide_banner','-loglevel','error','-probesize','32','-analyzeduration','0','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate','30','-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast','-tune','zerolatency','-profile:v','baseline','-pix_fmt','yuv420p','-g',str(GOP),'-keyint_min',str(GOP),'-sc_threshold','0','-bf','0','-b:v','2400k','-maxrate','2800k','-bufsize','1400k','-movflags','empty_moov+default_base_moof+frag_every_frame','-flush_packets','1','-f','mp4','pipe:1',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
                writer=asyncio.create_task(self._encode_input(first));init=[];fragment=[];count=0
                while self.subscribers or idle_since is None or time.monotonic()-idle_since<5:
                    if not self.subscribers:idle_since=idle_since or time.monotonic()
                    else:idle_since=None
                    if writer.done():await writer
                    kind,data=await asyncio.wait_for(self._box(self.process.stdout),4)
                    if kind in {b'ftyp',b'moov'}:
                        init.append(data)
                        if kind==b'moov':
                            self.init=b''.join(init);self.broadcast(('init',self.init,{'generation':self.generation,'source':self.name,'mime':'video/mp4; codecs="avc1.42c01f"'}))
                    elif kind==b'moof':fragment=[data]
                    elif kind==b'mdat' and fragment:
                        fragment.append(data);stamp=await asyncio.wait_for(self.meta_queue.get(),2)
                        payload=b''.join(fragment);stamp={**stamp,'encodedBytes':len(payload)};item=('frame',payload,stamp)
                        if count%GOP==0:self.gop=[]
                        self.gop.append(item);self.broadcast(item);count+=1
                        self.frame_count+=1;self.last_publish=time.monotonic();self.last_source=stamp;self.error=None
            except asyncio.CancelledError:raise
            except Exception as exc:
                self.error=type(exc).__name__
                if writer and writer.done() and not writer.cancelled():
                    failure=writer.exception()
                    if failure:self.error+=':'+type(failure).__name__+':'+str(failure)[:60]
                self.broadcast(('error',b'',{'code':'VIDEO_UNAVAILABLE','source':self.name}))
                await asyncio.sleep(1)
            finally:
                self.init=b'';self.gop=[]
                if writer:
                    writer.cancel()
                    with contextlib.suppress(asyncio.CancelledError,Exception):await writer
                if self.process and self.process.returncode is None:
                    self.process.kill();await self.process.communicate()

    async def close(self):
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):await self.task
