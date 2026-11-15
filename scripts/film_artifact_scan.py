#!/usr/bin/env python3
"""Find what a video model drew wrong in a generated family scene, before it goes into the film
(2026-11-15, user: "뒷배경 같은게 이상하잖아, 이상한게 생성되어있고 … 잡아내봐").

Three detectors, each aimed at a defect v9 shipped with:
  text    a text detector (PP-OCRv3 DB) over the whole frame, every 0.25 s: fake writing on a dashboard screen, a seat
          badge, a sweatshirt print, burned-in captions
  popin   things that appear in the still background and stay (camera is fixed): the model's background is compared with
          its own first half second, outside the people (torchvision Mask R-CNN), only where it had been still; a white
          blob appearing in the window, a logo growing on a car seat
  vlm     a vision-language model (Qwen3-VL-235B on Hugging Face's inference router, PRO account) shown six frames in order
          and asked as a film QC reviewer for garbled text, malformed or impossible objects, wrong hands, car geometry that
          cannot exist (Korea drives on the right: the driver sits on the left), and objects that change between frames

Writes <out>/<clip>-artifacts.json and <out>/<clip>-artifacts.png (frames with every finding boxed and numbered).
Exit code 1 when a clip has a finding at or above --fail (default: high).
usage: .tools/qwen-tts-venv/bin/python scripts/film_artifact_scan.py CLIP.mp4 [...] --out DIR [--context TEXT] [--no-vlm]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import urllib.request
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / '.tools/edge-ai/models/text/ppocr_cn.onnx'  # OpenCV zoo PP-OCRv3 (DB), as scripts/film_caption_mask.py
# The reviewer: Qwen3-VL-235B on Hugging Face's router, or (PLI_VLM_URL) any OpenAI-compatible server, e.g. the edge's own
# llama.cpp with Qwen3.5-4B + its vision projector when the router's prepaid credits run out (2026-11-15: HTTP 402)
ROUTER = os.environ.get('PLI_VLM_URL', 'https://router.huggingface.co/v1/chat/completions')
VLM = os.environ.get('PLI_VLM_MODEL', 'Qwen/Qwen3-VL-235B-A22B-Instruct')
VLM_SIDE = int(os.environ.get('PLI_VLM_SIDE', '1600'))      # long side of each frame sent; 1024 for the CPU-only local server
VLM_FRAMES = int(os.environ.get('PLI_VLM_FRAMES', '4'))
SCAN_FPS = 8                 # frames per second for the background comparison
REFERENCE_SECONDS = 0.5      # the background as the scene opens
STILL_STD = 7.0              # gray-level std over the first second: the parts of the frame that were still
CHANGE = 28                  # gray levels away from the opening background
MIN_AREA = 0.0012            # of the frame, for a soft change
SMALL_AREA = 0.0002          # of the frame, for a sharp one (v9: a 0.08% white dot in the night window, 200 levels brighter)
SHARP = 90                   # gray levels: a change this strong counts from SMALL_AREA
MIN_RUN = 3                  # samples in a row (0.375 s)
PERSON_GROW = 0.035          # of the frame width around each person
SEVERITY = {'low': 0, 'medium': 1, 'high': 2}
CHECKLIST = (  # yes/no questions per frame: the open "list every defect" request returned nothing on v9's known defects
    ('writing', 'text', 'Is there any writing, letters, numbers or a logo anywhere in the picture (on clothes, seats, screens, '
     'signs, objects)? Ignore only the brand emblem on the front of a car.'),
    ('screen', 'object', 'Does any small object a person holds or wears have a screen, display or glowing light? (A Hyundai car '
     'key fob is plain black with buttons and no screen.)'),
    ('blob', 'smear', 'Is there a bright dot, blob, glow or smear that is not a real lamp, streetlight or reflection?'),
    ('geometry', 'geometry', 'Is anything about the car physically impossible: seats, steering wheel, doors, windows or '
     'console in impossible places? (Korea is left-hand drive: the driver sits on the car\'s left; a camera on the dashboard '
     'looking back sees the driver on the right of the picture.)'),
    ('anatomy', 'anatomy', 'Is any hand, finger, arm or face malformed, merged or missing?'),
    ('object', 'object', 'Is any object malformed, melted, floating, duplicated or out of place?'),
)
CHECK_PROMPT = (
    'You check one frame of an AI-generated live-action video for defects a viewer could notice. {context}\n'
    'Answer each question about THIS picture, looking closely at small details. For every "yes", give where it is as a box '
    '[x0, y0, x1, y1] on a 0-1000 scale and say in a few words what it is. Do not count normal film look (depth of field, '
    'motion blur of passing lights, night colour).\n{questions}\n'
    'Answer with JSON only: {{"answers": {{"<key>": {{"yes": true|false, "what": "...", "box": [x0, y0, x1, y1]}}}}}}')


def probe(path: Path) -> tuple:
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height:format=duration', '-of', 'json', str(path)])
    info = json.loads(out)
    return int(info['streams'][0]['width']), int(info['streams'][0]['height']), float(info['format']['duration'])


def frames(path: Path, fps: float, width: int) -> tuple:
    w, h, _ = probe(path)
    height = round(h * width / w / 2) * 2
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-vf', f'fps={fps},scale={width}:{height}',
                                   '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'])
    return np.frombuffer(raw, np.uint8).reshape(-1, height, width, 3), w, h


def text_findings(path: Path) -> list:
    video, w, h = frames(path, 4, 736)
    scale = w / video.shape[2]
    model = cv2.dnn_TextDetectionModel_DB(str(DETECTOR))
    model.setBinaryThreshold(0.3).setPolygonThreshold(0.6).setMaxCandidates(200).setUnclipRatio(1.6)
    model.setInputParams(1.0 / 255.0, (736, 736), (122.67891434, 116.66876762, 104.00698793))
    hits = []
    for index, frame in enumerate(video):
        boxes, scores = model.detect(np.ascontiguousarray(frame))
        for quad, score in zip(boxes, scores):
            quad = np.array(quad)
            x0, y0 = quad.min(axis=0)
            x1, y1 = quad.max(axis=0)
            if (x1 - x0) * scale >= 18 and (y1 - y0) * scale >= 8:
                hits.append((index / 4, [x0 * scale, y0 * scale, x1 * scale, y1 * scale], float(score)))
    findings = []  # one finding per place: boxes that overlap across frames are the same writing
    for t, box, score in hits:
        for f in findings:
            b = f['box']
            if box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1]:
                f['times'].append(round(t, 2))
                f['box'] = [min(b[0], box[0]), min(b[1], box[1]), max(b[2], box[2]), max(b[3], box[3])]
                break
        else:
            findings.append({'detector': 'text', 'kind': 'text', 'box': box, 'times': [round(t, 2)], 'score': round(score, 2)})
    for f in findings:
        f['box'] = [round(v) for v in f['box']]
        f['what'] = f"writing-like marks in {len(f['times'])} of {len(video)} sampled frames"
        f['severity'] = 'high' if len(f['times']) >= 2 else 'medium'
    return findings


def person_masks(video: np.ndarray) -> np.ndarray:
    import torch
    from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights, maskrcnn_resnet50_fpn_v2
    model = maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT).eval().cuda()
    grow = max(3, round(video.shape[2] * PERSON_GROW))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))
    masks = []
    with torch.no_grad():
        for frame in video:
            x = torch.from_numpy(frame[..., ::-1].copy()).permute(2, 0, 1).float().div(255).cuda()
            out = model([x])[0]
            keep = (out['labels'] == 1) & (out['scores'] > 0.5)
            m = (out['masks'][keep, 0] > 0.5).any(dim=0).cpu().numpy() if keep.any() else np.zeros(frame.shape[:2], bool)
            masks.append(cv2.dilate(m.astype(np.uint8), kernel) > 0)
    del model
    torch.cuda.empty_cache()
    return np.array(masks)


def popin_findings(path: Path) -> list:
    video, w, h = frames(path, SCAN_FPS, 480)
    scale = w / video.shape[2]
    gray = np.array([cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (5, 5), 0) for f in video]).astype(np.float32)
    people = person_masks(video)
    near = np.array([people[max(0, i - 2):i + 3].any(axis=0) for i in range(len(people))])  # where people are, ±0.25 s
    n_ref = max(2, round(REFERENCE_SECONDS * SCAN_FPS))
    reference = np.median(gray[:n_ref], axis=0)
    still = gray[:max(n_ref, SCAN_FPS)].std(axis=0) < STILL_STD
    still &= ~near[:max(n_ref, SCAN_FPS)].any(axis=0)
    area_min = MIN_AREA * gray.shape[1] * gray.shape[2]
    changed, strength = [], []
    for i in range(len(gray)):
        diff = np.abs(gray[i] - reference)
        diff -= np.median(diff[still]) if still.any() else 0  # the whole frame brightening is light, not a new object
        changed.append((diff > CHANGE) & still & ~near[i])
        strength.append(np.where(changed[-1], diff, 0))
    changed = np.array(changed)
    runs = np.zeros(changed.shape, np.int32)  # samples in a row each pixel has stayed changed
    for i in range(len(changed)):
        runs[i] = np.where(changed[i], (runs[i - 1] + 1) if i else 1, 0)
    findings = []
    for i in range(len(changed)):
        mask = ((runs[i] == MIN_RUN) * 255).astype(np.uint8)  # the moment a change has lasted MIN_RUN samples
        count, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
        for c in range(1, count):
            x, y, bw, bh, area = stats[c]
            peak = float(strength[i][labels == c].max())
            if area < (SMALL_AREA * gray.shape[1] * gray.shape[2] if peak >= SHARP else area_min):
                continue
            box = [x * scale, y * scale, (x + bw) * scale, (y + bh) * scale]
            if any(f['box'][0] < box[2] and f['box'][2] > box[0] and f['box'][1] < box[3] and f['box'][3] > box[1] for f in findings):
                continue
            t = (i - MIN_RUN + 1) / SCAN_FPS
            findings.append({'detector': 'popin', 'kind': 'popin', 'box': [round(v) for v in box], 'times': [round(t, 2)],
                             'what': f'something appears in the still background at {t:.2f}s and stays',
                             'areaShare': round(float(area / (gray.shape[1] * gray.shape[2])), 4), 'peak': round(peak),
                             'severity': 'high' if area >= 4 * area_min or peak >= SHARP else 'medium'})
    return findings


def jpeg(frame: np.ndarray, long_side: int = 1600) -> str:
    h, w = frame.shape[:2]
    s = long_side / max(h, w)
    ok, buf = cv2.imencode('.jpg', cv2.resize(frame, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return base64.b64encode(buf.tobytes()).decode()


def ask(frame: np.ndarray, prompt: str) -> dict:
    content = [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + jpeg(frame, VLM_SIDE)}}]
    body = json.dumps({'model': VLM, 'messages': [{'role': 'user', 'content': content}], 'max_tokens': 1200, 'temperature': 0.0}).encode()
    headers = {'Content-Type': 'application/json'}
    if 'huggingface' in ROUTER:
        headers['Authorization'] = 'Bearer ' + (Path.home() / '.cache/huggingface/token').read_text().strip()
    request = urllib.request.Request(ROUTER, body, headers)
    reply = json.loads(urllib.request.urlopen(request, timeout=600).read())['choices'][0]['message']['content']
    return json.loads(reply[reply.find('{'):reply.rfind('}') + 1])


def vlm_findings(path: Path, context: str, count: int = VLM_FRAMES) -> tuple:
    w, h, seconds = probe(path)
    times = [round(seconds * (i + 0.5) / count, 2) for i in range(count)]
    questions = '\n'.join(f'- {key}: {question}' for key, _kind, question in CHECKLIST)
    findings = []
    for t in times:
        raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.3f}', '-i', str(path), '-frames:v', '1',
                                       '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'])
        answers = ask(np.frombuffer(raw, np.uint8).reshape(h, w, 3), CHECK_PROMPT.format(context=context, questions=questions))
        for key, kind, _question in CHECKLIST:
            a = answers.get('answers', {}).get(key) or {}
            if not a.get('yes'):
                continue
            box = a.get('box') if isinstance(a.get('box'), list) and len(a.get('box')) == 4 else [0, 0, 1000, 1000]
            box = [round(box[0] * w / 1000), round(box[1] * h / 1000), round(box[2] * w / 1000), round(box[3] * h / 1000)]
            same = next((f for f in findings if f['check'] == key and f['box'][0] < box[2] and f['box'][2] > box[0]
                         and f['box'][1] < box[3] and f['box'][3] > box[1]), None)
            if same:
                same['times'].append(t)
                continue
            findings.append({'detector': 'vlm', 'check': key, 'kind': kind, 'what': str(a.get('what', ''))[:200], 'times': [t], 'box': box})
    for f in findings:  # seen in more than one frame: a viewer will see it
        f['severity'] = 'high' if len(f['times']) >= 2 or f['check'] in ('writing', 'screen', 'geometry') else 'medium'
    return findings, times


def sheet(path: Path, findings: list, target: Path) -> None:
    """Every finding boxed and numbered on the frame where it was seen first."""
    w, h, seconds = probe(path)
    times = sorted({f['times'][0] for f in findings}) or [seconds / 2]
    tiles = []
    for t in times[:8]:
        raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{min(t, seconds - 0.05):.3f}', '-i', str(path),
                                       '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'])
        img = np.frombuffer(raw, np.uint8).reshape(h, w, 3).copy()
        for n, f in enumerate(findings):
            if f['times'][0] != t:
                continue
            colour = {'text': (60, 200, 255), 'popin': (80, 80, 255), 'vlm': (255, 160, 60)}[f['detector']]
            x0, y0, x1, y1 = f['box']
            cv2.rectangle(img, (x0, y0), (x1, y1), colour, max(2, w // 300))
            cv2.putText(img, str(n), (x0 + 4, max(24, y0 - 8)), cv2.FONT_HERSHEY_SIMPLEX, w / 900, colour, max(2, w // 400))
        cv2.putText(img, f'{t:.2f}s', (12, 40), cv2.FONT_HERSHEY_SIMPLEX, w / 900, (255, 255, 255), max(2, w // 400))
        s = 540 / max(h, w) * (1 if h > w else 1.4)
        tiles.append(cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA))
    cv2.imwrite(str(target), np.hstack(tiles) if len(tiles) > 1 else tiles[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('clips', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--context', default='A Korean mother and her young daughter, at dusk or night, in or beside a car.')
    parser.add_argument('--no-vlm', action='store_true')
    parser.add_argument('--fail', default='high', choices=list(SEVERITY))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    worst = -1
    for clip in args.clips:
        findings = text_findings(clip) + popin_findings(clip)
        vlm_times = None
        if not args.no_vlm:
            try:
                extra, vlm_times = vlm_findings(clip, args.context)
                findings += extra
            except Exception as error:  # the reviewer is a remote service: say so, never pass silently
                findings.append({'detector': 'vlm', 'kind': 'other', 'what': f'VLM review failed: {type(error).__name__}: {error}'[:300],
                                 'severity': 'high', 'times': [0.0], 'box': [0, 0, 1, 1]})
        report = {'clip': str(clip), 'vlm': None if args.no_vlm else VLM, 'vlmFrames': vlm_times, 'findings': findings,
                  'counts': {k: sum(1 for f in findings if f['severity'] == k) for k in SEVERITY}}
        stem = clip.stem
        (args.out / f'{stem}-artifacts.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
        sheet(clip, findings, args.out / f'{stem}-artifacts.png')
        worst = max([worst] + [SEVERITY[f['severity']] for f in findings])
        print(json.dumps({'clip': stem, **report['counts'],
                          'findings': [f"{n}:{f['detector']}:{f['severity']}:{f['what'][:90]}" for n, f in enumerate(findings)]},
                         ensure_ascii=False), flush=True)
    return 1 if worst >= SEVERITY[args.fail] else 0


if __name__ == '__main__':
    raise SystemExit(main())
