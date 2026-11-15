"""Reuse only an exactly qualified result; keep independent owners running after unrelated failures."""
from pathlib import Path
import argparse,json,subprocess,sys,runpy,os,signal,ast,datetime,uuid,hashlib,time
from run_record import source_snapshot,installed_identity,build_matches
from contracts import declared_contract,unsafe_resources,candidate_identity,identity_digest,resource_locks,conflicting_quarantines
ROOT=Path(__file__).resolve().parents[2]
GROUPS=['fast-unit','edge-ai','mcp-contract','server-contract','runtime-guard','native-instrumentation','viewport-recovery','portal-journey','experience-voice','private-navigation','kidsnote-integration','parent-private','document-transfer','public-access','portal-layout','portal-performance','portal-edge','voice-performance','session-boundaries','silent-output','server-crash','lease-recovery','native-ttl','cold-start','capture-preview','evidence-contract','publication-contract']
INDEPENDENT={'fast-unit','edge-ai','mcp-contract','evidence-contract','publication-contract','server-contract','runtime-guard'}
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--only',nargs='+',choices=GROUPS);parser.add_argument('--full',action='store_true',help='Explicitly select all original groups');parser.add_argument('--class',dest='test_class',help='One actual native instrumentation class');parser.add_argument('--scope',help='Select one predeclared scope of one --only owner');parser.add_argument('--list',action='store_true');parser.add_argument('--force',action='store_true',help='Re-run even an exactly qualified result');parser.add_argument('--plan',action='store_true',help='Check selected scripts and local dependencies without touching a device');args=parser.parse_args()
if args.list:print('\n'.join(GROUPS));raise SystemExit(0)
if args.full and args.only:parser.error('Choose --full or --only')
if args.test_class:
 if args.only!=['native-instrumentation']or args.scope not in {None,'focused'}:parser.error('--class requires --only native-instrumentation')
 args.scope='focused'
if args.scope and(not args.only or len(args.only)!=1):parser.error('--scope requires exactly one --only owner')
if not args.only and not args.full:args.plan=True
selected=args.only or GROUPS
def read(path):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {}
def owned_result(latest,pid,process_start,previous,run_id=None):
 candidates=[ROOT/'qa/native/runs'/run_id/'result.json']if run_id else[]
 candidates.append(latest)
 candidates.extend((ROOT/'qa/native/runs').glob('*/result.json'))
 for path in candidates:
  proof=read(path)
  if proof.get('pid')==pid and proof.get('runId')!=previous and process_start is not None and proof.get('processStart')==process_start:return proof
 return {}

def admitted_deadline(deadline,proof,manifest,pid,prior_run,now,limit):
 if deadline is not None:return deadline
 if proof.get('pid')==pid and proof.get('runId')!=prior_run and 'resources'in manifest:return now+limit
 return None
def selected_arguments(script):
 return (['--scope',args.scope]if args.scope else[])+(['--class',args.test_class]if args.test_class else[])+(['--seoul-gps']if script.stem=='private-navigation'else[])
def precheck(script):
 contract=declared_contract(script,selected_arguments(script))
 for name in contract['inputs']:
  path=ROOT/name
  if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
 for name in contract['fixtures']:
  if not(ROOT/'qa/native/fixtures'/name).is_file():raise ValueError('Missing fixture: '+name)
 return contract

def target_profile(script):
 from contracts import declared_contract
 return declared_contract(script)['profile']

def record_precheck_failure(script,error):
 from run_record import preflight_failure
 return preflight_failure(script,error,selected_arguments(script))

report_reader=runpy.run_path(str(ROOT/'scripts/build-report.py'));evaluate=report_reader['evaluate'];logs=ROOT/'.tools/logs';failures=[];blocked_resources=set()
context=report_reader['EvaluationContext']()if not args.plan else None
stopping=False;cancel_requested=False;current_process=None;cancel_deadline=None;cleanup_budget=30
def request_stop(sig,frame):
 global stopping,cancel_requested,cancel_deadline
 stopping=True
 if sig!=signal.SIGUSR1:cancel_requested=True;cancel_deadline=cancel_deadline or time.monotonic()+cleanup_budget
 if sig!=signal.SIGUSR1 and current_process is not None and current_process.poll()is None:
  try:os.killpg(current_process.pid,signal.SIGTERM)
  except ProcessLookupError:pass
