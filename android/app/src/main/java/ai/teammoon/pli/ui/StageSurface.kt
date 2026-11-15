package ai.teammoon.pli.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.PixelFormat
import android.graphics.PorterDuff
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.view.SurfaceHolder
import android.view.SurfaceView
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.*
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.res.ResourcesCompat
import ai.teammoon.pli.R
import ai.teammoon.pli.domain.*
import kotlin.math.*

/**
 * A SurfaceView painted by its own vsync-paced thread ([FrameLoop]). The activity window renders in
 * software (hardware renderer stalls, see IMPLEMENTATION), so continuous motion lives here: only
 * this surface is repainted each frame and the window redraws only when the UI state changes.
 */
@Composable fun AnimatedSurface(modifier: Modifier, name: String, fps: Int = 60, onTop: Boolean = true, rate: (() -> Int)? = null,
                                draw: DrawScope.(Long) -> Unit) {
    val density = LocalDensity.current
    val latest = rememberUpdatedState(draw)
    val currentRate = rememberUpdatedState(rate ?: { fps })
    AndroidView(modifier = modifier, factory = { context ->
        SurfaceView(context).apply {
            setZOrderOnTop(onTop)  // below the window: Compose content is drawn over it as glass
            holder.setFormat(if (onTop) PixelFormat.TRANSLUCENT else PixelFormat.OPAQUE)
            holder.addCallback(object : SurfaceHolder.Callback {
                private var loop: FrameLoop? = null
                override fun surfaceCreated(h: SurfaceHolder) {
                    val scope = CanvasDrawScope()
                    loop = FrameLoop(h, name, { currentRate.value() }) { canvas, t ->
                        scope.draw(density, LayoutDirection.Ltr, Canvas(canvas), Size(canvas.width.toFloat(), canvas.height.toFloat())) { latest.value(this, t) }
                    }
                }
                override fun surfaceChanged(h: SurfaceHolder, format: Int, width: Int, height: Int) = Unit
                override fun surfaceDestroyed(h: SurfaceHolder) { loop?.stop();loop = null }
            })
        }
    })
}

private fun pingPong(t: Long, period: Int): Float { val x = (t % (period * 2L)).toFloat() / period;return if (x <= 1f) x else 2f - x }
private fun ease(x: Float) = (1f - cos(x * PI.toFloat())) / 2f

/** Figure paths (read-only after creation). */
private class Figure {
    val body = PathParser().parsePathString("M161 48C179 35 201 40 210 57C240 58 258 80 254 106C278 124 276 153 263 173C278 200 262 226 238 233C231 261 203 271 181 259C161 276 134 272 119 257C91 266 68 249 68 223C40 210 39 180 54 161C38 137 47 109 69 98C65 73 86 53 110 56C123 36 149 36 161 48Z").toPath()
    val left = PathParser().parsePathString("M83 167C56 148 43 161 48 179C51 192 70 201 83 197Z").toPath()
    val right = PathParser().parsePathString("M239 162C261 140 279 149 275 167C272 182 254 193 240 191Z").toPath()
    val feet = PathParser().parsePathString("M114 252C102 270 109 283 124 279L144 261ZM181 260L198 278C210 287 226 270 210 253Z").toPath()
    val shine = PathParser().parsePathString("M81 106C77 82 96 64 116 67C132 47 153 49 163 58C182 46 199 52 204 65").toPath()
    val fill = Brush.radialGradient(listOf(Color(0xFFFFF2B0), Color(0xFFFFE074), Color(0xFFF9C64D), Color(0xFFDDA32B)), Offset(115f, 84f), 240f)
}

