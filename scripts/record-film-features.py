#!/usr/bin/env python3
"""Record real Pli feature takes on the isolated public Pleos emulator for the product film.

Each take opens a public voice session in Chrome, plays the film's own cast
lines (scripts/film_voice.py WAVs) into the session microphone, and records the
emulator display host-side (`adb emu screenrecord`) at native size. The app hears and
answers for real; every state change (heard text, spoken answer, playback) is
logged with wall-clock times next to the clip so the edit can place captions on
what the app actually said. Public profile only: no private family session.

Run with system python3 (Playwright); voices are synthesized with .tools/film-venv.
"""
from pathlib import Path
import argparse
import os, base64, json, os, re, signal, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from edge_games import VOCAB, first_options  # noqa: E402

TAKES = ROOT / 'media/pli-film/app-takes.json'
OUT = ROOT / '.tools/product-film/app-takes'
ADB = ROOT / '.tools/android-sdk/platform-tools/adb'
FILM_PYTHON = ROOT / '.tools/film-venv/bin/python'
GRAB_PYTHON = ROOT / '.tools/demo-venv/bin/python'
REGION = [0, 0, 2560, 1440]  # the whole Pleos display: vehicle view on the left, Pli on the right (x, y, w, h)
SERIAL = 'emulator-5556'  # Pli_Pleos_Demo, the public AVD
APP_SPEAKER = 'pli_remote_speaker_public.monitor'  # where the public emulator's voice goes
ENV = {**os.environ, 'ANDROID_USER_HOME': str(ROOT / '.tools/android-user')}
# An edge-agent answer replaces `speech` after a spoken filler without changing `requestedText`,
# so "finished" is only: listening, idle, and no new speech for a while (see settle()).
LISTENING = ("state.status.app.recognition==='READY' && state.status.app.phase==='LISTENING' && "
             "state.status.app.playback==='IDLE'")
PLAY = '''async b64=>{const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const voice=await ctx.decodeAudioData(bytes.buffer);
const lead=Math.round(0.3*voice.sampleRate);const audio=ctx.createBuffer(voice.numberOfChannels,voice.length+lead,voice.sampleRate);
for(let c=0;c<voice.numberOfChannels;c++){const d=audio.getChannelData(c);for(let i=0;i<lead;i++)d[i]=(Math.random()-0.5)*0.004;d.set(voice.getChannelData(c),lead);}
const s=ctx.createBufferSource();s.buffer=audio;s.connect(filter);window.filmPlayed=window.filmPlayed||[];
window.filmPlayed.push(Date.now()+300);await new Promise(r=>{s.onended=r;s.start()});}'''
LOGGER = '''()=>{window.filmLog=[];let last='';window.filmTimer=setInterval(()=>{const a=state.status.app||{};
const row={heard:a.heard,speech:a.speech,playback:a.playback,phase:a.phase,title:a.title,seq:a.spokenSequence,quiet:a.quiet,game:a.game,panel:a.panel};
const key=JSON.stringify(row);if(key!==last){last=key;filmLog.push({at:Date.now(),...row})}},50)}'''


def adb(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(ADB), '-s', SERIAL, *args], env=ENV, **kw)


def set_clock(when: str | None) -> None:
    """Fix the emulator's clock for the story (e.g. '2026-11-17 17:30' = a weekday drive home), or give
    it back to network time (None). The shell user holds SET_TIME on the Pleos emulator."""
    if when is None:
        adb('shell', 'cmd', 'time_detector', 'set_auto_detection_enabled', 'true', check=True)
        return
    epoch_ms = int(time.mktime(time.strptime(when, '%Y-%m-%d %H:%M')) * 1000)
    adb('shell', 'cmd', 'time_detector', 'set_auto_detection_enabled', 'false', check=True)
    adb('shell', 'cmd', 'alarm', 'set-time', str(epoch_ms), check=True)
    shown = adb('shell', 'date', '+%Y-%m-%d %H:%M %a', capture_output=True, text=True).stdout.strip()
    print(json.dumps({'clock': shown}), flush=True)


