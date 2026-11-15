"""What is actually said in a film clip, and where: the dialogue check of the film QA.

Two local recognizers read the same audio so one model's quirk is not taken for the cast's mistake:
SenseVoice (sherpa-onnx, token times) and Whisper large-v3-turbo (faster-whisper, word times).
`speech_level` measures 10 ms energy so the edit can check that no cut lands inside speech.

usage: .tools/edge-venv/bin/python scripts/film_speech.py FILE [START END]
"""
from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / '.tools/edge-ai/models'
RATE = 16000


def audio(path: Path, start: float = 0.0, end: float | None = None) -> np.ndarray:
    span = ['-ss', f'{start:.3f}'] + (['-t', f'{end - start:.3f}'] if end is not None else [])
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', *span, '-i', str(path), '-vn', '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'])
    return np.frombuffer(raw, np.float32)


@lru_cache(maxsize=1)
def sensevoice():
    import sherpa_onnx
    folder = next((MODELS / 'asr').glob('sherpa-onnx-sense-voice*'))
    return sherpa_onnx.OfflineRecognizer.from_sense_voice(model=str(next(folder.glob('model*.onnx'))), tokens=str(folder / 'tokens.txt'),
                                                          num_threads=6, language='ko', use_itn=False)


@lru_cache(maxsize=1)
def whisper():
    from faster_whisper import WhisperModel
    return WhisperModel('mobiuslabsgmbh/faster-whisper-large-v3-turbo', device='cpu', compute_type='int8', cpu_threads=6,
                        download_root=str(MODELS / 'whisper'))


def transcribe(path: Path, start: float = 0.0, end: float | None = None) -> dict:
    """Both recognizers' text; times are seconds in the file."""
    x = audio(path, start, end)
    stream = sensevoice().create_stream()
    stream.accept_waveform(RATE, x)
    sensevoice().decode_stream(stream)
    sv = stream.result
    segments, _ = whisper().transcribe(x, language='ko', beam_size=5, word_timestamps=True, vad_filter=False,
                                       condition_on_previous_text=False)
    words = [{'w': w.word.strip(), 'start': round(start + w.start, 2), 'end': round(start + w.end, 2)} for s in segments for w in (s.words or [])]
    return {'sensevoice': sv.text.strip(), 'svTokens': [[t, round(start + s, 2)] for t, s in zip(sv.tokens, sv.timestamps)],
            'whisper': ' '.join(w['w'] for w in words), 'words': words}


def speech_level(path: Path, start: float = 0.0, end: float | None = None, hop: float = 0.01) -> tuple:
    """(dB per 10 ms frame, noise floor p10, speech level p90) for the span."""
    x = audio(path, start, end)
    n = int(RATE * hop)
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    return db, float(np.percentile(db, 10)), float(np.percentile(db, 90))


def voiced_share(path: Path, start: float, end: float, floor: float, loud: float) -> float:
    """Share of 10 ms frames in [start, end] louder than halfway (in dB) between floor and speech level."""
    if end <= start:
        return 0.0
    db, _f, _l = speech_level(path, max(0.0, start), end)
    floor = max(floor, -80.0)  # app sound sits on digital silence (-180 dB): keep the bar at a real level
    return float((db > (floor + loud) / 2).mean()) if len(db) else 0.0


def main() -> int:
    path = Path(sys.argv[1])
    start = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    end = float(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(transcribe(path, start, end), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
