#!/usr/bin/env python3
"""Pli's original voice for an app take, in place of the emulator speaker re-recording.

The take's sound (<take>.wav) is what the public emulator played, re-recorded from the PC's virtual
speaker at about -43 dBFS: quiet, muffled above 4 kHz and noisy once amplified (2026-11-14 audit F3).
The edge voice server keeps every sentence it synthesized with its wall-clock time
(PLI_VOICE_JOURNAL, scripts/edge_voice_server.py). This places each of those original sentences
exactly where the app played it: the journal time gives a rough position, cross-correlation with
the re-recording gives the exact one. A sentence whose best correlation is weak is left out and
reported, so nothing is placed where the app did not say it.

Writes <take>-clean.wav (same time base as <take>.wav) and <take>-clean.json.
usage: .tools/edge-venv/bin/python scripts/film_clean_voice.py TAKE [TAKE ...]
"""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TAKES = ROOT / '.tools/product-film/app-takes'
JOURNAL = ROOT / '.tools/product-film/voice-journal'
RATE = 48000
HOP = 480          # 10 ms
SEARCH = 30.0      # seconds after the server sent a sentence in which the app may play it (it queues sentences)
LOG_LAG = 3.0      # seconds the app's reported PLAYING state may trail its sound (v7: up to 2.1 s)
MIN_SCORE = 0.6    # normalized envelope correlation needed to trust a placement (sentences the app really
                   # played score about 0.95; ones it synthesized ahead but never played, under 0.5)


def load(path: Path, rate: int = RATE) -> np.ndarray:
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-'])
    return np.frombuffer(raw, np.float32).copy()


def envelope(x: np.ndarray) -> np.ndarray:
    """10 ms energy envelope, log-compressed: robust to the re-recording's level and tone."""
    frames = len(x) // HOP
    e = np.sqrt((x[: frames * HOP].reshape(frames, HOP) ** 2).mean(axis=1))
    return np.log1p(e * 200)


def playing(record: dict) -> list:
    """(start, end) wav seconds where the app reported its voice PLAYING (film log, 50 ms polling)."""
    offset = record['appSound']['clipOffset']
    spans, start = [], None
    for event in record['events']:
        at = event['clipAt'] - offset
        if event.get('playback') == 'PLAYING' and start is None:
            start = at
        elif event.get('playback') != 'PLAYING' and start is not None:
            spans.append((start, at))
            start = None
    if start is not None:
        spans.append((start, 1e9))
    return spans


def place(sentence: np.ndarray, recording: np.ndarray, rough: float, not_before: float, windows: list) -> tuple:
    """(start seconds in the recording, normalized correlation) of the sentence after `rough`; sentences
    play in order, so it never starts before the previous one ended (`not_before`)."""
    s_env, r_env = envelope(sentence), envelope(recording)
    lo = max(0, int((max(rough - 1.0, not_before)) * RATE / HOP))
    hi = min(len(r_env) - len(s_env), int((rough + SEARCH) * RATE / HOP))
    if hi <= lo:
        return rough, 0.0
    s = (s_env - s_env.mean()) / (s_env.std() + 1e-9)
    best, best_at = -1.0, lo
    # the app's PLAYING state reaches the film log up to ~1.5 s after its sound starts (v7 takes: 1.4 s)
    allowed = [(int((a - LOG_LAG) * RATE / HOP), int(b * RATE / HOP)) for a, b in windows]
    for at in range(lo, hi):
        if allowed and not any(a <= at <= b for a, b in allowed):  # the app was not playing then
            continue
        window = r_env[at:at + len(s_env)]
        w = (window - window.mean()) / (window.std() + 1e-9)
        score = float((s * w).mean())
        if score > best:
            best, best_at = score, at
    start = best_at * HOP  # refine on the waveform within +-20 ms
    head = sentence[: RATE // 2]
    shifts = range(max(0, start - 960), min(start + 960, len(recording) - len(head)))
    if len(shifts):
        corr = [abs(float(np.dot(head, recording[k:k + len(head)]))) for k in shifts]
        start = shifts[int(np.argmax(corr))]
    return start / RATE, best


def display_text(spoken: list, said: str) -> str:
    """The sentence as the app showed it ('2분'), for the sentence as it was voiced ('이분')."""
    shown = [x for line in spoken for x in re.split(r'(?<=[.!?])\s+', line or '') if x.strip()]
    best = max(shown, key=lambda x: difflib.SequenceMatcher(None, x, said).ratio(), default=said)
    return best if difflib.SequenceMatcher(None, best, said).ratio() >= 0.6 else said  # e.g. album captions are not in `spoken`


def clean(take: str) -> dict:
    record = json.loads((TAKES / f'{take}.json').read_text())
    recording = load(TAKES / f'{take}.wav')
    wav_started = record['grab']['startedAt'] + record['appSound']['clipOffset']  # epoch time of wav t=0
    entries = [json.loads(line) for line in (JOURNAL / 'journal.jsonl').read_text().splitlines() if line.strip()]
    duration = len(recording) / RATE
    entries = [e for e in entries if wav_started - 1 <= e['at'] <= wav_started + duration]
    seen = {}
    unique = []
    for e in entries:  # the app may request the same sentence twice (prefetch, then play): place it once
        if e['text'] in seen and e['at'] - seen[e['text']] < 30:
            continue
        seen[e['text']] = e['at']
        unique.append(e)
    entries = unique
    track = np.zeros_like(recording)
    placed, skipped, free_from = [], [], 0.0
    windows = playing(record)
    for entry in entries:
        sentence = load(JOURNAL / entry['file'])
        at, score = place(sentence, recording, entry['sent'] - wav_started, free_from, windows)
        row = {'text': display_text(record.get('spoken') or [], entry['text']), 'voiced': entry['text'], 'at': round(at, 3),
               'seconds': round(len(sentence) / RATE, 3), 'score': round(score, 3)}
        if score < MIN_SCORE:
            skipped.append(row)
            continue
        start = int(at * RATE)
        end = min(len(track), start + len(sentence))
        track[start:end] += sentence[: end - start]
        placed.append(row)
        free_from = at + len(sentence) / RATE - 0.05
    out = TAKES / f'{take}-clean.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype('<i2').tobytes())
    report = {'take': take, 'sentences': placed, 'skipped': skipped, 'file': out.name}
    (TAKES / f'{take}-clean.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return report


def main() -> int:
    for take in sys.argv[1:]:
        report = clean(take)
        print(json.dumps({'take': take, 'placed': len(report['sentences']), 'skipped': [s['text'] for s in report['skipped']],
                          'scores': [s['score'] for s in report['sentences']]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
