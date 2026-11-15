package ai.teammoon.pli.vehicle

import android.app.Service
import android.content.Intent
import android.os.*
import ai.teammoon.pli.data.DataContract
import kotlinx.coroutines.*
import java.util.UUID

/** Car's internal connection lock must never be shared with the UI or speech process. */
class VehicleService:Service(){
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
    private val main=Handler(Looper.getMainLooper())
    private val id=UUID.randomUUID().toString()
    private var peer:Messenger?=null
    private var source:PleosVehicleSource?=null
    private val inbox=Messenger(Handler(Looper.getMainLooper()){msg->
        peer=msg.replyTo
        if(msg.what==1){emit("hello");if(source==null){source=PleosVehicleSource(this,{emit("state",DataContract.gson.toJson(it))},{emit("event",it)},{emit("issue")});scope.launch{source?.start()}}}
        else if(msg.what==2)emit("heartbeat")
        else if(msg.what==3){val choice=runCatching{DataContract.gson.fromJson(msg.data.getString("choice"),ai.teammoon.pli.domain.DestinationChoice::class.java)}.getOrNull();val request=msg.data.getString("requestId");if(choice!=null&&request!=null)scope.launch{runCatching{DataContract.destinations(listOf(choice));source?.requestRoute(choice,request)}}}
        else if(msg.what==4)scope.launch{runCatching{source?.cancelRoute()}}
        else if(msg.what==5){val name=msg.data.getString("name");val lat=msg.data.getDouble("lat",Double.NaN);val lon=msg.data.getDouble("lon",Double.NaN);if(name!=null&&lat.isFinite()&&lon.isFinite()&&kotlin.math.abs(lat)<=90&&kotlin.math.abs(lon)<=180)scope.launch{runCatching{source?.addWaypoint(name,lat,lon)}}}
        true
    })
    private fun emit(kind:String,text:String=""){
        try{peer?.send(Message.obtain(null,100).apply{data=Bundle().apply{putString("kind",kind);putString("text",text);putString("instance",id);putInt("pid",android.os.Process.myPid())}})}catch(e:RemoteException){stopSelf()}
    }
    override fun onBind(intent:Intent)=inbox.binder
    override fun onDestroy(){source?.close();scope.cancel();main.removeCallbacksAndMessages(null);super.onDestroy()}
}
