"""Mute the real bridge monitor; a short SDK reply must fail closed despite onDone."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['microphoneActuallyStopped',
                             'realSdkShortReplyStarted',
                             'silentReplyStopsAndReleasesLease'],
          'safetyChecks': {'microphoneActuallyStopped': 'public-avd'},
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
import base64,json,subprocess,time
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics);URL='https://127.0.0.1:9001'
from playwright.sync_api import sync_playwright
def mute(value):
 code="import pulsectl; p=pulsectl.Pulse('pli-silent-output-test'); s=next(x for x in p.source_list()if x.name=='pli_remote_speaker_public.monitor');p.source_mute(s.index,"+str(value)+");print(p.source_info(s.index).mute);p.close()"
 result=subprocess.check_output([str(ROOT/'.tools/demo-venv/bin/python'),'-c',code],cwd=ROOT).decode().strip();assert result==('1'if value else'0')
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=b.new_context(ignore_https_errors=True,permissions=['microphone']);v=c.new_page();v.goto(URL+'/app');v.wait_for_function('state.status.controlReady && !state.status.lease.busy',timeout=90000);v.locator('#connect').click();v.wait_for_function("state.voice && state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE' && state.status.app.recognition==='READY'",timeout=45000)
 try:
  v.evaluate('source.disconnect(filter)');mute(True);start=time.monotonic();raw=base64.b64encode((ROOT/'qa/native/fixtures/math-primary.wav').read_bytes()).decode()
  v.evaluate('''async raw=>{const bytes=Uint8Array.from(atob(raw),c=>c.charCodeAt(0));const data=await ctx.decodeAudioData(bytes.buffer);const s=ctx.createBufferSource();s.buffer=data;s.connect(filter);s.start();}''',raw)
  v.wait_for_function("state.status.app.game==='MATH' && state.status.app.spokenSequence>=2",timeout=18000);checks['realSdkShortReplyStarted']=True
  v.wait_for_function("state.status.app.sessionStatus==='STOPPED' && !state.status.voiceBusy && !state.status.lease.busy",timeout=16000);checks['silentReplyStopsAndReleasesLease']=True
  metrics['inputStartToConfirmedStopSeconds']=round(time.monotonic()-start,3)
  checks['microphoneActuallyStopped']=v.evaluate("state.status.app.capture==='STOPPED' && state.status.app.stopReceipt.captureStopped && state.status.app.stopReceipt.playbackStopped")
 finally:
  mute(False)
  try:v.evaluate('endSession()');v.wait_for_function('!state.status.lease.busy',timeout=15000)
  finally:b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
