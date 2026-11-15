"""Voice-only smoke test of the non-debuggable APK; no debug ingress or run-as."""
from pathlib import Path
import json,os,subprocess,time,urllib.request
import pulsectl
root=Path(__file__).resolve().parents[2];adb=root/'.tools/android-sdk/platform-tools/adb'
serial=json.loads((root/'.tools/run-state.json').read_text())['serial']
def shell(*args):return subprocess.run([str(adb),'-s',serial,'shell',*args],capture_output=True,text=True,check=True).stdout
pid=shell('pidof','ai.teammoon.pli').strip()
def logs():return subprocess.run([str(adb),'-s',serial,'logcat','-d','--pid='+pid,'-v','brief','-s','PliConversation:I','*:S'],capture_output=True,text=True,check=True).stdout.splitlines()
env=os.environ.copy();env['PULSE_SERVER']='unix:/run/user/1000/pulse/native'
def play(name):
    src=root/'qa/native/fixtures'/(name+'.wav');padded=root/'.tools'/('release-padded-'+name+'.wav')
    subprocess.run(['ffmpeg','-y','-nostdin','-loglevel','error','-i',str(src),'-af','adelay=800:all=1,apad=pad_dur=3','-ar','44100','-ac','2',str(padded)],check=True)
    subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(padded),'-f','pulse','-device','pli_release_mic','Pli release microphone test'],env=env,check=True)
def expect(fragment,offset):
    end=time.monotonic()+15
    while time.monotonic()<end:
        found=logs()[offset:]
        if any(fragment in line for line in found):return found
        time.sleep(.25)
    raise AssertionError(fragment+': '+str(found))
def screenshot(name):
    with (root/'qa/native'/name).open('wb') as f:subprocess.run([str(adb),'-s',serial,'exec-out','screencap','-p'],stdout=f,check=True)
steps=[]
with pulsectl.Pulse('pli-release-voice-test',server=env['PULSE_SERVER']) as p:
    stream=next(s for s in p.source_output_list() if s.proplist.get('application.name')=='qemu-system-x86_64');previous=stream.source
    module=p.module_load('module-null-sink','sink_name=pli_release_mic rate=44100 channels=2')
    monitor=next(s for s in p.source_list() if s.name=='pli_release_mic.monitor')
    try:
        p.source_output_move(stream.index,monitor.index)
        for name,event,picture in [('math-command','Play: MATH','release-math.png'),('hush','Hush:','release-quiet.png'),('mic-stop','Stop:',None)]:
            offset=len(logs());play(name);found=expect(event,offset);steps.append({'voice':name,'nativeLogs':found});print(event,flush=True)
            if picture:screenshot(picture)
            time.sleep(2)
    finally:
        for current in p.source_output_list():
            if current.index==stream.index:p.source_output_move(current.index,previous)
        p.module_unload(module)
shell('am','start','-W','--user','current','-n','ai.teammoon.pli/.MainActivity')
(root/'qa/native/release-smoke.json').write_text(json.dumps({'method':'Actual non-debuggable APK; synthetic speech through emulator microphone; no debug receiver or file recognition commands','passed':True,'process':pid,'steps':steps},ensure_ascii=False,indent=2))
print('PASS: release microphone, quiet, stop, reopen',flush=True)
