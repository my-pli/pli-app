"""Counterexamples for plan, effect admission, evidence and intent boundaries."""
from pathlib import Path
import ast,copy,hashlib,json,os,runpy,subprocess,sys,tempfile,fcntl,threading,time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'qa/native'),str(ROOT/'scripts')]
from contracts import declared_contract,unsafe_resources
from runtime_context import runtime_intent,set_runtime_intent,intent_current
checks={}
base={'profile':None,'nativeRequired':False,'expectedChecks':['one'],'safetyChecks':{},'inputs':[],'fixtures':[],'effects':'none','resources':[['host-load','shared']],'executionKind':'EVIDENCE'}
with tempfile.TemporaryDirectory(prefix='pli-methods-')as folder:
 root=Path(folder);owner=root/'owner.py'
 def declare(value):owner.write_text('QA_CONTRACT = '+repr(value)+'\n')
 declare({'full':base});checks['emptyFixturesMeansNoAudio']=declared_contract(owner)['fixtures']==[]
 for name,contract in [('missingFixtureDeclaration',{k:v for k,v in base.items()if k!='fixtures'}),('nullFixtureDeclaration',{**base,'fixtures':None}),('emptyExpectedChecks',{**base,'expectedChecks':[]}),('unknownResource',{**base,'resources':[['invented','exclusive']]}),('mutationWithoutExclusiveAvd',{**base,'profile':'public','nativeRequired':True,'effects':'mutate'})]:
  declare({'full':contract})
  try:declared_contract(owner);checks[name+'Rejected']=False
  except ValueError:checks[name+'Rejected']=True
 declare({'full':base,'other':{**base,'expectedChecks':['different']}});checks['scopePlanDoesNotMixOtherChecks']=declared_contract(owner)['expectedChecks']==['one']and declared_contract(owner,['--scope','other'])['expectedChecks']==['different']
 declare({'full':base});owner.write_text(owner.read_text()+"\ndef unrelated():\n checks={}\n checks['helperOnly']=False\n")
 checks['unrelatedHelperCannotExpandPlan']=declared_contract(owner)['expectedChecks']==['one']
 declare({'full':{**base,'resources':[('host-load','shared')]}});resolved=declared_contract(owner);checks['literalContractSurvivesJsonRoundTrip']=resolved==json.loads(json.dumps(resolved))
 marker=root/'runtime-paused';checks['legacyMissingMeansRunning']=runtime_intent(root)=={'desiredState':'running','generation':0};marker.touch();checks['legacyEmptyMeansPaused']=runtime_intent(root)['desiredState']=='paused'
 paused=set_runtime_intent(root,'paused');running=set_runtime_intent(root,'running');checks['stopThenStartInvalidatesOldOwner']=running['generation']>paused['generation']and not intent_current(root,paused['generation'])
 try:set_runtime_intent(root,'paused',expected_generation=paused['generation']);checks['staleCleanupCannotChangeNewIntent']=False
 except RuntimeError:checks['staleCleanupCannotChangeNewIntent']=runtime_intent(root)==running
 api=runpy.run_path(str(ROOT/'scripts/pleos.py'));launch=api['launch'];saved=launch.__globals__.copy()
 try:
  launch.__globals__['TOOLS']=root;launch.__globals__['ENV']={**os.environ,'PLI_QA_INTENT_GENERATION':str(paused['generation'])}
  try:launch(no_build=True);checks['actualLauncherRejectsSupersededOwnerBeforeDeviceAccess']=False
  except RuntimeError as e:checks['actualLauncherRejectsSupersededOwnerBeforeDeviceAccess']=str(e)=='RUNTIME_INTENT_CHANGED'
 finally:launch.__globals__.update(saved)
 # Exercise the actual context cache on an isolated mutable file.
 report=runpy.run_path(str(ROOT/'scripts/build-report.py'));Context=report['EvaluationContext'];globals_=Context.__init__.__globals__;prior=dict(globals_)
 try:
  globals_['ROOT']=root;globals_['source_snapshot']=lambda:{};globals_['latest_runs']=lambda:{}
  apk=root/'artifacts/pli-pleos.apk';apk.parent.mkdir();apk.write_bytes(b'candidate A');context=Context();one=context.apk
  for _ in range(33):assert context.apk==one
  checks['oneApkDigestPerEvaluationContext']=context.digestReads[str(apk)]==1
  apk.write_bytes(b'candidate B')
  try:context.assert_inputs_unchanged();checks['changedCandidateCannotCommitOldSnapshot']=False
  except RuntimeError:checks['changedCandidateCannotCommitOldSnapshot']=True
  checks['nextCandidateGetsFreshDigest']=Context().apk!=one
  try:context.apk;checks['frozenContextRejectsChangedApk']=False
  except RuntimeError:checks['frozenContextRejectsChangedApk']=True
  context.refresh();checks['runnerRefreshReadsNewCandidate']=context.apk!=one
 finally:globals_.update(prior)
