"""Live weather at the car's position: Pleos FusedLocation (sent by the app) + public forecasts.

The AI stays on the edge computer. Only a coarse position (0.01 degree, about 1 km) leaves it,
to fetch public weather data: Open-Meteo first, MET Norway when Open-Meteo does not answer
(both keyless). Answers are composed from the fetched numbers and the wiper signal only, so a
rain answer is never invented.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
MET_URL = 'https://api.met.no/weatherapi/locationforecast/2.0/compact'
MET_AGENT = 'pli-pleos-edge/1.0 (in-car weather answers)'  # MET Norway requires an identifying User-Agent
PRIMARY_BACKOFF_SECONDS = 600  # after an Open-Meteo failure, ask MET Norway directly for a while
SEOUL = ZoneInfo('Asia/Seoul')
PLACE_URL = 'https://api.bigdatacloud.net/data/reverse-geocode-client'
WEATHER_TTL_SECONDS = 600
PLACE_TTL_SECONDS = 86400
REQUEST_TIMEOUT_SECONDS = 3.5
COARSE_DIGITS = 2
RAIN_PROBABILITY = 50
RAIN_MM = 0.3

SKY = {0: '하늘이 맑아', 1: '하늘이 맑은 편이야', 2: '구름이 조금 있어', 3: '하늘이 흐려', 45: '안개가 꼈어', 48: '안개가 꼈어'}
SKY_AND = {0: '하늘이 맑고', 1: '하늘이 맑은 편이고', 2: '구름이 조금 있고', 3: '하늘이 흐리고', 45: '안개가 끼었고', 48: '안개가 끼었고'}
DAY_SKY = {0: '맑고', 1: '대체로 맑고', 2: '구름이 조금 끼고', 3: '흐리고', 45: '안개가 끼고', 48: '안개가 끼고'}
RAIN_CODES = set(range(51, 68)) | {80, 81, 82, 95, 96, 99}
SNOW_CODES = set(range(71, 78)) | {85, 86}
LABEL = {**{c: '맑음' for c in (0, 1)}, 2: '구름 조금', 3: '흐림', 45: '안개', 48: '안개',
         **{c: '비' for c in RAIN_CODES}, **{c: '눈' for c in SNOW_CODES}}
# MET Norway symbol (without _day/_night) -> the WMO code used above
MET_CODES = {'clearsky': 0, 'fair': 1, 'partlycloudy': 2, 'cloudy': 3, 'fog': 45}


@dataclass(frozen=True)
class Ask:
    topic: str  # rain | snow | temp | general
    when: str   # now | later | tomorrow


def parse(text: str) -> Ask:
    when = 'tomorrow' if '내일' in text else 'later' if re.search(r'(이따|오후|저녁|밤에|나중|조금 ?있다|오늘)', text) else 'now'
    if re.search(r'눈 ?(이 ?)?(와|오|올|내리)|눈사람|눈싸움', text):
        topic = 'snow'
    elif re.search(r'(비|우산|소나기|우비|장화|와이퍼)', text):
        topic = 'rain'
    elif re.search(r'(추워|더워|추울|더울|춥|덥|기온|몇 ?도|따뜻|쌀쌀)', text):
        topic = 'temp'
    else:
        topic = 'general'
    return Ask(topic, when)


def coarse(location: dict | None) -> tuple[float, float] | None:
    """Validate the app's position and blur it to about 1 km before it leaves the edge."""
    try:
        lat, lon = float(location['lat']), float(location['lon'])
    except (TypeError, KeyError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    return round(lat, COARSE_DIGITS), round(lon, COARSE_DIGITS)


def clock(hour: int) -> str:
    if hour == 0:
        return '밤 12시'
    if hour < 12:
        return f'오전 {hour}시'
    return '낮 12시' if hour == 12 else f'오후 {hour - 12}시'


class Weather:
    def __init__(self) -> None:
        self.session = None
        self.cache: dict = {}
        self.primary_failed_at = 0.0

    def bind(self, session) -> None:
        self.session = session

    async def _json(self, url: str, params: dict, headers: dict | None = None) -> dict:
        from aiohttp import ClientTimeout
        async with self.session.get(url, params=params, headers=headers,
                                    timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)) as r:
            r.raise_for_status()
            return await r.json(content_type=None)

    async def _cached(self, key: tuple, ttl: int, load):
        hit = self.cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        value = await load()
        self.cache[key] = (time.time(), value)
        return value

    async def _open_meteo(self, lat: float, lon: float) -> dict:
        params = {'latitude': lat, 'longitude': lon, 'timezone': 'Asia/Seoul', 'forecast_hours': 12, 'forecast_days': 2,
                  'current': 'temperature_2m,precipitation,rain,showers,snowfall,weather_code',
                  'hourly': 'precipitation_probability,precipitation,weather_code',
                  'daily': 'weather_code,precipitation_probability_max,precipitation_sum,temperature_2m_max,temperature_2m_min'}
        return await self._cached(('wx', lat, lon), WEATHER_TTL_SECONDS, lambda: self._json(FORECAST_URL, params))

    async def _met(self, lat: float, lon: float) -> dict:
        async def load() -> dict:
            data = await self._json(MET_URL, {'lat': lat, 'lon': lon}, {'User-Agent': MET_AGENT})
            return from_met(data, datetime.now(SEOUL))
        return await self._cached(('met', lat, lon), WEATHER_TTL_SECONDS, load)

    async def forecast(self, lat: float, lon: float) -> tuple[dict, str]:
        """Open-Meteo, or MET Norway in the same shape when Open-Meteo is down."""
        if time.time() - self.primary_failed_at > PRIMARY_BACKOFF_SECONDS:
            try:
                return await self._open_meteo(lat, lon), 'Open-Meteo'
            except Exception:
                self.primary_failed_at = time.time()
        return await self._met(lat, lon), 'MET Norway'

    async def place(self, lat: float, lon: float) -> str:
        async def load() -> str:
            data = await self._json(PLACE_URL, {'latitude': lat, 'longitude': lon, 'localityLanguage': 'ko'})
            levels = (data.get('localityInfo') or {}).get('administrative') or []
            district = next((a.get('name') for a in levels if a.get('adminLevel') == 6 and a.get('name')), '')
            return district or data.get('city') or data.get('locality') or ''
        try:
            return await self._cached(('place', lat, lon), PLACE_TTL_SECONDS, load)
        except Exception:  # the place name is decoration; the weather answer stands without it
            return ''

    async def lookup(self, location: dict | None) -> dict:
        position = coarse(location)
        if position is None:
            return {'ok': False, 'reason': 'no-location'}
        try:
            (data, source), place = await asyncio.gather(self.forecast(*position), self.place(*position))
        except Exception as exc:
            return {'ok': False, 'reason': type(exc).__name__, 'position': position}
        return {'ok': True, 'position': position, 'place': place, 'source': source, **summarize(data)}


