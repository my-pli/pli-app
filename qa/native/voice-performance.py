"""30 actual voice commands per fixed route; failures retained in the sample set."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['allSixActualHushInputsStopPlayback',
                             'allSixWarmStartsReadyWithin7Seconds',
                             'localAll30Commands',
                             'localP95Within3Seconds',
                             'publicAll30Commands',
                             'publicP95Within3Seconds',
                             'receivedHushPartialsStopWithin500ms'],
          'safetyChecks': {},
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
                     'qa/native/fixtures/utterances.json',
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': ['english-quiz.wav', 'hush.wav', 'math-primary.wav', 'resume.wav', 'silence.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'exclusive'],
                        ['public-service', 'shared'],
                        ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'},
 'startup': {'profile': 'public',
             'nativeRequired': True,
             'expectedChecks': ['allSixWarmStartsReadyWithin7Seconds'],
             'safetyChecks': {},
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
                        'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                        'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                        'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                        'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                        'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
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
                        'demo-v2/app.js',
                        'demo-v2/audio-worklet.js',
                        'demo-v2/index.html',
                        'demo-v2/style.css',
                        'qa/native/fixtures/utterances.json',
                        'scripts/audio_guard.py',
                        'scripts/demo-server.py',
                        'scripts/display_stream.py',
                        'scripts/portal_proxy.py',
                        'scripts/runtime_context.py'],
             'fixtures': ['silence.wav'],
             'effects': 'mutate',
             'resources': [['host-load', 'exclusive'],
                           ['public-service', 'shared'],
                           ['public-avd', 'exclusive']],
             'executionKind': 'NATIVE_E2E'},
 'response': {'profile': 'public',
              'nativeRequired': True,
              'expectedChecks': ['localAll30Commands',
                                 'localP95Within3Seconds',
                                 'publicAll30Commands',
                                 'publicP95Within3Seconds'],
              'safetyChecks': {},
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
                         'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                         'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                         'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                         'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                         'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
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
                         'demo-v2/app.js',
                         'demo-v2/audio-worklet.js',
                         'demo-v2/index.html',
                         'demo-v2/style.css',
                         'qa/native/fixtures/utterances.json',
                         'scripts/audio_guard.py',
                         'scripts/demo-server.py',
                         'scripts/display_stream.py',
                         'scripts/portal_proxy.py',
                         'scripts/runtime_context.py'],
              'fixtures': ['silence.wav', 'math-primary.wav', 'english-quiz.wav'],
              'effects': 'mutate',
              'resources': [['host-load', 'exclusive'],
                            ['public-service', 'shared'],
                            ['public-avd', 'exclusive']],
              'executionKind': 'NATIVE_E2E'},
 'interrupt': {'profile': 'public',
               'nativeRequired': True,
               'expectedChecks': ['allSixActualHushInputsStopPlayback',
                                  'receivedHushPartialsStopWithin500ms'],
               'safetyChecks': {},
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
                          'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                          'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                          'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                          'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                          'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
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
                          'demo-v2/app.js',
                          'demo-v2/audio-worklet.js',
                          'demo-v2/index.html',
                          'demo-v2/style.css',
                          'qa/native/fixtures/utterances.json',
                          'scripts/audio_guard.py',
                          'scripts/demo-server.py',
                          'scripts/display_stream.py',
                          'scripts/portal_proxy.py',
                          'scripts/runtime_context.py'],
               'fixtures': ['silence.wav', 'math-primary.wav', 'hush.wav', 'resume.wav'],
               'effects': 'mutate',
               'resources': [['host-load', 'exclusive'],
                             ['public-service', 'shared'],
                             ['public-avd', 'exclusive']],
               'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import base64,json,time,math,argparse
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['full','startup','response','interrupt'],default='full');args=parser.parse_args()
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'profiles':[],'startupFailures':[]};record=RunRecord(__file__,checks,metrics,fixtures=["silence.wav","math-primary.wav","english-quiz.wav","hush.wav","resume.wav"],dependencies=["qa/native/fixtures/utterances.json"])
import os
metrics['protocol']={'revision':1,'scope':args.scope,'hostLoadAtStart':list(os.getloadavg()),'sampling':'All planned observations, including failures and unattempted samples; no cross-protocol speedup claim'}
from playwright.sync_api import sync_playwright
profiles=[('local','https://127.0.0.1:9001'),('public',json.loads((ROOT/'.tools/public-config.json').read_text())['url'])]
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')])
 for label,url in profiles:
  profile={'route':label,'url':url,'commandProfile':'숫자 놀이 해 줘 / 영어 퀴즈 시작해 줘','scope':args.scope,'condition':'Recommended public UI phrases after the speech-UX change; fresh Chrome contexts on this host; actual TLS/network route; synthetic PCM, native ON_DEVICE; no text ingress; the earlier English-play profile failure is preserved separately','samples':[]};metrics['profiles'].append(profile)
  for batch in range(3):
   c=b.new_context(ignore_https_errors=label=='local',permissions=['microphone']);v=c.new_page();v.goto(url+'/app');v.wait_for_function('state.status.controlReady && !state.status.lease.busy',timeout=90000);claim=[];v.on('request',lambda r:claim.append(time.monotonic())if r.url.endswith('/api/session/claim')else None);v.locator('#connect').click()
   def ready():v.wait_for_function("state.status.app.recognition==='READY' && state.status.app.playback==='IDLE' && state.status.app.phase==='LISTENING' && state.status.app.speech===state.status.app.requestedText",timeout=35000)
   # Between samples: an edge-agent answer (a phrase that is not an app command) replaces `speech` without changing
   # `requestedText`, so equality never returns and one mis-heard sample used to fail every later sample of its batch
   # (2026-11-15). Listening and idle with nothing new spoken for 0.6 s is ready too; the mis-heard sample still fails.
   def settled():v.wait_for_function("(()=>{const a=state.status.app;const idle=a.recognition==='READY'&&a.playback==='IDLE'&&a.phase==='LISTENING';if(idle&&a.speech===a.requestedText)return true;const key=a.spokenSequence+'|'+a.speech;if(!idle||window.qaIdleKey!==key){window.qaIdleKey=key;window.qaIdleAt=performance.now();return false}return performance.now()-window.qaIdleAt>=600})()",polling=100,timeout=35000)
   try:
    v.wait_for_function('state.voice',timeout=45000)
    ready();profile.setdefault('warmQuestionReadySeconds',[]).append(round(time.monotonic()-claim[0],3));actual_backend=v.evaluate('state.status.app.backend');profile.setdefault('observedBackends',[]).append(actual_backend);assert 'ON_DEVICE'in actual_backend or '엣지 AI 음성인식'in actual_backend,'The fixed native SDK profile must not silently use the fallback recognizer';v.evaluate('source.disconnect(filter)')
    v.evaluate('''()=>{window.qaTiming=null;const send=voiceSocket.send.bind(voiceSocket);voiceSocket.send=data=>{if(qaTiming&&data instanceof ArrayBuffer){const a=new Int16Array(data);if(a.some(x=>Math.abs(x)>256))qaTiming.inputAt=performance.now();}return send(data);};const socket=voiceSocket,receive=socket.onmessage;socket.onmessage=e=>{if(qaTiming&&!qaTiming.outputAt&&qaTiming.inputAt>0&&e.data instanceof ArrayBuffer){const a=new Int16Array(e.data);if(a.some(x=>Math.abs(x)>256))qaTiming.outputAt=performance.now();}return receive.call(socket,e);};}''')
    for n in range(0 if args.scope=='startup'else 1 if args.scope=='interrupt'else 10):
     name,game=('math-primary.wav','MATH')if n%2==0 else('english-quiz.wav','ENGLISH');sample={'index':batch*10+n+1,'fixture':name,'success':False,'latencyMs':None};profile['samples'].append(sample)
     try:
      settled();v.wait_for_timeout(700);raw=base64.b64encode((ROOT/'qa/native/fixtures'/name).read_bytes()).decode()
      v.evaluate('''async b64=>{qaTiming={inputAt:0,outputAt:0,beforeSequence:state.status.app.spokenSequence};const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const buffer=await ctx.decodeAudioData(bytes.buffer);const s=ctx.createBufferSource();s.buffer=buffer;s.connect(filter);await new Promise(r=>{s.onended=r;s.start()});}''',raw)
      hush_here=n==0 and args.scope in {'full','interrupt'}
      if hush_here:
       # Inject the hush while Pli's reply is being heard: its audio reaching this page, not the app-state snapshot, which
       # is read every 1.1-1.6 s under host load and can miss a whole ~1 s reply (2026-11-15)
       v.wait_for_function("qaTiming.outputAt>qaTiming.inputAt && qaTiming.inputAt>0",timeout=12000)
       # the latency is read now: the hush's own input moves qaTiming.inputAt past this reply's first output
       measured=v.evaluate('({latencyMs:Math.round(qaTiming.outputAt-qaTiming.inputAt)})')
       began=time.monotonic();previous=v.evaluate('state.status.app.interruptPartialAtElapsed||0')
       def auxiliary(name):
        data=base64.b64encode((ROOT/'qa/native/fixtures'/name).read_bytes()).decode()
        v.evaluate('''async b64=>{const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const audio=await ctx.decodeAudioData(bytes.buffer);const input=ctx.createBufferSource();input.buffer=audio;input.connect(filter);await new Promise(r=>{input.onended=r;input.start()});}''',data)
       auxiliary('hush.wav')
       v.wait_for_function("expected=>state.status.app.game===expected && state.status.app.spokenSequence>qaTiming.beforeSequence",arg=game,timeout=12000)
       sample.update(measured);sample['heardLatest']=v.evaluate('state.status.app.heard');sample['success']=True
      else:
       v.wait_for_function("expected=>state.status.app.game===expected && state.status.app.spokenSequence>qaTiming.beforeSequence && qaTiming.outputAt>qaTiming.inputAt && qaTiming.inputAt>0",arg=game,timeout=12000)
       sample.update(v.evaluate('({latencyMs:Math.round(qaTiming.outputAt-qaTiming.inputAt),heard:state.status.app.heard})'));sample['success']=True
      if hush_here:
       v.wait_for_function("state.status.app.quiet&&state.status.app.playback==='IDLE'",timeout=12000)
       interrupted=v.evaluate('state.status.app');partial=interrupted.get('interruptPartialAtElapsed',0);stopped=interrupted.get('interruptStoppedAtElapsed',0)
       profile.setdefault('interruptSamples',[]).append({'fixture':'hush.wav','text':json.loads((ROOT/'qa/native/fixtures/utterances.json').read_text())['hush'],'inputStartToStopSeconds':round(time.monotonic()-began,3),'partialToConfirmedStopMs':stopped-partial if partial>previous and stopped>=partial else None})
       auxiliary('resume.wav');v.wait_for_function('!state.status.app.quiet',timeout=12000)
     except Exception as e:
      sample['failure']=type(e).__name__;sample['observed']=v.evaluate('({timing:qaTiming,game:state.status.app.game,phase:state.status.app.phase,recognition:state.status.app.recognition,playback:state.status.app.playback,heard:state.status.app.heard})');print(label,'FAIL',sample['index'],json.dumps(sample['observed'],ensure_ascii=False),flush=True)
      if not v.evaluate("state.voice && state.status.app.sessionStatus==='ACTIVE'"):break
      continue
     print(label,sample['index'],sample['latencyMs'],'ms',flush=True)
   except Exception as error:
    state=v.evaluate('state.status');app=state.get('app',{});failure={'route':label,'batch':batch+1,'exception':type(error).__name__,'runtime':state.get('runtime'),'process':state.get('process'),'appResponsive':state.get('appResponsive'),'nativeAgeMs':state.get('nativeStateAgeMs'),'app':{k:app.get(k)for k in ['bootId','sessionStatus','phase','capture','recognition','playback','focus','quiet','visible','hasView','appHeartbeatAgeMs','voiceHeartbeatAgeMs','error','spokenSequence','backend','modelReady','ttsReady']},'actualSpeechMatchesRequest':app.get('speech')==app.get('requestedText'),'speechLength':len(app.get('speech','')),'requestedLength':len(app.get('requestedText','')),'browserNote':v.locator('#voice-note').inner_text()};metrics['startupFailures'].append(failure);print('STARTUP FAILURE',json.dumps(failure,ensure_ascii=False),flush=True);raise
   finally:
    v.evaluate('endSession()');v.wait_for_function('!state.ending && !state.status.lease.busy && !state.status.voiceBusy',timeout=20000);c.close()
  # A missing sample remains a failure, not a faster subset.
  values=sorted(x['latencyMs']for x in profile['samples']if x['success']);planned=0 if args.scope=='startup'else 3 if args.scope=='interrupt'else 30;profile.update(totalPlanned=planned,attempted=len(profile['samples']),completed=len(profile['samples']),successful=len(values),failures=len(profile['samples'])-len(values),unattempted=planned-len(profile['samples']),p50Ms=values[len(values)//2]if values else None,p95Ms=values[math.ceil(len(values)*.95)-1]if values else None,maxMs=max(values)if values else None)
  if args.scope in {'full','response'}:checks[label+'All30Commands']=len(values)==30
  if args.scope in {'full','response'}:checks[label+'P95Within3Seconds']=len(values)==30 and profile['p95Ms']<=3000
 b.close()
warm=[value for profile in metrics['profiles']for value in profile.get('warmQuestionReadySeconds',[])]
interrupts=[sample for profile in metrics['profiles']for sample in profile.get('interruptSamples',[])]
if args.scope in {'full','startup'}:checks['allSixWarmStartsReadyWithin7Seconds']=len(warm)==6 and max(warm)<=7
if args.scope in {'full','interrupt'}:checks['allSixActualHushInputsStopPlayback']=len(interrupts)==6
received=[sample['partialToConfirmedStopMs']for sample in interrupts if sample['partialToConfirmedStopMs']is not None]
metrics['partialReceiptCoverage']={'received':len(received),'plannedHushInputs':6,'finalOnlyOrUnobserved':len(interrupts)-len(received)}
if args.scope in {'full','interrupt'}:checks['receivedHushPartialsStopWithin500ms']=bool(received)and all(0<=value<=500 for value in received)
print(json.dumps({'checks':checks,'metrics':metrics},ensure_ascii=False));assert all(checks.values())
