package ai.teammoon.pli.ui

import android.graphics.BitmapFactory
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.teammoon.pli.domain.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlin.math.*

// The window renders in software (IMPLEMENTATION: hardware renderer stalls). The sky, road and Pli
// are painted behind it on the GPU (StageBackdrop); this file only lays glass, text and small marks
// over them, and repaints only when the conversation state changes.

private val TitleBrush = Brush.linearGradient(listOf(Stage.Cream, Color(0xFFFFE7A8), Stage.Gold))

@Composable fun PliStage(state: ConversationState) {
    // while the car drives, answers appear whole and cards without entry motion: every typed word or entry frame repainted
    // the whole software-rendered window and took frames from the Pleos driving view (RenderBudget, 2026-11-15)
    val reduce = RenderBudget.calm(reduceMotion(), state.vehicle)
    Box(Modifier.fillMaxSize()) {
        val album = state.album
        if (state.panel == "ALBUM" && album != null) AlbumStage(state, album, reduce) else ConversationStage(state, reduce)
        Celebration(state.correct + if (state.card?.complete == true) 1 else 0, reduce)
    }
}

@Composable private fun ConversationStage(state: ConversationState, reduce: Boolean) {
    Column(Modifier.fillMaxSize().padding(horizontal = 44.dp, vertical = 28.dp)) {
        StageHeader(state)
        Row(Modifier.weight(1f).fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(.42f).fillMaxHeight(), contentAlignment = Alignment.Center) {
                if (state.game == Game.MATH && !state.vehicle.uxRestricted) AbacusPanel(state, Modifier.fillMaxSize().padding(vertical = 26.dp).glass(34.dp).padding(22.dp))
                else Column(Modifier.fillMaxSize()) {
                    PliPlaceholder(Modifier.fillMaxWidth().weight(1f))
                    CarPanel(state, Modifier.fillMaxWidth())
                }
            }
            Spacer(Modifier.width(32.dp))
            Column(Modifier.weight(.58f)) {
                Kicker(kicker(state), moodColor(state))
                Spacer(Modifier.height(14.dp))
                if (reduce) StageTitle(state.title)  // a new answer's title appears at once while driving (RenderBudget.calm)
                else AnimatedContent(targetState = state.title, transitionSpec = {
                    (fadeIn(tween(420)) + slideInVertically(tween(520, easing = FastOutSlowInEasing)) { it / 3 }) togetherWith fadeOut(tween(200))
                }, label = "title") { title -> StageTitle(title) }
                Spacer(Modifier.height(20.dp))
                SpeechBubble(speechLine(state), moodColor(state), reduce)
                Spacer(Modifier.height(if (state.card != null) 16.dp else 22.dp))
                val card = state.card
                when {
                    card != null -> { TraceChips(state.agentSteps);Spacer(Modifier.height(12.dp));StageCardPanel(card, reduce) }
                    state.agentSteps.isNotEmpty() -> AgentTrace(state.agentSteps, state.agentBusy, reduce)
                    state.game == Game.FRIEND -> IdeaTiles(reduce)
                }
            }
        }
        VoiceDock(state, reduce)
    }
}

@Composable private fun StageTitle(title: String) {
    Text(title, style = TextStyle(brush = TitleBrush), fontFamily = Stage.Font, fontSize = 48.sp, lineHeight = 60.sp,
        fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
}

private fun kicker(state: ConversationState) = when {
    state.agentBusy -> "엣지 AI가 생각하는 중"
    state.phase == VoicePhase.NAVIGATION -> "길 안내를 듣는 중"
    state.game == Game.WORDCHAIN || state.game == Game.RIDDLE -> "${state.game.title} · 엣지 놀이 엔진"
    state.panel == "ENGLISH_TURN" -> "이번엔 네가 선생님"
    state.game != Game.FRIEND -> "목소리로 함께하는 ${state.game.title}"
    else -> "${state.profile.name}의 밤길 친구"
}

private fun speechLine(state: ConversationState) = when {
    state.sessionStatus == "STOPPED" -> "마이크를 켜고, 편하게 말해 주세요."
    state.phase == VoicePhase.NAVIGATION -> "안내가 끝나면, 우리 이야기를 이어 갈게."
    state.quiet -> "잠시 쉬고 있어요. ‘다시 시작해’라고 말해 주세요."
    state.agentBusy && state.speech.isBlank() -> "질문을 이해하고, 필요한 정보를 찾아 답을 만들고 있어요."
    state.speech.isNotBlank() -> state.speech
    else -> "무엇이든 물어봐. 하늘이 왜 파란지, 오늘 준비물이 뭔지, 우리 사진까지!"
}

@Composable private fun Kicker(text: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(34.dp).height(3.dp).clip(RoundedCornerShape(50)).background(Brush.horizontalGradient(listOf(color, color.copy(alpha = 0f)))))
        Text(text, fontFamily = Stage.Font, fontSize = 17.sp, letterSpacing = 1.5.sp, color = color, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(start = 12.dp))
    }
}