private fun DrawScope.drawFigure(f: Figure, mood: Mood, area: Size, origin: Offset, lift: Float, blink: Float, hand: Float, talk: Float) {
    val factor = min(area.width / 330f, area.height / 300f)
    val dx = origin.x + (area.width - 320f * factor) / 2;val dy = origin.y + (area.height - 300f * factor) / 2
    withTransform({ translate(dx, dy + lift * factor);scale(factor, factor * (1f + talk * .035f), Offset.Zero) }) {
        withTransform({ translate(0f, 10f) }) { drawPath(f.body, Color(0x22000000)) }
        drawPath(f.left, Color(0xFFF2BF4B))
        rotate(if (mood == Mood.EXCITED) hand else 0f, Offset(242f, 174f)) { drawPath(f.right, Color(0xFFF8D56B)) }
        drawPath(f.feet, Color(0xFFE5B342))
        drawPath(f.body, f.fill)
        drawPath(f.shine, Color(0x88FFFFFF), style = Stroke(3.5f, cap = StrokeCap.Round))
        for (x in listOf(101f, 218f)) drawOval(Brush.radialGradient(listOf(Color(0xAAEBA764), Color.Transparent), Offset(x, 176f), 22f), Offset(x - 25f, 158f), Size(50f, 36f))
        val face = Color(0xFF343A2D)
        if (mood == Mood.SLEEPY || mood == Mood.QUIET) {
            for (x in listOf(125f, 196f)) drawPath(Path().apply { moveTo(x - 9f, 150f);quadraticBezierTo(x, 160f, x + 9f, 150f) }, face, style = Stroke(6f, cap = StrokeCap.Round))
        } else for (x in listOf(120f, 185f)) {
            val h = 27f * blink
            drawRoundRect(face, Offset(x, 150.5f - h / 2), Size(15f, h), CornerRadius(7.5f))
            if (blink > .5f) drawCircle(Color(0xBBFFFFFF), 2.7f, Offset(x + 6, 143f))
        }
        when {
            talk > .05f -> drawOval(face, Offset(150f, 182f), Size(22f, 8f + talk * 14f))
            mood == Mood.EXCITED -> drawPath(Path().apply { moveTo(141f, 180f);cubicTo(147f, 211f, 177f, 211f, 183f, 180f);close() }, face)
            mood == Mood.THINKING -> drawOval(face, Offset(154f, 180f), Size(14f, 18f))
            else -> drawPath(Path().apply { moveTo(143f, 183f);cubicTo(150f, 197f, 171f, 198f, 180f, 183f) }, face, style = Stroke(6f, cap = StrokeCap.Round))
        }
    }
}

private fun blinkAt(t: Long): Float {
    val x = t % 6200
    return when { x in 4300..4410 -> 1f - .9f * (x - 4300) / 110f;x in 4411..4520 -> .1f + .9f * (x - 4410) / 110f;else -> 1f }
}

/** What Pli is doing, captured on the main thread for the backdrop's render thread. */
internal data class PliPose(val mood: Mood, val speaking: Boolean, val listening: Boolean, val busy: Boolean, val restricted: Boolean, val glow: Color)

internal fun pliPose(state: ConversationState) = PliPose(
    mood = if (state.agentBusy) Mood.THINKING else state.mood, speaking = state.phase == VoicePhase.SPEAKING,
    listening = state.phase == VoicePhase.LISTENING, busy = state.agentBusy, restricted = state.vehicle.uxRestricted, glow = moodColor(state))

/** Pli with a mood-coloured halo, orbit, thinking ring, ground shadow and drifting motes, drawn into [area]. */
internal class PliPainter {
    private val figure = Figure()
    private var level = 0f

