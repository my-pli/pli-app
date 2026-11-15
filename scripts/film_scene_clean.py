#!/usr/bin/env python3
"""A generated family scene made ready for the film, in one reproducible pass (v10; v9 did these steps by hand):

  1. mask      the captions LTX-2 burns in (scripts/film_caption_mask.py)          -> <dir>/<name>-mask.mp4
  2. erase     DiffuEraser on Hugging Face (fffiloni/DiffuEraser-demo) fills the masked area -> clean/<name>-erased.mp4
  3. merge     only the masked area (feathered) is taken from the erased clip, at the clip's own size and frame count
                                                                                   -> clean/<name>.mp4
  4. upscale   Real-ESRGAN x2 to 1080x1920 (tall) or 1920x1080 (wide) (scripts/film_upscale.py) -> clean/<name>-hd.mp4
  5. scan      drawn defects (scripts/film_artifact_scan.py)                       -> scan/<name>-hd-artifacts.json

A clip whose mask is empty skips steps 2-3. Every step's output is kept, so a step can be redone alone (--from).
usage: .tools/qwen-tts-venv/bin/python scripts/film_scene_clean.py DIR NAME [NAME ...] [--from erase|merge|upscale|scan]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_caption_mask  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ERASER = 'fffiloni/DiffuEraser-demo'
STEPS = ['mask', 'erase', 'merge', 'upscale', 'scan']
FEATHER = 6  # px of blur on the mask edge, so the filled area has no seam


def run(args: list) -> None:
    subprocess.run(args, check=True)


def frame_count(path: Path) -> int:
    return int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                                        'stream=nb_read_frames', '-of', 'csv=p=0', str(path)]).decode().strip())


def size(path: Path) -> tuple:
    w, h = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                    '-of', 'csv=p=0', str(path)]).decode().strip().split(',')
    return int(w), int(h)


def erase(clip: Path, mask: Path, target: Path) -> None:
    from gradio_client import Client, handle_file
    token = (Path.home() / '.cache/huggingface/token').read_text().strip()
    client = Client(ERASER, token=token, verbose=False)
    result = client.predict(input_video=handle_file(str(clip)), input_mask=handle_file(str(mask)), api_name='/infer')
    produced = result.get('video') if isinstance(result, dict) else (result[0] if isinstance(result, (list, tuple)) else result)
    shutil.copyfile(produced, target)


def merge(clip: Path, erased: Path, mask_png: Path, target: Path) -> None:
    """The erased clip only where the mask is (feathered), at the original size; frames past the erased clip's end keep
    its last frame, so the result has exactly the original's frames and its sound."""
    w, h = size(clip)
    n = frame_count(clip)
    run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(clip), '-i', str(erased), '-loop', '1', '-i', str(mask_png),
         '-filter_complex',
         f'[1:v]scale={w}:{h}:flags=lanczos,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop=48,format=yuva420p[e];'
         f'[2:v]scale={w}:{h},format=gray,gblur=sigma={FEATHER}[m];[e][m]alphamerge[em];'
         f'[0:v][em]overlay=0:0:shortest=0:eof_action=pass,format=yuv420p[v]',
         '-map', '[v]', '-map', '0:a?', '-frames:v', str(n), '-c:v', 'libx264', '-crf', '12', '-c:a', 'copy', str(target)])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', type=Path)
    parser.add_argument('names', nargs='+')
    parser.add_argument('--from', dest='start', choices=STEPS, default='mask')
    parser.add_argument('--no-vlm', action='store_true')
    args = parser.parse_args()
    folder = args.dir if args.dir.is_absolute() else ROOT / args.dir
    clean, scan = folder / 'clean', folder / 'scan'
    clean.mkdir(exist_ok=True)
    scan.mkdir(exist_ok=True)
    first = STEPS.index(args.start)
    failures = 0
    for name in args.names:
        clip = folder / f'{name}.mp4'
        mask_png, mask_mp4 = folder / f'{name}-mask.png', folder / f'{name}-mask.mp4'
        erased, merged, hd = clean / f'{name}-erased.mp4', clean / f'{name}.mp4', clean / f'{name}-hd.mp4'
        started, record = time.time(), {'scene': name, 'dir': str(folder.relative_to(ROOT))}
        try:
            if first <= 0:
                m = film_caption_mask.mask(clip)
                film_caption_mask.write(clip, m)
                record['maskShare'] = round(float((m > 0).mean()), 4)
            masked = bool(cv2.imread(str(mask_png), 0).any())
            if not masked:
                shutil.copyfile(clip, merged)
            else:
                if first <= 1:
                    erase(clip, mask_mp4, erased)
                if first <= 2:
                    merge(clip, erased, mask_png, merged)
            if first <= 3:
                run([sys.executable, str(ROOT / 'scripts/film_upscale.py'), str(merged), str(hd)])
            if first <= 4:
                scan_args = [sys.executable, str(ROOT / 'scripts/film_artifact_scan.py'), str(hd), '--out', str(scan)]
                subprocess.run(scan_args + (['--no-vlm'] if args.no_vlm else []), check=False)
                report = json.loads((scan / f'{name}-hd-artifacts.json').read_text())
                record['findings'] = report['counts']
            record['frames'] = {'generated': frame_count(clip), 'hd': frame_count(hd)}
        except Exception as error:
            failures += 1
            record['error'] = f'{type(error).__name__}: {error}'[:300]
        record['elapsed'] = round(time.time() - started, 1)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
