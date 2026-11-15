package ai.teammoon.pli

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.voice.PliSpeaker
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Tests real Android audio focus and the real Pleos speech service, not debug events. */
fun visibleSdkTestHost(){
 val i=InstrumentationRegistry.getInstrumentation();val app=i.targetContext.applicationContext as PliApplication
 if(!app.state.value.visible||app.previewView.get()?.isAttachedToWindow!=true)
  i.targetContext.startActivity(i.targetContext.packageManager.getLaunchIntentForPackage(i.targetContext.packageName)!!.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
 val until=System.currentTimeMillis()+5000
 while(!app.state.value.visible&&System.currentTimeMillis()<until)Thread.sleep(50)
 assertTrue("SDK owner tests require the actual visible Pli activity",app.state.value.visible)
}
@RunWith(AndroidJUnit4::class)
class AudioFocusTest {
    @org.junit.Before fun visibleHost()=visibleSdkTestHost()
    private val instrumentation=InstrumentationRegistry.getInstrumentation()
    private val context=instrumentation.targetContext
    private fun main(block:()->Unit)=instrumentation.runOnMainSync(block)
    private fun waitFor(label:String,condition:()->Boolean){
        val end=System.currentTimeMillis()+12000
        while(System.currentTimeMillis()<end){if(condition())return;Thread.sleep(80)}
        fail(label)
    }
    private fun withSpeaker(test:(PliSpeaker,AudioManager,AudioFocusRequest)->Unit){
        val initialized=CountDownLatch(1)
        lateinit var speaker:PliSpeaker
        val audio=context.getSystemService(AudioManager::class.java)
        val navigation=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setOnAudioFocusChangeListener{}.build()
        main{speaker=PliSpeaker(context,{ready,_->if(ready)initialized.countDown()},{},{},{})}
        try{
            assertTrue("Native Pleos TTS initialization",initialized.await(12,TimeUnit.SECONDS))
            main{speaker.speak("오늘도 우리 함께 가는 길이 즐거워. 창밖에는 어떤 이야기가 숨어 있을까? 나무와 구름을 마음속에 그려 보자. 플리가 너의 이야기를 천천히 기다릴게.")}
            waitFor("Pleos native speech starts"){speaker.speaking}
            Thread.sleep(650)
            test(speaker,audio,navigation)
        }finally{audio.abandonAudioFocusRequest(navigation);val done=CountDownLatch(1);var ok=false;main{speaker.close{ok=it;done.countDown()}};assertTrue(done.await(5,TimeUnit.SECONDS));assertTrue("Actual TTS release confirmed",ok)}
    }
    @Test fun navigationActuallyPausesAndResumesSpeech()=withSpeaker{speaker,audio,navigation->
        assertEquals(AudioManager.AUDIOFOCUS_REQUEST_GRANTED,audio.requestAudioFocus(navigation))
        waitFor("Navigation focus pauses assistant"){speaker.navigation&&!speaker.speaking}
        // Keep navigation focus beyond the bounded native stop ACK. The queued
        // utterance must survive this order, then resume on the real focus gain.
        Thread.sleep(1500)
        audio.abandonAudioFocusRequest(navigation)
        waitFor("Assistant resumes after navigation"){!speaker.navigation&&speaker.speaking}
    }
    @Test fun hushDuringNavigationStaysQuietAfterFocusReturns()=withSpeaker{speaker,audio,navigation->
        audio.requestAudioFocus(navigation)
        waitFor("Navigation owns focus"){speaker.navigation}
        main{speaker.setQuiet(true)};audio.abandonAudioFocusRequest(navigation)
        waitFor("Navigation state clears even when quiet"){!speaker.navigation}
        Thread.sleep(700)
        assertTrue(speaker.quiet);assertFalse(speaker.speaking)
        main{speaker.setQuiet(false);speaker.speak("다시 만나서 반가워!")}
        waitFor("Explicit resume can speak again"){speaker.speaking}
    }
    @Test fun completedSpeechCanCloseWithoutAnExtraStopCallback(){
        val ready=CountDownLatch(1);val spoken=CountDownLatch(1);val closed=CountDownLatch(1);var ok=false;lateinit var speaker:PliSpeaker
        main{speaker=PliSpeaker(context,{r,_->if(r)ready.countDown()},{},{},{},onSpoken={spoken.countDown()})}
        assertTrue(ready.await(15,TimeUnit.SECONDS));main{speaker.speak("완료.")};assertTrue(spoken.await(8,TimeUnit.SECONDS));waitFor("Speech completed"){!speaker.speaking}
        main{speaker.close{ok=it;closed.countDown()}};assertTrue(closed.await(5,TimeUnit.SECONDS));assertTrue("An idle SDK needs no extra playback-stop callback",ok)
    }

}
