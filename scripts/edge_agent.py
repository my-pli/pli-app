"""Pli's on-edge agent: plan -> act with tools -> observe -> answer, streamed as events.

Planner: a Korean intent planner picks the tool instantly (a 2B model on a shared CPU is too
slow and too error-prone to route). Tools run on the edge (vehicle signals, album story,
word games) or in the app (verified family news, built-in games, album viewer). The local
LLM (Kanana 1.5 2.1B via llama.cpp) answers open questions and turns observations into words.
Family facts are never generated here.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Awaitable, Callable


from edge_games import Games
from edge_weather import Weather, coarse, observation as weather_observation, parse as weather_ask, speech as weather_speech
import edge_kidsnote
import edge_places
from edge_plans import DESTINATION, family_items, pack_card, pack_speech, place_of, route_card, route_speech, target_day

Emit = Callable[[dict], Awaitable[None]]

PERSONA = ("너는 '플리'야. Pleos 차 안에서 아이와 가족을 돕는 다정한 AI 친구야. 이 차의 엣지 컴퓨터에서만 동작해. "
           "아이에게 반말로, 쉬운 말로, 정확한 사실만 1~2문장(70자 이내)으로 말해. 모르면 모른다고 해. "
           "이모지·기호·영어 약어는 쓰지 마. 위험하거나 어른 주제는 부드럽게 거절하고 놀이를 제안해. "
           "가족 일정·식단 같은 소식은 지어내지 마.")
TOPICS = {'BRIEF': '일정·준비물', 'MENU': '식단', 'REPORT': '알림장', 'NOTICES': '공지'}
GAMES = {'MATH': '숫자 놀이', 'ENGLISH': '영어 놀이', 'NATURE': '숲 퀴즈', 'STORY': '이야기 놀이',
         'WORDCHAIN': '끝말잇기', 'RIDDLE': '수수께끼'}
LABELS = {'answer': '스스로 답 찾기', 'family_news': '어린이집 소식 확인', 'vehicle_status': '차량 상태 확인',
          'weather': '날씨 확인', 'prepare': '챙길 것 고르기', 'route': '가는 길 추천', 'start_game': '놀이 준비', 'game_turn': '놀이 진행', 'show_album': '가족 앨범 열기',
          'make_album': '사진으로 앨범 만들기', 'show_growth': '성장 기록 정리', 'quiet': '조용히 기다리기',
          'destinations': '목적지 후보 준비', 'remember': '추억에 메모하기', 'stop': '가는 길 들를 곳'}
# "집 가는 길에 들를 데 있어?", "어디 들렀다 갈까?" — a place along the current route, not a new destination.
STOP = re.compile(r'(들를 ?(데|곳|만한)|들렀다 ?(갈|가)|어디 ?(들러|들를)|가는 ?길에 ?(뭐가 ?있|어디|들를|놀다|갈 ?만한)|놀다 ?갈 ?(데|곳))')
UNSAFE = re.compile(r'(욕\s*(해|가르)|나쁜 ?말|죽이|죽는 ?법|칼로|총으로|불\s?붙|담배|술\s?마|야한|성인|폭탄|약을? 많이)')
SENTENCE_END = re.compile(r'([.!?]|[다요어야지네까자])(\s+|$)')
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿️]')
PLAY = r'(놀이|하자|할래|해\s?줘|게임|퀴즈|시작)'
WEATHER = re.compile(r'(비 ?(가 ?)?(와|오|올|내리|그쳐|그칠|그쳤)|비가|눈 ?(이 ?)?(와|오|올|내리)|날씨|우산|소나기|우비|장화|와이퍼|기온|몇 ?도야|추워|더워|추울|더울|쌀쌀|따뜻해)')
CAPTION_STYLE = 'v7-family-name'  # bump when the caption prompt changes, so cached stories are rewritten


STORY_PAGES = 8


def story_photos(photos: list, pages: int = STORY_PAGES) -> list:
    """Story pages: photos where the child was found, the clearest face from each KidsNote album
    first (newest albums), then more from the same albums; shown oldest to newest."""
    found = [p for p in photos if p.get('child')] or photos
    def face_area(p):
        box = p.get('faceBox') or [0, 0, 0, 0]
        return box[2] * box[3]
    albums = {}
    for photo in sorted(found, key=face_area, reverse=True):
        albums.setdefault((photo.get('origin') or {}).get('date') or '', []).append(photo)
    order = sorted(albums, reverse=True)
    chosen = []
    while len(chosen) < pages and any(albums[d] for d in order):
        for date in order:
            if albums[date] and len(chosen) < pages:
                chosen.append(albums[date].pop(0))
    return sorted(chosen, key=lambda p: (p.get('origin') or {}).get('date') or '')


EVENT = re.compile(r'(추석 ?행사|수료 ?사진|물놀이|운동회|소풍|견학|발표회|[가-힣]+ ?체험)')


def event_of(title: str) -> str:
    """The named event of a KidsNote album ('… & 즐거운 김장 체험' → '김장 체험'); '' for weekly albums."""
    found = EVENT.findall(title)
    return found[-1] if found else ''


ACTIVITY = re.compile(r'\d+월 ?\d주-([^()]+?)\s*\(\d+\)')  # '02_9월 5주-미술놀이 (30).jpg' → '미술놀이'


def plain_caption(photo: dict) -> str:
    """A caption for a photo the vision model could not describe: only the day and the kindergarten's own
    name for the activity — nothing about what is in the picture, so nothing is invented."""
    origin = photo.get('origin') or {}
    found = ACTIVITY.search(photo.get('source') or '')
    activity = event_of(origin.get('title') or '') or (found.group(1).strip() if found else '')
    when = re.match(r'\d{4}-(\d{2})-(\d{2})', origin.get('date') or '')
    day = f'{int(when.group(1))}월 {int(when.group(2))}일' if when else ''
    if activity:
        return f"{day + ', ' if day else ''}{activity} 시간에 찍은 사진이야."
    return f"{day + ' ' if day else ''}어린이집에서 찍은 사진이야."


def context_day(context: dict) -> date:
    """The car's local date from the turn context ('2026-11-13 17:20 금'); today on this host otherwise."""
    match = re.match(r'(\d{4}-\d{2}-\d{2})', str(context.get('time') or ''))
    return date.fromisoformat(match.group(1)) if match else date.today()


