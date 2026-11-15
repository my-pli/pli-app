#!/usr/bin/env python3
"""Project-local Pleos SDK, APK and emulator workflow. No hosted website is used."""
from pathlib import Path
import argparse,fcntl,glob,hashlib,json,os,shlex,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1]
if '--profile' in sys.argv:
 _profile_index=sys.argv.index('--profile');_profile=sys.argv[_profile_index+1]
 if _profile not in {'personal','public'}:raise SystemExit('profile: personal or public')
 os.environ['PLI_PROFILE']=_profile;del sys.argv[_profile_index:_profile_index+2]
from runtime_context import selected, state_dir, SHARED,runtime_intent,set_runtime_intent
CONTEXT=selected()
TOOLS=state_dir();SDK=SHARED/'android-sdk';AVD=SHARED/'android-avd';LOGS=TOOLS/'logs';DOWNLOADS=SHARED/'downloads'
PACKAGE='ai.teammoon.pli';NAME=CONTEXT.avd_name
APK=ROOT/'android/app/build/outputs/apk/debug/app-debug.apk'
IMAGE_URL='https://nexus-playground.pleos.ai/repository/raw-releases/connect-avd/2.x/crp_car_emulator.zip'
IMAGE_SHA1='b4f858d5bcc6c71506d7edfc872bcb9e5a11acaa'
GRADLE_VERSION='8.10.2'
EMULATOR_VERSION='35.6.11'
EMULATOR_SHA256='2fe2b56fe93ce75e1d478a40162131381d911c355efeaedb54dd1e0d0897a5cf'
ENV=os.environ.copy()
ENV.update(ANDROID_HOME=str(SDK),ANDROID_SDK_ROOT=str(SDK),ANDROID_AVD_HOME=str(AVD),ANDROID_USER_HOME=str(SHARED/'android-user'),GRADLE_USER_HOME=str(SHARED/'gradle-user'))
if Path('/usr/lib/jvm/java-17-openjdk-amd64').exists():ENV['JAVA_HOME']='/usr/lib/jvm/java-17-openjdk-amd64'
for folder in [TOOLS,LOGS,DOWNLOADS,AVD]:folder.mkdir(parents=True,exist_ok=True)

def run(args,**kwargs):
 return subprocess.run([str(x) for x in args],cwd=ROOT,env=ENV,check=True,**kwargs)
def output(args):return run(args,capture_output=True,text=True).stdout.strip()
def download(url,path):
 if path.exists() and path.stat().st_size>0:return
 partial=path.with_suffix(path.suffix+'.part')
 run(['curl','-L','--fail','--retry','3','--continue-at','-','-o',partial,url]);partial.rename(path)
def adb(serial,*args,**kwargs):return run([SDK/'platform-tools/adb','-s',serial,*args],**kwargs)
def adb_shell(serial,*args):return adb(serial,'shell',' '.join(shlex.quote(str(a)) for a in args),capture_output=True,text=True).stdout.strip()
def device():
 for line in output([SDK/'platform-tools/adb','devices']).splitlines()[1:]:
  parts=line.split()
  if len(parts)<2 or parts[1]!='device' or not parts[0].startswith('emulator-'):continue
  name=adb(parts[0],'emu','avd','name',capture_output=True,text=True).stdout.splitlines()
  if NAME in name:return parts[0]
 raise RuntimeError('플리의 Pleos 에뮬레이터가 없습니다. ./pleos run 으로 실행해 주세요.')
def gradle(*tasks):
 binary=SHARED/'gradle'/f'gradle-{GRADLE_VERSION}'/'bin/gradle'
 if not binary.exists():
  existing=glob.glob(str(Path.home()/f'.gradle/wrapper/dists/gradle-{GRADLE_VERSION}-bin/*/gradle-{GRADLE_VERSION}'))
  if existing:shutil.copytree(existing[0],binary.parent.parent,dirs_exist_ok=True)
  else:
   archive=DOWNLOADS/f'gradle-{GRADLE_VERSION}-bin.zip';download(f'https://downloads.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip',archive)
   with zipfile.ZipFile(archive) as z:z.extractall(SHARED/'gradle')
  binary.chmod(0o755)
 run([binary,'-p',ROOT/'android','--no-daemon','--console=plain','--max-workers=4',*tasks])
