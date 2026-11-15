package ai.teammoon.pli.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.teammoon.pli.domain.*

/**
 * Every Pli screen over one GPU-painted night scene ([StageBackdrop]). The scene lives outside the
 * per-session key and the entry fade, so it never restarts or flashes when the screen changes.
 */
@Composable fun PliScreen(state: ConversationState, presentation: Boolean = false) {
    val reduce = reduceMotion()
    val spot = remember { PliSpot() }
    Box(Modifier.fillMaxSize()) {
        StageBackdrop(state, spot, reduce, Modifier.fillMaxSize())
        CompositionLocalProvider(LocalPliSpot provides spot) {
            key(state.demo, state.epoch) {
                val scene = "${state.audience}:${state.panel}:${state.game}"
                // a new screen appears at once while the car drives (RenderBudget.calm); the backdrop keeps `reduce` so Pli still talks
                val calm = RenderBudget.calm(reduce, state.vehicle)
                val entry = remember(scene) { Animatable(if (calm) 1f else 0f) }
                LaunchedEffect(scene) { if (!calm) entry.animateTo(1f, tween(260, easing = FastOutSlowInEasing)) }
                Box(Modifier.fillMaxSize().graphicsLayer { alpha = entry.value;translationY = (1f - entry.value) * 14.dp.toPx() }) { PliScene(state) }
            }
        }
    }
}

@Composable private fun PliScene(state: ConversationState) {
    when {
        state.panel == "GROWTH" -> GrowthOverview(state)
        state.panel == "DESTINATIONS" -> DestinationOptions(state)
        state.panel == "CHARGE" -> ChargingPlayground(state)
        state.audience == "PARENT" -> ParentBriefing(state)
        else -> PliStage(state)
    }
}

/** What the parent asked for (notices, plans, preparation), read aloud and shown large enough to glance at. */
@Composable private fun ParentBriefing(state: ConversationState) {
    val limited = state.vehicle.uxRestricted
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth > 900.dp
        Column(Modifier.fillMaxSize().padding(horizontal = if (wide) 56.dp else 28.dp, vertical = if (wide) 36.dp else 22.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("pli", style = TextStyle(brush = Brush.linearGradient(listOf(Stage.Gold, Stage.Ember))), fontFamily = Stage.Font,
                    fontSize = if (wide) 46.sp else 30.sp, fontWeight = FontWeight.Black)
                Text("  우리 가족의 가는 길", fontFamily = Stage.Font, fontSize = if (wide) 22.sp else 15.sp, color = Stage.Soft)
                Spacer(Modifier.weight(1f))
                val live = state.capture == "ACTIVE"
                Row(Modifier.glass(50.dp, fill = (if (live) Stage.Mint else Stage.Dim).copy(alpha = .12f)).padding(horizontal = 18.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(10.dp).background(if (live) Stage.Mint else Stage.Dim, CircleShape))
                    Text(if (live) "목소리로 연결됨" else "대화 연결 확인", fontFamily = Stage.Font, fontSize = if (wide) 18.sp else 13.sp, color = Stage.Cream, modifier = Modifier.padding(start = 10.dp))
                }
            }
            Spacer(Modifier.height(if (wide) 40.dp else 22.dp))
            Text("FAMILY BRIEFING", fontFamily = Stage.Font, fontSize = if (wide) 16.sp else 12.sp, letterSpacing = 3.sp, color = Stage.Aurora, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(12.dp))
            Text(state.title, style = TextStyle(brush = Brush.linearGradient(listOf(Stage.Cream, Stage.Gold))), fontFamily = Stage.Font,
                fontSize = if (wide) 56.sp else 31.sp, fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Spacer(Modifier.height(if (wide) 30.dp else 20.dp))
            Column(Modifier.fillMaxWidth().weight(1f).glass(32.dp, fill = Stage.GlassStrong).padding(if (wide) 40.dp else 24.dp)) {
                Text(state.answerSource.ifBlank { "오늘의 일정과 준비물" }, fontFamily = Stage.Font, fontSize = if (wide) 22.sp else 14.sp, color = Stage.Gold, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(20.dp))
                Text(state.speech.ifBlank { "“오늘 등원 준비 알려줘”라고 말해 보세요." }, fontFamily = Stage.Font, color = Stage.Cream,
                    fontSize = if (wide) 40.sp else 23.sp, lineHeight = if (wide) 62.sp else 36.sp, maxLines = if (limited) 3 else if (wide) 7 else 6, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.weight(1f))
                if (!limited) {
                    Box(Modifier.fillMaxWidth().height(1.dp).background(Stage.GlassEdge))
                    Spacer(Modifier.height(18.dp))
                    Text(if (state.readingHasMore) "${state.readingPage + 1}번째 문단 · 이어서 들으려면 “더 읽어”" else "이어서 물어보세요",
                        fontFamily = Stage.Font, color = Stage.Aurora, fontSize = if (wide) 20.sp else 14.sp)
                    Spacer(Modifier.height(10.dp))
                    Text(if (state.readingHasMore) "더 읽어 · 이전 문단 · 처음부터 읽어 · 그만 읽어" else "내일 준비물 있어?     ·     최근 알림장 읽어줘",
                        fontFamily = Stage.Font, color = Stage.Soft, fontSize = if (wide) 26.sp else 17.sp, maxLines = 2)
                }
            }
            Spacer(Modifier.height(22.dp))
            Text(when {
                state.phase == VoicePhase.STOPPED -> "마이크를 껐어요."
                state.quiet -> "조용히 듣고 있어요. 다시 시작하려면 “다시 놀자”."
                state.playback == "PLAYING" -> "확인한 자료를 읽어드리고 있어요."
                state.recognition != "READY" -> "다음 질문을 받을 준비를 하고 있어요."
                else -> "플리가 듣고 있어요. 놀이로 돌아가려면 “숫자 놀이 해줘”."
            }, fontFamily = Stage.Font, color = Stage.Dim, fontSize = if (wide) 24.sp else 16.sp, maxLines = 2)
        }
    }
}
