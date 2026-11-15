#!/usr/bin/env python3
"""First frames for the v10 family scenes, in both shapes (9:16 short and 16:9 landscape), cleaned of what the
video model had drawn wrong in v9 (2026-11-15, user: "뒷배경 같은게 이상하잖아, 이상한게 생성되어있고").

v9 frame review found the wrong things started in the first frames or grew out of them:
  - the driver's front view had a glowing dashboard screen full of fake writing at its left edge
  - in the car park the key the mother holds up turned into a phone-like device with a blue screen
  - the girl's sweatshirt print carried made-up letters
Each frame here is made by Qwen-Image-Edit-2511 (Hugging Face Space, PRO account) from the frame the user already saw,
with the family's reference photos, and asked to keep the people exactly and change only the listed things.
The landscape frames of the two outdoor/side scenes are the original 16:9 Seedance frames (the 9:16 ones were crops).

Writes .tools/product-film/v10/frames/<name>.png with <name>.json (inputs' hashes, prompt, seed, Space).
usage: .tools/film-venv/bin/python scripts/make-scene-frames.py [--only name,name] [--seed N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / '.tools/product-film'
INPUTS = FILM / 'vertical/inputs'
REFS = FILM / 'weave-refs'
FAMILY = ROOT / '.tools/private-family/weave-refs'
OUT = FILM / 'v10/frames'
SPACE = 'Qwen/Qwen-Image-Edit-2511'
TALL, WIDE = (864, 1536), (1536, 864)
KEEP = ('Keep the people exactly the same: the same faces, eyes, noses, mouths, hair, clothes and pose. '
        'No text, no letters, no logos, no screens with writing anywhere. Photorealistic photo.')
CLEAN_KEY = ('the object the woman holds up is a small plain black car key fob with no screen and no lights, hanging from her fingers')
CLEAN_PRINT = 'the print on the girl\'s sweatshirt is a small cartoon bunny with no letters under it'
FRAMES = {
    'mom-tall': {'size': TALL, 'images': [INPUTS / 'mom-front.png', REFS / 'mother-ref.png'], 'prompt': (
        'Edit image 1 only a little: the glowing display at the left edge of the dashboard becomes a dark, switched-off black '
        'glass panel with nothing on it. Everything else stays exactly as in image 1: the woman from image 2 driving at night '
        'with both hands on the steering wheel, looking straight ahead past the camera, the burgundy leather cabin, the orange '
        'streetlights through the windshield, the framing. ')},
    'mom-wide': {'size': WIDE, 'images': [INPUTS / 'mom-front.png', REFS / 'mother-ref.png'], 'prompt': (
        'Make a wide horizontal 16:9 photo of the same moment as image 1: the camera sits on the dashboard in front of the '
        'driver and looks back at her. The driver is the woman from images 1 and 2 (same face, short bob, ivory knit '
        'cardigan over a light blue shirt), both hands on the steering wheel, looking straight ahead at the road just past the '
        'camera, calm and warm. The car is left-hand drive, so seen from the front she sits on the RIGHT half of the photo, '
        'with the driver\'s door and side window (orange streetlights passing) at the right edge; the centre console and the '
        'empty front passenger seat are on the LEFT half of the photo; behind them the back seats and the rear window. '
        'Every seat is the same dark burgundy leather. The centre screen and the radio are switched off: plain black glass, '
        'no lights, no buttons lit. Horizontal framing from the chest up. ')},
    # used as it is: it has no writing, and the edit asking for "no logos" drew a new badge on the headrest (2026-11-15)
    'child-tall': {'size': TALL, 'images': [INPUTS / 'child-front.png'], 'prompt': None},
    'child-wide': {'size': WIDE, 'images': [INPUTS / 'child-front.png', FAMILY / 'hayeon-0606.png'], 'prompt': (
        'Make a wide horizontal 16:9 photo of the same moment as image 1: in the back seat of the burgundy-leather car at '
        'night, the little girl from images 1 and 2 (keep her exact face, round cheeks, eyes, nose and mouth, short straight '
        'black bob with blunt bangs) in a peach sweatshirt sits upright, buckled into the same forward-facing grey child car '
        'seat with a five-point harness, hands on her lap, facing the camera, curious and bright. Seen from the front seats. '
        'Show more of the cabin on both sides: the side window with the dark blue night and warm streetlights on the right, '
        'the burgundy door and the empty rear seat on the left. The car seat has no logos. Horizontal framing from the waist '
        'up, the girl in the center. ')},
    'newcar-tall': {'size': TALL, 'images': [INPUTS / 'newcar-first.png', FAMILY / 'hayeon-0606.png'], 'prompt': (
        f'Edit image 1 only a little: {CLEAN_KEY}; {CLEAN_PRINT}. Everything else stays exactly as in image 1: the mother '
        'and the little girl beside the burgundy car at dusk, the pink sky, the buildings, the framing. ')},
    'newcar-wide': {'size': WIDE, 'seedance': ('newcar-seed', 0.05), 'images': [FAMILY / 'hayeon-0606.png'], 'prompt': (
        f'Edit image 1 only a little: {CLEAN_KEY}; {CLEAN_PRINT}. Everything else stays exactly as in image 1: the new '
        'burgundy Hyundai sedan, the mother and the little girl on the right, the car park at dusk, the framing. ')},
    'whine-wide': {'size': WIDE, 'seedance': ('whine-seed', 0.05), 'images': [], 'prompt': None},  # used as it is
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seedance_frame(clip: str, at: float, target: Path) -> Path:
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{at:.3f}', '-i', str(FILM / 'weave' / f'{clip}.mp4'),
                    '-frames:v', '1', str(target)], check=True)
    return target


def edit(client, images: list, prompt: str, size: tuple, seed: int) -> str:
    from gradio_client import handle_file
    result = client.predict(images=[{'image': handle_file(str(p)), 'caption': None} for p in images], prompt=prompt + KEEP,
                            seed=seed, randomize_seed=False, true_guidance_scale=4.0, num_inference_steps=28, height=size[1],
                            width=size[0], rewrite_prompt=False, api_name='/infer')
    gallery = result[0] if isinstance(result, (list, tuple)) else result
    first = gallery[0] if isinstance(gallery, list) else gallery
    produced = first.get('image') if isinstance(first, dict) else first
    return produced.get('path') if isinstance(produced, dict) else produced


def main() -> int:
    from gradio_client import Client
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    parser.add_argument('--seed', type=int, default=10101)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    token = (Path.home() / '.cache/huggingface/token').read_text().strip()
    client = Client(SPACE, token=token, verbose=False)
    failures = 0
    for name in (args.only.split(',') if args.only else FRAMES):
        spec, target = FRAMES[name], OUT / f'{name}.png'
        images = list(spec['images'])
        if 'seedance' in spec:
            images.insert(0, seedance_frame(*spec['seedance'], OUT / f'{name}-source.png'))
        started = time.time()
        try:
            if spec['prompt'] is None:
                shutil.copyfile(images[0], target)
            else:
                shutil.copyfile(edit(client, images, spec['prompt'], spec['size'], args.seed), target)
        except Exception as error:
            failures += 1
            print(json.dumps({'frame': name, 'error': f'{type(error).__name__}: {error}'[:300]}), flush=True)
            continue
        record = {'name': name, 'space': SPACE if spec['prompt'] else None, 'seed': args.seed, 'size': spec['size'],
                  'prompt': (spec['prompt'] + KEEP) if spec['prompt'] else None,
                  'inputs': [{'file': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in images],
                  'output': {'file': str(target.relative_to(ROOT)), 'sha256': sha(target)},
                  'elapsedSeconds': round(time.time() - started, 1), 'createdAt': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
        (OUT / f'{name}.json').write_text(json.dumps(record, ensure_ascii=False, indent=1))
        print(json.dumps({'frame': name, 'elapsed': record['elapsedSeconds']}), flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
