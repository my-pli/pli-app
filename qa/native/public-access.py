"""Public routing/privacy checks; final immutable bytes have an external vector receipt."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['blocked:/.tools/public-config.json',
                             'blocked:/api/diagnostics',
                             'blocked:/api/kidsnote/status',
                             'blocked:/api/personal/status',
                             'blocked:/family',
                             'blocked:/font.ttf',
                             'blocked:/live.mjpg',
                             'foreignOriginRejected',
                             'leaseRequired',
                             'noPrivateLogs',
                             'publicHttpsValidCertificate',
                             'publicProfileIsolated',
                             'publishedCandidateMatchesInstalledApk',
                             'publishedWebIsCurrentWorkingSource',
                             'publishedWebMatchesVector',
                             'runningServerModulesMatchCurrentSources',
                             'productResourcesReachable',
                             'resourcesContainOnlyProducts',
                             'videoOfferMatchesAvailability',
                             'historicalInternalHashesBlocked',
                             'blocked:/report',
                             'blocked:/docs/implementation-report.pdf',
                             'blocked:/docs/UX-AUDIT-2026-11-11.pdf',
                             'blocked:/docs/REMEDIATION-DESIGN-2026-11-11.pdf',
                             'blocked:/artifacts/pli-pleos-source.zip',
                             'blocked:/artifacts/pli-pleos-review-source.zip',
                             'publicPrivacyNotExposed'],
          'safetyChecks': {'publicPrivacyNotExposed': 'public-service',
                           'resourcesContainOnlyProducts': 'public-service',
                           'noPrivateLogs': 'public-service'},
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
                     'scripts/runtime_context.py',
                     'scripts/delivery_assets.py'],
          'fixtures': [],
          'effects': 'read',
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'shared']],
          'executionKind': 'NATIVE_E2E'}}
from pathlib import Path
import hashlib,json,urllib.request,urllib.error,sys,datetime,time,os
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2]
def verify_delivery(url,vector_path,receipt_path,include_media=False):
 began=time.monotonic();delivery_checks={};downloads={};errors={};raw=b'';vector={}
 try:
  raw=Path(vector_path).read_bytes();vector=json.loads(raw);delivery_checks['vectorReadable']=True
 except (OSError,ValueError):delivery_checks['vectorReadable']=False
 specs=[('apk','/artifacts/pli-pleos-review.apk'),('brief','/docs/pli-pleos-product-brief.pdf')]
 specs=[(kind,path)for kind,path in specs if kind in vector.get('assets',{})]
 if include_media:specs += [('video','/preview.mp4'),('subtitles','/preview.vtt'),('transcript','/preview-transcript.txt')]
 for kind,path in specs:
  delivery_checks[kind+'Http200']=False;delivery_checks[kind+'BytesMatch']=False;digest=hashlib.sha256();size=0
  try:
   expected=vector['assets'][kind]
   with urllib.request.urlopen(url+path,timeout=60)as response:
    delivery_checks[kind+'Http200']=response.status==200
    while chunk:=response.read(1024*1024):digest.update(chunk);size+=len(chunk)
   delivery_checks[kind+'BytesMatch']=digest.hexdigest()==expected['sha256']and size==expected['bytes']
  except (OSError,ValueError,KeyError)as error:errors[kind]=type(error).__name__
  downloads[kind]={'path':path,'bytes':size,'sha256':digest.hexdigest()};print('VERIFIED',kind,size,delivery_checks[kind+'BytesMatch'],flush=True)
 for path in ['/app','/pleos','/resources','/report','/docs/implementation-report.pdf','/artifacts/pli-pleos-source.zip','/family','/api/kidsnote/status','/api/personal/status']:
  try:
   with urllib.request.urlopen(url+path,timeout=15)as response:status=response.status
  except urllib.error.HTTPError as error:status=error.code
  except OSError:status=None
  delivery_checks[('blocked:'if path in ['/report','/docs/implementation-report.pdf','/artifacts/pli-pleos-source.zip','/family','/api/kidsnote/status','/api/personal/status']else'page:')+path]=status==(404 if path in ['/report','/docs/implementation-report.pdf','/artifacts/pli-pleos-source.zip','/family','/api/kidsnote/status','/api/personal/status']else 200)
 if include_media:
  try:
   with urllib.request.urlopen(url+'/api/preview',timeout=15)as response:info=json.load(response)
   delivery_checks['mediaMatchesDeclaredIdentity']=info.get('available')is True and info.get('videoSha256')==vector.get('assets',{}).get('video',{}).get('sha256')and(info.get('type')=='product-story'and info.get('actualAppFootage')is False and info.get('current')is False or info.get('actualAppFootage')is True and info.get('current')is True and info.get('apkSha256')==vector.get('apkSha256'))
  except (OSError,ValueError):delivery_checks['mediaMatchesDeclaredIdentity']=False
 try:delivery_checks['vectorUnchangedDuringCheck']=Path(vector_path).read_bytes()==raw and bool(raw)
 except OSError:delivery_checks['vectorUnchangedDuringCheck']=False
 receipt={'deliverySha256':hashlib.sha256(raw).hexdigest()if raw else None,'apkSha256':vector.get('apkSha256'),'checkedAt':datetime.datetime.now().astimezone().isoformat(),'scope':'Actual product aliases, full HTTPS response bytes, pages and internal/private-route isolation. '+('Includes delivered video, subtitles and transcript; AI commercial identity does not certify native APK behavior.'if include_media else'Excludes video and full product acceptance.'),'includesCurrentMedia':include_media,'checks':delivery_checks,'downloads':downloads,'errors':errors,'elapsedSeconds':round(time.monotonic()-began,3),'passed':bool(delivery_checks)and all(delivery_checks.values())}
 target=Path(receipt_path);temp=target.with_name(target.name+'.'+str(os.getpid())+'.tmp');temp.write_text(json.dumps(receipt,indent=2)+'\n');temp.replace(target);return receipt

def main():
 url=json.loads((ROOT/'.tools/public-config.json').read_text())['url']
 if '--delivery-receipt'in sys.argv:
  receipt=verify_delivery(url,ROOT/'artifacts/review-delivery.json',ROOT/'artifacts/review-delivery-receipt.json','--require-current-media'in sys.argv)
  raise SystemExit(0 if receipt['passed']else 1)
 checks={};metrics={'scope':'Public TLS, routing, privacy, control policy and current media identity; final APK/PDF/source/media bytes require the external delivery receipt.'};record=RunRecord(__file__,checks,metrics)
 def get(path):
  try:
   with urllib.request.urlopen(url+path,timeout=35)as response:return response.status,response.read()
  except urllib.error.HTTPError as error:return error.code,error.read()
 code,body=get('/');checks['publicHttpsValidCertificate']=code==200 and b'/pleos'in body and b'/app'in body
 code,body=get('/api/status');state=json.loads(body);checks['publicProfileIsolated']=code==200 and state['public']and state['profile']=='public'and bool(state['process'])
 checks['noPrivateLogs']=not any(k in state for k in ['events','error'])
 private_codes={}
 for path in ['/family','/api/diagnostics','/live.mjpg','/font.ttf','/.tools/public-config.json','/api/kidsnote/status','/api/personal/status']:
  code=get(path)[0];private_codes[path]=code;checks['blocked:'+path]=None if code>=500 else code==404
 for path,expected in [('/api/input',423),('/api/session/claim',403)]:
  req=urllib.request.Request(url+path,data=b'{"type":"key","key":"home"}',headers={'Content-Type':'application/json','Origin':url if path=='/api/input'else'https://example.com'})
  try:
   urllib.request.urlopen(req,timeout=15).close();actual=200
  except urllib.error.HTTPError as error:actual=error.code
  checks['leaseRequired'if expected==423 else'foreignOriginRejected']=actual==expected
 vector=json.loads((ROOT/'artifacts/review-delivery.json').read_text());checks['publishedCandidateMatchesInstalledApk']=vector['apkSha256']==record.manifest['apkSha256']
 checks['publishedWebMatchesVector']=hashlib.sha256(get('/app.js')[1]).hexdigest()==vector['assets']['web-js']['sha256']
 checks['publishedWebIsCurrentWorkingSource']=vector['assets']['web-js']['sha256']==hashlib.sha256((ROOT/'demo-v2/app.js').read_bytes()).hexdigest()
 loaded=state.get('runtimeRevision',{}).get('sourceSha256',{});modules={'demo-server.py','display_stream.py','delivery_assets.py','runtime_context.py','audio_guard.py','portal_proxy.py'}
 checks['runningServerModulesMatchCurrentSources']=set(loaded)==modules and all(hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()==loaded[name]for name in modules)
 checks['productResourcesReachable']=get('/resources')[0]==200 and get('/report')[0]==404
 resources=json.loads(get('/api/resources')[1]);checks['resourcesContainOnlyProducts']=all(not any(term in str(item).lower()for term in ['audit','defect','implementation-report','source.zip','remediation'])for item in resources)
 info=json.loads(get('/api/preview')[1]);offered='video'in vector.get('assets',{})
 if offered:checks['videoOfferMatchesAvailability']=info.get('available')is True and info.get('videoSha256')==vector['assets']['video']['sha256']and(info.get('type')=='product-story'and info.get('actualAppFootage')is False and info.get('current')is False or info.get('actualAppFootage')is True and info.get('current')is True and info.get('apkSha256')==record.manifest['apkSha256'])
 else:checks['videoOfferMatchesAvailability']=info.get('available')is False and get('/preview.mp4')[0]==404 and not any(item.get('status')in {'VIDEO','TRANSCRIPT'}for item in resources)
 for path in ['/report','/docs/implementation-report.pdf','/docs/UX-AUDIT-2026-11-11.pdf','/docs/REMEDIATION-DESIGN-2026-11-11.pdf','/artifacts/pli-pleos-source.zip','/artifacts/pli-pleos-review-source.zip']:checks['blocked:'+path]=get(path)[0]==404
 old=json.loads((ROOT/'.tools/published/index.json').read_text());checks['historicalInternalHashesBlocked']=all(get(item['href'])[0]==404 for item in old.values()if item.get('kind')not in {'apk','brief','video','subtitles','transcript','web-index','web-js','web-css','web-worklet','web-font','web-poster','web-pleos','preview-manifest'})
 checks['publicPrivacyNotExposed']=False if any(code==200 for path,code in private_codes.items()if path!='/font.ttf')else None if any(code>=500 for path,code in private_codes.items()if path!='/font.ttf')else checks['noPrivateLogs']and checks['resourcesContainOnlyProducts']
 print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
if __name__=='__main__':main()
