#!/usr/bin/env python3
"""Publish the demo through a credential-free HTTPS tunnel; keep its URL current."""
from pathlib import Path
import json,os,re,signal,subprocess,time
ROOT=Path(__file__).resolve().parents[1];TOOLS=ROOT/'.tools'
state=TOOLS/'public-config.json'
def save(value):
    temporary=state.with_suffix('.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2));temporary.replace(state)
save({'enabled':False,'starting':True,'updatedAt':time.time()})
config=TOOLS/'cloudflared-demo.yml';config.write_text('no-autoupdate: true\n')
process=subprocess.Popen([str(TOOLS/'bin/cloudflared'),'--config',str(config),'--no-autoupdate','tunnel','--url','http://127.0.0.1:8878','--http-host-header','pli-public.local','--protocol','http2'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
def stop(*_):process.terminate()
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
try:
    for line in process.stdout:
        print(line.rstrip(),flush=True)
        match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
        if match:save({'enabled':True,'url':match.group(0),'issuedAt':time.time(),'pid':process.pid,'provider':'Cloudflare Quick Tunnel'})
    code=process.wait()
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=10)
    save({'enabled':False,'updatedAt':time.time()})
raise SystemExit(code or 1)
