#!/usr/bin/env python3
"""Reference images for the film's Figma Weave generations.

- 하연: all four photos the user shared (IMG_0606~0609), each cropped to her head and shoulders,
  with any other child's face blurred first (one photo has another child at its edge).
- 더 뉴 그랜저: Hyundai's official launch photos (.tools/product-film/grandeur-official, from the
  Hyundai Motor Group newsroom 2026-05-14). Inside the car, the 17-inch Pleos Connect display gets
  the real Pli app on its right two thirds (a screenshot of the public Pleos emulator); the left
  vehicle panel and the dock stay as Hyundai photographed them, since that is what the real car shows.

Writes .tools/private-family/weave-refs/hayeon-*.png (private) and
.tools/product-film/weave-refs/*.png. usage: .tools/edge-venv/bin/python scripts/prepare-weave-refs.py PLEOS_SCREENSHOT.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_identity  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / '.tools/product-film/grandeur-official'
CHILD_OUT = ROOT / '.tools/private-family/weave-refs'
CAR_OUT = ROOT / '.tools/product-film/weave-refs'
# news-6.jpg (1920x1080, dashboard from the rear seat): the 17-inch display's active area and the
# end of its left vehicle panel / start of its bottom dock, measured on a zoomed crop.
DISPLAY = (776, 495, 1128, 691)
PANEL_END_X = 890
STATUS_BOTTOM_Y = 512  # the car's own status row stays
DOCK_TOP_Y = 670
EMULATOR_APP = (854, 90, 2560, 1300)  # Pli's area on the 2560x1440 Pleos display (below the status bar, above the dock)


def blur_box(image: np.ndarray, box: list) -> None:
    x, y, w, h = box
    x0, y0, x1, y1 = max(0, x - w // 4), max(0, y - h // 4), min(image.shape[1], x + w + w // 4), min(image.shape[0], y + h + h // 4)
    image[y0:y1, x0:x1] = cv2.GaussianBlur(image[y0:y1, x0:x1], (0, 0), 25)


def child_refs() -> list:
    CHILD_OUT.mkdir(parents=True, exist_ok=True)
    picks = film_identity.child_faces()
    written = []
    for path in sorted(film_identity.DRIVE.glob('*.JPG')):
        image = cv2.imread(str(path))
        child = picks[path.name]
        for face in film_identity.drive_faces()[path.name]:
            if face is not child:
                blur_box(image, face['box'])
        x, y, w, h = child['box']
        cx = x + w / 2
        x0, x1 = int(max(0, cx - 1.7 * w)), int(min(image.shape[1], cx + 1.7 * w))
        y0, y1 = int(max(0, y - 0.9 * h)), int(min(image.shape[0], y + 3.4 * h))
        crop = image[y0:y1, x0:x1]
        target = CHILD_OUT / f'hayeon-{path.stem[-4:]}.png'
        cv2.imwrite(str(target), crop)
        check = film_identity.check_image(crop)
        written.append({'file': str(target.relative_to(ROOT)), 'size': [crop.shape[1], crop.shape[0]], 'best': check and check['best']})
    return written


def cabin_with_pli(screenshot: Path) -> dict:
    CAR_OUT.mkdir(parents=True, exist_ok=True)
    cabin = cv2.imread(str(OFFICIAL / 'news-6.jpg'))
    screen = cv2.imread(str(screenshot))
    if screen is None or screen.shape[:2] != (1440, 2560):
        raise SystemExit(f'{screenshot}: expected a 2560x1440 Pleos screenshot')
    sx0, sy0, sx1, sy1 = EMULATOR_APP
    app = screen[sy0:sy1, sx0:sx1]
    dx0, dy0, dx1 = PANEL_END_X, STATUS_BOTTOM_Y, DISPLAY[2]
    fitted = cv2.resize(app, (dx1 - dx0, DOCK_TOP_Y - dy0), interpolation=cv2.INTER_AREA)
    region = cabin[dy0:DOCK_TOP_Y, dx0:dx1].astype(np.float32)
    cabin[dy0:DOCK_TOP_Y, dx0:dx1] = np.clip(fitted.astype(np.float32) * 0.94 + region * 0.06, 0, 255).astype(np.uint8)  # keep a trace of the glass
    target = CAR_OUT / 'grandeur-cabin-pli.png'
    cv2.imwrite(str(target), cabin)
    return {'file': str(target.relative_to(ROOT)), 'screenshot': str(screenshot)}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    report = {'child': child_refs(), 'cabin': cabin_with_pli(Path(sys.argv[1]))}
    for name in ('news-1.jpg', 'news-2.jpg', 'news-5.jpg', 'news-7.jpg'):
        image = cv2.imread(str(OFFICIAL / name))
        target = CAR_OUT / f"grandeur-{name.replace('.jpg', '.png')}"
        cv2.imwrite(str(target), image)
        report.setdefault('official', []).append(str(target.relative_to(ROOT)))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
