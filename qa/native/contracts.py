"""Read owner declarations without importing a producer or touching a device."""
from pathlib import Path
import ast,hashlib,json,contextlib,fcntl,time,os
ROOT=Path(__file__).resolve().parents[2]
def declared_contract(script,arguments=()):
 tree=ast.parse(Path(script).read_text());value=None
 for node in tree.body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='QA_CONTRACT'for t in node.targets):value=ast.literal_eval(node.value);break
 if not isinstance(value,dict):raise ValueError('QA_CONTRACT must be declared before execution: '+Path(script).name)
 scope='full'
 arguments=list(arguments)
 if '--scope'in arguments:
  i=arguments.index('--scope')
  if i+1==len(arguments):raise ValueError('Scope value missing')
  scope=arguments[i+1]
 if '--cleanup-only'in arguments:scope='cleanup'
 if '--class'in arguments or '--resources-only'in arguments:scope='focused'
 if Path(script).name=='native-instrumentation.py'and scope=='focused'and '--class'not in arguments and '--resources-only'not in arguments:raise ValueError('Focused instrumentation needs --class or --resources-only')
 if scope not in value:raise ValueError('Undeclared scope: '+scope)
 contract=value[scope]
 required={'profile','nativeRequired','expectedChecks','safetyChecks','inputs','fixtures','effects','resources','executionKind'}
 if set(contract)!=required:raise ValueError('Incomplete or unknown contract fields')
 if contract['profile']not in {'personal','public',None}or type(contract['nativeRequired'])is not bool:raise ValueError('Invalid profile/native declaration')
 expected=contract['expectedChecks']
 if not isinstance(expected,list)or not expected or len(expected)!=len(set(expected))or any(not isinstance(k,str)or not k for k in expected):raise ValueError('Expected checks must be explicit, unique and nonempty')
 if not isinstance(contract['safetyChecks'],dict)or not set(contract['safetyChecks'])<=set(expected):raise ValueError('Safety invariant must name a planned check')
 if contract['effects']not in {'none','read','mutate','runtime'}:raise ValueError('Unknown effect type')
 if contract['executionKind']not in {'NATIVE_E2E','NATIVE_OWNER','JVM','MCP_FIXTURE','HOST_CONTRACT','EVIDENCE','DELIVERY'}:raise ValueError('Unknown execution kind')
 if not isinstance(contract['fixtures'],list)or not isinstance(contract['inputs'],list):raise ValueError('Inputs must be explicit lists; empty means none')
 for name in contract['inputs']:
  path=(ROOT/name).resolve()
  if not path.is_relative_to(ROOT)or not path.is_file():raise ValueError('Missing or unsafe input: '+name)
 names=[]
 for pair in contract['resources']:
  if len(pair)!=2 or pair[0]not in {'host-load','personal-service','public-service','personal-avd','public-avd','evidence-probe-exclusive'}or pair[1]not in {'shared','exclusive'}:raise ValueError('Invalid resource mode/name')
  names.append(pair[0])
 if len(names)!=len(set(names)):raise ValueError('Duplicate resource')
 if any(resource not in names for resource in contract['safetyChecks'].values()):raise ValueError('Safety invariant needs its declared resource')
 if contract['effects']in {'mutate','runtime'}and(contract['profile']is None or [contract['profile']+'-avd','exclusive']not in [list(pair)for pair in contract['resources']]):raise ValueError('Mutation needs its owned AVD exclusive lock')
 if contract['nativeRequired']and contract['profile']is None:raise ValueError('Live native proof requires profile')
 if contract['executionKind']=='JVM':
  actual={str(path.relative_to(ROOT))for folder in ['android/app/src/main','android/app/src/test']for path in(ROOT/folder).rglob('*.kt')}
  if not actual<=set(contract['inputs']):raise ValueError('Compiled Kotlin input missing from owner declaration')
 for name in contract['fixtures']:
  if not isinstance(name,str)or Path(name).name!=name:raise ValueError('Unsafe fixture name')
 return {'scope':scope,**contract,'resources':[list(pair)for pair in contract['resources']]}
