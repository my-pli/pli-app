package ai.teammoon.pli

import ai.teammoon.pli.domain.*
import ai.teammoon.pli.data.DataContract as C
import org.junit.Assert.*
import org.junit.Test
import java.time.LocalDate

class JourneyExperienceTest{
 @Test fun actualGeneratedPhrasesReachTheInterpreterAndReviewedEnglishAnswers(){
  val root=generateSequence(java.io.File(System.getProperty("user.dir"))){it.parentFile}.map{java.io.File(it,"qa/native/fixtures")}.first{java.io.File(it,"intent-contract.json").isFile}
  fun json(name:String)=com.google.gson.JsonParser.parseString(java.io.File(root,name).readText()).asJsonObject
  val phrases=com.google.gson.JsonObject()
  root.listFiles()!!.filter{it.name.endsWith("phrases.json")}.forEach{file->json(file.name).entrySet().forEach{phrases.add(it.key,it.value)}}
  val expected=json("intent-contract.json")
  assertEquals(phrases.keySet(),expected.keySet())
  for((id,kind)in expected.entrySet()){
   assertTrue("Missing acoustic fixture $id",java.io.File(root,"$id.wav").isFile)
   val turn=when(id){"hello-v4"->0;"happy-v4"->1;"bye-v4","bye-clear","see-you-clear","bye-english","goodbye-english"->2;else->null}
   val question=turn?.let{LearningCatalog.dialogueQuestion(it)}
   val command=VoiceInterpreter.parse(phrases[id].asString,question)
   assertEquals("Original fixture $id: ${phrases[id].asString}",kind.asString,command.javaClass.simpleName)
   if(id.startsWith("weekly-refresh")){val family=command as VoiceCommand.FamilyAsk;assertTrue(family.refresh);assertEquals(7,family.days);assertEquals("BRIEF",family.topic)}
   if(id=="menu-refresh-v4"){val family=command as VoiceCommand.FamilyAsk;assertTrue(family.refresh);assertEquals("MENU",family.topic)}
   if(id=="destination-twelfth-clear")assertEquals("12",(command as VoiceCommand.ChooseDestination).choice)
   if(question!=null)assertTrue("Reviewed answer $id",Questions.correct(question,phrases[id].asString))
  }
 }

