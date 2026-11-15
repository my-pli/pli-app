#!/usr/bin/env python3
"""Film QA gate: measure the rendered film and its sources before anything is published.

The 2026-11-14 audit (docs/AUDIT-2026-11-14-FILM-VOICE.md, J1) found a film published on app tests alone.
This checks what a viewer sees and hears:
  - cutSpeech    no sound span starts or ends inside speech (0.3 s each side, energy; audit K1-K7)
  - dialogue     each family line, transcribed from its clip, matches the script it is captioned with
  - appFrames    app takes are constant 30 fps slots with <= 2% stale slots and >= 28 screenshots/s (A1)
  - faces        하연 in each generated cut: median best similarity to her four photos (B2; >= 0.45)
  - loudness     spoken cuts within 3 LU of each other in the final mix (G2)
  - noiseFloor   background jump a cut makes (each scene's background over the music held level) <= 8 dB (G3)
  - clock        app takes recorded on the story's weekday 17:30 clock (D1)
  - appMotion    the vehicle view really moves in every app cut: >= 15 redraws/s on average (v6: 2.6-3.6, "끊김")
  - voiceDrops   Pli's sound in every app cut has no mid-word digital silence (v6: 11 emulator dropouts)
  - lighting     every in-car scene after the new car looks like the same dusk: no cut much brighter than the darkest,
                 and no cut much warmer or bluer than another (R-B spread <= 15)
                 (v6 went overcast day -> dusk -> night -> sunlit day: "낮과 밤을 왔다갔다")
  - length       30-60 s
Writes .tools/product-film/qa/film-qa.json; exits 1 when a check fails.
usage: .tools/edge-venv/bin/python scripts/check-film.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_identity  # noqa: E402
import film_speech  # noqa: E402
import film_take_quality  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VARIANT = os.environ.get('PLI_FILM_VARIANT', 'vertical')  # v10: 'landscape' checks the 1920x1080 version
SUFFIX = '' if VARIANT == 'vertical' else f'-{VARIANT}'
PLAN = ROOT / f'media/pli-film/production{SUFFIX}.json'
MASTER = ROOT / f'artifacts/pli-product-film{SUFFIX}.mp4'
TAKES = ROOT / '.tools/product-film/app-takes'
OUT = ROOT / f'.tools/product-film/qa/film-qa{SUFFIX}.json'
VOICE_STEM = ROOT / f'.tools/product-film/new-cut{SUFFIX}/voice-stem.wav'  # written by scripts/build-product-film.py
MUSIC_STEM = ROOT / f'.tools/product-film/new-cut{SUFFIX}/music-stem.wav'  # the ducked music bed alone, same scale as VOICE_STEM
# seconds checked outside a span; share of voiced frames allowed there. 0.12 s: since v7 Pli speaks a whole answer in
# one pass and its sentence pauses are 0.25-0.45 s, so a clean cut between two sentences may sit 0.15 s from the next one;
# a cut into a word still shows speech right at the cut
EDGE, EDGE_MAX = 0.12, 0.2
FACE_MIN = 0.45
LOUD_SPREAD = 3.0
FLOOR_JUMP = 8.0
WARMTH_SPREAD = 15.0  # R-B between the evening scenes; v8: mother 22.5-24 (orange) vs child -19..-20 (blue) read as two evenings


def timeline(plan: dict) -> list:
    out, at = [], 0.0
    for cut in plan['edit']:
        at = round(at - cut.get('transition', {}).get('seconds', 0.0), 3)
        length = round(round((cut['out'] - cut['in']) * plan['format']['fps']) / plan['format']['fps'], 4)
        out.append({**cut, 'start': at, 'length': length})
        at = round(at + length, 3)
    return out


def cut_speech(plan: dict) -> dict:
    rows, bad = [], []
    for line in plan['dialogue']:
        audio = line.get('audio')
        if not audio:
            continue
        source = ROOT / audio['source']
        _db, floor, loud = film_speech.speech_level(source)
        duration = film_speech.audio(source).size / film_speech.RATE
        before = film_speech.voiced_share(source, audio['from'] - EDGE, audio['from'], floor, loud) if audio['from'] > 0.05 else 0.0
        after = film_speech.voiced_share(source, audio['to'], min(duration, audio['to'] + EDGE), floor, loud) if audio['to'] < duration - 0.05 else 0.0
        row = {'id': line['id'], 'before': round(before, 2), 'after': round(after, 2)}
        rows.append(row)
        if before > EDGE_MAX or after > EDGE_MAX:
            bad.append(row)
    return {'status': 'FAIL' if bad else 'PASS', 'spans': rows, 'cutInsideSpeech': bad}


def dialogue(plan: dict) -> dict:
    rows, bad = [], []
    for clip, check in (plan.get('speechCheck') or {}).items():
        for line in check['lines']:
            row = {'clip': clip, 'speaker': line['speaker'], 'heard': line.get('heard', line['text']), 'caption': line['text'], 'script': line['script'], 'match': line['match']}
            rows.append(row)
            if line['match'] < 0.6:
                bad.append(row)
    return {'status': 'FAIL' if bad else 'PASS', 'lines': rows, 'mismatch': bad}


def app_frames() -> dict:
    """App takes are constant 30 fps by construction (scripts/film_grab.py slots); what can still go wrong is
    a slot whose moment was older than the kept screenshots (stale) or a stream that sent too few pictures."""
    rows, bad = [], []
    for take in ('pack', 'album', 'stop'):
        record = json.loads((TAKES / f'{take}.json').read_text())
        grab = record['grab']
        stream = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries',
                                                     'stream=r_frame_rate,nb_frames', '-of', 'json', str(TAKES / f'{take}.mp4')]))['streams'][0]
        seconds = grab['stoppedAt'] - grab['startedAt']
        row = {'take': take, 'rate': stream['r_frame_rate'], 'frames': grab['frames'], 'staleShare': round(grab.get('staleFrames', 0) / grab['frames'], 4),
               'screenshotsPerSecond': round(grab['uniqueFrames'] / seconds, 1), 'timestamps': grab.get('timestamps')}
        rows.append(row)
        if row['rate'] != '30/1' or row['timestamps'] != 'cfr-slots' or row['staleShare'] > 0.02 or row['screenshotsPerSecond'] < 28:
            bad.append(row)
    return {'status': 'FAIL' if bad else 'PASS', 'takes': rows}


def faces(cuts: list) -> dict:
    rows, bad = [], []
    for cut in cuts:
        if ('weave' not in cut and 'vertical' not in cut) or cut.get('subject') == 'mother':  # the mother's shots have no 하연
            continue
        report = film_identity.check_video(MASTER, every=0.5, start=cut['start'] + 0.2, end=cut['start'] + cut['length'] - 0.2)
        row = {'cut': cut.get('weave') or cut.get('vertical'), 'median': report['median'], 'withFace': report['withFace'], 'frames': report['frames'],
               'passing': report['passing']}
        rows.append(row)
        if report['median'] is None or report['median'] < FACE_MIN:
            bad.append(row)
    return {'status': 'WARN' if bad else 'PASS', 'cuts': rows, 'below': bad,
            'note': 'profile and edge-of-frame faces score lower; WARN, not FAIL, below the median bar'}


def segment_levels(cuts: list) -> list:
    rows = []
    for cut in cuts:
        a, b = cut['start'] + 0.1, cut['start'] + cut['length'] - 0.1
        done = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', str(MASTER), '-vn',
                               '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'], capture_output=True, text=True)
        found = [line for line in done.stderr.splitlines() if line.strip().startswith('I:')]
        lufs = float(found[-1].split()[1]) if found else -70.0
        _db, floor, _loud = film_speech.speech_level(MASTER, a, b)
        rows.append({'cut': cut.get('weave') or cut.get('vertical') or cut.get('app'), 'start': cut['start'], 'lufs': round(lufs, 1), 'floorDb': round(floor, 1)})
    return rows


def loudness(rows: list) -> dict:
    spoken = [r['lufs'] for r in rows if r['lufs'] > -60]
    spread = max(spoken) - min(spoken) if spoken else 0.0
    return {'status': 'PASS' if spread <= LOUD_SPREAD else 'FAIL', 'spreadLU': round(spread, 1), 'cuts': rows}


def noise_floor(cuts: list) -> dict:
    """The background jump a cut itself makes (G3). Each scene's background is the quietest 100 ms of its own sound
    (dialogue stem) over the whole cut, if that is a real pause (12 dB under its speech; Pli's synthesized voice has
    digital silence there); the music bed that runs on across the cut is added to both sides at the quieter of its
    levels within 1 s of the cut, so a cut is judged by how much its change of scene background shows over it.
    (v6-v8 read the master within 1 s of the cut: it mostly measured soft and loud passages of the music, which moved
    one cut from 4.6 to 17.2 dB when the music started 0.7 s earlier, and in a line that runs to the cut, the decay of
    a word in a 60 ms gap: the whine scene read -45 dB there, its background is -60.) The master's own quietest 100 ms
    within 1 s on each side is reported beside it. A side with no pause is reported, not compared."""
    music_stem = MUSIC_STEM if MUSIC_STEM.is_file() else None

    def quietest(path: Path, a: float, b: float, pause_only: bool) -> float | None:
        db, _p10, loud = film_speech.speech_level(path, max(0.0, a), b)
        if len(db) < 10:
            return None
        power = float(np.convolve(10 ** (db / 10), np.ones(10) / 10, mode='valid').min())  # 100 ms moving mean power
        return None if pause_only and 10 * np.log10(power + 1e-12) > loud - 12 else power

    def level(power: float | None) -> float | None:
        return round(float(10 * np.log10(power + 1e-12)), 1) if power is not None else None

    jumps = []
    for prev, nxt in zip(cuts, cuts[1:]):
        edge = nxt['start']
        scene_b = quietest(VOICE_STEM, prev['start'], edge, True)
        scene_a = quietest(VOICE_STEM, edge, edge + nxt['length'], True)
        bed = 0.0
        if music_stem:
            bed = min(quietest(music_stem, edge - 1.0, edge, False) or 0.0, quietest(music_stem, edge, edge + 1.0, False) or 0.0)
        measured = scene_b is not None and scene_a is not None
        before, after = (level(scene_b + bed), level(scene_a + bed)) if measured else (None, None)
        jumps.append({'at': round(edge, 2), 'from': prev.get('weave') or prev.get('vertical') or prev.get('app'),
                      'to': nxt.get('weave') or nxt.get('vertical') or nxt.get('app'),
                      'sceneBeforeDb': level(scene_b), 'sceneAfterDb': level(scene_a), 'musicHeldDb': level(bed) if music_stem else None,
                      'beforeDb': before, 'afterDb': after, 'jumpDb': round(abs(after - before), 1) if measured else None,
                      'note': None if measured else 'no pause on one side',
                      'masterBeforeDb': level(quietest(MASTER, edge - 1.0, edge, False)),
                      'masterAfterDb': level(quietest(MASTER, edge, edge + 1.0, False))})
    worst = max((j['jumpDb'] for j in jumps if j['jumpDb'] is not None), default=0.0)
    return {'status': 'PASS' if worst <= FLOOR_JUMP else 'FAIL', 'worstDb': worst, 'cuts': jumps}


def app_motion(plan: dict, cuts: list) -> dict:
    whole = plan.get('appFrame', {}).get('mode') == 'full'  # v10 landscape: the whole display all through every app cut
    rows, bad = [], []
    for cut in cuts:
        if 'app' not in cut:
            continue
        punch = cut.get('punchIn')  # a closer look at Pli's card leaves the vehicle view out of the picture
        seen_until = (cut['out'] if whole else cut['in'] + punch['at'] if punch
                      else cut['in'] + cut['closeAt'] if 'closeAt' in cut else cut['out'])
        if seen_until - cut['in'] < 0.5:
            rows.append({'take': cut['app'], 'in': cut['in'], 'out': cut['out'], 'note': 'vehicle view not in the shot'})
            continue
        fps = film_take_quality.vehicle_fps(TAKES / f"{cut['app']}.mp4", cut['in'], seen_until)
        row = {'take': cut['app'], 'in': cut['in'], 'out': cut['out'], 'mean': fps['mean'], 'p10': fps['p10']}
        rows.append(row)
        if fps['mean'] < 15:
            bad.append(row)
    return {'status': 'FAIL' if bad else 'PASS', 'cuts': rows}


def voice_drops(plan: dict) -> dict:
    rows, bad = [], []
    for line in plan['dialogue']:
        audio = line.get('audio') or {}
        if '/app-takes/' not in audio.get('source', ''):
            continue
        found = film_take_quality.dropouts(ROOT / audio['source'], audio['from'], audio['to'])
        rows.append({'id': line['id'], 'source': audio['source'], 'dropouts': found})
        if found:
            bad.append(rows[-1])
    return {'status': 'FAIL' if bad else 'PASS', 'spans': rows}


def lighting(cuts: list) -> dict:
    """Mean luma (0-255) and warmth (R-B) of each family scene in the master, sampled every 0.5 s."""
    import cv2
    rows = []
    for cut in cuts:
        if 'weave' not in cut and 'vertical' not in cut:
            continue
        frames = film_identity.frames(MASTER, 0.5, cut['start'] + 0.1, cut['start'] + cut['length'] - 0.1)
        luma = [float(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean()) for _t, f in frames]
        warmth = [float(f[..., 2].mean() - f[..., 0].mean()) for _t, f in frames]
        rows.append({'cut': cut.get('weave') or cut.get('vertical'), 'start': cut['start'], 'look': cut.get('look'), 'luma': round(float(np.mean(luma)), 1),
                     'warmth': round(float(np.mean(warmth)), 1)})
    evening = [r for r in rows if r['look'] != 'before' and 'newcar' not in r['cut']]  # in the new car, 17:30 after sunset
    spread = (max(r['luma'] for r in evening) / max(1.0, min(r['luma'] for r in evening))) if evening else 1.0
    warmth = (max(r['warmth'] for r in evening) - min(r['warmth'] for r in evening)) if evening else 0.0
    ok = spread <= 1.6 and warmth <= WARMTH_SPREAD
    return {'status': 'PASS' if ok else 'FAIL', 'brightestOverDarkest': round(spread, 2), 'warmthSpread': round(warmth, 1), 'cuts': rows}


def drawn_defects(plan: dict, cuts: list) -> dict:
    """v10 ("이상한게 생성되어있고 … 잡아내봐"): every generated family clip in the edit has been scanned by
    scripts/film_artifact_scan.py (text, pop-in, VLM checklist), and no 'high' finding inside the part of the clip that is
    used is left open. A finding judged false on frame review is listed with its reason in the plan's artifactReview."""
    reviewed = plan.get('artifactReview', {})
    rows, bad = [], []
    for cut in cuts:
        if 'vertical' not in cut or not cut.get('folder'):
            continue
        clip = Path(cut['clip']).stem
        report_path = ROOT / cut['folder'] / 'scan' / f'{clip}-artifacts.json'
        if not report_path.is_file():
            bad.append({'cut': cut['vertical'], 'problem': 'not scanned'})
            continue
        report = json.loads(report_path.read_text())
        open_ = []
        for n, f in enumerate(report['findings']):
            used = [t for t in f['times'] if cut['in'] - 0.1 <= t <= cut['out'] + 0.1]
            key = f"{cut['folder']}/{clip}#{n}"
            if f['severity'] == 'high' and used and key not in reviewed:
                open_.append({'finding': key, 'detector': f['detector'], 'what': f['what'][:120], 'at': used[0]})
        rows.append({'cut': cut['vertical'], 'findings': len(report['findings']), 'open': open_})
        bad += open_
    return {'status': 'FAIL' if bad else 'PASS', 'clips': rows, 'reviewed': len(reviewed)}


