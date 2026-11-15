#!/usr/bin/env python3
"""Owner-only KidsNote session. Password is accepted on stdin and never persisted.
The browser state is private, outside exported source and public route whitelists.
"""
from pathlib import Path
import json,os,re,sys,termios,hashlib
from datetime import date,datetime,timedelta,timezone
from html import unescape
from urllib.parse import urlsplit,parse_qs,urlencode,urlunsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'.tools/private/kidsnote'
PRIVATE.mkdir(parents=True,exist_ok=True);PRIVATE.chmod(0o700)
STATE=PRIVATE/'browser.json'
if '--login' in sys.argv:
 if Path('/tmp/.X11-unix/X1').exists():os.environ.setdefault('DISPLAY',':1')
 authority=Path(f'/run/user/{os.getuid()}/gdm/Xauthority')
 if authority.exists():os.environ.setdefault('XAUTHORITY',str(authority))
if sys.stdin.isatty():
 attrs=termios.tcgetattr(sys.stdin);attrs[3]&=~termios.ECHO;termios.tcsetattr(sys.stdin,termios.TCSANOW,attrs)
menus={'알림장','공지사항','일정표','캘린더','Calendar','Notices','Notice','Reports','앨범','식단표','홈'}
responses=[]
def schema(x):
 if isinstance(x,dict):return {k:schema(v) if isinstance(v,(dict,list)) else type(v).__name__ for k,v in list(x.items())[:35]}
 if isinstance(x,list):return {'count':len(x),'item':schema(x[0]) if x else None}
 return type(x).__name__
