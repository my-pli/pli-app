package ai.teammoon.pli.data

import android.content.Context
import android.util.AtomicFile
import com.google.gson.JsonParser
import java.io.File

data class SessionMark(val id:String,val epoch:Long,val deviceBoot:Int,val active:Boolean,val public:Boolean)
/** Durable resource intent, separate from family records. Monotone writes reject late starts. */
class SessionJournal(context:Context,path:File=File(context.filesDir,"voice-session.json")){
 private val file=AtomicFile(path)
 @Synchronized fun read():SessionMark?{
  if(!file.baseFile.exists()&&!File(file.baseFile.path+".bak").exists())return null
  val o=JsonParser.parseString(file.openRead().bufferedReader().use{it.readText()}).asJsonObject
  for(k in listOf("id","epoch","deviceBoot","active","public"))require(o.has(k)&&!o[k].isJsonNull){"JOURNAL_CORRUPT"}
  require(o["active"].asJsonPrimitive.isBoolean&&o["public"].asJsonPrimitive.isBoolean)
  return DataContract.gson.fromJson(o,SessionMark::class.java).also{require(it.epoch>=0&&it.deviceBoot>=0&&it.id.isNotBlank())}
 }
 @Synchronized fun write(mark:SessionMark):Boolean{
  val previous=read()
  if(previous!=null&&(previous.deviceBoot>mark.deviceBoot||previous.deviceBoot==mark.deviceBoot&&previous.epoch>mark.epoch))return false
  put(mark);return true
 }
 @Synchronized fun confirmReboot(previousBoot:Int,currentBoot:Int){require(previousBoot>=0&&currentBoot>previousBoot);put(SessionMark("recovered",0,currentBoot,false,true))}
 private fun put(mark:SessionMark){val out=file.startWrite();try{out.write(DataContract.gson.toJson(mark).toByteArray());file.finishWrite(out)}catch(e:Exception){file.failWrite(out);throw e};check(read()==mark){"JOURNAL_READBACK"}}
}