def met_code(symbol: str | None) -> int:
    name = (symbol or '').split('_')[0]
    if 'thunder' in name:
        return 95
    if 'snow' in name:
        return 73 if name.startswith('heavy') else 71
    if 'sleet' in name or 'rain' in name:
        return 65 if name.startswith('heavy') else 61
    return MET_CODES.get(name, 3)


def from_met(data: dict, now: datetime) -> dict:
    """MET Norway compact forecast -> the Open-Meteo shape summarize() reads.

    MET gives amounts but no precipitation probability, so chances stay None
    and the answer speaks in millimetres instead of percentages.
    """
    series = (data.get('properties') or {}).get('timeseries') or []
    rows = []
    for entry in series:
        at = datetime.fromisoformat(entry['time'].replace('Z', '+00:00')).astimezone(SEOUL)
        info = entry.get('data') or {}
        hour = (info.get('next_1_hours') or {})
        rows.append({'at': at, 'temp': (info.get('instant') or {}).get('details', {}).get('air_temperature'),
                     'mm': (hour.get('details') or {}).get('precipitation_amount'),
                     'code': met_code((hour.get('summary') or {}).get('symbol_code')) if hour else None})
    hourly = [r for r in rows if r['code'] is not None]
    if not hourly:
        raise ValueError('MET Norway returned no hourly forecast')
    current = next((r for r in hourly if r['at'] <= now < r['at'] + timedelta(hours=1)), hourly[0])
    stamp = lambda d: d.strftime('%Y-%m-%dT%H:%M')
    upcoming = [r for r in hourly if r['at'] > current['at']][:12]
    tomorrow = (now + timedelta(days=1)).date()
    day = [r for r in hourly if r['at'].date() == tomorrow]
    daily = {'time': [stamp(now)[:10], tomorrow.isoformat()]}
    if day:
        wet = [r['code'] for r in day if r['code'] in RAIN_CODES | SNOW_CODES and (r['mm'] or 0) > 0]
        total = sum(r['mm'] or 0 for r in day)
        dry = [r['code'] for r in day if r['code'] not in RAIN_CODES | SNOW_CODES] or [3]
        rainy = len(wet) >= 3 or total >= 1  # one passing light-rain hour is not a rainy day
        daily.update(weather_code=[None, max(set(wet), key=wet.count) if rainy and wet else max(set(dry), key=dry.count)],
                     precipitation_probability_max=[None, None],
                     precipitation_sum=[None, round(sum(r['mm'] or 0 for r in day), 1)],
                     temperature_2m_max=[None, max(r['temp'] for r in day if r['temp'] is not None)],
                     temperature_2m_min=[None, min(r['temp'] for r in day if r['temp'] is not None)])
    else:
        daily = {}
    return {'current': {'time': stamp(current['at']), 'temperature_2m': current['temp'], 'precipitation': current['mm'] or 0,
                        'weather_code': current['code']},
            'hourly': {'time': [stamp(r['at']) for r in upcoming], 'precipitation_probability': [None] * len(upcoming),
                       'precipitation': [r['mm'] for r in upcoming], 'weather_code': [r['code'] for r in upcoming]},
            'daily': daily}


