package ai.teammoon.pli

import android.app.Instrumentation
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.ProviderInfo
import android.net.Uri
import android.os.Handler
import android.os.ParcelFileDescriptor
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.data.*
import ai.teammoon.pli.domain.*
import com.google.gson.JsonObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.cancel
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** Production Provider/parser/Application/store, isolated filesystem; no real family writes. */
@RunWith(AndroidJUnit4::class)
class ProviderContractTest{
 private class Fixture(seed:SavedData?=null,raw:String?=null):AutoCloseable{
  val base=InstrumentationRegistry.getInstrumentation().targetContext
  val root=File(base.cacheDir,"provider-contract-${UUID.randomUUID()}").apply{mkdirs()}
  private var owner:PliApplication?=null
  val context=object:ContextWrapper(base){override fun getFilesDir()=root;override fun getExternalFilesDir(type:String?)=File(root,"external").apply{mkdirs()};override fun getApplicationContext():Context=owner?:base.applicationContext}
  lateinit var app:PliApplication;private set
  lateinit var provider:DemoStateProvider;private set
  init{seed?.let{PliStore(context).save(it)};raw?.let{File(root,"pli-data.json").writeText(it)};boot()}
  private fun boot(){app=Instrumentation.newApplication(PliApplication::class.java,context)as PliApplication;owner=app;app.onCreate();provider=DemoStateProvider().apply{attachInfo(this@Fixture.context,ProviderInfo().apply{authority="ai.teammoon.pli.fixture";exported=false})}}
  private fun stop(){(PliApplication::class.java.getDeclaredField("main").apply{isAccessible=true}.get(app)as Handler).removeCallbacksAndMessages(null);(PliApplication::class.java.getDeclaredField("scope").apply{isAccessible=true}.get(app)as CoroutineScope).cancel()}
  fun restart(){stop();boot()}
  fun data()=PliStore(context).load()
  fun read(path:String):ByteArray=ParcelFileDescriptor.AutoCloseInputStream(provider.openFile(Uri.parse("content://ai.teammoon.pli.fixture/$path"),"r")).use{it.readBytes()}
  fun write(path:String,bytes:ByteArray){assertSame("Provider must use the isolated Application",app,provider.context!!.applicationContext);val revision=app.importRevision;var writeError:Throwable?=null;runCatching{ParcelFileDescriptor.AutoCloseOutputStream(provider.openFile(Uri.parse("content://ai.teammoon.pli.fixture/$path"),"w")).use{it.write(bytes)}}.onFailure{writeError=it};val end=System.currentTimeMillis()+10000;while(app.importRevision==revision&&System.currentTimeMillis()<end)Thread.sleep(20);assertTrue("Writer must publish a terminal receipt: ${writeError?.javaClass?.name}",app.importRevision>revision)}
  fun send(batch:ImportBatch):ImportReceipt{write("family",DataContract.gson.toJson(batch).toByteArray());val status=DataContract.gson.fromJson(String(read("integration")),JsonObject::class.java);return DataContract.gson.fromJson(status["receipt"],ImportReceipt::class.java)}
  override fun close(){stop();root.deleteRecursively()}
 }
 private fun row(id:String="one",title:String="새 일정",scope:String="synthetic-a")=Plan("kidsnote:$scope:$id","2026-11-11",title,origin="KIDSNOTE",sourceScope=scope,sourceEventId=id)
 private fun batch(rows:List<Plan>,seq:Long=1,scope:String="synthetic-a",complete:Boolean=false,profile:ChildProfile?=null)=ImportBatch(UUID.randomUUID().toString(),scope,seq,windowStart="2026-11-01",windowEnd="2026-11-30",complete=complete,plans=rows,profile=profile)