def photo_context(photo: dict, child: str = '', aliases: tuple = ()) -> str:
    """What the caption may talk about: the scene the vision model saw and the KidsNote album it came from
    (the kindergarten's spelling of the name is shown as the family's)."""
    origin = photo.get('origin') or {}
    title = re.sub(r'[^0-9A-Za-z가-힣&·,!?\s]', '', origin.get('title') or '').strip()
    for alias in aliases:
        title = title.replace(alias, child or alias)
    parts = [f"장면: {photo['scene']}" if photo.get('scene') else '']
    if origin.get('kind') == 'kidsnote' and title:
        parts.append(f"어린이집 앨범 '{title}' ({origin.get('date', '')})")
    return ' · '.join(part for part in parts if part) or '하루의 한 장면'
FILLERS = ('음, 좋은 질문이야!', '어디 보자.', '오, 궁금했구나!', '음, 생각해 볼게.')


@dataclass(frozen=True)
class Plan:
    name: str
    args: dict
    reason: str


def looks_like_game_turn(text: str, game: str) -> bool:
    """A short word or answer continues the game; a real question or another request leaves it."""
    if re.search(r'(조용|쉿|그만 ?말|앨범|사진|배터리|도착|준비물|점심|알림장|왜|어떻게|뭐야|알려 ?줘|\?)', text):
        return bool(re.search(r'(그만|끝내|다른 놀이|몰라|힌트|정답 알려|포기)', text)) and not re.search(r'(앨범|사진|배터리|도착)', text)
    hangul = re.findall(r'[가-힣]+', text)
    return len(hangul) <= (3 if game == 'RIDDLE' else 2) and sum(len(h) for h in hangul) <= 9


