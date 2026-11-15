"""Owner candidate receipts and real private voice -> NaviHelper; restore family candidates."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['allTwelveCandidatesReachTheirSpokenPage',
                             'familyDataAndOriginalCandidatesRestored',
                             'guardianRequiredBeforeAnyRequest',
                             'invalidSchemaRejectedBeforeNativeWrite',
                             'ownerCandidatesCommittedAndReadBack',
                             'privateNativeStopConfirmed',
                             'privateSpokenCandidateSelected',
                             'requestHasBoundedTerminalState',
                             'routeRestoredAfterNativeAck',
                             'sdkActuallyConfirmedCancellation',
                             'sdkActuallyConfirmedGuidance'],
          'safetyChecks': {'familyDataAndOriginalCandidatesRestored': 'personal-avd',
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
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': ['destination-confirm-clear.wav',
                       'destination-confirm-primary.wav',
                       'destination-options-private.wav',
                       'destination-page-clear.wav',
                       'destination-twelfth-clear.wav',
                       'destination-twelfth.wav',
                       'next-question.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['personal-service', 'shared'],
                        ['personal-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,subprocess,time,urllib.request,os,sys,re
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics,claims={'candidate-list':['ownerCandidatesCommittedAndReadBack','allTwelveCandidatesReachTheirSpokenPage','privateSpokenCandidateSelected','guardianRequiredBeforeAnyRequest','familyDataAndOriginalCandidatesRestored','privateNativeStopConfirmed','routeRestoredAfterNativeAck'],'guidance':['sdkActuallyConfirmedGuidance','sdkActuallyConfirmedCancellation','familyDataAndOriginalCandidatesRestored','privateNativeStopConfirmed','routeRestoredAfterNativeAck']});BASE='http://127.0.0.1:8876';ADB=ROOT/'.tools/android-sdk/platform-tools/adb'
from playwright.sync_api import sync_playwright
def adb(*args):return subprocess.check_output([str(ADB),'-s',json.loads((ROOT/'.tools/run-state.json').read_text())['serial'],*args],stderr=subprocess.DEVNULL,timeout=15)
def read(path='state'):return json.loads(adb('exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path))
def wait(predicate,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  s=read()
  if predicate(s):return s
  time.sleep(.2)
 record.diagnostic(s,'navigation-timeout')
 metrics['lastObserved']={k:s.get(k)for k in ['sessionStatus','phase','capture','recognition','playback','panel','routeStatus']}
 raise AssertionError('Private navigation condition not observed; family text omitted')
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome');c=b.new_context();c.request.get(BASE);headers={'Origin':BASE,'Content-Type':'application/json'};original=c.request.get(BASE+'/api/family/destinations').json();summary=read('private-summary');assert not original.get('currentDestination'),'An existing navigation route must not be replaced by QA'
 pending=ROOT/'.tools/private/navigation-original.json'
 assert not pending.exists(),'A previous navigation QA original must be restored from the private backup before another mutation'
 pending.write_text(json.dumps({'runId':record.id,'original':original,'summary':summary},ensure_ascii=False));pending.chmod(0o600)
 choices=[{'id':'qa:navigation-'+str(n),'name':'시연 장소 '+str(n),'latitude':37.48544722 if n<12 else 37.5665,'longitude':127.03636666 if n<12 else 126.9780,'address':''}for n in range(1,13)]
 def store(values):
  current=c.request.get(BASE+'/api/family/destinations').json();r=c.request.post(BASE+'/api/family/destinations',headers=headers,data=json.dumps({'revision':current['revision'],'destinations':values}));assert r.status==200, f'Candidate receipt HTTP {r.status}: {r.text()[:160]}';result=r.json();assert result['destinations']==values and result['receipt']['committed'];return result
 try:
  if '--seoul-gps'in sys.argv:
   ack=adb('emu','geo','fix','127.03636666','37.48544722');assert b'OK'in ack
   metrics['emulatorOrigin']={'latitude':37.48544722,'longitude':127.03636666,'synthetic':True,'consoleAcknowledged':True}
  store(choices);checks['ownerCandidatesCommittedAndReadBack']=True
  for invalid in [[],{'revision':summary['revision'],'destinations':[{'name':None,'latitude':37.5,'longitude':127}]},{'revision':summary['revision'],'destinations':[{'name':'invalid','latitude':True,'longitude':127}]}]:
   r=c.request.post(BASE+'/api/family/destinations',headers=headers,data=json.dumps(invalid));assert r.status==400
  checks['invalidSchemaRejectedBeforeNativeWrite']=True
  # Protect the owned guest's input and output before the real family greeting.
  routing="""import sys,json
