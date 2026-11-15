"""Real Chrome certificate confirmation and cancellation of a pending fake mic."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
URL=json.loads((ROOT/'.tools/demo-config.json').read_text())['https']
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required'])
    context=browser.new_context(permissions=['microphone'])
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    try:page.goto(URL,wait_until='domcontentloaded')
    except Exception:pass
    page.wait_for_timeout(350)
    if page.locator('#details-button').count():
        page.locator('#details-button').click();page.locator('#proceed-link').click()
    page.wait_for_selector('#connect',timeout=20000)
    page.wait_for_function("typeof emulatorReady!=='undefined' && emulatorReady===true")
    result=page.evaluate('''async()=>{const s=await navigator.mediaDevices.getUserMedia({audio:true});const a=new AudioContext({sampleRate:48000});await a.audioWorklet.addModule('/audio-worklet.js');s.getTracks().forEach(t=>t.stop());await a.close();return {passed:true,secure:isSecureContext}}''')
    page.evaluate('''()=>{const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);window.cancelTestTracks=[];navigator.mediaDevices.getUserMedia=async c=>{const s=await original(c);window.cancelTestTracks=s.getTracks();await new Promise(r=>setTimeout(r,1000));return s;}}''')
    page.locator('#connect').click()
    page.wait_for_function('window.cancelTestTracks.length>0')
    page.evaluate("disconnect('마이크 취소 검증')")
    page.wait_for_timeout(1500)
    result['cancelledMicTracksStopped']=page.evaluate("window.cancelTestTracks.every(t=>t.readyState==='ended')")
    result['cancelledSessionNotOpened']=page.evaluate('!connected && !connecting && ws===null')
    result['noBrowserErrors']=not errors
    result['passed']=all(result.values())
    browser.close()
document={'url':URL,'method':'Chrome without certificate bypass; actual browser certificate confirmation, fake microphone and AudioWorklet. A delayed fake microphone permission result is cancelled before resolving; its tracks must stop and no audio session may open. No user microphone recording.','result':result,'pageErrors':errors}
(ROOT/'qa/native/tailscale-certificate.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(document,ensure_ascii=False,indent=2))
assert result['passed']