signal.signal(signal.SIGTERM,request_stop);signal.signal(signal.SIGINT,request_stop);signal.signal(signal.SIGUSR1,request_stop)
for name in selected:
 if stopping:break
 script=ROOT/'qa/native'/(name+'.py');latest=script.with_suffix('.json');prior=read(latest);run_id=prior.get('runId');manifest=read(ROOT/'qa/native/runs'/str(run_id)/'manifest.json')
 try:contract=precheck(script)
 except (SyntaxError,ValueError,OSError)as error:
  failure_id=None if args.plan else record_precheck_failure(script,error);failures.append(name);print(json.dumps({'script':name,'status':'PRECHECK_FAILED','runId':failure_id,'reason':str(error),'deviceMutations':0}),flush=True);continue
 if args.plan:
  print(json.dumps({'script':name,'scope':contract['scope'],'status':'PLAN_READY','inputFiles':len(contract['inputs']),'fixtures':contract['fixtures'],'nativeRequired':contract['nativeRequired'],'effects':contract['effects'],'resources':contract['resources'],'expectedChecks':len(contract['expectedChecks']),'deviceAccess':False}),flush=True);continue
 selected_profile=contract['profile'];requested={resource for resource,mode in contract['resources']}
 if requested&blocked_resources:
  failures.append(name);print(json.dumps({'script':name,'status':'NOT_RUN','reason':'cleanup/safety not confirmed for '+','.join(sorted(requested&blocked_resources))}),flush=True);continue
 expected_args=selected_arguments(script)
 try:candidate=candidate_identity(script,expected_args,contract)
 except (OSError,ValueError,SyntaxError)as error:
  failure_id=record_precheck_failure(script,error);failures.append(name);print(json.dumps({'script':name,'status':'PRECHECK_FAILED','runId':failure_id,'reason':str(error),'deviceMutations':0}),flush=True);continue
 context.refresh()
 key=report_reader['run_key']({'script':str(script.relative_to(ROOT)),'arguments':expected_args,'profile':selected_profile});canonical=context.latest.get(key)
 if canonical:
  _,canonical_path,manifest=canonical;prior=read(canonical_path.with_name('result.json'));run_id=prior.get('runId')
 if not args.force and run_id and manifest.get('arguments',expected_args)==expected_args:
  # Reuse reads the installation under the same service/AVD lock order. The
  # selection fingerprint remains fixed while waiting for those readers.
  readers=[(resource,'shared')for resource,mode in contract['resources']]
  with resource_locks(readers,cancelled=lambda:stopping):
   try:
    if candidate_identity(script,expected_args,contract)!=candidate:raise ValueError('PRECONDITION_CHANGED')
    context.refresh();reusable=not context.evaluate(prior,manifest)and not conflicting_quarantines(contract['resources'])
    if contract['nativeRequired']:
     reusable=reusable and candidate['runtimeIntent']['desiredState']=='running'and build_matches()and installed_identity(contract['profile']).get('sha256')==manifest.get('apkSha256')
   except (OSError,ValueError,RuntimeError)as error:
    failure_id=record_precheck_failure(script,error);failures.append(name);print(json.dumps({'script':name,'status':'PRECHECK_FAILED','runId':failure_id,'reason':str(error),'deviceMutations':0}),flush=True);continue
   if reusable:
    print(json.dumps({'script':name,'status':'REUSED','runId':run_id,'reason':'same selected producer, inputs and scope; live identity read under shared locks only when required'}),flush=True);continue
 logs.mkdir(parents=True,exist_ok=True);print('START '+name,flush=True);log=logs/('acceptance-'+name+'.log')
 with log.open('w')as out:
  gate_read,gate_write=os.pipe()
  try:
   process=subprocess.Popen([sys.executable,str(script)]+expected_args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(gate_read,),env={**os.environ,'PLI_QA_START_FD':str(gate_read),'PLI_QA_CANDIDATE':identity_digest(candidate)})
   current_process=process
   try:process_start=Path('/proc')/str(process.pid)/'stat';process_start=process_start.read_text().split()[21]
   except (OSError,IndexError):process_start=None
   owned_run_id=None
   if not stopping:
    try:os.write(gate_write,b'G')
    except BrokenPipeError:pass
  finally:os.close(gate_read)
  limit={'voice-performance':900,'native-ttl':260,'cold-start':420,'experience-voice':420,'native-instrumentation':300,'private-navigation':420,'capture-preview':300,'portal-edge':120}.get(name,240)
  cleanup_budget=150 if name=='private-navigation'else 100 if name=='cold-start'else 30
  # A device owner waiting behind another owner has not started its execution
  # budget. Keep queue/startup and actual work deadlines separate.
  queued_at=time.monotonic();until=None;timeout_phase='STARTUP'
  try:
   while process.poll()is None:
    now=time.monotonic();pending=read(latest);fresh_pending=pending.get('pid')==process.pid and pending.get('processStart')==process_start and pending.get('runId')!=run_id
    if fresh_pending:owned_run_id=pending['runId']
    pending_manifest=read(ROOT/'qa/native/runs'/str(pending.get('runId'))/'manifest.json')if fresh_pending else{}
    until=admitted_deadline(until,pending,pending_manifest,process.pid,run_id,now,limit)
    timeout_phase='EXECUTION'if until is not None else'WAIT_RESOURCE'if fresh_pending else'STARTUP'
    expired=now>=until if until is not None else now-queued_at>1200 if fresh_pending else now-queued_at>30
    if expired or cancel_deadline is not None and now>=cancel_deadline:raise subprocess.TimeoutExpired(process.args,limit)
    try:process.wait(timeout=.2)
    except subprocess.TimeoutExpired:pass
  except subprocess.TimeoutExpired:
   print(json.dumps({'script':name,'status':'TIMEOUT','phase':timeout_phase,'limitSeconds':limit if timeout_phase=='EXECUTION'else 1200 if timeout_phase=='WAIT_RESOURCE'else 30}),flush=True)
   try:os.killpg(process.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:process.wait(timeout=0 if cancel_requested else cleanup_budget)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
  os.close(gate_write);current_process=None
  result=process
 proof=owned_result(latest,process.pid,process_start,run_id,owned_run_id);fresh=bool(proof.get('runId'));passed=result.returncode==0 and fresh and proof.get('passed')is True
 if passed:
  context.refresh();final_manifest=read(ROOT/'qa/native/runs'/proof['runId']/'manifest.json')
  try:passed=not context.evaluate(proof,final_manifest)
  except (OSError,ValueError,RuntimeError):passed=False
 if not fresh:
  failure_id=record_precheck_failure(script,RuntimeError('Child exited before evidence initialization; inspect '+str(log.relative_to(ROOT))));proof=read(latest);fresh=True
 print(json.dumps({'script':name,'exitCode':result.returncode,'freshRun':fresh,'runId':proof.get('runId')if fresh else None,'status':proof.get('status')if fresh else'NO_NEW_RESULT','log':str(log.relative_to(ROOT))}),flush=True)
 if not passed:
  failures.append(name)
  final_manifest=read(ROOT/'qa/native/runs'/str(proof.get('runId'))/'manifest.json')if fresh else{}
  blocked_resources.update(unsafe_resources(proof,final_manifest))
 elif name=='runtime-guard'and proof.get('cleanupStatus')=='CONFIRMED':blocked_resources.discard(str(selected_profile)+'-avd')
print(json.dumps({'failedOrNotRun':failures,'selectedScopeComplete':not args.plan and not failures and not stopping,'overallRequirementsComplete':False,'scope':'all original automated groups'if args.full else'selected owners only','planOnly':args.plan,'stopped':stopping}),flush=True)
raise SystemExit(130 if stopping else 1 if failures else 0)
