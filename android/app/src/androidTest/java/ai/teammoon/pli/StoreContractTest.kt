package ai.teammoon.pli

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.data.*
import ai.teammoon.pli.domain.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class StoreContractTest{
 @Test fun actualAtomicWriterReaderRestartAndCorruptionProtection(){
  val c=InstrumentationRegistry.getInstrumentation().targetContext;val f=File(c.cacheDir,"store-contract-${java.util.UUID.randomUUID()}.json")
  try{val d=SavedData(profile=ChildProfile("가".repeat(30)),plans=listOf(Plan("test","2026-11-10","제".repeat(120))),revision=1);val store=PliStore(c,f);assertEquals(d,store.save(d));assertEquals(d,PliStore(c,f).load());f.writeText("broken");val broken=PliStore(c,f);assertThrows(IllegalStateException::class.java){broken.load()};assertThrows(IllegalStateException::class.java){broken.save(SavedData())};assertEquals("broken",f.readText())}finally{f.delete();File(f.path+".bak").delete();File(f.path+".new").delete()}
 }
 @Test fun commitFailureAndUnknownReadbackPreserveRecoverableFiles(){
  val c=InstrumentationRegistry.getInstrumentation().targetContext;val f=File(c.cacheDir,"commit-fault-${java.util.UUID.randomUUID()}.json")
  val old=SavedData(plans=emptyList(),revision=1);val next=old.copy(revision=2,plans=listOf(Plan("next","2026-11-10","새 일정")))
  try{
   PliStore(c,f).save(old)
   val before=PliStore(c,f){at->if(at=="BEFORE_FINISH")throw java.io.IOException("simulated write failure")}
   assertThrows(java.io.IOException::class.java){before.save(next)};assertEquals(old,PliStore(c,f).load())
   val unknown=PliStore(c,f){at->if(at=="BEFORE_READBACK")throw java.io.IOException("simulated read failure")}
   assertThrows(IllegalStateException::class.java){unknown.save(next)};assertEquals("COMMIT_UNKNOWN",unknown.recoveryError)
   assertThrows(IllegalStateException::class.java){unknown.save(old)};assertEquals(next,PliStore(c,f).load())
  }finally{f.delete();File(f.path+".bak").delete();File(f.path+".new").delete()}
 }
 @Test fun durableSessionEpochRejectsAStartArrivingAfterStop(){
  val c=InstrumentationRegistry.getInstrumentation().targetContext;val f=File(c.cacheDir,"journal-${java.util.UUID.randomUUID()}.json")
  try{val j=SessionJournal(c,f);assertTrue(j.write(SessionMark("one",2,10,false,true)));assertFalse(j.write(SessionMark("one",1,10,true,true)));assertFalse(j.read()!!.active);assertTrue(j.write(SessionMark("two",3,10,true,true)));assertTrue(SessionJournal(c,f).read()!!.active);assertThrows(IllegalArgumentException::class.java){j.confirmReboot(10,10)};j.confirmReboot(10,11);assertFalse(j.read()!!.active)}finally{f.delete();File(f.path+".bak").delete()}
 }
 @Test fun firstPrivateLaunchDoesNotInventAChildOrSchoolSchedule(){val c=InstrumentationRegistry.getInstrumentation().targetContext;val f=File(c.cacheDir,"fresh-${java.util.UUID.randomUUID()}.json");val d=PliStore(c,f).load();assertTrue(d.plans.isEmpty());assertEquals("친구",d.profile.name);assertEquals("",d.profile.school);assertFalse(f.exists())}

 @Test fun fullFamilyDocumentSurvivesAtomicStoreReloadAndBackup(){
  val c=InstrumentationRegistry.getInstrumentation().targetContext;val f=File(c.cacheDir,"family-contract-${java.util.UUID.randomUUID()}.json")
  val backup=File(c.getExternalFilesDir(null),"pli-backup.json");val previous=backup.takeIf{it.exists()}?.readBytes();var document:File?=null
  try{
   val text="긴 알림장😀. ".repeat(3000);val fact=FamilyFact("REPORT","2026-11-11","fixture:"+java.util.UUID.randomUUID(),text.take(100),"https://www.kidsnote.com/service/report",100,status="AVAILABLE",truncated=true,coverage=QueryCoverage(true,3,false,"END"),fullText=text)
   val store=PliStore(c,f);val canonical=store.save(SavedData(plans=emptyList(),facts=listOf(fact)))
   val read=PliStore(c,f).load().facts.single();assertNull(read.fullText);assertNotNull(read.documentId);assertEquals(text,FamilyDocuments.read(c,read));assertEquals(fact.coverage,read.coverage)
   document=File(c.filesDir,"family-documents/${read.documentId}.txt")
   val restored=DataContract.decode(store.backup(canonical).readText());assertEquals(text,restored.facts.single().fullText)
   val cursor=ReadingContext(FamilyDocuments.read(c,read),read.documentId!!,read.sourceScope,1);val result=StringBuilder();do{result.append(cursor.current())}while(cursor.next());assertEquals(text.filterNot(Char::isWhitespace),result.toString().filterNot(Char::isWhitespace))
   document!!.writeText("corrupt");assertThrows(IllegalStateException::class.java){FamilyDocuments.read(c,read)}
  }finally{document?.delete();f.delete();File(f.path+".bak").delete();File(f.path+".new").delete();if(previous==null)backup.delete()else backup.writeBytes(previous)}
 }

}
