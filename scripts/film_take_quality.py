#!/usr/bin/env python3
"""Is an app take good enough for the film? Two things the 2026-11-14 v6 review found by eye and ear:

  vehicleFps   how often the Pleos vehicle view (left panel: the car on the road) actually changes. The grab is a
               steady 30 fps either way; when the shared host is loaded the emulator itself redraws that view only
               3-4 times a second (v6 album/stop takes 2.6-3.6, pack 21.8, an idle check 23.3) and the drive stutters.
  dropouts     Pli's voice stopping dead mid-word (5-180 ms seen): digital silence entered straight from speech level,
               the emulator's audio running dry under load (v6: 11 in the album and stop takes). A pause the voice
               model makes fades out first, so it is not counted.

usage: .tools/edge-venv/bin/python scripts/film_take_quality.py TAKE [...]   (pack, album, stop)
exit 1 when a take is below the bar.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TAKES = ROOT / '.tools/product-film/app-takes'
VEHICLE = (0, 100, 250, 700)        # x0, y0, x1, y1 of the vehicle view in a 1600x900 stream (scaled to the take's size)
CHANGE = 5000                       # summed |difference| of a redrawn vehicle view at 1600x900 (encoder noise stays < 2000)
MIN_MEAN_FPS, MIN_LOW_FPS = 18.0, 10.0
RATE, HOP = 44100, 0.005
SILENT_DB, SPEECH_DB = -80.0, -45.0
DROPOUT_MAX = 1.0  # any length: digital silence entered from speech level is the device running dry (v7 take: 150-180 ms gaps mid-sentence)


def vehicle_fps(video: Path, start: float, end: float | None = None) -> dict:
    width = int(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width',
                                         '-of', 'csv=p=0', str(video)]).decode().strip())
    scale = width / 1600
    x0, y0, x1, y1 = (round(v * scale) for v in VEHICLE)
    change = CHANGE * scale * scale
    span = ['-to', f'{end:.2f}'] if end is not None else []
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{start:.2f}', *span, '-i', str(video),
                                   '-vf', f'crop={x1 - x0}:{y1 - y0}:{x0}:{y0},format=gray', '-f', 'rawvideo', '-'])
    frames = np.frombuffer(raw, np.uint8).reshape(-1, y1 - y0, x1 - x0).astype(np.int16)
    changed = np.abs(np.diff(frames, axis=0)).sum(axis=(1, 2)) > change
    per_second = [int(changed[i:i + 30].sum()) for i in range(0, len(changed) - 29, 30)]
    if not per_second and len(changed):  # under a second on screen (v8 app cuts show the whole display for 1 s): a rate
        per_second = [round(float(changed.sum()) * 30 / len(changed), 1)]
    return {'mean': round(float(np.mean(per_second)), 1) if per_second else 0.0,
            'p10': round(float(np.percentile(per_second, 10)), 1) if per_second else 0.0, 'perSecond': per_second}


def dropouts(wav: Path, start: float = 0.0, end: float | None = None) -> list:
    span = ['-ss', f'{start:.3f}'] + (['-to', f'{end:.3f}'] if end is not None else [])
    x = np.frombuffer(subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', *span, '-i', str(wav), '-ac', '1', '-ar', str(RATE),
                                               '-f', 'f32le', '-']), np.float32)
    hop = int(RATE * HOP)
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-12)
    found, i = [], 0
    while i < n:
        if db[i] >= SILENT_DB:
            i += 1
            continue
        j = i
        while j < n and db[j] < SILENT_DB:
            j += 1
        length = (j - i) * HOP
        before, after = db[i - 1] if i else -999, db[j] if j < n else -999
        if length <= DROPOUT_MAX and before > SPEECH_DB and after > SPEECH_DB:
            found.append({'at': round(start + i * HOP, 3), 'ms': round(length * 1000)})
        i = j
    return found


def check(take: str) -> dict:
    record = json.loads((TAKES / f'{take}.json').read_text())
    drive_at = next((t['clipAt'] for t in record['turns'] if t.get('vehicle')), 0.0) + 1.0  # the take may start parked
    fps = vehicle_fps(TAKES / f'{take}.mp4', drive_at)
    drops = dropouts(TAKES / record['appSound']['file'])
    ok = fps['mean'] >= MIN_MEAN_FPS and fps['p10'] >= MIN_LOW_FPS and not drops
    return {'take': take, 'ok': ok, 'vehicleFps': {k: fps[k] for k in ('mean', 'p10')}, 'dropouts': drops,
            'recordedAt': record['recordedAt']}


def main() -> int:
    results = [check(take) for take in sys.argv[1:] or ('pack', 'album', 'stop')]
    for row in results:
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return 0 if all(r['ok'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
