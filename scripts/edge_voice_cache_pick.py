#!/usr/bin/env python3
"""Keeps the best lively rendition of each answer as the file the edge voice serves (see scripts/edge_voice_expressive.py).

For every text with candidates in .tools/voice-cache/candidates/:
  - words      Whisper (the film's own transcriber, scripts/film_speech.py) must hear the text: jamo similarity >= 0.9
  - quality    UTMOS and arousal (scripts/voice-liveliness.py); among the candidates that say the words, the one with
               the best UTMOS + arousal wins
  - served     44.1 kHz mono 16-bit (the app checks X-Sample-Rate), silence trimmed like the live voice (30 ms before,
               60 ms after), loudness matched to the live voice (-24 LUFS, Supertonic F3) -> .tools/voice-cache/<key>.wav
A text none of whose candidates says the words gets no cache file: the live voice keeps speaking it.

Writes .tools/voice-cache/<key>.json (text, candidates and their scores, chosen one) and prints one line per text.
usage: .tools/edge-venv/bin/python scripts/edge_voice_cache_pick.py [--all] [--again FILE] [--source mm]
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_speech  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.tools/voice-cache'
LIVELINESS = [str(ROOT / '.tools/mos-venv/bin/python'), str(ROOT / 'scripts/voice-liveliness.py')]
RATE = 44100
TARGET_LUFS = -24.0      # Supertonic F3 1.4x on Pli's answers (ffmpeg ebur128, 2026-11-15)
MIN_WORDS = 0.9
HEAD, TAIL = 0.03, 0.06


DIGITS = '영일이삼사오육칠팔구'


def sino(number: int) -> str:
    """Sino-Korean reading of a number: Whisper writes '13분' where the app sends '십삼분'."""
    if number == 0:
        return DIGITS[0]
    words = ''
    for unit, name in ((1000, '천'), (100, '백'), (10, '십')):
        count, number = divmod(number, unit)
        if count:
            words += ('' if count == 1 else DIGITS[count]) + name
    return words + (DIGITS[number] if number else '')


def jamo(text: str) -> str:
    text = re.sub(r'\d{1,4}', lambda m: sino(int(m.group())), unicodedata.normalize('NFC', text))
    return re.sub(r'[^가-힣ᄀ-ᇿ]', '', unicodedata.normalize('NFKD', text))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, jamo(a), jamo(b)).ratio()


def scores(paths: list) -> dict:
    out = subprocess.run(LIVELINESS + [str(p) for p in paths], capture_output=True, text=True, check=True).stdout
    return {row['file']: row for row in (json.loads(line) for line in out.splitlines() if line.startswith('{'))}


def served(candidate: Path, target: Path) -> float:
    """44.1 kHz, trimmed like the live voice, at the live voice's loudness; returns its seconds."""
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(candidate), '-ac', '1', '-ar', str(RATE),
                                   '-f', 'f32le', '-'])
    wav = np.frombuffer(raw, np.float32).copy()
    hop = RATE // 100
    frames = len(wav) // hop
    level = np.sqrt((wav[:frames * hop].reshape(frames, hop) ** 2).mean(axis=1))
    voiced = np.flatnonzero(level > 10 ** (-45 / 20))
    if len(voiced):
        wav = wav[max(0, voiced[0] * hop - int(HEAD * RATE)):min(len(wav), (voiced[-1] + 1) * hop + int(TAIL * RATE))]
    with tempfile.TemporaryDirectory() as tmp:
        trimmed = Path(tmp) / 'trimmed.f32'
        trimmed.write_bytes(wav.tobytes())
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(RATE), '-ac', '1', '-i', str(trimmed),
                        '-af', f'loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:linear=true', '-ar', str(RATE), '-ac', '1',
                        '-c:a', 'pcm_s16le', str(target)], check=True)
    return round(len(wav) / RATE, 2)


def main() -> int:
    texts = sorted((CACHE / 'candidates').glob('*.txt'))
    again = set()  # --again FILE: texts (one per line) to choose again although they are already served
    if '--again' in sys.argv:
        lines = Path(sys.argv[sys.argv.index('--again') + 1]).read_text(encoding='utf-8').splitlines()
        again = {hashlib.sha256(t.strip().encode('utf-8')).hexdigest()[:24] for t in lines if t.strip()}
    # --source mm: choose only among the MiniMax renditions (<key>-mm.wav, Weave MiniMax Speech 2.8 HD, 2026-11-15)
    source = sys.argv[sys.argv.index('--source') + 1] if '--source' in sys.argv else ''
    kept = 0
    for text_file in texts:
        key, text = text_file.stem, text_file.read_text(encoding='utf-8').strip()
        candidates = sorted((CACHE / 'candidates').glob(f'{key}-{source}*.wav'))
        if not candidates or ((CACHE / f'{key}.wav').is_file() and '--all' not in sys.argv and key not in again):
            continue  # already served (pass --all to choose again)
        measured = scores(candidates)
        rows = []
        for c in candidates:
            heard = film_speech.transcribe(c)['whisper']
            m = measured.get(c.name, {})
            rows.append({'file': c.name, 'heard': heard, 'words': round(similarity(heard, text), 3), 'utmos': m.get('utmos'),
                         'arousal': m.get('arousal'), 'seconds': m.get('seconds')})
        good = [r for r in rows if r['words'] >= MIN_WORDS and r['utmos'] is not None]
        record = {'key': key, 'text': text, 'candidates': rows, 'chosen': None}
        if good:
            best = max(good, key=lambda r: r['utmos'] + r['arousal'])
            record['chosen'] = best['file']
            record['servedSeconds'] = served(CACHE / 'candidates' / best['file'], CACHE / f'{key}.wav')
            kept += 1
        (CACHE / f'{key}.json').write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')
        print(json.dumps({'key': key, 'text': text[:30], 'chosen': record['chosen'],
                          'best': max(rows, key=lambda r: r['words'])['words']}, ensure_ascii=False), flush=True)
    print(json.dumps({'texts': len(texts), 'cached': kept}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
