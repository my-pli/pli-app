"""The edge agent's KidsNote tool: the family's real kindergarten calendar, over the loopback MCP.

The KidsNote MCP (scripts/kidsnote-mcp.mjs, 127.0.0.1:3904, private bearer token) already holds the
signed-in session. The agent asks it for the month's calendar and turns each event into a family
fact ({date, title, text}); "준비물 : 끈달린 물통, 원복" lines then become the packing checklist.
Nothing is written to disk; answers are cached for a few minutes because the site is slow.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from edge_plans import ITEMS

ROOT = Path(__file__).resolve().parents[1]
TOKEN = ROOT / '.tools/private/kidsnote/mcp-token'
URL = 'http://127.0.0.1:3904/mcp'
TIMEOUT_SECONDS = 8
CACHE_SECONDS = 600
LOOK_AHEAD_DAYS = 7
EVENT = re.compile(r'^- (\d{1,2})/(\d{1,2})\([^)]*\) · <([^>]+)> · [^·]+ · (.*)$')
WEEKDAYS = '월화수목금토일'

_cache: dict = {}


def _call(name: str, args: dict) -> str:
    payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}}).encode()
    request = urllib.request.Request(URL, data=payload, headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                                                 'Authorization': 'Bearer ' + TOKEN.read_text().strip()})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        result = json.load(response)['result']
    text = '\n'.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text')
    if result.get('isError'):
        raise RuntimeError(text[:120] or 'KIDSNOTE_ERROR')
    return text


def parse_calendar(text: str, year: int) -> list:
    """`- 11/18(수) · <title> · class · body` lines → [{date, title, text}] (class names are dropped)."""
    events = []
    for line in text.splitlines():
        match = EVENT.match(line.strip())
        if match:
            month, day, title, body = match.groups()
            events.append({'date': date(year, int(month), int(day)).isoformat(), 'title': title.strip(), 'text': body.strip()})
    return events


async def calendar(today: date) -> list:
    """This month's events, plus next month's when the look-ahead crosses into it (cached)."""
    key = today.isoformat()
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    following = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    months = [today, following] if (following - today).days <= LOOK_AHEAD_DAYS + 1 else [today]
    events = []
    for month in months:
        text = await asyncio.to_thread(_call, 'get_calendar', {'month': month.strftime('%Y-%m')})
        events += parse_calendar(text, month.year)
    _cache[key] = (time.monotonic(), events)
    return events


def short_title(title: str) -> str:
    """"지역사회연계활동 '수원 컨벤션 센터 다녀오기'" → "수원 컨벤션 센터 다녀오기"."""
    quoted = re.search(r"['‘\"“]([^'’\"”]+)['’\"”]", title)
    return (quoted.group(1) if quoted else title).strip()


def preparation(event: dict) -> str:
    """The `준비물 : ...` part of an event, '' when it names none. The MCP shortens long lines with
    '…', so a cut last word is completed from the packing vocabulary ('운동…' → '운동화')."""
    match = re.search(r'준비물\s*[:：]\s*([^-]+)', event['text'])
    if not match:
        return ''
    text = match.group(1).strip()
    if text.endswith('…'):
        words = [w.strip() for w in text.rstrip('…').split(',')]
        cut = words[-1]
        whole = next((w for w in ITEMS if w.startswith(cut) and len(cut) >= 2), None)
        words = words[:-1] + ([whole] if whole else [])
        text = ', '.join(w for w in words if w)
    return text


def day_name(when: date, today: date) -> str:
    gap = (when - today).days
    return {0: '오늘', 1: '내일', 2: '모레'}.get(gap, f'{WEEKDAYS[when.weekday()]}요일')


def facts_for(events: list, today: date, day: int) -> tuple:
    """Facts for the asked day; if that day has nothing to bring, the next event within a week
    that does. Returns (facts with `day` set to the asked offset, the date used or None)."""
    asked = today + timedelta(days=day)
    on_day = [e for e in events if e['date'] == asked.isoformat()]
    chosen = on_day
    if not any(preparation(e) for e in on_day):
        last = (asked + timedelta(days=LOOK_AHEAD_DAYS)).isoformat()
        ahead = sorted((e for e in events if asked.isoformat() < e['date'] <= last and preparation(e)), key=lambda e: e['date'])
        chosen = [e for e in ahead if e['date'] == ahead[0]['date']] if ahead else []
    facts = [{'source': 'notice', 'title': short_title(e['title']), 'text': f"{e['title']} 준비물 {preparation(e)}", 'day': day,
              'date': e['date'], 'bring': preparation(e)} for e in chosen if preparation(e)]
    return facts, (date.fromisoformat(facts[0]['date']) if facts else None)
