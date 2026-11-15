package ai.teammoon.pli.domain

import java.time.LocalDate

sealed interface VoiceCommand {
    data object Hush : VoiceCommand
    data object Resume : VoiceCommand
    data object Greet : VoiceCommand
    data object Next : VoiceCommand
    data object Hint : VoiceCommand
    data object Repeat : VoiceCommand
    data object Album : VoiceCommand
    data object Arrive : VoiceCommand
    data object Help : VoiceCommand
    data object ImportPlan : VoiceCommand
    data object Backup : VoiceCommand
    data object Stop : VoiceCommand
    data object Growth : VoiceCommand
    data object ChargingPlay : VoiceCommand
    data object EnglishDialogue : VoiceCommand
    data object SwapRoles : VoiceCommand
    data object DestinationOptions : VoiceCommand
    data object ConfirmDestination : VoiceCommand
    data object ReadNext : VoiceCommand
    data object ReadPrevious : VoiceCommand
    data object ReadStart : VoiceCommand
    data object StopReading : VoiceCommand
    data class DestinationPage(val delta:Int):VoiceCommand
    data object Ambiguous : VoiceCommand
    data class Prohibited(val target:String):VoiceCommand
    data class Unsupported(val topic:String):VoiceCommand
    data class ChooseDestination(val choice:String):VoiceCommand
    data class Translate(val word:String,val english:String):VoiceCommand
    data class FamilyAsk(val topic:String,val dayOffset:Int=0,val parent:Boolean=true,val refresh:Boolean=false,val days:Int=1,val field:String="ALL"):VoiceCommand
    data class Play(val game: Game) : VoiceCommand
    data class Destination(val name: String, val game: Game) : VoiceCommand
    data class Name(val name: String) : VoiceCommand
    data class AddPlan(val date: String, val title: String) : VoiceCommand
    data class Volume(val change: Float) : VoiceCommand
    data class Answer(val value: String) : VoiceCommand
    data class Remember(val note: String) : VoiceCommand
    data class Unrecognized(val text: String) : VoiceCommand
}