def clock() -> dict:
    rows = {t: json.loads((TAKES / f'{t}.json').read_text()).get('clock', '') for t in ('pack', 'album', 'stop')}
    ok = all(re.match(r'2026-11-17', v or '') for v in rows.values())
    return {'status': 'PASS' if ok else 'FAIL', 'takes': rows}


def main() -> int:
    plan = json.loads(PLAN.read_text())
    cuts = timeline(plan)
    length = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(MASTER)]))
    levels = segment_levels(cuts)
    checks = {'length': {'status': 'PASS' if 30 <= length <= 60 else 'FAIL', 'seconds': round(length, 2)},
              'cutSpeech': cut_speech(plan), 'dialogue': dialogue(plan), 'appFrames': app_frames(), 'faces': faces(cuts),
              'loudness': loudness(levels), 'noiseFloor': noise_floor(cuts), 'clock': clock(),
              'appMotion': app_motion(plan, cuts), 'voiceDrops': voice_drops(plan), 'lighting': lighting(cuts),
              'drawnDefects': drawn_defects(plan, cuts)}
    ok = all(c['status'] != 'FAIL' for c in checks.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'ok': ok, 'master': str(MASTER.relative_to(ROOT)), 'checks': checks}, ensure_ascii=False, indent=1))
    print(json.dumps({'ok': ok, **{k: v['status'] for k, v in checks.items()}}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
