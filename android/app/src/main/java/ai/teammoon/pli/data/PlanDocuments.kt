package ai.teammoon.pli.data

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.security.MessageDigest

/** Document bytes and active-kind metadata have one ordered writer; keep the other original. */
object PlanDocuments{
    private val lock=Any()
    fun active(context:Context):String?=synchronized(lock){val f=File(context.filesDir,"plan-active.txt");if(!f.exists()&&!File(f.path+".bak").exists())null else AtomicFile(f).openRead().bufferedReader().use{it.readText()}.also{require(it in setOf("text","image"))}}
    fun select(context:Context,kind:String)=synchronized(lock){require(kind in setOf("text","image"));require(File(context.filesDir,if(kind=="image")"plan-input.jpg"else"plan-input.txt").exists());val f=AtomicFile(File(context.filesDir,"plan-active.txt"));val out=f.startWrite();try{out.write(kind.toByteArray());f.finishWrite(out)}catch(e:Exception){f.failWrite(out);throw e}}
    fun commit(context:Context,image:Boolean,temp:File,expected:String,onCommit:()->Unit={})=synchronized(lock){
        val target=AtomicFile(File(context.filesDir,if(image)"plan-input.jpg"else"plan-input.txt"));val out=target.startWrite()
        try{temp.inputStream().use{it.copyTo(out)};target.finishWrite(out)}catch(e:Exception){target.failWrite(out);throw e}
        val actual=MessageDigest.getInstance("SHA-256");target.openRead().use{input->val buf=ByteArray(8192);var n=input.read(buf);while(n>0){actual.update(buf,0,n);n=input.read(buf)}}
        check(actual.digest().joinToString(""){"%02x".format(it)}==expected){"READBACK_MISMATCH"}
        select(context,if(image)"image"else"text")
        onCommit()
    }
}
