package ai.teammoon.pli
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.voice.ConversationController
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
/** Controller injection tests storage isolation. Real microphone ASR is tested separately in the portal. */
@RunWith(AndroidJUnit4::class)
class PublicPrivacyTest{
 @Test fun publicStorageRequestsLeavePrivateBackupAndProfileUntouched(){
  val i=InstrumentationRegistry.getInstrumentation();val c=i.targetContext;val app=c.applicationContext as PliApplication
  val backup=File(c.getExternalFilesDir(null),"pli-backup.json");val old=backup.takeIf{it.exists()}?.readBytes();val summary=app.privateSummary()
  fun waitFor(label:String,p:()->Boolean){val end=System.currentTimeMillis()+20000;while(System.currentTimeMillis()<end){i.runOnMainSync{if(app.state.value.sessionId=="privacy-test"&&app.state.value.sessionStatus in setOf("PREPARING","ACTIVE"))app.serverHeartbeat("privacy-test")};if(p())return;Thread.sleep(100)};fail(label)}
  if(!app.state.value.visible||app.previewView.get()?.isAttachedToWindow!=true)
   c.startActivity(c.packageManager.getLaunchIntentForPackage(c.packageName)!!.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
  waitFor("visible"){app.state.value.visible&&app.previewView.get()?.isAttachedToWindow==true}
  i.runOnMainSync{app.preview();app.prepareSession("privacy-test",true,true)}
  try{
   waitFor("ready"){app.state.value.modelReady&&app.state.value.ttsReady};i.runOnMainSync{app.beginSession("privacy-test")}
   val field=PliApplication::class.java.getDeclaredField("controller").apply{isAccessible=true}
   i.runOnMainSync{(field.get(app)as ConversationController).receive("파일로 저장해 주세요",fromTest=true)}
   assertEquals("체험 기록은 저장하지 않아요.",app.state.value.title)
   i.runOnMainSync{(field.get(app)as ConversationController).receive("계획안 읽어줘",fromTest=true)}
   assertEquals("샘플 일정으로 체험해요.",app.state.value.title)
   if(old==null)assertFalse(backup.exists())else assertArrayEquals(old,backup.readBytes())
   assertEquals(summary,app.privateSummary())
  }finally{i.runOnMainSync{app.endSession()};waitFor("stop"){app.state.value.sessionStatus=="STOPPED"};if(old==null)backup.delete()else backup.writeBytes(old);i.runOnMainSync{app.preview()}}
 }
}
