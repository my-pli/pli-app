#!/usr/bin/env python3
"""Play a supplied WAV into this project's microphone; restore its private input."""
from pathlib import Path
import json,os,subprocess,sys,urllib.request
import pulsectl
from audio_guard import prime,route_lock,owns,ROOT
state=json.load(urllib.request.urlopen('http://127.0.0.1:8876/api/status',timeout=4))
if state.get('lease',{}).get('busy')or state.get('voiceBusy')or state.get('app',{}).get('demo')or state.get('app',{}).get('capture')!='ACTIVE':raise SystemExit('개인용 음성 세션에서만 WAV 마이크 시험을 실행할 수 있습니다.')
path=Path(sys.argv[1]).resolve();assert path.is_file()and path.suffix.lower()=='.wav'
prime()
try:subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(path),'-f','pulse','-device','pli_remote_mic','Pli private synthetic input'],check=True)
finally:
 with route_lock():
  marker=ROOT/'.tools/demo-audio-state.json';saved=json.loads(marker.read_text())
  with pulsectl.Pulse('pli-private-mic-restore',server=os.environ.get('PULSE_SERVER',f'unix:/run/user/{os.getuid()}/pulse/native'))as p:
   target=next((x for x in p.source_list()if x.name==saved.get('source')),None)
   if target is None:raise RuntimeError('기존 마이크를 복원하지 못했습니다. 입력 장치를 확인하세요.')
   for stream in p.source_output_list():
    if owns(stream):p.source_output_move(stream.index,target.index)
  marker.unlink(missing_ok=True)
print('실제 마이크 경로로 WAV를 전달하고 기존 입력을 복원했습니다. 텍스트 주입이 아닙니다.')
