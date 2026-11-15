package ai.teammoon.pli.domain

import java.time.LocalDate
import java.util.UUID

enum class Mood { HAPPY, EXCITED, THINKING, SLEEPY, QUIET }
enum class VoicePhase { PREPARING, QUEUED, LISTENING, SPEAKING, QUIET, NAVIGATION, ERROR, PERMISSION, STOPPING, STOPPED, RECOVERING }
enum class Game(val title: String) { FRIEND("오늘의 작은 모험"), MATH("마음속 주판"), ENGLISH("주고받는 영어"), NATURE("작은 숲 탐험가"), STORY("우리의 하루 이야기"), WORDCHAIN("끝말잇기"), RIDDLE("수수께끼") }
/** One visible step of the edge agent (plan, tool, observation, answer). */
data class AgentStep(val id:String,val label:String,val state:String,val detail:String="",val ms:Int=0)
/** A photo from the family album on the edge computer, cached locally for display only. */
data class AlbumPhoto(val id:String,val path:String,val caption:String="",val focusX:Float=.5f,val focusY:Float=.45f)
/** GRID = 사진 보기, STORY = 엣지 AI가 만든 앨범을 한 장씩 넘겨 보기. */
data class AlbumView(val title:String,val child:String,val photos:List<AlbumPhoto>,val mode:String="GRID",val index:Int=0,val createdBy:String="")
data class ChildProfile(val name: String = "친구", val age: Int = 5, val school: String = "시연 유치원", val volume: Float = 0.7f)
fun childAddress(name:String):String {val last=name.lastOrNull();val vowel=last==null||last !in '가'..'힣'||(last.code-'가'.code)%28==0;return name+if(vowel)"야"else"아"}
fun topicParticle(word:String):String{val last=word.lastOrNull();return word+if(last!=null&&last in '가'..'힣'&&(last.code-'가'.code)%28!=0)"은"else"는"}
data class Plan(val id: String = UUID.randomUUID().toString(), val date: String, val title: String, val preparation: String = "", val origin:String="MANUAL", val sourceScope:String?=null, val sourceEventId:String?=null)
data class Memory(val id: String = UUID.randomUUID().toString(), val date: String, val destination: String, val kilometers: Float?, val correct: Int, val answered: Int, val note: String = "")
data class DestinationChoice(val id:String,val name:String,val latitude:Double,val longitude:Double,val address:String="")
data class SavedData(val version: Int = 4, val profile: ChildProfile = ChildProfile(), val plans: List<Plan> = listOf(Plan(id="seed:forest",date=LocalDate.now().toString(), title="가을 숲에서 도토리 찾기",preparation="운동화와 물병",origin="DEMO_SEED")), val memories: List<Memory> = emptyList(), val revision:Long=0, val batches:List<ImportReceipt> = emptyList(), val sourceSequences:Map<String,Long> = emptyMap(), val facts:List<FamilyFact> = emptyList(), val activeSourceScope:String?=null, val destinations:List<DestinationChoice> = emptyList())
/** Retain every imported scope in storage; read only the selected scope and personal plans. */
fun SavedData.currentPlans(includeSamples:Boolean=false):List<Plan> = plans.filter{(includeSamples||it.origin!="DEMO_SEED")&&(it.origin!="KIDSNOTE"||it.sourceScope==activeSourceScope)}
data class VehicleState(val connected: Boolean = false, val source: String = "차량 연결 중", val gear: String = "—", val speedKmh: Float? = null, val battery: Int? = null, val odometerKm: Float? = null, val destination: String? = null, val minutesRemaining: Int? = null, val uxRestricted: Boolean = false, val chargingConnected:Boolean?=null,val chargingActive:Boolean?=null, val altitudeMeters:Double?=null, val routeRequestId:String?=null, val routeStatus:String="IDLE",val destinationLatitude:Double?=null,val destinationLongitude:Double?=null,val routeActive:Boolean?=null,val cabinTemperatureC:Float?=null,val cabinTemperatureArea:Int?=null,val cabinTemperatureAt:Long=0,val latitude:Double?=null,val longitude:Double?=null,val demoTrip:Boolean=false)
fun VehicleState.publicView()=copy(destination=null,minutesRemaining=null,routeRequestId=null,routeStatus="IDLE",destinationLatitude=null,destinationLongitude=null,routeActive=null)
data class ConversationState(
    val phase: VoicePhase = VoicePhase.PREPARING,
    val title: String = "너의 목소리를 만날 준비 중이야.",
    val speech: String = "플리와 함께할 작은 모험을 준비하고 있어요.",
    val spokenSequence:Long=0,
    val playbackStartedAtElapsed:Long=0,
    val interruptPartialAtElapsed:Long=0,
    val interruptStoppedAtElapsed:Long=0,
    val heard: String = "",
    val partial: String = "",
    val mood: Mood = Mood.HAPPY,
    val game: Game = Game.FRIEND,
    val question: Question? = null,
    val modelReady: Boolean = false,
    val ttsReady: Boolean = false,
    val status: String = "음성 모델 준비 중",
    val quiet: Boolean = false,
    val correct: Int = 0,
    val answered: Int = 0,
    val profile: ChildProfile = ChildProfile(),
    val todayPlan: Plan? = null,
    val memories: List<Memory> = emptyList(),
    val vehicle: VehicleState = VehicleState(),
    val tripActive: Boolean = false,
    val sessionId:String?=null,
    val bootId:String="",
    val epoch:Long=0,
    val stateRevision:Long=0,
    val serviceInstanceId:String?=null,
    val presentation:Boolean=false,
    val focused:Boolean=false,
    val visible:Boolean=false,
    val demo:Boolean=false,
    val sessionStatus:String="STOPPED",
    val capture:String="STOPPED",
    val recognition:String="STOPPED",
    val playback:String="IDLE",
    val focus:String="NONE",
    val audience:String="FAMILY",
    val answerSource:String="",
    val panel:String="BRIEF",
    val abacusHint:Boolean=false,
    val destinationChoices:List<DestinationChoice> = emptyList(),
    val selectedDestination:DestinationChoice?=null,
    val requestedText:String="",
    val vehicleEvent:String?=null,val vehicleEventRevision:Long=0,val intentRevision:Long=0,
    val destinationPage:Int=0,
    val readingPage:Int=0,
    val readingHasMore:Boolean=false,
    val backend:String="",
    val expiresAtElapsed:Long=0,
    val stopReceipt:StopReceipt?=null,
    val error: String? = null,
    val agentSteps:List<AgentStep> = emptyList(),
    val agentBusy:Boolean=false,
    val album:AlbumView?=null,
    val avatarPath:String?=null,
    val edge:String="",
    val card:StageCard?=null
)
/** A plan the edge AI composed from facts (what to pack, what to do on the way); items can be ticked off by voice. */
/** A place on the way that Pli suggested (OpenStreetMap pack); [added] once it is a waypoint. */
data class StopPlace(val name:String,val type:String,val latitude:Double,val longitude:Double,val minutesAway:Int,val detourMinutes:Int,val added:Boolean=false)
data class StageCard(val kind:String,val title:String,val subtitle:String,val sections:List<CardSection>,val checked:Set<String> = emptySet(),val game:String?=null,val place:StopPlace?=null){
    val items:List<CardItem> get()=sections.flatMap{it.items}
    val complete:Boolean get()=kind=="pack"&&items.isNotEmpty()&&items.all{it.label in checked}
}
data class CardSection(val title:String,val items:List<CardItem>)
data class CardItem(val icon:String,val label:String,val reason:String)
data class Question(val prompt: String, val spoken: String, val answer: String, val accepted: Set<String>, val hint: String, val game: Game)

