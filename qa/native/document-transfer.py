"""Owner upload -> DUMP Provider bytes; preserve all pre-existing private originals."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['activeKindSelected',
                             'actualProviderBytesMatch',
                             'allOriginalBytesRestored',
                             'familyStoreUnchanged',
                             'otherOriginalPreserved',
                             'over64KiBRejected',
                             'over8MiBRejected',
                             'ownerGuiUploadAcknowledged'],
          'safetyChecks': {'allOriginalBytesRestored': 'personal-avd',
                           'familyStoreUnchanged': 'personal-avd'},
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
          'fixtures': [],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['personal-service', 'shared'],
                        ['personal-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import hashlib,json,subprocess,time
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics)
from playwright.sync_api import sync_playwright
ADB=ROOT/'.tools/android-sdk/platform-tools/adb';URI='content://ai.teammoon.pli.demo/';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial']
def command(*args,input=None):return subprocess.run([str(ADB),'-s',serial,*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
def read(path):
 r=command('exec-out','content','read','--user','10','--uri',URI+path)
 if r.returncode or r.stdout.startswith(b'Error while')or b'FileNotFoundException'in r.stderr:return None
 return r.stdout
def status():return json.loads(read('integration'))
def write(path,data):
 revision=status()['revision'];r=command('exec-in','content','write','--user','10','--uri',URI+path,input=data);assert r.returncode==0
 end=time.monotonic()+12
 while time.monotonic()<end:
  if path=='plan-active':
   if read(path)==data:return
  elif status()['revision']>revision and read(path)==data:return
  time.sleep(.1)
 raise AssertionError('Original document restoration unconfirmed')
original={key:read(key)for key in ['plan-text','plan-image','plan-active']};summary=json.loads(read('private-summary'))
try:
 with sync_playwright()as p:
  b=p.chromium.launch(headless=True,channel='chrome');c=b.new_context();v=c.new_page();v.goto('http://127.0.0.1:8876/family');v.wait_for_timeout(600)
  payload='2026-11-11, 합성 숲 체험, 물병\n'.encode();v.locator('#plan-file').set_input_files({'name':'synthetic-plan.csv','mimeType':'text/csv','buffer':payload});v.locator('#plan-upload').click();v.wait_for_function("document.querySelector('#plan-result').textContent.includes('기기에 저장한 파일')",timeout=35000)
  checks['ownerGuiUploadAcknowledged']=True;checks['actualProviderBytesMatch']=read('plan-text')==payload;checks['activeKindSelected']=read('plan-active')==b'text';checks['otherOriginalPreserved']=read('plan-image')==original['plan-image']
  # Streamed HTTP limits are enforced before native storage; no calendar import.
  r=c.request.post('http://127.0.0.1:8876/api/family/plan',headers={'Origin':'http://127.0.0.1:8876','X-Pli-Document':'text','Content-Type':'application/octet-stream'},data=b'x'*65537)
  checks['over64KiBRejected']=r.status==413 and read('plan-text')==payload
  r=c.request.post('http://127.0.0.1:8876/api/family/plan',headers={'Origin':'http://127.0.0.1:8876','X-Pli-Document':'image','Content-Type':'application/octet-stream'},data=b'x'*(8*1024*1024+1))
  checks['over8MiBRejected']=r.status==413 and read('plan-image')==original['plan-image'];b.close()
finally:
 for key in ['plan-text','plan-image']:
  if original[key]is not None:write(key,original[key])
 for key in ['plan-text','plan-image','plan-active']:
  if original[key]is None:command('shell','content','delete','--user','10','--uri',URI+key)
 if original['plan-active']is not None:write('plan-active',original['plan-active'])
 checks['allOriginalBytesRestored']=all(read(key)==data for key,data in original.items())
 checks['familyStoreUnchanged']=json.loads(read('private-summary'))==summary
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
