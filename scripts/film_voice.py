#!/usr/bin/env python3
"""Film voices: one cached WAV per spoken line, shared by the edit and the app takes.

The same file a child line is mixed from is the file played into the public
app's microphone while its screen is recorded, so what the film shows the app
hearing is exactly what it heard. Needs edge-tts (.tools/film-venv).
"""
from pathlib import Path
import argparse, asyncio, hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / '.tools/product-film/new-cut/voice'
# Korean neural TTS has one female voice and no child voice, so age is shaped acoustically:
# `shape` = (vocal tract, pitch, tempo). Vocal tract scales every frequency (asetrate) like a
# smaller/larger body; pitch then moves only F0 with formants kept (rubberband); tempo restores pace.
# Measured on the base voice (F0 median 222 Hz): 하연 -> 308 Hz with formants x1.24 (a five-year-old
# girl speaks around 280-320 Hz); 엄마 -> 199 Hz with formants x0.95 (a woman in her early thirties).
PRESETS = {  # the cast of the film
    '하연': {'voice': 'ko-KR-SunHiNeural', 'rate': '+0%', 'pitch': '+0Hz', 'shape': [1.24, 1.12, 0.84]},
    '엄마': {'voice': 'ko-KR-SunHiNeural', 'rate': '-4%', 'pitch': '-8Hz', 'shape': [0.95, 1.0, 1.04]},
    '플리': {'voice': 'ko-KR-InJoonNeural', 'rate': '+22%', 'pitch': '+18Hz'},
}
VOICE_KEYS = ('text', 'voice', 'rate', 'pitch', 'formant', 'shape')
TTS_RATE = 24000  # edge-tts MP3 sample rate
ATTEMPTS = 4


def with_preset(line: dict) -> dict:
    """A line names its speaker; voice settings come from the cast unless overridden."""
    return {**PRESETS.get(line.get('speaker'), {}), **line}


def voice_file(line: dict) -> Path:
    line = with_preset(line)
    key = json.dumps({k: line.get(k) for k in VOICE_KEYS}, ensure_ascii=False, sort_keys=True)
    return VOICE_DIR / (line['id'] + '-' + hashlib.sha256(key.encode()).hexdigest()[:12] + '.wav')


def age_filter(line: dict) -> str:
    """ffmpeg filters that give the voice its age (see PRESETS); ends with a comma."""
    if line.get('shape'):
        tract, pitch, tempo = line['shape']
        return (f'asetrate={TTS_RATE}*{tract},aresample=48000,'
                f'rubberband=tempo={tempo}:pitch={pitch}:formant=preserved:pitchq=quality,')
    lift = line.get('formant', 1.0)
    return f'asetrate={TTS_RATE}*{lift},aresample=48000,atempo={1 / lift:.5f},' if lift != 1.0 else 'aresample=48000,'


def _run(args: list) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


async def _one(line: dict) -> Path:
    import edge_tts
    line, target = with_preset(line), voice_file(line)
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = target.with_suffix('.mp3')
    for attempt in range(ATTEMPTS):  # the public TTS endpoint drops sockets now and then
        try:
            await edge_tts.Communicate(line['text'], line['voice'], rate=line['rate'], pitch=line['pitch']).save(str(raw))
            break
        except Exception:
            if attempt == ATTEMPTS - 1:
                raise
            await asyncio.sleep(2 * (attempt + 1))
    shape = age_filter(line)
    trim = 'silenceremove=start_periods=1:start_threshold=-50dB'
    partial = target.with_suffix('.part.wav')
    _run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-af',
          f'{shape}highpass=f=80,{trim},areverse,{trim},areverse,afade=t=in:d=0.015', '-ac', '2', str(partial)])
    partial.replace(target)
    raw.unlink()
    return target


def synthesize(lines: list) -> dict:
    async def everything():
        return await asyncio.gather(*(_one(line) for line in lines))
    return dict(zip((line['id'] for line in lines), asyncio.run(everything())))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lines', help='JSON list of {id, speaker, text}')
    args = parser.parse_args()
    made = synthesize(json.loads(args.lines))
    print(json.dumps({key: str(path) for key, path in made.items()}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
