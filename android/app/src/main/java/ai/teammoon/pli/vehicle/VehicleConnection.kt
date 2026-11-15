package ai.teammoon.pli.vehicle

import android.content.*
import android.app.ActivityManager
import android.os.*
import ai.teammoon.pli.data.DataContract
import ai.teammoon.pli.domain.VehicleState
import ai.teammoon.pli.domain.DestinationChoice

class VehicleConnection(private val context:Context,private val onState:(VehicleState)->Unit,private val onEvent:(String)->Unit){
    private val main=Handler(Looper.getMainLooper());private var remote:Messenger?=null;private var last=SystemClock.elapsedRealtime();private var pid=0;private var instance="";@Volatile private var closed=false;@Volatile private var bound=false
    private val framework=java.util.concurrent.Executors.newSingleThreadExecutor{r->Thread(r,"PliVehicleLifecycle").apply{isDaemon=true}}
    private var cleanupDone=false
    private var cleanupConfirmed=false
    private val closeCallbacks=mutableListOf<(Boolean)->Unit>()
    private val inbox=Messenger(Handler(Looper.getMainLooper()){msg->
        if(closed)return@Handler true
        val b=msg.data;val kind=b.getString("kind")
        if(kind=="hello"){pid=b.getInt("pid");instance=b.getString("instance")?:""}
        else if(b.getString("instance")!=instance)return@Handler true
        last=SystemClock.elapsedRealtime()
        when(kind){"state"->runCatching{DataContract.gson.fromJson(b.getString("text"),VehicleState::class.java)}.getOrNull()?.let(onState);"event"->onEvent(b.getString("text")?:"")};true
    })
    private val connection=object:ServiceConnection{
        override fun onServiceConnected(name:ComponentName,binder:IBinder){if(closed)return;remote=Messenger(binder);last=SystemClock.elapsedRealtime();send(1)}
        override fun onServiceDisconnected(name:ComponentName){close()}
    }
    private fun send(what:Int){try{remote?.send(Message.obtain(null,what).apply{replyTo=inbox})}catch(e:RemoteException){close()}}
    private val tick=object:Runnable{override fun run(){if(closed)return;if(SystemClock.elapsedRealtime()-last>(if(remote==null)15000 else 4000)){close();return};send(2);main.postDelayed(this,1000)}}
    fun start(){main.post(tick);framework.execute{if(!closed){val result=runCatching{context.bindService(Intent(context,VehicleService::class.java),connection,Context.BIND_AUTO_CREATE)}.getOrDefault(false);bound=result;main.post{if(!result&&!closed)close()}}}}
    fun requestRoute(choice:DestinationChoice,id:String):Boolean{if(closed||remote==null)return false;return try{remote!!.send(Message.obtain(null,3).apply{data=Bundle().apply{putString("choice",DataContract.gson.toJson(choice));putString("requestId",id)};replyTo=inbox});true}catch(e:RemoteException){false}}
    /** A stop Pli suggested on the current route (Pleos NaviHelper.addWaypoint, first waypoint). */
    fun addWaypoint(place:ai.teammoon.pli.domain.StopPlace):Boolean{if(closed||remote==null)return false;return try{remote!!.send(Message.obtain(null,5).apply{data=Bundle().apply{putString("name",place.name.take(80));putDouble("lat",place.latitude);putDouble("lon",place.longitude)};replyTo=inbox});true}catch(e:RemoteException){false}}
    fun cancelRoute():Boolean{if(closed||remote==null)return false;send(4);return !closed}
    fun close(done:(Boolean)->Unit={}){
        if(cleanupDone){done(cleanupConfirmed);return};closeCallbacks+=done
        if(closed)return;closed=true;main.removeCallbacksAndMessages(null)
        onState(VehicleState(source="차량 연결의 응답을 확인하지 못했어요"))
        framework.execute{
            try{
                if(bound)runCatching{context.unbindService(connection)};bound=false
                val processes=context.getSystemService(ActivityManager::class.java).runningAppProcesses.orEmpty()
                val owned=processes.singleOrNull{it.uid==android.os.Process.myUid()&&it.processName==context.packageName+":vehicle"&&(pid==0||it.pid==pid)}
                if(owned!=null){pid=owned.pid;android.os.Process.killProcess(pid)}
                val end=SystemClock.elapsedRealtime()+1800
                while(pid>0&&java.io.File("/proc/$pid").exists()&&SystemClock.elapsedRealtime()<end)Thread.sleep(40)
                cleanupConfirmed=pid==0||!java.io.File("/proc/$pid").exists()
            }finally{main.post{cleanupDone=true;closeCallbacks.toList().forEach{it(cleanupConfirmed)};closeCallbacks.clear()};framework.shutdown()}
        }
    }
}
