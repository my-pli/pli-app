"""Real emulator microphone + public console end-to-end test. No text injection.

Run with .tools/qa-venv/bin/python qa/native/voice-journey.py.
Only the emulator's recording stream is temporarily moved to synthetic audio.
"""
from pathlib import Path
import json, os, subprocess, time, urllib.request,threading
import pulsectl

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / '.tools/android-sdk/platform-tools/adb'
SERIAL=json.loads((ROOT/'.tools/run-state.json').read_text())['serial']
REPORT = ROOT / 'qa/native/voice-journey.json'
FIXTURES=ROOT/'qa/native/fixtures'
steps = []

def shell(*args):
    return subprocess.run([str(ADB), '-s', SERIAL, 'shell', *args], capture_output=True, text=True, check=True).stdout

USER = shell('am', 'get-current-user').strip()

def state():
    for _ in range(6):
        try:
            return json.loads(shell('run-as', 'ai.teammoon.pli', '--user', USER, 'cat', 'files/debug-state.json'))
        except json.JSONDecodeError:
            time.sleep(.15)
    raise RuntimeError('No complete debug snapshot')

def wait(predicate, label, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s = state()
        if predicate(s):
            return s
        time.sleep(.25)
    raise AssertionError(f'{label}: {json.dumps(s, ensure_ascii=False)}')

def record(label, s):
    steps.append({'step': label, 'time': time.time(), 'state': s})
    print(json.dumps({'step': label, 'phase': s['phase'], 'game': s['game'], 'heard': s['heard'], 'correct': s['correct'], 'quiet': s['quiet'], 'vehicle': s['vehicle']}, ensure_ascii=False), flush=True)
    REPORT.write_text(json.dumps({'method': 'Synthetic Korean speech played through the actual emulator microphone; Pleos ON_DEVICE recognizer; no text or file ASR command injection', 'passed': False, 'steps': steps}, ensure_ascii=False, indent=2))

def console(path):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8088' + path, data=b'', method='PUT'), timeout=8) as response:
                result = json.loads(response.read())
                if result.get('error'):raise RuntimeError(result)
                return
        except Exception:
            if attempt==5:raise
            time.sleep(.5)

def listen():
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        wait(lambda s: s['phase'] in ['LISTENING', 'QUIET'] and s['modelReady'] and s['ttsReady'], 'ready for next utterance', 45)
        time.sleep(1.1)
        if state()['phase'] in ['LISTENING','QUIET']:return
    raise AssertionError('No stable listening window')

def play(name, while_speaking=False):
    if not while_speaking:
        listen()
    env = os.environ.copy()
    env['PULSE_SERVER'] = 'unix:/run/user/1000/pulse/native'
    padded=ROOT/'.tools'/('qa-padded-'+name+'.wav')
    subprocess.run(['ffmpeg','-y','-nostdin','-loglevel','error','-i',str(FIXTURES/(name+'.wav')),'-af','adelay=800:all=1,apad=pad_dur=3','-ar','44100','-ac','2',str(padded)],check=True)
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-re', '-i', str(padded), '-f', 'pulse', '-device', 'pli_journey_mic', 'Pli synthetic microphone test'], env=env, check=True)

baseline = wait(lambda s:s['game']=='FRIEND' and s['answered']==0 and not s['quiet'] and s['modelReady'] and s['ttsReady'] and s['vehicle']['connected'], 'fresh companion session')
try:
    backup = shell('run-as', 'ai.teammoon.pli', '--user', USER, 'cat', 'files/pli-data.json')
except subprocess.CalledProcessError:
    backup = 'null'
(ROOT / '.tools/qa-before-journey.json').write_text(backup)
with pulsectl.Pulse('pli-voice-journey-test', server='unix:/run/user/1000/pulse/native') as pulse:
    streams = [s for s in pulse.source_output_list() if s.proplist.get('application.name') == 'qemu-system-x86_64']
    assert len(streams) == 1, 'A single Pleos emulator microphone is required'
    stream = streams[0]
    previous = stream.source
    originals={stream.index:previous};route_changes=[]
    module = pulse.module_load('module-null-sink', 'sink_name=pli_journey_mic rate=44100 channels=2 sink_properties=device.description=PliVoiceJourneyTest')
    monitor = next(s for s in pulse.source_list() if s.name == 'pli_journey_mic.monitor')
    routing_done=threading.Event()
    def maintain_route():
        with pulsectl.Pulse('pli-qa-microphone-route',server='unix:/run/user/1000/pulse/native') as router:
            while not routing_done.is_set():
                for current in router.source_output_list():
                    if current.proplist.get('application.process.id')==stream.proplist.get('application.process.id') and current.source!=monitor.index:
                        originals.setdefault(current.index,current.source)
                        router.source_output_move(current.index,monitor.index)
                        route_changes.append({'stream':current.index,'previousSource':current.source,'testSource':monitor.index,'time':time.time()})
                routing_done.wait(.1)
    route_thread=threading.Thread(target=maintain_route,daemon=True);route_thread.start()
    audio_env=os.environ.copy();audio_env['PULSE_SERVER']='unix:/run/user/1000/pulse/native'
    carrier=subprocess.Popen(['ffmpeg','-nostdin','-loglevel','error','-re','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-f','pulse','-device','pli_journey_mic','Pli QA silent microphone carrier'],env=audio_env)
    try:
        pulse.source_output_move(stream.index, monitor.index)
        console('/vehicle/controls?speed=0&accelerator=0&brake=0&steering=0')
        console('/vehicle/gear?gear=Park')
        wait(lambda s:s['vehicle']['gear']=='P' and s['vehicle'].get('speedKmh',-1)<1, 'repeatable emulator baseline')
        console('/vehicle/odometer?traveled_distance_km=100')
        console('/vehicle/ev-battery?field=soc&value=73')
        wait(lambda s: s['vehicle'].get('odometerKm', 0) >= 100, 'baseline odometer before departure')
        console('/vehicle/gear?gear=Drive')
        console('/vehicle/controls?speed=32&accelerator=10&brake=0&steering=0')
        s = wait(lambda s: s['vehicle'].get('gear') == 'D' and abs(s['vehicle'].get('speedKmh', 0) - 32) < 1 and s['vehicle'].get('battery') == 73 and s['vehicle'].get('odometerKm', 0) >= 100, 'real SDK vehicle readback')
        assert s['vehicle']['uxRestricted'] and s['tripActive']
        record('Real Pleos SDK reads D / 32 km/h / 73% battery / odometer', s)
        play('math-command')
        s = wait(lambda s: s['game'] == 'MATH' and s.get('question', {}).get('answer') == '6', 'voice starts math')
        record('Microphone: start mental arithmetic while driving', s)
        subprocess.run([str(ROOT / 'pleos'), 'screenshot', str(ROOT / 'qa/native/driving-math.png')], check=True, capture_output=True)
        play('answer-six')
        s = wait(lambda s: s['answered'] == 1 and s['correct'] == 1, 'spoken answer six')
        record('Microphone: correct spoken arithmetic answer', s)
        play('english-command')
        s = wait(lambda s: s['game'] == 'ENGLISH', 'voice switches to English')
        record('Microphone: switch to English without parking', s)
        play('answer-apple')
        s = wait(lambda s: s['answered'] == 2 and s['correct'] == 2 and s['phase'] == 'SPEAKING', 'spoken answer apple')
        record('Microphone: correct spoken English answer', s)
        began = time.monotonic()
        play('hush', while_speaking=True)
        s = wait(lambda s: s['quiet'] and s['phase'] == 'QUIET', 'interrupt speech with hush', 12)
        record('Microphone: hush interrupts speech', s)
        steps[-1]['clip_start_to_quiet_seconds'] = round(time.monotonic() - began, 3)
        subprocess.run([str(ROOT / 'pleos'), 'screenshot', str(ROOT / 'qa/native/quiet.png')], check=True, capture_output=True)
        time.sleep(4)
        assert state()['quiet'], 'Quiet must persist'
        play('resume')
        s = wait(lambda s: not s['quiet'] and s.get('question', {}).get('answer') == 'tree', 'resume advances completed question')
        record('Microphone: explicitly resume after quiet', s)
        play('schedule')
        s = wait(lambda s: '숲' in s['speech'] and s['heard'] != '다시 놀자', 'voice reads schedule')
        record('Microphone: read today plan while moving', s)
        console('/vehicle/odometer?traveled_distance_km=104')
        wait(lambda s: abs(s['vehicle'].get('odometerKm', 0) - 104) < .1, 'odometer changes via real Vehicle SDK')
        play('arrive')
        s = wait(lambda s: len(s['memories']) == len(baseline['memories']) + 1 and not s['tripActive'], 'arrival persists memory')
        record('Microphone: arrival saves a trip without a parking gate', s)
        assert s['vehicle']['gear'] == 'D' and s['vehicle']['speedKmh'] > 30
        assert abs(s['memories'][0]['kilometers'] - 4) < .1
        REPORT.write_text(json.dumps({'method': 'Synthetic Korean speech through actual emulator microphone and native Pleos ON_DEVICE speech recognition and TTS; public console -> DDS -> VHAL -> native Vehicle SDK readback; no app command injection', 'passed': True, 'steps': steps,'microphoneRoutes':route_changes}, ensure_ascii=False, indent=2))
        print('PASS: complete voice journey at D / 32 km/h', flush=True)
    finally:
        routing_done.set();route_thread.join(timeout=3)
        carrier.terminate()
        carrier.wait(timeout=5)
        for current in pulse.source_output_list():
            if current.index in originals:
                pulse.source_output_move(current.index, originals[current.index])
        pulse.module_unload(module)
        try:
            console('/vehicle/controls?speed=0&accelerator=0&brake=0&steering=0')
            console('/vehicle/gear?gear=Park')
        except Exception as error:
            print(f'Console cleanup unavailable: {error}', flush=True)
