#!/usr/bin/env python3
"""Write media/pli-film/production.json (v7, a vertical 1080x1920 short) from what was actually said, so no cut
lands inside a word.

v7 (2026-11-14 review of v6): vertical; the family scenes are 9:16 windows of the same Weave clips (no new
generation: "위브를쓰지말고 수행"); the new-car scene keeps only the child's line; the album request starts after
"플리야" (heard as 풀리) and is framed on the mother alone (the child's posture beside her looked wrong) and graded to the
story's dusk; the ending is the mother's question heard by the app and the app adding the stop, instead of the sunlit
scene where she turns to the back seat while driving. App cuts are the whole Pleos display as a band.

Family scenes are the Figma Weave clips (.tools/product-film/weave/*.mp4, each with a provenance .json);
their speech is located by the local Whisper word times plus 10 ms energy, and each scene is cut only
after its last word has ended (out = end of speech + 0.4 s, never past the clip). Pli's lines are what
the app played (the take's recorded sound: digital silence between sentences, a transparent path within
about 1 dB of the synthesized original, measured 2026-11-14 with scripts/film_clean_voice.py); sentences
are found from that silence and matched to the app's own text, and an app cut always holds whole sentences. Captions use the words actually spoken (Whisper for the
cast, the synthesized text for Pli), with only the two names normalized (풀리→플리, 하현→하연).
If the film would pass 60 s, whole scenes are dropped (OPTIONAL, in order); words never are.

usage: .tools/edge-venv/bin/python scripts/plan-product-film.py
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_speech  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'media/pli-film/production.json'
# v10 (2026-11-15, "가로버전 세로버전 둘다 만들어줘"): the same edit in two shapes. PLI_FILM_VARIANT=landscape writes
# production-landscape.json (1920x1080) from the same app takes and lines; the default is the vertical 1080x1920 short.
VARIANT = os.environ.get('PLI_FILM_VARIANT', 'vertical')
LANDSCAPE = VARIANT == 'landscape'
PLAN_OUT = ROOT / 'media/pli-film/production-landscape.json' if LANDSCAPE else PLAN
WEAVE = ROOT / '.tools/product-film/weave'
TAKES = ROOT / '.tools/product-film/app-takes'
APP_TAKES = ROOT / 'media/pli-film/app-takes.json'
FPS = 30
TAIL, LEAD = 0.4, 0.35            # seconds kept after the last word / before the first
FORMAT = {'width': 1920, 'height': 1080} if LANDSCAPE else {'width': 1080, 'height': 1920}
BAND_Y = 600                      # the app display band (1080x608) in the vertical frame
LABEL_X, LABEL_Y = 48, 330        # feature labels above the band (and over the family scenes)
APP_CAPTION_TOP = 1290            # app cuts: captions hang from here, under the band and the footage tag
MAX_SECONDS = 60.0
MID_ANSWER = 0.05                 # lead where a cut starts between two sentences of one answer (model pause 0.25-0.45 s)
MID_TAIL = 0.05                   # tail where a cut ends between two sentences: the -55 dB end already holds the word's decay
NAMES = [('풀리', '플리'), ('플이', '플리'), ('하현', '하연'), ('화연', '하연')]
SCENES = {  # clip: (look, [(speaker, script line)], (start, end) of the clip that is used)
    # the child's whine only: the clip ends while the mother is still saying "하연아" (-20 dB at its last frame) and
    # "참아" runs into it with no pause, so her answer cannot end cleanly
    'whine-seed': ('before', [('하연', '엄마아, 심심해! 언제 도착해?'), ('엄마', '조금만 참아, 하연아.')], (0.0, 5.95)),
    'newcar-seed': ('after', [('하연', '우와, 우리 새 차다!')], (0.0, 2.6)),  # v6 ran 5.9 s ("굳이 그렇게 길게 할 필요가 없고")
    'ask-pack-seed-noface': ('after', [('하연', '플리야, 내일 뭐 챙겨?')], (0.0, 4.2)),
    'momalbum-seed': ('dusk', [('엄마', '하연이 사진으로 앨범 만들어 줄래?')], (2.6, 5.0)),
    'gothere-seed': ('after', [('엄마', '하연아, 거기 가 볼까?')], (0.6, 2.6)),
}
ANSWERS = {  # app cut -> (take, turn whose family line it answers): the wait between them is cut out and labelled
    'pack-answer': ('pack', 'q-pack'), 'album-reply': ('album', 'q-album-mom'), 'stop-reply': ('stop', 'm-go'),
}
PUNCH = {  # zoom and centre (share of the 1600x900 stream) of the closer look in an app cut
    'card': {'zoom': 1.45, 'cx': 0.64, 'cy': 0.45},   # Pli's answer card and checklist, the mascot at its left
    'photo': {'zoom': 1.3, 'cx': 0.59, 'cy': 0.5},    # the album page: the photo and its caption
}
CROPS = {  # 9:16 windows (x, y, w, h) of the 1920x1080 Weave frames, chosen by eye on contact sheets
    'whine-child': [0, 0, 608, 1080], 'whine-mom': [650, 0, 608, 1080], 'newcar': [1150, 0, 608, 1080],
    'askpack': [0, 0, 608, 1080], 'momalbum': [190, 0, 608, 1080],
}
FEATURES = [('01', '내일 챙길 것', '어린이집 일정과 날씨를 읽고 챙길 것만'),
            ('02', '엄마가 부탁한 앨범', '하연이 얼굴만 골라 이야기로'),
            ('03', '가는 길에 들를 곳', '경로·시간·운영시간·하연이 취향으로 먼저 제안')]
OPTIONAL = ['album-page']  # dropped if the film runs long


def normalize(text: str) -> str:
    for wrong, right in NAMES:
        text = text.replace(wrong, right)
    return text.strip()


def jamo_similarity(a: str, b: str) -> float:
    import difflib
    keep = lambda t: re.sub(r'[^가-힣]', '', t)  # noqa: E731
    return difflib.SequenceMatcher(None, keep(a), keep(b)).ratio()


def scene_speech(clip: str, lines: list, window: tuple) -> dict:
    """Spoken lines of a Weave clip inside `window`: [(speaker, text heard, start, end)], speech start/end (clip seconds)."""
    path = WEAVE / f'{clip}.mp4'
    a, b = window
    transcript = film_speech.transcribe(path, a, b)
    words = transcript['words']  # already seconds in the file
    db, floor, loud = film_speech.speech_level(path, a, b)
    voiced = [a + i * 0.01 for i, v in enumerate(db) if v > (floor + loud) / 2]
    start = min(words[0]['start'] if words else 0.0, voiced[0] if voiced else 0.0)
    end = max(words[-1]['end'] if words else 0.0, voiced[-1] + 0.01 if voiced else 0.0)
    if len(lines) == 1:
        groups = [words]
    else:  # split the words where the two script lines match best
        best = max(range(1, len(words)), key=lambda k: jamo_similarity(' '.join(w['w'] for w in words[:k]), lines[0][1])
                   + jamo_similarity(' '.join(w['w'] for w in words[k:]), lines[1][1]))
        groups = [words[:best], words[best:]]
    spoken = []
    for (speaker, script), group in zip(lines, groups):
        if group:
            heard = normalize(' '.join(w['w'] for w in group))
            # the script's punctuation when the words match it (>= 0.9), otherwise exactly what was heard
            text = script if jamo_similarity(heard, script) >= 0.9 else heard
            spoken.append({'speaker': speaker, 'text': text, 'heard': heard, 'script': script, 'start': group[0]['start'],
                           'end': group[-1]['end'], 'match': round(jamo_similarity(heard, script), 2)})
    return {'lines': spoken, 'start': round(start, 2), 'end': round(end, 2), 'duration': film_speech.audio(path).size / film_speech.RATE,
            'whisper': transcript['whisper'], 'sensevoice': transcript['sensevoice']}


JOURNAL = ROOT / '.tools/product-film/voice-journal/journal.jsonl'
APP_EQ = 'treble=g=1.5:f=8000'  # the capture path is about 1-2 dB low above 8 kHz (measured against the originals)


def voice_track(name: str) -> tuple:
    """Pli's sound for a take: the edge server's original answers placed where the app played them
    (scripts/film_clean_voice.py, <take>-clean.wav: the emulator's virtual speaker drops 5-180 ms under host load),
    or the speaker re-recording with its small treble loss corrected when no journal was kept."""
    clean = TAKES / f'{name}-clean.wav'
    return (clean, None) if clean.is_file() and clean.stat().st_mtime >= (TAKES / f'{name}.wav').stat().st_mtime else (TAKES / f'{name}.wav', APP_EQ)


def record_of(name: str) -> dict:
    return json.loads((TAKES / f'{name}.json').read_text())


def voiced_segments(name: str) -> list:
    """(start, end) wav seconds of sound in a take. Since v7 the edge voice makes a whole answer in one pass, so
    sentences are separated by the model's own pauses (quiet, not digital silence): -55 dB splits them."""
    db, _floor, _loud = film_speech.speech_level(voice_track(name)[0])
    spans, start = [], None
    for i, value in enumerate(db):
        if value > -45 and start is None:  # v8: every pause is a candidate (-45 dB, 60 ms); answer_sentences picks the sentence ends
            start = i
        if value <= -45 and start is not None:
            spans.append([start * 0.01, i * 0.01])
            start = None
    if start is not None:
        spans.append([start * 0.01, len(db) * 0.01])
    merged = []
    for a, b in spans:
        if merged and a - merged[-1][1] < 0.06:  # bridge stop consonants only
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(round(a, 2), round(b, 2)) for a, b in merged if b - a >= 0.1]


