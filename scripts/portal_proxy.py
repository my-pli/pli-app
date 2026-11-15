"""The original entry point forwards public traffic to the isolated runtime only."""
import asyncio, contextlib
from aiohttp import web,ClientSession,ClientTimeout,WSMsgType,ClientError

async def forward_public(request, public_origin):
    headers={k:v for k,v in request.headers.items() if k.lower() not in {'host','connection','upgrade','content-length','sec-websocket-key','sec-websocket-version','sec-websocket-extensions'}}
    headers['Host']='pli-public.local'
    if 'Origin' in headers:headers['Origin']=public_origin
    url='http://127.0.0.1:8878'+request.raw_path
    try:
        async with ClientSession(timeout=ClientTimeout(total=None,connect=3),auto_decompress=False) as session:
            if request.headers.get('Upgrade','').lower()=='websocket':
                async with session.ws_connect(url,headers=headers,max_msg_size=8*1024*1024) as upstream:
                    downstream=web.WebSocketResponse(max_msg_size=8*1024*1024)
                    await downstream.prepare(request)
                    async def relay(a,b):
                        async for message in a:
                            if message.type==WSMsgType.BINARY:await b.send_bytes(message.data)
                            elif message.type==WSMsgType.TEXT:await b.send_str(message.data)
                            else:break
                    tasks=[asyncio.create_task(relay(upstream,downstream)),asyncio.create_task(relay(downstream,upstream))]
                    await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                    for task in tasks:task.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
                    await downstream.close();return downstream
            async with session.request(request.method,url,headers=headers,data=request.content,allow_redirects=False) as response:
                result=web.StreamResponse(status=response.status,headers={k:v for k,v in response.headers.items() if k.lower() not in {'transfer-encoding','connection','content-encoding'}})
                await result.prepare(request)
                if request.method!='HEAD':
                    async for chunk in response.content.iter_chunked(65536):await result.write(chunk)
                await result.write_eof();return result
    except (ClientError,ConnectionError,asyncio.TimeoutError,OSError):
        return web.json_response({'error':'public_runtime_unavailable','message':'공개 시연 환경을 연결하고 있어요. 잠시 뒤 다시 열어 주세요.'},status=503)
