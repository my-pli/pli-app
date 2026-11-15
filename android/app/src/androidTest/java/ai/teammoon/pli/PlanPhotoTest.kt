package ai.teammoon.pli

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import androidx.core.content.res.ResourcesCompat
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ai.teammoon.pli.data.PlanImporter
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** The bundled Korean OCR must read an actual image, not a substituted text result. */
@RunWith(AndroidJUnit4::class)
class PlanPhotoTest {
    @Test fun koreanPhotoProducesValidatedDatedPlans()=runBlocking{
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val image=File(context.filesDir,"plan-input.jpg")
        val text=File(context.filesDir,"plan-input.txt")
        val priorImage=image.takeIf{it.exists()}?.readBytes()
        val priorText=text.takeIf{it.exists()}?.readBytes()
        val active=File(context.filesDir,"plan-active.txt");val priorActive=active.takeIf{it.exists()}?.readBytes()
        try{
            text.delete()
            active.delete()
            val bitmap=Bitmap.createBitmap(1200,420,Bitmap.Config.ARGB_8888)
            val canvas=Canvas(bitmap);canvas.drawColor(Color.WHITE)
            val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{color=Color.BLACK;textSize=42f;typeface=ResourcesCompat.getFont(context,R.font.pretendard)}
            canvas.drawText("2026-11-10, 숲 체험, 물병",45f,110f,paint)
            canvas.drawText("2026-11-11, 생일잔치, 선물",45f,230f,paint)
            image.outputStream().use{bitmap.compress(Bitmap.CompressFormat.JPEG,98,it)};bitmap.recycle()
            val plans=PlanImporter(context).read()
            assertEquals(2,plans.size)
            assertEquals("2026-11-10",plans[0].date)
            assertTrue(plans[0].title.contains("숲"))
            assertEquals("2026-11-11",plans[1].date)
            assertTrue(plans[1].title.contains("생일"))
        }finally{
            if(priorImage==null)image.delete()else image.writeBytes(priorImage)
            if(priorText==null)text.delete()else text.writeBytes(priorText)
            if(priorActive==null)active.delete()else active.writeBytes(priorActive)
        }
    }
}