def contract_digest(contract):return hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def fingerprint(contract):
 files=list(contract['inputs'])+['qa/native/fixtures/'+name for name in contract['fixtures']]
 return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in files}

def candidate_identity(script, arguments=(), contract=None):
 """Bind the chosen producer and inputs before a child or resource wait starts."""
 script=Path(script);resolved=declared_contract(script,arguments)
 if contract is not None and resolved!=contract:raise ValueError('PRECONDITION_CHANGED')
 value={'scriptSha256':hashlib.sha256(script.read_bytes()).hexdigest(),
        'contract':resolved,'inputs':fingerprint(resolved),
        'recordToolSha256':hashlib.sha256((ROOT/'qa/native/run_record.py').read_bytes()).hexdigest(),
        'contractToolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 if resolved['nativeRequired']:
  import sys
  sys.path.insert(0,str(ROOT/'scripts'))
  from runtime_context import runtime_intent
  folder=ROOT/('.tools/profiles/public'if resolved['profile']=='public'else'.tools')
  value['runtimeIntent']=runtime_intent(folder)
 return value

def identity_digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@contextlib.contextmanager
def resource_locks(resources, folder=None, on_wait=None, cancelled=None):
 """One lock order for direct execution, reuse and explicit live packaging."""
 folder=Path(folder)if folder is not None else ROOT/'.tools/qa-resources'
 folder.mkdir(parents=True,exist_ok=True);held=[]
 try:
  for name,mode in sorted(resources,key=lambda v:(0 if v[0]=='host-load'else 1 if v[0].endswith('-service')else 2,v[0])):
   if cancelled is not None and cancelled():raise SystemExit(130)
   handle=(folder/(name+'.lock')).open('a');held.append(handle);started=time.monotonic();notified=False
   while True:
    try:fcntl.flock(handle,(fcntl.LOCK_EX if mode=='exclusive'else fcntl.LOCK_SH)|fcntl.LOCK_NB);break
    except BlockingIOError:
     if cancelled is not None and cancelled():raise SystemExit(130)
     if on_wait is not None and not notified:on_wait(name,mode);notified=True
     time.sleep(.1)
   if on_wait is not None:on_wait(name,mode,time.monotonic()-started)
  yield held
 finally:
  for handle in reversed(held):handle.close()

def conflicting_quarantines(resources, folder=None):
 folder=Path(folder)if folder is not None else ROOT/'.tools/qa-resources';requested={name for name,mode in resources};found=[]
 for path in folder.glob('quarantine-*.json'):
  try:
   value=json.loads(path.read_text());profile=path.stem.removeprefix('quarantine-').split('-')[0]
   affected=set(value.get('resources',[profile+'-avd',profile+'-service']))
   if requested&affected:found.append((path,value))
  except (OSError,ValueError,TypeError):
   if any(name.startswith(path.stem.removeprefix('quarantine-').split('-')[0]+'-')for name in requested):found.append((path,{'kind':'UNKNOWN','reason':'unreadable quarantine'}))
 return found
def unsafe_resources(proof,manifest):
 # Timing misses are requirement failures. Only physical cleanup or an explicit
 # safety invariant can quarantine resources after an admitted effect.
 if not manifest.get('effects'):
  return {resource for key,resource in manifest.get('safetyChecks',{}).items()if proof.get('checks',{}).get(key)=='FAIL'}
 affected=set()
 if proof.get('cleanupStatus')=='UNCONFIRMED':affected.update(name for name,mode in manifest.get('resources',[])if mode=='exclusive'and name.endswith(('-avd','-service')))
 for key,resource in manifest.get('safetyChecks',{}).items():
  verdict=proof.get('checks',{}).get(key)
  if verdict!='PASS'and(proof.get('cleanupStatus')!='SUPERSEDED'or verdict=='FAIL'):affected.add(resource)
 return affected
