package ai.teammoon.pli
import android.media.AudioManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.voice.PliSpeaker
import ai.teammoon.pli.voice.SpeechSdkIo
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
@RunWith(AndroidJUnit4::class)
class AudioFocusThreadTest{
 @org.junit.Before fun visibleHost()=visibleSdkTestHost()
 @Test fun blockedSttQueueFailsClosedWithoutBlockingUiOrOpeningTheMicrophone(){
  val i=InstrumentationRegistry.getInstrumentation();val held=CountDownLatch(1);val release=CountDownLatch(1);val error=CountDownLatch(1);val stopped=CountDownLatch(1);val pulse=CountDownLatch(1);val captured=AtomicInteger();val result=java.util.concurrent.atomic.AtomicReference<Boolean>()
  val scope=kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.SupervisorJob()+kotlinx.coroutines.Dispatchers.Main.immediate)
  val pending=SpeechSdkIo.stt{held.countDown();release.await()};assertTrue(held.await(1,TimeUnit.SECONDS));lateinit var listener:ai.teammoon.pli.voice.PleosSpeechListener
  try{i.runOnMainSync{listener=ai.teammoon.pli.voice.PleosSpeechListener(i.targetContext,scope,{},{},{},{},{error.countDown()},{},onCapture={if(it)captured.incrementAndGet()},edgeFirst=false);listener.start();android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({pulse.countDown()},100)};assertTrue(pulse.await(1,TimeUnit.SECONDS));assertTrue("Blocked SDK initialization must surface failure",error.await(13,TimeUnit.SECONDS));assertEquals(0,captured.get());i.runOnMainSync{listener.stop{ok->result.set(ok);stopped.countDown()}};assertTrue(stopped.await(4,TimeUnit.SECONDS));assertEquals(false,result.get())}finally{release.countDown();pending.get(2,TimeUnit.SECONDS);Thread.sleep(300);scope.coroutineContext[kotlinx.coroutines.Job]?.cancel()}
 }
 @Test fun unreachableEdgeFallsBackToSdkAndStillFailsClosed(){
  val i=InstrumentationRegistry.getInstrumentation();val held=CountDownLatch(1);val release=CountDownLatch(1);val error=CountDownLatch(1);val stopped=CountDownLatch(1);val pulse=CountDownLatch(1);val captured=AtomicInteger();val result=java.util.concurrent.atomic.AtomicReference<Boolean>()
  val scope=kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.SupervisorJob()+kotlinx.coroutines.Dispatchers.Main.immediate)
  val pending=SpeechSdkIo.stt{held.countDown();release.await()};assertTrue(held.await(1,TimeUnit.SECONDS));lateinit var listener:ai.teammoon.pli.voice.PleosSpeechListener
  try{i.runOnMainSync{ai.teammoon.pli.edge.EdgeAi.baseUrl="http://10.0.2.2:9";listener=ai.teammoon.pli.voice.PleosSpeechListener(i.targetContext,scope,{},{},{},{},{error.countDown()},{},onCapture={if(it)captured.incrementAndGet()});listener.start();android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({pulse.countDown()},100)};assertTrue(pulse.await(1,TimeUnit.SECONDS));assertTrue("Blocked SDK initialization must surface failure",error.await(13,TimeUnit.SECONDS));assertEquals(0,captured.get());i.runOnMainSync{listener.stop{ok->result.set(ok);stopped.countDown()}};assertTrue(stopped.await(4,TimeUnit.SECONDS));assertEquals(false,result.get())}finally{ai.teammoon.pli.edge.EdgeAi.baseUrl="http://10.0.2.2:8890";release.countDown();pending.get(2,TimeUnit.SECONDS);Thread.sleep(300);scope.coroutineContext[kotlinx.coroutines.Job]?.cancel()}
 }
 @Test fun deniedPolicyNeverClaimsPlayback(){
  val i=InstrumentationRegistry.getInstrumentation();val ready=CountDownLatch(1);val error=CountDownLatch(1);val closed=CountDownLatch(1);val spoken=AtomicInteger();val state=java.util.concurrent.atomic.AtomicReference("");lateinit var s:PliSpeaker
  i.runOnMainSync{s=PliSpeaker(i.targetContext,{ok,_->if(ok)ready.countDown()},{},{},{error.countDown()},onState={_,focus->state.set(focus)},onSpoken={spoken.incrementAndGet()},requestFocusOverride={AudioManager.AUDIOFOCUS_REQUEST_FAILED})}
  val result=java.util.concurrent.atomic.AtomicReference<Boolean>()
  try{assertTrue(ready.await(15,TimeUnit.SECONDS));i.runOnMainSync{s.speak("포커스 거절 시험")};assertTrue(error.await(3,TimeUnit.SECONDS));assertEquals("DENIED",state.get());assertEquals(0,spoken.get());assertFalse(s.speaking)}finally{i.runOnMainSync{s.close{ok->result.set(ok);closed.countDown()}};assertTrue(closed.await(5,TimeUnit.SECONDS));assertEquals(true,result.get())}
 }
 @Test fun unreturnedPolicyKeepsUiResponsiveAndCloseUnconfirmed(){
  val i=InstrumentationRegistry.getInstrumentation();val ready=CountDownLatch(1);val held=CountDownLatch(1);val release=CountDownLatch(1);val error=CountDownLatch(1);val closed=CountDownLatch(1);val pulse=CountDownLatch(1);val result=java.util.concurrent.atomic.AtomicReference<Boolean>();val spoken=AtomicInteger();lateinit var s:PliSpeaker
  i.runOnMainSync{s=PliSpeaker(i.targetContext,{ok,_->if(ok)ready.countDown()},{},{},{error.countDown()},onSpoken={spoken.incrementAndGet()},requestFocusOverride={held.countDown();release.await();AudioManager.AUDIOFOCUS_REQUEST_GRANTED})}
  try{assertTrue(ready.await(15,TimeUnit.SECONDS));i.runOnMainSync{s.speak("정체된 정책 뒤 재생 금지");android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({pulse.countDown()},100)};assertTrue(held.await(1,TimeUnit.SECONDS));assertTrue(pulse.await(1,TimeUnit.SECONDS));assertTrue(error.await(3,TimeUnit.SECONDS));i.runOnMainSync{s.close{ok->result.set(ok);closed.countDown()}};assertTrue(closed.await(5,TimeUnit.SECONDS));assertEquals(false,result.get());assertEquals(0,spoken.get())}finally{release.countDown();Thread.sleep(300)}
 }
 @Test fun blockedTtsQueueCannotBlockTheMainOrAcknowledgeClose(){
  val i=InstrumentationRegistry.getInstrumentation();val held=CountDownLatch(1);val release=CountDownLatch(1);val closed=CountDownLatch(1);val pulse=CountDownLatch(1);val ready=AtomicInteger();val result=java.util.concurrent.atomic.AtomicReference<Boolean>();lateinit var s:PliSpeaker
  val pending=SpeechSdkIo.tts{held.countDown();release.await()};assertTrue(held.await(1,TimeUnit.SECONDS))
  try{i.runOnMainSync{s=PliSpeaker(i.targetContext,{ok,_->if(ok)ready.incrementAndGet()},{},{},{});s.close{ok->result.set(ok);closed.countDown()};android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({pulse.countDown()},100)};assertTrue(pulse.await(1,TimeUnit.SECONDS));assertTrue(closed.await(5,TimeUnit.SECONDS));assertEquals(false,result.get())}finally{release.countDown();pending.get(2,TimeUnit.SECONDS);Thread.sleep(500)}
  assertEquals(0,ready.get())
 }
 @Test fun delayedPolicyDoesNotBlockMainAndLateGrantCannotSpeak(){
  val i=InstrumentationRegistry.getInstrumentation();val ready=CountDownLatch(1);val error=CountDownLatch(1);val callback=CountDownLatch(1);val closed=CountDownLatch(1);val spoken=AtomicInteger();val focusThread=java.util.concurrent.atomic.AtomicReference("");lateinit var s:PliSpeaker
  i.runOnMainSync{s=PliSpeaker(i.targetContext,{ok,_->if(ok)ready.countDown()},{},{},{error.countDown()},onSpoken={spoken.incrementAndGet()},requestFocusOverride={focusThread.set(Thread.currentThread().name);Thread.sleep(2400);AudioManager.AUDIOFOCUS_REQUEST_GRANTED})}
  try{assertTrue(ready.await(15,TimeUnit.SECONDS));i.runOnMainSync{s.speak("이 음성은 늦은 승인 뒤 재생되면 안 됩니다.");android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({callback.countDown()},100)};assertTrue("main still responds",callback.await(1,TimeUnit.SECONDS));assertTrue("policy timeout surfaced",error.await(3,TimeUnit.SECONDS));i.runOnMainSync{s.setQuiet(true)};Thread.sleep(650);assertEquals(0,spoken.get());assertFalse(s.speaking);assertTrue(focusThread.get().startsWith("PliAudioFocus"))}finally{i.runOnMainSync{s.close{closed.countDown()}};assertTrue(closed.await(5,TimeUnit.SECONDS))}
 }
 @Test fun lostCompletionCallbackFailsClosedInsteadOfClaimingIdle(){
  val i=InstrumentationRegistry.getInstrumentation();val ready=CountDownLatch(1);val started=CountDownLatch(1);val error=CountDownLatch(1);val closed=CountDownLatch(1);val state=java.util.concurrent.atomic.AtomicReference("");lateinit var s:PliSpeaker
  i.runOnMainSync{s=PliSpeaker(i.targetContext,{ok,_->if(ok)ready.countDown()},{if(it)started.countDown()},{},{error.countDown()},onState={p,_->state.set(p)},completionLimitOverrideMs=2000,acceptCompletion={false})}
  try{assertTrue(ready.await(15,TimeUnit.SECONDS));i.runOnMainSync{s.speak("플리")};assertTrue("Actual SDK playback starts",started.await(6,TimeUnit.SECONDS));assertTrue("Missing done must have a bounded error",error.await(5,TimeUnit.SECONDS));assertEquals("ERROR",state.get());assertFalse(s.speaking)}finally{i.runOnMainSync{s.close{closed.countDown()}};assertTrue(closed.await(5,TimeUnit.SECONDS))}
 }
 @Test fun actualQuietStopPublishesIdleAfterTheSdkStops(){
  val i=InstrumentationRegistry.getInstrumentation();val ready=CountDownLatch(1);val started=CountDownLatch(1);val idle=CountDownLatch(1);val closed=CountDownLatch(1);lateinit var s:PliSpeaker
  i.runOnMainSync{s=PliSpeaker(i.targetContext,{ok,_->if(ok)ready.countDown()},{if(it)started.countDown()},{},{},onState={p,_->if(p=="IDLE")idle.countDown()})}
  try{assertTrue(ready.await(15,TimeUnit.SECONDS));i.runOnMainSync{s.speak("이 문장을 실제로 읽는 도중에 조용히 멈추는 상태를 확인합니다.")};assertTrue(started.await(6,TimeUnit.SECONDS));i.runOnMainSync{s.setQuiet(true)};assertTrue("Confirmed SDK stop must update playback",idle.await(5,TimeUnit.SECONDS));assertFalse(s.speaking)}finally{i.runOnMainSync{s.close{closed.countDown()}};assertTrue(closed.await(5,TimeUnit.SECONDS))}
 }
}
