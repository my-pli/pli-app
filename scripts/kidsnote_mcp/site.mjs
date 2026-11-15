// 키즈노트(www.kidsnote.com) 학부모 계정으로 읽기만 한다. 외부 패키지 없음.
// 로그인: www.kidsnote.com/kr/login 에 아이디 · 비밀번호(form) → sessionid 쿠키 → kapi.kidsnote.com JSON API에 그 쿠키를 붙인다.
// 아이디 · 비밀번호는 key.txt(id= · pw= 두 줄)에서 읽고, login 도구로 새로 로그인에 성공하면 key.txt를 고쳐 쓴다.
// 같은 아이디 · 비밀번호로 실패하면 다시 시도하지 않는다(계정 잠김 방지). 새 값이 오거나 key.txt가 바뀌어야 다시 시도한다.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const WEB = 'https://www.kidsnote.com';
export const API = 'https://kapi.kidsnote.com';
export const DOWNLOAD_FOLDER = '내려받은 자료'; // backend/src/paths.js DOWNLOAD_FOLDER와 같아야 한다
export const SUB_FOLDER = '키즈노트';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
const TIMEOUT = 30000;

// ---------- 아이디 · 비밀번호 (key.txt) ----------
let keyDirs = [];
export function setKeyDirs(dirs) { keyDirs = Array.isArray(dirs) ? dirs : []; }
const candidateDirs = () => keyDirs.length?keyDirs:[path.dirname(process.execPath),process.cwd()];

export function parseKey(text) {
  const kv = {};
  for (const line of String(text ?? '').split(/\r?\n/)) {
    const i = line.indexOf('=');
    if (i > 0) kv[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
  }
  return kv.id && kv.pw ? { id: kv.id, pw: kv.pw } : null;
}

/** → {id, pw, file} | null */
export function readKey() {
  for (const d of candidateDirs()) {
    const file = path.join(d, 'key.txt');
    try {
      const k = parseKey(fs.readFileSync(file, 'utf8'));
      if (k) return { ...k, file };
    } catch { /* 없음 */ }
  }
  return null;
}

/** 로그인에 성공한 값을 key.txt에 쓴다(있던 파일이 있으면 그 자리, 없으면 MCP 폴더) */
export function writeKey(id, pw) {
  const file = readKey()?.file ?? path.join(keyDirs[0] ?? path.dirname(process.execPath), 'key.txt');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `id=${id}\npw=${pw}\n`, {encoding:'utf8',mode:0o600});fs.chmodSync(file,0o600);
  return file;
}

// ---------- 로그인 상태 ----------
export class NeedLogin extends Error {
  constructor(reason) {
    super(`${reason} 사용자에게 키즈노트 아이디와 비밀번호를 물어본 뒤 login 도구(id, pw)로 로그인하세요. `
      + '로그인에 성공하면 key.txt에 저장되어 다음부터는 묻지 않습니다. 비밀번호는 답변에 다시 적지 마세요.');
    this.code = 'NEED_LOGIN';
  }
}

const state = { cookie: '', ctx: null, failed: '', pending: null };
const fp = (id, pw) => crypto.createHash('sha256').update(`${id}\n${pw}`).digest('hex');
export function resetSession() { state.cookie = ''; state.ctx = null; state.failed = ''; state.pending = null; }

async function fetchT(url, opts = {}, ms = TIMEOUT) {
  try {
    return await fetch(url, { ...opts, signal: AbortSignal.timeout(ms) });
  } catch (e) {
    throw new Error(`키즈노트에 연결하지 못했습니다(${e.name === 'TimeoutError' ? '응답 없음' : e.message}).`);
  }
}

export async function seedSession(cookie) {
  const ctx=await verify(cookie);if(!ctx)throw new Error("AUTH_REQUIRED");state.cookie=cookie;state.ctx=ctx;return ctx;
}

