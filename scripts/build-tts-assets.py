"""Package Pli's voice (Supertonic 3, Supertone, OpenRAIL-M) as a voice pack for the edge and the head unit.

The four ONNX graphs keep fp32 compute but store their large weights as fp16 followed by a Cast
node; ONNX Runtime folds the Cast when the session is created, so the APK carries about half the
bytes with no change in what the graphs compute. Only the chosen voice style and the Korean
text indexer are copied. The script then runs the fp32 and packaged graphs side by side on the
same real line and refuses to write anything if their audio differs audibly (log-mel distance).

usage: .tools/tts-build-venv/bin/python scripts/build-tts-assets.py [--voice F1]
needs: onnx, onnxruntime, numpy (.tools/tts-build-venv); model in ~/.cache/supertonic3
(download once with `.tools/edge-venv/bin/python -c "from supertonic import TTS; TTS(auto_download=True)"`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import helper, numpy_helper

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / '.cache/supertonic3'
OUT = ROOT / '.tools/voice-pack'  # served to the car by the edge (scripts/edge_voice_server.py)
APK_MANIFEST = ROOT / 'android/app/src/main/assets/tts/manifest.json'  # the APK carries only names, sizes and hashes
GRAPHS = ('duration_predictor', 'text_encoder', 'vector_estimator', 'vocoder')
MIN_FP16_ELEMENTS = 4096  # small tensors (norm scales, biases) stay fp32
MAX_RELATIVE_ERROR = 0.02  # duration and text encoders
MAX_MEL_DISTANCE_DB = 0.5  # mean voiced log-mel difference; F1-F3 measure 0.06-0.15 dB
STEPS = 8  # as the edge synthesizes (scripts/edge_voice_server.py)


def halve(model: onnx.ModelProto) -> tuple[onnx.ModelProto, int]:
    """fp32 initializers above the size floor → fp16 initializer + Cast(to=float)."""
    graph = model.graph
    casts, kept, halved = [], [], 0
    for init in graph.initializer:
        if init.data_type != onnx.TensorProto.FLOAT or np.prod(init.dims) < MIN_FP16_ELEMENTS:
            kept.append(init)
            continue
        half = numpy_helper.from_array(numpy_helper.to_array(init).astype(np.float16), init.name + '__fp16')
        kept.append(half)
        casts.append(helper.make_node('Cast', [half.name], [init.name], to=onnx.TensorProto.FLOAT, name=init.name + '__cast'))
        halved += 1
    del graph.initializer[:]
    graph.initializer.extend(kept)
    nodes = list(graph.node)
    del graph.node[:]
    graph.node.extend(casts + nodes)
    return model, halved


def session(path: Path) -> ort.InferenceSession:
    return ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])


def log_mel(wav: np.ndarray, rate: int, n_fft: int = 1024, hop: int = 256, bands: int = 80) -> np.ndarray:
    """Log-mel spectrogram in dB (numpy only): what the ear compares, unlike raw samples whose phase may drift."""
    to_hz = lambda m: 700 * (10 ** (m / 2595) - 1)
    edges = np.floor((n_fft + 1) * to_hz(np.linspace(0, 2595 * np.log10(1 + rate / 2 / 700), bands + 2)) / rate).astype(int)
    bank = np.zeros((bands, n_fft // 2 + 1))
    for i in range(1, bands + 1):
        lo, mid, hi = edges[i - 1], edges[i], edges[i + 1]
        bank[i - 1, lo:mid] = (np.arange(lo, mid) - lo) / max(1, mid - lo)
        bank[i - 1, mid:hi] = (hi - np.arange(mid, hi)) / max(1, hi - mid)
    frames = 1 + (len(wav) - n_fft) // hop
    index = np.arange(n_fft)[None] + hop * np.arange(frames)[:, None]
    power = np.abs(np.fft.rfft(wav[index] * np.hanning(n_fft), axis=1)) ** 2
    return 10 * np.log10(power @ bank.T + 1e-10)


def compare(original: Path, packaged: Path, voice: dict, indexer: list) -> dict:
    """Synthesize a real Pli line in full (duration → text embedding → 8 denoising steps → vocoder) with both.

    The encoders are deterministic, so their outputs must match closely (relative error). The audio is compared as
    a log-mel spectrogram over its voiced frames: a diffusion sampler can drift a fraction of a sample in phase,
    which makes raw waveforms differ by up to 35% at a peak (voice F3, 2026-11-15) while sounding the same
    (log-mel 0.06-0.14 dB for F1, F2 and F3; UTMOS within 0.01 except one line where the pack scored higher).
    """
    cfg = json.loads((original / 'tts.json').read_text())
    rate = cfg['ae']['sample_rate']
    chunk = cfg['ae']['base_chunk_size'] * cfg['ttl']['chunk_compress_factor']
    channels = cfg['ttl']['latent_dim'] * cfg['ttl']['chunk_compress_factor']
    text = '<ko>하연아, 가는 길에 도서관이 있어. 들렀다 갈까?</ko>'
    ids = np.array([[indexer[ord(c)] for c in text]], dtype=np.int64)
    mask = np.ones((1, 1, ids.shape[1]), dtype=np.float32)
    ttl = np.array(voice['style_ttl']['data'], dtype=np.float32)
    dp = np.array(voice['style_dp']['data'], dtype=np.float32)
    results = []
    for folder in (original, packaged):
        s = {name: session(folder / f'{name}.onnx') for name in GRAPHS}
        duration = s['duration_predictor'].run(None, {'text_ids': ids, 'style_dp': dp, 'text_mask': mask})[0]
        emb = s['text_encoder'].run(None, {'text_ids': ids, 'style_ttl': ttl, 'text_mask': mask})[0]
        samples = int(float(results[0][0].ravel()[0] if results else duration.ravel()[0]) * rate)  # same length for both
        frames = (samples + chunk - 1) // chunk
        x = np.random.default_rng(7).standard_normal((1, channels, frames)).astype(np.float32)
        latent_mask = np.ones((1, 1, frames), dtype=np.float32)
        for step in range(STEPS):
            x = s['vector_estimator'].run(None, {'noisy_latent': x, 'text_emb': emb, 'style_ttl': ttl, 'latent_mask': latent_mask,
                                                 'text_mask': mask, 'current_step': np.array([step], np.float32),
                                                 'total_step': np.array([STEPS], np.float32)})[0]
        wav = s['vocoder'].run(None, {'latent': x})[0].ravel()[:samples]
        results.append((duration, emb, wav))
    (d0, e0, w0), (d1, e1, w1) = results
    encoders = max(float(np.abs(a - b).max() / (np.abs(a).max() + 1e-9)) for a, b in ((d0, d1), (e0, e1)))
    m0, m1 = log_mel(w0, rate), log_mel(w1, rate)
    voiced = m0.max(axis=1) > m0.max() - 50
    return {'encoderError': encoders, 'melDistanceDb': float(np.abs(m0[voiced] - m1[voiced]).mean())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice', default='F1')
    args = parser.parse_args()
    staging = OUT.with_name('voice-pack.staging')
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    halved = {}
    for name in GRAPHS:
        model, count = halve(onnx.load(str(SOURCE / 'onnx' / f'{name}.onnx')))
        onnx.save(model, str(staging / f'{name}.onnx'))
        halved[name] = count
    voice = json.loads((SOURCE / 'voice_styles' / f'{args.voice}.json').read_text())
    indexer = json.loads((SOURCE / 'onnx/unicode_indexer.json').read_text())
    check = compare(SOURCE / 'onnx', staging, voice, indexer)
    if check['encoderError'] > MAX_RELATIVE_ERROR or check['melDistanceDb'] > MAX_MEL_DISTANCE_DB:
        shutil.rmtree(staging)
        raise SystemExit(f'packaged voice differs from the original ({json.dumps(check)})')
    shutil.copy(SOURCE / 'onnx/tts.json', staging / 'tts.json')
    shutil.copy(SOURCE / 'onnx/unicode_indexer.json', staging / 'unicode_indexer.json')
    shutil.copy(SOURCE / 'voice_styles' / f'{args.voice}.json', staging / 'voice.json')
    shutil.copy(SOURCE / 'LICENSE', staging / 'LICENSE')
    files = sorted(p for p in staging.iterdir() if p.is_file())
    manifest = {'model': 'Supertone Supertonic 3 (OpenRAIL-M)', 'voice': args.voice, 'weights': 'fp16 storage, fp32 compute',
                'encoderError': round(check['encoderError'], 5), 'melDistanceDb': round(check['melDistanceDb'], 3), 'halvedTensors': halved,
                'files': {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}}
    (staging / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.rmtree(OUT, ignore_errors=True)
    staging.rename(OUT)
    APK_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(OUT / 'manifest.json', APK_MANIFEST)
    print(json.dumps({'voice': args.voice, **{k: round(v, 4) for k, v in check.items()},
                      'megabytes': round(sum(p.stat().st_size for p in OUT.iterdir()) / 1e6, 1)}))


if __name__ == '__main__':
    main()
