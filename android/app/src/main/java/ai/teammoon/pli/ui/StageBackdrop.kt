package ai.teammoon.pli.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.CanvasDrawScope
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.layout.boundsInRoot
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.LayoutDirection
import ai.teammoon.pli.domain.ConversationState
import ai.teammoon.pli.domain.RenderBudget
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin

/** Where Compose placed Pli, in root pixels; written on the main thread, read by the backdrop's render thread. */
internal class PliSpot {
    @Volatile var origin: Offset = Offset.Zero
    @Volatile var rect: Rect? = null
}

internal val LocalPliSpot = staticCompositionLocalOf { PliSpot() }

/** Reserves the space Pli flies in; the backdrop paints Pli there, under the glass panels. */
@Composable internal fun PliPlaceholder(modifier: Modifier) {
    val spot = LocalPliSpot.current
    DisposableEffect(spot) { onDispose { spot.rect = null } }
    androidx.compose.foundation.layout.Box(modifier.semantics { contentDescription = "노란 플리 캐릭터" }.onGloballyPositioned { spot.rect = it.boundsInRoot() })
}

/**
 * The whole scene behind the window, on the GPU at the display's vsync: night sky, three aurora
 * curtains, twinkling stars, a shooting star, a road whose lane marks flow with the car's speed,
 * and Pli. Static layers are painted once per size into a bitmap; every frame only moves
 * textured quads and points, so the render thread stays light.
 */
@Composable internal fun StageBackdrop(state: ConversationState, spot: PliSpot, reduce: Boolean, modifier: Modifier) {
    val scene = remember { SkyScene() }
    val pose = pliPose(state)
    val speed = state.vehicle.speedKmh ?: 0f
    val still = reduce || RenderBudget.driving(state.vehicle)
    // 30 posts a second for the moving sky (60 made the display recompose the whole screen twice as often), 12 while the
    // car drives and the sky stands still: only Pli's blink and mouth move then (RenderBudget, 2026-11-15)
    AnimatedSurface(modifier.onGloballyPositioned { spot.origin = it.boundsInRoot().topLeft }, "stage", onTop = false,
                    rate = { RenderBudget.stageFps(still) }) { t ->
        with(scene) { paint(t, speed, still) }
        spot.rect?.let { rect -> with(scene.pli) { paint(pose, t, rect.translate(-spot.origin), reduce) } }  // Pli still blinks and talks
    }
}

private class SkyScene {
    val pli = PliPainter()
    private var backdrop: ImageBitmap? = null
    private var backdropSize = IntSize.Zero
    private val strand = curtainStrand()
    private val tints = listOf(Stage.Aurora, Stage.Violet, Stage.Mint).map { ColorFilter.tint(it, BlendMode.Modulate) }
    private val stars = java.util.Random(11).let { random -> List(3) { List(46) { Offset(random.nextFloat(), random.nextFloat() * .66f) } } }
    private val lane = Path()

    fun DrawScope.paint(t: Long, speedKmh: Float, still: Boolean) {
        drawImage(staticLayer(this))
        val time = if (still) 0L else t
        aurora(time)
        stars(time)
        if (!still) shootingStar(t)
        road(if (still) 0f else t / 1000f * (.08f + speedKmh / 70f))
    }

    private fun staticLayer(scope: DrawScope): ImageBitmap {
        val size = IntSize(scope.size.width.toInt().coerceAtLeast(1), scope.size.height.toInt().coerceAtLeast(1))
        backdrop?.takeIf { backdropSize == size }?.let { return it }
        val image = ImageBitmap(size.width, size.height)
        CanvasDrawScope().draw(scope, LayoutDirection.Ltr, Canvas(image), Size(size.width.toFloat(), size.height.toFloat())) { paintStatic() }
        backdrop = image;backdropSize = size
        return image
    }

