package ai.teammoon.pli

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Build
import android.graphics.Rect
import android.view.View
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ai.teammoon.pli.domain.VoicePhase
import ai.teammoon.pli.ui.PliScreen
import ai.teammoon.pli.voice.CompanionService


class MainActivity:ComponentActivity(){
    companion object{internal var windowOwner=java.lang.ref.WeakReference<MainActivity>(null)}
    internal val windowIdentity=java.util.UUID.randomUUID().toString()
    private val app get()=application as PliApplication
    private var startAfterPermission=false
    private val permissions=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){
        app.reconnectVehicle()
        if(ContextCompat.checkSelfPermission(this,Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED){startCompanion();if(startAfterPermission&&app.state.value.visible&&app.state.value.sessionStatus=="STOPPED"&&!app.demoActive){startAfterPermission=false;app.prepareSession(java.util.UUID.randomUUID().toString(),false)}}
        else {startAfterPermission=false;app.reduce{it.copy(phase=VoicePhase.PERMISSION,status="마이크 권한이 필요해요",error="마이크 사용을 허용한 뒤 다시 시작해 주세요.")}}
    }
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState)
        window.setFormat(android.graphics.PixelFormat.TRANSLUCENT) // the GPU night scene is a SurfaceView behind this software-rendered window
        onBackPressedDispatcher.addCallback(this,object:OnBackPressedCallback(true){override fun handleOnBackPressed(){moveTaskToBack(true)}})
        configurePresentation(intent)
        setContent{
            val observed=app.state.collectAsStateWithLifecycle();val s=observed.value
            Column(Modifier.fillMaxSize()){
                Box(Modifier.weight(1f).fillMaxWidth()){PliScreen(s,s.presentation)}
                androidx.compose.runtime.SideEffect{app.markRendered(window.decorView,s)}
                if(!s.demo&&s.sessionStatus=="STOPPED") Surface(color=ai.teammoon.pli.ui.Stage.SkyTop){
                    Button(enabled=app.store.recoveryError==null,modifier=Modifier.fillMaxWidth().padding(horizontal=28.dp,vertical=12.dp).heightIn(min=56.dp),colors=ButtonDefaults.buttonColors(containerColor=ai.teammoon.pli.ui.Stage.Gold,contentColor=ai.teammoon.pli.ui.Stage.Ink),onClick={
                        if(ContextCompat.checkSelfPermission(this@MainActivity,Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)app.prepareSession(java.util.UUID.randomUUID().toString(),false)
                        else{startAfterPermission=true;permissions.launch(arrayOf(Manifest.permission.RECORD_AUDIO))}
                    }){Text(if(app.store.recoveryError==null)"목소리로 시작하기"else"자료 복구가 필요해요",fontSize=18.sp)}
                }
            }
        }
        app.previewView=java.lang.ref.WeakReference(window.decorView)
        window.decorView.viewTreeObserver.addOnGlobalLayoutListener{updateBounds()}
        val needed=arrayOf(Manifest.permission.RECORD_AUDIO,"android.car.permission.CAR_SPEED","android.car.permission.CAR_POWERTRAIN","pleos.car.permission.FUSED_LOCATION","pleos.car.permission.NAVI_ROUTE_SEARCH").filter{ContextCompat.checkSelfPermission(this,it)!=PackageManager.PERMISSION_GRANTED}
        if(needed.isEmpty())startCompanion()else permissions.launch(needed.toTypedArray())
    }
    private fun configurePresentation(value:Intent){
        val enabled=app.state.value.presentation
        window.decorView.setLayerType(if(enabled)View.LAYER_TYPE_SOFTWARE else View.LAYER_TYPE_NONE,null)
    }
    private fun updateBounds(){app.viewBounds=if(Build.VERSION.SDK_INT>=30)Rect(windowManager.currentWindowMetrics.bounds)else Rect().also{window.decorView.getGlobalVisibleRect(it)}}
    override fun onWindowFocusChanged(hasFocus:Boolean){super.onWindowFocusChanged(hasFocus);updateBounds();app.setView(hasFocus,app.viewBounds)}
    private fun startCompanion(){
        // Launcher extras do not grant control or microphone access.
        configurePresentation(intent)
    }
    override fun onStop(){if(app.previewView.get()===window.decorView)app.setVisible(false);super.onStop()}
    override fun recreate(){
        val epoch=app.state.value.epoch;val session=app.state.value.sessionId
        app.prepareWindowRecreation()
        super.recreate()
        // Pleos 2.1's embedded task organizer can discard the recreated window.
        // Reopen only this explicitly requested recreation, retaining the actual
        // Application/voice owner. Ordinary Back/background transitions do not do this.
        app.recoverRecreatedWindow(epoch,session)
    }
    override fun onNewIntent(intent:Intent){super.onNewIntent(intent);setIntent(intent);configurePresentation(intent);if(ContextCompat.checkSelfPermission(this,Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)startCompanion()}
    override fun onResume(){super.onResume();windowOwner=java.lang.ref.WeakReference(this);app.previewView=java.lang.ref.WeakReference(window.decorView);app.setVisible(true);app.connectVehicle();if(ContextCompat.checkSelfPermission(this,Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)startCompanion()}
    override fun onDestroy(){if(windowOwner.get()===this)windowOwner.clear();super.onDestroy()}
}
