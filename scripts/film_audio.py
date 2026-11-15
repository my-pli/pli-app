"""Original music bed, cabin ambience and Pli chime for the product film.

Everything is synthesized here from the edit timings, so the soundtrack has
no third-party licence and changes with the cut instead of drifting from it.
"""
from pathlib import Path
import wave

import numpy as np

RATE = 48000
A4 = 440.0


def midi(note: float) -> float:
    return A4 * 2 ** ((note - 69) / 12)


def envelope(length: int, attack: float, release: float) -> np.ndarray:
    env = np.ones(length)
    a, r = min(length, int(attack * RATE)), min(length, int(release * RATE))
    if a:
        env[:a] = np.linspace(0, 1, a) ** 2
    if r:
        env[-r:] *= np.linspace(1, 0, r) ** 2
    return env


def lowpass(signal: np.ndarray, cutoff: float) -> np.ndarray:
    """Zero-phase FFT low-pass with a soft roll-off (no ringing clicks)."""
    spectrum = np.fft.rfft(signal, axis=0)
    freqs = np.fft.rfftfreq(signal.shape[0], 1 / RATE)
    gain = 1 / np.sqrt(1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spectrum * (gain[:, None] if signal.ndim == 2 else gain), n=signal.shape[0], axis=0)


def bandpass(signal: np.ndarray, low: float, high: float) -> np.ndarray:
    return lowpass(signal, high) - lowpass(signal, low)


def pluck(freq: float, seconds: float, brightness: float = 1.0) -> np.ndarray:
    """Soft felt-piano-like tone: decaying harmonics with a gentle attack."""
    t = np.arange(int(seconds * RATE)) / RATE
    tone = sum((0.55 ** k) * brightness ** k * np.sin(2 * np.pi * freq * (k + 1) * t + k) * np.exp(-t * (2.2 + 1.6 * k))
               for k in range(5))
    return tone * envelope(len(t), 0.006, 0.08)


def pad(freqs: list, seconds: float) -> np.ndarray:
    """Warm sustained chord: slightly detuned soft voices, slow attack."""
    t = np.arange(int(seconds * RATE)) / RATE
    voice = np.zeros_like(t)
    for f in freqs:
        for detune in (-0.12, 0.12):
            phase = 2 * np.pi * (f + detune) * t
            voice += np.sin(phase) + np.sin(3 * phase) / 9 - np.sin(5 * phase) / 25
    return voice / (2 * len(freqs)) * envelope(len(t), 1.2, 1.4)


