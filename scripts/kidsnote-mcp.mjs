/** Reviewed sources from the user's KidsNote MCP. Loopback + private bearer token. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer,listen,setKeyDirs } from './kidsnote_mcp/server.mjs';
import { seedSession } from './kidsnote_mcp/site.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const dir=path.join(root,'.tools/private/kidsnote');fs.mkdirSync(dir,{recursive:true,mode:0o700});fs.chmodSync(dir,0o700);setKeyDirs([dir]);
const tokenPath=path.join(dir,'mcp-token');if(!fs.existsSync(tokenPath))fs.writeFileSync(tokenPath,crypto.randomBytes(32).toString('hex'),{mode:0o600});
const token=fs.readFileSync(tokenPath,'utf8').trim();
try{const state=JSON.parse(fs.readFileSync(path.join(dir,'browser.json'),'utf8'));const cookie=state.cookies.filter(c=>c.domain==='kidsnote.com'||c.domain.endsWith('.kidsnote.com')).map(c=>`${c.name}=${c.value}`).join('; ');if(cookie)await seedSession(cookie);}catch{console.error('기존 웹 세션을 확인하지 못했습니다. 공식 로그인 또는 개인 키 파일을 확인하세요.');}
const server=createServer({token,log:message=>console.log(message)});await listen(server);console.log('KidsNote MCP ready on loopback :3904');