    fun DrawScope.paint(pose: PliPose, t: Long, area: Rect, reduce: Boolean) {
        val target = if (pose.listening) MicLevel.value else if (pose.speaking) .5f + .25f * sin(t / 90f) else .08f
        level += (target - level) * .25f
        val c = area.center;val side = area.minDimension
        val r = side * .34f * (if (reduce) 1f else .94f + .08f * ease(pingPong(t, 2600))) * (1f + level * .16f)
        drawOval(Brush.radialGradient(listOf(Color(0x8C000000), Color.Transparent), Offset(c.x, c.y + side * .40f), side * .30f),
            Offset(c.x - side * .30f, c.y + side * .34f), Size(side * .60f, side * .12f))
        drawCircle(Brush.radialGradient(listOf(pose.glow.copy(alpha = .30f + level * .25f), pose.glow.copy(alpha = .08f), Color.Transparent), c, r * 1.6f), r * 1.6f, c)
        val period = if (pose.busy) 2600 else 16000
        val spin = if (reduce) 0f else (t % period) / period.toFloat() * 360f
        rotate(spin, c) {
            drawOval(pose.glow.copy(alpha = .45f), Offset(c.x - r * 1.24f, c.y - r * .4f), Size(r * 2.48f, r * .8f), style = Stroke(2f))
            drawCircle(pose.glow, 7f, Offset(c.x + r * 1.24f, c.y))
            drawCircle(pose.glow.copy(alpha = .25f), 16f, Offset(c.x + r * 1.24f, c.y))
        }
        if (pose.busy) rotate(-spin * 1.6f, c) {
            for (i in 0 until 12) { val a = i * PI.toFloat() / 6f;drawCircle(pose.glow.copy(alpha = .15f + .75f * i / 12f), 6f, Offset(c.x + cos(a) * r * 1.38f, c.y + sin(a) * r * 1.38f)) }
        }
        if (!reduce) for (i in 0 until 22) {
            val phase = ((t / 9000f) + i / 22f) % 1f
            drawCircle(pose.glow.copy(alpha = (sin(phase * PI).toFloat() * .6f).coerceAtLeast(0f)), 1.8f + (i % 3),
                Offset(area.left + area.width * ((i * .618f) % 1f), area.top + area.height * (1f - phase)))
        }
        val lift = if (reduce || pose.restricted) 0f else -4f + 9f * ease(pingPong(t, 2700))
        val tilt = if (pose.busy && !reduce) -3f + 6f * ease(pingPong(t, 1700)) else 0f
        val talk = if (pose.speaking && !reduce) (abs(sin(t / 110f)) * (.4f + level)).coerceIn(0f, 1f) else 0f
        val box = Size(area.width * .7f, area.height * .7f)
        rotate(tilt, Offset(c.x, c.y + box.height * .45f)) {
            drawFigure(figure, pose.mood, box, Offset(area.left + (area.width - box.width) / 2, area.top + (area.height - box.height) / 2), lift,
                if (reduce) 1f else blinkAt(t), if (reduce) 0f else -6f + 18f * pingPong(t, 650), talk)
        }
    }
}

@Composable fun WaveSurface(state: ConversationState, reduce: Boolean, modifier: Modifier) {
    val smooth = remember { floatArrayOf(0f) }
    val phase = state.phase;val quiet = state.quiet
    // the bars move only while Pli listens or speaks; otherwise two posts a second keep them drawn (RenderBudget)
    AnimatedSurface(modifier, "wave", rate = { RenderBudget.waveFps(phase) }) { t ->
        val target = when (phase) { VoicePhase.LISTENING -> .15f + MicLevel.value * .85f;VoicePhase.SPEAKING -> .55f + .2f * sin(t / 120f);else -> .07f }
        smooth[0] += (target - smooth[0]) * .3f
        val bars = 16;val w = size.width / bars
        for (i in 0 until bars) {
            val wave = if (reduce) .5f else (sin(t / 220f + i * .55f) * .5f + .5f)
            val h = size.height * (.12f + smooth[0] * (.35f + .65f * wave) * (1f - abs(i - bars / 2f) / bars))
            drawRoundRect(if (quiet) Color(0xFFA9BC95) else Color(0xFFE9CF8B), Offset(i * w + w * .25f, (size.height - h) / 2), Size(w * .5f, h), CornerRadius(w * .25f))
        }
    }
}

@Composable fun SpinnerSurface(modifier: Modifier) {
    AnimatedSurface(modifier, "spinner", fps = 30) { t ->
        rotate((t % 900) / 900f * 360f) { drawArc(Color(0xFFE9CF8B), 0f, 270f, false, Offset(3f, 3f), Size(size.width - 6f, size.height - 6f), style = Stroke(3f, cap = StrokeCap.Round)) }
    }
}