// App-owned protocol. SDK callbacks do not carry utterance IDs.
data class StopReceipt(val sessionId:String?,val epoch:Long,val captureStopped:Boolean,val playbackStopped:Boolean,val focusReleased:Boolean,val instanceClosed:Boolean,val confirmedAt:Long,val error:String?=null)
data class ImportBatch(val batchId:String,val sourceScope:String,val sourceSequence:Long=0,val baseRevision:Long?=null,val windowStart:String?=null,val windowEnd:String?=null,val complete:Boolean=false,val plans:List<Plan> = emptyList(),val profile:ChildProfile?=null,val facts:List<FamilyFact> = emptyList())
data class ImportReceipt(val batchId:String,val received:Int=0,val rejected:Int=0,val duplicateInput:Int=0,val acceptedUnique:Int=0,val created:Int=0,val updated:Int=0,val unchanged:Int=0,val removed:Int=0,val committed:Boolean=false,val retainedFromBatch:Int=0,val storeRevision:Long=0,val retainedIdsDigest:String="",val error:String?=null,val inputDigest:String?=null)

data class FamilyFact(val topic:String,val date:String,val sourceScope:String,val text:String="",val sourceUrl:String="",val retrievedAt:Long=0,val status:String="EMPTY",val truncated:Boolean=false,val coverage:QueryCoverage?=null,val fullText:String?=null,val documentId:String?=null,val windowStart:String?=null,val windowEnd:String?=null)
data class FamilyQuery(val requestId:String,val bootId:String,val epoch:Long,val topic:String,val date:String,val scope:String?=null,val intentRevision:Long=0,val days:Int=1,val field:String="ALL")
data class FamilyAnswer(val requestId:String,val bootId:String,val epoch:Long,val fact:FamilyFact?=null,val error:String?=null,val intentRevision:Long=0,val snapshot:ImportBatch?=null)

data class QueryCoverage(val complete:Boolean=false,val pagesRead:Int=0,val hasMore:Boolean=false,val reason:String="UNKNOWN")