def setup(with_emulator=True):
 manager=SDK/'cmdline-tools/latest/bin/sdkmanager'
 if not manager.exists():
  archive=DOWNLOADS/'commandlinetools.zip';download('https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip',archive)
  target=SDK/'cmdline-tools';target.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(archive) as z:z.extractall(target)
  (target/'cmdline-tools').rename(target/'latest')
  for p in (target/'latest/bin').iterdir():p.chmod(0o755)
 if not (SDK/'platforms/android-35/android.jar').exists() or not (SDK/'emulator/emulator').exists():
  print('Android 개발 도구의 라이선스를 적용하고 이 폴더에 설치합니다.',flush=True)
  run([manager,f'--sdk_root={SDK}','--licenses'],input='y\n'*200,text=True)
  run([manager,f'--sdk_root={SDK}','platform-tools','platforms;android-35','build-tools;35.0.0','emulator'])
 (ROOT/'android/local.properties').write_text(f'sdk.dir={SDK}\n')
 ensure_signing_key()
 model=ROOT/'android/app/src/main/assets/model-ko'
 if not (model/'am/final.mdl').exists():
  archive=DOWNLOADS/'vosk-ko.zip';download('https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip',archive)
  parent=model.parent;parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(archive) as z:z.extractall(parent)
  (parent/'vosk-model-small-ko-0.22').rename(model)
 font=ROOT/'android/app/src/main/res/font/pretendard.ttf'
 if not font.exists():font.parent.mkdir(parents=True,exist_ok=True);download('https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/variable/PretendardVariable.ttf',font)
 if with_emulator:
  install_emulator()
  image=SDK/'system-images/android-34/pleos_car_emulator/crp_avd_out_x86_64'
  if not (image/'system.img').exists():
   archive=DOWNLOADS/'pleos-connect-2.1.0.zip';download(IMAGE_URL,archive)
   sha=hashlib.sha1()
   with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(8388608),b''):sha.update(chunk)
   if sha.hexdigest()!=IMAGE_SHA1:raise RuntimeError('공식 Pleos 이미지 체크섬이 일치하지 않습니다. 다운로드 파일을 확인해 주세요.')
   image.parent.mkdir(parents=True,exist_ok=True)
   with zipfile.ZipFile(archive) as z:z.extractall(image.parent)
  configure_avd(image)
 print('프로젝트 로컬 개발 환경 준비 완료',flush=True)
def install_emulator():
 revision=SDK/'emulator/source.properties'
 if revision.exists() and f'Pkg.Revision={EMULATOR_VERSION}' in revision.read_text().replace(' ',''):return
 archive=DOWNLOADS/f'emulator-{EMULATOR_VERSION}.zip'
 download('https://dl.google.com/android/repository/emulator-linux_x64-13610412.zip',archive)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=EMULATOR_SHA256:raise RuntimeError('공식 Android Emulator 체크섬 불일치')
 if (SDK/'emulator').exists():
  backup=TOOLS/f'emulator-previous-{int(time.time())}';shutil.move(SDK/'emulator',backup)
 with zipfile.ZipFile(archive) as z:
  z.extractall(SDK)
  for item in z.infolist():
   permissions=item.external_attr>>16
   if permissions:(SDK/item.filename).chmod(permissions&0o777)
