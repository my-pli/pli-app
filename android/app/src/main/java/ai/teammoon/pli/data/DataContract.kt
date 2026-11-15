package ai.teammoon.pli.data

import ai.teammoon.pli.domain.*
import com.google.gson.Gson
import com.google.gson.JsonParser
import java.security.MessageDigest
import java.time.LocalDate

/** Shared by provider, voice writes, migration and disk reads. */
object DataContract {
    val gson=Gson()
    fun points(value:String)=value.codePointCount(0,value.length)
    fun text(value:String,max:Int,required:Boolean=false){require(points(value)<=max&&(!required||value.isNotBlank())){"INVALID_TEXT"}}
    fun profile(p:ChildProfile){text(p.name,30,true);require(p.age in 3..12&&p.volume.isFinite()&&p.volume in 0f..1f){"INVALID_PROFILE"}}
    fun plan(p:Plan){text(p.id,160,true);require(p.date==LocalDate.parse(p.date).toString()){"INVALID_DATE"};text(p.title,120,true);text(p.preparation,300);require(p.origin in setOf("MANUAL","LEGACY","KIDSNOTE","KIDSNOTE_LEGACY","DEMO_SEED")){"INVALID_ORIGIN"}}
    fun validate(data:SavedData):SavedData{
        require(data.version==4&&data.revision>=0){"UNSUPPORTED_VERSION"};profile(data.profile)
        require(data.plans.size<=500&&data.memories.size<=2000){"CAPACITY"}
        require(data.plans.map{it.id}.distinct().size==data.plans.size){"DUPLICATE_ID"};data.plans.forEach(::plan)
        data.memories.forEach{require(it.id.isNotBlank()&&it.correct>=0&&it.answered>=it.correct);LocalDate.parse(it.date);require(it.kilometers==null||(it.kilometers.isFinite()&&it.kilometers>=0))}
        require(data.facts.size<=100){"FACT_CAPACITY"};data.facts.forEach(::fact)
        destinations(data.destinations)
        require(data.batches.size<=16&&data.sourceSequences.size<=100){"METADATA_CAPACITY"};return data
    }
    fun decode(raw:String):SavedData{
        val o=JsonParser.parseString(raw).asJsonObject;val version=o["version"]?.asInt?:error("MISSING_VERSION")
        require(version in 2..4){"UNSUPPORTED_VERSION"};require(o.has("profile")&&o.has("plans")&&o.has("memories")){"MISSING_DATA"}
        val p=o["profile"].asJsonObject
        val profile=ChildProfile(name=p["name"].asString,age=p["age"].asInt,school=p["school"]?.takeUnless{it.isJsonNull}?.asString?:"",volume=p["volume"]?.takeUnless{it.isJsonNull}?.asFloat?:.7f)
        val plans=o["plans"].asJsonArray.map{j->val p=j.asJsonObject
            Plan(id=p["id"].asString,date=p["date"].asString,title=p["title"].asString,preparation=p["preparation"]?.takeUnless{it.isJsonNull}?.asString?:"",origin=p["origin"]?.takeUnless{it.isJsonNull}?.asString?:if(p["id"].asString.startsWith("kidsnote:"))"KIDSNOTE_LEGACY" else "LEGACY",sourceScope=p["sourceScope"]?.takeUnless{it.isJsonNull}?.asString,sourceEventId=p["sourceEventId"]?.takeUnless{it.isJsonNull}?.asString)
        }
        val memories=o["memories"].asJsonArray.map{gson.fromJson(it,Memory::class.java)}
        val loaded=if(version>=3)gson.fromJson(raw,SavedData::class.java)else SavedData(profile=profile,plans=plans,memories=memories)
        return validate(loaded.copy(version=4,profile=profile,plans=plans,memories=memories,batches=if(o.has("batches"))loaded.batches?:emptyList() else emptyList(),sourceSequences=if(o.has("sourceSequences"))loaded.sourceSequences?:emptyMap() else emptyMap(),facts=o["facts"]?.takeUnless{it.isJsonNull}?.asJsonArray?.map{gson.fromJson(it,FamilyFact::class.java)}?:emptyList(),destinations=o["destinations"]?.takeUnless{it.isJsonNull}?.asJsonArray?.map{gson.fromJson(it,DestinationChoice::class.java)}?:emptyList()))
    }
    fun destinations(values:List<DestinationChoice>){require(values.size<=12&&values.map{it.id}.distinct().size==values.size){"INVALID_DESTINATIONS"};values.forEach{text(it.id,80,true);text(it.name,80,true);text(it.address,200);require(it.latitude.isFinite()&&it.longitude.isFinite()&&it.latitude in -90.0..90.0&&it.longitude in -180.0..180.0){"INVALID_COORDINATES"}}}
    fun digest(plans:List<Plan>)=MessageDigest.getInstance("SHA-256").digest(gson.toJson(plans.sortedBy{it.id}).toByteArray()).joinToString(""){"%02x".format(it)}
    fun fact(f:FamilyFact){require(f.topic in setOf("BRIEF","MENU","REPORT","REPORT_RECENT","NOTICES","MONTHLY","ALBUMS","NOTIFICATIONS"));LocalDate.parse(f.date);text(f.sourceScope,160,true);text(f.text,2400);require(f.retrievedAt>0&&f.status in setOf("AVAILABLE","EMPTY","PARTIAL","AUTH_REQUIRED","FAILED","UNSUPPORTED"));require(f.sourceUrl.startsWith("https://www.kidsnote.com/service/"));require(f.fullText==null||f.fullText.toByteArray(Charsets.UTF_8).size<=128*1024){"DOCUMENT_CAPACITY"};require(f.documentId==null||f.documentId.matches(Regex("[a-f0-9]{64}"))){"INVALID_DOCUMENT"};if(f.windowStart!=null||f.windowEnd!=null){require(f.windowStart!=null&&f.windowEnd!=null);require(LocalDate.parse(f.windowStart)<=LocalDate.parse(f.windowEnd))};f.coverage?.let{require(it.pagesRead in 0..100&&it.reason.length<=80)}}
    fun merge(base:SavedData,incoming:ImportBatch):Pair<SavedData,ImportReceipt>{
        val batch=incoming.copy(facts=incoming.facts.orEmpty())
        validate(base);text(batch.batchId,120,true);text(batch.sourceScope,160,true)
        val inputDigest=MessageDigest.getInstance("SHA-256").digest(gson.toJson(batch.copy(baseRevision=null)).toByteArray()).joinToString(""){"%02x".format(it)}
        base.batches.firstOrNull{it.batchId==batch.batchId}?.let{require(base.sourceSequences[batch.sourceScope]==batch.sourceSequence){"STALE_BATCH"};require(it.inputDigest!=null&&it.inputDigest==inputDigest){"BATCH_PAYLOAD_CONFLICT"};return base to it}
        require(batch.baseRevision==null||batch.baseRevision==base.revision){"REVISION_CONFLICT"}
        require(batch.sourceSequence>(base.sourceSequences[batch.sourceScope]?:-1)){"STALE_BATCH"}
        require(batch.plans.size<=500){"CAPACITY"};batch.profile?.let(::profile)
        require(batch.facts.size<=100);batch.facts.forEach{fact(it);require(it.sourceScope==batch.sourceScope){"INVALID_SCOPE"}}
        batch.plans.forEach{plan(it);require(it.origin=="KIDSNOTE"&&it.sourceScope==batch.sourceScope&&it.sourceEventId!=null){"INVALID_SCOPE"}}
        val unique=batch.plans.distinctBy{it.id};require(unique.size==batch.plans.distinctBy{it.id to it}.size){"CONFLICTING_DUPLICATE"}
        if(batch.complete){require(batch.windowStart!=null&&batch.windowEnd!=null);require(LocalDate.parse(batch.windowStart)<=LocalDate.parse(batch.windowEnd))}
        val ids=unique.map{it.id}.toSet();val old=base.plans.associateBy{it.id}
        unique.forEach{p->old[p.id]?.let{require(it.origin=="KIDSNOTE"&&it.sourceScope==batch.sourceScope){"ID_OWNERSHIP"}}}
        val removals=if(batch.complete)base.plans.filter{it.origin=="KIDSNOTE"&&it.sourceScope==batch.sourceScope&&it.date>=batch.windowStart!!&&it.date<=batch.windowEnd!!&&it.id !in ids}else emptyList()
        val removed=removals.map{it.id}.toSet();val merged=base.plans.filter{it.id !in ids&&it.id !in removed}+unique
        require(merged.size<=500){"CAPACITY"}
        val created=unique.count{it.id !in old};val unchanged=unique.count{old[it.id]==it};val updated=unique.size-created-unchanged
        val receipt=ImportReceipt(batch.batchId,batch.plans.size,duplicateInput=batch.plans.size-unique.size,acceptedUnique=unique.size,created=created,updated=updated,unchanged=unchanged,removed=removed.size,committed=true,retainedFromBatch=unique.size,storeRevision=base.revision+1,retainedIdsDigest=digest(unique),inputDigest=inputDigest)
        val keys=batch.facts.map{Triple(it.sourceScope,it.topic,it.date)}.toSet()
        val facts=base.facts.filter{Triple(it.sourceScope,it.topic,it.date) !in keys}+batch.facts
        return validate(base.copy(facts=facts.sortedByDescending{it.retrievedAt}.take(100),activeSourceScope=batch.sourceScope,profile=batch.profile?.let{base.profile.copy(name=it.name,age=it.age,school=it.school.takeIf(String::isNotBlank)?:base.profile.school)}?:base.profile,plans=merged,revision=base.revision+1,batches=(base.batches+receipt).takeLast(16),sourceSequences=base.sourceSequences+(batch.sourceScope to batch.sourceSequence))) to receipt
    }
}
