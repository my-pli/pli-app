"""집 가는 길에 들를 곳 — a place on the drive home, chosen for the child, the weather and the hour.

The car knows where it is and where it is going (Pleos navigation: current position, destination,
minutes left). Pli looks along that line in an offline OpenStreetMap place pack
(scripts/build-place-pack.py), keeps places the car passes within a short detour, and ranks them by
what fits now: outdoor parks with a playground in daylight and dry weather, a library otherwise, and
the child's own interests read from her album captions (e.g. drawing → picture books).
Every fact spoken comes from the pack, the weather service or the vehicle; nothing is invented.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / 'scripts/edge_data'
MAX_OFFSET_KM = 0.9
CITY_KMH = 18.0  # door-to-door city speed including lights, for detour minutes
DAYLIGHT = range(9, 18)
INTERESTS = {
    '그림': ('그림', '색칠', '물감', '크레파스', '색연필'),
    '책': ('책', '동화'),
    '동물': ('동물', '강아지', '고양이', '곤충'),
    '만들기': ('종이접기', '색종이', '만들', '블록'),
    '바깥 놀이': ('놀이터', '미끄럼', '그네', '공놀이', '숲', '산책'),
}
INDOOR_FOR = {'그림': '그림책', '책': '그림책', '만들기': '만들기 책', '동물': '동물 그림책'}

_places: list | None = None


def places() -> list:
    global _places
    if _places is None:
        _places = [p for pack in sorted(PACKS.glob('places-*.json')) for p in json.loads(pack.read_text())['places']]
    return _places


def km(a: tuple, b: tuple) -> float:
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def along(origin: tuple, dest: tuple, point: tuple) -> tuple:
    """(fraction of the way, km off the line) in a local flat projection."""
    scale = math.cos(math.radians(origin[0]))
    ox, oy = origin[1] * scale, origin[0]
    vx, vy = dest[1] * scale - ox, dest[0] - oy
    px, py = point[1] * scale - ox, point[0] - oy
    length2 = vx * vx + vy * vy or 1e-12
    t = (px * vx + py * vy) / length2
    cx, cy = ox + t * vx, oy + t * vy
    return t, math.hypot(point[1] * scale - cx, point[0] - cy) * 111.0


def interest(album: dict | None) -> tuple:
    """The child's most frequent activity in what the vision model saw in her photos → (interest, count).
    Only the scene descriptions count: captions are written from them and may add words."""
    pages = (album or {}).get('pages') or []
    text = ' '.join(p.get('scene') or '' for p in pages)
    counts = {name: sum(text.count(word) for word in words) for name, words in INTERESTS.items()}
    best = max(counts, key=counts.get) if counts else None
    return (best, counts[best]) if best and counts[best] > 0 else (None, 0)


def sun_times(day: date, lat: float, lon: float, utc_offset_hours: float = 9.0) -> tuple:
    """(sunrise, sunset) in local minutes after midnight — NOAA's simplified solar position formulas."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(math.radians(lat)) * math.cos(decl)) - math.tan(math.radians(lat)) * math.tan(decl)
    ha = math.degrees(math.acos(max(-1.0, min(1.0, cos_ha))))
    noon = 720 - 4 * lon - eqtime + utc_offset_hours * 60
    return noon - 4 * ha, noon + 4 * ha


PLAY_MINUTES = 30  # outdoor play needs this much light left


def outdoor_ok(weather: dict, hour: int, minute: int = 0, day: date | None = None, where: tuple | None = None) -> tuple:
    if weather.get('raining'):
        return False, '지금 비가 와요'
    temp = weather.get('temp')
    if temp is not None and not 3 <= temp <= 31:
        return False, f'지금 {round(temp)}도예요'
    if day and where:  # the real sunset for the date and place (Seoul, mid-November: about 17:17)
        sunrise, sunset = sun_times(day, where[0], where[1])
        now = hour * 60 + minute
        if not sunrise <= now <= sunset - PLAY_MINUTES:
            return False, '해가 져서 어두워졌어요' if now > sunset else '곧 해가 져요' if now > sunrise else '아직 어두워요'
    elif hour not in DAYLIGHT:
        return False, '날이 어두워졌어요'
    return True, f'지금 {round(temp)}도, 놀기 좋은 날씨예요' if temp is not None else '놀기 좋은 시간이에요'


