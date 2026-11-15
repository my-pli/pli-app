#!/usr/bin/env python3
"""Build Pli's offline neighbourhood place pack from OpenStreetMap.

The in-car agent suggests a place on the everyday drive home (학원 → 집) — a playground, a park or a
library the child would enjoy — without a slow, rate-limited web call at the moment of speaking, so
places are packed ahead of time like navigation map data. Each place keeps only what OpenStreetMap
records: name, kind, position, OSM id, opening hours when mapped, and for parks whether a playground
lies within 250 m.

Queries Nominatim at most once per 1.2 s with an identifying User-Agent, as its usage policy asks.
Writes scripts/edge_data/places-<area>.json.

usage: python3 scripts/build-place-pack.py [--area yangjae|gwanggyo]
"""
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = 'PliFamilyAgent/1.0 (offline neighbourhood place pack; low volume)'
NOMINATIM = 'https://nominatim.openstreetmap.org/search'
AREAS = {'yangjae': (127.015, 37.495, 127.070, 37.450),   # west, north, east, south (서초 양재 일대)
         'gwanggyo': (127.020, 37.310, 127.080, 37.262)}  # 수원 광교 일대 (the public demo's drive home since 2026-11-14)
# Opening hours OpenStreetMap does not have yet, from a dated public listing (kept with their source; the agent only
# speaks hours it has a source for).
HOURS = {'way/1445310258': {'hours': 'Mo-Fr 10:00-21:00, Sa-Su 10:00-18:00',  # 경기도서관 (opened 2025-10, 수원 영통구 도청로 40)
                            'hoursSource': 'K-TRIP TIPS 경기도서관 안내(2026-10-21 수정): 평일 10~21시, 주말 10~18시, '
                                           '매월 둘째·넷째 월요일·1월 1일·설·추석 당일 휴관'}}
KINDS = {'playground': 'playground', 'park': 'park', 'library': 'library'}
PLAYGROUND_NEAR_KM = 0.25


def search(query: str, viewbox: tuple) -> list:
    params = {'format': 'jsonv2', 'limit': 40, 'bounded': 1, 'countrycodes': 'kr', 'q': query, 'extratags': 1,
              'viewbox': ','.join(f'{v:.4f}' for v in viewbox)}
    request = urllib.request.Request(NOMINATIM + '?' + urllib.parse.urlencode(params), headers={'User-Agent': AGENT})
    time.sleep(1.2)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def km(a: tuple, b: tuple) -> float:
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--area', default='yangjae', choices=sorted(AREAS))
    args = parser.parse_args()
    box = AREAS[args.area]
    places = []
    for kind, query in KINDS.items():
        for r in search(query, box):
            if r.get('type') != kind:
                continue
            place = {'kind': kind, 'name': (r.get('name') or '').strip(), 'lat': round(float(r['lat']), 5),
                     'lon': round(float(r['lon']), 5), 'osm': f"{r.get('osm_type')}/{r.get('osm_id')}"}
            hours = (r.get('extratags') or {}).get('opening_hours')
            if hours:  # OpenStreetMap's opening_hours, e.g. 'Mo-Th 09:00-22:00, Sa-Su 09:00~20:00'
                place['hours'] = hours
            elif place['osm'] in HOURS:
                place.update(HOURS[place['osm']])
            places.append(place)
    playgrounds = [(p['lat'], p['lon']) for p in places if p['kind'] == 'playground']
    for p in places:
        if p['kind'] == 'park':
            p['playground'] = any(km((p['lat'], p['lon']), g) <= PLAYGROUND_NEAR_KM for g in playgrounds)
    out = ROOT / f'scripts/edge_data/places-{args.area}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'source': 'OpenStreetMap contributors (ODbL) via Nominatim', 'area': args.area, 'bbox': box,
                               'built': time.strftime('%Y-%m-%d'), 'places': places}, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({kind: sum(p['kind'] == kind for p in places) for kind in KINDS}))


if __name__ == '__main__':
    main()