function cookieFrom(res) {
  const out = {};
  for (const c of res.headers.getSetCookie?.() ?? []) {
    const [pair] = c.split(';');
    const i = pair.indexOf('=');
    if (i > 0) out[pair.slice(0, i).trim()] = pair.slice(i + 1).trim();
  }
  return out;
}

/** 아이디 · 비밀번호로 로그인 → 쿠키 문자열. 틀리면 null */
async function postLogin(id, pw) {
  const body = new URLSearchParams({ username: id, password: pw, remember_me: 'on' });
  const r = await fetchT(`${WEB}/kr/login`, {
    method: 'POST', redirect: 'manual', body,
    headers: { 'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded', Origin: WEB, Referer: `${WEB}/login` },
  });
  const jar = cookieFrom(r);
  if (!jar.sessionid) return null;
  return Object.entries(jar).map(([k, v]) => `${k}=${v}`).join('; ');
}

async function rawGet(pathname, params, cookie, deadline) {
  const u = new URL(pathname, API);
  if(u.origin!==API||!u.pathname.startsWith("/v1"))throw new Error("UNTRUSTED_API_PATH");
  for (const [k, v] of Object.entries(params ?? {})) if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, String(v));
  const r = await fetchT(u, { redirect: 'error', headers: { 'User-Agent': UA, Cookie: cookie, Origin: WEB, Referer: `${WEB}/`, Accept: 'application/json' } },deadline?Math.max(1,Math.min(TIMEOUT,deadline-Date.now())):TIMEOUT);
  return r;
}

/** /v1/me/info → 아이 · 원 · 반 */
export function contextFromMe(me) {
  const children = (me?.children ?? []).map((c) => {
    const enr = (c.enrollment ?? []).filter((e) => e.is_approved !== false && !e.removed_child);
    const centers = new Map();
    for (const e of enr) {
      if (!centers.has(e.center_id)) centers.set(e.center_id, { id: e.center_id, name: e.center_name, classes: [] });
      const cen = centers.get(e.center_id);
      if (e.belong_to_class && !cen.classes.some((x) => x.id === e.belong_to_class)) cen.classes.push({ id: e.belong_to_class, name: e.class_name });
    }
    return { id: c.id, name: c.name, birth: c.date_birth, centers: [...centers.values()] };
  });
  return { user: me?.user?.name ?? '', accountId:me?.user?.id??me?.id, children };
}

/** 쿠키로 /v1/me/info를 불러 확인 → ctx. 쿠키가 안 통하면 null */
async function verify(cookie) {
  const r = await rawGet('/v1/me/info/', null, cookie);
  if (r.status === 401 || r.status === 403) return null;
  if (!r.ok) throw new Error(`키즈노트 정보를 불러오지 못했습니다(HTTP ${r.status}).`);
  return contextFromMe(await r.json());
}

/** 주어진 아이디 · 비밀번호로 로그인(login 도구). 성공하면 key.txt를 고쳐 쓴다 */
export async function loginWith(id, pw) {
  id = String(id ?? '').trim();
  pw = String(pw ?? '');
  if (!id || !pw) throw new Error('id와 pw를 모두 주세요.');
  const cookie = await postLogin(id, pw);
  const ctx = cookie ? await verify(cookie) : null;
  if (!ctx) {
    state.failed = fp(id, pw);
    throw new NeedLogin('아이디 또는 비밀번호가 맞지 않아 키즈노트에 로그인하지 못했습니다.');
  }
  state.cookie = cookie;
  state.ctx = ctx;
  state.failed = '';
  const file = writeKey(id, pw);
  return { ctx, file };
}

