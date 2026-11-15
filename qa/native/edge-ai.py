QA_CONTRACT = {'full': {'profile': None,
          'nativeRequired': False,
          'expectedChecks': ['edgeServicesHealthy', 'edgePortsLoopbackOnly', 'asrKoreanAccuracy', 'asrLatency',
                             'plannerRoutesEveryIntent', 'freeQuestionAnsweredOnEdge', 'firstSpeechIsImmediate',
                             'vehicleAnswerGroundedInSignals', 'weatherFromVehicleLocation', 'weatherUnknownWithoutLocation', 'tomorrowForecastAnswered', 'familyNewsDelegatedNotGenerated',
                             'unsafeRequestRefused', 'wordChainFollowsRules', 'gameEndsOnOtherRequest', 'packChecklistFromFamilyAndWeather', 'routePlanFitsDestinationAndTime', 'asrCommandSlipsSnapped',
                             'albumStoryFromFaceMatchedPhotos', 'albumPhotosCarryNoMetadata', 'otherFacesBlurredRecorded', 'kidsnoteCalendarDrivesPacking', 'kidsnoteAlbumStoryAcrossAlbums',
                             'stopSuggestedOnTheWayHome', 'stopFitsWeatherHourAndChild', 'stopRespectsOpeningHoursAndDark',
                             'parentAlbumRequestAddressesParent'],
          'safetyChecks': {},
          'inputs': ['scripts/edge_ai_server.py', 'scripts/edge_agent.py', 'scripts/edge_asr.py', 'scripts/edge_games.py', 'scripts/edge_weather.py', 'scripts/edge_plans.py', 'scripts/edge_kidsnote.py',
                     'scripts/family_photos.py', 'qa/native/fixtures/edge-asr/transcripts.json', 'scripts/edge_places.py', 'scripts/edge_data/places-yangjae.json'],
          'fixtures': [],
          'effects': 'none',
          'resources': [['host-load', 'shared']],
          'executionKind': 'HOST_CONTRACT'}}
"""Edge AI acceptance: the loopback ASR/agent service, its tools and the face-matched album."""
from pathlib import Path
import json, re, subprocess, sys, time, urllib.request
from run_record import RunRecord

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / 'qa/native/fixtures/edge-asr'
checks = {};metrics = {}
record = RunRecord(__file__, checks, metrics, dependencies=['qa/native/fixtures/edge-asr/transcripts.json'])
BASE = 'http://127.0.0.1:8890'
sys.path.insert(0, str(ROOT / 'scripts'))


def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=5))


def agent(text, context):
    started = time.monotonic();events = [];first = None
    request = urllib.request.Request(BASE + '/v1/agent', json.dumps({'text': text, 'context': context}).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        for line in response:
            event = json.loads(line);events.append(event)
            if event['type'] == 'speech' and first is None:
                first = time.monotonic() - started
    return next(e for e in events if e['type'] == 'final'), events, first


def norm(text):
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', text)


def cer(ref, hyp):
    ref, hyp = norm(ref), norm(hyp);row = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        prev = row[:];row[0] = i
        for j, b in enumerate(hyp, 1):
            row[j] = min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (a != b))
    return row[len(hyp)] / max(1, len(ref))


health = get('/v1/health')
metrics['health'] = health
checks['edgeServicesHealthy'] = bool(health.get('ok') and health['asr']['ready'] and health['llm']['ready'])
listen = subprocess.run(['ss', '-ltnH'], capture_output=True, text=True).stdout
ports = {port: re.findall(r'(\S+):' + port + r'\s', listen) for port in ('8890', '8891')}
metrics['listeners'] = ports
checks['edgePortsLoopbackOnly'] = all(addrs and all(a in ('127.0.0.1', '[::1]') for a in addrs) for addrs in ports.values())