def emit(x):print(json.dumps(x,ensure_ascii=False),flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless='--login' not in sys.argv,channel='chrome')
 context=browser.new_context(locale='ko-KR',storage_state=str(STATE) if STATE.exists() else None)
 page=context.new_page()
 if '--login' in sys.argv:
  page.goto('https://www.kidsnote.com/en/login',wait_until='domcontentloaded');print('열린 브라우저에서 키즈노트에 로그인해 주세요.',flush=True);page.wait_for_url(lambda u:'/service' in u.path,timeout=300000);STATE.write_text(json.dumps(context.storage_state()));STATE.chmod(0o600);browser.close();print('연결되었습니다. 가족 연결 화면에서 갱신해 주세요.');raise SystemExit()
 def response(r):
  if r.request.method!='GET' or 'kidsnote.com' not in r.url or 'json' not in r.headers.get('content-type',''):return
  try:
   body=r.json();responses.append({'url':r.url,'status':r.status,'body':body,'headers':r.request.all_headers()});del responses[:-50]
  except Exception:pass
 page.on('response',response)
 emit({'ready':True,'savedSession':STATE.exists()})
 commands=[json.dumps(x) for x in [{'action':'open','path':'/service/schedule'},{'action':'export'},{'action':'quit'}]] if '--sync' in sys.argv else sys.stdin
 for line in commands:
  try:
   cmd=json.loads(line);action=cmd.get('action')
   if action=='login':
    page.goto('https://www.kidsnote.com/en/login',wait_until='domcontentloaded');page.locator('input[name=username]').fill(cmd['username']);page.locator('input[name=password]').fill(cmd['password']);page.locator('button[type=submit]').click();cmd.clear()
    try:page.wait_for_url(lambda u:'/login' not in u.path,timeout=18000)
    except Exception:pass
    page.wait_for_timeout(2000)
    authenticated='/login' not in page.url
    if authenticated:
     temporary=STATE.with_suffix('.tmp');temporary.write_text(json.dumps(context.storage_state()));temporary.chmod(0o600);temporary.replace(STATE)
    emit({'authenticated':authenticated,'path':re.sub(r'/\d+','/:id',page.url.split('.com')[-1]),'loginError':None if authenticated else '로그인 화면에 머물러 있습니다. 추가 인증 또는 계정 정보 확인이 필요합니다.'})
   elif action=='inspect':
    links=page.locator('a').evaluate_all('(xs)=>xs.map(x=>({text:x.innerText.trim(),href:x.getAttribute("href")}))')
    emit({'path':page.url.split('.com')[-1],'menus':[x for x in links if x['text'] in menus],'jsonResponses':[{'path':re.sub(r'/second-factors/[^/]+', '/second-factors/:account',re.sub(r'/\d+', '/:id',x['url'].split('.com')[-1])).split('?')[0],'status':x['status'],'schema':schema(x['body'])} for x in responses]})
   elif action=='open':
    path=cmd['path']
    if not path.startswith('/') or path.startswith('//') or any(x in path.lower() for x in ['logout','delete','write','create']):raise ValueError('Unsupported read path')
    # Read navigation only. No comments, messages, profile changes, or posts.
    responses.clear()
    context.route('**/*',lambda route:route.continue_() if route.request.method in {'GET','HEAD','OPTIONS'} else route.abort())
    page.goto('https://www.kidsnote.com'+path,wait_until='domcontentloaded');page.wait_for_timeout(2000);emit({'opened':True})
   elif action=='export':
    calendar=next((x for x in reversed(responses) if re.search(r'/centers/\d+/calendar',x['url']) and x['status']==200),None)
    if not calendar or '/login' in page.url:
     meta={'connected':False,'error':'다시 로그인해 주세요.'};(PRIVATE/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False));(PRIVATE/'metadata.json').chmod(0o600);emit(meta);continue
    info=next((x['body'] for x in responses if '/me/info/' in x['url']),{})
    rows=calendar['body'];rows=rows if isinstance(rows,list) else rows.get('results',[])
    today=date.today();plans=[]
    parsed=urlsplit(calendar['url']);query=parse_qs(parsed.query);observed=query.get('month_event',[''])[0]
    if not (parsed.hostname=='kidsnote.com' or (parsed.hostname or '').endswith('.kidsnote.com')):raise ValueError('Untrusted calendar origin')
    if re.fullmatch(r'\d{4}-\d{2}',observed):fmt='%Y-%m'
    elif re.fullmatch(r'\d{6}',observed):fmt='%Y%m'
    elif re.fullmatch(r'\d{4}-\d{2}-\d{2}',observed):fmt='%Y-%m-%d'
    else:raise ValueError('Unsupported calendar month')
    rows=[]
    for offset in range(3):
     index=today.year*12+today.month-1+offset;month=date(index//12,index%12+1,1);query['month_event']=[month.strftime(fmt)]
     endpoint=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query,doseq=True),''))
     response=context.request.get(endpoint,headers=calendar['headers'],timeout=15000)
     if response.status!=200:raise ValueError('Calendar request failed')
     data=response.json();rows.extend(data if isinstance(data,list) else data.get('results',[]))

    for row in rows:
     try:day=date.fromisoformat(str(row.get('date_event',''))[:10])
     except ValueError:continue
     if not today<=day<=today+timedelta(days=60):continue
     title=unescape(re.sub('<[^>]+>','',str(row.get('title','')))).strip()[:120]
     if not title:continue
     text=unescape(re.sub('<[^>]+>','\n',str(row.get('content',''))))
     prep=' · '.join(x.strip() for x in text.splitlines() if any(k in x for k in ['준비물','지참','챙겨']))[:300]
     key=hashlib.sha256((str(row.get('id'))+'|'+str(day)).encode()).hexdigest()[:24]
     plans.append({'id':'kidsnote:'+key,'date':str(day),'title':title,'preparation':prep})
    family={'plans':plans}
    children=info.get('children',[])
    if len(children)==1:
     child=children[0];name=str(child.get('name','')).strip()[:30]
     try:
      born=date.fromisoformat(str(child.get('date_birth'))[:10]);age=today.year-born.year-((today.month,today.day)<(born.month,born.day))
      if name:family['profile']={'name':name,'age':max(3,min(10,age))}
     except ValueError:pass
    def save_private(name,data):
     target=PRIVATE/name;temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False));temp.chmod(0o600);temp.replace(target)
    save_private('family.json',family)
    meta={'connected':True,'syncedAt':datetime.now(timezone.utc).isoformat(),'calendarEvents':len(rows),'monthsRead':3,'upcomingPlans':len(plans),'profileLinked':'profile' in family,'source':'공식 웹 일정표','error':None}
    save_private('metadata.json',meta);emit(meta)
   elif action=='quit':break
   else:emit({'error':'unknown_command'})
  except Exception as e:
   emit({'error':type(e).__name__})
   if '--sync' in sys.argv:
    target=PRIVATE/'metadata.json';target.write_text(json.dumps({'connected':False,'error':'키즈노트 연결을 확인해 주세요.'},ensure_ascii=False));target.chmod(0o600);raise SystemExit(1)
 browser.close()
