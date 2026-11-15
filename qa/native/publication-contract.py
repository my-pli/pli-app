"""Frozen offline packaging, selected product scope and private publication boundaries."""
QA_CONTRACT = {'full': {'profile': None,
          'nativeRequired': False,
          'expectedChecks': ['concurrentSourceEditRefusesCandidateCommit',
                             'evaluationHashesApkOnce',
                             'failedPublicationPreservesPreviousVectorAndZip',
                             'offlineSnapshotDoesNotRequireRunningAvd',
                             'publicAssetsExcludeAllInternalKinds',
                             'reviewIsExplicitAndNeverWholeProductAcceptance',
                             'selectedMissingEvidenceRefusesPublication',
                             'selectedProductScopeCanPublishWithoutMetaSuite',
                             'selectedScopeCannotCertifyOverallRequirements',
                             'sourceChangePreservesPreviousVectorAndZip',
                             'commitFailureRollsBackVectorIndexAndZip',
                             'reviewCannotBypassKnownPublicPrivacyFailure',
                             'newSelectedFailureCannotHideBehindFrozenPass'],
          'safetyChecks': {},
          'inputs': ['qa/native/contracts.py',
                     'qa/native/run-acceptance.py',
                     'qa/native/run_record.py',
                     'scripts/build-report.py',
                     'scripts/build_identity.py',
                     'scripts/delivery_assets.py',
                     'scripts/package-source.py'],
          'fixtures': [],
          'effects': 'none',
          'resources': [['host-load', 'shared']],
          'executionKind': 'DELIVERY'}}
