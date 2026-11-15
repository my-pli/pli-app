"""Real Chrome -> TLS/WebSocket -> emulator microphone -> native APK verification.

Uses only synthetic fixture speech. It does not record a person's microphone.
Run with the installed Playwright Python and a prepared .tools/demo-test-journey.wav.
"""
from pathlib import Path
import array, json, ssl, subprocess, time, urllib.request
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / '.tools/demo-config.json').read_text())
URL = CONFIG['https']; HTTP = CONFIG['http']; TLS = ssl._create_unverified_context()
ADB = ROOT / '.tools/android-sdk/platform-tools/adb'
def status():
    with urllib.request.urlopen(HTTP+'/api/status',timeout=5) as r:return json.loads(r.read())
def logs():
    return subprocess.check_output([str(ADB),'-s',json.loads((ROOT/'.tools/run-state.json').read_text())['serial'],'logcat','-d','-v','brief','-s','PliConversation:I','*:S']).decode().splitlines()
baseline = logs(); before = status(); metrics = {'incomingBytes':0,'outgoingBytes':0,'outputNonZeroSamples':0,'receivedMessages':0}
checks = {}; console_errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chrome', args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+str(ROOT/'.tools/demo-test-journey.wav'),'--autoplay-policy=no-user-gesture-required'])
    context = browser.new_context(ignore_https_errors=True, permissions=['microphone'], viewport={'width':1440,'height':1100})
    page = context.new_page(); page.on('pageerror', lambda e: console_errors.append(str(e)))
    def attach(ws):
        def receive(data):
            if isinstance(data, bytes):
                metrics['incomingBytes'] += len(data); metrics['receivedMessages'] += 1
                pcm = array.array('h'); pcm.frombytes(data)
                metrics['outputNonZeroSamples'] += sum(abs(x)>64 for x in pcm)
        def send(data):
            if isinstance(data, bytes): metrics['outgoingBytes'] += len(data)
        ws.on('framereceived',receive);ws.on('framesent',send)
    page.on('websocket',attach)
    page.goto(URL,wait_until='domcontentloaded');page.wait_for_timeout(900)
    checks['secureContext'] = page.evaluate('isSecureContext && !!navigator.mediaDevices')
    page.locator('#connect').click()
    try: page.wait_for_function('connected === true',timeout=16000)
    except Exception:
        print('Voice failed:',page.locator('#voice-note').inner_text(),flush=True);raise
    print('Chrome microphone connected',flush=True)
    checks['secondVoiceClientRejected'] = context.request.get(URL+'/voice',headers={'Origin':URL}).status == 409
    page.wait_for_timeout(27000)
    new_logs = logs()[len(baseline):]
    checks['nativeMathIntent'] = any('Play: MATH' in x for x in new_logs)
    checks['nativeHushIntent'] = any('Hush:' in x for x in new_logs)
    checks['nativeResumeIntent'] = any('Resume:' in x for x in new_logs)
    checks['returnAudioIsNotSilence'] = metrics['outputNonZeroSamples'] > 10000
    checks['duplexTransport'] = metrics['incomingBytes'] > 100000 and metrics['outgoingBytes'] > 100000
    checks['desktopNoHorizontalOverflow'] = page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(ROOT/'qa/native/tailscale-desktop.png'),full_page=True)
    page.locator('#mute').click();checks['muteWorks'] = page.evaluate('muted === true')
    page.locator('#mute').click()
    page.locator('#disconnect').click()
    deadline = time.monotonic()+12
    while status()['voiceBusy'] and time.monotonic()<deadline: time.sleep(.3)
    checks['sessionReleased'] = not status()['voiceBusy']
    mobile = context.new_page();mobile.set_viewport_size({'width':390,'height':844})
    mobile.goto(HTTP,wait_until='domcontentloaded');mobile.wait_for_timeout(1500)
    checks['mobileNoHorizontalOverflow'] = mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    checks['httpMicrophoneGuidance'] = mobile.locator('#https-notice').is_visible()
    mobile.screenshot(path=str(ROOT/'qa/native/tailscale-mobile.png'),full_page=True)
    checks['noPageErrors'] = not console_errors
    browser.close()
after = status();checks['liveVideoFramesAdvance'] = after['videoFrames'] > before['videoFrames']+10
checks['videoFresh'] = after['videoAgeSeconds'] < 3
result = {'passed':all(checks.values()),'method':'Same-host real Chrome accesses Tailscale IPv4:port with synthetic Korean WAV as its microphone. Browser WebSocket PCM traverses virtual audio into the unchanged non-debuggable APK native microphone. Actual native command logs and non-silent return audio verified. This is not an external tailnet-device ACL or child voice test. TLS trust warning bypassed only by the test context.','http':HTTP,'https':URL,'checks':checks,'audioMetrics':metrics,'newNativeLogs':new_logs,'consoleErrors':console_errors,'statusAfter':after}
(ROOT/'qa/native/tailscale-demo.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
assert result['passed']
