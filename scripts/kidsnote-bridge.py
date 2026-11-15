#!/usr/bin/env python3
"""Private read-only MCP -> validated import batch. No passwords in arguments/logs."""
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import argparse,fcntl,json,os,subprocess,sys,urllib.request,uuid
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'.tools/private/kidsnote'
PRIVATE.mkdir(parents=True,exist_ok=True,mode=0o700);PRIVATE.chmod(0o700)
def save(name,data):
 target=PRIVATE/name;temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False));temp.chmod(0o600);temp.replace(target)
def rpc(method,params):
 token=(PRIVATE/'mcp-token').read_text().strip();payload=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
 req=urllib.request.Request('http://127.0.0.1:3904/mcp',data=payload,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
 with urllib.request.urlopen(req,timeout=65) as response:result=json.load(response)
 if 'error' in result:raise RuntimeError('MCP_PROTOCOL')
 value=result['result']
 if value.get('isError'):raise RuntimeError('MCP_READ_FAILED')
 return value

def tool(name,args=None):
 value=rpc('tools/call',{'name':name,'arguments':args or {}})
 if 'structuredContent' not in value:raise RuntimeError('MCP_SCHEMA')
 return value['structuredContent']

def options():return tool('get_sync_options')
def snapshot_window(scope,start,end):
 with (PRIVATE/'sync.lock').open('a') as lock:
  os.chmod(lock.name,0o600);fcntl.flock(lock,fcntl.LOCK_EX)
  if not scope:
   try:scope=json.loads((PRIVATE/'selection.json').read_text()).get('scope')
   except (OSError,ValueError):pass
  if not scope:
   choices=options()['choices']
   if len(choices)==1 or choices and choices[0].get('aggregate'):scope=choices[0]['scope']
  if not scope:raise RuntimeError('SCOPE_REQUIRED')
  result=tool('get_sync_snapshot',{'scope':scope,'from':start,'to':end,'deadline':int(__import__('time').time()*1000)+8500})
  if not result.get('complete') or result.get('sourceScope')!=scope or result.get('windowStart')!=start or result.get('windowEnd')!=end:raise RuntimeError('PARTIAL_FETCH')
  try:sequence=int(json.loads((PRIVATE/'sequence.json').read_text()))+1
  except (OSError,ValueError,TypeError):sequence=1
  save('sequence.json',sequence)
  batch={k:result[k]for k in ['sourceScope','complete','windowStart','windowEnd','plans']}
  batch.update(batchId='mcp:'+uuid.uuid4().hex,sourceSequence=sequence,facts=[])
  if len(batch['plans'])>500:raise RuntimeError('CAPACITY')
  return batch

def sync(scope=None):
 with (PRIVATE/'sync.lock').open('a') as lock:
  os.chmod(lock.name,0o600);fcntl.flock(lock,fcntl.LOCK_EX)
  choices=options()['choices']
  if scope is None:
   try:scope=json.loads((PRIVATE/'selection.json').read_text()).get('scope')
   except (OSError,ValueError):pass
  if scope is None and len(choices)==1:scope=choices[0]['scope']
  if scope is None and choices and choices[0].get('aggregate'):scope=choices[0]['scope']
  if scope not in {c['scope'] for c in choices}:raise RuntimeError('SCOPE_REQUIRED')
  today=datetime.now(ZoneInfo('Asia/Seoul')).date();snapshot=tool('get_sync_snapshot',{'scope':scope,'from':today.isoformat(),'to':(today+timedelta(days=60)).isoformat()})
  if not snapshot.get('complete') or snapshot['sourceScope']!=scope:raise RuntimeError('PARTIAL_FETCH')
  try:sequence=json.loads((PRIVATE/'sequence.json').read_text())+1
  except (OSError,ValueError,TypeError):sequence=1
  save('sequence.json',sequence)
  batch={k:snapshot[k]for k in ['sourceScope','complete','windowStart','windowEnd','plans']}
  batch.update(batchId='mcp:'+uuid.uuid4().hex,sourceSequence=sequence)
  if snapshot.get('profile'):batch['profile']=snapshot['profile']
  batch['facts']=[];briefing_errors=[]
  for topic,day in [('MENU',today),('MENU',today+timedelta(days=1)),('REPORT',today),('REPORT_RECENT',today),('NOTICES',today),('MONTHLY',today),('ALBUMS',today)]:
   try:batch['facts'].append(tool('get_voice_answer',{'scope':scope,'topic':topic,'date':str(day)}))
   except Exception:briefing_errors.append(topic)
  # Mirror Android's code point limits; no silent truncation or age clamping.
  if len(batch['plans'])>500:raise RuntimeError('CAPACITY')
  for p in batch['plans']:
   if not 1<=len(p['title'])<=120 or len(p['preparation'])>300:raise RuntimeError('FIELD_LIMIT')
  if len(json.dumps(batch,ensure_ascii=False).encode())>2*1024*1024:raise RuntimeError('CAPACITY')
  save('family.json',batch);save('selection.json',{'scope':scope})
  meta={'connected':True,'status':'CONNECTED','syncedAt':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'calendarEvents':snapshot['calendarEvents'],'monthsRead':snapshot['monthsRead'],'upcomingPlans':len(batch['plans']),'profileLinked':'profile'in batch,'source':snapshot['source'],'sourceScope':scope,'batchId':batch['batchId'],'error':None,'appliedPlans':None,'factsCount':len(batch['facts']),'briefingErrors':briefing_errors}
  save('metadata.json',meta);return meta

def main():
 p=argparse.ArgumentParser();p.add_argument('--sync',action='store_true');p.add_argument('--login',action='store_true');p.add_argument('--options',action='store_true');p.add_argument('--scope');p.add_argument('--answer',action='store_true');p.add_argument('--topic');p.add_argument('--date');p.add_argument('--days',type=int,default=1);a=p.parse_args()
 if a.login:return subprocess.call([sys.executable,str(ROOT/'scripts/kidsnote-web-login.py'),'--login'])
 try:
  rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'pli','version':'3.0.0'}})
  if a.answer and a.topic=='BRIEF':
   if a.days not in {1,7}:raise RuntimeError('INVALID_WINDOW')
   start=datetime.strptime(a.date,'%Y-%m-%d').date();result={'snapshot':snapshot_window(a.scope,str(start),str(start+timedelta(days=a.days-1)))}
  else:result=tool('get_voice_answer',{'scope':a.scope,'topic':a.topic,'date':a.date}) if a.answer else options() if a.options else sync(a.scope)
  if len(json.dumps(result,ensure_ascii=False).encode())>500*1024:raise RuntimeError('CAPACITY')
  print(json.dumps(result,ensure_ascii=False));return 0
 except Exception as e:
  code=str(e) if str(e) in {'SCOPE_REQUIRED','PARTIAL_FETCH','CAPACITY','FIELD_LIMIT','MCP_SCHEMA','MCP_PROTOCOL','MCP_READ_FAILED'}else'MCP_UNAVAILABLE'
  try:old=json.loads((PRIVATE/'metadata.json').read_text())
  except (OSError,ValueError):old={}
  old.update(status=code,error=code,lastAttempt=datetime.now(ZoneInfo('Asia/Seoul')).isoformat());save('metadata.json',old)
  print(json.dumps({'error':code},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
