package ai.teammoon.pli
import ai.teammoon.pli.domain.*
import org.junit.Assert.*
import org.junit.Test
import java.time.LocalDate
class RemediationTest{
 @Test fun negationsCorrectionsAndTimeQuestionsHaveNoUnrelatedActions(){
  for(s in listOf("종료하지 마","끝내지 마","숫자 놀이 하지 마","플리야 마이크 끄지 마"))assertTrue(s,VoiceInterpreter.parse(s)is VoiceCommand.Prohibited)
  assertEquals("MENU",(VoiceInterpreter.parse("내일 준비물 말고 식단 알려줘")as VoiceCommand.FamilyAsk).topic)
  assertEquals(1,(VoiceInterpreter.parse("내일 준비물 말고 식단 알려줘")as VoiceCommand.FamilyAsk).dayOffset)
  assertEquals("TIME",(VoiceInterpreter.parse("내일 유치원 몇 시에 가")as VoiceCommand.FamilyAsk).field)
  assertFalse(VoiceInterpreter.canInterrupt("종료",true));assertTrue(VoiceInterpreter.canInterrupt("쉿",true));assertTrue(VoiceInterpreter.canInterrupt("플리야 조용히",true));assertFalse(VoiceInterpreter.canInterrupt("조용히 하지 마",true));assertFalse(VoiceInterpreter.canInterrupt("조용",true));assertFalse(VoiceInterpreter.canInterrupt("조용히 하지 마"))
  assertEquals(VoiceCommand.Stop,VoiceInterpreter.parse("종료해줘"));assertEquals(VoiceCommand.Hush,VoiceInterpreter.parse("말하지마"))
 }
 @Test fun requestedRefreshSurvivesWeekAndUnsupportedWordsAreHonest(){val r=VoiceInterpreter.parse("다음 주 일정 다시 확인해줘",today=LocalDate.of(2026,11,11))as VoiceCommand.FamilyAsk;assertTrue(r.refresh);assertEquals(7,r.days);assertEquals(5,r.dayOffset);assertTrue(VoiceInterpreter.parse("망원경 영어로 뭐야")is VoiceCommand.Unsupported)}
 @Test fun allTwelveDestinationsCanBeSelected(){for((s,n)in listOf("네 번째" to "4","아홉 번째" to "9","열두 번째" to "12","십일 번" to "11","12번" to "12"))assertEquals(n,(VoiceInterpreter.parse(s)as VoiceCommand.ChooseDestination).choice)}
 @Test fun codePointReadingHasNoOmissionOrSplitSurrogates(){val text=("가나다😀\n".repeat(1000));val r=ReadingContext(text,"doc","scope",9);val out=StringBuilder();do{out.append(r.current())}while(r.next());assertEquals(text.filterNot(Char::isWhitespace),out.toString().filterNot(Char::isWhitespace));assertTrue(r.previous());r.first();assertEquals(0,r.page)}
 @Test fun partialAndLegacyEmptyDoNotInventAbsence(){val f=FamilyFact("REPORT","2026-11-11","scope",status="EMPTY");assertTrue(FamilyAnswers.speech(f,true).contains("확정할 수 없어요"));assertTrue(FamilyAnswers.speech(f.copy(status="PARTIAL"),true).contains("일부"));assertTrue(FamilyAnswers.speech(f.copy(coverage=QueryCoverage(true)),true).contains("자료가 없어요"))}
 @Test fun themesAndDialogueUseReviewedAnswerSets(){assertEquals("FOREST",LearningCatalog.theme("숲에서 나뭇잎 찾기"));assertEquals("tree",Questions.make(Game.ENGLISH,0,5,"FOREST").answer);assertTrue(Questions.correct(LearningCatalog.dialogueQuestion(1),"happy"));assertTrue(VoiceInterpreter.parse("영어로 대화하자")==VoiceCommand.EnglishDialogue);assertNotNull(LearningCatalog.followup("노란 나뭇잎"));assertEquals(VoiceCommand.Play(Game.STORY),VoiceInterpreter.parse("이야기도 해주세요"))}
 @Test fun naturalUpcomingPlansSynonymKeepsTheRequestedWeekAndRefresh(){val q=VoiceInterpreter.parse("이번 주 예정 다시 확인해 주세요",today=LocalDate.of(2026,11,11))as VoiceCommand.FamilyAsk;assertEquals("BRIEF",q.topic);assertEquals(7,q.days);assertEquals(-2,q.dayOffset);assertTrue(q.refresh)}

 @Test fun parentDateQuestionFallbackUsesTheCoverageAwareReader(){val r=VoiceInterpreter.parse("엄마한테 오늘 두 번 준비 알려줘")as VoiceCommand.FamilyAsk;assertEquals("BRIEF",r.topic);assertTrue(r.parent);assertEquals(0,r.dayOffset)}
 @Test fun greetingCanAnswerAnEnglishGreetingQuestion(){assertEquals(VoiceCommand.Answer("안녕"),VoiceInterpreter.parse("안녕",LearningCatalog.dialogueQuestion(0)));assertEquals(VoiceCommand.Greet,VoiceInterpreter.parse("안녕",Questions.make(Game.MATH,0)))}
 @Test fun requestingDestinationChoicesDoesNotChooseOrStartNavigation(){assertEquals(VoiceCommand.DestinationOptions,VoiceInterpreter.parse("플레이 목적지로 뽑아주세요"));assertNotEquals(VoiceCommand.DestinationOptions,VoiceInterpreter.parse("목적지 골라주지 마"))}
}
