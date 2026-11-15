package ai.teammoon.pli.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.teammoon.pli.domain.ConversationState
import ai.teammoon.pli.domain.StopPlace
import ai.teammoon.pli.domain.VehicleState
import kotlin.math.roundToInt

/**
 * The car Pli lives in, seen from above: who sits where (the child in the rear seat), gear and
 * speed, battery, and the route home with the stop Pli suggested. Everything shown is a live
 * vehicle or navigation signal; nothing animates on its own (the window is software-rendered).
 */
@Composable
fun CarPanel(state: ConversationState, modifier: Modifier = Modifier) {
    val v = state.vehicle
    val child = state.profile.name.takeIf { it.isNotBlank() && it != "친구" } ?: "아이"
    val stop = state.card?.takeIf { it.kind == "stop" }?.place
    val moving = (v.speedKmh ?: 0f) >= 1f
    Row(modifier.glass(30.dp).padding(horizontal = 18.dp, vertical = 16.dp).semantics {
        contentDescription = "차량 상태: ${gearLabel(v)}, 뒷좌석 $child"
    }, verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(width = 104.dp, height = 168.dp)) {
            Canvas(Modifier.size(width = 104.dp, height = 168.dp)) { drawCar(moving) }
            Box(Modifier.offset(x = 56.dp, y = 100.dp)) { Avatar(state.avatarPath, 34.dp, ring = Stage.Mint) }
        }
        Spacer(Modifier.width(18.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("우리 차", fontFamily = Stage.Font, fontSize = 15.sp, color = Stage.Dim, letterSpacing = 1.sp)
                Spacer(Modifier.width(10.dp))
                Chip(gearLabel(v), if (moving) Stage.Mint else Stage.Soft)
                v.battery?.let { Spacer(Modifier.width(8.dp)); Chip("배터리 $it%", if (it < 20) Stage.Coral else Stage.Soft) }
            }
            Text("뒷좌석 · $child", fontFamily = Stage.Font, fontSize = 18.sp, color = Stage.Cream, fontWeight = FontWeight.Bold)
            RouteBar(v, stop)
        }
    }
}

private fun gearLabel(v: VehicleState): String {
    val speed = v.speedKmh ?: 0f
    return when {
        v.gear == "D" && speed >= 1f -> "주행 ${speed.roundToInt()} km/h"
        v.gear == "D" -> "주행 준비"
        v.gear == "P" -> "정차"
        v.gear == "R" -> "후진"
        else -> "연결 중"
    }
}

@Composable private fun Chip(text: String, color: Color) {
    Text(text, fontFamily = Stage.Font, fontSize = 13.sp, color = color, maxLines = 1,
        modifier = Modifier.clip(RoundedCornerShape(50)).background(color.copy(alpha = .14f)).padding(horizontal = 10.dp, vertical = 4.dp))
}

/** 학원 ●────◆────● 집, with the car's progress and Pli's suggested stop. */
@Composable private fun RouteBar(v: VehicleState, stop: StopPlace?) {
    val minutes = v.minutesRemaining
    if (v.destination == null || minutes == null) {
        Text("목적지가 정해지면 가는 길을 보여 줄게요", fontFamily = Stage.Font, fontSize = 14.sp, color = Stage.Dim)
        return
    }
    val longest = remember(v.destination) { mutableIntStateOf(minutes) }
    if (minutes > longest.intValue) longest.intValue = minutes
    val progress = (1f - minutes.toFloat() / longest.intValue.coerceAtLeast(1)).coerceIn(0f, .95f)
    val stopAt = stop?.let { progress + (1f - progress) * (it.minutesAway.toFloat() / minutes.coerceAtLeast(1)).coerceIn(.05f, .95f) }
    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(if (v.demoTrip) "학원" else "지금", fontFamily = Stage.Font, fontSize = 13.sp, color = Stage.Soft)
            Spacer(Modifier.weight(1f))
            Text("${v.destination} · ${minutes}분", fontFamily = Stage.Font, fontSize = 13.sp, color = Stage.Cream, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(6.dp))
        BoxWithConstraints(Modifier.fillMaxWidth().height(18.dp)) {
            val width = maxWidth
            Canvas(Modifier.fillMaxWidth().height(18.dp)) {
                val y = size.height / 2
                drawLine(Stage.GlassEdge, Offset(0f, y), Offset(size.width, y), strokeWidth = 4.dp.toPx(), cap = StrokeCap.Round)
                drawLine(Stage.Sky, Offset(0f, y), Offset(size.width * progress, y), strokeWidth = 4.dp.toPx(), cap = StrokeCap.Round)
                drawCircle(Stage.Soft, 4.dp.toPx(), Offset(4.dp.toPx(), y))
                drawCircle(Stage.Cream, 5.dp.toPx(), Offset(size.width - 5.dp.toPx(), y))
                if (stop != null && stopAt != null) drawCircle(if (stop.added) Stage.Mint else Stage.Gold, 7.dp.toPx(), Offset(size.width * stopAt, y))
                drawCircle(Stage.Sky, 7.dp.toPx(), Offset(size.width * progress, y))
                drawCircle(Stage.Ink, 3.dp.toPx(), Offset(size.width * progress, y))
            }
            if (stop != null && stopAt != null) {
                Text(stop.name, fontFamily = Stage.Font, fontSize = 12.sp, color = if (stop.added) Stage.Mint else Stage.Gold, maxLines = 1,
                    overflow = TextOverflow.Ellipsis, modifier = Modifier.offset(x = (width * stopAt - 40.dp).coerceAtLeast(0.dp), y = 18.dp).width(150.dp))
            }
        }
        if (stop != null) Spacer(Modifier.height(16.dp))
        if (v.demoTrip) Text("시연 경로 · 에뮬레이터 내비 대신", fontFamily = Stage.Font, fontSize = 11.sp, color = Stage.Dim, modifier = Modifier.padding(top = 4.dp))
    }
}

