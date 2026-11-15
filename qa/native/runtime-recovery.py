"""Unexpected emulator exit while a browser voice session is open -> recovery.

Uses a synthetic silent microphone. Does not erase APK data or record user audio.
"""
from pathlib import Path
import json, subprocess, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
ADB=ROOT/'.tools/android-sdk/platform-tools/adb'
CONFIG=json.loads((ROOT/'.tools/demo-config.json').read_text())
URL=CONFIG['https'];HTTP=CONFIG['http']
checks={};timeline=[];errors=[]
def status():
    with urllib.request.urlopen(HTTP+'/api/status',timeout=5) as r:return json.load(r)
def record(label):
    state=status();timeline.append({'at':time.time(),'step':label,'process':state['process'],'videoAgeSeconds':state['videoAgeSeconds'],'voiceBusy':state['voiceBusy'],'runtime':state.get('runtime')});return state
old_pid=int((ROOT/'.tools/emulator.pid').read_text())
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+str(ROOT/'.tools/demo-silence.wav'),'--autoplay-policy=no-user-gesture-required'])
    context=browser.new_context(ignore_https_errors=True,permissions=['microphone'],viewport={'width':1440,'height':1100})
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    navigations=[];page.on('framenavigated',lambda f:navigations.append(f.url) if f==page.main_frame else None)
    page.goto(URL,wait_until='domcontentloaded');page.wait_for_function('emulatorReady===true',timeout=20000)
    page.locator('#connect').click();page.wait_for_function('connected===true',timeout=15000)
    record('voice connected before unexpected exit')
    subprocess.run([str(ADB),'-s',json.loads((ROOT/'.tools/run-state.json').read_text())['serial'],'emu','kill'],capture_output=True,check=True)
    killed_at=time.monotonic();page.wait_for_function('emulatorReady===false',timeout=15000)
    offline=record('offline visible')
    checks['staleScreenCovered']=page.locator('#loading').is_visible()
    checks['offlineControlsDisabled']=page.locator('#open-app').is_disabled() and page.locator('[data-vehicle=drive]').is_disabled()
    reply=context.request.post(URL+'/api/input',data={'type':'key','key':'back'},headers={'Origin':URL})
    checks['offlineInputIsStructured503']=reply.status==503 and reply.json().get('error')=='runtime_unavailable'
    page.screenshot(path=str(ROOT/'qa/native/recovery-offline.png'),full_page=True)
    deadline=time.monotonic()+12
    while status()['voiceBusy'] and time.monotonic()<deadline:page.wait_for_timeout(250)
    checks['deadRuntimeVoiceSessionReleased']=not status()['voiceBusy']
    page.wait_for_function('emulatorReady===true',timeout=150000)
    recovered=record('automatically recovered in same browser')
    checks['hostEmulatorProcessReplaced']=int((ROOT/'.tools/emulator.pid').read_text())!=old_pid
    checks['runtimeReady']=recovered.get('runtime',{}).get('phase')=='ready'
    checks['freshVideo']=recovered['videoAgeSeconds']<3
    checks['controlsEnabledAgain']=page.locator('#open-app').is_enabled() and not page.locator('#loading').is_visible()
    checks['noPageReloadRequired']=len(navigations)==1
    page.locator('#connect').click();page.wait_for_function('connected===true',timeout=15000)
    page.locator('#disconnect').click();page.wait_for_function('connected===false')
    deadline=time.monotonic()+10
    while status()['voiceBusy'] and time.monotonic()<deadline:page.wait_for_timeout(250)
    checks['microphoneReconnectAfterRecovery']=not status()['voiceBusy']
    with page.expect_response(lambda r:r.url.endswith('/api/reopen')) as r:page.locator('#open-app').click()
    checks['recoveredAppControlWorks']=r.value.ok
    page.screenshot(path=str(ROOT/'qa/native/recovery-restored.png'),full_page=True)
    checks['noBrowserErrors']=not errors
    recovery_seconds=round(time.monotonic()-killed_at,2)
    browser.close()
result={'passed':all(checks.values()),'checks':checks,'timeline':timeline,'recoveryAndReconnectSeconds':recovery_seconds,'pageErrors':errors,'method':'Actual Chrome uses a synthetic silent microphone; adb emu kill simulates unexpected runtime loss without the explicit CLI pause marker. The independent runtime service restarts the same AVD and APK. The same page covers stale video, disables input, receives structured 503 and automatically resumes without reload.'}
(ROOT/'qa/native/runtime-recovery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
assert result['passed']
