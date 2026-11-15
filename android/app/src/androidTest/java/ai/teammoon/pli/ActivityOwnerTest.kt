package ai.teammoon.pli
import android.media.AudioManager
import androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry
import androidx.test.runner.lifecycle.Stage
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
@RunWith(AndroidJUnit4::class)
class ActivityOwnerTest{
 @Test fun reopeningTheLauncherKeepsASingleActivityOwner(){
  val i=InstrumentationRegistry.getInstrumentation();val c=i.targetContext;val app=c.applicationContext as PliApplication;launchCurrent();val epoch=app.state.value.epoch;val session=app.state.value.sessionId
  repeat(3){c.startActivity(c.packageManager.getLaunchIntentForPackage(c.packageName)!!.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));Thread.sleep(150)}
  val deadline=System.currentTimeMillis()+10000;var settled=false
  while(!settled&&System.currentTimeMillis()<deadline){i.runOnMainSync{val m=ActivityLifecycleMonitorRegistry.getInstance();val all=listOf(Stage.CREATED,Stage.STARTED,Stage.RESUMED,Stage.PAUSED,Stage.STOPPED).flatMap{m.getActivitiesInStage(it)}.filterIsInstance<MainActivity>().distinct();settled=all.size==1&&m.getActivitiesInStage(Stage.RESUMED).contains(all.single())&&app.previewView.get()===all.single().window.decorView&&all.single().window.decorView.isAttachedToWindow&&app.state.value.visible};if(!settled)Thread.sleep(80)}
  assertTrue("Launcher transaction must settle to one Activity",settled)
  i.runOnMainSync{assertFalse("The Pleos window must bypass the blocked hardware renderer",app.previewView.get()!!.isHardwareAccelerated)}
  i.runOnMainSync{val monitor=ActivityLifecycleMonitorRegistry.getInstance();val active=listOf(Stage.CREATED,Stage.STARTED,Stage.RESUMED,Stage.PAUSED,Stage.STOPPED).flatMap{monitor.getActivitiesInStage(it)}.filterIsInstance<MainActivity>().distinct();assertEquals(1,active.size);assertEquals(epoch,app.state.value.epoch);assertEquals(session,app.state.value.sessionId);assertSame(active.single().window.decorView,app.previewView.get())}
 }
 private fun launchCurrent():MainActivity{
  val i=InstrumentationRegistry.getInstrumentation();val c=i.targetContext
  c.startActivity(c.packageManager.getLaunchIntentForPackage(c.packageName)!!.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
  val end=System.currentTimeMillis()+15000
  while(System.currentTimeMillis()<end){
   var activity:MainActivity?=null
   i.runOnMainSync{activity=ActivityLifecycleMonitorRegistry.getInstance().getActivitiesInStage(Stage.RESUMED).filterIsInstance<MainActivity>().firstOrNull()}
   activity?.let{return it};Thread.sleep(100)
  };throw AssertionError("Launcher Activity not resumed")
 }

 @Test fun recreationKeepsOneVoiceOwnerAndPublishesTheCurrentView(){
  val i=InstrumentationRegistry.getInstrumentation();val app=i.targetContext.applicationContext as PliApplication;val audio=i.targetContext.getSystemService(AudioManager::class.java)
  fun waitFor(label:String,p:()->Boolean){val end=System.currentTimeMillis()+20000;while(System.currentTimeMillis()<end){if(p())return;Thread.sleep(100)};fail(label)}
  val activity=launchCurrent()
  run{
   waitFor("visible"){app.state.value.visible};i.runOnMainSync{app.prepareSession("recreate-test",false,true)}
   try{
    waitFor("capture"){app.state.value.capture=="ACTIVE"};val epoch=app.state.value.epoch;val ids=audio.activeRecordingConfigurations.map{it.clientAudioSessionId}.toSet()
    val oldView=activity.window.decorView;var replacement:MainActivity?=null
    i.runOnMainSync{activity.recreate()}
    waitFor("replacement Activity owns the attached View"){
     i.runOnMainSync{replacement=ActivityLifecycleMonitorRegistry.getInstance().getActivitiesInStage(Stage.RESUMED).filterIsInstance<MainActivity>().firstOrNull{it!==activity}}
     replacement?.let{current->app.previewView.get()===current.window.decorView&&current.window.decorView.isAttachedToWindow&&app.state.value.visible}==true
    }
    android.util.Log.i("PliOwnerTest","activityReplaced=${replacement!==activity} decorReused=${oldView===replacement!!.window.decorView}")
    assertTrue("Real framework Activity destruction occurred",activity.isDestroyed);assertEquals(epoch,app.state.value.epoch);assertEquals("recreate-test",app.state.value.sessionId);assertEquals(ids,audio.activeRecordingConfigurations.map{it.clientAudioSessionId}.toSet())
    i.runOnMainSync{val current=ActivityLifecycleMonitorRegistry.getInstance().getActivitiesInStage(Stage.RESUMED).filterIsInstance<MainActivity>().single();assertSame(current.window.decorView,app.previewView.get())}
    // A completed recreation must not lend its old grace period to a later close.
    Thread.sleep(1200);i.runOnMainSync{replacement!!.finishAndRemoveTask()};val stopDeadline=System.currentTimeMillis()+5000
    while(app.state.value.sessionStatus!="STOPPED"&&System.currentTimeMillis()<stopDeadline)Thread.sleep(80)
    assertEquals("Private task removal after recreation stops promptly","STOPPED",app.state.value.sessionStatus)
   }finally{i.runOnMainSync{app.endSession()};waitFor("stopped"){app.state.value.sessionStatus=="STOPPED"};i.runOnMainSync{app.preview()}}
  }
 }
 @Test fun publicFramesWaitForThePublicCompositionToReplacePrivatePixels(){
  val i=InstrumentationRegistry.getInstrumentation();val c=i.targetContext;val app=c.applicationContext as PliApplication
  fun waitFor(label:String,p:()->Boolean){val end=System.currentTimeMillis()+10000;while(System.currentTimeMillis()<end){if(p())return;Thread.sleep(60)};fail(label)}
  launchCurrent()
  run{
   i.runOnMainSync{app.leaveDemo()};waitFor("private composition"){app.rendered?.demo==false&&app.rendered?.view?.get()===app.previewView.get()}
   i.runOnMainSync{val view=app.previewView.get()!!;app.preview();assertFalse("Old private composition cannot be exported",app.canCapture(view))}
   waitFor("public composition"){app.previewView.get()?.let{app.canCapture(it)}==true}
   val bytes=c.contentResolver.openInputStream(android.net.Uri.parse("content://ai.teammoon.pli.demo/frame"))!!.use{it.readBytes()};val image=android.graphics.BitmapFactory.decodeByteArray(bytes,0,bytes.size)
   assertEquals(960,image.width);val color=image.getPixel(20,20);assertTrue(android.graphics.Color.red(color)<120);image.recycle()
  }
 }

 @Test fun publicTaskRemovalKeepsOneCaptureUntilTheOwnedWindowReturns(){
  val i=InstrumentationRegistry.getInstrumentation();val app=i.targetContext.applicationContext as PliApplication;val audio=i.targetContext.getSystemService(AudioManager::class.java);val id="public-window-recovery"
  fun heartbeat(){i.runOnMainSync{if(app.state.value.sessionId==id&&app.state.value.sessionStatus in setOf("PREPARING","ACTIVE"))app.serverHeartbeat(id)}}
  fun waitFor(label:String,p:()->Boolean){val end=System.currentTimeMillis()+25000;while(System.currentTimeMillis()<end){heartbeat();if(p())return;Thread.sleep(80)};fail(label)}
  val old=launchCurrent();i.runOnMainSync{app.preview();app.prepareSession(id,true,true)}
  // The production server keeps heartbeats flowing while am start awaits the
  // vendor task organizer. Preserve that cadence during this blocking launch.
  val main=android.os.Handler(android.os.Looper.getMainLooper());var keepingLease=true
  val pulse=object:Runnable{override fun run(){if(!keepingLease)return;if(app.state.value.sessionId==id&&app.state.value.sessionStatus in setOf("PREPARING","ACTIVE"))app.serverHeartbeat(id);main.postDelayed(this,400)}}
  main.post(pulse)
  try{
   waitFor("public capture"){app.state.value.capture=="ACTIVE"};val epoch=app.state.value.epoch;val ids=audio.activeRecordingConfigurations.map{it.clientAudioSessionId}.toSet();assertTrue(ids.isNotEmpty())
   heartbeat();val removed=System.currentTimeMillis();i.runOnMainSync{old.finishAndRemoveTask()};waitFor("actual old Activity destroyed"){old.isDestroyed}
   while(System.currentTimeMillis()-removed<2500){heartbeat();assertEquals("ACTIVE",app.state.value.capture);Thread.sleep(80)}
   val replacement=launchCurrent();waitFor("replacement public composition"){app.state.value.visible&&app.previewView.get()===replacement.window.decorView&&app.canCapture(replacement.window.decorView)}
   while(System.currentTimeMillis()-removed<11500){heartbeat();assertEquals("ACTIVE",app.state.value.capture);Thread.sleep(100)}
   assertEquals(epoch,app.state.value.epoch);assertEquals(ids,audio.activeRecordingConfigurations.map{it.clientAudioSessionId}.toSet())
  }finally{i.runOnMainSync{keepingLease=false;main.removeCallbacks(pulse);app.endSession()};waitFor("confirmed stop"){app.state.value.sessionStatus=="STOPPED"};i.runOnMainSync{app.preview()}}
 }
 @Test fun privateTaskRemovalStillReleasesTheActualRecording(){
  val i=InstrumentationRegistry.getInstrumentation();val app=i.targetContext.applicationContext as PliApplication;val audio=i.targetContext.getSystemService(AudioManager::class.java)
  fun waitFor(label:String,p:()->Boolean){val end=System.currentTimeMillis()+25000;while(System.currentTimeMillis()<end){if(p())return;Thread.sleep(80)};fail(label)}
  val old=launchCurrent();i.runOnMainSync{app.prepareSession("private-task-removal",false,true)}
  try{
   waitFor("private capture"){app.state.value.capture=="ACTIVE"};val ids=audio.activeRecordingConfigurations.map{it.clientAudioSessionId}.toSet();assertTrue(ids.isNotEmpty());i.runOnMainSync{old.finishAndRemoveTask()}
   waitFor("private task removal stop"){app.state.value.sessionStatus=="STOPPED"&&app.state.value.capture=="STOPPED"};assertTrue(audio.activeRecordingConfigurations.none{it.clientAudioSessionId in ids});launchCurrent()
  }finally{if(app.state.value.sessionStatus!="STOPPED"){i.runOnMainSync{app.endSession()};waitFor("confirmed stop"){app.state.value.sessionStatus=="STOPPED"}};i.runOnMainSync{app.preview()}}
 }
}