def summarize(data: dict) -> dict:
    now = data.get('current') or {}
    hourly = data.get('hourly') or {}
    daily = data.get('daily') or {}
    code = int(now.get('weather_code') or 0)
    falling = float(now.get('precipitation') or 0) + float(now.get('rain') or 0) + float(now.get('showers') or 0)
    snow = float(now.get('snowfall') or 0)
    soon = None
    current_hour = str(now.get('time', ''))[:13]
    for stamp, chance, amount, hcode in zip(hourly.get('time', []), hourly.get('precipitation_probability', []),
                                            hourly.get('precipitation', []), hourly.get('weather_code', [])):
        if stamp[:13] <= current_hour:
            continue
        if (chance or 0) >= RAIN_PROBABILITY or (amount or 0) >= RAIN_MM:
            soon = {'hour': int(stamp[11:13]), 'chance': chance, 'snow': hcode in SNOW_CODES}
            break
    chances = [c for c in hourly.get('precipitation_probability', []) if c is not None]
    peak = max(chances) if chances else None  # None: the source gives amounts only
    upcoming_mm = round(sum(a or 0 for a in hourly.get('precipitation', [])), 1)
    tomorrow = None
    if len(daily.get('time', [])) > 1:
        tomorrow = {'code': int(daily['weather_code'][1] or 0), 'chance': daily['precipitation_probability_max'][1],
                    'mm': daily['precipitation_sum'][1], 'max': daily['temperature_2m_max'][1], 'min': daily['temperature_2m_min'][1]}
    return {'code': code, 'label': LABEL.get(code, '구름'), 'temp': now.get('temperature_2m'), 'precipMm': round(falling, 1),
            'raining': falling > 0 or code in RAIN_CODES, 'snowing': snow > 0 or code in SNOW_CODES,
            'soon': soon, 'peakChance': peak, 'upcomingMm': upcoming_mm, 'tomorrow': tomorrow, 'observedAt': now.get('time')}


def observation(w: dict, wiper: bool | None) -> str:
    """One line of facts for the agent trace."""
    if not w.get('ok'):
        return '위치 신호 없음' if w.get('reason') == 'no-location' else '날씨 서버 응답 없음'
    ahead = (f"12시간 내 비 확률 최대 {w['peakChance']}%" if w.get('peakChance') is not None
             else f"12시간 내 예상 강수 {w.get('upcomingMm', 0)}mm")
    parts = [w['place'] or '현재 위치', w['label'], f"{w['temp']}°C", f"강수 {w['precipMm']}mm", ahead]
    if w.get('tomorrow'):
        t = w['tomorrow']
        parts.append(f"내일 비 확률 {t['chance']}%" if t['chance'] is not None else f"내일 예상 강수 {t['mm']}mm")
    if w.get('source'):
        parts.append(w['source'])
    if wiper is not None:
        parts.append('와이퍼 최근 작동' if wiper else '와이퍼 꺼짐')
    return ' · '.join(parts)


def _josa(word: str, with_final: str, without_final: str) -> str:
    last = word[-1] if word else ''
    has_final = '가' <= last <= '힣' and (ord(last) - 0xAC00) % 28 != 0
    return word + (with_final if has_final else without_final)


