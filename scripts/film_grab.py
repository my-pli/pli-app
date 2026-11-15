#!/usr/bin/env python3
"""Grab the public emulator's display for the product film, at native pixels and a steady 30 fps.

The emulator's own WebM recorder drops to 6-10 fps while the edge AI is busy;
its gRPC screenshot stream keeps up. Only the given region (x,y,w,h, display
pixels) is kept, so the profile header with the family's photo is never even
written to disk. Frames are paced on the wall clock (latest frame repeated when
the screen did not change); each frame carries its wall-clock time, so clip time t is
`startedAt + t` even when the host is busy.
Stops on SIGINT/SIGTERM. Needs grpc (.tools/demo-venv).

The emulator scales each screenshot itself when asked for a smaller size: a 2560x1440 grab (11 MB a
frame) only reached 15-24 fps (lateFrames = every frame, 2026-11-14 audit), while the film is 1920x1080
anyway, so frames are requested at STREAM size and the region is given in display pixels.

usage: film_grab.py OUT.mp4 X,Y,W,H [STREAM_WxH]   (default stream 1600x900)
"""
from pathlib import Path
import asyncio, collections, json, os, signal, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import grpc  # noqa: E402
import numpy as np  # noqa: E402
from emulator_proto import emulator_controller_pb2 as pb  # noqa: E402
from emulator_proto import emulator_controller_pb2_grpc as rpc  # noqa: E402
from runtime_context import DeviceContext  # noqa: E402

FPS = 30
HISTORY = 48  # screenshots kept for slots written late (48 x 5.8 MB at 1600x900 RGBA)
ENCODER = ['h264_nvenc', '-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-cq', '16', '-b:v', '0']
DISPLAY = (2560, 1440)
STREAM = (1600, 900)  # 1920x1080 held only 18-26 fps on the shared host; 1600x900 = 30 fps (2026-11-14)


def channel() -> tuple:
    pid = DeviceContext('public').assert_owned()  # the isolated public AVD only
    ini = Path('/run/user') / str(os.getuid()) / f'avd/running/pid_{pid}.ini'
    fields = dict(line.split('=', 1) for line in ini.read_text().splitlines() if '=' in line)
    auth = (('authorization', 'Bearer ' + fields['grpc.token'].strip()),)
    chan = grpc.aio.insecure_channel(f"127.0.0.1:{int(fields['grpc.port'])}",
                                     options=[('grpc.max_receive_message_length', 64 * 1024 * 1024)])
    return chan, rpc.EmulatorControllerStub(chan), auth


async def grab(out: Path, region: list, stream: tuple = STREAM) -> dict:
    sx, sy = stream[0] / DISPLAY[0], stream[1] / DISPLAY[1]  # display pixels -> streamed pixels
    x, y = round(region[0] * sx), round(region[1] * sy)
    w, h = round(region[2] * sx), round(region[3] * sy)
    w, h = w - w % 2, h - h % 2  # yuv420p needs even sizes
    chan, stub, auth = channel()
    # Constant 30 fps by slots: every screenshot is kept with the wall-clock time it arrived, and output frame
    # k (time k/30 after start) is the newest screenshot that had arrived by then. Writing may lag behind
    # (pipe back-pressure on the busy host) without moving any frame in time; the history covers HISTORY
    # slots of lag. The earlier wall-clock-stamped variable-rate stream was written in bursts (frame gaps
    # 3-63 ms, 23 % over 50 ms) and its 25 fps input time base rounded stamps to 40 ms (2026-11-14 QA).
    # NVENC takes the RGBA frames as they are and converts colour on the GPU.
    encoder = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                                '-f', 'rawvideo', '-framerate', str(FPS), '-pix_fmt', 'rgba', '-s', f'{w}x{h}', '-i', '-',
                                '-c:v', ENCODER[0], *ENCODER[1:], str(out)], stdin=subprocess.PIPE)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    history: collections.deque = collections.deque(maxlen=HISTORY)  # (arrival time, frame)
    unique = 0
    fmt = pb.ImageFormat(format=pb.ImageFormat.RGBA8888, display=0, width=stream[0], height=stream[1])

    async def receive():
        nonlocal unique
        async for image in stub.streamScreenshot(fmt, metadata=auth):
            history.append((time.time(), (image.image, image.format.width, image.format.height)))
            unique += 1
            if stop.is_set():
                return

    def crop(frame) -> bytes:
        data, iw, ih = frame
        if (x, y, w, h) == (0, 0, iw, ih):  # the whole screen: hand the bytes over without a copy
            return data
        return np.frombuffer(data, np.uint8).reshape(ih, iw, 4)[y:y + h, x:x + w].tobytes()

    def at(slot_time: float) -> tuple:
        """The newest screenshot that had arrived by slot_time (and whether the history ran out)."""
        for arrived, frame in reversed(history):
            if arrived <= slot_time:
                return frame, False
        return history[0][1], True

    reader = asyncio.create_task(receive())
    while not history and not reader.done():
        await asyncio.sleep(0.005)
    if not history:
        raise SystemExit('No frame from the public emulator')
    started, frames, late, stale = time.time(), 0, 0, 0
    print(json.dumps({'ready': started}), flush=True)
    stopped_at = None
    while True:
        if stop.is_set() and stopped_at is None:
            stopped_at = time.time()  # catch up to the moment it was told to stop, not to a "now" that keeps moving (2026-11-15:
        if stopped_at is not None and started + frames / FPS > stopped_at:  # at host load 40-50 the writer ran slower than real
            break                                                          # time and never stopped)
        slot = started + frames / FPS
        wait = slot - time.time()
        if wait > 0:
            await asyncio.sleep(wait)
        elif wait < -1.0 / FPS:
            late += 1  # written behind its time; its picture is still the one from its time
        frame, ran_out = at(slot)
        stale += ran_out
        await loop.run_in_executor(None, encoder.stdin.write, crop(frame))
        frames += 1
    reader.cancel()
    encoder.stdin.close()
    encoder.wait(timeout=60)
    await chan.close()
    return {'startedAt': started, 'stoppedAt': time.time(), 'frames': frames, 'lateFrames': late, 'staleFrames': stale, 'fps': FPS,
            'region': region, 'stream': list(stream), 'streamRegion': [x, y, w, h], 'uniqueFrames': unique, 'timestamps': 'cfr-slots'}


def main() -> int:
    out, region = Path(sys.argv[1]), [int(v) for v in sys.argv[2].split(',')]
    stream = tuple(int(v) for v in sys.argv[3].split('x')) if len(sys.argv) > 3 else STREAM
    record = asyncio.run(grab(out, region, stream))
    Path(str(out) + '.json').write_text(json.dumps(record))
    print(json.dumps(record), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
