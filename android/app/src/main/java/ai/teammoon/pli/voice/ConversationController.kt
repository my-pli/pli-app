package ai.teammoon.pli.voice

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import ai.teammoon.pli.*
import ai.teammoon.pli.domain.*
import ai.teammoon.pli.vehicle.PleosVehicleSource
import ai.teammoon.pli.data.PlanImporter
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.update
import java.io.File
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.UUID

/** One foreground microphone session owns recognition, speech, vehicle subscriptions and conversation. */
class ConversationController(private val app:PliApplication,private val lifecycleScope:CoroutineScope,private val session:String,private val epoch:Long){
    private val state get()=app.state.value
    private val main=Handler(Looper.getMainLooper())
    private lateinit var speaker:VoiceSessionConnection
    private var source:PleosVehicleSource?=null
    private var initialized=false
    private var welcomed=false
    private var awaitingSpeech=false
    private var intentRevision=0L
    private var reading:ReadingContext?=null
    private var provisionalQuiet=false
    private var quietRevision=0L
    private var provisionalQuietRevision=0L
    private var dialogueTurn:Int?=null
    private var round=0
    private var questionAnswered=false
    private var utteranceDuringSpeech=false
    private var lastUserText=""
    private var lastUserAt=0L
    private var lastVehicleSpeech=0L
    private var pendingVehicleCue:Pair<String,Long>?=null
    private var tripId:String?=null
    private var tripStartKm:Float?=null
    private var destination="어린이집"
    private var storyNote=""
    private var pendingPlans:List<Plan> = emptyList()
    private val contextEngine=JourneyContextEngine()
    private var pendingDestination:DestinationChoice?=null
    private var choiceExpires=0L
    private var routeRequestId:String?=null
    private var modeDestination:String?=null
    private var importJob:Job?=null
    private var lastQuestion=false
    private var nextQuestionJob:Job?=null
    private var debugJob:Job?=null
    fun start(){
        speaker=VoiceSessionConnection(app,lifecycleScope,session,epoch,app.bootId,
            onReady={ready,message->app.reduce{it.copy(ttsReady=ready,error=if(ready)it.error else message)};if(ready)welcomeWhenReady()},
            onSpeaking={speaking->app.reduce{it.copy(phase=when{it.quiet->VoicePhase.QUIET;speaker.navigation->VoicePhase.NAVIGATION;speaking->VoicePhase.SPEAKING;awaitingSpeech->VoicePhase.QUEUED;it.modelReady->VoicePhase.LISTENING;else->VoicePhase.PREPARING},partial="")}},
            onNavigation={active->nextQuestionJob?.cancel();app.reduce{it.copy(phase=if(active)VoicePhase.NAVIGATION else if(it.quiet)VoicePhase.QUIET else VoicePhase.LISTENING,status=if(active)"길 안내를 먼저 듣고 있어요" else "다시 너의 목소리를 듣고 있어요")}},
            onError={message->app.failSession(message)},
            onClosed={ok->app.voiceClosed(this,ok)},
            onState={reportedPlayback,focus->
                val playback=if(reportedPlayback=="IDLE"&&awaitingSpeech)"QUEUED"else reportedPlayback
                app.reduce{it.copy(interruptStoppedAtElapsed=if(playback=="IDLE"&&it.interruptPartialAtElapsed>it.interruptStoppedAtElapsed)android.os.SystemClock.elapsedRealtime()else it.interruptStoppedAtElapsed,playback=playback,focus=focus,phase=when{it.quiet->VoicePhase.QUIET;speaker.navigation->VoicePhase.NAVIGATION;playback in setOf("QUEUED","STARTING","WAITING_FOR_FOCUS")->VoicePhase.QUEUED;playback=="PLAYING"->VoicePhase.SPEAKING;it.modelReady->VoicePhase.LISTENING;else->VoicePhase.PREPARING})}
                if(playback=="IDLE")flushVehicleCue()
            },
            onHeartbeat={instance,at->app.voiceHeartbeat=at;app.reduce{it.copy(serviceInstanceId=instance)}},
            onSpoken={text->awaitingSpeech=false;app.reduce{it.copy(speech=text,spokenSequence=it.spokenSequence+1,playbackStartedAtElapsed=android.os.SystemClock.elapsedRealtime())}}
        )
        speaker.recognitionCallbacks(
            onReady={app.reduce{it.copy(modelReady=true,sessionStatus=if(app.demoAwaiting)"PREPARING" else "ACTIVE",phase=if(it.quiet)VoicePhase.QUIET else if(welcomed)it.phase else VoicePhase.PREPARING,status=if(welcomed)"네 목소리를 듣고 있어"else"음성 대화를 준비하고 있어요")};welcomeWhenReady()},
            onFinal={text->if(provisionalQuiet){provisionalQuiet=false;if(VoiceInterpreter.parse(text)!=VoiceCommand.Hush&&quietRevision==provisionalQuietRevision){speaker.setQuiet(false);utteranceDuringSpeech=false;lastUserText="";app.reduce{it.copy(quiet=false,phase=VoicePhase.LISTENING)}}else app.invalidateFamilyQuery()};val ignore=utteranceDuringSpeech&&!VoiceInterpreter.canInterrupt(text);if(BuildConfig.DEBUG)Log.i("PliAsr","final=$text, echo=$ignore");utteranceDuringSpeech=false;app.reduce{it.copy(partial="")};if(!ignore)receive(text)},
            onPartial={text->if(text.isNotBlank()&&speaker.speaking)utteranceDuringSpeech=true;if(VoiceInterpreter.canInterrupt(text,partial=true)){if(!state.quiet)app.reduce{it.copy(interruptPartialAtElapsed=android.os.SystemClock.elapsedRealtime())};if(!state.quiet){provisionalQuiet=true;provisionalQuietRevision=quietRevision};receive(text,partial=true)}else if(!speaker.speaking&&!speaker.navigation&&!utteranceDuringSpeech){app.reduce{it.copy(partial=text)}}},
            onLevel={level->MicLevel.value=level},
            onError={message->app.failSession(message)},onBackend={backend->app.reduce{it.copy(backend=backend)}},onSessionEnd={utteranceDuringSpeech=false;provisionalQuiet=false},onCapture={active->app.reduce{it.copy(capture=if(active)"ACTIVE" else "RESTARTING")}},onRecognitionState={value->app.reduce{it.copy(recognition=value)}}
        )
        speaker.setQuiet(app.demoAwaiting);speaker.start()
        if(BuildConfig.DEBUG)debugJob=lifecycleScope.launch{while(isActive){withContext(Dispatchers.IO){runCatching{app.store.debugSnapshot(app.state.value)}};delay(400)}}
    }
    fun debugEvent(event:String){if(!BuildConfig.DEBUG)return;if(event=="navigation_start")speaker.navigationForTest(true)else if(event=="navigation_end")speaker.navigationForTest(false)else onVehicleEvent(event)}
    fun serverHeartbeat(){speaker.serverHeartbeat()}
    fun prepareWindowRecreation(){speaker.prepareWindowRecreation()}
    fun begin(){
        if(!app.demoAwaiting)return
        app.demoAwaiting=false;speaker.setQuiet(false);welcomed=false;initialized=false
        app.reduce{it.copy(quiet=false,phase=if(it.modelReady)VoicePhase.LISTENING else VoicePhase.PREPARING,sessionStatus="ACTIVE")}
        welcomeWhenReady()
    }
    /** Pli speaks first only for this: driving a known route with time to spare, nothing else going on. */
    private val stopCheck=object:Runnable{override fun run(){if(state.sessionId!=session||state.epoch!=epoch)return;maybeOfferStop();if(!stopOffered)main.postDelayed(this,STOP_CHECK_MS)}}
    private fun maybeOfferStop(){
        val v=state.vehicle
        if(stopOffered||!initialized||state.sessionStatus!="ACTIVE"||state.quiet||speaker.speaking||speaker.navigation||state.agentBusy)return
        if(state.card!=null||state.game!=Game.FRIEND||state.panel!="BRIEF"||reading!=null||state.album!=null)return
        if(v.destination==null||v.destinationLatitude==null||v.latitude==null||(v.speedKmh?:0f)<STOP_MIN_KMH||(v.minutesRemaining?:0)<STOP_MIN_MINUTES)return
        if(android.os.SystemClock.elapsedRealtime()-state.playbackStartedAtElapsed<STOP_QUIET_MS||System.currentTimeMillis()-lastUserAt<STOP_QUIET_MS)return
        if(!app.demoActive&&!ai.teammoon.pli.edge.EdgeAi.healthy())return
        stopOffered=true;askAgent("",proactive=true)
    }
    private fun acceptStop(card:StageCard,place:StopPlace){
        if(!app.demoActive&&runCatching{app.addWaypoint(place)}.isFailure){say("경유지를 넣지 못했어요. 내비게이션 연결을 확인해 주세요.","경유지 추가 실패",Mood.THINKING);return}
        app.reduce{it.copy(card=card.copy(place=place.copy(added=true)))}
        val name=state.profile.name.takeIf{it.isNotBlank()&&it!="친구"}
        val doing=if(place.type=="library")"그림책 같이 고르자" else "놀이터에서 신나게 놀자"
        say("좋아요! ${place.name}${josa(place.name,"을","를")} 경유지로 넣었어요. ${place.minutesAway}분 뒤에 도착해요."+(name?.let{" ${it}${josa(it,"아","야")}, $doing!"}?:""),"경유지 추가",Mood.EXCITED)
    }
    private fun josa(word:String,withFinal:String,without:String):String{val c=word.lastOrNull()?:return without;return if(c in '가'..'힣'&&(c-'가')%28!=0)withFinal else without}
    private fun welcomeWhenReady(){
        if(app.demoAwaiting)return
        if(!welcomed&&state.modelReady&&state.ttsReady){welcomed=true;initialized=true;main.postDelayed(stopCheck,STOP_CHECK_MS)
            if(state.vehicle.gear=="D"&&!state.tripActive)startTrip()
            if(app.demoActive)say("준비됐어!","무엇이든 말해 봐.",Mood.HAPPY)
            else say("준비됐어!","오늘도, 너와 함께 가는 길.",Mood.HAPPY)
        }
    }
    private fun say(text:String,title:String=state.title,mood:Mood=Mood.HAPPY){
        if(state.sessionId!=session||state.epoch!=epoch||state.sessionStatus !in setOf("PREPARING","ACTIVE"))return
        awaitingSpeech=!state.quiet
        app.reduce{it.copy(requestedText=text,title=title,mood=mood,partial="",error=null,playback=if(it.quiet)it.playback else"QUEUED",phase=if(it.quiet)it.phase else VoicePhase.QUEUED)}
        if(!state.quiet)speaker.speak(text,state.profile.volume)
    }
    private fun save(data:SavedData,success:()->Unit={}){
        val public=app.demoActive;val sessionId=state.sessionId
        lifecycleScope.launch{try{withContext(Dispatchers.IO){app.commitSaved(data,public,sessionId)};if(state.sessionId==session&&state.epoch==epoch)success()}
            catch(e:Exception){if(state.sessionId==session&&state.epoch==epoch)say(if(e.message=="REVISION_CONFLICT")"다른 변경이 있어서 이번 요청은 저장하지 않았어. 다시 한 번 말해 줘."else"저장 결과를 확인하지 못했어. 다시 덮어쓰지 않고 자료를 보존했어.","자료 보존을 확인해 주세요.")}}
    }
    fun receive(text:String,partial:Boolean=false,fromTest:Boolean=false){
        if(app.demoAwaiting)return
        if(text.isBlank())return
        val now=System.currentTimeMillis()
        if(text==lastUserText&&now-lastUserAt<1300)return
        val command=VoiceInterpreter.parse(text,state.question.takeUnless{questionAnswered})
        if(command is VoiceCommand.Unrecognized&&reading==null&&state.panel !in setOf("DESTINATIONS","ENGLISH_TURN")&&state.game!=Game.STORY&&pendingPlans.isEmpty()&&!fromTest&&!app.demoActive&&!VoiceInterpreter.hasWakeWord(text)){app.reduce{it.copy(heard=text,partial="")};return}
        val interrupt=command is VoiceCommand.Hush||command is VoiceCommand.Stop||command is VoiceCommand.StopReading
        if(speaker.navigation&&!interrupt)return
        val albumNarration=state.panel=="ALBUM"&&state.album?.mode=="STORY"&&albumJob?.isActive==true
        if(speaker.speaking&&!interrupt&&!fromTest&&!albumNarration)return
        if(albumNarration&&speaker.speaking&&!partial){albumJob?.cancel();speaker.stop()}
        if(partial&&!interrupt)return
        if(state.quiet&&command !is VoiceCommand.Resume&&command !is VoiceCommand.Greet&&command !is VoiceCommand.Hush&&command !is VoiceCommand.Stop)return
        lastUserText=text;lastUserAt=now
        if(!partial||interrupt)app.reduce{it.copy(heard=text,partial="")}
        nextQuestionJob?.cancel()
        val sameReading=(command is VoiceCommand.Unrecognized&&reading!=null)||command in setOf(VoiceCommand.ReadNext,VoiceCommand.ReadPrevious,VoiceCommand.ReadStart,VoiceCommand.Repeat,VoiceCommand.Next)
        if(!partial&&command !is VoiceCommand.Prohibited&&command!=VoiceCommand.Resume&&command!=VoiceCommand.Hush&&!sameReading){
            intentRevision++;pendingVehicleCue=null;app.invalidateFamilyQuery();speaker.stop();reading=null
            app.reduce{it.copy(intentRevision=intentRevision,readingPage=0,readingHasMore=false)}
        }
        if(fromTest){utteranceDuringSpeech=false;speaker.stop()}
        if(!partial&&command !is VoiceCommand.Hush&&command !is VoiceCommand.Resume&&!albumIntent.containsMatchIn(text)){albumJob?.cancel();if(state.panel=="ALBUM")app.reduce{it.copy(panel="BRIEF",album=null)}}
        if(command is VoiceCommand.Play||command is VoiceCommand.Destination||command is VoiceCommand.Translate||command==VoiceCommand.SwapRoles||command==VoiceCommand.Album||command==VoiceCommand.Arrive||command==VoiceCommand.ImportPlan||command==VoiceCommand.Help){pendingDestination=null;app.reduce{it.copy(audience="CHILD",panel="BRIEF",selectedDestination=null)}}
        if(!partial){
            state.card?.let{card->
                if(card.kind=="stop"){
                    val place=card.place
                    if(place!=null&&!place.added&&STOP_NO.containsMatchIn(text)){app.reduce{it.copy(card=null)};say("알겠어요. 바로 ${state.vehicle.destination?:"목적지"}으로 갈게요.","바로 가요",Mood.HAPPY);return}
                    if(place!=null&&!place.added&&STOP_YES.containsMatchIn(text)){acceptStop(card,place);return}
                    if(place?.added==true&&STOP_YES.containsMatchIn(text)){say("신난다! 같이 가자!","${place.name}로 가요",Mood.EXCITED);return}
                }
                val ticked=StageCards.ticked(card,text)
                if(ticked.isNotEmpty()){tick(card,ticked);return}
                val game=card.game?.let{g->runCatching{Game.valueOf(g)}.getOrNull()}
                if(game!=null&&StageCards.accepts(text)){app.reduce{it.copy(card=null)};startSuggested(game);return}
                app.reduce{it.copy(card=null)}
            }
        }
        val toAgent=!partial&&!fromTest&&(app.demoActive||VoiceInterpreter.hasWakeWord(text))&&wantsAgent(command,text)
        if(toAgent)askAgent(text)else handle(command,text,partial)
        Log.i("PliConversation","${command.javaClass.simpleName}: ${state.game}, quiet=${state.quiet}, score=${state.correct}/${state.answered}")
    }
    private fun handle(command:VoiceCommand,text:String,partial:Boolean){
        when(command){
            VoiceCommand.Ambiguous->say("한 가지씩 다시 말해 주세요. 어느 날짜의 어떤 내용을 먼저 확인할까요?","요청을 확인해 주세요.")
            is VoiceCommand.Prohibited->say("알겠어요. 요청하지 않은 동작은 실행하지 않을게요.","대화를 이어가요.")
            VoiceCommand.EnglishDialogue->{dialogueTurn=0;app.reduce{it.copy(game=Game.ENGLISH,panel="BRIEF",audience="CHILD",question=null)};askQuestion()}
            is VoiceCommand.Unsupported->say(if(command.topic=="WORD")"그 단어는 아직 알려주기 어려워요. 나무나 사과로 문제를 내 줄래요?"else"아직 지원하지 않는 질문이에요. 일정이나 놀이를 물어봐 주세요.","다른 질문을 해 볼까요?")
            VoiceCommand.ReadNext->readMore(1)
            VoiceCommand.ReadPrevious->readMore(-1)
            VoiceCommand.ReadStart->readMore(0)
            VoiceCommand.StopReading->{reading=null;speaker.stop();app.reduce{it.copy(readingHasMore=false,readingPage=0)};say("읽기를 마쳤어요. 다른 질문을 해 주세요.","다음 이야기를 기다려요.")}
            is VoiceCommand.DestinationPage->destinationPage(command.delta)

            VoiceCommand.Growth->{val g=GrowthSummary.from(app.saved.memories);app.reduce{it.copy(audience="PARENT",panel="GROWTH",question=null,game=Game.FRIEND,answerSource="이 기기에 저장한 여정")};say("${if(app.demoActive)"공개 체험의 기록이에요. "else"이 기기에 저장한 기록이에요. "}도착 스탬프 ${g.stamps}개. ${g.kilometers?.let{"함께 달린 거리 ${String.format("%.1f",it)} 킬로미터. "}?:"차량 거리 정보가 없는 기록은 합산하지 않았어요. "}${g.accuracy?.let{"${g.answered}문제 중 ${g.correct}문제 성공, 정답률 ${it}퍼센트예요."}?:"아직 저장된 문제 기록이 없어요."}","차곡차곡, 우리 가족의 기록")}
            VoiceCommand.ChargingPlay->{play(Game.MATH);app.reduce{it.copy(panel="CHARGE")}}
            VoiceCommand.SwapRoles->{app.reduce{it.copy(audience="CHILD",panel="ENGLISH_TURN",game=Game.ENGLISH,question=null,abacusHint=false)};say("이번엔 네가 선생님이야! 나무는 영어로 뭐게, 처럼 플리에게 문제를 내 줘.","이번엔 네가 선생님!")}
            is VoiceCommand.Translate->{app.reduce{it.copy(audience="CHILD",panel="ENGLISH_TURN",game=Game.ENGLISH,question=null)};say("${command.english}! ${topicParticle(command.word)} 영어로 ${command.english}. 맞았어? 다른 문제도 내 줘!","${command.word} · ${command.english}",Mood.EXCITED)}
            VoiceCommand.DestinationOptions->offerDestinations()
            is VoiceCommand.ChooseDestination->selectDestination(command.choice)
            VoiceCommand.ConfirmDestination->confirmDestination()
            VoiceCommand.Hush->{awaitingSpeech=false;if(!partial){quietRevision++;intentRevision++;app.invalidateFamilyQuery();app.reduce{it.copy(intentRevision=intentRevision)}};speaker.setQuiet(true);app.reduce{it.copy(quiet=true,phase=VoicePhase.QUIET,title="잠깐 쉬어도 괜찮아.",speech="플리는 여기서 조용히 기다릴게.",mood=Mood.SLEEPY,status="다시 놀자고 말하면 돌아올게")}}
            VoiceCommand.Resume->{speaker.setQuiet(false);app.reduce{it.copy(quiet=false,phase=VoicePhase.LISTENING,status="네 목소리를 듣고 있어")};if(reading!=null)readCurrent()else if(questionAnswered&&state.question!=null)askQuestion()else say(state.question?.spoken?:"잘 쉬었어! 우리 다시 함께할까?","다시 만나서 반가워!",Mood.HAPPY)}
            VoiceCommand.Greet->{speaker.setQuiet(false);app.reduce{it.copy(quiet=false)};say("${childAddress(state.profile.name)}, 반가워! 오늘도 우리 같이 가자. 어떤 놀이를 해 볼까?","오늘도 만나서 반가워!")}
            is VoiceCommand.FamilyAsk->{
                val date=LocalDate.now(java.time.ZoneId.of("Asia/Seoul")).plusDays(command.dayOffset.toLong())
                val revision=intentRevision
                app.reduce{it.copy(game=Game.FRIEND,question=null,panel="BRIEF",selectedDestination=null,audience=if(command.parent)"PARENT"else"CHILD",answerSource=if(app.demoActive)"공개 체험용 샘플"else if(command.topic=="BRIEF")"저장된 일정·준비물"else"어린이집 소식 자료",title=if(command.topic=="BRIEF")"등원 준비, 말로 확인해요."else"어린이집 소식을 확인해요.")}
                if(app.demoActive){if(command.topic=="BRIEF")brief(date,command.days,command.field,false)else startReading(FamilyAnswers.sample(command.topic,date),"sample", "demo",command.parent)}
                else if(command.topic=="BRIEF"&&!command.refresh&&(app.saved.currentPlans().any{it.date>=date.toString()&&it.date<=date.plusDays(command.days.toLong()-1).toString()}||app.saved.facts.any{it.topic=="BRIEF"&&it.sourceScope==app.saved.activeSourceScope&&it.coverage?.complete==true&&it.windowStart!=null&&it.windowEnd!=null&&it.windowStart<=date.toString()&&it.windowEnd>=date.plusDays(command.days.toLong()-1).toString()&&System.currentTimeMillis()/1000-it.retrievedAt in 0..300}))brief(date,command.days,command.field,false)
                else{
                    val cached=if(command.topic=="BRIEF")null else app.familyFact(command.topic,date.toString())?.takeUnless{command.refresh||it.truncated&&it.documentId==null}
                    if(cached!=null)readFact(cached,command.parent)
                    else{
                        say("어린이집 소식을 확인하고 있어요. 잠시만 기다려 주세요.")
                        app.requestFamily(command.topic,date.toString(),revision,command.days,command.field){fact,error->
                            if(state.sessionId==session&&state.epoch==epoch&&intentRevision==revision&&!state.quiet){
                                if(fact!=null){if(command.topic=="BRIEF")brief(date,command.days,command.field,true)else readFact(fact,command.parent)}
                                else{
                                    val old=app.familyFact(command.topic,date.toString(),true)
                                    if(old!=null){app.reduce{it.copy(answerSource="마지막 확인 자료 · 새 조회 실패")};readFact(old,command.parent,"지금 새로 확인하지는 못했어요. ")}
                                    else say(error?:"어린이집 소식을 확인하지 못했어요. 가족 연결에서 다시 확인해 주세요.","확인하지 못한 내용을 만들지 않아요.")
                                }
                            }
                        }
                    }
                }
            }
            is VoiceCommand.Play->play(command.game)
            is VoiceCommand.Destination->{destination=command.name;startTrip();app.reduce{it.copy(game=command.game,question=null)};if(command.game==Game.MATH||command.game==Game.ENGLISH||command.game==Game.NATURE)play(command.game)else if(command.game==Game.STORY)play(Game.STORY)else{val plan=state.todayPlan;say("${childAddress(state.profile.name)}, ${command.name} 가는 길이구나. ${plan?.let{"오늘은 ${it.title}! ${it.preparation.takeIf(String::isNotBlank)?.let{p->"준비물 안내에는 $p 라고 적혀 있어."}?:""}"}?:"창밖에서 어떤 색이 보이는지 찾아볼까?"}","오늘은 어떤 모험이 기다릴까?")}}
            VoiceCommand.Next->{if(state.panel=="DESTINATIONS")destinationPage(1)else if(reading!=null)readMore(1)else if(lastQuestion&&state.game !in setOf(Game.FRIEND,Game.STORY))say("이제 곧 도착이라 새 문제는 다음 여정에서 이어 가자. 오늘 준비물이 궁금하면 물어봐 줘.","도착할 준비를 해요.")else if(state.game==Game.FRIEND)play(Game.NATURE)else if(state.game==Game.STORY)askStory()else askQuestion()}
            VoiceCommand.Hint->{state.question?.let{q->app.reduce{it.copy(abacusHint=true)};say(q.hint,"천천히 함께 생각해 보자.",Mood.THINKING)}?:say("숫자 놀이, 영어 퀴즈, 숲 놀이 중에서 골라 말해 줘.","무엇이든 함께해!")}
            VoiceCommand.Repeat->if(reading!=null)readCurrent()else say(state.question?.spoken?:state.speech,state.title,state.mood)
            is VoiceCommand.Answer->answer(command.value)
            VoiceCommand.Album->{val memories=app.saved.memories;val km=memories.mapNotNull{it.kilometers}.sum();val last=memories.firstOrNull();say(if(last==null)"우리의 첫 추억이 기다리고 있어. 함께 출발하고 도착하면 반짝이는 스탬프를 남겨 줄게."else"우리는 ${memories.size}번의 여정을 함께했어. ${if(km>0)"함께 달린 거리는 ${String.format("%.1f",km)} 킬로미터야. " else ""}가장 최근에는 ${last.destination}에 갔어. ${last.note}","차곡차곡, 우리 추억",Mood.EXCITED)}
            VoiceCommand.Arrive->finishTrip()
            is VoiceCommand.Name->{save(app.saved.copy(profile=app.saved.profile.copy(name=command.name))){say("${childAddress(command.name)}, 이름을 알려 줘서 고마워. 앞으로 다정하게 불러 줄게!","우리, 조금 더 가까워졌어.")}}
            is VoiceCommand.AddPlan->{if(app.saved.plans.size>=500)say("일정이 가득 찼어. 가족과 함께 지난 일정을 정리해 줘.")else{val plan=Plan(date=command.date,title=command.title);save(app.saved.copy(plans=app.saved.plans+plan)){say("${command.title}. 설레는 하루로 기억해 둘게!","기다려지는 하루를 담았어.")}}}
            is VoiceCommand.Volume->{val value=(state.profile.volume+command.change).coerceIn(.1f,1f);save(app.saved.copy(profile=state.profile.copy(volume=value))){speaker.adjustVolume(value);say(if(command.change>0)"조금 더 또렷하게 이야기할게."else"조금 더 작고 다정하게 이야기할게.","너에게 맞는 목소리로.")}}
            is VoiceCommand.Remember->{val latest=app.saved.memories.firstOrNull();if(latest!=null&&!state.tripActive)save(app.saved.copy(memories=app.saved.memories.mapIndexed{i,m->if(i==0)m.copy(note=command.note)else m})){storyNote=command.note;say("소중한 한마디를 추억에 담았어. $storyNote","오래 기억하고 싶은 순간.")}else{storyNote=command.note;say("이번 여정에서 기억할게. 도착하면 추억으로 남겨 줄게.","여정이 끝나면 추억에 담아요.")}}
            VoiceCommand.ImportPlan->{if(app.demoActive)say("공개 체험에서는 샘플 일정으로 함께할게. 오늘 뭐 해, 라고 말해 봐.","샘플 일정으로 체험해요.")else{app.reduce{it.copy(game=Game.FRIEND,question=null)};importPlan()}}
            VoiceCommand.Backup->{if(app.demoActive)say("공개 체험의 대화는 따로 보관하지 않아. 다른 놀이를 해 볼까?","체험 기록은 저장하지 않아요.")else lifecycleScope.launch{try{withContext(Dispatchers.IO){app.store.backup(app.saved)};say("우리의 소중한 추억을 잘 보관했어.","함께한 순간을 소중하게.")}catch(e:Exception){Log.e("PliStore","Backup failed",e);say("지금은 추억을 따로 보관하지 못했어. 잠시 뒤 다시 말해 줘.","추억은 플리 안에 담겨 있어.")}}}
            VoiceCommand.Help->{app.reduce{it.copy(answerSource="말하기 도움말")};say("오늘 준비물 알려줘, 최근 알림장 읽어줘, 또는 숫자 놀이 해줘, 라고 말해 주세요. 잠깐 쉬려면 조용히, 대화를 끝내려면 마이크 꺼, 라고 말하면 돼요.","말로 물어보세요.")}
            VoiceCommand.Stop->{speaker.setQuiet(true);app.reduce{it.copy(quiet=true,phase=VoicePhase.QUIET,status="대화를 마쳤어요",title="다음 여정에서 또 만나.",speech="마이크를 껐어요. 앱을 다시 열면 플리가 돌아와요.")};app.endSession()}
            is VoiceCommand.Unrecognized->{
                if(pendingPlans.isNotEmpty()&&VoiceInterpreter.compact(text) in setOf("응","네","맞아","저장해줘","일정저장해줘","좋아")){
                    val keys=app.saved.plans.map{"${it.date}|${it.title}"}.toSet();val new=pendingPlans.filter{"${it.date}|${it.title}" !in keys};if(app.saved.plans.size+new.size>500){say("일정이 가득 차 가져온 일정을 반영하지 못했어. 기존 일정은 유지했어.");return};save(app.saved.copy(plans=app.saved.plans+new)){pendingPlans=emptyList();say("확인한 ${new.size}개의 일정을 담았어. 기다려지는 하루가 생겼네!","내일이 더 기다려져.")}
                }else if(state.game==Game.STORY){storyNote=listOf(storyNote,command.text).filter(String::isNotBlank).joinToString(" · ").take(300);say(LearningCatalog.followup(command.text)?:"그랬구나. 네 이야기를 더 들려주고 싶으면 계속 말해 줘.","네 이야기를 듣는 게 좋아.",Mood.HAPPY)}
                else{app.reduce{it.copy(answerSource="말하기 도움말")};val retry=when{
                    state.panel=="DESTINATIONS"->if(pendingDestination!=null)"확인을 잘 듣지 못했어요. 맞으면 보호자 확인, 이라고 한 번 더 말해 주세요."else"선택을 잘 듣지 못했어요. 첫 번째로 갈래, 처럼 다시 말해 주세요."
                    reading!=null->"잘 듣지 못했어요. 더 읽어줘, 이전 내용, 또는 그만 읽어, 라고 말해 주세요."
                    state.panel=="ENGLISH_TURN"->"문제를 잘 듣지 못했어. 나무는 영어로 뭐야, 처럼 한 번 더 물어봐 줘."
                    else->"잘 듣지 못했어요. 오늘 준비물 알려줘, 또는 숫자 놀이 해줘, 처럼 한 가지씩 다시 말해 주세요."
                };say(retry,"다시 한번 말해 주세요.",Mood.THINKING)}
            }
        }
    }
    // ---- Edge agent ------------------------------------------------------------------
    private val packIntent=Regex("(챙겨|챙길|챙기|준비물|가방)")
    private val placeIntent=Regex("(숲|공원|학원|어린이집|유치원|집|할머니|할아버지|수영장|도서관|박물관|동물원|바다|놀이터|소풍)")
    private var stopOffered=false
    private val STOP_YES=Regex("(가\\s?볼까|가\\s?보자|가자|좋아|그래|응|들르자|들렀다|거기)")
    private val STOP_NO=Regex("(아니|괜찮아|다음에|그냥 ?가|안 ?갈래|싫어)")
    private val albumIntent=Regex("(사진|앨범|사진첩|포토 ?북|추억 ?책).*(보여|볼래|보자|만들|꾸며|열어|구경)|(만들|꾸며).*(앨범|사진첩)")
    private val history=ArrayDeque<Pair<String,String>>()
    private var agentJob:Job?=null
    private var albumJob:Job?=null
    /** Free questions, album requests and the edge-run word games go to the edge agent. */
    private fun wantsAgent(command:VoiceCommand,text:String):Boolean{
        if(command is VoiceCommand.Hush||command is VoiceCommand.Stop||command is VoiceCommand.Resume||command is VoiceCommand.Prohibited)return false
        if(albumIntent.containsMatchIn(text)&&!text.contains("성장"))return true
        if(state.game==Game.WORDCHAIN||state.game==Game.RIDDLE)return command !is VoiceCommand.Play&&command !is VoiceCommand.FamilyAsk&&command !is VoiceCommand.Growth
        if(command is VoiceCommand.Unsupported||command==VoiceCommand.Ambiguous)return true
        // A named place goes to the edge, which plans the way there (game, things to do, things to bring); a bare "출발" stays local.
        if(command is VoiceCommand.Destination&&placeIntent.containsMatchIn(text))return true
        if(command is VoiceCommand.FamilyAsk&&command.topic=="BRIEF"&&!command.parent&&packIntent.containsMatchIn(text))return true
        return command is VoiceCommand.Unrecognized&&reading==null&&state.panel !in setOf("DESTINATIONS","ENGLISH_TURN")&&state.game!=Game.STORY&&pendingPlans.isEmpty()
    }
    private fun live(revision:Long)=state.sessionId==session&&state.epoch==epoch&&intentRevision==revision&&state.sessionStatus=="ACTIVE"
    private fun moodOf(value:String)=runCatching{Mood.valueOf(value)}.getOrDefault(Mood.HAPPY)
    private fun remember(role:String,text:String){history.addLast(role to text.take(160));while(history.size>6)history.removeFirst()}
    private fun agentContext()=org.json.JSONObject().apply{
        put("session",session);put("child",state.profile.name);put("demo",app.demoActive);put("game",state.game.name)
        put("time",java.time.ZonedDateTime.now(java.time.ZoneId.of("Asia/Seoul")).format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm E",java.util.Locale.KOREAN)))
        val v=state.vehicle
        put("vehicle",org.json.JSONObject().apply{put("gear",v.gear);v.speedKmh?.let{put("speedKmh",it.toDouble())};v.battery?.let{put("battery",it)};v.chargingActive?.let{put("chargingActive",it)};v.destination?.let{put("destination",it)};v.minutesRemaining?.let{put("minutesRemaining",it)};put("uxRestricted",v.uxRestricted);if(v.destinationLatitude!=null&&v.destinationLongitude!=null)put("destinationLocation",org.json.JSONObject().put("lat",v.destinationLatitude).put("lon",v.destinationLongitude));if(v.demoTrip)put("demoTrip",true);put("wiperOnRecently",lastRainAt>0&&android.os.SystemClock.elapsedRealtime()-lastRainAt<600_000);if(v.latitude!=null&&v.longitude!=null)put("location",org.json.JSONObject().put("lat",v.latitude).put("lon",v.longitude).put("source","Pleos FusedLocation"))})
        put("history",org.json.JSONArray().apply{history.forEach{(r,x)->put(org.json.JSONObject().put("role",r).put("text",x))}})
        put("family",familyFacts())
    }
    /** Today's and tomorrow's plans and notices the app already holds, for the edge's packing and route plans. */
    private fun familyFacts()=org.json.JSONArray().apply{
        val today=LocalDate.now(java.time.ZoneId.of("Asia/Seoul"))
        for(plan in app.saved.currentPlans(includeSamples=app.demoActive)){
            val day=when(plan.date){today.toString()->0;today.plusDays(1).toString()->1;else->null}?:continue
            put(org.json.JSONObject().put("source","plan").put("title",plan.title).put("preparation",plan.preparation).put("day",day))
        }
        for(fact in app.saved.facts.filter{it.sourceScope==app.saved.activeSourceScope&&it.topic in setOf("NOTICES","BRIEF")&&it.text.isNotBlank()}.take(4)){
            val day=when(fact.date){today.toString()->0;today.plusDays(1).toString()->1;else->null}
            put(org.json.JSONObject().put("source","notice").put("title","어린이집 소식").put("text",fact.text.take(400)).apply{day?.let{put("day",it)}})
        }
        if(app.demoActive)put(org.json.JSONObject().put("source","notice").put("title","샘플 공지").put("text",FamilyAnswers.sample("NOTICES",today.plusDays(1))).put("day",1))
    }
    private fun askAgent(text:String,proactive:Boolean=false){
        agentJob?.cancel();albumJob?.cancel()
        val revision=intentRevision;val context=agentContext().apply{if(proactive)put("proactive","route-stop")}
        val first=java.util.concurrent.atomic.AtomicBoolean(false);val rest=StringBuilder()
        app.reduce{it.copy(agentBusy=true,agentSteps=listOf(if(proactive)AgentStep("hear","차량 신호 읽기","done","주행 중 · ${it.vehicle.destination?:"목적지"}까지 ${it.vehicle.minutesRemaining?:"?"}분")else AgentStep("hear","말 이해하기","done","“$text”")),title="플리가 생각하고 있어요",mood=Mood.THINKING,answerSource="엣지 AI · ${ai.teammoon.pli.edge.EdgeAi.llmModel.substringBefore('.').ifBlank{"로컬 LLM"}}",panel=if(it.panel=="ALBUM"&&albumIntent.containsMatchIn(text))"ALBUM" else "BRIEF",question=null,card=null)}
        agentJob=lifecycleScope.launch(Dispatchers.IO){
            val reply=ai.teammoon.pli.edge.EdgeAi.converse(text,context,{s->main.post{if(live(revision))app.reduce{st->st.copy(agentSteps=st.agentSteps.filter{it.id!=s.id}+AgentStep(s.id,s.label,s.state,s.detail,s.ms))}}},
                {sentence,_->main.post{if(live(revision)&&sentence.isNotBlank()){if(first.compareAndSet(false,true))say(sentence,state.title,Mood.HAPPY)else rest.append(' ').append(sentence)}}})
            withContext(Dispatchers.Main){
                if(!live(revision))return@withContext
                app.reduce{it.copy(agentBusy=false)}
                if(reply==null){if(!proactive)agentFallback(text);return@withContext}
                if(!proactive)remember("child",text);if(reply.speech.isNotBlank())remember("pli",reply.speech)
                if(reply.speech.isNotBlank()){
                    app.reduce{it.copy(title=reply.title.ifBlank{it.title},speech=reply.speech,mood=moodOf(reply.mood))}
                    val tail=rest.toString().trim();if(tail.isNotEmpty()&&!state.quiet)speaker.speak(tail,state.profile.volume)
                }
                perform(reply)
                Log.i("PliConversation","Agent ${reply.action} ${reply.ms}ms")
            }
        }
    }
    private fun agentFallback(text:String){
        app.reduce{it.copy(answerSource="말하기 도움말",agentSteps=it.agentSteps+AgentStep("edge","엣지 AI 연결","fail","기기 안 규칙으로 대신 답해요"))}
        if(albumIntent.containsMatchIn(text)){showAlbum();return}
        say("지금은 엣지 AI와 연결되지 않았어. 오늘 준비물 알려줘, 또는 숫자 놀이 해줘, 처럼 말해 줘.","다시 한번 말해 주세요.",Mood.THINKING)
    }
    private fun perform(reply:ai.teammoon.pli.edge.EdgeAi.Reply){
        val a=reply.args
        if(reply.action !in setOf("start_game","game_turn")&&(state.game==Game.WORDCHAIN||state.game==Game.RIDDLE))app.reduce{it.copy(game=Game.FRIEND)}
        when(reply.action){
            "family_news"->handle(VoiceCommand.FamilyAsk(a.optString("topic","BRIEF"),a.optInt("day",0),parent=false),"",false)
            "start_game"->when(val g=a.optString("game")){
                "WORDCHAIN"->app.reduce{it.copy(game=Game.WORDCHAIN,question=null,audience="CHILD",panel="BRIEF",quiet=false)}
                "RIDDLE"->app.reduce{it.copy(game=Game.RIDDLE,question=null,audience="CHILD",panel="BRIEF",quiet=false)}
                else->runCatching{Game.valueOf(g)}.getOrNull()?.let{play(it)}
            }
            "game_turn"->if(a.optBoolean("ended"))app.reduce{it.copy(game=Game.FRIEND)}
            "show_album"->showAlbum()
            "make_album"->reply.album?.let{storyAlbum(it)}
            "show_growth"->handle(VoiceCommand.Growth,"",false)
            "quiet"->handle(VoiceCommand.Hush,"",false)
            "destinations"->handle(VoiceCommand.DestinationOptions,"",false)
            "remember"->handle(VoiceCommand.Remember(a.optString("note").take(120)),"",false)
            "prepare"->StageCards.parse(reply.card)?.let{card->app.reduce{it.copy(card=card,audience="CHILD",panel="BRIEF",game=Game.FRIEND,question=null)}}
            "stop"->StageCards.parse(reply.card)?.let{card->app.reduce{it.copy(card=card,audience="FAMILY",panel="BRIEF",game=Game.FRIEND,question=null)}}
            "route"->{
                a.optString("destination").takeIf(String::isNotBlank)?.let{destination=it}
                startTrip()
                StageCards.parse(reply.card,a.optString("game").takeIf(String::isNotBlank))?.let{card->app.reduce{it.copy(card=card,audience="CHILD",panel="BRIEF",game=Game.FRIEND,question=null)}}
            }
        }
    }
    private fun tick(card:StageCard,labels:Set<String>){
        val next=card.copy(checked=card.checked+labels);app.reduce{it.copy(card=next)}
        val left=next.items.map{it.label}.filterNot{it in next.checked}
        val day=card.title.substringBefore(' ')
        if(left.isEmpty())say("다 챙겼다! $day 준비 끝. 정말 멋져!","$day 준비 끝!",Mood.EXCITED)
        else say("${labels.joinToString(", ")} 체크! 이제 ${left.joinToString(", ")}만 남았어.",next.title,Mood.HAPPY)
    }
    private fun startSuggested(game:Game){
        when(game){
            Game.WORDCHAIN->askAgent("끝말잇기 하자")
            Game.RIDDLE->askAgent("수수께끼 내 줘")
            else->play(game)
        }
    }
    private fun showAlbum(){
        albumJob?.cancel()
        albumJob=lifecycleScope.launch{
            val album=withContext(Dispatchers.IO){ai.teammoon.pli.edge.EdgeAi.album?:ai.teammoon.pli.edge.EdgeAi.loadAlbum(app)}
            if(album==null||album.photos.isEmpty()){say("아직 앨범에 사진이 없어. 가족 연결에서 사진을 추가해 줘.","앨범이 비어 있어요.");return@launch}
            app.reduce{it.copy(panel="ALBUM",audience="CHILD",question=null,avatarPath=album.avatarPath,album=AlbumView("${album.child}의 사진",album.child,album.photos.map{p->AlbumPhoto(p.id,p.path,"",p.focusX,p.focusY)},"GRID",0,"얼굴 인식으로 ${album.child} 찾기"))}
            say("${childAddress(album.child)}, 우리 사진을 모아 봤어! 앨범 만들어 줘, 라고 말하면 이야기 앨범으로 꾸며 줄게.","${album.child}의 사진",Mood.EXCITED)
        }
    }
    private suspend fun awaitQuiet(limitMs:Long=20_000){
        val until=android.os.SystemClock.elapsedRealtime()+limitMs
        delay(300)
        while((speaker.speaking||state.playback!="IDLE")&&android.os.SystemClock.elapsedRealtime()<until)delay(120)
    }
    private fun storyAlbum(json:org.json.JSONObject){
        albumJob?.cancel()
        albumJob=lifecycleScope.launch{
            val album=withContext(Dispatchers.IO){ai.teammoon.pli.edge.EdgeAi.album?:ai.teammoon.pli.edge.EdgeAi.loadAlbum(app)}?:return@launch
            val pages=json.optJSONArray("pages")?:return@launch
            val byId=album.photos.associateBy{it.id}
            val photos=(0 until pages.length()).mapNotNull{i->val p=pages.getJSONObject(i);byId[p.optString("id")]?.let{AlbumPhoto(it.id,it.path,p.optString("caption"),it.focusX,it.focusY)}}
            if(photos.isEmpty())return@launch
            val title=json.optString("title").ifBlank{"${album.child}의 앨범"}
            app.reduce{it.copy(panel="ALBUM",audience="CHILD",question=null,avatarPath=album.avatarPath,album=AlbumView(title,album.child,photos,"STORY",0,"엣지 AI가 만든 앨범"))}
            // The cover stays while Pli finishes its reply; photos decode meanwhile. Each page is shown, then read,
            // and the next page only comes after its caption was heard: picture and voice never drift apart
            // (2026-11-14 film audit H2: page 2 was on screen while page 1 was being read).
            withContext(Dispatchers.IO){ai.teammoon.pli.ui.AlbumBitmaps.preload(photos.map{it.path})}
            delay(1200);awaitQuiet()
            for(i in photos.indices){
                if(state.panel!="ALBUM"||state.album?.mode!="STORY")return@launch
                app.reduce{it.copy(album=it.album?.copy(index=i+1))}
                delay(900)
                if(!state.quiet&&photos[i].caption.isNotBlank()){speaker.speak(photos[i].caption,state.profile.volume);awaitQuiet()}
                delay(1800)
            }
            if(state.panel!="ALBUM"||state.album?.mode!="STORY")return@launch
            app.reduce{it.copy(album=it.album?.copy(index=photos.size+1))}
            say("$title, 끝! 또 보고 싶으면 앨범 보여 줘, 라고 말해 줘.",title,Mood.HAPPY)
        }
    }

    private fun startReading(text:String,identity:String,scope:String,parent:Boolean){
        reading=ReadingContext(text,identity,scope,intentRevision,if(parent)420 else 200)
        readCurrent()
    }
    private fun readFact(fact:FamilyFact,parent:Boolean,prefix:String=""){
        if(fact.status !in setOf("AVAILABLE","PARTIAL")||fact.text.isBlank()){say(prefix+FamilyAnswers.speech(fact,parent));return}
        var disclosure=if(fact.truncated&&fact.documentId==null&&fact.fullText==null)"확인 가능한 앞부분만 보관되어 있어요. "else""
        val full=try{ai.teammoon.pli.data.FamilyDocuments.read(app,fact)}catch(e:Exception){disclosure="보관한 원문을 열지 못했어요. 확인 가능한 앞부분만 읽어드릴게요. ";fact.text}
        startReading(prefix+disclosure+FamilyAnswers.introduction(fact,parent)+full,fact.documentId?:fact.topic+fact.date,fact.sourceScope,parent)
    }
    private fun readCurrent(){
        val r=reading?:return
        if(!app.demoActive&&r.sourceScope!=(app.saved.activeSourceScope?:"manual")){reading=null;say("아이·기관 선택이 바뀌었어요. 소식을 다시 물어봐 주세요.");return}
        app.reduce{it.copy(readingPage=r.page,readingHasMore=r.hasMore)}
        say(r.current()+if(r.hasMore)" 이어서 들으려면 더 읽어, 라고 말해 주세요."else"")
    }
    private fun readMore(direction:Int){
        val r=reading
        if(r==null){say("읽고 있는 자료가 없어요. 식단이나 알림장을 먼저 물어봐 주세요.");return}
        val moved=when{direction>0->r.next();direction<0->r.previous();else->{r.first();true}}
        if(moved)readCurrent()else say(if(direction>0)"확인한 본문은 모두 읽었어요. 다른 소식을 물어봐 주세요."else"본문의 첫 부분이에요.")
    }
    private fun brief(date:LocalDate,days:Int,field:String,fresh:Boolean){
        val end=date.plusDays(days.toLong()-1);val plans=app.saved.currentPlans(app.demoActive).filter{it.date>=date.toString()&&it.date<=end.toString()}.sortedBy{it.date}
        val prefix=if(app.demoActive)"공개 체험용 샘플입니다. "else if(fresh)"어린이집에서 새로 확인하고 저장한 일정이에요. "else"저장된 일정과 준비물이에요. "
        val detail=if(plans.isEmpty())"${date.monthValue}월 ${date.dayOfMonth}일${if(days>1)"부터 ${end.dayOfMonth}일까지"else""} 확인한 일정과 준비물 안내가 없어요."else plans.joinToString(". "){(if(days>1)"${LocalDate.parse(it.date).dayOfMonth}일, "else"")+it.title+if(it.preparation.isNotBlank())". 준비물 안내: ${it.preparation}"else". 준비물 안내는 없어요"}
        val time=if(field=="TIME")" 등원 시각을 나타내는 별도 시간 정보는 자료에 없어 임의로 정하지 않을게요."else""
        app.reduce{it.copy(answerSource=if(app.demoActive)"공개 체험용 샘플"else if(fresh)"어린이집 일정 새로 확인"else"저장된 일정·준비물")}
        startReading(prefix+detail+time,"brief:$date:$days",if(app.demoActive)"demo"else app.saved.activeSourceScope?:"manual",true)
    }
    private fun destinationPage(delta:Int){
        choiceExpires=android.os.SystemClock.elapsedRealtime()+60000
        if(state.panel!="DESTINATIONS"){say("목적지 후보를 먼저 물어봐 주세요.");return}
        val choices=state.destinationChoices;val max=(choices.size-1).coerceAtLeast(0)/3
        val page=if(delta==0)0 else (state.destinationPage+delta).coerceIn(0,max)
        pendingDestination=null;app.reduce{it.copy(destinationPage=page,selectedDestination=null)}
        val start=page*3;val rows=choices.drop(start).take(3)
        say("후보 ${choices.size}곳 중 "+rows.mapIndexed{i,c->"${start+i+1}번 ${c.name}"}.joinToString(". ")+if(page<max)". 다음 후보, 라고 말하면 더 볼 수 있어요."else". 장소 이름이나 번호로 골라 주세요.","가족의 다음 목적지")
    }
    private fun offerDestinations(){
        pendingDestination=null;choiceExpires=android.os.SystemClock.elapsedRealtime()+60000
        val options=if(app.demoActive)listOf(DestinationChoice("sample:forest","숲 놀이터 · 샘플",0.0,0.0),DestinationChoice("sample:library","어린이 도서관 · 샘플",0.0,0.0))else app.saved.destinations
        app.reduce{it.copy(audience="PARENT",panel="DESTINATIONS",question=null,game=Game.FRIEND,destinationChoices=options,destinationPage=0,selectedDestination=null,answerSource=if(app.demoActive)"공개 체험용 후보"else"보호자가 등록한 후보")}
        if(options.isEmpty())say("아직 등록된 목적지 후보가 없어요. 가족 연결에서 보호자가 장소를 등록해 주세요.","가족의 다음 목적지")else destinationPage(0)

    }
    private fun selectDestination(value:String){
        if(state.panel!="DESTINATIONS"||android.os.SystemClock.elapsedRealtime()>choiceExpires){say("먼저 목적지 후보 알려줘, 라고 말해 주세요.","후보를 먼저 확인해요.");return}
        val options=state.destinationChoices
        val key=VoiceInterpreter.compact(value)
        val item=value.toIntOrNull()?.let{options.getOrNull(it-1)}?:options.filter{val name=VoiceInterpreter.compact(it.name.substringBefore(" ·"));name==key||(key.length>=2&&name.endsWith(key))}.singleOrNull()
        if(item==null){say("등록한 후보에서 골라 주세요. 첫 번째, 또는 두 번째처럼 말해도 좋아요.");return}
        pendingDestination=item;choiceExpires=android.os.SystemClock.elapsedRealtime()+60000
        app.reduce{it.copy(selectedDestination=item,destinationPage=options.indexOf(item)/3)}
        say("${item.name} 선택을 확인했어요. 아직 내비게이션은 바꾸지 않았어요. 보호자께서 장소를 확인하신 뒤, 보호자 확인, 이라고 말씀해 주세요.","보호자 확인을 기다려요.")
    }
    private fun confirmDestination(){
        val item=pendingDestination
        if(item==null||android.os.SystemClock.elapsedRealtime()>choiceExpires){pendingDestination=null;say("선택한 목적지가 없거나 확인 시간이 지났어요. 목적지 후보부터 다시 골라 주세요.");return}
        if(app.demoActive){pendingDestination=null;app.reduce{it.copy(panel="BRIEF",game=Game.FRIEND,question=null,selectedDestination=null,audience="FAMILY")};say("공개 체험에서는 선택과 확인까지만 연습해요. 실제 차량의 내비게이션은 바꾸지 않았어요.","샘플 목적지 확인을 마쳤어요.");return}
        val id=UUID.randomUUID().toString()
        try{app.requestRoute(item,id);routeRequestId=id;pendingDestination=null;say("${item.name} 안내를 요청했어요. 내비게이션의 실제 결과를 확인하고 있어요.","내비게이션 응답 확인 중")
            main.postDelayed({if(routeRequestId==id&&state.epoch==epoch){routeRequestId=null;say("내비게이션에서 결과를 확인하지 못했어요. 중복 요청하지 않았으니 내비게이션 화면을 확인해 주세요.","안내 결과 확인이 필요해요.")}},20000)
        }catch(e:Exception){routeRequestId=null;say("목적지 정보가 바뀌었거나 내비게이션에 연결하지 못했어요. 가족 연결의 후보와 차량 연결을 확인해 주세요.","안내를 시작하지 못했어요.")}
    }
    fun onVehicleState(value:VehicleState){
        if(state.sessionId!=session||state.epoch!=epoch)return
        if(value.routeActive==false)lastQuestion=false else if(value.minutesRemaining?.let{it in 1..2}==true)lastQuestion=true
        val id=routeRequestId
        if(id!=null&&value.routeRequestId==id&&value.routeStatus in setOf("CONFIRMED","FAILED")){
            routeRequestId=null;say(if(value.routeStatus=="CONFIRMED")"${value.destination?:"선택한 장소"}의 경로를 내비게이션에서 확인했어요."else"내비게이션이 안내 요청을 완료하지 못했어요. 다른 목적지를 자동으로 설정하지 않았어요.",if(value.routeStatus=="CONFIRMED")"목적지 안내를 확인했어요."else"경로 요청을 확인해 주세요.")
        }
        if(!initialized||state.quiet||speaker.speaking||speaker.navigation)return
        val dest=value.destination
        if(!app.demoActive&&value.routeActive==true&&dest!=null&&dest!=modeDestination&&state.game==Game.FRIEND){
            modeDestination=dest
            when{dest.contains("주산")->play(Game.MATH);dest.contains("영어")->play(Game.ENGLISH);dest.contains("집")&&!dest.contains("어린이집")->play(Game.STORY)}
        }
        contextEngine.update(value,android.os.SystemClock.elapsedRealtime())?.let(::onVehicleEvent)
    }
    private fun play(game:Game){
        dialogueTurn=null;round=0;questionAnswered=false
        lastQuestion=state.vehicle.minutesRemaining?.let{it in 1..2}==true
        app.reduce{it.copy(game=game,question=null,quiet=false,audience="CHILD",answerSource="",panel="BRIEF",abacusHint=false,selectedDestination=null)};speaker.setQuiet(false)
        if(game==Game.STORY)askStory()else askQuestion()
    }
    private fun askQuestion(){
        val turn=dialogueTurn
        if(turn!=null&&turn>=LearningCatalog.dialogue.size){dialogueTurn=null;app.reduce{it.copy(question=null)};say("짧은 영어 대화를 마쳤어. 서로 인사하고 기분도 물어봤네!","다음에 또 이야기하자.");return}
        val q=if(turn!=null)LearningCatalog.dialogueQuestion(turn)else Questions.make(state.game.takeUnless{it==Game.FRIEND}?:Game.NATURE,round++,state.profile.age,LearningCatalog.theme(state.todayPlan?.title.orEmpty()));questionAnswered=false
        app.reduce{it.copy(question=q,game=q.game,abacusHint=false)}
        say(q.spoken,q.prompt,Mood.THINKING)
    }
    private fun askStory(){
        val prompts=listOf(state.todayPlan?.let{"오늘 ${it.title}, 어땠어? 기억에 남는 걸 들려줘."}?:"오늘 가장 즐거웠던 일은 뭐야?","오늘 친구랑 어떤 놀이를 했어?","내일은 어떤 일이 기다려져?")
        app.reduce{it.copy(question=null,game=Game.STORY)};say(prompts[round++%prompts.size],"오늘 너의 하루는 어땠어?")
    }
    private fun answer(value:String){
        val q=state.question?:return;if(questionAnswered)return
        questionAnswered=true;val correct=Questions.correct(q,value)
        if(dialogueTurn!=null)dialogueTurn=dialogueTurn!!+1
        app.reduce{it.copy(correct=it.correct+if(correct)1 else 0,answered=it.answered+1)}
        say(if(correct)"반짝 성공! ${if(lastQuestion)"마지막 문제까지 함께했네. 이제 도착할 준비를 하자."else"다음 문제가 궁금하면 다음이라고 말해 줘."}" else "좋은 도전이야! ${q.hint} ${if(lastQuestion)"이제 도착할 준비를 하자."else"다음에도 함께 생각해 보자."}",if(correct)"반짝 성공, 정말 멋진걸!"else"괜찮아, 함께 배우면 되지.",if(correct)Mood.EXCITED else Mood.HAPPY)
    }
    private fun startTrip(){
        if(state.tripActive)return
        tripId=UUID.randomUUID().toString();tripStartKm=state.vehicle.odometerKm;storyNote=""
        app.reduce{it.copy(tripActive=true,correct=0,answered=0)}
    }
    private fun finishTrip(){
        if(!state.tripActive){say(if(app.saved.memories.isEmpty())"함께 출발한 다음 도착하면, 첫 추억을 남겨 줄게."else"오늘의 여정은 이미 소중하게 담아 두었어.","우리의 추억은 여기 있어.");return}
        val km=tripStartKm?.let{start->state.vehicle.odometerKm?.let{end->(end-start).takeIf{it>=0&&it<1000}}}
        val memory=Memory(id=tripId?:UUID.randomUUID().toString(),date=LocalDate.now().toString(),destination=state.vehicle.destination?:destination,kilometers=km,correct=state.correct,answered=state.answered,note=storyNote)
        if(app.saved.memories.any{it.id==memory.id})return
        if(app.saved.memories.size>=2000){say("추억 보관함이 가득 차 이번 기록을 저장하지 못했어. 기존 추억은 보존했어.");return}
        save(app.saved.copy(memories=listOf(memory)+app.saved.memories)){
            app.reduce{it.copy(tripActive=false,question=null,game=Game.FRIEND)};tripId=null
            say("${childAddress(state.profile.name)}, 도착했구나! ${app.saved.memories.size}번째 스탬프를 남겼어. 오늘도 함께해서 행복했어!","또 하나의 추억이 생겼어.",Mood.EXCITED)
        }
    }
    private fun importPlan(){
        if(importJob?.isActive==true){say("사진에서 일정을 확인하고 있어요. 잠시만 기다려 주세요.");return}
        importJob=lifecycleScope.launch{
            try{val plans=PlanImporter(app).read();pendingPlans=plans
                if(plans.isEmpty())say("사진에서 날짜를 찾지 못했어. 가족과 함께 계획안 사진을 확인해 줘.","오늘의 기대를 기다려.")else say("${plans.size}개의 일정을 찾았어. 첫 번째는 ${LocalDate.parse(plans.first().date).format(DateTimeFormatter.ofPattern("M월 d일"))} ${plans.first().title}. 맞으면 일정 저장해 줘라고 말해 줘.","일정 사진 속 설렘을 찾았어.")
            }catch(e:Exception){say("아직 준비된 계획안 사진이 없어. 가족에게 사진을 준비해 달라고 부탁해 줘.","오늘의 기대를 기다려.");Log.w("PliPlan","Import failed",e)}
        }
    }
    private fun flushVehicleCue(){
        val pending=pendingVehicleCue?:return
        if(state.sessionId!=session||state.epoch!=epoch||state.sessionStatus!="ACTIVE"||System.currentTimeMillis()-pending.second>45000){pendingVehicleCue=null;return}
        if(!questionAnswered||state.quiet||speaker.navigation||speaker.speaking||state.playback!="IDLE")return
        val wait=18000-(System.currentTimeMillis()-lastVehicleSpeech)
        if(wait>0){main.postDelayed({if(pendingVehicleCue==pending)flushVehicleCue()},wait);return}
        pendingVehicleCue=null;onVehicleEvent(pending.first)
    }
    private var lastRainAt=0L
    fun onVehicleEvent(event:String){
        if(event=="rain")lastRainAt=android.os.SystemClock.elapsedRealtime()
        if(state.sessionId!=session||state.epoch!=epoch)return
        if(BuildConfig.DEBUG)Log.i("PliVehicleEvent",event)
        if(event=="arrive"){finishTrip();return}
        if(event=="door_open"){if(state.vehicle.gear=="P"&&state.tripActive)finishTrip();return}
        if(event=="depart"){startTrip()}
        if(event=="nearby")lastQuestion=true
        if(!initialized||state.quiet||speaker.navigation)return
        if(state.question!=null&&!questionAnswered&&event !in setOf("boarding","depart","nearby")){pendingVehicleCue=event to System.currentTimeMillis();return}
        if(speaker.speaking)return
        val now=System.currentTimeMillis();if(now-lastVehicleSpeech<18000)return
        if(event=="slow_road"){lastVehicleSpeech=now;play(Game.NATURE);return}
        if(event=="charging"&&!state.vehicle.uxRestricted){lastVehicleSpeech=now;play(Game.MATH);app.reduce{it.copy(panel="CHARGE")};return}
        val line=when(event){
            "warm_cabin"->"실내 센서에서 따뜻한 온도가 들어왔어. 보호자와 함께 실내가 편안한지 확인해 볼까?"
            "boarding"->"${childAddress(state.profile.name)}, 만나서 반가워! ${state.todayPlan?.let{"오늘은 ${it.title}. "}?:""}오늘도 우리 같이 가자."
            "depart"->"우리의 작은 모험이 시작됐어. 오늘도 즐겁게 함께 가자!"
            "rain"->"톡톡, 빗방울 소리 들려? 와이퍼가 인사하네. 비는 영어로 레인!"
            "turn_left"->"깜빡깜빡! 차가 왼쪽으로 돌아간다고 인사하는 거야."
            "turn_right"->"깜빡깜빡! 차가 오른쪽으로 돌아간다고 인사하는 거야."
            "charging"->"차도 잠깐 간식 먹는 시간이야. 우리는 목소리로 숫자 놀이를 해 볼까?"
            "slow_road"->"천천히 가는 동안 거북이처럼 차분하게 생각해 볼까? 도토리는 어떤 나무에서 열릴까?"
            "cruise"->"쭉 이어지는 길에서 우주여행을 상상해 보자. 차는 안전한 속도로 가고, 우리는 마음속 로켓을 타는 거야!"
            "downhill"->"차에서 받은 고도가 조금 낮아졌네. 마음속 미끄럼틀을 타 볼까? 하나, 둘, 셋, 슝!"
            "nearby"->"이제 도착까지 2분 안팎이야. 지금 하던 놀이를 마지막으로 마무리하고 도착할 준비를 하자."
            else->return
        }
        lastVehicleSpeech=now;say(line,when(event){"rain"->"빗방울 오케스트라";"nearby"->"모험의 끝이 가까워져!";"charging"->"우리도 에너지를 채우는 시간";else->"길 위에서 만난 작은 이야기"})
    }
    fun close(){
        nextQuestionJob?.cancel();debugJob?.cancel();importJob?.cancel();agentJob?.cancel();albumJob?.cancel();source?.close();speaker.close();main.removeCallbacksAndMessages(null)
        if(BuildConfig.DEBUG)runCatching{app.store.debugSnapshot(app.state.value)}

    }
}

private const val STOP_CHECK_MS=2500L
private const val STOP_MIN_KMH=10f
private const val STOP_MIN_MINUTES=5
private const val STOP_QUIET_MS=6000L
