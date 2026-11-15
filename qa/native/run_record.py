"""Execution evidence shared by the existing native QA scripts; no stale PASS reuse."""
from pathlib import Path
import atexit,ast,datetime,hashlib,json,os,signal,subprocess,sys,time,uuid,fcntl,threading
ROOT=Path(__file__).resolve().parents[2]
from contracts import declared_contract,contract_digest,fingerprint,unsafe_resources,candidate_identity,identity_digest,resource_locks,conflicting_quarantines

def archived_producer(digest):
 if not isinstance(digest,str)or len(digest)!=64 or any(c not in '0123456789abcdef'for c in digest):return None
 target=ROOT/'.tools/private/qa-producers'/digest
 return target if target.is_file()and sha(target)==digest else None

def compatible_tool(manifest,result):
 version=manifest.get('recordVersion',1);producer=manifest.get('evidenceToolSha256')
 if version==3:
  contract=manifest.get('executionContract')
  if not isinstance(contract,dict)or contract_digest(contract)!=manifest.get('contractSha256'):return False
  if producer==sha(Path(__file__)):return True
  prior=archived_producer(producer)
  if not prior:return False
  try:
   # Reader-only compatibility edits do not change the producer's admission,
   # boolean checks or cleanup gates. Any other AST change needs fresh proof.
   def gates(path):
    tree=ast.parse(path.read_text());tree.body=[n for n in tree.body if not(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name=='compatible_tool')];return ast.dump(tree,include_attributes=False)
   return gates(prior)==gates(Path(__file__))
  except (OSError,SyntaxError):return False
 # Old raw records remain old records. Archived producer bytes establish their
 # origin, never new scopes or a current PASS after a failed original result.
 if version not in {1,2}or not archived_producer(producer):return False
 try:
  tree=ast.parse(archived_producer(producer).read_text());versions={v.value for node in ast.walk(tree)if isinstance(node,ast.Dict)for k,v in zip(node.keys,node.values)if isinstance(k,ast.Constant)and k.value=='recordVersion'and isinstance(v,ast.Constant)and isinstance(v.value,int)}or{1}
  if version not in versions:return False
 except (OSError,SyntaxError):return False
 normal=result.get('status')=='PASSED'and result.get('passed')is True and result.get('error')is None and result.get('sourceChanged')is False and bool(result.get('checks'))and all(v=='PASS'for v in result['checks'].values())
 if not normal:return False
 if version==1:return manifest.get('executionKind')!='NATIVE_OWNER'
 return result.get('cleanupStatus')in ({'CONFIRMED'}if manifest.get('effects')else{'NOT_REQUIRED','CONFIRMED'})and(manifest.get('executionKind')!='NATIVE_OWNER'or result.get('metrics',{}).get('cleanupObligations',{}).get('guestInstrumentationTerminated')is True)

def applied_public_source_checks(status,javascript,root):
 modules={'demo-server.py','display_stream.py','delivery_assets.py','runtime_context.py','audio_guard.py','portal_proxy.py'}
 loaded=status.get('runtimeRevision',{}).get('sourceSha256',{})
 return {'profileIsPublic':status.get('profile')=='public','runningModulesMatchWorkingSources':set(loaded)==modules and all((root/'scripts'/name).is_file()and sha(root/'scripts'/name)==loaded[name]for name in modules),'servedJavascriptMatchesWorkingSource':hashlib.sha256(javascript).hexdigest()==sha(root/'demo-v2/app.js')}

def resources_for(script,profile,execution_kind):
 contract=declared_contract(script,sys.argv[1:])
 if contract['profile']is not None and profile!=contract['profile']:raise ValueError('PROFILE_CONTRACT_MISMATCH')
 return contract['resources']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,data):
 p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(p)
