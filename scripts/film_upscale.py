#!/usr/bin/env python3
"""Sharper vertical scenes for the 1080x1920 short: Real-ESRGAN x2 on every frame of a 704x1248 generated clip, then down
to 1080x1920 (the film used a plain 1.54x Lanczos stretch in v8). Runs on this computer's GPU in tiles (it is shared).

usage: .tools/qwen-tts-venv/bin/python scripts/film_upscale.py IN.mp4 OUT.mp4
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / '.tools/edge-ai/models/upscale/RealESRGAN_x2plus.pth'
OUT_W, OUT_H = 1080, 1920  # a tall clip; a wide one (v10 landscape film) goes to 1920x1080
TILE = 416


def upscale_frame(model, frame: np.ndarray) -> np.ndarray:
    x = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0).float().div(255).cuda().half()
    _, _, h, w = x.shape
    out = torch.zeros((1, 3, h * 2, w * 2), dtype=torch.float16, device='cuda')
    with torch.no_grad():
        for y0 in range(0, h, TILE):
            for x0 in range(0, w, TILE):  # tiles with a 16 px overlap, kept from their centre
                ya, xa = max(0, y0 - 16), max(0, x0 - 16)
                yb, xb = min(h, y0 + TILE + 16), min(w, x0 + TILE + 16)
                part = model(x[:, :, ya:yb, xa:xb])
                cy, cx = (y0 - ya) * 2, (x0 - xa) * 2
                th, tw = min(TILE, h - y0) * 2, min(TILE, w - x0) * 2
                out[:, :, y0 * 2:y0 * 2 + th, x0 * 2:x0 * 2 + tw] = part[:, :, cy:cy + th, cx:cx + tw]
    return out.clamp(0, 1).mul(255).byte().squeeze(0).permute(1, 2, 0).cpu().numpy()


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    w, h = (int(v) for v in subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                                     'stream=width,height', '-of', 'csv=p=0', str(src)]).decode().split(','))
    out_w, out_h = (OUT_W, OUT_H) if h > w else (OUT_H, OUT_W)
    fps = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                                   '-of', 'csv=p=0', str(src)]).decode().strip()
    model = ModelLoader().load_from_file(str(MODEL)).model.cuda().eval().half()
    reader = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(src), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                              stdout=subprocess.PIPE)
    writer = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w * 2}x{h * 2}',
                               '-framerate', fps, '-i', '-', '-i', str(src), '-map', '0:v', '-map', '1:a?',
                               '-vf', f'scale={out_w}:{out_h}:flags=lanczos', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p',
                               '-c:a', 'copy', str(dst)], stdin=subprocess.PIPE)
    n = 0
    while True:
        raw = reader.stdout.read(w * h * 3)
        if len(raw) < w * h * 3:
            break
        writer.stdin.write(upscale_frame(model, np.frombuffer(raw, np.uint8).reshape(h, w, 3)).tobytes())
        n += 1
    writer.stdin.close()
    writer.wait()
    print(f'{src.name}: {n} frames -> {dst.name} ({out_w}x{out_h})', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
