package ai.teammoon.pli
import ai.teammoon.pli.domain.*
import org.junit.Assert.*
import org.junit.Test
class FamilyQuestionTest{
 @Test fun parentAndChildQuestionsReachDistinctSupportedTopics(){
  for((phrase,topic)in listOf("오늘 점심 뭐야" to "MENU","엄마한테 오늘 식단 알려줘" to "MENU","선생님이 오늘 뭐라고 하셨어" to "REPORT","최근 알림장 읽어줘" to "REPORT_RECENT","새 공지 있어" to "NOTICES","이번 달 놀이계획 알려줘" to "MONTHLY","키즈노트 앨범 알려줘" to "ALBUMS","내일 챙길 것 있어" to "BRIEF","오늘 등원 준비 알려줘" to "BRIEF","유치원 일정 확인해줘" to "BRIEF"))assertEquals(phrase,topic,(VoiceInterpreter.parse(phrase)as VoiceCommand.FamilyAsk).topic)
  val tomorrow=VoiceInterpreter.parse("엄마 내일 준비물 있어")as VoiceCommand.FamilyAsk;assertEquals(1,tomorrow.dayOffset);assertTrue(tomorrow.parent)
  assertFalse((VoiceInterpreter.parse("점심 뭐 먹어")as VoiceCommand.FamilyAsk).parent)
 }
 @Test fun weeklyScheduleUsesCalendarWeekAndRegistrationStillWorks(){
  val today=java.time.LocalDate.of(2026,11,10)
  val week=VoiceInterpreter.parse("이번 주 유치원 일정 알려줘",today=today)as VoiceCommand.FamilyAsk
  assertEquals(7,week.days);assertEquals(-1,week.dayOffset);assertTrue(week.parent)
  assertTrue(VoiceInterpreter.parse("내일 소풍 일정 추가해줘",today=today)is VoiceCommand.AddPlan)
  assertEquals("BRIEF",(VoiceInterpreter.parse("오늘 일정 알려줘")as VoiceCommand.FamilyAsk).topic)
 }
 @Test fun missingAndStaleSourcesNeverBecomeFreshInventedAnswers(){val fact=FamilyFact("MENU","2026-11-10","scope","쌀밥과 국","https://www.kidsnote.com/service/meal",100,status="AVAILABLE");assertTrue(FamilyAnswers.speech(fact,true,100000).contains("지금 새로 확인한 내용은 아니에요"));assertTrue(FamilyAnswers.speech(fact.copy(status="EMPTY",coverage=QueryCoverage(true,reason="END")),true).contains("자료가 없어요"));assertTrue(FamilyAnswers.sample("REPORT",java.time.LocalDate.now()).contains("샘플"))}
 @Test fun parentReadoutDisclosesClippingAndPreservesSource(){val f=FamilyFact("NOTICES","2026-11-10","scope","가".repeat(1500),"https://www.kidsnote.com/service/notice",System.currentTimeMillis()/1000,status="AVAILABLE");assertTrue(FamilyAnswers.speech(f,true).contains("앞부분"));assertTrue(FamilyAnswers.speech(f,false).length<500)}
 @Test fun selectedFamilyScopeReachesScheduleReaderWithoutDeletingOtherFamilies(){
  val manual=Plan("m","2026-11-10","우리 가족 일정")
  val a=Plan("a","2026-11-10","첫 아이 일정",origin="KIDSNOTE",sourceScope="child-a")
  val b=Plan("b","2026-11-10","다른 아이 일정",origin="KIDSNOTE",sourceScope="child-b")
  val saved=SavedData(plans=listOf(manual,a,b),activeSourceScope="child-a")
  assertEquals(listOf("m","a"),saved.currentPlans().map{it.id})
  assertEquals(listOf("m","b"),saved.copy(activeSourceScope="child-b").currentPlans().map{it.id})
  assertEquals(3,saved.plans.size)
 }

 @Test fun samplePlansAreExplicitlyOptedIntoOnlyByPublicReaders(){val d=SavedData();assertTrue(d.currentPlans().isEmpty());assertEquals(1,d.currentPlans(true).size);assertEquals(1,d.plans.size)}

}
