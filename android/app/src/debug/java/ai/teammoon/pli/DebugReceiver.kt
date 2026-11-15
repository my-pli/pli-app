package ai.teammoon.pli
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
/** Debug-only control; never installed with the release APK. */
class DebugReceiver:BroadcastReceiver(){override fun onReceive(context:Context,intent:Intent){
 val app=context.applicationContext as PliApplication
 val ok=app.debugCommand(intent.getStringExtra("text"),intent.getStringExtra("event"))
 resultCode=if(ok)0 else 1;resultData=if(ok)"Debug command accepted"else"Start an active voice session first"
}}