sys.path.insert(0,'scripts')
from audio_guard import _prime,route_lock,owns,ROOT
import pulsectl
with route_lock():
 _prime();f=ROOT/'.tools/demo-audio-state.json';saved=json.loads(f.read_text())
 with pulsectl.Pulse('pli-private-route-qa')as p:
  target=next((x for x in p.sink_list()if x.name=='pli_remote_speaker'),None)
  if target is None:p.module_load('module-null-sink','sink_name=pli_remote_speaker rate=44100 channels=2');target=next(x for x in p.sink_list()if x.name=='pli_remote_speaker')
  for stream in p.sink_input_list():
   if owns(stream):
    if 'sink'not in saved:saved['sink']=next(x.name for x in p.sink_list()if x.index==stream.sink)
    p.sink_input_move(stream.index,target.index)
 f.write_text(json.dumps(saved))
 import urllib.request,time
 base='http://127.0.0.1:8876'
 request=urllib.request.Request(base+'/api/kidsnote/personal',data=json.dumps({'action':'start'}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=12)as response:assert response.status==200
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  state=json.load(urllib.request.urlopen(base+'/api/personal/status')).get('app',{})
  if state.get('demo')is False and state.get('sessionStatus')in {'PREPARING','ACTIVE'}:break
  time.sleep(.1)
 else:raise RuntimeError('Private resource intent was not observed under the route lock')
"""
  subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',routing],cwd=ROOT,check=True)
  def ready():wait(lambda s:s['phase']=='LISTENING'and s['recognition']=='READY'and s['playback']=='IDLE'and s['requestedText']==s['speech'],45);time.sleep(.4)
  def speak(name,predicate,rephrase=None):
   for attempt in range(2):
    ready();before=read().get('spokenSequence',0);actual_name=rephrase if attempt and rephrase else name;subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-re','-i',str(ROOT/'qa/native/fixtures'/actual_name),'-f','pulse','-device','pli_remote_mic','PLI synthetic navigation input'],check=True)
    s=wait(lambda x:(predicate(x)and x.get('spokenSequence',0)>before and x.get('requestedText')==x.get('speech'))or x.get('spokenSequence',0)>before and x.get('title')=='다시 한번 말해 주세요.')
    ok=predicate(s);metrics.setdefault('utterances',[]).append({'fixture':actual_name,'attempt':attempt+1,'success':ok,'observedPage':s.get('destinationPage'),'panel':s.get('panel'),'heardLength':len(s.get('heard',''))})
    if ok:return s
    record.diagnostic(s,'navigation-observation-'+str(len(metrics['utterances'])))
   raise AssertionError('Two real spoken attempts were not recognized; no text injection')
  page=speak('destination-options-private.wav',lambda s:s['panel']=='DESTINATIONS'and s['destinationPage']==0)
  seen=set();metrics['spokenPages']=[]
  while True:
   names={item['id']for item in choices if re.search(re.escape(item['name'])+r'(?!\d)',page['speech'])}
   assert names-seen,'A spoken page exposed no new candidate'
   seen|=names;metrics['spokenPages'].append({'page':page['destinationPage'],'candidateIds':sorted(names)})
   if len(seen)==len(choices):break
   assert len(metrics['spokenPages'])<len(choices),'The list did not reach all owned candidates'
   previous_page=page['destinationPage'];page=speak('next-question.wav',lambda s:s['panel']=='DESTINATIONS'and s['destinationPage']>previous_page,rephrase='destination-page-clear.wav')
  checks['allTwelveCandidatesReachTheirSpokenPage']=seen=={item['id']for item in choices}
  speak('destination-twelfth.wav',lambda s:'확인'in s['title']and '시연 장소 12'in s['speech'],rephrase='destination-twelfth-clear.wav');checks['privateSpokenCandidateSelected']=True
  checks['guardianRequiredBeforeAnyRequest']=read()['routeStatus']=='IDLE'
  assert checks['guardianRequiredBeforeAnyRequest']
  s=speak('destination-confirm-primary.wav',lambda s:s['routeStatus']in {'CONFIRMED','FAILED','UNKNOWN'},rephrase='destination-confirm-clear.wav');metrics['actualSdkTerminal']=s['routeStatus'];checks['requestHasBoundedTerminalState']=True;checks['sdkActuallyConfirmedGuidance']=s['routeStatus']=='CONFIRMED'and s.get('routeActive')is True
  metrics['sdkErrors']=[line.split('Navi:')[-1].strip()for line in adb('logcat','-d','-v','brief','-s','PliVehicle:W','*:S').decode().splitlines()if 'Navi:'in line][-3:]
 finally:
  try:
   try:
    s=read()
    if not s['demo']and s['sessionStatus']=='ACTIVE'and (s.get('routeActive')or checks.get('requestHasBoundedTerminalState')):
     adb('shell','content','call','--user','10','--uri','content://ai.teammoon.pli.demo','--method','session','--arg','cancel_route');metrics['ownCancellationRequested']=True
     until=time.monotonic()+4
     while time.monotonic()<until:
      after_cancel=read()
      if after_cancel.get('routeStatus')=='CANCELLED':break
      time.sleep(.2)
     metrics['ownCancellationCallbackSeen']=after_cancel.get('routeStatus')=='CANCELLED';checks['sdkActuallyConfirmedCancellation']=metrics['ownCancellationCallbackSeen']
   except Exception as error:metrics['preCleanupError']=type(error).__name__
   # The owned guest can actually go offline during recovery. Keep the original
   # durable, await a real STOPPED state, then use a fresh revision to restore.
   cleanup_start=time.monotonic();until=cleanup_start+120;restored=False
   while time.monotonic()<until:
    try:
     status=c.request.get(BASE+'/api/personal/status',timeout=4000).json();app=status.get('app',{})
     if app.get('demo')is False:c.request.post(BASE+'/api/kidsnote/personal',headers=headers,data=json.dumps({'action':'stop'}),timeout=12000)
     elif app.get('sessionStatus')=='STOPPED'and not status.get('voiceBusy')and not status.get('lease',{}).get('busy'):
      store(original['destinations']);after=read('private-summary');restored=all(after[k]==v for k,v in summary.items()if k!='revision')
      if restored:(ROOT/'.tools/portal-mode').touch();pending.unlink();break
    except Exception as error:metrics['lastCleanupError']=type(error).__name__
    time.sleep(.4)
   metrics['cleanupSeconds']=round(time.monotonic()-cleanup_start,3);checks['familyDataAndOriginalCandidatesRestored']=restored
   checks['privateNativeStopConfirmed']=restored and read()['sessionStatus']=='STOPPED'
   checks['routeRestoredAfterNativeAck']=not(ROOT/'.tools/demo-audio-state.json').exists()
   if restored and checks['privateNativeStopConfirmed']and checks['routeRestoredAfterNativeAck']:record.confirm_cleanup()
  finally:b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
