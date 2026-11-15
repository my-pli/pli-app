"""Original presentation features through real browser PCM / Pleos speech SDK."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['abacusHintVoice',
                             'arrivalRecordsTrip',
                             'audibleSdkOutput',
                             'chargingPlayVoice',
                             'childAsksEnglish',
                             'confirmedPlacePromptMovesToNextAction',
                             'destinationChoiceVoice',
                             'destinationOptionsVoice',
                             'englishDialogueStarted',
                             'growthReadsActualTrip',
                             'idleMainProcessRestartPreservesFamily',
                             'mathVoice',
                             'natureVoice',
                             'publicCannotChangeRealRoute',
                             'recommendedNextActionActuallyCompletes',
                             'roleSwapVoice',
                             'selectedPlacePromptRequestsGuardian',
                             'stage1Completed',
                             'stage2Completed',
                             'stage3Completed',
                             'stage4Completed',
                             'storyNoteVoice',
                             'storyVoiceWhileDriving',
                             'threeEnglishDialogueTurnsSpokenAndAnswered'],
          'safetyChecks': {'idleMainProcessRestartPreservesFamily': 'public-avd',
                           'publicCannotChangeRealRoute': 'public-avd'},
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
          'fixtures': ['abacus-hint.wav',
                       'arrive.wav',
                       'bye-english.wav',
                       'charging-play.wav',
                       'destination-confirm-primary.wav',
                       'destination-options.wav',
                       'destination-ordinal.wav',
                       'destination-second.wav',
                       'english-dialogue-clear.wav',
                       'english-dialogue-v4.wav',
                       'growth-records.wav',
                       'happy-v4.wav',
                       'hello-v4.wav',
                       'math-primary.wav',
                       'nature-start.wav',
                       'next-question.wav',
                       'parent-prep.wav',
                       'role-swap.wav',
                       'silence.wav',
                       'story-note.wav',
                       'story-start.wav',
                       'word-tree.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import array,base64,json,time,os,hashlib,subprocess,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'utterances':[],'recognitionRecoveries':[],'nonSilentOutput':0,'englishFarewellProfile':'Bye bye, native English Piper voice; original Korean-voice acoustic failures retained'};record=RunRecord(__file__,checks,metrics)
from playwright.sync_api import sync_playwright
SHOT_DIR=record.dir/'screenshots';SHOT_DIR.mkdir(exist_ok=True)
URL=os.environ.get('PLI_QA_URL','https://127.0.0.1:9000')
# Exercise the formerly failing first preparation after a new idle main process.
adb=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/profiles/public/run-state.json').read_text())['serial']
def native_read(path='state'):
 return json.loads(subprocess.check_output([str(adb),'-s',serial,'exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path],timeout=8))
until=time.monotonic()+45
while True:
 status=json.load(urllib.request.urlopen('http://127.0.0.1:8878/api/status'));current=native_read()
 if not status['lease']['busy']and not status['voiceBusy']and current['sessionStatus']=='STOPPED'and current['capture']=='STOPPED':break
 assert time.monotonic()<until,'Cannot restart an owned or unconfirmed voice session'
 time.sleep(.2)
summary=native_read('private-summary');old_boot=current['bootId']
subprocess.run([str(adb),'-s',serial,'shell','am','force-stop','--user','10','ai.teammoon.pli'],check=True)
subprocess.run([str(adb),'-s',serial,'shell','am','start','--user','10','-n','ai.teammoon.pli/.MainActivity'],check=True,capture_output=True)
until=time.monotonic()+20
while True:
 current=native_read()
 if current['bootId']!=old_boot and current['visible']and current['hasView']and current['sessionStatus']=='STOPPED':break
 assert time.monotonic()<until,'Restarted actual main View unavailable'
 time.sleep(.2)
checks['idleMainProcessRestartPreservesFamily']=native_read('private-summary')==summary
metrics['preparationAfterNewMainProcess']={'receiptAbsent':current.get('stopReceipt')is None,'sessionStatus':current['sessionStatus'],'capture':current['capture']}
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')])
 c=b.new_context(ignore_https_errors=URL.startswith('https://127.'),permissions=['microphone'],viewport={'width':1440,'height':1000});v=c.new_page()
 def socket(w):
  if '/voice'not in w.url:return
  def received(data):
   if isinstance(data,bytes):
    a=array.array('h');a.frombytes(data);metrics['nonSilentOutput']+=sum(abs(x)>64 for x in a)
  w.on('framereceived',received)
 v.on('websocket',socket)
 def start():
  v.goto(URL+'/app');v.wait_for_function('state.status.controlReady && !state.status.lease.busy',timeout=90000);v.locator('#connect').click()
  try:v.wait_for_function('state.voice',timeout=45000);ready()
  except Exception:
   failed=v.evaluate('state.status.app');metrics['startupFailure']={k:failed.get(k)for k in ['sessionStatus','phase','capture','recognition','playback','modelReady','ttsReady','error','bootId']};metrics['startupBrowserNote']=v.locator('#voice-note').inner_text();raise
  v.evaluate('source.disconnect(filter)')
 def ready():v.wait_for_function("state.status.app.recognition==='READY' && state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE' && state.status.app.requestedText===state.status.app.speech",timeout=35000)
 def speak(name,predicate,rephrase=None,attempt=1):
  ready();v.wait_for_timeout(450);raw=base64.b64encode((ROOT/'qa/native/fixtures'/name).read_bytes()).decode();at=time.monotonic();before=v.evaluate('state.status.app.spokenSequence')
  v.evaluate('''async b64=>{const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const audio=await ctx.decodeAudioData(bytes.buffer);const s=ctx.createBufferSource();s.buffer=audio;s.connect(filter);await new Promise(r=>{s.onended=r;s.start()});}''',raw)
  try:v.wait_for_function(f"({predicate}) || (state.status.app.spokenSequence>{before} && state.status.app.title==='다시 한번 말해 주세요.')",timeout=20000)
  except Exception:
   failed=v.evaluate('state.status.app');metrics['utterances'].append({'fixture':name,'success':False,'elapsedSeconds':round(time.monotonic()-at,3),'heard':failed.get('heard'),'failure':'EXPECTED_RESULT_NOT_OBSERVED'});print(json.dumps({'failed':name,'state':failed},ensure_ascii=False),flush=True);raise
  s=v.evaluate('state.status.app');ok=bool(v.evaluate(predicate));metrics['utterances'].append({'fixture':name,'attempt':attempt,'success':ok,'elapsedSeconds':round(time.monotonic()-at,3),'game':s['game'],'panel':s['panel'],'heard':s['heard']})
  if not ok:
   assert attempt<2 and s['title']=='다시 한번 말해 주세요.','Two real spoken attempts did not complete the task'
   next_phrase=rephrase or name;metrics['recognitionRecoveries'].append({'from':name,'to':next_phrase});print('UNRECOGNIZED; actual spoken retry',name,'->',next_phrase,flush=True);return speak(next_phrase,predicate,attempt=2)
  print('PASS',name,flush=True)
 def stop():
  if v.evaluate('state.voice'):v.evaluate('endSession()')
  v.wait_for_function('!state.ending && !state.status.lease.busy && !state.status.voiceBusy',timeout=20000)
 try:
  if os.environ.get("PLI_QA_STAGE","all") in {"all","4"}:
   try:
    start();speak('english-dialogue-v4.wav',"state.status.app.question && state.status.app.question.includes('Hello')",rephrase='english-dialogue-clear.wav');checks['englishDialogueStarted']=True
    for answer,next_prompt in [('hello-v4.wav','How are you'),('happy-v4.wav','See you')]:
     before=v.evaluate('state.status.app.correct');speak(answer,f"state.status.app.correct==={before+1}");speak('next-question.wav',f"state.status.app.question && state.status.app.question.includes('{next_prompt}')")
    before=v.evaluate('state.status.app.correct');speak('bye-english.wav',f"state.status.app.correct==={before+1}");checks['threeEnglishDialogueTurnsSpokenAndAnswered']=True;stop()
   except Exception as error:
    metrics.setdefault('stageFailures',[]).append({'stage':4,'error':type(error).__name__});checks['stage4Completed']=False
    stop()
   else:checks['stage4Completed']=True
  if os.environ.get("PLI_QA_STAGE","all") in {"all","1"}:
   try:
    start();v.evaluate("post('/api/vehicle',{action:'park'})");v.wait_for_function("state.status.app.gear==='P'",timeout=10000)
    speak('math-primary.wav',"state.status.app.game==='MATH'");checks['mathVoice']=True
    speak('abacus-hint.wav',"state.status.app.abacusHint && state.status.app.speech.includes('딸깍')");checks['abacusHintVoice']=True
    ready();v.locator('#live-video').screenshot(path=str(SHOT_DIR/'abacus-native.png'))
    speak('nature-start.wav',"state.status.app.game==='NATURE' && state.status.app.question.includes('도토리')");checks['natureVoice']=True
    speak('role-swap.wav',"state.status.app.panel==='ENGLISH_TURN'");checks['roleSwapVoice']=True
    speak('word-tree.wav',"state.status.app.panel==='ENGLISH_TURN' && state.status.app.speech.includes('tree')");checks['childAsksEnglish']=True
    stop()
   except Exception as error:
    metrics.setdefault('stageFailures',[]).append({'stage':1,'error':type(error).__name__});checks['stage1Completed']=False
    stop()
   else:checks['stage1Completed']=True
  if os.environ.get("PLI_QA_STAGE","all") in {"all","2"}:
   try:
    start();v.evaluate("post('/api/vehicle',{action:'drive'})");v.wait_for_function("state.status.app.gear==='D' && state.status.app.speedKmh===32",timeout=10000)
    speak('story-start.wav',"state.status.app.game==='STORY'");checks['storyVoiceWhileDriving']=True
    speak('story-note.wav',"state.status.app.game==='STORY' && state.status.app.heard.includes('도토리')");checks['storyNoteVoice']=True
    before=v.evaluate('state.status.app.memoryCount')
    speak('arrive.wav',f"state.status.app.memoryCount==={before+1}");checks['arrivalRecordsTrip']=True
    speak('growth-records.wav',"state.status.app.panel==='GROWTH' && state.status.app.speech.includes('스탬프 1개')");checks['growthReadsActualTrip']=True
    v.evaluate("post('/api/vehicle',{action:'park'})");v.wait_for_function("state.status.app.gear==='P'",timeout=10000);ready();v.locator('#live-video').screenshot(path=str(SHOT_DIR/'growth-native.png'));stop()
   except Exception as error:
    metrics.setdefault('stageFailures',[]).append({'stage':2,'error':type(error).__name__});checks['stage2Completed']=False
    stop()
   else:checks['stage2Completed']=True
  if os.environ.get("PLI_QA_STAGE","all") in {"all","3"}:
   try:
    start();v.evaluate("post('/api/vehicle',{action:'park'})");v.wait_for_function("state.status.app.gear==='P'",timeout=10000)
    speak('charging-play.wav',"state.status.app.panel==='CHARGE' && state.status.app.game==='MATH'");checks['chargingPlayVoice']=True
    ready();v.locator('#live-video').screenshot(path=str(SHOT_DIR/'charging-native.png'))
    speak('destination-options.wav',"state.status.app.panel==='DESTINATIONS'");checks['destinationOptionsVoice']=True
    speak('destination-second.wav',"state.status.app.panel==='DESTINATIONS' && state.status.app.title.includes('확인')",rephrase='destination-ordinal.wav');checks['destinationChoiceVoice']=True
    checks['selectedPlacePromptRequestsGuardian']=v.locator('#say-this').inner_text()=='“보호자 확인”'
    speak('destination-confirm-primary.wav',"state.status.app.speech.includes('체험') && state.status.app.routeStatus==='IDLE'");checks['publicCannotChangeRealRoute']=True
    v.wait_for_function("state.status.app.title==='샘플 목적지 확인을 마쳤어요.' && document.querySelector('#say-this').textContent.includes('오늘 준비물')");checks['confirmedPlacePromptMovesToNextAction']=True
    speak('parent-prep.wav',"state.status.app.audience==='PARENT' && state.status.app.speech.includes('샘플')");checks['recommendedNextActionActuallyCompletes']=True
    ready();v.locator('#live-video').screenshot(path=str(SHOT_DIR/'destinations-native.png'));stop()
   except Exception as error:
    metrics.setdefault('stageFailures',[]).append({'stage':3,'error':type(error).__name__});checks['stage3Completed']=False
    stop()
   else:checks['stage3Completed']=True
  checks['audibleSdkOutput']=metrics['nonSilentOutput']>10000
 finally:
  try:stop()
  finally:b.close()
metrics['screenshots']={str((SHOT_DIR/name).relative_to(ROOT)):hashlib.sha256((SHOT_DIR/name).read_bytes()).hexdigest()for name in ['abacus-native.png','growth-native.png','charging-native.png','destinations-native.png']if(SHOT_DIR/name).exists()}
print(json.dumps({'checks':checks,'metrics':metrics},ensure_ascii=False));assert all(checks.values())
