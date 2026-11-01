package com.example.offlinetranslator

import android.content.Context
import androidx.compose.runtime.mutableStateListOf
import java.util.regex.Pattern
import org.json.JSONArray
import org.json.JSONObject

/**
 * Свой глоссарий, как в DeepL: термины, которые всегда переводятся заданным образом.
 * «*» в конце термина означает любое окончание: «вальхалл*» найдёт «Вальхаллы», «Вальхалле».
 */
object Glossary {
    data class Entry(
        val id: Long,
        val source: String,
        val target: String,
        val term: String,
        val translation: String
    )

    val entries = mutableStateListOf<Entry>()

    private var prefs: android.content.SharedPreferences? = null
    private const val START = "(?<![\\p{L}\\p{N}])"
    private const val END = "(?![\\p{L}\\p{N}])"
    private const val FLAGS = Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE

    @Synchronized
    fun load(context: Context) {
        if (prefs != null) return
        val p = context.getSharedPreferences("glossary", Context.MODE_PRIVATE)
        prefs = p
        try {
            val array = JSONArray(p.getString("entries", "[]") ?: "[]")
            for (i in 0 until array.length()) {
                val o = array.getJSONObject(i)
                entries += Entry(
                    o.getLong("id"),
                    o.getString("source"),
                    o.getString("target"),
                    o.getString("term"),
                    o.getString("translation")
                )
            }
        } catch (e: Exception) {
            // повреждённые данные просто пропускаем
        }
    }

    fun add(source: String, target: String, term: String, translation: String) {
        val t = term.trim()
        val r = translation.trim()
        if (t.isEmpty() || r.isEmpty() || t == "*") return
        entries.removeAll { it.source == source && it.target == target && it.term.equals(t, ignoreCase = true) }
        entries.add(0, Entry(System.currentTimeMillis(), source, target, t, r))
        save()
    }

    fun delete(id: Long) {
        entries.removeAll { it.id == id }
        save()
    }

    private fun save() {
        val array = JSONArray()
        entries.forEach {
            array.put(
                JSONObject()
                    .put("id", it.id)
                    .put("source", it.source)
                    .put("target", it.target)
                    .put("term", it.term)
                    .put("translation", it.translation)
            )
        }
        prefs?.edit()?.putString("entries", array.toString())?.apply()
    }

    private fun patternOf(term: String): String {
        val prefix = term.endsWith("*")
        val words = term.removeSuffix("*").trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val body = words.joinToString("\\s+") { Pattern.quote(it) }
        return if (prefix) body + "[\\p{L}\\p{N}]*" else body
    }

    private class Rules(val regex: Regex, val entries: List<Entry>)

    private fun rulesFor(source: String, target: String): Rules? {
        val list = entries.toList()
            .filter { it.source == source && it.target == target }
            .sortedByDescending { it.term.length }
        if (list.isEmpty()) return null
        val alternatives = list.joinToString("|") { "(" + patternOf(it.term) + ")" }
        return try {
            Rules(Pattern.compile("$START(?:$alternatives)$END", FLAGS).toRegex(), list)
        } catch (e: Exception) {
            null
        }
    }

    private fun entryOf(rules: Rules, m: MatchResult): Entry? {
        val index = (1..rules.entries.size).firstOrNull { m.groups[it] != null } ?: return null
        return rules.entries[index - 1]
    }

    private val token = Regex("Z\\s*X\\s*Q\\s*(\\d+)", RegexOption.IGNORE_CASE)

    /**
     * Перевод офлайн-движком с учётом глоссария. Термины заменяются метками, которые
     * переводчик оставляет как есть, а после перевода метки меняются на нужный перевод.
     */
    suspend fun translateWith(text: String, source: String, target: String, translate: suspend (String) -> String): String {
        val rules = rulesFor(source, target) ?: return translate(text)
        val used = mutableListOf<Entry>()
        val masked = rules.regex.replace(text) { m ->
            val entry = entryOf(rules, m) ?: return@replace m.value
            used += entry
            "ZXQ${used.size}"
        }
        if (used.isEmpty()) return translate(text)
        val translated = translate(masked)
        val restoredIds = mutableSetOf<Int>()
        val restored = token.replace(translated) { m ->
            val number = m.groupValues[1].toIntOrNull() ?: return@replace m.value
            val entry = used.getOrNull(number - 1) ?: return@replace m.value
            restoredIds += number
            entry.translation
        }
        if (restoredIds.size == used.size) return restored

        // Метки потерялись: переводим как обычно и подменяем машинный перевод термина.
        var plain = translate(text)
        used.distinct().forEach { entry ->
            val machine = try {
                translate(entry.term.removeSuffix("*")).trim()
            } catch (e: Exception) {
                ""
            }
            if (machine.isNotEmpty()) plain = plain.replace(machine, entry.translation, ignoreCase = true)
        }
        return plain
    }

    /** Для DeepL: экранирует текст как XML и оборачивает термины в неприкосновенные теги. */
    fun maskXml(text: String, source: String, target: String): Pair<String, Boolean> {
        val escaped = escape(text)
        val rules = rulesFor(source, target) ?: return escaped to false
        var used = false
        val masked = rules.regex.replace(escaped) { m ->
            val entry = entryOf(rules, m) ?: return@replace m.value
            used = true
            "<keep>" + escape(entry.translation) + "</keep>"
        }
        return masked to used
    }

    fun unmaskXml(text: String): String =
        text.replace(Regex("</?keep>"), "")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&apos;", "'")
            .replace("&amp;", "&")

    private fun escape(s: String): String =
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
}