NON_RUNTIME={"scripts/build-report.py","scripts/package-source.py"}
PUBLIC_OWNERS={'portal-journey.py','portal-edge.py','portal-layout.py','portal-performance.py','public-access.py','capture-preview.py','lease-recovery.py','experience-voice.py','voice-performance.py','session-boundaries.py','silent-output.py','server-crash.py','native-ttl.py'}
PURE={'mcp-contract.py':'MCP_FIXTURE','fast-unit.py':'JVM','evidence-contract.py':'EVIDENCE','native-instrumentation.py':'NATIVE_OWNER','server-contract.py':'HOST_CONTRACT','publication-contract.py':'DELIVERY'}
def kind(script):return PURE.get(Path(str(script)).name,'NATIVE_E2E')
def runtime_sources(values,script=None):
 name=Path(str(script)).name;k=kind(script)
 if k=='MCP_FIXTURE':return {p:v for p,v in values.items()if p in {'scripts/kidsnote_mcp/site.mjs','scripts/kidsnote_mcp/sync.mjs','scripts/kidsnote_mcp/voice.mjs'}}
 if k=='JVM':return {p:v for p,v in values.items()if p.startswith('android/')and '/src/androidTest/'not in p}
 if k=='HOST_CONTRACT':return {p:v for p,v in values.items()if p.startswith('scripts/emulator_proto/')or p in {'scripts/demo-server.py','scripts/runtime_context.py','scripts/display_stream.py','scripts/audio_guard.py','scripts/portal_proxy.py','scripts/delivery_assets.py'}}
 if k=='DELIVERY':return {p:v for p,v in values.items()if p in {'scripts/build-report.py','scripts/package-source.py','scripts/build_identity.py','scripts/delivery_assets.py'}}
 if k=='NATIVE_OWNER':return {p:v for p,v in values.items()if p.startswith('android/')and '/src/test/'not in p or p in {'scripts/audio_guard.py','scripts/runtime_context.py','scripts/build_identity.py'}}
 if k=='EVIDENCE':return {p:v for p,v in values.items()if p in {'scripts/build-report.py','scripts/package-source.py','scripts/build_identity.py'}}
 if name in {'portal-layout.py','portal-edge.py'}:return {p:v for p,v in values.items()if p.startswith('demo-v2/') or p in {'scripts/demo-server.py','scripts/portal_proxy.py','scripts/runtime_context.py'}}
 personal_native={'kidsnote-integration.py','parent-private.py','private-navigation.py','runtime-guard.py','cold-start.py','document-transfer.py'}
 if name in personal_native:values={p:v for p,v in values.items()if not p.startswith('demo-v2/')or p=='demo-v2/family.html'}
 public=name in PUBLIC_OWNERS
 return {p:v for p,v in values.items()if p not in NON_RUNTIME and '/src/test/'not in p and (name=='native-instrumentation.py' or '/src/androidTest/'not in p) and not(public and (p.startswith('scripts/kidsnote_mcp/')or p in {'scripts/kidsnote-mcp.mjs','scripts/kidsnote-bridge.py','scripts/kidsnote-web-login.py'}))}
def source_snapshot(script=None):
 if script is not None:
  contract=declared_contract(script,sys.argv[1:]);return {name:sha(ROOT/name)for name in contract['inputs']}
 paths=[]
 for folder in ['android/app/src','scripts','demo-v2']:
  paths.extend(p for p in (ROOT/folder).rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix in {'.kt','.xml','.kts','.py','.mjs','.js','.css','.html','.woff2','.svg'})
 paths += [ROOT/'android/app/build.gradle.kts',ROOT/'android/build.gradle.kts',ROOT/'android/gradle.properties',ROOT/'android/settings.gradle.kts']
 values={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(paths))}
 return runtime_sources(values,script)if script is not None else values
def build_matches():
 sys.path.insert(0,str(ROOT/'scripts'))
 from build_identity import valid_build
 return valid_build(ROOT/'artifacts/pli-pleos.apk')