# A newer sibling PASS cannot replace this coordinator child's own failure.
runner_tree=ast.parse((ROOT/'qa/native/run-acceptance.py').read_text());function=next(n for n in runner_tree.body if isinstance(n,ast.FunctionDef)and n.name=='owned_result')
with tempfile.TemporaryDirectory(prefix='pli-owned-result-')as folder:
 root=Path(folder);runs=root/'qa/native/runs';own=runs/'own';own.mkdir(parents=True);other=runs/'other';other.mkdir();latest=root/'latest.json'
 mine={'pid':41,'processStart':'start-a','runId':'own','status':'FAILED','passed':False};foreign={'pid':42,'processStart':'start-b','runId':'other','status':'PASSED','passed':True}
 (own/'result.json').write_text(json.dumps(mine));(other/'result.json').write_text(json.dumps(foreign));latest.write_text(json.dumps(foreign));namespace={'ROOT':root,'read':lambda path:json.loads(path.read_text())if path.is_file()else{}}
 exec(compile(ast.Module(body=[function],type_ignores=[]),'actual-owned-result','exec'),namespace)
 checks['coordinatorCannotConsumeSiblingPass']=namespace['owned_result'](latest,41,'start-a',None)==mine
 checks['recycledPidCannotAdoptPreviousProcessEvidence']=namespace['owned_result'](latest,41,'different-start',None)=={}
reader=runpy.run_path(str(ROOT/'scripts/build-report.py'));key=reader['run_key'];sample={'script':'qa/native/runtime-guard.py','profile':'personal','arguments':[]}
checks['explicitFullCannotHideLatestFailure']=key(sample)==key({**sample,'arguments':['--scope','full']})
checks['sameScopeAliasesShareFailureHistory']=key({**sample,'arguments':['--cleanup-only']})==key({**sample,'arguments':['--scope','cleanup']})
checks['differentProfilesDoNotShareFailureHistory']=key(sample)!=key({**sample,'profile':'public'})
# A stop request while waiting for cached-result reader locks must be prompt.
with tempfile.TemporaryDirectory(prefix='pli-cancel-lock-')as folder:
 from contracts import resource_locks
 path=Path(folder);held=(path/'host-load.lock').open('a');fcntl.flock(held,fcntl.LOCK_EX);cancelled=[False]
 timer=threading.Timer(.1,lambda:cancelled.__setitem__(0,True));timer.start();start=time.monotonic()
 try:
  with resource_locks([('host-load','shared')],path,cancelled=lambda:cancelled[0]):checks['reuseWaitCanBeCancelled']=False
 except SystemExit as error:checks['reuseWaitCanBeCancelled']=error.code==130 and time.monotonic()-start<1
 finally:timer.join();held.close()
manifest={'effects':True,'resources':[['public-avd','exclusive']],'safetyChecks':{'microphoneClosed':'public-avd'}}
checks['confirmedSlowStopDoesNotQuarantine']=unsafe_resources({'cleanupStatus':'CONFIRMED','checks':{'microphoneClosed':'PASS','nativeStopWithin5Seconds':'FAIL'}},manifest)==set()
checks['actualResourceFailureStillQuarantines']=unsafe_resources({'cleanupStatus':'CONFIRMED','checks':{'microphoneClosed':'FAIL'}},manifest)=={'public-avd'}
checks['preEffectFailureCannotQuarantine']=unsafe_resources({'cleanupStatus':'UNCONFIRMED','checks':{}},{**manifest,'effects':False})==set()
# Default and --plan are actual runner entrypoints with external operations forbidden.
for arguments in [[],['--only','document-transfer','--plan']]:
 with patch.object(sys,'argv',['run-acceptance.py',*arguments]),patch('subprocess.Popen',side_effect=AssertionError('Plan attempted child process')),patch('subprocess.check_output',side_effect=AssertionError('Plan attempted device command')):
  try:runpy.run_path(str(ROOT/'qa/native/run-acceptance.py'),run_name='__main__');ok=False
  except SystemExit as e:ok=e.code==0
 checks['defaultRunnerHasNoDeviceEffects'if not arguments else'explicitPlanHasNoDeviceEffects']=ok
print(json.dumps({'methodChecks':checks}));assert all(checks.values())
