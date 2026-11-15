package ai.teammoon.pli

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.net.Uri
import android.os.ParcelFileDescriptor
import com.google.gson.Gson
import java.io.FileNotFoundException
import kotlin.concurrent.thread
import android.graphics.Bitmap
import android.graphics.Canvas
import android.os.Handler
import android.os.Looper
import java.io.ByteArrayOutputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Shell-only read access. The web server publishes only the selected demo fields. */
class DemoStateProvider:ContentProvider(){
    override fun onCreate()=true
    override fun getType(uri:Uri)="application/json"
    override fun call(method:String,arg:String?,extras:android.os.Bundle?):android.os.Bundle{
        context!!.enforceCallingPermission(android.Manifest.permission.DUMP,"Project session control")
        if(method=="threads")return android.os.Bundle().apply{putString("main",Thread.getAllStackTraces().entries.firstOrNull{it.key.name=="main"}?.value?.joinToString("\n"))}
        require(method=="session");val app=context!!.applicationContext as PliApplication;app.awaitInitialized()
        app.onMain{when(arg){
            "provision_public"->app.provisionPublic()
            "confirm_reboot"->app.confirmGuestReboot(extras?.getInt("previousBoot")?:-1)
            "preview"->app.preview()
            "private"->app.leaveDemo()
            "prepare"->app.prepareSession(requireNotNull(extras?.getString("session")))
            "heartbeat"->app.serverHeartbeat(requireNotNull(extras?.getString("session")))
            "begin"->app.beginSession(requireNotNull(extras?.getString("session")))
            "end"->app.endSession(extras?.getString("session"))
            "personal"->app.prepareSession(java.util.UUID.randomUUID().toString(),false)
            "cancel_route"->app.cancelRoute()
            "remove_window"->{val activity=MainActivity.windowOwner.get()?:error("APP_NOT_VISIBLE");check(activity.window.decorView===app.previewView.get());activity.finishAndRemoveTask()}
            else->error("UNSUPPORTED_ACTION")
        }}
        return android.os.Bundle().apply{putString("status",app.state.value.sessionStatus)}
    }
    override fun openFile(uri:Uri,mode:String):ParcelFileDescriptor{
        (context!!.applicationContext as PliApplication).awaitInitialized()
        if(uri.path=="/plan-active"){
            if(mode=="r"){val value=ai.teammoon.pli.data.PlanDocuments.active(context!!)?:throw FileNotFoundException();val pipe=ParcelFileDescriptor.createPipe();thread(isDaemon=true){runCatching{ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use{it.write(value.toByteArray())}}};return pipe[0]}
            require(mode=="w");val pipe=ParcelFileDescriptor.createPipe();thread(isDaemon=true){runCatching{val bytes=ParcelFileDescriptor.AutoCloseInputStream(pipe[0]).use{input->val out=ByteArrayOutputStream();val b=ByteArray(9);var n=input.read(b);while(n>0){require(out.size()+n<=8);out.write(b,0,n);n=input.read(b)};out.toByteArray()};ai.teammoon.pli.data.PlanDocuments.select(context!!,String(bytes,Charsets.UTF_8))}};return pipe[1]
        }
        if(uri.path=="/destinations"){
            val app=context!!.applicationContext as PliApplication
            if(mode=="r"){val bytes=Gson().toJson(app.destinationConfig()).toByteArray();val pipe=ParcelFileDescriptor.createPipe();thread(isDaemon=true){runCatching{ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use{it.write(bytes)}}};return pipe[0]}
            require(mode=="w");val pipe=ParcelFileDescriptor.createPipe()
            thread(isDaemon=true){runCatching{val bytes=ParcelFileDescriptor.AutoCloseInputStream(pipe[0]).use{input->val out=ByteArrayOutputStream();val buf=ByteArray(1024);var n=input.read(buf);while(n>0){require(out.size()+n<=16384);out.write(buf,0,n);n=input.read(buf)};out.toByteArray()};val o=com.google.gson.JsonParser.parseString(String(bytes,Charsets.UTF_8)).asJsonObject;val values=o["destinations"].asJsonArray.map{Gson().fromJson(it,ai.teammoon.pli.domain.DestinationChoice::class.java)};app.replaceDestinations(values,o["revision"].asLong,o["requestId"].asString)}}
            return pipe[1]
        }
        if(uri.path=="/private-summary"&&mode=="r"){
            val app=context!!.applicationContext as PliApplication;val bytes=Gson().toJson(app.privateSummary()).toByteArray();val pipe=ParcelFileDescriptor.createPipe()
            thread(isDaemon=true){runCatching{ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use{it.write(bytes)}}};return pipe[0]
        }
        if(uri.path=="/family-query"&&mode=="r"){
            val app=context!!.applicationContext as PliApplication
            val bytes=Gson().toJson(if(!app.demoActive)app.familyQuery else null).toByteArray();val pipe=ParcelFileDescriptor.createPipe()
            thread(isDaemon=true){runCatching{ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use{it.write(bytes)}}};return pipe[0]
        }
        if(uri.path=="/family-answer"&&mode=="w"){
            val app=context!!.applicationContext as PliApplication;check(!app.demoActive);val pipe=ParcelFileDescriptor.createPipe()
            thread(isDaemon=true){runCatching{val bytes=ParcelFileDescriptor.AutoCloseInputStream(pipe[0]).use{input->val out=ByteArrayOutputStream();val buffer=ByteArray(2048);var n=input.read(buffer);while(n>0){require(out.size()+n<=512*1024);out.write(buffer,0,n);n=input.read(buffer)};out.toByteArray()};require(bytes.size<=512*1024);app.acceptFamily(Gson().fromJson(String(bytes,Charsets.UTF_8),ai.teammoon.pli.domain.FamilyAnswer::class.java))}};return pipe[1]
        }
        if(uri.path in listOf("/plan-text","/plan-image")&&mode=="r")return ParcelFileDescriptor.open(java.io.File(context!!.filesDir,if(uri.path=="/plan-image")"plan-input.jpg"else"plan-input.txt"),ParcelFileDescriptor.MODE_READ_ONLY)
        if(uri.path in listOf("/plan-text","/plan-image")&&mode=="w")return importDocument(uri.path=="/plan-image")
        if(uri.path in listOf("/plans","/family")&&mode=="w")return importPlans(uri.path=="/family")
        if(uri.path=="/integration"&&mode=="r"){
            val app=context!!.applicationContext as PliApplication;val pipe=ParcelFileDescriptor.createPipe()
            thread(isDaemon=true){runCatching{ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use{it.write(Gson().toJson(mapOf("revision" to app.importRevision,"count" to app.importedPlans,"error" to app.importError,"planSha256" to app.planUploadSha,"receipt" to app.importReceipt,"storeRevision" to app.privateRevision)).toByteArray())}}};return pipe[0]
        }
        if(uri.path in listOf("/frame","/frames")&&mode=="r")return previewFrame(uri.path=="/frames")
        if(uri.path!="/state"||mode!="r")throw FileNotFoundException()
        val app=context!!.applicationContext as PliApplication
        val s=app.state.value;val r=app.viewBounds
        val data=mapOf("heard" to s.heard,"audience" to s.audience,"answerSource" to s.answerSource,"requestedText" to s.requestedText,"phase" to s.phase.name,"game" to s.game.name,"title" to s.title,"speech" to s.speech,"modelReady" to s.modelReady,"ttsReady" to s.ttsReady,"quiet" to s.quiet,"correct" to s.correct,"answered" to s.answered,"question" to s.question?.spoken,"presentation" to s.presentation,"hasView" to (app.previewView.get()?.isAttachedToWindow==true),"demo" to s.demo,"active" to (s.sessionStatus in listOf("PREPARING","ACTIVE","STOPPING")),"bounds" to listOf(r.left,r.top,r.right,r.bottom),"focused" to s.focused,"visible" to s.visible,"gear" to s.vehicle.gear,"speedKmh" to s.vehicle.speedKmh,"error" to s.error,"sessionId" to s.sessionId,"bootId" to s.bootId,"deviceBootCount" to app.deviceBootCount,"epoch" to s.epoch,"stateRevision" to s.stateRevision,"serviceInstanceId" to s.serviceInstanceId,"sessionStatus" to s.sessionStatus,"capture" to s.capture,"recognition" to s.recognition,"playback" to s.playback,"focus" to s.focus,"backend" to s.backend,"appHeartbeatAgeMs" to (android.os.SystemClock.elapsedRealtime()-app.mainHeartbeat),"voiceHeartbeatAgeMs" to app.voiceHeartbeat.let{beat->if(beat>0)android.os.SystemClock.elapsedRealtime()-beat else null},"expiresInMs" to if(s.expiresAtElapsed>0)(s.expiresAtElapsed-android.os.SystemClock.elapsedRealtime()).coerceAtLeast(0) else null,"stopReceipt" to s.stopReceipt)
        val enriched=data+mapOf("vehicleEvent" to s.vehicleEvent,"vehicleEventRevision" to s.vehicleEventRevision,"chargingActive" to s.vehicle.chargingActive,"cabinTemperatureC" to s.vehicle.cabinTemperatureC,"cabinTemperatureArea" to s.vehicle.cabinTemperatureArea,"cabinTemperatureAt" to s.vehicle.cabinTemperatureAt,"captureFrames" to capturedFrames,"drawMicros" to drawMicros,"publicOnly" to app.publicOnly,"intentRevision" to s.intentRevision,"destinationPage" to s.destinationPage,"readingPage" to s.readingPage,"readingHasMore" to s.readingHasMore,"viewDisplayId" to app.previewView.get()?.display?.displayId,"panel" to  s.panel,"abacusHint" to  s.abacusHint,"routeStatus" to  s.vehicle.routeStatus,"memoryCount" to  s.memories.size,"routeActive" to s.vehicle.routeActive,"spokenSequence" to s.spokenSequence,"playbackStartedAtElapsed" to s.playbackStartedAtElapsed,"interruptPartialAtElapsed" to s.interruptPartialAtElapsed,"interruptStoppedAtElapsed" to s.interruptStoppedAtElapsed,"deviceElapsedMs" to android.os.SystemClock.elapsedRealtime())
        val agent=mapOf("agentBusy" to s.agentBusy,"agentSteps" to s.agentSteps.map{mapOf("id" to it.id,"label" to it.label,"state" to it.state,"detail" to it.detail.take(120),"ms" to it.ms)},"album" to s.album?.let{mapOf("title" to it.title,"mode" to it.mode,"index" to it.index,"count" to it.photos.size)},"edge" to mapOf("asr" to ai.teammoon.pli.edge.EdgeAi.asrEngine,"llm" to ai.teammoon.pli.edge.EdgeAi.llmModel.substringBefore('.'),"healthy" to ai.teammoon.pli.edge.EdgeAi.healthy(),"albumPhotos" to (ai.teammoon.pli.edge.EdgeAi.album?.photos?.size?:0),"avatar" to (s.avatarPath!=null)))
        val bytes=Gson().toJson(enriched+agent).toByteArray(Charsets.UTF_8);val pipe=ParcelFileDescriptor.createPipe()
        thread(name="pli-state",isDaemon=true){runCatching{ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use{it.write(bytes)}}}
        return pipe[0]
    }
    private fun importPlans(family:Boolean):ParcelFileDescriptor{
        val app=context!!.applicationContext as PliApplication;val pipe=ParcelFileDescriptor.createPipe()
        thread(name="pli-plan-import",isDaemon=true){
            runCatching{
                val bytes=ParcelFileDescriptor.AutoCloseInputStream(pipe[0]).use{input->val out=ByteArrayOutputStream();val buffer=ByteArray(4096);var count=input.read(buffer);while(count>0){require(out.size()+count<=2*1024*1024);out.write(buffer,0,count);count=input.read(buffer)};out.toByteArray()}
                require(family){"FAMILY_BATCH_REQUIRED"}
                val batch=Gson().fromJson(String(bytes,Charsets.UTF_8),ai.teammoon.pli.domain.ImportBatch::class.java)
                app.importExternalPlans(batch.copy(facts=batch.facts?:emptyList()))
            }.onFailure{app.importError="일정 형식을 확인해 주세요.";app.importRevision++}
        }
        return pipe[1]
    }
    private fun importDocument(image:Boolean):ParcelFileDescriptor{
        check(!(context!!.applicationContext as PliApplication).publicOnly){"PUBLIC_ONLY_INSTALLATION"}
        val app=context!!.applicationContext as PliApplication;val pipe=ParcelFileDescriptor.createPipe()
        thread(name="pli-document",isDaemon=true){
            val temp=java.io.File.createTempFile("plan-input-",".tmp",context!!.filesDir)
            runCatching{
                val digest=java.security.MessageDigest.getInstance("SHA-256");var total=0
                ParcelFileDescriptor.AutoCloseInputStream(pipe[0]).use{input->temp.outputStream().use{output->val buffer=ByteArray(8192);var count=input.read(buffer);while(count>0){total+=count;require(total<=if(image)8*1024*1024 else 65536);digest.update(buffer,0,count);output.write(buffer,0,count);count=input.read(buffer)}}}
                require(total>0)
                val expected=digest.digest().joinToString(""){"%02x".format(it)}
                ai.teammoon.pli.data.PlanDocuments.commit(context!!,image,temp,expected){app.documentResult(expected,null)}
            }.onFailure{temp.delete();app.documentResult(null,"계획안 파일을 확인해 주세요.")}
            temp.delete()
        }
        return pipe[1]
    }
    @Volatile private var capturedFrames=0L
    @Volatile private var drawMicros=0L
    private fun previewFrame(streaming:Boolean):ParcelFileDescriptor{
        val app=context!!.applicationContext as PliApplication
        if(!app.demoActive||!app.state.value.presentation||!app.state.value.visible)throw FileNotFoundException()
        val pipe=ParcelFileDescriptor.createPipe()
        val running=java.util.concurrent.atomic.AtomicBoolean(true)
        val free=java.util.concurrent.ArrayBlockingQueue<Bitmap>(2)
        val ready=java.util.concurrent.ArrayBlockingQueue<Bitmap>(1)
        val buffers=mutableListOf<Bitmap>()
        val handler=Handler(Looper.getMainLooper())
        val ownerEpoch=app.state.value.epoch
        var previous=0L
        lateinit var callback:android.view.Choreographer.FrameCallback
        callback=android.view.Choreographer.FrameCallback{time->
            if(running.get()){
                val view=app.previewView.get()
                if(view==null||!app.canCapture(view)||app.state.value.epoch!=ownerEpoch||view.width<=0||view.height<=0)running.set(false)
                else if(time-previous>=32_000_000L){
                    previous=time
                    val width=960;val height=(view.height.toFloat()/view.width*width).toInt().coerceIn(1,1200)
                    if(buffers.isEmpty())repeat(2){Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888).also{buffers.add(it);free.offer(it)}}
                    if(buffers[0].height!=height)running.set(false)
                    else free.poll()?.let{bitmap->
                        try{val started=System.nanoTime();val canvas=Canvas(bitmap);canvas.drawColor(0xFF050819.toInt());canvas.scale(width.toFloat()/view.width,height.toFloat()/view.height);view.draw(canvas);drawMicros=(System.nanoTime()-started)/1000
                            if(running.get()&&app.canCapture(view)&&app.state.value.epoch==ownerEpoch){if(!ready.offer(bitmap))free.offer(bitmap)}else free.offer(bitmap)
                        }catch(e:RuntimeException){free.offer(bitmap);running.set(false)}
                    }
                }
                if(running.get())android.view.Choreographer.getInstance().postFrameCallback(callback)
            }
        }
        handler.post{android.view.Choreographer.getInstance().postFrameCallback(callback)}
        thread(name="pli-frame-encode",isDaemon=true){
            try{java.io.DataOutputStream(ParcelFileDescriptor.AutoCloseOutputStream(pipe[1])).use{output->
                val bytes=ByteArrayOutputStream(128*1024)
                do{
                    val bitmap=ready.poll(3,TimeUnit.SECONDS)?:break
                    try{
                        if(!running.get()||!app.demoActive||app.state.value.epoch!=ownerEpoch)break
                        bytes.reset();check(bitmap.compress(Bitmap.CompressFormat.JPEG,79,bytes))
                        if(!running.get()||!app.demoActive||app.state.value.epoch!=ownerEpoch)break
                        if(streaming)output.writeInt(bytes.size());bytes.writeTo(output);output.flush();capturedFrames++
                    }finally{free.offer(bitmap)}
                }while(streaming&&running.get())
            }}catch(e:Exception){/* A closed reader cancels its producer. */}
            finally{running.set(false);handler.post{android.view.Choreographer.getInstance().removeFrameCallback(callback);buffers.forEach{it.recycle()};buffers.clear();free.clear();ready.clear()}}
        }
        return pipe[0]
    }
    override fun query(uri:Uri,projection:Array<out String>?,selection:String?,selectionArgs:Array<out String>?,sortOrder:String?):Cursor?=null
    override fun insert(uri:Uri,values:ContentValues?):Uri?=throw UnsupportedOperationException()
    override fun delete(uri:Uri,selection:String?,selectionArgs:Array<out String>?):Int{
        if(uri.path !in listOf("/plan-text","/plan-image","/plan-active"))throw UnsupportedOperationException()
        return if(java.io.File(context!!.filesDir,when(uri.path){"/plan-image"->"plan-input.jpg";"/plan-active"->"plan-active.txt";else->"plan-input.txt"}).delete())1 else 0
    }
    override fun update(uri:Uri,values:ContentValues?,selection:String?,selectionArgs:Array<out String>?):Int=throw UnsupportedOperationException()
}