def set_night(on: bool | None) -> str:
    """Pleos day/night UI mode for the takes (the story's 17:30 November drive is after sunset, so the vehicle
    view should be dark like Pli's screen); returns the mode it replaced so it can be given back."""
    before = adb('shell', 'cmd', 'uimode', 'night', capture_output=True, text=True).stdout.strip().split(':')[-1].strip()
    if on is not None:
        adb('shell', 'cmd', 'uimode', 'night', 'yes' if on else 'no', check=True)
    return before


def synthesize(lines: list) -> dict:
    out = subprocess.check_output([str(FILM_PYTHON), str(ROOT / 'scripts/film_voice.py'), json.dumps(lines, ensure_ascii=False)])
    return {key: Path(path) for key, path in json.loads(out).items()}


def chain_reply(speech: str) -> str | None:
    """A child's word-chain answer to Pli's opening word, from the vocabulary the engine checks."""
    match = re.search(r"'(.)' 자로 시작", speech or '')
    if not match:
        return None
    options = sorted(w for w in VOCAB if w[0] in first_options(match.group(1)) and 2 <= len(w) <= 3)
    return [w + '!' for w in options[:3]] if options else None


NATIVE = ['영', '하나', '둘', '셋', '넷', '다섯', '여섯', '일곱', '여덟', '아홉', '열', '열하나', '열둘', '열셋', '열넷',
          '열다섯', '열여섯', '열일곱', '열여덟', '열아홉', '스물']


def math_reply(speech: str) -> str | None:
    """'3 더하기 5 빼기 2 는?' -> '정답은 여섯!' (a full sentence survives the live microphone path)."""
    tokens = re.findall(r'\d+|더하기|빼기', speech or '')
    if not tokens or not tokens[0].isdigit():
        return None
    total, sign = int(tokens[0]), 1
    for token in tokens[1:]:
        if token == '더하기':
            sign = 1
        elif token == '빼기':
            sign = -1
        else:
            total += sign * int(token)
    return [f'{NATIVE[total]}!', f'정답은 {NATIVE[total]}!', f'{NATIVE[total]} 개!'] if 0 <= total < len(NATIVE) else None


def english_reply(speech: str) -> str | None:
    """'나무는 영어로 뭘까?' -> the catalog's Korean pronunciation ('트리!'), as the app accepts it."""
    catalog = (ROOT / 'android/app/src/main/java/ai/teammoon/pli/domain/LearningCatalog.kt').read_text()
    words = {ko: pron for ko, _en, pron in re.findall(r'Word\("([^"]+)","([^"]+)","([^"]+)"', catalog)}
    match = re.match(r'(\S+?)(?:은|는) 영어로', speech or '')
    if not match or match.group(1) not in words:
        return None
    english = {ko: en for ko, en, _pron in re.findall(r'Word\("([^"]+)","([^"]+)","([^"]+)"', catalog)}[match.group(1)]
    return ['정답은 ' + words[match.group(1)] + '!', '정답은 ' + english + '!', english + '!']


REPLIES = {'wordchain': chain_reply, 'math': math_reply, 'english': english_reply}


class Session:
    def __init__(self, page, url: str):
        self.v, self.url = page, url

    def start(self) -> None:
        v = self.v
        v.goto(self.url + '/app')
        v.wait_for_function("state.media==='LIVE' && state.status.controlReady && !state.status.lease.busy", timeout=90000)
        v.locator('#connect').click()
        v.wait_for_function('state.voice', timeout=45000)
        settle(self)  # the greeting is spoken first
        v.evaluate('source.disconnect(filter)')

    def ready(self) -> None:
        self.v.wait_for_function(LISTENING, timeout=40000)

    def say(self, wav: Path) -> int:
        before = self.v.evaluate('state.status.app.spokenSequence')
        self.v.evaluate(PLAY, base64.b64encode(wav.read_bytes()).decode())
        return before

    def stop(self) -> None:
        v = self.v
        try:
            if v.evaluate('state.voice'):
                v.evaluate('endSession()')
            v.wait_for_function('!state.ending && !state.status.lease.busy && !state.status.voiceBusy', timeout=20000)
        except Exception as error:  # cleanup is reported, never hidden
            print(json.dumps({'cleanupError': type(error).__name__}), flush=True)


