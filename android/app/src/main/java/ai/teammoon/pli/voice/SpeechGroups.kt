package ai.teammoon.pli.voice

/**
 * How an answer's sentences are handed to the voice model.
 *
 * On the edge GPU a whole answer takes about 0.2 s to synthesize (measured 2026-11-14: 4 sentences,
 * 176 ms), so it is made in one pass: the model phrases the sentences as one utterance with its own
 * pauses, instead of every sentence restarting its intonation after a silence the app inserts (the
 * 2026-11-14 film review heard that as Pli's voice breaking up). Groups stay under the edge server's
 * text limit; a sentence longer than the limit stays alone.
 */
object SpeechGroups {
    const val EDGE_GROUP_CHARS = 150  // the edge server accepts up to 200 characters per request

    fun forEdge(sentences: List<String>, maxChars: Int = EDGE_GROUP_CHARS): List<List<String>> {
        val groups = mutableListOf<List<String>>()
        var current = mutableListOf<String>()
        var length = 0
        for (sentence in sentences) {
            if (current.isNotEmpty() && length + 1 + sentence.length > maxChars) {
                groups += current
                current = mutableListOf()
            }
            length = if (current.isEmpty()) sentence.length else length + 1 + sentence.length
            current += sentence
        }
        if (current.isNotEmpty()) groups += current
        return groups
    }
}
