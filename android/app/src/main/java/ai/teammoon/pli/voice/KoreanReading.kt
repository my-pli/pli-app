package ai.teammoon.pli.voice

/**
 * Spells out numbers the way a Korean speaker reads them, before text reaches the on-device voice
 * (the model reads "2가지" as noise). Counted things use native numerals ("두 가지", "세 문제",
 * "첫 번째"), everything else Sino-Korean ("이십 분", "삼십팔 퍼센트", "칠십 킬로미터").
 */
object KoreanReading {
    private val NATIVE_COUNTERS = listOf(
        "가지", "개", "명", "마리", "살", "시간", "시", "장", "문제", "곳", "권", "잔", "벌", "켤레",
        "군데", "바퀴", "송이", "대", "판", "글자", "단어", "번째", "밤", "줄", "통"
    )
    private val NATIVE_ONES = listOf("", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉")
    private val NATIVE_TENS = listOf("", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔")
    private val SINO_DIGITS = listOf("영", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")
    private val UNITS = listOf(
        Regex("""(\d+(?:\.\d+)?)\s*%""") to "퍼센트",
        Regex("""(\d+(?:\.\d+)?)\s*km/h""", RegexOption.IGNORE_CASE) to "킬로미터",
        Regex("""(\d+(?:\.\d+)?)\s*kWh""") to "킬로와트시",
        Regex("""(\d+(?:\.\d+)?)\s*km""", RegexOption.IGNORE_CASE) to "킬로미터",
        Regex("""(\d+(?:\.\d+)?)\s*(?:℃|°C)""") to "도",
    )
    private val COUNTED = Regex("""(\d+)\s*(${NATIVE_COUNTERS.joinToString("|") { Regex.escape(it) }})""")
    private val CLOCK = Regex("""(\d{1,2}):(\d{2})""")
    private val NUMBER = Regex("""\d+(?:\.\d+)?""")

    fun normalize(text: String): String {
        var out = CLOCK.replace(text) { m ->
            val hour = m.groupValues[1].toInt()
            val minute = m.groupValues[2].toInt()
            native(hour) + " 시" + if (minute == 0) "" else " " + sino(minute.toLong()) + " 분"
        }
        for ((pattern, unit) in UNITS) out = pattern.replace(out) { m -> decimal(m.groupValues[1]) + " " + unit }
        out = COUNTED.replace(out) { m ->
            val n = m.groupValues[1].toLongOrNull() ?: return@replace m.value
            val counter = m.groupValues[2]
            val word = when {
                counter == "번째" && n == 1L -> "첫"
                n in 1..99 -> native(n.toInt())
                else -> sino(n)
            }
            "$word $counter"
        }
        return NUMBER.replace(out) { m -> decimal(m.value) }
    }

    /** Native numeral in its form before a counter ("스무 살", "한 개", "열두 시"). */
    fun native(n: Int): String {
        if (n !in 1..99) return sino(n.toLong())
        val tens = n / 10
        val ones = n % 10
        val ten = if (tens == 2 && ones == 0) "스무" else NATIVE_TENS[tens]
        return ten + NATIVE_ONES[ones]
    }

    fun sino(value: Long): String {
        if (value == 0L) return "영"
        val parts = mutableListOf<String>()
        var rest = value
        for ((size, name) in listOf(100_000_000L to "억", 10_000L to "만", 1L to "")) {
            val group = (rest / size).toInt()
            rest %= size
            if (group == 0) continue
            parts += if (name == "만" && group == 1) "만" else underTenThousand(group) + name
        }
        return parts.joinToString(" ")
    }

    private fun underTenThousand(n: Int): String {
        val sb = StringBuilder()
        for ((place, name) in listOf(1000 to "천", 100 to "백", 10 to "십")) {
            val d = (n / place) % 10
            if (d > 0) sb.append(if (d == 1) name else SINO_DIGITS[d] + name)
        }
        val ones = n % 10
        if (ones > 0) sb.append(SINO_DIGITS[ones])
        return sb.toString()
    }

    private fun decimal(raw: String): String {
        val whole = raw.substringBefore('.').toLongOrNull() ?: return raw
        val fraction = raw.substringAfter('.', "")
        return sino(whole) + if (fraction.isEmpty()) "" else " 점 " + fraction.map { SINO_DIGITS[it - '0'] }.joinToString("")
    }
}
