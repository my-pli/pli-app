package ai.teammoon.pli.voice

import ai.pleos.playground.tts.listener.EventListener
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.util.Log
import java.util.Random
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/**
 * Plays [PliVoiceEngine] speech through an AudioTrack and reports it with the same callbacks the
 * Pleos TTS SDK uses (start → done, or stop), so PliSpeaker's focus, hush and completion rules
 * apply unchanged. Sentence n+1 is synthesized while sentence n plays. If synthesis fails before
 * any sound, the utterance goes to [fallback] (Pleos TTS) instead.
 */
class OnDevicePlayback(
    private val attributes: AudioAttributes,
    private val events: EventListener,
    private val fallback: (String) -> Unit,
) {
    private val player = Executors.newSingleThreadExecutor { Thread({ Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_AUDIO); it.run() }, "PliVoicePlay").apply { isDaemon = true } }
    private val synth = Executors.newSingleThreadExecutor { Thread({ Process.setThreadPriority(Process.THREAD_PRIORITY_DEFAULT); it.run() }, "PliVoiceSynth").apply { isDaemon = true } }
    @Volatile private var token = 0L
    @Volatile private var started = false
    @Volatile private var closed = false
    private val lock = Any()

    fun speak(text: String) {
        val mine = synchronized(lock) { ++token }
        player.execute { play(text, mine) }
    }

    /** Stops at once; emits onStop if sound had started (PliSpeaker waits for that acknowledgement). */
    fun stop() {
        val wasPlaying = synchronized(lock) {
            token++
            started.also { started = false }
        }
        if (wasPlaying) events.onStop()
    }

    fun close() {
        closed = true
        stop()
        player.shutdownNow()
        synth.shutdownNow()
    }

    private fun current(mine: Long) = !closed && token == mine

    private fun play(text: String, mine: Long) {
        val sentences = PliVoiceEngine.chunks(text)
        if (sentences.isEmpty() || !current(mine)) return
        // Edge GPU: the whole answer in one pass (SpeechGroups), so it flows as one utterance. Head unit: one
        // sentence per chunk, so its first sound comes soon on a busy CPU.
        val groups = if (EdgeVoice.reachable()) SpeechGroups.forEdge(sentences) else sentences.map { listOf(it) }
        val chunks = groups.map { it.joinToString(" ") }
        val random = Random(text.hashCode().toLong())
        val rate = PliVoiceEngine.sampleRate
        val began = SystemClock.elapsedRealtime()
        // Every chunk is queued at once on the single synthesis thread, in order: synthesis runs ahead of
        // playback (about twice real time on the head unit), so chunks follow each other without gaps.
        val abandoned = java.util.concurrent.atomic.AtomicBoolean(false)
        val stale = { abandoned.get() || !current(mine) }
        // Edge GPU first (fast and unaffected by the head unit's load), then the head unit's own engine.
        val pending: List<Future<FloatArray>> = groups.map { group ->
            synth.submit<FloatArray> {
                if (stale()) throw java.util.concurrent.CancellationException("VOICE_ABANDONED")
                EdgeVoice.synthesize(group.joinToString(" "), rate) ?: headUnit(group, random, stale, rate)
            }
        }
        // A busy head unit must never leave the family waiting: if the first sentence is not ready in time,
        // this answer is spoken by Pleos TTS instead (the next one tries the own voice again).
        val first = runCatching { pending[0].get(FIRST_WAIT_MS, TimeUnit.MILLISECONDS) }.getOrElse {
            abandoned.set(true)
            pending.forEach { f -> f.cancel(false) }
            Log.w(TAG, "first sentence not ready (${it.javaClass.simpleName}); Pleos TTS speaks this answer")
            if (current(mine)) fallback(text)
            return
        }
        if (!current(mine)) return
        val ready = prebuffer(chunks, pending, first, began, rate)
        val track = buildTrack(rate)
        var written = 0L
        try {
            synchronized(lock) {
                if (!current(mine)) return
                track.play()
                started = true
            }
            Log.i(TAG, "start chunks=${chunks.size} buffered=${ready.size} firstMs=${SystemClock.elapsedRealtime() - began} text=${text.length}")
            events.onStart()
            for (i in chunks.indices) {
                val pcm = ready.getOrNull(i) ?: runCatching { pending[i].get() }.getOrNull() ?: break
                // The model pads each sentence with silence; trimmed, a short breath after "." or "," keeps speech conversational.
                if (i > 0) written += write(track, FloatArray(rate * pauseAfter(chunks[i - 1]) / 1000), mine)
                written += write(track, shaped(trimmed(pcm, rate), rate), mine)
                if (!current(mine)) { pending.forEach { it.cancel(false) }; return }
            }
            drain(track, written, rate, mine)
        } finally {
            runCatching { track.pause(); track.flush(); track.stop() }
            track.release()
        }
        val done = synchronized(lock) { (current(mine) && started).also { if (it) started = false } }
        if (done) events.onDone()
    }

    /**
     * Holds the first sound back just long enough that each next sentence is synthesized before the
     * audio already made runs out: the first sentence's speed (synthesis seconds per character) tells
     * how long the next one will take. Bounded by [PREBUFFER_MAX_MS] so a slow head unit still starts.
     */
    private fun prebuffer(chunks: List<String>, pending: List<Future<FloatArray>>, first: FloatArray, began: Long, rate: Int): List<FloatArray> {
        val ready = mutableListOf(first)
        val firstSeconds = first.size.toDouble() / rate
        val synthPerChar = (SystemClock.elapsedRealtime() - began) / 1000.0 / chunks[0].length.coerceAtLeast(1)
        var buffered = firstSeconds
        val deadline = SystemClock.elapsedRealtime() + PREBUFFER_MAX_MS
        while (ready.size < chunks.size) {
            val nextSynth = synthPerChar * chunks[ready.size].length * 1.15
            if (buffered >= nextSynth) break
            val left = deadline - SystemClock.elapsedRealtime()
            if (left <= 0) break
            val pcm = runCatching { pending[ready.size].get(left, TimeUnit.MILLISECONDS) }.getOrNull() ?: break
            ready += pcm
            buffered += pcm.size.toDouble() / rate + PAUSE_MS / 1000.0
        }
        return ready
    }

    /** The head unit's engine, one sentence at a time; a group the edge could not make is joined with the usual pauses. */
    private fun headUnit(group: List<String>, random: Random, stale: () -> Boolean, rate: Int): FloatArray {
        check(PliVoiceEngine.ready) { "NO_VOICE_ENGINE" }
        if (group.size == 1) return PliVoiceEngine.synthesize(group[0], random, stale)
        val parts = group.mapIndexed { i, sentence ->
            val voice = trimmed(PliVoiceEngine.synthesize(sentence, random, stale), rate)
            if (i == group.lastIndex) voice else voice + FloatArray(rate * pauseAfter(sentence) / 1000)
        }
        return parts.reduce { a, b -> a + b }
    }

    private fun pauseAfter(sentence: String): Int = when (sentence.trimEnd().lastOrNull()) {
        ',' -> COMMA_PAUSE_MS
        '?', '!' -> QUESTION_PAUSE_MS
        else -> PAUSE_MS
    }

    /** Cuts the model's leading/trailing silence (keeping a few milliseconds so consonants are not clipped). */
    private fun trimmed(pcm: FloatArray, rate: Int): FloatArray {
        val peak = pcm.maxOfOrNull { kotlin.math.abs(it) } ?: return pcm
        if (peak <= 0f) return pcm
        val floor = peak * SILENCE_RATIO
        val first = pcm.indexOfFirst { kotlin.math.abs(it) > floor }
        val last = pcm.indexOfLast { kotlin.math.abs(it) > floor }
        if (first < 0 || last <= first) return pcm
        val margin = rate * EDGE_MARGIN_MS / 1000
        return pcm.copyOfRange((first - margin).coerceAtLeast(0), (last + margin).coerceAtMost(pcm.size))
    }

    private fun buildTrack(rate: Int): AudioTrack {
        val format = AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_FLOAT).setSampleRate(rate)
            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build()
        val minimum = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_FLOAT)
        val track = AudioTrack.Builder().setAudioAttributes(attributes).setAudioFormat(format)
            .setTransferMode(AudioTrack.MODE_STREAM).setBufferSizeInBytes(maxOf(minimum, rate * 4 * BUFFER_SECONDS)).build()
        // Android 12+ waits for a full buffer before the first sound; a large buffer (headroom while the next
        // sentence is synthesized) would then never start a short reply.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) runCatching { track.setStartThresholdInFrames(START_FRAMES) }
        return track
    }

    /** Non-blocking writes in small pieces so stop() never waits behind a full buffer. */
    private fun write(track: AudioTrack, pcm: FloatArray, mine: Long): Long {
        var offset = 0
        while (offset < pcm.size && current(mine)) {
            val n = track.write(pcm, offset, minOf(PIECE, pcm.size - offset), AudioTrack.WRITE_NON_BLOCKING)
            if (n < 0) return offset.toLong()
            if (n == 0) SystemClock.sleep(8) else offset += n
        }
        return offset.toLong()
    }

    private fun drain(track: AudioTrack, frames: Long, rate: Int, mine: Long) {
        val deadline = SystemClock.elapsedRealtime() + frames * 1000 / rate + 1500
        while (current(mine) && SystemClock.elapsedRealtime() < deadline) {
            if (track.playbackHeadPosition.toLong() and 0xFFFFFFFFL >= frames) return
            SystemClock.sleep(15)
        }
    }

    /** Short fades and a soft level keep chunk joins click-free. */
    private fun shaped(pcm: FloatArray, rate: Int): FloatArray {
        val fade = minOf(rate / 200, pcm.size / 2)
        val peak = pcm.maxOfOrNull { kotlin.math.abs(it) } ?: 0f
        val gain = if (peak > 0f) minOf(1f, 0.89f / peak) else 1f
        return FloatArray(pcm.size) { i ->
            val edge = minOf(i, pcm.size - 1 - i)
            pcm[i] * gain * if (edge < fade) edge.toFloat() / fade else 1f
        }
    }

    private companion object {
        const val TAG = "PliVoice"
        const val PAUSE_MS = 230
        const val COMMA_PAUSE_MS = 120
        const val QUESTION_PAUSE_MS = 280
        // -46 dB below the peak: the model's padding goes, the soft end of a word stays (0.02 = -34 dB clipped
        // sentence endings, heard as Pli's voice cutting off in the 2026-11-14 film review).
        const val SILENCE_RATIO = 0.005f
        const val EDGE_MARGIN_MS = 60
        const val PIECE = 2048
        const val BUFFER_SECONDS = 2
        const val START_FRAMES = 4096
        const val FIRST_WAIT_MS = 5000L
        const val PREBUFFER_MAX_MS = 4000L
    }
}
