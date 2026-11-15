"""Deterministic word games for the edge agent: 끝말잇기 and 수수께끼.

A small model cannot be trusted to produce a valid next word, so the rules live here.
State is per app session and expires after ten idle minutes.
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field

WORDS = """기차 차표 표범 범고래 스키 키위 위성 이불 불꽃 꽃게 게임 사과 과자 자두 두부 부엉이 이사 사자 자동차 차고 고구마 마차
차례 예술 술래 미소 소나무 무지개 개구리 더하기 기린 바나나 나비 비누 누나 나무 나팔 팔찌 찌개 개미 미끄럼틀 트럭 럭비
비행기 기타 타조 조개 개나리 리듬 북극곰 곰인형 형광펜 연필 필통 통조림 보물 물고기 역사 사탕 탕수육 육지 지구 구름 바다
다람쥐 쥐포 포도 도토리 리모컨 너구리 카메라 라면 면봉 봉투 투표 판다 다리미 미역 역도 도마 마술 병아리 터널 널뛰기 기러기
기름 오리 리본 우유 유리 진주 주스 스케치북 북소리 조약돌 돌고래 고래 빗자루 루비 비둘기 기둥 둥지 지우개 개울 울타리 호랑이
이빨 빨대 대나무 무당벌레 레몬 몬스터 키보드 드레스 스웨터 전기 기억 억새 새우 우산 산타 타이어 어항 항아리 눈사람 보라색
색연필 강아지 지도 도서관 관람차 도로 로봇 짐볼 볼링 공룡 용기 기와 와플 플루트 수박 박쥐 멍멍이 이야기 기적 군고구마 마늘
늘보 보리 코끼리 그네 네모 모자 자석 석류 유치원 원숭이 이슬 슬리퍼 퍼즐 토끼 니모 모래 각도기 기념일 일기 기분 분수 수영
영어 어머니 은행 행복 복숭아 아이스크림 팬더 더위 양말 말랑이 이름 하늘 늑대 대추 추석 석탄 수건 건포도 도넛 김밥 솜사탕
탁구 구슬 고양이 이모 모기 여우 우체통 통나무 무 무릎 용궁 궁전 전화 화분 분홍색 색종이 이마 마스크 크레파스 스티커 커튼
튼튼이 이웃 웃음 음악 악어 어부 부채 채소 소방차 차표 표정 정원 원피스 스프 프린터 터키 키 키다리 리어카 카드 드럼 럼 노래
래미 미술 술 나라 라디오 오이 이불 불 낙엽 엽서 서랍 랍스터 터전 전등 등대 대문 문어 어묵 묵 묵찌빠 빠른우편 편지 지붕 붕어빵
빵 빵집 집게 게 계단 단추 추 축구 구두 두더지 지렁이 이삿짐 짐 짐차 장갑 갑옷 옷 옷걸이 이끼 끼 기지개 개똥벌레 레고 고무줄
줄넘기 기분 분필 필름 름 감자 자전거 거북이 이층버스 스노우볼 볼펜 펜 펭귄 귀 귤 귤껍질 질문 문 문방구 구름다리 리본끈""".split()
DUEUM = {'라': '나', '래': '내', '로': '노', '뢰': '뇌', '루': '누', '르': '느', '리': '이', '랴': '야', '려': '여',
         '례': '예', '료': '요', '류': '유', '녀': '여', '뇨': '요', '뉴': '유', '니': '이', '랑': '낭', '량': '양',
         '력': '역', '련': '연', '령': '영', '록': '녹', '론': '논', '룡': '용', '림': '임', '립': '입', '름': '음'}
VOCAB = sorted({w for w in WORDS if len(w) >= 2 and re.fullmatch(r'[가-힣]+', w)})
ENDINGS = re.compile(r'(이야|이에요|예요|이지|야|요|!|\?|\.|~)+$')

RIDDLES = [
    ('다리는 넷인데 걷지 못하는 건 뭘까?', ['의자', '책상', '식탁'], '앉을 때 쓰는 거야.'),
    ('세수를 할수록 더 더러워지는 건 뭘까?', ['물', '세숫물'], '세수할 때 손에 담는 거야.'),
    ('입은 있는데 말을 못 하고, 물건을 먹으면 배가 불룩해지는 건?', ['가방', '책가방'], '등에 메고 유치원 가!'),
    ('하늘에서 내려오는데 땅에 닿으면 녹아 사라지는 하얀 건?', ['눈', '눈송이'], '겨울에 오는 거야.'),
    ('얼굴은 하나고 바늘이 빙글빙글 도는 건 뭘까?', ['시계'], '시간을 알려 줘.'),
    ('물에 넣으면 사라지고 단맛이 나는 하얀 가루는?', ['설탕'], '달콤한 가루야.'),
    ('밤에 뜨고 매일 모양이 조금씩 바뀌는 건?', ['달'], '토끼가 산다는 이야기가 있어.'),
    ('발이 없는데 집집마다 찾아가는 종이는?', ['편지', '우편'], '우체부 아저씨가 가져다줘.'),
    ('귀가 길고 깡충깡충 뛰는 동물은?', ['토끼'], '당근을 좋아해.'),
    ('목이 아주 길어서 높은 나뭇잎을 먹는 동물은?', ['기린'], '노란 몸에 무늬가 있어.'),
]


def ro(word: str) -> str:
    """'기차로', '문어로', '곰으로' - Korean instrumental particle for the last syllable."""
    last = word[-1]
    if not '가' <= last <= '힣':
        return word + '로'
    jong = (ord(last) - ord('가')) % 28
    return word + ('로' if jong in (0, 8) else '으로')


def first_options(syllable: str) -> set[str]:
    return {syllable, DUEUM.get(syllable, syllable)}


def extract_word(text: str) -> str:
    words = re.findall(r'[가-힣]{2,}', text.strip())
    return ENDINGS.sub('', words[-1]) if words else ''


@dataclass
class GameState:
    kind: str
    last: str = ''
    used: set = field(default_factory=set)
    riddle: int = -1
    asked: list = field(default_factory=list)
    touched: float = field(default_factory=time.monotonic)


class Games:
    def __init__(self) -> None:
        self.states: dict[str, GameState] = {}

    def _get(self, session: str) -> GameState | None:
        state = self.states.get(session)
        if state and time.monotonic() - state.touched > 600:
            self.states.pop(session, None)
            return None
        return state

    def active(self, session: str) -> str | None:
        state = self._get(session)
        return state.kind if state else None

    def stop(self, session: str) -> None:
        self.states.pop(session, None)

    def start(self, session: str, kind: str) -> str:
        if kind == 'WORDCHAIN':
            word = random.choice([w for w in VOCAB if len(w) == 2 and any(v[0] in first_options(w[-1]) for v in VOCAB if v != w)])
            self.states[session] = GameState('WORDCHAIN', last=word, used={word})
            return f"좋아, 끝말잇기 시작! 내가 먼저 할게. {word}! 이제 '{word[-1]}' 자로 시작하는 말을 말해 줘."
        state = GameState('RIDDLE')
        self.states[session] = state
        return '수수께끼 시작! ' + self._next_riddle(state)

    def _next_riddle(self, state: GameState) -> str:
        left = [i for i in range(len(RIDDLES)) if i not in state.asked] or list(range(len(RIDDLES)))
        state.riddle = random.choice(left)
        state.asked.append(state.riddle)
        return RIDDLES[state.riddle][0]

    def play(self, session: str, text: str, child: str) -> tuple[str, str]:
        """Returns (speech, step detail). Empty speech means no game is running."""
        state = self._get(session)
        if state is None:
            return '', '진행 중인 놀이 없음'
        state.touched = time.monotonic()
        if re.search(r'(그만|끝내|안 할래|다른 놀이)', text):
            self.stop(session)
            return '재미있었어! 다음에 또 하자.', '놀이 마침'
        if state.kind == 'RIDDLE':
            _question, answers, hint = RIDDLES[state.riddle]
            if re.search(r'(몰라|힌트|어려워)', text):
                return f'힌트! {hint}', '힌트 주기'
            if re.search(r'(정답 알려|답 알려|포기)', text):
                return f'정답은 {answers[0]}였어! 다음 문제. ' + self._next_riddle(state), '정답 공개'
            if any(a in text.replace(' ', '') for a in answers):
                return f'딩동댕! 정답은 {answers[0]}! 다음 문제. ' + self._next_riddle(state), f'정답 확인: {answers[0]}'
            return f'음, 아쉽지만 아니야. 힌트를 줄게. {hint}', '오답 확인'
        word = extract_word(text)
        tail = state.last[-1]
        if not word:
            return f"'{tail}' 자로 시작하는 말을 하나 말해 줘.", '단어를 찾지 못함'
        if word[0] not in first_options(tail):
            return f"앗, '{tail}' 자로 시작해야 해. 다시 해 볼까?", f'규칙 확인: {word}'
        if word in state.used:
            return f'{word}는 벌써 나왔어. 다른 말을 찾아볼래?', f'중복 확인: {word}'
        state.used.add(word)
        candidates = [w for w in VOCAB if w[0] in first_options(word[-1]) and w not in state.used]
        if not candidates:
            self.stop(session)
            return f"우와, {word}! '{word[-1]}' 자로 시작하는 말이 생각 안 나. {child} 승리야!", f'단어장 탐색: {word[-1]} 없음'
        reply = random.choice(candidates)
        state.used.add(reply)
        state.last = reply
        return f"{word}, 좋아! 그럼 나는 {reply}! 이제 '{reply[-1]}' 자로 시작하는 말!", f'단어장 탐색: {word[-1]} → {reply}'
