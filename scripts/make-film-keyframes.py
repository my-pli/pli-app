#!/usr/bin/env python3
"""Start frames for the film's family scenes, with 하연 herself.

The first film used one AI storyboard still, so its girl was an invented child. Each start frame
here is an image edit of a storyboard crop (.tools/product-film/keyframes/<base>.png) together with
the child's private reference photo: the girl becomes 하연 (same face and bob with bangs), the new
car's cabin follows the current Grandeur's horizontal dashboard, and the light is the early-evening
drive home from 학원. The video model (LTX) then animates these frames with its own voices.

Sends the reference photo to the image-edit Space (Hugging Face ZeroGPU) — the user asked for the
real child's face in the generated scenes. Writes .tools/product-film/keyframes-v5/<name>.png and a
provenance record (<name>.json: inputs' hashes, prompt, seed, space).

usage: .tools/film-venv/bin/python scripts/make-film-keyframes.py [--only name,name]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE = 'Qwen/Qwen-Image-Edit-2511'  # the fast community build returned RuntimeError for every request (2026-11-13)
BASES = ROOT / '.tools/product-film/keyframes'
REFERENCE = ROOT / '.tools/private-family/reference-child.jpg'
OUT = ROOT / '.tools/product-film/keyframes-v5'
STEPS = 28  # the official Space's quality/time balance on ZeroGPU
GIRL = ('the girl from image 2 — keep her exact face, round cheeks and eyes, short straight black bob with blunt bangs — '
        'wearing a peach sweatshirt')
GRANDEUR = ('a brand-new premium Korean sedan cabin like the current Hyundai Grandeur: one wide horizontal dashboard with a long '
            'panoramic display, a thin full-width air-vent line across the dash, soft ambient light strip, cream leather seats')
EVENING = 'early-evening light on the drive home from an after-school academy, warm city lights outside'
JOBS = {
    'old-cabin-hayeon': {'base': 'old-cabin', 'seed': 7101, 'prompt': (
        f'Replace the little girl in the rear child seat of image 1 with {GIRL}. She looks bored and slumps in her seat. '
        f'Keep the older compact car interior, the mother driving, the camera angle and the gray {EVENING}. Photorealistic photo.')},
    'new-car-family': {'base': 'new-car', 'seed': 7102, 'prompt': (
        f'Make it an apartment parking lot in {EVENING}. The car is a brand-new midnight-green Hyundai Grandeur style sedan with one thin '
        f'full-width horizontal LED light bar across the front. Next to it stand {GIRL}, raising both hands in delight, and her mother, a Korean '
        'woman in her thirties with a short dark bob and an ivory cardigan, holding the car key. Photorealistic photo, no text.')},
    'hello-pli-hayeon': {'base': 'hello-pli', 'seed': 7103, 'prompt': (
        f'Replace the girl in the rear child seat with {GIRL}. Change the car interior to {GRANDEUR}; keep the yellow star character glowing '
        f'on the center screen. {EVENING.capitalize()}. Photorealistic photo, no text.')},
    'hayeon-close-v5': {'base': 'hayeon-close', 'seed': 7104, 'prompt': (
        f'Replace the girl with {GIRL}, buckled in a rear child seat of {GRANDEUR}. Close shot, her face clearly visible, {EVENING}. '
        'Photorealistic photo, no text.')},
    'calm-drive-hayeon': {'base': 'calm-drive', 'seed': 7105, 'prompt': (
        f'Keep the mother driving with both hands on the wheel. Replace the little girl in the back seat with {GIRL}. Change the car interior '
        f'to {GRANDEUR}. {EVENING.capitalize()}. Photorealistic photo, no text.')},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edit(client, name: str, job: dict) -> dict:
    from gradio_client import handle_file
    base = BASES / f"{job['base']}.png"
    started = time.time()
    result = client.predict(images=[{'image': handle_file(str(base)), 'caption': None}, {'image': handle_file(str(REFERENCE)), 'caption': None}], prompt=job['prompt'],
                            seed=job['seed'], randomize_seed=False, true_guidance_scale=4.0, num_inference_steps=STEPS,
                            height=720, width=1280, rewrite_prompt=False, api_name='/infer')
    gallery = result[0] if isinstance(result, (list, tuple)) else result
    first = gallery[0] if isinstance(gallery, list) else gallery
    produced = first.get('image') if isinstance(first, dict) else first
    produced = produced.get('path') if isinstance(produced, dict) else produced
    target = OUT / f'{name}.png'
    shutil.copyfile(produced, target)
    record = {'name': name, 'space': SPACE, 'baseSha256': sha(base), 'referenceSha256': sha(REFERENCE), 'prompt': job['prompt'],
              'seed': job['seed'], 'steps': STEPS, 'size': [1280, 720], 'pngSha256': sha(target), 'elapsedSeconds': round(time.time() - started, 1),
              'createdAt': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    target.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n')
    return record


def main() -> int:
    from gradio_client import Client
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    args = parser.parse_args()
    wanted = set(args.only.split(',')) if args.only else set(JOBS)
    OUT.mkdir(parents=True, exist_ok=True)
    client = Client(SPACE, token=(Path.home() / '.cache/huggingface/token').read_text().strip(), verbose=False)
    failed = 0
    for name, job in JOBS.items():
        if name not in wanted:
            continue
        try:
            record = edit(client, name, job)
            print(json.dumps({'name': name, 'status': 'MADE', 'seconds': record['elapsedSeconds']}), flush=True)
        except Exception as error:  # reported, never replaced by a stand-in
            failed += 1
            print(json.dumps({'name': name, 'status': 'FAILED', 'error': f'{type(error).__name__}: {error}'[:300]}, ensure_ascii=False), flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
