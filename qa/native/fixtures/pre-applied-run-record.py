"""Execution evidence shared by the existing native QA scripts; no stale PASS reuse."""
from pathlib import Path
import atexit,ast,datetime,hashlib,json,os,signal,subprocess,sys,time,uuid,fcntl,threading
ROOT=Path(__file__).resolve().parents[2]
LEGACY_NORMAL_TOOL='0ff056ab2ec25aafbf55a30dd3db4511e96d0cd62e94ce2f55aea52180b8a469'
COMPATIBLE_NORMAL_V2='bbb3bac8d52af45e1235637c2a531a6f5fb2baf750f184c7826754b201d797cf'
def compatible_tool(manifest,result):
 current=sha(Path(__file__))
 if manifest.get('evidenceToolSha256')==current:return True
 normal=result.get('status')=='PASSED'and result.get('passed')is True and result.get('error')is None and result.get('sourceChanged')is False and bool(result.get('checks'))and all(v=='PASS'for v in result['checks'].values())
 if not normal:return False
 if manifest.get('recordVersion',1)==1:return manifest.get('evidenceToolSha256')==LEGACY_NORMAL_TOOL
 return manifest.get('recordVersion')==2 and manifest.get('evidenceToolSha256')in {COMPATIBLE_NORMAL_V2,'7afa3503cefce55b04dd4a86a721f675d996604d9677c32d96758f33ca4a433a'} and (manifest.get('executionKind')!='NATIVE_OWNER'or manifest.get('evidenceToolSha256')=='7afa3503cefce55b04dd4a86a721f675d996604d9677c32d96758f33ca4a433a'and result.get('metrics',{}).get('cleanupObligations',{}).get('guestInstrumentationTerminated')is True)and result.get('cleanupStatus')in ({'CONFIRMED'}if manifest.get('effects')else{'NOT_REQUIRED','CONFIRMED'})

def resources_for(script,profile,execution_kind):
 name=Path(script).name
 result=[('host-load','exclusive'if name in {'portal-performance.py','voice-performance.py'}else'shared')]
 if execution_kind in {'JVM','MCP_FIXTURE','HOST_CONTRACT','EVIDENCE','DELIVERY'}:return result
 result.append((profile+'-avd','exclusive'))
 if profile=='public':result.append(('public-service','exclusive'if name in {'server-crash.py','lease-recovery.py','native-ttl.py'}else'shared'))
 elif name in {'kidsnote-integration.py','parent-private.py'}:result.append(('public-service','shared'))
 return result
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
    r.update(status='INCOMPLETE',passed=False,error='process_terminated_without_final_result',cleanupStatus='UNCONFIRMED');atomic(p,r)
    m=json.loads(p.with_name('manifest.json').read_text())
    latest=ROOT/m['script'];latest=latest.with_suffix('.json')
    if latest.exists()and json.loads(latest.read_text()).get('runId')==r['runId']:atomic(latest,r)
    if m.get('recordVersion',1)>=2 and m.get('effects'):
     atomic(ROOT/'.tools/qa-resources'/('quarantine-'+m['profile']+'.json'),{'runId':r['runId'],'reason':'owner process vanished before final cleanup'})
  except (OSError,ValueError,KeyError,IndexError):pass
