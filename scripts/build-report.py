#!/usr/bin/env python3
"""Render current, bound evidence. Legacy/missing/failed checks never count as PASS."""
from pathlib import Path
from html import escape
import datetime,hashlib,json,re,sys,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'qa/native'),str(ROOT/'scripts')]
from run_record import source_snapshot,runtime_sources,compatible_tool
from contracts import declared_contract,contract_digest

def read(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return {}
_CONTEXT=None
class EvaluationContext:
 def __init__(self):
  self.digests={};self.digestReads={};self.versions={};self._build_valid=None;self.source=source_snapshot();self.latest=latest_runs()
 def file_version(self,path):
  stat=path.stat();return(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
 def digest(self,path):
  path=Path(path)
  if path in self.digests and self.versions[path]!=self.file_version(path):raise RuntimeError('EVALUATION_INPUT_CHANGED: '+str(path))
  if path not in self.digests:
   before=self.file_version(path);value=hashlib.sha256(path.read_bytes()).hexdigest()
   if before!=self.file_version(path):raise RuntimeError('EVALUATION_INPUT_CHANGED: '+str(path))
   self.digests[path]=value;self.versions[path]=before;self.digestReads[str(path)]=self.digestReads.get(str(path),0)+1
  return self.digests[path]
 def refresh(self):
  source=source_snapshot()
  if {p:v for p,v in self.source.items()if p.startswith('android/')}!={p:v for p,v in source.items()if p.startswith('android/')} :self._build_valid=None
  for path in list(self.digests):
   if not path.is_file()or self.versions[path]!=self.file_version(path):
    del self.digests[path];self.versions.pop(path,None);self._build_valid=None
  self.source=source;self.latest=latest_runs()
 @property
 def apk(self):return self.digest(ROOT/'artifacts/pli-pleos.apk')
 @property
 def build_valid(self):
  if self._build_valid is None:
   from build_identity import valid_build
   self._build_valid=valid_build(ROOT/'artifacts/pli-pleos.apk',apk_digest=self.apk)
  return self._build_valid
 def evaluate(self,result,manifest):
  global _CONTEXT
  previous=_CONTEXT;_CONTEXT=self
  try:
   issues=[];folder=ROOT/'qa/native/runs'/str(manifest.get('runId',''))
   for leaf,expected in [('manifest.json',manifest),('result.json',result)]:
    path=folder/leaf
    if path.is_file():
     before=self.file_version(path);raw=path.read_bytes();checksum=hashlib.sha256(raw).hexdigest()
     if before!=self.file_version(path)or path in self.digests and self.digests[path]!=checksum:raise RuntimeError('EVALUATION_INPUT_CHANGED: '+str(path))
     if json.loads(raw)!=expected:issues.append('실행 원문 변경')
     if path not in self.digests:self.digestReads[str(path)]=self.digestReads.get(str(path),0)+1
     self.digests[path]=checksum;self.versions[path]=before
   return issues+evaluate(result,manifest,self.apk if manifest.get('nativeRequired',True)or Path(manifest.get('script','')).name=='capture-preview.py'else None,self.source)
  finally:_CONTEXT=previous
 def assert_latest_unchanged(self,scripts):
  def selected(entries):return {key:(stamp,value.get('runId'))for key,(stamp,path,value)in entries.items()if Path(value.get('script','')).stem in scripts}
  if selected(self.latest)!=selected(latest_runs()):raise RuntimeError('EVALUATION_LATEST_CHANGED')
 def assert_inputs_unchanged(self):
  for path,expected in self.digests.items():
   if not path.is_file()or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('EVALUATION_INPUT_CHANGED: '+str(path.relative_to(ROOT)))
def digest(p):
 p=Path(p)
 return _CONTEXT.digest(p)if _CONTEXT else hashlib.sha256(p.read_bytes()).hexdigest()
def run_key(manifest):
 name=manifest.get('script','');arguments=list(manifest.get('arguments',[]));scope=manifest.get('scope','full')
 if '--scope'in arguments:
  index=arguments.index('--scope')
  if index+1<len(arguments):scope=arguments[index+1];del arguments[index:index+2]
 if '--cleanup-only'in arguments:scope='cleanup';arguments.remove('--cleanup-only')
 if '--class'in arguments or '--resources-only'in arguments:scope='focused'
 expected=['--seoul-gps']if Path(name).name=='private-navigation.py'else[]
 try:default_profile=declared_contract(ROOT/name)['profile']
 except (OSError,ValueError,SyntaxError):
  from run_record import PUBLIC_OWNERS
  default_profile='public'if Path(name).name in PUBLIC_OWNERS else'personal'
 profile=manifest.get('profile',default_profile)
 return name if scope=='full'and arguments==expected and profile==default_profile else name+' [scope='+str(scope)+' · profile='+str(profile)+' · '+json.dumps(arguments,ensure_ascii=False)+']'
def latest_runs():
 latest={}
 for path in (ROOT/'qa/native/runs').glob('*/manifest.json'):
  manifest=read(path);name=manifest.get('script');stamp=manifest.get('startedAt','')
  if not name or Path(name).name.startswith('_'):continue
  key=run_key(manifest)
  if key not in latest or stamp>latest[key][0]:latest[key]=(stamp,path,manifest)
 return latest
def html_text(value):
 return ''.join('<a href="'+escape(part,quote=True)+'">'+escape(part)+'</a>'if part.startswith(('https://','http://'))else escape(part)for part in re.split(r'(https?://[^\s]+)',value))
def source_matches(manifest,source):
 if manifest.get('recordVersion')==3:
  try:
   contract=declared_contract(ROOT/manifest['script'],manifest.get('arguments',[]))
   return contract==manifest.get('executionContract')and contract_digest(contract)==manifest.get('contractSha256')and all((ROOT/name).is_file()and digest(ROOT/name)==value for name,value in manifest.get('source',{}).items())and set(manifest.get('source',{}))==set(contract['inputs'])
  except (OSError,ValueError,KeyError):return False
 # Historical evidence may be reported as historical. Source changes are never
 # waived by an ad-hoc pair of hashes in the current reader.
 return runtime_sources(manifest.get('source',{}),manifest.get('script'))==runtime_sources(source,manifest.get('script'))

def evaluate(result,manifest,apk,source,claim_checks=None):
 reasons=[]
 if any(not(ROOT/name).is_file()or digest(ROOT/name)!=expected for name,expected in result.get('metrics',{}).get('screenshots',{}).items()):reasons.append('화면 근거 불일치')
 if not compatible_tool(manifest,result):reasons.append('검증 기록 도구 불일치')
 if manifest.get("buildInputsMatch") is not True or result.get("buildInputsMatch") is not True:reasons.append("빌드 입력 근거 불일치")
 if result.get('runId')!=manifest.get('runId'):reasons.append('실행 ID 불일치')
 if result.get('status')!='PASSED' or result.get('passed') is not True:reasons.append('실패·미완료')
 if manifest.get('nativeRequired',True) and (manifest.get('apkSha256')!=apk or manifest.get('installed',{}).get('sha256')!=apk or result.get('installedMatchesArtifact') is not True):reasons.append('APK 근거 불일치')
 if manifest.get('recordVersion')==3 and manifest.get('nativeRequired'):
  context=_CONTEXT or EvaluationContext()
  if not context.build_valid:reasons.append('현재 네이티브 빌드 입력 불일치')
 if manifest.get('script') and(not(ROOT/manifest['script']).is_file()or digest(ROOT/manifest['script'])!=manifest.get('scriptSha256')):reasons.append('시험 스크립트 불일치')
 if any(not(ROOT/name).is_file()or digest(ROOT/name)!=expected for name,expected in manifest.get('dependencies',{}).items()):reasons.append('검증 도구 소스 불일치')
 if any(not(ROOT/'qa/native/fixtures'/name).is_file()or digest(ROOT/'qa/native/fixtures'/name)!=expected for name,expected in manifest.get('fixtures',{}).items()):reasons.append('입력 음원 근거 불일치')
 if not source_matches(manifest,source) or result.get('sourceChanged') is not False:reasons.append('소스 불일치')
 if Path(manifest.get('script','')).name=='capture-preview.py'and manifest.get('scope','full')!='record'and(not(ROOT/result.get('metrics',{}).get('videoPath','artifacts/native-preview/preview.mp4')).is_file()or result.get('metrics',{}).get('videoSha256')!=digest(ROOT/result.get('metrics',{}).get('videoPath','artifacts/native-preview/preview.mp4'))or result.get('metrics',{}).get('apkSha256')!=apk):reasons.append('시연 영상 근거 불일치')
 if Path(manifest.get('script','')).name=='native-instrumentation.py'and manifest.get('scope','full')=='full'and(result.get('metrics',{}).get('testCount',0)<31 or result.get('metrics',{}).get('activityRecreationIncluded')is not True):reasons.append('기기 전체 31개·재생성 검사 미실행')
 checks=result.get('checks',{})
 if manifest.get('recordVersion')==3:
  contract=manifest.get('executionContract',{});expected=claim_checks if claim_checks is not None else contract.get('expectedChecks',[])
  if not expected or set(checks)!=set(expected):reasons.append('선택 범위의 누락·미선언 조건')
  effect=contract.get('effects')in {'mutate','runtime'}
  if manifest.get('effects')is not effect or effect and result.get('cleanupStatus')!='CONFIRMED':reasons.append('효과·실제 정리 계약 불일치')
  obligations=manifest.get('cleanupObligations',[])
  if any(result.get('metrics',{}).get('cleanupObligations',{}).get(key)is not True for key in obligations):reasons.append('필수 정리 근거 미확인')
 if not checks or any(v!='PASS' for v in checks.values()):reasons.append('미통과 항목')
 return reasons

def evaluate_claim(result,manifest,claim,apk,source):
 keys=manifest.get('plannedClaims',{}).get(claim)
 proof=result.get('claims',{}).get(claim,{})
 if manifest.get('recordVersion')not in {2,3} or not keys or proof.get('checks')!=keys or proof.get('status')!='PASSED'or proof.get('cleanupStatus')!='CONFIRMED':return ['독립 주장 계약·정리 근거 불일치']
 if result.get('error')in {'CANCELLED','PRECONDITION_FAILED','PRECONDITION_CHANGED','PRECONDITION_PAUSED','CLEANUP_UNCONFIRMED'}:return ['취소·선행조건 실패']
 narrowed={**result,'status':'PASSED','passed':True,'error':None,'checks':{key:result.get('checks',{}).get(key,'NOT_RUN')for key in keys}}
 return evaluate(narrowed,manifest,apk,source,claim_checks=keys)

def claim_notes():
 context=_CONTEXT or EvaluationContext();entries=[];source=context.source;apk=context.apk;latest={}
 for p in (ROOT/'qa/native/runs').glob('*/manifest.json'):
  m=read(p);name=m.get('script')
  if m.get('plannedClaims')and(name not in latest or m.get('startedAt','')>latest[name][0]):latest[name]=(m.get('startedAt',''),p,m)
 for name,(_,path,m)in latest.items():
  r=read(path.with_name('result.json'))
  for claim in m['plannedClaims']:
   if not evaluate_claim(r,m,claim,apk,source):entries.append('- 독립 검증 '+Path(name).name+' / '+claim+': 해당 사전 선언 조건·현재 APK·원본 복원·자원 종료 확인. 다른 주장의 완료로 합산하지 않음.')
 return entries

def current_runs():
 context=_CONTEXT or EvaluationContext();latest=context.latest;source=context.source;apk=context.apk
 rows=[]
 for name,(_,path,m)in sorted(latest.items()):
  r=read(path.with_name('result.json'))
  reasons=context.evaluate(r,m);cs=r.get('checks',{});valid=not reasons
  scoped_match=valid and runtime_sources(m.get('source',{}),m.get('script'))!=runtime_sources(source,m.get('script'))
  cleanup_only=m.get('arguments')==['--cleanup-only']and r.get('cleanupStatus')=='CONFIRMED'
  rows.append([Path(name).name,r.get('runId','—'),'정리 확인 · 전체 검사 제외'if cleanup_only else'통과'if valid else'미완료',str(sum(x=='PASS'for x in cs.values()))+'/'+str(len(cs)),'실제 자원 종료만 확인. 기본 전체 검사의 통과는 별도 행에서 판정'if cleanup_only else', '.join(reasons)if reasons else'선택 소스·입력·조건 일치 · 설치 검증 제외'if not m.get('nativeRequired',True)else'검토한 변경과 독립적인 검사 · 설치 APK 일치'if scoped_match else'현재 소스·설치 APK 일치'])
 return rows

def verdict_summary(rows):
 """Body of '최신 실행 판정': what is currently valid, without promoting stale runs."""
 passed=[row for row in rows if row[2]=='통과'];other=[row for row in rows if row[2]!='통과']
 names=', '.join(row[0] for row in passed)
 return [f'- 현재 유효 실행: {len(passed)}/{len(rows)}. 통과: {names or "없음"}.',
         f'- 미완료 {len(other)}개: 실패·중단 원본이거나 소스·검사 도구 변경 뒤 재확인 전. 사유는 아래 실행별 근거.',
         '- 자동 실행 통과는 사람·실차·실제 내비 안내 인수와 별개.']

def bound_measurements(script):
 candidates=[]
 for path in (ROOT/'qa/native/runs').glob('*/manifest.json'):
  manifest=read(path)
  if Path(manifest.get('script','')).name==script and run_key(manifest)==manifest.get('script'):candidates.append((manifest.get('startedAt',''),path,manifest))
 if not candidates:return None
 _,path,manifest=max(candidates,key=lambda item:item[0]);result=read(path.with_name('result.json'))
 context=_CONTEXT or EvaluationContext();reasons=context.evaluate(result,manifest)
 # A failed performance target does not invalidate an honestly measured sample.
 # Source/APK/input mismatches still exclude it from current measurements.
 if any(reason not in {'실패·미완료','미통과 항목'}for reason in reasons)or result.get('status')=='RUNNING':return None
 return {'status':result.get('status'),'metrics':result.get('metrics',{}),'checks':result.get('checks',{})}

def performance_notes():
 lines=[];voice=bound_measurements('voice-performance.py');cold=bound_measurements('cold-start.py')
 page=bound_measurements('portal-performance.py')
 if page:
  for item in page['metrics'].get('surfaces',[]):
   lines.append(f"- 실제 {item['surface']} 화면: warm 첫 프레임 P95 {item['firstFrameP95Seconds']}초 · 고유 source 표시 {item['uniqueSourceFps']}fps · 전체 표시 {item['depictedFps']}fps · 마지막 main draw {item['latestMainDrawMicros']}μs. {item['condition']}.")
   if 'captureToPaintP50Ms'in item:lines.append(f"- {item['surface']} 캡처→표시: 같은 호스트의 시간 기준 P50 {item['captureToPaintP50Ms']}ms · P95 {item['captureToPaintP95Ms']}ms. 외부 기기 clock 측정으로 확대하지 않음.")
  for item in page['metrics'].get('inputEffect',[]):
   lines.append(f"- OS 앱 목록/앱 열기 {item['condition']}: 실제 click→화면 RGB 변화 P95 {item['p95Ms']}ms · 표본 {len(item['samples'])}회. 기준 {350 if item['condition']=='LAN'else 600}ms의 판정 {page['checks'].get(item['condition']+'InputEffectWithinTarget','NOT_RUN')}. 응답 ACK로 대체하지 않음.")
  touch=page['metrics'].get('kernelTouch',{})
  if touch:lines.append(f"- 포인터: {touch.get('condition','5개 기준점')} · guest 실제 입력 장치 관측 오차 최대 {touch.get('maxErrorNativePixels')} native px · UP 수신 {touch.get('lastTrackingReleased')}. 실제 회전 시험 전체를 뜻하지 않음.")
 if page and 'runtimeReadySeconds'in page['metrics']:
  m=page['metrics'];lines.append(f"- 첫 화면: 새 Chrome·80ms 지연·5Mbps 수신/1Mbps 송신에서 DOM 표시 {m['domContentLoadedSeconds']}초·실제 APK 화면 준비 {m['runtimeReadySeconds']}초. 기기 재부팅·음성 준비 시간은 제외한 페이지 측정.")
 journey=bound_measurements('portal-journey.py')
 if journey:
  m=journey['metrics']
  if 'warmRecognizerReadySeconds'in m:lines.append(f"- 기기가 켜진 상태의 음성 준비: 실제 세션 요청부터 캡처·인식기 준비 관측까지 {m['warmRecognizerReadySeconds']}초. 5초 목표 {journey['checks'].get('warmRecognizerWithin5Seconds','NOT_RUN')}. 마이크 허용·브라우저 사전 준비와 첫 인사 완료는 별도 구간.")
  if 'buttonToRecognizerReadySeconds'in m:lines.append(f"- 버튼부터 인식기 준비까지 전체 대기 {m['buttonToRecognizerReadySeconds']}초. 이 중 마이크·브라우저 사전 준비 {m['permissionAndBrowserSetupSeconds']}초. 사람이 권한을 결정하는 시간의 상한은 보증하지 않음.")
  if 'hushToStoppedSeconds'in m:lines.append(f"- 말하는 중 음성 중단: 실제 PLAYING 상태에서 쉿 입력을 시작한 뒤 재생 IDLE 확인까지 {m['hushToStoppedSeconds']}초. 입력을 답안으로 채점하지 않는 조건 별도 통과 여부는 portal-journey 실행 참조.")
  if 'endToNativeStoppedSeconds'in m:lines.append(f"- 정상 종료: 종료 버튼부터 실제 기기 정리·조작권 반환 관측까지 {m['endToNativeStoppedSeconds']}초. 5초 목표 {journey['checks'].get('nativeStopWithin5Seconds','NOT_RUN')}. 브라우저 트랙 선행 정리는 별도 검사.")
 if voice:
  for item in voice['metrics'].get('profiles',[]):
   if item.get('warmQuestionReadySeconds'):lines.append(f"- {item['route']} 질문 가능 대기: {item['warmQuestionReadySeconds']}초. 짧은 준비 알림 완료·실제 LISTENING까지 측정, 7초 조건 {voice['checks'].get('allSixWarmStartsReadyWithin7Seconds','NOT_RUN')}.")
   if item.get('interruptSamples'):lines.append(f"- {item['route']} 실제 조용히 중단: partial→재생 정지 {[s['partialToConfirmedStopMs']for s in item['interruptSamples']]}ms, 문구 시작→정지 {[s['inputStartToStopSeconds']for s in item['interruptSamples']]}초. 500ms 조건 {voice['checks'].get('receivedHushPartialsStopWithin500ms','NOT_RUN')}. 문구 전체 인식 지연과 구분.")
   if item.get('commandProfile'):lines.append(f"- 음성 {item['route']} 입력 문구: {item['commandProfile']}. 안내 문구 변경 전 프로필의 오인식은 IMPLEMENTATION.md에 별도 보존.")
   if 'p95Ms'in item:lines.append(f"- 음성 {item['route']}: 숫자/영어 놀이 교대·온디바이스 SDK·계획 {item['totalPlanned']}회·실행 {item.get('attempted',item.get('completed',0))}회·실패 {item['failures']}회·미실행 {item.get('unattempted',0)}회·P50 {item['p50Ms']}ms·P95 {item['p95Ms']}ms·최대 {item['maxMs']}ms. 3초 인수조건 {voice['checks'].get(item['route']+'P95Within3Seconds','NOT_RUN')}. 브라우저 송신의 마지막 유음부터 수신 첫 유음까지 측정.")
   else:lines.append(f"- 음성 {item['route']}: 계획 30회 중 {len(item.get('samples',[]))}회 기록 후 실행 {voice['status']}. 완료 분포로 사용하지 않음.")
 else:lines.append('- 음성 성능: 현재 APK의 로컬·외부 각 30회 기준 통과 근거 미확보. 아래 실행 판정 참조.')
 if cold:
  for item in cold['metrics'].get('samples',[]):
   if 'guestRebootToListeningSeconds'in item:lines.append(f"- 실제 게스트 재부팅 {item['iteration']}: 부팅 {item['bootSeconds']}초·앱 화면 {item['appViewSeconds']}초·음성 엔진 및 첫 인사 {item['engineAndGreetingSeconds']}초. 재부팅부터 듣기까지 {item['guestRebootToListeningSeconds']}초.")
   else:lines.append(f"- 실제 게스트 재부팅 {item['iteration']}: {item.get('failedStage','알 수 없는 단계')} 단계 실패·{item.get('failure','미완료')}. 성공 표본으로 합산하지 않음.")
   cleanup=item.get('cleanup',{})
   if cleanup:lines.append(f"- 재부팅 {item['iteration']} 뒤 종료: {'자원 정리 확인'if cleanup.get('success')else'정리 미확인'}·{cleanup.get('seconds','—')}초·정리 중 추가 게스트 재부팅 {cleanup.get('additionalGuestReboots','미확인')}회.")
  lines.append('- 재부팅 조건: 이 컴퓨터의 Pleos AVD 게스트 실제 재부팅. 호스트 VM 프로세스·디스크의 모델 캐시는 유지. 전원을 완전히 끈 실차의 결과와 구분.')
 else:lines.append('- 재부팅 성능: 현재 APK의 실제 게스트 재부팅 3회 통과 근거 미확보. 아래 실행 판정 참조.')
 parent=bound_measurements('parent-private.py')
 if parent and parent['status']=='PASSED':
  if parent['metrics'].get('menuRecognitionAttempts'):lines.append(f"- 개인 식단 질문 인식: 실제 발화 {len(parent['metrics']['menuRecognitionAttempts'])}회 · 실패 {sum(not x['success']for x in parent['metrics']['menuRecognitionAttempts'])}회. 재질문 뒤 실제 재발화 포함.")
  lines.append(f"- 개인용 키즈노트 새 조회: 합성 발화 재생 시작부터 실제 답변 PLAYING까지 {parent['metrics']['voiceToAnswerSeconds']}초. 외부 자료 조회를 포함하며, 놀이 명령의 3초 측정과 경계가 다름.")
 experience=bound_measurements('experience-voice.py')
 if experience and experience['status']=='PASSED':
  utterances=experience['metrics'].get('utterances',[]);retries=experience['metrics'].get('recognitionRecoveries',[])
  lines.append(f"- 전체 기능 음성: 실제 발화 {len(utterances)}회·재질문 뒤 추가 발화 {len(retries)}회. 과업 완료와 첫 발화의 인식 성공을 구분. 실패한 시도와 인식문도 실행 원본에 보존.")
 return lines

def remediation_notes(rows):
 status={row[0]:row[2]for row in rows}
 items=[
 ('N01','전체 Pleos display 0 전송·앱 View 분리','display_stream.py / demo-server.py','portal-performance.py','NVIDIA PRIME 선택 후 실제 차량 3D 표시 복구, 장기 운행 검증 별도'),
 ('N02','마이크와 OS 조작권 분리·공개 기기 고정','runtime_context.py / input / lease','portal-edge.py','기기·PID·userdata·오디오 분리'),
 ('N03','앱·Pleos·자료의 별도 진입과 첫 화면 배치','demo-v2 routes / CSS','portal-layout.py','실제 초회 사용자 과업 인수 별도'),
 ('N04','위계·타이포그래피·캐릭터·모션·실제 표시 크기','demo-v2 / PliScreen / ExperiencePanels','portal-layout.py','미학 만족도는 실제 사람 검증 대기'),
 ('N05','앱 픽셀을 전체 OS로 인정하던 검사 교정','journey / performance / public-access','public-access.py','실제 화면·입력 효과·파일 바이트를 검사'),
 ('N06','무관한 변경으로 빌드·검사를 반복하던 범위 축소','build_identity / run_record / runner','fast-unit.py','같은 소스·입력·설치 근거만 재사용'),
 ('N07','성공·실패·미완료·가설의 보고 경계 분리','run_record / build-report','evidence-contract.py','과거 실패·미실행·외부 장애 보존'),
 ('N08','APK·설치·웹·영상·보고·소스의 전달 계보','package-source / delivery_assets','publication-contract.py','두 기기 설치·보고서 SHA 검증, 미인수는 review'),
 ('N09','주행·정차·충전·부모 질문의 다음 행동 안내','presets / Controller / UI','experience-voice.py','시작 P/0·신호 확인·미지원 실제 구분'),
 ('N10','녹화 재생·종료·실시간 복귀의 수명 분리','app.js / preview-info','portal-edge.py','녹화 중 live 구독 종료·자막·대본 제공'),
 ('N11','8fps·메인 압축·프레임별 DOM 재작성 제거','Provider / encoder / MSE','portal-performance.py','표시율·첫 프레임·입력 효과를 별도 실측'),
 ('N12','메타데이터 준비를 LIVE로 보이던 판정 교정','frame stamp / health / input guard','portal-edge.py','실제 표시 없거나 상태 조회 실패 시 입력 차단'),
 ('N13','제품 소개·APK만 공개하고 내부 보고·소스 차단','immutable allowlist / resources','public-access.py','메뉴·별칭·과거 hash URL까지 차단'),
 ('N14','부정·정정·제외·일정 시각 질문을 우선 해석','VoiceInterpreter / Controller','native-instrumentation.py','partial Hush 복원·정답·호출어 회귀 보존'),
 ('N15','일·주 새 조회의 기간·refresh를 실제 MCP까지 전달','bridge / snapshot / Store / speech','parent-private.py','월~일 범위 원격 receipt·저장 revision·음성 확인'),
 ('N16','일부 응답과 확인된 자료 없음 구분','site / coverage / DataContract','mcp-contract.py','3페이지·다른 아이 뒤 결과·반복 cursor·삭제 방지'),
 ('N17','과거 과업·TTS callback이 새 과업을 덮는 경합 차단','intentRevision / TTS generation / stop ACK','native-instrumentation.py','실제 owner callback 경쟁 주입·음성 수명 확인'),
 ('N18','영어 역할 전환·검수 단어·3턴 대화·이야기 후속','LearningCatalog / Questions / Controller','experience-voice.py','지원 범위 밖 질문은 실제 미지원 안내'),
 ('N19','긴 본문과 12개 후보의 저장·읽기 문맥 연결','FamilyDocuments / ReadingContext / listContext','native-instrumentation.py','전체 본문·Unicode·백업·scope·목록 페이지 유지'),
 ('N20','글꼴 차단 0회의 허위 성공 근거 교정','portal-layout route / load receipt','portal-layout.py','실제 주입 hit와 실패 상태 확인 뒤 fallback 검사'),
 ('N21','자막·대본·호환 화면·권한 거절·소리 재개','capability / media state / fallback','portal-edge.py','Chrome 자동 검증, Safari·실기기 완주는 미검증')]
 lines=['','## 최신 감사 N01~N21 대응','']
 for ident,change,owner,script,limit in items:
  verdict=status.get(script,'미완료');lines.append(f'- {ident}: {change}. 변경 소유자 {owner}. 연계 검사 {script}: {verdict}. {limit}.')
 lines+=['','- F01~F09·D1~D14의 기존 종료·자료 보존·공개 격리 계약은 승계. 자세한 항목별 원인·변경·실행은 IMPLEMENTATION.md, 현재 인수 표는 ACCEPTANCE.md 참조.','- 위 연계 검사 통과는 해당 검사 범위의 근거. N01의 장기 차량 렌더링·N04 미학·N09/T19 사람 과업·실차·실제 내비 안내의 완료로 확대하지 않음.']
 return lines

def refresh_acceptance(rows):
 path=ROOT/'docs/ACCEPTANCE.md'
 if not path.exists():return
 text=path.read_text();head=text.split('## 최신 감사 N01~N21 대응',1)[0];status={row[0]:row for row in rows};updated=[]
 for line in head.splitlines():
  cells=line.split('|')
  if len(cells)==6:
   names=re.findall(r'([\w-]+\.py)',cells[3]);row=status.get(names[-1])if names else None
   if row:cells[4]=f' {row[2]} · {row[1]} · {row[3]} · {row[4]} ';line='|'.join(cells)
  updated.append(line)
 footer=text.split('## 외부 조건과 확인 한계',1)[-1]
 if footer==text:footer='\n- 사람·실차·실제 내비 안내 인수는 별도.\n'
 current='\n'.join(updated).rstrip()+'\n'+'\n'.join(remediation_notes(rows))+'\n\n## 성능 실측\n\n'+'\n'.join(performance_notes()+claim_notes())+'\n\n## 외부 조건과 확인 한계'+footer
 current=current.replace('기준: REMEDIATION-DESIGN-2026-11-11.md ·','기준: REMEDIATION-DESIGN-2026-11-11-DELAY.md · REMEDIATION-DESIGN-2026-11-11.md ·')
 path.write_text(current)

def main():
 global _CONTEXT
 _CONTEXT=EvaluationContext()
 rows=current_runs();refresh_acceptance(rows);apk=ROOT/'artifacts/pli-pleos.apk';public=read(ROOT/'.tools/public-config.json').get('url','현재 주소 확인 필요');date=datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')
 raw=subprocess.check_output([str(ROOT/'.tools/android-sdk/build-tools/35.0.0/aapt2'),'dump','badging',str(apk)],timeout=15).decode()
 version=re.search(r"versionName='([^']+)'",raw).group(1)
 lines=['# 플리 구현·검증 보고서' ,'',f'- 생성: {date}',f'- 버전: APK {version} · 개발용 서명 · release 빌드','- 종합 판정: 검토용 후보. 첫 질문 준비·OS 입력 반응의 성능 조건, 실제 내비 안내·사람/실차 인수는 별도로 판정.','- 제품: 아이의 음성 놀이 + 부모의 등원 준비·키즈노트 소식 확인','- 개발: 현재 프로젝트 폴더의 Pleos 환경 · 에이전트 미사용','', '## 주요 변경','', '- 화면 분리: /app은 실제 앱 View, /pleos는 실제 Pleos display 0. 별도 공개 AVD를 사용하며 마이크 없이 터치·키·차량 조건 조작 가능.', '- 성능 원인 수정: 프레임마다 전체 DOM을 다시 쓰던 경로 제거. 동일 6초 조건 DOM 변경 7,906→252회, 96.8% 감소. 전체 서비스 속도 개선율로 확대하지 않음.', '- 부모 질문: 오늘·내일 일정·준비물, 이번 주·다음 주 일정, 식단·알림장·공지·놀이계획·앨범 소식','- 응답: 공개 샘플·실제 조회·저장 자료·오래된 캐시·자료 없음·조회 실패 구분','- 화면: 실제 Pleos APK 화면 유지. 부모 질문에서 출처를 표시하는 브리핑 화면으로 전환','- 음성: 앱에서 마이크 입력을 관리하고 음성·차량 작업을 별도 프로세스로 분리. SDK 응답을 기다릴 때 화면이 멈추던 경로 제거.','- 종료: 기기에서 마이크·재생·포커스 해제를 확인한 뒤 다음 체험 허용. 연결 확인·세션 만료·재시작 기록으로 비정상 중단 후 복구.','- 저장: 원자적 쓰기·재읽기·용량 사전 검사·범위별 병합·입력과 실제 반영 건수 분리','- 보고: 실행별 기록·소스/설치 APK 연결. 미실행·실패·예전 결과의 성공 합산 차단','- 원본 기능: 실제 수식의 주판 애니메이션·아이 출제 영어·충전 놀이·성장 앨범','- 목적지: 보호자 등록 후보 → 아이의 음성 선택 → 보호자 확인 → 실제 내비 요청·결과 확인. 공개 체험은 샘플로 제한','', '## 최신 실행 판정','']
 heading=lines.index('## 최신 실행 판정')+2;lines[heading:heading]=verdict_summary(rows)
 lines+=['','## 연구·검증 방식 수정 · V01~V14','',
 '- 실행: 기본 호출은 계획만 출력. 필요한 owner와 scope를 선택하며 전체 실행은 --full로 명시.',
 '- 입력: 각 owner가 사용한 파일·음원·조건을 선언. 문서/세션 만료 검사에 무관한 음원56개를 결합하던 기본값 제거.',
 '- 자원: 오프라인/읽기/변경을 구분. 종료 시간 초과와 실제 마이크·자료 보존 실패를 별도 판정.',
 '- 재발 방지: 사용자 중지·재시작 generation이 바뀌면 이전 QA의 subprocess/HTTP 변경/다른 프로세스 kill 차단. 다른 실행의 PASS를 가져오는 경합 차단.',
 '- 범위: 음성 준비/응답/중단, 화면 표시/입력/포인터, 원본 녹화/인코딩을 별도 선택. 과거 실패를 새 범위의 통과로 소급하지 않음.',
 '- 평가·패키지: 평가 context당 APK digest1회. 고정 snapshot의 ZIP bytes를 재확인하고 소스 변경 시 기존 전달본 유지. 기본 패키징은 AVD 접근 없음.',
 '- 공개 범위: 제품 소개·APK·영상만 제공. 내부 보고·설계·감사·소스 ZIP은 메뉴·별칭·과거 hash URL 모두 차단.',
 '- 영상 공개: '+('제품 소개 영상 제공 중. 실제 앱/SDK 검증과 분리.'if read(ROOT/'artifacts/review-delivery.json').get('assets',{}).get('video')else'이전 컷신 철회. 실제 움직이는 동영상 원본을 준비 중이며 현재 공개 영상 없음.'),
 '- 상세 근거와 한계: IMPLEMENTATION.md. 자동 선택 범위·전체 제품 요구·외부 전달 확인을 각각 판정.','', '## 실행별 근거','']
 lines += [f'- {row[0]}: {row[2]} · 개별 조건 {row[3]} · 실행 {row[1]} · {row[4]}.' for row in rows]
 lines+=remediation_notes(rows)
 lines+=['','## 지연 감사 DLY01~DLY12 구현','',
 '- DLY01·08: 후보와 빌드 입력 고정, 검사별 입력 범위·검증된 과거 producer 보관 적용. 임의 hash 쌍 예외 제거. 무관한 웹/보고 변경으로 APK 재빌드하지 않음.',
 '- DLY02·09: 원 한국어 발화·실제 ASR·의도·채점을 분리. 정당한 good by를 정규화하고 무관한 오인식 단어는 명령이나 정답으로 등록하지 않음.',
 '- DLY03: 실제 원 후보 12개 발화·12번 선택·원본 복원과 실제 내비 안내 주장을 분리. 안내/취소 성공은 미확보.',
 '- DLY04: 실행 runId별 진단 저장. 오래된 timeout 진단을 다음 실행의 원인으로 재사용하지 않음.',
 '- DLY05: 호스트 부하·공개 서비스·각 AVD의 공통 자원 잠금 적용. 직접 실행에도 같은 잠금 적용.',
 '- DLY06: AST와 의존 파일 확인 후 작업 시작. 실패는 새 실행 기록으로 남기고 이전 PASS로 대체하지 않음.',
 '- DLY07: 부모 질문의 재질문·조회 실패·의도 불일치·종료를 실제 대기 종료 상태로 소비. 이미 실패한 뒤 성공 timeout을 추가로 기다리지 않음.',
 '- DLY10: 브라우저/기기 준비 병행, 현재 음성의 상태 전달, 중복 상태 RPC 공유, 초기 구간의 빠른 관측, 진행 중 END의 중복 정리 차단. 실제 지연·미달 조건은 아래 측정값으로 판정.',
 '- DLY11: review 채널의 고정 제품 자산과 외부 바이트 확인서 적용. 보고·소스 ZIP은 내부 snapshot으로 보존. 다운로드 확인서를 PDF/ZIP 내부에 넣어 해시가 바뀌는 순환 제거.',
 '- DLY12: 취소 시 새 단계 금지, 실제 finally와 자원 해제 확인 뒤 최종 기록. 기기 내부 instrumentation 종료 미확인은 격리.',
 '- 기준: REMEDIATION-DESIGN-2026-11-11-DELAY.md. 항목별 원인·소유자·반례·실행·잔여는 IMPLEMENTATION.md. 개별 구현과 전체 인수 완료를 구분.']
 for script,label in [('native-instrumentation.py','실제 기기 계측'),('fast-unit.py','JVM 단위')]:
  measurement=bound_measurements(script)
  if measurement and measurement['status']=='PASSED':lines += ['',f"- {label}: {measurement['metrics']['testCount']}개 통과. 위 실행표의 개별 조건 수와 구분."]
 lines+=['','- 개별 PASS가 있어도 실행이 미완료면 해당 범위의 완료 근거로 사용하지 않음.','- 원 요구별 현재 판정: ACCEPTANCE.md. 원인·수정 이력: IMPLEMENTATION.md. 기준 설계: REMEDIATION-DESIGN-2026-11-11.md. 변경 전 감사: UX-AUDIT-2026-11-11.md.','', '## 접속·사용','', '- 공개 주소: '+public,'- APK 내려받기: '+public+('/artifacts/pli-pleos-review.apk · 검토용·미인수'if '--review'in sys.argv else'/artifacts/pli-pleos.apk'),'- 시작: 앱 체험 또는 Pleos 시뮬레이터 선택. 앱은 마이크를 켜고 말하기, Pleos는 마이크 없이 직접 조작.', '- 앱 체험: '+public+'/app', '- Pleos 전체 화면: '+public+'/pleos', '- 제품 소개·APK·영상: '+public+'/resources','- 개인용 가족 연결: http://127.0.0.1:8876/family','- 가족 연결: 아이·기관 선택 → 갱신·반영 → 개인용 플리에서 대화 시작','- 공개 주소와 Tailscale에서는 개인 가족 자료·관리 화면 차단','- 키즈노트: 사용자 제공 MCP의 읽기 도구 활용. 공식 제휴 API를 뜻하지 않음. 외부 서비스 변경 시 재로그인·어댑터 수정 가능','', '## 남은 필수 확인·외부 장애','', '- 실제 내비게이션: 현재 후보의 12개 발화·선택·보호자 확인 전 요청 차단·원본 복원은 확인. 실제 안내/취소 callback은 미확보. 제공 지도 엔진의 401·Service Not Found 관측, 정상 인증/서비스 환경이 필요. 공개 샘플 성공과 구분.', '- Pleos 3D 화면: Radeon 610M에서 반복 충돌. 이 컴퓨터에 있던 RTX 4070을 PRIME으로 선택한 뒤 실제 DrivingView·차량 모델 표시 복구. 임의 웹 차량 그림을 사용하지 않음. 장기 안정성·실차 결과와 구분.', '- 사람 5명의 초회 과업·실차 소음·실차 SDK 및 iOS/Safari 완주 검증 근거 없음. 자동 Chrome·합성 발화를 사람 인수로 합산하지 않음.', '', '## 확인 범위','', '- 자동 시험: 합성 한국어 음성, Chrome, 실제 Pleos 에뮬레이터 마이크·온디바이스 SDK','- 네이티브 검사 수·재생성 포함 여부·실패 원인은 해당 실행의 manifest/result 기준', '- 실패 반례와 재실행 결과는 IMPLEMENTATION.md 및 실행별 기록에 보존', *performance_notes(), *claim_notes(), '- 미검증: 실제 부모·아이 5명의 초회 과업, 실차 소음·장기 운행·모든 모바일 브라우저','- 공개 Quick Tunnel: 재시작 시 주소 변경 가능. 이 컴퓨터·네트워크가 켜져 있어야 시연 가능','', '## 산출물','', '- APK: artifacts/pli-pleos.apk','- APK SHA-256: '+digest(apk),'- 원 소스 및 시험 입력: artifacts/'+('pli-pleos-review-source.zip'if '--review'in sys.argv else'pli-pleos-source.zip'),'- 전달 식별자: artifacts/'+('review-delivery.json · 검토용·미인수. 공개 검토 경로에서 현재 후보 제공, 이전 정식 파일 보존'if '--review'in sys.argv else'delivery.json'),'- 비공개 도구·계정 세션·원문·키 파일은 소스 패키지에서 제외','- 버전 번호만으로 동일 배포본을 판정하지 않음. APK 해시와 실행 manifest를 비교']
 text='\n'.join(lines)+'\n';(ROOT/'docs/implementation-report.md').write_text(text)
 body='';in_list=False;in_table=False
 for line in lines:
  if not line.startswith('- ') and in_list:body+='</ul>';in_list=False
  if not line.startswith('|') and in_table:body+='</table>';in_table=False
  if line.startswith('# '):body+='<h1>'+escape(line[2:])+'</h1>'
  elif line.startswith('## '):body+='<h2>'+escape(line[3:])+'</h2>'
  elif line.startswith('- '):
   if not in_list:body+='<ul>';in_list=True
   body+='<li>'+html_text(line[2:])+'</li>'
  elif line.startswith('|'):
   if set(line.replace('|','').strip())<={'-',':',' '}:continue
   if not in_table:body+='<table>';in_table=True
   body+='<tr>'+''.join('<td>'+escape(c.strip())+'</td>'for c in line.strip('|').split('|'))+'</tr>'
 if in_list:body+='</ul>'
 if in_table:body+='</table>' 
 css="@font-face{font-family:P;src:url('/font.woff2'),url('../android/app/src/main/res/font/pretendard.ttf')}body{font:10pt/1.65 P,sans-serif;color:#293b2e;margin:0;padding:18mm}h1{font-size:25pt}h2{font-size:14pt;margin-top:24pt}li{margin:5pt 0;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:8pt;overflow-wrap:anywhere}tr{break-inside:avoid}a{color:#355b46;text-decoration:underline}td,th{border-bottom:1px solid #ddd;padding:7pt;text-align:left;vertical-align:top}th{background:#edf1e8}@page{size:A4;margin:6mm}"
 out=ROOT/'docs/implementation-report.html';out.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>플리 구현·검증 보고서</title><style>'+css+'</style>'+body+'</html>')
 if '--pdf'in sys.argv:
  from playwright.sync_api import sync_playwright
  with sync_playwright()as p:
   b=p.chromium.launch(headless=True);v=b.new_page();v.goto(out.as_uri());v.evaluate('document.fonts.ready');v.pdf(path=str(ROOT/'docs/implementation-report.pdf'),print_background=True,prefer_css_page_size=True);b.close()
 if '--pdf'in sys.argv:
  info={'apkSha256':digest(apk),'generatedAt':date,'files':{str(path.relative_to(ROOT)):digest(path)for path in [ROOT/'docs/implementation-report.md',out,ROOT/'docs/implementation-report.pdf']}}
  (ROOT/'docs/report-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