/** Top-down sedan: horizon light bar in front, two rows of seats, the child seat lit in the rear. */
private fun DrawScope.drawCar(moving: Boolean) {
    val w = size.width
    val h = size.height
    val body = Size(w * .78f, h * .9f)
    val left = (w - body.width) / 2
    val top = h * .05f
    val radius = CornerRadius(body.width * .42f, body.width * .42f)
    if (moving) for (i in 0..2) {
        val x = left + body.width * (.25f + i * .25f)
        drawLine(Stage.Sky.copy(alpha = .35f - i * .08f), Offset(x, top + body.height + 2f), Offset(x, h), strokeWidth = 2.dp.toPx())
    }
    val wheel = Size(body.width * .14f, body.height * .17f)
    for ((x, y) in listOf(left - wheel.width * .45f to top + body.height * .14f, left + body.width - wheel.width * .55f to top + body.height * .14f,
        left - wheel.width * .45f to top + body.height * .68f, left + body.width - wheel.width * .55f to top + body.height * .68f)) {
        drawRoundRect(Color(0xFF05070F), Offset(x, y), wheel, CornerRadius(6f, 6f))
    }
    drawRoundRect(Brush.verticalGradient(listOf(Color(0xFF1E2A55), Color(0xFF111833))), Offset(left, top), body, radius)
    drawRoundRect(Stage.GlassEdge, Offset(left, top), body, radius, style = Stroke(1.5.dp.toPx()))
    drawRoundRect(Stage.Cream.copy(alpha = .85f), Offset(left + body.width * .12f, top + 3.dp.toPx()), Size(body.width * .76f, 2.5.dp.toPx()), CornerRadius(4f, 4f))
    val glass = Path().apply {
        moveTo(left + body.width * .16f, top + body.height * .17f); lineTo(left + body.width * .84f, top + body.height * .17f)
        lineTo(left + body.width * .76f, top + body.height * .29f); lineTo(left + body.width * .24f, top + body.height * .29f); close()
    }
    drawPath(glass, Brush.verticalGradient(listOf(Stage.Sky.copy(alpha = .55f), Stage.Sky.copy(alpha = .15f))))
    drawRoundRect(Stage.Sky.copy(alpha = .22f), Offset(left + body.width * .22f, top + body.height * .86f), Size(body.width * .56f, body.height * .06f), CornerRadius(8f, 8f))
    val seat = Size(body.width * .3f, body.height * .15f)
    fun seat(x: Float, y: Float, color: Color) = drawRoundRect(color, Offset(left + body.width * x, top + body.height * y), seat, CornerRadius(10f, 10f))
    seat(.13f, .34f, Stage.Gold.copy(alpha = .55f))  // driver (left-hand drive)
    seat(.57f, .34f, Color.White.copy(alpha = .14f))
    seat(.13f, .58f, Color.White.copy(alpha = .14f))
    drawRoundRect(Stage.Mint.copy(alpha = .3f), Offset(left + body.width * .53f, top + body.height * .55f), Size(seat.width * 1.12f, seat.height * 1.3f), CornerRadius(14f, 14f))
}