def plan(text: str, game: str | None = None) -> Plan:
    """Korean intent planner. Order matters: the most specific intent wins."""
    t = re.sub(r'\s+', ' ', text.strip())
    day = 1 if re.search(r'내일', t) else 0
    if game in ('WORDCHAIN', 'RIDDLE') and looks_like_game_turn(t, game):
        return Plan('game_turn', {'game': game}, f'{GAMES[game]} 진행 중')
    if re.search(r'(조용|쉿|그만 ?말|시끄러|말하지 ?마)', t):
        return Plan('quiet', {}, '쉬고 싶다는 말')
    if re.search(r'(앨범|사진|추억 ?책|포토 ?북).*(만들|꾸며|엮|모아)|(만들|꾸며).*(앨범|사진첩)', t):
        return Plan('make_album', {}, '앨범을 만들어 달라는 요청')
    if re.search(r'성장 ?(앨범|기록)|정답률|몇 문제|내 기록', t):
        return Plan('show_growth', {}, '성장 기록 요청')
    if re.search(r'(사진|앨범|사진첩).*(보여|볼래|보자|보고 ?싶|열어|구경)|(보여|볼래).*(사진|앨범)', t):
        return Plan('show_album', {}, '사진을 보고 싶다는 말')
    if WEATHER.search(t) and not re.search(r'에어컨|히터|차 ?안|실내', t) and ('와이퍼' in t or not re.search(r'왜|어떻게 ?(생기|만들어|내리)', t)):
        return Plan('weather', {}, '창밖 날씨 질문')
    if STOP.search(t):
        return Plan('stop', {}, '가는 길에 들를 곳 질문')
    if DESTINATION.search(t) or re.search(r'가는 ?(동안|길에) ?(뭐|무슨)', t):
        return Plan('route', {}, '목적지에 맞춘 추천')
    if re.search(r'(준비물|챙겨|챙길|챙기|가방 ?(싸|챙)|뭐 ?가져)', t) and not re.search(r'(일정|스케줄|식단|점심|알림장)', t):
        return Plan('prepare', {'day': 1 if '내일' in t else 0}, '챙길 것 질문')
    if re.search(r'(배터리|충전|전기 ?얼마|속도|몇 ?킬로|얼마나 ?빨리|언제 ?도착|도착 ?(해|하|까지)|얼마나 ?(남|걸려)|몇 ?분|어디 ?(가|로 가)|목적지|기어)', t):
        return Plan('vehicle_status', {}, '차에 대한 질문')
    if re.search(r'(데려다|길 ?안내|목적지 ?(바꿔|정해)|어디로 ?갈까|가고 ?싶어)', t):
        return Plan('destinations', {}, '가고 싶은 곳 이야기')
    if re.search(r'(점심|급식|식단|메뉴|간식|반찬|밥 ?뭐)', t):
        return Plan('family_news', {'topic': 'MENU', 'day': day}, '식단 질문')
    if re.search(r'알림장', t):
        return Plan('family_news', {'topic': 'REPORT', 'day': day}, '알림장 요청')
    if re.search(r'(공지|안내문|가정통신문)', t):
        return Plan('family_news', {'topic': 'NOTICES', 'day': day}, '공지 요청')
    if re.search(r'(준비물|챙겨|일정|스케줄|행사|유치원에서 ?뭐|오늘 ?뭐 ?해|내일 ?뭐 ?해)', t):
        return Plan('family_news', {'topic': 'BRIEF', 'day': day}, '일정·준비물 질문')
    # Speech recognition often bends '잇기' ('끝말있 게 하자', '끝말 게 하자'); '끝말' itself is unambiguous.
    if re.search(r'끝말 ?(잇|있|이|익)기|끝말.{0,4}(하자|할래|놀자|해 ?줘)', t):
        return Plan('start_game', {'game': 'WORDCHAIN'}, '끝말잇기 요청')
    if re.search(r'수수께끼', t):
        return Plan('start_game', {'game': 'RIDDLE'}, '수수께끼 요청')
    if re.search(r'(숫자|수학|더하기|빼기|계산|주판).*' + PLAY, t):
        return Plan('start_game', {'game': 'MATH'}, '숫자 놀이 요청')
    if re.search(r'영어.*' + PLAY, t):
        return Plan('start_game', {'game': 'ENGLISH'}, '영어 놀이 요청')
    if re.search(r'(숲|자연|동물|곤충).*(퀴즈|놀이|문제)', t):
        return Plan('start_game', {'game': 'NATURE'}, '자연 퀴즈 요청')
    if re.search(r'(이야기 ?(놀이|하자)|동화)', t):
        return Plan('start_game', {'game': 'STORY'}, '이야기 놀이 요청')
    if re.search(r'기억해', t):
        return Plan('remember', {'note': t[:120]}, '기억해 달라는 말')
    return Plan('answer', {}, '스스로 생각해서 답할 질문')


def vehicle_observation(vehicle: dict) -> str:
    """A factual summary built only from signals the app reported."""
    facts = []
    if vehicle.get('gear') and vehicle['gear'] != '—':
        facts.append(f"기어 {vehicle['gear']}")
    if vehicle.get('speedKmh') is not None:
        facts.append(f"속도 {round(float(vehicle['speedKmh']))}km/h")
    if vehicle.get('battery') is not None:
        facts.append(f"배터리 {vehicle['battery']}%")
    if vehicle.get('chargingActive'):
        facts.append('충전 중')
    if vehicle.get('destination'):
        facts.append(f"목적지 {vehicle['destination']}")
    if vehicle.get('minutesRemaining') is not None:
        facts.append(f"도착까지 {vehicle['minutesRemaining']}분")
    if vehicle.get('wiperOnRecently'):
        facts.append('와이퍼 최근 켜짐')
    elif 'wiperOnRecently' in vehicle:
        facts.append('와이퍼 꺼짐')
    return ', '.join(facts) if facts else '차량 신호 없음'


def sentences(buffer: str) -> tuple[list[str], str]:
    """Split complete sentences off the front of the buffer (Korean endings or punctuation)."""
    done, start = [], 0
    for match in SENTENCE_END.finditer(buffer):
        end = match.end()
        piece = buffer[start:end].strip()
        if len(piece) >= 6:
            done.append(piece)
            start = end
    return done, buffer[start:]


