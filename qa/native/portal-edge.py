"""Permission cancellation, actual denied permission, missing frames and API failure."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['appActualSnapshotFallback',
                             'cancelLeavesNoLease',
                             'denialLeavesNoLease',
                             'deniedPermissionExplained',
                             'initialFrameFailureActuallyInjected',
                             'lateClaimCancellationNeverPreparesNativeMicrophone',
                             'latePreparedResponseCannotBeginOrOverwriteConfirmedStop',
                             'noJsErrors',
                             'osControlNeedsNoMicrophone',
                             'pendingPermissionCancellationStopsTracks',
                             'permissionActuallyDenied',
                             'pleosActualSnapshotFallback',
                             'snapshotFallbackActuallyDelivered',
                             'statusFailureActuallyInjected',
                             'statusFailureBlocksControl',
                             'zeroFramesNeverClaimsLive'],
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
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'},
 'media': {'profile': 'public',
           'nativeRequired': True,
           'expectedChecks': ['productFilmDurationMatchesMetadata',
                              'aiFilmNeverClaimsCurrentApkFootage',
                              'liveSubscriptionReleasedDuringFilm',
                              'filmCopyMatchesDuration',
                              'filmEndHasExplicitReturn',
                              'filmReturnResumesActualNativePixels',
                              'filmNeedsNoMicrophoneOrLease',
                              'filmHasNoJavascriptErrors',
                              'watchingFilmReleasesOsControl'],
           'safetyChecks': {'watchingFilmReleasesOsControl': 'public-avd',
                            'filmNeedsNoMicrophoneOrLease': 'public-avd'},
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
                      'scripts/runtime_context.py',
                      'demo-v2/preview.mp4',
                      'demo-v2/preview-info.json'],
           'fixtures': [],
           'effects': 'mutate',
           'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
           'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json
from run_record import RunRecord
import argparse
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['full','media'],default='full');args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2];url=json.loads((ROOT/'.tools/public-config.json').read_text())['url'];checks={};metrics={};errors=[];record=RunRecord(__file__,checks,metrics)
if args.scope=='media':
 import hashlib
 with sync_playwright()as p:
  browser=p.chromium.launch(headless=True,channel='chrome');context=browser.new_context(viewport={'width':1440,'height':1000});context.add_init_script("window.qaMicRequests=0;const g=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=(...args)=>{qaMicRequests++;return g(...args)}")
  page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url+'/app');page.wait_for_function("state.media==='LIVE'&&state.previewInfo?.available",timeout=20000)
  page.locator('#watch').click();page.wait_for_function("state.media==='RECORDING'&&$('preview').currentTime>0",timeout=15000)
  checks['productFilmDurationMatchesMetadata']=page.evaluate("$('preview').duration>=30&&$('preview').duration<=60&&Math.abs($('preview').duration-state.previewInfo.durationSeconds)<.1")
  checks['aiFilmNeverClaimsCurrentApkFootage']=page.evaluate("$('recording-identity').textContent==='AI 제품 소개 영상'&&$('live-label').textContent==='플리 제품 소개 영상'&&!$('film-return').hidden&&state.previewInfo.actualAppFootage===false&&state.previewInfo.current===false")
  page.wait_for_timeout(1200);checks['liveSubscriptionReleasedDuringFilm']=page.evaluate("socket===null&&state.media==='RECORDING'")
  page.evaluate("async()=>{const v=$('preview');await new Promise(resolve=>{v.addEventListener('seeked',resolve,{once:true});v.currentTime=21;});await new Promise(resolve=>v.requestVideoFrameCallback(resolve));}");shot=record.dir/'product-film.png';page.screenshot(path=str(shot));metrics['screenshots']={str(shot.relative_to(ROOT)):hashlib.sha256(shot.read_bytes()).hexdigest()}
  checks['filmCopyMatchesDuration']=page.evaluate("$('prompt-detail').textContent.startsWith(Math.round($('preview').duration)+'초 ')")
  page.evaluate("$('preview').currentTime=Math.max(0,$('preview').duration-0.2)");page.wait_for_function("!$('recording-end').hidden",timeout=5000);checks['filmEndHasExplicitReturn']=page.locator('#end-return-live').is_visible()
  page.locator('#film-return').click();page.wait_for_function("state.media==='LIVE'",timeout=15000);checks['filmReturnResumesActualNativePixels']=page.evaluate("state.lastStamp.source==='app'&&state.media==='LIVE'")
  checks['filmNeedsNoMicrophoneOrLease']=page.evaluate('qaMicRequests===0&&!state.token&&!state.voice&&!state.status.lease.busy')
  page.goto(url+'/pleos');page.wait_for_function("state.media==='LIVE'&&state.status.controlReady&&!state.status.lease.busy&&state.previewInfo?.available",timeout=20000);page.locator('#claim-control').click();page.wait_for_function('owned()');page.locator('#watch').click();page.wait_for_function("state.media==='RECORDING'&&!state.token&&!state.status.lease.busy",timeout=20000);checks['watchingFilmReleasesOsControl']=page.evaluate('!state.token&&!state.status.lease.busy&&!state.voice&&qaMicRequests===0');page.locator('#film-return').click();page.wait_for_function("state.media==='LIVE'",timeout=15000)
  checks['filmHasNoJavascriptErrors']=not errors;metrics['pageErrors']=errors;browser.close()
 print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values());raise SystemExit(0)
def navigate(page,target):
 try:page.goto(target)
 except Exception as error:
  if 'ERR_CERT_VERIFIER_CHANGED'not in str(error):raise
  metrics.setdefault('navigationTransportRecoveries',[]).append({'error':'ERR_CERT_VERIFIER_CHANGED','retry':1});page.goto(target)
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']);c=b.new_context(permissions=['microphone']);v=c.new_page();v.on('pageerror',lambda e:errors.append(str(e)))
 navigate(v,url+'/app');v.wait_for_function("state.media==='LIVE'&&state.status.controlReady",timeout=20000)
 v.evaluate('''()=>{const get=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);window.qaGetMedia=get;window.qaTracks=[];navigator.mediaDevices.getUserMedia=async c=>{const s=await get(c);qaTracks=s.getTracks();await new Promise(r=>setTimeout(r,1500));return s;};}''')
 v.locator('#connect').click();v.wait_for_function('qaTracks.length>0');v.locator('#cancel-connect').click();v.wait_for_timeout(1800)
 checks['pendingPermissionCancellationStopsTracks']=v.evaluate("qaTracks.every(t=>t.readyState==='ended')&&!state.voice&&!state.connecting&&voiceSocket===null")
 checks['cancelLeavesNoLease']=v.evaluate('!state.status.lease.busy')
 v.evaluate("""()=>{navigator.mediaDevices.getUserMedia=async options=>{const stream=await qaGetMedia(options);qaTracks=stream.getTracks();return stream;};window.qaOriginalPost=post;window.qaPrepareCalls=0;post=async(...args)=>{if(args[0].endsWith('/prepare'))qaPrepareCalls++;const result=await qaOriginalPost(...args);if(args[0].endsWith('/claim'))await new Promise(resolve=>window.qaReleaseLateClaim=resolve);return result;};}""")
 v.locator('#connect').click();v.wait_for_function("typeof qaReleaseLateClaim==='function'");v.locator('#cancel-connect').click();v.evaluate('qaReleaseLateClaim()');v.wait_for_function('!state.status.lease.busy&&!state.token&&!state.connecting',timeout=20000)
 checks['lateClaimCancellationNeverPreparesNativeMicrophone']=v.evaluate("qaPrepareCalls===0&&qaTracks.every(track=>track.readyState==='ended')&&state.status.app.capture==='STOPPED'")
 v.evaluate("""()=>{post=async(...args)=>{if(args[0].endsWith('/begin'))window.qaBeginCalls=(window.qaBeginCalls||0)+1;const result=await qaOriginalPost(...args);if(args[0].endsWith('/prepare'))await new Promise(resolve=>window.qaReleasePrepared=resolve);return result;};}""")
 v.locator('#connect').click();v.wait_for_function("typeof qaReleasePrepared==='function'",timeout=35000);v.locator('#cancel-connect').click();v.wait_for_function('!state.ending&&!state.token&&!state.status.lease.busy',timeout=20000);v.evaluate('qaReleasePrepared()');v.wait_for_timeout(300)
 checks['latePreparedResponseCannotBeginOrOverwriteConfirmedStop']=v.evaluate("!window.qaBeginCalls&&!state.voice&&!state.connecting&&qaTracks.every(track=>track.readyState==='ended')&&state.status.app.capture==='STOPPED'&&state.status.app.sessionStatus==='STOPPED'");b.close()
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-device-for-media-stream']);c=b.new_context();v=c.new_page();v.on('pageerror',lambda e:errors.append(str(e)));navigate(v,url+'/app');v.wait_for_function("state.media==='LIVE'",timeout=15000)
 cdp=c.new_cdp_session(v);cid=cdp.send('Target.getTargetInfo')['targetInfo']['browserContextId'];cdp.send('Browser.setPermission',{'permission':{'name':'microphone'},'setting':'denied','origin':url,'browserContextId':cid})
 checks['permissionActuallyDenied']=v.evaluate("async()=> (await navigator.permissions.query({name:'microphone'})).state==='denied'")
 v.locator('#connect').click();v.wait_for_timeout(800);checks['deniedPermissionExplained']='허용'in v.locator('#voice-note').inner_text();checks['denialLeavesNoLease']=v.evaluate('!state.status.lease.busy&&mic===null&&ctx===null')
 # OS control remains available with an explicitly denied microphone.
 calls=[];v.evaluate("()=>{window.qaMicCalls=0;navigator.mediaDevices.getUserMedia=()=>{qaMicCalls++;throw Error('denied');};}");v.locator('nav a[href="/pleos"]').click();v.wait_for_function("state.media==='LIVE'&&state.surface==='pleos'");v.locator('#claim-control').click();v.wait_for_function('owned()');checks['osControlNeedsNoMicrophone']=v.evaluate("qaMicCalls===0&&state.status.app.capture==='STOPPED'&&!state.voice");v.locator('#disconnect').click();v.wait_for_function('!state.token&&!state.ending')
 # A real successful stream first, then fail the status producer. Pixels alone cannot keep controls live.
 hits=[];v.route('**/api/status',lambda r:(hits.append(1),r.fulfill(status=503,body='unavailable')));v.wait_for_timeout(5200);checks['statusFailureActuallyInjected']=len(hits)>=3;checks['statusFailureBlocksControl']=v.evaluate("state.media==='STALE'&&!$('picture-message').hidden&&$('claim-control').disabled")
 # A real WebSocket fault receipt before any decoded frame: cannot claim LIVE.
 c.close();c=b.new_context();v=c.new_page();faults=[];dropped=[]
 def no_video(ws):
  faults.append(ws.url);peer=ws.connect_to_server();peer.on_message(lambda message:dropped.append(1))
 v.route_web_socket('**/video?*',no_video);v.goto(url+'/pleos');v.wait_for_timeout(4200)
 checks['initialFrameFailureActuallyInjected']=len(faults)>0 and len(dropped)>0
 checks['zeroFramesNeverClaimsLive']=v.evaluate("state.lastFrame===0&&state.media==='STALE'&&!$('picture-message').hidden&&$('claim-control').disabled&&$('loading-spinner').hidden")
 metrics['initialVideoFaults']=len(faults);metrics['actualDroppedVideoMessages']=len(dropped)
 # Exercise the shipped JPEG compatibility route on both sources.
 c.close();c=b.new_context();c.add_init_script('window.MediaSource=undefined');v=c.new_page();hits=[]
 v.on('response',lambda r:hits.append(r.status)if '/snapshot?surface='in r.url else None)
 for surface in ['app','pleos']:
  v.goto(url+'/'+surface);v.wait_for_function("state.media==='LIVE'&&state.lastStamp?.sourceSeq>0",timeout=18000)
  checks[surface+'ActualSnapshotFallback']=v.evaluate("!$('screen').hidden&&$('screen').width>=640&&$('live-video').hidden")
 checks['snapshotFallbackActuallyDelivered']=200 in hits;metrics['snapshotResponses']=hits
 # Recorded playback has its own lifecycle, while status polling continues.
 checks['noJsErrors']=not errors;metrics.update(statusFailureHits=len(hits),pageErrors=errors);b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
