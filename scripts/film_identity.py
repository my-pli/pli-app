"""하연's identity check for the product film: does a face in a picture or a video match her real photos?

The reference is all four photos the user shared (.tools/private-family/hayoung-drive, IMG_0606~0609),
not a single crop. A face counts as 하연 when its SFace cosine similarity to the photos is high:
`best` = the highest similarity to any one photo, `mean` = the mean over the four. The film gate
(docs/AUDIT-2026-11-14-FILM-VOICE.md 6.2) asks for best >= 0.5 on each generated scene.
The models are OpenCV's YuNet detector and SFace recognizer (.tools/edge-ai/models/face).

usage: .tools/edge-venv/bin/python scripts/film_identity.py IMAGE_OR_VIDEO [...]
"""
from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / '.tools/edge-ai/models/face'
DRIVE = ROOT / '.tools/private-family/hayoung-drive'
SAME_PERSON = 0.363  # SFace's published same-identity threshold
GATE = 0.5           # the film's stricter bar for "looks like 하연"


@lru_cache(maxsize=1)
def models() -> tuple:
    det = cv2.FaceDetectorYN.create(str(MODELS / 'face_detection_yunet_2023mar.onnx'), '', (320, 320), 0.6, 0.3, 5000)
    rec = cv2.FaceRecognizerSF.create(str(MODELS / 'face_recognition_sface_2021dec.onnx'), '')
    return det, rec


def faces(image: np.ndarray) -> list:
    """[{box, area, score, embedding}] for every face, largest first."""
    det, rec = models()
    h, w = image.shape[:2]
    scale = min(1.0, 1600 / max(h, w))
    small = cv2.resize(image, (int(w * scale), int(h * scale))) if scale < 1 else image
    det.setInputSize((small.shape[1], small.shape[0]))
    _ok, found = det.detect(small)
    out = []
    for row in found if found is not None else []:
        emb = rec.feature(rec.alignCrop(small, row)).flatten()
        out.append({'box': [int(v / scale) for v in row[:4]], 'area': float(row[2] * row[3]) / (small.shape[0] * small.shape[1]),
                    'score': float(row[-1]), 'embedding': emb / np.linalg.norm(emb)})
    return sorted(out, key=lambda f: -f['area'])


@lru_cache(maxsize=1)
def drive_faces() -> dict:
    found = {p.name: faces(cv2.imread(str(p))) for p in sorted(DRIVE.glob('*.JPG'))}
    if len(found) != 4 or not all(found.values()):
        raise SystemExit(f'expected 4 photos with faces in {DRIVE}')
    return found


@lru_cache(maxsize=1)
def child_faces() -> dict:
    """In each photo, the face that agrees most with the other photos (another child may be in the frame)."""
    found = drive_faces()
    pick = {name: fs[0] for name, fs in found.items()}
    for _ in range(2):
        pick = {name: max(fs, key=lambda f: sum(float(f['embedding'] @ p['embedding']) for n, p in pick.items() if n != name))
                for name, fs in found.items()}
    return pick


def references() -> dict:
    return {name: face['embedding'] for name, face in child_faces().items()}


def similarity(embedding: np.ndarray) -> dict:
    sims = [float(embedding @ ref) for ref in references().values()]
    return {'best': round(max(sims), 3), 'mean': round(float(np.mean(sims)), 3)}


def check_image(image: np.ndarray, min_area: float = 0.0005) -> dict | None:
    """The face most like 하연 in a picture (None when there is no face)."""
    scored = [{**similarity(f['embedding']), 'box': f['box'], 'area': round(f['area'], 4)} for f in faces(image) if f['area'] >= min_area]
    return max(scored, key=lambda s: s['best']) if scored else None


def frames(video: Path, every: float = 0.5, start: float = 0.0, end: float | None = None) -> list:
    """(time, BGR frame) every `every` seconds between start and end (default: the whole video)."""
    duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video)]))
    stop = min(duration - 0.1, end if end is not None else duration)
    out, t = [], max(0.1, start)
    while t < stop:
        raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(video), '-frames:v', '1',
                                       '-f', 'image2pipe', '-vcodec', 'png', '-'])
        if raw:
            out.append((round(t, 2), cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)))
        t += every
    return out


def check_video(video: Path, every: float = 0.5, start: float = 0.0, end: float | None = None) -> dict:
    """Per-frame best match; `passRate` = share of sampled frames with a face at or above the gate."""
    rows = [{'t': t, **(check_image(f) or {})} for t, f in frames(video, every, start, end)]
    with_face = [r for r in rows if 'best' in r]
    bests = [r['best'] for r in with_face]
    passing = sum(b >= GATE for b in bests)
    return {'video': str(video), 'frames': len(rows), 'withFace': len(with_face), 'passing': passing,
            'passRate': round(passing / len(rows), 3) if rows else 0.0,
            'median': round(float(np.median(bests)), 3) if bests else None, 'min': min(bests, default=None), 'rows': rows}


def main() -> int:
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.suffix.lower() in ('.mp4', '.mov', '.webm'):
            report = check_video(path)
            report.pop('rows')
        else:
            report = {'image': str(path), **(check_image(cv2.imread(str(path))) or {'best': None})}
        print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
