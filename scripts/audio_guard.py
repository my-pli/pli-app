"""Project-only silence routing retained across demo server crashes."""
from pathlib import Path
import os,json,fcntl,time
from contextlib import contextmanager
import pulsectl
from runtime_context import selected,state_dir
CONTEXT=selected();STATE=state_dir()
ROOT=Path(__file__).resolve().parents[1]
class AudioRouteBusy(RuntimeError):
 pass
@contextmanager
def route_lock():
 with (STATE/'demo-audio.lock').open('a')as lock:
  deadline=time.monotonic()+.5
  while True:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:
    if time.monotonic()>deadline:raise AudioRouteBusy('AUDIO_ROUTE_BUSY')
    time.sleep(.01)
  try:yield
  finally:fcntl.flock(lock,fcntl.LOCK_UN)

def owns(stream):
 if stream.proplist.get('application.name')!='qemu-system-x86_64':return False
 try:
  if int(stream.proplist.get('application.process.id','0'))!=int((STATE/'emulator.pid').read_text()):return False
  a=(Path('/proc')/stream.proplist.get('application.process.id','0')/'cmdline').read_bytes().split(b'\0');return b'-avd'in a and a[a.index(b'-avd')+1:a.index(b'-avd')+2]==[CONTEXT.avd_name.encode()]
 except (OSError,ValueError):return False

def _prime():
 state=STATE/'demo-audio-state.json'
 with pulsectl.Pulse('pli-silence-prime',server=os.environ.get('PULSE_SERVER',f'unix:/run/user/{os.getuid()}/pulse/native'))as p:
  name='pli_remote_mic'+('_public' if CONTEXT.profile=='public' else '');monitor=next((x for x in p.source_list()if x.name==name+'.monitor'),None)
  if monitor is None:p.module_load('module-null-sink',f'sink_name={name} rate=44100 channels=2');monitor=next(x for x in p.source_list()if x.name==name+'.monitor')
  try:saved=json.loads(state.read_text())
  except (OSError,ValueError):saved={}
  if CONTEXT.profile=='public':
   output='pli_remote_speaker_public'
   if not any(x.name==output for x in p.sink_list()):p.module_load('module-null-sink',f'sink_name={output} rate=44100 channels=2')
   saved.update(source=monitor.name,sink=output)
  streams=[x for x in p.source_output_list()if owns(x)]
  if not streams and CONTEXT.profile!='public':raise RuntimeError('PROJECT_MIC_UNAVAILABLE')
  for stream in streams:
   original=next((x.name for x in p.source_list()if x.index==stream.source),None)
   if CONTEXT.profile=='public':saved['source']=monitor.name
   elif 'source'not in saved and original!=monitor.name:saved['source']=original
  if not saved.get('source'):raise RuntimeError('ORIGINAL_ROUTE_UNKNOWN')
  temp=state.with_suffix('.tmp');temp.write_text(json.dumps(saved));temp.replace(state)
  for stream in streams:p.source_output_move(stream.index,monitor.index)

def _guard():
 if not (STATE/'demo-audio-state.json').exists() and CONTEXT.profile!='public':return
 with pulsectl.Pulse('pli-silence-guard',server=os.environ.get('PULSE_SERVER',f'unix:/run/user/{os.getuid()}/pulse/native'))as p:
  name='pli_remote_mic'+('_public' if CONTEXT.profile=='public' else '');monitor=next((x for x in p.source_list()if x.name==name+'.monitor'),None)
  if monitor is None:p.module_load('module-null-sink',f'sink_name={name} rate=44100 channels=2');monitor=next(x for x in p.source_list()if x.name==name+'.monitor')
  for stream in p.source_output_list():
   if owns(stream)and stream.source!=monitor.index:p.source_output_move(stream.index,monitor.index)
def prime():
 with route_lock():_prime()
def guard():
 with route_lock():_guard()
if __name__=='__main__':guard()
