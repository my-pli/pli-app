"""Real END transport loss, lost response, repetition and stale ownership."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['lostEndRequestRecoveredThroughSocketClosure',
                             'lostEndResponseRecoveredThroughActualReceipt',
                             'newClaimDeniedUntilStopConfirmed',
                             'repeatedEndIsIdempotent',
                             'resourceNavigationConfirmsNativeStop',
                             'resourceNavigationStopsBrowserTracks',
                             'staleEndCannotCancelNewOwner'],
          'safetyChecks': {'newClaimDeniedUntilStopConfirmed': 'public-avd',
                           'staleEndCannotCancelNewOwner': 'public-avd',
                           'resourceNavigationConfirmsNativeStop': 'public-avd'},
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
          'fixtures': ['silence.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import asyncio,json
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics);URL='https://127.0.0.1:9001'
from playwright.async_api import async_playwright
async def main():
 async with async_playwright()as p:
  b=await p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=await b.new_context(ignore_https_errors=True,permissions=['microphone']);v=await c.new_page()
  async def start():
   await v.goto(URL+'/app');await v.wait_for_function('state.status.controlReady && !state.status.lease.busy',timeout=90000);await v.locator('#connect').click();await v.wait_for_function("state.voice && state.status.app.phase==='LISTENING' && state.status.app.playback==='IDLE'",timeout=45000)
   return await v.evaluate('state.token')
  async def ended():await v.wait_for_function("!state.ending && !state.status.lease.busy && state.status.app.sessionStatus==='STOPPED' && state.status.app.stopReceipt.captureStopped && state.status.app.stopReceipt.focusReleased",timeout=20000)
  try:
   await start()
   async def drop_request(route):await route.abort('failed')
   await v.route('**/api/session/end',drop_request);await v.evaluate('endSession()');await ended();checks['lostEndRequestRecoveredThroughSocketClosure']=True;await v.unroute('**/api/session/end')
   await start()
   async def drop_response(route):
    response=await route.fetch();metrics['lostResponseActualStatus']=response.status;await route.abort('failed')
   await v.route('**/api/session/end',drop_response);await v.evaluate('endSession()');await ended();checks['lostEndResponseRecoveredThroughActualReceipt']=metrics['lostResponseActualStatus']==200;await v.unroute('**/api/session/end')
   token=await start();headers={'Origin':URL,'X-Pli-Session':token}
   responses=await asyncio.gather(c.request.post(URL+'/api/session/end',headers=headers,data='{}'),c.request.post(URL+'/api/session/end',headers=headers,data='{}'),c.request.post(URL+'/api/session/claim',headers={'Origin':URL},data='{}'))
   statuses=[x.status for x in responses];metrics['concurrentStatuses']=statuses
   checks['repeatedEndIsIdempotent']=statuses[:2]==[200,200]
   checks['newClaimDeniedUntilStopConfirmed']=statuses[2]==423
   await v.wait_for_function("!state.status.lease.busy && state.status.app.sessionStatus==='STOPPED'",timeout=15000)
   claim=await c.request.post(URL+'/api/session/claim',headers={'Origin':URL},data='{}');new=(await claim.json())['sessionToken']
   stale=await c.request.post(URL+'/api/session/end',headers=headers,data='{}');checks['staleEndCannotCancelNewOwner']=stale.status==423
   await c.request.post(URL+'/api/session/end',headers={'Origin':URL,'X-Pli-Session':new},data='{}')
   await start();await v.evaluate('window.qaNavTracks=mic.getTracks()');await v.locator('nav a[href="/resources"]').click();await v.wait_for_function("state.route==='/resources'&&!state.voice&&mic===null&&qaNavTracks.every(t=>t.readyState==='ended')",timeout=3000)
   checks['resourceNavigationStopsBrowserTracks']=True
   await ended();checks['resourceNavigationConfirmsNativeStop']=True
  finally:
   try:await v.evaluate('endSession()')
   finally:await b.close()
asyncio.run(main());print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
