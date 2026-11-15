#!/usr/bin/env python3
"""Install and manage the local Pli tailnet demo as a persistent user service."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools'
UNIT_NAME = 'pli-pleos-demo.service'

def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['start','stop','status'], nargs='?', default='start')
    action = parser.parse_args().action
    if action == 'stop':
        run('systemctl', '--user', 'disable', '--now', UNIT_NAME)
        print('Tailscale 시연 서버 종료. Pleos APK는 계속 실행됩니다.'); return
    if action == 'status':
        run('systemctl', '--user', 'status', '--no-pager', UNIT_NAME)
        path = TOOLS / 'demo-config.json'
        if path.exists():
            c = json.loads(path.read_text()); print(c['http']); print(c['https'])
        return
    state = json.loads(subprocess.check_output(['tailscale','status','--json']))
    if state.get('BackendState') != 'Running': raise RuntimeError('이 컴퓨터에서 Tailscale 로그인이 필요합니다.')
    ip = next(x for x in state['TailscaleIPs'] if ':' not in x)
    for name in ['ffmpeg','openssl','systemctl']:
        if not shutil.which(name): raise RuntimeError(name + ' 설치가 필요합니다.')
    python = TOOLS / 'demo-venv/bin/python'
    if not python.exists(): run(sys.executable, '-m', 'venv', TOOLS / 'demo-venv')
    requirements = ROOT / 'scripts/demo-requirements.txt'
    marker = TOOLS / 'demo-venv/requirements.sha256'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not marker.exists() or marker.read_text() != digest:
        run(python, '-m', 'pip', 'install', '-r', requirements)
        marker.write_text(digest)
    (TOOLS/'runtime-paused').unlink(missing_ok=True)
    tls = TOOLS / 'demo-tls'; tls.mkdir(parents=True, exist_ok=True)
    current = tls / 'address'
    if not (tls / 'cert.pem').exists() or not current.exists() or current.read_text() != ip:
        run('openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes', '-keyout', tls / 'key.pem', '-out', tls / 'cert.pem', '-days', '90', '-subj', '/CN=Pli Local Pleos Demo', '-addext', f'subjectAltName=IP:{ip},IP:127.0.0.1,DNS:localhost', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (tls / 'key.pem').chmod(0o600); current.write_text(ip)
    config = {'ip':ip, 'dnsName':state['Self']['DNSName'].rstrip('.'), 'http':f'http://{ip}:8876', 'https':f'https://{ip}:9000', 'httpsAlias':f'https://{ip}:8877', 'scope':'Tailscale IPv4 and loopback only', 'certificate':'Self-signed; browser confirmation needed on first HTTPS visit'}
    (TOOLS / 'demo-config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2))
    folder = Path.home() / '.config/systemd/user'; folder.mkdir(parents=True, exist_ok=True)
    # systemd quoted paths retain spaces; all values originate from this checkout.
    def quote(p): return '"' + str(p).replace('\\','\\\\').replace('"','\\"').replace('%','%%') + '"'
    runtime_name='pli-pleos-runtime.service'
    (TOOLS/'portal-mode').touch()
    runtime_unit='\n'.join(['[Unit]','Description=Pli Pleos emulator and APK supervisor','','[Service]','Type=simple','WorkingDirectory='+str(ROOT).replace('%','%%'),'ExecStart='+quote(python)+' '+quote(ROOT/'scripts/demo-runtime.py'),'Restart=on-failure','RestartSec=5','TimeoutStopSec=15','KillMode=process','UMask=0077','','[Install]','WantedBy=default.target',''])
    (folder/runtime_name).write_text(runtime_unit)
    node=shutil.which('node')
    if node:
        mcp_name='pli-kidsnote-mcp.service'
        mcp='\n'.join(['[Unit]','Description=Private read-only KidsNote MCP','','[Service]','WorkingDirectory='+str(ROOT),'ExecStart='+quote(Path(node))+' '+quote(ROOT/'scripts/kidsnote-mcp.mjs'),'Restart=on-failure','RestartSec=3','UMask=0077','','[Install]','WantedBy=default.target',''])
        (folder/mcp_name).write_text(mcp)
    unit = '\n'.join(['[Unit]', 'Description=Pli Pleos live demo on Tailscale','Wants='+runtime_name,'After='+runtime_name, '', '[Service]', 'Type=simple', 'WorkingDirectory='+str(ROOT).replace('%','%%'), 'ExecStart='+quote(python)+' '+quote(ROOT/'scripts/demo-server.py'), 'Environment=PLI_TAILSCALE_IP='+ip, f'Environment=PULSE_SERVER=unix:/run/user/{os.getuid()}/pulse/native', 'Restart=on-failure', 'RestartSec=5', 'TimeoutStopSec=20', 'KillMode=control-group', 'UMask=0077', '', '[Install]', 'WantedBy=default.target', ''])
    (folder / UNIT_NAME).write_text(unit)
    # The public portal owns a clean AVD, independent audio and console ports.
    public=TOOLS/'profiles/public';public.mkdir(parents=True,exist_ok=True);(public/'portal-mode').touch()
    public_runtime=runtime_unit.replace('Description=Pli Pleos emulator and APK supervisor','Description=Pli isolated public Pleos runtime').replace('Type=simple','Type=simple\nEnvironment=PLI_PROFILE=public')
    public_portal=unit.replace('pli-pleos-runtime.service','pli-pleos-public-runtime.service').replace('Type=simple','Type=simple\nEnvironment=PLI_PROFILE=public')
    (folder/'pli-pleos-public-runtime.service').write_text(public_runtime)
    (folder/'pli-pleos-portal.service').write_text(public_portal)
    run('systemctl','--user','daemon-reload')
    run('systemctl','--user','enable','--now',runtime_name,'pli-pleos-public-runtime.service','pli-pleos-portal.service',stdout=subprocess.DEVNULL)
    if node:run('systemctl','--user','enable','--now',mcp_name,stdout=subprocess.DEVNULL)
    run('systemctl','--user','enable',UNIT_NAME,stdout=subprocess.DEVNULL)
    run('systemctl','--user','restart',UNIT_NAME)
    for _ in range(30):
        try:
            with urllib.request.urlopen(config['http']+'/api/status', timeout=2) as response: json.loads(response.read())
            print('원격 조작·보고서: '+config['http']+'\n음성 시연: '+config['https']+'\nHTTPS 첫 접속 시 자체 서명 인증서 확인 후 마이크를 허용해 주세요.'); return
        except Exception: time.sleep(.5)
    raise RuntimeError('시연 서버를 시작하지 못했습니다. journalctl --user -u '+UNIT_NAME+' -n 30 으로 확인해 주세요.')

if __name__ == '__main__': main()