class RunRecord:
 def __init__(self,script,checks,metrics=None,dependencies=(),execution_kind=None,fixtures=None,claims=None):
  reconcile();self.script=Path(script);self.kind=execution_kind or kind(script);self.native=self.kind in {"NATIVE_E2E","NATIVE_OWNER","DELIVERY"};self.profile=os.environ.get("PLI_QA_PROFILE","public"if self.script.name in PUBLIC_OWNERS else"personal");self.checks=checks;self.metrics=metrics if metrics is not None else {};self.failure=None;self.done=False;self.locks=[];self.cleanup_status='NOT_REQUIRED';self.effect_started=False;self.cleanup_barriers=[];self.finalized=threading.Event();self.cleanup_budget=150 if self.script.name=='private-navigation.py'else 100 if self.script.name=='cold-start.py'else 30
  self.id=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];self.dir=ROOT/'qa/native/runs'/self.id;self.latest=self.script.with_suffix('.json');self.start=time.monotonic()
  tree=ast.parse(self.script.read_text());self.planned=sorted({n.targets[0].slice.value for n in ast.walk(tree)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Subscript)and isinstance(n.targets[0].value,ast.Name)and n.targets[0].value.id=='checks'and isinstance(n.targets[0].slice,ast.Constant)and isinstance(n.targets[0].slice.value,str)})
  self.manifest={'recordVersion':2,'arguments':sys.argv[1:],'plannedClaims':claims or{},'runId':self.id,'script':str(self.script.relative_to(ROOT)),'scriptSha256':sha(self.script),'evidenceToolSha256':sha(Path(__file__)),'source':source_snapshot(self.script),'executionKind':self.kind,'claimScope':'actual installed APK path'if self.native else self.kind,'profile':self.profile if self.native else None,'nativeRequired':self.native,'plannedChecks':self.planned,'startedAt':datetime.datetime.now().astimezone().isoformat(),'apkSha256':sha(ROOT/'artifacts/pli-pleos.apk')if (ROOT/'artifacts/pli-pleos.apk').exists()else None,'buildInputsMatch':True,'dependencies':{name:sha(ROOT/name)for name in dependencies},'installed':{},'fixtures':{p.name:sha(p)for p in (ROOT/'qa/native/fixtures').glob('*.wav') if (self.kind=='NATIVE_E2E'or fixtures is not None)and self.script.name not in {'portal-layout.py','portal-performance.py','public-access.py','portal-edge.py'}and (fixtures is None or p.name in fixtures)}}
  self.base={'runId':self.id,'pid':os.getpid(),'processStart':Path(f'/proc/{os.getpid()}/stat').read_text().split()[21],'status':'RUNNING','passed':False}
  if self.latest.exists():
   prior=ROOT/'qa/native/runs/legacy'/(self.id+'-'+self.latest.name);prior.parent.mkdir(parents=True,exist_ok=True);prior.write_bytes(self.latest.read_bytes())
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
    if self.effect_started:atomic(ROOT/'.tools/qa-resources'/('quarantine-'+self.profile+'.json'),{'runId':self.id,'reason':'cleanup deadline exceeded'})
    if os.getpgrp()==os.getpid():os.killpg(os.getpid(),signal.SIGKILL)
    os._exit(130)
   threading.Thread(target=deadline,name='qa-cleanup-deadline',daemon=True).start()
   raise SystemExit(128+sig)
  signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel);atexit.register(self.finish)
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
  requested=resources_for(self.script,self.profile,self.kind);folder=ROOT/'.tools/qa-resources';folder.mkdir(parents=True,exist_ok=True)
  for name,mode in sorted(requested,key=lambda v:(0 if v[0]=='host-load'else 1 if v[0].endswith('-service')else 2,v[0])):
   lock=(folder/(name+'.lock')).open('a');self.locks.append(lock);began=time.monotonic();notified=False
   while True:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB if mode=='exclusive'else fcntl.LOCK_SH|fcntl.LOCK_NB);break
    except BlockingIOError:
     if not notified:print(json.dumps({'runId':self.id,'phase':'WAIT_RESOURCE','resource':name,'mode':mode}),flush=True);notified=True
     time.sleep(.1)
   self.metrics.setdefault('resourceWaitSeconds',{})[name]=round(time.monotonic()-began,3)
  self.manifest['resources']=requested;self.manifest['effects']=self.kind in {'NATIVE_E2E','NATIVE_OWNER'}and self.script.name!='public-access.py'
  quarantine=folder/('quarantine-'+self.profile+'.json')
  if self.manifest['effects']and quarantine.exists()and self.script.name!='runtime-guard.py':self.failure='CLEANUP_UNCONFIRMED';self.finish();raise SystemExit('Owned device quarantined pending confirmed recovery')
  self.manifest['buildInputsMatch']=build_matches()if self.native else True;self.manifest['installed']=installed_identity(self.profile)if self.native else {};atomic(self.dir/'manifest.json',self.manifest)
  if self.native and (not self.manifest['buildInputsMatch']or self.manifest['installed'].get('sha256')!=self.manifest['apkSha256']):
   self.failure='PRECONDITION_FAILED';self.finish();raise SystemExit('QA refused: complete the matching build and installation first')
  self.effect_started=self.manifest['effects'];self.cleanup_status='UNCONFIRMED'if self.effect_started else'NOT_REQUIRED'
 def confirm_cleanup(self):
  self.cleanup_status='CONFIRMED'
  if self.script.name=='runtime-guard.py':(ROOT/'.tools/qa-resources'/('quarantine-'+self.profile+'.json')).unlink(missing_ok=True)
 def require_cleanup(self,name,probe):
  self.cleanup_barriers.append((name,probe));self.manifest.setdefault('cleanupObligations',[]).append(name);atomic(self.dir/'manifest.json',self.manifest)
 def verify_cleanup(self):
  for name,probe in self.cleanup_barriers:
   try:ok=probe()is True
   except Exception:ok=False
   self.metrics.setdefault('cleanupObligations',{})[name]=ok
   if not ok:self.cleanup_status='UNCONFIRMED';return False
  if not self.effect_started:return True
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
 def finish(self):
  if self.done:return
  self.verify_cleanup()
  self.done=True;changed=sha(Path(__file__))!=self.manifest['evidenceToolSha256']or source_snapshot(self.script)!=self.manifest['source'] or sha(self.script)!=self.manifest['scriptSha256'] or any(sha(ROOT/name)!=digest for name,digest in self.manifest['dependencies'].items())or any(not(ROOT/'qa/native/fixtures'/name).is_file()or sha(ROOT/'qa/native/fixtures'/name)!=digest for name,digest in self.manifest['fixtures'].items());missing=[k for k in self.planned if k not in self.checks]
  installed_ok=not self.native or self.manifest['installed'].get('sha256')==self.manifest['apkSha256'] and installed_identity(self.profile).get('sha256')==self.manifest['apkSha256']
  build_ok=not self.native or self.manifest["buildInputsMatch"] and build_matches()
  cleanup_ok=(not self.effect_started or self.cleanup_status=='CONFIRMED')and all(self.metrics.get('cleanupObligations',{}).values())
  passed=cleanup_ok and installed_ok and build_ok and bool(self.checks)and all(v is True for v in self.checks.values())and not missing and self.failure is None and not changed
  status='PASSED'if passed else 'CANCELLED'if self.failure=='CANCELLED'else'INCOMPLETE'if missing or changed else'FAILED'
  result={**self.base,'recordVersion':2,'status':status,'passed':passed,'checks':{k:('PASS'if self.checks.get(k)is True else'FAIL'if k in self.checks else'NOT_RUN')for k in sorted(set(self.planned)|self.checks.keys())},'metrics':self.metrics,'elapsedSeconds':round(time.monotonic()-self.start,3),'error':self.failure,'sourceChanged':changed,'installedMatchesArtifact':installed_ok,'buildInputsMatch':build_ok,'cleanupStatus':self.cleanup_status,'finishedAt':datetime.datetime.now().astimezone().isoformat(),'manifest':'manifest.json'}
  result['claims']={name:{'status':'PASSED'if cleanup_ok and installed_ok and build_ok and not changed and self.failure not in {'CANCELLED','PRECONDITION_FAILED','CLEANUP_UNCONFIRMED'}and all(self.checks.get(k)is True for k in keys)else'INCOMPLETE','checks':keys,'cleanupStatus':self.cleanup_status}for name,keys in self.manifest.get('plannedClaims',{}).items()}
  atomic(self.dir/'result.json',result)
  try:latest=json.loads(self.latest.read_text()).get('runId')
  except (OSError,ValueError):latest=None
  if latest in {None,self.id}:atomic(self.latest,result)
  if self.effect_started and self.cleanup_status!='CONFIRMED':atomic(ROOT/'.tools/qa-resources'/('quarantine-'+self.profile+'.json'),{'runId':self.id,'reason':'cancellation cleanup not confirmed'})
  for lock in reversed(self.locks):lock.close()
  self.finalized.set()
  print(json.dumps({'runId':self.id,'status':status,'checks':len(result['checks']),'notRun':len(missing),'sourceChanged':changed}),flush=True)
