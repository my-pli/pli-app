#!/usr/bin/env python3
"""Freeze an offline review bundle; publish product assets, keep engineering files private."""
from pathlib import Path
import argparse,hashlib,json,re,sys,os,shutil,fcntl,tempfile,zipfile,runpy,contextlib
from delivery_assets import publish_file,atomic_json,PUBLIC_KINDS,commit_delivery
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
# Product requirements remain visible even when a smaller delivery is selected.
REQUIREMENTS={
 'web':['public-access','portal-layout','server-contract'],
 'app':['public-access','portal-journey','experience-voice','voice-performance','session-boundaries','silent-output','viewport-recovery'],
 'pleos':['public-access','portal-performance','portal-edge','server-crash','lease-recovery','native-ttl'],
 'family':['kidsnote-integration','parent-private','document-transfer'],
 'navigation':['private-navigation']}
def selected_requirements(scope):
 return set(REQUIREMENTS.get(scope,[]))if scope in REQUIREMENTS else set().union(*map(set,REQUIREMENTS.values()))if scope=='product'else set()
def export_files():
 files=[ROOT/name for name in ['README.md','pleos','.gitignore']if(ROOT/name).is_file()]
 for folder in ['android','demo-v2','scripts','docs','qa/native','media/pli-film']:
  for path in (ROOT/folder).rglob('*'):
   if not path.is_file():continue
   rel=path.relative_to(ROOT)
   if any(part in rel.parts for part in ['build','.gradle','.kotlin','__pycache__','model-ko','runs','before-redesign']):continue
   if path.name=='local.properties'or path.suffix in {'.keystore','.pem','.key','.p12'}:continue
   if folder=='qa/native'and path.suffix not in {'.py','.mjs','.wav'}and not('fixtures'in rel.parts and path.suffix in {'.json','.txt'}):continue
   files.append(path)
 return sorted(set(files))
