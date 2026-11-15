#!/usr/bin/env python3
"""Fixes drawn defects that sit in the still background of a generated scene, by covering just that area in every frame
(v10, 2026-11-15: "뒷배경 같은게 이상하잖아, 이상한게 생성되어있고"). The camera of these scenes does not move, so a
background area can be replaced by a clean picture of the same place without touching the people:

  plate   the area from clean frames of the same clip (median over a time span), or from an edited still of it
  dim     the area blurred and darkened, as a switched-off screen (a dashboard display full of fake writing)

With "people": true, pixels where a person is (torchvision Mask R-CNN, per frame, slightly grown) keep the original,
so a child moving her head in front of the patched seat stays as she was. Edges are feathered.

Spec (JSON): {"source": "<clip>.mp4", "output": "<clip>.mp4", "patches": [
   {"box": [x0, y0, x1, y1], "kind": "plate", "from": [t0, t1] | "image": "<png>", "people": false, "feather": 12, "why": "..."},
   {"box": [...], "kind": "dim", "level": 0.22, "blur": 9, "why": "..."}]}
usage: .tools/qwen-tts-venv/bin/python scripts/film_scene_patch.py SPEC.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def probe(path: Path) -> tuple:
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                               'stream=width,height,r_frame_rate', '-of', 'json', str(path)]))['streams'][0]
    num, den = info['r_frame_rate'].split('/')
    return int(info['width']), int(info['height']), info['r_frame_rate'], float(num) / float(den)


def read(path: Path) -> np.ndarray:
    w, h, _, _ = probe(path)
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'])
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).copy()


def soft_box(h: int, w: int, box: list, feather: int) -> np.ndarray:
    m = np.zeros((h, w), np.float32)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = 1.0
    if feather:
        m = cv2.GaussianBlur(m, (0, 0), feather)
        m[y0 + feather:y1 - feather, x0 + feather:x1 - feather] = 1.0
    return m


def people(frames: np.ndarray, grow: int = 9) -> np.ndarray:
    import torch
    from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights, maskrcnn_resnet50_fpn_v2
    model = maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT).eval().cuda()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))
    out = []
    with torch.no_grad():
        for f in frames:
            small = cv2.resize(f, (f.shape[1] // 2, f.shape[0] // 2), interpolation=cv2.INTER_AREA)
            x = torch.from_numpy(small[..., ::-1].copy()).permute(2, 0, 1).float().div(255).cuda()
            r = model([x])[0]
            keep = (r['labels'] == 1) & (r['scores'] > 0.5)
            m = (r['masks'][keep, 0] > 0.5).any(dim=0).float().cpu().numpy() if keep.any() else np.zeros(small.shape[:2], np.float32)
            m = cv2.resize(m, (f.shape[1], f.shape[0]), interpolation=cv2.INTER_LINEAR)
            out.append(cv2.GaussianBlur(cv2.dilate(m, kernel), (0, 0), 3))
    del model
    torch.cuda.empty_cache()
    return np.clip(np.array(out), 0, 1)


def mattes(frames: np.ndarray) -> np.ndarray:
    """The people as a soft matte (BiRefNet-portrait, MIT): unlike Mask R-CNN's coarse mask it follows single strands of
    hair, so an object drawn right behind a child's bob is covered without leaving a strip of it along her hair."""
    import torch
    from transformers import AutoModelForImageSegmentation
    model = AutoModelForImageSegmentation.from_pretrained('ZhengPeng7/BiRefNet-portrait', trust_remote_code=True).eval().cuda().half()
    mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
    out = []
    with torch.no_grad():
        for f in frames:
            x = (cv2.resize(f[..., ::-1], (1024, 1024), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 - mean) / std
            a = model(torch.from_numpy(x).permute(2, 0, 1)[None].cuda().half())[-1].sigmoid()[0, 0].float().cpu().numpy()
            out.append(cv2.resize(a, (f.shape[1], f.shape[0]), interpolation=cv2.INTER_LINEAR))
    del model
    torch.cuda.empty_cache()
    return np.clip(np.array(out), 0, 1)


def main() -> int:
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text())
    source, output = ROOT / spec['source'], ROOT / spec['output']
    w, h, rate, fps = probe(source)
    frames = read(source).astype(np.float32)
    grow = min([p.get('grow', 9) for p in spec['patches'] if p.get('people')] or [9])
    wants = {p.get('people') for p in spec['patches']}
    person = (mattes(frames.astype(np.uint8)) if 'matte' in wants else
              people(frames.astype(np.uint8), grow) if True in wants else None)
    for p in spec['patches']:
        weight = soft_box(h, w, p['box'], p.get('feather', 12))
        if p['kind'] == 'plate':
            if 'image' in p:
                plate = cv2.resize(cv2.imread(str(ROOT / p['image'])), (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
            else:
                a, b = (round(t * fps) for t in p['from'])
                plate = np.median(frames[a:max(a + 1, b)], axis=0)
            if p.get('matchFrom'):
                # The drawn object is fixed to the still background, so it looks the same in every frame it is not hidden
                # in: its own picture is the median over a span where it is shown. A pixel is covered only while it still
                # matches that picture; hair or a face in front of it differs and stays (2026-11-15, the whine cushion).
                a, b = (round(t * fps) for t in p['matchFrom'])
                shown = np.median(frames[a:max(a + 1, b)], axis=0)
                near, far = p.get('threshold', [22, 48])
                for i in range(len(frames)):
                    distance = np.sqrt(((frames[i] - shown) ** 2).sum(axis=2))
                    match = np.clip((far - distance) / (far - near), 0, 1).astype(np.float32)
                    match = cv2.GaussianBlur(cv2.morphologyEx(match, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), (0, 0), 1.2)
                    k = weight * match
                    frames[i] = frames[i] * (1 - k[..., None]) + plate * k[..., None]
                continue
            for i in range(len(frames)):
                keep = person[i] if p.get('people') else 0.0
                if p.get('protect') == 'hair-skin' and p.get('people'):
                    # Mask R-CNN's edge also takes in a strip of the drawn object next to the hair (2026-11-15: the cushion's
                    # letters along the girl's bob). Near the person, keep only what looks like her: dark, not-blue hair and
                    # skin tones; the rest of the box, the object's strip included, takes the plate.
                    hsv = cv2.cvtColor(frames[i].astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.int16)
                    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
                    blue = (hue >= 95) & (hue <= 135) & (sat >= 60)
                    hair = (val < 95) & ~blue
                    skin = (hue <= 25) & (sat >= 35) & (sat <= 185) & (val >= 105)
                    looks = ((hair | skin).astype(np.uint8) * 255)
                    looks = cv2.morphologyEx(looks, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
                    looks = cv2.morphologyEx(looks, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
                    keep = keep * cv2.GaussianBlur(looks.astype(np.float32) / 255, (0, 0), 1.5)
                k = weight * (1 - keep)
                frames[i] = frames[i] * (1 - k[..., None]) + plate * k[..., None]
        elif p['kind'] == 'dim':
            for i in range(len(frames)):
                dark = cv2.GaussianBlur(frames[i], (0, 0), p.get('blur', 9)) * p.get('level', 0.22)
                frames[i] = frames[i] * (1 - weight[..., None]) + dark * weight[..., None]
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}',
                               '-framerate', rate, '-i', '-', '-i', str(source), '-map', '0:v', '-map', '1:a?', '-c:v', 'libx264',
                               '-crf', '14', '-pix_fmt', 'yuv420p', '-c:a', 'copy', str(output)], stdin=subprocess.PIPE)
    writer.stdin.write(np.clip(frames, 0, 255).astype(np.uint8).tobytes())
    writer.stdin.close()
    writer.wait()
    print(json.dumps({'output': spec['output'], 'frames': len(frames), 'patches': len(spec['patches'])}), flush=True)
    return writer.returncode


if __name__ == '__main__':
    raise SystemExit(main())