// ---- Header ----------------------------------------------------------------------------------

@Composable private fun StageHeader(state: ConversationState) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text("pli", style = TextStyle(brush = Brush.linearGradient(listOf(Stage.Gold, Stage.Ember))), fontFamily = Stage.Font, fontSize = 48.sp,
            fontWeight = FontWeight.Black, letterSpacing = (-2.5).sp)
        Text("✦", fontSize = 18.sp, color = Stage.Mint, modifier = Modifier.padding(start = 4.dp, bottom = 26.dp))
        Spacer(Modifier.width(24.dp))
        Row(Modifier.glass(50.dp).padding(start = 6.dp, end = 22.dp, top = 6.dp, bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Avatar(state.avatarPath, 46.dp, moodColor(state))
            Column(Modifier.padding(start = 12.dp)) {
                Text(state.profile.name, fontFamily = Stage.Font, fontSize = 20.sp, color = Stage.Cream, fontWeight = FontWeight.SemiBold)
                Text("작은 탐험가 · 오늘도 함께", fontFamily = Stage.Font, fontSize = 13.sp, color = Stage.Dim)
            }
        }
        Spacer(Modifier.weight(1f))
        tripChips(state.vehicle).forEach { (icon, label) -> HeaderChip(icon, label) }
        StatusPill(state)
    }
}

private fun tripChips(vehicle: VehicleState): List<Pair<String, String>> = buildList {
    vehicle.destination?.let { add("📍" to it) }
    vehicle.minutesRemaining?.let { add("⏱" to "${it}분 남음") }
    vehicle.speedKmh?.takeIf { it >= 1f }?.let { add("🚗" to "${it.roundToInt()} km/h") }
    vehicle.cabinTemperatureC?.let { add("🌡" to "${it.roundToInt()}°") }
}.take(3)

@Composable private fun HeaderChip(icon: String, label: String) {
    Row(Modifier.padding(end = 10.dp).glass(50.dp).padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(icon, fontSize = 15.sp)
        Text(label, fontFamily = Stage.Font, fontSize = 15.sp, color = Stage.Soft, maxLines = 1, modifier = Modifier.padding(start = 8.dp).widthIn(max = 220.dp), overflow = TextOverflow.Ellipsis)
    }
}

@Composable private fun StatusPill(state: ConversationState) {
    val color = moodColor(state)
    Row(Modifier.glass(50.dp, fill = color.copy(alpha = .12f), edge = color.copy(alpha = .45f)).padding(horizontal = 18.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(18.dp), contentAlignment = Alignment.Center) {
            Box(Modifier.size(18.dp).background(color.copy(alpha = .25f), CircleShape))
            Box(Modifier.size(9.dp).background(color, CircleShape))
        }
        Text(phaseLabel(state), fontFamily = Stage.Font, fontSize = 16.sp, color = Stage.Cream, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 10.dp))
        Text("  ·  온디바이스 AI", fontFamily = Stage.Font, fontSize = 14.sp, color = Stage.Dim)
    }
}

