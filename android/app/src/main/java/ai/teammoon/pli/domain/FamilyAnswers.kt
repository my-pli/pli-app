package ai.teammoon.pli.domain

import java.time.*
import java.time.format.DateTimeFormatter

object FamilyAnswers{
    fun label(topic:String)=when(topic){"BRIEF"->"일정";"MENU"->"식단표";"REPORT","REPORT_RECENT"->"알림장";"NOTICES"->"공지";"MONTHLY"->"놀이계획";"ALBUMS"->"앨범";else->"알림"}
    fun introduction(fact:FamilyFact,parent:Boolean,now:Long=System.currentTimeMillis()/1000):String{
        val checked=Instant.ofEpochSecond(fact.retrievedAt).atZone(ZoneId.of("Asia/Seoul")).format(DateTimeFormatter.ofPattern("M월 d일 HH:mm"))
        val stale=if(now-fact.retrievedAt>300)"지금 새로 확인한 내용은 아니에요. $checked 확인 자료예요. "else"$checked 확인 자료예요. "
        val partial=if(fact.status=="PARTIAL"||fact.coverage?.complete==false)"일부 범위만 확인했어요. 확인하지 못한 소식이 더 있을 수 있어요. "else""
        return stale+partial+"어린이집 ${label(fact.topic)}${if(parent)"를 읽어드릴게요."else"를 읽어줄게."} "
    }
    fun speech(fact:FamilyFact,parent:Boolean,now:Long=System.currentTimeMillis()/1000):String{
        val checked=Instant.ofEpochSecond(fact.retrievedAt).atZone(ZoneId.of("Asia/Seoul")).format(DateTimeFormatter.ofPattern("M월 d일 HH:mm"))
        val stale=if(now-fact.retrievedAt>300)"지금 새로 확인한 내용은 아니에요. $checked 확인 자료예요. "else""
        if(fact.status=="EMPTY")return stale+if(fact.coverage?.complete==true)"${LocalDate.parse(fact.date).monthValue}월 ${LocalDate.parse(fact.date).dayOfMonth}일 기준으로 확인한 어린이집 ${label(fact.topic)} 자료가 없어요."else"확인 범위가 충분하지 않아 자료가 없다고 확정할 수 없어요. 다시 확인해 주세요."
        if(fact.status=="PARTIAL"&&fact.text.isBlank())return stale+"일부 자료만 조회되어 소식이 없다고 확정할 수 없어요. 나머지 범위는 다시 확인해 주세요."
        if(fact.status in setOf("FAILED","AUTH_REQUIRED","UNSUPPORTED"))return stale+"지금은 어린이집 ${label(fact.topic)}를 확인하지 못했어요. 가족 연결을 확인해 주세요."
        val max=if(parent)1000 else 260
        val count=fact.text.codePointCount(0,fact.text.length)
        val text=if(count>max)fact.text.substring(0,fact.text.offsetByCodePoints(0,max))else fact.text
        return introduction(fact,parent,now)+(if(count>max||fact.truncated)"앞부분이에요. "else"")+text
    }
    fun sample(topic:String,date:LocalDate):String=when(topic){
        "MENU"->"공개 체험용 샘플 식단표예요. 점심은 밥과 미역국, 간식은 사과예요. 실제 가족의 식단과는 달라요."
        "REPORT","REPORT_RECENT"->"공개 체험용 샘플 알림장이에요. 오늘은 친구들과 나뭇잎 색깔을 찾아봤대요. 실제 아이의 알림장은 개인용 앱에서만 읽어드려요."
        "MONTHLY"->"공개 체험용 샘플 놀이계획이에요. 이번 달에는 가을 숲과 나뭇잎을 살펴보는 놀이가 있어요."
        "ALBUMS"->"공개 체험에서는 샘플 소식만 들려드려요. 가족의 사진과 앨범은 개인용 앱에서 확인할 수 있어요."
        else->"공개 체험용 샘플 공지예요. 내일 숲 체험에는 운동화와 물병을 챙겨요. 실제 가족의 공지는 개인용 앱에서 확인해 주세요."
    }
}
