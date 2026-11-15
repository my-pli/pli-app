#!/usr/bin/env python3
"""Route only this project's emulator to a real input; preserve all host defaults."""
from pathlib import Path
import os,time
import pulsectl
if (Path(__file__).resolve().parents[1]/'.tools/demo-audio-state.json').exists():raise SystemExit('공개 세션 정리 전 실제 마이크 복원을 보류합니다.')
server=os.environ.get('PULSE_SERVER',f'unix:/run/user/{os.getuid()}/pulse/native')
with pulsectl.Pulse('pli-emulator-microphone',server=server) as pulse:
    sources=[s for s in pulse.source_list() if s.name.startswith(('alsa_input.','bluez_input.'))]
    preferred=os.environ.get('PLI_MIC_SOURCE',pulse.server_info().default_source_name)
    source=next((s for s in sources if s.name==preferred),sources[0] if sources else None)
    if source is None:raise SystemExit('실제 마이크 입력 장치를 찾지 못했습니다.')
    for _ in range(30):
        moved=False
        for stream in pulse.source_output_list():
            if stream.proplist.get('application.name')!='qemu-system-x86_64':continue
            process=Path('/proc')/stream.proplist.get('application.process.id','0')/'cmdline'
            argv=process.read_bytes().split(b'\0') if process.exists() else []
            owns=b'-avd' in argv and argv[argv.index(b'-avd')+1:argv.index(b'-avd')+2]==[b'Pli_Pleos']
            if owns:
                pulse.source_output_move(stream.index,source.index);moved=True
        if moved:print('Pleos 마이크: '+source.name);break
        time.sleep(.3)
