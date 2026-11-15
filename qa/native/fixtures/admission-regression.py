"""Execute admission/rejection and safety persistence without using an AVD."""
from pathlib import Path
import ast,copy,fcntl,json,os,runpy,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'qa/native'),str(ROOT/'scripts')]
import contracts,run_record
from runtime_context import set_runtime_intent
checks={};probe=ROOT/'qa/native/_admission_probe.py';latest=probe.with_suffix('.json');input_=ROOT/'qa/native/fixtures/_admission_input.txt'
base={'profile':None,'nativeRequired':False,'expectedChecks':['one'],'safetyChecks':{},'inputs':['qa/native/fixtures/_admission_input.txt'],'fixtures':[],'effects':'none','resources':[['host-load','shared'],['evidence-probe-exclusive','exclusive']],'executionKind':'EVIDENCE'}
with tempfile.TemporaryDirectory(prefix='pli-admission-')as directory:
 folder=Path(directory);mark=folder/'effect';intent=folder/'intent';intent.mkdir()
 def source(contract,native=False):
  return 'QA_CONTRACT = '+repr({'full':contract})+'\n'+f'''from pathlib import Path
import run_record,json,sys
if {native!r}:
 sys.path.insert(0,'scripts')
 import runtime_context
 original=runtime_context.runtime_intent
 runtime_context.runtime_intent=lambda folder:original(Path({str(intent)!r}))
 def unexpected(*args):
  Path({str(mark)!r}).write_text('unexpected device read')
  raise AssertionError('Device read before admission')
 run_record.build_matches=unexpected
 run_record.installed_identity=unexpected
from run_record import RunRecord
checks={{}};record=RunRecord(__file__,checks)
Path({str(mark)!r}).write_text('admitted')
checks['one']=True
'''
 def launch(pin=None):
  env={k:v for k,v in os.environ.items()if k not in {'PLI_QA_CANDIDATE','PLI_QA_PROFILE','PLI_QA_START_FD'}}
  if pin is not None:env['PLI_QA_CANDIDATE']=pin
  return subprocess.Popen([sys.executable,str(probe)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def initialized(process):
  until=time.monotonic()+8
  while time.monotonic()<until:
   try:
    result=json.loads(latest.read_text())
    if result.get('pid')==process.pid:return result
   except (OSError,ValueError):pass
   time.sleep(.02)
  raise AssertionError('Child did not initialize')
 def result(process):
  process.wait(timeout=10);return json.loads(latest.read_text())
 try:
  input_.write_text('selected input');probe.write_text(source(base));pin=contracts.identity_digest(contracts.candidate_identity(probe));input_.write_text('changed before child')
  process=launch(pin);r=result(process);checks['changedSelectionRejectedBeforeChildEffects']=r.get('error')=='PRECONDITION_CHANGED'and not mark.exists()
  input_.write_text('selected input');probe.write_text(source(base));lockfile=ROOT/'.tools/qa-resources/evidence-probe-exclusive.lock'
  with lockfile.open('a')as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);process=launch();initialized(process);probe.write_text(probe.read_text()+'\n# producer edited while queued\n');fcntl.flock(lock,fcntl.LOCK_UN)
  r=result(process);checks['producerEditDuringQueueHasNoEffects']=r.get('error')=='PRECONDITION_CHANGED'and not mark.exists()
  native={**base,'profile':'public','nativeRequired':True,'effects':'read','resources':[['host-load','shared'],['evidence-probe-exclusive','exclusive'],['public-avd','shared']],'executionKind':'NATIVE_OWNER'}
  probe.write_text(source(native,True))
  with lockfile.open('a')as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);process=launch();initialized(process);set_runtime_intent(intent,'paused');set_runtime_intent(intent,'running');fcntl.flock(lock,fcntl.LOCK_UN)
  r=result(process);checks['stopStartDuringQueueRejectedBeforeDeviceRead']=r.get('error')=='PRECONDITION_CHANGED'and not mark.exists()
  set_runtime_intent(intent,'paused')
  with lockfile.open('a')as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);process=launch();process.wait(timeout=2);r=json.loads(latest.read_text());checks['pausedSelectionDoesNotWaitOrReadDevice']=r.get('error')=='PRECONDITION_PAUSED'and not mark.exists()
  set_runtime_intent(intent,'running')
  probe.write_text(source(base));process=launch();r=result(process);checks['unchangedDirectCandidateStillRuns']=r.get('passed')is True and mark.read_text()=='admitted';mark.unlink()
 finally:probe.unlink(missing_ok=True);latest.unlink(missing_ok=True);input_.unlink(missing_ok=True)
 # Exercise the actual runner's syntax-failure writer on an isolated checkout.
 fixture=folder/'project';(fixture/'qa/native').mkdir(parents=True);(fixture/'scripts').mkdir();owner=fixture/'qa/native/fast-unit.py';owner.write_text('QA_CONTRACT = (\n')
 (fixture/'scripts/build-report.py').write_text('evaluate=lambda *a: []\nclass EvaluationContext:\n def __init__(self):self.latest={}\n')
 old_root=run_record.ROOT;run_record.ROOT=fixture
 try:
  code=(ROOT/'qa/native/run-acceptance.py').read_text();previous=list(sys.argv);sys.argv=['run-acceptance.py','--only','fast-unit','--force']
  try:exec(compile(code,str(ROOT/'qa/native/run-acceptance.py'),'exec'),{'__file__':str(fixture/'qa/native/run-acceptance.py'),'__name__':'__main__'});exit_=0
  except SystemExit as error:exit_=error.code
  finally:sys.argv=previous
  r=json.loads(owner.with_suffix('.json').read_text());checks['actualRunnerRecordsInvalidContractWithoutSecondFailure']=exit_==1 and r.get('status')=='PRECHECK_FAILED'and r.get('cleanupStatus')=='NOT_REQUIRED'
 finally:run_record.ROOT=old_root
 # A closed resource does not prove that a failed original-data invariant was
 # repaired. Test the actual result writer and the actual recovery clear path.
 (fixture/'qa/native/run_record.py').write_bytes((ROOT/'qa/native/run_record.py').read_bytes());(fixture/'qa/native/contracts.py').write_bytes((ROOT/'qa/native/contracts.py').read_bytes())
 owner=fixture/'qa/native/runtime-guard.py';contract={**base,'profile':'personal','inputs':[],'effects':'mutate','resources':[['host-load','shared'],['personal-avd','exclusive']],'safetyChecks':{'one':'personal-avd'}};owner.write_text('QA_CONTRACT = '+repr({'full':contract})+'\n')
 old_run_root,old_contract_root=run_record.ROOT,contracts.ROOT;run_record.ROOT=contracts.ROOT=fixture;previous=list(sys.argv);sys.argv=[str(owner)]
 try:
  values={};r=run_record.RunRecord(owner,values);r.verify_cleanup=lambda:True;r.cleanup_status='CONFIRMED';values['one']=False;r.finish()
  path=fixture/'.tools/qa-resources/quarantine-personal.json';data=json.loads(path.read_text());checks['failedDataInvariantPersistsAfterConfirmedClose']=data.get('kind')=='SAFETY'and data.get('resources')==['personal-avd']
  r.quarantine_at_admission=data;r.quarantines_at_admission=[(path,data)];r.confirm_cleanup();checks['cleanupConfirmationCannotClearDataFailure']=path.exists()
  checks['quarantineBlocksOnlyItsActualResource']=bool(contracts.conflicting_quarantines([('personal-avd','exclusive')],path.parent))and not contracts.conflicting_quarantines([('public-avd','exclusive')],path.parent)
  # Read-only observations may report an existing public exposure. Repeating
  # a failure preserves both owners; a fresh pass resolves only that boundary.
  owner=fixture/'qa/native/public-access.py';public={**base,'profile':'public','inputs':[],'effects':'read','resources':[['host-load','shared'],['public-service','shared']],'safetyChecks':{'one':'public-service'}};owner.write_text('QA_CONTRACT = '+repr({'full':public})+'\n');sys.argv=[str(owner)]
  for _ in range(2):
   values={};observation=run_record.RunRecord(owner,values);values['one']=False;observation.finish()
  incidents=contracts.conflicting_quarantines([('public-service','shared')],path.parent);checks['readOnlyExposureIsPersistedWithoutLosingPreviousIncident']=len(incidents)==2 and all(item['kind']=='SAFETY'for file,item in incidents)
  values={};observation=run_record.RunRecord(owner,values);values['one']=True;observation.finish();checks['sameBoundaryPassResolvesExposureButPreservesDataFailure']=not contracts.conflicting_quarantines([('public-service','shared')],path.parent)and path.exists()
 finally:sys.argv=previous;run_record.ROOT=old_run_root;contracts.ROOT=old_contract_root
print(json.dumps({'admissionChecks':checks}));assert all(checks.values())
