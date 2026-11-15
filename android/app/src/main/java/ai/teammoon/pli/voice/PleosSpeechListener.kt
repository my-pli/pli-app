package ai.teammoon.pli.voice

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import ai.pleos.playground.stt.SpeechToText
import ai.pleos.playground.stt.constant.Mode
import ai.pleos.playground.stt.constant.ErrorType
import ai.pleos.playground.stt.listener.ResultListener
import ai.pleos.playground.stt.listener.OnInitializeListener
import kotlinx.coroutines.*
import java.util.Locale

/** SDK calls, including construction and configuration, stay on the STT queue. */
class PleosSpeechListener(private val context:Context,private val scope:CoroutineScope,private val onReady:()->Unit,private val onFinal:(String)->Unit,private val onPartial:(String)->Unit,private val onLevel:(Float)->Unit,private val onError:(String)->Unit,private val onBackend:(String)->Unit,private val onSessionEnd:()->Unit={},private val onCapture:(Boolean)->Unit={},private val onRecognitionState:(String)->Unit={},private val edgeFirst:Boolean=true){
    private val main=Handler(Looper.getMainLooper())
    @Volatile private var sdk:SpeechToText?=null
    private var fallback:OfflineListener?=null
    private var capture:PcmCapture?=null
    private val queued=java.util.concurrent.atomic.AtomicInteger(0)
    @Volatile private var closed=false
    private var finalDelivered=false
    private var ready=false;private var recording=false;private var usingFallback=false
    private fun dispatch(work:()->Unit){main.post{if(!closed)work()}}
    private val restart=Runnable{if(!closed)capture?.resultReceived()}
    private val initializationTimeout=Runnable{if(!ready&&!closed)switchToFallback("초기화 응답 없음")}
    private val results=object:ResultListener{
        override fun onReady()=Unit
        override fun onStartedRecognition(){dispatch{recording=true;finalDelivered=false;onCapture(true)}}
        override fun onUpdated(stt:String,completed:Boolean){dispatch{if(!usingFallback){if(completed){if(!finalDelivered){finalDelivered=true;capture?.resultReceived();if(stt.isNotBlank())onFinal(stt)}}else onPartial(stt)}}}
        override fun onUpdatedEpdData(on:Long,off:Long)=Unit
        override fun onUpdatedRms(rms:Double){dispatch{onLevel((if(rms<=1.0)rms else rms/4000.0).toFloat().coerceIn(0f,1f))}}
        override fun onEndedRecognition(){dispatch{recording=false;onSessionEnd();capture?.recognitionEnded()}}
        override fun onError(errorType:ErrorType){dispatch{recording=false;if(errorType==ErrorType.PERMISSION_DENIED){onCapture(false);onError("마이크 사용 권한이 필요해요.")}else if(errorType in setOf(ErrorType.ON_DEVICE_ENGINE_ERROR,ErrorType.NOT_SUPPORTED_API)){onCapture(false);switchToFallback(errorType.name)}else scheduleRestart(700)}}
    }
    // Edge path: the app's own PCM goes to the vehicle edge computer (SenseVoice) for recognition.
    @Volatile private var edgeMode=false
    private var edgeFailures=0
    private val utterance=java.io.ByteArrayOutputStream()
    fun start(){
        if(!edgeFirst){startPleos();return}
        scope.launch(Dispatchers.IO){
            val edge=ai.teammoon.pli.edge.EdgeAi.checkHealth()
            withContext(Dispatchers.Main){
                if(closed)return@withContext
                if(edge){edgeMode=true;ready=true;onBackend("엣지 AI 음성인식 · ${ai.teammoon.pli.edge.EdgeAi.asrEngine.ifBlank{"SenseVoice"}} · 앱 소유 PCM");onReady();startEdgeCapture()}
                else startPleos()
            }
        }
    }
    private fun startEdgeCapture(){
        if(closed)return
        capture=PcmCapture(scope,{recording=true;onCapture(true)},onLevel,{bytes->
            val token=capture?.gate?.id?:0
            synchronized(utterance){if(capture?.gate?.maySend(token)==true&&utterance.size()<16000*2*15)utterance.write(bytes)}
        },{
            val token=capture?.gate?.id?:0
            val pcm=synchronized(utterance){val b=utterance.toByteArray();utterance.reset();b}
            if(capture?.gate?.mayComplete(token)==true)scope.launch(Dispatchers.IO){
                val result=ai.teammoon.pli.edge.EdgeAi.transcribe(pcm)
                withContext(Dispatchers.Main){
                    if(closed||!edgeMode)return@withContext
                    capture?.resultReceived();capture?.recognitionEnded();onSessionEnd()
                    when{
                        result==null->{edgeFailures++;Log.w("PliStt","Edge ASR failure $edgeFailures");if(edgeFailures>=2)leaveEdge()else onError("엣지 음성인식 연결을 다시 확인하고 있어요.")}
                        result.text.isNotBlank()->{edgeFailures=0;Log.i("PliStt","Edge ASR ${result.ms}ms");onFinal(result.text)}
                        else->edgeFailures=0
                    }
                }
            }
        },{onError("마이크 입력 또는 음성 응답을 확인하지 못했어요.")},onRecognitionState).also{it.start()}
    }
    private fun leaveEdge(){
        if(closed||!edgeMode)return
        edgeMode=false;ready=false;val own=capture;capture=null
        scope.launch(Dispatchers.IO){own?.stop();withContext(Dispatchers.Main){if(!closed){onBackend("Pleos SpeechToText 3.3.1 · ON_DEVICE · 엣지 연결 끊김 대체");startPleos()}}}
    }
    private fun startPleos(){
        main.postDelayed(initializationTimeout,8000)
        SpeechSdkIo.stt{if(!closed)try{
            val recognizer=SpeechToText(context.applicationContext,Mode.ON_DEVICE);sdk=recognizer
            recognizer.initialize(object:OnInitializeListener{
                override fun onSuccess(){SpeechSdkIo.stt{if(!closed&&!usingFallback)try{recognizer.addListener(results);recognizer.setLocale(Locale.KOREA);dispatch{ready=true;main.removeCallbacks(initializationTimeout);onBackend("Pleos SpeechToText 3.3.1 · ON_DEVICE · 앱 소유 PCM");onReady();startCapture()}}catch(e:Exception){dispatch{switchToFallback("설정 실패")}}}}
                override fun onFailure(errorType:ErrorType){dispatch{switchToFallback(errorType.name)}}
            })
        }catch(e:Exception){dispatch{switchToFallback("초기화 실패")}}}
    }
    private fun startCapture(){
        if(closed)return
        capture=PcmCapture(scope,{recording=true;onCapture(true)},onLevel,{bytes->
            val token=capture?.gate?.id?:0
            if(queued.incrementAndGet()>10){queued.decrementAndGet();dispatch{onError("음성 입력 처리가 지연돼 연결을 멈췄어요.")}}
            else SpeechSdkIo.stt{try{if(!closed&&capture?.gate?.maySend(token)==true)sdk?.sendAudio(bytes)}finally{queued.decrementAndGet()}}
        },{val token=capture?.gate?.id?:0;SpeechSdkIo.stt{if(!closed&&capture?.gate?.mayComplete(token)==true)sdk?.completeAudioSend()}},{onError("마이크 입력 또는 음성 응답을 확인하지 못했어요.")},onRecognitionState).also{it.start()}
    }
    private fun scheduleRestart(delay:Long=180){capture?.recognitionEnded()}
    private fun switchToFallback(reason:String){
        if(closed||usingFallback)return
        usingFallback=true;main.removeCallbacks(restart);main.removeCallbacks(initializationTimeout)
        val old=sdk;sdk=null;val own=capture;capture=null
        val task=SpeechSdkIo.stt{check(own?.stop()!=false);old?.stop();old?.removeListener(results);old?.release()}
        scope.launch(Dispatchers.IO){
            val released=runCatching{task.get(2500,java.util.concurrent.TimeUnit.MILLISECONDS)}.isSuccess
            withContext(Dispatchers.Main){if(!closed){if(!released){onError("이전 음성 인식기의 종료를 확인하지 못했어요.");return@withContext}
                Log.w("PliStt","Embedded fallback: $reason");onBackend("앱 내장 한국어 인식 · Vosk")
                fallback=OfflineListener(context,scope,{onCapture(true);onRecognitionState("READY");onReady()},onFinal,onPartial,onLevel,onError).also{it.start()}
            }}
        }
    }
    fun stop(done:(Boolean)->Unit={}){
        closed=true;ready=false;recording=false;main.removeCallbacksAndMessages(null);val old=sdk;sdk=null;val embedded=fallback;fallback=null;val own=capture;capture=null
        val captureDone=java.util.concurrent.CompletableFuture.supplyAsync{own?.stop()!=false}
        val task=SpeechSdkIo.stt{embedded?.stop();old?.stop();old?.removeListener(results);old?.release()}
        scope.launch(Dispatchers.IO){val ok=runCatching{task.get(2500,java.util.concurrent.TimeUnit.MILLISECONDS);check(captureDone.get(2000,java.util.concurrent.TimeUnit.MILLISECONDS));embedded?.awaitStopped()}.isSuccess;withContext(Dispatchers.Main){onCapture(false);done(ok)}}
    }
}