async function loginFromKey() {
  const k = readKey();
  if (!k) throw new NeedLogin('키즈노트 아이디 · 비밀번호가 아직 저장되어 있지 않습니다.');
  if (state.failed === fp(k.id, k.pw)) throw new NeedLogin('저장된 아이디 또는 비밀번호로 로그인하지 못했습니다(계정 잠김을 막으려고 같은 값으로 다시 시도하지 않습니다).');
  const cookie = await postLogin(k.id, k.pw);
  const ctx = cookie ? await verify(cookie) : null;
  if (!ctx) {
    state.failed = fp(k.id, k.pw);
    throw new NeedLogin('저장된 아이디 또는 비밀번호로 키즈노트에 로그인하지 못했습니다(비밀번호가 바뀌었을 수 있습니다).');
  }
  state.cookie = cookie;
  state.ctx = ctx;
}

/** 로그인된 상태를 보장한다(동시에 여러 도구가 불려도 로그인은 한 번) */
export async function ensureSession() {
  if (state.cookie && state.ctx) return state.ctx;
  if (!state.pending) state.pending = loginFromKey().finally(() => { state.pending = null; });
  await state.pending;
  return state.ctx;
}

/** API GET → JSON. 세션이 끊겼으면 한 번 다시 로그인한다 */
export async function api(pathname, params, {deadline}={}) {
  await ensureSession();
  let r = await rawGet(pathname, params, state.cookie,deadline);
  if (r.status === 401) {
    state.cookie = '';
    state.ctx = null;
    await ensureSession();
    r = await rawGet(pathname, params, state.cookie,deadline);
  }
  if (r.status === 404) throw new Error('키즈노트에서 그 글을 찾지 못했습니다(지워졌거나 번호가 틀림).');
  if (r.status === 403) throw new Error('이 계정으로는 볼 수 없는 내용입니다(권한 없음).');
  if (!r.ok) throw new Error(`키즈노트 응답 오류(HTTP ${r.status}).`);
  return r.json();
}

/** 쪽을 넘기며 모은다. next는 쪽 번호이거나 커서 문자열이고, 둘 다 page=로 넘긴다. stop(item)이 true면 그만 */
export async function collect(pathname, params, { max = 200, pages = 10, stop } = {}) {
  const out = [];
  let page;
  for (let i = 0; i < pages; i++) {
    const j = await api(pathname, { ...params, ...(page ? { page } : {}) });
    const items = Array.isArray(j) ? j : j?.results;
    if(!Array.isArray(items))throw new Error("UNSUPPORTED_SCHEMA");
    for (const it of items) {
      if (stop?.(it)) return out;
      out.push(it);
      if (out.length >= max) return out;
    }
    if (!j.next || !items.length) break;
    page = j.next;
  }
  return out;
}

/** Bounded query with explicit evidence: a filtered empty page is never global absence. */
export async function collectWithCoverage(pathname,params,{max=1000,pages=20,deadline=Date.now()+8000}={}){
 const items=[];const seen=new Set();let page,pagesRead=0;
 const result=(complete,hasMore,reason)=>({items,coverage:{complete,pagesRead,hasMore,reason}});
 for(let i=0;i<pages;i++){
  if(Date.now()>=deadline)return result(false,true,'DEADLINE');
  let j;try{j=await api(pathname,{...params,...(page===undefined?{}:{page})},{deadline});}catch(e){if(!pagesRead)throw e;return result(false,true,'PAGE_FAILED');}
  const rows=Array.isArray(j)?j:j?.results;if(!Array.isArray(rows))throw new Error('UNSUPPORTED_SCHEMA');pagesRead++;
  const next=Array.isArray(j)?null:j.next;
  for(let k=0;k<rows.length;k++){if(items.length>=max)return result(false,true,'ITEM_LIMIT');items.push(rows[k]);}
  if(!next)return result(true,false,'END');
  if(!rows.length||seen.has(String(next)))return result(false,true,'CURSOR_REPEATED');
  seen.add(String(next));page=next;
 }
 return result(false,true,'PAGE_LIMIT');
}

