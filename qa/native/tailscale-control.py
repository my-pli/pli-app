"""Browser gestures/buttons -> actual Android UI and virtual vehicle.

Tests the Tailscale IP from this PC; it is not a second-device ACL test.
"""
from pathlib import Path
import json, subprocess, time, xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / '.tools/android-sdk/platform-tools/adb'
URL = json.loads((ROOT/'.tools/demo-config.json').read_text())['https']
checks = {}; responses = []; evidence = {}; errors = []; latest_nodes=[]
def shell(*args):
    return subprocess.check_output([str(ADB),'-s',json.loads((ROOT/'.tools/run-state.json').read_text())['serial'],'shell',*args],timeout=15).decode()
def texts():
    global latest_nodes
    shell('uiautomator','dump','/data/local/tmp/pli-control-test.xml')
    raw=shell('cat','/data/local/tmp/pli-control-test.xml')
    latest_nodes=[(n.get('text'),n.get('bounds')) for n in ET.fromstring(raw).iter('node') if n.get('text')]
    return [x[0] for x in latest_nodes]
def activities():
    return [x.strip() for x in shell('dumpsys','activity','activities').splitlines() if 'topResumedActivity' in x]

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='chrome')
    context=browser.new_context(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL,wait_until='domcontentloaded');page.wait_for_timeout(800)
    def button(selector, endpoint):
        with page.expect_response(lambda r:r.url.endswith(endpoint) and r.request.method=='POST') as response:
            page.locator(selector).click()
        reply=response.value;responses.append({'selector':selector,'status':reply.status,'body':reply.json()})
        assert reply.ok
        page.wait_for_timeout(350)
    def tap(x,y, mobile=False):
        page.locator('#screen').scroll_into_view_if_needed();box=page.locator('#screen').bounding_box()
        with page.expect_response(lambda r:r.url.endswith('/api/input') and r.request.method=='POST') as response:
            if mobile:page.touchscreen.tap(box['x']+box['width']*x,box['y']+box['height']*y)
            else:page.mouse.click(box['x']+box['width']*x,box['y']+box['height']*y)
        assert response.value.ok
        responses.append({'gesture':'tap','mobile':mobile,'response':response.value.json()});page.wait_for_timeout(450)
    button('#open-app','/api/reopen')
    tap(.92,.16)  # dismiss any OEM drawer without changing app state
    tap(.542,.95)
    t=texts();evidence['desktopDrawerTexts']=t
    checks['desktopTapOpensActualAndroidDrawer']='앱' in t and '공조' in t
    assert checks['desktopTapOpensActualAndroidDrawer']
    tap(.373,.503)  # Select Apps explicitly; SystemUI remembers its previous tab.
    # Open the actual OEM vehicle-settings Activity. The launcher drawer itself
    # is not a normal Android Back target, so verify Back on this real Activity.
    tap(.598,.60)
    before=texts();evidence['settingsBefore']=before;before_positions=latest_nodes.copy()
    checks['tapOpensNativeSettings']=any('ai.umos.vehiclecontrol' in x for x in activities())
    page.locator('#screen').scroll_into_view_if_needed();box=page.locator('#screen').bounding_box()
    with page.expect_response(lambda r:r.url.endswith('/api/input') and r.request.method=='POST') as response:
        page.mouse.move(box['x']+box['width']*.40,box['y']+box['height']*.75)
        page.mouse.down();page.mouse.move(box['x']+box['width']*.40,box['y']+box['height']*.25,steps=12);page.mouse.up()
    checks['dragDispatchedAsAndroidSwipe']=response.value.ok and response.value.json()['type']=='swipe'
    page.wait_for_timeout(400)
    evidence['settingsAfterSwipe']=texts()
    checks['dragChangesActualScrollPositions']=before_positions!=latest_nodes and '모든 창문' in evidence['settingsAfterSwipe']
    page.locator('#touch-surface').focus()
    with page.expect_response(lambda r:r.url.endswith('/api/input') and r.request.method=='POST') as response:page.keyboard.press('Escape')
    checks['keyboardBackDispatch']=response.value.ok and response.value.json()['type']=='key'
    dispatcher=shell('dumpsys','input')
    queue=dispatcher.split('RecentQueue:',1)[-1].split('PendingEvent:',1)[0]
    evidence['nativeKeyDispatcherQueue']=queue
    checks['keyboardReachesAndroidInputDispatcher']=queue.count('KeyEvent')>=2
    page.wait_for_timeout(500)
    evidence['rootBackStillHasSettingsTask']=any('ai.umos.vehiclecontrol' in x for x in activities())
    button('[data-remote-key=home]','/api/input');evidence['afterHomeActivities']=activities()
    checks['homeButtonDispatch']=responses[-1]['body']['type']=='key'
    button('#open-app','/api/reopen');evidence['afterReopenTexts']=texts()
    checks['appReopensFromBrowser']='두근두근 가는 길' in evidence['afterReopenTexts']
    for action in ['drive','rain_on','rain_off','rear_open','rear_close','left_on','left_off','park']:
        button('[data-vehicle='+action+']','/api/vehicle')
        checks['vehicle_'+action]=responses[-1]['body'].get('action')==action
        if action=='drive':
            page.wait_for_timeout(1000)
            with (ROOT/'qa/native/remote-control-driving.png').open('wb') as f:
                subprocess.run([str(ADB),'-s',json.loads((ROOT/'.tools/run-state.json').read_text())['serial'],'exec-out','screencap','-p'],stdout=f,check=True)
    page.locator('#touch-surface').focus()
    page.locator('#screen').scroll_into_view_if_needed();box=page.locator('#screen').bounding_box()
    page.mouse.move(box['x']+box['width']*.7,box['y']+box['height']*.5)
    with page.expect_response(lambda r:r.url.endswith('/api/input') and r.request.method=='POST') as response:page.mouse.wheel(0,450)
    checks['wheelRequestAccepted']=response.value.ok
    for data in [{'type':'tap','x':-1,'y':.5},{'type':'tap','x':.5,'y':True},{'type':'key','key':'home; id'},{'type':[]},{'type':'swipe','x':0,'y':0,'x2':1,'y2':1,'duration':999999}]:
        response=context.request.post(URL+'/api/input',data=json.dumps(data),headers={'Origin':URL,'Content-Type':'application/json'})
        assert response.status==400
    checks['invalidInputRejected']=True
    checks['foreignOriginRejected']=context.request.post(URL+'/api/input',data={'type':'key','key':'home'},headers={'Origin':'https://example.invalid'}).status==403
    checks['missingOriginRejected']=context.request.post(URL+'/api/input',data={'type':'key','key':'home'}).status==403
    checks['desktopNoOverflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('#open-app').click();page.wait_for_timeout(1000)
    page.screenshot(path=str(ROOT/'qa/native/remote-control-desktop.png'),full_page=True)
    mobile_context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,ignore_https_errors=True)
    page=mobile_context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL,wait_until='domcontentloaded');page.wait_for_timeout(600)
    tap(.92,.16,mobile=True);tap(.542,.95,mobile=True)
    mobile_text=texts();evidence['mobileDrawerTexts']=mobile_text
    checks['mobileTouchOpensActualDrawer']='앱' in mobile_text and '공조' in mobile_text
    tap(.92,.16,mobile=True)
    checks['mobileNoOverflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(ROOT/'qa/native/remote-control-mobile.png'),full_page=True)
    checks['noPageErrors']=not errors
    browser.close()

result={'passed':all(checks.values()),'date':'2026-11-10','url':URL,'checks':checks,'actualAndroidUI':evidence,'responses':responses,'pageErrors':errors,'method':'Actual Chrome mouse/touch/keyboard and visible buttons through same-origin HTTP API into ADB input on the named Pleos emulator, plus whitelisted official virtual-console requests. Android UI and Activity dumps confirm drawer, native settings scroll/navigation and Pli return. Mobile is a touch-enabled Chrome emulation, not a physical phone.'}
(ROOT/'qa/native/tailscale-control.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
assert result['passed']
