package ai.teammoon.pli.domain

/** Project-authored, reviewed short activities; age 3–8, no external text or generated facts. */
object LearningCatalog{
    data class Word(val ko:String,val en:String,val pronunciation:String,val theme:String)
    val words=listOf(
        Word("사과","apple","애플","FOOD"),Word("물","water","워터","WATER"),Word("우유","milk","밀크","FOOD"),Word("바나나","banana","버내너","FOOD"),
        Word("나무","tree","트리","FOREST"),Word("나뭇잎","leaf","리프","FOREST"),Word("도토리","acorn","에이콘","FOREST"),Word("꽃","flower","플라워","FOREST"),Word("숲","forest","포리스트","FOREST"),
        Word("비","rain","레인","WEATHER"),Word("해","sun","썬","WEATHER"),Word("달","moon","문","WEATHER"),Word("별","star","스타","WEATHER"),Word("구름","cloud","클라우드","WEATHER"),Word("눈","snow","스노우","WEATHER"),
        Word("개","dog","도그","ANIMAL"),Word("고양이","cat","캣","ANIMAL"),Word("나비","butterfly","버터플라이","FOREST"),Word("새","bird","버드","FOREST"),Word("물고기","fish","피시","WATER"),Word("거북이","turtle","터틀","ANIMAL"),
        Word("빨간색","red","레드","COLOR"),Word("파란색","blue","블루","COLOR"),Word("노란색","yellow","옐로우","COLOR"),Word("초록색","green","그린","COLOR"),
        Word("친구","friend","프렌드","SCHOOL"),Word("선생님","teacher","티처","SCHOOL"),Word("책","book","북","SCHOOL"),Word("가방","bag","백","SCHOOL"),
        Word("자동차","car","카","TRAFFIC"),Word("버스","bus","버스","TRAFFIC"),Word("기차","train","트레인","TRAFFIC"),Word("신호등","traffic light","트래픽라이트","TRAFFIC")
    )
    fun theme(text:String):String?=listOf("FOREST" to listOf("숲","나뭇잎","도토리"),"WATER" to listOf("물놀이","수영","바다"),"TRAFFIC" to listOf("교통","버스","기차"),"FOOD" to listOf("요리","사과","음식"),"COLOR" to listOf("색깔","색칠")).firstOrNull{(_,keys)->keys.any(text::contains)}?.first
    fun english(round:Int,theme:String?):Question{
        val items=words.filter{theme==null||it.theme==theme}.ifEmpty{words};val w=items[Math.floorMod(round,items.size)]
        return Question("${topicParticle(w.ko)} 영어로?","${topicParticle(w.ko)} 영어로 뭘까?",w.en,setOf(w.en,w.pronunciation),"${topicParticle(w.ko)} 영어로 ${w.en}. 함께 말해 보자.",Game.ENGLISH)
    }
    data class Turn(val prompt:String,val answers:Set<String>,val hint:String)
    val dialogue=listOf(
        Turn("Hello! 인사해 줄래?",setOf("hello","hallo","hullo","hellow","hi","hey","헐로","할로","헬로","헬로우","핼로","하이","헤이","안녕","안녕하세요"),"Hello, 또는 Hi라고 인사해 보자."),
        Turn("How are you? 오늘 기분이 어때?",setOf("good","happy","fine","sad","tired","imgood","imhappy","imfine","imsad","imtired","iamhappy","iamgood","iamfine","iamsad","iamtired","아임해피","아임굿","아임파인","굿","해피","파인","좋아","행복해","슬퍼","피곤해"),"Good, happy, sad처럼 지금 기분을 말해 줘."),
        Turn("See you! 다음에 또 만나자. 뭐라고 인사할까?",setOf("bye","byebye","goodbye","goodby","seeyou","seeyoulater","바이","바이바이","굿바이","씨유","시유","잘가","또만나","안녕"),"Bye, 또는 See you라고 말해 보자.")
    )
    fun dialogueQuestion(turn:Int):Question{val t=dialogue[turn];return Question(t.prompt,t.prompt,t.answers.first(),t.answers,t.hint,Game.ENGLISH)}
    fun followup(answer:String):String?=when{listOf("빨간","노란","파란","초록").any(answer::contains)->"그 색은 어디에서 봤어? 눈에 보인 걸 하나만 들려줘.";listOf("나무","나뭇잎","도토리","꽃").any(answer::contains)->"그 친구는 어떤 모양이었어? 네가 본 모습을 들려줘.";answer.contains("친구")->"친구와 함께한 순간 중에 무엇이 가장 기억에 남아?";else->null}
}
