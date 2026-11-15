"""Actual file handler: first checkout works without a publication, unsafe APK IDs fail closed."""
QA_CONTRACT = {'full': {'profile': None,
          'nativeRequired': False,
          'expectedChecks': ['activeSessionCannotResetSpeechEngine',
                             'actualViewerCapacityBranchRejectsThirteenthViewer',
                             'cancelledLateClaimCannotPrepareOrRetainLease',
                             'cancelledPreparationCannotBeginOrOverwriteStoppedState',
                             'cancelledReaderCannotCancelAnotherReadersDeviceRead',
                             'cancelledSetupCannotOpenMicrophoneAfterEndAck',
                             'currentActiveSpeechStillRequiresAudibleOutput',
                             'endAndPrepareSerializeNativeMutations',
                             'fastPollingIsLimitedToPublicVoice',
                             'freshAppCacheStillAccepted',
                             'freshNativeAndConsoleAgreementAvoidsDuplicateRead',
                             'heartbeatDoesNotInvalidateStateRead',
                             'homepageWithoutDelivery',
                             'housekeeperCannotDuplicateAnOwnedPendingEnd',
                             'missingDeliveryOnlyBlocksApk',
                             'nativeActualAckAccepted',
                             'nativeConsoleDisagreementStillRequiresConfirmation',
                             'nativeEmptyAckRejected',
                             'nativeStderrErrorRejected',
                             'newBootCanStartItsOwnRevision',
                             'newIdleProcessWithoutReceiptCanResetItsIsolatedSpeechEngine',
                             'newerSocketSnapshotIsApplied',
                             'olderSocketSnapshotCannotReplaceNewerState',
                             'personalEngineCannotBeResetByPublicPreparation',
                             'postCommandReadCannotReusePreCommandSnapshot',
                             'previousSessionSpeechCannotKillNewConnection',
                             'privateModeMarkerRevokedBeforeNativeView',
                             'privateProfileCannotBecomePublicPixelSource',
                             'privateStartStillPreparesAfterMarkerRevocation',
                             'privateStartUsesFreshProviderWhenBootCacheIsEmpty',
                             'privateVoiceStateCannotEnterPublicSocket',
                             'publicSocketRemovesBothSessionIdentifiers',
                             'receiptMissingWithActualVoiceProcessCannotResetSpeech',
                             'recoveryBlocksNewRuntimeCommands',
                             'repeatedPrivateStopIsIdempotent',
                             'reviewDownloadRequiresExplicitReviewChannel',
                             'reviewDownloadUsesItsOwnImmutableArtifact',
                             'sendOnlyVideoConsumesHeartbeatPongsWithoutDisconnecting',
                             'simultaneousClaimsCannotBothObserveAnEmptyLease',
                             'simultaneousReadOnlyPollsShareOneDeviceRead',
                             'staleAppCacheCannotStartEncoderOrFallback',
                             'stopDuringPendingPersonalStartCannotCreateLateMicrophone',
                             'stoppedOrPreparingSpeechIsNotCurrentOutput',
                             'unavailablePinnedApkRejected',
                             'unsafeArtifactIdentityRejected',
                             'unsuppliedSnapshotStillUsesActualConfirmation',
                             'vehicleActualSignalAccepted',
                             'vehicleConsoleAckWithoutSignalFailsAndRecovers',
                             'videoDisconnectReleasesActualSubscription'],
          'safetyChecks': {},
          'inputs': ['demo-v2/app.js',
                     'qa/native/fixtures/bootstrap-races.mjs',
                     'qa/native/fixtures/privacy-boundary.py',
                     'scripts/audio_guard.py',
                     'scripts/delivery_assets.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/emulator_proto/__init__.py',
                     'scripts/emulator_proto/emulator_controller_pb2.py',
                     'scripts/emulator_proto/emulator_controller_pb2_grpc.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': [],
          'effects': 'none',
          'resources': [['host-load', 'shared']],
          'executionKind': 'HOST_CONTRACT'}}
from pathlib import Path
import json,subprocess
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics,dependencies=['demo-v2/app.js','qa/native/fixtures/bootstrap-races.mjs'])
code="""import asyncio,importlib.util,sys,os,tempfile,json
from pathlib import Path
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
sys.path.insert(0,'scripts');os.environ.setdefault('PLI_TAILSCALE_IP','127.0.0.1')
s=importlib.util.spec_from_file_location('pli_server_contract','scripts/demo-server.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.serial=lambda:'synthetic';snapshot_impl=m.native_snapshot;session_impl=m.native_session
async def main():
 with tempfile.TemporaryDirectory(prefix='pli-publication-')as folder:
  m.ROOT=Path(folder);m.RUN_TOOLS=m.ROOT/'.tools';m.RUN_TOOLS.mkdir();(m.ROOT/'artifacts').mkdir()
  home=await m.file(make_mocked_request('GET','/'));result={'homepageWithoutDelivery':home.status==200}
  async def blocked(path='/artifacts/pli-pleos.apk'):
   try:await m.file(make_mocked_request('GET',path));return False
   except web.HTTPNotFound:return True
  result['missingDeliveryOnlyBlocksApk']=await blocked()
  (m.ROOT/'artifacts/delivery.json').write_text(json.dumps({'apkSha256':'../../private'}));result['unsafeArtifactIdentityRejected']=await blocked()
  (m.ROOT/'artifacts/delivery.json').write_text(json.dumps({'apkSha256':'a'*64}));result['unavailablePinnedApkRejected']=await blocked()
  candidate=m.ROOT/'artifacts/review-delivery.json';candidate.write_text(json.dumps({'channel':'release','apkSha256':'a'*64}));result['reviewDownloadRequiresExplicitReviewChannel']=await blocked('/artifacts/pli-pleos-review.apk')
  pinned=m.ROOT/'.tools/published'/('a'*64+'.apk');pinned.parent.mkdir(parents=True);pinned.write_bytes(b'isolated artifact fixture');candidate.write_text(json.dumps({'channel':'review','apkSha256':'a'*64,'acceptanceComplete':False}));response=await m.file(make_mocked_request('GET','/artifacts/pli-pleos-review.apk'));result['reviewDownloadUsesItsOwnImmutableArtifact']=response._path==pinned and response.headers.get('X-Pli-Artifact-Channel')=='review'
  import io,time
  from PIL import Image
  buffer=io.BytesIO();Image.new('RGB',(4,4),'green').save(buffer,'JPEG');m.native={'presentation':True,'demo':True,'visible':True};m.screen.jpeg=buffer.getvalue();m.screen.updated=time.monotonic()-.7
  result['staleAppCacheCannotStartEncoderOrFallback']=m.screen.app_frame()is None
  m.screen.updated=time.monotonic();result['freshAppCacheStillAccepted']=m.screen.app_frame()is not None
  from display_stream import PublicDisplay
  from runtime_context import DeviceContext
  try:PublicDisplay(DeviceContext('personal'));result['privateProfileCannotBecomePublicPixelSource']=False
  except ValueError:result['privateProfileCannotBecomePublicPixelSource']=True
  real_command=m.command
  async def stderr_failure(*args,**kwargs):return await real_command(sys.executable,'-c',"import sys;sys.stderr.write('Error while accessing provider: IllegalStateException: SESSION_MISMATCH')",**kwargs)
  m.command=stderr_failure
  try:await m.native_session('heartbeat','synthetic');result['nativeStderrErrorRejected']=False
  except m.DeviceUnavailable:result['nativeStderrErrorRejected']=True
  async def empty_ack(*args,**kwargs):return await real_command(sys.executable,'-c','pass',**kwargs)
  m.command=empty_ack
  try:await m.native_session('heartbeat','synthetic');result['nativeEmptyAckRejected']=False
  except m.DeviceUnavailable:result['nativeEmptyAckRejected']=True
  async def success_ack(*args,**kwargs):return await real_command(sys.executable,'-c',"print('Result: Bundle[{status=PREPARING}]')",**kwargs)
  m.command=success_ack;await m.native_session('heartbeat','synthetic');result['nativeActualAckAccepted']=True
  class ReadAck:
   status=200
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   def raise_for_status(self):pass
   async def json(self):return {'gear':{'actual':{'value':'Park'}},'controls':{'speed_kph':0}}
   async def read(self):return b'{}'
  class FixtureConsole:
   def __init__(self,*args,**kwargs):pass
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   def get(self,*args,**kwargs):return ReadAck()
   def put(self,*args,**kwargs):return ReadAck()
  m.ClientSession=FixtureConsole
  async def parked():return {'gear':'P','speedKmh':0}
  m.native_snapshot=parked;await m.confirm_vehicle_signal('park');result['vehicleActualSignalAccepted']=True
  active={'sessionStatus':'ACTIVE','sessionId':'current','spokenSequence':1}
  result['currentActiveSpeechStillRequiresAudibleOutput']=m.current_tts_expected(active,{'status':'ACTIVE','nativeId':'current'})
  result['previousSessionSpeechCannotKillNewConnection']=not m.current_tts_expected({**active,'sessionId':'previous'},{'status':'ACTIVE','nativeId':'current'})
  result['stoppedOrPreparingSpeechIsNotCurrentOutput']=not m.current_tts_expected({**active,'sessionStatus':'STOPPED'},{'status':'ACTIVE','nativeId':'current'})and not m.current_tts_expected(active,{'status':'PREPARING','nativeId':'current'})
  result['privateVoiceStateCannotEnterPublicSocket']=m.public_app_snapshot({'demo':False,'profile':{'name':'private'}})=={}
  public=m.public_app_snapshot({'demo':True,'sessionId':'hidden','stopReceipt':{'sessionId':'hidden','captureStopped':True}})
  result['publicSocketRemovesBothSessionIdentifiers']='sessionId'not in public and 'sessionId'not in public['stopReceipt']and public['stopReceipt']['captureStopped']
  import types
  saved_context=m.CONTEXT;saved_confirm=m.confirm_vehicle_signal;saved_client=m.ClientSession;confirmed=[]
  class CleanAck(ReadAck):
   async def json(self):return {'gear':{'actual':{'value':'Park'}},'controls':{'speed_kph':0},'body':{'wipers':{'front':{'mode':'Off'}},'doors':{'rear_left':False}},'lights':{'turn_signal_mode':'Off'},'ev_battery':{'charging_activated':False}}
  class CleanConsole(FixtureConsole):
   def get(self,*args,**kwargs):return CleanAck()
  async def confirm_again(action):confirmed.append(action)
  m.CONTEXT=types.SimpleNamespace(profile='public',console_port=18088,assert_owned=lambda:123);m.ClientSession=CleanConsole;m.confirm_vehicle_signal=confirm_again
  await m.reset_public_vehicle({'sessionStatus':'STOPPED','gear':'P','speedKmh':0});result['freshNativeAndConsoleAgreementAvoidsDuplicateRead']=not confirmed
  await m.reset_public_vehicle({'sessionStatus':'STOPPED','gear':'D','speedKmh':0});result['nativeConsoleDisagreementStillRequiresConfirmation']=confirmed==['park']
  await m.reset_public_vehicle();result['unsuppliedSnapshotStillUsesActualConfirmation']=confirmed==['park','park']
  m.CONTEXT=saved_context;m.confirm_vehicle_signal=saved_confirm;m.ClientSession=saved_client
  original_claim=m.claim_session_locked;entered_claim=asyncio.Event();release_claim=asyncio.Event();claim_order=[]
  async def held_claim(request):
   claim_order.append('start-'+request)
   if request=='one':entered_claim.set();await release_claim.wait()
   claim_order.append('end-'+request);return request
  m.claim_session_locked=held_claim;one=asyncio.create_task(m.session_claim('one'));await entered_claim.wait();two=asyncio.create_task(m.session_claim('two'));await asyncio.sleep(.01);queued=claim_order==['start-one'];release_claim.set();await asyncio.gather(one,two);m.claim_session_locked=original_claim
  result['simultaneousClaimsCannotBothObserveAnEmptyLease']=queued and claim_order==['start-one','end-one','start-two','end-two']
  saved={name:getattr(m,name)for name in ['CONTEXT','lease','lease_info','native','native_updated','native_snapshot','native_session','reset_idle_public_speech','prime','recover_audio','require_control_origin','public_start_generation']}
  setup_entered=asyncio.Event();continue_setup=asyncio.Event();native_calls=[]
  stopped_state={'demo':True,'visible':True,'hasView':True,'sessionStatus':'STOPPED','capture':'STOPPED','playback':'IDLE','focus':'NONE','sessionId':None}
  state=dict(stopped_state)
  async def setup_snapshot():return dict(state)
  async def delayed_setup(value):setup_entered.set();await continue_setup.wait()
  async def setup_command(action,target=None):
   native_calls.append(action)
   if action=='prepare':state.update(sessionId=target,sessionStatus='ACTIVE',capture='ACTIVE',modelReady=True,ttsReady=True)
   elif action=='end':state.update(stopped_state)
  m.CONTEXT=types.SimpleNamespace(profile='public');m.lease={'nativeId':'owned','ending':False,'status':'CLAIMED','voice':False};m.lease_info=lambda request:{'mine':True};m.native=dict(stopped_state);m.native_updated=0;m.native_snapshot=setup_snapshot;m.native_session=setup_command;m.reset_idle_public_speech=delayed_setup;m.prime=lambda:None;m.recover_audio=lambda:None;m.require_control_origin=lambda request:None;m.public_start_generation=0
  preparing=asyncio.create_task(m.session_prepare(types.SimpleNamespace()));await asyncio.wait_for(setup_entered.wait(),1);ending=asyncio.create_task(m.end_native_session('owned'));await asyncio.sleep(.01);stop_waited=not ending.done();continue_setup.set()
  try:await asyncio.wait_for(preparing,1);cancelled_setup=False
  except m.SessionLocked:cancelled_setup=True
  actual_end=await asyncio.wait_for(ending,1)
  result['endAndPrepareSerializeNativeMutations']=stop_waited
  result['cancelledSetupCannotOpenMicrophoneAfterEndAck']=cancelled_setup and 'prepare'not in native_calls and actual_end['sessionStatus']=='STOPPED'
  for name,value in saved.items():setattr(m,name,value)
  saved={name:getattr(m,name)for name in ['lease','native','recovery_task','lease_runtime_changed','recover_speech_engine_if_stopped','queue_public_view_restore','audio_owner','recover_audio','end_native_session']}
  duplicate_ends=[]
  async def duplicate_end(*args,**kwargs):duplicate_ends.append(args)
  async def no_recovery():pass
  m.lease={'owner':'owned','ending':True,'status':'STOPPING','voice':True,'nativeId':'owned','expires':time.monotonic()+30};m.native={'sessionStatus':'STOPPED','sessionId':'owned'};m.recovery_task=None;m.lease_runtime_changed=lambda:False;m.recover_speech_engine_if_stopped=no_recovery;m.queue_public_view_restore=lambda:None;m.audio_owner=None;m.recover_audio=lambda:None;m.end_native_session=duplicate_end
  keeper=asyncio.create_task(m.housekeeping());await asyncio.sleep(.03);keeper.cancel()
  try:await keeper
  except asyncio.CancelledError:pass
  result['housekeeperCannotDuplicateAnOwnedPendingEnd']=not duplicate_ends
  for name,value in saved.items():setattr(m,name,value)
  async def unchanged():return {'gear':'D','speedKmh':0}
  m.native_snapshot=unchanged
  class Ack:
   status=200
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   async def read(self):return b'{"actual":{"value":"Park"}}'
  class Console:
   def __init__(self,*args,**kwargs):pass
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   def put(self,*args,**kwargs):return Ack()
   def get(self,*args,**kwargs):return FixtureConsole().get()
  m.ClientSession=Console
  async def body(request):return {'action':'park'}
  m.control_body=body;m.require_lease=lambda request:None;original_runtime=m.require_runtime;m.require_runtime=lambda:None;recovery=[];m.request_recovery=lambda stop_first=False:recovery.append(stop_first)
  try:await m.vehicle_control(make_mocked_request('POST','/api/vehicle'));result['vehicleConsoleAckWithoutSignalFailsAndRecovers']=False
  except web.HTTPBadGateway:result['vehicleConsoleAckWithoutSignalFailsAndRecovers']=recovery==[True]
  m.require_runtime=original_runtime;m.cached['process']='synthetic';m.recovery_task=asyncio.create_task(asyncio.sleep(60))
  try:m.require_runtime();result['recoveryBlocksNewRuntimeCommands']=False
  except m.DeviceUnavailable:result['recoveryBlocksNewRuntimeCommands']=True
  m.recovery_task.cancel()
  try:await m.recovery_task
  except asyncio.CancelledError:pass
  from types import SimpleNamespace
  marker=m.RUN_TOOLS/'portal-mode';marker.touch();m.native={'demo':True,'visible':True,'hasView':True,'sessionStatus':'STOPPED'}
  m.owner_request=lambda request:True;m.require_control_origin=lambda request:None;m.require_runtime=lambda:None
  async def actual_state():return m.native
  transitions=[]
  async def session(action,*args,**kwargs):
   transitions.append(action)
   if action=='private':result['privateModeMarkerRevokedBeforeNativeView']=not marker.exists();m.native.update(demo=False)
   if action=='personal':m.native.update(sessionStatus='PREPARING')
  async def shown():pass
  async def start_body():return {'action':'start'}
  m.native_snapshot=actual_state;m.native_session=session;m.show_app=shown;m.CONTEXT=SimpleNamespace(assert_owned=lambda:123);m.cached['process']=None
  reply=await m.kids_personal(SimpleNamespace(json=start_body,cookies={}))
  result['privateStartUsesFreshProviderWhenBootCacheIsEmpty']=m.cached['process']is None and transitions==['private','personal']
  result['privateStartStillPreparesAfterMarkerRevocation']=json.loads(reply.text)['status']=='PREPARING'and transitions==['private','personal']
  m.native.update(demo=True,sessionStatus='STOPPED');m.recover_audio=lambda:None
  async def stop_body():return {'action':'stop'}
  reply=await m.kids_personal(SimpleNamespace(json=stop_body,cookies={}))
  result['repeatedPrivateStopIsIdempotent']=reply.status==200 and json.loads(reply.text)['status']=='STOPPED'and marker.exists()
  entered=asyncio.Event();release=asyncio.Event();personal_calls=[];held_once=False
  m.native={'sessionStatus':'STOPPED','capture':'STOPPED','playback':'IDLE','focus':'NONE','demo':True,'visible':True,'hasView':True}
  async def personal_snapshot():return dict(m.native)
  async def personal_command(action,*args,**kwargs):
   personal_calls.append(action)
   if action=='private':m.native['demo']=False
   elif action=='preview':m.native['demo']=True
   elif action=='personal':m.native.update(sessionStatus='ACTIVE',capture='ACTIVE')
  async def personal_show(*args,**kwargs):
   nonlocal held_once
   if not held_once:held_once=True;entered.set();await release.wait()
  async def personal_end(*args,**kwargs):m.native.update(sessionStatus='STOPPED',capture='STOPPED');return dict(m.native)
  m.native_snapshot=personal_snapshot;m.native_session=personal_command;m.show_app=personal_show;m.end_native_session=personal_end;m.recovery_task=None;m.audio_owner=None;m.lease_info=lambda request:{'busy':False}
  async def starting_body():return {'action':'start'}
  start=asyncio.create_task(m.kids_personal(SimpleNamespace(json=starting_body,cookies={})));await entered.wait()
  stop=asyncio.create_task(m.kids_personal(SimpleNamespace(json=stop_body,cookies={})));await asyncio.sleep(.01);release.set()
  try:await start;cancelled=False
  except web.HTTPConflict:cancelled=True
  stopped=await stop
  result['stopDuringPendingPersonalStartCannotCreateLateMicrophone']=cancelled and 'personal'not in personal_calls and m.native['sessionStatus']=='STOPPED'and json.loads(stopped.text)['status']=='STOPPED'
  m.CONTEXT=SimpleNamespace(profile='public',assert_owned=lambda:123)
  calls=[]
  async def idle_engine_command(*args,**kwargs):
   calls.append(args);return b'ai.teammoon.pli\\n'if 'ps'in args else b''
  m.command=idle_engine_command
  clean={'sessionStatus':'STOPPED','capture':'STOPPED','playback':'IDLE','focus':'NONE','sessionId':None,'serviceInstanceId':None}
  result['newIdleProcessWithoutReceiptCanResetItsIsolatedSpeechEngine']=await m.reset_idle_public_speech(clean)and any('force-stop'in x for x in calls)
  async def live_process(*args,**kwargs):return b'ai.teammoon.pli:voice\\n'
  m.command=live_process
  result['receiptMissingWithActualVoiceProcessCannotResetSpeech']=not await m.reset_idle_public_speech(clean)
  result['activeSessionCannotResetSpeechEngine']=not await m.reset_idle_public_speech({**clean,'sessionStatus':'ACTIVE'})
  m.CONTEXT=SimpleNamespace(profile='personal',assert_owned=lambda:123)
  result['personalEngineCannotBeResetByPublicPreparation']=not await m.reset_idle_public_speech(clean)
  m.CONTEXT=DeviceContext('public');m.encoded_sources={'app':SimpleNamespace(subscribers=set(range(12)))}
  reply=await m.video(SimpleNamespace(query={'surface':'app'}))
  result['actualViewerCapacityBranchRejectsThirteenthViewer']=reply.status==503 and json.loads(reply.text)['code']=='VIEWER_LIMIT'
  from aiohttp.test_utils import TestServer,TestClient
  class VideoFixture:
   def __init__(self):self.subscribers=set();self.task=None
   async def subscribe(self):
    q=asyncio.Queue();self.subscribers.add(q)
    async def frames():
     while True:
      await q.put(('frame',b'fixture',{'source':'pleos','sourceSeq':1}));await asyncio.sleep(.01)
    self.task=asyncio.create_task(frames());return q
   def unsubscribe(self,q):self.subscribers.discard(q);self.task.cancel()
  fake=VideoFixture();m.encoded_sources={'pleos':fake}
  original_ws=m.web.WebSocketResponse
  m.web.WebSocketResponse=lambda **kw:original_ws(**{**kw,'heartbeat':.08})
  app=m.web.Application();app.router.add_get('/video',m.video)
  async with TestClient(TestServer(app))as client:
   ws=await client.ws_connect('/video?surface=pleos');began=time.monotonic();count=0
   while time.monotonic()-began<.4:
    message=await ws.receive(timeout=1)
    if message.type in {m.WSMsgType.CLOSED,m.WSMsgType.CLOSE,m.WSMsgType.ERROR}:break
    count+=1
   result['sendOnlyVideoConsumesHeartbeatPongsWithoutDisconnecting']=count>=20 and not ws.closed
   await ws.close()
  m.web.WebSocketResponse=original_ws
  result['videoDisconnectReleasesActualSubscription']=not fake.subscribers
  saved={name:getattr(m,name)for name in ['command','accept_native','native_snapshot','native_session','native_read_task','native_read_generation','native_command_generation']}
  m.accept_native=lambda value,order:value;m.native_snapshot=snapshot_impl;m.native_session=session_impl
  m.native_read_task=None;m.native_read_generation=-1;m.native_command_generation=0
  entered=asyncio.Event();release=asyncio.Event();reads=0
  async def shared_read(*args,**kwargs):
   nonlocal reads
   reads+=1;entered.set();await release.wait();return b'{"version":"current"}'
  m.command=shared_read;first=asyncio.create_task(m.native_snapshot(coalesce=True));await asyncio.wait_for(entered.wait(),1);second=asyncio.create_task(m.native_snapshot(coalesce=True));await asyncio.sleep(.01);one_read=reads==1;release.set();values=await asyncio.gather(first,second)
  result['simultaneousReadOnlyPollsShareOneDeviceRead']=one_read and reads==1 and values[0]==values[1]
  m.native_read_task=None;m.native_read_generation=-1;m.native_command_generation=0;reads=0;model='old';old_entered=asyncio.Event();old_release=asyncio.Event();new_entered=asyncio.Event();new_release=asyncio.Event()
  async def changing_read(*args,**kwargs):
   nonlocal reads,model
   if 'exec-out'in args:
    reads+=1;value=model
    if reads==1:old_entered.set();await old_release.wait()
    elif reads==2:new_entered.set();await new_release.wait()
    return json.dumps({'version':value}).encode()
   if 'begin'in args:model='new'
   return b'Result: Bundle[{status=ACTIVE}]'
  m.command=changing_read;first=asyncio.create_task(m.native_snapshot(coalesce=True));await asyncio.wait_for(old_entered.wait(),1);await m.native_session('begin','owned');second=asyncio.create_task(m.native_snapshot());old_release.set();await asyncio.wait_for(new_entered.wait(),1);await asyncio.sleep(.01);new_release.set();values=await asyncio.gather(first,second)
  result['postCommandReadCannotReusePreCommandSnapshot']=reads==2 and all(value['version']=='new'for value in values)
  before_heartbeat=m.native_command_generation;await m.native_session('heartbeat','owned');result['heartbeatDoesNotInvalidateStateRead']=m.native_command_generation==before_heartbeat
  m.native_read_task=None;m.native_read_generation=-1;m.native_command_generation=0;entered=asyncio.Event();release=asyncio.Event();reads=0;m.command=shared_read
  first=asyncio.create_task(m.native_snapshot(coalesce=True));await asyncio.wait_for(entered.wait(),1);second=asyncio.create_task(m.native_snapshot(coalesce=True));await asyncio.sleep(.01);first.cancel()
  try:await first
  except asyncio.CancelledError:pass
  survived=not m.native_read_task.cancelled();release.set();await asyncio.wait_for(second,1);result['cancelledReaderCannotCancelAnotherReadersDeviceRead']=survived and reads==1
  result['fastPollingIsLimitedToPublicVoice']=m.native_poll_interval('public',True,{'spokenSequence':0})==.2 and m.native_poll_interval('public',True,{'spokenSequence':1,'playback':'PLAYING'})==.2 and m.native_poll_interval('public',True,{'spokenSequence':2,'playback':'PLAYING'})==.3 and m.native_poll_interval('public',False,{'spokenSequence':2})==1 and m.native_poll_interval('personal',True,{'spokenSequence':0})==1
  for name,value in saved.items():setattr(m,name,value)
  print(json.dumps(result))
asyncio.run(main())
"""
r=subprocess.run([str(ROOT/'.tools/demo-venv/bin/python'),'-c',code],cwd=ROOT,capture_output=True,text=True)
if r.returncode:raise AssertionError(r.stderr[-600:])
checks.update(json.loads(r.stdout))
js=r"""const fs=require('fs'),vm=require('vm');const source=fs.readFileSync('demo-v2/app.js','utf8');const fn=source.split('\n').find(x=>x.startsWith('function acceptAppSnapshot('));const box={state:{status:{app:{bootId:'same',stateRevision:10}}},render:()=>{}};vm.createContext(box);vm.runInContext(fn,box);vm.runInContext("acceptAppSnapshot({bootId:'same',stateRevision:9})",box);const stale=box.state.status.app.stateRevision===10;vm.runInContext("acceptAppSnapshot({bootId:'same',stateRevision:11})",box);const newer=box.state.status.app.stateRevision===11;vm.runInContext("acceptAppSnapshot({bootId:'new',stateRevision:1})",box);console.log(JSON.stringify({olderSocketSnapshotCannotReplaceNewerState:stale,newerSocketSnapshotIsApplied:newer,newBootCanStartItsOwnRevision:box.state.status.app.bootId==='new'}));"""
checks.update(json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT)))
checks.update(json.loads(subprocess.check_output(['node','qa/native/fixtures/bootstrap-races.mjs'],cwd=ROOT)));print(json.dumps(checks));assert all(checks.values())
