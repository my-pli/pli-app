"""Real 180-second native preparation expiry and stale BEGIN; no shortened clock."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['actualPreparedMicrophoneOpened',
                             'actualThreeMinuteTtlStopsWithoutBegin',
                             'familyStorePreserved',
                             'staleBeginCannotReopenCapture'],
          'safetyChecks': {'actualThreeMinuteTtlStopsWithoutBegin': 'public-avd',
                           'staleBeginCannotReopenCapture': 'public-avd',
                           'familyStorePreserved': 'public-avd'},
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
          'fixtures': [],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['public-service', 'exclusive'],
                        ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,subprocess,time,uuid,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics);ADB=ROOT/'.tools/android-sdk/platform-tools/adb';marker=ROOT/'.tools/profiles/public/runtime-transition';URI='content://ai.teammoon.pli.demo';serial=json.loads((ROOT/'.tools/profiles/public/run-state.json').read_text())['serial']
def adb(*args):return subprocess.check_output([str(ADB),'-s',serial,*args],stderr=subprocess.STDOUT,timeout=12)
def read(path='state'):return json.loads(adb('exec-out','content','read','--user','10','--uri',URI+'/'+path))
def call(action,session=None,expect_error=False):
 out=adb('shell','content','call','--user','10','--uri',URI,'--method','session','--arg',action,*(['--extra','session:s:'+session]if session else[]))
 if not expect_error:assert b'Result:'in out and b'Exception'not in out,'Native control was not acknowledged: '+out.decode(errors='replace')[:1200]
 return out
ready_until=time.monotonic()+45
while True:
 s=json.load(urllib.request.urlopen('http://127.0.0.1:8878/api/status'));a=s.get('app',{})
 if not s['lease']['busy']and not s['voiceBusy']and s.get('appResponsive')is True and a.get('sessionStatus')=='STOPPED'and all(a.get(k)is True for k in ['demo','presentation','visible','hasView']):break
 assert time.monotonic()<ready_until,'The actual idle app View was not ready; TTL not started'
 time.sleep(.3)
summary=read('private-summary');marker.write_text(str(time.time()+260));session='ttl-'+uuid.uuid4().hex
subprocess.run(['systemctl','--user','stop','pli-pleos-portal.service'],check=True)
try:
 subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',"import os,sys;os.environ['PLI_PROFILE']='public';sys.path.insert(0,'scripts');from audio_guard import prime;prime()"],check=True,cwd=ROOT)
 call('preview')
 current=read()
 if not current.get('visible')or not current.get('hasView'):
  adb('shell','am','start','-W','--user','10','-n','ai.teammoon.pli/.MainActivity')
  view_deadline=time.monotonic()+8
  while not (current:=read()).get('visible')or not current.get('hasView'):
   assert time.monotonic()<view_deadline,'Actual native View unavailable after stopping host server'
   time.sleep(.2)
 metrics['actualPreparationState']={k:current.get(k)for k in ['visible','hasView','sessionStatus','deviceBootCount']}
 assert current['sessionStatus']=='STOPPED'
 receipt=current.get('stopReceipt')or{}
 if all(receipt.get(k)is True for k in ['captureStopped','playbackStopped','focusReleased','instanceClosed']):adb('shell','am','force-stop','--user','10','ai.pleos.playground.caas')
 start=time.monotonic();call('prepare',session);states=[];ready=False
 while time.monotonic()-start<200:
  s=read();state=(s['sessionStatus'],s['capture'])
  if not states or states[-1]['state']!=list(state):states.append({'atSeconds':round(time.monotonic()-start,3),'state':list(state)})
  if s['sessionStatus']=='STOPPED':break
  if s['capture']=='ACTIVE':ready=True
  call('heartbeat',session);time.sleep(.8)
 metrics.update(actualElapsedSeconds=round(time.monotonic()-start,3),transitions=states)
 checks['actualPreparedMicrophoneOpened']=ready
 checks['actualThreeMinuteTtlStopsWithoutBegin']=s['sessionStatus']=='STOPPED'and 178<=time.monotonic()-start<=195 and s['stopReceipt']['captureStopped']is True
 out=call('begin',session,expect_error=True);after=read();checks['staleBeginCannotReopenCapture']=b'SESSION_MISMATCH'in out and after['sessionStatus']=='STOPPED'and after['capture']=='STOPPED'
 checks['familyStorePreserved']=read('private-summary')==summary
finally:
 try:
  if read()['sessionStatus']!='STOPPED':call('end',session)
  call('preview')
 finally:marker.unlink(missing_ok=True);subprocess.run(['systemctl','--user','start','pli-pleos-portal.service'],check=True)
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
