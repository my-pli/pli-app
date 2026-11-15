from pathlib import Path
import json,os,subprocess,time
import pulsectl
ROOT=Path(__file__).resolve().parents[2]
ADB=ROOT/'.tools/android-sdk/platform-tools/adb'
def state():
 result=subprocess.run([str(ADB),'-s','emulator-5554','shell','run-as','ai.teammoon.pli','--user','10','cat','files/debug-state.json'],capture_output=True,text=True,check=True)
 return json.loads(result.stdout)
with pulsectl.Pulse('pli-synthetic-microphone-test',server='unix:/run/user/1000/pulse/native') as pulse:
 streams=[s for s in pulse.source_output_list() if 'qemu-system-x86_64'==s.proplist.get('application.name')]
 if not streams:raise RuntimeError('Emulator microphone stream unavailable')
 stream=streams[0];previous=stream.source
 module=pulse.module_load('module-null-sink','sink_name=pli_synthetic_mic rate=16000 channels=1 sink_properties=device.description=PliSyntheticTestMic')
 source=next(x for x in pulse.source_list() if x.name=='pli_synthetic_mic.monitor')
 try:
  pulse.source_output_move(stream.index,source.index)
  deadline=time.monotonic()+25
  while state()['phase'] not in ['LISTENING','QUIET'] and time.monotonic()<deadline:time.sleep(.3)
  env=os.environ.copy();env['PULSE_SERVER']='unix:/run/user/1000/pulse/native'
  subprocess.run(['ffmpeg','-y','-loglevel','error','-re','-i',str(ROOT/'.tools/voice-fixtures/math-command.wav'),'-f','pulse','-device','pli_synthetic_mic','Pli synthetic microphone test'],env=env,check=True)
  timeline=[];deadline=time.monotonic()+18
  while time.monotonic()<deadline:
   s=state();timeline.append({k:s.get(k) for k in ['phase','game','heard','partial','error']})
   if s['game']=='MATH':break
   time.sleep(.35)
  s=state();result={'method':'synthetic Korean speech through emulator PulseAudio microphone input; no text command injection','passed':s['game']=='MATH','state':s,'timeline':timeline}
  (ROOT/'qa/native/microphone-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  print(json.dumps({'passed':result['passed'],'game':s['game'],'heard':s.get('heard'),'partial':s.get('partial'),'error':s.get('error')},ensure_ascii=False),flush=True)
 finally:
  for current in pulse.source_output_list():
   if current.index==stream.index:pulse.source_output_move(current.index,previous)
  pulse.module_unload(module)
