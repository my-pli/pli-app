/** Real adapter code with an isolated network boundary. No account/session files are read. */
import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import * as site from '../../scripts/kidsnote_mcp/site.mjs';
import {voiceAnswer} from '../../scripts/kidsnote_mcp/voice.mjs';
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'pli-mcp-fixture-'));site.setKeyDirs([temp]);
const me={user:{id:'fixture-owner',name:'테스트 보호자'},children:[{id:'fixture-child',name:'테스트 친구',date_birth:'2021-01-01',enrollment:[{center_id:1,center_name:'테스트 원',belong_to_class:10,class_name:'테스트 반',is_approved:true}]}]};
let queue=[],posts=0;globalThis.fetch=async(url,opts)=>{if(opts?.method==='POST')posts++;if(new URL(url).pathname==='/v1/me/info/')return Response.json(me);const item=queue.shift();if(!item)throw Error('Unexpected fixture request');return Response.json(item.body,{status:item.status||200});};
const checks={};const seed=async()=>{site.resetSession();await site.seedSession('sessionid=fixture');};
try{
 await seed();queue=[{body:{error:'invalid successful schema'}}];await assert.rejects(()=>voiceAnswer({topic:'REPORT',date:'2026-11-11'}),/UNSUPPORTED_SCHEMA/);checks.malformedSuccessIsNotEmpty=true;
 await seed();queue=[{body:[]}];const empty=await voiceAnswer({topic:'REPORT',date:'2026-11-11'});assert.equal(empty.status,'EMPTY');checks.realEmptyArrayAccepted=true;
 await seed();queue=[{body:{results:[],next:null}}];assert.deepEqual(await site.collect('/v1/fixture/'),[]);checks.realEmptyPageAccepted=true;
 await seed();queue=[{body:{results:[{id:1}],next:2}},{body:{results:[{id:2}],next:null}}];assert.deepEqual((await site.collect('/v1/fixture/')).map(x=>x.id),[1,2]);checks.fullPaginationCollected=true;
 await seed();queue=[{body:{results:[{id:1}],next:2}},{body:{error:'upstream failure'},status:503}];await assert.rejects(()=>site.collect('/v1/fixture/'));checks.partialPageFailureRejected=true;
 await seed();queue=[{body:{error:'expired'},status:401}];await assert.rejects(()=>site.collect('/v1/fixture/'));assert.equal(posts,0);checks.expiredAuthDoesNotInventEmptyOrRetryPasswords=true;
 await seed();queue=[{body:{results:[{id:1,date_written:'2026-11-10'}],next:2}},{body:{results:[{id:2,date_written:'2026-11-09'}],next:3}},{body:{results:[{id:3,date_written:'2026-11-08'}],next:null}},{body:{id:3,date_written:'2026-11-08',content:'세 번째 쪽의 알림장'}}];let answer=await voiceAnswer({topic:'REPORT',date:'2026-11-08'});assert.equal(answer.coverage.pagesRead,3);assert.equal(answer.status,'AVAILABLE');assert.match(answer.fullText,/세 번째/);checks.reportDateBeyondSecondPage=true;
 await seed();queue=[{body:{results:Array.from({length:20},(_,i)=>({id:i,child_id:'other'})),next:2}},{body:{results:[{id:22,child_id:'fixture-child',title:'선택한 아이 소식',summary:'소식 내용'}],next:null}}];answer=await voiceAnswer({topic:'NOTIFICATIONS',date:'2026-11-11'});assert.equal(answer.status,'AVAILABLE');assert.match(answer.text,/선택한 아이/);assert.equal(answer.coverage.pagesRead,2);checks.notificationsFilterAfterPagination=true;
 await seed();queue=[{body:{results:[{id:1}],next:2}},{body:{results:[{id:2}],next:2}}];let covered=await site.collectWithCoverage('/v1/fixture/');assert.equal(covered.coverage.complete,false);assert.equal(covered.coverage.reason,'CURSOR_REPEATED');checks.repeatedCursorIsPartial=true;
 await seed();queue=[{body:{results:[{id:1,date_written:'2026-11-10'}],next:2}},{body:{error:'failure'},status:503}];answer=await voiceAnswer({topic:'REPORT',date:'2026-11-11'});assert.equal(answer.status,'PARTIAL');assert.equal(answer.coverage.complete,false);assert.equal(answer.text,'');checks.partialEmptyNeverMeansAbsent=true;
 await seed();queue=[{body:{results:[{id:1}],next:2}}];covered=await site.collectWithCoverage('/v1/fixture/',{}, {pages:1});assert.equal(covered.coverage.reason,'PAGE_LIMIT');checks.pageLimitIsPartial=true;
 await seed();queue=[{body:{results:[{id:1,date_written:'2026-11-11'}],next:null}},{body:{id:1,date_written:'2026-11-11',content:'긴 본문😀'.repeat(1400)}}];answer=await voiceAnswer({topic:'REPORT',date:'2026-11-11'});assert.equal(answer.truncated,true);assert.ok(answer.fullText.length>answer.text.length);assert.ok(answer.fullText.endsWith('😀'));assert.equal([...answer.text].length,2400);checks.fullDocumentAndUnicodePreserved=true;
 await seed();queue=[{body:{results:[{id:1,error:'missing source date'}],next:null}}];await assert.rejects(()=>voiceAnswer({topic:'REPORT',date:'2026-11-11'}),/UNSUPPORTED_SCHEMA/);checks.malformedRowsNeverBecomeEmpty=true;
 console.log(JSON.stringify(checks));
}finally{fs.rmSync(temp,{recursive:true,force:true});}