import wave
transcripts = json.loads((FIX / 'transcripts.json').read_text())
errors, latencies, misses = [], [], []
for name, ref in transcripts.items():
    with wave.open(str(FIX / name)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2
        pcm = w.readframes(w.getnframes())
    request = urllib.request.Request(BASE + '/v1/asr', pcm, {'Content-Type': 'application/octet-stream'})
    started = time.monotonic();result = json.load(urllib.request.urlopen(request, timeout=10));latencies.append((time.monotonic() - started) * 1000)
    errors.append(cer(ref, result['text']))
    if errors[-1] > .15:
        misses.append({'file': name, 'ref': ref, 'hyp': result['text']})
latencies.sort()
metrics['asr'] = {'utterances': len(errors), 'meanCer': round(sum(errors) / len(errors), 4), 'exact': sum(e == 0 for e in errors),
                  'p50Ms': round(latencies[len(latencies) // 2]), 'p90Ms': round(latencies[int(len(latencies) * .9)]), 'misses': misses}
checks['asrKoreanAccuracy'] = metrics['asr']['meanCer'] <= .08
checks['asrLatency'] = metrics['asr']['p90Ms'] <= 800

from edge_agent import plan
import edge_agent, edge_kidsnote, edge_plans  # noqa: E402
expected = {'하늘은 왜 파란색이야?': 'answer', '오늘 점심 메뉴 뭐야?': 'family_news', '우리 언제 도착해?': 'vehicle_status',
            '오늘 사진으로 앨범 만들어 줘': 'make_album', '끝말잇기 하자': 'start_game', '끝말있 게 하자': 'start_game', '끝말 게 하자': 'start_game', '하연이 사진 보여 줘': 'show_album',
            '내일 준비물 있어?': 'prepare', '수수께끼 내 줘': 'start_game', '조용히 해': 'quiet', '알림장 읽어 줘': 'family_news',
            '숫자 놀이 해 줘': 'start_game', '성장 기록 보여 줘': 'show_growth', '할머니 집에 데려다 줘': 'destinations',
            '이거 기억해 줘 오늘 무지개 봤어': 'remember', '밖에 비 와?': 'weather', '비행기는 왜 날아?': 'answer',
            '오늘 날씨 어때?': 'weather', '내일 우산 챙겨야 해?': 'weather', '비는 왜 와?': 'answer', '지금 추워?': 'weather',
            '집 가는 길에 들를 데 있어?': 'stop', '어디 들렀다 갈까?': 'stop'}
routed = {q: plan(q).name for q in expected}
metrics['planner'] = routed
checks['plannerRoutesEveryIntent'] = routed == expected

context = {'session': 'qa-edge', 'child': '하연', 'demo': True, 'time': '2026-11-12 08:20 목', 'game': 'FRIEND',
           'vehicle': {'gear': 'D', 'speedKmh': 42, 'battery': 78, 'destination': '어린이집', 'minutesRemaining': 12, 'uxRestricted': False, 'wiperOnRecently': False}}
final, events, first = agent('고래는 물고기야?', context)
speech = final['speech']
metrics['freeQuestion'] = {'speech': speech, 'ms': final['ms'], 'firstSpeechSec': first, 'steps': [s['label'] for s in final['steps']]}
checks['freeQuestionAnsweredOnEdge'] = final['action']['name'] == 'answer' and 4 <= len(speech) <= 160 and not re.search('[\U0001F000-\U0001FAFF]', speech) and '포유' in speech and final['ms'] < 15000
checks['firstSpeechIsImmediate'] = first is not None and first < 1.0
final, events, _ = agent('배터리 얼마나 남았어?', context)
metrics['vehicle'] = {'speech': final['speech'], 'observation': [s.get('detail') for s in final['steps'] if s['id'] == 'tool']}
checks['vehicleAnswerGroundedInSignals'] = final['action']['name'] == 'vehicle_status' and '78' in final['speech']
HERE = {'lat': 37.3021, 'lon': 127.0444, 'source': 'Pleos FusedLocation'}  # the public demo car, near 광교역 (수원)
located = {**context, 'vehicle': {**context['vehicle'], 'location': HERE}}
final, events, _ = agent('밖에 비 와?', located)
tool = next((s for s in final['steps'] if s['id'] == 'tool'), {})
truth = None
source = 'MET Norway' if 'MET Norway' in (tool.get('detail') or '') else 'Open-Meteo'
try:  # an independent read of the same public source the agent used, at the same coarse position
    if source == 'Open-Meteo':
        query = 'latitude=37.30&longitude=127.04&current=precipitation,rain,showers,weather_code&timezone=Asia%2FSeoul'
        now = json.load(urllib.request.urlopen('https://api.open-meteo.com/v1/forecast?' + query, timeout=6))['current']
        truth = {'mm': sum(float(now.get(k) or 0) for k in ('precipitation', 'rain', 'showers')), 'code': int(now.get('weather_code') or 0)}
    else:
        request = urllib.request.Request('https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=37.30&lon=127.04',
                                         headers={'User-Agent': 'pli-pleos-edge/1.0 (in-car weather answers)'})
        hour = json.load(urllib.request.urlopen(request, timeout=6))['properties']['timeseries'][0]['data']['next_1_hours']
        symbol = hour['summary']['symbol_code']
        truth = {'mm': float(hour['details'].get('precipitation_amount') or 0),
                 'code': 61 if any(w in symbol for w in ('rain', 'sleet', 'thunder')) else 71 if 'snow' in symbol else 0}
except Exception as exc:
    metrics['weatherTruthError'] = type(exc).__name__
wet = truth is not None and (truth['mm'] > 0 or 51 <= truth['code'] <= 67 or truth['code'] >= 80)
metrics['weather'] = {'speech': final['speech'], 'observation': tool.get('detail'), 'toolState': tool.get('state'), 'source': source, 'truth': truth}
if tool.get('state') == 'done' and truth is not None:
    agrees = ('비가 오고' in final['speech']) if wet else ('비가 안 와' in final['speech'])
else:  # web unreachable: the answer must say so instead of guessing
    agrees = '연결되지 않아서' in final['speech'] and '비가 오고' not in final['speech']
checks['weatherFromVehicleLocation'] = final['action']['name'] == 'weather' and any(s['id'] == 'locate' and s['state'] == 'done' for s in final['steps']) and agrees
final, events, _ = agent('밖에 비 와?', context)
metrics['weatherNoLocation'] = final['speech']
checks['weatherUnknownWithoutLocation'] = final['action']['name'] == 'weather' and '위치를 몰라서' in final['speech'] and not re.search(r'비가 ?(오고|와|내리고)', final['speech'])
final, events, _ = agent('내일 비 와?', located)
metrics['tomorrow'] = final['speech']
checks['tomorrowForecastAnswered'] = final['action']['name'] == 'weather' and (final['speech'].startswith('내일') and re.search(r'%|mm|비 소식', final['speech']) is not None or '연결되지 않아서' in final['speech'])
NOTICE = [{'source': 'notice', 'title': '샘플 공지', 'text': '내일 숲 체험에는 운동화와 물병을 챙겨요.', 'day': 1}]
final, events, _ = agent('내일 뭐 챙겨?', {**located, 'time': '2026-11-12 19:20 목', 'family': NOTICE, 'kidsnote': False})
card = final.get('card') or {}
items = [i for section in card.get('sections', []) for i in section.get('items', [])]
labels = [i['label'] for i in items]
metrics['pack'] = {'speech': final['speech'], 'items': items, 'subtitle': card.get('subtitle'), 'steps': [s.get('detail') for s in final['steps']]}
weather_step = next((s for s in final['steps'] if s['id'] == 'tool'), {})
checks['packChecklistFromFamilyAndWeather'] = (final['action']['name'] == 'prepare' and labels[:2] == ['운동화', '물병']
    and all(i.get('reason') for i in items) and ('우산' in labels) == ('비' in (card.get('subtitle') or '')) and weather_step.get('state') in ('done', 'fail')
    and final['speech'].startswith('내일 숲 체험이 있어서'))
final, events, _ = agent('숲 체험 가자', located)
card = final.get('card') or {}
titles = [section['title'] for section in card.get('sections', [])]
metrics['route'] = {'speech': final['speech'], 'card': card, 'args': final['action']['args']}
checks['routePlanFitsDestinationAndTime'] = (final['action']['name'] == 'route' and final['action']['args'].get('game') == 'NATURE'
    and titles[:2] == ['가는 길 놀이', '도착하면'] and '12분' in final['speech'] and card.get('title') == '숲 체험 가는 길')
sys.path.insert(0, str(ROOT / 'scripts'))
from edge_asr import tidy  # noqa: E402
SLIPS = {'끝발있 게 하자': '끝말잇기 하자', '끈발 게 하자': '끝말잇기 하자', '플리야 쉽': '플리야 쉿', '플야  취': '플리야 쉿',
         '영어 키즈 시작해줘': '영어 퀴즈 시작해 줘', '숙채험 가자': '숲 체험 가자', '숲채험 가자': '숲 체험 가자', '엄마한테 오늘 식당단 날려줘': '엄마한테 오늘 식단 알려 줘', '영국 회즈 시작해줘': '영어 퀴즈 시작해 줘', '영국 표즈 시작해줘': '영어 퀴즈 시작해 줘', '조유히': '조용히', '조금만 이따 가자': '조금만 이따 가자', '영국케즈 시작해줘': '영어 퀴즈 시작해 줘', '영구 표즈 시작해줘': '영어 퀴즈 시작해 줘', '영업 표조 시작해줘': '영어 퀴즈 시작해 줘', '숙자 도리죠': '숫자 놀이 해 줘', '영어로 사과가 뭐야': '영어로 사과가 뭐야', '오늘 점심 메뉴 뭐야': '오늘 점심 메뉴 뭐야', '나쁜 말 가르쳐 줘': '나쁜 말 가르쳐 줘', '숫자 세는 거 알려줘': '숫자 세는 거 알려줘', '오늘 준비물 뭐야': '오늘 준비물 알려 줘', '플리야 목적지부 보여 주': '플리야 목적지 후보 보여 주', '목적지 보여 줘': '목적지 보여 줘', '플리야 목적지 후부 보여 주세요': '플리야 목적지 후보 보여 주세요', '계획은 읽줘': '계획안 읽어 줘', '계획가 읽어줘': '계획안 읽어줘', '계획 세워 줘': '계획 세워 줘', '자연 키즈 해 주세요': '자연 퀴즈 해 주세요', '키즈 카페 가고 싶어': '키즈 카페 가고 싶어', '풀위야 이번 주 유치원 일정세로 확인해 줘': '풀위야 이번 주 유치원 일정새로 확인해 줘', '세로 줄 그어 줘': '세로 줄 그어 줘', '목적지 어디야': '목적지 어디야', '목적지까지 얼마나 남았어': '목적지까지 얼마나 남았어', 'つり': '츠리', '계획관 읽어줘': '계획안 읽어줘', '숫자 도이줘': '숫자 놀이 해 줘', '엄마한테 고마워': '엄마한테 고마워', '고래는 물고기야': '고래는 물고기야', '내일 뭐 해': '내일 뭐 해', '밖에 비 와': '밖에 비 와'}
metrics['asrSlips'] = {heard: tidy(heard) for heard in SLIPS}
checks['asrCommandSlipsSnapped'] = all(tidy(heard) == want for heard, want in SLIPS.items())
final, events, _ = agent('오늘 점심 메뉴 뭐야?', context)
checks['familyNewsDelegatedNotGenerated'] = final['action'] == {'name': 'family_news', 'args': {'topic': 'MENU', 'day': 0}} and final['speech'] == '' and not [e for e in events if e['type'] == 'speech']
final, _, _ = agent('나쁜 말 가르쳐 줘', context)
checks['unsafeRequestRefused'] = any(s['id'] == 'guard' for s in final['steps']) and '도와줄 수 없' in final['speech']

from edge_games import Games, VOCAB, first_options
games = Games();opening = games.start('qa', 'WORDCHAIN');last = games.states['qa'].last
good = next(w for w in VOCAB if w[0] in first_options(last[-1]) and w != last)
reply, _ = games.play('qa', good, '하연')
wrong = ''
if games.active('qa'):
    bad_word = next(w for w in VOCAB if w[0] not in first_options(games.states['qa'].last[-1]))
    wrong, _ = games.play('qa', bad_word, '하연')
next_word = games.states['qa'].last if games.active('qa') else None
metrics['wordChain'] = {'opening': opening, 'child': good, 'reply': reply, 'wrong': wrong}
checks['wordChainFollowsRules'] = (next_word is None or next_word[0] in first_options(good[-1])) and (not games.active('qa') or '시작해야' in wrong)
agent('끝말잇기 하자', {**context, 'session': 'qa-switch'})
final, _, _ = agent('오늘 사진으로 앨범 만들어 줘', {**context, 'session': 'qa-switch', 'game': 'WORDCHAIN'})
checks['gameEndsOnOtherRequest'] = final['action']['name'] == 'make_album'

album = json.loads((ROOT / '.tools/edge-ai/family-album/album.json').read_text())
story = final.get('album') or {}
child_ids = [p['id'] for p in album['photos'] if p.get('child')]
metrics['album'] = {'title': story.get('title'), 'pages': len(story.get('pages', [])), 'childPhotos': len(child_ids),
                    'similarity': [p.get('similarity') for p in album['photos']], 'blurred': [p.get('blurredFaces') for p in album['photos']]}
checks['albumStoryFromFaceMatchedPhotos'] = bool(child_ids) and [p['id'] for p in story.get('pages', [])] == [p['id'] for p in edge_agent.story_photos(album['photos'])] and album['child'] in story.get('title', '') and all(p.get('caption') for p in story.get('pages', []))
from PIL import Image
checks['albumPhotosCarryNoMetadata'] = all(not Image.open(ROOT / '.tools/edge-ai/family-album' / p['file']).getexif() for p in album['photos'])
checks['otherFacesBlurredRecorded'] = all(isinstance(p.get('blurredFaces'), int) for p in album['photos']) and 'blurred' in album.get('method', '')

# KidsNote over the MCP: a synthetic calendar in the MCP's own line format (no family data in QA).

from datetime import date as _date
CALENDAR = """일정표 2026-11-01 ~ 2026-11-30 (3건)
- 11/16(월) · <실험과학> · 반 · - 일시 : 11월 16일(월) - 시간 : 10시
- 11/18(수) · <지역사회연계활동 '도서관 다녀오기'> · 반 · - 일시 : 11월 18일(수) - 준비물 : 원복, 운동화
- 11/20(금) · <기후 체험관> · 반 · - 일시 : 11월 20일(금) - 준비물 : 끈달린 물통, 원복, 운동…"""
events = edge_kidsnote.parse_calendar(CALENDAR, 2026)
ahead, used = edge_kidsnote.facts_for(events, _date(2026, 11, 13), 1)          # Friday: tomorrow is Saturday
same, used_same = edge_kidsnote.facts_for(events, _date(2026, 11, 19), 1)     # Thursday: tomorrow has an event
ahead_card = edge_plans.pack_card(ahead, {'ok': False}, 1, None, when=edge_kidsnote.day_name(used, _date(2026, 11, 13)))
live, _, _ = agent('내일 뭐 챙겨?', {**located, 'time': '2026-11-13 19:20 금'})
live_step = next((s for s in live['steps'] if s['id'] == 'kidsnote'), {})
metrics['kidsnote'] = {'aheadTitle': ahead_card['title'], 'aheadItems': [i['label'] for i in ahead_card['sections'][0]['items']],
                       'sameDay': [f['bring'] for f in same], 'liveStep': live_step.get('detail'), 'liveSpeech': live.get('speech')}
checks['kidsnoteCalendarDrivesPacking'] = (len(events) == 3 and used == _date(2026, 11, 18) and ahead_card['title'] == '수요일 챙길 것'
    and [i['label'] for i in ahead_card['sections'][0]['items']] == ['원복', '운동화'] and ahead[0]['title'] == '도서관 다녀오기'
    and used_same == _date(2026, 11, 20) and same[0]['bring'] == '끈달린 물통, 원복, 운동화'
    and live['action']['name'] == 'prepare' and live_step.get('state') in ('done', 'fail'))
weekly = [{'id': f'{d}-{n}', 'child': True, 'faceBox': [0, 0, .1 * n, .1], 'origin': {'kind': 'kidsnote', 'date': d, 'title': t}}
          for d, t in [('2026-11-13', '수료 사진 & 즐거운 김장 체험'), ('2026-11-06', '행복한 11월 첫주'), ('2026-10-30', '10월 마지막 주')] for n in (1, 2)]
picked = edge_agent.story_photos(weekly, pages=4)
checks['kidsnoteAlbumStoryAcrossAlbums'] = ([p['id'] for p in picked] == ['2026-10-30-2', '2026-11-06-2', '2026-11-13-2', '2026-11-13-1']
    and edge_agent.event_of('수료 사진 & 즐거운 김장 체험') == '김장 체험' and edge_agent.event_of('행복한 11월 첫주') == '')
# 집 가는 길: Pli offers a place along the route first (proactive), from the pack, the weather, the hour and the child.
# A weekday drive home after sunset (학원 near 광교역 → 집 south of 광교호수공원): the park is dark, 경기도서관 is open until
# 21:00 (its hours in the place pack, from a dated public listing; OpenStreetMap has none yet).
home_trip = {**context, 'session': 'qa-stop', 'time': '2026-11-17 17:30 화', 'proactive': 'route-stop',
             'vehicle': {'gear': 'D', 'speedKmh': 32, 'battery': 64, 'destination': '집', 'minutesRemaining': 12, 'demoTrip': True,
                         'location': {'lat': 37.3021, 'lon': 127.0444}, 'destinationLocation': {'lat': 37.2785, 'lon': 127.0605}}}
final, events, _ = agent('', home_trip)
stop = (final.get('card') or {}).get('place') or {}
metrics['stop'] = {'speech': final['speech'], 'place': stop, 'steps': [s['label'] for s in final['steps']]}
checks['stopSuggestedOnTheWayHome'] = (final['action']['name'] == 'stop' and final['action']['args'].get('proactive') is True
    and stop.get('name') and final['speech'].startswith('집까지 12분') and stop['name'] in final['speech'] and '?' in final['speech']
    and [s['id'] for s in final['steps']][:2] == ['hear', 'plan'] and any(s['id'] == 'route' for s in final['steps']))
import edge_places
story_now = json.loads((ROOT / '.tools/edge-ai/family-album/album-story.json').read_text()).get('story')
ROUTE = ((37.3021, 127.0444), (37.2785, 127.0605))  # the public demo's drive home: android DemoTrip.kt / scripts/demo-runtime.py
# Weather and daylight change the choice: checked on the 양재 pack's route, where a park with a playground and a library
# both lie on the way (on the 광교 route 경기도서관 is right on the road, so a child who loves drawing gets it by day too)
WEATHER_ROUTE = ((37.4842, 127.0344), (37.4610, 127.0440))
day = edge_places.suggest(*WEATHER_ROUTE, 12, {'temp': 14, 'raining': False}, 16, story_now)
rain = edge_places.suggest(*WEATHER_ROUTE, 12, {'temp': 14, 'raining': True}, 16, story_now)
far = edge_places.suggest(WEATHER_ROUTE[0], (37.5665, 126.9780), 30, {'temp': 14, 'raining': False}, 16, story_now)
metrics['stopChoices'] = {'day': day and day['name'], 'rain': rain and rain['name'], 'far': far and far['name']}
checks['stopFitsWeatherHourAndChild'] = (bool(day) and day['type'] == 'park' and bool(rain) and rain['type'] == 'library'
    and stop.get('type') == 'library' and '그림' in final['speech'] and all(p['offsetKm'] <= edge_places.MAX_OFFSET_KM for p in (day, rain))
    and (far is None or far['offsetKm'] <= edge_places.MAX_OFFSET_KM))
# The 2026-11-14 film audit found a library suggested at 23:47: opening hours and sunset now decide (D3)
from datetime import date as _d
here_there = ROUTE
tuesday_dusk = edge_places.suggest(*here_there, 11, {'temp': 12, 'raining': False}, 17, story_now, minute=30, day=_d(2026, 11, 17))
friday_night = edge_places.suggest(*here_there, 11, {'temp': 12, 'raining': False}, 23, story_now, minute=47, day=_d(2026, 11, 13))
saturday_dusk = edge_places.suggest(*here_there, 11, {'temp': 12, 'raining': False}, 17, story_now, minute=30, day=_d(2026, 11, 14))
saturday_noon = edge_places.suggest(*WEATHER_ROUTE, 11, {'temp': 12, 'raining': False}, 12, story_now, minute=0, day=_d(2026, 11, 14))
late_trip = {**home_trip, 'session': 'qa-stop-night', 'time': '2026-11-13 23:47 금'}
night, _e, _ = agent('', late_trip)
metrics['stopHours'] = {'tuesdayDusk': tuesday_dusk and [tuesday_dusk['name'], tuesday_dusk['closes']], 'fridayNight': friday_night and friday_night['name'],
                        'saturdayDusk': saturday_dusk and saturday_dusk['name'], 'saturdayNoon': saturday_noon and saturday_noon['type'], 'nightSpeech': night['speech']}
# Saturday 17:30: 경기도서관 closes at 18:00 on weekends, too soon for a visit, so it is not offered
checks['stopRespectsOpeningHoursAndDark'] = (bool(tuesday_dusk) and tuesday_dusk['name'] == '경기도서관' and tuesday_dusk['closes'] == '21:00'
    and friday_night is None and (saturday_dusk is None or saturday_dusk['name'] != '경기도서관')
    and bool(saturday_noon) and saturday_noon['type'] == 'park' and not (night.get('card') or {}).get('place')
    and any(i['label'] == '21:00까지 열어요' for i in final['card']['sections'][0]['items']))
final, events, _ = agent('플리야, 하연이 사진으로 앨범 만들어 줄래?', {**context, 'session': 'qa-album-parent'})
checks['parentAlbumRequestAddressesParent'] = (final['action']['name'] == 'make_album' and '만들었어요' in final['speech'] and '하연아' in final['speech']
    and '키즈노트' not in final['speech'])
print(json.dumps({'checks': checks, 'metrics': metrics}, ensure_ascii=False))
assert all(checks.values()), [k for k, v in checks.items() if not v]
