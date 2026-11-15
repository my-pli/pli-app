"""Current public APK pixels and actual TTS output, with receipt-timed captions."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': True,
          'expectedChecks': ['actualSpokenReceiptsCaptioned',
                             'allRecordedTasksCompleted',
                             'currentApkRecorded',
                             'exportFrameRateIs30WithoutTimestampDuplication'],
          'safetyChecks': {},
          'inputs': ['android/app/src/main/AndroidManifest.xml',
                     'android/app/src/main/java/ai/teammoon/pli/DemoStateProvider.kt',
                     'android/app/src/main/java/ai/teammoon/pli/MainActivity.kt',
                     'android/app/src/main/java/ai/teammoon/pli/PliApplication.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/DataContract.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/FamilyDocuments.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/PlanDocuments.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/PlanImporter.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/PliStore.kt',
                     'android/app/src/main/java/ai/teammoon/pli/data/SessionJournal.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/FamilyAnswers.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/JourneyExperience.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/LearningCatalog.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/Models.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/ReadingContext.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/VehicleSignalHealth.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/VoiceInterpreter.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/StageCards.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/MicLevel.kt',
                     'android/app/src/main/java/ai/teammoon/pli/domain/DemoTrip.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/KoreanReading.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PliVoiceEngine.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/OnDevicePlayback.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/EdgeVoice.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/CarPanel.kt',
                     'android/app/src/main/assets/tts/manifest.json',
                     'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
                     'android/app/src/main/java/ai/teammoon/pli/edge/EdgeAi.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/PliStage.kt',
                     'android/app/src/main/java/ai/teammoon/pli/ui/StageSurface.kt',
                     'android/app/src/main/java/ai/teammoon/pli/vehicle/PleosVehicleSource.kt',
                     'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleConnection.kt',
                     'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleService.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/CompanionService.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/ConversationController.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/KoreanModel.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/OfflineListener.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PcmCapture.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PcmWav.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PleosSpeechListener.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/PliSpeaker.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/SpeechSdkIo.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/UtteranceGate.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/VoiceSessionConnection.kt',
                     'android/app/src/main/java/ai/teammoon/pli/voice/WindowRecoveryPolicy.kt',
                     'android/app/src/main/res/drawable/ic_pli.xml',
                     'android/app/src/main/res/values/styles.xml',
                     'android/app/src/main/res/xml/automotive_app_desc.xml',
                     'android/app/src/main/res/xml/network_security_config.xml',
                     'demo-v2/app.js',
                     'demo-v2/audio-worklet.js',
                     'demo-v2/index.html',
                     'demo-v2/style.css',
                     'scripts/audio_guard.py',
                     'scripts/demo-server.py',
                     'scripts/display_stream.py',
                     'scripts/portal_proxy.py',
                     'scripts/runtime_context.py'],
          'fixtures': ['abacus-hint.wav',
                       'answer-six.wav',
                       'arrive.wav',
                       'growth-records.wav',
                       'math-primary.wav',
                       'parent-prep.wav',
                       'role-swap.wav',
                       'silence.wav',
                       'word-tree.wav'],
          'effects': 'mutate',
          'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
          'executionKind': 'NATIVE_E2E'},
 'record': {'profile': 'public',
            'nativeRequired': True,
            'expectedChecks': ['actualSpokenReceiptsCaptioned',
                               'allRecordedTasksCompleted',
                               'currentApkRecorded'],
            'safetyChecks': {},
            'inputs': ['android/app/src/main/AndroidManifest.xml',
                       'android/app/src/main/java/ai/teammoon/pli/DemoStateProvider.kt',
                       'android/app/src/main/java/ai/teammoon/pli/MainActivity.kt',
                       'android/app/src/main/java/ai/teammoon/pli/PliApplication.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/DataContract.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/FamilyDocuments.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/PlanDocuments.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/PlanImporter.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/PliStore.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/SessionJournal.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/FamilyAnswers.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/JourneyExperience.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/LearningCatalog.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/Models.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/ReadingContext.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/VehicleSignalHealth.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/VoiceInterpreter.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/StageCards.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/MicLevel.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
                       'android/app/src/main/java/ai/teammoon/pli/vehicle/PleosVehicleSource.kt',
                       'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleConnection.kt',
                       'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleService.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/CompanionService.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/ConversationController.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/KoreanModel.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/OfflineListener.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PcmCapture.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PcmWav.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PleosSpeechListener.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PliSpeaker.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/SpeechSdkIo.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/UtteranceGate.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/VoiceSessionConnection.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/WindowRecoveryPolicy.kt',
                       'android/app/src/main/res/drawable/ic_pli.xml',
                       'android/app/src/main/res/values/styles.xml',
                       'android/app/src/main/res/xml/automotive_app_desc.xml',
                       'demo-v2/app.js',
                       'demo-v2/audio-worklet.js',
                       'demo-v2/index.html',
                       'demo-v2/style.css',
                       'scripts/audio_guard.py',
                       'scripts/demo-server.py',
                       'scripts/display_stream.py',
                       'scripts/portal_proxy.py',
                       'scripts/runtime_context.py'],
            'fixtures': ['abacus-hint.wav',
                         'answer-six.wav',
                         'arrive.wav',
                         'growth-records.wav',
                         'math-primary.wav',
                         'parent-prep.wav',
                         'role-swap.wav',
                         'silence.wav',
                         'word-tree.wav'],
            'effects': 'mutate',
            'resources': [['host-load', 'shared'], ['public-service', 'shared'], ['public-avd', 'exclusive']],
            'executionKind': 'NATIVE_E2E'},
 'export': {'profile': None,
            'nativeRequired': False,
            'expectedChecks': ['actualSpokenReceiptsCaptioned',
                               'allRecordedTasksCompleted',
                               'currentApkRecorded',
                               'exportFrameRateIs30WithoutTimestampDuplication'],
            'safetyChecks': {},
            'inputs': ['android/app/src/main/AndroidManifest.xml',
                       'android/app/src/main/java/ai/teammoon/pli/DemoStateProvider.kt',
                       'android/app/src/main/java/ai/teammoon/pli/MainActivity.kt',
                       'android/app/src/main/java/ai/teammoon/pli/PliApplication.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/DataContract.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/FamilyDocuments.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/PlanDocuments.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/PlanImporter.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/PliStore.kt',
                       'android/app/src/main/java/ai/teammoon/pli/data/SessionJournal.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/FamilyAnswers.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/JourneyExperience.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/LearningCatalog.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/Models.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/ReadingContext.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/VehicleSignalHealth.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/VoiceInterpreter.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/StageCards.kt',
                       'android/app/src/main/java/ai/teammoon/pli/domain/MicLevel.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/FrameLoop.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/StageTheme.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/StageBackdrop.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/ExperiencePanels.kt',
                       'android/app/src/main/java/ai/teammoon/pli/ui/PliScreen.kt',
                       'android/app/src/main/java/ai/teammoon/pli/vehicle/PleosVehicleSource.kt',
                       'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleConnection.kt',
                       'android/app/src/main/java/ai/teammoon/pli/vehicle/VehicleService.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/CompanionService.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/ConversationController.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/KoreanModel.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/OfflineListener.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PcmCapture.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PcmWav.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PleosSpeechListener.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/PliSpeaker.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/SpeechSdkIo.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/UtteranceGate.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/VoiceSessionConnection.kt',
                       'android/app/src/main/java/ai/teammoon/pli/voice/WindowRecoveryPolicy.kt',
                       'android/app/src/main/res/drawable/ic_pli.xml',
                       'android/app/src/main/res/values/styles.xml',
                       'android/app/src/main/res/xml/automotive_app_desc.xml',
                       'artifacts/build-info.json',
                       'artifacts/pli-pleos.apk',
                       'scripts/audio_guard.py',
                       'scripts/display_stream.py',
                       'scripts/runtime_context.py',
                       '.tools/exec-evidence/current-preview.webm'],
            'fixtures': [],
            'effects': 'none',
            'resources': [['host-load', 'shared']],
            'executionKind': 'EVIDENCE'}}
from pathlib import Path
import json,time,base64,hashlib,subprocess,argparse
parser=argparse.ArgumentParser();parser.add_argument('--scope',choices=['full','record','export'],default='full');args=parser.parse_args()
from run_record import RunRecord,compatible_tool,archived_producer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics)
url=json.loads((ROOT/'.tools/public-config.json').read_text())['url'];output=ROOT/'artifacts/native-preview';output.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def vtt_time(t):
 ms=max(0,round(t*1000));return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
# Reviewed successful producer before the export-only FPS correction. Its APK,
# runtime sources, fixtures, raw bytes and confirmed cleanup must all still match.
# Raw producer bytes are archived by RunRecord; unknown producers are not reused.
def recording_sources(values):
 return {name:value for name,value in values.items()if name.startswith('android/')or name.startswith('scripts/emulator_proto/')or name in {'scripts/display_stream.py','scripts/audio_guard.py','scripts/runtime_context.py'}}
def recording_reusable(manifest,result,data,current):
 return (manifest.get('profile')=='public'and manifest.get('scope','full')in {'full','record'}
  and archived_producer(manifest.get('scriptSha256'))is not None
  and compatible_tool(manifest,result)
  and manifest.get('apkSha256')==current['apkSha256']==data.get('apkSha256')==manifest.get('installed',{}).get('sha256')
  and recording_sources(manifest.get('source',{}))==recording_sources(current['source'])and(current.get('scope')=='export'or manifest.get('fixtures')==current['fixtures'])
  and manifest.get('buildInputsMatch')is True and result.get('buildInputsMatch')is True
  and result.get('runId')==manifest.get('runId')and result.get('status')=='PASSED'and result.get('passed')is True
  and result.get('sourceChanged')is False and result.get('installedMatchesArtifact')is True and result.get('cleanupStatus')=='CONFIRMED'
  and bool(result.get('checks'))and all(value=='PASS'for value in result['checks'].values())
  and len(data.get('tasks',[]))==8 and len(data.get('receipts',[]))>=8
  and data.get('rawPath')=='.tools/exec-evidence/current-preview.webm')
def finish_recording(payload):
 raw=ROOT/payload['rawPath'];assert sha(raw)==payload['rawSha256'];assert payload['apkSha256']==record.manifest['apkSha256']
 duration=payload['durationSeconds'];receipts=payload['receipts'];metrics['actualTasks']=payload['tasks'];began=time.monotonic()
 # captureStream WebM advertises a 1000 Hz timestamp base. Unspecified output
 # fps duplicates ~84k frames for an 84-second clip and stalls export/playback.
 subprocess.run(['ffmpeg','-nostdin','-y','-loglevel','error','-i',str(raw),'-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-r','30','-fps_mode','cfr','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output/'preview.mp4')],check=True)
 exported=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_frames','-of','json',str(output/'preview.mp4')]))['streams'][0]
 metrics['exportedVideo']=exported;checks['exportFrameRateIs30WithoutTimestampDuplication']=exported['avg_frame_rate']=='30/1'and int(exported['nb_frames'])<=int(duration*30)+60
 subtitles=['WEBVTT',''];transcript=[]
 for i,r in enumerate(receipts):
  end=min(duration,receipts[i+1]['at']if i+1<len(receipts)else duration)
  if end<=r['at']:continue
  subtitles += [str(i+1),vtt_time(r['at'])+' --> '+vtt_time(end),r['text'],''];transcript.append(f"[{vtt_time(r['at'])}] {r['text']}")
 (output/'preview.vtt').write_text('\n'.join(subtitles));(output/'preview-transcript.txt').write_text('\n'.join(transcript)+'\n')
 info={'videoSha256':sha(output/'preview.mp4'),'apkSha256':sha(ROOT/'artifacts/pli-pleos.apk'),'durationSeconds':round(duration,3),'recordedAt':payload.get('recordedAt',__import__('datetime').datetime.now().astimezone().isoformat()),'encodedAt':__import__('datetime').datetime.now().astimezone().isoformat(),'recordingRunId':payload.get('producerRunId',record.id),'source':'Actual isolated public APK view and received native TTS PCM; synthetic microphone input. Greeting and preparation excluded before recording. No private family data.','tasks':metrics['actualTasks'],'subtitleSha256':sha(output/'preview.vtt'),'transcriptSha256':sha(output/'preview-transcript.txt'),'receipts':receipts}
 (output/'preview-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));checks['allRecordedTasksCompleted']=len(metrics['actualTasks'])==8;checks['actualSpokenReceiptsCaptioned']=len(receipts)>=8;checks['currentApkRecorded']=info['apkSha256']==record.manifest['apkSha256'];metrics.update(videoPath=str((output/'preview.mp4').relative_to(ROOT)),videoSha256=info['videoSha256'],apkSha256=info['apkSha256'],durationSeconds=duration,captionCount=len(receipts))
 metrics['encodingSeconds']=round(time.monotonic()-began,3)
for prior in ([]if args.scope=='record'else sorted((ROOT/'qa/native/runs').glob('*/recording.json'),reverse=True)):
 try:
  data=json.loads(prior.read_text());manifest=json.loads(prior.with_name('manifest.json').read_text());result=json.loads(prior.with_name('result.json').read_text())
  if not recording_reusable(manifest,result,data,record.manifest)or sha(ROOT/data['rawPath'])!=data['rawSha256']:continue
 except (OSError,ValueError,KeyError):continue
 metrics['reusedNativeRecording']={'runId':data.get('producerRunId',manifest['runId']),'rawSha256':data['rawSha256'],'scope':'Previously PASSED actual native pixels, 8 tasks and TTS receipts; same APK, runtime, fixtures and confirmed cleanup. Only encoding and delivery are new.'}
 data.setdefault('recordedAt',manifest['startedAt']);data['producerRunId']=data.get('producerRunId',manifest['runId']);(record.dir/'recording.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));finish_recording(data)
 print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values());raise SystemExit(0)
if args.scope=='export':record.failure='PRECONDITION_FAILED';raise SystemExit('No qualified raw recording; export never falls back to a device session')
with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome',args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required','--use-file-for-fake-audio-capture='+str(ROOT/'qa/native/fixtures/silence.wav')]);c=b.new_context(permissions=['microphone'],viewport={'width':1440,'height':1000});v=c.new_page();v.goto(url+'/app');v.wait_for_function("state.media==='LIVE'&&state.status.controlReady&&!state.status.lease.busy");v.locator('#connect').click();v.wait_for_function('state.voice',timeout=45000)
 def ready():v.wait_for_function("state.status.app.phase==='LISTENING'&&state.status.app.recognition==='READY'&&state.status.app.playback==='IDLE'&&state.status.app.speech===state.status.app.requestedText",timeout=40000);v.wait_for_timeout(500)
 try:
  ready();v.evaluate('source.disconnect(filter)')
  # Arrival needs a real started trip, even when the recording opens parked.
  v.evaluate("post('/api/vehicle',{action:'drive'})");v.wait_for_function("state.status.app.gear==='D'");ready()
  v.evaluate("post('/api/vehicle',{action:'park'})");v.wait_for_function("state.status.app.gear==='P'");ready()
  v.evaluate('''()=>{const live=$('live-video');window.qaMediaChunks=[];window.qaAudio=ctx.createMediaStreamDestination();duplex.connect(qaAudio);window.qaRecorder=new MediaRecorder(new MediaStream([...live.captureStream().getVideoTracks(),...qaAudio.stream.getAudioTracks()]),{mimeType:'video/webm;codecs=vp8,opus',videoBitsPerSecond:2500000,audioBitsPerSecond:128000});qaRecorder.ondataavailable=e=>{if(e.data.size)qaMediaChunks.push(e.data)};window.qaStarted=performance.now();window.qaReceipts=[];window.qaLastSpeech=state.status.app.spokenSequence;window.qaCaptionTimer=setInterval(()=>{const a=state.status.app;if(a.spokenSequence>qaLastSpeech){qaLastSpeech=a.spokenSequence;qaReceipts.push({at:Math.max(0,(performance.now()-qaStarted-(a.deviceElapsedMs-a.playbackStartedAtElapsed))/1000),text:a.speech,sequence:a.spokenSequence})}},100);qaRecorder.start(500);}''')
  for name,predicate in [('parent-prep.wav',"state.status.app.audience==='PARENT'&&state.status.app.speech.includes('샘플')"),('math-primary.wav',"state.status.app.game==='MATH'"),('abacus-hint.wav',"state.status.app.abacusHint"),('answer-six.wav',"state.status.app.answered>0"),('role-swap.wav',"state.status.app.panel==='ENGLISH_TURN'"),('word-tree.wav',"state.status.app.speech.includes('tree')"),('arrive.wav',"state.status.app.memoryCount>0"),('growth-records.wav',"state.status.app.panel==='GROWTH'")]:
   ready();raw=base64.b64encode((ROOT/'qa/native/fixtures'/name).read_bytes()).decode();v.evaluate('''async data=>{const a=Uint8Array.from(atob(data),c=>c.charCodeAt(0));const audio=await ctx.decodeAudioData(a.buffer);const s=ctx.createBufferSource();s.buffer=audio;s.connect(filter);s.start();await new Promise(r=>s.onended=r)}''',raw);v.wait_for_function(predicate,timeout=20000);metrics.setdefault('actualTasks',[]).append(name);print('CAPTURE',name,flush=True)
  ready();duration=v.evaluate('(performance.now()-qaStarted)/1000');receipts=v.evaluate('qaReceipts');encoded=v.evaluate('''async()=>{clearInterval(qaCaptionTimer);await new Promise(r=>{qaRecorder.onstop=r;qaRecorder.stop()});const blob=new Blob(qaMediaChunks,{type:'video/webm'});return new Promise(r=>{const reader=new FileReader();reader.onloadend=()=>r(reader.result.split(',')[1]);reader.readAsDataURL(blob)})}''');raw=ROOT/'.tools/exec-evidence/current-preview.webm';raw.write_bytes(base64.b64decode(encoded))
  payload={'apkSha256':record.manifest['apkSha256'],'rawPath':str(raw.relative_to(ROOT)),'rawSha256':sha(raw),'durationSeconds':duration,'receipts':receipts,'tasks':metrics['actualTasks']};(record.dir/'recording.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
  # Encoding owns no microphone or browser lease. Release them before CPU work;
  # the 180-second public consent limit remains unchanged.
  v.locator('#disconnect').click();v.wait_for_function('!state.token&&!state.ending',timeout=20000);c.close();b.close()
  if args.scope!='record':finish_recording(payload)
  else:
   checks['allRecordedTasksCompleted']=len(payload['tasks'])==8;checks['actualSpokenReceiptsCaptioned']=len(payload['receipts'])>=8;checks['currentApkRecorded']=payload['apkSha256']==record.manifest['apkSha256']
 except Exception:
  if b.is_connected()and not v.is_closed():
   observed=v.evaluate('state.status');record.diagnostic(observed,'capture-failure');a=observed.get('app',{});metrics['lastObserved']={k:a.get(k)for k in ['sessionStatus','phase','recognition','playback','heard','title','tripActive','memoryCount','error']}
  raise
 finally:
  try:
   if b.is_connected()and not v.is_closed()and v.evaluate('!!state.token'):v.locator('#disconnect').click();v.wait_for_function('!state.token&&!state.ending',timeout=20000)
  except Exception as error:metrics['browserCleanupError']=type(error).__name__
  finally:
   if b.is_connected():b.close()
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
