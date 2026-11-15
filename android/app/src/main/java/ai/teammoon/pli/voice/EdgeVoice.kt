package ai.teammoon.pli.voice

import android.os.SystemClock
import android.util.Log
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Pli's voice synthesized on the vehicle edge computer's GPU (scripts/edge_voice_server.py; in the
 * emulator the host is 10.0.2.2). Same model, voice and number reading as [PliVoiceEngine], so the
 * family hears one voice whichever side made a sentence. Every call is bounded; a failure marks the
 * edge unusable for a while and the head unit synthesizes instead.
 */
object EdgeVoice {
    private const val TAG = "PliVoice"
    private const val BASE = "http://10.0.2.2:8892"
    private const val HEALTH_TTL_MS = 15_000L
    private const val RETRY_AFTER_FAILURE_MS = 20_000L

    @Volatile private var healthyUntil = 0L
    @Volatile private var blockedUntil = 0L
    @Volatile var provider = ""; private set

    /** Non-blocking: whether the last health check (or synthesis) succeeded recently. */
    fun usable(): Boolean = SystemClock.elapsedRealtime() < healthyUntil

    /** Non-blocking: false only for a while after a failed call, when the head unit synthesizes instead. */
    fun reachable(): Boolean = SystemClock.elapsedRealtime() >= blockedUntil

    /** Blocking (call off the main thread): refreshes [usable]. */
    fun check(): Boolean {
        if (SystemClock.elapsedRealtime() < blockedUntil) return false
        return runCatching {
            val c = (URL("$BASE/v1/voice/health").openConnection() as HttpURLConnection).apply { connectTimeout = 600; readTimeout = 1200 }
            try {
                val body = JSONObject(c.inputStream.bufferedReader().readText())
                check(c.responseCode == 200 && body.optBoolean("ok"))
                provider = body.optString("provider")
            } finally { c.disconnect() }
            healthyUntil = SystemClock.elapsedRealtime() + HEALTH_TTL_MS
            true
        }.getOrElse { healthyUntil = 0L; blockedUntil = SystemClock.elapsedRealtime() + RETRY_AFTER_FAILURE_MS; false }
    }

    /** Blocking: one voice-pack file from the edge into [target] (streamed; large files take a few seconds). */
    fun download(name: String, target: java.io.File) {
        val c = (URL("$BASE/v1/voice/pack/$name").openConnection() as HttpURLConnection).apply { connectTimeout = 2000; readTimeout = 30_000 }
        try {
            check(c.responseCode == 200) { "VOICE_PACK_HTTP_${c.responseCode}:$name" }
            c.inputStream.use { input -> target.outputStream().use { input.copyTo(it, 1 shl 20) } }
        } finally { c.disconnect() }
    }

    /** One sentence → float PCM at [rate] Hz, or null when the edge cannot answer in time. */
    fun synthesize(text: String, rate: Int): FloatArray? {
        if (SystemClock.elapsedRealtime() < blockedUntil) return null
        val started = SystemClock.elapsedRealtime()
        return runCatching {
            val c = (URL("$BASE/v1/voice").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"; doOutput = true; connectTimeout = 800; readTimeout = 4000
                setRequestProperty("Content-Type", "application/json")
            }
            try {
                c.outputStream.use { it.write(JSONObject().put("text", text).toString().toByteArray()) }
                check(c.responseCode == 200) { "HTTP ${c.responseCode}" }
                check(c.getHeaderField("X-Sample-Rate")?.toIntOrNull() == rate) { "RATE" }
                val bytes = c.inputStream.use { it.readBytes() }
                val shorts = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
                FloatArray(shorts.remaining()) { shorts.get(it) / 32768f }.also {
                    healthyUntil = SystemClock.elapsedRealtime() + HEALTH_TTL_MS
                    Log.i(TAG, "edge sentence ms=${SystemClock.elapsedRealtime() - started} audioMs=${it.size * 1000L / rate} via=$provider")
                }
            } finally { c.disconnect() }
        }.getOrElse {
            Log.w(TAG, "edge voice unavailable: ${it.javaClass.simpleName} ${it.message}")
            healthyUntil = 0L; blockedUntil = SystemClock.elapsedRealtime() + RETRY_AFTER_FAILURE_MS
            null
        }
    }
}
