package ai.teammoon.pli

import ai.teammoon.pli.data.DataContract as C
import ai.teammoon.pli.domain.*
import org.junit.Assert.*
import org.junit.Test

class DataContractTest{
 private val scope="test-child-center"
 private fun plan(id:String="a",title:String="제목",date:String="2026-11-10")=Plan("kidsnote:$id",date,title,origin="KIDSNOTE",sourceScope=scope,sourceEventId=id)
 private fun batch(plans:List<Plan>,seq:Long=1,complete:Boolean=false)=ImportBatch("batch:$seq",scope,seq,windowStart="2026-11-01",windowEnd="2026-11-30",complete=complete,plans=plans)
 @Test fun acceptedUnicodeSurvivesSerialization(){for(n in listOf(16,17,30)){val data=SavedData(profile=ChildProfile("😀".repeat(n)),plans=listOf(plan(title="가".repeat(120))));assertEquals(data,C.decode(C.gson.toJson(C.validate(data))))};assertThrows(IllegalArgumentException::class.java){C.validate(SavedData(profile=ChildProfile("😀".repeat(31))))};assertThrows(IllegalArgumentException::class.java){C.plan(plan(title="가".repeat(121)))}}
 @Test fun legacyLongFieldsAndExplicitEmptyArraysArePreserved(){val old="""{"version":2,"profile":{"name":"가나다라마바사아자차카타파하가나다","age":5,"school":"","volume":0.7},"plans":[{"id":"manual","date":"2026-11-10","title":"${"가".repeat(101)}"}],"memories":[]}""";val d=C.decode(old);assertEquals(4,d.version);assertEquals(101,d.plans.single().title.length);assertEquals("LEGACY",d.plans.single().origin);assertEquals(0,C.decode(old.replace(old.substringAfter("\"plans\":").substringBefore(",\"memories\""),"[]")).plans.size)}
 @Test fun capacityRejectsWholeBatchWithoutMisreporting(){val base=SavedData(plans=(0 until 500).map{Plan("m$it","2026-11-10","수기 $it")});assertThrows(IllegalArgumentException::class.java){C.merge(base,batch((0 until 10).map{plan("new$it")}))};assertEquals(500,base.plans.size);assertFalse(base.plans.any{it.origin=="KIDSNOTE"})}
 @Test fun receiptMatchesActualContentsAndRetryIsIdempotent(){val b=batch(listOf(plan(),plan(),plan("b")));val (d,r)=C.merge(SavedData(plans=emptyList()),b);assertEquals(3,r.received);assertEquals(1,r.duplicateInput);assertEquals(2,r.created);assertEquals(2,d.plans.size);assertEquals(d,C.merge(d,b).first);assertEquals(r,C.merge(d,b).second);assertEquals(C.digest(d.plans),r.retainedIdsDigest)}
 @Test fun scopeAndManualOwnershipSurviveVerifiedEmptySnapshot(){val manual=Plan("manual","2026-11-10","제목");val other=plan("other").copy(sourceScope="other-child");val base=SavedData(plans=listOf(manual,plan(),other));val(d,r)=C.merge(base,batch(emptyList(),complete=true));assertEquals(setOf(manual.id,other.id),d.plans.map{it.id}.toSet());assertEquals(1,r.removed);assertTrue(r.committed);assertEquals(0,r.retainedFromBatch)}
 @Test fun partialEmptyDoesNotDeleteAndDateChangeUpdatesStableId(){val base=SavedData(plans=listOf(plan()));assertEquals(base.plans,C.merge(base,batch(emptyList())).first.plans);val(d,r)=C.merge(base,batch(listOf(plan(date="2026-11-12"))));assertEquals(1,d.plans.size);assertEquals("2026-11-12",d.plans.single().date);assertEquals(1,r.updated);assertEquals(0,r.created)}
 @Test fun staleRevisionAndConflictingIdsAreRejected(){val base=C.merge(SavedData(plans=emptyList()),batch(listOf(plan()),2)).first;assertThrows(IllegalArgumentException::class.java){C.merge(base,batch(listOf(plan()),1))};assertThrows(IllegalArgumentException::class.java){C.merge(base,batch(listOf(plan()),3).copy(baseRevision=0))};assertThrows(IllegalArgumentException::class.java){C.merge(base,batch(listOf(plan(),plan(title="다름")),3))}}
 @Test fun manualSameContentIsNeverRemovedAsSeed(){val manual=Plan("manual","2026-11-10","가을 숲에서 도토리 찾기","운동화와 물병");val(d,_)=C.merge(SavedData(plans=listOf(manual)),batch(listOf(plan(title=manual.title))));assertTrue(d.plans.contains(manual));assertEquals(2,d.plans.size)}
 @Test fun unsupportedCorruptNullAndImpossibleDateNeverBecomeSamples(){for(raw in listOf("{broken","{\"version\":99}","{\"version\":2,\"profile\":null,\"plans\":[],\"memories\":[]}"))assertThrows(Exception::class.java){C.decode(raw)};assertThrows(Exception::class.java){C.plan(plan(date="2026-02-30"))}}
 @Test fun serializedCalendarSnapshotWithOmittedOptionalFactsIsAValidCompleteBatch(){
  val raw=C.gson.toJsonTree(batch(emptyList(),complete=true)).asJsonObject;raw.remove("facts")
  val decoded=C.gson.fromJson(raw,ImportBatch::class.java);val manual=Plan("manual","2026-11-11","가족 일정")
  val(base,receipt)=C.merge(SavedData(plans=listOf(manual)),decoded);assertTrue(receipt.committed);assertEquals(listOf(manual),base.plans)
  assertEquals(base,C.merge(base,decoded).first)
 }

}
