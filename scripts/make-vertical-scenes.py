#!/usr/bin/env python3
"""The film's family scenes made natively vertical (9:16) on Hugging Face (PRO account, ZeroGPU), 2026-11-14 (v8).

The user asked for a short made vertically from the start () on Hugging Face PRO
(), not on Weave. Each scene keeps the performance and the voice of the Seedance scene the user
already accepted, and is generated again at 704x1248 by LTX-2 (19B distilled, audio-to-video) in a private copy of the
Space multimodalart/ltx2-audio-to-video (ByeongChanee/pli-ltx2-a2v-hr: only the 9:16 size raised from 512x768):
  - first frame   a 9:16 frame of the scene, or a new front view made by Qwen-Image-Edit-2511 from the scene and the family's
                  reference photos: the mother seen from the dashboard (looking at the camera = looking at the road; a side view
                  made her turn to the camera while driving) and 하연 sitting upright in her car seat (the v6/v7 posture complaint)
  - voice         the scene's own lines, denoised and sped up (); the model moves the lips to them
(linoyts/LTX-2-3-sync, which also takes a pose video, aborted every GPU task on 2026-11-14.)

Writes .tools/product-film/vertical/<scene>.mp4 with <scene>.json (inputs' hashes, prompt, seed, Space, timing).
usage: .tools/film-venv/bin/python scripts/make-vertical-scenes.py [--only scene,scene] [--seed N]
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
WEAVE = ROOT / '.tools/product-film/weave'
OUT = ROOT / '.tools/product-film/vertical'
INPUTS = OUT / 'inputs'
SIZE = (704, 1248)
SYNC_SPACE = 'ByeongChanee/pli-ltx2-a2v-hr'
EDIT_SPACE = 'Qwen/Qwen-Image-Edit-2511'
WIDTH, HEIGHT = 864, 1536  # first frames (9:16); the video size is --size (864x1536 ran past the Space's 100 s GPU limit)
DENOISE = 'afftdn=nr=16:nf=-46'
# The spoken words are never written into the prompt: LTX drew them as garbled on-screen captions (2026-11-14 test).
LOOK = ('Photorealistic live-action film, natural skin, sharp focus on the face, steady camera. '
        'No text, no subtitles, no captions, no logos.')
SCENES = {
    # clip, span (s), 9:16 crop x in the 1920x1080 clip, speed, pose video?, prompt
    'whine': {'clip': 'whine-seed', 'span': (0.0, 3.83), 'x': 0, 'speed': 1.12, 'pose': True, 'prompt': (
        'Inside an older compact car on an overcast afternoon. A little Korean girl with a short black bob and blunt bangs, '
        'in a peach sweatshirt, sits buckled into her child car seat in the back, bored and sleepy, and whines to her mother. '
        'Only she speaks. Her mother, if in view, keeps her mouth closed and keeps driving with her eyes on the road; nobody '
        'leans into the frame. ')},
    'newcar': {'clip': 'newcar-seed', 'span': (0.0, 2.3), 'x': 1150, 'speed': 1.08, 'pose': True, 'prompt': (
        'A car park at dusk, pink sky, building lights on. A little Korean girl in a peach sweatshirt raises both arms and '
        'shouts with joy beside a new burgundy Hyundai sedan. Her mother in an ivory cardigan stands '
        'beside her, smiling, holding up a small plain black car key fob; the mother does not speak. ')},
    'askpack': {'clip': 'ask-pack-seed-noface', 'span': (1.17, 3.95), 'x': 0, 'speed': 1.1, 'pose': False, 'image': 'child-front', 'prompt': (
        'Night, the back seat of a burgundy-leather car, seen from the front seats, streetlights passing outside. A little Korean '
        'girl with a short black bob sits upright, buckled into her child car seat, and asks the car brightly, looking toward the '
        'front. Only she speaks; she stays seated. ')},
    'momalbum': {'clip': 'momalbum-seed', 'span': (2.75, 4.95), 'x': 190, 'speed': 1.1, 'pose': False, 'image': 'mom-front', 'prompt': (
        'Night, seen from the dashboard of a burgundy-leather car, warm streetlights passing. A Korean mother with a short bob, '
        'ivory knit cardigan, drives with both hands on the wheel, looking straight ahead at the road the whole time, and talks warmly. '
        'Small natural head movement only. ')},
    'gothere-mom': {'clip': 'gothere-seed', 'span': (0.85, 2.45), 'speed': 1.05, 'pose': False, 'image': 'mom-front', 'prompt': (
        'Night, seen from the dashboard of a burgundy-leather car, warm streetlights passing. A Korean mother with a short bob, '
        'ivory knit cardigan, drives with both hands on the wheel, looking straight ahead at the road, smiles and asks a gentle question. '
        'She does not turn her head. ')},
    'gothere-child': {'clip': 'gothere-seed', 'span': (3.05, 4.0), 'speed': 1.0, 'pose': False, 'image': 'child-front', 'prompt': (
        'Night, the back seat of a burgundy-leather car, seen from the front seats. A little Korean girl with a short black bob, '
        'sitting upright and buckled into her child car seat, lights up, nods and answers happily. Only she speaks. ')},
}
EXTRA_IMAGES = {'askpack-late': ('ask-pack-seed-noface', 3.6, 0)}  # first frames taken from another moment
RELIGHT = ('Change only the lighting to night: dark blue night sky and warm orange streetlights passing outside the windows, '
           'the cabin lit softly by the dashboard and streetlights. Keep the woman exactly the same (face, hair, cardigan, '
           'hands on the steering wheel, pose), the burgundy interior and the framing. Photorealistic photo.')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list) -> None:
    subprocess.run(args, check=True)


def frame(clip: str, at: float, x: int, target: Path) -> Path:
    run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{at:.3f}', '-i', str(WEAVE / f'{clip}.mp4'), '-frames:v', '1',
         '-vf', f'crop=608:1080:{x}:0,scale={WIDTH}:{HEIGHT}:flags=lanczos', str(target)])
    return target


def inputs(name: str, scene: dict) -> dict:
    """First frame, pose video (with its voice) and voice for one scene, made from its Seedance clip."""
    INPUTS.mkdir(parents=True, exist_ok=True)
    clip, (a, b), speed = WEAVE / f"{scene['clip']}.mp4", scene['span'], scene['speed']
    voice = INPUTS / f'{name}-voice.wav'
    run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', str(clip), '-vn',
         '-af', f'{DENOISE},atempo={speed}', '-ac', '1', '-ar', '48000', str(voice)])
    out = {'voice': voice}
    if scene.get('pose'):
        pose = INPUTS / f'{name}-pose.mp4'
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', str(clip),
             '-vf', f"crop=608:1080:{scene['x']}:0,setpts=PTS/{speed},fps=24", '-af', f'{DENOISE},atempo={speed}',
             '-c:v', 'libx264', '-crf', '16', '-c:a', 'aac', str(pose)])
        out['pose'] = pose
    image_from = scene.get('image')
    if image_from in EXTRA_IMAGES:
        c, at, x = EXTRA_IMAGES[image_from]
        out['image'] = frame(c, at, x, INPUTS / f'{name}-first.png')
    elif image_from:
        out['image'] = INPUTS / f'{image_from}.png'  # a front view made by Qwen-Image-Edit (inputs/<name>.json)
    else:
        out['image'] = frame(scene['clip'], a + 0.02, scene['x'], INPUTS / f'{name}-first.png')
    return out


def relight(client, image: Path, seed: int) -> Path:
    from gradio_client import handle_file
    result = client.predict(images=[{'image': handle_file(str(image)), 'caption': None}], prompt=RELIGHT, seed=seed,
                            randomize_seed=False, true_guidance_scale=4.0, num_inference_steps=28, height=HEIGHT, width=WIDTH,
                            rewrite_prompt=False, api_name='/infer')
    gallery = result[0] if isinstance(result, (list, tuple)) else result
    first = gallery[0] if isinstance(gallery, list) else gallery
    produced = first.get('image') if isinstance(first, dict) else first
    produced = produced.get('path') if isinstance(produced, dict) else produced
    target = image.with_name(image.stem + '-night.png')
    shutil.copyfile(produced, target)
    return target


def seconds(path: Path) -> float:
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]))


NEGATIVE = ('looking away from the road, turning to the back seat, extra people talking, text, subtitles, captions, watermark, '
            'low quality, worst quality, deformed, distorted, blurry face, '
            # v10: what v9's frame review found drawn wrong (a badge growing on the car seat, a key turning into a phone with a
            # blue screen, a glowing dot in the night window, fake writing on the dashboard and on the sweatshirt)
            'logo, badge, letters, writing on clothes, phone, glowing screen, glowing dot, lens flare')
# v10 (2026-11-15): both shapes from the cleaned first frames of scripts/make-scene-frames.py; output in .tools/product-film/v10/<shape>
V10_FRAMES = ROOT / '.tools/product-film/v10/frames'
V10_IMAGE = {'whine': 'whine', 'newcar': 'newcar', 'askpack': 'child', 'momalbum': 'mom', 'gothere-mom': 'mom', 'gothere-child': 'child'}
V10_WHINE_TALL = INPUTS / 'whine-first.png'  # the v8/v9 9:16 frame (the badge was drawn later by the video model, not in it)


def generate(client, name: str, scene: dict, parts: dict, seed: int) -> dict:
    from gradio_client import handle_file
    duration = round(seconds(parts['voice']) + 0.3, 2)
    started = time.time()
    result = client.predict(image_path=handle_file(str(parts['image'])), audio_path=handle_file(str(parts['voice'])),
                            prompt=scene['prompt'] + 'Lips move in sync with the words. ' + LOOK, negative_prompt=NEGATIVE,
                            video_duration=duration, seed=seed, api_name='/generate')
    produced = result[0] if isinstance(result, (list, tuple)) else result
    produced = produced.get('video') if isinstance(produced, dict) else produced
    if not produced:
        raise RuntimeError(f'{name}: the Space returned no video')
    target = OUT / f'{name}.mp4'
    shutil.copyfile(produced, target)
    record = {'scene': name, 'space': SYNC_SPACE, 'model': 'Lightricks LTX-2 19B distilled, audio-to-video (static camera LoRA)',
              'seed': seed, 'prompt': scene['prompt'] + LOOK, 'durationRequested': duration, 'speed': scene['speed'],
              'source': {'clip': f".tools/product-film/weave/{scene['clip']}.mp4", 'span': scene['span']},
              'inputs': {k: {'file': str(v.relative_to(ROOT)), 'sha256': sha(v)} for k, v in parts.items()},
              'video': {'file': str(target.relative_to(ROOT)), 'sha256': sha(target), 'seconds': round(seconds(target), 3)},
              'elapsedSeconds': round(time.time() - started, 1), 'createdAt': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    (OUT / f'{name}.json').write_text(json.dumps(record, ensure_ascii=False, indent=1))
    return record


def main() -> int:
    from gradio_client import Client
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    parser.add_argument('--seed', type=int, default=8101)
    parser.add_argument('--size', default='704x1248', help='video width x height, multiples of 32')
    parser.add_argument('--keep-inputs', action='store_true', help='reuse prepared inputs (and the relit frame)')
    parser.add_argument('--v10', choices=['tall', 'wide'], help='v10: cleaned first frames of this shape, the prepared voices')
    parser.add_argument('--tag', help='v10: keep the result as <name>-<tag> (another seed of the same scene)')
    args = parser.parse_args()
    global SIZE, OUT
    SIZE = tuple(int(v) for v in args.size.split('x'))
    token = (Path.home() / '.cache/huggingface/token').read_text().strip()
    names = args.only.split(',') if args.only else list(SCENES)
    if args.v10:
        OUT = ROOT / '.tools/product-film/v10' / args.v10
        OUT.mkdir(parents=True, exist_ok=True)
        sync = Client(SYNC_SPACE, token=token, verbose=False)
        failures = 0
        for name in names:
            image = V10_WHINE_TALL if (name, args.v10) == ('whine', 'tall') else V10_FRAMES / f'{V10_IMAGE[name]}-{args.v10}.png'
            parts = {'voice': INPUTS / f'{name}-voice.wav', 'image': image}
            for attempt in range(3):  # uploads time out when the line is busy (2026-11-15: ReadTimeout while models downloaded)
                try:
                    record = generate(sync, name, SCENES[name], parts, args.seed)
                    if args.tag:  # several seeds of one scene side by side: <name>-<tag>.mp4
                        for ext in ('mp4', 'json'):
                            (OUT / f'{name}.{ext}').replace(OUT / f'{name}-{args.tag}.{ext}')
                    print(json.dumps({'scene': name, 'shape': args.v10, 'seed': args.seed, 'seconds': record['video']['seconds'],
                                      'elapsed': record['elapsedSeconds']}), flush=True)
                    break
                except Exception as error:
                    print(json.dumps({'scene': name, 'shape': args.v10, 'attempt': attempt, 'error': f'{type(error).__name__}: {error}'[:300]}), flush=True)
                    if 'Timeout' not in type(error).__name__ or attempt == 2:
                        failures += 1
                        break
                    sync = Client(SYNC_SPACE, token=token, verbose=False)
        return 1 if failures else 0
    prepared = {}
    for name in sorted(names, key=lambda n: 0 if SCENES[n].get('relight') else 1):  # the relit frame is reused by a later scene
        if args.keep_inputs and (INPUTS / f'{name}-voice.wav').is_file():
            prepared[name] = {k: INPUTS / f'{name}-{k}.{ext}' for k, ext in (('voice', 'wav'), ('pose', 'mp4'), ('first', 'png'))
                              if (INPUTS / f'{name}-{k}.{ext}').is_file()}
            prepared[name]['image'] = prepared[name].pop('first', None) or OUT / 'inputs' / f"{SCENES[name].get('image')}-first.png"
            continue
        prepared[name] = inputs(name, SCENES[name])
        if SCENES[name].get('relight'):
            prepared[name]['image'] = relight(Client(EDIT_SPACE, token=token, verbose=False), prepared[name]['image'], args.seed)
            shutil.copyfile(prepared[name]['image'], INPUTS / f'{name}-first.png')
    sync = Client(SYNC_SPACE, token=token, verbose=False)
    failures = 0
    for name in names:
        try:
            record = generate(sync, name, SCENES[name], prepared[name], args.seed)
            print(json.dumps({'scene': name, 'seconds': record['video']['seconds'], 'elapsed': record['elapsedSeconds']}), flush=True)
        except Exception as error:
            failures += 1
            print(json.dumps({'scene': name, 'error': f'{type(error).__name__}: {error}'[:300]}), flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
