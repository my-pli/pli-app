import { api, ensureSession, todayKst, plain } from './site.mjs';
import crypto from 'node:crypto';
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
export const SYNC_TOOLS=[
 {name:'get_sync_options',description:'플리 개인 연동의 아이·기관·반 선택 목록. 자동 첫 아이 선택 없음.',inputSchema:{type:'object',properties:{}}},
 {name:'get_sync_snapshot',description:'선택된 아이·기관·반의 완전한 일정 snapshot. 부분 조회는 오류.',inputSchema:{type:'object',properties:{scope:{type:'string'},from:{type:'string'},to:{type:'string'}},required:['scope','from','to']}}
];
export async function syncOptions(){
 const ctx=await ensureSession();const result=[];
 for(const child of ctx.children)for(const center of child.centers)for(const cls of center.classes){
  const key=hash(`${ctx.accountId??""}|${child.id}|${center.id}|${cls.id}`).slice(0,32);
  result.push({scope:key,childId:child.id,childName:child.name,birth:child.birth,centerId:center.id,centerName:center.name,classId:cls.id,className:cls.name});
 }
 const children=new Set(result.map(x=>String(x.childId)));
 if(result.length>1&&children.size===1){const first=result[0];result.unshift({...first,scope:'all:'+hash(`${ctx.accountId??''}|${first.childId}`).slice(0,24),centerName:'연결된 모든 기관',className:'전체 일정',aggregate:true});}
 return result;
}
async function allPages(path,params,deadline){
 const rows=[];let page;const cursors=new Set();
 for(let i=0;i<100;i++){
  if(deadline&&Date.now()>=deadline)throw new Error("PARTIAL_DEADLINE");
  const j=await api(path,{...params,...(page===undefined?{}:{page})},{deadline});
  const list=Array.isArray(j)?j:j?.results;
  if(!Array.isArray(list))throw new Error('UNSUPPORTED_SCHEMA');
  rows.push(...list);if(rows.length>10000)throw new Error('PARTIAL_LIMIT');
  const next=Array.isArray(j)?null:j.next;if(!next)return rows;
  if(!list.length||cursors.has(String(next)))throw new Error('PARTIAL_PAGINATION');
  cursors.add(String(next));page=next;
 }
 throw new Error('PARTIAL_LIMIT');
}
export async function syncTool(name,args){
 const choices=await syncOptions();if(name==='get_sync_options')return {choices};
 const chosen=choices.find(x=>x.scope===args.scope);if(!chosen)throw new Error('SCOPE_REQUIRED');
 const from=String(args.from),to=String(args.to);if(!/^\d{4}-\d{2}-\d{2}$/.test(from)||!/^\d{4}-\d{2}-\d{2}$/.test(to)||from>to)throw new Error('INVALID_WINDOW');
 const months=[];let month=from.slice(0,7);while(month<=to.slice(0,7)){
  months.push(month);if(months.length>4)throw new Error('INVALID_WINDOW');const [y,m]=month.split('-').map(Number);month=`${m===12?y+1:y}-${String(m===12?1:m+1).padStart(2,'0')}`;
 }
 const targets=chosen.aggregate?choices.filter(x=>!x.aggregate&&x.childId===chosen.childId):[chosen];
 const all=[];
 for(const target of targets)for(const m of months){const rows=await allPages(`/v1/centers/${target.centerId}/calendar`,{cls:target.classId,month_event:m+'-01',page_size:100},args.deadline);all.push(...rows.map(row=>({...row,_scopeEvent:target.centerId+':'+row.id})));}
 const rows=[...new Map(all.map(row=>{if(row.id===undefined||!/^\d{4}-\d{2}-\d{2}/.test(String(row.date_event))||typeof row.title!=='string')throw new Error('UNSUPPORTED_SCHEMA');return [String(row._scopeEvent),row];})).values()];
 const plans=rows.filter(x=>String(x.date_event).slice(0,10)>=from&&String(x.date_event).slice(0,10)<=to).map(x=>{
  const title=plain(x.title).trim(),content=plain(x.content||'');
  const prep=content.split(/\n/).filter(s=>/준비물|지참|챙겨/.test(s)).map(s=>s.trim()).join(' · ');
  if(!title||[...title].length>120||[...prep].length>300)throw new Error('FIELD_LIMIT');
  return {id:'kidsnote:'+hash(chosen.scope+'|'+x._scopeEvent).slice(0,40),date:String(x.date_event).slice(0,10),title,preparation:prep,origin:'KIDSNOTE',sourceScope:chosen.scope,sourceEventId:String(x._scopeEvent)};
 });
 let profile;const today=todayKst();if(/^\d{4}-\d{2}-\d{2}$/.test(String(chosen.birth))){const age=+today.slice(0,4)-+chosen.birth.slice(0,4)-(today.slice(5)<chosen.birth.slice(5)?1:0);if(age>=3&&age<=12&&chosen.childName&&[...chosen.childName].length<=30)profile={name:chosen.childName,age,school:[...new Set(targets.map(x=>x.centerName))].join(' · '),volume:.7};}
 return {sourceScope:chosen.scope,complete:true,windowStart:from,windowEnd:to,plans,profile,calendarEvents:rows.length,monthsRead:months.length,source:'제공된 키즈노트 MCP · 공식 계정 읽기'};
}
