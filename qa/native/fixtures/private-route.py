import sys,json,os
sys.path.insert(0,'scripts')
from audio_guard import _prime,route_lock,owns,ROOT
import pulsectl
with route_lock():
 _prime()
 f=ROOT/'.tools/demo-audio-state.json';saved=json.loads(f.read_text())
 with pulsectl.Pulse('pli-private-qualification')as p:
  target=next((x for x in p.sink_list()if x.name=='pli_remote_speaker'),None)
  if target is None:p.module_load('module-null-sink','sink_name=pli_remote_speaker rate=44100 channels=2');target=next(x for x in p.sink_list()if x.name=='pli_remote_speaker')
  for stream in p.sink_input_list():
   if owns(stream):
    if 'sink'not in saved:saved['sink']=next(x.name for x in p.sink_list()if x.index==stream.sink)
    p.sink_input_move(stream.index,target.index)
 f.write_text(json.dumps(saved))
 import urllib.request,time
 req=urllib.request.Request('http://127.0.0.1:8876/api/kidsnote/personal',data=json.dumps({'action':'start'}).encode(),headers={'Origin':'http://127.0.0.1:8876','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=45)as r:assert r.status==200
 for _ in range(30):
  s=json.load(urllib.request.urlopen('http://127.0.0.1:8876/api/personal/status'))
  if s.get('app',{}).get('demo')is False and s['app'].get('sessionStatus')in ['PREPARING','ACTIVE']:break
  time.sleep(.1)
 else:raise RuntimeError('Private resource intent not observed')
