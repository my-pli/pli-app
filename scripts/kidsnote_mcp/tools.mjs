// 키즈노트 MCP 도구 정의와 실행(읽기 전용: 좋아요 · 댓글 · 글쓰기는 하지 않는다)
import {
  WEB, DOWNLOAD_FOLDER, api, collect, dayLabel, download, ensureSession, excerpt, fileKinds, kstDate, loginWith,
  monthKey, monthRange, parseMonth, photoName, photoUrl, pickMonthly, plain, safeName, targetDir, todayKst,
} from './site.mjs';

const SITE = `${WEB}/service/`;
const src = (p = '') => `\n\n출처: 키즈노트 ${WEB}/service/${p}`;
const clampN = (v, d, max) => Math.max(1, Math.min(Number(v) || d, max));
const kb = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)}MB` : `${Math.max(1, Math.round(b / 1024))}KB`);
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function dateArg(v, label) {
  if (v === undefined || v === null || v === '') return null;
  const s = String(v).trim();
  if (!DATE_RE.test(s)) throw new Error(`${label}는 YYYY-MM-DD로 주세요(예: 2026-11-10).`);
  return s;
}
/** from · to · month 인자 → {from, to} (없으면 null) */
function rangeArgs(a) {
  if (a.month) {
    const m = parseMonth(a.month);
    if (!m) throw new Error('month는 2026-11 · 11월 · 이번 달 · 지난달처럼 주세요.');
    return monthRange(m);
  }
  const from = dateArg(a.from, 'from');
  const to = dateArg(a.to, 'to');
  return from || to ? { from: from ?? '0000-01-01', to: to ?? '9999-12-31' } : null;
}
const inRange = (key, r) => !r || (key >= r.from && key <= r.to);

/** 아이 고르기: child(이름 일부)가 있으면 그 아이, 없으면 모두 */
function pickChildren(ctx, child) {
  const want = String(child ?? '').trim();
  const list = want ? ctx.children.filter((c) => c.name?.includes(want)) : ctx.children;
  if (!list.length) throw new Error(want ? `"${want}" 아이를 찾지 못했습니다. 아이: ${ctx.children.map((c) => c.name).join(', ') || '(없음)'}` : '이 계정에 등록된 아이가 없습니다.');
  return list;
}
/**
 * 볼 곳(어린이집 · 학원 등) 고르기: 키즈노트 웹의 원 선택 목록과 같다. 등록된 곳이 하나면 그곳,
 * 여러 곳인데 center를 안 주면 사용자에게 물으라고 답한다(사용자 결정). → 고른 곳만 남긴 아이 목록
 */
export function pickScope(ctx, a) {
  const children = pickChildren(ctx, a.child);
  const all = centersOf(children);
  const want = String(a.center ?? '').replace(/\s+/g, '');
  let chosen = all;
  if (want) {
    chosen = all.filter((c) => String(c.name ?? '').replace(/\s+/g, '').includes(want));
    if (!chosen.length) throw new Error(`"${a.center}"에 해당하는 곳이 없습니다. 등록된 곳: ${all.map((c) => c.name).join(', ')}`);
  } else if (all.length > 1) {
    throw new Error(`이 계정에는 키즈노트를 쓰는 곳이 ${all.length}곳 있습니다: ${all.map((c) => c.name).join(', ')}. `
      + '어느 곳의 정보를 볼지 사용자에게 물어본 뒤(질문 카드로 선택지를 보여 줌) center에 그 이름을 넣어 다시 부르세요.');
  }
  const ids = new Set(chosen.map((c) => c.id));
  return children.map((c) => ({ ...c, centers: c.centers.filter((x) => ids.has(x.id)) })).filter((c) => c.centers.length);
}
const scopeCenterIds = (children) => new Set(centersOf(children).map((c) => c.id));

/** 고른 아이들의 원 · 반 목록 → [{center, cls}] (중복 없이) */
function classTargets(children) {
  const out = [];
  for (const c of children) for (const cen of c.centers) for (const cls of cen.classes) {
    if (!out.some((x) => x.center.id === cen.id && x.cls.id === cls.id)) out.push({ center: cen, cls });
  }
  return out;
}
const centersOf = (children) => [...new Map(children.flatMap((c) => c.centers).map((x) => [x.id, x])).values()];
const className = (ctx, clsId) => {
  for (const c of ctx.children) for (const cen of c.centers) for (const cls of cen.classes) if (cls.id === clsId) return cls.name;
  return '';
};

// ---------- 공지사항 ----------
/** 고른 아이들의 반마다 공지를 불러 합친다(원 전체 공지는 반마다 겹쳐 오므로 id로 하나만). 최신순 */
async function fetchNotices(ctx, children, { title, range, max = 60 } = {}) {
  const lists = await Promise.all(classTargets(children).map(({ center, cls }) => collect(`/v1/centers/${center.id}/notices`, {
    cls: cls.id, page_size: 50, ...(title ? { title } : {}),
  }, { max, pages: range ? 20 : 4, stop: range ? (n) => kstDate(n.created) < range.from : undefined })));
  const seen = new Map();
  for (const n of lists.flat()) if (!seen.has(n.id)) seen.set(n.id, n);
  const sorted = [...seen.values()].filter((n) => inRange(kstDate(n.created), range)).sort((a, b) => String(b.created).localeCompare(String(a.created)));
  return mergeSame(ctx, sorted);
}
/** 같은 글을 반마다 따로 올린 것(번호만 다르고 제목 · 날짜 · 첨부가 같음)은 하나로 합치고 올라온 반을 모아 둔다 */
export function mergeSame(ctx, list) {
  const key = (n) => `${n.title}\n${kstDate(n.created)}\n${(n.attached_files ?? []).map((f) => `${f.original_file_name}:${f.file_size}`).join('|')}\n${n.attached_images?.length ?? 0}`;
  const byKey = new Map();
  const out = [];
  for (const n of list) {
    const k = key(n);
    const first = byKey.get(k);
    if (!first) { const copy = { ...n, _where: [noticeWhere(ctx, n)] }; byKey.set(k, copy); out.push(copy); continue; }
    const w = noticeWhere(ctx, n);
    if (!first._where.includes(w)) first._where.push(w);
  }
  return out;
}
function noticeWhere(ctx, n) {
  if (!n.cls) return '원 전체';
  const id = typeof n.cls === 'object' ? n.cls.id : n.cls;
  return (typeof n.cls === 'object' && n.cls.name) || className(ctx, id) || '반 공지';
}
const noticeLine = (ctx) => (n, i) => {
  const files = n.attached_files?.length ? ` · 첨부 ${n.attached_files.length}(${fileKinds(n.attached_files)})` : '';
  const imgs = n.attached_images?.length ? ` · 사진 ${n.attached_images.length}` : '';
  return `${i + 1}. ${kstDate(n.created)} · ${n.title} · ${(n._where ?? [noticeWhere(ctx, n)]).join(' · ')}${files}${imgs} · 공지 ${n.id}`;
};

/** 글 하나의 첨부 파일 · 사진을 받는다 → 결과 글 줄들 */
/** 글의 동영상 목록(앨범은 attached_videos, 알림장 · 공지는 attached_video 하나) */
export const videosOf = (x) => [...(x?.attached_videos ?? []), ...(x?.attached_video ? [x.attached_video] : [])].filter((v) => v && (v.high || v.low));
/** 동영상 파일 이름: 영상01_원래이름.mp4 */
export function videoName(v, i) {
  const base = safeName(v?.original_file_name || `video${i + 1}.mp4`);
  return `영상${String(i + 1).padStart(2, '0')}_${/\.(mp4|m4v|mov|webm)$/i.test(base) ? base : `${base}.mp4`}`;
}

async function saveAttachments({ saveDir, group, files = [], images = [], videos = [], quality = 'high', maxPhotos = 12, offset = 0 }) {
  const dir = targetDir(saveDir, group);
  const saved = [];
  const failed = [];
  for (const f of files) {
    try { saved.push({ kind: 'file', ...(await download(f.original, dir, f.original_file_name || `file-${f.id}`)) }); } catch (e) { failed.push(e.message); }
  }
  // 동영상(mp4)은 크니 하나씩, 사진을 이어 받을 때(offset)는 다시 받지 않는다
  if (!offset) {
    for (const [i, v] of videos.entries()) {
      const url = quality === 'low' ? v.low || v.high : v.high || v.low;
      try { saved.push({ kind: 'video', order: i, duration: v.duration, ...(await download(url, dir, videoName(v, i))) }); } catch (e) { failed.push(e.message); }
    }
  }
  const pick = images.slice(offset, offset + maxPhotos);
  await Promise.all(pick.map(async (img, i) => {
    try { saved.push({ kind: 'photo', order: i, ...(await download(photoUrl(img), dir, photoName(img, offset + i))) }); } catch (e) { failed.push(e.message); }
  }));
  const rank = { file: 0, video: 1, photo: 2 };
  saved.sort((a, b) => (a.kind === b.kind ? (a.order ?? 0) - (b.order ?? 0) : rank[a.kind] - rank[b.kind]));
  const out = [];
  const photos = saved.filter((s) => s.kind === 'photo');
  const docs = saved.filter((s) => s.kind === 'file');
  const vids = saved.filter((s) => s.kind === 'video');
  if (saved.length) out.push(`받은 곳: ${dir}`);
  if (docs.length) out.push(`첨부 파일 ${docs.length}개: ${docs.map((s) => `${s.name}(${kb(s.size)})`).join(', ')}`);
  if (vids.length) out.push(`동영상 ${vids.length}개: ${vids.map((s) => `${s.name}(${kb(s.size)}${s.duration ? `, ${Math.round(s.duration)}초` : ''})`).join(', ')} · 대화창에서 누르면 재생된다`);
  if (photos.length) {
    const left = images.length - offset - pick.length;
    out.push(`사진 ${photos.length}장 (전체 ${images.length}장${left > 0 ? `, 남은 ${left}장은 offset ${offset + pick.length}로 이어서 받기` : ''})`);
  }
  if (failed.length) out.push('받지 못한 것:', ...failed.map((m) => `- ${m}`));
  if (saved.length) {
    out.push('', '답변에 아래 줄을 그대로 넣으면(한 줄에 하나, 다른 글자 없이) 대화창에 파일 카드 · 사진 · 동영상(누르면 재생)으로 보인다. 사진은 보여 줄 것만 골라 넣어도 된다:',
      ...saved.map((s) => `<<file:${s.path}>>`));
    if (docs.length) out.push('', '첨부 파일 내용: npx -y kordoc@4.24.29 "<경로>" 로 읽는다(hwp · hwpx · pdf · docx · xlsx; pptx는 읽지 못할 수 있음). 받은 파일은 원본이므로 고치지 않는다.');
  }
  return out;
}

async function noticeText(ctx, n, a) {
  const out = [`■ ${n.title} (공지 ${n.id})`, `${kstDate(n.created)} · ${(n._where ?? [noticeWhere(ctx, n)]).join(' · ')} · ${n.author_name || '-'}`, '', plain(n.content) || '(본문 없음)'];
  const files = n.attached_files ?? [];
  const images = n.attached_images ?? [];
  const videos = videosOf(n);
  if (!files.length && !images.length && !videos.length) { out.push('', '첨부 없음'); return out; }
  if (a.save_dir) {
    out.push('', ...(await saveAttachments({ saveDir: a.save_dir, group: `${kstDate(n.created)} 공지 ${n.title}`, files, images, videos, quality: a.video_quality, maxPhotos: clampN(a.max_photos, 12, 60), offset: Math.max(0, Number(a.offset) || 0) })));
  } else {
    out.push('', `첨부 파일 ${files.length}개${files.length ? `: ${files.map((f) => f.original_file_name).join(', ')}` : ''} · 사진 ${images.length}장${videos.length ? ` · 동영상 ${videos.length}개` : ''}`, '내용을 읽거나 사진 · 동영상을 보이려면 save_dir(세션 출력 경로)를 주고 다시 부른다.');
  }
  return out;
}

// ---------- 알림장 · 앨범 ----------
async function fetchByChild(children, pathOf, { range, max, dateOf }) {
  const lists = await Promise.all(children.map((c) => collect(pathOf(c), { page_size: 30 }, {
    max, pages: range ? 20 : 3, stop: range ? (x) => dateOf(x) < range.from : undefined,
  }).then((xs) => xs.map((x) => ({ ...x, _child: c.name })))));
  const ids = scopeCenterIds(children);
  return lists.flat().filter((x) => (x.center == null || ids.has(x.center)) && inRange(dateOf(x), range)).sort((a, b) => dateOf(b).localeCompare(dateOf(a)) || String(b.created).localeCompare(String(a.created)));
}
const reportDate = (r) => r.date_written || kstDate(r.created);
const albumDate = (x) => kstDate(x.created);
const multi = (children) => children.length > 1;

// ---------- 식단 ----------
const MEALS = [['morning', '아침'], ['morning_snack', '오전 간식'], ['lunch', '점심'], ['afternoon_snack', '오후 간식'], ['dinner', '저녁']];

// ---------- 도구 ----------
const CHILD = { type: 'string', description: '아이 이름(여러 아이일 때만, 일부만 써도 됨). 없으면 모든 아이' };
const CENTER = { type: 'string', description: '볼 곳 이름(어린이집 · 학원 등, 일부만 써도 됨). 등록된 곳이 여러 곳이면 사용자에게 물어본 뒤 넣는다' };
const SAVE_DIR = { type: 'string', description: `저장할 폴더(절대 경로, 망무물 세션 정보의 출력 경로). 주면 첨부 파일 · 사진을 그 아래 "${DOWNLOAD_FOLDER}/키즈노트" 폴더에 받는다` };
const MONTH = { type: 'string', description: '달(2026-11 · 11월 · 이번 달 · 지난달)' };
const FROM = { type: 'string', description: '시작 날짜 YYYY-MM-DD' };
const TO = { type: 'string', description: '끝 날짜 YYYY-MM-DD' };
const MAX_PHOTOS = { type: 'number', description: '받을 사진 수(기본 12, 최대 60)' };
const OFFSET = { type: 'number', description: '사진을 몇 번째부터 받을지(기본 0). 이어서 더 받을 때(동영상은 다시 받지 않음)' };
const VIDEO_Q = { type: 'string', description: '동영상 화질: high(기본, 원본에 가까움) · low(작은 파일)' };

export const TOOLS = [
  { name: 'login', description: '키즈노트 로그인. 다른 도구가 "로그인하지 못했습니다"라고 하면 사용자에게 키즈노트 아이디 · 비밀번호를 물은 뒤 이 도구로 로그인한다. 성공하면 key.txt에 저장해 다음부터 묻지 않는다. 비밀번호는 답변에 다시 적지 않는다.',
    inputSchema: { type: 'object', properties: { id: { type: 'string', description: '키즈노트 아이디' }, pw: { type: 'string', description: '키즈노트 비밀번호' } }, required: ['id', 'pw'] } },
  { name: 'get_info', description: '로그인한 계정의 아이 · 어린이집(유치원) · 반 정보. 무엇을 볼 수 있는지 처음에 확인할 때.',
    inputSchema: { type: 'object', properties: {} } },
  { name: 'search_notices', description: '공지사항 목록과 제목 검색(아이의 모든 반 공지 + 원 전체 공지를 합쳐 최신순). 결과의 "공지 N" 번호로 get_notice. 매달 올라오는 글(놀이계획안 · 특별활동 등)은 get_monthly_notice가 더 편하다.',
    inputSchema: { type: 'object', properties: { keyword: { type: 'string', description: '제목에 든 말(없으면 최근 공지)' }, month: MONTH, from: FROM, to: TO, in_content: { type: 'boolean', description: 'true면 제목뿐 아니라 본문에서도 keyword를 찾는다(최근 글 위주로 느림)' }, limit: { type: 'number', description: '보일 건수(기본 15, 최대 50)' }, child: CHILD, center: CENTER } } },
  { name: 'get_notice', description: '공지 하나의 본문 · 첨부 파일 · 사진. save_dir를 주면 첨부 파일과 사진을 받아 <<file:>> 줄을 준다(사진은 답변 창에 사진으로 보인다, 첨부는 kordoc으로 읽는다).',
    inputSchema: { type: 'object', properties: { notice_id: { type: 'string', description: '공지 번호(search_notices의 "공지 N")' }, save_dir: SAVE_DIR, max_photos: MAX_PHOTOS, offset: OFFSET, video_quality: VIDEO_Q }, required: ['notice_id'] } },
  { name: 'get_monthly_notice', description: '매달 올라오는 공지(예: 놀이계획안, 특별활동, 식단표, 가정통신문)를 달로 찾아 본문 · 첨부까지 한 번에. 제목의 "N월"로 그 달을 판단(없으면 올린 달), month를 안 주면 가장 최근 것. 반마다 따로 올라오면(예: 담임반 · 연장반) 모두 준다.',
    inputSchema: { type: 'object', properties: { keyword: { type: 'string', description: '제목에 든 말(예: 놀이계획안, 특별활동)' }, month: MONTH, save_dir: SAVE_DIR, child: CHILD, center: CENTER }, required: ['keyword'] } },
  { name: 'list_reports', description: '알림장 목록(날짜 · 반 · 선생님 · 내용 앞부분 · 사진 수). 날짜 범위를 안 주면 최근 10개. 결과의 "알림장 N"으로 get_report.',
    inputSchema: { type: 'object', properties: { month: MONTH, from: FROM, to: TO, keyword: { type: 'string', description: '내용에 든 말로 거르기' }, limit: { type: 'number', description: '보일 건수(기본 10, 최대 60)' }, child: CHILD, center: CENTER } } },
  { name: 'get_report', description: '알림장 하나의 전체 내용(날씨 · 활동 · 선생님 글)과 사진. save_dir를 주면 사진을 받아 <<file:>> 줄을 준다.',
    inputSchema: { type: 'object', properties: { report_id: { type: 'string', description: '알림장 번호' }, save_dir: SAVE_DIR, max_photos: MAX_PHOTOS, offset: OFFSET, video_quality: VIDEO_Q }, required: ['report_id'] } },
  { name: 'list_albums', description: '앨범 목록(날짜 · 제목 · 사진 · 동영상 수). 날짜 범위를 안 주면 최근 10개. 결과의 "앨범 N"으로 get_album.',
    inputSchema: { type: 'object', properties: { month: MONTH, from: FROM, to: TO, keyword: { type: 'string', description: '제목 · 내용에 든 말로 거르기' }, limit: { type: 'number', description: '보일 건수(기본 10, 최대 60)' }, child: CHILD, center: CENTER } } },
  { name: 'get_album', description: '앨범 하나의 글 · 사진 · 동영상. save_dir를 주면 사진(기본 12장, offset으로 이어 받기)과 동영상(mp4, 대화창에서 누르면 재생)을 받아 <<file:>> 줄을 준다.',
    inputSchema: { type: 'object', properties: { album_id: { type: 'string', description: '앨범 번호' }, save_dir: SAVE_DIR, max_photos: MAX_PHOTOS, offset: OFFSET, video_quality: VIDEO_Q }, required: ['album_id'] } },
  { name: 'get_calendar', description: '일정표(행사 · 일정). 달(기본 이번 달) 또는 날짜 범위로. 아이의 모든 반 일정 + 원 전체 일정.',
    inputSchema: { type: 'object', properties: { month: MONTH, from: FROM, to: TO, child: CHILD, center: CENTER } } },
  { name: 'get_menu', description: '식단표(아침 · 오전 간식 · 점심 · 오후 간식 · 저녁). date 하나, 날짜 범위, 달 중 하나로(기본 오늘). save_dir를 주면 식단 사진도 함께 받아 <<file:>> 줄을 준다(사진이 있으면 늘 함께 보여 준다; 7일이 넘는 기간은 photos=true일 때만).',
    inputSchema: { type: 'object', properties: { date: { type: 'string', description: '날짜 YYYY-MM-DD' }, month: MONTH, from: FROM, to: TO, photos: { type: 'boolean', description: 'false면 사진을 받지 않는다. 7일이 넘는 기간에서 사진까지 받으려면 true' }, save_dir: SAVE_DIR, child: CHILD, center: CENTER } } },
  { name: 'get_notifications', description: '키즈노트 알림 목록(앱 알림과 같은 것: 새 공지 · 앨범 · 알림장 · 댓글 등) 최신순.',
    inputSchema: { type: 'object', properties: { limit: { type: 'number', description: '보일 건수(기본 15, 최대 50)' } } } },
];

const H = {
  async login(a) {
    const { ctx } = await loginWith(a.id, a.pw);
    return ['키즈노트에 로그인했습니다. 아이디 · 비밀번호를 저장해 두었으니 다음부터는 묻지 않습니다.', '', infoText(ctx)].join('\n') + src();
  },

  async get_info() {
    return infoText(await ensureSession()) + src();
  },

  async search_notices(a) {
    const ctx = await ensureSession();
    const children = pickScope(ctx, a);
    const limit = clampN(a.limit, 15, 50);
    const range = rangeArgs(a);
    const kw = String(a.keyword ?? '').trim();
    let list;
    if (kw && a.in_content) {
      const all = await fetchNotices(ctx, children, { range, max: range ? 300 : 150 });
      const k = kw.replace(/\s+/g, '').toLowerCase();
      list = all.filter((n) => `${n.title}\n${plain(n.content)}`.replace(/\s+/g, '').toLowerCase().includes(k));
    } else {
      list = await fetchNotices(ctx, children, { title: kw || undefined, range, max: range ? 300 : Math.max(limit, 20) });
    }
    if (!list.length) return `${kw ? `"${kw}"` : ''} 공지가 없습니다${range ? ` (${range.from} ~ ${range.to})` : ''}.${kw && !a.in_content ? ' 본문까지 찾으려면 in_content=true.' : ''}${src('notice')}`;
    const head = `공지사항${kw ? ` "${kw}"` : ''}${range ? ` ${range.from} ~ ${range.to}` : ''} ${list.length}건${list.length > limit ? ` 중 ${limit}건` : ''}`;
    return [head, ...list.slice(0, limit).map(noticeLine(ctx))].join('\n') + src('notice');
  },

  async get_notice(a) {
    const ctx = await ensureSession();
    const id = String(a.notice_id ?? '').replace(/\D/g, '');
    if (!id) throw new Error('notice_id(공지 번호)를 주세요.');
    const n = await api(`/v1_2/notices/${id}`);
    return (await noticeText(ctx, n, a)).join('\n') + src('notice');
  },

  async get_monthly_notice(a) {
    const ctx = await ensureSession();
    const children = pickScope(ctx, a);
    const kw = String(a.keyword ?? '').trim();
    if (!kw) throw new Error('keyword(예: 놀이계획안)를 주세요.');
    let month = null;
    if (a.month) {
      month = parseMonth(a.month);
      if (!month) throw new Error('month는 2026-11 · 11월 · 이번 달 · 지난달처럼 주세요.');
    }
    const list = await fetchNotices(ctx, children, { title: kw, max: 120 });
    const { month: got, items } = pickMonthly(list, kw, month);
    if (!items.length) {
      const recent = list.slice(0, 5).map(noticeLine(ctx));
      return [`${month ? `${month.y}년 ${month.m}월 ` : ''}"${kw}" 공지를 찾지 못했습니다.`, ...(recent.length ? ['최근에 올라온 비슷한 글:', ...recent] : [])].join('\n') + src('notice');
    }
    const out = [`${got.y}년 ${got.m}월 "${kw}" 공지 ${items.length}건${month ? '' : ' (가장 최근 달)'}`];
    for (const n of items) {
      const full = await api(`/v1_2/notices/${n.id}`);
      out.push('', ...(await noticeText(ctx, { ...full, _where: n._where }, a)));
    }
    return out.join('\n') + src('notice');
  },

  async list_reports(a) {
    const ctx = await ensureSession();
    const children = pickScope(ctx, a);
    const limit = clampN(a.limit, 10, 60);
    const range = rangeArgs(a);
    let list = await fetchByChild(children, (c) => `/v1_2/children/${c.id}/reports/`, { range, max: range ? 200 : limit, dateOf: reportDate });
    const kw = String(a.keyword ?? '').replace(/\s+/g, '');
    if (kw) list = list.filter((r) => plain(r.content).replace(/\s+/g, '').includes(kw));
    if (!list.length) return `알림장이 없습니다${range ? ` (${range.from} ~ ${range.to})` : ''}.${src('report')}`;
    const lines = list.slice(0, limit).map((r, i) => `${i + 1}. ${dayLabel(reportDate(r))}${multi(children) ? ` · ${r._child}` : ''} · ${r.class_name || '-'} · ${r.author_name || '-'}${r.is_sent_from_center ? '' : ' (부모 작성)'} · ${excerpt(r.content)}${r.attached_images?.length ? ` · 사진 ${r.attached_images.length}` : ''} · 알림장 ${r.id}`);
    return [`알림장 ${list.length}건${list.length > limit ? ` 중 ${limit}건` : ''}`, ...lines].join('\n') + src('report');
  },

  async get_report(a) {
    await ensureSession();
    const id = String(a.report_id ?? '').replace(/\D/g, '');
    if (!id) throw new Error('report_id(알림장 번호)를 주세요.');
    const r = await api(`/v1_2/reports/${id}/`);
    const out = [`■ 알림장 ${dayLabel(reportDate(r))} (알림장 ${r.id})`, `${r.child_name || ''} · ${r.class_name || '-'} · ${r.author_name || '-'}${r.weather ? ` · 날씨 ${r.weather}` : ''}`, '', plain(r.content) || '(내용 없음)'];
    const images = r.attached_images ?? [];
    const files = r.attached_files ?? [];
    const videos = videosOf(r);
    if (a.save_dir && (images.length || files.length || videos.length)) {
      out.push('', ...(await saveAttachments({ saveDir: a.save_dir, group: `${reportDate(r)} 알림장`, files, images, videos, quality: a.video_quality, maxPhotos: clampN(a.max_photos, 12, 60), offset: Math.max(0, Number(a.offset) || 0) })));
    } else if (images.length || files.length || videos.length) {
      out.push('', `사진 ${images.length}장 · 첨부 ${files.length}개${videos.length ? ` · 동영상 ${videos.length}개` : ''}. 사진 · 동영상을 보이려면 save_dir(세션 출력 경로)를 주고 다시 부른다.`);
    }
    return out.join('\n') + src('report');
  },

  async list_albums(a) {
    const ctx = await ensureSession();
    const children = pickScope(ctx, a);
    const limit = clampN(a.limit, 10, 60);
    const range = rangeArgs(a);
    let list = await fetchByChild(children, (c) => `/v1_3/children/${c.id}/albums/`, { range, max: range ? 200 : limit, dateOf: albumDate });
    const kw = String(a.keyword ?? '').replace(/\s+/g, '');
    if (kw) list = list.filter((x) => `${x.title}${plain(x.content)}`.replace(/\s+/g, '').includes(kw));
    // 형제가 같은 반이면 같은 앨범이 두 번 온다
    list = list.filter((x, i) => list.findIndex((y) => y.id === x.id) === i);
    if (!list.length) return `앨범이 없습니다${range ? ` (${range.from} ~ ${range.to})` : ''}.${src('album')}`;
    const lines = list.slice(0, limit).map((x, i) => `${i + 1}. ${dayLabel(albumDate(x))} · ${x.title || excerpt(x.content, 30) || '(제목 없음)'} · 사진 ${x.attached_images?.length ?? 0}${x.attached_videos?.length ? ` · 동영상 ${x.attached_videos.length}` : ''} · ${x.author_name || '-'} · 앨범 ${x.id}`);
    return [`앨범 ${list.length}건${list.length > limit ? ` 중 ${limit}건` : ''}`, ...lines].join('\n') + src('album');
  },

  async get_album(a) {
    await ensureSession();
    const id = String(a.album_id ?? '').replace(/\D/g, '');
    if (!id) throw new Error('album_id(앨범 번호)를 주세요.');
    const x = await api(`/v1_3/albums/${id}/`);
    const images = x.attached_images ?? [];
    const videos = videosOf(x);
    const out = [`■ ${x.title || '앨범'} (앨범 ${x.id})`, `${dayLabel(albumDate(x))} · ${x.author_name || '-'} · 사진 ${images.length}장${videos.length ? ` · 동영상 ${videos.length}개` : ''}`, '', plain(x.content) || '(글 없음)'];
    if (a.save_dir && (images.length || videos.length)) {
      out.push('', ...(await saveAttachments({ saveDir: a.save_dir, group: `${albumDate(x)} 앨범 ${x.title || x.id}`, images, videos, quality: a.video_quality, maxPhotos: clampN(a.max_photos, 12, 60), offset: Math.max(0, Number(a.offset) || 0) })));
    } else if (images.length || videos.length) {
      out.push('', '사진 · 동영상을 보이려면 save_dir(세션 출력 경로)를 주고 다시 부른다.');
    }
    return out.join('\n') + src('album');
  },

  async get_calendar(a) {
    const ctx = await ensureSession();
    const children = pickScope(ctx, a);
    const range = rangeArgs(a) ?? monthRange(parseMonth('이번 달'));
    const lists = await Promise.all(classTargets(children).map(({ center, cls }) => collect(`/v1/centers/${center.id}/calendar`, { cls: cls.id, page_size: 100 }, { max: 1000, pages: 10 })));
    const seen = new Map();
    for (const e of lists.flat()) if (!seen.has(e.id)) seen.set(e.id, e);
    const list = [...seen.values()].filter((e) => inRange(String(e.date_event).slice(0, 10), range)).sort((x, y) => String(x.date_event).localeCompare(String(y.date_event)));
    if (!list.length) return `일정이 없습니다 (${range.from} ~ ${range.to}).${src('schedule')}`;
    const lines = list.map((e) => `- ${dayLabel(String(e.date_event).slice(0, 10))} · ${e.title}${e.is_center_event ? ' · 원 전체' : e.class_name ? ` · ${e.class_name}` : ''}${e.content ? ` · ${excerpt(e.content, 60)}` : ''}${e.address_summary ? ` · 장소 ${e.address_summary}` : ''}`);
    return [`일정표 ${range.from} ~ ${range.to} (${list.length}건)`, ...lines].join('\n') + src('schedule');
  },

  async get_menu(a) {
    const ctx = await ensureSession();
    const children = pickScope(ctx, a);
    const date = dateArg(a.date, 'date');
    const range = date ? { from: date, to: date } : rangeArgs(a) ?? { from: todayKst(), to: todayKst() };
    const out = [];
    for (const cen of centersOf(children)) {
      const list = date
        ? (await api(`/v1/centers/${cen.id}/menu`, { date_menu: date, page_size: 5 })).results ?? []
        : await collect(`/v1/centers/${cen.id}/menu`, { page_size: 31 }, { max: 400, pages: 15, stop: (m) => m.date_menu < range.from });
      const days = list.filter((m) => inRange(m.date_menu, range)).sort((x, y) => x.date_menu.localeCompare(y.date_menu));
      out.push(`식단표 · ${cen.name} · ${range.from === range.to ? dayLabel(range.from) : `${range.from} ~ ${range.to}`}`);
      if (!days.length) { out.push('등록된 식단이 없습니다.'); continue; }
      const photoJobs = [];
      for (const d of days) {
        out.push('', `■ ${dayLabel(d.date_menu)}`);
        for (const [k, label] of MEALS) {
          const text = plain(d[k]).replace(/\n+/g, ', ');
          if (text) out.push(`- ${label}: ${text}`);
          if (d[`${k}_img`]) photoJobs.push({ img: d[`${k}_img`], name: `${d.date_menu} ${label}` });
        }
      }
      // 사진: save_dir가 있으면 기본으로 받는다(7일이 넘는 기간은 너무 많아 photos=true일 때만). photos=false면 받지 않는다
      const days7 = (Date.parse(range.to) - Date.parse(range.from)) / 86400000 < 7;
      const wantPhotos = a.photos === true || (a.photos !== false && days7 && !!a.save_dir);
      if (wantPhotos && photoJobs.length) {
        if (!a.save_dir) out.push('', '식단 사진을 받으려면 save_dir(세션 출력 경로)도 준다.');
        else {
          const group = range.from === range.to ? `${range.from} 식단` : `${range.from}~${range.to} 식단`;
          const imgs = photoJobs.map((j) => ({ ...j.img, original_file_name: `${safeName(j.name)}.jpg` }));
          const lines = await saveAttachments({ saveDir: a.save_dir, group, images: imgs, maxPhotos: 60 });
          out.push('', ...lines);
        }
      } else if (photoJobs.length) {
        out.push('', `식단 사진 ${photoJobs.length}장 있음(save_dir를 주면 받아서 보여 줄 수 있음${days7 ? '' : ', 7일이 넘는 기간은 photos=true도'}).`);
      }
    }
    return out.join('\n') + src('meal');
  },

  async get_notifications(a) {
    await ensureSession();
    const limit = clampN(a.limit, 15, 50);
    const list = await collect('/v1/me/notifications/', { page_size: Math.min(limit, 50) }, { max: limit, pages: 2 });
    if (!list.length) return `알림이 없습니다.${src()}`;
    return [`알림 ${list.length}건(최신순)`, ...list.map((n, i) => `${i + 1}. ${kstDate(n.created)} · ${n.title || n.code}${n.summary ? ` · ${excerpt(n.summary, 60)}` : ''}${n.author_name ? ` · ${n.author_name}` : ''}`)].join('\n') + src();
  },
};

function infoText(ctx) {
  const lines = [`계정: ${ctx.user || '-'}`];
  for (const c of ctx.children) {
    lines.push(`아이: ${c.name}${c.birth ? ` (${c.birth})` : ''}`);
    for (const cen of c.centers) lines.push(`- ${cen.name}: ${cen.classes.map((x) => x.name).join(' · ') || '(반 정보 없음)'}`);
  }
  const places = centersOf(ctx.children);
  if (places.length > 1) lines.push('', `키즈노트를 쓰는 곳이 ${places.length}곳입니다. 다른 도구를 부를 때 어느 곳인지 사용자에게 물어 center에 넣는다.`);
  lines.push('', '볼 수 있는 것: 공지사항(search_notices · get_notice · get_monthly_notice) · 알림장(list_reports · get_report) · 앨범(list_albums · get_album) · 일정표(get_calendar) · 식단표(get_menu) · 알림(get_notifications)');
  return lines.join('\n');
}

export async function callTool(name, args) {
  const h = H[name];
  if (!h) throw new Error(`없는 도구입니다: ${name}`);
  return h(args ?? {});
}

export { SITE };
