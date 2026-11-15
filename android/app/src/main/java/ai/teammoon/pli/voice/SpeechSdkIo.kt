package ai.teammoon.pli.voice

import java.util.concurrent.Executors
import java.util.concurrent.Future

/** Blocking policy/STT/TTS operations cannot starve each other's stop queue. */
object SpeechSdkIo {
    private val focusQueue=Executors.newSingleThreadExecutor{r->Thread(r,"PliAudioFocus").apply{isDaemon=true}}
    private val sttQueue=Executors.newSingleThreadExecutor{r->Thread(r,"PliSttIo").apply{isDaemon=true}}
    private val ttsQueue=Executors.newSingleThreadExecutor{r->Thread(r,"PliTtsIo").apply{isDaemon=true}}
    fun focus(work:()->Unit):Future<*> = focusQueue.submit(work)
    fun stt(work:()->Unit):Future<*> = sttQueue.submit(work)
    fun tts(work:()->Unit):Future<*> = ttsQueue.submit(work)
    fun run(work:()->Unit)=stt(work)
}