def private_values():
 secrets=[];private=ROOT/'.tools/private/kidsnote'
 key=private/'key.txt'
 if key.exists():
  for line in key.read_text().splitlines():
   if '='in line:
    value=line.split('=',1)[1].strip()
    if len(value)>=6:secrets.append(value.encode())
 token=private/'mcp-token'
 if token.exists():secrets.append(token.read_bytes().strip())
 try:
  for cookie in json.loads((private/'browser.json').read_text()).get('cookies',[]):
   if cookie.get('name')in {'sessionid','csrftoken'}and len(cookie.get('value',''))>=12:secrets.append(cookie['value'].encode())
 except (OSError,ValueError,AttributeError):pass
 return secrets
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--review',action='store_true');parser.add_argument('--stage-dir',type=Path);parser.add_argument('--scope',choices=['product','web','app','pleos','family','navigation','media'],default='product');parser.add_argument('--live-installation',action='store_true',help='Explicit read-only proof of both currently installed APKs')
 args=parser.parse_args();output=args.stage_dir.resolve()if args.stage_dir else ROOT;artifacts=output/'artifacts';artifacts.mkdir(parents=True,exist_ok=True);tools=output/'.tools';tools.mkdir(parents=True,exist_ok=True)
 from build_identity import valid_build
 sys.path.insert(0,str(ROOT/'qa/native'))
 report=runpy.run_path(str(ROOT/'scripts/build-report.py'));context=report['EvaluationContext']();apk=ROOT/'artifacts/pli-pleos.apk';apk_hash=context.apk
 if not valid_build(apk,apk_digest=apk_hash):raise SystemExit('Native sources differ from build inputs')
 qualified=[];evidence=[];files=export_files()
 for _,(_,mpath,manifest)in sorted(context.latest.items()):
  result=json.loads(mpath.with_name('result.json').read_text());issues=context.evaluate(result,manifest)
  evidence.append({'script':manifest['script'],'scope':manifest.get('scope','legacy full'),'runId':manifest['runId'],'status':result['status'],'qualificationIssues':issues});files.extend([mpath,mpath.with_name('result.json')])
  if not issues:qualified.append({'script':manifest['script'],'scope':manifest.get('scope','full'),'runId':manifest['runId']})
 required=selected_requirements(args.scope);valid={Path(item['script']).stem for item in qualified if item['scope']=='full'};missing=sorted(required-valid)
 # Automation cannot certify the unmet human/vehicle/navigation requirements.
 overall_missing=['human-first-use','real-vehicle-acceptance']+sorted(set().union(*map(set,REQUIREMENTS.values()))-valid)
 if missing and not args.review:raise SystemExit('Publication refused; selected product evidence missing: '+', '.join(missing))
 report_info=ROOT/'docs/report-info.json'
 if report_info.is_file():
  info=json.loads(report_info.read_text())
  if info.get('apkSha256')!=apk_hash or len(info.get('files',{}))!=3 or any(not(ROOT/name).is_file()or sha(ROOT/name)!=value for name,value in info.get('files',{}).items()):raise SystemExit('Report inputs are not bound to current APK/files')
 secrets=private_values();files=sorted(set(files));version=re.search(r'versionName\s*=\s*"([^"]+)"',(ROOT/'android/app/build.gradle.kts').read_text()).group(1)
 installed={};observed_at=None
 with contextlib.ExitStack()as stack:
  lock=stack.enter_context((tools/'publication.lock').open('a'));fcntl.flock(lock,fcntl.LOCK_EX)
  from contracts import resource_locks,conflicting_quarantines
  conflicts=conflicting_quarantines([('public-service','shared')],ROOT/'.tools/qa-resources')
  if any(value.get('kind')=='SAFETY'for path,value in conflicts):raise SystemExit('Publication refused: unresolved public privacy invariant')
  stack.enter_context(resource_locks([('host-load','shared')],ROOT/'.tools/qa-resources'))
  if args.live_installation:
   from run_record import installed_identity
   from runtime_context import runtime_intent,SHARED
   stack.enter_context(resource_locks([(name,'shared')for name in ['personal-service','public-service','personal-avd','public-avd']],ROOT/'.tools/qa-resources'))
   for profile in ['personal','public']:
    folder=SHARED if profile=='personal'else SHARED/'profiles/public'
    if runtime_intent(folder)['desiredState']!='running':raise SystemExit('Live installation unavailable while paused')
    item=installed_identity(profile)
    if item.get('sha256')!=apk_hash:raise SystemExit('Live installed APK differs: '+profile)
    installed[profile]=item
   import datetime
   observed_at=datetime.datetime.now().astimezone().isoformat()
  with tempfile.TemporaryDirectory(prefix='pli-snapshot-',dir=tools)as folder:
   staging=Path(folder);snapshot=staging/'source';snapshot.mkdir();expected={}
   for path in files:
    name=str(path.relative_to(ROOT));target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);expected[name]=sha(target)
    if path.suffix.lower()in {'.md','.html','.json','.py','.mjs','.kt','.js','.txt','.xml','.kts'}and any(secret and secret in target.read_bytes()for secret in secrets):raise SystemExit('Private credential detected in export: '+name)
   # Copy the APK separately. Hashing/readback is an actual delivery check,
   # distinct from the single cached APK read in the evaluation loop.
   frozen_apk=staging/'pli-pleos.apk';shutil.copyfile(apk,frozen_apk)
   if sha(frozen_apk)!=apk_hash:raise SystemExit('SOURCE_CHANGED: APK')
   identity={'version':version,'channel':'review'if args.review else'release','selectedScope':args.scope,'selectedScopeComplete':not missing,'overallRequirementsComplete':False,'acceptanceComplete':False,'missingAcceptance':missing,'remainingRequirements':overall_missing,'apkSha256':apk_hash,'installationObservation':{'current':bool(installed),'observedAt':observed_at,'profiles':installed},'files':expected,'privateAssetsExcluded':True,'qualifiedRuns':qualified,'latestEvidence':evidence,'build':json.loads((ROOT/'artifacts/build-info.json').read_text())}
   archive=staging/'source.zip'
   with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
    for name in expected:z.write(snapshot/name,name)
    z.writestr('SOURCE-MANIFEST.json',json.dumps(identity,ensure_ascii=False,indent=2))
   with zipfile.ZipFile(archive)as z:
    if z.testzip()is not None:raise RuntimeError('ZIP_CRC')
    for name,value in expected.items():
     if hashlib.sha256(z.read(name)).hexdigest()!=value:raise RuntimeError('ZIP_BYTES: '+name)
   # All public paths are staged from that same snapshot. Internal source ZIP,
   # reports and engineering evidence never enter the public allowlist.
   public_files={'apk':frozen_apk,'brief':snapshot/'docs/pli-pleos-product-brief.pdf'}
   for kind,name in {'web-index':'index.html','web-js':'app.js','web-css':'style.css','web-worklet':'audio-worklet.js','web-font':'font.woff2','web-poster':'poster.svg','web-pleos':'pleos-preview.jpg','video':'preview.mp4','subtitles':'preview.vtt','transcript':'preview-transcript.txt','preview-manifest':'preview-info.json'}.items():public_files[kind]=snapshot/'demo-v2'/name
   assets={kind:publish_file(path,kind,staging/'published')for kind,path in public_files.items()if path.is_file()}
   if args.scope=='media'and not {'video','subtitles','transcript','preview-manifest'}<=assets.keys():raise SystemExit('Selected media assets missing')
   if 'video'in assets:
    if 'preview-manifest'not in assets:raise SystemExit('Video identity missing')
    media=json.loads(public_files['preview-manifest'].read_text())
    if media.get('videoSha256')!=assets['video']['sha256']:raise SystemExit('Video identity differs from staged bytes')
    if media.get('type')=='product-story'and(media.get('actualAppFootage')is not False or not 30<=media.get('durationSeconds',0)<=60):raise SystemExit('Product story identity/duration invalid')
   if any(not(ROOT/name).is_file()or sha(ROOT/name)!=value for name,value in expected.items())or sha(apk)!=apk_hash or not valid_build(apk,apk_digest=apk_hash):raise SystemExit('SOURCE_CHANGED: previous publication preserved')
   context.assert_inputs_unchanged();context.assert_latest_unchanged(required)
   existing_pin=output/'.tools/published'/(apk_hash+'.apk')
   if existing_pin.exists()and sha(existing_pin)!=apk_hash:raise RuntimeError('PINNED_APK_CORRUPT')
   target=artifacts/('pli-pleos-review-source.zip'if args.review else'pli-pleos-source.zip')
   vector={k:v for k,v in identity.items()if k!='files'};vector.update(assets=assets,sourceZipSha256=sha(archive),sourceFileCount=len(expected),sourceManifest='SOURCE-MANIFEST.json',deliveryVerified=False,webVector={name:value for name,value in expected.items()if name.startswith('demo-v2/')and Path(name).suffix in {'.js','.css','.html','.woff2'}},evaluationApkDigestReads=context.digestReads.get(str(apk),0),privateCredentialScanPassed=True)
   destination=artifacts/('review-delivery.json'if args.review else'delivery.json')
   commit_delivery(staging,output/'.tools/published',assets,archive,target,destination,vector)
   print(json.dumps({'vector':str(destination.relative_to(output)),'scope':args.scope,'selectedScopeComplete':not missing,'overallRequirementsComplete':False,'missingAcceptance':missing,'sourceFileCount':len(expected),'deviceAccess':args.live_installation,'evaluationApkDigestReads':vector['evaluationApkDigestReads']},ensure_ascii=False))
if __name__=='__main__':main()
