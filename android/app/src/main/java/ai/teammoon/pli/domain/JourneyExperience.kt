package ai.teammoon.pli.domain

import java.time.LocalDate

data class GrowthSummary(val stamps:Int,val kilometers:Float?,val answered:Int,val correct:Int,val recent:List<Memory>,val dailyStamps:List<Int>){
    val accuracy:Int? get()=if(answered>0)(correct*100.0/answered).toInt()else null
    companion object{
        fun from(memories:List<Memory>,today:LocalDate=LocalDate.now()):GrowthSummary{
            val known=memories.mapNotNull{it.kilometers}
            val sorted=memories.sortedWith(compareByDescending<Memory>{it.date}.thenBy{it.id})
            return GrowthSummary(memories.size,known.takeIf{it.isNotEmpty()}?.sum(),memories.sumOf{it.answered},memories.sumOf{it.correct},sorted.take(3),(6 downTo 0).map{days->memories.count{it.date==today.minusDays(days.toLong()).toString()}})
        }
    }
}

object AbacusSteps{
    fun values(q:Question?):List<Int>{
        if(q?.game!=Game.MATH)return emptyList()
        val n=Regex("\\d+").findAll(q.prompt).map{it.value.toInt()}.toList()
        if(n.size!=3)return emptyList()
        return listOf(n[0],n[0]+n[1],n[0]+n[1]-n[2]).takeIf{it.all{v->v in 0..99}}?:emptyList()
    }
}

object Vocabulary{
    val words=LearningCatalog.words.associate{it.ko to it.en}
    fun find(text:String):Pair<String,String>?{
        val t=VoiceInterpreter.compact(text)
        if(!t.contains("영어로"))return null
        return words.entries.sortedByDescending{it.key.length}.firstOrNull{t.substringBefore("영어로").endsWith(it.key)||t.substringBefore("영어로").endsWith(it.key+"는")||t.substringBefore("영어로").endsWith(it.key+"은")||t.substringBefore("영어로").endsWith(it.key+"가")}?.let{it.key to it.value}
    }
}

/** Reads measured signals only. Slow movement is not labelled as a known traffic jam. */
class JourneyContextEngine{
    private var slowSince:Long?=null
    private var cruiseSince:Long?=null
    private var lastEvent=Long.MIN_VALUE
    private var altitude:Pair<Long,Double>?=null
    fun update(s:VehicleState,now:Long):String?{
        val moving=s.gear=="D";val speed=s.speedKmh
        slowSince=if(moving&&speed!=null&&speed<=5f)slowSince?:now else null
        cruiseSince=if(moving&&speed!=null&&speed>=60f)cruiseSince?:now else null
        val old=altitude
        if(s.altitudeMeters!=null&&(old==null||now-old.first>=15000))altitude=now to s.altitudeMeters
        if(lastEvent!=Long.MIN_VALUE&&now-lastEvent<120000)return null
        val kind=when{
            s.cabinTemperatureC?.let{it>=28f}==true&&s.cabinTemperatureArea!=null&&now-s.cabinTemperatureAt in 0..60000->"warm_cabin"
            moving&&speed!=null&&speed>=8&&old!=null&&s.altitudeMeters!=null&&now-old.first in 5000..20000&&old.second-s.altitudeMeters>=5->"downhill"
            slowSince?.let{now-it>=20000}==true->"slow_road"
            cruiseSince?.let{now-it>=8000}==true->"cruise"
            else->null
        }
        if(kind!=null)lastEvent=now
        return kind
    }
}
