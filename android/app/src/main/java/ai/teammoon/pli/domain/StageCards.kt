package ai.teammoon.pli.domain

import org.json.JSONObject

object StageCards{
    fun parse(json:JSONObject?,game:String?=null):StageCard?{
        if(json==null)return null
        val sections=json.optJSONArray("sections")?:return null
        val parsed=(0 until sections.length()).map{i->val s=sections.getJSONObject(i);val items=s.optJSONArray("items")
            CardSection(s.optString("title"),(0 until (items?.length()?:0)).map{j->val it=items!!.getJSONObject(j);CardItem(it.optString("icon"),it.optString("label"),it.optString("reason"))}.filter{it.label.isNotBlank()})}
        val place=json.optJSONObject("place")?.let{p->runCatching{StopPlace(p.getString("name"),p.optString("type"),p.getDouble("lat"),p.getDouble("lon"),p.optInt("minutesAway"),p.optInt("detourMinutes"))}.getOrNull()}
        return build(json.optString("kind"),json.optString("title"),json.optString("subtitle"),parsed,game)?.copy(place=place)
    }
    /** A card with nothing in it is no card. */
    fun build(kind:String,title:String,subtitle:String,sections:List<CardSection>,game:String?=null):StageCard?=
        sections.map{s->s.copy(items=s.items.filter{it.label.isNotBlank()})}.takeIf{it.any{s->s.items.isNotEmpty()}}?.let{StageCard(kind,title,subtitle,it,game=game)}
    private val packed=Regex("(챙겼|챙겨[어써쓰]|넣었|넣어[써어]|담았|챙김|준비했|다 ?했)")  // "챙겨어" is how the recogniser often hears "챙겼어"
    /** Labels a child's "물병 챙겼어" / "우산이랑 장화 넣었어" / "다 챙겼어" ticks off; empty when it is not about packing. */
    fun ticked(card:StageCard,text:String):Set<String>{
        if(card.kind!="pack")return emptySet()
        val t=VoiceInterpreter.compact(text)
        if(!packed.containsMatchIn(t))return emptySet()
        if(Regex("^(다|전부|모두|몽땅)").containsMatchIn(t))return card.items.map{it.label}.toSet()
        return card.items.map{it.label}.filter{label->t.contains(VoiceInterpreter.compact(label))}.toSet()
    }
    private val yes=Regex("^(응|어|그래|좋아|시작|하자|할래|해줘|오케이|ㅇㅋ|네|예)")
    fun accepts(text:String)=yes.containsMatchIn(VoiceInterpreter.compact(text))
}
