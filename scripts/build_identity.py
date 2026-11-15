"""Native build inputs shared by builder, execution records and delivery packaging."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def native_sources():
 paths=[p for p in (ROOT/'android/app/src/main').rglob('*')if p.is_file()]
 paths += [p for p in (ROOT/'android').glob('*')if p.suffix in {'.kts','.properties'}and p.name!='local.properties']
 paths += [p for p in (ROOT/'android/gradle').rglob('*') if p.is_file()]
 paths += [ROOT/'android/app/build.gradle.kts',ROOT/'android/app/proguard-rules.pro']
 return {str(p.relative_to(ROOT)):sha(p)for p in sorted(set(paths))if p.is_file()}
def valid_build(apk,apk_digest=None):
 try:
  b=json.loads((ROOT/'artifacts/build-info.json').read_text());return b.get('apkSha256')==(apk_digest if apk_digest is not None else sha(apk))and b.get('nativeSources')==native_sources()
 except (OSError,ValueError):return False
