"""Practical plans for the family: what to pack, and what to do on the way somewhere.

Both are composed from facts only — the family's schedule and notices the app sends,
the fetched weather, the car's destination and remaining minutes — so they are fast
(no LLM call) and never invent an event. Each returns a card the app draws.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# word in a notice or plan -> (icon, label)
ITEMS = {
    '운동화': ('👟', '운동화'), '물병': ('💧', '물병'), '물통': ('💧', '물병'), '텀블러': ('💧', '물병'),
    '우산': ('☂️', '우산'), '우비': ('🧥', '우비'), '장화': ('🥾', '장화'), '모자': ('🧢', '모자'),
    '도시락': ('🍱', '도시락'), '수저': ('🥄', '수저'), '수건': ('🧺', '수건'), '여벌옷': ('👕', '여벌옷'),
    '여벌': ('👕', '여벌옷'), '실내화': ('🩴', '실내화'), '수영복': ('🩱', '수영복'), '물안경': ('🥽', '물안경'),
    '선크림': ('🧴', '선크림'), '색연필': ('🖍️', '색연필'), '크레파스': ('🖍️', '크레파스'), '스케치북': ('📒', '스케치북'),
    '돗자리': ('🧺', '돗자리'), '간식': ('🍪', '간식'), '손수건': ('🧣', '손수건'), '장갑': ('🧤', '장갑'),
    '목도리': ('🧣', '목도리'), '마스크': ('😷', '마스크'), '책': ('📚', '책'), '가방': ('🎒', '가방'),
    '양말': ('🧦', '양말'), '물티슈': ('🧻', '물티슈'), '주판': ('🧮', '주판'), '필통': ('✏️', '필통'),
    '줄넘기': ('🪢', '줄넘기'), '편지': ('💌', '편지'), '그림': ('🎨', '그림'), '겉옷': ('🧥', '겉옷'),
    '원복': ('🎽', '원복'), '흰티': ('👕', '흰 티셔츠'), '청바지': ('👖', '청바지'), '앞치마': ('🧑\u200d🍳', '앞치마'),
    '여벌양말': ('🧦', '여벌 양말'), '이름표': ('🏷️', '이름표'),
}
OCCASIONS = ('숲 체험', '숲체험', '소풍', '현장 학습', '현장학습', '체육 대회', '운동회', '생일 파티', '수영',
             '견학', '발표회', '도서관', '텃밭', '물놀이', '캠핑')


@dataclass(frozen=True)
class Place:
    key: str      # nature | english | math | school | family | swim | library | zoo | home | other
    name: str     # how Pli says it


PLACES = [  # (pattern, kind, display name); the first match wins
    (r'숲 ?체험', 'nature', '숲 체험'), (r'(수목원|숲|산|캠핑|공원|놀이터|소풍)', 'nature', None),
    (r'영어 ?학원', 'english', '영어 학원'), (r'(주산|수학) ?학원', 'math', '주산 학원'),
    (r'(어린이집|유치원)', 'school', None), (r'(할머니|할아버지|외갓집)', 'family', None),
    (r'(수영장|워터파크|바다|해수욕장)', 'swim', None), (r'(도서관|박물관|과학관|미술관)', 'library', None),
    (r'(동물원|아쿠아리움)', 'zoo', None), (r'우리 ?집|집', 'home', '우리 집'),
]
DESTINATION = re.compile(r'(?P<place>숲 ?체험|수목원|숲|캠핑장?|공원|놀이터|소풍|영어 ?학원|주산 ?학원|수학 ?학원|어린이집|유치원|'
                         r'할머니 ?댁|할아버지 ?댁|할머니 ?집|외갓집|수영장|워터파크|바다|해수욕장|도서관|박물관|과학관|미술관|'
                         r'동물원|아쿠아리움|우리 ?집|집)\s*(?:에|으로|로|에서)?\s*(?:가자|가요|가는 ?중|가는 ?길|갈 ?거야|갈래|간다|가|출발)')

# kind -> (game the app can start, way game, two things to do there, things to bring)
IDEAS = {
    'nature': ('NATURE', ('🌳', '숲 퀴즈'), [('🌰', '도토리 세 개 찾기'), ('🍁', '제일 큰 나뭇잎 모으기')], ['모자', '물병']),
    'english': ('ENGLISH', ('🔤', '영어 단어 미리 연습'), [('👋', '선생님께 영어로 인사하기'), ('⭐', '새로 배운 단어 하나 기억하기')], ['책', '필통']),
    'math': ('MATH', ('🧮', '마음속 주판 셈'), [('✋', '오늘 배운 셈 한 문제 엄마한테 내기'), ('🎯', '틀린 문제 다시 풀어 보기')], ['주판', '필통']),
    'school': ('WORDCHAIN', ('🔗', '끝말잇기 한 판'), [('😊', '친구에게 오늘 기분 말해 주기'), ('🖐️', '선생님께 인사하기')], ['가방', '실내화']),
    'family': ('RIDDLE', ('🧩', '할머니께 낼 수수께끼 연습'), [('📸', '앨범 보여 드리기'), ('💌', '안아 드리고 고맙다고 말하기')], ['그림', '편지']),
    'swim': ('ENGLISH', ('🐟', '바다 동물 영어 퀴즈'), [('🤸', '준비 운동 열 번'), ('🫧', '물속에서 숨 참기 놀이')], ['수영복', '수건', '물안경']),
    'library': ('RIDDLE', ('🧩', '수수께끼 세 개'), [('🔎', '제일 신기한 것 하나 골라 오기'), ('🤫', '조용조용 탐험가 되기')], ['책', '가방']),
    'zoo': ('NATURE', ('🦁', '동물 소리 퀴즈'), [('🐘', '제일 큰 동물 찾기'), ('📸', '좋아하는 동물 사진 찍기')], ['모자', '물병']),
    'home': ('STORY', ('📖', '오늘 있었던 일 이야기'), [('📸', '오늘의 추억 앨범 만들기'), ('🛁', '손 씻고 쉬기')], []),
    'other': ('WORDCHAIN', ('🔗', '끝말잇기 한 판'), [('👀', '새로운 것 세 개 찾아보기'), ('📸', '기억하고 싶은 장면 말해 주기')], []),
}
GAME_WORDS = {'NATURE': '숲 퀴즈', 'ENGLISH': '영어 퀴즈', 'MATH': '숫자 놀이', 'WORDCHAIN': '끝말잇기', 'RIDDLE': '수수께끼', 'STORY': '이야기 놀이'}
RAIN_CODES = set(range(51, 68)) | {80, 81, 82, 95, 96, 99}
SNOW_CODES = set(range(71, 78)) | {85, 86}


def _item(label: str, reason: str, source: str) -> dict:
    icon = next((icon for icon, name in ITEMS.values() if name == label), '✔️')
    return {'icon': icon, 'label': label, 'reason': reason, 'source': source}


def _merge(items: list) -> list:
    """One row per thing; a thing two sources ask for keeps both reasons."""
    merged: dict = {}
    for item in items:
        if item['label'] in merged:
            old = merged[item['label']]
            if item['reason'] not in old['reason']:
                merged[item['label']] = {**old, 'reason': old['reason'] + ' · ' + item['reason']}
        else:
            merged[item['label']] = dict(item)
    return list(merged.values())


def occasion_of(text: str) -> str:
    found = next((o for o in OCCASIONS if o in text), '')
    return {'숲체험': '숲 체험', '현장학습': '현장 학습'}.get(found, found)


def _words(text: str) -> list:
    """(position, word) of every item named in the text, in order; a word inside a longer named
    word ('양말' in '여벌양말', '물통' in '끈달린 물통' stays) is not counted twice."""
    found = sorted((text.find(w), w) for w in ITEMS if w in text)
    return [(at, w) for at, w in found
            if not any(o != w and len(o) > len(w) and oat <= at and at + len(w) <= oat + len(o) for oat, o in found)]


def family_items(facts: list, day: int) -> tuple:
    """Things the family's own notices and plans name for that day, in the order written."""
    found, occasion = [], ''
    for fact in facts or []:
        text = (str(fact.get('text') or '') + ' ' + str(fact.get('preparation') or '')).strip()
        if not text:
            continue
        if fact.get('day') is not None:
            if int(fact['day']) != day:
                continue
        elif ('내일' in text) != (day == 1):
            continue
        place = occasion_of(text) or str(fact.get('title') or '')
        occasion = occasion or place
        reason = (place + (' 공지' if fact.get('source') == 'notice' else ' 일정')).strip()
        seen: list = []
        for _, word in _words(text):
            label = ITEMS[word][1]
            if label not in seen and not any(label in other for other in seen):
                seen.append(label)
                found.append(_item(label, reason, 'family'))
    return found, occasion


