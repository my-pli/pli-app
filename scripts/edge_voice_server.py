#!/usr/bin/env python3
"""Pli's voice on the edge computer's GPU.

Same model, voice and text rules as the in-APK engine (android/.../voice/PliVoiceEngine.kt): the
Supertonic 3 graphs packaged in android/app/src/main/assets/tts, Korean number reading, NFKD text
encoding. The app asks for one sentence at a time and plays it while the next is made; on the GPU a
sentence takes well under a second, so Pli answers at once even while the head unit's CPU is busy.
If this service is unreachable the app synthesizes on the head unit, then falls back to Pleos TTS.

POST /v1/voice  {"text": "..."}  → audio/L16 mono 44.1 kHz little-endian (header X-Sample-Rate)
GET  /v1/voice/health           → {"ok": true, "provider": "CUDAExecutionProvider", "p50Ms": ...}

Each sentence is trimmed to 30 ms of silence before and 60 ms after the voice, so the pause between
sentences is the app's own gap, not the model's padding (the 2026-11-14 film audit measured 310-410 ms).
With PLI_VOICE_JOURNAL=<dir> set (film recording only), every sentence is also kept as a WAV with the
wall-clock time it was requested and sent (<dir>/journal.jsonl), so the film can use Pli's original
voice instead of re-recording the emulator's speaker.

Lively answers (2026-11-15, "플리 목소리가 왜케 생동감이 없냐고"; "음성은 … 위브를쓰던 다른 tts를 써야"): an answer the
car has spoken before is served from .tools/voice-cache/<key>.wav, a rendition by a commercial voice, MiniMax Speech 2.8 HD
(voice Exuberant_Girl, emotion happy, 1.15x, run through Figma Weave; .tools/voice-cache/minimax/<key>.json keeps the
run id). Measured on Pli's answers (scripts/voice-liveliness.py, audeering arousal 0..1): 0.75-0.92, mean 0.84, vs
0.53-0.57 for Supertonic and 0.77 for the earlier CosyVoice3 renditions (kept in .tools/voice-cache/cosyvoice-served/).
scripts/edge_voice_cache_pick.py --source mm checks each one with Whisper and serves it at the live voice's level. A new
answer is still spoken at once by Supertonic, in a different timbre, and queued (.tools/voice-cache/queue.jsonl) to be
rendered for next time. The response says which (X-Voice-Source).

Loopback only (the emulator reaches the host's 127.0.0.1 as 10.0.2.2).
usage: .tools/tts-gpu-venv/bin/python scripts/edge_voice_server.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import threading
import time
import unicodedata
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / '.tools/voice-pack'
PORT = 8892
STEPS = 8          # the GPU can afford the model's default quality
SPEED = 1.4  # 2026-11-15: voice F3 at 1.4x — on three real answers: UTMOS 4.10 (F2 at 1.2x: 3.96), pitch spread 13.9 semitones (12.4), same pace as F2 at 1.2x (6.3 syllables/s with pauses) ("너무 딱딱", "너무 느리잖아")
MAX_TEXT = 200
HEAD_SILENCE, TAIL_SILENCE = 0.03, 0.06  # seconds of silence kept around the voice
JOURNAL = Path(os.environ['PLI_VOICE_JOURNAL']) if os.environ.get('PLI_VOICE_JOURNAL') else None
CACHE = ROOT / '.tools/voice-cache'
QUEUED: set = set()
QUEUE_LOCK = threading.Lock()


def cache_key(text: str) -> str:
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()[:24]  # as scripts/edge_voice_expressive.py


def cached(text: str, rate: int) -> bytes | None:
    """The lively rendition of this exact answer, as 16-bit PCM at the live voice's rate, or None."""
    path = CACHE / f'{cache_key(text)}.wav'
    if not path.is_file():
        return None
    try:
        with wave.open(str(path), 'rb') as w:
            if w.getframerate() != rate or w.getnchannels() != 1 or w.getsampwidth() != 2:
                return None
            return w.readframes(w.getnframes())
    except (OSError, wave.Error):
        return None


