#!/usr/bin/env python3
"""Hide the earlier film's (invented) child face in a reference video, so a video model that copies the
reference's staging takes the child's face only from 하연's photos.

Each frame: YuNet finds the faces; the one most like 하연 (SFace vs her four photos; the invented child is
closer to her than the mother is) is blurred heavily, with the box carried over frames where detection
misses. usage: .tools/edge-venv/bin/python scripts/blur-reference-child.py IN.mp4 OUT.mp4 [X0,X1]
(X0,X1 = where the child sits, as fractions of the frame width; default the whole frame;
'all' blurs every face, so the mother's face also comes only from her reference image)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_identity  # noqa: E402


def child_box(frame: np.ndarray, x_range: tuple) -> list | None:
    """The child's face: only faces whose centre lies in x_range (fractions of the width), the one most like 하연."""
    width = frame.shape[1]
    found = [f for f in film_identity.faces(frame) if x_range[0] <= (f['box'][0] + f['box'][2] / 2) / width <= x_range[1]]
    if not found:
        return None
    return max(found, key=lambda f: film_identity.similarity(f['embedding'])['best'])['box']


def main() -> int:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    everyone = len(sys.argv) > 3 and sys.argv[3] == 'all'
    x_range = tuple(float(v) for v in sys.argv[3].split(',')) if len(sys.argv) > 3 and not everyone else (0.0, 1.0)
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', str(out)], stdin=subprocess.PIPE)
    last, misses, n = None, 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        found = [f['box'] for f in film_identity.faces(frame)] if everyone else [child_box(frame, x_range)]
        found = [b for b in found if b]
        if not found:
            misses += 1
            found = last or []
        last = found or last
        for box in found:
            x, y, bw, bh = box
            x0, y0 = max(0, x - bw // 2), max(0, y - bh // 2)
            x1, y1 = min(w, x + bw + bw // 2), min(h, y + bh + bh // 3)
            region = frame[y0:y1, x0:x1]
            frame[y0:y1, x0:x1] = cv2.GaussianBlur(cv2.resize(cv2.resize(region, (8, 8)), (x1 - x0, y1 - y0)), (0, 0), 9)  # noqa: E501
        enc.stdin.write(frame.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    print({'frames': n, 'detectionMisses': misses})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
