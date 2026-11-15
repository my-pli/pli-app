package ai.teammoon.pli.voice

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.os.SystemClock
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.FloatBuffer
import java.nio.LongBuffer
import java.text.Normalizer
import java.util.Random

/**
 * Pli's own voice, synthesized inside the APK on the head unit's CPU — no network and no host
 * computer. Supertonic 3 (Supertone, OpenRAIL-M; packaged by scripts/build-tts-assets.py) runs
 * through ONNX Runtime: text → duration → text embedding → flow-matching denoiser → vocoder.
 * Loaded once per :voice process; Pleos TTS remains the fallback while it loads or if it fails.
 */
object PliVoiceEngine {
    private const val TAG = "PliVoice"
    private const val ASSETS = "tts"
    private const val STEPS = 6  // Supertonic: 5 (fast) … 12 (best); 6 keeps the first sentence quick on a shared head-unit CPU
    private const val SPEED = 1.4f  // same as the edge voice (scripts/edge_voice_server.py): voice F3 at 1.4x since 2026-11-15
    private const val MAX_CHUNK = 60  // a sentence or a clause: a few seconds of speech

    @Volatile var ready = false; private set
    @Volatile var failure: String? = null; private set
    @Volatile var label = ""; private set
    @Volatile var sampleRate = 44100; private set
    private var env: OrtEnvironment? = null
    private var dp: OrtSession? = null
    private var encoder: OrtSession? = null
    private var estimator: OrtSession? = null
    private var vocoder: OrtSession? = null
    private var indexer = LongArray(0)
    private var styleTtl = FloatArray(0)
    private var styleTtlShape = longArrayOf()
    private var styleDp = FloatArray(0)
    private var styleDpShape = longArrayOf()
    private var chunkSize = 0
    private var latentChannels = 0
    private val listeners = mutableListOf<(Boolean) -> Unit>()
    private var loading = false
    private val lock = Any()
    private val inference = Any()

    /** Starts loading in the background; [done] runs on the loader thread (or at once if settled). */
    fun warm(context: Context, done: (Boolean) -> Unit = {}) {
        synchronized(lock) {
            if (ready || failure != null) {
                done(ready)
                return
            }
            listeners += done
            if (loading) return
            loading = true
        }
        val app = context.applicationContext
        Thread({
            val ok = runCatching { load(app) }
                .onFailure { failure = it.javaClass.simpleName + ": " + it.message; Log.w(TAG, "load failed", it) }
                .isSuccess
            val waiting = synchronized(lock) { loading = false; listeners.toList().also { listeners.clear() } }
            waiting.forEach { runCatching { it(ok) } }
        }, "PliVoiceLoad").start()
    }