private fun decode(path: String, maxSide: Int): Bitmap? = runCatching {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(path, bounds)
    var sample = 1
    while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
    BitmapFactory.decodeFile(path, BitmapFactory.Options().apply { inSampleSize = sample })
}.getOrNull()

/** Draws a photo filling [rect] with a slow push-in toward the child's face. */
private fun DrawScope.kenBurns(bitmap: Bitmap, focusX: Float, focusY: Float, rect: Rect, progress: Float, alpha: Float, paint: android.graphics.Paint) {
    val zoom = 1.04f + .12f * progress
    val viewAspect = rect.width / rect.height;val imgAspect = bitmap.width.toFloat() / bitmap.height
    val srcW = (if (imgAspect > viewAspect) bitmap.height * viewAspect else bitmap.width.toFloat()) / zoom
    val srcH = (if (imgAspect > viewAspect) bitmap.height.toFloat() else bitmap.width / viewAspect) / zoom
    val cx = (focusX * bitmap.width).coerceIn(srcW / 2, bitmap.width - srcW / 2)
    val cy = (focusY * bitmap.height).coerceIn(srcH / 2, bitmap.height - srcH / 2)
    val src = android.graphics.Rect((cx - srcW / 2).roundToInt(), (cy - srcH / 2).roundToInt(), (cx + srcW / 2).roundToInt(), (cy + srcH / 2).roundToInt())
    paint.alpha = (alpha * 255).roundToInt().coerceIn(0, 255)
    drawIntoCanvas { it.nativeCanvas.drawBitmap(bitmap, src, android.graphics.RectF(rect.left, rect.top, rect.right, rect.bottom), paint) }
}

private fun newPhotoPaint() = android.graphics.Paint(android.graphics.Paint.FILTER_BITMAP_FLAG or android.graphics.Paint.ANTI_ALIAS_FLAG)

/** Photo cards that fly in, tilt and slowly push in, all on one surface. */
@Composable fun AlbumGridSurface(album: AlbumView, reduce: Boolean, modifier: Modifier) {
    val bitmaps = remember(album.photos) { album.photos.take(6).map { decode(it.path, 900) } }
    val paint = remember { newPhotoPaint() }
    AnimatedSurface(modifier, "album", fps = 30) { t ->  // a slow push-in: 30 posts a second are enough (was 60)
        val n = bitmaps.size.coerceAtLeast(1);val gap = size.width * .025f
        val cardW = (size.width - gap * (n + 1)) / n;val cardH = min(size.height * .9f, cardW * 1.45f)
        bitmaps.forEachIndexed { i, bitmap ->
            if (bitmap == null) return@forEachIndexed
            val appear = if (reduce) 1f else ((t - i * 140L) / 700f).coerceIn(0f, 1f)
            val settle = 1f - (1f - appear) * (1f - appear)
            val left = gap + i * (cardW + gap);val top = (size.height - cardH) / 2 + (1f - settle) * 140f
            rotate((if (i % 2 == 0) -2.4f else 2.1f) * settle, Offset(left + cardW / 2, top + cardH / 2)) {
                val rect = Rect(left, top, left + cardW, top + cardH)
                val clip = Path().apply { addRoundRect(RoundRect(rect, CornerRadius(26f))) }
                clipPath(clip) { kenBurns(bitmap, album.photos[i].focusX, album.photos[i].focusY, rect, if (reduce) 0f else ease(pingPong(t + i * 1500L, 9000 + i * 700)), appear, paint) }
                drawPath(clip, Color(0xFFF4F1E6).copy(alpha = .92f * appear), style = Stroke(4f))
            }
        }
    }
}

/** Story page: Ken Burns photo, cross-fade from the previous page, caption and page dots. */
/** Album photos decoded off the UI thread: decoding all pages at once on it left the story album blank for
 * seconds on a busy head unit (2026-11-14 film audit A6). The controller preloads during the cover. */
