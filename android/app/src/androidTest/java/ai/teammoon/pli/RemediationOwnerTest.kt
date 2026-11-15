package ai.teammoon.pli
import android.content.Intent
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.domain.*
import ai.teammoon.pli.voice.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Exercises the installed Controller and its actual registered SDK callbacks; text injection is explicit. */
@RunWith(AndroidJUnit4::class)
class RemediationOwnerTest{
 @Test fun lateFamilyReplyCannotReplaceNewGameAndPartialHushIsReversible(){
  val i=InstrumentationRegistry.getInstrumentation();val app=i.targetContext.applicationContext as PliApplication
  fun waitFor(label:String,p:()->Boolean){val until=System.currentTimeMillis()+25000;while(System.currentTimeMillis()<until){i.runOnMainSync{if(app.demoActive&&app.state.value.sessionStatus in setOf("PREPARING","ACTIVE"))app.serverHeartbeat("remediation-owner")};if(p())return;Thread.sleep(80)};val s=app.state.value;fail("$label: session=${s.sessionStatus}, phase=${s.phase}, playback=${s.playback}, quiet=${s.quiet}, tts=${s.ttsReady}, recognition=${s.recognition}, error=${s.error}")}
  // Reuse the existing resumed host. Repeated AAOS launcher transactions can
  // remove the previous embedded task seconds later and correctly end a private
  // microphone session. This callback test does not own a task transition.
  if(!app.state.value.visible||app.previewView.get()?.isAttachedToWindow!=true)
   i.targetContext.startActivity(i.targetContext.packageManager.getLaunchIntentForPackage(i.targetContext.packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
  waitFor("visible"){app.state.value.visible&&app.previewView.get()?.isAttachedToWindow==true}
  i.runOnMainSync{app.prepareSession("remediation-owner",false,true)}
  try{
   waitFor("engines ready"){app.state.value.modelReady&&app.state.value.ttsReady};i.runOnMainSync{app.beginSession("remediation-owner")}
   val owner=PliApplication::class.java.getDeclaredField("controller").apply{isAccessible=true}.get(app)as ConversationController
   i.runOnMainSync{owner.receive("최근 알림장 새로 확인해줘",fromTest=true)};val query=app.familyQuery!!
   i.runOnMainSync{owner.receive("숫자 놀이 해줘",fromTest=true)};val next=app.state.value.requestedText
   app.acceptFamily(FamilyAnswer(query.requestId,query.bootId,query.epoch,fact=FamilyFact(query.topic,query.date,query.scope?:"fixture","옛 질문의 답변","https://www.kidsnote.com/service/report",System.currentTimeMillis()/1000,coverage=QueryCoverage(true)),intentRevision=query.intentRevision))
   Thread.sleep(700);assertEquals(Game.MATH,app.state.value.game);assertEquals(next,app.state.value.requestedText);assertNull(app.familyQuery)
   i.runOnMainSync{owner.onVehicleEvent("rain")}
   val cue=ConversationController::class.java.getDeclaredField("pendingVehicleCue").apply{isAccessible=true};assertNotNull("a question defers its vehicle cue",cue.get(owner))
   i.runOnMainSync{owner.receive("영어 놀이 해줘",fromTest=true)};assertNull("a new task cancels the old deferred cue",cue.get(owner))
   i.runOnMainSync{owner.receive("숫자 놀이 하자",fromTest=true)}
   val connection=ConversationController::class.java.getDeclaredField("speaker").apply{isAccessible=true}.get(owner)as VoiceSessionConnection
   @Suppress("UNCHECKED_CAST") fun callback(name:String)=VoiceSessionConnection::class.java.getDeclaredField(name).apply{isAccessible=true}.get(connection)as (String)->Unit
   i.runOnMainSync{callback("partial")("쉿")};assertTrue(app.state.value.quiet)
   i.runOnMainSync{callback("final")("쉿 하지 마")};assertFalse(app.state.value.quiet);assertEquals(Game.MATH,app.state.value.game)
   i.runOnMainSync{callback("partial")("조용히")};assertTrue(app.state.value.quiet)
   i.runOnMainSync{callback("final")("조용히 하지 마")};assertFalse(app.state.value.quiet);assertEquals(Game.MATH,app.state.value.game)
   i.runOnMainSync{owner.receive("조용히",fromTest=true)};assertTrue(app.state.value.quiet)
   i.runOnMainSync{callback("partial")("쉿");callback("final")("쉿 하지 마")};assertTrue("an earlier explicit quiet cannot be undone",app.state.value.quiet)
   val beforeResume=app.state.value.spokenSequence
   i.runOnMainSync{
    owner.receive("다시 시작해",fromTest=true)
    @Suppress("UNCHECKED_CAST") val oldState=VoiceSessionConnection::class.java.getDeclaredField("onState").apply{isAccessible=true}.get(connection)as (String,String)->Unit
    oldState("IDLE","NONE")
    assertEquals("a previous stop cannot mark queued speech ready","QUEUED",app.state.value.playback)
   }
   waitFor("speech settled before solicited input"){app.state.value.spokenSequence>beforeResume&&app.state.value.requestedText==app.state.value.speech&&!connection.speaking&&app.state.value.playback=="IDLE"&&app.state.value.phase==VoicePhase.LISTENING}
   i.runOnMainSync{app.reduce{it.copy(panel="DESTINATIONS",game=Game.FRIEND,question=null)};callback("final")("호보자 화긴")}
   assertEquals("다시 한번 말해 주세요.",app.state.value.title);assertEquals("IDLE",app.state.value.vehicle.routeStatus)
   waitFor("clarification settled"){app.state.value.requestedText==app.state.value.speech&&!connection.speaking&&app.state.value.playback=="IDLE"&&app.state.value.phase==VoicePhase.LISTENING}
   val cursor=ReadingContext("합성 읽기 문단 ".repeat(120),"fixture","fixture",1);assertTrue(cursor.next());val page=cursor.page
   val reader=ConversationController::class.java.getDeclaredField("reading").apply{isAccessible=true}
   i.runOnMainSync{reader.set(owner,cursor);app.reduce{it.copy(panel="BRIEF")};callback("final")("다른 문다느")}
   assertSame(cursor,reader.get(owner));assertEquals(page,cursor.page);assertTrue(app.state.value.requestedText.contains("더 읽어줘"))
  }finally{i.runOnMainSync{app.endSession()};waitFor("stop receipt"){app.state.value.sessionStatus=="STOPPED"};i.runOnMainSync{app.preview()}}
 }
}
