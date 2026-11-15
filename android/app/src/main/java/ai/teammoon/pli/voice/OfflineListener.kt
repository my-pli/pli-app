package ai.teammoon.pli.voice

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.NoiseSuppressor
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import java.io.File
import kotlin.math.sqrt

/** Embedded Korean recognizer. PCM stays in memory; there is no network or raw audio recording. */
class OfflineListener(private val context:Context,private val scope:CoroutineScope,private val onReady:()->Unit,private val onFinal:(String)->Unit,private val onPartial:(String)->Unit,private val onLevel:(Float)->Unit,private val onError:(String)->Unit){
    private var model:Model?=null
    private var audio:AudioRecord?=null
    private var job:Job?=null
    @Volatile private var active=false
    fun start(){
        if(active)return
        active=true
        job=scope.launch(Dispatchers.IO){
            var rec:Recognizer?=null;var echo:AcousticEchoCanceler?=null;var noise:NoiseSuppressor?=null
            try{
                if(ContextCompat.checkSelfPermission(context,Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)throw IllegalStateException("마이크 권한이 필요해요")
                val folder=KoreanModel.unpack(context)
                val loaded=Model(folder.absolutePath);model=loaded
                rec=Recognizer(loaded,16000f)
                val size=maxOf(AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT)*2,8192)
                val recorder=AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size);audio=recorder
                check(recorder.state==AudioRecord.STATE_INITIALIZED){"마이크를 초기화할 수 없어요"}
                if(AcousticEchoCanceler.isAvailable())echo=AcousticEchoCanceler.create(recorder.audioSessionId)?.apply{enabled=true}
                if(NoiseSuppressor.isAvailable())noise=NoiseSuppressor.create(recorder.audioSessionId)?.apply{enabled=true}
                recorder.startRecording();withContext(Dispatchers.Main){onReady()}
                val samples=ShortArray(1600);var partial="";var lastLevel=0L
                while(isActive&&active){
                    val count=recorder.read(samples,0,samples.size)
                    if(count<=0){if(active)delay(50);continue}
                    val now=System.currentTimeMillis()
                    if(now-lastLevel>=100){lastLevel=now;var sum=0.0;for(i in 0 until count)sum+=samples[i].toDouble()*samples[i];val level=(sqrt(sum/count)/4500.0).toFloat().coerceIn(0f,1f);withContext(Dispatchers.Main){onLevel(level)}}
                    if(rec.acceptWaveForm(samples,count)){
                        val text=JSONObject(rec.result).optString("text").trim();partial=""
                        if(text.isNotBlank())withContext(Dispatchers.Main){onFinal(text)}
                    }else{
                        val text=JSONObject(rec.partialResult).optString("partial").trim()
                        if(text!=partial){partial=text;withContext(Dispatchers.Main){onPartial(text)}}
                    }
                }
            }catch(e:CancellationException){throw e}catch(e:Exception){if(active)withContext(Dispatchers.Main){onError(e.message?:"음성 인식을 시작하지 못했어요")}}
            finally{active=false;runCatching{audio?.stop()};audio?.release();audio=null;echo?.release();noise?.release();rec?.close();model?.close();model=null}
        }
    }
    suspend fun recognizeFile(file:File):String=withContext(Dispatchers.IO){
        val loaded=model?:error("음성 모델 준비 전입니다")
        Recognizer(loaded,16000f).use{rec->
            val texts=mutableListOf<String>()
            val pcm=PcmWav.read(file)
            var offset=0
            while(offset<pcm.size){val end=minOf(offset+4096,pcm.size);val bytes=pcm.copyOfRange(offset,end);if(rec.acceptWaveForm(bytes,bytes.size)){val value=JSONObject(rec.result).optString("text");if(value.isNotBlank())texts+=value};offset=end}
            val final=JSONObject(rec.finalResult).optString("text");if(final.isNotBlank())texts+=final;texts.joinToString(" ")
        }
    }
    suspend fun awaitStopped(){withTimeout(2000){job?.join()}}
    fun stop(){active=false;runCatching{audio?.stop()};job?.cancel()}
}
