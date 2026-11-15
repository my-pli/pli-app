#!/usr/bin/env python3
"""Tailnet-only emulator controls, viewing and duplex audio for the real APK.

No speech text injection, desktop capture, or audio recording.
Only project artifacts and the named emulator are exposed.
"""
import asyncio, contextlib, io, json, logging, math, os, re, secrets, signal, ssl, subprocess, time,hashlib,contextvars
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit
from aiohttp import web, WSMsgType, ClientSession, ClientTimeout
from audio_guard import prime,route_lock,owns,AudioRouteBusy
from delivery_assets import public_asset
from runtime_context import selected, state_dir,DeviceContext
from portal_proxy import forward_public
from display_stream import PublicDisplay,EncodedSource,DisplayUnavailable
CONTEXT=selected();RUN_TOOLS=state_dir()
import pulsectl
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools'
ADB = TOOLS / 'android-sdk/platform-tools/adb'
PACKAGE = 'ai.teammoon.pli'
ASSETS = ROOT / os.environ.get('PLI_PORTAL_ASSETS','demo-v2')
IP = os.environ['PLI_TAILSCALE_IP']
HTTPS_PORT, HTTP_PORT = ((8879,8878) if CONTEXT.profile=='public' else (8877,8876))
SHARED_HTTPS_PORT = 9001 if CONTEXT.profile=='public' else 9000
PULSE = os.environ.get('PULSE_SERVER', f'unix:/run/user/{os.getuid()}/pulse/native')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('pli-demo')
PUBLIC_MARKER='pli-public.local'
RUNTIME_LOADED_AT=time.time()
RUNTIME_SOURCES={name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()for name in ['demo-server.py','display_stream.py','delivery_assets.py','runtime_context.py','audio_guard.py','portal_proxy.py']}
INPUT_SPAN=contextvars.ContextVar('input_span',default=None)
input_traces=deque(maxlen=60)
SESSION_SECONDS=180
lease={'owner':None,'expires':0.0,'nativeId':None,'ending':False,'status':'STOPPED','surface':'app','voice':False,'deviceBootCount':None,'emulatorPid':None}
native_updated=0.0
native_issued=0
native_accepted=0
end_lock=asyncio.Lock()
native={}
native_user='10'
video_ack_ms=[]
video_bytes=0
audio_client=None
kids_lock=asyncio.Lock()
family_inflight=set()
recovery_task=None
recovery_attempts=[]
audio_signal={"last":0.0,"expected":0.0,"confirmed":False,"signature":None}
class SessionLocked(web.HTTPClientError):
    status_code=423

def public_config():
    try:return json.loads((TOOLS/'public-config.json').read_text())
    except (OSError,ValueError):return {}

def origin(request):return request.get('external_origin',f'{request.scheme}://{request.host}')
def client_id(request):return request.cookies.get('pli_demo','')
def owner_request(request):return CONTEXT.profile=='personal' and not request.get('public') and request.remote in {'127.0.0.1','::1'}
def lease_runtime_changed():
    if not lease['owner']:return False
    try:pid=CONTEXT.assert_owned()
    except (OSError,ValueError,RuntimeError):return True
    return lease.get('emulatorPid')not in (None,pid)or (lease.get('deviceBootCount')is not None and native.get('deviceBootCount')is not None and lease['deviceBootCount']!=native['deviceBootCount'])

def lease_info(request):
    remaining=max(0,int(lease['expires']-time.monotonic()))
    busy=bool(lease['ending'] or lease['owner'] and remaining)
    return {'busy':busy,'mine':bool(busy and not lease_runtime_changed() and lease['owner']==client_id(request) and (request.get('sessionToken') or request.headers.get('X-Pli-Session') or request.query.get('session'))==lease['nativeId']),'seconds':remaining,'status':lease['status']}
def persist_control():
    data={'surface':lease.get('surface','app'),'busy':bool(lease['owner'] and not lease['ending']),'expiresAt':time.time()+max(0,lease['expires']-time.monotonic()),'serverPid':os.getpid()}
    path=RUN_TOOLS/'control-lease.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(path)

def require_lease(request):
    if not lease_info(request)['mine']:
        raise SessionLocked(text='다른 분이 체험 중입니다. 잠시 뒤 시작해 주세요.')
class DeviceUnavailable(RuntimeError): pass

def runtime_state():
    try:
        state = json.loads((RUN_TOOLS/'runtime-status.json').read_text())
        if time.time()-state.get('updatedAt',0)>20:return {'phase':'error','message':'시연 환경 연결을 확인하고 있어요.'}
        return {k:state.get(k) for k in ['phase','message','attempt','updatedAt']}
    except (OSError,ValueError):return {'phase':'checking','message':'시연 환경을 준비하고 있어요.'}

def require_runtime():
    if CONTEXT.profile=='public':
        try:CONTEXT.assert_owned();return
        except Exception:raise DeviceUnavailable('공개 시연 기기를 확인하고 있어요.')
    if not cached['process'] or recovery_task is not None and not recovery_task.done():
        raise DeviceUnavailable('시연 환경을 다시 연결하고 있어요. 복구 후 다시 눌러 주세요.')

async def command(*args, timeout=12,include_stderr=False):
    began=time.monotonic();span=INPUT_SPAN.get()
    p = await asyncio.create_subprocess_exec(*map(str, args), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(p.communicate(), timeout)
        if p.returncode:
            message=err.decode(errors='replace')[:250]
            if str(args[0])==str(ADB) and any(x in message for x in ['not found','offline','no devices','device disconnected','closed']):raise DeviceUnavailable(message)
            raise RuntimeError(message)
        return out+err if include_stderr else out
    finally:
        if span is not None:span['commandMs']=round((time.monotonic()-began)*1000,2)
        if p.returncode is None:
            p.kill(); await p.communicate()

def serial():
    return CONTEXT.serial()

def qemu_stream(stream):return owns(stream)

async def stop_process(p):
    if not p or p.returncode is not None: return
    if p.stdin:
        with contextlib.suppress(Exception): p.stdin.close()
    with contextlib.suppress(ProcessLookupError): p.terminate()
    try: await asyncio.wait_for(p.communicate(), 3)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError): p.kill()
        await p.communicate()

class Screen:
    """Read actual app-rendered pixels; avoid the emulator H.264 encoder."""
    def __init__(self):
        self.compat_until=0.;self.jpeg=b'';self.frames=0;self.updated=0;self.condition=asyncio.Condition()
        self.task=None;self.error=None;self.clients=0;self.display_size=None;self.variants={};self.capture_ms=[]

    async def publish(self,jpeg):
        self.jpeg=jpeg;self.frames+=1;self.updated=time.monotonic();self.error=None;self.variants={}
        async with self.condition:self.condition.notify_all()

    def app_frame(self,width=960):
        if not self.jpeg or time.monotonic()-self.updated>.5 or not native.get('presentation') or not native.get('demo') or not native.get('visible',native.get('focused')):return None
        key=(self.frames,width)
        if key in self.variants:return self.variants[key]
        img=Image.open(io.BytesIO(self.jpeg))
        if width>=img.width:value=(self.jpeg,img.width,img.height)
        else:
            img.thumbnail((width,1000));out=io.BytesIO();img.save(out,'JPEG',quality=76);value=(out.getvalue(),img.width,img.height)
        self.variants[key]=value;return value

    async def snapshot(self):
        raw=await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/frame',timeout=5)
        if not raw.startswith(b'\xff\xd8'):raise DeviceUnavailable('앱 화면을 준비하고 있어요.')
        await self.publish(raw)

    async def run(self):
        while True:
            process=None
            try:
                if not (lease['owner'] or self.clients or time.monotonic()<self.compat_until) or not native.get('presentation') or not native.get('demo') or not native.get('visible',native.get('focused')):
                    await asyncio.sleep(.2);continue
                process=await asyncio.create_subprocess_exec(str(ADB),'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/frames',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
                while lease['owner'] or self.clients or time.monotonic()<self.compat_until:
                    started=time.monotonic();length=int.from_bytes(await asyncio.wait_for(process.stdout.readexactly(4),5),'big')
                    if not 100<length<3000000:raise DeviceUnavailable('Preview frame unavailable')
                    raw=await asyncio.wait_for(process.stdout.readexactly(length),4)
                    if not raw.startswith(b'\xff\xd8'):raise DeviceUnavailable('Preview frame invalid')
                    await self.publish(raw);self.capture_ms.append(round((time.monotonic()-started)*1000,2));del self.capture_ms[:-300]
            except asyncio.CancelledError:raise
            except Exception as e:self.error=str(e)
            finally:await stop_process(process)
            await asyncio.sleep(.2)

    async def close(self):
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):await self.task

async def os_pixels():
    pixels,meta=await public_display.screenshot()
    return pixels,{**meta,'deviceBootCount':native.get('deviceBootCount')}