def clean_speech(text: str) -> str:
    text = EMOJI.sub('', text.replace('<|eot_id|>', ''))
    text = re.sub(r'[\*#_`<>{}\[\]|]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def first_paragraph(text: str) -> str:
    return clean_speech(text.strip().split('\n\n')[0].replace('\n', ' '))


@dataclass
class Turn:
    text: str
    context: dict
    started: float = field(default_factory=time.monotonic)
    steps: list = field(default_factory=list)

    def ms(self) -> int:
        return round((time.monotonic() - self.started) * 1000)


class Agent:
    def __init__(self, llm_url: str, album: Callable[[], dict | None], story_path=None) -> None:
        self.llm_url = llm_url.rstrip('/')
        self.album = album
        self.story_path = story_path
        self.session = None
        self.model = ''
        self.games = Games()
        self.weather = Weather()
        self.story: dict | None = None
        self.story_key = None

    async def start(self) -> None:
        from aiohttp import ClientSession, ClientTimeout  # server-only dependency; planning stays importable
        self.session = ClientSession(timeout=ClientTimeout(total=60))
        self.weather.bind(self.session)
        if self.story_path and self.story_path.exists():
            try:
                saved = json.loads(self.story_path.read_text())
                self.story, self.story_key = saved.get('story'), saved.get('key')
            except ValueError:
                pass

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def health(self) -> dict:
        from aiohttp import ClientTimeout
        try:
            async with self.session.get(self.llm_url + '/health', timeout=ClientTimeout(total=2)) as r:
                ok = r.status == 200 and (await r.json()).get('status') == 'ok'
            if ok and not self.model:
                async with self.session.get(self.llm_url + '/v1/models', timeout=ClientTimeout(total=2)) as r:
                    data = await r.json()
                    self.model = ((data.get('data') or [{}])[0].get('id', '')).rsplit('/', 1)[-1]
            return {'ready': ok, 'model': self.model}
        except Exception as exc:  # the app falls back to its on-device rules
            return {'ready': False, 'error': type(exc).__name__}

    async def chat(self, messages: list, max_tokens: int, on_text=None, temperature: float = 0.3) -> str:
        body = {'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature, 'top_p': 0.9,
                'stream': on_text is not None, 'cache_prompt': True, 'stop': ['<|eot_id|>']}
        async with self.session.post(self.llm_url + '/v1/chat/completions', json=body) as r:
            r.raise_for_status()
            if on_text is None:
                return first_paragraph((await r.json())['choices'][0]['message']['content'])
            text = ''
            async for raw in r.content:
                line = raw.decode('utf-8', 'ignore').strip()
                if not line.startswith('data:') or line == 'data: [DONE]':
                    continue
                delta = json.loads(line[5:])['choices'][0].get('delta', {}).get('content') or ''
                if delta:
                    text += delta
                    if '\n\n' in text.strip():
                        break
                    await on_text(first_paragraph(text))
            return first_paragraph(text)

    async def step(self, turn: Turn, emit: Emit, key: str, label: str, state: str, detail: str = '') -> None:
        event = {'type': 'step', 'id': key, 'label': label, 'state': state, 'detail': detail, 'ms': turn.ms()}
        turn.steps = [s for s in turn.steps if s['id'] != key] + [event]
        await emit(event)

    async def say(self, turn: Turn, emit: Emit, speech: str) -> None:
        if speech:
            await emit({'type': 'speech', 'text': speech, 'index': 0, 'ms': turn.ms()})

    async def run(self, text: str, context: dict, emit: Emit) -> dict:
        turn = Turn(text.strip()[:200], context)
        session = str(context.get('session') or 'default')
        child = context.get('child') or '친구'
        if context.get('proactive'):
            await self.step(turn, emit, 'hear', '차량 신호 읽기', 'done', vehicle_observation(context.get('vehicle') or {})[:70])
        else:
            await self.step(turn, emit, 'hear', '말 이해하기', 'done', f'“{turn.text}”')
        if UNSAFE.search(turn.text):
            await self.step(turn, emit, 'guard', '안전 확인', 'done', '아이에게 맞지 않는 요청')
            speech = '그건 플리가 도와줄 수 없는 이야기야. 대신 재미있는 수수께끼 할까?'
            await self.say(turn, emit, speech)
            return await self._finish(turn, emit, Plan('answer', {}, 'guard'), 'THINKING', speech)
        game = context.get('game') if context.get('game') in ('WORDCHAIN', 'RIDDLE') else self.games.active(session)
        decided = Plan('stop', {'proactive': True}, '주행 중 먼저 제안') if context.get('proactive') == 'route-stop' else plan(turn.text, game)
        detail = LABELS[decided.name]
        if decided.name == 'family_news':
            detail += f" · {'내일' if decided.args['day'] else '오늘'} {TOPICS[decided.args['topic']]}"
        elif decided.name in ('start_game', 'game_turn'):
            detail += f" · {GAMES[decided.args['game']]}"
        await self.step(turn, emit, 'plan', '할 일 고르기', 'done', f'{detail} ({decided.reason})')
        if decided.name not in ('game_turn', 'start_game'):
            self.games.stop(session)
        handler = getattr(self, '_' + decided.name)
        return await handler(turn, emit, decided, session, child)

    async def _finish(self, turn: Turn, emit: Emit, decided: Plan, mood: str, speech: str, album: dict | None = None,
                      title: str | None = None, card: dict | None = None) -> dict:
        final = {'type': 'final', 'action': {'name': decided.name, 'args': decided.args}, 'speech': speech,
                 'mood': mood, 'title': title or LABELS[decided.name], 'steps': turn.steps, 'album': album, 'card': card,
                 'model': self.model, 'ms': turn.ms()}
        await emit(final)
        return final

    async def _answer(self, turn, emit, decided, session, child):
        driving = bool((turn.context.get('vehicle') or {}).get('uxRestricted'))
        await self.step(turn, emit, 'context', '맥락 확인', 'done', f"{child} · {'주행 중이라 짧게' if driving else '정차 중'}")
        await self.say(turn, emit, FILLERS[len(turn.text) % len(FILLERS)])
        await self.step(turn, emit, 'think', '엣지 LLM으로 생각하기', 'running', self.model or 'local')
        messages = [{'role': 'system', 'content': PERSONA + f' 아이 이름은 {child}.' + (' 지금은 운전 중이라 아주 짧게 말해.' if driving else '')}]
        for item in (turn.context.get('history') or [])[-4:]:
            role = 'assistant' if item.get('role') == 'pli' else 'user'
            if item.get('text'):
                messages.append({'role': role, 'content': str(item['text'])[:160]})
        messages.append({'role': 'user', 'content': turn.text})
        spoken = {'count': 0}

        async def on_text(partial: str) -> None:
            done, _ = sentences(clean_speech(partial))
            for sentence in done[spoken['count']:]:
                spoken['count'] += 1
                if spoken['count'] == 1:
                    await self.step(turn, emit, 'think', '엣지 LLM으로 생각하기', 'done', f'첫 문장 {turn.ms()}ms')
                await emit({'type': 'speech', 'text': sentence, 'index': spoken['count'], 'ms': turn.ms()})

        speech = await self.chat(messages, 90, on_text) or '음, 그건 잘 모르겠어. 다른 걸 물어봐 줄래?'
        done, tail = sentences(speech)
        rest = ' '.join(done[spoken['count']:] + ([tail.strip()] if tail.strip() else []))
        if rest:
            await emit({'type': 'speech', 'text': rest, 'index': spoken['count'] + 1, 'ms': turn.ms()})
        await self.step(turn, emit, 'think', '엣지 LLM으로 생각하기', 'done', f'답변 완성 {turn.ms()}ms')
        return await self._finish(turn, emit, decided, 'HAPPY', speech, title=f'“{turn.text}”')

    async def _vehicle_status(self, turn, emit, decided, session, child):
        await self.say(turn, emit, '차를 확인해 볼게.')
        await self.step(turn, emit, 'tool', '차량 신호 읽기', 'running', 'Pleos Vehicle SDK')
        observation = vehicle_observation(turn.context.get('vehicle') or {})
        await self.step(turn, emit, 'tool', '차량 신호 읽기', 'done', observation)
        await self.step(turn, emit, 'think', '관찰로 답 만들기', 'running', self.model or 'local')
        messages = [{'role': 'system', 'content': PERSONA + f' 아이 이름은 {child}. 아래 관찰한 차량 정보에 있는 사실만 써서 답해. 정보가 없으면 아직 모른다고 해.'},
                    {'role': 'user', 'content': f'관찰: {observation}\n질문: {turn.text}'}]
        try:
            speech = await self.chat(messages, 60)
        except Exception:
            speech = ''
        speech = speech or f'지금 차는 {observation}이야.'
        await self.step(turn, emit, 'think', '관찰로 답 만들기', 'done')
        await emit({'type': 'speech', 'text': speech, 'index': 1, 'ms': turn.ms()})
        return await self._finish(turn, emit, decided, 'HAPPY', speech, title='우리 차는 지금')

    async def _weather(self, turn, emit, decided, session, child):
        vehicle = turn.context.get('vehicle') or {}
        wiper = bool(vehicle['wiperOnRecently']) if 'wiperOnRecently' in vehicle else None
        location = vehicle.get('location')
        await self.say(turn, emit, '창밖 날씨를 알아볼게.')
        located = coarse(location) is not None
        await self.step(turn, emit, 'locate', '차 위치 확인', 'done' if located else 'fail',
                        'Pleos 위치 신호 · 약 1km 단위로만 사용' if located else 'Pleos 위치 신호를 아직 받지 못함')
        await self.step(turn, emit, 'tool', '실시간 날씨 받기', 'running', '공개 기상 데이터 · Open-Meteo, 응답 없으면 MET Norway')
        result = await self.weather.lookup(location)
        await self.step(turn, emit, 'tool', '실시간 날씨 받기', 'done' if result['ok'] else 'fail', weather_observation(result, wiper))
        speech = weather_speech(result, weather_ask(turn.text), wiper)
        await self.step(turn, emit, 'think', '관찰로 답 만들기', 'done', '받아온 수치와 와이퍼 신호로만 답함')
        await emit({'type': 'speech', 'text': speech, 'index': 1, 'ms': turn.ms()})
        mood = 'THINKING' if not result['ok'] else 'EXCITED' if result.get('raining') or result.get('snowing') else 'HAPPY'
        return await self._finish(turn, emit, decided, mood, speech, title='창밖 날씨')

    async def _prepare(self, turn, emit, decided, session, child):
        """Tomorrow's (or today's) things to bring: family notices + weather + destination, no LLM."""
        day = target_day(turn.text, str(turn.context.get('time') or ''))
        facts = turn.context.get('family') or []
        vehicle = turn.context.get('vehicle') or {}
        today = context_day(turn.context)
        asked = today + timedelta(days=day)
        # The kindergarten's real calendar (KidsNote MCP) outranks the demo's sample notices; the
        # family's own plans for the asked day outrank a school event found days ahead.
        school, used = await self._kidsnote_facts(turn, emit, today, day) if turn.context.get('kidsnote', True) else ([], None)
        own = [] if turn.context.get('demo') else [f for f in facts if f.get('title') != '샘플 공지']
        if school and used != asked and family_items(own, day)[0]:
            school, used = [], None
        if school:
            facts = school + (own if used == asked else [])
        named = [f.get('title') or f.get('source') for f in facts if f.get('text') or f.get('preparation')]
        await self.step(turn, emit, 'family', '가족 일정 확인', 'done' if named else 'fail',
                        ' · '.join(dict.fromkeys(named))[:60] if named else '이 날의 일정·공지가 없음')
        when = edge_kidsnote.day_name(used, today) if used and used != asked else None
        skipped = ''
        if when:
            skipped = f"{edge_kidsnote.day_name(asked, today)}은 {'주말이라 쉬는 날이야!' if asked.weekday() >= 5 else '어린이집 일정이 없어.'}"
        else:
            await self.step(turn, emit, 'tool', f"{'내일' if day else '오늘'} 날씨 확인", 'running', 'Pleos 위치 · 공개 기상 데이터')
        weather = await self.weather.lookup(vehicle.get('location')) if not when else {'ok': False}
        if not when:
            await self.step(turn, emit, 'tool', f"{'내일' if day else '오늘'} 날씨 확인", 'done' if weather['ok'] else 'fail',
                            weather_observation(weather, None))
        card = pack_card(facts, weather, day, place_of('', vehicle), when=when)
        speech = pack_speech(card, day, skipped)
        await self.step(turn, emit, 'think', '챙길 것 고르기', 'done', f"{len(card['sections'][0]['items'])}가지 · 공지와 날씨에 적힌 것만")
        await self.say(turn, emit, speech)
        return await self._finish(turn, emit, Plan('prepare', {'day': day}, decided.reason), 'EXCITED', speech,
                                  title=card['title'], card=card)

    async def _kidsnote_facts(self, turn, emit, today: date, day: int) -> tuple:
        """The kindergarten calendar over the KidsNote MCP: facts for the asked day or the next school event."""
        await self.step(turn, emit, 'kidsnote', '어린이집 일정 확인', 'running', 'MCP · get_calendar')
        try:
            events = await edge_kidsnote.calendar(today)
        except Exception:  # offline or signed out: the plan falls back to the app's facts and weather
            await self.step(turn, emit, 'kidsnote', '어린이집 일정 확인', 'fail', '일정 서비스에 연결하지 못했어요')
            return [], None
        facts, used = edge_kidsnote.facts_for(events, today, day)
        detail = (f"{used.month}/{used.day} {facts[0]['title']} · 준비물 " + ', '.join(f['bring'] for f in facts)
                  if facts else f'이번 달 일정 {len(events)}건 · 이 날 준비물 없음')
        await self.step(turn, emit, 'kidsnote', '어린이집 일정 확인', 'done', detail[:70])
        return facts, used

    async def _route(self, turn, emit, decided, session, child):
        """Where we are going decides the game on the way, what to do there and what to bring."""
        vehicle = turn.context.get('vehicle') or {}
        place = place_of(turn.text, vehicle)
        if place is None:
            speech = '어디로 가는지 알려 주면 가는 길 놀이를 골라 줄게. 예를 들면 숲 체험 가자, 처럼!'
            await self.say(turn, emit, speech)
            return await self._finish(turn, emit, decided, 'THINKING', speech)
        minutes = vehicle.get('minutesRemaining')
        minutes = int(minutes) if isinstance(minutes, (int, float)) else None
        await self.step(turn, emit, 'place', '목적지 확인', 'done',
                        f"{place.name}" + (f' · 도착까지 {minutes}분 (Pleos 내비)' if minutes is not None else ''))
        weather = await self.weather.lookup(vehicle.get('location'))
        await self.step(turn, emit, 'tool', '오늘 날씨 확인', 'done' if weather['ok'] else 'fail', weather_observation(weather, None))
        card, game = route_card(place, minutes, weather, turn.context.get('family') or [])
        speech = route_speech(card, place, minutes, game)
        await self.step(turn, emit, 'think', '가는 길 추천 만들기', 'done', ' · '.join(s['title'] for s in card['sections']))
        await self.say(turn, emit, speech)
        return await self._finish(turn, emit, Plan('route', {'destination': place.name, 'kind': place.key, 'game': game}, decided.reason),
                                  'EXCITED', speech, title=card['title'], card=card)

    async def _stop(self, turn, emit, decided, session, child):
        """A place on the way (Pleos route: here → destination), chosen for the child, weather and hour."""
        vehicle = turn.context.get('vehicle') or {}
        here, there = vehicle.get('location') or {}, vehicle.get('destinationLocation') or {}
        home = str(vehicle.get('destination') or '집').split(' · ')[0]
        minutes = vehicle.get('minutesRemaining')
        if not (here.get('lat') and there.get('lat') and isinstance(minutes, (int, float))):
            speech = '내비게이션에 목적지가 있으면 가는 길에 들를 곳을 찾아 드릴게요.'
            await self.say(turn, emit, speech)
            return await self._finish(turn, emit, decided, 'THINKING', speech)
        minutes = int(minutes)
        source = 'Pleos 내비' + (' · 시연 경로' if vehicle.get('demoTrip') else '')
        await self.step(turn, emit, 'route', '경로 확인', 'done', f'{home}까지 {minutes}분 ({source})')
        weather = await self.weather.lookup(here)
        await self.step(turn, emit, 'tool', '날씨 확인', 'done' if weather['ok'] else 'fail', weather_observation(weather, None))
        album = await self.album_story()
        liked, count = edge_places.interest(album)
        await self.step(turn, emit, 'child', f'{child}이가 좋아하는 것', 'done', f'앨범 기록 · {liked} {count}번' if liked else '기록 없음')
        clock = re.search(r' (\d{1,2}):(\d{2})', str(turn.context.get('time') or ' 12:00'))
        hour, minute = (int(clock.group(1)), int(clock.group(2))) if clock else (12, 0)
        stop = edge_places.suggest((here['lat'], here['lon']), (there['lat'], there['lon']), minutes,
                                   weather if weather.get('ok') else {}, hour, album,
                                   minute=minute, day=context_day(turn.context))
        if not stop:
            await self.step(turn, emit, 'think', '가는 길 장소 고르기', 'done', '경로 가까이에 알맞은 곳 없음')
            speech = '' if decided.args.get('proactive') else f'{home} 가는 길에는 지금 들르기 좋은 곳이 없어요. 바로 가요!'
            await self.say(turn, emit, speech)
            return await self._finish(turn, emit, decided, 'HAPPY', speech)
        await self.step(turn, emit, 'think', '가는 길 장소 고르기', 'done',
                        f"경로 옆 {stop['considered']}곳 중 {stop['name']} · {stop['minutesAway']}분 뒤")
        speech = edge_places.stop_speech(stop, child, home, minutes)
        card = edge_places.stop_card(stop, child, home, minutes)
        await self.say(turn, emit, speech)
        return await self._finish(turn, emit, Plan('stop', {**decided.args, 'stop': card['place']}, decided.reason),
                                  'EXCITED', speech, title=card['title'], card=card)

    async def _start_game(self, turn, emit, decided, session, child):
        name = decided.args['game']
        if name in ('WORDCHAIN', 'RIDDLE'):
            await self.step(turn, emit, 'tool', '놀이 엔진 준비', 'done', '엣지 단어장·수수께끼')
            speech = self.games.start(session, name)
            await self.say(turn, emit, speech)
            return await self._finish(turn, emit, decided, 'EXCITED', speech, title=GAMES[name])
        self.games.stop(session)
        await self.step(turn, emit, 'act', '앱에 실행 요청', 'done', GAMES[name])
        return await self._finish(turn, emit, decided, 'EXCITED', '', title=GAMES[name])

    async def _game_turn(self, turn, emit, decided, session, child):
        if not self.games.active(session):
            self.games.start(session, decided.args['game'])
        speech, detail = self.games.play(session, turn.text, child)
        await self.step(turn, emit, 'tool', '놀이 규칙 확인', 'done', detail)
        await self.say(turn, emit, speech)
        ended = not self.games.active(session)
        return await self._finish(turn, emit, Plan('game_turn', {**decided.args, 'ended': ended}, decided.reason),
                                  'EXCITED', speech, title=GAMES[decided.args['game']])

    async def _make_album(self, turn, emit, decided, session, child):
        manifest = self.album() or {}
        photos = manifest.get('photos') or []
        await self.step(turn, emit, 'tool', '사진 고르기', 'done', f'가족 사진 {len(photos)}장')
        found = [p for p in photos if p.get('child')]
        sims = [p.get('similarity') for p in found if p.get('similarity')]
        await self.step(turn, emit, 'face', '얼굴 인식으로 아이 찾기', 'done',
                        f"{manifest.get('child', child)} {len(found)}장 · 유사도 {min(sims):.2f}~{max(sims):.2f}" if sims else '아이 얼굴 없음')
        await self.step(turn, emit, 'story', '장면 이해 · 이야기 쓰기', 'running', self.model or 'local')
        story = await self.album_story()
        await self.step(turn, emit, 'story', '장면 이해 · 이야기 쓰기', 'done', f"‘{story['title']}’" if story else '사진이 없어요')
        if not story:
            speech = '앨범에 넣을 사진이 아직 없어. 가족 연결에서 사진을 추가해 줘.'
            await self.say(turn, emit, speech)
            return await self._finish(turn, emit, decided, 'THINKING', speech)
        name = story['child']
        if name and name in turn.text:  # "하연이 사진으로 앨범 만들어 줄래?" — a parent asking about the child
            speech = (f"네, {name}이가 나온 사진만 골라 '{story['title']}'을 만들었어요. "
                      f"{edge_places.vocative(name)}, 같이 볼까?")
        else:
            speech = f"'{story['title']}'을 만들었어! 한 장씩 같이 볼까?"
        await self.say(turn, emit, speech)
        return await self._finish(turn, emit, decided, 'EXCITED', speech, album=story, title=story['title'])

    async def _client(self, turn, emit, decided, session, child):
        await self.step(turn, emit, 'act', '앱에 실행 요청', 'done', LABELS[decided.name])
        return await self._finish(turn, emit, decided, 'HAPPY', '')

    _family_news = _show_album = _show_growth = _quiet = _destinations = _remember = _client

    async def album_story(self) -> dict | None:
        """Album title and captions, written once per photo set and kept (the CPU model is slow)."""
        manifest = self.album()
        if not manifest or not manifest.get('photos'):
            return None
        photos = story_photos(manifest['photos'])
        key = [self.model, CAPTION_STYLE] + [p['id'] for p in photos] + [p.get('scene') for p in photos]
        if self.story and self.story_key == key:
            return self.story
        child = manifest.get('child', '아이')
        captions, title, complete = [], f'{child}의 반짝이는 하루', True
        for photo in photos:
            if not photo.get('scene'):  # the vision model saw nothing: say only the day and the activity
                captions.append(plain_caption(photo))
                continue
            scene = photo_context(photo, child, manifest.get('aliases') or ())
            line = ''
            for _attempt in range(2):
                try:
                    line = await self.chat([{'role': 'system', 'content': ('너는 플리야. 아이에게 앨범을 읽어 주는 다정한 친구야. 장면 문장과 앨범 제목에 없는 물건·동물·사람·사건은 절대 넣지 마. '
                                                                         '아이에게 말하듯 반말로, 25자 안팎의 끝까지 완성된 한 문장. 앨범 제목에 행사 이름(김장 체험, 추석 행사 같은 것)이 있으면 꼭 넣고, '
                                                                         '없으면 장면의 구체적인 것(물건·색·하는 일)을 넣어. 앞 문장과 같은 표현은 다시 쓰지 마.')},
                                            {'role': 'user', 'content': f'{child}의 사진 — {scene}\n이 사진에 붙일 한 문장:'}], 64, temperature=0.4)
                except Exception:
                    line = ''
                if line:
                    break
            complete = complete and bool(line)
            caption = sentences(line)[0][0] if sentences(line)[0] else (line or scene)
            event = event_of((photo.get('origin') or {}).get('title') or '')
            captions.append(f'{event} 날, {caption}' if event and event not in caption else caption)
        try:
            got = await self.chat([{'role': 'system', 'content': f'너는 아이 추억 앨범 작가야. 따옴표 없이 15자 이내 제목만 써. 제목에 {child} 이름을 넣어.'},
                                   {'role': 'user', 'content': f'{child}의 사진들: ' + ' / '.join(photo_context(p, child, manifest.get('aliases') or ()) for p in photos) + '\n앨범 제목:'}], 24, temperature=0.6)
            title = got.strip('"\'“”‘’. ') or title
        except Exception:
            complete = False
        self.story = {'title': title, 'child': child,
                      'pages': [{'id': p['id'], 'file': p['file'], 'caption': c, 'focus': p.get('focus'), 'scene': p.get('scene'),
                                 'date': (p.get('origin') or {}).get('date')}
                                for p, c in zip(photos, captions)]}
        self.story_key = key if complete else None
        if self.story_path and complete:
            self.story_path.write_text(json.dumps({'key': key, 'story': self.story}, ensure_ascii=False, indent=1))
        return self.story