// ---------- 날짜 ----------
const pad2 = (n) => String(n).padStart(2, '0');
const WEEK = ['일', '월', '화', '수', '목', '금', '토'];
export const dateKey = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
/** API 시각(UTC) → 한국 날짜 'YYYY-MM-DD' */
export function kstDate(iso) {
  if (!iso) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return String(iso).slice(0, 10);
  return new Date(t + 9 * 3600000).toISOString().slice(0, 10);
}
export function dayLabel(key) {
  const [y, m, d] = String(key).split('-').map(Number);
  if (!y || !m || !d) return String(key);
  return `${m}/${d}(${WEEK[new Date(y, m - 1, d).getDay()]})`;
}
export function todayKst(now = new Date()) { return kstDate(now.toISOString()); }

/** '2026-11' · '11월' · '11' · '이번 달' · '지난달' · '다음 달' → {y, m}. 못 읽으면 null */
export function parseMonth(input, now = new Date()) {
  const s = String(input ?? '').replace(/\s+/g, '');
  const [ty, tm] = todayKst(now).split('-').map(Number);
  const shift = (n) => { const d = new Date(ty, tm - 1 + n, 1); return { y: d.getFullYear(), m: d.getMonth() + 1 }; };
  if (!s || /^(이번|이달|금월)/.test(s)) return s ? shift(0) : null;
  if (/^(지난|저번|전)달|^지난월|^전월/.test(s)) return shift(-1);
  if (/^(다음|담)달|^내달|^익월/.test(s)) return shift(1);
  let m = /^(\d{4})[-./년]?(\d{1,2})월?$/.exec(s);
  if (m && Number(m[2]) >= 1 && Number(m[2]) <= 12) return { y: Number(m[1]), m: Number(m[2]) };
  m = /^(\d{1,2})월?$/.exec(s);
  if (m && Number(m[1]) >= 1 && Number(m[1]) <= 12) {
    // 연도 없이 월만: 지금과 가장 가까운 그 달(11월에 "1월"이면 내년 1월, 2월에 "12월"이면 작년 12월)
    const mm = Number(m[1]);
    const cands = [ty - 1, ty, ty + 1].map((y) => ({ y, m: mm, gap: Math.abs((y - ty) * 12 + (mm - tm)) }));
    cands.sort((a, b) => a.gap - b.gap || b.y - a.y);
    return { y: cands[0].y, m: mm };
  }
  return null;
}
export const monthKey = ({ y, m }) => `${y}-${pad2(m)}`;
export function monthRange({ y, m }) {
  const last = new Date(y, m, 0).getDate();
  return { from: `${y}-${pad2(m)}-01`, to: `${y}-${pad2(m)}-${pad2(last)}` };
}

/** 제목 속 'N월' → 그 글이 다루는 달. 연도는 올린 날짜와 가장 가까운 해. 없으면 올린 달 */
export function noticeMonth(title, createdKey) {
  const [cy, cm] = String(createdKey).split('-').map(Number);
  const t = /(?:^|[^\d])(1[0-2]|0?[1-9])\s*월/.exec(String(title ?? ''));
  if (!t || !cy) return cy ? { y: cy, m: cm, fromTitle: false } : null;
  const mm = Number(t[1]);
  const cands = [cy - 1, cy, cy + 1].map((y) => ({ y, gap: Math.abs((y - cy) * 12 + (mm - cm)) })).sort((a, b) => a.gap - b.gap);
  return { y: cands[0].y, m: mm, fromTitle: true };
}

const norm = (s) => String(s ?? '').replace(/\s+/g, '').toLowerCase();

/**
 * 매달 올라오는 공지 고르기: 제목에 keyword가 든 글 중 그 달(제목의 'N월', 없으면 올린 달) 것.
 * month를 안 주면 가장 최근 달. → {month:{y,m}, items}
 */
