"""Kill only the owned demo server; verify native release after service restart."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['frozenOsControlNeverOpenedMicrophone',
                             'independentRuntimeReleasesHeldPointerAfterFreeze',
                             'nativeStopsAfterServerSigkill',
                             'voiceResourceProcessGone'],
          'safetyChecks': {'nativeStopsAfterServerSigkill': 'public-avd',
                           'voiceResourceProcessGone': 'public-avd'},
          'inputs': ['android/app/src/main/AndroidManifest.xml',
                     'android/app/src/main/java/ai/teammoon/pli/DemoStateProvider.kt',
                     'android/app/src/main/java/ai/teammoon/pli/MainActivity.kt',
                     'android/app/src/main/java/ai/teammoon/pli/PliApplication.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/DataContract.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/FamilyDocuments.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/PlanDocuments.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/PlanImporter.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/PliStore.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/SessionJournal.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/FamilyAnswers.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/JourneyExperience.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/LearningCatalog.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/Models.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/ReadingContext.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/VehicleSignalHealth.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/VoiceInterpreter.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/StageCards.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/MicLevel.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/DemoTrip.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/KoreanReading.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PliVoiceEngine.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/OnDevicePlayback.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/EdgeVoice.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/CarPanel.kt',
                     'android/app/src/main/assets/tts/manifest.json',
                     'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
                     'android/app/src/main/java/ai/teammoon/pli/edge/EdgeAi.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/PliStage.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/StageSurface.kt',
                     'android/app/src/main/java/ai/teammoon/pli/vehicle/PleosVehicleSource.kt',
                     'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleConnection.kt',
                     'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleService.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/CompanionService.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/ConversationController.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/KoreanModel.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/OfflineListener.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PcmCapture.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PcmWav.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PleosSpeechListener.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PliSpeaker.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/SpeechSdkIo.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/UtteranceGate.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/VoiceSessionConnection.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/WindowRecoveryPolicy.kt',
                     'android/app/src/main/res/drawable/ic_pli.xml',
                     'android/app/src/main/res/values/styles.xml',
                     'android/app/src/main/res/xml/automotive_app_desc.xml',
                     'android/app/src/main/res/xml/network_security_config.xml',
                     'demo-v2/app.js',
                     'demo-v2/audio-worklet.js',
                     'demo-v2/index.html',
                     'demo-v2/style.css',
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': ['silence.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['public-service', 'exclusive'],
                        ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,os,signal,subprocess,time
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics)
from playwright.sync_api import sync_playwright
ADB=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/profiles/public/run-state.json').read_text())['serial'];BASE='https://127.0.0.1:9001'
def adb(*args):return subprocess.check_output([str(ADB),'-s',serial,*args],timeout=8)
def native(path='state'):return json.loads(adb('exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path))
def wait(p,seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   s=native()
   entry={k:s.get(k)for k in ['sessionStatus','capture','playback','epoch','deviceBootCount']}
   history=metrics.setdefault('nativeTransitions',[])
   if not history or history[-1]['state']!=entry:history.append({'atSeconds':round(time.monotonic()-record.start,3),'state':entry})
   if p(s):return s
  except (subprocess.SubprocessError,ValueError):pass
  time.sleep(.3)
 raise AssertionError('Native recovery did not meet the deadline')
# The runtime watchdog must also lift a held pointer while the server is frozen.
with sync_playwright()as q:
 browser=q.chromium.launch(headless=True,channel='chrome');context=browser.new_context(ignore_https_errors=True);page=context.new_page();page.goto(BASE+'/pleos');page.wait_for_function("state.media==='LIVE'&&state.status.controlReady&&!state.status.lease.busy",timeout=30000);page.locator('#claim-control').click();page.wait_for_function('owned()');page.evaluate("()=>{window.qaMicCalls=0;navigator.mediaDevices.getUserMedia=()=>{qaMicCalls++;throw Error('unexpected microphone');};}")
 rect=page.locator('#live-video').bounding_box();page.mouse.move(rect['x']+rect['width']*.9,rect['y']+rect['height']*.2);page.mouse.down();page.wait_for_timeout(200)
 journal=ROOT/'.tools/profiles/public/held-pointers.json';assert json.loads(journal.read_text())['pointers'],'Actual DOWN journal was not established'
 pid=int(subprocess.check_output(['systemctl','--user','show','-p','MainPID','--value','pli-pleos-portal.service']).decode());start=time.monotonic();os.kill(pid,signal.SIGSTOP)
 try:
  until=time.monotonic()+10
  while time.monotonic()<until:
   held=json.loads(journal.read_text())
   if not held.get('pointers')and held.get('serverPid')!=pid:break
   time.sleep(.15)
  checks['independentRuntimeReleasesHeldPointerAfterFreeze']=not held.get('pointers')and held.get('serverPid')!=pid
  checks['frozenOsControlNeverOpenedMicrophone']=native()['capture']=='STOPPED'and page.evaluate('qaMicCalls===0')
  metrics['heldPointerRecoverySeconds']=round(time.monotonic()-start,3)
 finally:os.kill(pid,signal.SIGCONT)
 page.mouse.up();page.evaluate('endSession()');page.wait_for_function('!state.token&&!state.ending',timeout=20000);browser.close()

with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=b.new_context(ignore_https_errors=True,permissions=['microphone']);v=c.new_page();v.goto(BASE+'/app');v.wait_for_function('state.status.controlReady && !state.status.lease.busy');v.locator('#connect').click();v.wait_for_function('state.voice',timeout=45000)
 v.wait_for_function("state.status.app.sessionStatus==='ACTIVE' && state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE' && state.status.app.ttsReady",timeout=30000)
 before=native();pid=int(subprocess.check_output(['systemctl','--user','show','-p','MainPID','--value','pli-pleos-portal.service']).decode());assert str(ROOT/'scripts/demo-server.py').encode()in(Path('/proc')/str(pid)/'cmdline').read_bytes()
 start=time.monotonic();os.kill(pid,signal.SIGKILL)
 try:
  stopped=wait(lambda s:s['sessionStatus']=='STOPPED'and s['capture']=='STOPPED',18)
  checks['nativeStopsAfterServerSigkill']=stopped['epoch']>before['epoch']and stopped['stopReceipt']['captureStopped']is True
  checks['voiceResourceProcessGone']='ai.teammoon.pli:voice' not in adb('shell','ps','-A','-o','NAME').decode().splitlines()
  metrics['autonomousStopSeconds']=round(time.monotonic()-start,3)
 finally:subprocess.run(['systemctl','--user','start','pli-pleos-portal.service'],check=True)
 v.wait_for_function('!state.status.lease.busy',timeout=20000);v.wait_for_function('!state.ending',timeout=15000)
 b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
