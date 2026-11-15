"""Reproduce the observed live CarService stall; retain its real reboot recovery.

This diagnostic requires an already stalled property service. The repeatable
fault contract is covered separately by server-contract and VehicleSignalHealthTest.
No system service is killed and no vehicle data is fabricated.
"""
from pathlib import Path
import json,subprocess,time,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics)
from playwright.sync_api import sync_playwright
ADB=ROOT/'.tools/android-sdk/platform-tools/adb';URL='https://127.0.0.1:9000'
def native(path='state'):
 return json.loads(subprocess.check_output([str(ADB),'-s',json.loads((ROOT/'.tools/run-state.json').read_text())['serial'],'exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path],timeout=8))
def status():return json.load(urllib.request.urlopen('http://127.0.0.1:8876/api/status',timeout=4))
before=native();summary=native('private-summary');assert before['sessionStatus']=='STOPPED'and before['gear']=='—'and before.get('speedKmh')is None,'This diagnostic needs the existing observed CarService stall, not a healthy guest'
checks['stalledCoreDoesNotKeepOldDriveValue']=True;metrics['bootBefore']=before['deviceBootCount'];at=time.monotonic()
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=b.new_context(ignore_https_errors=True,permissions=['microphone']);v=c.new_page()
 try:
  v.goto(URL);v.wait_for_function('emulatorReady && !lastStatus.lease.busy',timeout=90000);v.locator('#connect').click();until=time.monotonic()+120;recovered=False;observed=False
  while time.monotonic()<until:
   s=status();a=s.get('app',{});observed=observed or s.get('lease',{}).get('status')=='RECOVERING'
   if a.get('deviceBootCount',0)>before['deviceBootCount']and a.get('sessionStatus')=='STOPPED'and a.get('visible')and a.get('demo')and not s.get('lease',{}).get('busy'):recovered=True;break
   v.wait_for_timeout(300)
  checks['unconfirmedVehicleTriggersRealGuestRecovery']=observed and recovered;assert recovered,'Actual recovery was not confirmed'
  metrics.update(bootAfter=a['deviceBootCount'],recoverySeconds=round(time.monotonic()-at,3));checks['browserTracksReleasedDuringRecovery']=v.evaluate('stream===null && ctx===null')
  checks['publicViewAndSupervisorRestored']=(ROOT/'.tools/portal-mode').exists()and native()['visible'];checks['familyStorePreserved']=native('private-summary')==summary
  v.reload();v.wait_for_function('emulatorReady && !lastStatus.lease.busy',timeout=45000);v.locator('#connect').click();v.wait_for_function("connected && lastStatus.app.sessionStatus==='ACTIVE' && lastStatus.app.recognition==='READY' && lastStatus.app.phase==='LISTENING' && lastStatus.app.playback==='IDLE' && lastStatus.app.speech===lastStatus.app.requestedText",timeout=45000)
  checks['newDriveActuallyConfirmed']=v.evaluate("lastStatus.app.gear==='D' && lastStatus.app.speedKmh===32")
  ack=v.evaluate("post('/api/vehicle',{action:'park'})");v.wait_for_function("lastStatus.app.gear==='P' && lastStatus.app.speedKmh===0",timeout=10000);checks['newParkActuallyConfirmed']=ack.get('ok')is True
 finally:
  try:v.evaluate('disconnect()');v.wait_for_function('!ending && !lastStatus.voiceBusy && !lastStatus.lease.busy',timeout=20000)
  finally:b.close()
checks['actualMicrophoneStopped']=native()['capture']=='STOPPED';checks['familyStoreStillPreserved']=native('private-summary')==summary
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
