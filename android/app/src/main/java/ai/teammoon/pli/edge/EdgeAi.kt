package ai.teammoon.pli.edge

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Client for the Pli edge AI server (speech recognition, agent, family album).
 * The server runs on the vehicle's edge computer; in the emulator that is the host at 10.0.2.2.
 * Every call is bounded; callers fall back to on-device behaviour when it returns null.
 */
object EdgeAi {
    @Volatile var baseUrl = "http://10.0.2.2:8890"
    @Volatile var lastHealthy = 0L;private set
    @Volatile var asrEngine = "";private set
    @Volatile var llmModel = "";private set
    @Volatile var childName: String? = null;private set
    @Volatile var album: EdgeAlbum? = null;private set

    data class Transcript(val text: String, val engine: String, val ms: Int, val rejected: String?)
    data class Step(val id: String, val label: String, val state: String, val detail: String, val ms: Int)
    data class Reply(val action: String, val args: JSONObject, val speech: String, val mood: String, val title: String,
                     val steps: List<Step>, val album: JSONObject?, val model: String, val ms: Int, val card: JSONObject? = null)
    data class EdgePhoto(val id: String, val file: String, val path: String, val focusX: Float, val focusY: Float, val scene: String)
    data class EdgeAlbum(val child: String, val avatarPath: String?, val photos: List<EdgePhoto>)

    private fun open(path: String, method: String, connect: Int, read: Int): HttpURLConnection =
        (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method;connectTimeout = connect;readTimeout = read;useCaches = false
        }

    fun healthy(maxAgeMs: Long = 20_000) = System.currentTimeMillis() - lastHealthy < maxAgeMs

    /** Blocking; call off the main thread. */
    fun checkHealth(): Boolean = runCatching {
        val c = open("/v1/health", "GET", 800, 1500)
        try {
            if (c.responseCode != 200) return false
            val json = JSONObject(c.inputStream.bufferedReader().readText())
            asrEngine = json.optJSONObject("asr")?.optString("engine").orEmpty()
            llmModel = json.optJSONObject("llm")?.optString("model").orEmpty()
            val ok = json.optJSONObject("asr")?.optBoolean("ready") == true
            if (ok) lastHealthy = System.currentTimeMillis()
            ok
        } finally { c.disconnect() }
    }.getOrDefault(false)

    /** One utterance of 16 kHz mono PCM16 in, text out. Blocking. */
    fun transcribe(pcm: ByteArray): Transcript? = runCatching {
        val c = open("/v1/asr", "POST", 800, 6000)
        try {
            c.doOutput = true;c.setRequestProperty("Content-Type", "application/octet-stream");c.setFixedLengthStreamingMode(pcm.size)
            c.outputStream.use { it.write(pcm) }
            if (c.responseCode != 200) return null
            val json = JSONObject(c.inputStream.bufferedReader().readText())
            lastHealthy = System.currentTimeMillis()
            Transcript(json.optString("text"), json.optString("engine"), json.optInt("ms"), json.optString("rejected").takeIf { it.isNotBlank() && it != "null" })
        } finally { c.disconnect() }
    }.onFailure { Log.w("PliEdge", "ASR unavailable: ${it.javaClass.simpleName}") }.getOrNull()

    /** Streams agent events; blocking until the final event. */
    fun converse(text: String, context: JSONObject, onStep: (Step) -> Unit, onSpeech: (String, Int) -> Unit): Reply? = runCatching {
        val c = open("/v1/agent", "POST", 800, 20_000)
        try {
            val body = JSONObject().put("text", text).put("context", context).toString().toByteArray()
            c.doOutput = true;c.setRequestProperty("Content-Type", "application/json");c.setFixedLengthStreamingMode(body.size)
            c.outputStream.use { it.write(body) }
            if (c.responseCode != 200) return null
            var reply: Reply? = null
            c.inputStream.bufferedReader().useLines { lines ->
                for (line in lines) {
                    if (line.isBlank()) continue
                    val e = JSONObject(line)
                    when (e.optString("type")) {
                        "step" -> onStep(step(e))
                        "speech" -> onSpeech(e.optString("text"), e.optInt("index"))
                        "final" -> {
                            val action = e.optJSONObject("action") ?: JSONObject()
                            val steps = e.optJSONArray("steps")?.let { a -> (0 until a.length()).map { step(a.getJSONObject(it)) } }.orEmpty()
                            reply = Reply(action.optString("name", "answer"), action.optJSONObject("args") ?: JSONObject(), e.optString("speech"),
                                e.optString("mood", "HAPPY"), e.optString("title"), steps, e.optJSONObject("album"), e.optString("model"), e.optInt("ms"),
                                e.optJSONObject("card"))
                        }
                        "error" -> return null
                    }
                }
            }
            lastHealthy = System.currentTimeMillis()
            reply
        } finally { c.disconnect() }
    }.onFailure { Log.w("PliEdge", "Agent unavailable: ${it.javaClass.simpleName}") }.getOrNull()

    private fun step(e: JSONObject) = Step(e.optString("id"), e.optString("label"), e.optString("state"), e.optString("detail"), e.optInt("ms"))

    /** Fetches the album manifest and caches photos in the app cache (never in saved data). Blocking. */
    fun loadAlbum(context: Context): EdgeAlbum? = runCatching {
        val c = open("/v1/album", "GET", 800, 3000)
        val json = try {
            if (c.responseCode != 200) return null
            JSONObject(c.inputStream.bufferedReader().readText())
        } finally { c.disconnect() }
        val dir = File(context.cacheDir, "edge-album").apply { mkdirs() }
        fun fetch(file: String): File? {
            if (!Regex("^[0-9a-f]{16}\\.jpg$|^avatar\\.jpg$").matches(file)) return null
            val target = File(dir, file)
            if (target.length() > 0 && file != "avatar.jpg") return target
            val p = open("/v1/album/photo/$file", "GET", 800, 6000)
            try {
                if (p.responseCode != 200) return null
                val tmp = File(dir, "$file.part");p.inputStream.use { input -> tmp.outputStream().use { input.copyTo(it) } }
                check(tmp.renameTo(target));return target
            } finally { p.disconnect() }
        }
        val photos: JSONArray = json.optJSONArray("photos") ?: JSONArray()
        val list = (0 until photos.length()).mapNotNull { i ->
            val p = photos.getJSONObject(i);val file = p.optString("file");val local = fetch(file) ?: return@mapNotNull null
            val focus = p.optJSONArray("focus")
            EdgePhoto(p.optString("id"), file, local.absolutePath, focus?.optDouble(0, .5)?.toFloat() ?: .5f, focus?.optDouble(1, .45)?.toFloat() ?: .45f,
                p.optString("scene").takeIf { it != "null" }.orEmpty())
        }
        val avatar = json.optString("avatar").takeIf { it.isNotBlank() }?.let { fetch(it)?.absolutePath }
        EdgeAlbum(json.optString("child", "친구"), avatar, list).also { album = it;childName = it.child.takeIf { n -> n.isNotBlank() } }
    }.onFailure { Log.w("PliEdge", "Album unavailable: ${it.javaClass.simpleName}") }.getOrNull()
}
