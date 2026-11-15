"""Actual MCP -> owner web -> release Provider -> durable store; metadata only."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['accountUiNoErrors',
                             'actualMcpConnected',
                             'actualReadbackReceipt',
                             'completeThreeMonthRead',
                             'ownerPageOnlyLocal',
                             'parentFactsStored',
                             'privateFilesRestricted',
                             'privateProfileAndFactsSurviveRestart',
                             'publicAccountBlocked',
                             'publicFamilyBlocked',
                             'publicHidesPrivateState',
                             'publicSyncBlocked',
                             'safePublicPreviewRestored',
                             'storedPlanIdsMatch',
                             'tailnetAccountBlocked',
                             'tailnetHidesPrivateState'],
          'safetyChecks': {'privateFilesRestricted': 'personal-avd',
                           'publicHidesPrivateState': 'public-service',
                           'tailnetHidesPrivateState': 'public-service'},
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
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/kidsnote-bridge.py',
                     'scripts/kidsnote_mcp/site.mjs',
                     'scripts/kidsnote_mcp/sync.mjs',
                     'scripts/kidsnote_mcp/voice.mjs',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': [],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'],
                        ['public-service', 'shared'],
                        ['personal-service', 'shared'],
                        ['personal-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import json,subprocess,time,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];BASE='http://127.0.0.1:8876';PUBLIC=json.loads((ROOT/'.tools/public-config.json').read_text())['url'];ADB=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial'];checks={};metrics={}
record=RunRecord(__file__,checks,metrics)
from playwright.sync_api import sync_playwright
def adb(*args,input=None):return subprocess.run([str(ADB),'-s',serial,*args],input=input,capture_output=True,check=True,timeout=20).stdout
user=adb('shell','am','get-current-user').decode().strip()
def read(path):return json.loads(adb('exec-out','content','read','--user',user,'--uri','content://ai.teammoon.pli.demo/'+path))
def control(action):
 out=adb('shell','content','call','--user',user,'--uri','content://ai.teammoon.pli.demo','--method','session','--arg',action)
 assert b'Exception'not in out and b'Result:'in out

def launch():adb('shell','am','start','--user',user,'--activity-single-top','-n','ai.teammoon.pli/.MainActivity')
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome');c=b.new_context();v=c.new_page();errors=[];v.on('pageerror',lambda e:errors.append(str(e)));v.goto(BASE+'/family');v.wait_for_function('document.querySelector("#scope").value.length>0')
 with v.expect_response('**/api/kidsnote/sync',timeout=100000)as response:v.locator('#sync').click()
 metrics['syncStatusCode']=response.value.status
 assert response.value.status==200,'Sync did not commit (HTTP '+str(response.value.status)+')';meta=response.value.json()
 integration=read('integration');summary=read('private-summary');receipt=integration['receipt'];batch=json.loads((ROOT/'.tools/private/kidsnote/family.json').read_text())
 checks['actualMcpConnected']=meta['connected'] is True
 checks['completeThreeMonthRead']=meta['monthsRead']==3 and batch['complete'] is True
 checks['actualReadbackReceipt']=receipt['committed'] and receipt['batchId']==batch['batchId'] and receipt['retainedFromBatch']==len(batch['plans'])
 checks['storedPlanIdsMatch']=set(p['id']for p in batch['plans']).issubset(summary['planIds'])
 checks['parentFactsStored']=summary['facts']>=len(batch['facts'])>=7 and not meta['briefingErrors']
 checks['accountUiNoErrors']=not errors
 checks['ownerPageOnlyLocal']=c.request.get('http://100.95.226.69:8876/family').status==404
 checks['tailnetAccountBlocked']=c.request.get('http://100.95.226.69:8876/api/kidsnote/status').status==404
 # This owner also checks public routes. A simultaneous intentional server
 # outage (TTL/crash QA) is a missing precondition, not a private-data exposure.
 public_wait=time.monotonic();until=public_wait+200
 while True:
  try:
   response=c.request.get('http://127.0.0.1:8878/api/status',timeout=3000)
   if response.status==200 and response.json().get('profile')=='public':break
  except Exception:pass
  assert time.monotonic()<until,'Public service unavailable; strict 404 boundary checks were not reached'
  time.sleep(.5)
 metrics['publicBoundaryReadinessWaitSeconds']=round(time.monotonic()-public_wait,3)
 codes={'account':c.request.get(PUBLIC+'/api/kidsnote/status').status,'family':c.request.get(PUBLIC+'/family').status,'sync':c.request.post(PUBLIC+'/api/kidsnote/sync',headers={'Origin':PUBLIC},data='{}').status};metrics['publicBoundaryStatusCodes']=codes
 checks['publicAccountBlocked']=codes['account']==404
 checks['publicFamilyBlocked']=codes['family']==404
 checks['publicSyncBlocked']=codes['sync']==404
 assert read('state')['sessionStatus']=='STOPPED','Do not interrupt a live session'
 (ROOT/'.tools/runtime-transition').write_text(str(time.time()+60))
 try:
  control('private');launch();adb('shell','am','force-stop','--user',user,'ai.teammoon.pli');time.sleep(1.2);launch()
  reloaded=read('private-summary');checks['privateProfileAndFactsSurviveRestart']=reloaded==summary
  # Compare the remote boundary after the monitor has observed this private boot,
  # rather than comparing it to its older, harmless public sample snapshot.
  boot_id=read('state')['bootId'];deadline=time.monotonic()+8
  while True:
   observed=c.request.get(BASE+'/api/personal/status').json().get('app',{})
   if observed.get('bootId')==boot_id and observed.get('demo')is False:break
   assert time.monotonic()<deadline,'Monitor did not observe the private boot'
   time.sleep(.2)
  privacy=json.loads(subprocess.check_output([str(ROOT/'.tools/demo-venv/bin/python'),str(ROOT/'qa/native/fixtures/privacy-boundary.py')],cwd=ROOT));assert all(privacy.values())
  checks['publicHidesPrivateState']=privacy['public']and privacy['socket']and privacy['ownerPositive']
  checks['tailnetHidesPrivateState']=privacy['tailnet']and privacy['labelOnlyRejected']
 finally:
  try:control('preview');launch()
  finally:(ROOT/'.tools/runtime-transition').unlink(missing_ok=True)
 checks['safePublicPreviewRestored']=read('state')['demo'] and read('state')['capture']=='STOPPED'
 metrics.update(calendarEvents=meta['calendarEvents'],upcomingPlans=meta['upcomingPlans'],retainedPlans=receipt['retainedFromBatch'],facts=len(batch['facts']),storeRevision=receipt['storeRevision'])
 checks['privateFilesRestricted']=all((ROOT/'.tools/private/kidsnote'/n).stat().st_mode&0o077==0 for n in ['browser.json','family.json','metadata.json','mcp-token'])
 b.close()
print(json.dumps({'checks':checks,'metrics':metrics},ensure_ascii=False));assert all(checks.values())
