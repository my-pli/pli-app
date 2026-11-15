#!/usr/bin/env python3
"""Manage the internet demo without changing tailnet policy or router ports."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];TOOLS=ROOT/'.tools';UNIT='pli-pleos-public.service'
def run(*args):subprocess.run(list(map(str,args)),check=True)
parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','status'],nargs='?',default='start');action=parser.parse_args().action
if action=='stop':run('systemctl','--user','disable','--now',UNIT);raise SystemExit()
if action=='status':
    run('systemctl','--user','status','--no-pager',UNIT)
    if (TOOLS/'public-config.json').exists():print((TOOLS/'public-config.json').read_text())
    raise SystemExit()
binary=TOOLS/'bin/cloudflared';binary.parent.mkdir(parents=True,exist_ok=True)
expected='1f99fb518b83dec2ba8d870a7cc991d82a77e6196295a3d2754ba17ab9f91872'
if not binary.exists():
    temp=binary.with_suffix('.part');urllib.request.urlretrieve('https://github.com/cloudflare/cloudflared/releases/download/2026.10.7/cloudflared-linux-amd64',temp)
    if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise RuntimeError('cloudflared checksum mismatch')
    temp.rename(binary)
if hashlib.sha256(binary.read_bytes()).hexdigest()!=expected:raise RuntimeError('cloudflared checksum mismatch')
binary.chmod(0o755)
if subprocess.run(['systemctl','--user','is-active','--quiet','pli-pleos-portal.service']).returncode:run(ROOT/'pleos','demo')
def quote(x):return '"'+str(x).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
folder=Path.home()/'.config/systemd/user';folder.mkdir(parents=True,exist_ok=True)
(folder/UNIT).write_text('\n'.join(['[Unit]','Description=Pli public HTTPS demo tunnel','Wants=pli-pleos-portal.service','After=pli-pleos-portal.service','','[Service]','Type=simple','WorkingDirectory='+str(ROOT),'ExecStart='+quote(sys.executable)+' '+quote(ROOT/'scripts/public-tunnel.py'),'Restart=on-failure','RestartSec=5','TimeoutStopSec=15','KillMode=control-group','UMask=0077','','[Install]','WantedBy=default.target','']))
run('systemctl','--user','daemon-reload');run('systemctl','--user','enable','--now',UNIT)
for _ in range(90):
    try:
        value=json.loads((TOOLS/'public-config.json').read_text())
        if value.get('enabled') and value.get('url'):print(value['url']);raise SystemExit()
    except (OSError,ValueError):pass
    time.sleep(1)
raise RuntimeError('Public tunnel startup timed out; check journalctl --user -u '+UNIT)