def installed_identity(profile=None):
 try:
  selected=profile or os.environ.get('PLI_QA_PROFILE','personal');state=ROOT/('.tools/profiles/public/run-state.json'if selected=='public'else'.tools/run-state.json');serial=json.loads(state.read_text())['serial'];adb=ROOT/'.tools/android-sdk/platform-tools/adb'
  def call(*args):return subprocess.check_output([str(adb),'-s',serial,'shell',*args],timeout=8).decode().strip()
  apk=call('pm','path','ai.teammoon.pli').splitlines()[0].removeprefix('package:')
  return {'profile':selected,'serial':serial,'sha256':call('sha256sum',apk).split()[0],'android':call('getprop','ro.build.version.release'),'fingerprint':call('getprop','ro.build.fingerprint')}
 except Exception:return {'error':'INSTALLED_APK_IDENTITY_UNAVAILABLE'}
def reconcile():
 for p in (ROOT/'qa/native/runs').glob('*/result.json'):
  try:
   r=json.loads(p.read_text())
   if r.get('status')!='RUNNING':continue
   proc=Path('/proc')/str(r['pid'])/'stat'
   if not proc.exists()or proc.read_text().split()[21]!=r.get('processStart'):
    try:m=json.loads(p.with_name('manifest.json').read_text())
    except (OSError,ValueError):m={}
    cleanup='NOT_REQUIRED'if m.get('recordVersion',1)>=2 and m.get('effects')is False else'UNCONFIRMED'
    if m.get('runtimeIntent'):
     sys.path.insert(0,str(ROOT/'scripts'));from runtime_context import runtime_intent
     intent_dir=ROOT/('.tools/profiles/public'if m.get('profile')=='public'else'.tools')
     if runtime_intent(intent_dir)['generation']!=m['runtimeIntent']['generation']:cleanup='SUPERSEDED'
    r.update(status='INCOMPLETE',passed=False,error='process_terminated_without_final_result',cleanupStatus=cleanup);atomic(p,r)
    latest=ROOT/m['script'];latest=latest.with_suffix('.json')
    if latest.exists()and json.loads(latest.read_text()).get('runId')==r['runId']:atomic(latest,r)
    if m.get('recordVersion',1)>=2 and m.get('effects')and cleanup!='SUPERSEDED':
     save_quarantine(m,r['runId'],'owner process vanished before final cleanup')
  except (OSError,ValueError,KeyError,IndexError):pass
def save_quarantine(manifest,run_id,reason,kind='CLEANUP',resources=None,failed_checks=None):
 profile=manifest.get('profile')or'personal';folder=ROOT/'.tools/qa-resources';target=folder/('quarantine-'+profile+'.json')
 try:previous=json.loads(target.read_text())
 except (OSError,ValueError):previous={}
 if previous and previous.get('runId')!=run_id:target=folder/('quarantine-'+profile+'-'+run_id+'.json')
 if resources is None:resources=[name for name,mode in manifest.get('resources',[])if mode=='exclusive'and name.endswith(('-avd','-service'))]or[profile+'-avd']
 atomic(target,{'runId':run_id,'script':manifest.get('script'),'kind':kind,'resources':resources,'failedChecks':failed_checks or[],'reason':reason,'runtimeIntent':manifest.get('runtimeIntent')})
 return target

def preflight_failure(script,error,arguments=None):
 script=Path(script);arguments=list(sys.argv[1:]if arguments is None else arguments)
 run_id=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];folder=ROOT/'qa/native/runs'/run_id
 manifest={'recordVersion':3,'runId':run_id,'script':str(script.relative_to(ROOT)),'scriptSha256':sha(script)if script.is_file()else None,'evidenceToolSha256':sha(Path(__file__)),'executionKind':'PREFLIGHT','arguments':arguments,'nativeRequired':False,'effects':False,'startedAt':datetime.datetime.now().astimezone().isoformat(),'source':{},'fixtures':{},'dependencies':{}}
 result={'runId':run_id,'status':'PRECHECK_FAILED','passed':False,'checks':{},'error':type(error).__name__,'reason':str(error),'sourceChanged':False,'cleanupStatus':'NOT_REQUIRED','installedMatchesArtifact':True,'buildInputsMatch':False}
 atomic(folder/'manifest.json',manifest);atomic(folder/'result.json',result);atomic(script.with_suffix('.json'),result)
 return run_id

