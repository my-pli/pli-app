"""Exercise real run failures/cancellation/termination and the report consumer."""
QA_CONTRACT = {'full': {'profile': None,
          'nativeRequired': False,
          'expectedChecks': ['actualAliasBytesWriteBoundReceipt',
                             'actualLauncherRejectsSupersededOwnerBeforeDeviceAccess',
                             'actualParentWaitConsumesFiveTerminalStatesWithoutThirtySecondTimeout',
                             'actualResourceFailureStillQuarantines',
                             'actuallyLoadedAndServedSourcesAreAccepted',
                             'apkMismatchRejected',
                             'archivedProducerBytesAreActuallyPresent',
                             'auxiliaryCleanupDoesNotInvalidateCanonicalScope',
                             'boundPassAccepted',
                             'cancellationFinishesAfterFinally',
                             'cancellationRecorded',
                             'changedCandidateCannotCommitOldSnapshot',
                             'changedPixelProducerInvalidatesNativeClip',
                             'changedRawBytesRejectedBeforeEncoding',
                             'changedRecordingApkCannotBeReused',
                             'changedRecordingFixtureCannotBeReused',
                             'changedRecordingRuntimeCannotBeReused',
                             'claimCannotBypassApkIdentity',
                             'cleanupOnlyHasASeparateClaimFromWholeSuite',
                             'concurrentRunsKeepTheirOwnEvidence',
                             'confirmedSlowStopDoesNotQuarantine',
                             'declaredIndependentClaimAcceptedWithoutPromotingWholeRun',
                             'declaredPublicViewportCannotBeBlockedByPersonalFailure',
                             'defaultRunnerHasNoDeviceEffects',
                             'dependencyImportFailureReplacesOldSuccess',
                             'directProcessesShareExclusiveResource',
                             'emptyExpectedChecksRejected',
                             'emptyFixturesMeansNoAudio',
                             'explicitPlanHasNoDeviceEffects',
                             'failedDownloadReplacesPriorPassReceipt',
                             'failedRecordingCannotBePromoted',
                             'firstStepExceptionReplacesOldSuccess',
                             'fixtureChangeInvalidatesRun',
                             'focusedNativeOwnerCannotReplaceWholeOwnerSuite',
                             'fullWorkBudgetStartsOnlyAfterAdmission',
                             'knownV2NormalEvidenceRetained',
                             'legacyCancellationNotPromoted',
                             'legacyEmptyMeansPaused',
                             'legacyMissingMeansRunning',
                             'missingFixtureDeclarationRejected',
                             'missingFixtureRejected',
                             'missingScreenshotRejected',
                             'mutationWithoutExclusiveAvdRejected',
                             'nativeChangeStillInvalidatesHistoricalEvidence',
                             'newProducerCannotClaimLegacyFormat',
                             'newestCanonicalFailureCannotBeHiddenByOlderPass',
                             'nextCandidateGetsFreshDigest',
                             'notRunNeverTruthyPass',
                             'nullFixtureDeclarationRejected',
                             'oldRunCannotAdmitNextExecution',
                             'oldServedJavascriptCannotCertifyNewWorkingTree',
                             'oldV2CannotAssertNewGuestOwnerBarrier',
                             'oneApkDigestPerEvaluationContext',
                             'ownerProfileAndPublicProfileRemainDistinct',
                             'passedNativeRecordingSurvivesExportOnlyChange',
                             'pointerRotationDuringDownloadCannotBeVerified',
                             'pollingCannotExtendAdmittedWorkBudget',
                             'preEffectFailureCannotQuarantine',
                             'preflightPredecessorSourceIsPreserved',
                             'preflightPredecessorStillNeedsGuestExitBarrier',
                             'publicAndPersonalCleanupRecordsStayDistinct',
                             'readOnlyKilledRunNeedsNoDeviceQuarantine',
                             'reconciledLatestMatchesRun',
                             'resourceQueueCannotConsumeExecutionBudget',
                             'reviewedPreflightPredecessorRetainsNormalEvidence',
                             'scopePlanDoesNotMixOtherChecks',
                             'scriptChangeInvalidatesRun',
                             'serverHashPairCannotWaiveSourceChange',
                             'sigkillReconciled',
                             'sourceMismatchRejected',
                             'staleCleanupCannotChangeNewIntent',
                             'staleLoadedModuleCannotCertifyEditedSource',
                             'stopThenStartInvalidatesOldOwner',
                             'stuckDirectCleanupHasBoundedFailure',
                             'unappliedPublicCodeRejectedBeforeDeviceEffects',
                             'unavailableLegacyProducerNotPromoted',
                             'unchangedLegacySourceCanBeReused',
                             'unconfirmedGuestObligationCannotBecomePass',
                             'unconfirmedRecordingCleanupCannotBeReused',
                             'undeclaredClaimRejected',
                             'unknownArchivedProducerRejected',
                             'unknownLegacyToolRejected',
                             'unknownRecordingProducerCannotBeReused',
                             'unknownResourceRejected',
                             'unknownServerCannotCertifyPrivateConsumer',
                             'unrelatedHelperCannotExpandPlan',
                             'webWrapperChangeDoesNotInvalidateActualNativeClip',
                             'wrongPidCannotAdmitOldEvidence',
                             'coordinatorCannotConsumeSiblingPass',
                             'recycledPidCannotAdoptPreviousProcessEvidence',
                             'supersededCleanupCannotSpawn',
                             'supersededCleanupCannotSendMutation',
                             'supersededCleanupCannotKillAnotherProcess',
                             'changedSelectionRejectedBeforeChildEffects',
                             'producerEditDuringQueueHasNoEffects',
                             'stopStartDuringQueueRejectedBeforeDeviceRead',
                             'unchangedDirectCandidateStillRuns',
                             'actualRunnerRecordsInvalidContractWithoutSecondFailure',
                             'failedDataInvariantPersistsAfterConfirmedClose',
                             'cleanupConfirmationCannotClearDataFailure',
                             'quarantineBlocksOnlyItsActualResource',
                             'frozenContextRejectsChangedApk',
                             'runnerRefreshReadsNewCandidate',
                             'explicitFullCannotHideLatestFailure',
                             'sameScopeAliasesShareFailureHistory',
                             'differentProfilesDoNotShareFailureHistory',
                             'pausedSelectionDoesNotWaitOrReadDevice',
                             'reuseWaitCanBeCancelled',
                             'exportUsesBoundRawInsteadOfUnrelatedCurrentAudio',
                             'literalContractSurvivesJsonRoundTrip',
                             'readOnlyExposureIsPersistedWithoutLosingPreviousIncident',
                             'sameBoundaryPassResolvesExposureButPreservesDataFailure'],
          'safetyChecks': {},
          'inputs': ['qa/native/capture-preview.py',
                     'qa/native/contracts.py',
                     'qa/native/fixtures/before-public-cancel-app.txt',
                     'qa/native/fixtures/before-public-cancel-server.py',
                     'qa/native/fixtures/before-steady-poll-server.py',
                     'qa/native/fixtures/legacy-public-bootstrap-server.py',
                     'qa/native/fixtures/methods-regression.py',
                     'qa/native/fixtures/pre-applied-run-record.py',
                     'qa/native/parent-private.py',
                     'qa/native/public-access.py',
                     'qa/native/run-acceptance.py',
                     'qa/native/run_record.py',
                     'scripts/build-report.py',
                     'scripts/build_identity.py',
                     'scripts/delivery_assets.py',
                     'scripts/package-source.py',
                     'scripts/pleos.py',
                     'scripts/runtime_context.py',
                     'qa/native/fixtures/intent-revocation-probe.py',
                     'qa/native/fixtures/admission-regression.py'],
          'fixtures': [],
          'effects': 'none',
          'resources': [['host-load', 'shared']],
          'executionKind': 'EVIDENCE'}}
