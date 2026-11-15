"""Guided portal: synthetic PCM -> browser worklet -> real APK ON_DEVICE STT.
No human microphone recording. Records only public demo APK frames and TTS.
"""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['audioDuplex',
                             'audioRestartsByExplicitAction',
                             'backToChildVoice',
                             'browserMicrophoneStopped',
                             'browserTracksReleasedBeforeNativeWait',
                             'closingOtherTabKeepsSession',
                             'desktopOverflow',
                             'driving32',
                             'english',
                             'hush',
                             'hushInterruptsSpeechWithoutGradingAnswer',
                             'mathIntent',
                             'mobileOverflow',
                             'mobileStartAboveFold',
                             'mute',
                             'nativeMicrophoneStopped',
                             'nativeOnlyCanvas',
                             'nativeStopWithin5Seconds',
                             'noPageErrors',
                             'parentGuidanceMatchesAudience',
                             'parentMenuVoice',
                             'parentPreparationVoice',
                             'parentReportVoice',
                             'privateBackupUntouchedInDemo',
                             'privateDocumentBlockedInDemo',
                             'resume',
                             'secondClientClaimRejected',
                             'secondTabCannotTakeControl',
                             'spokenAnswerScored',
                             'suspendedAudioExplained',
                             'warmRecognizerWithin5Seconds'],
          'safetyChecks': {'nativeMicrophoneStopped': 'public-avd',
                           'browserMicrophoneStopped': 'public-avd',
                           'privateBackupUntouchedInDemo': 'public-avd'},
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
          'fixtures': ['answer-six.wav',
                       'backup-save.wav',
                       'english-command.wav',
                       'hush.wav',
                       'math-primary.wav',
                       'parent-menu.wav',
                       'parent-prep.wav',
                       'parent-report.wav',
                       'read-private-plan.wav',
                       'resume.wav',
                       'silence.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import array,base64,json,time,os,hashlib
ROOT=Path(__file__).resolve().parents[2]
URL=os.environ.get('PLI_QA_URL',json.loads((ROOT/'.tools/public-config.json').read_text())['url'])
checks={};errors=[];metrics={'url':URL,'tlsCertificateVerified':not URL.startswith('https://127.'),'audioIn':0,'audioOut':0,'nonSilentOutput':0};states=[]
from run_record import RunRecord
run_record=RunRecord(__file__,checks,globals().get("metrics"))
from playwright.sync_api import sync_playwright
SHOT_DIR=run_record.dir/'screenshots';SHOT_DIR.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')])
 c=b.new_context(ignore_https_errors=URL.startswith('https://127.'),permissions=['microphone'],viewport={'width':1440,'height':1000},accept_downloads=True)
 v=c.new_page();v.on('pageerror',lambda e:errors.append(str(e)))
 def attach(w):
  if '/voice' not in w.url:return
  def recv(data):
   if isinstance(data,bytes):
    a=array.array('h');a.frombytes(data);metrics['audioOut']+=len(data);metrics['nonSilentOutput']+=sum(abs(x)>64 for x in a)
  def sent(data):
   if isinstance(data,bytes):
    metrics['audioIn']+=len(data);a=array.array('h');a.frombytes(data);metrics['nonSilentInput']=metrics.get('nonSilentInput',0)+sum(abs(x)>64 for x in a)
  w.on('framereceived',recv);w.on('framesent',sent)
 v.on('websocket',attach)
 v.goto(URL+'/app',wait_until='domcontentloaded');v.evaluate("window.qaDisconnects=[]");v.wait_for_function('state.status.controlReady',timeout=90000)
 claim_times=[];prepare_times=[]
 def claim_started(request):
  if request.url.split('?',1)[0].endswith('/api/session/claim')and not claim_times:claim_times.append(time.monotonic())
 def prepared(response):
  if response.url.split('?',1)[0].endswith('/api/session/prepare')and response.status==200 and response.json().get('status')=='PREPARED':prepare_times.append(time.monotonic())
 v.on('response',prepared);v.on('request',claim_started);t=time.monotonic();v.locator('#connect').click()
 v.wait_for_function("state.status.app.modelReady && state.status.app.capture==='ACTIVE'",timeout=45000)
 ready_at=time.monotonic();assert claim_times,'The real session-claim request was not observed'
 metrics['buttonToRecognizerReadySeconds']=round(ready_at-t,3);metrics['permissionAndBrowserSetupSeconds']=round(claim_times[0]-t,3);metrics['warmRecognizerReadySeconds']=round(ready_at-claim_times[0],3)
 metrics['claimToNativePreparedAckSeconds']=round(prepare_times[0]-claim_times[0],3)if prepare_times else None
 checks['warmRecognizerWithin5Seconds']=metrics['warmRecognizerReadySeconds']<=5
 try:v.wait_for_function('state.voice',timeout=45000)
 except Exception:
  print({'connectError':v.locator('#voice-note').inner_text(),'state':v.evaluate('state.status.app')},flush=True);raise
 metrics['startToVoiceSeconds']=round(time.monotonic()-t,3)
 v.evaluate('ctx.suspend()');v.wait_for_function("!$('resume-audio').hidden");checks['suspendedAudioExplained']=v.locator('#phase-label').inner_text()=='소리 연결 일시 정지';v.locator('#resume-audio').click();v.wait_for_function("ctx.state==='running'");checks['audioRestartsByExplicitAction']=True
 v.wait_for_function('!document.querySelector("#live-video").hidden && state.status.app.active && !state.status.app.quiet && state.status.app.phase==="LISTENING"',timeout=20000)
 v.wait_for_function("$('live-video').videoWidth>=640 && state.status.app.presentation && state.status.app.demo && state.status.app.visible",timeout=10000)
 metrics['initialCanvas']=v.evaluate("({width:$('live-video').videoWidth,height:$('live-video').videoHeight,presentation:state.status.app.presentation,demo:state.status.app.demo,visible:state.status.app.visible})")
 checks['nativeOnlyCanvas']=all(metrics['initialCanvas'].values())
 v.evaluate("post('/api/vehicle',{action:'drive'})");v.wait_for_function("state.status.app.gear==='D' && state.status.app.speedKmh===32",timeout=10000)
 checks['driving32']=v.evaluate("state.status.app.gear==='D' && state.status.app.speedKmh===32")
 checks['secondClientClaimRejected']=b.new_context(ignore_https_errors=URL.startswith('https://127.')).request.get(URL).ok
 second=b.new_context(ignore_https_errors=URL.startswith('https://127.'));second.request.get(URL)
 checks['secondClientClaimRejected']=second.request.post(URL+'/api/session/claim',headers={'Origin':URL},data='{}').status==423
 same=c.new_page();same.goto(URL+'/app',wait_until='domcontentloaded');same.wait_for_timeout(600)
 checks['secondTabCannotTakeControl']=c.request.post(URL+'/api/session/claim',headers={'Origin':URL},data='{}').status==423
 same.close();v.wait_for_timeout(700);checks['closingOtherTabKeepsSession']=v.evaluate('state.voice && state.status.lease.mine && state.status.voiceBusy')
 metrics['disconnectsBeforeFixtures']=v.evaluate('qaDisconnects');print('startup-state',json.dumps(metrics['disconnectsBeforeFixtures']),flush=True)
 v.evaluate('()=>source.disconnect(filter)')
 # When Pli is heard: non-silent reply audio reaching this page (the page's app state is a snapshot read every 1.1-1.6 s
 # under host load, which can skip a whole ~1 s reply; 2026-11-15)
 v.evaluate('''()=>{window.qaLastOutputAt=0;window.qaInputEnded=0;const socket=voiceSocket,receive=socket.onmessage;socket.onmessage=e=>{if(e.data instanceof ArrayBuffer){const a=new Int16Array(e.data);if(a.some(x=>Math.abs(x)>256))window.qaLastOutputAt=performance.now();}return receive.call(socket,e);};}''')
 def wait_listening():
  v.wait_for_function("state.status.app.recognition==='READY' && (state.status.app.quiet || (state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE' && state.status.app.recognition==='READY' && state.status.app.requestedText===state.status.app.speech))",timeout=30000);v.wait_for_timeout(500)
 def speak(name,predicate,interrupt=False):
  if interrupt:
   # Pli's reply audio is reaching the page right now (within 0.4 s); the stop checks below are unchanged
   v.wait_for_function("performance.now()-window.qaLastOutputAt<400",timeout=12000)
   metrics['hushInputStartedDuringPlayback']=v.evaluate("performance.now()-window.qaLastOutputAt<400")
   metrics['hushInputHostMonotonic']=time.monotonic()
  else:wait_listening()
  raw=base64.b64encode((ROOT/'qa/native/fixtures'/name).read_bytes()).decode()
  v.evaluate('''async b64=>{const raw=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const b=await ctx.decodeAudioData(raw.buffer);const s=ctx.createBufferSource();s.buffer=b;s.connect(filter);await new Promise(resolve=>{s.onended=resolve;s.start()});window.qaInputEnded=performance.now();}''',raw)
  try:v.wait_for_function(predicate,timeout=18000)
  except Exception:
   print(json.dumps({'failedFixture':name,'metrics':metrics,'app':v.evaluate('state.status.app'),'note':v.locator('#voice-note').inner_text()},ensure_ascii=False),flush=True)
   v.evaluate('endSession()');v.wait_for_timeout(3000);raise
  states.append(v.evaluate('state.status.app'))
  print('PASS',name,flush=True)
 speak('backup-save.wav',"state.status.app.title==='체험 기록은 저장하지 않아요.'");checks['privateBackupUntouchedInDemo']=True
 speak('math-primary.wav',"window.qaLastOutputAt>window.qaInputEnded")  # Pli answers (its ~1 s question is heard)
 speak('hush.wav','state.status.app.quiet',interrupt=True);checks['hush']=True
 v.wait_for_function("state.status.app.game==='MATH'",timeout=10000);checks['mathIntent']=True
 v.wait_for_function("state.status.app.playback==='IDLE'",timeout=5000);metrics['hushToStoppedSeconds']=round(time.monotonic()-metrics.pop('hushInputHostMonotonic'),3)
 checks['hushInterruptsSpeechWithoutGradingAnswer']=metrics['hushInputStartedDuringPlayback']and metrics['hushToStoppedSeconds']<6 and v.evaluate('state.status.app.answered===0')
 speak('resume.wav','!state.status.app.quiet');checks['resume']=True
 speak('answer-six.wav',"state.status.app.answered>=1");checks['spokenAnswerScored']=True
 v.screenshot(path=str(SHOT_DIR/'portal-math.png'),full_page=True)
 speak('english-command.wav',"state.status.app.game==='ENGLISH'");checks['english']=True
 speak('parent-prep.wav',"state.status.app.audience==='PARENT' && state.status.app.speech.includes('샘플')");checks['parentPreparationVoice']=True
 checks['parentGuidanceMatchesAudience']='준비물' in v.locator('#say-this').inner_text() and '알림장' in v.locator('#say-this').inner_text()
 v.screenshot(path=str(SHOT_DIR/'portal-parent.png'),full_page=True)
 v.locator('#live-video').screenshot(path=str(SHOT_DIR/'parent-native.png'))
 speak('parent-menu.wav',"state.status.app.audience==='PARENT' && state.status.app.speech.includes('식단표') && state.status.app.speech.includes('샘플')");checks['parentMenuVoice']=True
 speak('parent-report.wav',"state.status.app.audience==='PARENT' && state.status.app.speech.includes('알림장') && state.status.app.speech.includes('샘플')");checks['parentReportVoice']=True
 speak('math-primary.wav',"state.status.app.audience==='CHILD' && state.status.app.game==='MATH'");checks['backToChildVoice']=True
 checks['audioDuplex']=metrics['audioIn']>50000 and metrics['audioOut']>50000 and metrics['nonSilentOutput']>10000
 checks['desktopOverflow']=v.evaluate('document.documentElement.scrollWidth<=innerWidth')
 speak('read-private-plan.wav',"state.status.app.title==='샘플 일정으로 체험해요.'");checks['privateDocumentBlockedInDemo']=True
 v.locator('#mute').click();checks['mute']=v.evaluate('state.muted');v.locator('#mute').click()
 stopped_at=time.monotonic();v.locator('#disconnect').click();checks['browserTracksReleasedBeforeNativeWait']=v.evaluate('mic===null && ctx===null');v.wait_for_function('!state.ending && !state.status.voiceBusy',timeout=12000)
 metrics['endToNativeStoppedSeconds']=round(time.monotonic()-stopped_at,3);checks['nativeStopWithin5Seconds']=metrics['endToNativeStoppedSeconds']<=5
 v.wait_for_timeout(1700)
 checks['nativeMicrophoneStopped']=v.evaluate('!state.status.app.active && !state.status.app.modelReady')
 checks['browserMicrophoneStopped']=v.evaluate('mic===null && ctx===null && !state.voice')
 mobile=c.new_page();mobile.set_viewport_size({'width':390,'height':844});mobile.goto(URL+'/app',wait_until='domcontentloaded');mobile.wait_for_timeout(1300)
 checks['mobileOverflow']=mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
 checks['mobileStartAboveFold']=mobile.locator('#connect').bounding_box()['y']+mobile.locator('#connect').bounding_box()['height']<844
 mobile.screenshot(path=str(SHOT_DIR/'portal-mobile.png'),full_page=True)
 checks['noPageErrors']=not errors
 c.close();second.close();b.close()
metrics['screenshots']={str((SHOT_DIR/name).relative_to(ROOT)):hashlib.sha256((SHOT_DIR/name).read_bytes()).hexdigest()for name in ['portal-math.png','portal-parent.png','parent-native.png','portal-mobile.png']}
result={'passed':all(checks.values()),'url':URL,'checks':checks,'metrics':metrics,'states':states,'pageErrors':errors,'method':'Synthetic Korean WAV is decoded in Chrome and sent through the same 24kHz worklet/WebSocket/PulseAudio/emulator microphone path. Native state is read from the release APK; no text injection. TLS bypass only for private localhost. Public URL test uses normal certificate verification.'}
(ROOT/'qa/native/portal-journey.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));assert result['passed']
