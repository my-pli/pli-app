#!/usr/bin/env python3
"""Find the child in family photos and prepare privacy-safe album assets for the edge server.

Faces are detected with OpenCV YuNet and identified with SFace. The child is the identity
that appears in the most photos (or matches --reference). Every other face is blurred.
Outputs carry no EXIF and stay under .tools (never inside the APK or the source snapshot).
"""
import argparse, hashlib, json, sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / '.tools/edge-ai/models/face'
DETECTOR = MODELS / 'face_detection_yunet_2023mar.onnx'
RECOGNIZER = MODELS / 'face_recognition_sface_2021dec.onnx'
SAME_PERSON = 0.363          # SFace cosine threshold published with the model
CLASS_PHOTO_MATCH = 0.72  # class photos: below this other children were matched (checked by eye, 2026-11-13)
MIN_SCORE = 0.62
MAX_SIDE = 1600
AVATAR = 512


def load(path):
    image = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def faces(image, detector, recognizer):
    """Detect at two scales so small background faces are blurred as well."""
    found = []
    for scale in (1.0, 2.0):
        view = image if scale == 1.0 else cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        detector.setInputSize((view.shape[1], view.shape[0]))
        _, rows = detector.detect(view)
        for row in rows if rows is not None else []:
            row = row.copy(); row[:14] /= scale
            if row[14] < MIN_SCORE:
                continue
            x, y, w, h = row[:4]
            if any(_iou((x, y, w, h), f['box']) > .4 for f in found):
                continue
            aligned = recognizer.alignCrop(image, row)
            found.append({'box': (float(x), float(y), float(w), float(h)), 'score': float(row[14]),
                          'feature': recognizer.feature(aligned).flatten()})
    return found


def _iou(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx)); iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / max(1e-6, aw * ah + bw * bh - inter)


def similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def choose_child(records, reference=None):
    """Return the feature centroid of the identity seen in the most photos."""
    candidates = [f for r in records for f in r['faces']]
    if not candidates:
        raise SystemExit('NO_FACE_FOUND')
    if reference is not None:
        seed = reference
    else:
        def support(face):
            return sum(any(similarity(face['feature'], g['feature']) >= SAME_PERSON for g in r['faces']) for r in records)
        seed = max(candidates, key=lambda f: (support(f), f['box'][2] * f['box'][3]))['feature']
    members = [f['feature'] for f in candidates if similarity(f['feature'], seed) >= SAME_PERSON]
    centroid = np.mean(members, axis=0)
    return centroid / np.linalg.norm(centroid)


def blur_face(image, box):
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.ellipse(mask, (int(cx), int(cy)), (int(w * .85), int(h * 1.05)), 0, 0, 360, 255, -1)
    k = max(31, int(max(w, h) * .6) | 1)
    blurred = cv2.GaussianBlur(image, (k, k), 0)
    soft = cv2.GaussianBlur(mask, (31, 31), 0).astype(np.float32)[..., None] / 255
    return (image * (1 - soft) + blurred * soft).astype(np.uint8)


def avatar(image, box):
    x, y, w, h = box
    side = max(w, h) * 2.1
    cx, cy = x + w / 2, y + h / 2 + h * .08
    left = int(max(0, cx - side / 2)); top = int(max(0, cy - side / 2))
    right = int(min(image.shape[1], cx + side / 2)); bottom = int(min(image.shape[0], cy + side / 2))
    return cv2.resize(image[top:bottom, left:right], (AVATAR, AVATAR), interpolation=cv2.INTER_AREA)


VISION = ROOT / '.tools/edge-ai/models/Qwen3.5-4B-GGUF'
MTMD = ROOT / '.tools/edge-ai/bin/llama-b12314/llama-mtmd-cli'


def describe(path: Path) -> str:
    """One Korean sentence about the (already face-blurred) photo, from the local vision model."""
    import re
    import subprocess
    prompt = '사진 속 아이가 무엇을 하고 있는지 한국어 한 문장(40자 이내)으로 설명해. 사람 이름과 기관 이름은 쓰지 마.'
    out = subprocess.run([str(MTMD), '-m', str(VISION / 'Qwen3.5-4B-Q4_K_M.gguf'), '--mmproj', str(VISION / 'mmproj-F16.gguf'),
                          '--image', str(path), '-p', prompt, '-n', '120', '--temp', '0.2', '-t', '12', '--image-max-tokens', '256'],
                         capture_output=True, text=True, timeout=600).stdout
    text = re.sub(r'<think>.*?</think>', '', out, flags=re.S).strip().splitlines()
    text = next((line.strip() for line in reversed(text) if re.search(r'[가-힣]', line)), '')
    first = re.split(r'(?<=[.!?다요])\s', text)[0]
    return re.sub(r'^사진 속\s*', '', first).strip()[:80]


def save_jpeg(image, path, quality=88):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(path, 'JPEG', quality=quality, optimize=True, progressive=True)  # no EXIF


def process(record, child):
    image = record['image']
    scored = sorted(((similarity(f['feature'], child), f) for f in record['faces']), key=lambda t: -t[0])
    threshold = CLASS_PHOTO_MATCH if record['origin'].get('kind') == 'kidsnote' else SAME_PERSON
    target = scored[0][1] if scored and scored[0][0] >= threshold else None
    others = [f for _, f in scored if f is not target]
    for face in others:
        image = blur_face(image, face['box'])
    return image, target, (scored[0][0] if target is not None else None), len(others)


