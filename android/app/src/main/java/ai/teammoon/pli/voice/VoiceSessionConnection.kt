package ai.teammoon.pli.voice

import android.content.*
import android.app.ActivityManager
import android.os.*
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*

/** Main-process owner of an epoch-fenced connection; no speech SDK objects here. */
class VoiceSessionConnection(private val context:Context,private val scope:CoroutineScope,private val session:String,private val epoch:Long,private val boot:String,private val onReady:(Boolean,String)->Unit,private val onSpeaking:(Boolean)->Unit,private val onNavigation:(Boolean)->Unit,private val onError:(String)->Unit,private val onClosed:(Boolean)->Unit,private val onState:(String,String)->Unit,private val onHeartbeat:(String,Long)->Unit,private val onSpoken:(String)->Unit={}){
    private val main=Handler(Looper.getMainLooper());private var remote:Messenger?=null
    private val framework=java.util.concurrent.Executors.newSingleThreadExecutor{r->Thread(r,"PliVoiceLifecycle").apply{isDaemon=true}}
    private var speechRequested=false
    private var configured=false;@Volatile private var bound=false;@Volatile private var closing=false;@Volatile private var closed=false;private var pid=0;private var instance="";private var heartbeat=SystemClock.elapsedRealtime()
    var ready=false;private set
    var speaking=false;private set
    var navigation=false;private set
    var quiet=false;private set
    private var sttReady:()->Unit={};private var final:(String)->Unit={};private var partial:(String)->Unit={};private var level:(Float)->Unit={};private var error:(String)->Unit={};private var backend:(String)->Unit={};private var ended:()->Unit={};private var recognition:(String)->Unit={};private var capture:(Boolean)->Unit={}
    private val inbox=Messenger(Handler(Looper.getMainLooper()){msg->
        val b=msg.data
        if(b.getString("session")!=session||b.getLong("epoch")!=epoch||b.getString("boot")!=boot)return@Handler true
        if(closed)return@Handler true
        val event=b.getString("event")
        heartbeat=SystemClock.elapsedRealtime()
        if(event=="hello"){pid=b.getInt("pid");instance=b.getString("instance")?:""}
        else if(b.getString("instance")!=instance)return@Handler true
        if(closing&&event!="closed")return@Handler true
        when(event){
            "hello"->onHeartbeat(instance,SystemClock.elapsedRealtime())
            "heartbeat"->onHeartbeat(instance,SystemClock.elapsedRealtime())
            "tts_ready"->{ready=b.getBoolean("value");onReady(ready,b.getString("text")?:"")}
            "spoken_text"->onSpoken(b.getString("text")?:"")
            "speaking"->{speaking=b.getBoolean("value");onSpeaking(speaking)}
            "navigation"->{navigation=b.getBoolean("value");onNavigation(navigation)}
            "state"->onState(b.getString("playback")?:"IDLE",b.getString("focus")?:"NONE")
            "error"->onError(b.getString("text")?:"음성 연결 오류")
            "stt_ready"->sttReady()
            "final"->final(b.getString("text")?:"")
            "partial"->partial(b.getString("text")?:"")
            "level"->level(b.getFloat("value"))
            "stt_error"->error(b.getString("text")?:"마이크 연결 오류")
            "backend"->backend(b.getString("text")?:"")
            "ended"->ended()
            "recognition_state"->recognition(b.getString("text")?:"UNKNOWN")
            "capture"->capture(b.getBoolean("value"))
            "closed"->finish(b.getBoolean("value"))
        };true
    })
    private val connection=object:ServiceConnection{
        override fun onServiceConnected(name:ComponentName,binder:IBinder){if(closed)return;remote=Messenger(binder);if(closing){finish(true);return};configured=true;heartbeat=SystemClock.elapsedRealtime();send("configure");if(quiet)send("quiet",value=true)}
        override fun onServiceDisconnected(name:ComponentName){remote=null;if(!closed){if(closing)finish(false)else onError("음성 프로세스 연결이 끊겼어요.")}}
        override fun onBindingDied(name:ComponentName){onServiceDisconnected(name)}
    }
    fun recognitionCallbacks(onReady:()->Unit,onFinal:(String)->Unit,onPartial:(String)->Unit,onLevel:(Float)->Unit,onError:(String)->Unit,onBackend:(String)->Unit,onSessionEnd:()->Unit,onCapture:(Boolean)->Unit,onRecognitionState:(String)->Unit={}){recognition=onRecognitionState;sttReady=onReady;final=onFinal;partial=onPartial;level=onLevel;error=onError;backend=onBackend;ended=onSessionEnd;capture=onCapture}
    private fun send(action:String,text:String="",value:Boolean=false,number:Float=0f){try{val b=Bundle().apply{putString("action",action);putString("window",ai.teammoon.pli.MainActivity.windowOwner.get()?.windowIdentity);putString("session",session);putLong("epoch",epoch);putString("boot",boot);putBoolean("public",(context as ai.teammoon.pli.PliApplication).demoActive);putString("text",text);putBoolean("value",value);putFloat("number",number)};remote?.send(Message.obtain(null,1).apply{data=b;replyTo=inbox})}catch(e:RemoteException){if(!closing)onError("음성 명령을 전달하지 못했어요.")}}
    private val tick=object:Runnable{override fun run(){if(!closed&&!closing){if(remote==null&&SystemClock.elapsedRealtime()-heartbeat>15000){onError("음성 서비스 준비를 확인하지 못했어요.");return};if(remote!=null&&SystemClock.elapsedRealtime()-heartbeat>3500){onError("음성 프로세스의 응답을 확인하지 못했어요.");return};send("ping",value=(context as ai.teammoon.pli.PliApplication).state.value.visible);main.postDelayed(this,1000)}}}
    fun start(){main.post(tick);framework.execute{
        if(closed||closing)return@execute
        val at=SystemClock.elapsedRealtime()
        try{val intent=Intent(context,CompanionService::class.java);ContextCompat.startForegroundService(context,intent);bound=context.bindService(intent,connection,Context.BIND_AUTO_CREATE);main.post{if(!closed&&!closing&&!bound)onError("음성 서비스를 연결하지 못했어요.")}}
        catch(e:Exception){main.post{if(!closed&&!closing)onError("마이크를 시작하려면 앱 화면에서 다시 시작해 주세요.")}}
        finally{android.util.Log.i("PliVoiceLifecycle","start/bind elapsed=${SystemClock.elapsedRealtime()-at}")}
    }}