def weather_items(w: dict, day: int) -> tuple:
    """Rain, snow, cold and heat turned into things to bring, with the number that justifies each."""
    if not w or not w.get('ok'):
        return [], ''
    items, note = [], ''
    if day == 1 and w.get('tomorrow'):
        t = w['tomorrow']
        chance, mm, code = t.get('chance'), t.get('mm') or 0, t.get('code')
        reason = f'내일 비 {mm:g}mm' if chance is None else f'내일 비 올 확률 {chance}%'
        if code in SNOW_CODES:
            items += [_item('장갑', '내일 눈 소식', 'weather'), _item('장화', '내일 눈 소식', 'weather')]
            note = '내일 눈이 온대'
        elif (chance or 0) >= 40 or mm >= 1 or code in RAIN_CODES:
            items.append(_item('우산', reason, 'weather'))
            if mm >= 5 or (chance or 0) >= 70:
                items.append(_item('장화', reason, 'weather'))
            note = '내일 비가 온대'
        low, high = t.get('min'), t.get('max')
        if low is not None and low < 8:
            items.append(_item('겉옷', f'아침 {round(low)}도', 'weather'))
        if high is not None and high >= 27:
            items += [_item('모자', f'낮 {round(high)}도', 'weather'), _item('물병', f'낮 {round(high)}도', 'weather')]
    else:
        temp = w.get('temp')
        if rain_within(w, 8):
            items.append(_item('우산', '지금 비' if w.get('raining') else '오늘 비 소식', 'weather'))
            note = '오늘 비 소식이 있어'
        if temp is not None and temp < 8:
            items.append(_item('겉옷', f'지금 {round(temp)}도', 'weather'))
        if temp is not None and temp >= 27:
            items.append(_item('모자', f'지금 {round(temp)}도', 'weather'))
    return items, note