def reverb(stereo: np.ndarray, seconds: float = 1.8, mix: float = 0.28, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    length = int(seconds * RATE)
    decay = np.exp(-np.linspace(0, 6.5, length))
    total = stereo.shape[0] + length - 1
    size = 1 << int(np.ceil(np.log2(total)))
    wet = np.zeros_like(stereo)
    for ch in range(2):
        ir = rng.standard_normal(length) * decay
        ir /= np.sqrt(np.sum(ir ** 2))
        wet[:, ch] = np.fft.irfft(np.fft.rfft(stereo[:, ch], size) * np.fft.rfft(ir, size), size)[:stereo.shape[0]]
    return stereo * (1 - mix) + wet * mix


def place(track: np.ndarray, sound: np.ndarray, at: float, gain: float = 1.0, pan: float = 0.0) -> None:
    """Add a mono sound into a stereo buffer (bounded; never grows the track)."""
    start = int(at * RATE)
    if start >= track.shape[0] or start < 0:
        return
    end = min(track.shape[0], start + sound.shape[0])
    left, right = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    track[start:end, 0] += sound[:end - start] * gain * left
    track[start:end, 1] += sound[:end - start] * gain * right


def _before_turn(track: np.ndarray, turn: float, beat: float) -> None:
    """Hushed, unresolved A-minor colour that leaves room for the child's voice."""
    for i, chord in enumerate([[57, 60, 64, 71], [53, 57, 60, 67], [55, 59, 62, 69]]):
        at = i * 4 * beat
        if at < turn:
            place(track, pad([midi(n) for n in chord], min(4 * beat + 1.2, turn - at + 0.6)), at, 0.10)
    for at, note in zip(np.arange(0.4, turn - 0.2, 2 * beat), [76, 74, 72, 71, 72, 69]):
        place(track, pluck(midi(note), 2.2, 0.7), at, 0.10, pan=-0.2)


def _after_turn(track: np.ndarray, turn: float, until: float, beat: float, rng: np.random.Generator) -> None:
    """Warm I–V–vi–IV in D with arpeggiated plucks and a soft off-beat shaker."""
    progression = [[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]]
    bar, at, index = 4 * beat, turn, 0
    tick_len = int(0.05 * RATE)
    while at < until:
        chord = progression[index % 4]
        place(track, pad([midi(n - 12) for n in chord] + [midi(chord[0] - 24)], bar + 1.0), at, 0.12)
        for step in range(8):
            note = chord[[0, 1, 2, 1, 0, 2, 1, 2][step]] + 12
            place(track, pluck(midi(note), 1.4, 0.85), at + step * beat / 2, 0.075, pan=0.3 if step % 2 else -0.3)
        for step in range(4):
            tick = bandpass(rng.standard_normal(tick_len), 5000, 11000) * np.exp(-np.linspace(0, 9, tick_len))
            place(track, tick, at + step * beat + beat / 2, 0.035, pan=0.5)
        at, index = at + bar, index + 1


def music(duration: float, turn: float, end_card: float, seed: int = 11) -> np.ndarray:
    track = np.zeros((int(duration * RATE), 2))
    beat = 60 / 84
    rng = np.random.default_rng(seed)
    _before_turn(track, turn, beat)
    swell = int(1.6 * RATE)  # rising air into the new car
    air = bandpass(rng.standard_normal(swell), 900, 7000) * np.linspace(0, 1, swell) ** 3
    place(track, air / np.max(np.abs(air)), turn - 1.6, 0.06)
    _after_turn(track, turn, duration - end_card + 0.5, beat, rng)
    final = duration - end_card  # resolve under the end card
    place(track, pad([midi(n) for n in [50, 57, 62, 66, 69]], end_card + 0.4), final, 0.13)
    for k, note in enumerate([74, 78, 81, 86]):
        place(track, pluck(midi(note), 3.0, 0.9), final + 0.15 + k * 0.12, 0.07, pan=-0.3 + 0.2 * k)
    track = reverb(track)
    fade = int(1.2 * RATE)
    track[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return track


AMBIENCE_LEVELS = {'old-cabin': (0.085, 260), 'new-cabin': (0.035, 160), 'exterior': (0.05, 2400)}


def ambience(duration: float, segments: list, seed: int = 5) -> np.ndarray:
    """Road and cabin noise; the old cabin is louder and rougher than the new one."""
    rng = np.random.default_rng(seed)
    track = np.zeros((int(duration * RATE), 2))
    for segment in segments:
        gain, cutoff = AMBIENCE_LEVELS[segment['kind']]
        n = int((segment['to'] - segment['from']) * RATE)
        if n <= 0:
            continue
        if segment['kind'] == 'exterior':  # a passing car: band noise swelling and fading
            body = bandpass(rng.standard_normal((n, 2)), 200, cutoff) * np.sin(np.linspace(0, np.pi, n))[:, None] ** 1.5
        else:  # cabin rumble: integrated noise, drift removed, then low-passed
            noise = np.cumsum(rng.standard_normal((n, 2)), axis=0)
            body = lowpass(noise - lowpass(noise, 8), cutoff)
        body /= np.max(np.abs(body)) + 1e-9
        wobble = 1 + 0.12 * np.sin(2 * np.pi * 0.37 * np.arange(n) / RATE)[:, None]
        start = int(segment['from'] * RATE)
        track[start:start + n] += body * gain * wobble * envelope(n, 0.25, 0.25)[:, None]
    return track


def chime(seed: int = 9) -> np.ndarray:
    """Pli's soft two-note sparkle (E6 → B6), mono."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(1.2 * RATE)) / RATE
    tone = np.zeros_like(t)
    for at, f in [(0, midi(88)), (0.11, midi(95))]:
        shifted = np.clip(t - at, 0, None)
        tone += (t >= at) * (np.sin(2 * np.pi * f * shifted) + 0.3 * np.sin(4 * np.pi * f * shifted)) * np.exp(-shifted * 5)
    shimmer = bandpass(rng.standard_normal(len(t)), 6000, 12000) * np.exp(-t * 9) * 0.15
    return (tone + shimmer) * envelope(len(t), 0.004, 0.2) * 0.5


def write_wav(path: Path, stereo: np.ndarray) -> dict:
    """Write 16-bit stereo PCM; scale down (never clip) when the peak is too hot."""
    peak = float(np.max(np.abs(stereo)))
    if peak > 0.98:
        stereo = stereo * (0.98 / peak)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(pcm.tobytes())
    return {'peak': round(peak, 4), 'rms': round(float(np.sqrt(np.mean(stereo ** 2))), 4)}