object VoiceInterpreter {
    private val wakePrefix=Regex("^(플리|플레이|프리|블리|풀리)(야|아)?")
    fun canInterrupt(text:String,partial:Boolean=false):Boolean {
        if(partial)return addressedText(text) in setOf("쉿","조용히")
        val command=parse(text)
        return command==VoiceCommand.Hush||command==VoiceCommand.Stop||command==VoiceCommand.StopReading
    }
    fun compact(text: String): String = text.lowercase().replace(Regex("[\\s,.!?~’']"), "")
    fun hasWakeWord(text:String):Boolean=wakePrefix.containsMatchIn(compact(text))
    private fun addressedText(text:String):String=compact(text).replace(wakePrefix,"")
    fun isHush(text: String): Boolean {
        val t = addressedText(text)
        return t in setOf("쉿", "쉬", "쉬잇", "조용", "조용히", "조용히해줘", "조용히해", "잠깐쉬자", "말하지마", "잠깐멈춰", "쉬어")
    }
    fun parse(text: String, question: Question? = null, today: LocalDate = LocalDate.now(java.time.ZoneId.of("Asia/Seoul"))): VoiceCommand {
        val original = text.trim().take(500)
        val full = addressedText(original)
        val correction=Regex("말고|대신").findAll(full).lastOrNull()
        val active=correction?.let{full.substring(it.range.last+1)}?:full
        val dateToken=Regex("다음주|이번주|모레|내일|어제|오늘").find(full)?.value
        val t=if(correction!=null&&dateToken!=null&&!Regex("다음주|이번주|모레|내일|어제|오늘").containsMatchIn(active))dateToken+active else active
        if(t.isBlank())return VoiceCommand.Unrecognized(original)
        if(correction!=null&&Regex("모레|내일|어제|오늘").findAll(full).map{it.value}.distinct().count()>1)return VoiceCommand.Ambiguous
        if(full.contains("알려주고")&&full.contains("놀이"))return VoiceCommand.Ambiguous
        if(isHush(t))return VoiceCommand.Hush
        if(Regex("하지마|하지말|하지않|안할래|안해|끄지마|끝내지마").containsMatchIn(t))return VoiceCommand.Prohibited(when{t.contains("종료")||t.contains("마이크")->"STOP";t.contains("놀이")->"PLAY";else->"ACTION"})
        if (isHush(original)) return VoiceCommand.Hush
        if(Regex("^(?:더|계속|이어서)읽어(?:줘|주세요)?$").matches(t)||t in setOf("다음내용","다음문단"))return VoiceCommand.ReadNext
        if(t in setOf("이전내용","이전문단","앞문단"))return VoiceCommand.ReadPrevious
        if(Regex("^(?:다)?처음부터읽어(?:줘|주세요)?$").matches(t))return VoiceCommand.ReadStart
        if(Regex("^그만읽어(?:줘|주세요)?$").matches(t)||t in setOf("읽기그만","읽기중단"))return VoiceCommand.StopReading
        if(t in setOf("다음후보","다음목적지","다른후보","다른장소"))return VoiceCommand.DestinationPage(1)
        if(t in setOf("이전후보","이전목적지"))return VoiceCommand.DestinationPage(-1)
        if(t in setOf("후보처음","목록처음"))return VoiceCommand.DestinationPage(0)
        if (t in setOf("다시놀자","다시시작","다시시작해","일어나","이제말해도돼","계속해","같이놀자")) return VoiceCommand.Resume
        if (Regex("^(?:대화|앱|체험|플리)?(?:를|을)?종료(?:해|해줘|해주세요|하자|해요|시켜줘)?$").matches(t) || t == "그만들을래" || t in setOf("마이크꺼","마이크꺼줘")) return VoiceCommand.Stop
        if(t.contains("성장앨범")||t.contains("성장기록")||t.contains("지난주성적")||t.contains("부모앨범")||(t.startsWith("성장")&&t.contains("보여")))return VoiceCommand.Growth
        if(t.contains("충전놀이")||t.contains("충전놀이터"))return VoiceCommand.ChargingPlay
        if(t.contains("영어대화")||t.contains("영어로대화"))return VoiceCommand.EnglishDialogue
        if(t.contains("역할바꾸")||t.contains("내가문제낼")||t.contains("내가선생님"))return VoiceCommand.SwapRoles
        Vocabulary.find(t)?.let{return VoiceCommand.Translate(it.first,it.second)}
        if(t.contains("영어로"))return VoiceCommand.Unsupported("WORD")
        if(t in setOf("보호자확인","보호자확인했어","보호자가확인했어","보호자확인했어요","보호자가확인했어요"))return VoiceCommand.ConfirmDestination
        if(Regex("보호자(?:가)?확인").containsMatchIn(t)&&(t.contains("안내")||t.contains("목적지"))&&!Regex("취소|하지마|아니|안돼").containsMatchIn(t))return VoiceCommand.ConfirmDestination
        if((t.startsWith("목적지")&&Regex("(?:뽑아|골라)(?:줘|주세요)$").containsMatchIn(t))||t in setOf("주말어디","이번주말어디","다음주말어디")||t.contains("목적지후보")||t.contains("갈곳골라")||t.contains("어디갈까")||t.contains("어디갈지"))return VoiceCommand.DestinationOptions
        if(question==null){
            for((ordinal,value)in mapOf("첫" to "1","두" to "2","세" to "3","네" to "4","다섯" to "5","여섯" to "6","일곱" to "7","여덟" to "8","아홉" to "9","열" to "10","열한" to "11","열두" to "12"))if(Regex("^(?:나는|난|저는)?${ordinal}번째(?:장소)?(?:으로|로|를|을)?(?:갈래요?|가자|선택할래|선택해줘)?$").matches(t))return VoiceCommand.ChooseDestination(value)
            if(t in setOf("첫번째","첫번째로갈래","1번","일번"))return VoiceCommand.ChooseDestination("1")
            if(t in setOf("두번째","두번째로갈래","두번째장소로갈래","2번","이번"))return VoiceCommand.ChooseDestination("2")
            if(t in setOf("세번째","세번째로갈래","3번","삼번"))return VoiceCommand.ChooseDestination("3")
            Regex("^([1-9]|1[0-2])번(?:으로갈래)?$").find(t)?.let{return VoiceCommand.ChooseDestination(it.groupValues[1])}
        }
        val numbered=Regex("^(사|오|육|칠|팔|구|십|십일|십이)번(?:으로갈래|선택해줘)?$").find(t)
        if(question==null&&numbered!=null)return VoiceCommand.ChooseDestination(normalizeAnswer(numbered.groupValues[1],Game.MATH))
        if(t.endsWith("갈래"))return VoiceCommand.ChooseDestination(t.removeSuffix("으로갈래").removeSuffix("로갈래").removeSuffix("갈래"))
        val day=if(t.contains("모레"))2 else if(t.contains("내일"))1 else if(t.contains("어제"))-1 else 0
        val refresh=t.contains("최신")||t.contains("다시확인")||t.contains("새로확인")||t.contains("갱신")
        val parent=listOf("엄마","아빠","부모","보호자","브리핑","공지","알림장","자세히","식단","준비물","등원").any(t::contains)
        val registering=listOf("추가","등록").any(t::contains)
        if(!registering&&(t.contains("이번주")||t.contains("다음주"))&&(t.contains("일정")||t.contains("예정")||t.contains("준비물"))){
            val monday=today.minusDays((today.dayOfWeek.value-1).toLong()).plusDays(if(t.contains("다음주"))7 else 0)
            return VoiceCommand.FamilyAsk("BRIEF",java.time.temporal.ChronoUnit.DAYS.between(today,monday).toInt(),true,refresh=refresh,days=7)
        }
        if((t.contains("몇시")||t.contains("언제")||t.contains("시간"))&&(t.contains("유치원")||t.contains("어린이집")||t.contains("등원")||t.contains("일정")))return VoiceCommand.FamilyAsk("BRIEF",day,true,refresh,field="TIME")
        val topic=when{
            (t.contains("이번달")||t.contains("이달"))&&(t.contains("놀이")||t.contains("계획")||t.contains("특별활동"))->"MONTHLY"
            t.contains("알림장")||(t.contains("선생님")&&(t.contains("뭐")||t.contains("말씀")))||t.contains("밥잘먹었")->if(t.contains("최근")||t.contains("마지막"))"REPORT_RECENT"else"REPORT"
            listOf("식단","급식","점심","간식","뭐먹").any(t::contains)->"MENU"
            t.contains("공지")||t.contains("가정통신문")->"NOTICES"
            t.contains("앨범")||t.contains("키즈노트사진")->"ALBUMS"
            t.contains("새알림")||t.contains("키즈노트알림")->"NOTIFICATIONS"
            !registering&&(t.contains("일정")||t.contains("브리핑")||(t.contains("등원")&&listOf("준비","알려","확인","뭐").any(t::contains))||t.contains("준비물")||t.contains("챙길")||t.contains("챙겨야"))->"BRIEF"
            else->null
        }
        if(topic!=null)return VoiceCommand.FamilyAsk(topic,day,parent||topic=="BRIEF",refresh)
        val requestsPlay=listOf("하자","해줘","해주세요","하고싶어").any(t::endsWith)
        if (t in setOf("숫자","주산","계산","주산하자") || t.contains("숫자놀이") || t.contains("숫자노래") || t.contains("주산놀이") || t.contains("계산놀이") || ((t.startsWith("숫자")||t.startsWith("계산"))&&requestsPlay)) return VoiceCommand.Play(Game.MATH)
        if (t=="영어" || t.contains("영어놀이") || t.contains("영어퀴즈") || t.contains("영어하자") || (t.startsWith("영어")&&requestsPlay)) return VoiceCommand.Play(Game.ENGLISH)
        if (t in setOf("숲","자연","거북이") || t.contains("자연퀴즈") || t.contains("숲놀이") || t.contains("숲퀴즈") || t.contains("거북이퀴즈") || (t.startsWith("퀴즈")&&requestsPlay)) return VoiceCommand.Play(Game.NATURE)
        if (t.contains("오늘이야기") || t.contains("하루이야기") || t.contains("이야기하자") || t.contains("이야기놀이") || (t.startsWith("이야기")&&requestsPlay)) return VoiceCommand.Play(Game.STORY)
        if (t.contains("주산학원") && (t.contains("가") || t.contains("출발"))) return VoiceCommand.Destination("주산학원", Game.MATH)
        if (t.contains("영어학원") && (t.contains("가") || t.contains("출발"))) return VoiceCommand.Destination("영어학원", Game.ENGLISH)
        if ((t.contains("어린이집") || t.contains("유치원")) && (t.contains("가") || t.contains("출발"))) return VoiceCommand.Destination("어린이집", Game.FRIEND)
        if (t.contains("집에가") || t.contains("집으로가") || t.contains("하원")) return VoiceCommand.Destination("우리 집", Game.STORY)
        if (t.contains("소풍가") || t.contains("숲에가")) return VoiceCommand.Destination("숲 놀이터", Game.NATURE)
        if (t in setOf("출발","출발하자","가자","시작하자","여행시작")) return VoiceCommand.Destination("어린이집", Game.FRIEND)
        if (t.contains("도착했") || t == "도착" || t.contains("다왔어")) return VoiceCommand.Arrive
        if (t.contains("힌트") || t.contains("모르겠") || t in setOf("어려워","몰라","잘모르겠어")) return VoiceCommand.Hint
        if (t.contains("다시말해") || t.contains("한번더말해") || t.contains("다시들려")) return VoiceCommand.Repeat
        if (Regex("^다음(?:문제|질문|목록|페이지|내용)?(?:(?:보여|해|내|말해|읽어|넘겨)(?:줘|주세요)|주세요|부탁해요?|요)?$").matches(t) || t in setOf("한번더","다음으로","다른문제")) return VoiceCommand.Next
        if (t.contains("목소리") && (t.contains("작게") || t.contains("줄여"))) return VoiceCommand.Volume(-0.15f)
        if (t.contains("목소리") && (t.contains("크게") || t.contains("키워"))) return VoiceCommand.Volume(0.15f)
        if (t.contains("백업") || Regex("파일(?:로|을)?저장해").containsMatchIn(t) || ((t.contains("추억")||t.contains("기록"))&&t.contains("따로보관해"))) return VoiceCommand.Backup
        if (t.contains("계획안") && (t.contains("읽어") || t.contains("불러") || t.contains("가져"))) return VoiceCommand.ImportPlan
        if (t.contains("추억") && (t.contains("알려") || t.contains("들려") || t.contains("몇") || t.contains("읽어"))) return VoiceCommand.Album
        if (t.startsWith("기억해") || t.endsWith("기억해줘") || t.endsWith("기억해")) {
            val note=original.replace(Regex("^(플리야\\s*)?기억해(?:줘)?[ ,]*"), "").replace(Regex("[ ,]*기억해(?:\\s*줘)?$"), "").trim().take(300)
            if(note.isNotBlank())return VoiceCommand.Remember(note)
        }
        if ((t.contains("일정추가") || t.endsWith("추가해줘") || t.endsWith("일정등록"))) {
            val date = when { t.contains("모레") -> today.plusDays(2); t.contains("내일") -> today.plusDays(1); else -> today }
            val title = original.replace(Regex("^(플리야\\s*)?(오늘|내일|모레)?\\s*"), "").replace(Regex("\\s*(일정)?\\s*(추가해줘|추가|등록해줘|등록)$"), "").trim()
            if (title.isNotBlank()&&title.codePointCount(0,title.length)<=120) return VoiceCommand.AddPlan(date.toString(), title)
        }
        if ((t.contains("오늘") || t.contains("내일") || t.contains("일정")) && (t.contains("뭐") || t.contains("알려") || t.contains("읽어"))) return VoiceCommand.FamilyAsk("BRIEF",day,parent,refresh)
        Regex("(?:내이름은|이름을)(.+?)(?:이야|예요|야|로바꿔줘|으로바꿔줘)$").find(t)?.groupValues?.get(1)?.let { name ->
            if (name.isNotBlank() && name.codePointCount(0,name.length) <= 30) return VoiceCommand.Name(name)
        }
        if (t in setOf("안녕","안녕하세요","반가워","좋은아침")) return if(question!=null&&Questions.correct(question,t))VoiceCommand.Answer(normalizeAnswer(t,question.game))else VoiceCommand.Greet
        if (t.contains("도와줘") || t.contains("뭐라고") || t.contains("어떻게") || t.contains("도움말")) return VoiceCommand.Help
        // A request that did not match a supported action is not a quiz answer.
        if (requestsPlay || listOf("줘","주세요","줄래","해봐").any(t::endsWith)) return VoiceCommand.Unrecognized(original)
        // A child's offer to do something is a conversational turn, not a guess.
        // Supported role changes above still win; an unrelated offer asks again.
        val offerStem=listOf("게요","래요","거예요","거야","게","래").firstOrNull(t::endsWith)?.let{t.removeSuffix(it)}
        val futureOffer=offerStem?.lastOrNull()?.let{it in '가'..'힣' && (it.code-'가'.code)%28==8}==true // Korean ㄹ + 게/래.
        if ((t.contains("내가") || t.startsWith("난")) && futureOffer) return VoiceCommand.Unrecognized(original)
        if (question != null) {
            val value = normalizeAnswer(t, question.game)
            if (value.isNotBlank()) return VoiceCommand.Answer(value)
        }
        return VoiceCommand.Unrecognized(original)
    }
    fun normalizeAnswer(text: String, game: Game): String {
        val value=compact(text).replace(Regex("^(정답은|답은|정답)"), "").replace(Regex("(?:개)?(?:입니다|이에요|예요|이야|이요|요|야)$|개$"), "")
        if(game==Game.MATH){
            val number=value.replace(Regex("(명|마리|번|시|살)$"),"")
            val sino=mapOf("영" to "0","일" to "1","이" to "2","삼" to "3","사" to "4","오" to "5","육" to "6","칠" to "7","팔" to "8","구" to "9","십" to "10","십일" to "11","십이" to "12","십삼" to "13","십사" to "14","십오" to "15","십육" to "16","십칠" to "17","십팔" to "18","십구" to "19","이십" to "20","하나" to "1","둘" to "2","셋" to "3","넷" to "4","다섯" to "5","여섯" to "6","일곱" to "7","여덟" to "8","아홉" to "9","열" to "10")
            return if(number.matches(Regex("\\d{1,3}"))) number else sino[number] ?: ""
        }
        val aliases=mapOf("애플" to "apple","에플" to "apple","트리" to "tree","트리이" to "tree","레인" to "rain","썬" to "sun","선" to "sun","문" to "moon","스타" to "star","도그" to "dog","독" to "dog")
        return aliases[value] ?: value
    }
}

