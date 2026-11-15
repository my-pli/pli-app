package ai.teammoon.pli.voice

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.*
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import ai.teammoon.pli.*
import java.util.UUID

/** Non-exported resource owner. Conversation/storage live in the default process. */
class CompanionService:LifecycleService(){
    private val main=Handler(Looper.getMainLooper())
    private var peer:Messenger?=null
    private var session="";private var boot="";private var epoch=0L
    private val instance=UUID.randomUUID().toString()
    private var speaker:PliSpeaker?=null;private var listener:PleosSpeechListener?=null
    private var closing=false;private var configured=false;@Volatile private var deadline=0L;@Volatile private var lastPeer=0L;@Volatile private var lastServer=0L;private var publicSession=false
    private val watchdog=java.util.concurrent.Executors.newSingleThreadScheduledExecutor()
    private var recreationUntil=0L
    private var removedTaskPending=false
    private var recreationWindow=""
    private var lastWindow=""
    private val inbox=Messenger(Handler(Looper.getMainLooper()){msg->handle(msg);true})
    override fun onCreate(){super.onCreate();foreground()}
    override fun onBind(intent:Intent):IBinder{super.onBind(intent);return inbox.binder}
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{super.onStartCommand(intent,flags,startId);return START_NOT_STICKY}
    private fun emit(event:String,text:String="",value:Boolean=false,level:Float=0f,playback:String="",focus:String=""){
        val b=Bundle().apply{putString("event",event);putString("session",session);putString("boot",boot);putLong("epoch",epoch);putString("instance",instance);putInt("pid",android.os.Process.myPid());putString("text",text);putBoolean("value",value);putFloat("value",level);if(event in setOf("speaking","navigation","tts_ready","closed","capture"))putBoolean("value",value);putString("playback",playback);putString("focus",focus)}
        try{peer?.send(Message.obtain(null,100).apply{data=b})}catch(e:RemoteException){shutdown()}
    }
    private fun handle(msg:Message){
        if(closing)return
        val b=msg.data;val action=b.getString("action")
        if(action=="configure"&&!configured){
            configured=true;session=b.getString("session")?:return;boot=b.getString("boot")?:return;epoch=b.getLong("epoch");peer=msg.replyTo;lastPeer=SystemClock.elapsedRealtime();lastServer=lastPeer;publicSession=b.getBoolean("public");deadline=if(b.getBoolean("public"))lastPeer+180000 else Long.MAX_VALUE
            emit("hello");watchdog.scheduleAtFixedRate({val now=SystemClock.elapsedRealtime();if(configured&&!closing&&(now>=deadline||now-lastPeer>10000||publicSession&&now-lastServer>10000)){main.post{shutdown()};watchdog.schedule({android.os.Process.killProcess(android.os.Process.myPid())},2500,java.util.concurrent.TimeUnit.MILLISECONDS)}},1,1,java.util.concurrent.TimeUnit.SECONDS);initialize();main.post(tick);return
        }
        if(b.getString("session")!=session||b.getString("boot")!=boot||b.getLong("epoch")!=epoch)return
        lastPeer=SystemClock.elapsedRealtime()
        if(closing)return
        when(action){
            "ping"->{val window=b.getString("window")?:"";if(WindowRecoveryPolicy.acknowledges(recreationWindow,window,b.getBoolean("value"),recreationUntil,SystemClock.elapsedRealtime())){removedTaskPending=false;recreationUntil=0};lastWindow=window;emit("heartbeat")}
            "ui_recreation"->{recreationUntil=SystemClock.elapsedRealtime()+WindowRecoveryPolicy.GRACE_MS;recreationWindow=b.getString("window")?:lastWindow}
            "server_heartbeat"->{lastServer=SystemClock.elapsedRealtime()}
            "speak"->speaker?.speak((b.getString("text")?:"").take(4000),b.getFloat("number"))
            "quiet"->speaker?.setQuiet(b.getBoolean("value"))
            "stop_playback"->speaker?.stop()
            "volume"->speaker?.adjustVolume(b.getFloat("number"))
            "navigation"->if(BuildConfig.DEBUG)speaker?.navigationForTest(b.getBoolean("value"))
            "close"->shutdown()
        }
    }
    private fun initialize(){
        speaker=PliSpeaker(this,{ready,message->emit("tts_ready",message,ready)},{emit("speaking",value=it)},{emit("navigation",value=it)},{emit("error",it)},{p,f->emit("state",playback=p,focus=f)},{emit("spoken_text",it)},onDeviceVoice=true)
        listener=PleosSpeechListener(this,lifecycleScope,{emit("stt_ready")},{emit("final",it)},{emit("partial",it)},{emit("level",level=it)},{emit("stt_error",it)},{emit("backend",it)},{emit("ended")},{emit("capture",value=it)},{emit("recognition_state",it)})
        listener?.start()
    }
    private val tick=object:Runnable{override fun run(){if(closing)return;val now=SystemClock.elapsedRealtime();if(now>=deadline||now-lastPeer>10000){shutdown();return};emit("heartbeat");main.postDelayed(this,1000)}}
    private fun shutdown(){
        if(closing)return;closing=true;main.removeCallbacks(tick)
        var stt:Boolean?=null;var tts:Boolean?=null
        fun finish(){if(stt!=null&&tts!=null){emit("closed",value=stt==true&&tts==true);stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}}
        listener?.stop{stt=it;finish()}?:run{stt=true}
        speaker?.close{tts=it;finish()}?:run{tts=true};finish()
    }
    private fun foreground(){
        val manager=getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("pli-companion","플리와 함께하는 길",NotificationManager.IMPORTANCE_LOW).apply{description="음성 대화를 위한 마이크 사용 상태"})
        val launch=packageManager.getLaunchIntentForPackage(packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val intent=PendingIntent.getActivity(this,0,launch,PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification=NotificationCompat.Builder(this,"pli-companion").setSmallIcon(R.drawable.ic_pli).setContentTitle("플리가 함께하고 있어요").setContentText("목소리로 대화 중 · 원본 음성은 저장하지 않아요").setContentIntent(intent).setOngoing(true).setSilent(true).build()
        if(Build.VERSION.SDK_INT>=29)startForeground(21,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE or ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)else startForeground(21,notification)
    }

    override fun onTaskRemoved(rootIntent:Intent?){
        val now=SystemClock.elapsedRealtime()
        // A public browser lease owns the silenced emulator input. A vendor
        // launcher restart may remove its embedded task without ending consent.
        // Private sessions retain immediate task-removal shutdown.
        if(recreationUntil<=now&&publicSession&&now-lastServer<3500){recreationUntil=now+WindowRecoveryPolicy.GRACE_MS;recreationWindow=lastWindow}
        val until=recreationUntil;val remaining=until-now
        android.util.Log.i("PliVoiceLifecycle","task removed public=$publicSession graceMs=${remaining.coerceAtLeast(0)}")
        if(remaining>0){removedTaskPending=true;main.postDelayed({if(removedTaskPending&&recreationUntil==until)shutdown()},remaining)}else shutdown()
        super.onTaskRemoved(rootIntent)
    }
    override fun onDestroy(){if(!closing)shutdown();watchdog.shutdown();super.onDestroy()}
}
