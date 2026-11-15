#!/usr/bin/env python3
"""Record an app take several times and keep the attempt whose vehicle view moves most smoothly while Pli speaks.

The public emulator shares a loaded host (other projects keep the load average near 28 of 32 threads), so how often it
redraws the vehicle view varies from take to take (v7: 12-22 redraws/s while Pli speaks). Each attempt is recorded with
scripts/record-film-features.py, its original voice placed with scripts/film_clean_voice.py, and scored by the mean
redraw rate over the seconds the app reported SPEAKING after its first answer; attempts with an answer sentence that
could not be placed (skipped) or that show a blank loading panel are chosen only when no complete attempt exists. Every attempt is kept in
.tools/product-film/app-takes/attempts/<take>-<n>/; the best one is copied back as the take.

usage: python3 scripts/film_best_take.py TAKE ATTEMPTS [--clock '2026-11-17 17:30'] [--night]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAKES = ROOT / '.tools/product-film/app-takes'
ATTEMPTS = TAKES / 'attempts'
EDGE_PY = ROOT / '.tools/edge-venv/bin/python'
FILES = ('{t}.mp4', '{t}.json', '{t}.wav', '{t}.mp4.json', '{t}-clean.wav', '{t}-clean.json')


def score(take: str) -> dict:
    """Mean vehicle-view redraws per second over the seconds the app was SPEAKING (the greeting excluded)."""
    probe = ('import json,sys;sys.path.insert(0,"scripts");import film_take_quality as Q;from pathlib import Path;'
             f'r=json.load(open("{TAKES}/{take}.json"));'
             f'f=Q.vehicle_fps(Path("{TAKES}/{take}.mp4"),0)["perSecond"];'
             'ev=r["events"];spans=[];start=None\n'
             'for e in ev:\n'
             ' s=e["phase"]=="SPEAKING" and not e["speech"].startswith(("준비","우리의"))\n'
             ' if s and start is None: start=e["clipAt"]\n'
             ' if not s and start is not None: spans.append((start,e["clipAt"])); start=None\n'
             'secs=[f[int(t)] for a,b in spans for t in range(int(a),int(b)) if int(t)<len(f)]\n'
             f'skipped=json.load(open("{TAKES}/{take}-clean.json")).get("skipped",[])\n'
             'print(json.dumps({"speakingFps":round(sum(secs)/max(1,len(secs)),1),"seconds":len(secs),"skipped":len(skipped)}))')
    return json.loads(subprocess.check_output([str(EDGE_PY), '-c', probe], cwd=ROOT, text=True).strip().splitlines()[-1])


PANEL = 'crop=1600:1000:900:150,scale=80:50'  # Pli's half of the 2560x1440 display
BLANK = 200  # mean grey of a white "서비스 연결 중입니다" screen (the navigation app loading) is 238; Pli's night UI ~56


def blank_panel(take: str) -> int:
    """Half-second samples in which Pli's panel is a blank white loading screen (v9: one stop take switched to the
    navigation app for 3 s as the waypoint was added; 10 other attempts did not)."""
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(TAKES / f'{take}.mp4'), '-vf', f'fps=2,{PANEL}',
                                   '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
    size = 80 * 50
    return sum(1 for i in range(0, len(raw) - size + 1, size) if sum(raw[i:i + size]) / size > BLANK)


def keep(take: str, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for pattern in FILES:
        source = TAKES / pattern.format(t=take)
        if source.is_file():
            shutil.copy2(source, folder / source.name)


def restore(take: str, folder: Path) -> None:
    for pattern in FILES:
        source = folder / pattern.format(t=take)
        if source.is_file():
            shutil.copy2(source, TAKES / source.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('take')
    parser.add_argument('attempts', type=int)
    parser.add_argument('--clock')
    parser.add_argument('--night', action='store_true')
    args = parser.parse_args()
    existing = sorted(ATTEMPTS.glob(f'{args.take}-*'))
    results = [{'folder': str(f), **json.loads((f / 'score.json').read_text())} for f in existing if (f / 'score.json').is_file()]
    for n in range(len(existing), len(existing) + args.attempts):
        command = [sys.executable, str(ROOT / 'scripts/record-film-features.py'), '--only', args.take]
        command += ['--clock', args.clock] if args.clock else []
        command += ['--night'] if args.night else []
        if subprocess.run(command, cwd=ROOT).returncode != 0:
            print(json.dumps({'attempt': n, 'failed': True}), flush=True)
            continue
        subprocess.run([str(EDGE_PY), str(ROOT / 'scripts/film_clean_voice.py'), args.take], cwd=ROOT, check=True)
        folder = ATTEMPTS / f'{args.take}-{n}'
        keep(args.take, folder)
        result = {**score(args.take), 'blankPanel': blank_panel(args.take)}
        (folder / 'score.json').write_text(json.dumps(result))
        results.append({'folder': str(folder), **result})
        print(json.dumps({'attempt': n, **result}), flush=True)
    # an attempt whose answer could not all be placed from the voice journal is missing a line the edit may need
    complete = [r for r in results if not r.get('skipped') and not r.get('blankPanel')]
    if not complete:  # none complete: the fewest lines missing first (2026-11-15: album-0 had lost the answer itself)
        fewest = min(r.get('skipped', 0) + (99 if r.get('blankPanel') else 0) for r in results)
        complete = [r for r in results if r.get('skipped', 0) + (99 if r.get('blankPanel') else 0) == fewest]
    best = max(complete, key=lambda r: r['speakingFps'])
    restore(args.take, Path(best['folder']))
    print(json.dumps({'take': args.take, 'best': best, 'all': [r['speakingFps'] for r in results]}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
