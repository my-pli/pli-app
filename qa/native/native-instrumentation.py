"""Run resource/AtomicFile tests against the installed release APK; preserve family data."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['actualSdkWarmupReady',
                             'familyDataPreserved',
                             'idleBeforeOwnerTests',
                             'instrumentationCompleted',
                             'silenceRouteReleasedAfterStop',
                             'testApkBuiltFromCurrentSources'],
          'safetyChecks': {'silenceRouteReleasedAfterStop': 'personal-avd',
                           'familyDataPreserved': 'personal-avd'},
          'inputs': ['android/app/src/androidTest/assets/bye-native.pcm',
                     'android/app/src/androidTest/assets/hush-native.pcm',
                     'android/app/src/androidTest/java/ai/teammoon/pli/ActivityOwnerTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/AudioFocusTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/AudioFocusThreadTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/CompanionLifecycleTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/PlanPhotoTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/ProviderContractTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/PublicPrivacyTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/RecognitionLocaleTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/RemediationOwnerTest.kt',
                     'android/app/src/androidTest/java/ai/teammoon/pli/StoreContractTest.kt',
                     'android/app/src/main/AndroidManifest.xml',
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
          'executionKind': 'NATIVE_OWNER'},
 'focused': {'profile': 'personal',
             'nativeRequired': True,
             'expectedChecks': ['actualSdkWarmupReady',
                                'familyDataPreserved',
                                'idleBeforeOwnerTests',
                                'instrumentationCompleted',
                                'silenceRouteReleasedAfterStop',
                                'testApkBuiltFromCurrentSources'],
             'safetyChecks': {'silenceRouteReleasedAfterStop': 'personal-avd',
                              'familyDataPreserved': 'personal-avd'},
             'inputs': ['android/app/src/androidTest/assets/bye-native.pcm',
                        'android/app/src/androidTest/assets/hush-native.pcm',
                        'android/app/src/androidTest/java/ai/teammoon/pli/ActivityOwnerTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/AudioFocusTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/AudioFocusThreadTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/CompanionLifecycleTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/PlanPhotoTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/ProviderContractTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/PublicPrivacyTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/RecognitionLocaleTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/RemediationOwnerTest.kt',
                        'android/app/src/androidTest/java/ai/teammoon/pli/StoreContractTest.kt',
                        'android/app/src/main/AndroidManifest.xml',
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
             'executionKind': 'NATIVE_OWNER'}}
from pathlib import Path
import hashlib,json,re,subprocess,sys,time,urllib.request,os
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics,dependencies=['android/app/src/androidTest/assets/bye-native.pcm','android/app/src/androidTest/assets/hush-native.pcm','qa/native/fixtures/private-route.py'])
# Bind the actual test APK to current test/main sources; a leftover compiled
# androidTest APK must not certify newly edited Kotlin source.
from run_record import source_snapshot
before_build=source_snapshot(__file__);build_env=os.environ.copy();build_env.update(ANDROID_HOME=str(ROOT/'.tools/android-sdk'),GRADLE_USER_HOME=str(ROOT/'.tools/gradle-user'))
with (ROOT/'.tools/logs/native-test-build.log').open('w')as output:
 built=subprocess.run([str(ROOT/'.tools/gradle/gradle-8.10.2/bin/gradle'),'-p',str(ROOT/'android'),':app:assembleDebugAndroidTest','--console=plain'],cwd=ROOT,env=build_env,stdout=output,stderr=subprocess.STDOUT)
checks['testApkBuiltFromCurrentSources']=built.returncode==0 and source_snapshot(__file__)==before_build
metrics['testBuildExitCode']=built.returncode
assert checks['testApkBuiltFromCurrentSources'],'Current instrumentation sources did not build; stale test APK refused'
ADB=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial'];marker=ROOT/'.tools/runtime-transition'
def adb(*args):return subprocess.check_output([str(ADB),'-s',serial,*args],timeout=240)
def control(action):
 out=adb('shell','content','call','--user','10','--uri','content://ai.teammoon.pli.demo','--method','session','--arg',action);assert b'Result:'in out and b'Exception'not in out

def read(path):return json.loads(adb('exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path))
deadline=time.monotonic()+25
while True:
 s=json.load(urllib.request.urlopen('http://127.0.0.1:8876/api/personal/status'))
 if not s['voiceBusy']and not s['lease']['busy']and s.get('app',{}).get('sessionStatus')=='STOPPED':break
 assert time.monotonic()<deadline,'Idle APK not ready for instrumentation'
 time.sleep(.5)
before=read('private-summary')
# Require a real, closed SDK session before destructive owner tests. A cold or
# poisoned shared engine is a precondition failure, not 31 cascading timeouts.
route=(ROOT/'qa/native/fixtures/private-route.py').read_text();warm=time.monotonic()
try:
 subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',route],cwd=ROOT,check=True,capture_output=True)
 until=time.monotonic()+25
 while time.monotonic()<until:
  actual=read('state')
  if actual.get('sessionStatus')=='ACTIVE'and actual.get('capture')=='ACTIVE'and actual.get('recognition')=='READY'and actual.get('playback')=='IDLE'and actual.get('phase')=='LISTENING':break
  time.sleep(.15)
 else:raise AssertionError('The actual SDK is not ready before owner tests')
 metrics['sdkWarmupSeconds']=round(time.monotonic()-warm,3);checks['actualSdkWarmupReady']=True
finally:
 request=urllib.request.Request('http://127.0.0.1:8876/api/kidsnote/personal',data=b'{"action":"stop"}',headers={'Origin':'http://127.0.0.1:8876','Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=30)as response:assert response.status==200
initial=read('state');names=adb('shell','ps','-A','-o','NAME').decode().splitlines()
checks['idleBeforeOwnerTests']=all(initial.get(k)==v for k,v in {'sessionStatus':'STOPPED','capture':'STOPPED','playback':'IDLE','focus':'NONE'}.items())and 'ai.teammoon.pli:voice'not in names
assert checks['idleBeforeOwnerTests'],'Actual warmup resources must be released before owner tests'
assert read('private-summary')==before,'The warmup must preserve all family data'
marker.write_text(str(time.time()+400));subprocess.run(['systemctl','--user','stop','pli-pleos-demo.service'],check=True)
try:
 subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',"import sys;sys.path.insert(0,'scripts');from audio_guard import prime;prime()"],cwd=ROOT,check=True)
 test=ROOT/'android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk';metrics['testApkSha256']=hashlib.sha256(test.read_bytes()).hexdigest()
 try:
  path=adb('shell','pm','path','--user','10','ai.teammoon.pli.test').decode().strip().removeprefix('package:');same=adb('shell','sha256sum',path).decode().split()[0]==metrics['testApkSha256']
 except (subprocess.SubprocessError,IndexError):same=False
 if not same:adb('install','-r','-t',str(test))
 # AAOS removes the old embedded task asynchronously; settle it before the new instrumentation process exists.
 adb('shell','am','force-stop','--user','10','ai.teammoon.pli');time.sleep(1.2)
 names=['AudioFocusTest','AudioFocusThreadTest','CompanionLifecycleTest','StoreContractTest','PlanPhotoTest','PublicPrivacyTest','ProviderContractTest','RemediationOwnerTest']
 if '--resources-only'not in sys.argv:names.append('ActivityOwnerTest')
 metrics['testClasses']=names;metrics['activityRecreationIncluded']='ActivityOwnerTest'in names
 if '--class'in sys.argv:names=[sys.argv[sys.argv.index('--class')+1]];metrics['testClasses']=names;metrics['activityRecreationIncluded']=False
 classes=','.join('ai.teammoon.pli.'+s for s in names)
 metrics['guestInstrumentationTerminated']=False
 record.require_cleanup('guestInstrumentationTerminated',lambda:metrics['guestInstrumentationTerminated'])
 start=time.monotonic();out=adb('shell','am','instrument','--user','10','-w','-r','-e','class',classes,'ai.teammoon.pli.test/androidx.test.runner.AndroidJUnitRunner').decode(errors='replace');(ROOT/'.tools/logs/native-instrumentation.txt').write_text(out);metrics['guestInstrumentationTerminated']='INSTRUMENTATION_CODE:'in out
 checks['instrumentationCompleted']=bool(re.search(r'OK \(\d+ tests?\)',out))and 'FAILURES!!!'not in out
 metrics['durationSeconds']=round(time.monotonic()-start,3)
 total=re.search(r'INSTRUMENTATION_STATUS: numtests=(\d+)',out);metrics['testCount']=int(total.group(1))if total else 0
 metrics['failedTests']=re.findall(r'INSTRUMENTATION_STATUS: stack=([^\n]+)',out)
 checks['familyDataPreserved']=read('private-summary')==before
finally:
 try:
  if metrics.get('guestInstrumentationTerminated')is False:raise RuntimeError('Guest instrumentation exit unconfirmed; retain quarantine instead of assigning the device')
  if read('state')['sessionStatus']!='STOPPED':control('end');time.sleep(3)
  control('preview');adb('shell','am','start','--user','10','--activity-single-top','-n','ai.teammoon.pli/.MainActivity')
 finally:
  marker.unlink(missing_ok=True);subprocess.run(['systemctl','--user','start','pli-pleos-demo.service'],check=True)
for _ in range(30):
 if not(ROOT/'.tools/demo-audio-state.json').exists():break
 time.sleep(.25)
checks['silenceRouteReleasedAfterStop']=not(ROOT/'.tools/demo-audio-state.json').exists()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