DAYS = ('Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su')
STAY_MINUTES = 40  # a visit needs this long before closing time
UNKNOWN_HOURS_OK = (10 * 60, 17 * 60)  # a library without mapped hours: only well inside usual opening hours


def _minutes(clock: str) -> int:
    h, m = clock.split(':')
    return int(h) * 60 + int(m)


def hours_on(spec: str | None, weekday: int) -> list | None:
    """Opening intervals [(open, close) in minutes] on a weekday (0 = Monday) from a simple OSM
    opening_hours value such as 'Mo-Th 09:00-22:00, Sa-Su 09:00~20:00'. Days the value does not list
    are closed ([]); None when there is no value or it is too complex to read safely."""
    if not spec:
        return None
    if spec.strip() == '24/7':
        return [(0, 1440)]
    intervals, listed = [], False
    for rule in re.split(r'[;,]\s*(?=[A-Z][a-z]\b)', spec.strip()):
        found = re.fullmatch(r'\s*([A-Z][a-z])(?:\s*-\s*([A-Z][a-z]))?\s+(.+?)\s*', rule)
        if not found or found.group(1) not in DAYS or (found.group(2) and found.group(2) not in DAYS):
            return None
        first, last = DAYS.index(found.group(1)), DAYS.index(found.group(2) or found.group(1))
        days = set(range(first, last + 1)) if first <= last else set(range(first, 7)) | set(range(0, last + 1))
        times = re.findall(r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})', found.group(3))
        if not times and found.group(3).strip().lower() != 'off':
            return None
        if weekday in days:
            listed = True
            intervals = [(_minutes(a), _minutes(b)) for a, b in times]
    return intervals if listed else []


def open_for_visit(spec: str | None, weekday: int | None, arrive: int) -> tuple:
    """('open', closes 'HH:MM') when the place is open at `arrive` (minutes after midnight) and stays open
    long enough to visit; ('closed', None) when its hours say otherwise; ('unknown', None) without hours."""
    intervals = hours_on(spec, weekday) if weekday is not None else None
    if intervals is None:
        return 'unknown', None
    for start, end in intervals:
        if start <= arrive and arrive + STAY_MINUTES <= end:
            return 'open', f'{end // 60}:{end % 60:02d}'
    return 'closed', None


def kind_of(place: dict) -> str | None:
    if place['kind'] == 'library' and place['name']:
        return 'library'
    if place['kind'] == 'park' and place['name'] and (place.get('playground') or '어린이' in place['name']):
        return 'park'
    return None


def suggest(origin: tuple, dest: tuple, minutes: int, weather: dict, hour: int, album: dict | None,
            minute: int = 0, day: date | None = None) -> dict | None:
    """The best place on the way. A park only in daylight and dry weather; a library only when it is open
    when the car gets there (its mapped hours) or, without mapped hours, in the daytime."""
    liked, liked_count = interest(album)
    outdoor, sky = outdoor_ok(weather or {}, hour, minute, day, origin)
    weekday = day.weekday() if day else None
    best, best_score, considered = None, -99.0, 0
    for p in places():
        kind = kind_of(p)
        if not kind:
            continue
        t, off = along(origin, dest, (p['lat'], p['lon']))
        if not 0.08 <= t <= 0.92 or off > MAX_OFFSET_KM:
            continue
        hours, closes = ('unknown', None)
        if kind == 'park' and not outdoor:  # no playground in the dark or the rain
            continue
        if kind == 'library':
            hours, closes = open_for_visit(p.get('hours'), weekday, hour * 60 + minute + round(t * minutes))
            arrive = hour * 60 + minute + round(t * minutes)
            if hours == 'closed' or (hours == 'unknown' and not UNKNOWN_HOURS_OK[0] <= arrive <= UNKNOWN_HOURS_OK[1]):
                continue
        considered += 1
        score = (3.0 if kind == 'park' else 2.0) - 2.0 * off + (0.5 if 0.2 <= t <= 0.7 else 0.0)
        if kind == 'library' and liked in INDOOR_FOR:
            score += 1.5
        if '어린이' in p['name']:
            score += 0.5
        if score > best_score:
            best, best_score = {**p, 'type': kind, 'fraction': round(t, 3), 'offsetKm': round(off, 2), 'closes': closes}, score
    if not best:
        return None
    best['minutesAway'] = max(1, round(best['fraction'] * minutes))
    best['detourMinutes'] = max(2, round(2 * best['offsetKm'] / CITY_KMH * 60))
    best.update(interest=liked, interestCount=liked_count, outdoor=outdoor, sky=sky, considered=considered)
    return best