from pathlib import Path
import hashlib,json,tempfile,runpy,sys,copy,subprocess
from unittest.mock import patch
from run_record import RunRecord,sha as record_sha
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics)
sys.path.insert(0,str(ROOT/'scripts'));import build_identity,delivery_assets
real_runpy=runpy.run_path;package=real_runpy(str(ROOT/'scripts/package-source.py'));real_root=ROOT
with tempfile.TemporaryDirectory(prefix='pli-publication-fixture-')as directory:
 root=Path(directory)/'project';root.mkdir();(root/'artifacts').mkdir();(root/'demo-v2').mkdir();(root/'docs').mkdir();(root/'qa/native/runs').mkdir(parents=True);(root/'android/app').mkdir(parents=True)
 (root/'README.md').write_text('Frozen fixture source.');(root/'android/app/build.gradle.kts').write_text('versionName = "fixture"');apk=root/'artifacts/pli-pleos.apk';apk.write_bytes(b'APK fixture, never a real installation');(root/'docs/pli-pleos-product-brief.pdf').write_bytes(b'product-brief-fixture')
 for name in ['index.html','app.js','style.css','audio-worklet.js','font.woff2','poster.svg','pleos-preview.jpg']:(root/'demo-v2'/name).write_bytes(('product fixture '+name).encode())
 old_build_root=build_identity.ROOT;build_identity.ROOT=root
 try:
  (root/'artifacts/build-info.json').write_text(json.dumps({'apkSha256':record_sha(apk),'nativeSources':build_identity.native_sources()}))
  report=real_runpy(str(real_root/'scripts/build-report.py'));globals_=report['EvaluationContext'].__init__.__globals__;globals_['ROOT']=root;globals_['source_snapshot']=lambda:{}
  contract={'scope':'full','profile':None,'nativeRequired':False,'expectedChecks':['one'],'safetyChecks':{},'inputs':[],'fixtures':[],'effects':'none','resources':[['host-load','shared']],'executionKind':'HOST_CONTRACT'}
  from contracts import contract_digest
  for name in ['public-access','portal-layout','server-contract']:
   owner=root/'qa/native'/(name+'.py');owner.write_text('QA_CONTRACT = '+repr({'full':{k:v for k,v in contract.items()if k!='scope'}})+'\n');folder=root/'qa/native/runs'/name;folder.mkdir()
   manifest={'recordVersion':3,'runId':name,'script':str(owner.relative_to(root)),'scriptSha256':record_sha(owner),'evidenceToolSha256':record_sha(real_root/'qa/native/run_record.py'),'executionContract':contract,'contractSha256':contract_digest(contract),'source':{},'dependencies':{},'fixtures':{},'nativeRequired':False,'effects':False,'buildInputsMatch':True,'scope':'full','startedAt':'2026-11-12','arguments':[]}
   result={'runId':name,'status':'PASSED','passed':True,'checks':{'one':'PASS'},'sourceChanged':False,'buildInputsMatch':True,'installedMatchesArtifact':True,'cleanupStatus':'NOT_REQUIRED'}
   (folder/'manifest.json').write_text(json.dumps(manifest));(folder/'result.json').write_text(json.dumps(result))
  main=package['main'];main.__globals__['ROOT']=root
  def reader(path,*args,**kwargs):
   if Path(path).name=='build-report.py':return report
   return real_runpy(path,*args,**kwargs)
  def invoke(output,*arguments):
   with patch('runpy.run_path',side_effect=reader),patch.object(sys,'argv',['package-source.py','--stage-dir',str(output),'--scope','web',*arguments]),patch('subprocess.check_output',side_effect=AssertionError('Offline export touched a device')):
    try:main();return True,None
    except (SystemExit,RuntimeError)as e:return False,str(e)
  staged=Path(directory)/'staged';ok,error=invoke(staged);vector=staged/'artifacts/delivery.json';candidate=json.loads(vector.read_text())if ok else{}
  checks['selectedProductScopeCanPublishWithoutMetaSuite']=ok and candidate.get('selectedScopeComplete')is True
  checks['selectedScopeCannotCertifyOverallRequirements']=ok and candidate.get('overallRequirementsComplete')is False and candidate.get('acceptanceComplete')is False
  checks['offlineSnapshotDoesNotRequireRunningAvd']=ok and not candidate.get('installationObservation',{}).get('current')
  checks['publicAssetsExcludeAllInternalKinds']=ok and set(candidate.get('assets',{}))<=delivery_assets.PUBLIC_KINDS and not any(k in candidate.get('assets',{})for k in ['report','audit','design','source'])
  raw=vector.read_bytes();index=staged/'.tools/published/index.json';before_index=index.read_bytes();source=staged/'artifacts/pli-pleos-source.zip';before_zip=record_sha(source)
  failed=root/'qa/native/runs/public-access/result.json';original=failed.read_text();obj=json.loads(original);obj.update(status='FAILED',passed=False);failed.write_text(json.dumps(obj))
  refused,error=invoke(staged);checks['selectedMissingEvidenceRefusesPublication']=not refused and 'selected product evidence missing'in error
  checks['failedPublicationPreservesPreviousVectorAndZip']=vector.read_bytes()==raw and index.read_bytes()==before_index and record_sha(source)==before_zip
  failed.write_text(original)
  original_publish=main.__globals__['publish_file'];changed=False
  def change_during_snapshot(*args,**kwargs):
   global changed
   item=original_publish(*args,**kwargs)
   if not changed:changed=True;(root/'README.md').write_text('Concurrent edit during candidate preparation.')
   return item
  main.__globals__['publish_file']=change_during_snapshot
  try:refused,error=invoke(staged)
  finally:main.__globals__['publish_file']=original_publish
  checks['concurrentSourceEditRefusesCandidateCommit']=not refused and 'SOURCE_CHANGED'in error
  checks['sourceChangePreservesPreviousVectorAndZip']=vector.read_bytes()==raw and index.read_bytes()==before_index and record_sha(source)==before_zip
  # Inject a failure at the last mutable commit, after ZIP/index replacement.
  # The real committer must restore all three original files.
  original_replace=Path.replace;injected=[False]
  def fail_vector(path,destination):
   if path.name=='commit-vector.json'and not injected[0]:injected[0]=True;raise RuntimeError('injected vector commit failure')
   return original_replace(path,destination)
  with patch.object(Path,'replace',fail_vector):refused,error=invoke(staged)
  checks['commitFailureRollsBackVectorIndexAndZip']=not refused and injected[0]and vector.read_bytes()==raw and index.read_bytes()==before_index and record_sha(source)==before_zip
  quarantine=root/'.tools/qa-resources/quarantine-public.json';quarantine.parent.mkdir(parents=True,exist_ok=True);quarantine.write_text(json.dumps({'kind':'SAFETY','resources':['public-service'],'runId':'fixture-privacy-failure'}))
  try:refused,error=invoke(Path(directory)/'unsafe-review','--review')
  finally:quarantine.unlink()
  checks['reviewCannotBypassKnownPublicPrivacyFailure']=not refused and 'unresolved public privacy invariant'in error
  # A newer selected failure arriving during staging must not be hidden by
  # the older qualified snapshot, even if source files remain unchanged.
  newer=root/'qa/native/runs/newer-failure';inserted=[False]
  def fail_during_stage(*args,**kwargs):
   item=original_publish(*args,**kwargs)
   if not inserted[0]:
    inserted[0]=True;newer.mkdir();m=json.loads((root/'qa/native/runs/public-access/manifest.json').read_text());r=json.loads((root/'qa/native/runs/public-access/result.json').read_text());m.update(runId='newer-failure',startedAt='2027');r.update(runId='newer-failure',status='FAILED',passed=False);(newer/'manifest.json').write_text(json.dumps(m));(newer/'result.json').write_text(json.dumps(r))
   return item
  main.__globals__['publish_file']=fail_during_stage
  try:refused,error=invoke(staged)
  finally:
   main.__globals__['publish_file']=original_publish
   if newer.exists():
    for file in newer.iterdir():file.unlink()
    newer.rmdir()
  checks['newSelectedFailureCannotHideBehindFrozenPass']=not refused and 'EVALUATION_LATEST_CHANGED'in error and vector.read_bytes()==raw and index.read_bytes()==before_index and record_sha(source)==before_zip
  review=Path(directory)/'review';ok,error=invoke(review,'--review');candidate=json.loads((review/'artifacts/review-delivery.json').read_text())if ok else{}
  checks['reviewIsExplicitAndNeverWholeProductAcceptance']=ok and candidate.get('channel')=='review'and candidate.get('acceptanceComplete')is False
  checks['evaluationHashesApkOnce']=ok and candidate.get('evaluationApkDigestReads')==1
 finally:build_identity.ROOT=old_build_root
metrics['scope']='Actual offline packager, actual reader and frozen ZIP bytes on isolated fixtures; no AVD, public pointer or live document writes.'
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
