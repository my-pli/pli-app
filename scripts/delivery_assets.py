"""Allowlisted, content-addressed public delivery files. No development directory serving."""
from pathlib import Path
import fcntl,hashlib,json,os,re,shutil,uuid
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'.tools/published'
PUBLIC_KINDS=frozenset({'apk','brief','video','subtitles','transcript','web-index','web-js','web-css','web-worklet','web-font','web-poster','web-pleos','preview-manifest'})
def internal_path(path):
 return (path=='/report' or path.startswith('/qa/') or path.startswith('/artifacts/') and ('source' in path or path.endswith('.json')) or path.startswith('/docs/') and path!='/docs/pli-pleos-product-brief.pdf')
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def atomic_json(path,value):
 path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');temp.chmod(0o600)
 with temp.open('rb')as f:os.fsync(f.fileno())
 temp.replace(path)
def publish_file(path,kind,folder=None):
 folder=Path(folder)if folder is not None else FOLDER
 path=Path(path)
 if kind not in PUBLIC_KINDS:raise ValueError('INTERNAL_ASSET_NOT_PUBLIC')
 digest=sha(path);suffix=''.join(path.suffixes[-1:]);name=digest+'.'+kind+suffix
 folder.mkdir(parents=True,exist_ok=True,mode=0o700);target=folder/name
 if target.exists():
  if sha(target)!=digest:raise RuntimeError('IMMUTABLE_ASSET_CORRUPT')
 else:
  temporary=target.with_suffix(target.suffix+'.tmp');shutil.copyfile(path,temporary);temporary.chmod(0o600)
  if sha(temporary)!=digest:raise RuntimeError('ASSET_READBACK')
  with temporary.open('rb')as f:os.fsync(f.fileno())
  temporary.replace(target)
 item={'filename':name,'sha256':digest,'bytes':target.stat().st_size,'href':'/published/'+name,'kind':kind}
 with (folder/'index.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  try:index=json.loads((folder/'index.json').read_text())
  except (OSError,ValueError):index={}
  index[name]=item;atomic_json(folder/'index.json',index)
 return item
def public_asset(name):
 if not re.fullmatch(r'[a-f0-9]{64}\.[a-z][a-z0-9-]*\.[a-z0-9]+',name):return None
 try:
  index=json.loads((FOLDER/'index.json').read_text());item=index[name];target=FOLDER/name
  if item.get('kind')not in PUBLIC_KINDS or name.split('.')[1]!=item.get('kind') or item['filename']!=name or not target.is_file()or target.stat().st_size!=item['bytes']:return None
  return target
 except (OSError,ValueError,KeyError):return None

def commit_delivery(staging,published,assets,archive,target,destination,vector):
 """Prepare immutable bytes first; roll back mutable files if commit raises."""
 staging=Path(staging);published=Path(published);published.mkdir(parents=True,exist_ok=True,mode=0o700)
 with(published/'index.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  index_path=published/'index.json'
  try:index=json.loads(index_path.read_text())
  except FileNotFoundError:index={}
  for item in assets.values():
   name=item['filename'];source=staging/'published'/name;output=published/name
   if not output.exists():
    temporary=published/(name+'.'+uuid.uuid4().hex+'.tmp')
    try:
     shutil.copyfile(source,temporary);temporary.chmod(0o600)
     if sha(temporary)!=item['sha256']:raise RuntimeError('ASSET_READBACK')
     with temporary.open('rb')as stream:os.fsync(stream.fileno())
     temporary.replace(output)
    finally:temporary.unlink(missing_ok=True)
   elif sha(output)!=item['sha256']:raise RuntimeError('IMMUTABLE_ASSET_CORRUPT')
   index[name]=item
  pinned=published/(vector['apkSha256']+'.apk')
  if pinned.exists()and sha(pinned)!=vector['apkSha256']:raise RuntimeError('PINNED_APK_CORRUPT')
  if not pinned.exists():
   temporary=published/(pinned.name+'.'+uuid.uuid4().hex+'.tmp')
   try:
    shutil.copyfile(staging/'pli-pleos.apk',temporary);temporary.chmod(0o600)
    if sha(temporary)!=vector['apkSha256']:raise RuntimeError('PINNED_APK_CORRUPT')
    temporary.replace(pinned)
   finally:temporary.unlink(missing_ok=True)
  prepared_index=staging/'commit-index.json';prepared_vector=staging/'commit-vector.json'
  atomic_json(prepared_index,index);atomic_json(prepared_vector,vector)
  outputs=[(Path(target),Path(archive)),(index_path,prepared_index),(Path(destination),prepared_vector)]
  backups={};committed=[]
  for position,(path,_)in enumerate(outputs):
   if path.exists():
    backup=staging/('rollback-'+str(position));os.link(path,backup);backups[path]=backup
  try:
   for path,pending in outputs:
    pending.replace(path);committed.append(path)
  except BaseException:
   for path in reversed(committed):
    if path in backups:backups[path].replace(path)
    else:path.unlink(missing_ok=True)
   raise

def publish_portal():
 """Publish product-facing assets without building, booting or certifying the APK."""
 vector=ROOT/'artifacts/review-delivery.json'
 with (ROOT/'.tools/publication.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  current=json.loads(vector.read_text());assets={k:v for k,v in current.get('assets',{}).items()if k in PUBLIC_KINDS and public_asset(v.get('filename',''))}
  names={'web-index':'index.html','web-js':'app.js','web-css':'style.css','web-worklet':'audio-worklet.js','web-font':'font.woff2','web-poster':'poster.svg','web-pleos':'pleos-preview.jpg','video':'preview.mp4','subtitles':'preview.vtt','transcript':'preview-transcript.txt','preview-manifest':'preview-info.json'}
  snapshot={kind:sha(ROOT/'demo-v2'/name)for kind,name in names.items()if(ROOT/'demo-v2'/name).is_file()}
  for kind,digest in snapshot.items():
   item=publish_file(ROOT/'demo-v2'/names[kind],kind)
   if item['sha256']!=digest:raise RuntimeError('PORTAL_INPUT_CHANGED')
   assets[kind]=item
  if any(sha(ROOT/'demo-v2'/names[kind])!=digest for kind,digest in snapshot.items()):raise RuntimeError('PORTAL_INPUT_CHANGED')
  current.update(assets=assets,webVector={str((ROOT/'demo-v2'/name).relative_to(ROOT)):snapshot[kind]for kind,name in names.items()if kind.startswith('web-')and kind in snapshot},acceptanceComplete=False,deliveryVerified=False)
  atomic_json(vector,current)
  return {'published':sorted(assets),'deviceAccess':False,'apkRebuilt':False}
