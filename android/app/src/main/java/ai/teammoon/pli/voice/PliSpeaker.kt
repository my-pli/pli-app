package ai.teammoon.pli.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import ai.pleos.playground.tts.TextToSpeech
import ai.pleos.playground.tts.constant.Mode
import ai.pleos.playground.tts.constant.ErrorType
import ai.pleos.playground.tts.listener.EventListener
import ai.pleos.playground.tts.listener.OnInitializeListener
import java.util.Locale

/** Runs only in :voice. No SDK/Binder operation is executed by a main callback. */
class PliSpeaker(context:Context,private val onReady:(Boolean,String)->Unit,private val onSpeaking:(Boolean)->Unit,private val onNavigation:(Boolean)->Unit,private val onError:(String)->Unit,private val onState:(String,String)->Unit={_,_->},private val onSpoken:(String)->Unit={},private val requestFocusOverride:(()->Int)?=null,private val completionLimitOverrideMs:Long?=null,private val acceptCompletion:(()->Boolean)?=null,private val onDeviceVoice:Boolean=false){
    private val main=Handler(Looper.getMainLooper())
    private val audio=context.getSystemService(AudioManager::class.java)
    private var tts:TextToSpeech?=null
    private var playback:OnDevicePlayback?=null
    private var announced=false
    @Volatile private var usingVoice=false
    var ready=false;private set
    var quiet=false;private set
    var speaking=false;private set
    var navigation=false;private set
    @Volatile private var closed=false
    @Volatile private var generation=0L
    private var pending:String?=null
    private var currentText=""
    private var active=false
    private var stopping=false
    private var stopRevision=0L
    @Volatile private var backendPlaying=false
    private val playbackLock=Any()
    private var stopAck=java.util.concurrent.CountDownLatch(0)
    private var requesting=false
    private var granted=false
    private var volume=.7f
    private val attributes=AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
    private val focus=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK).setAudioAttributes(attributes).setAcceptsDelayedFocusGain(true).setWillPauseWhenDucked(true).setOnAudioFocusChangeListener({change->
        if(!closed)when(change){
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT,AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK->{granted=false;navigation=true;pending=currentText.takeIf{active};stop(false);onNavigation(true)}
            AudioManager.AUDIOFOCUS_LOSS->{granted=false;navigation=true;pending=null;stop(false);onNavigation(true)}
            AudioManager.AUDIOFOCUS_GAIN->{if(quiet||closed){navigation=false;onNavigation(false);abandon()}else{granted=true;navigation=false;onNavigation(false);val text=pending;pending=null;if(text!=null)speak(text,volume)}}
        }
    },main).build()
    private val events=object:EventListener{
        override fun onReady()=Unit
        override fun onStart(){synchronized(playbackLock){backendPlaying=true};main.post{if(!closed&&active&&!speaking){speaking=true;main.removeCallbacks(startTimeout);val limit=completionLimitOverrideMs?:(8000L+currentText.codePointCount(0,currentText.length)*240L).coerceIn(12000L,1200000L);main.postDelayed(completionTimeout,limit);Log.i("PliTtsEvent","start generation=$generation length=${currentText.length} limitMs=$limit engine=${if(usingVoice)"on-device" else "pleos"}");onState("PLAYING","GRANTED");onSpoken(currentText);onSpeaking(true)}}}
        override fun onDone(){val eventGeneration=generation;synchronized(playbackLock){backendPlaying=false;stopAck.countDown()};if(acceptCompletion?.invoke()==false)return;main.post{Log.i("PliTtsEvent","done generation=$generation");if(!closed&&!stopping&&eventGeneration==generation&&active&&speaking){main.removeCallbacks(completionTimeout);active=false;speaking=false;onSpeaking(false);onState("IDLE","NONE");abandon();val next=pending;pending=null;if(next!=null&&!quiet&&!navigation)speak(next,volume)}}}
        override fun onStop(){synchronized(playbackLock){backendPlaying=false;stopAck.countDown()};main.post{if(!closed&&!active&&!requesting){main.removeCallbacks(completionTimeout);speaking=false;onSpeaking(false);onState("IDLE","NONE")}}}
        override fun onUpdatedRms(rms:Double)=Unit
        override fun onError(errorType:ErrorType){main.post{main.removeCallbacks(completionTimeout);if(!closed){active=false;speaking=false;onSpeaking(false);abandon();onError("음성 재생을 확인하지 못했어요 · ${errorType.name}")}}}
    }
    private val focusTimeout=Runnable{if(requesting&&!closed){generation++;pending=null;onState("ERROR","UNKNOWN");onError("오디오 포커스 응답이 늦어 음성 연결을 중단했어요.")}}
    private val startTimeout=Runnable{if(active&&!speaking&&!closed){generation++;active=false;pending=null;onState("ERROR","UNKNOWN");onError("플리 목소리의 재생 시작을 확인하지 못했어요.")}}
    private val completionTimeout=Runnable{if(active&&speaking&&!closed){generation++;active=false;speaking=false;pending=null;Log.w("PliTtsEvent","completion not confirmed");onState("ERROR","UNKNOWN");onError("음성 재생의 완료를 확인하지 못해 연결을 정리하고 있어요.")}}
    init{SpeechSdkIo.tts{
        try{val engine=TextToSpeech(context.applicationContext,Mode.ON_DEVICE);tts=engine
            engine.initialize(object:OnInitializeListener{
                override fun onSuccess(){SpeechSdkIo.tts{if(!closed)try{engine.addEventListener(events);engine.setLocale(Locale.KOREA);engine.setAudioAttributes(attributes);main.post{if(!closed)becomeReady("Pleos ON_DEVICE")}}catch(e:Exception){main.post{onError("음성 설정에 실패했어요.")}}}}
                override fun onFailure(errorType:ErrorType){main.post{if(!closed&&!ready)onReady(false,"음성 엔진 초기화 실패 · ${errorType.name}")}}
            })
        }catch(e:Exception){main.post{if(!closed)onReady(false,"음성 엔진에 연결하지 못했어요.")}}
    }
        if(onDeviceVoice){
            // Pli's own voice runs in this APK; Pleos TTS stays the fallback while it loads or if it fails.
            playback=OnDevicePlayback(attributes,events){text->SpeechSdkIo.tts{if(!closed)runCatching{usingVoice=false;tts?.speak(text,true)}}}
            main.postDelayed({if(!closed&&ready)pending?.let{if(!active&&!requesting&&!stopping){pending=null;speak(it,volume)}}},VOICE_WAIT_MS+50)
            Thread({val edge=EdgeVoice.check();Log.i("PliVoice","edge voice ${if(edge)"ready via ${EdgeVoice.provider}" else "unreachable"}");main.post{edgeKnown=true;if(!closed&&edge)becomeReady("엣지 음성 · Supertonic")}},"PliEdgeVoice").start()
            PliVoiceEngine.warm(context){ok->Log.i("PliVoice","engine ${if(ok)"ready" else "unavailable: ${PliVoiceEngine.failure}"}");main.post{if(!closed){if(ok)becomeReady(PliVoiceEngine.label)else if(ready)pending?.let{if(!active&&!requesting&&!stopping){pending=null;speak(it,volume)}}}}}
        }
    }
    private val voiceDeadline=SystemClock.elapsedRealtime()+VOICE_WAIT_MS
    /** While Pli's own voice is still loading (first seconds of a session), hold speech instead of switching voices mid-session. */
    @Volatile private var edgeKnown=false
    /** Until the edge has answered (or the head unit's engine is loaded), hold speech so the session keeps one voice. */
    private fun waitingForVoice()=onDeviceVoice&&!EdgeVoice.usable()&&!PliVoiceEngine.ready&&PliVoiceEngine.failure==null&&(!edgeKnown||!PliVoiceEngine.ready)&&SystemClock.elapsedRealtime()<voiceDeadline
    private fun becomeReady(label:String){ready=true;if(!announced){announced=true;onReady(true,label)};pending?.let{if(!active&&!requesting&&!stopping){pending=null;speak(it,volume)}}}
    fun speak(text:String,level:Float=.7f){
        if(closed||quiet)return
        if(active||requesting||stopping){pending=text;return}
        currentText=text;volume=level
        if(!ready||navigation||waitingForVoice()){pending=text;return}
        val token=++generation;requesting=true;onState("QUEUED","REQUESTING");main.postDelayed(focusTimeout,2000)
        SpeechSdkIo.focus{
            val at=SystemClock.elapsedRealtime();Log.i("PliFocus","request generation=$token start=$at")
            try{val result=requestFocusOverride?.invoke()?:audio.requestAudioFocus(focus);Log.i("PliFocus","result=$result elapsed=${SystemClock.elapsedRealtime()-at}")
                main.post{
                    requesting=false;main.removeCallbacks(focusTimeout)
                    if(closed||quiet||token!=generation){abandon();return@post}
                    when(result){
                        AudioManager.AUDIOFOCUS_REQUEST_GRANTED->{granted=true;active=true;speaking=false;onState("STARTING","GRANTED");val own=playback!=null&&(EdgeVoice.usable()||PliVoiceEngine.ready||edgeKnown);usingVoice=own;main.postDelayed(startTimeout,if(own)VOICE_START_MS else 3000);SpeechSdkIo.tts{if(!closed&&token==generation)try{if(own)playback?.speak(text)else tts?.speak(text,true)}catch(e:Exception){main.post{onError("음성 재생에 실패했어요.")}}}}
                        AudioManager.AUDIOFOCUS_REQUEST_DELAYED->{pending=text;onState("WAITING_FOR_FOCUS","DELAYED")}
                        else->{pending=null;onState("ERROR","DENIED");onError("오디오 사용 권한을 받지 못했어요.")}
                    }
                }
            }catch(e:Exception){main.post{requesting=false;main.removeCallbacks(focusTimeout);if(!closed)onError("오디오 연결을 확인해 주세요.")}}
        }
    }
    private fun abandon(){granted=false;SpeechSdkIo.focus{runCatching{audio.abandonAudioFocusRequest(focus)}}}
    fun setQuiet(value:Boolean){quiet=value;if(value){pending=null;stop(abandon=!navigation)}}
    fun adjustVolume(level:Float){SpeechSdkIo.focus{val max=audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);audio.setStreamVolume(AudioManager.STREAM_MUSIC,(max*level).toInt().coerceIn(0,max),0)}}
    fun stop(abandon:Boolean=true){
        generation++;active=false;if(abandon)pending=null;main.removeCallbacks(startTimeout);main.removeCallbacks(completionTimeout);speaking=false
        stopping=true;val revision=++stopRevision
        onSpeaking(false);if(abandon)abandon()
        SpeechSdkIo.tts{
            val ack=synchronized(playbackLock){java.util.concurrent.CountDownLatch(if(backendPlaying)1 else 0).also{stopAck=it}}
            val stopped=runCatching{playback?.stop();tts?.stop();check(ack.await(1200,java.util.concurrent.TimeUnit.MILLISECONDS)){"PLAYBACK_STOP_UNCONFIRMED"}}.isSuccess
            main.post{if(!closed&&revision==stopRevision){
                stopping=false
                if(!stopped){pending=null;onError("이전 음성의 중단을 확인하지 못해 새 답변을 재생하지 않았어요.")}
                else{onState("IDLE","NONE");if(!quiet&&!navigation){val next=pending;pending=null;if(next!=null)speak(next,volume)}}
            }}
        }
    }
    private companion object{const val VOICE_START_MS=12000L;const val VOICE_WAIT_MS=8000L}
    fun navigationForTest(value:Boolean){navigation=value;if(value)stop(false);onNavigation(value)}
    fun close(done:(Boolean)->Unit={}){
        closed=true;generation++;pending=null;active=false;ready=false;main.removeCallbacksAndMessages(null)
        val t=SpeechSdkIo.tts{
            val ack=synchronized(playbackLock){java.util.concurrent.CountDownLatch(if(backendPlaying)1 else 0).also{stopAck=it}}
            // Completion can win a race with stop. Both SDK terminal callbacks confirm
            // playback has ended; create the latch under the same lock as those callbacks.
            var failure:Throwable?=null
            fun attempt(stage:String,work:()->Unit){try{work()}catch(e:Exception){Log.w("PliTtsClose","$stage: ${e.javaClass.simpleName}");if(failure==null)failure=e}}
            attempt("voice"){playback?.close();playback=null}
            attempt("stop"){tts?.stop();check(ack.await(1200,java.util.concurrent.TimeUnit.MILLISECONDS)){"PLAYBACK_STOP_UNCONFIRMED"}}
            // A failed stop must never skip SDK cleanup or poison the next owner.
            attempt("listener removal"){tts?.removeEventListener(events)}
            attempt("release"){tts?.release()}
            tts=null
            failure?.let{throw it}
        }
        val f=SpeechSdkIo.focus{audio.abandonAudioFocusRequest(focus)}
        Thread({val ok=runCatching{t.get(2500,java.util.concurrent.TimeUnit.MILLISECONDS);f.get(1500,java.util.concurrent.TimeUnit.MILLISECONDS)}.onFailure{Log.w("PliTtsClose","close: ${it.javaClass.simpleName}")}.isSuccess;main.post{done(ok)}},"PliTtsClose").start()
    }
}