 @Test fun unicodeBoundariesRoundTripThroughProviderAndApplicationRestart(){
  Fixture().use{f->var seq=0L
   for(n in listOf(16,17,30))for(length in listOf(100,101,120)){val profile=ChildProfile("😀".repeat(n));val plan=row(title="제".repeat(length));val receipt=f.send(batch(listOf(plan),++seq,profile=profile));assertTrue(receipt.committed);f.restart();assertEquals(profile.name,f.data().profile.name);assertEquals(plan,f.data().plans.single());assertEquals(receipt.inputDigest,f.data().batches.last().inputDigest)}
   val before=f.data();assertFalse(f.send(batch(listOf(row()),++seq,profile=ChildProfile("😀".repeat(31)))).committed);assertEquals(before,f.data());assertFalse(f.send(batch(listOf(row(title="제".repeat(121))),++seq)).committed);f.restart();assertEquals(before,f.data())
  }
 }
 @Test fun fiveHundredManualPlansRejectTenWithoutLosingAnyOriginal(){val original=SavedData(profile=PliStore.freshData().profile,plans=(0 until 500).map{Plan("manual:$it","2026-11-11","수기 $it")});Fixture(original).use{f->val r=f.send(batch((0 until 10).map{row("new:$it")}));assertFalse(r.committed);assertEquals(0,r.retainedFromBatch);f.restart();assertEquals(original,f.data())}}
 @Test fun completeEmptyUpdateAndDeleteRespectManualAndOtherChild(){
  val manual=Plan("manual","2026-11-11","같은 제목");Fixture(SavedData(profile=PliStore.freshData().profile,plans=listOf(manual))).use{f->
   assertTrue(f.send(batch(listOf(row(title=manual.title)),complete=true)).committed)
   assertTrue(f.send(batch(listOf(row("other",scope="synthetic-b")),scope="synthetic-b")).committed)
   val updated=row(title="변경된 일정");assertEquals(1,f.send(batch(listOf(updated),seq=2)).updated)
   assertEquals(1,f.send(batch(emptyList(),seq=3,complete=true)).removed);f.restart();assertEquals(setOf("manual","kidsnote:synthetic-b:other"),f.data().plans.map{it.id}.toSet())
  }
 }
 @Test fun duplicateRetryAndPayloadConflictUseActualStoredReceipt(){Fixture().use{f->val b=batch(listOf(row(),row()));val r=f.send(b);assertTrue(r.committed);assertEquals(1,r.duplicateInput);assertEquals(1,r.retainedFromBatch);assertEquals(r,f.send(b));val before=f.data();val invalid=f.send(b.copy(plans=listOf(row(title="다른 내용"))));assertFalse(invalid.committed);assertEquals("BATCH_PAYLOAD_CONFLICT",invalid.error);f.restart();assertEquals(before,f.data())}}
 @Test fun oldSequenceAndConcurrentManualRevisionAreRejected(){Fixture().use{f->assertTrue(f.send(batch(listOf(row()),seq=2)).committed);val before=f.data();assertFalse(f.send(batch(listOf(row()),seq=1)).committed);val stale=batch(listOf(row("two")),seq=3).copy(baseRevision=before.revision);f.app.commitSaved(before.copy(plans=before.plans+Plan("manual","2026-11-11","직접 등록")),false);assertFalse(f.send(stale).committed);f.restart();assertTrue(f.data().plans.any{it.id=="manual"});assertEquals(2,f.data().plans.size)}}
 @Test fun validLegacyEmptyAndBrokenStoresNeverBecomeDemoSeeds(){
  val raw="""{"version":2,"profile":{"name":"가나다라마바사아자차카타파하가나다","age":5},"plans":[],"memories":[]}"""
  Fixture(raw=raw).use{f->assertTrue(f.data().plans.isEmpty());assertTrue(f.send(batch(emptyList(),complete=true)).committed);f.restart();assertEquals(4,f.data().version);assertEquals("가나다라마바사아자차카타파하가나다",f.data().profile.name)}
  for(broken in listOf("broken","{\"version\":99}")){Fixture(raw=broken).use{f->assertFalse(f.send(batch(listOf(row()))).committed);assertEquals(broken,File(f.root,"pli-data.json").readText());assertNotNull(f.app.store.recoveryError)}}
 }
 @Test fun documentBytesLimitsAndActiveKindPreserveOtherOriginal(){Fixture().use{f->
  val image=byteArrayOf(1,2,3,4);File(f.root,"plan-input.jpg").writeBytes(image)
  val text="2026-11-11, 숲 체험, 물병".toByteArray();f.write("plan-text",text);assertArrayEquals(text,f.read("plan-text"));assertArrayEquals(image,f.read("plan-image"));assertEquals("text",String(f.read("plan-active")))
  assertEquals("숲 체험",kotlinx.coroutines.runBlocking{PlanImporter(f.context).read()}.single().title)
  f.write("plan-text",ByteArray(65537));assertNotNull(f.app.importError);assertArrayEquals(text,f.read("plan-text"));assertArrayEquals(image,f.read("plan-image"));assertEquals("text",String(f.read("plan-active")))
  f.write("plan-image",ByteArray(8*1024*1024+1));assertNotNull(f.app.importError);assertArrayEquals(image,f.read("plan-image"));f.restart();assertArrayEquals(text,f.read("plan-text"));assertEquals("text",String(f.read("plan-active")))
 }}
}
