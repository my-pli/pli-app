package ai.teammoon.pli
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.pleos.playground.stt.SpeechToText
import ai.pleos.playground.stt.constant.Mode
import ai.pleos.playground.stt.constant.ErrorType
import ai.pleos.playground.stt.listener.OnInitializeListener
import ai.pleos.playground.stt.listener.ResultListener
import ai.teammoon.pli.domain.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
@RunWith(AndroidJUnit4::class)
class RecognitionLocaleTest{
 @Test fun samePcmCanBeRecognizedInEnglishThenReturnToKorean(){
  visibleSdkTestHost();val i=InstrumentationRegistry.getInstrumentation();val ready=CountDownLatch(1);val failure=AtomicReference<String>();val value=AtomicReference("");val pending=AtomicReference<CountDownLatch>()
  val sdk=SpeechToText(i.targetContext,Mode.ON_DEVICE)
  val listener=object:ResultListener{
   override fun onReady()=Unit
   override fun onStartedRecognition()=Unit
   override fun onUpdated(text:String,completed:Boolean){if(completed){value.set(text);pending.get()?.countDown()}}
   override fun onUpdatedEpdData(on:Long,off:Long)=Unit
   override fun onUpdatedRms(rms:Double)=Unit
   override fun onEndedRecognition()=Unit
   override fun onError(type:ErrorType){failure.set(type.name);pending.get()?.countDown()}
  }
  try{
   sdk.initialize(object:OnInitializeListener{override fun onSuccess(){ready.countDown()};override fun onFailure(type:ErrorType){failure.set(type.name);ready.countDown()}})
   assertTrue(ready.await(15,TimeUnit.SECONDS));assertNull(failure.get());sdk.addListener(listener)
   fun recognize(locale:Locale,file:String):String{val latch=CountDownLatch(1);pending.set(latch);value.set("");failure.set(null);sdk.setLocale(locale);sdk.sendAudio(i.context.assets.open(file).use{it.readBytes()});sdk.completeAudioSend();assertTrue("actual result $locale",latch.await(15,TimeUnit.SECONDS));assertNull(failure.get());Thread.sleep(250);android.util.Log.i("PliLocaleProbe","locale=$locale, transcript=${value.get()}");return value.get()}
   val english=recognize(Locale.US,"bye-native.pcm");assertTrue("actual English goodbye: $english",Questions.correct(LearningCatalog.dialogueQuestion(2),english))
   val korean=recognize(Locale.KOREA,"hush-native.pcm");assertEquals(VoiceCommand.Hush,VoiceInterpreter.parse(korean))
  }finally{sdk.stop();sdk.removeListener(listener);sdk.release()}
 }
}