def split_sentences(text: str) -> list:
    return [x.strip() for x in re.split(r'(?<=[.!?])\s+', text or '') if x.strip()]


def expected_seconds(text: str) -> float:
    """Length of the sentence as the voice server made it (journal), or a reading-speed estimate."""
    best, score = None, 0.0
    for line in JOURNAL.read_text().splitlines():
        entry = json.loads(line)
        ratio = difflib.SequenceMatcher(None, entry['text'], text).ratio()
        if ratio > score:
            best, score = entry, ratio
    if best and score > 0.7:
        import wave
        with wave.open(str(JOURNAL.parent / best['file'])) as w:
            return w.getnframes() / w.getframerate()
    return 0.11 * len(re.sub(r'\s', '', text))


def sentences(name: str, texts: list, after: float, before: float = 1e9) -> list:
    """The take's sound segments between two clip times, grouped into the given sentences (in order) so each
    group's span best matches the sentence's synthesized length; [{text, at, seconds}] in wav time."""
    offset = record_of(name)['appSound']['clipOffset']
    segs = [s for s in voiced_segments(name) if after <= s[0] + offset < before]
    want = [expected_seconds(t) for t in texts]
    n, k = len(segs), len(texts)
    if n < k:
        raise SystemExit(f'{name}: {n} sound segments for {k} sentences after {after}s')
    inf = float('inf')
    cost = [[inf] * (k + 1) for _ in range(n + 1)]
    back = [[0] * (k + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    for i in range(1, n + 1):  # first i segments split into j sentences (trailing segments may stay unused)
        for j in range(1, k + 1):
            for m in range(j - 1, i):
                span = segs[i - 1][1] - segs[m][0]
                c = cost[m][j - 1] + abs(span - want[j - 1])
                if c < cost[i][j]:
                    cost[i][j], back[i][j] = c, m
    end = min(range(k, n + 1), key=lambda i: cost[i][k])
    groups, i = [], end
    for j in range(k, 0, -1):
        m = back[i][j]
        groups.append((segs[m][0], segs[i - 1][1]))
        i = m
    groups.reverse()
    return [{'text': t, 'at': a, 'seconds': round(b - a, 3)} for t, (a, b) in zip(texts, groups)]


def answer_sentences(name: str, text: str) -> list:
    """The sentences of one spoken answer, timed inside that answer. The answer's exact start and length come from the
    original-voice placement (<take>-clean.json); every sound segment inside it is given to one of its sentences, in
    order, so the last sentence ends where the answer ends (v7: guessing sentence lengths across the whole take put
    the stop offer's last sentence 1 s early and the cut ended inside it)."""
    report = json.loads((TAKES / f'{name}-clean.json').read_text())
    entry = max(report['sentences'], key=lambda e: difflib.SequenceMatcher(None, e['text'], text).ratio())
    texts = split_sentences(text)
    a, b = entry['at'] - 0.05, entry['at'] + entry['seconds'] + 0.05
    segs = [s for s in voiced_segments(name) if s[1] > a + 0.05 and s[0] < b - 0.05]  # overlapping the answer (its first word may start a few ms before the placed start)
    if len(segs) < len(texts):  # at 1.2x a sentence pause can stay above -55 dB for all but a few frames: split at the deepest dips
        db, _floor, _loud = film_speech.speech_level(voice_track(name)[0])
        level = lambda t: float(sum(db[int(t * 100) + k] for k in range(6)) / 6)  # noqa: E731  (60 ms mean, dB)
        while len(segs) < len(texts):
            best = min(((level(t / 100), i, t / 100) for i, (x, y) in enumerate(segs)
                        for t in range(int((x + 0.3) * 100), int((y - 0.3) * 100))), default=None)
            if best is None:
                raise SystemExit(f'{name}: {len(segs)} sound segments for {len(texts)} sentences in "{text[:30]}…"')
            _db, i, t = best
            x, y = segs[i]
            segs = segs[:i] + [(x, round(t, 2)), (round(t + 0.06, 2), y)] + segs[i + 1:]
    weight = [len(re.sub(r'\s', '', t)) for t in texts]
    total_chars, total_time = sum(weight), segs[-1][1] - segs[0][0]
    want = [total_time * w / total_chars for w in weight]  # this answer's own speaking rate
    n, k = len(segs), len(texts)
    inf = float('inf')
    cost = [[inf] * (k + 1) for _ in range(n + 1)]
    back = [[0] * (k + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, k + 1):
            for m in range(j - 1, i):
                # a sentence should also end at a pause: the longer the gap after it, the better (comma pauses are as long
                # as sentence pauses at 1.2x, so lengths alone mis-split "…넣었어요. 8분 뒤에 도착해요." in v8)
                gap = segs[i][0] - segs[i - 1][1] if j < k and i < n else 0.0
                c = cost[m][j - 1] + abs(segs[i - 1][1] - segs[m][0] - want[j - 1]) - 1.5 * gap
                if c < cost[i][j]:
                    cost[i][j], back[i][j] = c, m
    groups, i = [], n  # all segments are used: the answer ends with its last sentence
    for j in range(k, 0, -1):
        m = back[i][j]
        groups.append((segs[m][0], segs[i - 1][1]))
        i = m
    groups.reverse()
    groups = asr_boundaries(name, entry, texts, groups) or groups
    return [{'text': t, 'at': x, 'seconds': round(y - x, 3)} for t, (x, y) in zip(texts, groups)]


def pause_between(name: str, end: float, start: float) -> tuple:
    """Whisper's word edges are about 0.1 s late and often abut; the pause is the longest run of 10 ms frames 20 dB under
    the speech within 0.4 s of them. Returns (end of the sentence, start of the next)."""
    lo, hi = min(end, start) - 0.4, max(end, start) + 0.2
    db, _floor, loud = film_speech.speech_level(voice_track(name)[0], lo, hi)
    quiet = [v < loud - 20 for v in db]
    best, run = None, None
    for i, q in enumerate(quiet + [False]):
        if q and run is None:
            run = i
        if not q and run is not None:
            if best is None or i - run > best[1] - best[0]:
                best = (run, i)
            run = None
    if best is None or best[1] - best[0] < 3:  # under 30 ms: keep Whisper's edges
        return end, start
    return lo + best[0] * 0.01, lo + best[1] * 0.01


def asr_boundaries(name: str, entry: dict, texts: list, groups: list) -> list | None:
    """Sentence boundaries inside one answer from Whisper's word times (v9: at 1.4x Pli's pause between two sentences
    can be 60 ms, shallower than its comma pauses, so sound levels put "하연아," into the sentence before it). The
    answer's first start and last end stay where the sound says; None when the words do not match the answer."""
    if len(texts) < 2:
        return None
    voiced = split_sentences(entry.get('voiced') or ' '.join(texts))  # the answer as read aloud (numbers in words)
    if len(voiced) != len(texts):
        return None
    heard = film_speech.transcribe(voice_track(name)[0], groups[0][0] - 0.05, groups[-1][1] + 0.05)['words']
    syllables = lambda t: len(re.findall(r'[가-힣]', t))  # noqa: E731
    counts, total = [], 0
    for word in heard:
        total += syllables(word['w'])
        counts.append(total)
    if not heard or abs(total - sum(syllables(t) for t in voiced)) > 0.15 * total:
        return None
    out, start, done = [], groups[0][0], 0
    for j in range(len(texts) - 1):
        done += syllables(voiced[j])
        w = min(range(len(heard) - 1), key=lambda i: abs(counts[i] - done))
        end, nxt = pause_between(name, float(heard[w]['end']), float(heard[w + 1]['start']))
        out.append((round(start, 2), round(end, 2)))
        start = nxt
    out.append((round(start, 2), groups[-1][1]))
    return out if all(y > x for x, y in out) else None


NEIGHBOUR_GAP = 0.15  # clear of the sentence before/after a cut; check-film looks 0.12 s outside each sound span


def app_cut(name: str, sentences: list, feature: int, lead: float = 0.3, tail: float = 0.35, frame: dict | None = None,
            answer: list | None = None) -> dict:
    """An app take span holding whole sentences (sentence times are wav times: clip = wav + clipOffset). With the whole
    `answer` the span came from, lead and tail stop short of the sentence before and after (v9: at 1.4x Pli pauses
    0.2-0.4 s between sentences, less than a fixed 0.25 s tail plus the check's 0.12 s)."""
    record = record_of(name)
    offset = record['appSound']['clipOffset']
    first, last = sentences[0], sentences[-1]
    if answer:
        index = [i for i, x in enumerate(answer) if x['at'] == first['at']][0]
        after = index + len(sentences)
        if index > 0:
            gap = first['at'] - (answer[index - 1]['at'] + answer[index - 1]['seconds'])
            lead = max(0.0, min(lead, gap - NEIGHBOUR_GAP))
        if after < len(answer):
            gap = answer[after]['at'] - (last['at'] + last['seconds'])
            tail = max(0.0, min(tail, gap - NEIGHBOUR_GAP))
    a = max(0.0, round(first['at'] + offset - lead, 2))
    b = min(float(record['video']['format']['duration']) - 0.05, round(last['at'] + last['seconds'] + offset + tail, 2))
    cut = {'app': name, 'in': a, 'out': b, 'speed': 1.0, **(frame or {})}
    lines = [{'speaker': '플리', 'text': s['text'], 'at': round(s['at'] + offset - a, 3), 'seconds': s['seconds']} for s in sentences]
    track, eq = voice_track(name)
    sound = {'source': str(track.relative_to(ROOT)), 'from': round(a - offset, 3), 'to': round(b - offset, 3), **({'eq': eq} if eq else {})}
    return {'cut': cut, 'feature': feature, 'lines': lines, 'sound': sound}


def heard_cut(name: str, turn_id: str, clip: str, speech: dict, feature: int) -> dict:
    """The app screen while it hears a family line: the line's own sound (the clip it was played from) over the
    take's picture at the moment it was played into the app's microphone."""
    record = record_of(name)
    turn = next(t for t in record['turns'] if t['id'] == turn_id)
    spec = next(t for take in json.loads(APP_TAKES.read_text())['takes'] if take['id'] == name for t in take['turns'] if t['id'] == turn_id)
    line = speech['lines'][0]
    spoken_from, spoken_to = spec['from'], spec['to']  # the span of `clip` that was played into the app
    a = max(0.0, round(turn['clipAt'] - 0.25, 2))
    b = round(turn['clipAt'] + (spoken_to - spoken_from) + 0.15, 2)
    sound = {'source': f'.tools/product-film/weave/{clip}.mp4', 'from': round(spoken_from - 0.25, 3), 'to': round(spoken_to + 0.15, 3),
             'denoise': DENOISE, 'gate': GATE}
    lines = [{'speaker': line['speaker'], 'text': line['text'], 'at': round(line['start'] - spoken_from + 0.25, 3),
              'seconds': round(line['end'] - line['start'], 3)}]
    return {'cut': {'app': name, 'in': a, 'out': b, 'speed': 1.0, 'punchIn': {'at': 0.0, **PUNCH['card']}}, 'feature': feature, 'lines': lines,
            'sound': sound}


# the model's hiss: stronger than v6 (nr=10), and pulled down a further 12 dB between words, so the floor steps less
# at cuts into the app scenes (G3); speech (about -20 dBFS) is far above the gate (-30 dBFS)
DENOISE = 'afftdn=nr=16:nf=-46'
# after the line is at -20 LUFS (speech peaks -10..-20 dBFS): the generated cabin hum (about -40 dBFS) goes down up to 20 dB
# between words; ratio 4 because at ratio 2 hum just under the threshold was barely touched (v7 QA: 14-20 dB steps left)
GATE = 'agate=threshold=0.0316:ratio=4:range=0.1:attack=5:release=120'  # v8: closes 0.12 s after a word (0.3 s left hum at cuts)


def weave_cut(clip: str, feature: int | None, speech: dict, crop: list, start: float | None = None, end: float | None = None,
              lines_between: tuple = (0.0, 1e9)) -> dict:
    """A 9:16 window of a Weave scene from `start` (default: just before the speech) to `end` (default: after it)."""
    look = SCENES[clip][0]
    a = start if start is not None else (max(SCENES[clip][2][0], round(speech['start'] - LEAD, 2)) if speech['start'] > 1.2 else 0.0)
    b = end if end is not None else round(min(speech['duration'] - 0.02, speech['end'] + TAIL), 2)
    cut = {'weave': clip, 'in': a, 'out': b, 'speed': 1.0, 'look': look, 'crop': crop}
    lines = [{'speaker': l['speaker'], 'text': l['text'], 'at': round(max(0.0, l['start'] - a), 3), 'seconds': round(l['end'] - l['start'], 3)}
             for l in speech['lines'] if lines_between[0] <= l['start'] < lines_between[1]]
    sound = {'source': f'.tools/product-film/weave/{clip}.mp4', 'from': a, 'to': b, 'denoise': DENOISE, 'gate': GATE}
    return {'cut': cut, 'feature': feature, 'lines': lines, 'sound': sound}


def quiet_point(clip: str, a: float, b: float, min_len: float = 0.12) -> float:
    """Where one speaker hands over to the other between two clip times: the start (+80 ms of decay) of the last pause
    of at least `min_len` seconds, a pause being frames 14 dB under the span's speech level (Whisper's word ends are
    too loose for this: in the whine scene it put the child's last word 0.45 s into the mother's line)."""
    db, _floor, loud = film_speech.speech_level(WEAVE / f'{clip}.mp4', a, b)
    quiet = [v < loud - 14 for v in db]
    runs, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_len:
                runs.append(i)
            i = j
        else:
            i += 1
    if not runs:
        raise SystemExit(f'{clip}: no pause of {min_len}s between {a} and {b}')
    return round(a + runs[-1] * 0.01 + 0.08, 2)  # 80 ms: the 40 ms fade-out starts after the last vowel has decayed


VERTICAL = ROOT / '.tools/product-film/vertical'  # v8 family scenes, 9:16 (scripts/make-vertical-scenes.py)
# v10: the family scenes made again from cleaned first frames, 9:16 (tall) and 16:9 (wide) (make-scene-frames.py,
# make-vertical-scenes.py --v10), captions removed and upscaled like v9, then scanned for drawn defects (film_artifact_scan.py)
SCENE_DIR = ROOT / '.tools/product-film/v10' / ('final-wide' if LANDSCAPE else 'final-tall')
# 'High' findings of scripts/film_artifact_scan.py on the final scenes that frame review judged not to be drawn defects
# (2026-11-15, full-resolution frames checked by eye). scripts/check-film.py fails on any high finding not listed here.
LIGHTS = 'streetlights and other cars\' lights moving past the windows: the scene is driving at night'
ARTIFACT_REVIEW = {
    'final-tall/newcar-hd#0': 'the cartoon bunny on her sweatshirt; it has no letters (the made-up letters of v9 were removed)',
    'final-tall/askpack-hd#0': LIGHTS, 'final-tall/askpack-hd#1': LIGHTS, 'final-tall/askpack-hd#2': LIGHTS,
    'final-tall/askpack-hd#4': 'the red release button of the car seat harness buckle',
    'final-tall/gothere-mom-hd#0': 'streetlight reflections moving over the dashboard', 'final-tall/gothere-mom-hd#1': LIGHTS,
    'final-tall/gothere-mom-hd#2': LIGHTS, 'final-tall/gothere-mom-hd#3': LIGHTS,
    'final-tall/gothere-mom-hd#4': 'orange streetlight on the dashboard edge',
    'final-tall/gothere-mom-hd#5': 'the steering wheel seen from a camera on the dashboard; it is where a wheel is',
    **{f'final-wide/askpack-hd#{n}': LIGHTS for n in (0, 1, 2, 3, 4, 6, 8, 9, 10)},
    'final-wide/momalbum-hd#0': 'the climate-control buttons and their indicator lights; no writing',
    **{f'final-wide/momalbum-hd#{n}': LIGHTS for n in (1, 2, 3, 4, 5)},
    'final-wide/momalbum-hd#6': 'the centre screen, switched off (dimmed by film_scene_patch.py); only its bezel catches light',
    'final-wide/gothere-mom-hd#0': 'her hands on the steering wheel', 'final-wide/gothere-mom-hd#1': 'the climate-control buttons',
    **{f'final-wide/gothere-mom-hd#{n}': 'headlights of the cars behind, through the rear window' for n in (2, 3, 4, 5)},
    'final-wide/gothere-mom-hd#6': 'the climate-control indicator lights',
    'final-wide/gothere-mom-hd#7': 'the centre screen, switched off (dimmed by film_scene_patch.py)',
    'final-wide/gothere-child-hd#0': 'her fringe (hair) over the forehead',
}
PLI_VOICE = ('answers the car speaks again and again served from the edge voice cache: renditions by a commercial voice, '
             'MiniMax Speech 2.8 HD (Exuberant_Girl, happy, 1.15x) via Figma Weave, each checked by Whisper; new answers '
             'live from Supertonic 3 F3 at 1.4x. APK with the driving render budget: no title, entry or typing motion '
             'while the car drives, so the Pleos driving view keeps 28-30 redraws/s while Pli speaks')  # v10 (AB.10, AB.11)
# v9 layout (1080x1920): the family scenes fill the whole frame (the captions the video model burned in are removed,
# scripts/film_caption_mask.py + DiffuEraser, and the clips upscaled, scripts/film_upscale.py); a soft dark gradient from
# SCRIM_TOP carries the captions; the app's screen is centred in the APP_AREA above it. Feature labels at the top.
SCRIM_TOP = 700 if LANDSCAPE else 1150
CAPTION_TOP = 1400                     # vertical: captions hang from here; landscape: CAPTION_BOTTOM above the bottom edge
CAPTION_BOTTOM = 70
APP_AREA = 1300
# landscape: under the cluster's speed readout (y 60-120 of the Pleos display), over the dark sky above the road; at y 70
# the translucent label showed the speed "32" through its title (v10 frame review)
V8_LABEL = (48, 206) if LANDSCAPE else (48, 70)
V8_TAG_Y = 1316                        # notes (left) and the footage tag (right), above the captions
NOTE_Y = 880 if LANDSCAPE else V8_TAG_Y  # landscape: the note above the captions, the tag at the top right
TAG_Y = 64 if LANDSCAPE else V8_TAG_Y
HD_CLIP = 'clean/{name}-hd.mp4'        # under VERTICAL: caption-free, 1080x1920, same timing and sound as the generated clip
SCENE_ZOOM = {}  # v9 newcar 1.16 (a caption box across the full width); v10 clips are checked on their own
SCENE_DENOISE = {'whine': 'afftdn=nr=30:nf=-60'}  # the old car's hiss between the whined words (stem -46 dB vs -60..-84 elsewhere)
WARMTH_TARGET = {'엄마': 10.0, '하연': 6.0}  # source frames; the lower gradient cools the child's (pink top) by ~7 in the master  # mean R-B at night: v8 had 22.5-24 (mother, sodium street light) vs -19..-20 (child, blue window)
DISPLAY = (2560, 1440)  # the Pleos display; CLOSEUPS are in its pixels


def take_stream() -> tuple:
    """The size the app takes were streamed at (v10: 1920x1080 under host load 30-50; v8/v9: 2560x1440); all three alike."""
    sizes = {tuple(json.loads((TAKES / f'{t}.json').read_text())['grab']['stream']) for t in ('pack', 'album', 'stop')}
    if len(sizes) != 1:
        raise SystemExit(f'app takes streamed at different sizes: {sizes}')
    return sizes.pop()


STREAM = take_stream()
CLOSEUPS = {  # display pixels of the tall close-up in each app cut (chosen on frames of the v8 takes)
    'card': [1560, 290, 950, 770],     # Pli's answer card: title, text, checklist / reasons (1080x876 on screen)
    'photo': [1230, 210, 1040, 880],   # the album: cover title / the photo around 하연, above its own caption (1080x914 on screen)
}
V8_LEAD, V8_TAIL = 0.1, 0.25           # "대사간 공백도 너무 길고": tight around every line
V8_SCENES = {  # vertical clip: (speaker, line, look, feature)
    'whine': ('하연', '엄마아, 심심해! 언제 도착해?', 'before', None),
    'newcar': ('하연', '우와, 우리 새 차다!', 'after', None),
    'askpack': ('하연', '플리야, 내일 뭐 챙겨?', 'after', 0),
    'momalbum': ('엄마', '하연이 사진으로 앨범 만들어 줄래?', 'after', 1),
    'gothere-mom': ('엄마', '하연아, 거기 가 볼까?', 'after', 2),
    'gothere-child': ('하연', '응, 좋아!', 'after', 2),
}


def scaled(region: list) -> list:
    """Display pixels (2560x1440) -> pixels of the streamed takes, even sizes."""
    k = STREAM[0] / DISPLAY[0]
    return [round(v * k / 2) * 2 for v in region]


def night_grade(path: Path, a: float, b: float, look: str, target: float) -> str:
    """Channel gains that bring a night scene's mean warmth (R-B, after its look) to `target`, half from red and half
    from blue, so the mother's sodium-lit shots and the child's blue-window shots read as the same evening."""
    import subprocess
    import numpy as np
    looks = runpy_looks()
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', str(path), '-vf',
                                   f"fps=4,{looks[look]},scale=270:480", '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    rgb = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270, 3).astype(np.float64)
    r, g, bl = (float(rgb[..., i].mean()) for i in range(3))
    shift = target - (r - bl)
    gr, gb = (r + shift / 2) / r, (bl - shift / 2) / bl
    return f'colorchannelmixer=rr={gr:.3f}:gg=1:bb={gb:.3f}'


def runpy_looks() -> dict:
    """The builder's looks (scripts/build-product-film.py LOOKS), read without importing the builder."""
    import ast
    tree = ast.parse((ROOT / 'scripts/build-product-film.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'LOOKS')
    return ast.literal_eval(node.value)


def vertical_cut(name: str) -> tuple:
    """A v8 family scene: its whole spoken line, 0.1 s before and 0.25 s after (speech found from the clip's own sound,
    which is the voice the lips were made to)."""
    speaker, line, look, feature = V8_SCENES[name]
    path = SCENE_DIR / f'{name}.mp4'
    duration = film_speech.audio(path).size / film_speech.RATE
    db, floor, loud = film_speech.speech_level(path)
    voiced = [i * 0.01 for i, v in enumerate(db) if v > max(floor + 15, loud - 25)]
    first, last = (voiced[0], voiced[-1] + 0.01) if voiced else (0.0, duration)
    heard = film_speech.transcribe(path)
    if heard['words']:  # a soft first word ("엄마아", whined at -38 dB) is under the energy bar but Whisper hears it
        first = min(first, heard['words'][0]['start'])
    a, b = max(0.0, round(first - V8_LEAD, 2)), round(min(duration - 0.02, last + V8_TAIL), 2)
    text = normalize(heard['whisper'])
    check = {'speaker': speaker, 'text': line, 'heard': text, 'script': line, 'start': round(first, 2), 'end': round(last, 2),
             'match': round(jamo_similarity(text, line), 2)}
    subject = {'subject': 'mother'} if speaker == '엄마' else {}  # the mother's shots have no 하연 to match faces against
    clip = HD_CLIP.format(name=name)
    grade = night_grade(SCENE_DIR / clip, a, b, look, WARMTH_TARGET[speaker]) if look == 'after' and name != 'newcar' else None
    folder = str(SCENE_DIR.relative_to(ROOT))
    piece = {'cut': {'vertical': name, 'folder': folder, 'clip': clip, 'in': a, 'out': b, 'speed': 1.0, 'look': look, **subject,
                     **({'grade': grade} if grade else {}), **({'zoom': SCENE_ZOOM[name]} if name in SCENE_ZOOM else {})}, 'feature': feature,
             'lines': [{'speaker': speaker, 'text': line, 'at': round(first - a, 3), 'seconds': round(last - first, 3)}],
             'sound': {'source': f'{folder}/{name}.mp4', 'from': a, 'to': b, 'denoise': SCENE_DENOISE.get(name, DENOISE), 'gate': GATE,
                       # the scene's background fades over the lead and tail around its line, not cut at the shot change
                       'fadeIn': round(max(0.0, first - a - 0.02), 2), 'fadeOut': round(max(0.0, b - last - 0.03), 2)}}
    return piece, {'lines': [check], 'start': round(first, 2), 'end': round(last, 2), 'whisper': heard['whisper'], 'sensevoice': heard['sensevoice']}


def build() -> dict:
    plan = json.loads(PLAN.read_text())
    pack, album, stop = record_of('pack'), record_of('album'), record_of('stop')
    said = lambda record, start: next(x for x in record['spoken'] if x.startswith(start))  # noqa: E731  (by content, not order)
    story = json.loads((ROOT / '.tools/edge-ai/family-album/album-story.json').read_text())['story']
    pack_full = answer_sentences('pack', said(pack, '내일'))
    pack_answer = pack_full[:1]            # the checklist; the "다 챙겼어" hint is left out
    album_full = answer_sentences('album', said(album, '네,'))
    album_reply = album_full  # v9: at 1.4x "…만들었어요. 하연아, 같이 볼까?" has a 60 ms pause: no clean cut between them
    album_page = answer_sentences('album', story['pages'][0]['caption'])
    offer_full = answer_sentences('stop', said(stop, '집까지'))
    offer = offer_full                     # v10: the lively take runs its sentences together, so there is no clean cut after the first
    reply = answer_sentences('stop', said(stop, '좋아요'))
    close = lambda region, at=1.0: {'region': scaled(CLOSEUPS[region]), 'closeAt': at}  # noqa: E731
    speech, pieces = {}, []
    for name in ('whine', 'newcar', 'askpack'):
        piece, speech[name] = vertical_cut(name)
        pieces.append((name, piece))
    # the card close-up from the start: as the answer card appears the app redraws and the vehicle view drops to ~10 fps
    # v10: the lively answer comes from the edge cache at once, about 0.6 s before the app has faded out the earlier card
    # and drawn the new one, so the close-up waits until the new card is up (the whole display shows the change)
    pieces.append(('pack-answer', app_cut('pack', pack_answer, 0, lead=0.15, tail=V8_TAIL, frame=close('card', 0.75), answer=pack_full)))
    piece, speech['momalbum'] = vertical_cut('momalbum')
    pieces.append(('momalbum', piece))
    pieces.append(('album-reply', app_cut('album', album_reply, 1, lead=0.15, tail=MID_TAIL, frame=close('photo', 1.2), answer=album_full)))
    pieces.append(('album-page', app_cut('album', album_page, 1, lead=0.15, tail=V8_TAIL, frame=close('photo', 0.0))))
    # the offer opens the answer (seconds of quiet before it): a whole-answer lead, not the 0.05 s between two sentences
    # (v10: its first word starts ~0.1 s before the found sentence edge, so 0.05 s cut into it)
    pieces.append(('stop-offer', app_cut('stop', offer, 2, lead=0.3, tail=V8_TAIL, frame=close('card', 0.0), answer=offer_full)))
    for name in ('gothere-mom', 'gothere-child'):
        piece, speech[name] = vertical_cut(name)
        pieces.append((name, piece))
    # the offer and the reply open on the card: as the offer card appears the vehicle view drops to ~5 redraws/s, and
    # on 2026-11-15 another project kept the host at load 24, so the only clean stop take redraws it 7-10 times/s
    pieces.append(('stop-reply', app_cut('stop', reply, 2, lead=0.15, tail=0.4, frame=close('card', 0.0))))
    return assemble(plan, pieces, 2.1, speech, [])


def assemble(plan: dict, pieces: list, card_seconds: float, speech: dict, dropped: list) -> dict:
    starts, at = [], 0.0
    for _name, p in pieces:
        cut = p['cut']
        length = round(round((cut['out'] - cut['in']) * FPS) / FPS, 4)
        starts.append((at, length))
        at = round(at + length, 3)
    card = dict(plan['endCard'])
    card.update(seconds=card_seconds, transition={'type': 'fade', 'seconds': 0.5})
    card_start = round(at - 0.5, 3)
    total = round(card_start + card_seconds, 3)
    dialogue = []
    for index, ((name, p), (start, _length)) in enumerate(zip(pieces, starts)):
        if p['sound'] is not None:
            sound = {**p['sound'], 'to': round(p['sound']['from'] + _length, 3)}  # exactly the cut's whole frames: sounds abut, never overlap
            dialogue.append({'id': f'snd-{index}-{name}', 'speaker': '', 'text': '', 'at': start, 'audio': sound})
        for n, line in enumerate(p['lines']):
            dialogue.append({'id': f'cap-{index}-{n}', 'speaker': line['speaker'], 'text': line['text'], 'captionOnly': True,
                             'at': round(start + line['at'], 3), 'seconds': round(line['seconds'] + 0.25, 2),
                             'until': round(start + _length - 0.04, 3),  # over the lower gradient
                             **({'marginV': CAPTION_BOTTOM, 'align': 2} if LANDSCAPE else {'marginV': CAPTION_TOP, 'align': 8})})
    names = [n for n, _p in pieces]
    labels = []
    for f, (number, title, detail) in enumerate(FEATURES):
        idx = [i for i, (_n, p) in enumerate(pieces) if p['feature'] == f]
        if idx:
            labels.append({'number': number, 'title': title, 'detail': detail, 'at': round(starts[idx[0]][0] + 0.05, 3),
                           'until': round(starts[idx[-1]][0] + starts[idx[-1]][1] - 0.08, 3)})
    notes = []
    for answer_name, (take, turn_id) in ANSWERS.items():  # honest about the waiting time the edit leaves out (audit F5)
        if answer_name not in names:
            continue
        record = record_of(take)
        turn = next(t for t in record['turns'] if t['id'] == turn_id)
        spec = next(t for x in json.loads(APP_TAKES.read_text())['takes'] if x['id'] == take for t in x['turns'] if t['id'] == turn_id)
        asked_until = turn['clipAt'] + (spec['to'] - spec['from'])  # the family line has been heard by then
        skipped = round(pieces[names.index(answer_name)][1]['cut']['in'] - asked_until, 1)
        at = starts[names.index(answer_name)][0]
        if skipped >= 0.5:
            notes.append({'text': f'음성 인식·응답 대기 {skipped:g}초 생략', 'at': round(at, 3), 'until': round(at + 2.2, 3),
                          'x': 40, 'y': NOTE_Y})
    newcar_at = starts[names.index('newcar')][0]
    band_h = round(FORMAT['width'] * STREAM[1] / STREAM[0] / 2) * 2
    plan.update({
        'format': {**plan['format'], **FORMAT, 'fps': FPS, 'durationSeconds': total},
        'edit': [p['cut'] for _n, p in pieces], 'endCard': card, 'dialogue': dialogue, 'labels': labels, 'notes': notes,
        'footageTag': '실제 Pleos 에뮬레이터 화면 · 플리 앱', 'overlayY': V8_LABEL[1], 'labelX': V8_LABEL[0],
        'tagY': TAG_Y, 'tagRight': 40, 'scrimTop': SCRIM_TOP,
        'appFrame': {'mode': 'full', 'stream': list(STREAM), 'crop': [0, 0, *STREAM], 'redact': False} if LANDSCAPE else {'mode': 'closeup', 'stream': list(STREAM), 'fullY': (APP_AREA - band_h) // 2, 'closeY': 'center', 'closeMargin': 28,
                     'areaHeight': APP_AREA, 'region': scaled(CLOSEUPS['card']), 'closeAt': 1.0, 'crop': [0, 0, *STREAM], 'redact': False,
                     # behind the car's screen: the evening cabin, blurred (its centre display)
                     # v10: a clean night gradient in the app's colours (v9's blurred cabin photo read as stray blobs)
                     'background': {'style': 'night'}},
        # Weave-generated music (MiniMax Music v2.6) from the new-car reveal to the end; it swells in over the last second of
        # the old car (v9: 2.0 s before the cut, at full level for the last second, so the old car's hiss stops under it, G3)
        'sound': {'music': {'file': '.tools/product-film/weave/music-minimax.wav', 'start': round(newcar_at - 2.0, 3), 'gainDb': -20}},
        'identity': (('Landscape 1920x1080' if LANDSCAPE else 'Vertical 1080x1920 short') + ' (v10). Family scenes: made '
                     + ('16:9' if LANDSCAPE else '9:16') + ' on Hugging Face (PRO, ZeroGPU) by LTX-2 audio-to-video from first '
                     'frames cleaned of what v9 had drawn wrong (Qwen-Image-Edit-2511 with the family\'s reference photos, '
                     'scripts/make-scene-frames.py), speaking the Seedance voices the user accepted, sped up 1.05-1.12x; the '
                     'captions the model burned in were removed (PP-OCRv3 text detection + DiffuEraser on Hugging Face), the clips '
                     'upscaled 2x (Real-ESRGAN) and scanned for drawn defects (scripts/film_artifact_scan.py). Feature scenes: real '
                     'recordings of the public Pli APK on the Pleos emulator (full display 2560x1440, night mode), answering those '
                     'voices on a weekday 17:30 drive home in Gwanggyo; Pli speaks with its own voice (' + PLI_VOICE + ').'),
        'transcriptNote': ('플리 제품 소개 영상(세로) · 가족 장면은 허깅페이스 PRO(LTX-2)로 세로 화면에 맞춰 새로 만들었고(목소리는 앞서 '
                           '만든 장면의 목소리), 기능 장면은 공개용 플리 앱이 그 목소리를 실제로 듣고 답한 화면과 음성입니다.'),
        'status': 'edit-v10-' + VARIANT,
        'artifactReview': {f'{str(SCENE_DIR.parent.relative_to(ROOT))}/{k}': v for k, v in ARTIFACT_REVIEW.items()
                           if k.startswith(SCENE_DIR.name + '/')},
        'speechCheck': speech,
        'dropped': dropped,
    })
    return plan


def main() -> int:
    plan = build()
    PLAN_OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'seconds': plan['format']['durationSeconds'], 'cuts': len(plan['edit']), 'dropped': plan['dropped'],
                      'edit': [(c.get('weave') or c.get('app'), c['in'], c['out']) for c in plan['edit']]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
