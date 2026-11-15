#!/usr/bin/env python3
"""Find where the real child's name is drawn in a recorded app take (film redaction).

The public emulator shows the family profile; the film's family is fictional, so
the name is removed from every app cut. Templates are crops of the name as the
app's own font renders it (.tools/product-film/redact/name-*.png, private). The
union of matches over frames sampled through the cut is printed as source-pixel
boxes for ffmpeg `delogo`. Needs OpenCV (.tools/edge-venv).

usage: film_redact.py TAKE.webm IN OUT [X,Y,W,H]
"""
from pathlib import Path
import json, sys

import cv2

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = sorted((ROOT / '.tools/product-film/redact').glob('name-*.png'))
MATCH = 0.82
PAD = 5
STEP_SECONDS = 0.2


def matches(gray, template) -> list:
    h, w = template.shape
    score = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    ys, xs = (score >= MATCH).nonzero()
    return [(int(x), int(y), w, h) for x, y in zip(xs, ys)]


def merge(boxes: list) -> list:
    """Overlapping or touching hits of the same word become one padded box."""
    merged = []
    for x, y, w, h in sorted(boxes):
        box = [x - PAD, y - PAD, w + 2 * PAD, h + 2 * PAD]
        for other in merged:
            if box[0] <= other[0] + other[2] and other[0] <= box[0] + box[2] and box[1] <= other[1] + other[3] and other[1] <= box[1] + box[3]:
                right, bottom = max(other[0] + other[2], box[0] + box[2]), max(other[1] + other[3], box[1] + box[3])
                other[0], other[1] = min(other[0], box[0]), min(other[1], box[1])
                other[2], other[3] = right - other[0], bottom - other[1]
                break
        else:
            merged.append(box)
    return merged


def main() -> int:
    clip, start, end = Path(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
    region = [int(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else None  # x,y,w,h searched
    templates = [cv2.imread(str(t), cv2.IMREAD_GRAYSCALE) for t in TEMPLATES]
    if not templates:
        raise SystemExit('No name templates in .tools/product-film/redact')
    video = cv2.VideoCapture(str(clip))  # decoded from the first frame: seeking lands on keyframes, past `start`
    hits, sampled, last = [], 0, -1.0
    while True:  # decode forward once; sample about every STEP_SECONDS
        ok, frame = video.read()
        if not ok:
            break
        at = video.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if at > end + 0.1:
            break
        if at < start - 0.05 or at - last < STEP_SECONDS:
            continue
        last = at
        x0, y0 = (region[0], region[1]) if region else (0, 0)
        view = frame[region[1]:region[1] + region[3], region[0]:region[0] + region[2]] if region else frame
        gray = cv2.cvtColor(view, cv2.COLOR_BGR2GRAY)
        for template in templates:
            hits += [(x + x0, y + y0, w, h) for x, y, w, h in matches(gray, template)]
        sampled += 1
    if sampled == 0:
        raise SystemExit(f'{clip.name}: no frames between {start}s and {end}s')
    print(json.dumps({'boxes': merge(hits), 'frames': sampled}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
