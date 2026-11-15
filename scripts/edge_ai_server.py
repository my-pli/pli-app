#!/usr/bin/env python3
"""Pli edge AI server: speech recognition, agent and family album on this computer only.

The emulator reaches it at 10.0.2.2:8890 (host loopback). Nothing listens on the LAN,
nothing leaves the machine: ASR is SenseVoice (CPU), the agent is a local llama.cpp model.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from collections import deque
from pathlib import Path

from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parent))
from edge_agent import Agent  # noqa: E402
from edge_asr import RATE, Recognizer, pcm16_to_float  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ALBUM = Path(os.environ.get('PLI_EDGE_ALBUM', ROOT / '.tools/edge-ai/family-album'))
HOST = os.environ.get('PLI_EDGE_HOST', '127.0.0.1')
PORT = int(os.environ.get('PLI_EDGE_PORT', '8890'))
LLM_URL = os.environ.get('PLI_EDGE_LLM', 'http://127.0.0.1:8891')
ASR_TAP = Path(__file__).resolve().parents[1] / '.tools/edge-ai/asr-tap'  # private; created by hand for a measurement
MAX_PCM_BYTES = 16000 * 2 * 15
NAME = re.compile(r'^[0-9a-f]{16}\.jpg$|^avatar\.jpg$')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('pli-edge')
metrics = {'asr': deque(maxlen=200), 'agent': deque(maxlen=200), 'started': time.time()}


def load_album() -> dict | None:
    try:
        return json.loads((ALBUM / 'album.json').read_text())
    except (OSError, ValueError):
        return None


recognizer = Recognizer(os.environ.get('PLI_EDGE_ASR', 'sensevoice'), int(os.environ.get('PLI_EDGE_ASR_THREADS', '4')))
agent = Agent(LLM_URL, load_album, ALBUM / 'album-story.json')
agent_lock = asyncio.Lock()


def p50(values) -> int | None:
    data = sorted(values)
    return data[len(data) // 2] if data else None


async def health(_request: web.Request) -> web.Response:
    llm = await agent.health()
    album = load_album()
    return web.json_response({'ok': recognizer.ready and llm.get('ready', False),
                              'asr': {'engine': recognizer.engine, 'ready': recognizer.ready, 'p50Ms': p50(metrics['asr'])},
                              'llm': {**llm, 'p50Ms': p50(metrics['agent'])},
                              'album': {'photos': len((album or {}).get('photos', [])), 'child': (album or {}).get('child')},
                              'edge': 'on-device', 'uptime': round(time.time() - metrics['started'])})


async def asr(request: web.Request) -> web.Response:
    if not recognizer.ready:
        return web.json_response({'error': 'ASR_NOT_READY'}, status=503)
    body = await request.read()
    if ASR_TAP.is_dir():  # diagnostics only: exists while the microphone path is being measured
        (ASR_TAP / f'{time.time():.3f}.pcm').write_bytes(body)
    if not body or len(body) > MAX_PCM_BYTES:
        return web.json_response({'error': 'PCM_SIZE'}, status=413)
    result = await asyncio.to_thread(recognizer.transcribe, pcm16_to_float(body))
    metrics['asr'].append(result.ms)
    log.info('asr %.1fs %dms rejected=%s text=%r', result.seconds, result.ms, result.rejected, result.text[:60])
    return web.json_response({'text': result.text, 'engine': result.engine, 'ms': result.ms,
                              'seconds': round(result.seconds, 2), 'rejected': result.rejected})


async def agent_turn(request: web.Request) -> web.StreamResponse:
    try:
        data = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(text='JSON body required')
    text = str(data.get('text', '')).strip()
    context = data.get('context') if isinstance(data.get('context'), dict) else {}
    if not text and context.get('proactive') != 'route-stop':  # Pli may speak first only for the route-stop offer
        raise web.HTTPBadRequest(text='text required')
    response = web.StreamResponse(headers={'Content-Type': 'application/x-ndjson', 'Cache-Control': 'no-store'})
    await response.prepare(request)

    async def emit(event: dict) -> None:
        await response.write((json.dumps(event, ensure_ascii=False) + '\n').encode())

    started = time.monotonic()
    try:
        async with agent_lock:  # one turn at a time on the CPU model
            final = await agent.run(text, context, emit)
        metrics['agent'].append(final['ms'])
        log.info('agent %dms action=%s text=%r speech=%r', final['ms'], final['action']['name'], text[:40], final['speech'][:60])
    except Exception as exc:
        log.exception('agent failed')
        await emit({'type': 'error', 'message': '엣지 AI가 답을 만들지 못했어요.', 'code': type(exc).__name__,
                    'ms': round((time.monotonic() - started) * 1000)})
    await response.write_eof()
    return response


def public_album(manifest: dict) -> dict:
    photos = [{k: p.get(k) for k in ('id', 'file', 'width', 'height', 'focus', 'faceBox', 'scene', 'child')} for p in manifest['photos']]
    return {'child': manifest.get('child'), 'avatar': manifest.get('avatar'), 'photos': photos, 'method': manifest.get('method')}


async def album(_request: web.Request) -> web.Response:
    manifest = load_album()
    if not manifest:
        return web.json_response({'error': 'ALBUM_EMPTY'}, status=404)
    return web.json_response(public_album(manifest), headers={'Cache-Control': 'no-store'})


async def photo(request: web.Request) -> web.FileResponse:
    name = request.match_info['name']
    if not NAME.match(name) or not (ALBUM / name).is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(ALBUM / name, headers={'Cache-Control': 'private, max-age=3600'})


async def warm() -> None:
    """Load the system prompt into the llama.cpp cache so the first child question is fast."""
    async def ignore(_event: dict) -> None:
        return None
    for _ in range(90):
        if (await agent.health()).get('ready'):
            try:
                async with agent_lock:
                    await agent.run('안녕 플리', {'child': '하연', 'demo': True}, ignore)
                    story = await agent.album_story()
                log.info('agent warmed (%s); album story %r', agent.model, story and story['title'])
            except Exception:
                log.exception('warm-up failed')
            return
        await asyncio.sleep(2)


def warm_asr() -> int:
    """The first decodes after a start are several times slower; spend them before a child speaks."""
    import numpy as np
    noise = (np.random.default_rng(0).standard_normal(RATE * 2) * 0.05).astype(np.float32)
    started = time.monotonic()
    for _ in range(2):
        recognizer.transcribe(noise)
    return round((time.monotonic() - started) * 1000)


async def startup(app: web.Application) -> None:
    await agent.start()
    await asyncio.to_thread(recognizer.load)
    log.info('ASR ready (%s); warmed in %d ms; LLM at %s', recognizer.engine, await asyncio.to_thread(warm_asr), LLM_URL)
    app['warm'] = asyncio.create_task(warm())


async def cleanup(app: web.Application) -> None:
    app['warm'].cancel()
    await agent.close()


def main() -> None:
    app = web.Application(client_max_size=MAX_PCM_BYTES + 1024)
    app.router.add_get('/v1/health', health)
    app.router.add_post('/v1/asr', asr)
    app.router.add_post('/v1/agent', agent_turn)
    app.router.add_get('/v1/album', album)
    app.router.add_get('/v1/album/photo/{name}', photo)
    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)
    web.run_app(app, host=HOST, port=PORT, access_log=None)


if __name__ == '__main__':
    main()
