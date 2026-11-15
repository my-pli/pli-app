package ai.teammoon.pli.data

import android.content.Context
import android.net.Uri
import android.graphics.BitmapFactory
import ai.teammoon.pli.domain.Plan
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.io.File
import java.time.LocalDate
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class PlanImporter(private val context:Context){
    suspend fun read():List<Plan> = withContext(Dispatchers.IO){
        val root=context.getExternalFilesDir(null)?:error("저장 공간이 없어요")
        val image=File(context.filesDir,"plan-input.jpg").takeIf{it.exists()}?:File(root,"plan-input.jpg")
        val textFile=File(context.filesDir,"plan-input.txt").takeIf{it.exists()}?:File(root,"plan-input.txt")
        val active=PlanDocuments.active(context)
        if(active=="text"||active==null&&textFile.exists()){require(textFile.exists()&&textFile.length()<=65536);return@withContext parse(textFile.readText())}
        require(image.exists()&&image.length()<=8*1024*1024){"계획안 사진이 필요해요"}
        val bounds=BitmapFactory.Options().apply{inJustDecodeBounds=true};BitmapFactory.decodeFile(image.path,bounds);require(bounds.outWidth>0&&bounds.outHeight>0)
        var sample=1;while(bounds.outWidth/sample>2048||bounds.outHeight/sample>2048)sample*=2
        val bitmap=BitmapFactory.decodeFile(image.path,BitmapFactory.Options().apply{inSampleSize=sample})?:error("사진을 읽지 못했어요")
        val recognizer=try{TextRecognition.getClient(KoreanTextRecognizerOptions.Builder().build())}catch(e:Exception){bitmap.recycle();throw e}
        try{
            val text=suspendCancellableCoroutine<String>{continuation->
                recognizer.process(InputImage.fromBitmap(bitmap,0)).addOnCompleteListener{task->try{if(continuation.isActive){if(task.isSuccessful)continuation.resume(task.result.text)else continuation.resumeWithException(task.exception?:IllegalStateException("OCR_FAILED"))}}finally{bitmap.recycle();recognizer.close()}}
            }
            parse(text)
        }catch(e:kotlinx.coroutines.CancellationException){throw e}catch(e:Exception){if(!bitmap.isRecycled){bitmap.recycle();recognizer.close()};throw e}
    }
    companion object{
        fun parse(text:String,today:LocalDate=LocalDate.now()):List<Plan> = text.lineSequence().mapNotNull{line->
            val m=Regex("(?:(\\d{4})[-./년\\s]+)?(\\d{1,2})[-./월\\s]+(\\d{1,2})(?:일)?[\\s,;:|]*(.+)").find(line)?:return@mapNotNull null
            val year=m.groupValues[1].toIntOrNull()?:today.year
            val date=runCatching{LocalDate.of(year,m.groupValues[2].toInt(),m.groupValues[3].toInt())}.getOrNull()?:return@mapNotNull null
            val content=m.groupValues[4].split(Regex("[,;|]"));val title=content.first().trim()
            if(title.isEmpty())null else Plan(date=date.toString(),title=title,preparation=content.getOrElse(1){""}.trim()).also(DataContract::plan)
        }.toList().also{require(it.size<=500){"일정 용량을 초과했어요"}}
    }
}
