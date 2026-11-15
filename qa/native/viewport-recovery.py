"""Real owned task removal -> same voice owner -> visible View, and END while lost."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['actualTaskLossAndViewRecovery',
                             'browserVoiceConnectionRetained',
                             'endDuringRecoveryCannotReopenMicrophone',
                             'familyStorePreserved',
                             'realVoiceWorksAfterWindowReturns',
                             'sameEpochAndCaptureThroughoutRecovery'],
          'safetyChecks': {'endDuringRecoveryCannotReopenMicrophone': 'public-avd',
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
          'fixtures': ['math-primary.wav', 'silence.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,subprocess,time,base64,array,re
import os
os.environ['PLI_QA_PROFILE']='public'
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'transitions':[],'nonSilentOutput':0};record=RunRecord(__file__,checks,metrics);URL='https://127.0.0.1:9001';ADB=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/profiles/public/run-state.json').read_text())['serial']
from playwright.sync_api import sync_playwright
def native(path='state'):return json.loads(subprocess.check_output([str(ADB),'-s',serial,'exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path],timeout=12))
def task_records():
 out=subprocess.check_output([str(ADB),'-s',serial,'shell','dumpsys','activity','activities','ai.teammoon.pli'],timeout=12).decode()
 return sorted(set(re.findall(r'Hist\s+#\d+: ActivityRecord\{([a-f0-9]+) u10 ai\.teammoon\.pli/\.MainActivity t(\d+)\}',out)))
def remove_window():
 out=subprocess.check_output([str(ADB),'-s',serial,'shell','content','call','--user','10','--uri','content://ai.teammoon.pli.demo','--method','session','--arg','remove_window'],stderr=subprocess.STDOUT,timeout=12);assert b'Result:'in out and b'Exception'not in out
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=b.new_context(ignore_https_errors=True,permissions=['microphone']);v=c.new_page();summary=native('private-summary')
 def socket(w):
  if '/voice'not in w.url:return
  def received(data):
   if isinstance(data,bytes):
    a=array.array('h');a.frombytes(data);metrics['nonSilentOutput']+=sum(abs(x)>64 for x in a)
  w.on('framereceived',received)
 v.on('websocket',socket)
 def start():
  v.goto(URL+'/app');v.wait_for_function('state.status.controlReady && !state.status.lease.busy',timeout=90000);v.locator('#connect').click();v.wait_for_function("state.voice && state.status.app.capture==='ACTIVE' && state.status.app.recognition==='READY' && state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE'",timeout=45000)
 def stop():
  v.evaluate('endSession()');v.wait_for_function("!state.ending && !state.status.lease.busy && state.status.app.sessionStatus==='STOPPED'",timeout=20000)
 try:
  start();before=native();old_tasks=task_records();assert old_tasks;metrics['oldTasks']=old_tasks;start_at=time.monotonic();remove_window();lost=False;restored=False
  # AAOS may defer actual destruction for its 10s idle timeout after finish.
  # Observe the replacement, rather than assuming the finish ACK removed it.
  while time.monotonic()-start_at<25:
   s=native();entry={k:s.get(k)for k in ['epoch','capture','visible','hasView','serviceInstanceId']}
   if not metrics['transitions']or metrics['transitions'][-1]['state']!=entry:metrics['transitions'].append({'atSeconds':round(time.monotonic()-start_at,3),'state':entry})
   assert s['epoch']==before['epoch']and s['serviceInstanceId']==before['serviceInstanceId']and s['capture']=='ACTIVE','A lost public window changed the actual voice owner'
   if not s['visible']or not s['hasView']:lost=True
   else:
    current_tasks=task_records()
    if current_tasks and not(set(map(tuple,old_tasks))&set(map(tuple,current_tasks))):metrics['replacementTasks']=current_tasks;metrics['finishToNewViewSeconds']=round(time.monotonic()-start_at,3);restored=True;break
   time.sleep(.08)
  metrics['visibleGapObserved']=lost
  checks['actualTaskLossAndViewRecovery']=restored
  checks['sameEpochAndCaptureThroughoutRecovery']=True
  v.wait_for_function('state.voice && state.status.controlReady',timeout=12000);checks['browserVoiceConnectionRetained']=True
  v.wait_for_function("state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE' && state.status.app.recognition==='READY'",timeout=25000);v.evaluate('source.disconnect(filter)');before_audio=metrics['nonSilentOutput'];raw=base64.b64encode((ROOT/'qa/native/fixtures/math-primary.wav').read_bytes()).decode()
  v.evaluate('''async raw=>{const bytes=Uint8Array.from(atob(raw),c=>c.charCodeAt(0));const data=await ctx.decodeAudioData(bytes.buffer);const s=ctx.createBufferSource();s.buffer=data;s.connect(filter);s.start();await new Promise(r=>{s.onended=r});}''',raw);v.wait_for_function("state.status.app.game==='MATH'",timeout=20000)
  until=time.monotonic()+10
  while metrics['nonSilentOutput']-before_audio<10000 and time.monotonic()<until:v.wait_for_timeout(100)
  checks['realVoiceWorksAfterWindowReturns']=metrics['nonSilentOutput']-before_audio>=10000;stop()
  start();remove_window();stop();v.wait_for_timeout(11000);s=native();checks['endDuringRecoveryCannotReopenMicrophone']=s['sessionStatus']=='STOPPED'and s['capture']=='STOPPED'and not v.evaluate('state.status.lease.busy')
  checks['familyStorePreserved']=native('private-summary')==summary
 finally:
  try:stop()
  finally:b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
