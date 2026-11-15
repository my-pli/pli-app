'use strict';
const $=id=>document.getElementById(id);
const state={route:location.pathname,surface:location.pathname==='/pleos'?'pleos':'app',status:{},token:null,media:'CONNECTING',voice:false,connecting:false,ending:false,muted:false,lastFrame:0,lastStamp:null,videoEpoch:0,voiceEpoch:0,previewInfo:null};
let socket,mediaSource,sourceBuffer,objectUrl,appendQueue=[],frameStamps=[],fallbackTimer,frameTimer,toastTimer;
let voiceSocket,ctx,mic,source,duplex,filter,controlSocket,inputSeq=0;
function acceptAppSnapshot(next){const current=state.status.app;if(!next||current?.bootId===next.bootId&&next.stateRevision<current.stateRevision)return;state.status.app=next;render();}
function connectControl(){
 controlSocket?.close();if(!state.token)return;
 const token=state.token,ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/control`);controlSocket=ws;
 ws.onopen=()=>ws.send(JSON.stringify({sessionToken:token}));ws.onmessage=({data})=>{const m=JSON.parse(data);if(m.type==='error')toast(m.message);};ws.onclose=()=>{if(controlSocket===ws)controlSocket=null;};
}
function deadline(ms){if(AbortSignal.timeout)return AbortSignal.timeout(ms);const c=new AbortController();setTimeout(()=>c.abort(),ms);return c.signal;}
const paths=new Set(['/','/app','/pleos','/resources']);
const errorText=e=>({NotAllowedError:'마이크 사용이 허용되지 않았어요. 주소창의 사이트 권한에서 허용한 뒤 다시 시작해 주세요.',NotFoundError:'마이크를 찾지 못했어요. 입력 장치를 확인해 주세요.',NotReadableError:'다른 앱에서 마이크를 사용 중인지 확인해 주세요.'}[e.name]||e.message||'연결을 확인한 뒤 다시 시도해 주세요.');
function toast(message){clearTimeout(toastTimer);$('toast').textContent=message;$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,4500);}
async function post(path,body={},timeout=25000,token=state.token){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json',...(token?{'X-Pli-Session':token}:{})},body:JSON.stringify(body),signal:deadline(timeout)});if(!r.ok){let message;try{message=(await r.json()).message;}catch{}throw Error(message||(r.status===423?'다른 분이 체험 중이에요. 잠시 뒤 다시 시작해 주세요.':r.status===503?'시연 환경을 다시 연결하고 있어요. 잠시 기다려 주세요.':'요청을 확인하지 못했어요. 다시 시도해 주세요.'));}return r.json();}
function owned(){return !!state.token&&!!state.status.lease?.mine;}
function fresh(){return state.media==='LIVE'&&performance.now()-state.lastFrame<850;}
function note(text){if($('voice-note').textContent!==text)$('voice-note').textContent=text;}
function overlay(title,detail,spinning=false){$('picture-message').hidden=false;if($('loading-title').textContent!==title)$('loading-title').textContent=title;if($('loading-detail').textContent!==detail)$('loading-detail').textContent=detail;$('loading-spinner').hidden=!spinning;}
function render(){
 const os=state.surface==='pleos',recording=state.media==='RECORDING';
 document.body.classList.toggle('surface-pleos',os);document.body.classList.toggle('route-experience',['/app','/pleos'].includes(state.route));
 $('home-view').hidden=state.route!=='/';$('resources-view').hidden=state.route!=='/resources';$('experience-view').hidden=!['/app','/pleos'].includes(state.route);
 document.querySelectorAll('nav [data-route]').forEach(a=>{a.classList.toggle('active',a.getAttribute('href')===state.route);a.setAttribute('aria-current',a.classList.contains('active')?'page':'false');});
 $('page-kicker').textContent=os?'PLEOS SIMULATOR':'VOICE EXPERIENCE';$('page-title').textContent=os?'Pleos 전체를, 직접 바꿔보세요.':'목소리로, 함께 가는 길.';$('page-description').textContent=os?'마이크 없이 화면을 누르고, 차량 조건을 바꿔보세요.':'아이의 놀이와 부모의 하루를 함께 잇습니다.';
 $('switch-experience').href=os?'/app':'/pleos';$('switch-experience').textContent=os?'앱 음성 체험하기 ↗':'전체 Pleos 조작하기 ↗';
 $('live-label').textContent=recording?(state.previewInfo?.type==='product-story'?'플리 제품 소개 영상':'실제 앱 녹화 영상'):os?'Pleos 전체 화면':'플리 앱 화면';
 const me=owned(),busy=state.status.lease?.busy&&!me;
 $('connection').textContent=recording?'소개 영상 재생':fresh()?(me?'직접 체험 중':'실시간 관람 중'):state.media==='CONNECTING'?'화면 연결 중':'화면 확인 필요';
 $('status-dot').className=fresh()?'ready':recording?'':'warn';
 $('connect').hidden=os;$('claim-control').hidden=!os;
 const disabled=!fresh()||!state.status.controlReady||busy||state.connecting||state.ending;
 $('connect').disabled=disabled;$('claim-control').disabled=disabled;
 $('film-return').hidden=!recording;$('before-session').hidden=recording||me&&!state.connecting;$('active-session').hidden=recording||!me||state.connecting;
 $('cancel-connect').hidden=!state.connecting;$('connect').textContent=state.connecting?'목소리 연결 중…':'목소리로 시작하기 ↗';
 $('remaining').hidden=!me;const sec=state.status.lease?.seconds||0;$('remaining').textContent=`${String(Math.floor(sec/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`;
 $('busy-note').hidden=!busy;$('busy-note').textContent=`다른 분이 체험 중이에요. 약 ${state.status.lease?.seconds||0}초 뒤 시작할 수 있어요. 지금은 화면과 영상을 볼 수 있습니다.`;
 $('session-kicker').textContent=os?'YOU ARE IN THE DRIVER’S SEAT':'VOICE COMPANION';
 $('voice-examples').hidden=os||recording;$('vehicle-panel').hidden=!os||recording;$('watch').hidden=recording||!state.previewInfo?.available;
 document.querySelectorAll('[data-vehicle],[data-key],#open-app').forEach(b=>b.disabled=!me||!fresh()||state.ending||recording);
 $('picture').classList.toggle('controlled',os&&me&&fresh()&&!recording);$('control-hint').hidden=!(os&&me&&fresh()&&!recording);
 const app=state.status.app||{};
 $('vehicle-state').textContent=app.gear?`${app.gear} · ${app.speedKmh??'—'}km/h`:'신호 확인 중';document.querySelectorAll('[data-vehicle="park"],[data-vehicle="drive"]').forEach(b=>b.classList.toggle('selected',b.dataset.vehicle===(app.gear==='P'?'park':app.gear==='D'?'drive':'')));
 $('resume-audio').hidden=!(state.voice&&ctx&&ctx.state!=='running');$('mute').hidden=!state.voice;$('mute').textContent=state.muted?'내 목소리 보내기':'내 목소리 음소거';$('voice-toggle').hidden=!os;$('voice-toggle').textContent=state.voice?'목소리 끄기':'목소리도 켜기';
 $('voice-led').classList.toggle('on',state.voice&&!state.muted);
 let phase=state.voice?'듣는 중':'목소리 꺼짐',prompt=os?'차 안의 모든 순간을.':'플리에게 말해 보세요.',detail=os?'직접 조작하기를 누르면 화면을 누를 수 있어요.':'마이크를 켠 뒤 듣는 중 안내가 나오면 질문하세요.',say='“오늘 준비물 알려줘”';
 if(state.connecting){phase='연결 준비 중';prompt='목소리를 연결하고 있어요.';detail='마이크와 음성 엔진의 실제 준비를 확인합니다.';}
 else if(state.voice){
  if(ctx&&ctx.state!=='running'){phase='소리 연결 일시 정지';prompt='소리 연결을 다시 켜 주세요.';detail='소리 연결 다시 켜기를 누르면 목소리 체험을 이어갑니다.';}
  else if(app.sessionStatus!=='ACTIVE'){phase='연결 준비 중';prompt='음성 엔진의 준비를 확인해요.';detail='준비가 끝나면 플리가 먼저 인사해요.';}
  else if(state.muted){phase='내 목소리 음소거';prompt='목소리 전송을 멈췄어요.';detail='플리의 목소리는 계속 들을 수 있어요.';}
  else if(app.quiet){phase='조용히 기다리는 중';prompt='잠깐 쉬어도 괜찮아요.';say='“다시 시작해”';detail='다시 이야기하고 싶을 때 말해 주세요.';}
  else if(app.phase==='NAVIGATION'){phase='길 안내를 듣는 중';prompt='길 안내를 먼저 들을게요.';detail='안내가 끝나면 대화를 이어갑니다.';}
  else if(['QUEUED','STARTING','WAITING_FOR_FOCUS'].includes(app.playback)){phase='답변 준비 중';prompt='플리가 답변을 준비하고 있어요.';detail='목소리가 들리면 이어서 대화해 주세요.';}
  else if(app.playback==='PLAYING'){phase='플리가 말하는 중';prompt='플리의 말을 들어보세요.';detail='말을 마치면 이어서 질문하거나 답해 주세요.';}
  else if(app.recognition!=='READY'){phase='입력 준비 중';prompt='다음 질문을 준비하고 있어요.';detail='듣는 중 안내가 나오면 말해 주세요.';}
  else{prompt='지금, 플리가 듣고 있어요.';detail='부모의 질문도 아이의 놀이도 목소리로 전환해요.';}
  if(app.panel==='ENGLISH_TURN')say='“나무는 영어로 뭐게?”';else if(app.panel==='DESTINATIONS')say=app.title?.includes('보호자 확인')?'“보호자 확인”':'“첫 번째로 갈래”';else if(app.game==='MATH'||app.game==='NATURE'||app.game==='ENGLISH')say='문제의 답 · “힌트 줘” · “다음 문제”';else if(app.audience==='PARENT')say='“내일 준비물 있어?” · “최근 알림장 읽어줘”';
 }
 if(me&&!state.voice&&!state.connecting&&os){prompt='내가 바꾸는 Pleos.';detail='차량 조건, Home, 앱 전환을 직접 사용해 보세요.';}
 if(state.ending){prompt='체험 종료를 확인하고 있어요.';detail='마이크·소리·조작권 정리가 끝나면 다시 시작할 수 있어요.';}
 if(recording){prompt='함께 가는 길이 달라져요.';const length=Math.round(state.previewInfo?.durationSeconds||0);detail=(length?length+'초 ':'')+'소개 영상을 본 뒤, 플리를 직접 만나보세요.';$('session-kicker').textContent='MEET PLI';}
 $('phase-label').textContent=phase;$('prompt-title').textContent=prompt;$('prompt-detail').textContent=detail;$('say-this').textContent=say;
 $('caption-label').textContent=recording?'영상 안내':state.voice&&app.playback==='PLAYING'?'플리의 말':os?'Pleos 직접 체험':'함께 시작해요';
 $('caption-text').textContent=recording?'가족 장면은 영상 AI가 화면과 목소리를 함께 만들었고, 기능 장면은 그 목소리를 플리 앱이 실제로 듣고 답한 화면과 음성이에요. 직접 체험으로 돌아가 플리와 이야기해 보세요.':state.voice&&app.speech?app.speech:os?'전체 OS를 그대로 보여줍니다. 조작은 “직접 조작하기”로 시작하세요.':'“오늘 준비물 알려줘” 또는 “숫자 놀이 해줘”라고 말해 보세요.';
 syncDock();renderAgent();
}
async function navigate(path,push=true){
 if(!paths.has(path))path='/';const next=path==='/pleos'?'pleos':'app',changed=next!==state.surface;
 if(state.token&&!['/app','/pleos'].includes(path)){endSession();}
 else if(state.token&&changed){try{await post('/api/session/surface',{surface:next});}catch(e){toast(errorText(e));}}
 state.route=path;state.surface=next;if(push)history.pushState({},'',path);document.title=path==='/pleos'?'Pleos 시뮬레이터 · 플리':path==='/resources'?'플리 소개 · APK':'플리 · 함께 가는 길';
 stopVideo();$('recording-end').hidden=true;$('preview').pause();$('preview').hidden=true;$('recording-banner').hidden=true;
 if(path==='/resources')loadResources();else if(path!=='/')startVideo();render();window.scrollTo({top:0,behavior:'instant'});
}
document.addEventListener('click',e=>{const a=e.target.closest('a[data-route]');if(!a||e.metaKey||e.ctrlKey||e.shiftKey||e.button!==0)return;e.preventDefault();navigate(new URL(a.href).pathname);});window.addEventListener('popstate',()=>navigate(location.pathname,false));
function stopVideo(){state.videoEpoch++;socket?.close();socket=null;clearTimeout(fallbackTimer);clearTimeout(frameTimer);$('live-video').pause();$('live-video').hidden=true;$('screen').hidden=true;if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;sourceBuffer=null;mediaSource=null;appendQueue=[];frameStamps=[];state.lastFrame=0;state.lastStamp=null;}
function displayed(stamp){if(!stamp)return;const alreadyLive=state.media==='LIVE';if(pollFailures>=3){state.lastFrame=performance.now();state.lastStamp=stamp;return;}state.lastFrame=performance.now();state.lastStamp=stamp;state.media='LIVE';if(!alreadyLive){$('picture-message').hidden=true;render();}}
const arrivals=[];function noteArrival(m){if(typeof m.encoderPtsUs!=='number')return;arrivals.push(performance.now()/1000-m.encoderPtsUs/1e6);if(arrivals.length>120)arrivals.shift();}
function jitterTarget(){if(arrivals.length<20)return .22;const s=[...arrivals].sort((a,b)=>a-b);return Math.min(.6,Math.max(.12,s[Math.floor(s.length*.92)]-s[0]+.06));}
function flushMedia(){
 const sb=sourceBuffer,v=$('live-video');if(!sb||sb.updating||!mediaSource||mediaSource.readyState!=='open')return;
 try{
  if(v.buffered.length){const start=v.buffered.start(0),end=v.buffered.end(v.buffered.length-1),lag=end-v.currentTime,target=jitterTarget();if(!v.seeking&&(v.currentTime<start||lag>Math.max(1.2,target*4)))v.currentTime=Math.max(start,end-target);else if(!v.seeking){const rate=lag>target+.3?1.08:lag>target+.1?1.03:lag<target*.4?.95:lag<target*.75?.98:1;if(v.playbackRate!==rate)v.playbackRate=rate;}if(v.currentTime>4&&start<v.currentTime-3){sb.remove(start,v.currentTime-2);return;}}
  if(appendQueue.length)sb.appendBuffer(appendQueue.shift());
 }catch(e){mediaFailure('영상 표시를 다시 연결하고 있어요.');}
}
function setupMedia(meta,epoch){
 if(objectUrl)URL.revokeObjectURL(objectUrl);sourceBuffer=null;appendQueue=[];frameStamps=[];arrivals.length=0;
 mediaSource=new MediaSource();objectUrl=URL.createObjectURL(mediaSource);const v=$('live-video');v.playbackRate=1;v.src=objectUrl;v.hidden=false;$('screen').hidden=true;
 mediaSource.addEventListener('sourceopen',()=>{if(epoch!==state.videoEpoch)return;try{sourceBuffer=mediaSource.addSourceBuffer(meta.mime||'video/mp4; codecs="avc1.42c01f"');sourceBuffer.addEventListener('updateend',flushMedia);flushMedia();v.play().catch(()=>{$('loading-title').textContent='화면 재생을 눌러 주세요.';});}catch{startFallback(epoch);}});
 function frame(now,info){if(epoch!==state.videoEpoch||state.media==='RECORDING')return;const pts=info.mediaTime*1e6;let best=frameStamps[0];for(const stamp of frameStamps){if(stamp.encoderPtsUs<=pts+20000)best=stamp;else break;}displayed(best);v.requestVideoFrameCallback(frame);}
 if(v.requestVideoFrameCallback)v.requestVideoFrameCallback(frame);else v.ontimeupdate=()=>{if(epoch===state.videoEpoch)displayed(frameStamps[frameStamps.length-1]);};
}
function mediaFailure(title){if(state.status.viewerCapacity?.current>=12)title='관람 연결이 가득 찼어요. 영상으로 먼저 만나보세요.';if(state.media==='RECORDING')return;state.media='STALE';overlay(title,'조작을 잠시 멈췄어요. 다시 연결하거나 녹화 영상을 볼 수 있습니다.');render();}
function startVideo(){
 stopVideo();const epoch=state.videoEpoch;state.media='CONNECTING';overlay('실제 화면을 연결하고 있어요.','공개 시연용 Pleos에 연결합니다.',true);render();
 frameTimer=setTimeout(()=>{if(epoch===state.videoEpoch&&!state.lastFrame)mediaFailure('화면을 아직 받지 못했어요.');},3000);
 if(!window.MediaSource||!MediaSource.isTypeSupported('video/mp4; codecs="avc1.42c01f"')){startFallback(epoch);return;}
 let meta;
 socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/video?surface=${state.surface}`);socket.binaryType='arraybuffer';
 socket.onmessage=({data})=>{
  if(epoch!==state.videoEpoch)return;
  if(typeof data==='string'){const m=JSON.parse(data);meta=m;if(m.type==='init')setupMedia(m,epoch);else if(m.type==='frame'){noteArrival(m);frameStamps.push(m);if(frameStamps.length>150)frameStamps.shift();}else if(m.type==='error'){mediaFailure('화면 연결을 확인해 주세요.');}return;}
  if(appendQueue.length>30){mediaFailure('네트워크가 느려 화면을 다시 맞추고 있어요.');socket.close();return;}appendQueue.push(data);flushMedia();
 };
 socket.onerror=()=>socket?.close();socket.onclose=()=>{if(epoch!==state.videoEpoch||state.media==='RECORDING')return;mediaFailure(state.lastFrame?'화면 연결이 끊겼어요.':'첫 화면을 받지 못했어요. 다시 연결하거나 영상을 볼 수 있습니다.');fallbackTimer=setTimeout(()=>{if(epoch===state.videoEpoch)startVideo();},1800);};
}
async function startFallback(epoch){
 socket?.close();socket=null;clearTimeout(fallbackTimer);$('live-video').hidden=true;$('screen').hidden=false;
 async function next(){if(epoch!==state.videoEpoch||state.media==='RECORDING')return;try{const r=await fetch('/snapshot?surface='+state.surface,{signal:deadline(4000),cache:'no-store'});if(!r.ok)throw Error();const stamp=JSON.parse(r.headers.get('X-Pli-Frame'));const bitmap=await createImageBitmap(await r.blob());const canvas=$('screen');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();displayed(stamp);$('connection').textContent='실시간 · 호환 모드';}catch{mediaFailure('화면을 받지 못했어요.');}if(epoch===state.videoEpoch)fallbackTimer=setTimeout(next,150);}
 next();
}
async function claim(){try{const r=await post('/api/session/claim',{surface:state.surface});state.token=r.sessionToken;connectControl();await poll();render();}catch(e){toast(errorText(e));}}
$('claim-control').onclick=claim;
let pollBusy=false,pollFailures=0;
async function poll(){if(pollBusy)return;pollBusy=true;try{const r=await fetch('/api/status',{headers:state.token?{'X-Pli-Session':state.token}:{},signal:deadline(3500),cache:'no-store'});if(!r.ok)throw Error();const next=await r.json();if(next.app?.bootId===state.status.app?.bootId&&next.app?.stateRevision<state.status.app?.stateRevision)next.app=state.status.app;state.status=next;pollFailures=0;if(state.token&&!state.status.lease?.mine&&!state.connecting&&!state.ending){await cleanupAudio();state.token=null;note('체험을 마쳤어요. 다시 시작할 수 있습니다.');}if(state.ending&&!state.status.lease?.busy){state.ending=false;state.token=null;}render();}catch{pollFailures++;if(pollFailures>=3){state.status.controlReady=false;mediaFailure('서버 연결을 확인해 주세요.');}}finally{pollBusy=false;}}
async function cleanupAudio(){state.voiceEpoch++;state.voice=false;state.connecting=false;const old=voiceSocket;voiceSocket=null;old?.close();mic?.getTracks().forEach(t=>t.stop());mic=null;source?.disconnect();filter?.disconnect();duplex?.disconnect();source=filter=duplex=null;const oldCtx=ctx;ctx=null;if(oldCtx)await oldCtx.close().catch(()=>{});state.muted=false;}
async function connectVoice(){
 if(state.connecting||state.voice)return;
 if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia||!window.AudioWorkletNode||!window.AudioContext){note('마이크 체험은 최신 브라우저의 HTTPS 주소에서 열어 주세요. Pleos 조작과 영상 관람은 계속 사용할 수 있어요.');return;}
 const epoch=++state.voiceEpoch;state.connecting=true;render();note('마이크 사용을 허용해 주세요.');let acquired,localContext;
 try{
  localContext=new AudioContext({sampleRate:48000,latencyHint:'interactive'});ctx=localContext;localContext.onstatechange=()=>{if(ctx===localContext)render();};await localContext.resume();acquired=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:false,autoGainControl:false},video:false});
  if(epoch!==state.voiceEpoch){acquired.getTracks().forEach(t=>t.stop());await localContext.close().catch(()=>{});return;}mic=acquired;
  if(localContext.sampleRate!==48000)throw Error('이 브라우저의 마이크 형식을 지원하지 않아요. Chrome 또는 Edge에서 열어 주세요.');
  if(!state.token){const r=await post('/api/session/claim',{surface:state.surface});if(epoch!==state.voiceEpoch){acquired.getTracks().forEach(t=>t.stop());await localContext.close().catch(()=>{});await post('/api/session/end',{sessionToken:r.sessionToken},12000,r.sessionToken).catch(()=>{});return;}state.token=r.sessionToken;connectControl();}
  if(state.media==='RECORDING'){$('preview').pause();$('preview').hidden=true;$('recording-banner').hidden=true;startVideo();}
  const preparing=post('/api/session/prepare');
  const connecting=(async()=>{
  await localContext.audioWorklet.addModule('/audio-worklet.js?v=5fbc1b983d28');if(epoch!==state.voiceEpoch)return null;
  duplex=new AudioWorkletNode(localContext,'pli-duplex',{numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1],processorOptions:{wireRate:24000}});source=localContext.createMediaStreamSource(acquired);filter=localContext.createBiquadFilter();filter.type='lowpass';filter.frequency.value=10000;filter.Q.value=.707;
  const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/voice?rate=24000`);voiceSocket=ws;ws.binaryType='arraybuffer';
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('목소리 연결 시간이 길어지고 있어요. 다시 시작해 주세요.')),14000);ws.onopen=()=>ws.send(JSON.stringify({sessionToken:state.token}));ws.onmessage=({data})=>{if(epoch!==state.voiceEpoch)return;if(typeof data!=='string'){duplex?.port.postMessage(data,[data]);return;}const m=JSON.parse(data);if(m.type==='app-state'){acceptAppSnapshot(m.app);return;}if(m.type==='ready'){clearTimeout(timer);resolve();}else if(m.type==='error'){clearTimeout(timer);reject(Error(m.message));}};ws.onerror=()=>{clearTimeout(timer);reject(Error('목소리 연결을 열지 못했어요.'));};ws.onclose=()=>{clearTimeout(timer);reject(Error('목소리 연결이 끊겼어요.'));};});
  return ws;})();
  const [prepared,ws]=await Promise.all([preparing,connecting]);if(epoch!==state.voiceEpoch||!ws)return;acceptAppSnapshot(prepared.app);
  if(epoch!==state.voiceEpoch)return;duplex.port.onmessage=({data})=>{if(epoch===state.voiceEpoch&&ws.readyState===WebSocket.OPEN&&ws.bufferedAmount<48000)ws.send(data);};source.connect(filter);filter.connect(duplex);duplex.connect(localContext.destination);
  state.voice=true;state.connecting=false;ws.onclose=()=>{if(voiceSocket===ws)stopVoice('목소리 연결을 마쳤어요.');};ws.onerror=()=>ws.close();await post('/api/session/begin');note('플리가 말을 마치면 질문하거나 답해 주세요. 이어폰을 권장합니다.');await poll();render();
 }catch(e){if(epoch===state.voiceEpoch)await stopVoice(errorText(e));else{acquired?.getTracks().forEach(t=>t.stop());await localContext?.close().catch(()=>{});}}
}
async function stopVoice(message='마이크와 소리를 껐어요.'){await cleanupAudio();if(state.token){try{await post('/api/session/voice-end',{},10000);if(state.surface==='app')state.token=null;}catch(e){note('목소리 종료 상태를 확인하고 있어요.');}}note(message);await poll();render();}
async function endSession(){if(state.ending)return;state.ending=true;controlSocket?.close();controlSocket=null;render();await cleanupAudio();if(state.token){try{const r=await post('/api/session/end',{sessionToken:state.token},12000);if(r.status==='STOPPED'){state.token=null;state.ending=false;note('체험을 마쳤어요. 마이크와 조작 연결을 해제했습니다.');}}catch(e){note('종료를 확인하지 못했어요. 기기 정리 후 다시 시작할 수 있습니다.');}}else state.ending=false;await poll();render();}
$('connect').onclick=connectVoice;$('voice-toggle').onclick=()=>state.voice?stopVoice():connectVoice();$('disconnect').onclick=endSession;$('cancel-connect').onclick=()=>state.surface==='pleos'?stopVoice('연결을 취소했어요.'):endSession();
$('mute').onclick=()=>{state.muted=!state.muted;duplex?.port.postMessage({type:'mute',value:state.muted});note(state.muted?'내 목소리 전송만 멈췄어요. 플리의 목소리는 계속 들립니다.':'내 목소리 전송을 다시 시작했어요.');render();};
async function watch(){if(!state.previewInfo?.available){toast('소개 영상을 준비하고 있어요.');return;}$('recording-end').hidden=true;if(state.token||state.voice||state.connecting){await endSession();if(state.token||state.ending){toast('체험 종료를 확인한 뒤 영상을 열 수 있어요.');return;}}stopVideo();state.media='RECORDING';$('picture-message').hidden=true;$('recording-banner').hidden=false;const info=state.previewInfo||{};$('recording-identity').textContent=info.type==='product-story'?'AI 제품 소개 영상':info.current?'녹화 영상 · 현재 검토본':'이전 버전 녹화 · 실제 앱';$('preview').src='/preview.mp4?v='+(info.videoSha256||'recording');$('preview-captions').src=info.subtitles||'';for(const track of $('preview').textTracks)track.mode='disabled';$('show-transcript').hidden=!info.transcript;$('preview').hidden=false;render();try{await $('preview').play();}catch{toast('영상의 재생 버튼을 눌러 주세요.');}}
$('resume-audio').onclick=async()=>{try{await ctx?.resume();render();}catch{note('소리를 연결하지 못했어요. 체험을 마친 뒤 다시 연결해 주세요.');}};
$('film-return').onclick=()=>$('return-live').click();$('watch').onclick=watch;$('fallback-watch').onclick=watch;$('end-return-live').onclick=()=>$('return-live').click();$('replay-recording').onclick=()=>{$('recording-end').hidden=true;$('preview').currentTime=0;$('preview').play().catch(()=>{});};$('return-live').onclick=()=>{$('recording-end').hidden=true;$('preview').pause();$('preview').hidden=true;$('recording-banner').hidden=true;startVideo();};$('preview').onended=()=>{$('recording-end').hidden=false;};$('preview').onerror=()=>toast('영상을 불러오지 못했어요. 실시간 화면으로 돌아가 다시 연결해 주세요.');$('retry-video').onclick=startVideo;
$('show-transcript').onclick=async()=>{const section=$('transcript');section.hidden=!section.hidden;if(!section.hidden&&state.previewInfo?.transcript){const r=await fetch(state.previewInfo.transcript);$('transcript-content').textContent=await r.text();}};

function renderAgent(){
 const stepNodes=window.__pliStepNodes||(window.__pliStepNodes=new Map());const app=state.status.app||{},steps=Array.isArray(app.agentSteps)?app.agentSteps:[],panel=$('agent-panel');
 const show=state.surface==='app'&&state.media!=='RECORDING'&&steps.length>0;panel.hidden=!show;if(!show)return;
 const list=$('agent-steps'),ids=new Set(steps.map(s=>s.id));
 for(const [id,node]of stepNodes)if(!ids.has(id)){node.remove();stepNodes.delete(id);}
 for(const s of steps){let li=stepNodes.get(s.id);if(!li){li=document.createElement('li');li.append(document.createElement('i'),document.createElement('div'));stepNodes.set(s.id,li);}
  li.className=s.state==='running'?'running':s.state==='fail'?'fail':'';const body=li.lastChild;body.textContent=s.label;if(s.detail){const small=document.createElement('small');small.textContent=s.detail;body.append(small);}list.append(li);}
 $('agent-latency').textContent=app.agentBusy?'생각하는 중':Math.max(0,...steps.map(s=>s.ms||0))+'ms';
 const edge=app.edge||{},chips=$('edge-chips');chips.replaceChildren();
 for(const label of [edge.asr?'음성인식 '+edge.asr:null,edge.llm?'LLM '+edge.llm:null,edge.healthy?'엣지 연결됨':null,edge.albumPhotos?'가족 사진 '+edge.albumPhotos+'장':null].filter(Boolean)){const c=document.createElement('span');c.textContent=label;chips.append(c);}
}
if('IntersectionObserver'in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('shown');io.unobserve(e.target);}}),{threshold:.12});document.querySelectorAll('.journey,.resource-grid').forEach(n=>{n.classList.add('reveal');io.observe(n);});}
const immersiveOn=()=>document.body.classList.contains('immersive');let dockTimer=0;
function wakeDock(){const d=$('immersive-dock');d.classList.remove('idle');clearTimeout(dockTimer);dockTimer=setTimeout(()=>{if(immersiveOn()&&$('dock-vehicle-menu').hidden&&!d.matches(':hover,:focus-within'))d.classList.add('idle');},3400);}
async function setImmersive(on){
 const stage=document.querySelector('.stage');document.body.classList.toggle('immersive',on);$('fullscreen').setAttribute('aria-pressed',String(on));$('fullscreen').title=on?'전체 화면 나가기 (Esc)':'전체 화면 (F)';
 if(on){const request=stage.requestFullscreen||stage.webkitRequestFullscreen;try{if(request&&!document.fullscreenElement&&!document.webkitFullscreenElement)await request.call(stage,{navigationUI:'hide'});}catch{}try{await screen.orientation?.lock?.('landscape');}catch{}wakeDock();}
 else{$('dock-vehicle-menu').hidden=true;try{if(document.fullscreenElement)await document.exitFullscreen();else if(document.webkitFullscreenElement)document.webkitExitFullscreen();}catch{}try{screen.orientation?.unlock?.();}catch{}}
 render();
}
$('fullscreen').onclick=()=>setImmersive(!immersiveOn());$('dock-exit').onclick=()=>setImmersive(false);
for(const name of ['fullscreenchange','webkitfullscreenchange'])document.addEventListener(name,()=>{if(!document.fullscreenElement&&!document.webkitFullscreenElement&&immersiveOn()&&document.querySelector('.stage').requestFullscreen)setImmersive(false);});
document.addEventListener('keydown',e=>{if(e.target.closest?.('input,textarea,select'))return;if(e.key==='Escape'&&immersiveOn())setImmersive(false);else if((e.key==='f'||e.key==='F')&&!e.metaKey&&!e.ctrlKey&&['/app','/pleos'].includes(state.route))setImmersive(!immersiveOn());});
for(const name of ['pointermove','pointerdown'])document.querySelector('.stage').addEventListener(name,()=>{if(immersiveOn())wakeDock();},{passive:true});
document.querySelectorAll('[data-proxy]').forEach(b=>b.onclick=()=>{$(b.dataset.proxy).click();wakeDock();});
document.querySelectorAll('[data-proxy-key]').forEach(b=>b.onclick=()=>{document.querySelector(`[data-key="${b.dataset.proxyKey}"]`).click();wakeDock();});
document.querySelectorAll('[data-proxy-vehicle]').forEach(b=>b.onclick=()=>{document.querySelector(`[data-vehicle="${b.dataset.proxyVehicle}"]`).click();wakeDock();});
$('dock-vehicle').onclick=()=>{const m=$('dock-vehicle-menu');m.hidden=!m.hidden;$('dock-vehicle').setAttribute('aria-expanded',String(!m.hidden));wakeDock();};
function syncDock(){
 const os=state.surface==='pleos';document.querySelector('[data-dock="pleos"]').hidden=!os;document.querySelector('[data-dock="app"]').hidden=os;
 document.querySelectorAll('[data-proxy]').forEach(b=>{const src=$(b.dataset.proxy);const hidden=src.hidden||!!src.closest('[hidden]');b.hidden=hidden;b.disabled=src.disabled;const label=src.textContent.replace(/[↗→]/g,'').trim();if(label&&b.textContent!==label)b.textContent=label;});
 document.querySelectorAll('[data-proxy-key]').forEach(b=>{const src=document.querySelector(`[data-key="${b.dataset.proxyKey}"]`);b.disabled=src.disabled;});
 document.querySelectorAll('[data-proxy-vehicle]').forEach(b=>{const src=document.querySelector(`[data-vehicle="${b.dataset.proxyVehicle}"]`);b.disabled=src.disabled;b.classList.toggle('selected',src.classList.contains('selected'));});
 $('dock-vehicle').disabled=document.querySelector('[data-vehicle="park"]').disabled;if($('dock-vehicle').disabled)$('dock-vehicle-menu').hidden=true;
}
document.querySelectorAll('[data-vehicle]').forEach(b=>b.onclick=async()=>{b.disabled=true;$('vehicle-status').textContent='차량에 적용하고 있어요…';try{await post('/api/vehicle',{action:b.dataset.vehicle});$('vehicle-status').textContent=`${b.textContent.trim()} · 실제 신호를 확인했어요.${state.voice&&state.status.app?.question?' 대화와 놀이에 맞춰 음성 안내를 조절해요.':''}`;}catch(e){$('vehicle-status').textContent=errorText(e);}finally{await poll();}});
document.querySelectorAll('[data-key]').forEach(b=>b.onclick=()=>post('/api/input',{type:'key',key:b.dataset.key}).catch(e=>toast(errorText(e))));$('open-app').onclick=()=>post('/api/input',{type:'open_app'}).catch(e=>toast(errorText(e)));
const pendingPointers=new Map();let moveAt=0;
function point(e){const element=$('screen').hidden?$('live-video'):$('screen');const rect=element.getBoundingClientRect();const stamp=state.lastStamp;if(!stamp)return null;const scale=Math.min(rect.width/stamp.width,rect.height/stamp.height),w=stamp.width*scale,h=stamp.height*scale;const x=(e.clientX-rect.x-(rect.width-w)/2)/w,y=(e.clientY-rect.y-(rect.height-h)/2)/h;return x>=0&&x<=1&&y>=0&&y<=1?{x,y}:null;}
function sendPointer(payload){if(controlSocket?.readyState===WebSocket.OPEN){controlSocket.send(JSON.stringify({...payload,inputSeq:++inputSeq}));}else if(payload.phase!=='move'){post('/api/input',payload,3000).catch(e=>toast(errorText(e)));}}
function pointer(e,phase){
 const finishing=phase==='up'||phase==='cancel';
 if(state.surface!=='pleos'||!owned()||(!finishing&&!fresh())||state.media==='RECORDING')return;
 if(phase==='down'&&pendingPointers.size)return;
 const p=point(e)||(finishing?pendingPointers.get(e.pointerId):null);if(!p)return;
 if(phase==='down'){e.preventDefault();$('picture').setPointerCapture(e.pointerId);pendingPointers.set(e.pointerId,p);}
 else if(!pendingPointers.has(e.pointerId))return;
 if(phase==='move'){if(performance.now()-moveAt<35)return;moveAt=performance.now();pendingPointers.set(e.pointerId,p);}
 if(finishing)pendingPointers.delete(e.pointerId);
 sendPointer({type:'pointer',phase,pointerId:0,geometryRevision:state.lastStamp.geometryRevision,streamGeneration:state.lastStamp.generation,lastDepictedSourceSeq:state.lastStamp.sourceSeq,...p});
}
$('picture').addEventListener('pointerdown',e=>pointer(e,'down'));$('picture').addEventListener('pointermove',e=>pointer(e,'move'));$('picture').addEventListener('pointerup',e=>pointer(e,'up'));$('picture').addEventListener('pointercancel',e=>pointer(e,'cancel'));
window.addEventListener('blur',()=>{for(const [id,p]of pendingPointers){sendPointer({type:'pointer',phase:'cancel',pointerId:0,geometryRevision:state.lastStamp?.geometryRevision,...p});}pendingPointers.clear();});
async function loadResources(){try{const r=await fetch('/api/resources');const items=await r.json();const container=$('resources-list');container.replaceChildren();for(const item of items){const card=document.createElement('article');card.className='resource-card';const badge=document.createElement('span');badge.textContent=item.status;const title=document.createElement('h2');title.textContent=item.title;const desc=document.createElement('p');desc.textContent=item.description;card.append(badge,title,desc);if(item.href){const a=document.createElement('a');a.href=item.href;a.textContent='열기 · 내려받기 ↗';a.target='_blank';a.rel='noopener';card.append(a);}container.append(card);}}catch{toast('자료 목록을 불러오지 못했어요.');}}
fetch('/api/preview').then(r=>r.json()).then(info=>{state.previewInfo=info;for(const id of ['watch','fallback-watch'])$(id).hidden=!info.available;$('watch').textContent=info.type==='product-story'?'▷ 플리 소개 영상 보기':'▷ 자막 영상으로 먼저 보기';}).catch(()=>{});
window.addEventListener('pagehide',()=>{state.voiceEpoch++;mic?.getTracks().forEach(t=>t.stop());voiceSocket?.close();controlSocket?.close();socket?.close();if(state.token){const body=JSON.stringify({sessionToken:state.token});if(navigator.sendBeacon)navigator.sendBeacon('/api/session/end',new Blob([body],{type:'application/json'}));else fetch('/api/session/end',{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true}).catch(()=>{});}ctx?.close().catch(()=>{});});
async function pollNext(){await poll();setTimeout(pollNext,state.connecting||state.voice?250:1000);}setTimeout(pollNext,1000);setInterval(()=>{if(['LIVE','CONNECTING'].includes(state.media)&&state.lastFrame&&performance.now()-state.lastFrame>850)mediaFailure('화면 갱신을 확인하고 있어요.');},250);poll();navigate(state.route,false);