def _here(w: dict, marker: str) -> str:
    """'지금 서초구에는' / '지금 서초구는', falling back to the car's position without a name."""
    place = w.get('place') or '우리 차가 있는 곳'
    return f"지금 {place}에는" if marker == '에는' else f"지금 {_josa(place, '은', '는')}"


def _upcoming(w: dict, ask: Ask) -> str:
    soon = w.get('soon')
    if soon:
        return f"{clock(soon['hour'])}쯤부터 {'눈' if soon['snow'] else '비'} 소식이 있어. 우산 챙기자!"
    calm = '앞으로 12시간은 비 소식이 없어.' if ask.when == 'later' else ''
    t = w.get('tomorrow')
    if t and ((t['chance'] or 0) >= 70 or (t['mm'] or 0) >= 5):
        return (calm + ' 내일은 비가 온대.').strip()
    if t and ((t['chance'] or 0) >= 40 or (t['mm'] or 0) >= 1):
        return (calm + ' 내일은 비가 올 수도 있대.').strip()
    return calm


def _feel(temp: float) -> str:
    if temp < 5:
        return '많이 추우니까 따뜻하게 입자!'
    if temp < 12:
        return '쌀쌀하니까 겉옷 꼭 챙기자.'
    return '딱 좋은 날씨야.' if temp < 25 else '더우니까 물 자주 마시자.'


def _tomorrow(w: dict) -> str:
    t = w['tomorrow']
    place = _josa(w.get('place') or '이곳', '은', '는')
    wet = (t['chance'] or 0) >= 40 or (t['mm'] or 0) >= 1 or t['code'] in RAIN_CODES | SNOW_CODES
    known = t['chance'] is not None
    if t['code'] in SNOW_CODES:
        head = f'내일 {place} 눈 소식이 있어.'
    elif t['code'] in RAIN_CODES:
        head = f'내일 {place} 비 소식이 있어.'
    elif known:
        head = f"내일 {place} {DAY_SKY.get(t['code'], '구름이 끼고')} 비 올 확률은 {t['chance']}%야."
    else:
        rain = '비는 조금 올 수도 있대.' if wet else '비 소식은 없어.'
        head = f"내일 {place} {DAY_SKY.get(t['code'], '구름이 끼고')} {rain}"
    if t['code'] in RAIN_CODES | SNOW_CODES:
        amount = f"비 올 확률은 {t['chance']}%" if known else f"비는 {t['mm']:g}mm쯤 온다고 하고"
        body = f" {amount}, 가장 따뜻할 때 {round(t['max'])}도래."
    else:
        body = f" 가장 따뜻할 때 {round(t['max'])}도래."
    return head + body + (' 우산 챙기면 좋겠어!' if wet else '')


def speech(w: dict, ask: Ask, wiper: bool | None) -> str:
    """A short, child-friendly answer built only from fetched data and the wiper signal."""
    if not w.get('ok'):
        lead = '아직 우리 차 위치를 몰라서' if w.get('reason') == 'no-location' else '지금은 기상 정보에 연결되지 않아서'
        if wiper:
            return f'{lead} 정확히는 모르지만, 와이퍼가 움직인 걸 보니 비가 오는 것 같아.'
        return f'{lead} 날씨는 잘 모르겠어. 창밖을 같이 볼까?'
    if ask.when == 'tomorrow' and w.get('tomorrow'):
        return _tomorrow(w)
    if w['raining']:
        extra = ' 와이퍼도 열심히 움직이고 있네.' if wiper else ''
        return f"{_here(w, '에는')} 비가 오고 있어.{extra} 내릴 때 우산 꼭 쓰자!"
    if w['snowing']:
        return f"{_here(w, '에는')} 눈이 내리고 있어! 미끄러우니까 천천히 걷자."
    temp = round(float(w['temp'])) if w.get('temp') is not None else None
    if ask.topic == 'temp' and temp is not None:
        return f"{_here(w, '는')} {temp}도야. {_feel(temp)}"
    sky = SKY_AND.get(w['code'], '구름이 끼었고')
    weather = f'{sky} 기온은 {temp}도야.' if temp is not None else SKY.get(w['code'], '구름이 끼었어') + '.'
    if ask.topic in ('rain', 'snow'):
        head = f"{_here(w, '에는')} {'눈이' if ask.topic == 'snow' else '비가'} 안 와. {weather}"
    else:
        head = f"{_here(w, '는')} {weather}"
    note = ' 그런데 와이퍼가 움직였네. 창문에 물이 묻었나 봐.' if wiper else ''
    later = _upcoming(w, ask)
    return head + note + (' ' + later if later else '')