object Questions {
    fun make(game: Game, round: Int, age: Int = 5,theme:String?=null): Question {
        if(game==Game.ENGLISH)return LearningCatalog.english(round,theme)
        if(game==Game.NATURE){
            val items=listOf(Triple("도토리는 어떤 나무에서 열릴까?","참나무",setOf("참나무","참나무에서")),Triple("나비가 되기 전에는 누구일까?","애벌레",setOf("애벌레","벌레")),Triple("개구리가 되기 전에는 누구일까?","올챙이",setOf("올챙이")))
            val (prompt,answer,accepted)=items[Math.floorMod(round,items.size)]
            return Question(prompt,prompt,answer,accepted,"정답은 $answer. 신기한 자연 친구야!",game)
        }
        val a=3+(round*3)%(if(age<6)5 else 9);val b=5+round%3;val c=2+round%2;val answer=(a+b-c).toString()
        return Question("$a + $b − $c = ?","$a 더하기 $b 빼기 $c 는?",answer,setOf(answer),"주판에 $a 를 놓고, $b 를 더하면 ${a+b}. 딸깍! 여기서 $c 개를 빼면 $answer. 한 알씩 생각해 보자.",Game.MATH)
    }
    fun correct(question: Question, value: String):Boolean{
        val heard=VoiceInterpreter.normalizeAnswer(AnswerMatch.collapseEcho(VoiceInterpreter.compact(value)),question.game)
        val accepted=question.accepted.flatMap{listOf(it,VoiceInterpreter.normalizeAnswer(it,question.game))}.toSet()
        if(heard in accepted)return true
        // Numbers stay exact. Words get one recogniser slip of leeway, judged on letters (jamo), not syllables.
        return question.game!=Game.MATH&&heard.isNotBlank()&&accepted.any{AnswerMatch.similarity(heard,it)>=AnswerMatch.WORD_SLIP}
    }
}

