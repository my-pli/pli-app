"""Actual Pulse route-lock contention must not become a false environment failure."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['modeRecoveryNeverOpensMicrophoneOrChangesFamily',
                             'privateOrphanPreservesFamilyAndReleasesInput',
                             'privateOrphanRestoresPublicPreviewAndSupervisor',
                             'publicModeRestoredFromVisiblePrivateIdle',
                             'realContentionDoesNotPublishFalseFailure',
                             'sameAppAndNoMicrophoneOpened',
                             'staleIdleCacheCannotKillAnActualVoiceSession'],
          'safetyChecks': {'sameAppAndNoMicrophoneOpened': 'personal-avd',
                           'modeRecoveryNeverOpensMicrophoneOrChangesFamily': 'personal-avd',
                           'staleIdleCacheCannotKillAnActualVoiceSession': 'personal-avd',
                           'privateOrphanPreservesFamilyAndReleasesInput': 'personal-avd'},
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
                     'qa/native/fixtures/private-route.py',
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': [],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['personal-service', 'exclusive'],
                        ['personal-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'},
 'cleanup': {'profile': 'personal',
             'nativeRequired': True,
             'expectedChecks': ['physicalCleanupConfirmed'],
             'safetyChecks': {'physicalCleanupConfirmed': 'personal-avd'},
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
                        'qa/native/fixtures/private-route.py',
                        'scripts/audio_guard.py',
                        'scripts/demo-server.py',
                        'scripts/display_stream.py',
                        'scripts/portal_proxy.py',
                        'scripts/runtime_context.py'],
             'fixtures': [],
             'effects': 'mutate',
             'resources': [['host-load', 'shared'],
                           ['personal-service', 'exclusive'],
                           ['personal-avd', 'exclusive']],
             'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import subprocess,json,time,urllib.request,sys
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'transitions':[]};record=RunRecord(__file__,checks,metrics,dependencies=['qa/native/fixtures/private-route.py'])
if '--cleanup-only'in sys.argv:
 verified_idle=record.verify_cleanup();checks['physicalCleanupConfirmed']=verified_idle
 assert verified_idle,'Actual idle resource barrier has not been satisfied'
 raise SystemExit(0)
def status():return json.load(urllib.request.urlopen('http://127.0.0.1:8876/api/personal/status',timeout=8))
deadline=time.monotonic()+45;stable=None;stable_since=time.monotonic()
while True:
 s=status();a=s.get('app',{});identity=(s.get('process'),a.get('bootId'))
 ready=s.get('appResponsive')and s.get('runtime',{}).get('phase')=='ready'and not s['voiceBusy']and not s['lease']['busy']and a.get('sessionStatus')=='STOPPED'and a.get('visible')and a.get('hasView')
 if not ready or identity!=stable:stable=identity if ready else None;stable_since=time.monotonic()
 if ready and time.monotonic()-stable_since>=2:break
 assert time.monotonic()<deadline,'Actual idle runtime not ready before contention'
 time.sleep(.2)
before=s['process'];metrics['processBefore']=before;code="import sys,time;sys.path.insert(0,'scripts');from audio_guard import route_lock\nwith route_lock():\n print('LOCKED',flush=True);time.sleep(4)"
p=subprocess.Popen([str(ROOT/'.tools/demo-venv/bin/python'),'-c',code],cwd=ROOT,stdout=subprocess.PIPE,text=True);assert p.stdout.readline().strip()=='LOCKED';began=time.monotonic();healthy=True
try:
 while time.monotonic()-began<6:
  s=status();r=s.get('runtime',{});entry={**{k:r.get(k)for k in ['phase','lastError']},'process':s.get('process')}
  if not metrics['transitions']or metrics['transitions'][-1]!=entry:metrics['transitions'].append(entry)
  healthy=healthy and r.get('phase')=='ready'and s.get('process')==before
  time.sleep(.15)
 p.wait(timeout=3);checks['realContentionDoesNotPublishFalseFailure']=healthy and p.returncode==0
 checks['sameAppAndNoMicrophoneOpened']=s.get('process')==before and s.get('app',{}).get('capture')=='STOPPED'and not s['voiceBusy']and not s['lease']['busy']
finally:
 if p.poll()is None:p.terminate();p.wait(timeout=3)
adb=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial'];marker=ROOT/'.tools/portal-mode'
def native(path='state'):return json.loads(subprocess.check_output([str(adb),'-s',serial,'exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path],timeout=8))
def control(action):
 out=subprocess.check_output([str(adb),'-s',serial,'shell','content','call','--user','10','--uri','content://ai.teammoon.pli.demo','--method','session','--arg',action],stderr=subprocess.STDOUT,timeout=8);assert b'Result:'in out and b'Exception'not in out
summary=native('private-summary');restored=False
try:
 marker.unlink(missing_ok=True);control('private');a=native();assert not a['demo']and a['visible']and a['hasView']and a['sessionStatus']=='STOPPED','The observed visible-private idle condition was not established'
 marker.touch();began=time.monotonic();deadline=began+25
 while time.monotonic()<deadline:
  a=native()
  if a['demo']and a['presentation']and a['visible']and a['hasView']:restored=True;break
  time.sleep(.2)
 metrics['visibleIdleModeRecoverySeconds']=round(time.monotonic()-began,3);checks['publicModeRestoredFromVisiblePrivateIdle']=restored
 checks['modeRecoveryNeverOpensMicrophoneOrChangesFamily']=a['capture']=='STOPPED'and native('private-summary')==summary
finally:
 marker.touch()
 if not restored:control('preview')
# Real personal native resource owner; public browser now owns a different AVD.
import ast
route=(ROOT/'qa/native/fixtures/private-route.py').read_text()
try:
 subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',route],cwd=ROOT,check=True,capture_output=True)
 until=time.monotonic()+45
 while time.monotonic()<until:
  live=native()
  if live['sessionStatus']=='ACTIVE'and live['capture']=='ACTIVE'and live['phase']=='LISTENING'and live['playback']=='IDLE':break
  time.sleep(.2)
 else:raise AssertionError('Actual personal voice owner not ready')
 process=status()['process'];began=time.monotonic();health=ROOT/'.tools/native-health.json';pending=health.with_suffix('.qa.tmp')
 while time.monotonic()-began<6:
  pending.write_text(json.dumps({'at':time.time(),'pid':process,'demo':False,'visible':True,'hasView':True,'sessionStatus':'STOPPED'}));pending.replace(health);time.sleep(.07)
 actual=native();checks['staleIdleCacheCannotKillAnActualVoiceSession']=status()['process']==process and actual['sessionId']==live['sessionId']and actual['serviceInstanceId']==live['serviceInstanceId']and actual['capture']=='ACTIVE'and actual['sessionStatus']=='ACTIVE'
finally:
 req=urllib.request.Request('http://127.0.0.1:8876/api/kidsnote/personal',data=b'{"action":"stop"}',headers={'Origin':'http://127.0.0.1:8876','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=20)as response:assert response.status==200
 marker.touch()
# Preserve the private orphan contract on its own AVD after profile separation.
try:
 subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',route],cwd=ROOT,check=True,capture_output=True)
 until=time.monotonic()+45
 while time.monotonic()<until:
  actual=native()
  if not actual['demo']and actual['sessionStatus']=='ACTIVE'and actual['capture']=='ACTIVE':break
  time.sleep(.2)
 else:raise AssertionError('Private orphan setup did not open actual capture')
 family_before=native('private-summary');boot=actual['deviceBootCount'];began=time.monotonic()
 subprocess.run([str(adb),'-s',serial,'shell','am','force-stop','--user','10','ai.teammoon.pli'],check=True)
 until=time.monotonic()+120
 while time.monotonic()<until:
  try:
   actual=native()
   if actual['capture']=='STOPPED'and actual.get('playback')=='IDLE'and actual.get('focus')=='NONE'and actual['sessionStatus']=='STOPPED'and actual['demo']and actual['visible']and actual['hasView']and(actual['deviceBootCount']>boot or all((actual.get('stopReceipt')or{}).get(key)is True for key in ['captureStopped','playbackStopped','focusReleased','instanceClosed'])):break
  except (OSError,ValueError,subprocess.SubprocessError):pass
  time.sleep(.3)
 else:raise AssertionError('Private orphan did not recover through a verified guest reboot')
 checks['privateOrphanRestoresPublicPreviewAndSupervisor']=marker.exists()and actual['capture']=='STOPPED'
 checks['privateOrphanPreservesFamilyAndReleasesInput']=native('private-summary')==family_before and not(ROOT/'.tools/demo-audio-state.json').exists()
 metrics['recoveryPolicy']={'strategy':'guest-reboot','observedReboot':actual['deviceBootCount']>boot,'outcome':'closed native resources and restored family'}
 metrics['privateOrphanRecoverySeconds']=round(time.monotonic()-began,3)
finally:
 marker.touch()
 try:
  req=urllib.request.Request('http://127.0.0.1:8876/api/kidsnote/personal',data=b'{"action":"stop"}',headers={'Origin':'http://127.0.0.1:8876','Content-Type':'application/json'})
  urllib.request.urlopen(req,timeout=20).close()
 except (OSError,ValueError):pass
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
