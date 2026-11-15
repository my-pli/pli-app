package ai.teammoon.pli.data

import android.content.Context
import android.util.AtomicFile
import ai.teammoon.pli.domain.FamilyFact
import java.io.File
import java.security.MessageDigest

/** Full source text is private, immutable, bounded and keyed by scope plus content. */
object FamilyDocuments{
    private fun folder(context:Context)=File(context.filesDir,"family-documents").also{it.mkdirs()}
    private fun id(scope:String,text:String)=MessageDigest.getInstance("SHA-256").digest((scope+"\u0000"+text).toByteArray(Charsets.UTF_8)).joinToString(""){"%02x".format(it)}
    @Synchronized fun persist(context:Context,fact:FamilyFact):FamilyFact{
        val full=fact.fullText?:return fact
        val bytes=full.toByteArray(Charsets.UTF_8);require(bytes.size<=128*1024){"DOCUMENT_CAPACITY"}
        val key=id(fact.sourceScope,full);val target=AtomicFile(File(folder(context),key+".txt"))
        if(!target.baseFile.exists()){
            val stream=target.startWrite()
            try{stream.write(bytes);target.finishWrite(stream)}catch(e:Exception){target.failWrite(stream);throw e}
        }
        val read=target.openRead().use{it.readBytes()};check(read.contentEquals(bytes)){"DOCUMENT_READBACK"}
        return fact.copy(fullText=null,documentId=key)
    }
    fun read(context:Context,fact:FamilyFact):String{
        fact.fullText?.let{return it}
        val key=fact.documentId?:return fact.text
        require(key.matches(Regex("[a-f0-9]{64}"))){"INVALID_DOCUMENT"}
        val file=File(folder(context),key+".txt");require(file.length()<=128*1024){"DOCUMENT_CAPACITY"}
        val value=file.readText();check(id(fact.sourceScope,value)==key){"DOCUMENT_HASH"};return value
    }
    @Synchronized fun prune(context:Context,retained:Set<String>){
        val files=folder(context).listFiles().orEmpty().filter{it.isFile&&it.name.matches(Regex("[a-f0-9]{64}\\.txt"))}
        val spare=files.filter{it.nameWithoutExtension !in retained}.sortedByDescending{it.lastModified()}
        spare.drop(10).forEach{it.delete()}
    }
}
