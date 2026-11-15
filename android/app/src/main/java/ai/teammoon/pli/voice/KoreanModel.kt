package ai.teammoon.pli.voice

import android.content.Context
import java.io.File

internal object KoreanModel {
    @Synchronized fun unpack(context:Context):File {
        val target=File(context.filesDir,"model-ko-v1")
        if(File(target,".ready").exists())return target
        val temp=File(context.filesDir,"model-ko-copy");temp.deleteRecursively();temp.mkdirs()
        fun copy(path:String,dest:File){
            val children=context.assets.list(path).orEmpty()
            if(children.isEmpty()){dest.parentFile?.mkdirs();context.assets.open(path).use{input->dest.outputStream().use{input.copyTo(it,65536)}}}
            else{dest.mkdirs();children.forEach{copy("$path/$it",File(dest,it))}}
        }
        copy("model-ko",temp);File(temp,".ready").writeText("vosk-model-small-ko-0.22")
        target.deleteRecursively();check(temp.renameTo(target)){"음성 모델 설치를 마치지 못했어요"};return target
    }
}