def rain_within(w: dict, hours: int) -> bool:
    """Raining now, or the forecast's first rainy hour is within `hours` of the observation."""
    if not w or not w.get('ok'):
        return False
    if w.get('raining'):
        return True
    soon, observed = w.get('soon'), re.search(r'T(\d{2})', str(w.get('observedAt') or ''))
    if not soon or not observed:
        return False
    return (int(soon['hour']) - int(observed.group(1))) % 24 <= hours


def place_of(text: str, vehicle: dict | None = None) -> Place | None:
    match = DESTINATION.search(text)
    raw = match.group('place') if match else str((vehicle or {}).get('destination') or '')
    if not raw:
        return None
    for pattern, kind, name in PLACES:
        found = re.search(pattern, raw)
        if found:
            return Place(kind, name or ('할머니 댁' if kind == 'family' else found.group(0)))
    return Place('other', raw.strip())


def target_day(text: str, clock: str) -> int:
    """Packing is for tomorrow unless the child says today, or it is still before 3 p.m."""
    if '내일' in text:
        return 1
    if '오늘' in text:
        return 0
    hour = re.search(r' (\d{1,2}):', clock or '')
    return 1 if not hour or int(hour.group(1)) >= 15 else 0


def pack_card(facts: list, weather: dict, day: int, destination: Place | None = None, when: str | None = None) -> dict:
    """`when` names a later day ("수요일") when the asked day had nothing and the next school event does."""
    found, occasion = family_items(facts, day)
    weathered, note = weather_items(weather, day) if when is None else ([], '')
    extra = []
    if destination and destination.key in IDEAS and day == 0 and when is None:  # today's trip says nothing about tomorrow's bag
        extra = [_item(label, f'{destination.name} 가는 날', 'destination') for label in IDEAS[destination.key][3]]
    items = _merge(found + weathered + extra)[:6]
    when = when or ('내일' if day else '오늘')
    subtitle = ' · '.join(x for x in [occasion, note] if x)
    return {'kind': 'pack', 'title': f'{when} 챙길 것', 'subtitle': subtitle, 'occasion': occasion,
            'sections': [{'title': '', 'items': items}]}