def configure_avd(image):
 folder=AVD/f'{NAME}.avd';folder.mkdir(parents=True,exist_ok=True)
 if (folder/'config.ini').exists():return
 config={'AvdId':NAME,'avd.ini.displayname':'Pli · Pleos Connect 2.1','avd.ini.encoding':'UTF-8','abi.type':'x86_64','hw.cpu.arch':'x86_64','hw.cpu.ncore':'4','hw.ramSize':'6144','hw.lcd.width':'2560','hw.lcd.height':'1440','hw.lcd.density':'160','hw.gpu.enabled':'yes','hw.gpu.mode':'auto','hw.keyboard':'yes','hw.audioInput':'yes','hw.audioOutput':'yes','hw.mainKeys':'no','hw.initialOrientation':'landscape','hw.sdCard':'no','hw.device.name':'pleos_connect_v2.1','hw.device.manufacturer':'42dot','hw.multi_display_window':'no','hw.hotplug_multi_display':'no','disk.dataPartition.size':'8G','image.sysdir.1':str(image)+'/','runtime.network.latency':'none','runtime.network.speed':'full','tag.id':'android-automotive','tag.display':'Pleos Connect v2.1.0','fastboot.forceColdBoot':'yes','showDeviceFrame':'no','skin.dynamic':'yes'}
 (folder/'config.ini').write_text('\n'.join(f'{k}={v}' for k,v in config.items())+'\n')
 (AVD/f'{NAME}.ini').write_text(f'avd.ini.encoding=UTF-8\npath={folder}\ntarget=android-34\n')
def build(release=False):
 sys.path.insert(0,str(ROOT/"scripts"))
 from build_identity import native_sources,sha
 before=native_sources()
 if not (SDK/'platforms/android-35/android.jar').exists():setup(False)
 (ROOT/'android/local.properties').write_text(f'sdk.dir={SDK}\n')
 ensure_signing_key()
 gradle(':app:assembleRelease' if release else ':app:assembleDebug')
 artifacts=ROOT/'artifacts';artifacts.mkdir(exist_ok=True)
 source=ROOT/'android/app/build/outputs/apk/release/app-release.apk' if release else APK
 target=artifacts/('pli-pleos.apk' if release else 'pli-pleos-debug.apk')
 if native_sources()!=before:raise RuntimeError('Android 소스가 빌드 도중 바뀌었습니다. 배포하지 않았습니다.')
 temporary=target.with_suffix('.apk.tmp')
 shutil.copy2(source,temporary)
 if sha(temporary)!=sha(source):raise RuntimeError('APK 복사 무결성 검사 실패')
 with temporary.open('rb') as stream:os.fsync(stream.fileno())
 temporary.replace(target)
 if release:(artifacts/'build-info.json').write_text(json.dumps({'apkSha256':sha(target),'nativeSources':before,'gradle':GRADLE_VERSION,'release':True},indent=2)+'\n')
 print(f'APK: {target}',flush=True)
 return target
def ensure_signing_key():
 key=SHARED/'android-user/debug.keystore'
 if key.exists():return
 key.parent.mkdir(parents=True,exist_ok=True)
 keytool=Path(ENV['JAVA_HOME'])/'bin/keytool' if ENV.get('JAVA_HOME') else shutil.which('keytool')
 if not keytool:raise RuntimeError('JDK 17의 keytool을 찾을 수 없습니다. JAVA_HOME을 설정해 주세요.')
 run([keytool,'-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','androiddebugkey','-dname','CN=Android Debug,O=Android,C=US','-keyalg','RSA','-keysize','2048','-validity','10000'],capture_output=True)
 key.chmod(0o600)
