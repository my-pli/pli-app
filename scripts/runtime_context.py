"""Explicit ownership of the personal and public project AVDs."""
from pathlib import Path
from dataclasses import dataclass
import json, os, subprocess, time

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / '.tools'
_ownership_cache={}

@dataclass(frozen=True)
class DeviceContext:
    profile: str

    def __post_init__(self):
        if self.profile not in {'personal', 'public'}:
            raise ValueError('Unknown runtime profile')

    @property
    def state_dir(self):
        return SHARED if self.profile == 'personal' else SHARED / 'profiles/public'

    @property
    def avd_name(self):
        return 'Pli_Pleos' if self.profile == 'personal' else 'Pli_Pleos_Demo'

    @property
    def console_port(self):
        return 8088 if self.profile == 'personal' else 18088

    @property
    def grpc_port(self):
        return 8554 if self.profile == 'personal' else 8560

    def state(self):
        return json.loads((self.state_dir / 'run-state.json').read_text())

    def serial(self):
        value = self.state()
        if value.get('profile', 'personal') != self.profile:
            raise RuntimeError('PROFILE_MISMATCH')
        self.assert_owned()
        return value['serial']

    def assert_owned(self):
        pid = int((self.state_dir / 'emulator.pid').read_text())
        args = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
        if b'-avd' not in args or args[args.index(b'-avd') + 1] != self.avd_name.encode():
            raise RuntimeError('PROFILE_MISMATCH')
        state = self.state()
        if state.get('profile', 'personal') != self.profile:
            raise RuntimeError('PROFILE_MISMATCH')
        discovery=Path('/run/user')/str(os.getuid())/'avd/running'/f'pid_{pid}.ini'
        fields={}
        for line in (discovery.read_text().splitlines()if discovery.exists()else []):
            if '='in line:
                key,value=line.split('=',1);fields[key.strip()]=value.strip()
        port=fields.get('port.serial')
        if port and state.get('serial')!=f'emulator-{port}':raise RuntimeError('PROFILE_SERIAL_MISMATCH')
        if not port:
            adb=SHARED/'android-sdk/platform-tools/adb'
            key=(pid,state['serial'],self.avd_name)
            if time.monotonic()-_ownership_cache.get(key,0)>2:
                name=subprocess.check_output([str(adb),'-s',state['serial'],'emu','avd','name'],timeout=3).decode().splitlines()[0].strip()
                if name!=self.avd_name:raise RuntimeError('PROFILE_SERIAL_MISMATCH')
                _ownership_cache[key]=time.monotonic()
        return pid

def selected():
    return DeviceContext(os.environ.get('PLI_PROFILE', 'personal'))

def state_dir():
    path = selected().state_dir
    path.mkdir(parents=True, exist_ok=True)
    return path

def runtime_intent(folder):
    """Missing marker is legacy running; an empty legacy marker means paused."""
    path=Path(folder)/'runtime-paused'
    try:
        value=json.loads(path.read_text())
        if value.get('desiredState')not in {'running','paused'}or not isinstance(value.get('generation'),int):raise ValueError('INVALID_RUNTIME_INTENT')
        return value
    except FileNotFoundError:return {'desiredState':'running','generation':0}
    except json.JSONDecodeError:return {'desiredState':'paused','generation':0}

def set_runtime_intent(folder,desired,expected_generation=None):
    import fcntl,uuid
    if desired not in {'running','paused'}:raise ValueError('INVALID_RUNTIME_INTENT')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with (folder/'runtime-intent.lock').open('a')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);prior=runtime_intent(folder)
        if expected_generation is not None and prior['generation']!=expected_generation:raise RuntimeError('RUNTIME_INTENT_CHANGED')
        value={'desiredState':desired,'generation':prior['generation']+1,'updatedAt':time.time()};path=folder/'runtime-paused';pending=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');pending.write_text(json.dumps(value)+'\n');pending.replace(path);return value

def intent_current(folder,generation):
    return runtime_intent(folder)==generation if isinstance(generation,dict)else runtime_intent(folder)['generation']==generation
