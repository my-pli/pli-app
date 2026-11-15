#!/usr/bin/env python3
"""Retain the project's emulator exit reason after the launcher returns."""
from pathlib import Path
import json,os,signal,subprocess,sys,time
from runtime_context import state_dir
root=Path(__file__).resolve().parents[1];state=state_dir()
p=subprocess.Popen(sys.argv[1:])
(state/'emulator.pid').write_text(str(p.pid))
def stop(*_):
    if p.poll() is None:p.terminate()
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
code=p.wait()
(state/'emulator-exit.json').write_text(json.dumps({'pid':p.pid,'returnCode':code,'at':time.time()}))
print('Pli emulator exited:',code,flush=True)
sys.exit(0 if code==0 else 1)