 @Test fun spokenEnglishAcceptsReviewedGreetingsAndPhrasesWithoutAcceptingUnrelatedWords(){
  for((turn,values)in listOf(listOf("Hello", "hallo", "hullo", "헬로우", "안녕하세요"),listOf("I'm happy", "I am happy", "아임 해피"),listOf("See you later", "Good by", "Bye bye", "바이 바이", "안녕")).withIndex()){
   val q=LearningCatalog.dialogueQuestion(turn)
   for(value in values){assertTrue("turn $turn: $value",Questions.correct(q,value));assertTrue(VoiceInterpreter.parse(value,q)is VoiceCommand.Answer)}
   assertFalse(Questions.correct(q,"banana"));assertFalse(Questions.correct(q,"그따위"));assertFalse(Questions.correct(q,"하해이"))
  }
 }
 @Test fun politeNextRequestsPageOrQuestionButCannotConfirmAGuardian(){
  for(value in listOf("다음 문제 주세요","다음 문제 해주세요","다음 페이지 보여 주세요","다음 목록 보여줘","다음 문제 내주세요","다음 질문 말해 주세요","다음 문제 부탁해요","다음 페이지 넘겨 주세요"))assertEquals(VoiceCommand.Next,VoiceInterpreter.parse(value))
  for(value in listOf("더 읽어주세요","계속 읽어 주세요","이어서 읽어 주세요"))assertEquals(VoiceCommand.ReadNext,VoiceInterpreter.parse(value))
  assertEquals(VoiceCommand.ReadStart,VoiceInterpreter.parse("처음부터 읽어 주세요"))
  assertEquals(VoiceCommand.StopReading,VoiceInterpreter.parse("그만 읽어 주세요"))
  assertEquals(VoiceCommand.DestinationPage(1),VoiceInterpreter.parse("다음 후보"))
  assertNotEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("보호자 확인해 주세요"))
  assertNotEquals(VoiceCommand.Next,VoiceInterpreter.parse("다음 일정 알려줘"))
 }

 @Test fun wakeDetectionAndCommandNormalizationShareTheSameAliases(){for(name in listOf("플리","플레이","프리","블리","풀리")){assertTrue(VoiceInterpreter.hasWakeWord("${name}야, 목적지 효과 보여주세요"));assertTrue(VoiceInterpreter.parse("${name}야, 목적지 효과 보여주세요")is VoiceCommand.Unrecognized);assertEquals(VoiceCommand.Play(Game.MATH),VoiceInterpreter.parse("${name}야 숫자 놀이 해줘"))};assertFalse(VoiceInterpreter.hasWakeWord("주말에 어디 갈"))}
 @Test fun anUnrelatedOfferIsNotAnAnswerOrARoleChange(){val q=Questions.make(Game.NATURE,0);assertTrue(VoiceInterpreter.parse("이번에는 내가 문자 낼게",q)is VoiceCommand.Unrecognized);assertTrue(VoiceInterpreter.parse("내가 그림 그릴게",q)is VoiceCommand.Unrecognized);assertEquals(VoiceCommand.SwapRoles,VoiceInterpreter.parse("이번엔 내가 문제 낼게",q));assertEquals(VoiceCommand.Answer("참나무"),VoiceInterpreter.parse("참나무",q))}
 @Test fun anUnsupportedQuizSubjectNeverSelectsAnotherGame(){assertTrue(VoiceInterpreter.parse("연극 퀴즈 시작해줘")is VoiceCommand.Unrecognized);assertTrue(VoiceInterpreter.parse("역사 퀴즈 해줘",Questions.make(Game.ENGLISH,0))is VoiceCommand.Unrecognized);assertEquals(VoiceCommand.Play(Game.NATURE),VoiceInterpreter.parse("퀴즈 해줘"));assertEquals(VoiceCommand.Play(Game.NATURE),VoiceInterpreter.parse("자연 퀴즈 해줘"));assertEquals(VoiceCommand.Play(Game.ENGLISH),VoiceInterpreter.parse("영어 퀴즈 시작해줘"))}
 @Test fun anUnsupportedRequestNeverBecomesAWrongEnglishAnswer(){val question=Questions.make(Game.ENGLISH,0);assertTrue(VoiceInterpreter.parse("진짜 노래해줘",question)is VoiceCommand.Unrecognized);assertTrue(VoiceInterpreter.parse("동화 읽어주세요",question)is VoiceCommand.Unrecognized);assertEquals(VoiceCommand.Answer("apple"),VoiceInterpreter.parse("apple",question));assertEquals(VoiceCommand.Answer("banana"),VoiceInterpreter.parse("banana",question))}
 @Test fun numericSubjectAndPlayRequestUseTheSameRuleAsEnglish(){assertEquals(VoiceCommand.Play(Game.MATH),VoiceInterpreter.parse("숫자 문제 해줘"));assertEquals(VoiceCommand.Play(Game.MATH),VoiceInterpreter.parse("숫자 둘이 해줘"));assertEquals(VoiceCommand.Play(Game.MATH),VoiceInterpreter.parse("계산 문제 해줘"));assertEquals(VoiceCommand.Play(Game.ENGLISH),VoiceInterpreter.parse("영어 문제 해줘"));assertTrue(VoiceInterpreter.parse("둘이 해줘")is VoiceCommand.Unrecognized)}
 @Test fun upcomingPlaceDeliberationIsAReadOnlyCandidateRequest(){assertEquals(VoiceCommand.DestinationOptions,VoiceInterpreter.parse("주말에 어디 갈지"));assertEquals(VoiceCommand.DestinationOptions,VoiceInterpreter.parse("다음 주말에 어디 갈지 알려줘"));assertTrue(VoiceInterpreter.parse("지난주에 어디 갔었지")is VoiceCommand.Unrecognized);assertTrue(VoiceInterpreter.parse("지난 주말 어디 갔지")is VoiceCommand.Unrecognized)}
 @Test fun explicitEnglishQuizKeepsUnrelatedRecognitionUnrecognized(){assertEquals(VoiceCommand.Play(Game.ENGLISH),VoiceInterpreter.parse("영어 퀴즈 시작해 줘"));assertEquals(VoiceCommand.Play(Game.ENGLISH),VoiceInterpreter.parse("영어 퀴즈"));assertTrue(VoiceInterpreter.parse("영원돌이 했죠")is VoiceCommand.Unrecognized)}
 @Test fun growthUsesStoredTripsAndWeightedAccuracy(){val today=LocalDate.of(2026,11,11);val rows=listOf(Memory("a",today.toString(),"집",null,1,1),Memory("b",today.minusDays(1).toString(),"학원",1.5f,0,9));val g=GrowthSummary.from(rows,today);assertEquals(2,g.stamps);assertEquals(10,g.accuracy);assertEquals(1.5f,g.kilometers!!);assertEquals(listOf(0,0,0,0,0,1,1),g.dailyStamps)}
 @Test fun noRecordsDoNotInventSuccessOrDistance(){val g=GrowthSummary.from(emptyList());assertNull(g.accuracy);assertNull(g.kilometers);assertEquals(0,g.stamps);assertEquals(0,g.dailyStamps.sum());assertEquals(VoiceCommand.Growth,VoiceInterpreter.parse("성장 그래프 보여 주세요"))}
 @Test fun abacusUsesTheQuestionNumbers(){assertEquals(listOf(3,8,6),AbacusSteps.values(Questions.make(Game.MATH,0)));assertTrue(AbacusSteps.values(Questions.make(Game.ENGLISH,0)).isEmpty());assertEquals(VoiceCommand.ChooseDestination("2"),VoiceInterpreter.parse("두 번째 장소를 갈래"));assertEquals(VoiceCommand.ChooseDestination("1"),VoiceInterpreter.parse("첫 번째로 갈래요"))}
 @Test fun rolesCanSwapAndTheChildCanAskAWord(){assertEquals(VoiceCommand.SwapRoles,VoiceInterpreter.parse("이번엔 내가 문제 낼게"));assertEquals(VoiceCommand.Translate("나무","tree"),VoiceInterpreter.parse("플리야 나무는 영어로 뭐게"));assertNull(Vocabulary.find("우주선은 영어로 뭐야"));assertEquals(VoiceCommand.Growth,VoiceInterpreter.parse("부모 성장 앨범 보여줘"));assertEquals(VoiceCommand.ChargingPlay,VoiceInterpreter.parse("충전 놀이터 하자"))}
 @Test fun answerTwoIsNotAPlaceSelection(){assertEquals(VoiceCommand.Answer("2"),VoiceInterpreter.parse("2번",Questions.make(Game.MATH,0)));assertEquals(VoiceCommand.ChooseDestination("2"),VoiceInterpreter.parse("두 번째로 갈래"));assertEquals(VoiceCommand.ChooseDestination("2"),VoiceInterpreter.parse("두 번째 장소로 갈래"));assertEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("보호자 확인 목적지로 안내해 줘"));assertEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("보호자가 확인했어. 길 안내 시작해"));assertEquals(VoiceCommand.Play(Game.STORY),VoiceInterpreter.parse("이야기 놀이 해 주세요"))}
 @Test fun destinationsSurviveOldSchemaAndRejectNonFiniteOrDuplicates(){val choice=DestinationChoice("one","도서관",37.5,127.0);val d=SavedData(plans=emptyList(),destinations=listOf(choice));assertEquals(d,C.decode(C.gson.toJson(d)));assertTrue(C.decode(C.gson.toJson(d).replace(Regex(",\\\"destinations\\\":\\[.*?]"),"")).destinations.isEmpty());assertThrows(IllegalArgumentException::class.java){C.destinations(listOf(choice.copy(latitude=Double.NaN)))};assertThrows(IllegalArgumentException::class.java){C.destinations(listOf(choice,choice))}}
 @Test fun publicVehicleKeepsMeasuredSpeedButRemovesPersonalDestination(){val v=VehicleState(gear="D",speedKmh=32f,battery=73,destination="개인 장소",destinationLatitude=37.5,destinationLongitude=127.0,routeRequestId="private");val p=v.publicView();assertEquals(32f,p.speedKmh!!);assertEquals(73,p.battery);assertNull(p.destination);assertNull(p.destinationLatitude);assertNull(p.destinationLongitude);assertNull(p.routeRequestId)}
 @Test fun contextRequiresSignalDurationAndDoesNotInferUnknownTraffic(){val e=JourneyContextEngine();assertNull(e.update(VehicleState(gear="D"),0));assertNull(e.update(VehicleState(gear="D",speedKmh=0f),1000));assertEquals("slow_road",e.update(VehicleState(gear="D",speedKmh=0f),21000));assertNull(e.update(VehicleState(gear="D",speedKmh=0f),22000));val cruise=JourneyContextEngine();assertNull(cruise.update(VehicleState(gear="D",speedKmh=70f),0));assertEquals("cruise",cruise.update(VehicleState(gear="D",speedKmh=70f),8000));val down=JourneyContextEngine();assertNull(down.update(VehicleState(gear="D",speedKmh=10f,altitudeMeters=100.0),0));assertEquals("downhill",down.update(VehicleState(gear="D",speedKmh=10f,altitudeMeters=92.0),6000))}
 @Test fun guardianConfirmationCanBeOneUtteranceButNeverANegatedRequest(){
  assertEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("보호자 확인"))
  assertEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("보호자가 확인했어요"))
  assertNotEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("확인"))
  assertNotEquals(VoiceCommand.ConfirmDestination,VoiceInterpreter.parse("보호자 확인 목적지 안내 하지 마"))
 }
}