private fun phaseLabel(state: ConversationState) = when {
    state.error != null -> "연결 확인 필요"
    state.sessionStatus == "STOPPED" -> "마이크 꺼짐"
    state.agentBusy -> "생각하는 중"
    state.phase == VoicePhase.SPEAKING -> "플리가 말하는 중"
    state.phase == VoicePhase.LISTENING -> "듣는 중"
    state.phase == VoicePhase.QUIET -> "쉬는 중"
    state.phase == VoicePhase.NAVIGATION -> "길 안내 중"
    state.phase == VoicePhase.QUEUED -> "답변 준비"
    else -> "준비 중"
}

/** "5분 뒤 · +3분", or the waypoint confirmation once the parent said yes. */
@Composable private fun StopBadge(place: StopPlace) {
    val color = if (place.added) Stage.Mint else Stage.Soft
    Text(if (place.added) "경유지 · ${place.minutesAway}분 뒤" else "${place.minutesAway}분 뒤 · +${place.detourMinutes}분", fontFamily = Stage.Font, fontSize = 15.sp,
        fontWeight = FontWeight.Bold, color = color, modifier = Modifier.clip(RoundedCornerShape(50)).background(color.copy(alpha = .16f)).padding(horizontal = 12.dp, vertical = 5.dp))
}

@Composable internal fun Avatar(path: String?, size: Dp, ring: Color = Stage.Gold) {
    val image = rememberImage(path, 256)
    Box(Modifier.size(size).border(2.5.dp, Brush.sweepGradient(listOf(ring, Stage.Gold, ring)), CircleShape).padding(3.dp).clip(CircleShape).background(Stage.SkyMid),
        contentAlignment = Alignment.Center) {
        if (image != null) Image(image, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) else Text("✦", color = Stage.Gold, fontSize = 18.sp)
    }
}

/** Decoded photos are reused across album pages and the end card (decoding is slow in software rendering). */
private object StageImages { val cache = android.util.LruCache<String, ImageBitmap>(8) }

@Composable private fun rememberImage(path: String?, maxSide: Int): ImageBitmap? {
    val key = "$path@$maxSide"
    var image by remember(path) { mutableStateOf(path?.let { StageImages.cache.get(key) }) }
    LaunchedEffect(path) {
        if (path == null || image != null) return@LaunchedEffect
        image = withContext(Dispatchers.IO) {
            runCatching {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeFile(path, bounds)
                var sample = 1
                while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
                BitmapFactory.decodeFile(path, BitmapFactory.Options().apply { inSampleSize = sample })?.asImageBitmap()
            }.getOrNull()
        }?.also { StageImages.cache.put(key, it) }
    }
    return image
}

// ---- What Pli says ---------------------------------------------------------------------------

/** Glass speech bubble whose tail points back at Pli. */
@Composable private fun SpeechBubble(text: String, accent: Color, reduce: Boolean) {
    Box(Modifier.fillMaxWidth().drawBehind {
        val tail = Path().apply { moveTo(0f, size.height * .38f);lineTo(-18.dp.toPx(), size.height * .5f);lineTo(0f, size.height * .62f);close() }
        drawPath(tail, Stage.GlassStrong)
    }.glass(28.dp, fill = Stage.GlassStrong).drawBehind {
        drawRect(Brush.verticalGradient(listOf(accent, accent.copy(alpha = .2f))), Offset.Zero, Size(5.dp.toPx(), size.height))
    }.padding(start = 30.dp, end = 26.dp, top = 22.dp, bottom = 22.dp)) {
        Typewriter(text, reduce)
    }
}

private const val WORD_STEP_MILLIS = 110L

/** Reveals the answer a word at a time: each step repaints the whole software-rendered window,
 *  so ~9 word steps a second read as typing without the 36 full repaints a second of per-letter steps. */
@Composable private fun Typewriter(text: String, reduce: Boolean) {
    var shown by remember(text) { mutableIntStateOf(if (reduce) text.length else 0) }
    LaunchedEffect(text) {
        if (reduce) return@LaunchedEffect
        while (shown < text.length) {
            delay(WORD_STEP_MILLIS)
            val next = text.indexOf(' ', shown + 1)
            shown = if (next < 0) text.length else next
        }
    }
    Text(text.take(shown), fontFamily = Stage.Font, fontSize = 27.sp, lineHeight = 40.sp, color = Stage.Cream, maxLines = 4, overflow = TextOverflow.Ellipsis)
}