    /** Sky, horizon glow, mountains, ground, road bed, far lights and vignette: painted once per size. */
    private fun DrawScope.paintStatic() {
        val w = size.width;val h = size.height;val horizon = h * HORIZON;val vanish = Offset(w * VANISH_X, horizon)
        drawRect(Brush.verticalGradient(0f to Stage.SkyTop, .42f to Stage.SkyMid, .74f to Stage.Horizon, .80f to Color(0xFF3A2A5C), .805f to Color(0xFF0B0F24), 1f to Color(0xFF05070F)))
        scale(1f, .32f, vanish) {
            drawCircle(Brush.radialGradient(listOf(Stage.Ember.copy(alpha = .30f), Stage.Rose.copy(alpha = .10f), Color.Transparent), vanish, w * .55f), w * .55f, vanish)
        }
        ridge(w, horizon, h * .10f, Color(0xFF161B45), 1.7f, .2f)
        ridge(w, horizon, h * .055f, Color(0xFF0E1235), 3.1f, 1.4f)
        val random = java.util.Random(3)
        repeat(26) {
            val x = random.nextFloat() * w;val warm = random.nextBoolean()
            drawCircle((if (warm) Stage.Ember else Stage.Sky).copy(alpha = .35f + random.nextFloat() * .4f), 1.4f + random.nextFloat() * 1.6f, Offset(x, horizon - 2f - random.nextFloat() * 6f))
        }
        val bed = Path().apply { moveTo(vanish.x - 6f, horizon);lineTo(vanish.x + 6f, horizon);lineTo(w * .74f, h);lineTo(-w * .10f, h);close() }
        drawPath(bed, Brush.verticalGradient(listOf(Color(0xFF1A1E3D), Color(0xFF10132A)), horizon, h))
        val edge = Brush.verticalGradient(listOf(Stage.Soft.copy(alpha = .05f), Stage.Soft.copy(alpha = .35f)), horizon, h)
        drawLine(edge, Offset(vanish.x - 6f, horizon), Offset(-w * .10f, h), 3f)
        drawLine(edge, Offset(vanish.x + 6f, horizon), Offset(w * .74f, h), 3f)
        val grain = java.util.Random(7)
        drawPoints(List(1400) { Offset(grain.nextFloat() * w, grain.nextFloat() * h) }, PointMode.Points, Color(0x0FFFFFFF), 1.2f)
        drawRect(Brush.radialGradient(listOf(Color.Transparent, Color(0xAA02030A)), Offset(w / 2, h * .45f), maxOf(w, h) * .78f))
    }

    private fun DrawScope.ridge(w: Float, horizon: Float, height: Float, color: Color, waves: Float, phase: Float) {
        val path = Path().apply {
            moveTo(0f, horizon + 2f)
            for (i in 0..90) {
                val k = i / 90f
                lineTo(k * w, horizon - height * (.45f + .35f * sin(k * PI.toFloat() * waves + phase) + .2f * sin(k * PI.toFloat() * waves * 3.3f + phase * 2)))
            }
            lineTo(w, horizon + 2f);close()
        }
        drawPath(path, color)
    }

    /** Three curtains of tinted, textured strands that sway and breathe. */
    private fun DrawScope.aurora(t: Long) {
        val w = size.width;val h = size.height
        val count = 22;val strandWidth = (w / count * 2.4f).toInt()
        for (ribbon in 0 until 3) {
            for (k in 0 until count) {
                val x = k / (count - 1f)
                val base = h * (.30f + .07f * ribbon) + h * .05f * sin(x * 5.0f + t * .00011f * (ribbon + 1) + ribbon * 1.7f)
                val height = h * (.20f + .09f * sin(t * .00055f + k * .7f + ribbon * 2.1f))
                val alpha = (.16f + .10f * sin(t * .0008f + k * 1.3f + ribbon * 2f)) * (1f - .25f * ribbon)
                drawImage(strand, dstOffset = IntOffset((x * w - strandWidth / 2f).toInt(), (base - height).toInt()),
                    dstSize = IntSize(strandWidth, height.toInt().coerceAtLeast(1)), alpha = alpha.coerceIn(0f, 1f),
                    colorFilter = tints[ribbon], blendMode = BlendMode.Plus)
            }
        }
    }