def _subject(word: str) -> str:
    last = word[-1:] or ' '
    return word + ('이' if '가' <= last <= '힣' and (ord(last) - 0xAC00) % 28 else '가')


def pack_speech(card: dict, day: int, skipped: str = '') -> str:
    """`skipped` says why the asked day was passed over ("내일은 토요일이라 쉬는 날이야!")."""
    items = card['sections'][0]['items']
    when = card['title'].removesuffix(' 챙길 것') or ('내일' if day else '오늘')
    if not items:
        return f'{when}은 따로 챙길 게 없어 보여. 그래도 물 한 병은 늘 좋아!'
    labels = [i['label'] for i in items]
    head = f"{when} {_subject(card['occasion'])} 있어서" if card.get('occasion') else f'{when}은'
    head = f'{skipped} {head}'.strip()
    return f"{head} {', '.join(labels)} 챙기면 돼! 다 챙기면 '다 챙겼어!' 해 줘."


def route_card(place: Place, minutes: int | None, weather: dict, facts: list) -> tuple:
    game, way, arrive, bring = IDEAS.get(place.key, IDEAS['other'])
    rounds = None if minutes is None else 3 if minutes <= 8 else 5 if minutes <= 20 else 8
    way_label = f'{way[1]} {rounds}문제' if rounds and game in ('NATURE', 'ENGLISH', 'MATH') else way[1]
    way_items = [{'icon': way[0], 'label': way_label, 'reason': f'도착까지 {minutes}분' if minutes is not None else '가는 동안'}]
    if place.key == 'nature':
        way_items.append({'icon': '🟢', 'label': '창밖에서 초록색 다섯 개 찾기', 'reason': '눈으로 하는 놀이'})
    wet = rain_within(weather, 4)
    arrive_items = [{'icon': icon, 'label': label, 'reason': ''} for icon, label in arrive]
    if wet and place.key in ('nature', 'zoo'):
        arrive_items[0] = {'icon': '🌧️', 'label': '우비 입고 웅덩이 관찰하기', 'reason': '비 소식'}
    packed, _ = family_items(facts, 0)
    rain = [_item('우산', '오늘 비 소식', 'weather')] if wet else []
    bring_items = _merge(packed + rain + [_item(b, place.name, 'destination') for b in bring])[:3]
    sections = [{'title': '가는 길 놀이', 'items': way_items}, {'title': '도착하면', 'items': arrive_items}]
    if bring_items:
        sections.append({'title': '챙길 것', 'items': bring_items})
    card = {'kind': 'route', 'title': f'{place.name} 가는 길',
            'subtitle': f'도착까지 {minutes}분' if minutes is not None else '함께 가는 길', 'sections': sections}
    return card, game


def route_speech(card: dict, place: Place, minutes: int | None, game: str) -> str:
    way = card['sections'][0]['items'][0]['label']
    arrive = card['sections'][1]['items'][0]['label']
    time = f'도착까지 {minutes}분이니까 ' if minutes is not None else ''
    return (f"{place.name}에 가는구나! {time}가는 길엔 {way} 어때? 도착하면 {arrive}! "
            f"'시작'이라고 말하면 바로 {GAME_WORDS.get(game, '놀이')}를 열게.")
