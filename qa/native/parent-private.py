"""Private actual voice -> live MCP -> durable fact -> TTS. No family content artifact."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['actualMcpAnswerSpoken',
                             'liveQueryConsumed',
                             'privateNativeStopConfirmed',
                             'privateScheduleConsumer',
                             'privateVoiceRecognized',
                             'publicPrivateStateHidden',
                             'remoteToolReceipt',
                             'routeRestoredAfterNativeAck',
                             'weeklyRemoteWindowAndReadback'],
          'safetyChecks': {'publicPrivateStateHidden': 'public-service',
                           'privateNativeStopConfirmed': 'personal-avd',
                           'routeRestoredAfterNativeAck': 'personal-avd'},
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
                     'demo-v2/family.html',
                     'qa/native/fixtures/privacy-boundary.py',
                     'qa/native/fixtures/private-route.py',
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/kidsnote-bridge.py',
                     'scripts/kidsnote_mcp/site.mjs',
                     'scripts/kidsnote_mcp/sync.mjs',
                     'scripts/kidsnote_mcp/voice.mjs',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': ['menu-refresh-v4.wav',
                       'parent-prep.wav',
                       'weekly-refresh-clear.wav',
                       'weekly-refresh-v4.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['public-service', 'shared'],
                        ['personal-service', 'shared'],
                        ['personal-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,os,sys,time,subprocess,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'preparationPhrase':'엄마한테 오늘 준비물 알려줘 · 원래 입력과 부모 날짜 질문 fallback 반례 유지','liveQueryPhrase':'오늘 식단표 다시 확인해 주세요.','condition':'Explicit supported refresh phrase after the original latest/vegetarian ASR confusion; earlier failures retained; actual PCM and MCP, no text ingress'};record=RunRecord(__file__,checks,metrics,dependencies=['qa/native/fixtures/private-route.py'])
sys.path.insert(0,str(ROOT/'scripts'))
# Pulse is available in the service venv. Use that interpreter only for routing.
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8876'
def status():return json.load(urllib.request.urlopen(BASE+'/api/personal/status'))
def wait(predicate,seconds=25,after=None,reject_cached=False):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  s=status()
  if predicate(s):return s
  a=s.get('app',{})
  if after is not None and a.get('sessionStatus')in {'STOPPED','STOP_FAILED','UNKNOWN'}:
   metrics.setdefault('earlyTerminalResponses',[]).append({'kind':'SESSION_ENDED','elapsedSeconds':round(seconds-(end-time.monotonic()),3)})
   record.diagnostic(s,'parent-response-'+str(len(metrics['earlyTerminalResponses'])));raise AssertionError('The actual voice session ended before the expected response')
  if after is not None and a.get('spokenSequence',0)>after:
   intent_mismatch=a.get('audience')=='CHILD'and a.get('game')in {'MATH','ENGLISH','STORY','NATURE'}
   terminal=intent_mismatch or a.get('title')in {'다시 한번 말해 주세요.','확인하지 못한 내용을 만들지 않아요.'}or a.get('speech','').startswith('지금 새로 확인하지는 못했어요.')or reject_cached and a.get('speech','').startswith('저장된 일정과 준비물이에요.')
   if terminal:
    metrics.setdefault('earlyTerminalResponses',[]).append({'kind':'CACHED_CONTENT'if a.get('speech','').startswith('저장된')else'INTENT_MISMATCH'if intent_mismatch else'CLARIFICATION_OR_LOOKUP_FAILED','elapsedSeconds':round(seconds-(end-time.monotonic()),3)})
    record.diagnostic(s,'parent-response-'+str(len(metrics['earlyTerminalResponses'])));raise AssertionError('Actual response requires a new utterance; no timeout wait')
  time.sleep(.25)
 metrics['timeoutState']={k:s.get('app',{}).get(k)for k in ['sessionStatus','audience','modelReady','ttsReady','capture','recognition','phase','playback']}
 record.diagnostic(s,'parent-timeout')
 heard=s.get('app',{}).get('heard','');metrics['timeoutState'].update(heardLength=len(heard),heardIncludesMenu='식단'in heard,heardIncludesRefresh='최신'in heard,source=s.get('app',{}).get('answerSource'))
 raise AssertionError('Expected private session state was not observed')
# The app's spoken wording no longer names the family-app service ("키즈노트라는걸 표현하지마", 2026-11-14): '어린이집 …'.
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome');c=b.new_context();c.request.get(BASE)
 # Silence the owned guest microphone and output before private content is read.
 route=(ROOT/'qa/native/fixtures/private-route.py').read_text()
 try:
  subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',route],cwd=ROOT,check=True)
  wait(lambda s:s.get('app',{}).get('capture')=='ACTIVE'and s['app'].get('phase')=='LISTENING'and s['app'].get('recognition')=='READY'and s['app'].get('ttsReady')and s['app'].get('playback')=='IDLE'and bool(s['app'].get('speech'))and s['app'].get('requestedText')==s['app'].get('speech'),40);time.sleep(.5)
  adb=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial']
  def summary():return json.loads(subprocess.check_output([str(adb),'-s',serial,'exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/private-summary']))
  preparation_sequence=status()['app'].get('spokenSequence',0)
  subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(ROOT/'qa/native/fixtures/parent-prep.wav'),'-f','pulse','-device','pli_remote_mic','Pli parent preparation input'],check=True)
  prepared=wait(lambda s:(s['app'].get('speech','').startswith('저장된')or s['app'].get('speech','').startswith('어린이집에서 새로 확인하고 저장한')) and s['app'].get('playback')=='PLAYING',25)
  batch=json.loads((ROOT/'.tools/private/kidsnote/family.json').read_text())
  from datetime import datetime
  from zoneinfo import ZoneInfo
  today=str(datetime.now(ZoneInfo('Asia/Seoul')).date());plans=[x for x in batch['plans']if x['date']==today]
  checks['privateScheduleConsumer']=any(x['title']in prepared['app']['speech']for x in plans) if plans else '확인한 일정과 준비물 안내가 없어요' in prepared['app']['speech']
  wait(lambda s:s['app'].get('phase')=='LISTENING'and s['app'].get('recognition')=='READY'and s['app'].get('playback')=='IDLE',40)
  before=summary()['revision'];start=time.monotonic();menu_sequence=status()['app'].get('spokenSequence',0)
  subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(ROOT/'qa/native/fixtures/menu-refresh-v4.wav'),'-f','pulse','-device','pli_remote_mic','Pli private synthetic input'],check=True)
  metrics['menuRecognitionAttempts']=[]
  for attempt in range(2):
   try:
    s=wait(lambda s:s['app'].get('audience')=='PARENT'and ('어린이집 식단표'in s['app'].get('speech','')or'자료가 없어요'in s['app'].get('speech',''))and s['app'].get('playback')=='PLAYING',30,after=menu_sequence)
    metrics['menuRecognitionAttempts'].append({'attempt':attempt+1,'success':True});break
   except AssertionError:
    current=status()['app'];metrics['menuRecognitionAttempts'].append({'attempt':attempt+1,'success':False,'askedForRepetition':current.get('title')=='다시 한번 말해 주세요.'})
    if attempt or current.get('title')!='다시 한번 말해 주세요.'or current.get('sessionStatus')!='ACTIVE':raise
    wait(lambda s:s['app'].get('recognition')=='READY'and s['app'].get('playback')=='IDLE',20);time.sleep(.5)
    menu_sequence=status()['app'].get('spokenSequence',0)
    subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(ROOT/'qa/native/fixtures/menu-refresh-v4.wav'),'-f','pulse','-device','pli_remote_mic','Pli actual spoken repetition after clarification'],check=True)
  checks['privateVoiceRecognized']=s['app'].get('audience')=='PARENT'
  checks['actualMcpAnswerSpoken']=s['app']['answerSource']=='어린이집 소식 자료'and ('어린이집 식단표' in s['app']['speech'] or '자료가 없어요' in s['app']['speech'])
  privacy=json.loads(subprocess.check_output([str(ROOT/'.tools/demo-venv/bin/python'),str(ROOT/'qa/native/fixtures/privacy-boundary.py')],cwd=ROOT));assert all(privacy.values())
  checks['publicPrivateStateHidden']=privacy['public']and privacy['socket']and privacy['ownerPositive']
  checks['liveQueryConsumed']=summary()['revision']>before
  receipts=json.loads((ROOT/'.tools/private/kidsnote/query-receipts.json').read_text());latest=receipts[-1];checks['remoteToolReceipt']=latest['tool']=='get_voice_answer'and latest['topic']=='MENU'and latest['error']is None;metrics['actualQuery']={k:latest.get(k)for k in ['tool','topic','date','days','status','coverage']}
  metrics['voiceToAnswerSeconds']=round(time.monotonic()-start,3)
  wait(lambda s:s['app'].get('phase')=='LISTENING'and s['app'].get('recognition')=='READY'and s['app'].get('playback')=='IDLE'and s['app'].get('requestedText')==s['app'].get('speech'),45);time.sleep(.5)
  before_week=summary()['revision']
  metrics['weeklyRecognitionAttempts']=[]
  for attempt,phrase in enumerate(['weekly-refresh-v4.wav','weekly-refresh-clear.wav']):
   weekly_sequence=status()['app'].get('spokenSequence',0)
   subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(ROOT/'qa/native/fixtures'/phrase),'-f','pulse','-device','pli_remote_mic','Pli private weekly query'],check=True)
   try:
    weekly=wait(lambda s:s['app'].get('answerSource')=='어린이집 일정 새로 확인'and s['app'].get('playback')=='PLAYING'and s['app'].get('speech','').startswith('어린이집에서 새로 확인하고 저장한'),30,after=weekly_sequence,reject_cached=True)
    metrics['weeklyRecognitionAttempts'].append({'fixture':phrase,'success':True});break
   except AssertionError:
    current=status()['app'];metrics['weeklyRecognitionAttempts'].append({'fixture':phrase,'success':False,'answerSource':current.get('answerSource')})
    if attempt or current.get('sessionStatus')!='ACTIVE':raise
    wait(lambda s:s['app'].get('recognition')=='READY'and s['app'].get('playback')=='IDLE',25);time.sleep(.5)
  receipt=json.loads((ROOT/'.tools/private/kidsnote/query-receipts.json').read_text())[-1]
  from datetime import date,timedelta
  monday=date.today()-timedelta(days=date.today().weekday())
  checks['weeklyRemoteWindowAndReadback']=receipt['tool']=='get_sync_snapshot'and receipt['days']==7 and receipt['windowStart']==str(monday)and receipt['windowEnd']==str(monday+timedelta(days=6))and receipt['snapshotComplete']is True and summary()['revision']>before_week
  metrics['weeklyQuery']={k:receipt[k]for k in ['tool','date','days','windowStart','windowEnd','snapshotComplete']}

 finally:
  r=c.request.post(BASE+'/api/kidsnote/personal',headers={'Origin':BASE},data=json.dumps({'action':'stop'}));checks['privateNativeStopConfirmed']=r.status==200
  wait(lambda s:s['app'].get('sessionStatus')=='STOPPED'and s['app'].get('demo')is True,30)
  checks['routeRestoredAfterNativeAck']=not(ROOT/'.tools/demo-audio-state.json').exists()
  if checks['privateNativeStopConfirmed']and checks['routeRestoredAfterNativeAck']:record.confirm_cleanup()
 b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