def scene_voices(takes: list) -> dict:
    """Lines spoken in a generated scene (`audio`: the scene's clip) are played to the app from that
    clip's own sound, so the film shows one voice: the one generated with the picture."""
    made = {}
    for take in takes:
        for turn in take['turns']:
            if turn.get('audio'):
                target = OUT / 'voice' / f"{turn['id']}.wav"
                target.parent.mkdir(parents=True, exist_ok=True)
                span = (['-ss', str(turn['from'])] if turn.get('from') else []) + (['-to', str(turn['to'])] if turn.get('to') else [])
                subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *span, '-i', str(ROOT / turn['audio']), '-vn',
                                '-af', 'afade=t=in:d=0.05,areverse,afade=t=in:d=0.2,areverse', '-ac', '2', '-ar', '48000', str(target)],
                               check=True)
                made[turn['id']] = target
    return made


def start_app_sound(target: Path) -> tuple:
    """Record what the app actually says: the public emulator's speaker sink, stamped on the wall clock."""
    env = {**os.environ, 'PULSE_SERVER': f'unix:/run/user/{os.getuid()}/pulse/native'}
    process = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'pulse', '-i', APP_SPEAKER,
                                '-ac', '2', '-ar', '48000', str(target)], env=env, stdin=subprocess.PIPE)
    return process, time.time()


