#!/usr/bin/env python3
"""Supervise only this project's Pleos runtime, honoring an explicit CLI stop."""
from pathlib import Path
import json, os, re, runpy, signal, subprocess, time
from audio_guard import guard,AudioRouteBusy

ROOT = Path(__file__).resolve().parents[1]
from runtime_context import selected, state_dir,runtime_intent
CONTEXT=selected()
TOOLS = state_dir()
PAUSED = TOOLS / 'runtime-paused'
STATE = TOOLS / 'runtime-status.json'
api = runpy.run_path(str(ROOT / 'scripts/pleos.py'))
running = True
attempt = 0
last_error = None
missing_since = None

# A fresh emulator reports Google's campus in California. The demo car lives in 수원 광교 (near 광교역, the start of
# the demo drive home in android DemoTrip.kt), so the edge weather and place tools answer for the right neighbourhood.
DEMO_POSITION = (float(os.environ.get('PLI_DEMO_LAT', '37.3021')), float(os.environ.get('PLI_DEMO_LON', '127.0444')))
FACTORY_POSITION = (37.421998, -122.084)
placed = set()

def place_vehicle(serial):
    """Once per emulator boot, replace only the factory GPS default; a real or simulated fix is kept."""
    key = (serial, own_emulator())
    if key in placed: return
    try:
        fixes = re.findall(r'Location\[\w+ (-?[\d.]+),(-?[\d.]+)', api['adb_shell'](serial, 'dumpsys', 'location'))
        factory = [f for f in fixes if abs(float(f[0]) - FACTORY_POSITION[0]) < 1e-3 and abs(float(f[1]) - FACTORY_POSITION[1]) < 1e-3]
        if not fixes or factory:
            api['adb'](serial, 'emu', 'geo', 'fix', str(DEMO_POSITION[1]), str(DEMO_POSITION[0]), capture_output=True, timeout=5)
        placed.add(key)
    except (subprocess.SubprocessError, OSError, RuntimeError):
        pass  # retried on the next health tick

def publish(phase, message, serial=None):
    target = STATE.with_suffix('.tmp')
    target.write_text(json.dumps({'phase':phase,'message':message,'serial':serial,'attempt':attempt,'updatedAt':time.time(),'lastError':last_error},ensure_ascii=False))
    target.replace(STATE)

def stop(*_):
    global running
    running = False

def own_emulator():
    path = TOOLS / 'emulator.pid'
    try:
        pid = int(path.read_text())
        args = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
        if b'-avd' in args and args[args.index(b'-avd')+1:args.index(b'-avd')+2] == [CONTEXT.avd_name.encode()]:return pid
    except (OSError,ValueError): pass
    return None

def restore_idle_public_view(serial):
    try:
        control=json.loads((TOOLS/'control-lease.json').read_text())
        if control.get('busy') and control.get('surface')=='pleos' and control.get('expiresAt',0)>time.time():return
    except (OSError,ValueError):pass
    # A cache can still say STOPPED while the owner has started voice. Read the
    # APK again, and let its atomic session guard refuse a racing preview.
    # A view-repair refusal never means that the running process has died.
    try:
        user=api['adb_shell'](serial,'am','get-current-user')
        value=json.loads(api['adb_shell'](serial,'content','read','--user',user,'--uri','content://'+api['PACKAGE']+'.demo/state'))
        if not(TOOLS/'portal-mode').exists()or value.get('sessionStatus')!='STOPPED':return
        if value.get('demo')and value.get('visible')and value.get('hasView'):return
        if not value.get('demo'):api['session_control'](serial,'preview')
        api['adb_shell'](serial,'am','start','--user','current','--activity-single-top','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','-n',api['PACKAGE']+'/.MainActivity')
    except (RuntimeError,subprocess.SubprocessError,OSError,ValueError):
        return

