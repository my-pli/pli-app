from pathlib import Path
import os,json,time
os.environ['PLI_QA_PROFILE']='public'
from run_record import RunRecord
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};r=RunRecord(__file__,checks,metrics,fixtures=['silence.wav']);url=os.environ.get('PLI_QA_URL',json.loads((ROOT/'.tools/public-config.json').read_text())['url'])
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=b.new_context(ignore_https_errors=url.startswith('https://127.'),permissions=['microphone']);v=c.new_page();v.route('**/app.js*',lambda route:route.fulfill(path=str(ROOT/'demo-v2/app.js'),content_type='application/javascript'));v.goto(url+'/app');v.wait_for_function('state.status.controlReady&&!state.status.lease.busy');assert v.evaluate('connectVoice.toString().includes("Promise.all")');start=time.monotonic();events=[]
 def request(req):
  if '/api/session/'in req.url or '/audio-worklet'in req.url:events.append({'event':'request','path':req.url.split(url)[-1],'at':round(time.monotonic()-start,3)})
 def response(res):
  if '/api/session/'in res.url or '/audio-worklet'in res.url:events.append({'event':'response','path':res.url.split(url)[-1],'at':round(time.monotonic()-start,3),'status':res.status})
 v.on('request',request);v.on('response',response);v.evaluate("()=>{window.startupTrace=[];let prior='';window.startupTimer=setInterval(()=>{const a=state.status.app||{},key=JSON.stringify([a.sessionStatus,a.modelReady,a.ttsReady,a.phase,a.recognition,a.playback,a.spokenSequence]);if(key!==prior){prior=key;startupTrace.push({at:performance.now(),state:JSON.parse(key)});}},50);}")
 try:
  v.locator('#connect').click();v.wait_for_function('state.voice',timeout=45000);events.append({'event':'voice-ready','at':round(time.monotonic()-start,3)});v.wait_for_function("state.status.app.recognition==='READY'&&state.status.app.playback==='IDLE'&&state.status.app.phase==='LISTENING'&&state.status.app.speech===state.status.app.requestedText",timeout=35000);events.append({'event':'question-ready','at':round(time.monotonic()-start,3)});metrics['events']=events;metrics['stateTransitions']=v.evaluate('startupTrace');checks['questionReady']=True
 except Exception:
  metrics['events']=events
  r.diagnostic(v.evaluate('state.status'),'startup-failure');raise
 finally:
  v.evaluate('endSession()');v.wait_for_function('!state.ending&&!state.status.voiceBusy&&!state.status.lease.busy',timeout=20000);b.close()
print(json.dumps(metrics));assert all(checks.values())
