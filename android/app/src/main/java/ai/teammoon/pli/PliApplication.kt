package ai.teammoon.pli

import android.app.Application
import android.graphics.Rect
import android.os.*
import android.view.View
import ai.teammoon.pli.data.*
import ai.teammoon.pli.domain.*
import ai.teammoon.pli.voice.ConversationController
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.lang.ref.WeakReference
import java.time.LocalDate
import java.util.UUID

/** Only the default process owns application state and persistent family data. */
class PliApplication:Application(){
    private val initialized=java.util.concurrent.CountDownLatch(1)
    fun awaitInitialized(){check(initialized.await(5,java.util.concurrent.TimeUnit.SECONDS)){"APP_INITIALIZING"}}
    lateinit var store:PliStore;private set
    private lateinit var journal:SessionJournal
    var deviceBootCount=0;private set
    val bootId=UUID.randomUUID().toString()
    private val mutableState=MutableStateFlow(ConversationState())
    val state=mutableState.asStateFlow()
    @Volatile private var privateData=PliStore.freshData()
    @Volatile private var demoData=SavedData()
    /** Public demo seed: the child named in the edge family album (face-matched photos), else the generic friend. */
    private fun demoSeed()=SavedData(profile=ChildProfile(name=ai.teammoon.pli.edge.EdgeAi.childName?:"친구"))
    /** Refresh the edge album off the main thread; the avatar and the child's name follow it. */
    fun refreshEdgeAlbum(){scope.launch(Dispatchers.IO){ai.teammoon.pli.edge.EdgeAi.checkHealth();val album=ai.teammoon.pli.edge.EdgeAi.loadAlbum(this@PliApplication);android.util.Log.i("PliEdge","album photos=${album?.photos?.size} avatar=${album?.avatarPath!=null} asr=${ai.teammoon.pli.edge.EdgeAi.asrEngine}");if(album!=null)main.post{reduce{it.copy(avatarPath=album.avatarPath)}}}}
    fun debugCommand(text:String?,event:String?):Boolean{
        if(!BuildConfig.DEBUG||controller==null||state.value.sessionStatus!="ACTIVE")return false
        text?.let{controller?.receive(it,fromTest=true)};event?.let{controller?.debugEvent(it)};return true
    }
    fun privateSummary()=synchronized(dataLock){mapOf("revision" to privateData.revision,"planIds" to privateData.plans.filter{it.origin=="KIDSNOTE"}.map{it.id},"facts" to privateData.facts.size,"profileDigest" to java.security.MessageDigest.getInstance("SHA-256").digest((privateData.profile.name+"|"+privateData.profile.age).toByteArray()).joinToString(""){"%02x".format(it)})}
    val privateRevision get()=privateData.revision
    val saved get()=if(state.value.demo)demoData else privateData
    val demoActive get()=state.value.demo
    val publicOnly get()=getSharedPreferences("provisioning",MODE_PRIVATE).getBoolean("publicOnly",false)
    fun provisionPublic(){
        awaitInitialized();check(controller==null&&state.value.sessionStatus=="STOPPED"){"SESSION_BUSY"}
        check(privateData.facts.isEmpty()&&privateData.memories.isEmpty()&&privateData.destinations.isEmpty()&&privateData.plans.none{it.origin!="DEMO_SEED"}){"PRIVATE_DATA_PRESENT"}
        check(getSharedPreferences("provisioning",MODE_PRIVATE).edit().putBoolean("publicOnly",true).commit()){"PROVISIONING_FAILED"}
    }
    val activeDemoSession get()=state.value.sessionId.takeIf{state.value.sessionStatus in setOf("PREPARING","ACTIVE","STOPPING","STOP_FAILED","UNKNOWN")}
    @Volatile var demoAwaiting=true
    @Volatile var viewBounds=Rect(853,90,2535,1300)
    val viewFocused get()=state.value.focused
    var previewView=WeakReference<View>(null)
    data class RenderStamp(val view:WeakReference<View>,val epoch:Long,val demo:Boolean,val presentation:Boolean)
    @Volatile var rendered:RenderStamp?=null;private set
    fun markRendered(view:View,s:ConversationState){if(previewView.get()===view)rendered=RenderStamp(WeakReference(view),s.epoch,s.demo,s.presentation)}
    fun canCapture(view:View):Boolean{val s=state.value;val r=rendered;return s.demo&&s.presentation&&s.visible&&r?.view?.get()===view&&r.epoch==s.epoch&&r.demo&&r.presentation}
    @Volatile var importRevision=0
    @Volatile var importedPlans=0
    @Volatile var importError:String?=null
    @Volatile var importReceipt:ImportReceipt?=null
    @Volatile var planUploadSha:String?=null
    private val dataLock=Any()
    fun documentResult(sha:String?,error:String?)=synchronized(dataLock){if(sha!=null)planUploadSha=sha;importError=error;importRevision++}
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
    private val main=Handler(Looper.getMainLooper())
    @Volatile var mainHeartbeat=0L;private set
    /** Last voice-service heartbeat (elapsedRealtime); kept out of the UI state so it never repaints the window. */
    @Volatile var voiceHeartbeat=0L
    private var vehicle:ai.teammoon.pli.vehicle.VehicleConnection?=null
    @Volatile private var lastVehicle=VehicleState()
    @Volatile private var destinationReceipt:Map<String,Any?>?=null
    fun connectVehicle(){if(vehicle!=null)return;vehicle=ai.teammoon.pli.vehicle.VehicleConnection(this,{value->lastVehicle=value;reduce{it.copy(vehicle=if(it.demo)ai.teammoon.pli.domain.DemoTrip.apply(value.publicView())else value)};controller?.onVehicleState(if(state.value.demo)state.value.vehicle else value)},{event->reduce{it.copy(vehicleEvent=event,vehicleEventRevision=it.vehicleEventRevision+1)};controller?.onVehicleEvent(event)}).also{it.start()}}
    fun requestRoute(choice:DestinationChoice,id:String){check(!demoActive&&state.value.sessionStatus=="ACTIVE");DataContract.destinations(listOf(choice));check(privateData.destinations.any{it==choice}){"DESTINATION_CHANGED"};connectVehicle();check(vehicle?.requestRoute(choice,id)==true){"VEHICLE_UNAVAILABLE"}}
    fun addWaypoint(place:ai.teammoon.pli.domain.StopPlace){check(!demoActive&&state.value.sessionStatus=="ACTIVE");check(vehicle?.addWaypoint(place)==true){"VEHICLE_UNAVAILABLE"}}
    fun cancelRoute(){check(!demoActive&&state.value.sessionStatus=="ACTIVE");check(vehicle?.cancelRoute()==true){"VEHICLE_UNAVAILABLE"}}
    fun reconnectVehicle(){val old=vehicle;if(old==null)connectVehicle()else old.close{ok->if(ok&&vehicle===old){vehicle=null;connectVehicle()}}}
    fun destinationConfig()=synchronized(dataLock){val v=lastVehicle;mapOf("revision" to  privateData.revision,"destinations" to  privateData.destinations,"receipt" to  destinationReceipt,"currentDestination" to  if(v.destination!=null&&v.destinationLatitude!=null&&v.destinationLongitude!=null)DestinationChoice("navigation-current",v.destination,v.destinationLatitude,v.destinationLongitude)else null)}
    fun replaceDestinations(values:List<DestinationChoice>,revision:Long,request:String)=synchronized(dataLock){try{check(!publicOnly){"PUBLIC_ONLY_INSTALLATION"};check(privateData.revision==revision){"REVISION_CONFLICT"};DataContract.destinations(values);privateData=store.save(DataContract.validate(privateData.copy(destinations=values,revision=revision+1)));if(!demoActive)refreshSaved();destinationReceipt=mapOf("requestId" to  request,"committed" to  true,"revision" to  privateData.revision)}catch(e:Exception){destinationReceipt=mapOf("requestId" to  request,"committed" to  false,"error" to (e.message?.takeIf{it.matches(Regex("[A-Z_]+"))}?:"STORE_ERROR"));throw e}}
    private val tick=object:Runnable{override fun run(){mainHeartbeat=SystemClock.elapsedRealtime();main.postDelayed(this,1000)}}
    private var controller:ConversationController?=null
    private var pendingStartEpoch:Long?=null
    override fun onCreate(){
        super.onCreate()
        if(getProcessName()!=packageName)return
        main.post(tick)
        refreshEdgeAlbum()
        deviceBootCount=android.provider.Settings.Global.getInt(contentResolver,android.provider.Settings.Global.BOOT_COUNT,0)
        journal=SessionJournal(this)
        var journalError=false
        val mark=try{journal.read()}catch(e:Exception){journalError=true;null}
        val orphan=journalError||(mark?.active==true&&mark.deviceBoot==deviceBootCount)
        store=PliStore(this)
        val error=try{privateData=store.load();null}catch(e:Exception){privateData=PliStore.freshData();"자료를 읽지 못했어요. 원본을 보존하고 저장을 멈췄어요."}
        reduce{it.copy(bootId=bootId,epoch=mark?.epoch?:0,sessionId=mark?.id,demo=if(orphan)mark?.public?:false else false,presentation=if(orphan)mark?.public?:false else false,sessionStatus=if(orphan)"UNKNOWN"else"STOPPED",capture=if(orphan)"UNKNOWN"else"STOPPED",profile=if(orphan&&mark?.public==true)demoData.profile else privateData.profile,todayPlan=if(orphan&&mark?.public==true)demoData.plans.firstOrNull()else privateData.currentPlans().lastOrNull{p->p.date==LocalDate.now().toString()},memories=if(orphan&&mark?.public==true)emptyList()else privateData.memories,error=error,phase=if(orphan)VoicePhase.RECOVERING else if(error==null)VoicePhase.STOPPED else VoicePhase.ERROR)}
        initialized.countDown()
        if(publicOnly&&!orphan&&state.value.sessionStatus=="STOPPED")preview()
    }
    /** A change that changes nothing is dropped: each new revision recomposes and repaints the whole
     *  software-rendered window, and repeated vehicle/focus callbacks were doing that ~11 times a second. */
    @Synchronized fun reduce(change:(ConversationState)->ConversationState){val old=state.value;val changed=change(old);if(changed==old)return;val next=changed.copy(stateRevision=old.stateRevision+1,bootId=bootId);mutableState.value=next}
    fun setView(focused:Boolean,bounds:Rect){viewBounds=bounds;reduce{it.copy(focused=focused)}}
    fun setVisible(value:Boolean){reduce{it.copy(visible=value)}}
    fun prepareWindowRecreation(){controller?.prepareWindowRecreation()}
    fun recoverRecreatedWindow(epoch:Long,session:String?){
        for(delay in listOf(2500L,6500L,11000L))main.postDelayed({
            val current=state.value
            if(current.epoch==epoch&&current.sessionId==session&&current.sessionStatus in setOf("PREPARING","ACTIVE")&&(!current.visible||previewView.get()?.isAttachedToWindow!=true)){
                runCatching{startActivity(packageManager.getLaunchIntentForPackage(packageName)!!.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP))}
            }
        },delay)
    }
    private fun refreshSaved(){reduce{current->val data=if(current.demo)demoData else privateData;current.copy(profile=data.profile,todayPlan=data.currentPlans(current.demo).lastOrNull{p->p.date==LocalDate.now().toString()},memories=data.memories,destinationChoices=data.destinations)}}
    fun commitSaved(data:SavedData,public:Boolean=demoActive,session:String?=state.value.sessionId)=synchronized(dataLock){
        check(public||!publicOnly){"PUBLIC_ONLY_INSTALLATION"}
        if(public)check(demoActive&&state.value.sessionId==session&&state.value.sessionStatus in setOf("PREPARING","ACTIVE")){"STALE_SESSION"}
        val base=if(public)demoData else privateData
        require(data.revision==base.revision){"REVISION_CONFLICT"}
        val next=DataContract.validate(data.copy(revision=base.revision+1))
        if(public){demoData=next;if(demoActive)refreshSaved()}else{val read=store.save(next);privateData=read;if(!demoActive)refreshSaved()}
    }
    fun importExternalPlans(batch:ImportBatch)=synchronized(dataLock){
        check(!publicOnly){"PUBLIC_ONLY_INSTALLATION"}
        try{val (candidate,receipt)=DataContract.merge(privateData,batch)
            val read=if(candidate==privateData)candidate else store.save(candidate)
            check(read.batches.any{it==receipt}){"READBACK_MISMATCH"};val ids=batch.plans.map{it.id}.toSet();check(DataContract.digest(read.plans.filter{it.id in ids})==receipt.retainedIdsDigest){"READBACK_MISMATCH"};privateData=read
            if(!demoActive)refreshSaved()
            importReceipt=receipt;importedPlans=receipt.retainedFromBatch;importError=null;importRevision++
        }catch(e:Exception){val code=e.message?.takeIf{it.matches(Regex("[A-Z_]+"))}?:"INVALID_DATA";importReceipt=ImportReceipt(batch.batchId,received=batch.plans.size,rejected=batch.plans.size,error=code,storeRevision=privateData.revision);importedPlans=0;importError=code;importRevision++}
    }
    fun preview(){check(controller==null&&state.value.sessionStatus=="STOPPED"){"SESSION_BUSY"};demoData=demoSeed();demoAwaiting=true;voiceHeartbeat=0L;reduce{ConversationState(bootId=bootId,avatarPath=it.avatarPath,epoch=it.epoch+1,demo=true,presentation=true,focused=it.focused,visible=it.visible,vehicle=it.vehicle.publicView(),quiet=true,profile=demoData.profile,todayPlan=demoData.plans.firstOrNull(),speech="",phase=VoicePhase.STOPPED,title="아이의 놀이, 부모의 등원 준비를 함께해요.")}}
    fun enterDemo()=preview()
    fun leaveDemo(){check(!publicOnly){"PUBLIC_ONLY_INSTALLATION"};check(controller==null&&state.value.sessionStatus=="STOPPED"){"SESSION_BUSY"};reduce{it.copy(demo=false,presentation=false,sessionId=null,quiet=false,vehicle=lastVehicle,phase=if(store.recoveryError==null)VoicePhase.STOPPED else VoicePhase.ERROR,error=if(store.recoveryError==null)null else"자료 복구가 필요해요. 원본은 보존되어 있어요.")};refreshSaved()}
    fun prepareSession(id:String,public:Boolean=true,awaitBegin:Boolean=public){
        check(public||!publicOnly){"PUBLIC_ONLY_INSTALLATION"}
        check(state.value.visible){"APP_NOT_VISIBLE"};check(controller==null&&state.value.sessionStatus=="STOPPED"){"SESSION_BUSY"}
        if(public&&!demoActive)preview()
        if(!public)check(store.recoveryError==null){"RECOVERY_REQUIRED"}
        if(!public&&demoActive)leaveDemo()
        val epoch=state.value.epoch+1;demoAwaiting=awaitBegin
        if(public)demoData=demoSeed()
        val data=saved
        voiceHeartbeat=0L;reduce{ConversationState(bootId=bootId,avatarPath=it.avatarPath,epoch=epoch,sessionId=id,demo=public,presentation=public,focused=it.focused,visible=it.visible,vehicle=it.vehicle,sessionStatus="PREPARING",capture="PREPARING",quiet=public,profile=data.profile,todayPlan=data.currentPlans(public).firstOrNull{p->p.date==LocalDate.now().toString()},memories=data.memories,expiresAtElapsed=if(public)SystemClock.elapsedRealtime()+180000 else 0)}
        pendingStartEpoch=epoch
        if(public)refreshEdgeAlbum()
        scope.launch{
            val committed=try{withContext(Dispatchers.IO){journal.write(SessionMark(id,epoch,deviceBootCount,true,public))}}catch(e:Exception){false}
            if(state.value.sessionId!=id||state.value.epoch!=epoch||state.value.sessionStatus!="PREPARING")return@launch
            if(!committed){reduce{it.copy(sessionStatus="STOP_FAILED",phase=VoicePhase.RECOVERING,error="시작 상태를 보존하지 못해 마이크를 열지 않았어요.")};return@launch}
            pendingStartEpoch=null
            val next=ConversationController(this@PliApplication,scope,id,epoch);controller=next;next.start()
        }

    }
    fun serverHeartbeat(id:String){check(state.value.demo&&state.value.sessionId==id){"SESSION_MISMATCH"};controller?.serverHeartbeat()}
    fun beginSession(id:String){check(state.value.sessionId==id&&state.value.sessionStatus in setOf("PREPARING","ACTIVE")){"SESSION_MISMATCH"};controller?.begin()}
    fun failSession(message:String){reduce{it.copy(error=message)};endSession()}
    fun endSession(id:String?=null){
        if(id!=null)check(id==state.value.sessionId){"SESSION_MISMATCH"}
        if(state.value.sessionStatus=="STOPPED")return
        if(state.value.sessionStatus=="STOPPING")return
        val neverOpened=controller==null&&pendingStartEpoch==state.value.epoch&&state.value.sessionStatus=="PREPARING"
        familyQuery=null;familyCallback=null
        demoAwaiting=true;reduce{it.copy(epoch=it.epoch+1,sessionStatus="STOPPING",phase=VoicePhase.STOPPING,capture="STOPPING",quiet=true,modelReady=false,ttsReady=false,requestedText="",title="마이크와 소리를 끄고 있어요.")}
        val active=controller
        if(active!=null)active.close() else finishStop(neverOpened)
    }
    fun voiceClosed(owner:ConversationController,ok:Boolean){
        if(controller!==owner)return
        controller=null;familyQuery=null;familyCallback=null
        if(state.value.sessionStatus!="STOPPING")reduce{it.copy(epoch=it.epoch+1,sessionStatus="STOPPING",quiet=true,modelReady=false,ttsReady=false)}
        finishStop(ok)
    }
    private fun finishStop(resourcesOk:Boolean){
        val stop=state.value
        scope.launch{
            val ok=resourcesOk&&try{withContext(Dispatchers.IO){journal.write(SessionMark(stop.sessionId?:"cancelled",stop.epoch,deviceBootCount,false,stop.demo))}}catch(e:Exception){false}
            if(state.value.epoch!=stop.epoch)return@launch
            reduce{it.copy(sessionStatus=if(ok)"STOPPED"else"STOP_FAILED",phase=if(ok)VoicePhase.STOPPED else VoicePhase.RECOVERING,capture=if(ok)"STOPPED"else"UNKNOWN",recognition=if(ok)"STOPPED"else"UNKNOWN",playback=if(ok)"IDLE"else"UNKNOWN",focus=if(ok)"NONE"else"UNKNOWN",modelReady=false,ttsReady=false,quiet=true,serviceInstanceId=null,stopReceipt=StopReceipt(it.sessionId,it.epoch,ok,ok,ok,ok,android.os.SystemClock.elapsedRealtime(),if(ok)null else "RESOURCE_UNCONFIRMED"),title=if(ok)"대화를 마쳤어요."else"종료 확인이 필요해요.")}
        }
    }
    fun confirmGuestReboot(previousBoot:Int){
        check(controller==null&&previousBoot>=0&&deviceBootCount>previousBoot)
        scope.launch{try{withContext(Dispatchers.IO){journal.confirmReboot(previousBoot,deviceBootCount)};reduce{it.copy(epoch=it.epoch+1,sessionId=null,sessionStatus="STOPPED",phase=VoicePhase.STOPPED,capture="STOPPED",playback="IDLE",focus="NONE",error=null)}}catch(e:Exception){reduce{it.copy(sessionStatus="STOP_FAILED",error="복구 결과를 보존하지 못했어요.")}}}
    }
    @Volatile var familyQuery:FamilyQuery?=null;private set
    private var acceptingFamily:String?=null
    private var familyCallback:((FamilyFact?,String?)->Unit)?=null
    fun familyFact(topic:String,date:String,allowStale:Boolean=false)=privateData.facts.filter{it.topic==topic&&it.date==date&&it.sourceScope==privateData.activeSourceScope&&(allowStale||System.currentTimeMillis()/1000-it.retrievedAt in 0..300)}.maxByOrNull{it.retrievedAt}
    fun invalidateFamilyQuery(){familyQuery=null;familyCallback=null}
    fun requestFamily(topic:String,date:String,intentRevision:Long=0,days:Int=1,field:String="ALL",callback:(FamilyFact?,String?)->Unit){
        check(!demoActive&&state.value.sessionStatus=="ACTIVE")
        val q=FamilyQuery(UUID.randomUUID().toString(),bootId,state.value.epoch,topic,date,privateData.activeSourceScope,intentRevision,days,field);familyQuery=q;familyCallback=callback
        main.postDelayed({if(familyQuery?.requestId==q.requestId){familyQuery=null;familyCallback=null;callback(null,"어린이집 소식 확인이 늦어지고 있어. 잠시 뒤 다시 물어봐 줘.")}},12000)
    }
    fun acceptFamily(answer:FamilyAnswer){scope.launch{
        val q=familyQuery?:return@launch
        if(acceptingFamily==q.requestId)return@launch
        if(answer.requestId!=q.requestId||answer.bootId!=bootId||answer.epoch!=state.value.epoch||answer.intentRevision!=q.intentRevision||demoActive)return@launch
        acceptingFamily=q.requestId
        var fact=answer.fact
        var error=answer.error
        if(answer.snapshot!=null)try{withContext(Dispatchers.IO){synchronized(dataLock){
            check(q.topic=="BRIEF"&&familyQuery?.requestId==q.requestId&&state.value.epoch==q.epoch&&!demoActive){"STALE_QUERY"}
            val batch=answer.snapshot;check(batch.complete&&batch.windowStart==q.date&&batch.windowEnd==java.time.LocalDate.parse(q.date).plusDays(q.days.toLong()-1).toString()&&(q.scope==null||batch.sourceScope==q.scope)){"SNAPSHOT_SCOPE"}
            privateData=store.save(DataContract.merge(privateData,batch.copy(baseRevision=privateData.revision)).first)
            fact=FamilyFact("BRIEF",q.date,batch.sourceScope,sourceUrl="https://www.kidsnote.com/service/schedule",retrievedAt=System.currentTimeMillis()/1000,status=if(batch.plans.isEmpty())"EMPTY"else"AVAILABLE",coverage=QueryCoverage(true,reason="SNAPSHOT_COMPLETE"),windowStart=batch.windowStart,windowEnd=batch.windowEnd)
        }}}catch(e:Exception){error="일정의 전체 조회와 저장을 확인하지 못했어요. 기존 자료는 보존했어요."}
        if(fact!=null)try{withContext(Dispatchers.IO){synchronized(dataLock){
            check(familyQuery?.requestId==q.requestId&&state.value.epoch==q.epoch&&!demoActive){"STALE_SESSION"}
            val received=requireNotNull(fact);DataContract.fact(received);check(q.topic==received.topic&&q.date==received.date&&(q.scope==null||q.scope==received.sourceScope)){"ANSWER_SCOPE"}
            val base=privateData;check(base.activeSourceScope==null||base.activeSourceScope==received.sourceScope){"STALE_SCOPE"}
            val next=base.copy(revision=base.revision+1,facts=(base.facts.filterNot{it.topic==received.topic&&it.date==received.date&&it.sourceScope==received.sourceScope}+received).sortedByDescending{it.retrievedAt}.take(100),activeSourceScope=received.sourceScope)
            privateData=store.save(next)
            fact=privateData.facts.first{it.topic==received.topic&&it.date==received.date&&it.sourceScope==received.sourceScope}
        }}}catch(e:Exception){error="확인한 자료를 보존하지 못해서 지금은 읽어줄 수 없어."}
        if(acceptingFamily==q.requestId)acceptingFamily=null
        if(familyQuery?.requestId!=q.requestId||state.value.epoch!=q.epoch||demoActive)return@launch
        if(!demoActive)refreshSaved()
        val callback=familyCallback;familyCallback=null;familyQuery=null;callback?.invoke(if(error==null)fact else null,error)
    }}
    fun onMain(action:()->Unit){
        if(Looper.myLooper()==Looper.getMainLooper()){action();return}
        val latch=java.util.concurrent.CountDownLatch(1);var failure:Throwable?=null;val expires=SystemClock.elapsedRealtime()+4500
        val work=Runnable{try{check(SystemClock.elapsedRealtime()<expires){"COMMAND_EXPIRED"};action()}catch(e:Throwable){failure=e}finally{latch.countDown()}}
        main.post(work);if(!latch.await(5,java.util.concurrent.TimeUnit.SECONDS)){main.removeCallbacks(work);error("APP_UNRESPONSIVE")};failure?.let{throw it}
    }
}

