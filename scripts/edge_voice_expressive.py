#!/usr/bin/env python3
"""Lively renditions of Pli's answers for the edge voice cache (2026-11-15, user: "플리 목소리가 왜케 생동감이 없냐고").

Measured on Pli's real answers (scripts/voice-liveliness.py, audeering arousal 0..1): the edge's real-time voice,
Supertonic 3 F3 at 1.4x, sounds read aloud (arousal 0.53-0.57); CosyVoice3 (Fun-CosyVoice3-0.5B, Apache-2.0) told to
speak "very warmly, excited, full of energy" in Pli's own timbre (prompt: the Supertonic F3 voice) reaches 0.78-0.89 at
1.25x. It needs about twice real time on this shared laptop GPU, so it cannot answer live; instead it renders, ahead of
time, the answers the car speaks again and again, and scripts/edge_voice_server.py serves those from the cache (a new
answer is spoken at once by Supertonic and queued here for next time).

Each text gets several sampled candidates in .tools/voice-cache/candidates/<key>-<n>.wav (24 kHz); the picker
(scripts/edge_voice_cache_pick.py) keeps the best one as the served file.

usage: .tools/tts-eval/cosy-python scripts/edge_voice_expressive.py [--journal-day YYYY-MM-DD] [--queue] [--candidates N] [TEXT ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / '.tools/tts-eval'
CACHE = ROOT / '.tools/voice-cache'
JOURNAL = ROOT / '.tools/product-film/voice-journal/journal.jsonl'
MODEL = EVAL / 'models/Fun-CosyVoice3-0.5B'
PROMPT = EVAL / 'prompt-f3.wav'      # Pli's timbre: a Supertonic F3 line (its text in prompt-f3.txt)
INSTRUCT = 'You are a helpful assistant. 请用非常热情、兴奋、充满活力的语气说这句话，语速稍快。<|endofprompt|>'
SPEED = float(__import__('os').environ.get('PLI_EXPRESSIVE_SPEED', '1.25'))  # the edge voice's pace; 1.15 when 1.25 sounds strained


def key(text: str) -> str:
    """The cache key of a request: the exact text the app sends (it spells numbers out itself)."""
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()[:24]


def journal_texts(day: str) -> list:
    texts = []
    for line in JOURNAL.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if time.strftime('%Y-%m-%d', time.localtime(row['at'])) == day and row['text'] not in texts:
            texts.append(row['text'])
    return texts


def queued_texts() -> list:
    path = CACHE / 'queue.jsonl'
    if not path.is_file():
        return []
    texts = []
    for line in path.read_text(encoding='utf-8').splitlines():
        text = json.loads(line)['text']
        if text not in texts and not (CACHE / f'{key(text)}.wav').is_file():
            texts.append(text)
    return texts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('texts', nargs='*')
    parser.add_argument('--journal-day')
    parser.add_argument('--queue', action='store_true')
    parser.add_argument('--candidates', type=int, default=3)
    args = parser.parse_args()
    texts = list(args.texts) + (journal_texts(args.journal_day) if args.journal_day else []) + (queued_texts() if args.queue else [])
    texts = list(dict.fromkeys(t.strip() for t in texts if t.strip()))
    if not texts:
        print(json.dumps({'rendered': 0}))
        return 0
    sys.path.insert(0, str(EVAL / 'cosyvoice-src'))
    sys.path.insert(0, str(EVAL / 'cosyvoice-src/third_party/Matcha-TTS'))
    import torch
    import torchaudio
    from cosyvoice.cli.cosyvoice import AutoModel
    model = AutoModel(model_dir=str(MODEL), fp16=True)
    (CACHE / 'candidates').mkdir(parents=True, exist_ok=True)
    for text in texts:
        k = key(text)
        (CACHE / 'candidates' / f'{k}.txt').write_text(text, encoding='utf-8')
        for n in range(args.candidates):
            target = CACHE / 'candidates' / f'{k}-{n}.wav'
            if target.is_file():
                continue
            torch.manual_seed(1000 + n)
            started = time.time()
            chunks = list(model.inference_instruct2(text, INSTRUCT, str(PROMPT), stream=False, speed=SPEED))
            wav = torch.cat([c['tts_speech'] for c in chunks], dim=1)
            torchaudio.save(str(target), wav, model.sample_rate)
            print(json.dumps({'key': k, 'candidate': n, 'seconds': round(wav.shape[1] / model.sample_rate, 2),
                              'synth': round(time.time() - started, 1), 'text': text[:40]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