// ---- How the edge agent got there ------------------------------------------------------------

@Composable private fun AgentTrace(steps: List<AgentStep>, busy: Boolean, reduce: Boolean) {
    if (steps.isEmpty()) return
    Column(Modifier.fillMaxWidth().glass(26.dp).padding(horizontal = 22.dp, vertical = 16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("EDGE AGENT", fontFamily = Stage.Font, fontSize = 12.sp, letterSpacing = 2.5.sp, color = Stage.Violet, fontWeight = FontWeight.Bold)
            Text("  ·  이 차 안에서만 생각해요", fontFamily = Stage.Font, fontSize = 12.sp, color = Stage.Dim)
            Spacer(Modifier.weight(1f))
            Text(if (busy) "처리 중" else "${steps.maxOf { it.ms }}ms", fontFamily = Stage.Font, fontSize = 13.sp, color = if (busy) Stage.Violet else Stage.Mint)
        }
        Spacer(Modifier.height(10.dp))
        val shown = steps.takeLast(5)
        shown.forEachIndexed { index, step ->
            key(step.id) {
                val visible = remember { MutableTransitionState(reduce) }
                visible.targetState = true
                AnimatedVisibility(visible, enter = fadeIn(tween(320, delayMillis = index * 60)) + slideInHorizontally(tween(420, delayMillis = index * 60, easing = FastOutSlowInEasing)) { -it / 6 }) {
                    StepRow(step, last = index == shown.lastIndex, reduce)
                }
            }
        }
    }
}