def stop_app_sound(process: subprocess.Popen) -> None:
    try:
        process.communicate(b'q', timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def start_recorder(target: Path) -> subprocess.Popen:
    """30 fps native-pixel grab of the Pli window over the emulator's gRPC stream (scripts/film_grab.py)."""
    target.unlink(missing_ok=True)
    grabber = subprocess.Popen([str(GRAB_PYTHON), str(ROOT / 'scripts/film_grab.py'), str(target), ','.join(map(str, REGION)),
                                os.environ.get('PLI_FILM_STREAM', '1600x900')],  # v8: 2560x1440 for the vertical close-ups
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = grabber.stdout.readline()  # {"ready": epoch} once the first frame arrived
    if not line.startswith('{"ready"'):
        grabber.kill()
        raise RuntimeError('film_grab did not start: ' + (line + grabber.stderr.read())[:300])
    return grabber


def stop_recorder(grabber: subprocess.Popen) -> dict:
    grabber.send_signal(signal.SIGINT)
    try:
        out, err = grabber.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        grabber.kill()  # 2026-11-15: a grab left running after this timeout kept streaming 2560x1440 into NVENC for minutes
        grabber.communicate()
        raise
    if grabber.returncode != 0:
        raise RuntimeError('film_grab failed: ' + err[-300:])
    return json.loads(out.strip().splitlines()[-1])


def settle(session: Session, quiet_seconds: float = 2.5) -> None:
    """The agent may speak a filler before its answer: wait until it is listening and silent."""
    v, seq, since, until = session.v, None, time.monotonic(), time.monotonic() + 60
    while time.monotonic() < until:
        current = v.evaluate('state.status.app.spokenSequence')
        listening = v.evaluate(LISTENING)
        if current != seq or not listening:
            seq, since = current, time.monotonic()
        elif time.monotonic() - since >= quiet_seconds:
            return
        time.sleep(0.2)
    raise RuntimeError('Pli did not finish answering')


def play_turns(session: Session, take: dict, voices: dict, started: float) -> tuple:
    v, turns, spoken = session.v, [], []
    for turn in take['turns']:
        if turn.get('adaptive'):  # the child answers what Pli actually asked, retrying other words if unheard
            heard = v.evaluate('state.status.app.speech')
            replies = REPLIES[turn['adaptive']](heard)
            if not replies:
                raise RuntimeError(f"{take['id']}: no {turn['adaptive']} answer for {heard!r}")
            for attempt, reply in enumerate(replies):
                line = {'id': f"{turn['id']}-{attempt}", 'speaker': turn['speaker'], 'text': reply}
                voices.update(synthesize([line]))
                session.ready()
                time.sleep(0.35)
                score = v.evaluate('[state.status.app.correct, state.status.app.game]')
                before = session.say(voices[line['id']])
                turns.append({'id': line['id'], 'speaker': turn['speaker'], 'text': reply,
                              'playedAt': round(v.evaluate('filmPlayed[filmPlayed.length-1]') / 1000 - started, 3)})
                v.wait_for_function(f"state.status.app.spokenSequence>{before} && state.status.app.playback==='IDLE'", timeout=60000)
                settle(session, turn.get('settle', take.get('settle', 2.5)))
                spoken.append(v.evaluate('state.status.app.speech'))
                now = v.evaluate('[state.status.app.correct, state.status.app.game, state.status.app.speech]')
                accepted = now[0] > score[0] if turn['adaptive'] != 'wordchain' else ('자로 시작하는 말' in now[2] or '승리' in now[2])
                if accepted:
                    break
            else:
                raise RuntimeError(f"{take['id']}: Pli did not accept any of {replies}")
            continue
        if turn.get('vehicle'):  # a vehicle signal changes during the take (e.g. the car starts driving)
            v.evaluate("a=>post('/api/vehicle',{action:a})", turn['vehicle'])
            turns.append({'id': turn['id'], 'speaker': '', 'text': '', 'vehicle': turn['vehicle'], 'playedAt': round(time.time() - started, 3)})
            time.sleep(turn.get('pause', 1.0))
            continue
        if turn.get('wait'):  # Pli speaks first (proactive offer): wait for it and let it finish
            v.wait_for_function(turn['until'], timeout=turn.get('timeout', 90) * 1000)
            turns.append({'id': turn['id'], 'speaker': '플리', 'text': '', 'playedAt': round(time.time() - started, 3)})
            settle(session, turn.get('settle', take.get('settle', 2.5)))
            spoken.append(v.evaluate('state.status.app.speech'))
            continue
        if not turn.get('interrupt'):
            session.ready()
            time.sleep(0.35)
        before = session.say(voices[turn['id']])
        turns.append({'id': turn['id'], 'speaker': turn['speaker'], 'text': turn['text'],
                      'playedAt': round(v.evaluate('filmPlayed[filmPlayed.length-1]') / 1000 - started, 3)})
        if turn.get('cutIn') is not None:  # the next turn interrupts while Pli is still speaking
            v.wait_for_function(f"state.status.app.spokenSequence>{before} && state.status.app.playback!=='IDLE'", timeout=30000)
            time.sleep(turn['cutIn'])
            continue
        v.wait_for_function(turn.get('until') or f"state.status.app.spokenSequence>{before} && state.status.app.playback==='IDLE'",
                            timeout=60000)
        if not turn.get('until'):
            settle(session, turn.get('settle', take.get('settle', 2.5)))  # tool calls pause longer
        spoken.append(v.evaluate('state.status.app.speech'))
    return turns, spoken


def record_take(session: Session, take: dict, voices: dict) -> dict:
    v = session.v
    clip, log = OUT / f"{take['id']}.mp4", OUT / f"{take['id']}.json"
    if take.get('vehicle'):
        v.evaluate("a=>post('/api/vehicle',{action:a})", take['vehicle'])
        time.sleep(1.5)
    session.ready()
    v.evaluate(LOGGER)
    sound, sound_started = start_app_sound(OUT / f"{take['id']}.wav")
    grabber = start_recorder(clip)
    grab = {}
    try:
        started = time.time()
        time.sleep(take.get('lead', 1.2))
        turns, spoken = play_turns(session, take, voices, started)
        time.sleep(take.get('tail', 1.0))
    finally:
        try:
            grab = stop_recorder(grabber)
        finally:  # 2026-11-15: when the grab's stop timed out the sound recorder was never stopped and kept writing for hours
            stop_app_sound(sound)
            v.evaluate('clearInterval(filmTimer)')
    offset = grab['startedAt'] - started  # clip time = log time - offset (frames carry wall-clock stamps)
    turns = [{**t, 'clipAt': round(t['playedAt'] - offset, 3)} for t in turns]
    events = [{**row, 'at': round(row['at'] / 1000 - started, 3), 'clipAt': round(row['at'] / 1000 - grab['startedAt'], 3)}
              for row in v.evaluate('filmLog')]
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                                                'stream=width,height,nb_read_frames:format=duration', '-of', 'json', str(clip)]))
    record = {'take': take['id'], 'recordedAt': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'serial': SERIAL,
              'profile': 'public', 'region': grab['region'], 'grab': grab, 'turns': turns, 'spoken': spoken,
              'appSound': {'file': f"{take['id']}.wav", 'clipOffset': round(sound_started - grab['startedAt'], 3)},  # wav time = clip time - clipOffset
              'clock': adb('shell', 'date', '+%Y-%m-%d %H:%M %a', capture_output=True, text=True).stdout.strip(),
              'voiceJournal': '.tools/product-film/voice-journal/journal.jsonl',  # Pli's original sentences (edge voice server)
              'events': events, 'video': probe}
    log.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='comma separated take ids')
    parser.add_argument('--clock', help="emulator clock for the takes, e.g. '2026-11-17 17:30' (restored afterwards)")
    parser.add_argument('--night', action='store_true', help='record in the dark (night) UI mode, restored afterwards')
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright
    spec = json.loads(TAKES.read_text())
    wanted = set(args.only.split(',')) if args.only else None
    takes = [t for t in spec['takes'] if wanted is None or t['id'] in wanted]
    voices = synthesize([{'id': turn['id'], 'speaker': turn['speaker'], 'text': turn['text']}
                         for take in takes for turn in take['turns'] if not turn.get('adaptive') and not turn.get('audio') and not turn.get('wait') and not turn.get('vehicle')])
    voices.update(scene_voices(takes))
    OUT.mkdir(parents=True, exist_ok=True)
    url = json.loads((ROOT / '.tools/public-config.json').read_text())['url']
    failures = {}
    if args.clock:
        set_clock(args.clock)
    night_before = set_night(True) if args.night else None
    try:
        failures = record_all(takes, voices, url)
    finally:
        if args.clock:
            set_clock(None)
        if night_before is not None:
            set_night(night_before == 'yes')
    return 1 if failures else 0


