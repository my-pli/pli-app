"""Isolate host audio transport with a synthetic tone; never records a user microphone."""
from pathlib import Path
import json,os,subprocess,time
import pulsectl
root=Path(__file__).resolve().parents[2];adb=root/'.tools/android-sdk/platform-tools/adb'
serial=json.loads((root/'.tools/run-state.json').read_text())['serial']
def shell(*args):return subprocess.run([str(adb),'-s',serial,'shell',*args],capture_output=True,text=True,check=True).stdout
user=shell('am','get-current-user').strip();env=os.environ.copy();env['PULSE_SERVER']='unix:/run/user/1000/pulse/native'
with pulsectl.Pulse('pli-transport-probe',server=env['PULSE_SERVER']) as p:
    stream=next(s for s in p.source_output_list() if s.proplist.get('application.name')=='qemu-system-x86_64');original=stream.source
    module=p.module_load('module-null-sink','sink_name=pli_probe rate=44100 channels=2')
    monitor=next(s for s in p.source_list() if s.name=='pli_probe.monitor')
    try:
        p.source_output_move(stream.index,monitor.index)
        tone=subprocess.Popen(['ffmpeg','-nostdin','-loglevel','error','-re','-f','lavfi','-i','sine=frequency=700:sample_rate=44100:duration=8','-af','volume=4','-ac','2','-f','pulse','-device','pli_probe','Pli probe tone'],env=env)
        timeline=[]
        while tone.poll() is None:
            s=json.loads(shell('run-as','ai.teammoon.pli','--user',user,'cat','files/debug-state.json'))
            streams=[{'index':x.index,'source':x.source,'mute':x.mute} for x in p.source_output_list() if x.proplist.get('application.name')=='qemu-system-x86_64']
            timeline.append({'amplitude':s['amplitude'],'partial':s.get('partial'),'streams':streams});time.sleep(.25)
        result={'maximumAmplitude':max(x['amplitude'] for x in timeline),'timeline':timeline}
        (root/'qa/native/microphone-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
    finally:
        for current in p.source_output_list():
            if current.index==stream.index:p.source_output_move(current.index,original)
        p.module_unload(module)