from pathlib import Path
import json,os,signal,subprocess,sys,time,runpy,ast,io,tempfile,hashlib,datetime,urllib.request,urllib.error
from unittest.mock import patch
from types import SimpleNamespace
from run_record import RunRecord,reconcile,source_snapshot,archived_producer,compatible_tool,applied_public_source_checks
ROOT=Path(__file__).resolve().parents[2]
COMPATIBLE_NORMAL_V2=APPLIED_SOURCE_PREDECESSOR=hashlib.sha256((ROOT/'qa/native/fixtures/pre-applied-run-record.py').read_bytes()).hexdigest();LEGACY_NORMAL_TOOL='unavailable-legacy-producer'
checks={};metrics={};record=RunRecord(__file__,checks,metrics,dependencies=["scripts/build-report.py","scripts/package-source.py","qa/native/parent-private.py","qa/native/public-access.py","qa/native/run-acceptance.py","qa/native/capture-preview.py","qa/native/fixtures/legacy-public-bootstrap-server.py","qa/native/fixtures/before-public-cancel-server.py","qa/native/fixtures/before-public-cancel-app.txt","qa/native/fixtures/pre-applied-run-record.py","qa/native/fixtures/before-steady-poll-server.py"])
probe=ROOT/'qa/native/_evidence_probe.py';latest=probe.with_suffix('.json')
fixture_probe=ROOT/'qa/native/fixtures/_evidence_probe.wav'
code="QA_CONTRACT = {'full': {'profile': None, 'nativeRequired': False, 'expectedChecks': ['reached', 'finallyCompleted'], 'safetyChecks': {}, 'inputs': [], 'fixtures': [], 'effects': 'none', 'resources': [['host-load', 'shared']], 'executionKind': 'EVIDENCE'}, 'fixture': {'profile': None, 'nativeRequired': False, 'expectedChecks': ['reached', 'finallyCompleted'], 'safetyChecks': {}, 'inputs': [], 'fixtures': ['_evidence_probe.wav'], 'effects': 'none', 'resources': [['host-load', 'shared']], 'executionKind': 'EVIDENCE'}, 'applied': {'profile': 'public', 'nativeRequired': True, 'expectedChecks': ['reached', 'finallyCompleted'], 'safetyChecks': {}, 'inputs': [], 'fixtures': [], 'effects': 'mutate', 'resources': [['host-load', 'shared'], ['public-avd', 'exclusive']], 'executionKind': 'NATIVE_E2E'}}\n"+"""from pathlib import Path
import sys,time
import run_record
if sys.argv[1]=='applied_mismatch':
 import os,io,urllib.request
 os.environ['PLI_QA_PROFILE']='public'
 run_record.resources_for=lambda *args:[('evidence-probe-exclusive','exclusive')]
 run_record.build_matches=lambda:True
 run_record.installed_identity=lambda *args:{'sha256':run_record.sha(run_record.ROOT/'artifacts/pli-pleos.apk')}
 urllib.request.urlopen=lambda url,**kwargs:io.BytesIO(b'{"profile":"public","runtimeRevision":{"sourceSha256":{}}}'if url.endswith('/api/status')else b'stale javascript')
from run_record import RunRecord
if sys.argv[1].startswith('lock'):run_record.resources_for=lambda *args:[('evidence-probe-exclusive','exclusive')]
checks={};r=RunRecord(__file__,checks,execution_kind='NATIVE_E2E'if sys.argv[1]=='applied_mismatch'else'EVIDENCE',fixtures=['_evidence_probe.wav'])
if sys.argv[1].startswith('lock'):
 (r.dir/'admitted').touch()
 if sys.argv[1]=='lock_hold':
  while not (r.dir/'release').exists():time.sleep(.02)
if sys.argv[1]=='hang_cleanup':r.cleanup_budget=.5
if sys.argv[1]=='barrier':r.require_cleanup('guestTermination',lambda:False)
if sys.argv[1]=='fail':raise ValueError('intentional first-step failure')
if sys.argv[1]=='import_fail':import pli_intentionally_missing_dependency
try:
 time.sleep(float(sys.argv[2]))
 checks['reached']=True
finally:
 if sys.argv[1]=='hang_cleanup':time.sleep(20)
 checks['finallyCompleted']=True
 r.confirm_cleanup()
"""
def child(mode,seconds=0):
 probe.write_text(code);p=subprocess.Popen([sys.executable,str(probe),mode,str(seconds)]+(['--scope','applied']if mode=='applied_mismatch'else['--scope','fixture']if fixture_probe.exists()else[]),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 end=time.monotonic()+10
 while time.monotonic()<end:
  try:
   x=json.loads(latest.read_text())
   if x.get('pid')==p.pid:metrics.setdefault('childRuns',[]).append(x['runId']);return p,x['runId']
  except (OSError,ValueError):pass
  time.sleep(.05)
 raise AssertionError('Child did not initialize a new record')
def result(id):return json.loads((ROOT/'qa/native/runs'/id/'result.json').read_text())
try:
 p,id=child('fail');p.wait(timeout=10);r=result(id);checks['firstStepExceptionReplacesOldSuccess']=r['passed']is False and r['error']=='ValueError' and 'NOT_RUN'in r['checks'].values()
 p,id=child('import_fail');p.wait(timeout=10);r=result(id);checks['dependencyImportFailureReplacesOldSuccess']=r['passed']is False and r['error']=='ModuleNotFoundError'and 'NOT_RUN'in r['checks'].values()
 p,id=child('wait',20);p.send_signal(signal.SIGTERM);p.wait(timeout=10);checks['cancellationRecorded']=result(id)['status']=='CANCELLED'
 checks['cancellationFinishesAfterFinally']=result(id)['checks'].get('finallyCompleted')=='PASS'and result(id)['cleanupStatus']=='CONFIRMED'
 p,id=child('hang_cleanup',20);p.send_signal(signal.SIGTERM);p.wait(timeout=5);checks['stuckDirectCleanupHasBoundedFailure']=result(id)['status']=='INCOMPLETE'and result(id)['error']=='CLEANUP_DEADLINE_EXCEEDED'and result(id)['cleanupStatus']=='UNCONFIRMED'
 p,id=child('barrier',0);p.wait(timeout=10);checks['unconfirmedGuestObligationCannotBecomePass']=result(id)['passed']is False and result(id)['cleanupStatus']=='UNCONFIRMED'and result(id)['metrics']['cleanupObligations']['guestTermination']is False
 p,id=child('wait',20);p.kill();p.wait(timeout=10);reconcile();checks['sigkillReconciled']=result(id)['status']=='INCOMPLETE'and result(id)['passed']is False
 checks['reconciledLatestMatchesRun']=json.loads(latest.read_text())['status']=='INCOMPLETE'
 checks['readOnlyKilledRunNeedsNoDeviceQuarantine']=result(id)['cleanupStatus']=='NOT_REQUIRED'
 p,id=child('applied_mismatch',0);p.wait(timeout=10);mismatch=result(id);admission=json.loads((ROOT/'qa/native/runs'/id/'manifest.json').read_text());checks['unappliedPublicCodeRejectedBeforeDeviceEffects']=mismatch['error']=='PRECONDITION_FAILED'and mismatch['passed']is False and mismatch['cleanupStatus']=='NOT_REQUIRED'and admission['effects']is False
 p,id=child('wait',1);probe.write_text(code+'\n# changed during execution\n');p.wait(timeout=10);checks['scriptChangeInvalidatesRun']=result(id)['sourceChanged']is True and result(id)['passed']is False
 p,first=child('wait',1);q,second=child('wait',.3);q.wait(timeout=10);p.wait(timeout=10)
 checks['concurrentRunsKeepTheirOwnEvidence']=first!=second and result(first)['runId']==first and result(second)['runId']==second and json.loads(latest.read_text())['runId']==second
 p,first=child('lock_hold',0)
 while not(ROOT/'qa/native/runs'/first/'admitted').exists():time.sleep(.02)
 q,second=child('lock',.1);time.sleep(.25);blocked=not(ROOT/'qa/native/runs'/second/'admitted').exists()
 (ROOT/'qa/native/runs'/first/'release').touch();q.wait(timeout=10);p.wait(timeout=10)
 checks['directProcessesShareExclusiveResource']=blocked and result(second)['metrics']['resourceWaitSeconds']['evidence-probe-exclusive']>=.1
 fixture_probe.write_bytes(b'evidence-only-fixture-one');p,id=child('wait',1);fixture_probe.write_bytes(b'evidence-only-fixture-two');p.wait(timeout=10);checks['fixtureChangeInvalidatesRun']=result(id)['sourceChanged']is True and result(id)['passed']is False;fixture_probe.unlink()
 runner_tree=ast.parse((ROOT/'qa/native/run-acceptance.py').read_text());profile_node=next(n for n in runner_tree.body if isinstance(n,ast.FunctionDef)and n.name=='target_profile');profile_ns={'ast':ast,'os':os};exec(compile(ast.Module(body=[profile_node],type_ignores=[]),'actual-profile-selector','exec'),profile_ns)
 checks['declaredPublicViewportCannotBeBlockedByPersonalFailure']=profile_ns['target_profile'](ROOT/'qa/native/viewport-recovery.py')=='public'
 checks['ownerProfileAndPublicProfileRemainDistinct']=profile_ns['target_profile'](ROOT/'qa/native/native-instrumentation.py')=='personal'and profile_ns['target_profile'](ROOT/'qa/native/portal-layout.py')=='public'
 deadline_node=next(n for n in runner_tree.body if isinstance(n,ast.FunctionDef)and n.name=='admitted_deadline');deadline_ns={};exec(compile(ast.Module(body=[deadline_node],type_ignores=[]),'actual-admission-budget','exec'),deadline_ns);deadline=deadline_ns['admitted_deadline'];pending={'pid':42,'runId':'new'}
 checks['resourceQueueCannotConsumeExecutionBudget']=deadline(None,pending,{},42,'old',1200,5)is None
 checks['wrongPidCannotAdmitOldEvidence']=deadline(None,{'pid':41,'runId':'new'},{'resources':[]},42,'old',1200,5)is None
 checks['oldRunCannotAdmitNextExecution']=deadline(None,{'pid':42,'runId':'old'},{'resources':[]},42,'old',1200,5)is None
 admitted=deadline(None,pending,{'resources':[]},42,'old',1200,5)
 checks['fullWorkBudgetStartsOnlyAfterAdmission']=admitted==1205
 checks['pollingCannotExtendAdmittedWorkBudget']=deadline(admitted,pending,{'resources':[]},42,'old',1204,5)==1205
 parent_tree=ast.parse((ROOT/'qa/native/parent-private.py').read_text());wait_node=next(n for n in parent_tree.body if isinstance(n,ast.FunctionDef)and n.name=='wait')
 terminal_cases=[{'sessionStatus':'STOPPED'},{'sessionStatus':'ACTIVE','spokenSequence':11,'title':'다시 한번 말해 주세요.'},{'sessionStatus':'ACTIVE','spokenSequence':11,'speech':'지금 새로 확인하지는 못했어요.'},{'sessionStatus':'ACTIVE','spokenSequence':11,'speech':'저장된 일정과 준비물이에요.'},{'sessionStatus':'ACTIVE','spokenSequence':11,'audience':'CHILD','game':'MATH'}]
 terminal_times=[]
 for observed in terminal_cases:
  diagnoses=[];namespace={'time':time,'status':lambda:{'app':observed},'metrics':{},'record':SimpleNamespace(diagnostic=lambda *args:diagnoses.append(args))};exec(compile(ast.Module(body=[wait_node],type_ignores=[]),'actual-parent-wait','exec'),namespace);began=time.monotonic()
  try:namespace['wait'](lambda state:False,30,after=10,reject_cached=True);early=False
  except AssertionError:early=bool(diagnoses)
  terminal_times.append(time.monotonic()-began);assert early
 checks['actualParentWaitConsumesFiveTerminalStatesWithoutThirtySecondTimeout']=all(t<.5 for t in terminal_times)
 metrics['terminalWaitSeconds']=terminal_times
 receipt_tree=ast.parse((ROOT/'qa/native/public-access.py').read_text());verify_node=next(n for n in receipt_tree.body if isinstance(n,ast.FunctionDef)and n.name=='verify_delivery')
 receipt_ns={'Path':Path,'time':time,'os':os,'json':json,'hashlib':hashlib,'datetime':datetime,'urllib':urllib};exec(compile(ast.Module(body=[verify_node],type_ignores=[]),'actual-delivery-receipt','exec'),receipt_ns)
 with tempfile.TemporaryDirectory(prefix='pli-receipt-')as directory:
  folder=Path(directory);vector_path=folder/'vector.json';receipt_path=folder/'receipt.json';payloads={'apk':b'actual-apk-fixture','brief':b'actual-brief-fixture'}
  vector={'apkSha256':hashlib.sha256(payloads['apk']).hexdigest(),'assets':{kind:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}for kind,data in payloads.items()}};vector_raw=json.dumps(vector).encode();vector_path.write_bytes(vector_raw);fault={'apk':False,'rotate':False}
  def fixture_response(url,timeout=None):
   path=urllib.parse.urlsplit(url).path
   if path in ['/report','/docs/implementation-report.pdf','/artifacts/pli-pleos-source.zip','/family','/api/kidsnote/status','/api/personal/status']:raise urllib.error.HTTPError(url,404,'private',None,None)
   if path=='/artifacts/pli-pleos-review.apk'and fault['apk']:raise urllib.error.HTTPError(url,503,'unavailable',None,None)
   if path=='/artifacts/pli-pleos-review.apk'and fault['rotate']:vector_path.write_bytes(vector_raw+b' ')
   key={'/artifacts/pli-pleos-review.apk':'apk','/docs/pli-pleos-product-brief.pdf':'brief'}.get(path)
   response=io.BytesIO(payloads.get(key,b'<html>fixture</html>'));response.status=200;return response
  with patch('urllib.request.urlopen',side_effect=fixture_response):
   good=receipt_ns['verify_delivery']('https://receipt.invalid',vector_path,receipt_path);checks['actualAliasBytesWriteBoundReceipt']=good['passed']is True
   fault['apk']=True;bad=receipt_ns['verify_delivery']('https://receipt.invalid',vector_path,receipt_path);checks['failedDownloadReplacesPriorPassReceipt']=bad['passed']is False and json.loads(receipt_path.read_text())['passed']is False
   fault.update(apk=False,rotate=True);rotated=receipt_ns['verify_delivery']('https://receipt.invalid',vector_path,receipt_path);checks['pointerRotationDuringDownloadCannotBeVerified']=rotated['passed']is False and rotated['checks']['vectorUnchangedDuringCheck']is False
 module=runpy.run_path(str(ROOT/'scripts/build-report.py'));evaluate=module['evaluate'];source=source_snapshot();apk='qualified';m={'recordVersion':2,'executionKind':'NATIVE_E2E','effects':True,'evidenceToolSha256':COMPATIBLE_NORMAL_V2,'buildInputsMatch':True,'runId':'one','source':source,'apkSha256':apk,'installed':{'sha256':apk}};r={'error':None,'cleanupStatus':'CONFIRMED','buildInputsMatch':True,'runId':'one','status':'PASSED','passed':True,'installedMatchesArtifact':True,'sourceChanged':False,'checks':{'one':'PASS'}}
 normal='qa/native/runtime-guard.py';aux={'script':normal,'arguments':['--cleanup-only'],'profile':'public'}
 checks['cleanupOnlyHasASeparateClaimFromWholeSuite']=module['run_key'](aux)!=normal
 checks['focusedNativeOwnerCannotReplaceWholeOwnerSuite']=module['run_key']({'script':'qa/native/native-instrumentation.py','arguments':['--class','RecognitionLocaleTest'],'profile':'personal'})!='qa/native/native-instrumentation.py'
 checks['publicAndPersonalCleanupRecordsStayDistinct']=module['run_key'](aux)!=module['run_key']({**aux,'profile':'personal'})
 with tempfile.TemporaryDirectory(prefix='pli-claim-reader-')as directory:
  base=Path(directory);folder=base/'qa/native/runs'
  for stamp,identity,arguments in [('01','older-pass',[]),('02','newer-failure',[]),('03','cleanup',['--cleanup-only'])]:
   run=folder/identity;run.mkdir(parents=True);(run/'manifest.json').write_text(json.dumps({'script':normal,'arguments':arguments,'startedAt':stamp,'runId':identity,'profile':'personal'}))
  reader=module['latest_runs'];old_root=reader.__globals__['ROOT']
  try:
   reader.__globals__['ROOT']=base;selected=reader()
   checks['newestCanonicalFailureCannotBeHiddenByOlderPass']=selected[normal][2]['runId']=='newer-failure'
   checks['auxiliaryCleanupDoesNotInvalidateCanonicalScope']=len(selected)==2 and any(item[2]['runId']=='cleanup'for item in selected.values())
  finally:reader.__globals__['ROOT']=old_root
 capture_tree=ast.parse((ROOT/'qa/native/capture-preview.py').read_text());capture_nodes=[node for node in capture_tree.body if isinstance(node,ast.FunctionDef)and node.name in {'recording_reusable','recording_sources','sha','finish_recording'}or isinstance(node,ast.Assign)and any(isinstance(target,ast.Name)and target.id=='REVIEWED_RECORDING_PRODUCER'for target in node.targets)];capture_ns={'hashlib':hashlib,'compatible_tool':compatible_tool,'archived_producer':archived_producer};exec(compile(ast.Module(body=capture_nodes,type_ignores=[]),'actual-recording-pipeline','exec'),capture_ns);can_reuse=capture_ns['recording_reusable']
 producer={'recordVersion':2,'executionKind':'NATIVE_E2E','effects':True,'runId':'native-producer','profile':'public','arguments':[],'scriptSha256':json.loads((ROOT/'.tools/private/remediation-source-baseline.json').read_text())['qa/native/capture-preview.py'],'evidenceToolSha256':COMPATIBLE_NORMAL_V2,'apkSha256':'apk','installed':{'sha256':'apk'},'source':{'android/native.kt':'source','scripts/display_stream.py':'display'},'fixtures':{'speech.wav':'fixture'},'buildInputsMatch':True}
 complete={'runId':'native-producer','status':'PASSED','passed':True,'sourceChanged':False,'installedMatchesArtifact':True,'buildInputsMatch':True,'cleanupStatus':'CONFIRMED','checks':{'allEightTasks':'PASS'}}
 recording={'apkSha256':'apk','tasks':list(range(8)),'receipts':list(range(8)),'rawPath':'.tools/exec-evidence/current-preview.webm'};current={**producer,'scriptSha256':'current-export'}
 checks['passedNativeRecordingSurvivesExportOnlyChange']=can_reuse(producer,complete,recording,current)
 checks['failedRecordingCannotBePromoted']=not can_reuse(producer,{**complete,'status':'FAILED'},recording,current)
 checks['unconfirmedRecordingCleanupCannotBeReused']=not can_reuse(producer,{**complete,'cleanupStatus':'UNCONFIRMED'},recording,current)
 checks['changedRecordingApkCannotBeReused']=not can_reuse(producer,complete,recording,{**current,'apkSha256':'other'})
 checks['changedRecordingRuntimeCannotBeReused']=not can_reuse(producer,complete,recording,{**current,'source':{'android/native.kt':'changed','scripts/display_stream.py':'display'}})
 checks['changedRecordingFixtureCannotBeReused']=not can_reuse(producer,complete,recording,{**current,'fixtures':{'speech.wav':'changed'}})
 checks['exportUsesBoundRawInsteadOfUnrelatedCurrentAudio']=can_reuse(producer,complete,recording,{**current,'scope':'export','fixtures':{}})
 checks['unknownRecordingProducerCannotBeReused']=not can_reuse({**producer,'scriptSha256':'unknown'},complete,recording,current)
 checks['webWrapperChangeDoesNotInvalidateActualNativeClip']=can_reuse(producer,complete,recording,{**current,'source':{**current['source'],'demo-v2/app.js':'new-wrapper'}})
 checks['changedPixelProducerInvalidatesNativeClip']=not can_reuse(producer,complete,recording,{**current,'source':{**current['source'],'scripts/display_stream.py':'changed'}})
 scope_before={'scripts/demo-server.py':'original','android/native.kt':'same'};scope_after={**scope_before,'scripts/demo-server.py':'changed'};private_manifest={'script':'qa/native/parent-private.py','profile':'personal','source':scope_before}
 checks['unchangedLegacySourceCanBeReused']=module['source_matches'](private_manifest,scope_before)
 checks['serverHashPairCannotWaiveSourceChange']=not module['source_matches'](private_manifest,scope_after)
 checks['unknownServerCannotCertifyPrivateConsumer']=not module['source_matches'](private_manifest,{**scope_after,'scripts/demo-server.py':'unknown'})
 checks['nativeChangeStillInvalidatesHistoricalEvidence']=not module['source_matches'](private_manifest,{**scope_before,'android/native.kt':'changed'})
 checks['archivedProducerBytesAreActuallyPresent']=archived_producer(COMPATIBLE_NORMAL_V2)is not None
 checks['unknownArchivedProducerRejected']=archived_producer('f'*64)is None
 with tempfile.TemporaryDirectory(prefix='pli-recording-bytes-')as directory:
  root=Path(directory);raw=root/recording['rawPath'];raw.parent.mkdir(parents=True);raw.write_bytes(b'changed raw recording');invocations=[];capture_ns.update(ROOT=root,record=SimpleNamespace(manifest={'apkSha256':'apk'}),subprocess=SimpleNamespace(run=lambda *a,**k:invocations.append(a)))
  try:capture_ns['finish_recording']({**recording,'rawSha256':hashlib.sha256(b'original raw recording').hexdigest()})
  except AssertionError:checks['changedRawBytesRejectedBeforeEncoding']=not invocations
  else:checks['changedRawBytesRejectedBeforeEncoding']=False
 checks['knownV2NormalEvidenceRetained']=evaluate({**r,'error':None,'cleanupStatus':'CONFIRMED'},{**m,'recordVersion':2,'executionKind':'NATIVE_E2E','effects':True,'evidenceToolSha256':COMPATIBLE_NORMAL_V2},apk,source)==[]
 checks['reviewedPreflightPredecessorRetainsNormalEvidence']=evaluate({**r,'error':None,'cleanupStatus':'CONFIRMED'},{**m,'recordVersion':2,'executionKind':'NATIVE_E2E','effects':True,'evidenceToolSha256':APPLIED_SOURCE_PREDECESSOR},apk,source)==[]
 checks['preflightPredecessorStillNeedsGuestExitBarrier']=bool(evaluate({**r,'error':None,'cleanupStatus':'CONFIRMED'},{**m,'recordVersion':2,'executionKind':'NATIVE_OWNER','effects':True,'evidenceToolSha256':APPLIED_SOURCE_PREDECESSOR},apk,source))
 checks['preflightPredecessorSourceIsPreserved']=module['digest'](ROOT/'qa/native/fixtures/pre-applied-run-record.py')==APPLIED_SOURCE_PREDECESSOR
 modules={'demo-server.py','display_stream.py','delivery_assets.py','runtime_context.py','audio_guard.py','portal_proxy.py'};loaded={'profile':'public','runtimeRevision':{'sourceSha256':{name:module['digest'](ROOT/'scripts'/name)for name in modules}}};javascript=(ROOT/'demo-v2/app.js').read_bytes()
 checks['actuallyLoadedAndServedSourcesAreAccepted']=all(applied_public_source_checks(loaded,javascript,ROOT).values())
 checks['oldServedJavascriptCannotCertifyNewWorkingTree']=not applied_public_source_checks(loaded,b'old served bytes',ROOT)['servedJavascriptMatchesWorkingSource']
 checks['staleLoadedModuleCannotCertifyEditedSource']=not applied_public_source_checks({**loaded,'runtimeRevision':{'sourceSha256':{**loaded['runtimeRevision']['sourceSha256'],'demo-server.py':'old'}}},javascript,ROOT)['runningModulesMatchWorkingSources']
 checks['oldV2CannotAssertNewGuestOwnerBarrier']=bool(evaluate({**r,'error':None,'cleanupStatus':'CONFIRMED'},{**m,'recordVersion':2,'executionKind':'NATIVE_OWNER','effects':True,'evidenceToolSha256':COMPATIBLE_NORMAL_V2},apk,source))
 checks['unavailableLegacyProducerNotPromoted']=bool(evaluate({**r,'error':None},{**m,'recordVersion':1,'evidenceToolSha256':LEGACY_NORMAL_TOOL},apk,source))
 checks['newProducerCannotClaimLegacyFormat']=not compatible_tool({**m,'recordVersion':2,'evidenceToolSha256':record.manifest['evidenceToolSha256']},r)
 checks['unknownLegacyToolRejected']=bool(evaluate(r,{**m,'evidenceToolSha256':'unknown'},apk,source))
 checks['legacyCancellationNotPromoted']=bool(evaluate({**r,'status':'CANCELLED','error':'CANCELLED'},{**m,'evidenceToolSha256':LEGACY_NORMAL_TOOL},apk,source))
 claim_manifest={**m,'recordVersion':2,'plannedClaims':{'list':['one']}};claim_result={**r,'status':'FAILED','passed':False,'error':'AssertionError','checks':{'one':'PASS','other':'FAIL'},'claims':{'list':{'status':'PASSED','checks':['one'],'cleanupStatus':'CONFIRMED'}}}
 checks['declaredIndependentClaimAcceptedWithoutPromotingWholeRun']=module['evaluate_claim'](claim_result,claim_manifest,'list',apk,source)==[]and bool(evaluate(claim_result,claim_manifest,apk,source))
 checks['undeclaredClaimRejected']=bool(module['evaluate_claim'](claim_result,claim_manifest,'unknown',apk,source))
 checks['claimCannotBypassApkIdentity']=bool(module['evaluate_claim'](claim_result,claim_manifest,'list','different',source))
 checks['boundPassAccepted']=evaluate(r,m,apk,source)==[]
 checks['notRunNeverTruthyPass']=bool(evaluate({**r,'checks':{'one':'NOT_RUN'}},m,apk,source))
 checks['apkMismatchRejected']=bool(evaluate(r,m,'different',source))
 checks['sourceMismatchRejected']=bool(evaluate(r,m,apk,{}))
 checks['missingFixtureRejected']=bool(evaluate(r,{**m,'fixtures':{'_absent.wav':'unavailable'}},apk,source))
 checks['missingScreenshotRejected']=bool(evaluate({**r,'metrics':{'screenshots':{'qa/native/_absent.png':'unavailable'}}},m,apk,source))
finally:
 probe.unlink(missing_ok=True);latest.unlink(missing_ok=True);fixture_probe.unlink(missing_ok=True)
admission_output=subprocess.check_output([sys.executable,str(ROOT/'qa/native/fixtures/admission-regression.py')],cwd=ROOT,text=True);checks.update(json.loads(admission_output.splitlines()[-1])['admissionChecks'])
revoked=json.loads(subprocess.check_output([sys.executable,str(ROOT/'qa/native/fixtures/intent-revocation-probe.py')],cwd=ROOT,text=True));checks.update(revoked)
method_output=subprocess.check_output([sys.executable,str(ROOT/'qa/native/fixtures/methods-regression.py')],cwd=ROOT,text=True);checks.update(json.loads(method_output.splitlines()[-1])['methodChecks'])
print(json.dumps(checks));assert all(checks.values())