    private fun DrawScope.stars(t: Long) {
        stars.forEachIndexed { bucket, points ->
            val alpha = .45f + .30f * sin(t / (900f + bucket * 370f) + bucket * 2.1f)
            drawPoints(points.map { Offset(it.x * size.width, it.y * size.height) }, PointMode.Points, Color.White.copy(alpha = alpha),
                2.6f - bucket * .6f, StrokeCap.Round)
        }
    }

    private fun DrawScope.shootingStar(t: Long) {
        val cycle = t % SHOOTING_PERIOD
        if (cycle > SHOOTING_MILLIS) return
        val p = cycle / SHOOTING_MILLIS.toFloat();val seed = (t / SHOOTING_PERIOD).toInt()
        val start = Offset(size.width * (.45f + .4f * ((seed * 37) % 10) / 10f), size.height * (.06f + .1f * ((seed * 13) % 5) / 5f))
        val head = start + Offset(-size.width * .22f * p, size.height * .12f * p)
        val tail = head + Offset(size.width * .07f, -size.height * .038f)
        drawLine(Brush.linearGradient(listOf(Color.White.copy(alpha = .9f * (1f - p)), Color.Transparent), head, tail), head, tail, 2.4f, StrokeCap.Round)
    }

    /** Lane marks flowing toward the viewer; [travel] advances one mark spacing per unit. */
    private fun DrawScope.road(travel: Float) {
        val w = size.width;val h = size.height;val horizon = h * HORIZON
        val vanish = Offset(w * VANISH_X, horizon);val near = Offset(w * .32f, h)
        lane.reset()
        val marks = 7;val shift = travel % 1f
        for (i in 0 until marks) {
            val s0 = (i + shift) / marks;val s1 = s0 + .45f / marks
            if (s1 > 1.02f) continue
            val a = s0 * s0;val b = s1.coerceAtMost(1f).let { it * it } // perspective: far marks crowd toward the horizon
            val pa = vanish + (near - vanish) * a;val pb = vanish + (near - vanish) * b
            val wa = 2f + 16f * a;val wb = 2f + 16f * b
            lane.moveTo(pa.x - wa / 2, pa.y);lane.lineTo(pa.x + wa / 2, pa.y);lane.lineTo(pb.x + wb / 2, pb.y);lane.lineTo(pb.x - wb / 2, pb.y);lane.close()
        }
        drawPath(lane, Brush.verticalGradient(listOf(Stage.Gold.copy(alpha = .15f), Stage.Gold.copy(alpha = .75f)), horizon, h))
        // Reflector posts on both shoulders rush past with the same travel.
        val leftNear = Offset(-w * .10f, h);val rightNear = Offset(w * .74f, h)
        posts.clear()
        for (i in 0 until POSTS) {
            val s = ((i + (travel * 1.6f) % 1f) / POSTS).let { it * it }
            posts += vanish + (leftNear - vanish) * s + Offset(-14f * s, -10f * s)
            posts += vanish + (rightNear - vanish) * s + Offset(14f * s, -10f * s)
        }
        drawPoints(posts, PointMode.Points, Stage.Ember.copy(alpha = .8f), 5f, StrokeCap.Round)
    }

    private val posts = ArrayList<Offset>(POSTS * 2)

    private companion object {
        const val HORIZON = .80f
        const val VANISH_X = .30f
        const val SHOOTING_PERIOD = 11_000L
        const val SHOOTING_MILLIS = 900L
        const val POSTS = 6
    }
}

/** One aurora strand: bright at its foot, fading upward, soft at both sides. Tinted per curtain. */
private fun curtainStrand(): ImageBitmap {
    val width = 48;val height = 256
    val pixels = IntArray(width * height)
    for (y in 0 until height) {
        val v = y / (height - 1f)
        val vertical = if (v < .82f) (v / .82f).let { it * it } else 1f - (v - .82f) / .18f
        for (x in 0 until width) {
            val u = (x - (width - 1) / 2f) / (width / 2f)
            val alpha = (vertical * exp(-u * u * 3f) * 255).toInt().coerceIn(0, 255)
            pixels[y * width + x] = (alpha shl 24) or 0xFFFFFF
        }
    }
    return android.graphics.Bitmap.createBitmap(pixels, width, height, android.graphics.Bitmap.Config.ARGB_8888).asImageBitmap()
}
