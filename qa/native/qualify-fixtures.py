"""Qualify synthetic fixtures with native file ASR; separate from microphone E2E."""
from pathlib import Path
import runpy,time,json,subprocess,sys
root=Path(__file__).resolve().parents[2]
p=runpy.run_path(str(root/'scripts/pleos.py'));serial=p['device']();user=p['adb_shell'](serial,'am','get-current-user')
report=root/'qa/native/fixture-qualification.json'
results=json.loads(report.read_text()).get('results',[]) if report.exists() else []
for name in sys.argv[1:]:
    p['adb_shell'](serial,'run-as',p['PACKAGE'],'--user',user,'rm','-f','files/asr-result.txt')
    p['run'](['ffmpeg','-y','-loglevel','error','-i',root/'.tools/voice-fixtures'/(name+'.wav'),'-ar','16000','-ac','1','-c:a','pcm_s16le',p['TOOLS']/'qualified-fixture.wav'])
    p['upload_private'](serial,user,p['TOOLS']/'qualified-fixture.wav','voice-input.wav');p['inject']('wav','voice-input.wav')
    end=time.monotonic()+30
    while time.monotonic()<end:
        r=subprocess.run([str(p['SDK']/'platform-tools/adb'),'-s',serial,'shell','run-as',p['PACKAGE'],'--user',user,'cat','files/asr-result.txt'],capture_output=True,text=True)
        if r.returncode==0 and r.stdout.strip():break
        time.sleep(.3)
    result={'file':name,'transcript':r.stdout.strip()};results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
    time.sleep(1)
(root/'qa/native/fixture-qualification.json').write_text(json.dumps({'method':'Native SDK file ASR fixture qualification only; not microphone E2E','results':results},ensure_ascii=False,indent=2))