def console_session():
 with (LOGS/'console-session.log').open('a') as log:
  subprocess.Popen([sys.executable,str(ROOT/'scripts/console-session.py')],cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
def connect_microphone():
 if CONTEXT.profile=='public':
  run([SHARED/'demo-venv/bin/python',ROOT/'scripts/audio_guard.py']);return
 if not (Path('/run/user')/str(os.getuid())/'pulse/native').exists():return
 python=SHARED/'qa-venv/bin/python'
 if not python.exists():
  python=SHARED/'audio-venv/bin/python'
  if not python.exists():run([sys.executable,'-m','venv',SHARED/'audio-venv'])
  run([python,'-m','pip','install','--quiet','pulsectl'])
 run([python,ROOT/'scripts/connect-microphone.py'])
def shutdown(serial):
 pidfile=TOOLS/'emulator.pid'
 pid=int(pidfile.read_text()) if pidfile.exists() else 0
 adb(serial,'emu','kill',capture_output=True)
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  command=Path(f'/proc/{pid}/cmdline')
  alive=pid and command.exists() and NAME.encode() in command.read_bytes()
  if not alive and serial not in output([SDK/'platform-tools/adb','devices']):return
  time.sleep(.25)
def launch(headless=False,no_build=False,release=False,installed_now=False,_locked=False):
 if not _locked:
  with (TOOLS/'runtime-launch.lock').open('w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   intent=runtime_intent(TOOLS);qa_generation=ENV.get('PLI_QA_INTENT_GENERATION')
   if qa_generation is not None and (intent['generation']!=int(qa_generation)or intent['desiredState']!='running'):raise RuntimeError('RUNTIME_INTENT_CHANGED')
   if ENV.get('PLI_RUNTIME_AUTOMATIC') == '1' and intent['desiredState']=='paused':return
   if ENV.get('PLI_RUNTIME_AUTOMATIC') != '1' and qa_generation is None:set_runtime_intent(TOOLS,'running')
   return launch(headless,no_build,release,installed_now,True)
 if not (AVD/f'{NAME}.ini').exists():setup(True)
 if CONTEXT.profile=='public':(TOOLS/'portal-mode').touch()
 if CONTEXT.profile=='public':
  run([SHARED/'demo-venv/bin/python',ROOT/'scripts/audio_guard.py'])
  os.environ['PLI_MIC_SOURCE']='pli_remote_mic_public.monitor'
  ENV.update(PULSE_SOURCE='pli_remote_mic_public.monitor',QEMU_PA_SOURCE='pli_remote_mic_public.monitor',PULSE_SINK='pli_remote_speaker_public',QEMU_PA_SINK='pli_remote_speaker_public')
 package=ROOT/'artifacts'/('pli-pleos.apk' if release else 'pli-pleos-debug.apk')
 if not no_build or not package.exists():package=build(release)
 try:serial=device()
 except RuntimeError:
  install_emulator()
  runtime=Path('/run/user')/str(os.getuid())
  if runtime.exists():ENV.setdefault('XDG_RUNTIME_DIR',str(runtime))
  if (runtime/'pulse/native').exists():ENV.setdefault('PULSE_SERVER',f'unix:{runtime}/pulse/native')
  if shutil.which('wpctl'):
   props=subprocess.run(['wpctl','inspect','@DEFAULT_AUDIO_SOURCE@'],capture_output=True,text=True).stdout
   import re
   found=re.search(r'node.name = "([^"]+)"',props)
   if found and 'input' in found.group(1):ENV['PULSE_SOURCE']=os.environ.get('PLI_MIC_SOURCE',found.group(1))
   else:
    nodes=subprocess.run(['wpctl','status','-n'],capture_output=True,text=True).stdout
    physical=re.search(r'(?:alsa_input|bluez_input)\.[\w.-]+',nodes)
    if physical:ENV['PULSE_SOURCE']=os.environ.get('PLI_MIC_SOURCE',physical.group(0))
  if not ENV.get('DISPLAY'):
   displays=glob.glob('/tmp/.X11-unix/X*')
   if displays:ENV['DISPLAY']=':'+Path(displays[0]).name[1:]
  if not ENV.get('XAUTHORITY') and (runtime/'gdm/Xauthority').exists():ENV['XAUTHORITY']=str(runtime/'gdm/Xauthority')
  ports=output([SDK/'platform-tools/adb','devices'])
  port=5554
  while f'emulator-{port}' in ports:port+=2
  gpu=os.environ.get('PLI_EMULATOR_GPU','host')
  # PRIME must be selected before the emulator loads GL. The desktop default
  # may be an integrated adapter even on a supported discrete NVIDIA host.
  if gpu=='host'and (CONTEXT.profile=='public'or ENV.get('PLI_HOST_GPU')=='nvidia')and ENV.get('PLI_HOST_GPU','auto')!='default'and shutil.which('nvidia-smi'):
   probe=subprocess.run(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],capture_output=True,timeout=4)
   if probe.returncode==0:
    ENV.setdefault('__NV_PRIME_RENDER_OFFLOAD','1');ENV.setdefault('__GLX_VENDOR_LIBRARY_NAME','nvidia')
    print('Pleos GPU: NVIDIA PRIME (actual renderer is recorded in emulator.log)',flush=True)
  args=[str(SDK/'emulator/emulator'),'-avd',NAME,'-no-snapshot','-no-boot-anim','-no-metrics','-gpu',gpu,'-feature','-Vulkan','-memory','8192','-cores','6','-port',str(port),'-scale','.67','-timezone','Asia/Seoul']
  if CONTEXT.profile=='public':args += ['-grpc',str(CONTEXT.grpc_port),'-grpc-use-token']
  if headless or not ENV.get('DISPLAY'):args.append('-no-window')
  previous_log=LOGS/'emulator.log'
  if previous_log.exists():previous_log.rename(LOGS/('emulator-'+time.strftime('%Y%m%d-%H%M%S')+'.log'))
  (TOOLS/'emulator.pid').unlink(missing_ok=True)
  with previous_log.open('w') as log:process=subprocess.Popen([sys.executable,str(ROOT/'scripts/emulator-keeper.py'),*args],cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  serial=f'emulator-{port}'
  print('Pleos Connect 부팅 중…',flush=True)
  deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   if process.poll() is not None:raise RuntimeError(f'에뮬레이터가 종료됐습니다. {LOGS}/emulator.log 를 확인해 주세요.')
   result=subprocess.run([str(SDK/'platform-tools/adb'),'-s',serial,'shell','getprop','sys.boot_completed'],capture_output=True,text=True,env=ENV)
   if result.stdout.strip()=='1':break
   time.sleep(2)
  else:raise RuntimeError('부팅 대기 시간을 초과했습니다. 에뮬레이터 로그를 확인해 주세요.')
 if adb_shell(serial,'getprop','ro.fw.mu.headless_system_user')=='true':
  for _ in range(60):
   if adb_shell(serial,'am','get-current-user')!='0':break
   time.sleep(.5)
  else:raise RuntimeError('Pleos 운전자 프로필이 아직 준비되지 않았습니다.')
 try:previous=adb_shell(serial,'pm','path','--user','current',PACKAGE).splitlines()
 except subprocess.CalledProcessError:previous=[]
 same=False
 if previous and not same:
  try:same=adb_shell(serial,'sha256sum',previous[0].removeprefix('package:')).split()[0]==hashlib.sha256(package.read_bytes()).hexdigest()
  except subprocess.CalledProcessError:pass
 if not same:
  if previous:
   user=adb_shell(serial,'am','get-current-user')
   current=json.loads(adb_shell(serial,'content','read','--user',user,'--uri','content://'+PACKAGE+'.demo/state'))
   if current.get('sessionStatus')!='STOPPED':
    session_control(serial,'end')
    until=time.monotonic()+8
    while time.monotonic()<until:
     current=json.loads(adb_shell(serial,'content','read','--user',user,'--uri','content://'+PACKAGE+'.demo/state'))
     if current.get('sessionStatus')=='STOPPED':break
     time.sleep(.2)
    else:raise RuntimeError('기존 음성 자원 종료 미확인: APK를 교체하지 않았습니다.')
  if CONTEXT.profile=='public':
   # The image speech service can retain a dead SDK client across APK replacement.
   # Reset only the isolated demo engine, after the old app has confirmed STOPPED.
   adb(serial,'shell','am','force-stop','--user','current','ai.pleos.playground.caas',capture_output=True)
  adb(serial,'install','-r','-t',package)
  adb(serial,'shell','sync',capture_output=True)
 for permission in ['android.permission.RECORD_AUDIO','android.permission.POST_NOTIFICATIONS','android.car.permission.CAR_SPEED','android.car.permission.CAR_POWERTRAIN','pleos.car.permission.FUSED_LOCATION','pleos.car.permission.NAVI_ROUTE_SEARCH']:
  subprocess.run([str(SDK/'platform-tools/adb'),'-s',serial,'shell','pm','grant','--user','current',PACKAGE,permission],env=ENV,capture_output=True)
 adb(serial,'shell','settings','put','global','auto_time_zone','0',capture_output=True)
 adb(serial,'shell','cmd','alarm','set-time',str(int(time.time()*1000)),capture_output=True)
 adb(serial,'shell','cmd','alarm','set-timezone','Asia/Seoul',capture_output=True)
 adb(serial,'emu','avd','hostmicon',capture_output=True)
 adb(serial,'forward',f'tcp:{CONTEXT.console_port}','tcp:8088',capture_output=True)
 console_session()
 presentation=[]
 if (TOOLS/'portal-mode').exists():
  presentation=[]
  # Pleos starts its navigation task after sys.boot_completed. Launching in that
  # interval can leave an app behind the organizer's initial navigation surface.
  for _ in range(30):
   ready=subprocess.run([str(SDK/'platform-tools/adb'),'-s',serial,'shell','pidof','ai.umos.maps.android.navigation.app'],capture_output=True,text=True,env=ENV)
   if ready.returncode==0 and ready.stdout.strip():break
   time.sleep(1)
  user=adb_shell(serial,'am','get-current-user')
  current=json.loads(adb_shell(serial,'content','read','--user',user,'--uri','content://'+PACKAGE+'.demo/state'))
  if current.get('sessionStatus')!='STOPPED':
   session_control(serial,'end');until=time.monotonic()+8
   while time.monotonic()<until:
    current=json.loads(adb_shell(serial,'content','read','--user',user,'--uri','content://'+PACKAGE+'.demo/state'))
    if current.get('sessionStatus')=='STOPPED':break
    time.sleep(.2)
   else:raise RuntimeError('음성 종료 미확인: 앱을 강제 종료하지 않았습니다.')
  adb(serial,'shell','am','force-stop','--user','current',PACKAGE,capture_output=True)
  if CONTEXT.profile=='public':session_control(serial,'provision_public')
  session_control(serial,'preview')
 started=adb(serial,'shell','am','start','--user','current','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','-n',PACKAGE+'/.MainActivity',*presentation,capture_output=True,text=True)
 print(started.stdout,flush=True)
 if 'Error:' in started.stdout or 'Error type' in started.stdout or 'Error:' in started.stderr:raise RuntimeError('APK 실행 실패: '+started.stdout+started.stderr)
 (TOOLS/'run-state.json').write_text(json.dumps({'serial':serial,'profile':CONTEXT.profile,'avdName':NAME,'userId':adb_shell(serial,'am','get-current-user'),'package':PACKAGE,'release':release,'grpcPort':CONTEXT.grpc_port,'consolePort':CONTEXT.console_port}))
 connect_microphone()
 print(f'실행 완료: {serial}\n음성으로 “숫자 놀이 해 줘”, “플리야 쉿”, “다시 놀자”라고 말해 보세요.\n차량 개발 콘솔: http://127.0.0.1:{CONTEXT.console_port}/',flush=True)
def session_control(serial,action):
 user=adb_shell(serial,'am','get-current-user')
 result=adb(serial,'shell','content','call','--user',user,'--uri','content://'+PACKAGE+'.demo','--method','session','--arg',action,capture_output=True)
 out=result.stdout.decode(errors='replace') if isinstance(result.stdout,bytes) else result.stdout
 if 'Exception' in out or 'Error' in out or 'Result:' not in out:raise RuntimeError('APK 세션 명령을 적용하지 못했습니다: '+action)
def inject(key,text):
 serial=device();print('개발용 입력 주입입니다. 실제 마이크 인식 시험과 구분합니다.',flush=True)
 print(adb_shell(serial,'am','broadcast','--user','current','-n',PACKAGE+'/.DebugReceiver','-a',PACKAGE+'.DEBUG','--es',key,text))
def upload_private(serial,user,source,name):
 remote='/data/local/tmp/pli-upload-'+name
 try:
  adb(serial,'push',source,remote,capture_output=True)
  adb_shell(serial,'chmod','600',remote)
  command='cat '+shlex.quote(remote)+' | run-as '+shlex.quote(PACKAGE)+' --user '+shlex.quote(user)+' tee '+shlex.quote('files/'+name)+' >/dev/null'
  adb_shell(serial,'sh','-c',command)
  actual=adb_shell(serial,'run-as',PACKAGE,'--user',user,'sha256sum','files/'+name).split()[0]
  if actual!=hashlib.sha256(Path(source).read_bytes()).hexdigest():raise RuntimeError('파일 전송 검증 실패')
 finally:adb_shell(serial,'rm','-f',remote)
def snapshot():
 serial=device();user=adb_shell(serial,'am','get-current-user');raw=adb_shell(serial,'run-as',PACKAGE,'--user',user,'cat','files/debug-state.json');print(raw)
def main():
 parser=argparse.ArgumentParser(description='이 폴더에서 Pleos APK 개발·실행')
 sub=parser.add_subparsers(dest='command',required=True)
 sub.add_parser('setup');sub.add_parser('doctor');b=sub.add_parser('build');b.add_argument('--release',action='store_true')
 r=sub.add_parser('run');r.add_argument('--headless',action='store_true');r.add_argument('--no-build',action='store_true');r.add_argument('--release',action='store_true')
 sub.add_parser('test');sub.add_parser('state');sub.add_parser('stop');sub.add_parser('personal')
 q=sub.add_parser('demo');q.add_argument('action',nargs='?',default='start',choices=['start','stop','status'])
 q=sub.add_parser('public');q.add_argument('action',nargs='?',default='start',choices=['start','stop','status'])
 for cmd in ['say','event']:
  q=sub.add_parser(cmd);q.add_argument('text',nargs='+')
 q=sub.add_parser('wav');q.add_argument('path',type=Path)
 q=sub.add_parser('screenshot');q.add_argument('path',nargs='?',default=str(ROOT/'qa/native/screen.png'))
 q=sub.add_parser('import-plan');q.add_argument('path',type=Path)
 args=parser.parse_args()
 if args.command=='setup':setup()
 elif args.command=='demo':run([sys.executable,ROOT/'scripts/demo.py',args.action])
 elif args.command=='public':run([sys.executable,ROOT/'scripts/public-demo.py',args.action])
 elif args.command=='doctor':
  checks={'Java 17':Path(ENV.get('JAVA_HOME',''))/'bin/java','Android SDK':SDK/'platforms/android-35/android.jar','Pleos 이미지':SDK/'system-images/android-34/pleos_car_emulator/crp_avd_out_x86_64/system.img','한국어 모델':ROOT/'android/app/src/main/assets/model-ko/am/final.mdl','AVD':AVD/f'{NAME}.ini'}
  for name,path in checks.items():print(('OK ' if path.exists() else 'MISSING ')+name+': '+str(path))
  print('KVM:',os.access('/dev/kvm',os.R_OK|os.W_OK))
  revision=SDK/'emulator/source.properties'
  if revision.exists():print(next((line for line in revision.read_text().splitlines() if line.startswith('Pkg.Revision')),''))
 elif args.command=='build':build(args.release)
 elif args.command=='run':launch(args.headless,args.no_build,args.release)
 elif args.command=='personal':
  import urllib.request
  try:
   with urllib.request.urlopen('http://127.0.0.1:8876/api/status',timeout=3) as response:shared=json.loads(response.read())
  except OSError:shared={}
  if shared.get('lease',{}).get('busy') or shared.get('voiceBusy'):raise RuntimeError('공개 체험이 끝난 뒤 개인용 앱을 열어 주세요.')
  (TOOLS/'portal-mode').unlink(missing_ok=True)
  serial=device()
  session_control(serial,'private')
  adb(serial,'shell','am','start','--user','current','--activity-single-top','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','-n',PACKAGE+'/.MainActivity',capture_output=True)
  time.sleep(.4)
  session_control(serial,'personal')
  print('개인용 플리를 열었습니다. “오늘 뭐 해?”라고 말해 주세요.')
 elif args.command=='test':gradle(':app:testDebugUnitTest')
 elif args.command=='state':snapshot()
 elif args.command=='say':inject('text',' '.join(args.text))
 elif args.command=='event':inject('event',' '.join(args.text))
 elif args.command=='stop':
  qa_generation=ENV.get('PLI_QA_INTENT_GENERATION')
  if qa_generation is None:set_runtime_intent(TOOLS,'paused')
  elif runtime_intent(TOOLS)['generation']!=int(qa_generation):raise RuntimeError('RUNTIME_INTENT_CHANGED')
  pidfile=TOOLS/'console-session.pid'
  if pidfile.exists():
   pid=int(pidfile.read_text());cmdline=Path(f'/proc/{pid}/cmdline')
   if cmdline.exists() and str(ROOT/'scripts/console-session.py').encode() in cmdline.read_bytes():os.kill(pid,signal.SIGTERM)
  with (TOOLS/'runtime-launch.lock').open('w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   try:shutdown(device())
   except RuntimeError:pass
 elif args.command=='screenshot':
  path=Path(args.path);path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('wb') as f:adb(device(),'exec-out','screencap','-p',stdout=f)
  print(path)
 elif args.command in ['wav','import-plan']:
  serial=device();user=adb_shell(serial,'am','get-current-user')
  if args.command=='wav':
   python=SHARED/'demo-venv/bin/python'
   if not python.exists():python=SHARED/'audio-venv/bin/python'
   run([python,ROOT/'scripts/feed-microphone.py',args.path.resolve()])
  else:
   path=args.path.resolve();kind='plan-text' if path.suffix.lower() in ['.txt','.csv'] else 'plan-image'
   payload=path.read_bytes();limit=65536 if kind=='plan-text' else 8*1024*1024
   if not payload or len(payload)>limit:raise RuntimeError('계획안은 텍스트 64KB, 사진 8MB 이내로 준비해 주세요.')
   adb(serial,'exec-in','content','write','--user',user,'--uri','content://ai.teammoon.pli.demo/'+kind,input=payload,capture_output=True)
   expected=hashlib.sha256(payload).hexdigest()
   for _ in range(8):
    info=json.loads(adb_shell(serial,'content','read','--user',user,'--uri','content://ai.teammoon.pli.demo/integration'))
    if info.get('planSha256')==expected:break
    time.sleep(.25)
   else:raise RuntimeError('계획안 전송 검증 실패. 최신 배포 APK를 설치해 주세요.')
   print('계획안 준비 완료. 앱에서 “계획안 읽어 줘”라고 말해 주세요.')
if __name__=='__main__':
 try:main()
 except (RuntimeError,subprocess.CalledProcessError) as error:print(str(error),file=sys.stderr);sys.exit(1)