/** Recogniser slips on short child answers, measured on the app's own captured audio (2026-11-13). */
object AnswerMatch{
    const val WORD_SLIP=0.75
    private const val CHO="ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
    private const val JUNG="ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
    private const val JONG=" ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
    /** '트리리' -> '트리': the recogniser sometimes repeats the last syllable of a short word. */
    fun collapseEcho(text:String):String=if(text.length>=3&&text.last() in '가'..'힣'&&text.last()==text[text.length-2])text.dropLast(1)else text
    fun jamo(text:String):String=buildString{for(ch in text.lowercase()){if(ch in '가'..'힣'){val c=ch.code-0xAC00;append(CHO[c/588]);append(JUNG[(c%588)/28]);if(c%28!=0)append(JONG[c%28])}else append(ch)}}
    fun similarity(a:String,b:String):Double{
        val x=jamo(a);val y=jamo(b);if(x.isEmpty()||y.isEmpty())return 0.0
        var prev=IntArray(y.length+1){it}
        for(i in 1..x.length){val cur=IntArray(y.length+1);cur[0]=i;for(j in 1..y.length)cur[j]=minOf(prev[j]+1,cur[j-1]+1,prev[j-1]+if(x[i-1]==y[j-1])0 else 1);prev=cur}
        return 1.0-prev[y.length].toDouble()/maxOf(x.length,y.length)
    }
}