def subject(word: str) -> str:
    last = word[-1:] or ' '
    return word + ('이' if '가' <= last <= '힣' and (ord(last) - 0xAC00) % 28 else '가')


def vocative(name: str) -> str:
    last = name[-1:] or ' '
    return name + ('아' if '가' <= last <= '힣' and (ord(last) - 0xAC00) % 28 else '야')


def stop_speech(stop: dict, child: str, home: str, minutes: int) -> str:
    """Spoken to the driving parent: where, why it fits now, and a yes/no question."""
    # short spoken sentences: the 2026-11-14 review found Pli slow and stiff ("너무 느리잖아, 대사같은거")
    head = f"{home}까지 {minutes}분 남았어요. 가는 길에 {subject(stop['name'])} 있어요."
    if stop['type'] == 'library':
        why = (f"{child}이가 요즘 그림 좋아하잖아요. 그림책 보러 잠깐 들를까요?"
               if stop.get('interest') == '그림' else
               f"{child}이랑 {INDOOR_FOR.get(stop.get('interest'), '그림책')} 보러 잠깐 들를까요?")
    else:
        why = f"{stop['sky']}. 놀이터에서 잠깐 놀다 갈까요?"
    return f"{head} {why} {stop['detourMinutes']}분만 더 걸려요."


def stop_card(stop: dict, child: str, home: str, minutes: int) -> dict:
    reasons = [{'icon': '🧭', 'label': f"{stop['minutesAway']}분 뒤 지나가요", 'reason': f"{home}까지 {minutes}분 · 들러도 {stop['detourMinutes']}분"},
               {'icon': '☀️' if stop['outdoor'] else '🌙', 'label': stop['sky'], 'reason': '지금 날씨와 시간'}]
    if stop.get('closes'):
        reasons.append({'icon': '🕘', 'label': f"{stop['closes']}까지 열어요",
                        'reason': '운영시간 · 공개 안내' if stop.get('hoursSource') else '운영시간 · OpenStreetMap'})
    if stop.get('interest'):
        reasons.append({'icon': '🎨' if stop['interest'] == '그림' else '⭐', 'label': f"{child}이가 좋아하는 {stop['interest']}",
                        'reason': f"앨범 기록 {stop['interestCount']}번"})
    doing = ([{'icon': '📚', 'label': f"{INDOOR_FOR.get(stop.get('interest'), '그림책')} 고르기", 'reason': '도서관'}]
             if stop['type'] == 'library' else [{'icon': '🛝', 'label': '놀이터에서 놀기', 'reason': '공원 안 놀이터'}])
    return {'kind': 'stop', 'title': f'{home} 가는 길에 들를 곳', 'subtitle': stop['name'],
            'sections': [{'title': '왜 여기예요', 'items': reasons}, {'title': '할 수 있는 것', 'items': doing}],
            'place': {k: stop[k] for k in ('name', 'type', 'lat', 'lon', 'osm', 'minutesAway', 'detourMinutes')}}