    fun speak(text:String,level:Float=.7f){speechRequested=true;send("speak",text,number=level)}
    fun setQuiet(value:Boolean){quiet=value;send("quiet",value=value)}
    fun stop(){send("stop_playback")}
    fun serverHeartbeat(){send("server_heartbeat")}
    fun prepareWindowRecreation(){send("ui_recreation")}
    fun adjustVolume(value:Float){send("volume",number=value)}
    fun navigationForTest(value:Boolean){if(ai.teammoon.pli.BuildConfig.DEBUG)send("navigation",value=value)}
    fun close(){if(closing||closed)return;closing=true;if(!configured){finish(true);return};send("close");main.postDelayed({if(!closed){finish(false)}},4000)}
    private fun killOwnVoice():Boolean{
        val running=context.getSystemService(ActivityManager::class.java).runningAppProcesses.orEmpty()
        val owned=running.singleOrNull{it.uid==android.os.Process.myUid()&&it.processName==context.packageName+":voice"&&(pid==0||it.pid==pid)}?:return false
        pid=owned.pid;android.os.Process.killProcess(pid);return true
    }
    private fun finish(ok:Boolean){
        if(closed)return;closed=true;ready=false;speaking=false;main.removeCallbacksAndMessages(null)
        val delivered=java.util.concurrent.atomic.AtomicBoolean(false)
        val deadline=Runnable{if(delivered.compareAndSet(false,true))onClosed(false)}
        main.postDelayed(deadline,2500)
        // This queue is also the startup queue: a cancelled bind can never complete
        // after its cleanup receipt and attach the next epoch to a closing service.
        framework.execute{
            val at=SystemClock.elapsedRealtime();var confirmed=false
            try{
                if(bound)runCatching{context.unbindService(connection)};bound=false
                context.stopService(Intent(context,CompanionService::class.java));killOwnVoice()
                val end=SystemClock.elapsedRealtime()+1800
                while(SystemClock.elapsedRealtime()<end){
                    val gone=pid==0||!java.io.File("/proc/$pid").exists()
                    val recording=runCatching{context.getSystemService(android.media.AudioManager::class.java).activeRecordingConfigurations.any{it.clientAudioSessionId>0}}.getOrDefault(true)
                    if(gone&&!recording){confirmed=ok||!speechRequested;break};Thread.sleep(40)
                }
            }catch(e:Exception){confirmed=false}
            finally{
                android.util.Log.i("PliVoiceLifecycle","cleanup confirmed=$confirmed elapsed=${SystemClock.elapsedRealtime()-at}")
                val result=confirmed;main.post{if(delivered.compareAndSet(false,true)){main.removeCallbacks(deadline);onClosed(result)}};framework.shutdown()
            }
        }
    }
}