@Composable private fun StepRow(step: AgentStep, last: Boolean, reduce: Boolean) {
    val color = when (step.state) { "running" -> Stage.Violet;"fail" -> Stage.Coral;else -> Stage.Mint }
    Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min), verticalAlignment = Alignment.Top) {
        Box(Modifier.width(26.dp).fillMaxHeight().drawBehind {
            if (!last) drawLine(Stage.GlassEdge, Offset(size.width / 2, 24.dp.toPx()), Offset(size.width / 2, size.height), 2.dp.toPx())
        }, contentAlignment = Alignment.TopCenter) {
            if (step.state == "running" && !reduce) SpinnerSurface(Modifier.padding(top = 3.dp).size(20.dp))
            else Canvas(Modifier.padding(top = 3.dp).size(20.dp)) {
                drawCircle(color.copy(alpha = .22f), size.minDimension / 2)
                when (step.state) {
                    "running" -> drawArc(color, 0f, 270f, false, style = Stroke(3f, cap = StrokeCap.Round))
                    "fail" -> drawCircle(color, size.minDimension / 4)
                    else -> drawPath(Path().apply { moveTo(size.width * .28f, size.height * .52f);lineTo(size.width * .44f, size.height * .68f);lineTo(size.width * .74f, size.height * .34f) },
                        color, style = Stroke(3f, cap = StrokeCap.Round))
                }
            }
        }
        Column(Modifier.padding(start = 12.dp, bottom = if (last) 0.dp else 10.dp)) {
            Text(step.label, fontFamily = Stage.Font, fontSize = 18.sp, color = Stage.Cream, fontWeight = FontWeight.Medium)
            if (step.detail.isNotBlank()) Text(step.detail, fontFamily = Stage.Font, fontSize = 14.sp, color = Stage.Dim, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

// ---- Plans the edge composed: what to pack, what to do on the way ---------------------------------

/** The agent's work as one quiet line of chips, so the card gets the room. */
@Composable private fun TraceChips(steps: List<AgentStep>) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text("EDGE AGENT", fontFamily = Stage.Font, fontSize = 12.sp, letterSpacing = 2.5.sp, color = Stage.Violet, fontWeight = FontWeight.Bold)
        steps.filter { it.id != "hear" && it.id != "plan" }.takeLast(3).forEach { step ->
            val fail = step.state == "fail"
            Text((if (fail) "· " else "✓ ") + step.label, fontFamily = Stage.Font, fontSize = 14.sp, color = if (fail) Stage.Coral else Stage.Mint, maxLines = 1,
                modifier = Modifier.padding(start = 10.dp).glass(50.dp).padding(horizontal = 12.dp, vertical = 5.dp))
        }
    }
}

@Composable private fun StageCardPanel(card: StageCard, reduce: Boolean) {
    val accent = when (card.kind) { "pack" -> Stage.Gold; "stop" -> Stage.Mint; else -> Stage.Aurora }
    Column(Modifier.fillMaxWidth().glass(28.dp, fill = Stage.GlassStrong, edge = accent.copy(alpha = .55f)).padding(horizontal = 22.dp, vertical = 18.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(when (card.kind) { "pack" -> "CHECKLIST"; "stop" -> if (card.place?.added == true) "WAYPOINT ADDED" else "ON THE WAY HOME"; else -> "ON THE WAY" }, fontFamily = Stage.Font, fontSize = 12.sp, letterSpacing = 2.5.sp, color = accent, fontWeight = FontWeight.Bold)
            if (card.subtitle.isNotBlank()) Text(card.subtitle, fontFamily = Stage.Font, fontSize = 15.sp, color = Stage.Cream, maxLines = 1,
                modifier = Modifier.padding(start = 12.dp).clip(RoundedCornerShape(50)).background(accent.copy(alpha = .18f)).padding(horizontal = 12.dp, vertical = 4.dp))
            Spacer(Modifier.weight(1f))
            if (card.kind == "pack") PackProgress(card)
            card.place?.let { StopBadge(it) }
        }
        Spacer(Modifier.height(14.dp))
        if (card.kind == "pack") {
            card.items.chunked(2).forEachIndexed { row, pair ->
                Row(Modifier.fillMaxWidth().padding(bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    pair.forEachIndexed { col, item -> PackTile(item, item.label in card.checked, row * 2 + col, reduce, Modifier.weight(1f)) }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        } else {
            var index = 0
            card.sections.forEach { section ->
                Text(section.title, fontFamily = Stage.Font, fontSize = 14.sp, letterSpacing = 1.sp, color = Stage.Soft, modifier = Modifier.padding(top = 4.dp, bottom = 6.dp))
                section.items.forEach { item -> RouteRow(item, index++, reduce) }
            }
        }
    }
}

/** A ring that fills as the child says what they packed. */
@Composable private fun PackProgress(card: StageCard) {
    val done = if (card.items.isEmpty()) 0f else card.checked.size / card.items.size.toFloat()
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(if (card.complete) "준비 끝! ✨" else "${card.checked.size} / ${card.items.size}", fontFamily = Stage.Font, fontSize = 16.sp,
            fontWeight = FontWeight.SemiBold, color = if (card.complete) Stage.Mint else Stage.Soft)
        Canvas(Modifier.padding(start = 10.dp).size(30.dp)) {
            drawCircle(Stage.GlassEdge, size.minDimension / 2 - 2.dp.toPx(), style = Stroke(3.dp.toPx()))
            drawArc(Brush.sweepGradient(listOf(Stage.Gold, Stage.Mint, Stage.Gold)), -90f, 360f * done, false, style = Stroke(3.dp.toPx(), cap = StrokeCap.Round),
                topLeft = Offset(2.dp.toPx(), 2.dp.toPx()), size = Size(size.width - 4.dp.toPx(), size.height - 4.dp.toPx()))
        }
    }
}

@Composable private fun Appear(index: Int, reduce: Boolean, content: @Composable (Modifier) -> Unit) {
    val shown = remember { Animatable(if (reduce) 1f else 0f) }
    LaunchedEffect(Unit) { if (!reduce) { delay(90L * index);shown.animateTo(1f, tween(380, easing = FastOutSlowInEasing)) } }
    content(Modifier.graphicsLayer { alpha = shown.value;translationY = (1f - shown.value) * 16.dp.toPx() })
}

private val TileHues = listOf(Stage.Gold, Stage.Aurora, Stage.Violet, Stage.Rose, Stage.Sky, Stage.Ember)

@Composable private fun PackTile(item: CardItem, checked: Boolean, index: Int, reduce: Boolean, modifier: Modifier) {
    val tick by animateFloatAsState(if (checked) 1f else 0f, tween(if (reduce) 0 else 320, easing = FastOutSlowInEasing), label = "tick")
    val hue = TileHues[index % TileHues.size]
    Appear(index, reduce) { motion ->
        Row(modifier.then(motion).glass(20.dp, fill = lerp(Stage.GlassFill, Stage.Mint.copy(alpha = .16f), tick), edge = lerp(Stage.GlassEdge, Stage.Mint.copy(alpha = .7f), tick))
            .padding(horizontal = 14.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(54.dp).background(Brush.radialGradient(listOf(hue.copy(alpha = .45f), hue.copy(alpha = .08f))), CircleShape), contentAlignment = Alignment.Center) {
                Text(item.icon, fontSize = 30.sp)
            }
            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                Text(item.label, fontFamily = Stage.Font, fontSize = 26.sp, fontWeight = FontWeight.Bold, color = lerp(Stage.Cream, Stage.Mint, tick), maxLines = 1)
                if (item.reason.isNotBlank()) Text(item.reason, fontFamily = Stage.Font, fontSize = 14.sp, color = Stage.Dim, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Canvas(Modifier.size(32.dp)) {
                drawCircle(lerp(Stage.GlassEdge, Stage.Mint, tick), size.minDimension / 2, style = if (tick > .5f) androidx.compose.ui.graphics.drawscope.Fill else Stroke(2.5f))
                if (tick > 0f) drawPath(Path().apply { moveTo(size.width * .28f, size.height * .52f);lineTo(size.width * .44f, size.height * .68f);lineTo(size.width * .74f, size.height * .34f) },
                    Stage.Ink.copy(alpha = tick), style = Stroke(3.5f, cap = StrokeCap.Round))
            }
        }
    }
}

@Composable private fun RouteRow(item: CardItem, index: Int, reduce: Boolean) {
    Appear(index, reduce) { motion ->
        Row(motion.fillMaxWidth().padding(vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(46.dp).background(Brush.radialGradient(listOf(Stage.Aurora.copy(alpha = .35f), Stage.Aurora.copy(alpha = .05f))), CircleShape), contentAlignment = Alignment.Center) {
                Text(item.icon, fontSize = 24.sp)
            }
            Text(item.label, fontFamily = Stage.Font, fontSize = 24.sp, color = Stage.Cream, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(start = 14.dp).weight(1f, fill = false))
            if (item.reason.isNotBlank()) Text("  " + item.reason, fontFamily = Stage.Font, fontSize = 13.sp, color = Stage.Dim, maxLines = 1)
        }
    }
}

// ---- Voice dock --------------------------------------------------------------------------------

private val Hints = listOf("🎒" to "내일 뭐 챙겨?", "🌲" to "숲 체험 가자", "📸" to "앨범 만들어 줘")
private val MoreHints = listOf("❓" to "하늘은 왜 파래?", "🎵" to "수수께끼 내 줘", "🤫" to "플리야 쉿")

/** What Pli can do, shown while nothing else is on the stage. */
private data class Idea(val icon: String, val title: String, val say: String, val hue: Color)
private val Ideas = listOf(
    Idea("🎒", "준비물 체크", "내일 뭐 챙겨?", Stage.Gold), Idea("🌲", "가는 길 놀이", "숲 체험 가자", Stage.Aurora),
    Idea("📸", "이야기 앨범", "앨범 만들어 줘", Stage.Rose), Idea("🧩", "끝말잇기 · 퀴즈", "끝말잇기 하자", Stage.Violet))

@Composable private fun IdeaTiles(reduce: Boolean) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("이렇게 말해 봐", fontFamily = Stage.Font, fontSize = 14.sp, letterSpacing = 2.sp, color = Stage.Dim, fontWeight = FontWeight.SemiBold)
        Ideas.chunked(2).forEachIndexed { row, pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                pair.forEachIndexed { col, idea ->
                    Appear(row * 2 + col, reduce) { motion ->
                        Row(Modifier.weight(1f).then(motion).glass(22.dp, edge = idea.hue.copy(alpha = .45f)).padding(horizontal = 14.dp, vertical = 14.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(52.dp).background(Brush.radialGradient(listOf(idea.hue.copy(alpha = .5f), idea.hue.copy(alpha = .06f))), CircleShape),
                                contentAlignment = Alignment.Center) { Text(idea.icon, fontSize = 28.sp) }
                            Column(Modifier.padding(start = 14.dp)) {
                                Text(idea.title, fontFamily = Stage.Font, fontSize = 21.sp, color = Stage.Cream, fontWeight = FontWeight.Bold, maxLines = 1)
                                Text("“${idea.say}”", fontFamily = Stage.Font, fontSize = 15.sp, color = idea.hue, maxLines = 1)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable private fun VoiceDock(state: ConversationState, reduce: Boolean) {
    val color = moodColor(state)
    Row(Modifier.fillMaxWidth().padding(top = 18.dp).glass(32.dp, fill = Color(0x24101633), edge = color.copy(alpha = .45f)).padding(horizontal = 18.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(58.dp).background(Brush.radialGradient(listOf(color.copy(alpha = .55f), color.copy(alpha = .10f))), CircleShape)
            .border(1.5.dp, color.copy(alpha = .8f), CircleShape), contentAlignment = Alignment.Center) {
            Text(if (state.quiet) "🤫" else if (state.sessionStatus == "STOPPED") "🔇" else "🎙", fontSize = 24.sp)
        }
        WaveSurface(state, reduce, Modifier.padding(start = 14.dp).width(112.dp).height(40.dp))
        Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f)) {
            Text(state.partial.ifBlank { state.heard }.ifBlank { "“하늘은 왜 파래?”처럼 무엇이든 물어보세요" }, fontFamily = Stage.Font, fontSize = 22.sp,
                color = Stage.Cream, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            val error = state.error
            if (error != null) Text(error, fontFamily = Stage.Font, fontSize = 13.sp, color = Stage.Coral, maxLines = 1, overflow = TextOverflow.Ellipsis)
            else Text(state.answerSource.ifBlank { "말하면 플리가 바로 들어요 · 원본은 이 차의 엣지 컴퓨터에만" }, fontFamily = Stage.Font, fontSize = 13.sp, color = Stage.Dim, maxLines = 1)
        }
        val ideasShown = state.card == null && state.agentSteps.isEmpty() && state.game == Game.FRIEND
        (if (ideasShown) MoreHints else Hints).forEachIndexed { i, (icon, hint) ->
            val hue = TileHues[(i + 1) % TileHues.size]
            Row(Modifier.padding(start = 10.dp).glass(50.dp, edge = hue.copy(alpha = .5f)).padding(horizontal = 14.dp, vertical = 9.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(icon, fontSize = 16.sp)
                Text(hint, fontFamily = Stage.Font, fontSize = 15.sp, color = Stage.Soft, modifier = Modifier.padding(start = 6.dp))
            }
        }
    }
}

@Composable private fun Celebration(correct: Int, reduce: Boolean) {
    var last by remember { mutableIntStateOf(correct) }
    val burst = remember { Animatable(1f) }
    LaunchedEffect(correct) {
        if (correct > last && !reduce) { burst.snapTo(0f);burst.animateTo(1f, tween(1700, easing = LinearEasing)) }
        last = correct
    }
    if (burst.value >= 1f) return
    Canvas(Modifier.fillMaxSize()) {
        val p = burst.value;val colors = listOf(Stage.Gold, Stage.Mint, Stage.Rose, Stage.Violet, Stage.Cream)
        for (i in 0 until 52) {
            val angle = i * 2.4f;val speed = .35f + (i % 7) / 10f
            val x = size.width * .5f + cos(angle) * size.width * .42f * speed * p
            val y = size.height * .45f + sin(angle) * size.height * .3f * speed * p + size.height * .5f * p * p
            rotate(p * 540f + i * 31f, Offset(x, y)) { drawRect(colors[i % colors.size].copy(alpha = 1f - p), Offset(x - 7f, y - 3.5f), Size(14f, 7f)) }
        }
    }
}

// ---- Album ---------------------------------------------------------------------------------

@Composable fun AlbumStage(state: ConversationState, album: AlbumView, reduce: Boolean = reduceMotion()) {
    Column(Modifier.fillMaxSize().padding(horizontal = 44.dp, vertical = 28.dp)) {
        Row(Modifier.fillMaxWidth().glass(30.dp).padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Avatar(state.avatarPath, 56.dp, Stage.Rose)
            Column(Modifier.padding(start = 16.dp).weight(1f)) {
                Text(if (album.mode == "STORY") "엣지 AI가 만든 이야기 앨범" else "가족 앨범 · 얼굴 인식으로 ${album.child} 찾기", fontFamily = Stage.Font, fontSize = 15.sp,
                    color = Stage.Rose, letterSpacing = 1.sp, fontWeight = FontWeight.SemiBold)
                Text(album.title, style = TextStyle(brush = TitleBrush), fontFamily = Stage.Font, fontSize = 36.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Text(state.agentSteps.lastOrNull { it.id == "face" }?.detail.orEmpty(), fontFamily = Stage.Font, fontSize = 14.sp, color = Stage.Dim)
        }
        Spacer(Modifier.height(20.dp))
        Box(Modifier.weight(1f).fillMaxWidth()) {
            if (album.mode == "STORY") StoryPages(album, reduce) else PhotoGrid(album, reduce)
        }
        Text(if (album.mode == "STORY") "사진 속 다른 사람 얼굴은 흐리게 처리했어요 · 원본은 이 차의 엣지 컴퓨터에만 있어요" else "“앨범 만들어 줘”라고 말하면 플리가 이야기 앨범으로 꾸며 줘요",
            fontFamily = Stage.Font, fontSize = 14.sp, color = Stage.Dim, modifier = Modifier.padding(top = 14.dp))
    }
}

@Composable private fun PhotoGrid(album: AlbumView, reduce: Boolean) {
    AlbumGridSurface(album, reduce, Modifier.fillMaxSize().semantics { contentDescription = "${album.child}의 사진 ${album.photos.size}장" })
}

@Composable private fun StoryPages(album: AlbumView, reduce: Boolean) {
    when {
        album.index <= 0 -> TitleCard(album)
        album.index > album.photos.size -> EndCard(album)
        else -> StorySurface(album, reduce, Modifier.fillMaxSize().semantics { contentDescription = album.photos[album.index - 1].caption })
    }
}

@Composable private fun CardPhoto(photo: AlbumPhoto, modifier: Modifier) {
    val image = rememberImage(photo.path, 900)
    Box(modifier.background(Stage.SkyMid)) { if (image != null) Image(image, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) }
}

@Composable private fun TitleCard(album: AlbumView) {
    val cover = album.photos.firstOrNull()
    Box(Modifier.fillMaxSize().clip(RoundedCornerShape(34.dp)), contentAlignment = Alignment.Center) {
        if (cover != null) CardPhoto(cover, Modifier.fillMaxSize().graphicsLayer { alpha = .38f })
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0x660C1433), Color(0xE6050819)))))
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("PLI ALBUM", fontFamily = Stage.Font, fontSize = 16.sp, letterSpacing = 6.sp, color = Stage.Rose, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(18.dp))
            Text(album.title, style = TextStyle(brush = TitleBrush), fontFamily = Stage.Font, fontSize = 62.sp, fontWeight = FontWeight.Black, textAlign = TextAlign.Center)
            Spacer(Modifier.height(16.dp))
            Text("${album.child}의 사진 ${album.photos.size}장 · ${album.createdBy}", fontFamily = Stage.Font, fontSize = 19.sp, color = Stage.Soft)
        }
    }
}

@Composable private fun EndCard(album: AlbumView) {
    Box(Modifier.fillMaxSize().glass(34.dp), contentAlignment = Alignment.Center) {
        Row(horizontalArrangement = Arrangement.spacedBy((-28).dp)) {
            album.photos.take(4).forEachIndexed { i, photo ->
                CardPhoto(photo, Modifier.size(220.dp, 280.dp).graphicsLayer { rotationZ = (i - 1.5f) * 7f }.clip(RoundedCornerShape(18.dp)).border(4.dp, Stage.Cream, RoundedCornerShape(18.dp)))
            }
        }
        Text("또 보고 싶으면 “앨범 보여 줘”", fontFamily = Stage.Font, fontSize = 26.sp, color = Stage.Cream, modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 40.dp))
    }
}
