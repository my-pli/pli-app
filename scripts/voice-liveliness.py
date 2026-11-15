#!/usr/bin/env python3
"""How lively a voice sounds, measured, for choosing Pli's voice (2026-11-15, user: "플리 목소리가 왜케 생동감이 없냐고").

Per WAV:
  arousal, valence   audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim (0..1; calm read speech sits near 0.3-0.4)
  utmos              UTMOS22 strong (predicted naturalness, 1..5)
  pitchSpread        5th-95th percentile of F0 in semitones (the v9 measure)
  pitchMotion        median |ΔF0| between voiced 10 ms frames, semitones per second (how much the melody moves)
  loudnessSpread     std of the voiced frames' level in dB (stress and emphasis)
  syllablesPerSecond Korean syllables of the text / audio seconds (from a sidecar .txt next to the WAV)

usage: .tools/mos-venv/bin/python scripts/voice-liveliness.py A.wav [B.wav ...] [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import torch
from torch import nn
from transformers import Wav2Vec2Model, Wav2Vec2PreTrainedModel, Wav2Vec2Processor

EMOTION = 'audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim'
RATE = 16000


class RegressionHead(nn.Module):
    def __init__(self, config) -> None:
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(features)))))


class EmotionModel(Wav2Vec2PreTrainedModel):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.init_weights()

    def forward(self, input_values: torch.Tensor) -> torch.Tensor:
        return self.classifier(torch.mean(self.wav2vec2(input_values)[0], dim=1))


def load(path: Path) -> np.ndarray:
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'])
    return np.frombuffer(raw, np.float32).copy()


def pitch_track(w: np.ndarray) -> tuple:
    """Autocorrelation F0 every 10 ms (the v9 measure), with the voiced frames' levels."""
    n, hop = int(RATE * .04), int(RATE * .01)
    lo, hi = int(RATE / 500), int(RATE / 70)
    f0, level = [], []
    for i in range(0, len(w) - n, hop):
        fr = w[i:i + n] * np.hanning(n)
        rms = float(np.sqrt((fr ** 2).mean()))
        if rms < .01:
            f0.append(np.nan)
            continue
        sp = np.fft.rfft(fr, 2 * n)
        ac = np.fft.irfft(sp * np.conj(sp))[:n]
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > .5 * ac[0]:
            f0.append(RATE / lag)
            level.append(20 * np.log10(rms))
        else:
            f0.append(np.nan)
    return np.array(f0), np.array(level)


def prosody(w: np.ndarray) -> dict:
    f0, level = pitch_track(w / max(1e-6, float(np.abs(w).max())) * .9)
    voiced = f0[~np.isnan(f0)]
    st = 12 * np.log2(f0 / np.nanmedian(f0))
    steps = np.abs(np.diff(st))
    steps = steps[~np.isnan(steps) & (steps < 3)]  # octave jumps of the tracker are not melody
    return {'pitchSpread': round(float(12 * np.log2(np.percentile(voiced, 95) / np.percentile(voiced, 5))), 1),
            'pitchMotion': round(float(np.median(steps) * 100), 1) if len(steps) else None,
            'medianF0': round(float(np.median(voiced)), 1),
            'loudnessSpread': round(float(np.std(level)), 2)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('wavs', nargs='+', type=Path)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    processor = Wav2Vec2Processor.from_pretrained(EMOTION)
    emotion = EmotionModel.from_pretrained(EMOTION).eval()
    utmos = torch.hub.load('tarepan/SpeechMOS:v1.2.0', 'utmos22_strong', trust_repo=True)
    rows = []
    for path in args.wavs:
        w = load(path)
        with torch.no_grad():
            x = processor(w, sampling_rate=RATE, return_tensors='pt').input_values
            arousal, dominance, valence = (float(v) for v in emotion(x)[0])
            mos = float(utmos(torch.from_numpy(w).unsqueeze(0), RATE))
        text_file = path.with_suffix('.txt')
        syllables = len(re.findall(r'[가-힣]', text_file.read_text())) if text_file.is_file() else None
        row = {'file': path.name, 'seconds': round(len(w) / RATE, 2), 'arousal': round(arousal, 3), 'valence': round(valence, 3),
               'dominance': round(dominance, 3), 'utmos': round(mos, 2), **prosody(w),
               'syllablesPerSecond': round(syllables / (len(w) / RATE), 2) if syllables else None}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
