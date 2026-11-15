"""Source and depicted frames are separate measurements on the actual installed APK."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['LANInputEffectWithinTarget',
                             'LANTenActualOpticalEffects',
                             'actualGuestPointerUpReceived',
                             'appFirstFrameP95Within2s',
                             'appStayedLive',
                             'appUniqueDepictedAtLeast24Fps',
                             'fiveBrowserPointsReachGuestWithin2Pixels',
                             'limitedInputEffectWithinTarget',
                             'limitedTenActualOpticalEffects',
                             'pleosFirstFrameP95Within2s',
                             'pleosStayedLive',
                             'pleosUniqueDepictedAtLeast24Fps',
                             'staleGeometryRejected',
                             'videoDoesNotReconnectDuringActualInputs'],
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
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': [],
          'effects': 'mutate',
          'resources': [['host-load', 'exclusive'],
                        ['public-service', 'shared'],
                        ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'},
 'display': {'profile': 'public',
             'nativeRequired': True,
             'expectedChecks': ['appFirstFrameP95Within2s',
                                'appStayedLive',
                                'appUniqueDepictedAtLeast24Fps',
                                'pleosFirstFrameP95Within2s',
                                'pleosStayedLive',
                                'pleosUniqueDepictedAtLeast24Fps'],
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
                        'scripts/audio_guard.py',
                        'scripts/demo-server.py',
                        'scripts/display_stream.py',
                        'scripts/portal_proxy.py',
                        'scripts/runtime_context.py'],
             'fixtures': [],
             'effects': 'read',
             'resources': [('host-load', 'exclusive'),
                           ('public-service', 'shared'),
                           ('public-avd', 'shared')],
             'executionKind': 'NATIVE_E2E'},
 'pointer': {'profile': 'public',
             'nativeRequired': True,
             'expectedChecks': ['actualGuestPointerUpReceived',
                                'fiveBrowserPointsReachGuestWithin2Pixels',
                                'staleGeometryRejected'],
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
                        'scripts/audio_guard.py',
                        'scripts/demo-server.py',
                        'scripts/display_stream.py',
                        'scripts/portal_proxy.py',
                        'scripts/runtime_context.py'],
             'fixtures': [],
             'effects': 'mutate',
             'resources': [['host-load', 'exclusive'],
                           ['public-service', 'shared'],
                           ['public-avd', 'exclusive']],
             'executionKind': 'NATIVE_E2E'},
 'input': {'profile': 'public',
           'nativeRequired': True,
           'expectedChecks': ['LANInputEffectWithinTarget',
                              'LANTenActualOpticalEffects',
                              'limitedInputEffectWithinTarget',
                              'limitedTenActualOpticalEffects',
                              'videoDoesNotReconnectDuringActualInputs'],
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
                      'scripts/audio_guard.py',
                      'scripts/demo-server.py',
                      'scripts/display_stream.py',
                      'scripts/portal_proxy.py',
                      'scripts/runtime_context.py'],
           'fixtures': [],
           'effects': 'mutate',
           'resources': [['host-load', 'exclusive'],
                         ['public-service', 'shared'],
                         ['public-avd', 'exclusive']],
           'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,time,statistics,subprocess,tempfile,re,argparse
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['full','display','input','pointer'],default='full');args=parser.parse_args()
from run_record import RunRecord
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'surfaces':[],'concurrentQaScripts':[]}
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:cmd=(proc/'cmdline').read_bytes().split(b'\0')  # not `args`: that name holds the parsed options (args.scope below)
 except OSError:continue
 if len(cmd)>1 and b'qa/native/'in cmd[1]and not cmd[1].endswith(b'portal-performance.py')and not cmd[1].endswith(b'run-acceptance.py'):metrics['concurrentQaScripts'].append(Path(cmd[1].decode()).name)
record=RunRecord(__file__,checks,metrics)
import os
metrics['protocol']={'revision':1,'scope':args.scope,'hostLoadAtStart':list(os.getloadavg()),'sampling':'All planned observations, including failures and unattempted samples; no cross-protocol speedup claim'}
metrics['inputRequests']=[]
url='http://127.0.0.1:8878'
adb_config=ROOT/'.tools/android-sdk/platform-tools/adb';config_serial=json.loads((ROOT/'.tools/profiles/public/run-state.json').read_text())['serial'];metrics['windowAnimationScales']={k:subprocess.check_output([str(adb_config),'-s',config_serial,'shell','settings','get','global',k],timeout=5).decode().strip()for k in ['window_animation_scale','transition_animation_scale','animator_duration_scale']}
def p95(xs):return sorted(xs)[max(0,int(len(xs)*.95+.999)-1)]
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome');c=b.new_context(viewport={'width':1440,'height':1000});v=c.new_page()
 def input_response(response):
  if response.url.endswith('/api/input'):metrics['inputRequests'].append({'serverTiming':response.headers.get('server-timing'),'requestId':response.headers.get('x-pli-input-id'),'status':response.status})
 v.on('response',input_response)
 def video_events(ws):
  if '/video?'not in ws.url:return
  def message(value):
   if not isinstance(value,str):return
   data=json.loads(value)
   if data.get('type')in {'init','error'}:metrics.setdefault('videoEvents',[]).append({k:data.get(k)for k in ['type','code','generation','source']})
  ws.on('framereceived',message);ws.on('close',lambda:metrics.setdefault('videoEvents',[]).append({'type':'close'}))
 v.on('websocket',video_events)
 if args.scope in {'full','display'}:
  for surface in ['app','pleos']:
   first=[]
   for _ in range(5):
    start=time.monotonic();v.goto(url+'/'+surface);v.wait_for_function("state.media==='LIVE'",timeout=15000);first.append(round(time.monotonic()-start,3))
   v.evaluate('bias=>window.qaClockBiasValue=bias',(time.time()-time.monotonic())*1000)
   v.evaluate("""()=>{window.qaDepicted=[];window.qaSource=[];window.qaClockBias=window.qaClockBiasValue;const video=$('live-video');function next(now,info){qaDepicted.push({at:now,pts:info.mediaTime,ageMs:performance.timeOrigin+now-(state.lastStamp.captureMono*1000+qaClockBias)});qaSource.push(state.lastStamp?.sourceSeq);if(qaDepicted.length<600)video.requestVideoFrameCallback(next);}video.requestVideoFrameCallback(next);window.qaStart=performance.now();}""")
   before=v.evaluate("({frames:state.status.app.captureFrames,draw:state.status.app.drawMicros,producer:state.status.frameProducer?.frames})");v.wait_for_timeout(12000)
   result=v.evaluate("({frames:qaDepicted,sources:qaSource,seconds:(performance.now()-qaStart)/1000,stamp:state.lastStamp,after:{frames:state.status.app.captureFrames,draw:state.status.app.drawMicros,producer:state.status.frameProducer?.frames},media:state.media})")
   elapsed=result['seconds'];depicted=len(result['frames'])/elapsed;unique=len(set(result['sources']))/elapsed
   row={'surface':surface,'condition':'LAN, Chrome 1440x1000, warm emulator; 12 second real native animation / OS scene','firstFrameSeconds':first,'firstFrameP95Seconds':p95(first),'depictedFps':round(depicted,2),'uniqueSourceFps':round(unique,2),'sourceCounterDelta':(result['after']['producer']or 0)-(before['producer']or 0),'latestMainDrawMicros':result['after']['draw'],'media':result['media'],'captureToPaintP50Ms':round(statistics.median(x['ageMs']for x in result['frames']),1),'captureToPaintP95Ms':round(p95([x['ageMs']for x in result['frames']]),1)};metrics['surfaces'].append(row)
   checks[surface+'FirstFrameP95Within2s']=p95(first)<=2;checks[surface+'UniqueDepictedAtLeast24Fps']=unique>=24;checks[surface+'StayedLive']=result['media']=='LIVE'
 # Browser monotonic clock: actual OS key click -> changed video pixels.
 # Crop excludes the animated character and system clock; ACKs are not used.
 if args.scope!='display':
  v.goto(url+'/pleos');v.wait_for_function("state.media==='LIVE'&&state.status.controlReady&&!state.status.lease.busy",timeout=20000);v.locator('#claim-control').click();v.wait_for_function('owned()');v.wait_for_timeout(500)
 if args.scope in {'full','pointer'}:
  # Independent guest kernel input receipts; no server coordinate ACK as evidence.
  adb=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/profiles/public/run-state.json').read_text())['serial']
  v.evaluate("$('picture').style.aspectRatio='4 / 3';$('picture').style.transform='scale(.9)'");v.wait_for_timeout(300)
  points=[(.04,.12),(.96,.12),(.5,.5),(.04,.88),(.96,.88)];native_size=v.evaluate('({w:state.lastStamp.nativeWidth,h:state.lastStamp.nativeHeight})')
  with tempfile.TemporaryFile(mode='w+')as output:
   reader=subprocess.Popen([str(adb),'-s',serial,'shell','getevent','-lt','/dev/input/event2'],stdout=output,stderr=subprocess.STDOUT,text=True)
   try:
    v.wait_for_timeout(500)
    rect=v.locator('#live-video').bounding_box();v.mouse.click(rect['x']+20,rect['y']+5);v.wait_for_timeout(200)
    for x,y in points:
     rect=v.locator('#live-video').bounding_box();content_height=rect['width']*9/16;content_top=rect['y']+(rect['height']-content_height)/2;v.mouse.move(rect['x']+rect['width']*x,content_top+content_height*y);v.mouse.down();v.wait_for_timeout(100);v.mouse.up();v.wait_for_timeout(350)
    v.wait_for_timeout(400)
   finally:reader.terminate();reader.wait(timeout=5)
   output.seek(0);lines=output.read().splitlines()
  kernel=[];x=y=None;down=False;tracking=None;captured=False
  for line in lines:
   parts=line.split()
   if len(parts)<2:continue
   code,value=parts[-2:]
   if code=='ABS_MT_POSITION_X':x=int(value,16)
   elif code=='ABS_MT_POSITION_Y':y=int(value,16)
   elif code=='ABS_MT_TRACKING_ID':
    if value=='ffffffff':down=False
    else:down=True;tracking=value;captured=False
   elif code=='SYN_REPORT'and down and x is not None and y is not None:
    if not captured:kernel.append({'tracking':tracking,'x':x,'y':y});captured=True
  errors=[]
  for expected,actual in zip(points,kernel):
   errors.append(max(abs(actual['x']/32767*(native_size['w']-1)-round(expected[0]*(native_size['w']-1))),abs(actual['y']/32767*(native_size['h']-1)-round(expected[1]*(native_size['h']-1)))))
  metrics['kernelTouch']={'condition':'4:3 letterbox, CSS scale(.9), 5 content points plus one outside-letterbox click','device':'virtio_input_multi_touch_1 /dev/input/event2','nativeSize':native_size,'points':points,'receipts':kernel,'maxErrorNativePixels':max(errors)if errors else None,'lastTrackingReleased':not down,'rawEventCount':len(lines)}
  checks['fiveBrowserPointsReachGuestWithin2Pixels']=len(kernel)==5 and len(errors)==5 and max(errors)<=2
  checks['actualGuestPointerUpReceived']=not down and len(kernel)==5
  # A stale geometry cannot reach the guest producer.
  response=c.request.post(url+'/api/input',headers={'Origin':url,'X-Pli-Session':v.evaluate('state.token')},data=json.dumps({'type':'pointer','phase':'down','pointerId':2,'x':.5,'y':.5,'geometryRevision':-1,'streamGeneration':v.evaluate('state.lastStamp.generation'),'lastDepictedSourceSeq':v.evaluate('state.lastStamp.sourceSeq')}))
  checks['staleGeometryRejected']=response.status==409
  v.evaluate("$('picture').style.aspectRatio='';$('picture').style.transform=''");v.locator('#open-app').click();v.wait_for_timeout(500)
  input_video_inits=sum(x.get('type')=='init'for x in metrics.get('videoEvents',[]))
 if args.scope in {'full','input'}:
  cdp=c.new_cdp_session(v)
  try:
   for label,latency,down,up,target in [('LAN',0,-1,-1,350),('limited',80,625000,125000,600)]:
    cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':latency,'downloadThroughput':down,'uploadThroughput':up});v.wait_for_timeout(1000);samples=[]
    for number in range(10):
     v.wait_for_timeout(650)
     v.evaluate("""()=>{const video=$('live-video'),can=document.createElement('canvas');can.width=96;can.height=24;const ctx2=can.getContext('2d',{willReadFrequently:true});const pixels=()=>{ctx2.drawImage(video,video.videoWidth*.4,video.videoHeight*.08,video.videoWidth*.55,video.videoHeight*.16,0,0,96,24);return ctx2.getImageData(0,0,96,24).data;};window.qaOptical={at:0,ms:null,maxDifference:0,frames:[]};const reference=pixels();document.addEventListener('click',function click(e){if(!e.target.closest('[data-key],#open-app'))return;document.removeEventListener('click',click,true);qaOptical.at=performance.now();const until=qaOptical.at+2500;function frame(now){if(!qaOptical.at)return;const current=pixels();let delta=0;for(let i=0;i<current.length;i+=4)delta+=Math.abs(current[i]-reference[i])+Math.abs(current[i+1]-reference[i+1])+Math.abs(current[i+2]-reference[i+2]);delta/=96*24*3;qaOptical.maxDifference=Math.max(qaOptical.maxDifference,delta);if(qaOptical.frames.length<80)qaOptical.frames.push({at:performance.now()-qaOptical.at,pts:video.currentTime,bufferEnd:video.buffered.length?video.buffered.end(video.buffered.length-1):null,sourceSeq:state.lastStamp?.sourceSeq,encodedBytes:state.lastStamp?.encodedBytes,media:state.media});if(delta>15){qaOptical.ms=performance.now()-qaOptical.at;return;}if(performance.now()<until)video.requestVideoFrameCallback(frame);}video.requestVideoFrameCallback(frame);},true);}""")
     key='recent'if number%2==0 else'open_app';v.locator('[data-key=recent]'if key=='recent'else'#open-app').click();v.wait_for_function('qaOptical.ms!==null||performance.now()-qaOptical.at>2600',timeout=4000);sample=v.evaluate('qaOptical');sample['key']=key;samples.append(sample)
    valid=[x['ms']for x in samples if x['ms']is not None];row={'condition':label,'method':'Actual browser click event -> first video ROI RGB mean change >15; top-right app header, excludes character; ACK excluded','samples':samples,'p95Ms':round(p95(valid),1)if valid else None};metrics.setdefault('inputEffect',[]).append(row)
    checks[label+'TenActualOpticalEffects']=len(valid)==10
    checks[label+'InputEffectWithinTarget']=len(valid)==10 and p95(valid)<=target
   checks['videoDoesNotReconnectDuringActualInputs']=sum(x.get('type')=='init'for x in metrics.get('videoEvents',[]))==input_video_inits
  finally:
   cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1});v.locator('#open-app').click();v.locator('#disconnect').click();v.wait_for_function('!state.token&&!state.ending',timeout=15000)
 elif args.scope!='display':
  v.locator('#disconnect').click();v.wait_for_function('!state.token&&!state.ending',timeout=15000)
 b.close()
metrics['hostInputTimings']=json.load(__import__('urllib.request',fromlist=['urlopen']).urlopen(url+'/api/status')).get('inputTimings',[])
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
