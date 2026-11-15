#!/usr/bin/env python3
"""Keep the official emulator console session active without a browser UI."""
import signal,time,urllib.request,os,fcntl
from pathlib import Path
from runtime_context import selected,state_dir
context=selected();root=Path(__file__).resolve().parents[1];state=state_dir()
lock=(state/'console-session.lock').open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit(0)
pidfile=state/'console-session.pid'
pidfile.write_text(str(os.getpid()))
running=True
def stop(*_):
 global running
 running=False
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
url=f'http://127.0.0.1:{context.console_port}/browser/session?client=pli-{context.profile}-development'
def send(closing=False):
 request=urllib.request.Request(url+('&closing=1' if closing else ''),data=b'',method='POST')
 try:
  with urllib.request.urlopen(request,timeout=.8) as response:response.read()
 except Exception:pass
try:
 while running:send();time.sleep(.5)
finally:
 send(True)
 if pidfile.exists() and pidfile.read_text()==str(os.getpid()):pidfile.unlink()
