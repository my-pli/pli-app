package ai.teammoon.pli.ui

import android.graphics.Canvas
import android.graphics.PorterDuff
import android.os.Handler
import android.os.HandlerThread
import android.os.Process
import android.util.Log
import android.view.Choreographer
import android.view.SurfaceHolder
import java.util.Locale

/**
 * Paints one SurfaceView on its own thread, on the display's vsync, on the GPU when it can.
 *
 * Measured on the public emulator (2026-11-13): the old loop drew on the guest CPU and slept a
 * fixed 33 ms, so a busy host turned it into 16-25 updates a second with 0.4 s stalls. The
 * emulator renders with the host GPU (`-gpu host`), so a hardware canvas moves the pixel work
 * there; vsync timing keeps every frame's motion time on the display's clock. Animation time is
 * the frame's vsync time, so a late frame lands where it should instead of "catching up".
 * If the GPU canvas rejects an operation, the loop keeps going on the CPU canvas.
 */
internal class FrameLoop(
    private val holder: SurfaceHolder,
    name: String,
    private val fps: () -> Int,  // asked every vsync: a surface may slow down while the car drives (RenderBudget)
    private val render: (Canvas, Long) -> Unit,
) : Choreographer.FrameCallback {
    private val thread = HandlerThread("pli-stage-$name", Process.THREAD_PRIORITY_DISPLAY).apply { start() }
    private val handler = Handler(thread.looper)
    private val stats = FrameStats(name)
    @Volatile private var running = true
    private var hardware = true
    private var start = 0L
    private var last = 0L

    init {
        handler.post { Choreographer.getInstance().postFrameCallback(this) }
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running) return
        Choreographer.getInstance().postFrameCallback(this)
        if (last != 0L && frameTimeNanos - last < NANOS_PER_SECOND / fps().coerceAtLeast(1) - VSYNC_SLACK_NANOS) return
        if (start == 0L) start = frameTimeNanos
        last = frameTimeNanos
        val began = System.nanoTime()
        if (!drawOnce((frameTimeNanos - start) / NANOS_PER_MILLI)) {
            running = false
            return
        }
        stats.record(frameTimeNanos, System.nanoTime() - began, hardware)
    }

    private fun drawOnce(t: Long): Boolean {
        val canvas = lock() ?: return false
        val failure = try {
            canvas.drawColor(0, PorterDuff.Mode.CLEAR)
            render(canvas, t)
            null
        } catch (error: RuntimeException) {
            error
        } finally {
            try { holder.unlockCanvasAndPost(canvas) } catch (_: RuntimeException) { /* surface already gone */ }
        }
        if (failure == null) return true
        if (!hardware) return false
        Log.w(FrameStats.TAG, "GPU canvas rejected a frame; drawing on the CPU canvas", failure)
        hardware = false
        return true
    }

    private fun lock(): Canvas? {
        if (!holder.surface.isValid) return null
        if (hardware) {
            try { return holder.lockHardwareCanvas() } catch (error: RuntimeException) {
                Log.w(FrameStats.TAG, "No GPU canvas for this surface; drawing on the CPU canvas", error)
                hardware = false
            }
        }
        return try { holder.lockCanvas() } catch (_: RuntimeException) { null }
    }

    /** Called from surfaceDestroyed: no frame may touch the surface after this returns. */
    fun stop() {
        running = false
        handler.post { Choreographer.getInstance().removeFrameCallback(this) }
        thread.quitSafely()
        thread.join(JOIN_MILLIS)
    }

    private companion object {
        const val NANOS_PER_SECOND = 1_000_000_000L
        const val NANOS_PER_MILLI = 1_000_000L
        const val VSYNC_SLACK_NANOS = 4_000_000L // a 30 fps surface still draws on every second 60 Hz vsync
        const val JOIN_MILLIS = 600L
    }
}

/** Per-surface pacing, logged as `PliFrame` every few seconds so smoothness is measured, not guessed. */
internal class FrameStats(private val name: String) {
    private val draws = FloatArray(CAPACITY)
    private var count = 0
    private var late = 0
    private var maxGap = 0L
    private var windowStart = 0L
    private var lastFrame = 0L

    fun record(frameNanos: Long, drawNanos: Long, hardware: Boolean) {
        if (windowStart == 0L) windowStart = frameNanos
        if (lastFrame != 0L) {
            val gap = frameNanos - lastFrame
            if (gap > maxGap) maxGap = gap
            if (gap > LATE_NANOS) late++
        }
        lastFrame = frameNanos
        if (count < CAPACITY) draws[count] = drawNanos / 1e6f
        count++
        val span = frameNanos - windowStart
        if (span < REPORT_NANOS) return
        val sorted = draws.copyOf(minOf(count, CAPACITY)).also { it.sort() }
        Log.i(TAG, String.format(Locale.US, "surface=%s canvas=%s fps=%.1f drawP50=%.1fms drawP90=%.1fms gapMax=%dms late=%d",
            name, if (hardware) "gpu" else "cpu", count * 1e9 / span, sorted[sorted.size / 2], sorted[sorted.size * 9 / 10],
            maxGap / 1_000_000, late))
        count = 0; late = 0; maxGap = 0L; windowStart = frameNanos
    }

    companion object {
        const val TAG = "PliFrame"
        private const val CAPACITY = 1024
        private const val LATE_NANOS = 50_000_000L
        private const val REPORT_NANOS = 5_000_000_000L
    }
}
