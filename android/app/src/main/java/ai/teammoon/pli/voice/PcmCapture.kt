package ai.teammoon.pli.voice

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock
import kotlinx.coroutines.*
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.math.sqrt

/** App-owned microphone; bounded 100ms chunks and one utterance in flight. No audio files. */
class PcmCapture(private val scope:CoroutineScope,private val onStart:()->Unit,private val onLevel:(Float)->Unit,private val onChunk:(ByteArray)->Unit,private val onComplete:()->Unit,private val onError:()->Unit,private val onState:(String)->Unit={}){
    @Volatile private var active=false
    val gate=UtteranceGate()
    @Volatile private var recorder:AudioRecord?=null
    private val released=CountDownLatch(1)
    fun resultReceived(){gate.result()}
    fun recognitionEnded(){gate.end()}
    fun start(){active=true;scope.launch(Dispatchers.IO){
        try{
            val min=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT)
            val audio=AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,maxOf(min*2,12800));recorder=audio
            check(audio.state==AudioRecord.STATE_INITIALIZED);audio.startRecording();withContext(Dispatchers.Main){onStart();onState("READY")}
            val bytes=ByteArray(3200);val pre=ArrayDeque<ByteArray>();var speaking=false;var quietFrames=0;var chunks=0;var sentAt=0L;var reported="READY"
            while(isActive&&active){
                val n=audio.read(bytes,0,bytes.size,AudioRecord.READ_BLOCKING);if(n<=0){if(active)error("CAPTURE_FAILED");break}
                var sum=0.0;for(i in 0 until n-1 step 2){val x=((bytes[i].toInt()and 255)or(bytes[i+1].toInt()shl 8)).toShort().toInt();sum+=x.toDouble()*x}
                val rms=sqrt(sum/(n/2));withContext(Dispatchers.Main){if(active)onLevel((rms/4500).toFloat().coerceIn(0f,1f))}
                if(gate.state!=reported){reported=gate.state;withContext(Dispatchers.Main){onState(reported)}}
                if(gate.state=="DRAINING"){if(gate.complete()){sentAt=SystemClock.elapsedRealtime();onComplete()};speaking=false;quietFrames=0;pre.clear();gate.silence(rms<140);if(SystemClock.elapsedRealtime()-sentAt>12000)error("RECOGNITION_END_TIMEOUT");continue}
                if(gate.state=="WAITING"){if(SystemClock.elapsedRealtime()-sentAt>8000)error("RECOGNITION_TIMEOUT");continue}
                val chunk=bytes.copyOf(n)
                if(!speaking){pre.addLast(chunk);while(pre.size>3)pre.removeFirst();if(rms<180)continue;if(!gate.begin())continue;sentAt=SystemClock.elapsedRealtime();speaking=true;chunks=0;quietFrames=0;while(pre.isNotEmpty()){onChunk(pre.removeFirst());chunks++}}
                else{onChunk(chunk);chunks++}
                quietFrames=if(rms<140)quietFrames+1 else 0
                if((quietFrames>=7||chunks>=120)&&gate.complete()){sentAt=SystemClock.elapsedRealtime();onComplete();speaking=false;quietFrames=0;pre.clear()}
            }
        }catch(e:CancellationException){throw e}catch(e:Exception){if(active)withContext(Dispatchers.Main){onError()}}
        finally{active=false;runCatching{recorder?.stop()};runCatching{recorder?.release()};recorder=null;released.countDown()}
    }}
    fun stop():Boolean{active=false;runCatching{recorder?.stop()};return released.await(1500,TimeUnit.MILLISECONDS)}
}