    private fun load(context: Context) {
        val started = SystemClock.elapsedRealtime()
        val dir = install(context)
        val config = JSONObject(File(dir, "tts.json").readText())
        sampleRate = config.getJSONObject("ae").getInt("sample_rate")
        val compress = config.getJSONObject("ttl").getInt("chunk_compress_factor")
        chunkSize = config.getJSONObject("ae").getInt("base_chunk_size") * compress
        latentChannels = config.getJSONObject("ttl").getInt("latent_dim") * compress
        val raw = JSONArray(File(dir, "unicode_indexer.json").readText())
        indexer = LongArray(raw.length()) { raw.getLong(it) }
        val voice = JSONObject(File(dir, "voice.json").readText())
        voice.getJSONObject("style_ttl").let { styleTtl = flatten(it.getJSONArray("data")); styleTtlShape = dims(it) }
        voice.getJSONObject("style_dp").let { styleDp = flatten(it.getJSONArray("data")); styleDpShape = dims(it) }
        val environment = OrtEnvironment.getEnvironment()
        // Leave cores for the audio mixer, recognizer and UI: speech plays while the next sentence is made,
        // and idle ONNX workers must sleep instead of spin-waiting (spinning starved the mixer: gaps in words).
        val threads = (Runtime.getRuntime().availableProcessors() - 2).coerceIn(2, 4)
        val options = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(threads)
            setInterOpNumThreads(1)
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            addConfigEntry("session.intra_op.allow_spinning", "0")
            addConfigEntry("session.inter_op.allow_spinning", "0")
        }
        env = environment
        dp = environment.createSession(File(dir, "duration_predictor.onnx").path, options)
        encoder = environment.createSession(File(dir, "text_encoder.onnx").path, options)
        estimator = environment.createSession(File(dir, "vector_estimator.onnx").path, options)
        vocoder = environment.createSession(File(dir, "vocoder.onnx").path, options)
        label = "기기 내 음성 · Supertonic " + JSONObject(File(dir, "manifest.json").readText()).optString("voice")
        val warmStart = SystemClock.elapsedRealtime()
        val warmup = synthesize("안녕! 오늘도 같이 가자.", Random(1))
        ready = true
        Log.i(TAG, "ready threads=$threads loadMs=${warmStart - started} warmupMs=${SystemClock.elapsedRealtime() - warmStart} " +
            "warmupAudioMs=${warmup.size * 1000L / sampleRate}")
    }

    /**
     * The voice pack (~200 MB) is not inside the APK: like a navigation map pack it is delivered once —
     * here from the edge computer — into app storage, and every file is checked against the hashes in
     * the manifest the APK carries. ONNX Runtime then opens the files by path.
     */
    private fun install(context: Context): File {
        val manifest = JSONObject(context.assets.open("$ASSETS/manifest.json").use { it.readBytes().decodeToString() })
        val files = manifest.getJSONObject("files")
        val version = files.getJSONObject("vector_estimator.onnx").getString("sha256").take(12)
        val root = File(context.filesDir, "voice")
        val target = File(root, version)
        if (File(target, "manifest.json").exists()) return target
        val staging = File(root, ".staging-$version").apply { deleteRecursively(); mkdirs() }
        for (name in files.keys()) {
            val expected = files.getJSONObject(name).getString("sha256")
            val file = File(staging, name)
            EdgeVoice.download(name, file)
            check(sha256(file) == expected) { "VOICE_PACK_HASH:$name" }
        }
        File(staging, "manifest.json").writeText(manifest.toString())
        root.listFiles()?.filter { it.name != version && it.name != staging.name }?.forEach { it.deleteRecursively() }
        check(staging.renameTo(target)) { "VOICE_INSTALL_FAILED" }
        return target
    }

    private fun sha256(file: File): String {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input -> val buffer = ByteArray(1 shl 20); while (true) { val n = input.read(buffer); if (n < 0) break; digest.update(buffer, 0, n) } }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    /** One piece per sentence (long sentences split at commas): each is a few seconds of speech, so the
     *  next one is ready before the current one ends and the first words start quickly. */
    fun chunks(text: String): List<String> {
        val spoken = KoreanReading.normalize(text).replace(Regex("\\s+"), " ").trim()
        if (spoken.isEmpty()) return emptyList()
        val out = mutableListOf<String>()
        for (sentence in Regex("(?<=[.!?…~])\\s+").split(spoken).map { it.trim() }.filter { it.isNotEmpty() }) {
            if (sentence.length <= MAX_CHUNK) { out += sentence; continue }
            val current = StringBuilder()
            for (piece in sentence.split(Regex("(?<=,)\\s*")).filter { it.isNotBlank() }) {
                if (current.isNotEmpty() && current.length + piece.length + 1 > MAX_CHUNK) { out += current.toString(); current.clear() }
                if (current.isNotEmpty()) current.append(' ')
                current.append(piece)
            }
            if (current.isNotEmpty()) out += current.toString()
        }
        return out
    }

    /** One chunk → mono float PCM at [sampleRate]. Serialised: sessions are shared by all speakers. */
    fun synthesize(text: String, random: Random, cancelled: () -> Boolean = { false }): FloatArray = synchronized(inference) {
        val environment = checkNotNull(env)
        val ids = encode(text)
        val length = ids.size.toLong()
        val textIds = OnnxTensor.createTensor(environment, LongBuffer.wrap(ids), longArrayOf(1, length))
        val textMask = OnnxTensor.createTensor(environment, FloatBuffer.wrap(FloatArray(ids.size) { 1f }), longArrayOf(1, 1, length))
        val ttl = OnnxTensor.createTensor(environment, FloatBuffer.wrap(styleTtl), styleTtlShape)
        val dpStyle = OnnxTensor.createTensor(environment, FloatBuffer.wrap(styleDp), styleDpShape)
        try {
            val seconds = checkNotNull(dp).run(mapOf("text_ids" to textIds, "style_dp" to dpStyle, "text_mask" to textMask)).use {
                (it.get(0) as OnnxTensor).floatBuffer.get(0) / SPEED
            }
            val samples = (seconds * sampleRate).toInt().coerceAtLeast(1)
            val frames = (samples + chunkSize - 1) / chunkSize
            checkNotNull(encoder).run(mapOf("text_ids" to textIds, "style_ttl" to ttl, "text_mask" to textMask)).use { encoded ->
                val latent = denoise(environment, encoded.get(0) as OnnxTensor, ttl, textMask, frames, random, cancelled)
                vocode(environment, latent, frames, samples)
            }
        } finally {
            textIds.close(); textMask.close(); ttl.close(); dpStyle.close()
        }
    }

    private fun denoise(environment: OrtEnvironment, embedding: OnnxTensor, ttl: OnnxTensor, textMask: OnnxTensor, frames: Int, random: Random,
                        cancelled: () -> Boolean): FloatArray {
        var latent = FloatArray(latentChannels * frames) { random.nextGaussian().toFloat() }
        val shape = longArrayOf(1, latentChannels.toLong(), frames.toLong())
        val latentMask = OnnxTensor.createTensor(environment, FloatBuffer.wrap(FloatArray(frames) { 1f }), longArrayOf(1, 1, frames.toLong()))
        val total = OnnxTensor.createTensor(environment, floatArrayOf(STEPS.toFloat()))
        try {
            for (step in 0 until STEPS) {
                if (cancelled()) throw java.util.concurrent.CancellationException("VOICE_ABANDONED")  // stop between steps, not after the whole sentence
                val current = OnnxTensor.createTensor(environment, floatArrayOf(step.toFloat()))
                val noisy = OnnxTensor.createTensor(environment, FloatBuffer.wrap(latent), shape)
                try {
                    checkNotNull(estimator).run(mapOf("noisy_latent" to noisy, "text_emb" to embedding, "style_ttl" to ttl,
                        "latent_mask" to latentMask, "text_mask" to textMask, "current_step" to current, "total_step" to total)).use {
                        val out = (it.get(0) as OnnxTensor).floatBuffer
                        latent = FloatArray(out.remaining()).also { array -> out.get(array) }
                    }
                } finally {
                    current.close(); noisy.close()
                }
            }
        } finally {
            latentMask.close(); total.close()
        }
        return latent
    }

    private fun vocode(environment: OrtEnvironment, latent: FloatArray, frames: Int, samples: Int): FloatArray {
        val input = OnnxTensor.createTensor(environment, FloatBuffer.wrap(latent), longArrayOf(1, latentChannels.toLong(), frames.toLong()))
        try {
            return checkNotNull(vocoder).run(mapOf("latent" to input)).use {
                val wav = (it.get(0) as OnnxTensor).floatBuffer
                FloatArray(minOf(samples, wav.remaining())).also { array -> wav.get(array) }
            }
        } finally {
            input.close()
        }
    }

    /** Supertonic's own text preparation: NFKD (Hangul → jamo), symbol clean-up, language tags. */
    private fun encode(text: String): LongArray {
        var t = Normalizer.normalize(text, Normalizer.Form.NFKD)
        t = t.codePoints().filter { !(it in 0x1F300..0x1FAFF || it in 0x2600..0x27BF || it in 0x1F1E6..0x1F1FF) }
            .toArray().let { String(it, 0, it.size) }
        for ((from, to) in REPLACEMENTS) t = t.replace(from, to)
        t = t.replace(Regex("[♥☆♡©\\\\*]"), "").replace(Regex(" ([,.!?;:'])"), "$1").replace(Regex("\\s+"), " ").trim()
        if (!t.matches(Regex(".*[.!?;:,'\")\\]}…]$"))) t += "."
        val points = "<ko>$t</ko>".codePoints().toArray()
        return LongArray(points.size) { i -> points[i].let { if (it < indexer.size) indexer[it] else 0L } }
    }

    private val REPLACEMENTS = listOf("–" to "-", "—" to "-", "_" to " ", "“" to "\"", "”" to "\"", "‘" to "'", "’" to "'",
        "[" to " ", "]" to " ", "|" to " ", "/" to " ", "#" to " ", "→" to " ", "←" to " ", "·" to ", ")

    private fun dims(style: JSONObject): LongArray = style.getJSONArray("dims").let { a -> LongArray(a.length()) { a.getLong(it) } }

    private fun flatten(array: JSONArray): FloatArray {
        val out = ArrayList<Float>()
        fun walk(node: Any) {
            if (node is JSONArray) for (i in 0 until node.length()) walk(node.get(i)) else out += (node as Number).toFloat()
        }
        walk(array)
        return out.toFloatArray()
    }
}