def record_all(takes: list, voices: dict, url: str) -> dict:
    from playwright.sync_api import sync_playwright
    failures = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel='chrome', args=[
            '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--autoplay-policy=no-user-gesture-required',
            '--use-file-for-fake-audio-capture=' + str(ROOT / 'qa/native/fixtures/silence.wav')])
        context = browser.new_context(permissions=['microphone'], viewport={'width': 1440, 'height': 1000})
        for take in takes:
            session = Session(context.new_page(), url)
            try:
                session.start()
                record = record_take(session, take, voices)
                print(json.dumps({'take': take['id'], 'spoken': record['spoken'],
                                  'seconds': record['video']['format']['duration']}, ensure_ascii=False), flush=True)
            except Exception as error:
                failures[take['id']] = type(error).__name__ + ': ' + str(error)[:300]
                try:
                    observed = session.v.evaluate("({voice:state.voice,media:state.media,app:state.status.app,lease:state.status.lease})")
                    app = observed.get('app') or {}
                    observed['app'] = {k: app.get(k) for k in ('sessionStatus', 'phase', 'recognition', 'playback', 'heard', 'speech',
                                                               'requestedText', 'title', 'quiet', 'game', 'error', 'spokenSequence')}
                except Exception as probe_error:
                    observed = {'unavailable': type(probe_error).__name__}
                print(json.dumps({'take': take['id'], 'failed': failures[take['id']], 'observed': observed}, ensure_ascii=False), flush=True)
            finally:
                if take.get('vehicle') or any(t.get('vehicle') for t in take['turns']):  # leave the public car parked
                    try:
                        session.v.evaluate("()=>post('/api/vehicle',{action:'park'})")
                    except Exception as error:
                        print(json.dumps({'parkError': type(error).__name__}), flush=True)
                session.stop()
                session.v.close()
        browser.close()
    return failures


if __name__ == '__main__':
    raise SystemExit(main())
