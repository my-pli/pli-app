from pathlib import Path
import json,subprocess,time,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics);adb=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial'];marker=ROOT/'.tools/runtime-transition'
def call(*args):return subprocess.check_output([str(adb),'-s',serial,*args],timeout=8)
def native(part='state'):return json.loads(call('exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+part))
def control(action):assert b'Result:'in call('shell','content','call','--user','10','--uri','content://ai.teammoon.pli.demo','--method','session','--arg',action)
before=native('private-summary');state=native();assert state['sessionStatus']=='STOPPED'and state['capture']=='STOPPED';boot=state['deviceBootCount'];marker.write_text(str(time.time()+180));began=time.monotonic()
try:
 call('reboot');deadline=time.monotonic()+100
 while time.monotonic()<deadline:
  try:
   if call('shell','getprop','sys.boot_completed').decode().strip()=='1'and call('shell','am','get-current-user').decode().strip()=='10':break
  except subprocess.SubprocessError:pass
  time.sleep(.5)
 else:raise AssertionError('Owned private guest did not boot')
 control('preview');call('shell','am','start','--user','10','--activity-single-top','-n','ai.teammoon.pli/.MainActivity');marker.unlink(missing_ok=True);time.sleep(10)
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  s=json.load(urllib.request.urlopen('http://127.0.0.1:8876/api/personal/status',timeout=5));a=s.get('app',{})
  if s.get('appResponsive')and a.get('visible')and a.get('hasView')and a.get('sessionStatus')=='STOPPED':break
  time.sleep(.5)
 else:raise AssertionError('Private idle view did not recover')
 after=native();checks['oneActualPrivateGuestReboot']=after['deviceBootCount']==boot+1;checks['familySummaryPreserved']=native('private-summary')==before;checks['idleCaptureConfirmed']=after['capture']=='STOPPED'and after['playback']=='IDLE'and after['focus']=='NONE';metrics['recoverySeconds']=round(time.monotonic()-began,3)
finally:marker.unlink(missing_ok=True)
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