def launch():
    global attempt,last_error
    attempt += 1
    publish('starting','Pleos와 플리를 다시 시작하고 있어요.')
    with (TOOLS/'logs/runtime-recovery.log').open('a') as log:
        log.write('\nRecovery attempt '+str(attempt)+' at '+time.strftime('%F %T')+'\n');log.flush()
        process = subprocess.Popen([str(ROOT/'pleos'),'run','--release','--no-build'],cwd=ROOT,env={**os.environ,'PLI_RUNTIME_AUTOMATIC':'1'},stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+300
        while process.poll() is None:
            publish('starting','Pleos와 플리를 다시 시작하고 있어요.')
            if time.monotonic()>deadline:
                process.kill();process.wait();raise RuntimeError('Pleos launcher timed out')
            time.sleep(2)
    if process.returncode: raise RuntimeError('Pleos launcher exited '+str(process.returncode))
    last_error = None

for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,stop)
publish('checking','시연 환경 연결을 확인하고 있어요.')
while running:
    try:
        if CONTEXT.profile=='public':
            try:
                held=json.loads((TOOLS/'held-pointers.json').read_text());owner=Path('/proc')/str(held.get('serverPid',0))/'cmdline'
                heartbeat=json.loads((TOOLS/'server-heartbeat.json').read_text())
                stale=heartbeat.get('pid')!=held.get('serverPid')or time.time()-heartbeat.get('at',0)>5
                if held.get('pointers') and (stale or not owner.exists() or b'demo-server.py' not in owner.read_bytes()):
                    import asyncio
                    from display_stream import PublicDisplay
                    async def clear_pointers():
                        display=PublicDisplay(CONTEXT);await display.connect();await display.close()
                    asyncio.run(clear_pointers())
            except Exception:pass
        try:guard()
        except AudioRouteBusy:pass  # An owned route mutation is in progress; continue health checks.
        try:transition=float((TOOLS/'runtime-transition').read_text())
        except (OSError,ValueError):transition=0
        if transition>time.time():
            publish('preparing','플리 음성 앱을 준비하고 있어요.');time.sleep(.5);continue
        if runtime_intent(TOOLS)['desiredState']=='paused':
            publish('paused','시연 실행이 중지되어 있어요.');time.sleep(2);continue
        serial = None;boot = None
        try:
            serial = api['device']()
            boot = api['adb_shell'](serial,'getprop','sys.boot_completed')
            if boot != '1':
                publish('starting','Pleos가 부팅되고 있어요.',serial);time.sleep(2);continue
            try:control=json.loads((TOOLS/'control-lease.json').read_text())
            except (OSError,ValueError):control={}
            if CONTEXT.profile=='public' and control.get('busy') and control.get('surface')=='pleos' and control.get('expiresAt',0)>time.time():
                publish('ready','Pleos 전체 화면 조작 중',serial);time.sleep(1);continue
            process = api['adb_shell'](serial,'pidof',api['PACKAGE'])
            if not process: raise RuntimeError('Pli is not running')
            if (TOOLS/'portal-mode').exists():
                try:health=json.loads((TOOLS/'native-health.json').read_text())
                except (OSError,ValueError):health={}
                if time.time()-health.get('at',0)<5 and health.get('pid')==process and health.get('sessionStatus')=='STOPPED' and (health.get('demo') is False or health.get('hasView') is False or health.get('visible') is False):
                    restore_idle_public_view(serial)
            missing_since = None;last_error = None
            place_vehicle(serial)
            publish('ready','기기 부팅·앱 프로세스 확인',serial)
        except (RuntimeError,subprocess.CalledProcessError) as error:
            if runtime_intent(TOOLS)['desiredState']=='paused':continue
            if serial and boot == '1':
                launch();missing_since = None;continue
            # ADB can briefly disappear while a live emulator is still booting.
            pid = own_emulator()
            if pid:
                if missing_since is None:missing_since = time.monotonic()
                if time.monotonic()-missing_since < 90:
                    publish('starting','Pleos 연결을 다시 기다리고 있어요.');time.sleep(2);continue
                os.kill(pid,signal.SIGTERM)
                for _ in range(30):
                    if own_emulator() is None:break
                    time.sleep(.2)
                if own_emulator() == pid:os.kill(pid,signal.SIGKILL)
            launch();missing_since = None
    except Exception as error:
        last_error = str(error)
        publish('error','연결을 복구하지 못해 잠시 뒤 다시 시도해요.')
        time.sleep(8)
    time.sleep(2)
