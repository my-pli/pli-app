#!/usr/bin/env python3
"""Masks of the captions LTX-2 burns into a generated clip (garbled text, always in the lower part of the frame).

A caption is drawn the same in every frame of a clip, while the people and the cabin move: its pixels have a strong
edge (white glyphs, dark outline) and almost no change over time. Those pixels below MIN_Y of the frame, grown by a few
pixels, are the mask that scripts/make-vertical-scenes.py hands to the video inpainting Space (DiffuEraser).

usage: .tools/edge-venv/bin/python scripts/film_caption_mask.py CLIP.mp4 [...]   -> CLIP-mask.mp4, CLIP-mask.png
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

MIN_Y = 0.52        # captions never started above 65% of the frame (2026-11-14 clips); a margin above that
STROKE = 70         # white top-hat response of a glyph stroke (gray levels above its 13x13 surroundings)
STILL = 6.0         # temporal std (gray levels) of pixels that do not move
GROW = 9            # pixels added around the glyphs
PAD = 18            # pixels around the caption block (it sits on a translucent dark box)
GAP = 40            # caption lines closer than this are one block


def frames(path: Path) -> np.ndarray:
    probe = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                     '-of', 'csv=p=0', str(path)]).decode().strip().split(',')
    w, h = int(probe[0]), int(probe[1])
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w)


DETECTOR = Path(__file__).resolve().parents[1] / '.tools/edge-ai/models/text/ppocr_cn.onnx'  # OpenCV zoo PP-OCRv3 (DB)


def detector():
    model = cv2.dnn_TextDetectionModel_DB(str(DETECTOR))
    model.setBinaryThreshold(0.3).setPolygonThreshold(0.5).setMaxCandidates(200).setUnclipRatio(2.0)
    model.setInputParams(1.0 / 255.0, (736, 736), (122.67891434, 116.66876762, 104.00698793))
    return model


def mask(path: Path) -> np.ndarray:
    """Text boxes found by a text detector in frames across the clip, below MIN_Y, as one padded rectangle per line."""
    probe = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                     '-of', 'csv=p=0', str(path)]).decode().strip().split(',')
    w, h = int(probe[0]), int(probe[1])
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'])
    video = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    model = detector()
    lines = []
    for frame in video[:: max(1, len(video) // 12)]:
        boxes, _scores = model.detect(np.ascontiguousarray(frame))
        for quad in boxes:
            quad = np.array(quad)
            x0, y0 = quad.min(axis=0)
            x1, y1 = quad.max(axis=0)
            if y0 >= h * MIN_Y and (x1 - x0) >= 30:
                lines.append([int(x0), int(y0), int(x1), int(y1)])
    blocks = []  # lines less than GAP apart belong to one caption (with its translucent box between them)
    for x0, y0, x1, y1 in sorted(lines, key=lambda b: b[1]):
        if blocks and y0 - blocks[-1][3] < GAP and x0 < blocks[-1][2] and x1 > blocks[-1][0]:
            b = blocks[-1]
            blocks[-1] = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]
        else:
            blocks.append([x0, y0, x1, y1])
    keep = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in blocks:
        keep[max(0, y0 - PAD):min(h, y1 + PAD), max(0, x0 - PAD):min(w, x1 + PAD)] = 255
    return keep


def write(path: Path, m: np.ndarray) -> Path:
    n = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'csv=p=0', str(path)]).decode().strip())
    fps = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                                   '-of', 'csv=p=0', str(path)]).decode().strip()
    png = path.with_name(path.stem + '-mask.png')
    cv2.imwrite(str(png), m)
    out = path.with_name(path.stem + '-mask.mp4')
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-loop', '1', '-framerate', fps, '-i', str(png), '-frames:v', str(n),
                    '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '0', str(out)], check=True)
    return out


def main() -> int:
    for arg in sys.argv[1:]:
        path = Path(arg)
        m = mask(path)
        out = write(path, m)
        print(f'{path.name}: {round(float((m > 0).mean()) * 100, 2)}% of the frame masked -> {out.name}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