PHOTO_TYPES = {'.jpg', '.jpeg', '.png', '.webp'}


def kidsnote_sources(folder: Path) -> list:
    """(photo path, origin) for every synced KidsNote album photo, newest album first."""
    albums = json.loads((folder / 'albums.json').read_text())
    return [(folder / album['id'] / name, {'kind': 'kidsnote', 'album': album['id'], 'date': album['date'], 'title': album['title']})
            for album in sorted(albums, key=lambda a: a['date'], reverse=True) for name in album['photos']
            if (folder / album['id'] / name).suffix.lower() in PHOTO_TYPES]


def read_record(path: Path, origin: dict, detector, recognizer) -> dict:
    image = load(path)
    scale = min(1.0, MAX_SIDE / max(image.shape[:2]))
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return {'path': path, 'origin': origin, 'image': image, 'faces': faces(image, detector, recognizer)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / '.tools/private-family/hayoung-drive')
    parser.add_argument('--kidsnote', type=Path, help='albums synced by scripts/kidsnote-album-sync.mjs (albums.json + one folder per album)')
    parser.add_argument('--output', type=Path, default=ROOT / '.tools/edge-ai/family-album')
    parser.add_argument('--child', default='하연')
    parser.add_argument('--alias', action='append', default=[], help='other spellings of the name in source titles (KidsNote registration), shown as --child')
    parser.add_argument('--reference', type=Path, help='photo whose largest face is the child (inside or outside the inputs)')
    parser.add_argument('--only-child', action='store_true', help='keep only photos where the child was found (class photos)')
    parser.add_argument('--describe', action='store_true', help='add a scene sentence per photo with the local vision model')
    args = parser.parse_args()
    detector = cv2.FaceDetectorYN.create(str(DETECTOR), '', (320, 320), MIN_SCORE, .3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER), '')
    sources = kidsnote_sources(args.kidsnote) if args.kidsnote else []  # newest album first
    sources += [(p, {'kind': 'family'}) for p in sorted(args.input.iterdir()) if p.suffix.lower() in PHOTO_TYPES]
    records = [read_record(path, origin, detector, recognizer) for path, origin in sources]
    reference = None
    if args.reference:
        ref = next((r for r in records if r['path'] == args.reference), None) or read_record(args.reference, {}, detector, recognizer)
        if not ref['faces']:
            raise SystemExit('NO_FACE_IN_REFERENCE')
        reference = max(ref['faces'], key=lambda f: f['box'][2] * f['box'][3])['feature']
    child = choose_child(records, reference)
    args.output.mkdir(parents=True, exist_ok=True)
    photos, best = [], None
    for record in records:
        image, target, score, blurred = process(record, child)
        if args.only_child and target is None and record['origin'].get('kind') == 'kidsnote':
            continue  # a class photo without the child: other children are never kept
        digest = hashlib.sha256(cv2.imencode('.png', image)[1].tobytes()).hexdigest()[:16]
        name = f'{digest}.jpg'
        save_jpeg(image, args.output / name)
        h, w = image.shape[:2]
        entry = {'id': digest, 'file': name, 'width': w, 'height': h, 'source': record['path'].name, 'origin': record['origin'],
                 'child': target is not None, 'blurredFaces': blurred, 'focus': [.5, .45]}
        if target is not None:
            x, y, fw, fh = target['box']
            entry.update({'similarity': round(score, 3),
                          'faceBox': [round(x / w, 4), round(y / h, 4), round(fw / w, 4), round(fh / h, 4)],
                          'focus': [round((x + fw / 2) / w, 4), round((y + fh / 2) / h, 4)]})
            quality = fw * fh * target['score']
            if best is None or quality > best[0]:
                best = (quality, image, target['box'])
        photos.append(entry)
    if best is None:
        raise SystemExit('CHILD_NOT_FOUND')
    save_jpeg(avatar(best[1], best[2]), args.output / 'avatar.jpg', 90)
    previous = {}
    try:
        previous = {p['id']: p.get('scene') for p in json.loads((args.output / 'album.json').read_text())['photos']}
    except (OSError, ValueError, KeyError):
        pass
    for entry in photos:
        entry['scene'] = previous.get(entry['id']) or (describe(args.output / entry['file']) if args.describe else None)
    manifest = {'child': args.child, 'aliases': args.alias, 'avatar': 'avatar.jpg', 'photos': photos,
                'method': 'OpenCV YuNet 2023mar detection + SFace 2021dec identity (cosine >= 0.363); other faces blurred; EXIF removed'}
    (args.output / 'album.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    keep = {p['file'] for p in photos} | {'avatar.jpg'}
    for stale in args.output.glob('*.jpg'):
        if stale.name not in keep:
            stale.unlink()
    print(json.dumps({'photos': len(photos), 'withChild': sum(p['child'] for p in photos),
                      'blurred': sum(p['blurredFaces'] for p in photos),
                      'similarity': [p.get('similarity') for p in photos],
                      'faces': [len(r['faces']) for r in records]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