object AlbumBitmaps {
    private const val MAX_SIDE = 1400
    private val cache = java.util.concurrent.ConcurrentHashMap<String, Bitmap>()
    fun peek(path: String): Bitmap? = cache[path]
    fun load(path: String): Bitmap? = cache[path] ?: decode(path, MAX_SIDE)?.also { cache[path] = it }
    fun preload(paths: List<String>) { paths.forEach { load(it) } }
}

@Composable fun StorySurface(album: AlbumView, reduce: Boolean, modifier: Modifier) {
    val context = LocalContext.current
    val paths = remember(album.photos) { album.photos.map { it.path } }
    LaunchedEffect(paths, album.index) { // the page on screen first, then the rest
        val order = (listOf(album.index - 1) + paths.indices).filter { it in paths.indices }.distinct()
        kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { order.forEach { AlbumBitmaps.load(paths[it]) } }
    }
    val bitmaps = object : AbstractList<Bitmap?>() {
        override val size get() = paths.size
        override fun get(index: Int) = AlbumBitmaps.peek(paths[index])
    }
    val typeface = remember { ResourcesCompat.getFont(context, R.font.pretendard) }
    val paint = remember { newPhotoPaint() }
    val track = remember { longArrayOf(-1, 0, -1) } // shown index, change time, previous index
    val index = album.index
    AnimatedSurface(modifier, "story", fps = 30) { t ->  // a slow push-in: 30 posts a second are enough (was 60)
        if (track[0] != index.toLong()) { track[2] = track[0];track[0] = index.toLong();track[1] = t }
        val since = t - track[1];val fade = if (reduce) 1f else (since / 800f).coerceIn(0f, 1f)
        val rect = Rect(0f, 0f, size.width, size.height)
        val clip = Path().apply { addRoundRect(RoundRect(rect, CornerRadius(32f))) }
        clipPath(clip) {
            drawRect(Color(0xFF101813))
            val previous = track[2].toInt()
            if (fade < 1f && previous in 1..bitmaps.size) bitmaps[previous - 1]?.let { kenBurns(it, album.photos[previous - 1].focusX, album.photos[previous - 1].focusY, rect, 1f, 1f - fade, paint) }
            if (index in 1..bitmaps.size) bitmaps[index - 1]?.let { kenBurns(it, album.photos[index - 1].focusX, album.photos[index - 1].focusY, rect, if (reduce) 0f else ease((since / 6500f).coerceIn(0f, 1f)), fade, paint) }
            drawRect(Brush.verticalGradient(listOf(Color.Transparent, Color(0xD90B120D)), startY = size.height * .5f, endY = size.height))
            if (index in 1..album.photos.size) drawIntoCanvas { canvas ->
                val native = canvas.nativeCanvas
                val small = TextPaint(TextPaint.ANTI_ALIAS_FLAG).apply { color = 0xFFE9CF8B.toInt();textSize = 22f;letterSpacing = .15f;this.typeface = typeface;alpha = (fade * 255).toInt() }
                native.drawText("$index / ${album.photos.size}", 52f, size.height - 150f, small)
                val big = TextPaint(TextPaint.ANTI_ALIAS_FLAG).apply { color = 0xFFF4F1E6.toInt();textSize = 46f;this.typeface = typeface;alpha = (fade * 255).toInt() }
                val caption = album.photos[index - 1].caption
                val layout = StaticLayout.Builder.obtain(caption, 0, caption.length, big, (size.width * .72f).toInt()).setAlignment(Layout.Alignment.ALIGN_NORMAL).setMaxLines(2).setLineSpacing(8f, 1f).build()
                native.save();native.translate(52f, size.height - 130f + (1f - fade) * 30f);layout.draw(native);native.restore()
                val dots = album.photos.size
                var x = size.width - 52f - (dots - 1) * 22f - 34f
                for (i in 0 until dots) {
                    val w = if (i == index - 1) 34f else 12f
                    drawRoundRect(if (i == index - 1) Color(0xFFE9CF8B) else Color(0x55FFFFFF), Offset(x, size.height - 70f), Size(w, 12f), CornerRadius(6f))
                    x += w + 10f
                }
            }
        }
    }
}
