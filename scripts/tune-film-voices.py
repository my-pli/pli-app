#!/usr/bin/env python3
"""Lower the pitch of a generated child voice without re-voicing it.

The film's family voices come from the video model with the picture (LTX); a few child lines came
out far above a five-year-old's range (430-500 Hz against ~250-330 Hz). For each generated shot with
`voiceTune` segments in media/pli-film/production.json, the shot's own soundtrack is pitch-shifted
inside those segments only, with formants preserved and duration unchanged (ffmpeg rubberband), so
the words, timing and lip-sync stay exactly as generated. Output: .tools/product-film/tuned/<id>.wav
plus <id>.json (source hash, segments, median F0 before/after) for the edit to reference.

usage: python3 scripts/tune-film-voices.py [--only id,id]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'media/pli-film/production.json'
GENERATED = ROOT / '.tools/product-film/generated'
OUT = ROOT / '.tools/product-film/tuned'
RATE = 48000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> np.ndarray:
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '2', '-ar', str(RATE), '-f', 'f32le', '-'])
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def shift(audio: np.ndarray, pitch: float) -> np.ndarray:
    """Formant-preserving pitch shift of a stereo float block; same length out."""
    filt = f'rubberband=pitch={pitch}:formant=preserved:pitchq=quality:transients=smooth:detector=soft'
    out = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ac', '2', '-ar', str(RATE), '-i', '-', '-af', filt,
                          '-ac', '2', '-ar', str(RATE), '-f', 'f32le', '-'], input=audio.tobytes(), capture_output=True, check=True).stdout
    shifted = np.frombuffer(out, np.float32).reshape(-1, 2)
    fitted = np.zeros_like(audio)
    n = min(len(audio), len(shifted))
    fitted[:n] = shifted[:n]
    return fitted


def median_f0(audio: np.ndarray) -> int | None:
    mono = audio.mean(axis=1)[:: RATE // 16000]
    sr, frame, hop, found = 16000, 640, 160, []
    for i in range(0, len(mono) - frame, hop):
        w = mono[i:i + frame] * np.hanning(frame)
        if np.sqrt((w ** 2).mean()) < 0.01:
            continue
        ac = np.correlate(w, w, 'full')[frame - 1:]
        lo, hi = sr // 600, sr // 80
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] / ac[0] > 0.45:
            found.append(sr / k)
    return int(np.median(found)) if found else None


def tune(shot: dict) -> dict:
    source = GENERATED / f"{shot['id']}.mp4"
    audio = read(source)
    out, report = audio.copy(), []
    fade = int(0.03 * RATE)
    for seg in shot['voiceTune']:
        a, b = int(seg['from'] * RATE), min(len(audio), int(seg['to'] * RATE))
        block = shift(audio[a:b], seg['pitch'])
        ramp = np.ones(b - a, np.float32)
        ramp[:fade] = np.linspace(0, 1, fade)
        ramp[-fade:] = np.linspace(1, 0, fade)
        out[a:b] = block * ramp[:, None] + audio[a:b] * (1 - ramp[:, None])
        report.append({**seg, 'f0Before': median_f0(audio[a:b]), 'f0After': median_f0(out[a:b])})
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{shot['id']}.wav"
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(RATE), '-i', '-', str(target)],
                   input=out.tobytes(), check=True)
    record = {'shot': shot['id'], 'sourceSha256': sha(source), 'method': 'ffmpeg rubberband, formant preserved, duration unchanged',
              'segments': report, 'wavSha256': sha(target)}
    target.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n')
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    args = parser.parse_args()
    wanted = set(args.only.split(',')) if args.only else None
    plan = json.loads(PLAN.read_text())
    for shot in plan['shots']:
        if shot.get('voiceTune') and (wanted is None or shot['id'] in wanted):
            print(json.dumps(tune(shot), ensure_ascii=False))


if __name__ == '__main__':
    main()
