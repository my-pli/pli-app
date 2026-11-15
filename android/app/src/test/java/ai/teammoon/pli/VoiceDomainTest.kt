package ai.teammoon.pli

import ai.teammoon.pli.domain.*
import ai.teammoon.pli.data.PlanImporter
import ai.teammoon.pli.voice.PcmWav
import org.junit.Assert.*
import org.junit.Test
import java.time.LocalDate
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class VoiceDomainTest{
 @Test fun edgeVoiceSpeaksAWholeAnswerInOnePass(){val s=listOf("집까지 십일 분 남았어요.","가는 길에 경기도서관이 있어요.","요즘 하연이가 그림 그리는 걸 정말 좋아하잖아요.","그림책 보러 잠깐 들러 볼까요?","들렀다 가도 이 분만 더 걸려요.");assertEquals(listOf(s),ai.teammoon.pli.voice.SpeechGroups.forEdge(s));val long=List(6){"가".repeat(40)+"."};val g=ai.teammoon.pli.voice.SpeechGroups.forEdge(long,150);assertTrue(g.all{it.joinToString(" ").length<=150});assertEquals(long,g.flatten());val huge=listOf("나".repeat(170),"다.");assertEquals(listOf(listOf("나".repeat(170)),listOf("다.")),ai.teammoon.pli.voice.SpeechGroups.forEdge(huge,150));assertEquals(emptyList<List<String>>(),ai.teammoon.pli.voice.SpeechGroups.forEdge(emptyList()))}
 @Test fun hushSupportsWakePhraseAndDirectSpeech(){for(s in listOf("플리야 쉿","조용히 해 줘","쉬어","플리야, 조용히"))assertEquals(s,VoiceCommand.Hush,VoiceInterpreter.parse(s))}
 @Test fun resumeIsAnExplicitVoiceCommand(){for(s in listOf("플리야 다시 놀자","다시 시작","이제 말해도 돼"))assertEquals(VoiceCommand.Resume,VoiceInterpreter.parse(s));assertFalse(VoiceInterpreter.parse("우리 추억 알려 줘") is VoiceCommand.Resume)}
 @Test fun gameSelectionUsesNaturalSpokenPhrases(){assertEquals(VoiceCommand.Play(Game.MATH),VoiceInterpreter.parse("플리야 숫자 놀이 해 줘"));assertEquals(VoiceCommand.Play(Game.ENGLISH),VoiceInterpreter.parse("영어 놀이 하자"));assertEquals(VoiceCommand.Play(Game.NATURE),VoiceInterpreter.parse("숲 놀이 해 줘"))}
 @Test fun commonKoreanAsrHomophoneStillSelectsMath(){assertEquals(VoiceCommand.Play(Game.MATH),VoiceInterpreter.parse("숫자 노래 해줘"))}
 @Test fun routeContextUsesVoiceWithoutAnyParkDependency(){assertEquals(VoiceCommand.Destination("주산학원",Game.MATH),VoiceInterpreter.parse("주산 학원 가자"));assertEquals(VoiceCommand.Destination("우리 집",Game.STORY),VoiceInterpreter.parse("집에 가자"))}
 @Test fun nativeAndSinoKoreanAnswersMapToExactNumbers(){val q=Questions.make(Game.MATH,0);for(s in listOf("6","육","여섯","여섯이야","6이에요"))assertTrue(s,Questions.correct(q,s));assertFalse(Questions.correct(q,"7"));assertEquals("12",VoiceInterpreter.normalizeAnswer("십이",Game.MATH));assertEquals("2",VoiceInterpreter.normalizeAnswer("이",Game.MATH));assertEquals("12",VoiceInterpreter.normalizeAnswer("12예요",Game.MATH))}
 @Test fun englishCanBeAnsweredInRecognizedKoreanPhonetics(){val q=Questions.make(Game.ENGLISH,0);assertTrue(Questions.correct(q,"apple"));assertTrue(Questions.correct(q,"애플이야"));assertFalse(Questions.correct(q,"tree"))}
 @Test fun allGeneratedMathProblemsHaveCorrectNonnegativeAnswers(){for(age in 3..12)for(round in 0..119){val q=Questions.make(Game.MATH,round,age);val n=Regex("\\d+").findAll(q.prompt).map{it.value.toInt()}.toList();assertEquals((n[0]+n[1]-n[2]).toString(),q.answer);assertTrue(q.answer.toInt()>=0)}}
 @Test fun quizAnswersSurviveRecognizerSlips(){val tree=Question("나무는 영어로?","나무는 영어로 뭘까?","tree",setOf("tree","트리"),"",Game.ENGLISH);for(s in listOf("트리리","트리","tree","정답은 트리"))assertTrue(s,Questions.correct(tree,s));for(s in listOf("트럭","애플","나무","트리 아니야"))assertFalse(s,Questions.correct(tree,s));val nature=Questions.make(Game.NATURE,0);assertTrue(Questions.correct(nature,"참나뭐"));val math=Questions.make(Game.MATH,0);assertFalse("numbers stay exact",Questions.correct(math,"66"));assertEquals("100",AnswerMatch.collapseEcho("100"))}
 @Test fun nonMathAnswersAreNeverScoredBySubstring(){val q=Questions.make(Game.NATURE,0);assertTrue(Questions.correct(q,"참나무"));assertFalse(Questions.correct(q,"참나무가아닌것"))}
 @Test fun voiceCanInterruptQuestionsToReadSchedule(){val q=Questions.make(Game.MATH,0);assertEquals(VoiceCommand.FamilyAsk("BRIEF",parent=false),VoiceInterpreter.parse("오늘 뭐 해",q));assertEquals(VoiceCommand.Hush,VoiceInterpreter.parse("플리야 쉿",q));assertEquals(VoiceCommand.Album,VoiceInterpreter.parse("우리 추억 알려 줘",q))}
 @Test fun childNameAndRelativeScheduleAreParsed(){assertEquals(VoiceCommand.Name("지우"),VoiceInterpreter.parse("내 이름은 지우야"));assertEquals(VoiceCommand.AddPlan("2026-11-10","숲 체험"),VoiceInterpreter.parse("내일 숲 체험 일정 추가해줘",today=LocalDate.of(2026,11,9)))}
 @Test fun planImportRejectsImpossibleDates(){val plans=PlanImporter.parse("2026-11-09, 숲 체험, 물병\n11/10, 생일잔치\n11월 11일 음악 놀이\n2026-02-30, 불가능\n13/40 잘못됨",LocalDate.of(2026,11,9));assertEquals(3,plans.size);assertEquals("물병",plans[0].preparation);assertEquals("2026-11-10",plans[1].date)}
 @Test fun microphoneStopIsDifferentFromQuiet(){assertEquals(VoiceCommand.Stop,VoiceInterpreter.parse("마이크 꺼"));assertEquals(VoiceCommand.Hush,VoiceInterpreter.parse("쉿"))}
 @Test fun onlyHushAndMicrophoneStopCanInterruptSpeech(){assertTrue(VoiceInterpreter.canInterrupt("조용히"));assertTrue(VoiceInterpreter.canInterrupt("마이크 꺼 줘"));assertFalse(VoiceInterpreter.canInterrupt("영어 놀이 하자"))}
 @Test fun naturalAnswerPhrasesAndRememberSuffixWork(){val q=Questions.make(Game.MATH,0);for(s in listOf("정답은 여섯이야","답은 여섯 개야","여섯시야","여섯 명이야","여섯 마리야"))assertTrue(s,Questions.correct(q,s));assertEquals(VoiceCommand.Remember("오늘 친구와 도토리 찾은 거"),VoiceInterpreter.parse("오늘 친구와 도토리 찾은 거 기억해 줘"))}
 @Test fun pcmReaderAcceptsMetadataChunksAndRejectsWrongSampleRate(){
  val bytes=ByteBuffer.allocate(60).order(ByteOrder.LITTLE_ENDIAN).apply{put("RIFF".toByteArray());putInt(52);put("WAVE".toByteArray());put("fmt ".toByteArray());putInt(16);putShort(1);putShort(1);putInt(16000);putInt(32000);putShort(2);putShort(16);put("JUNK".toByteArray());putInt(4);putInt(0);put("data".toByteArray());putInt(4);putShort(0);putShort(123)}.array()
  val file=File.createTempFile("pli-pcm-",".wav");try{file.writeBytes(bytes);assertEquals(4,PcmWav.read(file).size);ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).putInt(24,22050);file.writeBytes(bytes);assertThrows(IllegalArgumentException::class.java){PcmWav.read(file)}}finally{file.delete()}
 }
    @Test fun naturalBackupRequestDoesNotTreatHungrySpeechAsAStorageCommand(){
        assertEquals(VoiceCommand.Backup,VoiceInterpreter.parse("우리 추억 따로 보관해 줘"))
        assertEquals(VoiceCommand.Backup,VoiceInterpreter.parse("내 기록 파일로 저장해 주세요"))
        assertEquals(VoiceCommand.Backup,VoiceInterpreter.parse("파일로 저장해 주세요"))
        assertEquals(VoiceCommand.Backup,VoiceInterpreter.parse("파일을 저장해 주세요"))
        assertEquals(VoiceCommand.Backup,VoiceInterpreter.parse("파일 저장해 줘"))
        assertNotEquals(VoiceCommand.Backup,VoiceInterpreter.parse("배고프죠"))
        assertFalse(VoiceInterpreter.parse("우리 추억 배고프죠?") is VoiceCommand.Backup)
    }

}
