"""Public Pleos console -> DDS/VHAL -> actual SDK callback verification."""
from pathlib import Path
import json,subprocess,time,urllib.request
root=Path(__file__).resolve().parents[2]
adb=root/'.tools/android-sdk/platform-tools/adb'
serial=json.loads((root/'.tools/run-state.json').read_text())['serial']
def logs():
    return subprocess.run([str(adb),'-s',serial,'logcat','-d','-v','brief','-s','PliVehicleEvent:I','*:S'],capture_output=True,text=True,check=True).stdout.splitlines()
def send(path):
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8088'+path,data=b'',method='PUT'),timeout=8) as r:return json.loads(r.read())
results=[]
try:
    for path,event in [('/vehicle/body?front_wiper=Low','rain'),('/vehicle/turn-signal?mode=BlinkLeft','turn_left'),('/vehicle/body?door_rl=true','door_open'),('/vehicle/body?door_rl=false','boarding')]:
        offset=len(logs());send(path);deadline=time.monotonic()+10;new=[]
        while time.monotonic()<deadline:
            new=logs()[offset:]
            if any(line.endswith(': '+event) for line in new):break
            time.sleep(.25)
        result={'control':path,'expectedEvent':event,'passed':any(line.endswith(': '+event) for line in new),'nativeLogs':new}
        results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
    (root/'qa/native/vehicle-events.json').write_text(json.dumps({'method':'Official development console control -> actual native Pleos Vehicle SDK callbacks; no debug event injection','passed':all(r['passed'] for r in results),'results':results},ensure_ascii=False,indent=2))
    assert all(r['passed'] for r in results)
finally:
    send('/vehicle/body?front_wiper=Off&door_rl=false')
    send('/vehicle/turn-signal?mode=Off')
