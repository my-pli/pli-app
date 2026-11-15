package ai.teammoon.pli.data

import android.content.Context
import android.util.AtomicFile
import ai.teammoon.pli.domain.*
import java.io.File

class PliStore(private val context:Context,base:File=File(context.filesDir,"pli-data.json"),private val fault:((String)->Unit)?=null){
    companion object{fun freshData()=SavedData(profile=ChildProfile(name="친구",school=""),plans=emptyList())}
    private val file=AtomicFile(base)
    @Volatile var recoveryError:String?=null;private set
    @Synchronized fun load():SavedData{
        if(!file.baseFile.exists()&&!File(file.baseFile.path+".bak").exists())return freshData()
        return try{DataContract.decode(file.openRead().use{input->require(input.channel.size()<=8*1024*1024){"STORE_CAPACITY"};input.bufferedReader().readText()}).also{recoveryError=null}}
        catch(e:Exception){recoveryError="RECOVERY_REQUIRED";throw IllegalStateException("RECOVERY_REQUIRED",e)}
    }
    @Synchronized fun save(data:SavedData):SavedData{
        check(recoveryError==null){"RECOVERY_REQUIRED"};val canonical=data.copy(facts=data.facts.map{FamilyDocuments.persist(context,it)});DataContract.validate(canonical)
        val stream=file.startWrite()
        try{stream.write(DataContract.gson.toJson(canonical).toByteArray());fault?.invoke("BEFORE_FINISH");file.finishWrite(stream)}catch(e:Exception){file.failWrite(stream);throw e}
        try{fault?.invoke("BEFORE_READBACK");val read=load();check(read==canonical){"READBACK_MISMATCH"};if(file.baseFile==File(context.filesDir,"pli-data.json"))FamilyDocuments.prune(context,read.facts.mapNotNull{it.documentId}.toSet());return read}
        catch(e:Exception){recoveryError="COMMIT_UNKNOWN";throw IllegalStateException("COMMIT_UNKNOWN",e)}
    }
    @Synchronized fun backup(data:SavedData):File{
        DataContract.validate(data);check(recoveryError==null){"RECOVERY_REQUIRED"}
        val target=File(context.getExternalFilesDir(null),"pli-backup.json");val out=AtomicFile(target);val stream=out.startWrite()
        try{val complete=data.copy(facts=data.facts.map{it.copy(fullText=FamilyDocuments.read(context,it))});val bytes=DataContract.gson.toJson(complete).toByteArray();require(bytes.size<=32*1024*1024){"BACKUP_CAPACITY"};stream.write(bytes);out.finishWrite(stream)}catch(e:Exception){out.failWrite(stream);throw e};return target
    }
    fun debugSnapshot(state:ConversationState){
        val target=AtomicFile(File(context.filesDir,"debug-state.json"));val stream=target.startWrite()
        try{stream.write(DataContract.gson.toJson(mapOf("phase" to state.phase,"game" to state.game,"revision" to state.stateRevision,"sessionStatus" to state.sessionStatus)).toByteArray());target.finishWrite(stream)}catch(e:Exception){target.failWrite(stream);throw e}
    }
}