class RunRecord:
 def __init__(self,script,checks,metrics=None,dependencies=(),execution_kind=None,fixtures=None,claims=None):
  reconcile();self.script=Path(script)
  try:
   self.contract=declared_contract(self.script,sys.argv[1:]);self.candidate=candidate_identity(self.script,sys.argv[1:],self.contract);initial_fingerprint=self.candidate['inputs']
   if os.environ.get('PLI_QA_PROFILE',self.contract['profile']or'personal')!=(self.contract['profile']or'personal'):raise ValueError('PROFILE_CONTRACT_MISMATCH')
  except (OSError,ValueError,SyntaxError)as error:preflight_failure(self.script,error);raise
  self.kind=self.contract['executionKind'];self.native=self.contract['nativeRequired'];self.profile=self.contract['profile']or'personal'
  self.checks=checks;self.metrics=metrics if metrics is not None else {};self.failure=None;self.done=False;self.locks=[];self.cleanup_status='NOT_REQUIRED';self.effect_started=False;self.identity_checked=False;self.cleanup_barriers=[];self.finalized=threading.Event();self.cleanup_budget=150 if self.script.name=='private-navigation.py'else 100 if self.script.name=='cold-start.py'else 30
  self.id=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];self.dir=ROOT/'qa/native/runs'/self.id;self.latest=self.script.with_suffix('.json');self.start=time.monotonic()
  self.planned=self.contract['expectedChecks'];self.input_fingerprint=initial_fingerprint
  self.manifest={'recordVersion':3,'scope':self.contract['scope'],'executionContract':self.contract,'contractSha256':contract_digest(self.contract),'safetyChecks':self.contract['safetyChecks'],'arguments':sys.argv[1:],'plannedClaims':claims or{},'runId':self.id,'script':str(self.script.relative_to(ROOT)),'scriptSha256':sha(self.script),'evidenceToolSha256':sha(Path(__file__)),'source':{name:self.input_fingerprint[name]for name in self.contract['inputs']},'executionKind':self.kind,'claimScope':self.contract['scope'],'profile':self.contract['profile'],'nativeRequired':self.native,'plannedChecks':self.planned,'startedAt':datetime.datetime.now().astimezone().isoformat(),'apkSha256':self.input_fingerprint['artifacts/pli-pleos.apk']if 'artifacts/pli-pleos.apk'in self.input_fingerprint else sha(ROOT/'artifacts/pli-pleos.apk')if self.native else None,'buildInputsMatch':True,'dependencies':{**{name:sha(ROOT/name)for name in dependencies},'qa/native/contracts.py':sha(ROOT/'qa/native/contracts.py')},'installed':{},'fixtures':{name:self.input_fingerprint['qa/native/fixtures/'+name]for name in self.contract['fixtures']}}
  self.manifest['candidateIdentity']=identity_digest(self.candidate);self.manifest['effects']=False
  self.base={'runId':self.id,'pid':os.getpid(),'processStart':Path(f'/proc/{os.getpid()}/stat').read_text().split()[21],'status':'RUNNING','passed':False}
  if self.latest.exists():
   prior=ROOT/'qa/native/runs/legacy'/(self.id+'-'+self.latest.name);prior.parent.mkdir(parents=True,exist_ok=True);prior.write_bytes(self.latest.read_bytes())
  archive=ROOT/'.tools/private/qa-producers';archive.mkdir(parents=True,exist_ok=True,mode=0o700)
  for producer in [self.script,Path(__file__)]:
   target=archive/sha(producer)
   if not target.exists():target.write_bytes(producer.read_bytes());target.chmod(0o600)
  atomic(self.dir/'manifest.json',self.manifest);atomic(self.dir/'result.json',self.base);atomic(self.latest,self.base)
  original=sys.excepthook
  def fail(t,v,tb):self.failure=t.__name__;original(t,v,tb)
  sys.excepthook=fail
  def cancel(sig,frame):
   if self.failure=='CANCELLED':return
   self.failure='CANCELLED'
   def deadline():
    if self.finalized.wait(self.cleanup_budget):return
    result={**self.base,'status':'INCOMPLETE','passed':False,'error':'CLEANUP_DEADLINE_EXCEEDED','cleanupStatus':'UNCONFIRMED','checks':{k:'NOT_RUN'for k in self.planned},'sourceChanged':True,'finishedAt':datetime.datetime.now().astimezone().isoformat()}
    atomic(self.dir/'result.json',result)
    try:
     if json.loads(self.latest.read_text()).get('runId')==self.id:atomic(self.latest,result)
    except (OSError,ValueError):pass
    if self.effect_started and self.intent_unchanged():save_quarantine(self.manifest,self.id,'cleanup deadline exceeded')
    if os.getpgrp()==os.getpid():os.killpg(os.getpid(),signal.SIGKILL)
    os._exit(130)
   threading.Thread(target=deadline,name='qa-cleanup-deadline',daemon=True).start()
   raise SystemExit(128+sig)
  signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel);atexit.register(self.finish)
  if self.native:
   self.intent_dir=ROOT/('.tools/profiles/public'if self.profile=='public'else'.tools');self.intent=self.candidate['runtimeIntent'];self.manifest['runtimeIntent']=self.intent
   if self.intent['desiredState']!='running':self.failure='PRECONDITION_PAUSED';self.finish();raise SystemExit('Runtime paused by user; admission stopped before resource wait')
  expected_candidate=os.environ.pop('PLI_QA_CANDIDATE',None)
  if expected_candidate is not None and expected_candidate!=identity_digest(self.candidate):self.failure='PRECONDITION_CHANGED';self.finish();raise SystemExit('Selected candidate changed before child admission')
  gate=os.environ.pop('PLI_QA_START_FD',None)
  if gate is not None:
   start_fd=int(gate);os.set_inheritable(start_fd,False)
   if os.read(start_fd,1)!=b'G':self.failure='CANCELLED';raise SystemExit('Coordinator cancelled before device admission')
   def parent_lifetime():
    try:
     while os.read(start_fd,1):pass
     if not self.done:os.kill(os.getpid(),signal.SIGTERM)
    except OSError:pass
    finally:os.close(start_fd)
   threading.Thread(target=parent_lifetime,name='qa-coordinator-lifetime',daemon=True).start()
  requested=resources_for(self.script,self.profile,self.kind);folder=ROOT/'.tools/qa-resources'
  def on_wait(name,mode,seconds=None):
   if seconds is None:print(json.dumps({'runId':self.id,'phase':'WAIT_RESOURCE','resource':name,'mode':mode}),flush=True)
   else:self.metrics.setdefault('resourceWaitSeconds',{})[name]=round(seconds,3)
  self.resource_context=resource_locks(requested,folder,on_wait);self.locks=self.resource_context.__enter__()
  planned_effects=self.contract['effects']in {'mutate','runtime'}
  try:unchanged=candidate_identity(self.script,sys.argv[1:],self.contract)==self.candidate and not self.inputs_changed()
  except (OSError,ValueError,SyntaxError):unchanged=False
  if not unchanged:self.failure='PRECONDITION_CHANGED';self.finish();raise SystemExit('Selected producer, intent or inputs changed while waiting for resources')
  self.manifest['resources']=requested;self.manifest['effects']=False
  if self.native:
   sys.path.insert(0,str(ROOT/'scripts'));from runtime_context import runtime_intent
   if self.intent['desiredState']!='running':self.failure='PRECONDITION_FAILED';self.finish();raise SystemExit('Runtime paused by user; no QA device effects')
   os.environ['PLI_QA_INTENT_GENERATION']=str(self.intent['generation'])
  quarantine=folder/('quarantine-'+self.profile+'.json')
  try:self.quarantine_at_admission=json.loads(quarantine.read_text())
  except (OSError,ValueError):self.quarantine_at_admission=None
  conflicts=conflicting_quarantines(requested,folder);self.quarantines_at_admission=conflicts
  recovery_allowed=self.script.name=='runtime-guard.py'and all(item.get('kind','CLEANUP')=='CLEANUP'for path,item in conflicts)
  if planned_effects and conflicts and not recovery_allowed:self.failure='CLEANUP_UNCONFIRMED';self.finish();raise SystemExit('Affected resource quarantined pending its actual cleanup or data restoration')
  self.manifest['buildInputsMatch']=build_matches()if self.native else True;self.manifest['installed']=installed_identity(self.profile)if self.native else {};self.identity_checked=True;atomic(self.dir/'manifest.json',self.manifest)
  if self.native and (not self.manifest['buildInputsMatch']or self.manifest['installed'].get('sha256')!=self.manifest['apkSha256']):
   self.failure='PRECONDITION_FAILED';self.finish();raise SystemExit('QA refused: complete the matching build and installation first')
  # Bind browser tests to the code actually served/loaded, after acquiring all
  # availability locks. Native-only recording export and diagnostics have their
  # own input identities and do not claim the current browser application.
  if self.kind=='NATIVE_E2E'and self.profile=='public'and self.script.name not in {'_warm_trace.py','capture-preview.py','runtime-guard.py'}:
   try:
    import urllib.request
    with urllib.request.urlopen('http://127.0.0.1:8878/api/status',timeout=5)as response:status=json.load(response)
    with urllib.request.urlopen('http://127.0.0.1:8878/app.js',timeout=5)as response:javascript=response.read()
    applied=applied_public_source_checks(status,javascript,ROOT)
   except (OSError,ValueError):applied={'sourceEndpointsAvailable':False}
   self.manifest['appliedSourceIdentity']=applied;atomic(self.dir/'manifest.json',self.manifest)
   if not all(applied.values()):self.failure='PRECONDITION_FAILED';self.metrics['appliedSourceIdentity']=applied;self.finish();raise SystemExit('QA refused: publish/restart the matching public sources before device effects')
  self.manifest['effects']=planned_effects;atomic(self.dir/'manifest.json',self.manifest)
  self.effect_started=planned_effects;self.cleanup_status='UNCONFIRMED'if self.effect_started else'NOT_REQUIRED'
  if self.effect_started and self.native:self.install_intent_guard()
 def guard_effects(self):
  if not self.intent_unchanged():raise RuntimeError('RUNTIME_INTENT_CHANGED')
 def install_intent_guard(self):
  # All native QA producers share this effect boundary, including their finally
  # blocks and children. A previous run cannot restart/kill a later user runtime.
  frozen={}
  def token(pid):
   try:return(Path('/proc')/str(pid)/'stat').read_text().split()[21]
   except (OSError,IndexError):return None
  def audit(event,args):
   if event=='os.kill':
    pid,sig=args
    if pid==os.getpid():return
    if sig==signal.SIGCONT and pid in frozen:
     if token(pid)!=frozen.pop(pid):raise RuntimeError('PROCESS_OWNER_CHANGED')
     return
    self.guard_effects()
    if sig==signal.SIGSTOP:frozen[pid]=token(pid)
   elif event=='subprocess.Popen':self.guard_effects()
   elif event=='urllib.Request'and(args[1]is not None or args[3]not in {'GET','HEAD'}):self.guard_effects()
  sys.addaudithook(audit)
  def watch_intent():
   while not self.finalized.wait(.2):
    if not self.intent_unchanged():
     if not self.done:os.kill(os.getpid(),signal.SIGTERM)
     return
  threading.Thread(target=watch_intent,name='qa-user-runtime-intent',daemon=True).start()
 def confirm_cleanup(self):
  self.cleanup_status='CONFIRMED'
  if self.script.name=='runtime-guard.py':
   owned={name for name,mode in self.manifest.get('resources',[])}
   for target,baseline in getattr(self,'quarantines_at_admission',[]):
    try:
     current=json.loads(target.read_text())
     affected=set(current.get('resources',[self.profile+'-avd',self.profile+'-service']))
     if self.intent_unchanged()and current.get('kind','CLEANUP')=='CLEANUP'and current==baseline and affected<=owned:target.unlink()
    except (OSError,ValueError):pass
 def require_cleanup(self,name,probe):
  self.cleanup_barriers.append((name,probe));self.manifest.setdefault('cleanupObligations',[]).append(name);atomic(self.dir/'manifest.json',self.manifest)
 def verify_cleanup(self):
  for name,probe in self.cleanup_barriers:
   try:ok=probe()is True
   except Exception:ok=False
   self.metrics.setdefault('cleanupObligations',{})[name]=ok
   if not ok:self.cleanup_status='UNCONFIRMED';return False
  if not self.effect_started:return True
  if not self.intent_unchanged():self.cleanup_status='SUPERSEDED';return False
  import urllib.request
  port=8878 if self.profile=='public'else 8876;path='/api/status'if self.profile=='public'else'/api/personal/status'
  until=time.monotonic()+10
  while time.monotonic()<until:
   try:
    state=json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=2));a=state.get('app',{})
    route=ROOT/('.tools/profiles/public/demo-audio-state.json'if self.profile=='public'else'.tools/demo-audio-state.json')
    idle=a.get('sessionStatus')=='STOPPED'and a.get('capture')=='STOPPED'and a.get('playback')=='IDLE'and a.get('focus')=='NONE'and not state.get('voiceBusy')and not state.get('lease',{}).get('busy')and not route.exists()
    if self.profile=='personal'and(ROOT/'.tools/private/navigation-original.json').exists():idle=False
    if idle:
     names=subprocess.check_output([str(ROOT/'.tools/android-sdk/platform-tools/adb'),'-s',self.manifest['installed']['serial'],'shell','ps','-A','-o','NAME'],timeout=3).decode().splitlines()
     if 'ai.teammoon.pli:voice'not in names:self.confirm_cleanup();return True
   except (OSError,ValueError,KeyError,subprocess.SubprocessError):pass
   time.sleep(.2)
  return False
 def diagnostic(self,state,label='state'):
  folder=ROOT/'.tools/private'/self.id;folder.mkdir(parents=True,exist_ok=True,mode=0o700);path=folder/(label+'.json');atomic(path,{'runId':self.id,'apkSha256':self.manifest.get('apkSha256'),'profile':self.profile,'state':state});path.chmod(0o600);return str(path.relative_to(ROOT))
 def inputs_changed(self):
  try:return sha(Path(__file__))!=self.manifest['evidenceToolSha256']or declared_contract(self.script,sys.argv[1:])!=self.contract or fingerprint(self.contract)!=self.input_fingerprint or sha(self.script)!=self.manifest['scriptSha256']or any(sha(ROOT/name)!=digest for name,digest in self.manifest['dependencies'].items())
  except (OSError,ValueError,SyntaxError):return True
 def intent_unchanged(self):
  if not hasattr(self,'intent'):return True
  from runtime_context import runtime_intent
  return runtime_intent(self.intent_dir)['generation']==self.intent['generation']
 def finish(self):
  if self.done:return
  self.verify_cleanup()
  self.done=True;changed=self.inputs_changed();missing=[k for k in self.planned if k not in self.checks];unknown=set(self.checks)-set(self.planned)
  if self.native and not self.intent_unchanged():self.failure=self.failure or'RUNTIME_INTENT_CHANGED'
  installed_ok=not self.native or self.identity_checked and self.manifest['installed'].get('sha256')==self.manifest['apkSha256']and(not self.effect_started or self.intent_unchanged()and installed_identity(self.profile).get('sha256')==self.manifest['apkSha256'])
  build_ok=not self.native or self.identity_checked and self.manifest["buildInputsMatch"]and(not self.effect_started or build_matches())
  cleanup_ok=(not self.effect_started or self.cleanup_status=='CONFIRMED')and all(self.metrics.get('cleanupObligations',{}).values())
  passed=cleanup_ok and installed_ok and build_ok and bool(self.checks)and all(v is True for v in self.checks.values())and not missing and not unknown and self.failure is None and not changed
  status='PASSED'if passed else 'CANCELLED'if self.failure=='CANCELLED'else'INCOMPLETE'if missing or unknown or changed else'FAILED'
  result={**self.base,'recordVersion':3,'status':status,'passed':passed,'checks':{k:('PASS'if self.checks.get(k)is True else'NOT_EVALUATED'if k in self.checks and self.checks[k]is None else'FAIL'if k in self.checks else'NOT_RUN')for k in sorted(set(self.planned)|self.checks.keys())},'metrics':self.metrics,'elapsedSeconds':round(time.monotonic()-self.start,3),'error':self.failure,'sourceChanged':changed,'installedMatchesArtifact':installed_ok,'buildInputsMatch':build_ok,'cleanupStatus':self.cleanup_status,'unknownChecks':sorted(unknown),'finishedAt':datetime.datetime.now().astimezone().isoformat(),'manifest':'manifest.json'}
  result['claims']={name:{'status':'PASSED'if cleanup_ok and installed_ok and build_ok and not changed and self.failure not in {'CANCELLED','PRECONDITION_FAILED','PRECONDITION_CHANGED','PRECONDITION_PAUSED','CLEANUP_UNCONFIRMED'}and all(self.checks.get(k)is True for k in keys)else'INCOMPLETE','checks':keys,'cleanupStatus':self.cleanup_status}for name,keys in self.manifest.get('plannedClaims',{}).items()}
  result['unsafeResources']=sorted(unsafe_resources(result,self.manifest))
  atomic(self.dir/'result.json',result)
  try:latest=json.loads(self.latest.read_text()).get('runId')
  except (OSError,ValueError):latest=None
  if latest in {None,self.id}:atomic(self.latest,result)
  if result['unsafeResources']:
   kind='CLEANUP'if self.cleanup_status=='UNCONFIRMED'else'SAFETY'
   save_quarantine(self.manifest,self.id,'unconfirmed cleanup'if kind=='CLEANUP'else'explicit safety invariant failed or missing',kind,result['unsafeResources'],[key for key in self.manifest['safetyChecks']if result['checks'].get(key)!='PASS'])
  elif passed:
   # A fresh observation by the same public-boundary owner may resolve its own
   # exposure finding. Closing resources never proves restoration of data.
   for target,baseline in getattr(self,'quarantines_at_admission',[]):
    keys=baseline.get('failedChecks',[])
    if baseline.get('kind')=='SAFETY'and baseline.get('resources')==['public-service']and baseline.get('script')==self.manifest['script']and keys and all(self.manifest['safetyChecks'].get(key)=='public-service'and self.checks.get(key)is True for key in keys):
     try:
      if self.intent_unchanged()and json.loads(target.read_text())==baseline:target.unlink()
     except (OSError,ValueError):pass
  if hasattr(self,'resource_context'):self.resource_context.__exit__(None,None,None)
  else:
   for lock in reversed(self.locks):lock.close()
  self.finalized.set()
  print(json.dumps({'runId':self.id,'status':status,'checks':len(result['checks']),'notRun':len(missing),'sourceChanged':changed}),flush=True)
