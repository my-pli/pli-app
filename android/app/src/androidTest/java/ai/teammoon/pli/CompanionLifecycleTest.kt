package ai.teammoon.pli

import android.Manifest
import android.content.Intent
import android.media.AudioManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CompanionLifecycleTest{
 @get:Rule val microphone=GrantPermissionRule.grant(Manifest.permission.RECORD_AUDIO,Manifest.permission.POST_NOTIFICATIONS)
 @Test fun actualCaptureStopsAndEpochCanRestartWithoutUiProcessDeath(){
  val i=InstrumentationRegistry.getInstrumentation();val c=i.targetContext;val app=c.applicationContext as PliApplication;val audio=c.getSystemService(AudioManager::class.java)
  fun waitFor(label:String,p:()->Boolean){val end=System.currentTimeMillis()+25000;while(System.currentTimeMillis()<end){if(p())return;Thread.sleep(80)};fail("$label: status=${app.state.value.sessionStatus}, capture=${app.state.value.capture}, model=${app.state.value.modelReady}, tts=${app.state.value.ttsReady}, error=${app.state.value.error}")}
  val pid=android.os.Process.myPid();val launch=c.packageManager.getLaunchIntentForPackage(c.packageName)!!.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
  c.startActivity(launch);waitFor("visible"){app.state.value.visible}
  if(app.state.value.sessionStatus!="STOPPED"){i.runOnMainSync{app.endSession()};waitFor("prior stop"){app.state.value.sessionStatus=="STOPPED"}}
  i.runOnMainSync{app.preview();app.prepareSession("lifecycle-test-1",false,true)}
  try{
   waitFor("SDK and app-owned capture"){app.state.value.modelReady&&app.state.value.ttsReady&&app.state.value.capture=="ACTIVE"}
   val ids=audio.activeRecordingConfigurations.map{it.clientAudioSessionId}.filter{it>0}.toSet();assertTrue("OS observes a real recording",ids.isNotEmpty())
   val epoch=app.state.value.epoch;i.runOnMainSync{app.endSession()};waitFor("confirmed stop"){app.state.value.sessionStatus=="STOPPED"}
   waitFor("OS recording sessions released"){audio.activeRecordingConfigurations.none{it.clientAudioSessionId in ids}}
   assertTrue(app.state.value.stopReceipt!!.captureStopped);assertTrue(app.state.value.epoch>epoch);assertEquals(pid,android.os.Process.myPid())
   i.runOnMainSync{app.prepareSession("lifecycle-test-2",false,true)};waitFor("next epoch capture"){app.state.value.capture=="ACTIVE"};assertEquals("lifecycle-test-2",app.state.value.sessionId)
  }finally{i.runOnMainSync{app.endSession()};waitFor("final stop"){app.state.value.sessionStatus=="STOPPED"};i.runOnMainSync{app.preview()}}
 }
}