def enqueue(text: str) -> None:
    """A new answer: remembered once so the renderer can make its lively version for next time."""
    with QUEUE_LOCK:
        if text in QUEUED:
            return
        QUEUED.add(text)
        CACHE.mkdir(parents=True, exist_ok=True)
        with (CACHE / 'queue.jsonl').open('a', encoding='utf-8') as out:
            out.write(json.dumps({'text': text, 'at': round(time.time(), 3)}, ensure_ascii=False) + '\n')
CPU_THREADS = 8
# Share the laptop GPU politely: a bounded arena and no exhaustive cuDNN search (its workspace spikes).
CUDA = {'device_id': 0, 'gpu_mem_limit': 900 * 1024 * 1024, 'arena_extend_strategy': 'kSameAsRequested', 'cudnn_conv_algo_search': 'HEURISTIC'}

NATIVE_COUNTERS = ['가지', '개', '명', '마리', '살', '시간', '시', '장', '문제', '곳', '권', '잔', '벌', '켤레',
                   '군데', '바퀴', '송이', '대', '판', '글자', '단어', '번째', '밤', '줄', '통']
NATIVE_ONES = ['', '한', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉']
NATIVE_TENS = ['', '열', '스물', '서른', '마흔', '쉰', '예순', '일흔', '여든', '아흔']
SINO = ['영', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
UNITS = [(re.compile(r'(\d+(?:\.\d+)?)\s*%'), '퍼센트'), (re.compile(r'(\d+(?:\.\d+)?)\s*km/h', re.I), '킬로미터'),
         (re.compile(r'(\d+(?:\.\d+)?)\s*kWh'), '킬로와트시'), (re.compile(r'(\d+(?:\.\d+)?)\s*km', re.I), '킬로미터'),
         (re.compile(r'(\d+(?:\.\d+)?)\s*(?:℃|°C)'), '도')]
COUNTED = re.compile(r'(\d+)\s*(' + '|'.join(map(re.escape, NATIVE_COUNTERS)) + ')')
CLOCK = re.compile(r'(\d{1,2}):(\d{2})')
NUMBER = re.compile(r'\d+(?:\.\d+)?')
REPLACEMENTS = [('–', '-'), ('—', '-'), ('_', ' '), ('“', '"'), ('”', '"'), ('‘', "'"), ('’', "'"), ('[', ' '), (']', ' '),
                ('|', ' '), ('/', ' '), ('#', ' '), ('→', ' '), ('←', ' '), ('·', ', ')]


def native(n: int) -> str:
    if not 1 <= n <= 99:
        return sino(n)
    tens, ones = divmod(n, 10)
    return ('스무' if tens == 2 and ones == 0 else NATIVE_TENS[tens]) + NATIVE_ONES[ones]


def under_ten_thousand(n: int) -> str:
    out = ''
    for place, name in ((1000, '천'), (100, '백'), (10, '십')):
        d = (n // place) % 10
        if d:
            out += name if d == 1 else SINO[d] + name
    return out + (SINO[n % 10] if n % 10 else '')


def sino(value: int) -> str:
    if value == 0:
        return '영'
    parts, rest = [], value
    for size, name in ((100_000_000, '억'), (10_000, '만'), (1, '')):
        group, rest = divmod(rest, size)
        if group:
            parts.append('만' if name == '만' and group == 1 else under_ten_thousand(group) + name)
    return ' '.join(parts)


def decimal(raw: str) -> str:
    whole, _, fraction = raw.partition('.')
    return sino(int(whole)) + (' 점 ' + ''.join(SINO[int(c)] for c in fraction) if fraction else '')


def normalize(text: str) -> str:
    """Korean reading of numbers; the same rules as KoreanReading.kt."""
    out = CLOCK.sub(lambda m: native(int(m.group(1))) + ' 시' + ('' if int(m.group(2)) == 0 else f' {sino(int(m.group(2)))} 분'), text)
    for pattern, unit in UNITS:
        out = pattern.sub(lambda m: decimal(m.group(1)) + ' ' + unit, out)

    def counted(m: re.Match) -> str:
        n, counter = int(m.group(1)), m.group(2)
        word = '첫' if counter == '번째' and n == 1 else native(n) if 1 <= n <= 99 else sino(n)
        return f'{word} {counter}'
    out = COUNTED.sub(counted, out)
    return NUMBER.sub(lambda m: decimal(m.group(0)), out)


class Voice:
    def __init__(self) -> None:
        cfg = json.loads((ASSETS / 'tts.json').read_text())
        self.rate = cfg['ae']['sample_rate']
        compress = cfg['ttl']['chunk_compress_factor']
        self.chunk = cfg['ae']['base_chunk_size'] * compress
        self.channels = cfg['ttl']['latent_dim'] * compress
        self.indexer = np.array(json.loads((ASSETS / 'unicode_indexer.json').read_text()), dtype=np.int64)
        style = json.loads((ASSETS / 'voice.json').read_text())
        self.ttl = np.array(style['style_ttl']['data'], dtype=np.float32)
        self.dp = np.array(style['style_dp']['data'], dtype=np.float32)
        ort.preload_dlls()
        self.lock = threading.Lock()
        self.timings: list[float] = []
        try:  # the GPU is shared with other work on this computer; when it has no room, the CPU takes over
            self.sessions = self.open([('CUDAExecutionProvider', CUDA), 'CPUExecutionProvider'])
            self.synthesize('안녕! 오늘도 같이 가자.')  # load kernels (and prove the GPU has room) before the first request
        except Exception as error:
            print(json.dumps({'gpu': 'unavailable', 'reason': f'{type(error).__name__}: {error}'[:200]}), flush=True)
            self.sessions = self.open(['CPUExecutionProvider'])
            self.synthesize('안녕! 오늘도 같이 가자.')
        self.provider = self.sessions['vector_estimator'].get_providers()[0]

    def open(self, providers: list) -> dict:
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.intra_op_num_threads = CPU_THREADS
        return {name: ort.InferenceSession(str(ASSETS / f'{name}.onnx'), options, providers=providers)
                for name in ('duration_predictor', 'text_encoder', 'vector_estimator', 'vocoder')}

    def encode(self, text: str) -> np.ndarray:
        t = unicodedata.normalize('NFKD', normalize(text))
        t = ''.join(c for c in t if not (0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF))
        for a, b in REPLACEMENTS:
            t = t.replace(a, b)
        t = re.sub(r'\s+', ' ', re.sub(r' ([,.!?;:\'])', r'\1', re.sub(r'[♥☆♡©\\*]', '', t))).strip()
        if not re.search(r'[.!?;:,\'")\]}…]$', t):
            t += '.'
        points = np.array([ord(c) for c in f'<ko>{t}</ko>'], dtype=np.int64)
        known = points < len(self.indexer)
        return np.where(known, self.indexer[np.where(known, points, 0)], 0)[None, :]

    def synthesize(self, text: str) -> np.ndarray:
        started = time.monotonic()
        ids = self.encode(text)
        mask = np.ones((1, 1, ids.shape[1]), np.float32)
        s = self.sessions
        with self.lock:
            seconds = float(s['duration_predictor'].run(None, {'text_ids': ids, 'style_dp': self.dp, 'text_mask': mask})[0].ravel()[0]) / SPEED
            samples = max(1, int(seconds * self.rate))
            frames = (samples + self.chunk - 1) // self.chunk
            emb = s['text_encoder'].run(None, {'text_ids': ids, 'style_ttl': self.ttl, 'text_mask': mask})[0]
            x = np.random.default_rng(abs(hash(text)) % (2 ** 32)).standard_normal((1, self.channels, frames)).astype(np.float32)
            latent_mask = np.ones((1, 1, frames), np.float32)
            total = np.array([STEPS], np.float32)
            for step in range(STEPS):
                x = s['vector_estimator'].run(None, {'noisy_latent': x, 'text_emb': emb, 'style_ttl': self.ttl, 'latent_mask': latent_mask,
                                                     'text_mask': mask, 'current_step': np.array([step], np.float32), 'total_step': total})[0]
            wav = s['vocoder'].run(None, {'latent': x})[0].ravel()[:samples]
        self.timings = (self.timings + [(time.monotonic() - started) * 1000])[-50:]
        return self.trim(wav)

    def trim(self, wav: np.ndarray) -> np.ndarray:
        """Cut the model's leading and trailing silence (below -45 dBFS in 10 ms frames)."""
        hop = self.rate // 100
        frames = len(wav) // hop
        if frames < 3:
            return wav
        level = np.sqrt((wav[: frames * hop].reshape(frames, hop) ** 2).mean(axis=1))
        voiced = np.flatnonzero(level > 10 ** (-45 / 20))
        if not len(voiced):
            return wav
        start = max(0, voiced[0] * hop - int(HEAD_SILENCE * self.rate))
        end = min(len(wav), (voiced[-1] + 1) * hop + int(TAIL_SILENCE * self.rate))
        return wav[start:end]


VOICE: Voice | None = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # quiet: the app calls once per sentence
        pass

    def send(self, code: int, body: bytes, kind: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith('/v1/voice/pack/'):  # the head unit's fallback engine downloads the pack once
            name = self.path.rsplit('/', 1)[-1]
            files = json.loads((ASSETS / 'manifest.json').read_text())['files']
            if name not in files and name != 'manifest.json':
                return self.send(404, b'{}', 'application/json')
            return self.send(200, (ASSETS / name).read_bytes(), 'application/octet-stream')
        if self.path != '/v1/voice/health':
            return self.send(404, b'{}', 'application/json')
        p50 = round(statistics.median(VOICE.timings)) if VOICE and VOICE.timings else None
        self.send(200, json.dumps({'ok': VOICE is not None, 'provider': VOICE.provider if VOICE else None, 'p50Ms': p50,
                                   'expressiveCache': len(list(CACHE.glob('*.wav'))) if CACHE.is_dir() else 0}).encode(), 'application/json')

    def do_POST(self) -> None:
        if self.path != '/v1/voice' or VOICE is None:
            return self.send(404, b'{}', 'application/json')
        try:
            length = int(self.headers.get('Content-Length') or 0)
            if not 0 < length <= 4096:
                raise ValueError('BODY_SIZE')
            text = str(json.loads(self.rfile.read(length)).get('text', '')).strip()
            if not text or len(text) > MAX_TEXT:
                raise ValueError('TEXT_SIZE')
        except (ValueError, json.JSONDecodeError) as error:
            return self.send(400, json.dumps({'error': str(error)}).encode(), 'application/json')
        received = time.time()
        pcm = cached(text, VOICE.rate)
        if pcm is not None:
            self.send(200, pcm, 'audio/L16', {'X-Sample-Rate': VOICE.rate, 'X-Synth-Ms': 0, 'X-Voice-Source': 'expressive-cache'})
        else:
            wav = VOICE.synthesize(text)
            pcm = (np.clip(wav, -1, 1) * 32767).astype('<i2').tobytes()
            self.send(200, pcm, 'audio/L16', {'X-Sample-Rate': VOICE.rate, 'X-Synth-Ms': round(VOICE.timings[-1]), 'X-Voice-Source': 'supertonic'})
            enqueue(text)
        if JOURNAL:
            keep(text, pcm, received)


def keep(text: str, pcm: bytes, received: float) -> None:
    """Film recording only: the exact sentence the app was sent, with wall-clock times."""
    JOURNAL.mkdir(parents=True, exist_ok=True)
    name = f'{received:.3f}.wav'
    with wave.open(str(JOURNAL / name), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(VOICE.rate)
        out.writeframes(pcm)
    with (JOURNAL / 'journal.jsonl').open('a', encoding='utf-8') as log:
        log.write(json.dumps({'at': round(received, 3), 'sent': round(time.time(), 3), 'text': text, 'file': name, 'rate': VOICE.rate},
                             ensure_ascii=False) + '\n')


def main() -> None:
    global VOICE
    VOICE = Voice()
    print(json.dumps({'ready': True, 'provider': VOICE.provider, 'warmupMs': round(VOICE.timings[-1])}), flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
