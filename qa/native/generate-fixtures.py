"""PC-side Korean synthetic audio for reproducible microphone QA. Not part of APK."""
from pathlib import Path
import json,wave
from piper import PiperVoice,SynthesisConfig
root=Path(__file__).resolve().parents[2]/'.tools/voice-fixtures'
voice=PiperVoice.load(str(root/'ko_KR-kss-medium.onnx'))
items={'math-command':'숫자 놀이 해 줘','answer-six':'여섯이야','english-command':'영어 놀이 해 줘','answer-apple':'정답은 애플이야','hush':'조용히','resume':'다시 시작해','schedule':'오늘 일정 알려 줘','arrive':'도착했어','memory-command':'우리 추억 알려 줘'}
for name,text in items.items():
    with wave.open(str(root/(name+'.wav')),'wb') as wav:voice.synthesize_wav(text,wav,SynthesisConfig(length_scale=1.2 if name=="hush" else 1.12))
    print(name,flush=True)
(root/'fixtures.json').write_text(json.dumps(items,ensure_ascii=False,indent=2))
