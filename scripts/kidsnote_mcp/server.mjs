// 키즈노트 MCP 서버(외부 패키지 없음, Node 내장 기능만): Streamable HTTP, 상태 없음, JSON 응답.
// 주소는 http://127.0.0.1:3904/mcp 로 고정(사용자 결정: 어느 PC에서나 같은 주소).
// 아이디 · 비밀번호: 이 폴더(또는 exe 옆)의 key.txt(id= · pw=). 로그인에 실패하면 도구가 "아이디 · 비밀번호를 물어 login 도구로"라고
// 답하고, login 도구가 성공하면 key.txt를 고쳐 쓴다. 도구 인자(비밀번호)는 기록에 남기지 않는다.
import http from 'node:http';
import { TOOLS, callTool } from './tools.mjs';
import { setKeyDirs as setSiteKeyDirs } from './site.mjs';
import { SYNC_TOOLS, syncTool } from './sync.mjs';
import {VOICE_TOOLS,voiceAnswer}from './voice.mjs';

export const VERSION = '1.0.0';
export const PORT = 3904;
export const TITLE = '키즈노트 MCP'; // GET / 첫 줄. 망무물 · main.mjs가 "같은 서버가 이미 떠 있는지" 알아볼 때 쓴다
export { TOOLS, callTool };
const PROTOCOLS = ['2025-06-18', '2025-03-26', '2024-11-05'];

/** 망무물이 같은 프로세스로 띄울 때 mcp/kidsnote 폴더를 알려 준다(key.txt 위치) */
export function setKeyDirs(dirs) { setSiteKeyDirs(dirs); }

const INSTRUCTIONS = [
  '키즈노트(어린이집 · 유치원 알림장 앱) 학부모 계정을 읽기만 한다: 공지사항 · 알림장 · 앨범 · 일정표 · 식단표 · 알림.',
  '매달 올라오는 공지(놀이계획안 · 특별활동 등)는 get_monthly_notice, 공지 검색은 search_notices → get_notice.',
  '첨부 파일 · 사진은 save_dir(망무물 세션 정보의 출력 경로)를 주면 받아서 <<file:경로>> 줄을 돌려준다. 그 줄을 답변에 그대로 넣으면 사진은 답변 창에 사진으로, 문서는 파일 카드로 보인다. 첨부 문서 내용은 kordoc으로 읽어 답한다.',
  '계정에 키즈노트를 쓰는 곳(어린이집 · 학원 등)이 여러 곳이면 도구가 선택지를 돌려준다. 그때는 어느 곳의 정보를 볼지 사용자에게 물어본 뒤 center에 넣어 다시 부른다. 한 곳이면 묻지 않는다.',
  '식단 · 앨범 · 알림장 · 공지를 물으면 처음부터 save_dir를 함께 줘서, 사진이 있으면 따로 묻지 않고 답변에 사진도 같이 보여 준다.',
  '로그인에 실패했다는 답이 오면 사용자에게 키즈노트 아이디와 비밀번호를 물어 login 도구로 로그인한다. 비밀번호는 답변에 다시 적지 않는다.',
  '답변 출처에는 결과 끝의 키즈노트 주소를 적는다.',
].join(' ');

async function handleRpc(msg) {
  if (!msg || msg.jsonrpc !== '2.0' || typeof msg.method !== 'string') {
    return { jsonrpc: '2.0', id: msg?.id ?? null, error: { code: -32600, message: 'Invalid Request' } };
  }
  const isNote = msg.id === undefined || msg.id === null;
  const ok = (result) => (isNote ? null : { jsonrpc: '2.0', id: msg.id, result });
  switch (msg.method) {
    case 'initialize': {
      const want = msg.params?.protocolVersion;
      return ok({
        protocolVersion: PROTOCOLS.includes(want) ? want : PROTOCOLS[1],
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'kidsnote', title: '키즈노트', version: VERSION },
        instructions: INSTRUCTIONS,
      });
    }
    case 'ping': return ok({});
    case 'tools/list': return ok({ tools: [...TOOLS,...SYNC_TOOLS,...VOICE_TOOLS] });
    case 'tools/call':
      try {
        if(VOICE_TOOLS.some(t=>t.name===msg.params?.name)){const data=await voiceAnswer(msg.params.arguments??{});return ok({structuredContent:data,content:[{type:'text',text:JSON.stringify(data)}]});}
        if(SYNC_TOOLS.some(t=>t.name===msg.params?.name)){const data=await syncTool(msg.params.name,msg.params.arguments??{});return ok({structuredContent:data,content:[{type:'text',text:JSON.stringify(data)}]});}
        if(msg.params?.arguments?.save_dir)throw new Error('첨부 저장은 이 앱에서 사용하지 않습니다.');
        return ok({ content: [{ type: 'text', text: await callTool(msg.params?.name, msg.params?.arguments) }] });
      } catch (e) {
        return ok({ content: [{ type: 'text', text: String(e?.message ?? e) }], isError: true });
      }
    case 'resources/list': return ok({ resources: [] });
    case 'prompts/list': return ok({ prompts: [] });
    default:
      if (msg.method.startsWith('notifications/')) return null;
      return isNote ? null : { jsonrpc: '2.0', id: msg.id, error: { code: -32601, message: `Method not found: ${msg.method}` } };
  }
}

const LOCAL_HOST = /^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/i;
const LOCAL_ORIGIN = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/i;

export function createServer({ log = () => {}, token = "" } = {}) {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://x');
    if(token&&req.headers.authorization!==`Bearer ${token}`){res.writeHead(401).end('unauthorized');return;}
    // 다른 웹 페이지가 브라우저를 통해 부르지 못하게(DNS 리바인딩 방지)
    const origin = req.headers.origin;
    if (!LOCAL_HOST.test(req.headers.host ?? '') || (origin && !LOCAL_ORIGIN.test(origin))) { res.writeHead(403).end('forbidden'); return; }
    if (url.pathname === '/' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end(`${TITLE} ${VERSION}\nMCP 주소: http://${req.headers.host}/mcp\n`);
      return;
    }
    if (url.pathname !== '/mcp') { res.writeHead(404).end('not found'); return; }
    if (req.method !== 'POST') { res.writeHead(405, { Allow: 'POST' }).end(); return; }
    let body = '';
    for await (const c of req) { body += c; if (body.length > 1e6) { res.writeHead(413).end(); return; } }
    let msg;
    try { msg = JSON.parse(body); } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }));
      return;
    }
    const batch = Array.isArray(msg);
    // 도구 이름만 남긴다(login의 비밀번호 등 인자는 기록하지 않음)
    for (const m of batch ? msg : [msg]) if (m?.method === 'tools/call') log(`도구 ${m.params?.name}`);
    const replies = (await Promise.all((batch ? msg : [msg]).map((m) => handleRpc(m)))).filter(Boolean);
    if (!replies.length) { res.writeHead(202).end(); return; }
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(batch ? replies : replies[0]));
  });
}

/** 정해진 포트 하나에만 띄운다(다른 포트로 넘어가지 않음) */
export function listen(server, port = PORT) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server.address().port));
  });
}