export function pickMonthly(notices, keyword, month) {
  const kw = norm(keyword);
  const hits = notices.filter((n) => norm(n.title).includes(kw)).map((n) => ({ n, mon: noticeMonth(n.title, kstDate(n.created)) })).filter((x) => x.mon);
  if (!hits.length) return { month: month ?? null, items: [] };
  const target = month ?? hits.map((x) => x.mon).sort((a, b) => b.y - a.y || b.m - a.m)[0];
  const items = hits.filter((x) => x.mon.y === target.y && x.mon.m === target.m).map((x) => x.n);
  return { month: { y: target.y, m: target.m }, items };
}

// ---------- 글 다듬기 ----------
/** 본문(대개 일반 글, 가끔 HTML) → 글 */
export function plain(s) {
  let t = String(s ?? '');
  if (/<\w+[^>]*>/.test(t)) {
    t = t.replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|div|li|tr|h\d)>/gi, '\n').replace(/<[^>]+>/g, '')
      .replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  }
  return t.replace(/\r\n?/g, '\n').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}
export const excerpt = (s, n = 70) => { const t = plain(s).replace(/\s+/g, ' '); return t.length > n ? `${t.slice(0, n)}…` : t; };
const ext = (name) => (path.extname(String(name ?? '')).slice(1) || '').toLowerCase();
export const fileKinds = (files) => [...new Set((files ?? []).map((f) => ext(f.original_file_name)).filter(Boolean))].join('·');

// ---------- 내려받기 ----------
export const safeName = (s) => String(s ?? '').replace(/[\\/:*?"<>|\x00-\x1f]/g, '_').replace(/\s+/g, ' ').replace(/[. ]+$/, '').trim().slice(0, 80) || 'download';

/** save_dir → <save_dir>/내려받은 자료/키즈노트/<묶음 이름> */
export function targetDir(saveDir, group) {
  let dir = String(saveDir ?? '').trim();
  if (!dir || !path.isAbsolute(dir)) throw new Error('save_dir는 절대 경로로 주세요(망무물 세션 정보의 출력 경로).');
  if (path.basename(dir) !== DOWNLOAD_FOLDER) dir = path.join(dir, DOWNLOAD_FOLDER);
  return path.join(dir, SUB_FOLDER, safeName(group));
}

function sameFile(p, buf) {
  try { return fs.statSync(p).size === buf.length && fs.readFileSync(p).equals(buf); } catch { return false; }
}

/** url을 dir/name으로 저장 → {path, size, name, existed?}. 같은 이름 · 같은 내용이면 다시 쓰지 않는다 */
export async function download(url, dir, name) {
  if (!url) throw new Error(`${name}: 받을 주소가 없습니다.`);
  const fname = safeName(name);
  const exist = path.join(dir, fname);
  const r = await fetchT(url, { headers: { 'User-Agent': UA } }, 120000);
  if (!r.ok) throw new Error(`${name}: 받지 못했습니다(HTTP ${r.status}).`);
  const buf = Buffer.from(await r.arrayBuffer());
  if (!buf.length) throw new Error(`${name}: 빈 파일이 왔습니다.`);
  fs.mkdirSync(dir, { recursive: true });
  let target = exist;
  const e = path.extname(fname);
  for (let n = 2; fs.existsSync(target); n++) {
    if (sameFile(target, buf)) return { path: target, size: buf.length, name: path.basename(target), existed: true };
    target = path.join(dir, `${path.basename(fname, e)} (${n})${e}`);
  }
  fs.writeFileSync(target, buf);
  return { path: target, size: buf.length, name: path.basename(target) };
}

/** 사진 파일 이름: 01_원래이름.jpg (확장자 없으면 .jpg) */
export function photoName(img, i) {
  const base = safeName(img?.original_file_name || `photo${i + 1}.jpg`);
  return `${pad2(i + 1)}_${/\.(jpe?g|png|gif|webp|heic|bmp)$/i.test(base) ? base : `${base}.jpg`}`;
}
/** 화면에 보일 사진 주소: 큰 사진(줄인 것) → 큰 사진 → 원본 */
export const photoUrl = (img) => img?.large_resize || img?.large || img?.original || '';
