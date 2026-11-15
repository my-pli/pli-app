"""Three actual personal Android reboots; native receipts, separate boot/view/voice timings."""
QA_CONTRACT = {'full': {'profile': 'personal',
          'nativeRequired': True,
          'expectedChecks': ['everyCleanupConfirmed',
                             'familySurvivesAllBoots',
                             'threeRealBootsAndVoiceStarts'],
          'safetyChecks': {'familySurvivesAllBoots': 'personal-avd', 'everyCleanupConfirmed': 'personal-avd'},
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
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import ast,json,subprocess,time,urllib.request
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'samples':[],'condition':'Three real personal Pleos guest reboots; host process and disk/model caches retained; 10s system stabilization included; real private speech session and SDK greeting, no text ingress'};record=RunRecord(__file__,checks,metrics,dependencies=['qa/native/fixtures/private-route.py'])
ADB=ROOT/'.tools/android-sdk/platform-tools/adb';serial=json.loads((ROOT/'.tools/run-state.json').read_text())['serial'];marker=ROOT/'.tools/runtime-transition';BASE='http://127.0.0.1:8876'
def adb(*args):return subprocess.check_output([str(ADB),'-s',serial,*args],stderr=subprocess.DEVNULL,timeout=12).decode().strip()
def native(path='state'):return json.loads(adb('exec-out','content','read','--user','10','--uri','content://ai.teammoon.pli.demo/'+path))
def status():return json.load(urllib.request.urlopen(BASE+'/api/personal/status',timeout=5))
def action(value):
 req=urllib.request.Request(BASE+'/api/kidsnote/personal',data=json.dumps({'action':value}).encode(),headers={'Origin':BASE,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=15)as response:assert response.status==200

def wait(predicate,seconds=80):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   s=status()
   if metrics['samples']:
    sample=metrics['samples'][-1];history=sample.setdefault('transitions',[]);state={k:s.get('app',{}).get(k)for k in ['sessionStatus','phase','capture','recognition','playback','error','demo']}
    if not history or history[-1]['state']!=state:history.append({'at':round(time.monotonic()-record.start,2),'state':state})
   if predicate(s):return s
  except (OSError,ValueError,KeyError):pass
  time.sleep(.3)
 raise AssertionError('Actual runtime readiness deadline exceeded')
def idle(s):return not s['voiceBusy']and not s['lease']['busy']and s['app']['sessionStatus']=='STOPPED'and s.get('runtime',{}).get('phase')=='ready'
# Reuse the existing private route owner rather than create a second Pulse writer.
route=(ROOT/'qa/native/fixtures/private-route.py').read_text()
summary=native('private-summary')
try:
 for iteration in range(3):
  sample={'iteration':iteration+1,'success':False};metrics['samples'].append(sample);stage='idle';start=time.monotonic()
  try:
   wait(idle);boot=int(adb('shell','settings','get','global','boot_count'));sample['bootBefore']=boot;marker.write_text(str(time.time()+240));stage='boot';start=time.monotonic();adb('reboot');until=start+180
   while time.monotonic()<until:
    try:
     after=int(adb('shell','settings','get','global','boot_count'))
     if after>boot and adb('shell','getprop','sys.boot_completed')=='1'and 'car_service'in adb('shell','service','list'):break
    except (subprocess.SubprocessError,ValueError):pass
    time.sleep(.5)
   else:raise AssertionError('Guest boot exceeded 180s')
   time.sleep(10);sample.update(bootAfter=after,bootSeconds=round(time.monotonic()-start,3));stage='view';view=time.monotonic();adb('forward','tcp:8088','tcp:8088');adb('shell','content','call','--user','10','--uri','content://ai.teammoon.pli.demo','--method','session','--arg','preview');adb('shell','am','start','--user','10','-n','ai.teammoon.pli/.MainActivity');marker.unlink(missing_ok=True)
   wait(lambda s:idle(s)and s['app']['visible']and s['app']['hasView']);sample['appViewSeconds']=round(time.monotonic()-view,3);stage='voice';voice=time.monotonic()
   subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',route],cwd=ROOT,check=True,capture_output=True)
   s=wait(lambda s:s['app']['sessionStatus']=='ACTIVE'and s['app']['capture']=='ACTIVE'and s['app']['recognition']=='READY'and s['app']['phase']=='LISTENING'and s['app']['playback']=='IDLE'and bool(s['app']['speech'])and s['app']['speech']==s['app']['requestedText'],50)
   sample.update(engineAndGreetingSeconds=round(time.monotonic()-voice,3),guestRebootToListeningSeconds=round(time.monotonic()-start,3),backend=s['app']['backend'],success=True)
  except Exception as error:
   sample.update(failedStage=stage,failure=type(error).__name__)
   if isinstance(error,subprocess.CalledProcessError):sample['routeFailure']=(error.stderr or b'').decode(errors='replace').splitlines()[-1:]
   try:sample['state']={k:native().get(k)for k in ['sessionStatus','phase','capture','recognition','playback','error','deviceBootCount']}
   except Exception:pass
  finally:
   marker.unlink(missing_ok=True);clean=time.monotonic()
   try:
    action('stop');wait(idle);sample['cleanup']={'success':not(ROOT/'.tools/demo-audio-state.json').exists(),'seconds':round(time.monotonic()-clean,3),'additionalGuestReboots':int(adb('shell','settings','get','global','boot_count'))-sample.get('bootAfter',boot)}
   except Exception as error:sample['cleanup']={'success':False,'error':type(error).__name__}
   print(json.dumps(sample),flush=True)
  if not sample['cleanup']['success']:break
 checks['threeRealBootsAndVoiceStarts']=len(metrics['samples'])==3 and all(x['success']and x['bootAfter']>x['bootBefore']for x in metrics['samples'])
 checks['familySurvivesAllBoots']=native('private-summary')==summary
 checks['everyCleanupConfirmed']=all(x['cleanup']['success']for x in metrics['samples'])
finally:marker.unlink(missing_ok=True)
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