async def app_pixels():
    frame=screen.app_frame(960)
    # Keep the first subscriber alive while the native producer starts. Closing
    # it immediately removes the very demand that wakes Screen.run().
    deadline=time.monotonic()+3
    while frame is None and time.monotonic()<deadline:
        await asyncio.sleep(.05)
        frame=screen.app_frame(960)
    if frame is None:raise DisplayUnavailable('APP_VIEW_UNAVAILABLE')
    jpeg,w,h=frame
    def convert():
        image=Image.open(io.BytesIO(jpeg)).convert('RGB')
        if image.width%2 or image.height%2:image=image.resize((image.width//2*2,image.height//2*2))
        return image.tobytes(),image.width,image.height
    pixels,w,h=await asyncio.to_thread(convert)
    return pixels,{'source':'app','sourceSeq':screen.frames,'geometryRevision':native.get('epoch',0),'width':w,'height':h,'captureMono':screen.updated}

public_display=PublicDisplay(CONTEXT) if CONTEXT.profile=='public' else None
encoded_sources={'pleos':EncodedSource(os_pixels,'pleos'),'app':EncodedSource(app_pixels,'app')} if public_display else {}

class Audio:
    """Move just the Pli emulator to owned virtual devices; restore on disconnect."""
    def __init__(self,rate=48000):
        self.rate=rate
        self.pulse = None; self.modules = []; self.saved = {}; self.writer = self.reader = None
        self.input_name = 'pli_remote_mic'+('_public' if CONTEXT.profile=='public' else ''); self.output_name = 'pli_remote_speaker'+('_public' if CONTEXT.profile=='public' else '')
        self.input_packets = 0; self.output_bytes = 0

    def route(self):
        with route_lock():
            if lease['ending']:return
            with pulsectl.Pulse('pli-demo-route',server=PULSE) as p:
                for name in [self.input_name,self.output_name]:
                    if not any(m.name=='module-null-sink' and f'sink_name={name} ' in m.argument for m in p.module_list()):p.module_load('module-null-sink',f'sink_name={name} rate=44100 channels=2')
                try:self.saved.update(json.loads((RUN_TOOLS/'demo-audio-state.json').read_text()))
                except (OSError,ValueError):pass
                sources=p.source_list();sinks=p.sink_list();monitor=next(x for x in sources if x.name==self.input_name+'.monitor');output=next(x for x in sinks if x.name==self.output_name)
                captures=[x for x in p.source_output_list() if qemu_stream(x)];players=[x for x in p.sink_input_list() if qemu_stream(x)]
                if not captures:raise DeviceUnavailable('에뮬레이터 마이크 연결이 끊겼어요.')
                for stream in captures:
                    old=next((x.name for x in sources if x.index==stream.source),None)
                    if 'source' not in self.saved and old!=monitor.name:self.saved['source']=old
                for stream in players:
                    old=next((x.name for x in sinks if x.index==stream.sink),None)
                    if 'sink' not in self.saved and old!=output.name:self.saved['sink']=old
                target=RUN_TOOLS/'demo-audio-state.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(self.saved));tmp.replace(target)
                for stream in captures:
                    if stream.source!=monitor.index:p.source_output_move(stream.index,monitor.index)
                for stream in players:
                    if stream.sink!=output.index:p.sink_input_move(stream.index,output.index)

    async def open(self):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            try:await asyncio.to_thread(self.route);break
            except (DeviceUnavailable,AudioRouteBusy):await asyncio.sleep(.1)
        else:raise DeviceUnavailable('마이크를 준비하지 못했어요.')
        env = {**os.environ, 'PULSE_SERVER': PULSE}
        self.writer = await asyncio.create_subprocess_exec('ffmpeg', '-nostdin', '-loglevel', 'error', '-probesize', '32', '-analyzeduration', '0', '-f', 's16le', '-ar', str(self.rate), '-ac', '1', '-i', 'pipe:0', '-ar', '44100', '-ac', '2', '-f', 'pulse', '-device', self.input_name, 'Pli remote voice', stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, env=env)
        self.reader = await asyncio.create_subprocess_exec('ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'pulse', '-i', self.output_name + '.monitor', '-ar', str(self.rate), '-ac', '1', '-c:a', 'pcm_s16le', '-flush_packets', '1', '-f', 's16le', 'pipe:1', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=env)

    async def close(self):
        await stop_process(self.writer);await stop_process(self.reader)
        await asyncio.to_thread(recover_audio)

def restore(pulse, saved):
    for method, key, targets in [(pulse.source_output_list, 'source', pulse.source_list()), (pulse.sink_input_list, 'sink', pulse.sink_list())]:
        if key not in saved:continue
        target=next((x for x in targets if x.name==saved[key]),None)
        if target is None:raise DeviceUnavailable('ORIGINAL_AUDIO_ROUTE_UNAVAILABLE')
        for stream in method():
            if qemu_stream(stream):(pulse.source_output_move if key=='source' else pulse.sink_input_move)(stream.index,target.index)
        if any(qemu_stream(x) and (x.source if key=='source' else x.sink)!=target.index for x in method()):raise DeviceUnavailable('AUDIO_ROUTE_NOT_RESTORED')

def recover_audio():
    with route_lock():
        path=RUN_TOOLS/'demo-audio-state.json';current=native
        if not path.exists() or current.get('sessionStatus')!='STOPPED':return
        if not (current.get('stopReceipt') or {}).get('captureStopped') and current.get('sessionId') is not None:return
        with pulsectl.Pulse('pli-demo-recovery',server=PULSE) as pulse:restore(pulse,json.loads(path.read_text()))
        path.unlink(missing_ok=True)

screen = Screen()
audio_owner = None
audio_lock = asyncio.Lock()
cached = {'package': PACKAGE, 'process': None, 'events': [], 'nativeSpeech': False, 'error': None}
started = time.time()
input_lock = asyncio.Lock()
last_input = None
KEYS = {'back':4, 'home':3, 'enter':66, 'escape':111, 'tab':61, 'up':19,
        'down':20, 'left':21, 'right':22, 'backspace':67, 'delete':112,
        'space':62, 'volume_up':24, 'volume_down':25}
VEHICLE_ACTIONS = {
    'drive': ['/vehicle/gear?gear=Drive', '/vehicle/controls?speed=32&accelerator=10&brake=0&steering=0'],
    'slow': ['/vehicle/gear?gear=Drive','/vehicle/controls?speed=3&accelerator=2&brake=0&steering=0'],
    'cruise': ['/vehicle/gear?gear=Drive','/vehicle/controls?speed=70&accelerator=15&brake=0&steering=0'],
    'charge_on': ['/vehicle/controls?speed=0&accelerator=0&brake=0&steering=0','/vehicle/gear?gear=Park','/vehicle/ev-battery?field=charge_switch&value=true'],
    'charge_off': ['/vehicle/ev-battery?field=charge_switch&value=false'],
    'park': ['/vehicle/controls?speed=0&accelerator=0&brake=0&steering=0', '/vehicle/gear?gear=Park'],
    'rain_on': ['/vehicle/body?front_wiper=Low'], 'rain_off': ['/vehicle/body?front_wiper=Off'],
    'left_on': ['/vehicle/turn-signal?mode=BlinkLeft'], 'left_off': ['/vehicle/turn-signal?mode=Off'],
    'rear_open': ['/vehicle/body?door_rl=true'], 'rear_close': ['/vehicle/body?door_rl=false'],
}

vehicle_reset_lock=asyncio.Lock()
async def reset_public_vehicle():
    if CONTEXT.profile!='public':return
    CONTEXT.assert_owned()
    async with vehicle_reset_lock:
        async with ClientSession(timeout=ClientTimeout(total=6))as session:
            async with session.get(f'http://127.0.0.1:{CONTEXT.console_port}/vehicle/state')as response:
                response.raise_for_status();actual=await response.json()
            body=actual.get('body',{});dirty=(actual.get('gear',{}).get('actual',{}).get('value')!='Park' or actual.get('controls',{}).get('speed_kph')!=0 or body.get('wipers',{}).get('front',{}).get('mode')!='Off' or body.get('doors',{}).get('rear_left')is not False or actual.get('lights',{}).get('turn_signal_mode')!='Off' or actual.get('ev_battery',{}).get('charging_activated')is True)
            if dirty:
                paths=['/vehicle/controls?speed=0&accelerator=0&brake=0&steering=0','/vehicle/gear?gear=Park','/vehicle/body?front_wiper=Off&door_rl=false','/vehicle/turn-signal?mode=Off','/vehicle/ev-battery?field=charge_switch&value=false']
                for path in paths:
                    async with session.put(f'http://127.0.0.1:{CONTEXT.console_port}'+path)as response:
                        response.raise_for_status();await response.read()
        await confirm_vehicle_signal('park')

def require_control_origin(request):
    if request.headers.get('Origin') != origin(request):
        raise web.HTTPForbidden(text='Same-origin emulator controls required.')

def validate_pointer_generation(data):
    if data.get('phase') in {'up','cancel'}:return
    current=encoded_sources['pleos']
    if data.get('streamGeneration')not in {current.generation,f'snapshot:{public_display.pid}:{public_display.geometry_revision}'}:raise ValueError('STREAM_CHANGED')
    sequence=data.get('lastDepictedSourceSeq')
    if type(sequence)is not int or sequence<=0 or not 0<=public_display.source_sequence-sequence<=30:raise ValueError('DEPICTED_FRAME_STALE')

async def control_body(request):
    require_control_origin(request)
    if request.content_length and request.content_length > 4096: raise web.HTTPRequestEntityTooLarge(max_size=4096, actual_size=request.content_length)
    try: data = await request.json()
    except (ValueError, UnicodeError): raise web.HTTPBadRequest(text='Invalid JSON')
    if not isinstance(data, dict): raise web.HTTPBadRequest(text='Expected an object')
    return data

def coordinate(value, maximum):
    if type(value) not in (int, float) or not 0 <= value <= 1 or not math.isfinite(value):
        raise web.HTTPBadRequest(text='Coordinates must be finite numbers from 0 to 1.')
    return round(value * (maximum - 1))

async def device_input(request):
    span={'requestId':secrets.token_hex(8),'receivedMono':time.monotonic()}
    token=INPUT_SPAN.set(span)
    try:
        response=await apply_device_input(request)
        response.headers['X-Pli-Input-Id']=span['requestId']
        response.headers['Server-Timing']='device;dur='+str(span.get('commandMs',0))
        return response
    finally:
        span['totalMs']=round((time.monotonic()-span['receivedMono'])*1000,2)
        input_traces.append(span);INPUT_SPAN.reset(token)

async def apply_device_input(request):
    if CONTEXT.profile!='public':raise web.HTTPNotFound()
    data=await control_body(request);require_lease(request);require_runtime()
    if lease['ending']:raise SessionLocked(text='체험 종료를 확인하고 있어요.')
    if data.get('type')=='pointer':
        try:
            validate_pointer_generation(data)
            return web.json_response(await public_display.touch(data))
        except ValueError as e:raise web.HTTPConflict(text=str(e))
        except DisplayUnavailable as e:raise DeviceUnavailable(str(e))
    kind=data.get('type');INPUT_SPAN.get()['kind']=data.get('key')if kind=='key'else kind
    if kind=='key' and data.get('key') in {'home','back','recent','volume_up','volume_down'}:
        if data['key']=='recent':
            # This Pleos CarLauncher exposes its app switcher by an explicit
            # intent; KEYCODE_APP_SWITCH returns success without showing it.
            result=await command(ADB,'-s',serial(),'shell','am','start','--user',native_user,'--activity-no-animation','-a','com.android.car.carlauncher.ACTION_APP_GRID',include_stderr=True)
            if b'Error'in result or b'Exception'in result:raise DeviceUnavailable('앱 목록을 표시하지 못했어요.')
        else:
            code={'home':3,'back':4,'volume_up':24,'volume_down':25}[data['key']]
            await command(ADB,'-s',serial(),'shell','input','keyevent',str(code))
        return web.json_response({'ok':True})
    if kind=='open_app':
        await show_app(animate=False);return web.json_response({'ok':True})
    raise web.HTTPBadRequest(text='Unsupported public control')

async def vehicle_control(request):
    global last_input
    data = await control_body(request)
    require_lease(request)
    require_runtime()
    if lease['ending']:raise SessionLocked(text='현재 체험의 종료를 확인하고 있어요.')
    action = data.get('action')
    if not isinstance(action, str) or action not in VEHICLE_ACTIONS: raise web.HTTPBadRequest(text='Unsupported simulator action')
    if input_lock.locked(): raise web.HTTPTooManyRequests(text='Previous emulator input is still running.')
    async with input_lock:
        try:
            async with ClientSession(timeout=ClientTimeout(total=6)) as session:
                for path in VEHICLE_ACTIONS[action]:
                    async with session.put(f'http://127.0.0.1:{CONTEXT.console_port}' + path) as response:
                        await response.read()
                        if response.status >= 400: raise RuntimeError('Console returned '+str(response.status))
            await confirm_vehicle_signal(action)
        except DeviceUnavailable:
            request_recovery(stop_first=True)
            raise web.HTTPBadGateway(text='차량 신호 변경을 확인하지 못해 시연 환경을 복구하고 있어요. 잠시 뒤 다시 시작해 주세요.')
        except Exception:
            log.exception('Virtual vehicle command failed')
            raise web.HTTPBadGateway(text='차량 조건을 연결하지 못했어요. 화면을 다시 연결한 뒤 다시 시도해 주세요.')
        last_input = {'type':'vehicle', 'action':action, 'at':time.time()}
        return web.json_response({'ok':True, 'action':action})

async def confirm_vehicle_signal(action):
    deadline=time.monotonic()+6
    while time.monotonic()<deadline:
        async with ClientSession(timeout=ClientTimeout(total=2)) as session:
            async with session.get(f'http://127.0.0.1:{CONTEXT.console_port}/vehicle/state') as response:
                response.raise_for_status();actual=await response.json()
        body=actual.get('body',{});gear=actual.get('gear',{}).get('actual',{}).get('value');speed=actual.get('controls',{}).get('speed_kph')
        if action in {'drive','park','slow','cruise'}:
            expected_gear,expected_speed={'drive':('D',32),'park':('P',0),'slow':('D',3),'cruise':('D',70)}[action]
            native_value=await native_snapshot()
            confirmed=gear=={'P':'Park','D':'Drive'}[expected_gear] and native_value.get('gear')==expected_gear and isinstance(native_value.get('speedKmh'),(float,int)) and abs(native_value['speedKmh']-expected_speed)<.5
        elif action.startswith('rain_'):confirmed=body.get('wipers',{}).get('front',{}).get('mode')==('Low'if action=='rain_on'else'Off')
        elif action.startswith('rear_'):confirmed=body.get('doors',{}).get('rear_left')==(action=='rear_open')
        elif action.startswith('left_'):confirmed=actual.get('lights',{}).get('turn_signal_mode')==('BlinkLeft'if action=='left_on'else'Off')
        elif action.startswith('charge_'):confirmed=actual.get('ev_battery',{}).get('charging_activated')==(action=='charge_on')
        else:confirmed=False
        if confirmed:return
        await asyncio.sleep(.2)
    raise DeviceUnavailable('The actual vehicle state did not confirm the console request')

def accept_native(value,order):
    global native,native_updated,native_accepted
    if order<native_accepted:return native
    if value.get('bootId')==native.get('bootId') and value.get('stateRevision',0)<native.get('stateRevision',0):return native
    native=value;native_updated=time.monotonic();native_accepted=order
    health={'at':time.time(),'pid':cached.get('process'),'demo':value.get('demo'),'visible':value.get('visible'),'hasView':value.get('hasView'),'sessionStatus':value.get('sessionStatus'),'mainHeartbeatAgeMs':value.get('appHeartbeatAgeMs')}
    target=RUN_TOOLS/'native-health.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(health));tmp.replace(target)
    cached['nativeSpeech']=bool(value.get('modelReady') and 'ON_DEVICE' in value.get('backend',''))
    return native

def next_native_read():
    global native_issued
    native_issued+=1;return native_issued

async def monitor():
    global native,native_user,native_updated
    tick=0;user='10'
    while True:
        started_poll=time.monotonic()
        try:
            pid = (await command(ADB, '-s', serial(), 'shell', 'pidof', PACKAGE)).decode().strip()
            if cached['process']!=pid:user=(await command(ADB,'-s',serial(),'shell','am','get-current-user')).decode().strip()
            native_user=user
            cached.update(process=pid,error=None)
            try:
                order=next_native_read();value=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',user,'--uri','content://ai.teammoon.pli.demo/state',timeout=5));accept_native(value,order)
            except Exception:pass
            if tick%4==0:
                lines=(await command(ADB,'-s',serial(),'logcat','--pid='+pid,'-d','-v','brief','-s','PliConversation:I','PliStt:I','*:S')).decode(errors='replace').splitlines()
                backend=cached['nativeSpeech']
                for line in lines:
                    if 'ON_DEVICE' in line or ('PliStt' in line and 'recognition ready' in line):backend=True
                    if 'Embedded fallback:' in line:backend=False
                cached.update(events=[x.split(': ',1)[-1] for x in lines if 'PliConversation' in x][-6:],nativeSpeech=backend)
        except Exception as e:
            cached.update(process=None,nativeSpeech=False,events=[],error=str(e))
        if CONTEXT.profile=='personal' and native and not native.get('demo') and native.get('sessionStatus')=='ACTIVE' and not family_inflight:
            asyncio.create_task(relay_family_question())
        tick+=1
        await asyncio.sleep(max(.15,1-time.monotonic()+started_poll))

async def recover_guest(stop_first=False):
    # Last resort for unconfirmed resources. Only this named project's Android guest.
    try:
        pid=int((RUN_TOOLS/'emulator.pid').read_text());args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
        if b'-avd' not in args or args[args.index(b'-avd')+1:args.index(b'-avd')+2]!=[CONTEXT.avd_name.encode()]:raise DeviceUnavailable('Unknown emulator owner')
        lease.update(ending=True,status='RECOVERING');(RUN_TOOLS/'runtime-transition').write_text(str(time.time()+100))
        if stop_first:
            if audio_owner:await audio_owner.close()
            try:await end_native_session(lease['nativeId'])
            except Exception:log.warning('Stopping voice before vehicle recovery was not acknowledged')
        before_boot=(await native_snapshot()).get('deviceBootCount',0)
        await command(ADB,'-s',serial(),'reboot')
        deadline=time.monotonic()+85
        while time.monotonic()<deadline:
            try:
                boot=(await command(ADB,'-s',serial(),'shell','getprop','sys.boot_completed',timeout=3)).decode().strip()
                user=(await command(ADB,'-s',serial(),'shell','am','get-current-user',timeout=3)).decode().strip()
                if boot=='1' and user!='0':break
            except Exception:pass
            await asyncio.sleep(1)
        else:raise DeviceUnavailable('Guest recovery timed out')
        current=await native_snapshot()
        if current.get('sessionStatus')!='STOPPED':
            await native_session('confirm_reboot',previous_boot=before_boot)
            for _ in range(30):
                current=await native_snapshot()
                if current.get('sessionStatus')=='STOPPED':break
                await asyncio.sleep(.1)
        await command(ADB,'-s',serial(),'forward',f'tcp:{CONTEXT.console_port}','tcp:8088')
        await native_session('preview');await show_app();current=await native_snapshot()
        if current.get('sessionStatus')!='STOPPED' or current.get('capture')!='STOPPED' or not current.get('demo'):raise DeviceUnavailable('Recovery not confirmed')
        (RUN_TOOLS/'portal-mode').touch()
        recover_audio();lease.update(owner=None,nativeId=None,expires=0.0,voice=False,ending=False,status='STOPPED')
    except Exception:lease.update(ending=True,status='STOP_FAILED');log.error('Project guest resource recovery not confirmed')
    finally:(RUN_TOOLS/'runtime-transition').unlink(missing_ok=True)

def request_recovery(stop_first=False):
    global recovery_task
    if recovery_task is not None and not recovery_task.done():return
    now=time.monotonic();recovery_attempts[:]=[t for t in recovery_attempts if now-t<3600]
    if recovery_attempts and now-recovery_attempts[-1]<60 or len(recovery_attempts)>=3:return
    recovery_attempts.append(now);recovery_task=asyncio.create_task(recover_guest(stop_first))

public_view_task=None
public_view_recovery={'key':None,'lost':0.0,'last':0.0,'attempts':0}

def public_view_is_owned(value):
    return bool(lease['owner'] and not lease['ending'] and time.monotonic()<lease['expires'] and lease['status'] in {'PREPARING','ACTIVE'} and value.get('demo') is True and value.get('sessionId')==lease['nativeId'] and value.get('sessionStatus') in {'PREPARING','ACTIVE'} and value.get('appHeartbeatAgeMs',99999)<3000)

async def restore_public_view(key):
    try:
        value=await native_snapshot()
        if public_view_is_owned(value) and (value.get('sessionId'),value.get('epoch'),value.get('bootId'))==key and not(value.get('visible') and value.get('hasView')):
            await show_app()
    except Exception:log.warning('Owned public app window reopen was not acknowledged')

def queue_public_view_restore():
    global public_view_task
    if lease.get('surface')=='pleos' or not public_view_is_owned(native):return
    key=(native.get('sessionId'),native.get('epoch'),native.get('bootId'))
    if public_view_recovery['key']!=key:public_view_recovery.update(key=key,lost=0.0,last=0.0,attempts=0)
    if native.get('visible') and native.get('hasView'):public_view_recovery['lost']=0.0;return
    now=time.monotonic()
    if not public_view_recovery['lost']:public_view_recovery['lost']=now
    if now-public_view_recovery['lost']>8 or public_view_recovery['attempts']>=3 or now-public_view_recovery['last']<1.5:return
    if public_view_task is not None and not public_view_task.done():return
    public_view_recovery.update(last=now,attempts=public_view_recovery['attempts']+1)
    public_view_task=asyncio.create_task(restore_public_view(key))

speech_recovery_at=0.0
async def recover_speech_engine_if_stopped():
    global speech_recovery_at
    if CONTEXT.profile!='public' or lease['owner'] or audio_owner or native.get('sessionStatus')!='STOPPED':return
    if not any(fragment in (native.get('error') or '')for fragment in ['음성 재생의 완료','목소리의 재생 시작']):return
    if time.monotonic()-speech_recovery_at<120:return
    receipt=native.get('stopReceipt') or {}
    if not all(receipt.get(key)is True for key in ['captureStopped','playbackStopped','focusReleased','instanceClosed']):return
    CONTEXT.assert_owned();speech_recovery_at=time.monotonic()
    await command(ADB,'-s',serial(),'shell','am','force-stop','--user',native_user,'ai.pleos.playground.caas',timeout=5)
    await native_session('preview')
    log.warning('Restarted isolated public speech engine after confirmed resource stop; preserved the failed session')

async def housekeeping():
    global speech_reset_required
    while True:
        target=RUN_TOOLS/'server-heartbeat.json';temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps({'pid':os.getpid(),'at':time.time()}));temporary.replace(target)
        if recovery_task and not recovery_task.done():await asyncio.sleep(1);continue
        changed=lease_runtime_changed()
        if lease['owner'] and (changed or time.monotonic()>=lease['expires'] or lease.get('voice') and lease['status'] in {'PREPARING','ACTIVE','STOPPING','STOP_FAILED'} and native.get('sessionId')==lease['nativeId'] and native.get('sessionStatus') in {'STOPPED','STOP_FAILED','UNKNOWN'}):
            log.info('Ending native lease: status=%s native=%s expired=%s',lease['status'],native.get('sessionStatus'),time.monotonic()>=lease['expires'])
            log.warning('Native resource summary: %s',{k:native.get(k)for k in ['error','capture','playback','focus','stopReceipt','appHeartbeatAgeMs','voiceHeartbeatAgeMs']})
            lease['ending']=True;lease['status']='STOPPING'
            try:
                if public_display:await public_display.release_all()
                if audio_owner:await audio_owner.close(code=1000,message=b'Session ending')
                await end_native_session(lease['nativeId'])
                if not changed and lease.get('surface')=='pleos' and time.monotonic()<lease['expires']:
                    lease.update(voice=False,ending=False,status='CONTROLLING')
                else:
                    await reset_public_vehicle()
                    lease.update(owner=None,expires=0.0,nativeId=None,voice=False,ending=False,status='STOPPED')
                persist_control()
            except Exception:lease['status']='STOP_FAILED';request_recovery()
        elif not lease['owner'] and ((native.get('demo') and native.get('sessionStatus') in {'PREPARING','ACTIVE','STOPPING'}) or native.get('sessionStatus') in {'UNKNOWN','STOP_FAILED'}):
            lease['ending']=True;lease['status']='RECOVERING'
            try:await end_native_session(native.get('sessionId'));lease.update(ending=False,status='STOPPED')
            except Exception:lease['status']='UNKNOWN';request_recovery()
        if not lease['owner'] and native.get('sessionStatus')=='STOPPED':
            with contextlib.suppress(Exception):await asyncio.to_thread(recover_audio)
        if lease['owner'] and lease.get('voice') and not lease['ending'] and lease['status'] in {'PREPARING','ACTIVE'}:
            try:await native_session('heartbeat',lease['nativeId'])
            except Exception:log.warning('Native server heartbeat not acknowledged')
        with contextlib.suppress(Exception):await recover_speech_engine_if_stopped()
        queue_public_view_restore()
        if audio_owner and native.get('spokenSequence',0)>0:
            signature=(native.get('sessionId'),native.get('spokenSequence'))
            if signature!=audio_signal['signature']:
                audio_signal['signature']=signature
                age=max(0,(native.get('deviceElapsedMs',0)-native.get('playbackStartedAtElapsed',0))/1000)
                audio_signal['expected']=native_updated-age
                audio_signal['confirmed']=False
            if audio_signal['last']>=audio_signal['expected']-.25:audio_signal['confirmed']=True
            # Keep a silent short utterance pending even after SDK onDone.
            if time.monotonic()-audio_signal['expected']>3 and not audio_signal['confirmed']:
                speech_reset_required=True
                log.error('Expected TTS output is silent');lease.update(ending=True,status='STOPPING')
                await audio_owner.close()
                try:await end_native_session(lease['nativeId']);lease.update(owner=None,nativeId=None,expires=0.0,voice=False,ending=False,status='STOPPED')
                except Exception:lease['status']='STOP_FAILED';request_recovery()
        elif not audio_owner:audio_signal.update(expected=0.0,confirmed=False,signature=None)
        await asyncio.sleep(.2 if audio_owner or lease['voice']else 1)

@web.middleware
async def boundaries(request, handler):
    host = (urlsplit('//' + request.host).hostname or '').rstrip('.').lower()
    try:dns=json.loads((TOOLS/'demo-config.json').read_text()).get('dnsName','')
    except (OSError,ValueError):dns=''
    allowed={IP,'127.0.0.1','localhost'}
    if dns:allowed.update({dns,dns.split('.')[0]})
    config=public_config()
    public=request.remote in {'127.0.0.1','::1'} and host==PUBLIC_MARKER and config.get('enabled')
    request['public']=bool(public)
    request['external_origin']=config['url'] if public else f'{request.scheme}://{request.host}'
    if host not in allowed and not public:
        log.warning('Rejected demo host remote=%s host=%s',request.remote,request.host)
        raise web.HTTPForbidden(text='Use the project Tailscale address.')
    if request.method not in {'GET', 'HEAD'}:
        origin = request.headers.get('Origin')
        if origin and origin != request['external_origin']:
            log.warning('Rejected demo origin remote=%s host=%s',request.remote,request.host)
            raise web.HTTPForbidden()
    try:
        private_path=request.path=='/family' or request.path.startswith(('/api/family/','/api/kidsnote/','/api/personal/'))
        if CONTEXT.profile=='personal' and (request.get('public') or not private_path):
            return await forward_public(request,public_config().get('url',''))
        response = await handler(request)
    except SessionLocked as error:
        response=web.json_response({'code':'CONTROL_BUSY','retryable':True,'phase':'control','message':error.text,'suggestedAction':'WATCH'},status=423)
    except DeviceUnavailable:
        response=web.json_response({'code':'RUNTIME_UNAVAILABLE','retryable':True,'phase':'runtime','suggestedAction':'RETRY','error':'runtime_unavailable','message':'시연 환경을 다시 연결하고 있어요. 복구 후 다시 시도해 주세요.'},status=503,headers={'Retry-After':'3'})
    except asyncio.TimeoutError:
        response=web.json_response({'code':'RUNTIME_TIMEOUT','retryable':True,'phase':'runtime','suggestedAction':'RETRY','error':'runtime_timeout','message':'시연 환경의 응답을 기다리고 있어요. 잠시 뒤 다시 시도해 주세요.'},status=503,headers={'Retry-After':'3'})
    if request.path=='/':log.info('Demo page remote=%s scheme=%s host=%s status=%s',request.remote,request.scheme,request.host,response.status)
    if not response.prepared:
        response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','X-Frame-Options':'SAMEORIGIN','Permissions-Policy':'camera=(), microphone=(self)'})
        response.headers.setdefault('Cache-Control','no-store')
        if request.path in {'/','/app','/pleos','/resources'} and not client_id(request):response.set_cookie('pli_demo',secrets.token_urlsafe(24),httponly=True,secure=request.secure or public,samesite='Strict',max_age=3600)
    return response

async def status(request):
    if request.path.startswith('/api/personal/') and not owner_request(request):raise web.HTTPNotFound()
    data={**cached,'app':{k:v for k,v in native.items() if k!='sessionId'},'lease':lease_info(request),'public':request.get('public',False),'publicUrl':public_config().get('url'),'runtime':runtime_state(),'https':origin(request) if request.get('public') else f'https://{IP}:{SHARED_HTTPS_PORT}','videoFrames':screen.frames,'videoAgeSeconds':round(time.monotonic()-screen.updated,2) if screen.updated else None,'viewers':screen.clients,'voiceBusy':audio_owner is not None,'controls':True,'displaySize':screen.display_size,'appResponsive':bool(native) and time.monotonic()-native_updated<3 and native.get('appHeartbeatAgeMs',99999)<3000,'audioOutputConfirmed':audio_signal['confirmed'],'availability':'PRIVATE_IN_USE' if not native.get('demo') and native.get('active') else 'RECOVERING' if lease['ending'] else 'AVAILABLE','nativeStateAgeMs':round((time.monotonic()-native_updated)*1000) if native_updated else None}
    if not owner_request(request) and not native.get('demo'):data['app']={}
    if request.get('public'):
        data['process']=bool(data['process']);data.pop('events',None);data.pop('error',None)
        if not native.get('demo'):data['app']={}
    if isinstance(data['app'].get('stopReceipt'),dict):data['app']['stopReceipt']={k:v for k,v in data['app']['stopReceipt'].items()if k!='sessionId'}
    data['owner']=owner_request(request)
    data['profile']=CONTEXT.profile
    data['runtimeRevision']={'loadedAt':RUNTIME_LOADED_AT,'pid':os.getpid(),'sourceSha256':RUNTIME_SOURCES}
    if request.remote in {'127.0.0.1','::1'}and not request.get('public'):data['inputTimings']=list(input_traces)
    data['frameProducer']={'clients':screen.clients,'frames':screen.frames,'error':screen.error}
    if CONTEXT.profile=='public':
        try:CONTEXT.assert_owned();data['controlReady']=native.get('publicOnly') is True
        except Exception:data['controlReady']=False
        data['lease'].update(surface=lease.get('surface'),voice=lease.get('voice',False))
        data['viewerCapacity']={'current':sum(len(x.subscribers)for x in encoded_sources.values()),'maximum':12}
        data['media']={name:{'frames':src.frame_count,'ageSeconds':round(time.monotonic()-src.last_publish,3) if src.last_publish else None,'error':src.error,'generation':src.generation} for name,src in encoded_sources.items()}
        data['displayGeometry']=public_display.latest[1] if public_display.latest else None
    return web.json_response(data)

def family_query_receipt(query,result,error=None):
    path=TOOLS/'private/kidsnote/query-receipts.json'
    try:rows=json.loads(path.read_text())
    except (OSError,ValueError):rows=[]
    fact=result.get('fact',{})if isinstance(result,dict)else{}
    snapshot=result.get('snapshot',{})if isinstance(result,dict)else{}
    rows.append({'requestId':query['requestId'],'topic':query['topic'],'date':query['date'],'days':query.get('days',1),'intentRevision':query.get('intentRevision',0),'tool':'get_sync_snapshot'if query['topic']=='BRIEF'else'get_voice_answer','sourceScope':query.get('scope'),'completedAt':time.time(),'error':error,'status':fact.get('status'),'coverage':fact.get('coverage'),'snapshotComplete':snapshot.get('complete'),'windowStart':snapshot.get('windowStart'),'windowEnd':snapshot.get('windowEnd')})
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(rows[-100:],ensure_ascii=False));temporary.chmod(0o600);temporary.replace(path)

async def relay_family_question():
    try:
        query=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/family-query',timeout=3))
        if not isinstance(query,dict) or not query.get('requestId') or query['requestId'] in family_inflight:return
        key=query['requestId'];family_inflight.add(key)
        try:
            args=['/usr/bin/python3',ROOT/'scripts/kidsnote-bridge.py','--answer','--topic',query['topic'],'--date',query['date'],'--days',str(query.get('days',1))]
            if query.get('scope'):args+=['--scope',query['scope']]
            answer={'requestId':key,'bootId':query['bootId'],'epoch':query['epoch'],'intentRevision':query.get('intentRevision',0)}
            try:
                result=json.loads(await command(*args,timeout=10))
                if 'error' in result:raise DeviceUnavailable('FAMILY_QUERY_FAILED')
                if query['topic']=='BRIEF':answer['snapshot']=result['snapshot']
                else:answer['fact']=result
            except Exception:answer['error']='지금은 키즈노트 소식을 확인하지 못했어. 가족 연결에서 로그인과 아이 선택을 확인해 줘.'
            family_query_receipt(query,answer,answer.get('error'))
            current=await native_snapshot()
            if current.get('demo') or current.get('bootId')!=query['bootId'] or current.get('epoch')!=query['epoch'] or current.get('intentRevision',0)!=query.get('intentRevision',0):return
            proc=await asyncio.create_subprocess_exec(str(ADB),'-s',serial(),'exec-in','content','write','--user',native_user,'--uri','content://ai.teammoon.pli.demo/family-answer',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
            await asyncio.wait_for(proc.communicate(json.dumps(answer,ensure_ascii=False).encode()),5)
        finally:family_inflight.discard(key)
    except Exception:pass

async def family_destinations(request):
    if not owner_request(request):raise web.HTTPNotFound()
    require_runtime()
    async def read_config():return json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/destinations',timeout=5))
    if request.method=='GET':
        config=await read_config()
        if (config.get('receipt')or{}).get('error')in {'COMMIT_UNKNOWN','RECOVERY_REQUIRED'}:raise web.HTTPServiceUnavailable(text='저장 상태를 다시 확인해야 해요. 앱의 자료 복구 안내를 확인해 주세요.')
        return web.json_response(config)
    require_control_origin(request)
    try:body=await request.json()
    except (ValueError,TypeError):raise web.HTTPBadRequest(text='목적지 형식을 확인해 주세요.')
    if not isinstance(body,dict):raise web.HTTPBadRequest(text='목적지 형식을 확인해 주세요.')
    values=body.get('destinations')
    if not isinstance(values,list)or len(values)>12:raise web.HTTPBadRequest(text='목적지는 12곳까지 등록할 수 있어요.')
    choices=[]
    for value in values:
        try:
            assert isinstance(value,dict)and isinstance(value.get('name'),str)and isinstance(value.get('address',''),str)
            assert all(isinstance(value.get(k),(int,float))and not isinstance(value.get(k),bool)for k in ['latitude','longitude'])
            assert value.get('id')is None or isinstance(value['id'],str)
            name=value['name'].strip();lat=float(value['latitude']);lon=float(value['longitude']);key=str(value.get('id')or secrets.token_hex(8));address=str(value.get('address',''))
            assert name and len(name)<=80 and len(key)<=80 and len(address)<=200 and math.isfinite(lat)and math.isfinite(lon)and -90<=lat<=90 and -180<=lon<=180
        except (KeyError,TypeError,ValueError,AssertionError):raise web.HTTPBadRequest(text='장소 이름과 위도·경도를 확인해 주세요.')
        choices.append({'id':key,'name':name,'latitude':lat,'longitude':lon,'address':address})
    if len({value['id']for value in choices})!=len(choices):raise web.HTTPBadRequest(text='중복된 후보를 확인해 주세요.')
    before=await read_config()
    if body.get('revision')!=before['revision']:raise web.HTTPConflict(text='다른 변경이 있어요. 후보를 다시 불러와 주세요.')
    request_id=secrets.token_hex(16);payload=json.dumps({'revision':before['revision'],'requestId':request_id,'destinations':choices},ensure_ascii=False).encode()
    proc=await asyncio.create_subprocess_exec(str(ADB),'-s',serial(),'exec-in','content','write','--user',native_user,'--uri','content://ai.teammoon.pli.demo/destinations',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
    await asyncio.wait_for(proc.communicate(payload),10)
    for _ in range(20):
        config=await read_config();receipt=config.get('receipt')or{}
        if receipt.get('requestId')==request_id:
            if receipt.get('committed')is True and config['destinations']==choices:return web.json_response(config)
            raise web.HTTPConflict(text='저장 결과를 확인하지 못했어요. 앱의 자료 복구 안내를 확인한 뒤 다시 불러와 주세요.')
        await asyncio.sleep(.1)
    raise web.HTTPServiceUnavailable(text='저장 결과가 아직 확인되지 않았어요. 자동으로 다시 저장하지 않았습니다.')

async def family_plan(request):
    if not owner_request(request):raise web.HTTPNotFound()
    require_control_origin(request);require_runtime()
    kind=request.headers.get('X-Pli-Document');limit=8*1024*1024 if kind=='image' else 65536
    if kind not in {'image','text'}:raise web.HTTPBadRequest(text='사진 또는 TXT/CSV를 선택해 주세요.')
    payload=bytearray()
    async for chunk in request.content.iter_chunked(8192):
        if len(payload)+len(chunk)>limit:raise web.HTTPRequestEntityTooLarge(max_size=limit,actual_size=len(payload)+len(chunk))
        payload.extend(chunk)
    if not payload:raise web.HTTPBadRequest(text='빈 파일은 올릴 수 없어요.')
    import hashlib
    digest=hashlib.sha256(payload).hexdigest();before=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/integration',timeout=5))
    proc=await asyncio.create_subprocess_exec(str(ADB),'-s',serial(),'exec-in','content','write','--user',native_user,'--uri','content://ai.teammoon.pli.demo/plan-'+kind,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
    await asyncio.wait_for(proc.communicate(payload),20)
    for _ in range(25):
        current=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/integration',timeout=5))
        if current.get('revision',0)>before.get('revision',0):
            if current.get('planSha256')==digest and not current.get('error'):return web.json_response({'stored':True,'sha256':digest,'bytes':len(payload),'kind':kind})
            raise web.HTTPBadRequest(text='계획안 저장을 확인하지 못했어요. 원본 파일을 확인해 주세요.')
        await asyncio.sleep(.1)
    raise web.HTTPServiceUnavailable(text='계획안 저장 결과를 확인하지 못했어요. 중복 업로드하지 않았습니다.')

async def kids_status(request):
    if not owner_request(request):raise web.HTTPNotFound()
    try:meta=json.loads((TOOLS/'private/kidsnote/metadata.json').read_text())
    except (OSError,ValueError):meta={'connected':False}
    return web.json_response({**meta,'busy':kids_lock.locked()})

async def kids_options(request):
    if not owner_request(request):raise web.HTTPNotFound()
    try:
        raw=await command('/usr/bin/python3',ROOT/'scripts/kidsnote-bridge.py','--options',timeout=40)
        result=json.loads(raw)
        return web.json_response({'choices':[{'scope':x['scope'],'label':x['childName']+' · '+x['centerName']+' · '+x['className']} for x in result.get('choices',[])]})
    except Exception:return web.json_response({'choices':[],'error':'MCP 연결과 로그인을 확인해 주세요.'},status=503)

family_login_task=None
family_login_status='IDLE'
async def kids_login(request):
    global family_login_task,family_login_status
    if not owner_request(request):raise web.HTTPNotFound()
    if request.method=='GET':return web.json_response({'status':family_login_status})
    require_control_origin(request)
    if family_login_task and not family_login_task.done():return web.json_response({'status':'WAITING'})
    async def login():
        global family_login_status
        family_login_status='WAITING'
        try:
            await command('/usr/bin/python3',ROOT/'scripts/kidsnote-web-login.py','--login',timeout=320)
            await command('systemctl','--user','restart','pli-kidsnote-mcp.service',timeout=10)
            family_login_status='CONNECTED'
        except Exception:family_login_status='FAILED'
    family_login_task=asyncio.create_task(login());return web.json_response({'status':'WAITING'})

personal_control_lock=asyncio.Lock()
personal_stop_generation=0
async def kids_personal(request):
    global personal_stop_generation
    if not owner_request(request):raise web.HTTPNotFound()
    require_control_origin(request)
    body=await request.json();action=body.get('action')
    if action not in {'start','stop'}:raise web.HTTPBadRequest()
    if action=='stop':personal_stop_generation+=1
    generation=personal_stop_generation
    async with personal_control_lock:
        return await perform_personal_action(request,action,generation)

async def perform_personal_action(request,action,generation):
    def current_start():
        if action=='start'and generation!=personal_stop_generation:
            raise web.HTTPConflict(text=json.dumps({'code':'PERSONAL_START_CANCELLED','message':'시작을 취소했어요. 현재 상태를 확인해 주세요.'}),content_type='application/json')
    current_start()
    # A fresh post-boot provider observation is authoritative. The background
    # process cache can still describe the previous guest during reconnect.
    # Resource closure must also remain available while that cache recovers.
    if action=='start':
        deadline=time.monotonic()+8
        while True:
            current_start()
            try:
                if recovery_task is not None and not recovery_task.done():raise DeviceUnavailable('앱을 복구하고 있어요.')
                CONTEXT.assert_owned()
                await native_snapshot()
                break
            except (DeviceUnavailable,RuntimeError):
                if time.monotonic()>=deadline:raise DeviceUnavailable('앱 연결을 확인하고 있어요. 잠시 뒤 다시 시작해 주세요.')
                await asyncio.sleep(.2)
    else:await native_snapshot()
    if action=='stop':
        if native.get('demo')and native.get('sessionStatus')=='STOPPED':
            recover_audio();(RUN_TOOLS/'portal-mode').touch();return web.json_response({'status':'STOPPED'})
        if native.get('demo'):raise web.HTTPConflict(text='개인 대화가 진행 중이 아니에요.')
        await end_native_session(native.get('sessionId'),allow_private=True);await native_session('preview');await show_app();(RUN_TOOLS/'portal-mode').touch()
    elif action=='start':
        if lease_info(request)['busy'] or audio_owner or native.get('sessionStatus')!='STOPPED':raise SessionLocked(text='진행 중인 대화를 먼저 끝내 주세요.')
        # Revoke public supervision before publishing the private idle View.
        # Otherwise the supervisor can restore preview during this transition.
        (RUN_TOOLS/'portal-mode').unlink(missing_ok=True)
        try:
            current_start();await native_session('private');current_start();await show_app();current_start()
        except Exception:
            current=await native_snapshot()
            if current.get('demo')and current.get('sessionStatus')=='STOPPED':(RUN_TOOLS/'portal-mode').touch()
            raise
        deadline=time.monotonic()+5
        while not (await native_snapshot()).get('visible'):
            current_start()
            if time.monotonic()>deadline:raise DeviceUnavailable('앱 화면을 확인하지 못했어요.')
            await asyncio.sleep(.1)
        current_start();await native_session('personal');current_start()
    else:raise web.HTTPBadRequest()
    return web.json_response({'status':'STOPPED' if action=='stop' else 'PREPARING'})

async def kids_sync(request):
    if not owner_request(request):raise web.HTTPNotFound()
    require_control_origin(request);require_runtime()
    if kids_lock.locked():raise SessionLocked(text='키즈노트 일정을 불러오고 있어요.')
    async with kids_lock:
        body=await request.json() if request.can_read_body else {}
        args=['/usr/bin/python3',ROOT/'scripts/kidsnote-bridge.py','--sync']
        if body.get('scope'):args+=['--scope',str(body['scope'])]
        try:await command(*args,timeout=80)
        except RuntimeError:
            raise web.HTTPBadGateway(text='MCP에서 조회를 완료하지 못했어요. 아이·기관 선택과 로그인 상태를 확인해 주세요.')
        folder=TOOLS/'private/kidsnote';meta=json.loads((folder/'metadata.json').read_text())
        if not meta.get('connected'):raise web.HTTPUnauthorized(text='키즈노트에 다시 로그인해 주세요.')
        batch=json.loads((folder/'family.json').read_text())
        private_revision=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/integration')).get('storeRevision')
        batch['baseRevision']=private_revision;payload=json.dumps(batch,ensure_ascii=False).encode()
        before=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/integration'))
        proc=await asyncio.create_subprocess_exec(str(ADB),'-s',serial(),'exec-in','content','write','--user',native_user,'--uri','content://ai.teammoon.pli.demo/family',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(payload),12)
        if proc.returncode:raise web.HTTPBadGateway(text='APK에 일정을 전달하지 못했어요.')
        result={}
        for _ in range(5):
            result=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/integration'))
            if result.get('revision',0)>before.get('revision',0):break
            await asyncio.sleep(.2)
        if result.get('error') or result.get('revision',0)<=before.get('revision',0):raise web.HTTPBadGateway(text='일정 형식을 확인해 주세요.')
        receipt=result.get('receipt') or {}
        if not receipt.get('committed') or receipt.get('batchId')!=batch['batchId']:raise web.HTTPBadGateway(text='저장 결과를 확인하지 못했어요.')
        meta.update(appliedPlans=receipt['retainedFromBatch'],created=receipt['created'],updated=receipt['updated'],unchanged=receipt['unchanged'],removed=receipt['removed'],storeRevision=receipt['storeRevision'],appliedAt=time.time(),privateProfile=True)
        (folder/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False));(folder/'metadata.json').chmod(0o600)
        return web.json_response(meta)

async def native_snapshot():
    global native,native_updated
    order=next_native_read()
    value=json.loads(await command(ADB,'-s',serial(),'exec-out','content','read','--user',native_user,'--uri','content://ai.teammoon.pli.demo/state',timeout=5))
    return accept_native(value,order)

async def native_session(action,session_id=None,previous_boot=None):
    args=[ADB,'-s',serial(),'shell','content','call','--user',native_user,'--uri','content://ai.teammoon.pli.demo','--method','session','--arg',action]
    if previous_boot is not None:args+=['--extra','previousBoot:i:'+str(previous_boot)]
    if session_id:args+=['--extra','session:s:'+session_id]
    out=await command(*args,timeout=7,include_stderr=True)
    if b'Result:'not in out or b'Exception' in out or b'Error' in out:raise DeviceUnavailable('기기 세션 상태를 확인하지 못했어요.')

async def show_app(animate=True):
    # Explicit web shortcuts need immediate task switching; native in-app
    # motion and the OS dock keep their original animation behavior.
    flags=[]if animate else['--activity-no-animation']
    await command(ADB,'-s',serial(),'shell','am','start','--user','current',*flags,'--activity-single-top','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','-n',PACKAGE+'/.MainActivity')

async def session_claim(request):
    body=await control_body(request);require_runtime()
    surface=body.get('surface','app')
    if surface not in {'app','pleos'}:raise web.HTTPBadRequest(text='Unknown surface')
    client=client_id(request)
    if not client:raise web.HTTPBadRequest(text='페이지를 새로고침해 주세요.')
    current=await native_snapshot()
    if lease['ending'] or lease_info(request)['busy'] or audio_owner or current.get('sessionStatus')!='STOPPED':raise SessionLocked(text='현재 대화의 종료를 확인하고 있어요. 잠시 뒤 시작해 주세요.')
    if public_display:await public_display.connect();await public_display.release_recorded()
    await reset_public_vehicle()
    lease.update(owner=client,expires=time.monotonic()+(SESSION_SECONDS if surface=='pleos' else 30),nativeId=secrets.token_hex(16),status='CONTROLLING' if surface=='pleos' else 'CLAIMED',surface=surface,voice=False,deviceBootCount=current.get('deviceBootCount'),emulatorPid=CONTEXT.assert_owned())
    persist_control()
    return web.json_response({'ok':True,'seconds':SESSION_SECONDS,'sessionToken':lease['nativeId']})

speech_reset_required=True
async def reset_idle_public_speech(current):
    global speech_reset_required
    if CONTEXT.profile!='public' or current.get('sessionStatus')!='STOPPED':return False
    if any(current.get(k)!=v for k,v in {'capture':'STOPPED','playback':'IDLE','focus':'NONE'}.items()):return False
    receipt=current.get('stopReceipt')or{}
    confirmed=all(receipt.get(k)is True for k in ['captureStopped','playbackStopped','focusReleased','instanceClosed'])
    if not confirmed:
        # A new main process/preview has no session receipt. Do not invent one:
        # require the durable idle state plus an independent guest process read.
        if current.get('sessionId')is not None or current.get('serviceInstanceId')is not None:return False
        names=(await command(ADB,'-s',serial(),'shell','ps','-A','-o','NAME')).decode().splitlines()
        if PACKAGE+':voice'in names:return False
    if confirmed and not speech_reset_required:return False
    CONTEXT.assert_owned()
    await command(ADB,'-s',serial(),'shell','am','force-stop','--user',native_user,'ai.pleos.playground.caas')
    speech_reset_required=False
    return True

async def session_prepare(request):
    require_control_origin(request)
    if not lease_info(request)['mine']:raise SessionLocked(text='체험 시작을 먼저 눌러 주세요.')
    # Claim already read the device before reserving this lease. Reuse only that
    # very recent observation; keep the fresh visible-view and PREPARED checks
    # below, and the APK's atomic resource/session guards, as the authority.
    current=native if time.monotonic()-native_updated<.5 else await native_snapshot()
    if not current.get('demo'):await native_session('preview')
    if not current.get('visible')or not current.get('hasView'):await show_app()
    deadline=time.monotonic()+5
    while not current.get('visible')or not current.get('hasView'):
        if time.monotonic()>deadline:raise DeviceUnavailable('앱 화면을 표시하지 못했어요.')
        await asyncio.sleep(.15)
        current=await native_snapshot()
    await reset_idle_public_speech(current)
    await asyncio.to_thread(prime)  # Never capture the host room during public preparation.
    await native_session('prepare',lease['nativeId']);lease['status']='PREPARING';lease['voice']=True
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        current=await native_snapshot()
        if current.get('modelReady') and current.get('ttsReady') and current.get('capture')=='ACTIVE' and current.get('sessionId')==lease['nativeId']:
            prepared={k:v for k,v in current.items()if k not in {'sessionId','stopReceipt'}}
            return web.json_response({'ok':True,'status':'PREPARED','app':prepared})
        if current.get('sessionStatus') in {'STOP_FAILED','STOPPED','UNKNOWN'}:break
        await asyncio.sleep(.2)
    raise DeviceUnavailable('음성 엔진의 실제 준비를 확인하지 못했어요.')

async def session_begin(request):
    require_control_origin(request)
    if not lease_info(request)['mine']:raise SessionLocked(text='체험 시작을 먼저 눌러 주세요.')
    await native_session('begin',lease['nativeId']);lease['status']='ACTIVE'
    if lease.get('surface')=='app':lease['expires']=time.monotonic()+SESSION_SECONDS
    persist_control()
    return web.json_response({'ok':True,'status':'ACTIVE'})

async def end_native_session(session_id=None,allow_private=False):
    async with end_lock:
        current=await native_snapshot()
        if not allow_private and not current.get('demo') and current.get('sessionStatus')!='STOPPED':raise DeviceUnavailable('개인 대화가 사용 중입니다.')
        # A reserved lease can be cancelled before any native session starts.
        if current.get('sessionStatus')=='STOPPED' and not current.get('active'):
            recover_audio();return current
        target=session_id or current.get('sessionId')
        if target and current.get('sessionId')!=target:raise DeviceUnavailable('세션이 바뀌어 종료 권한을 확인하지 못했어요.')
        await native_session('end',target)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            current=await native_snapshot();receipt=current.get('stopReceipt') or {}
            if current.get('sessionStatus')=='STOPPED' and all(receipt.get(k) is True for k in ['captureStopped','playbackStopped','focusReleased','instanceClosed']):
                recover_audio();return current
            if current.get('sessionStatus') in {'STOP_FAILED','UNKNOWN'}:break
            await asyncio.sleep(.15)
        raise DeviceUnavailable('기기 마이크와 소리의 종료를 확인하지 못했어요.')

async def session_end(request):
    require_control_origin(request)
    try:body=await request.json() if request.can_read_body else {}
    except (ValueError,TypeError):raise web.HTTPBadRequest(text='Invalid session request')
    if not isinstance(body,dict):raise web.HTTPBadRequest(text='Invalid session request')
    token=request.headers.get('X-Pli-Session') or body.get('sessionToken')
    if lease['owner'] is None and not lease['ending']:
        if not token:return web.json_response({'ok':True,'status':'NO_SESSION'})
        current=await native_snapshot()
        if current.get('sessionId')==token and current.get('sessionStatus')=='STOPPED':return web.json_response({'ok':True,'status':'STOPPED'})
        raise SessionLocked(text='이전 세션의 상태를 확인할 수 없어요.')
    if lease['owner']!=client_id(request) or not token or token!=lease['nativeId']:raise SessionLocked(text='이 탭에서 시작한 체험만 종료할 수 있어요.')
    if recovery_task is not None and not recovery_task.done():raise DeviceUnavailable('시연 환경을 복구하고 있어요. 종료 상태 확인 뒤 다시 시작해 주세요.')
    log.info('Owner requested end; native=%s',native.get('sessionStatus'))
    lease.update(ending=True,status='STOPPING')
    if public_display:await public_display.release_all()
    if audio_owner and audio_client==client_id(request):await audio_owner.close()
    try:
        await end_native_session(lease['nativeId'])
        await reset_public_vehicle()
    except Exception:
        lease['status']='STOP_FAILED';request_recovery()
        return web.json_response({'ok':False,'status':'STOP_FAILED','message':'종료를 확인하지 못해 새 체험을 잠시 막았어요.'},status=503)
    lease.update(owner=None,expires=0.0,nativeId=None,voice=False,ending=False,status='STOPPED')
    persist_control()
    return web.json_response({'ok':True,'status':'STOPPED'})

async def voice_end(request):
    await control_body(request);require_lease(request)
    if audio_owner:await audio_owner.close()
    await end_native_session(lease['nativeId'])
    lease['voice']=False
    if lease.get('surface')=='pleos':lease['status']='CONTROLLING'
    else:
        await reset_public_vehicle()
        lease.update(owner=None,nativeId=None,expires=0.,ending=False,status='STOPPED')
    persist_control()
    return web.json_response({'ok':True,'status':'STOPPED'})

async def surface_select(request):
    body=await control_body(request);require_lease(request)
    if body.get('surface') not in {'app','pleos'}:raise web.HTTPBadRequest()
    lease['surface']=body['surface'];persist_control()
    if body['surface']=='app':await show_app()
    return web.json_response({'ok':True})

async def session_reset(request):
    if request.get('public'):raise web.HTTPNotFound()
    require_control_origin(request);lease.update(ending=True,status='STOPPING')
    if audio_owner:await audio_owner.close()
    await end_native_session(lease['nativeId'])
    lease.update(owner=None,expires=0.0,nativeId=None,voice=False,ending=False,status='STOPPED')
    persist_control()
    return web.json_response({'ok':True,'status':'STOPPED'})

async def video(request):
    require_control_origin(request)
    if CONTEXT.profile!='public':raise web.HTTPNotFound()
    source_name=request.query.get('surface','app')
    if source_name not in encoded_sources:raise web.HTTPBadRequest()
    source=encoded_sources[source_name]
    if sum(len(x.subscribers) for x in encoded_sources.values())>=12:return web.json_response({'code':'VIEWER_LIMIT','retryable':True,'phase':'video','message':'관람 연결이 가득 찼어요. 잠시 뒤 다시 연결하거나 영상을 먼저 봐 주세요.','suggestedAction':'WATCH_RECORDING'},status=503)
    ws=web.WebSocketResponse(heartbeat=15,max_msg_size=2048);await ws.prepare(request)
    queue=await source.subscribe()
    if source_name=='app':screen.clients+=1
    # Receiving is also required on a send-only video channel: aiohttp consumes
    # heartbeat PONG frames in receive(), not in the socket writer.
    async def receive_control_frames():
        async for message in ws:
            if message.type in {WSMsgType.TEXT,WSMsgType.BINARY}:
                await ws.close(code=1008,message=b'Video channel is read-only');break
    receiver=asyncio.create_task(receive_control_frames())
    try:
        while not ws.closed:
            kind,data,meta=await asyncio.wait_for(queue.get(),8)
            await ws.send_json({'type':kind,**meta,'mime':'video/mp4; codecs="avc1.42c01f"'})
            if data:await ws.send_bytes(data)
            if kind=='error':break
    except (ConnectionError,asyncio.TimeoutError):pass
    finally:
        receiver.cancel()
        with contextlib.suppress(asyncio.CancelledError):await receiver
        source.unsubscribe(queue)
        if source_name=='app':screen.clients-=1
        await ws.close()
    return ws

async def control_socket(request):
    require_control_origin(request)
    if CONTEXT.profile!='public':raise web.HTTPNotFound()
    ws=web.WebSocketResponse(heartbeat=10,max_msg_size=4096);await ws.prepare(request)
    connection=None;sequence=-1
    try:
        message=await asyncio.wait_for(ws.receive(),3)
        if message.type!=WSMsgType.TEXT:return ws
        auth=json.loads(message.data);request['sessionToken']=auth.get('sessionToken')
        if not lease_info(request)['mine']:await ws.close(code=1008);return ws
        connection=lease['nativeId'];await ws.send_json({'type':'ready'})
        async for message in ws:
            if message.type!=WSMsgType.TEXT:break
            if not lease_info(request)['mine'] or lease['ending']:break
            data=json.loads(message.data);seq=data.get('inputSeq')
            if type(seq) is not int or seq<=sequence:raise ValueError('INPUT_SEQUENCE')
            sequence=seq
            validate_pointer_generation(data)
            result=await public_display.touch(data)
            await ws.send_json({'type':'ack','inputSeq':seq,**result})
    except (asyncio.TimeoutError,ConnectionError,ValueError,DisplayUnavailable):
        with contextlib.suppress(Exception):await ws.send_json({'type':'error','message':'화면의 조작 연결을 다시 확인해 주세요.'})
    finally:
        if connection and connection==lease['nativeId']:
            with contextlib.suppress(Exception):await public_display.release_all()
        await ws.close()
    return ws

async def snapshot_frame(request):
    if CONTEXT.profile!='public':raise web.HTTPNotFound()
    surface=request.query.get('surface','app')
    if surface=='pleos':
        pixels,meta=public_display.latest if public_display.latest and time.monotonic()-public_display.last_read<.15 else await public_display.screenshot()
        def jpeg():
            image=Image.frombytes('RGB',(meta['width'],meta['height']),pixels);data=io.BytesIO();image.save(data,'JPEG',quality=78);return data.getvalue()
        data=await asyncio.to_thread(jpeg)
    elif surface=='app':
        screen.compat_until=time.monotonic()+2
        frame=screen.app_frame(960)
        until=time.monotonic()+2
        while frame is None and time.monotonic()<until:
            await asyncio.sleep(.04);frame=screen.app_frame(960)
        if not frame:raise DeviceUnavailable('앱 화면을 준비하고 있어요.')
        data,w,h=frame;meta={'width':w,'height':h,'geometryRevision':native.get('epoch',0),'sourceSeq':screen.frames,'source':'app'}
    else:raise web.HTTPBadRequest()
    meta={**meta,'generation':f'snapshot:{public_display.pid}:{public_display.geometry_revision}'if surface=='pleos'else f'snapshot:app:{native.get("epoch",0)}'}
    return web.Response(body=data,content_type='image/jpeg',headers={'X-Pli-Frame':json.dumps(meta),'Cache-Control':'no-store'})

async def preview_info(request):
    manifest=ASSETS/'preview-info.json'
    try:
        vector=json.loads((ROOT/'artifacts/review-delivery.json').read_text());manifest=public_asset(vector['assets']['preview-manifest']['filename'])or manifest
    except (OSError,ValueError,KeyError):pass
    try:info=json.loads(manifest.read_text())
    except Exception:info={}
    build=json.loads((ROOT/'artifacts/build-info.json').read_text())
    result={k:v for k,v in info.items() if k in {'videoSha256','apkSha256','durationSeconds'}}
    result['current']=info.get('apkSha256')==build.get('apkSha256')
    if (ASSETS/'preview.vtt').exists():result['subtitles']='/preview.vtt'
    if (ASSETS/'preview-transcript.txt').exists():result['transcript']='/preview-transcript.txt'
    return web.json_response(result)

async def resources(request):
    specs=[('기획 제안서','아이와 부모를 잇는 이동 경험과 원 기획입니다.','/docs/pli-pleos-product-brief.pdf','PRODUCT BRIEF'),('결함 감사보고서','시연 결함·근본 원인·실측·남은 항목을 기록했습니다.','/docs/UX-AUDIT-2026-11-11.pdf','AUDIT'),('상세 수정 설계안','앱·전체 Pleos 분리와 모든 결함의 수정·검증 계약입니다.','/docs/REMEDIATION-DESIGN-2026-11-11.pdf','DESIGN')]
    result=[{'title':t,'description':d,'href':h,'status':tag} for t,d,h,tag in specs]
    for review in [True,False]:
        path=ROOT/'artifacts'/('review-delivery.json' if review else 'delivery.json')
        if path.exists():
            d=json.loads(path.read_text());result.append({'title':('검토용 APK' if review else '기존 정식 APK'),'description':f"버전 {d.get('version','—')} · "+('미인수 항목이 남은 검토용입니다.' if review else '이전 공개 배포본입니다. 현재 개선 작업과 구분하세요.'),'href':'/artifacts/'+('pli-pleos-review.apk' if review else 'pli-pleos.apk'),'status':'REVIEW · 미인수' if review else 'PUBLISHED'})
    try:
        vector_bytes=(ROOT/'artifacts/review-delivery.json').read_bytes();delivery=json.loads(vector_bytes)
        try:receipt=json.loads((ROOT/'artifacts/review-delivery-receipt.json').read_text())
        except (OSError,ValueError):receipt={}
        downloaded=receipt.get('passed')is True and receipt.get('deliverySha256')==hashlib.sha256(vector_bytes).hexdigest()
        result.append({'title':'다운로드 확인','description':'현재 APK·보고서·소스를 외부 HTTPS에서 모두 내려받아 확인했어요.'if downloaded else'현재 검토본의 외부 다운로드 확인을 진행하고 있어요.','status':'다운로드 확인 완료'if downloaded else'확인 중'})
        for key,title,description in [('report','구현·검증 보고서','적용한 변경, 실제 검증 결과와 남은 항목입니다.'),('source','검토용 전체 소스','개인 계정·자료를 제외한 재현 가능한 개발 소스입니다.')]:
            asset=delivery.get('assets',{}).get(key)
            if asset:result.append({'title':title,'description':description,'href':asset['href'],'status':'REVIEW · 미인수'if not delivery.get('acceptanceComplete')else'VERIFIED'})
        for item,key in zip(result[:3],['brief','audit','design']):
            if delivery.get('assets',{}).get(key):item['href']=delivery['assets'][key]['href']
    except (OSError,ValueError,KeyError):pass
    return web.json_response(result)


async def stream(request):
    if request.get('public'):raise web.HTTPNotFound()
    if screen.clients >= 8: raise web.HTTPServiceUnavailable(text='시청 연결이 많습니다. 잠시 뒤 다시 연결해 주세요.')
    response = web.StreamResponse(headers={'Content-Type': 'multipart/x-mixed-replace; boundary=pli', 'Cache-Control': 'no-store'})
    await response.prepare(request); screen.clients += 1; previous = -1
    try:
        while True:
            if request.transport is None or request.transport.is_closing(): break
            async with screen.condition:
                if screen.frames == previous: await asyncio.wait_for(screen.condition.wait(), 25)
                jpeg = screen.jpeg; previous = screen.frames
            if jpeg:
                await asyncio.wait_for(response.write(b'--pli\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n'), 8)
    except (ConnectionError, asyncio.TimeoutError, asyncio.CancelledError): pass
    finally: screen.clients -= 1
    return response

async def voice(request):
    global audio_owner,audio_client
    if not request.secure and not request.get('public') and not owner_request(request):raise web.HTTPForbidden(text='마이크 연결은 HTTPS 주소에서 사용하세요.')
    require_control_origin(request)
    try:rate=int(request.query.get('rate','48000'))
    except ValueError:raise web.HTTPBadRequest()
    if rate not in {24000,48000}:raise web.HTTPBadRequest()
    require_runtime()
    if audio_lock.locked(): raise web.HTTPConflict(text='다른 시연자가 마이크를 사용 중입니다.')
    ws=web.WebSocketResponse(heartbeat=15,max_msg_size=65536)
    await ws.prepare(request)
    try:
        auth=await asyncio.wait_for(ws.receive_json(),3)
        request['sessionToken']=auth.get('sessionToken')
        if not lease_info(request)['mine']:await ws.close(code=1008);return ws
    except Exception:
        await ws.close(code=1008);return ws
    async with audio_lock:
        audio_signal.update(last=0.0,expected=0.0,confirmed=False,signature=None)
        bridge = Audio(rate); audio_owner = ws;audio_client=client_id(request);tasks = [];connection_session=lease['nativeId'];connection_client=client_id(request)
        try:
            await bridge.open()
            async def output():
                while chunk := await bridge.reader.stdout.readexactly(rate*2//25):
                    bridge.output_bytes += len(chunk)
                    import array
                    samples=array.array('h');samples.frombytes(chunk)
                    if any(abs(x)>64 for x in samples):audio_signal['last']=time.monotonic()
                    await ws.send_bytes(chunk)
            async def keep_route():
                while True:
                    await asyncio.to_thread(bridge.route); await asyncio.sleep(.5)
            async def receive():
                async for msg in ws:
                    if msg.type == WSMsgType.BINARY:
                        if not lease_info(request)['mine'] or lease['ending'] or lease['status'] not in {'PREPARING','ACTIVE'} or time.monotonic()>=lease['expires']:await ws.close(code=1000);break
                        if len(msg.data) > 19200 or len(msg.data) % 2: await ws.close(code=1009); break
                        bridge.writer.stdin.write(msg.data); await bridge.writer.stdin.drain(); bridge.input_packets += 1
                    elif msg.type in {WSMsgType.ERROR, WSMsgType.CLOSE}: break
            tasks = [asyncio.create_task(output()), asyncio.create_task(keep_route()),asyncio.create_task(receive())]
            await ws.send_json({'type': 'ready', 'sampleRate': rate, 'format': 's16le', 'nativeMicrophone': True})
            done,_=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
            for task in done:task.result()
        except (ConnectionError, BrokenPipeError, asyncio.CancelledError): pass
        except Exception:
            log.exception('Remote audio failure')
            with contextlib.suppress(Exception): await ws.send_json({'type': 'error', 'message': '오디오 연결이 끊겼습니다. 다시 연결해 주세요.'})
        finally:
            for task in tasks: task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError, Exception): await task
            await bridge.close(); audio_owner = None;audio_client=None
            if lease['nativeId']==connection_session and lease['owner']==connection_client and not lease['ending']:
                lease.update(ending=True,status='STOPPING')
                try:
                    await end_native_session(connection_session)
                    if lease.get('surface')=='pleos':lease.update(voice=False,ending=False,status='CONTROLLING')
                    else:
                        await reset_public_vehicle()
                        lease.update(owner=None,nativeId=None,expires=0.0,voice=False,ending=False,status='STOPPED')
                    persist_control()
                except Exception:lease['status']='STOP_FAILED';request_recovery()
            with contextlib.suppress(Exception):await ws.close()
            log.info('Voice session closed; input packets=%s output bytes=%s; resource receipt controls route restoration', bridge.input_packets, bridge.output_bytes)
        return ws

async def reopen(request):
    require_control_origin(request)
    if not owner_request(request):require_lease(request)
    require_runtime()
    await show_app()
    return web.json_response({'ok': True})

async def reconnect(request):
    require_control_origin(request)
    if not owner_request(request):require_lease(request)
    (RUN_TOOLS/'runtime-paused').unlink(missing_ok=True)
    await command('systemctl','--user','start','pli-pleos-public-runtime.service'if CONTEXT.profile=='public'else'pli-pleos-runtime.service')
    return web.json_response({'ok':True,'message':'시연 환경을 다시 연결하고 있어요.'},status=202)

async def file(request):
    if request.path=='/family':
        if not owner_request(request):raise web.HTTPNotFound()
        return web.FileResponse(ASSETS/'family.html',headers={'Cache-Control':'no-store'})
    if request.get('public') and request.path in {'/font.ttf','/android/app/src/main/res/font/pretendard.ttf'}:raise web.HTTPNotFound()
    if request.path.startswith('/published/'):
        target=public_asset(request.path.removeprefix('/published/'))
        if not target:raise web.HTTPNotFound()
        return web.FileResponse(target,headers={'Cache-Control':'public, max-age=31536000, immutable','X-Content-Type-Options':'nosniff'})
    aliases={'/':'web-index','/app':'web-index','/pleos':'web-index','/resources':'web-index','/app.js':'web-js','/style.css':'web-css','/audio-worklet.js':'web-worklet','/font.woff2':'web-font','/poster.svg':'web-poster','/pleos-preview.jpg':'web-pleos','/artifacts/pli-pleos-source.zip':'source','/artifacts/pli-pleos-review-source.zip':'source','/docs/implementation-report.pdf':'report','/report':'report-html','/preview.mp4':'video','/preview.vtt':'subtitles','/preview-transcript.txt':'transcript'}
    if request.path in aliases:
        try:
            delivery=json.loads((ROOT/'artifacts/review-delivery.json').read_text());name=delivery['assets'][aliases[request.path]]['filename'];target=public_asset(name)
            if target:
                headers={'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','X-Pli-Artifact-Channel':delivery.get('channel','review')}
                if aliases[request.path]=='source':headers['Content-Disposition']='attachment; filename="pli-pleos-review-source.zip"'
                return web.FileResponse(target,headers=headers)
        except (OSError,ValueError,KeyError):pass
        if aliases[request.path]in {'source','report','report-html'}and request.get('public'):raise web.HTTPNotFound()
    mapping = {
        '/': ASSETS / 'index.html', '/app':ASSETS/'index.html','/pleos':ASSETS/'index.html','/resources':ASSETS/'index.html', '/app.js': ASSETS / 'app.js', '/style.css': ASSETS / 'style.css', '/audio-worklet.js': ASSETS / 'audio-worklet.js',
        '/font.ttf': ROOT / 'android/app/src/main/res/font/pretendard.ttf',
        '/font.woff2':ASSETS/'font.woff2','/pleos-preview.jpg':ASSETS/'pleos-preview.jpg','/preview.vtt':ASSETS/'preview.vtt','/preview-transcript.txt':ASSETS/'preview-transcript.txt','/poster.svg':ASSETS/'poster.svg','/preview.mp4':ASSETS/'preview.mp4','/preview.jpg':ASSETS/'preview.jpg',
        '/report': ROOT / 'docs/implementation-report.html',
        '/docs/implementation-report.pdf': ROOT / 'docs/implementation-report.pdf',
        '/docs/pli-pleos-product-brief.pdf': ROOT / 'docs/pli-pleos-product-brief.pdf','/docs/UX-AUDIT-2026-11-11.pdf':ROOT/'docs/UX-AUDIT-2026-11-11.pdf','/docs/REMEDIATION-DESIGN-2026-11-11.pdf':ROOT/'docs/REMEDIATION-DESIGN-2026-11-11.pdf',
        '/artifacts/pli-pleos-source.zip': ROOT / 'artifacts/pli-pleos-source.zip',
        '/android/app/src/main/res/font/pretendard.ttf': ROOT / 'android/app/src/main/res/font/pretendard.ttf',
    }
    for name in ['first-launch.png', 'driving-math.png', 'release-quiet.png']:
        mapping['/qa/native/' + name] = ROOT / 'qa/native' / name
    path = mapping.get(request.path)
    review_artifact=request.path=='/artifacts/pli-pleos-review.apk'
    if request.path=='/artifacts/pli-pleos.apk'or review_artifact:
        try:
            delivery=json.loads((ROOT/'artifacts'/('review-delivery.json'if review_artifact else'delivery.json')).read_text())
            if review_artifact and delivery.get('channel')!='review':raise ValueError('Review artifact must be explicitly labelled')
            fingerprint=delivery['apkSha256']
            if not isinstance(fingerprint,str)or not re.fullmatch('[a-f0-9]{64}',fingerprint):raise ValueError('Invalid published identity')
            path=ROOT/'.tools/published'/(fingerprint+'.apk')
        except (OSError,ValueError,KeyError):raise web.HTTPNotFound()
    if path is None or not path.exists(): raise web.HTTPNotFound()
    response=web.FileResponse(path)
    if review_artifact:response.headers.update({'X-Pli-Artifact-Channel':'review','Cache-Control':'no-store','Content-Disposition':'attachment; filename="pli-pleos-review.apk"'})
    if path.parent==ASSETS and path.suffix in {'.css','.js','.woff2','.svg','.jpg','.mp4'}:response.headers['Cache-Control']='public, max-age=3600'
    return response

async def diagnostics(request):
    if request.get('public'):raise web.HTTPNotFound()
    values=sorted(video_ack_ms)
    return web.json_response({'captureP50Ms':sorted(screen.capture_ms)[len(screen.capture_ms)//2] if screen.capture_ms else None,'captureFrames':len(screen.capture_ms),'videoBytes':video_bytes,'acks':len(values),'ackP50Ms':values[len(values)//2] if values else None,'ackP95Ms':values[min(len(values)-1,int(len(values)*.95))] if values else None})

async def lifecycle(app):
    recover_audio()
    screen.task = asyncio.create_task(screen.run())
    poll = asyncio.create_task(monitor())
    maintenance=asyncio.create_task(housekeeping())
    yield
    lease.update(ending=True,status='STOPPING')
    if audio_owner: await audio_owner.close(code=1001, message=b'Server stopping')
    if native.get('demo') and native.get('active'):
        try:await end_native_session(native.get('sessionId'))
        except Exception:log.error('Native stop not confirmed during shutdown')
    poll.cancel()
    maintenance.cancel()
    with contextlib.suppress(asyncio.CancelledError): await poll
    with contextlib.suppress(asyncio.CancelledError): await maintenance
    for source in encoded_sources.values():await source.close()
    if public_display:await public_display.close()
    await screen.close()

async def main():
    app = web.Application(middlewares=[boundaries], client_max_size=65536)
    app.router.add_get('/api/status', status)
    app.router.add_get('/api/personal/status', status)
    app.router.add_get('/api/family/destinations',family_destinations)
    app.router.add_post('/api/family/destinations',family_destinations)
    app.router.add_post('/api/family/plan',family_plan)
    app.router.add_get('/api/kidsnote/status',kids_status)
    app.router.add_get('/api/kidsnote/options',kids_options)
    app.router.add_post('/api/kidsnote/sync',kids_sync)
    app.router.add_get('/api/kidsnote/login',kids_login)
    app.router.add_post('/api/kidsnote/login',kids_login)
    app.router.add_post('/api/kidsnote/personal',kids_personal)
    app.router.add_get('/live.mjpg', stream)
    app.router.add_get('/voice', voice)
    app.router.add_get('/video',video)
    app.router.add_get('/control',control_socket)
    app.router.add_get('/snapshot',snapshot_frame)
    app.router.add_get('/api/preview',preview_info)
    app.router.add_get('/api/resources',resources)
    app.router.add_get('/api/diagnostics',diagnostics)
    app.router.add_post('/api/session/claim',session_claim)
    app.router.add_post('/api/session/prepare',session_prepare)
    app.router.add_post('/api/session/begin',session_begin)
    app.router.add_post('/api/session/end',session_end)
    app.router.add_post('/api/session/reset',session_reset)
    app.router.add_post('/api/session/voice-end',voice_end)
    app.router.add_post('/api/session/surface',surface_select)
    app.router.add_post('/api/reopen', reopen)
    app.router.add_post('/api/reconnect', reconnect)
    app.router.add_post('/api/input', device_input)
    app.router.add_post('/api/vehicle', vehicle_control)
    app.router.add_get('/{path:.*}', file)
    app.cleanup_ctx.append(lifecycle)
    runner = web.AppRunner(app, access_log=None); await runner.setup()
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(TOOLS / 'demo-tls/cert.pem', TOOLS / 'demo-tls/key.pem')
    for host in [IP, '127.0.0.1']:
        await web.TCPSite(runner, host, SHARED_HTTPS_PORT, ssl_context=tls).start()
        await web.TCPSite(runner, host, HTTPS_PORT, ssl_context=tls).start()
        await web.TCPSite(runner, host, HTTP_PORT).start()
    log.info('Pli demo ready: https://%s:%s / http://%s:%s', IP, SHARED_HTTPS_PORT, IP, HTTP_PORT)
    finished = asyncio.Event()
    for sig in [signal.SIGINT, signal.SIGTERM]: asyncio.get_running_loop().add_signal_handler(sig, finished.set)
    await finished.wait(); await runner.cleanup()

if __name__ == '__main__': asyncio.run(main())
