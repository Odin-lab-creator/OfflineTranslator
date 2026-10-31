package com.example.offlinetranslator

import android.content.Context
import java.util.regex.Pattern

/**
 * Распознавание сленга, сокращений и идиом (английский и русский), полностью офлайн.
 * Перед переводом сленг заменяется обычными словами, чтобы переводчик понял смысл,
 * а пользователю показывается, что означает каждое найденное выражение.
 * Словари лежат в assets/slang/*.tsv: term, pattern, replacement, meaning.
 */
object Slang {
    class Entry(
        val language: String,
        val term: String,
        val pattern: String,
        val replacement: String,
        val meaning: String
    )

    class Found(val original: String, val entry: Entry)

    class Result(val text: String, val found: List<Found>)

    private class Dictionary(
        val entries: List<Entry>,
        val specials: List<Pair<Regex, Entry>>,
        val combined: Regex?,
        val combinedEntries: List<Entry>
    )

    /** Включено ли распознавание (настройка). */
    @Volatile
    var enabled: Boolean = true

    private val dictionaries = mutableMapOf<String, Dictionary>()

    private const val START = "(?<![\\p{L}\\p{N}'’-])"
    private const val END = "(?![\\p{L}\\p{N}'’-])"
    private const val FLAGS = Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE

    @Synchronized
    fun load(context: Context) {
        if (dictionaries.isNotEmpty()) return
        for (language in listOf("en", "ru")) {
            val entries = try {
                context.assets.open("slang/$language.tsv").bufferedReader().useLines { lines ->
                    lines.filter { it.isNotBlank() && !it.startsWith("#") }
                        .mapNotNull { line ->
                            val c = line.split('\t')
                            if (c.size < 4) null else Entry(language, c[0], c[1], c[2], c[3])
                        }
                        .toList()
                }
            } catch (e: Exception) {
                emptyList()
            }
            dictionaries[language] = build(entries)
        }
    }

    private fun regexSource(entry: Entry): String =
        if (entry.pattern == "-") Pattern.quote(entry.term) else entry.pattern

    private fun isSpecial(entry: Entry): Boolean =
        entry.replacement.contains("$1") || entry.pattern.startsWith("^")

    private fun build(entries: List<Entry>): Dictionary {
        val specials = entries.filter(::isSpecial).mapNotNull { entry ->
            val source = regexSource(entry)
            val full = if (source.startsWith("^")) source else START + source + END
            try {
                Pattern.compile(full, FLAGS).toRegex() to entry
            } catch (e: Exception) {
                null
            }
        }
        val regular = entries.filterNot(::isSpecial)
            .filter { e ->
                try {
                    Pattern.compile(regexSource(e), FLAGS)
                    true
                } catch (ex: Exception) {
                    false
                }
            }
            .sortedByDescending { regexSource(it).length }
        val combined = if (regular.isEmpty()) null else {
            val alternatives = regular.joinToString("|") { "(" + regexSource(it) + ")" }
            Pattern.compile("$START(?:$alternatives)$END", FLAGS).toRegex()
        }
        return Dictionary(entries, specials, combined, regular)
    }

    /** Все записи словаря для экрана «Словарь сленга». */
    fun entries(language: String): List<Entry> = dictionaries[language]?.entries.orEmpty()

    /** Заменяет сленг обычными словами и возвращает найденные выражения. */
    fun normalize(text: String, language: String): Result {
        val dictionary = dictionaries[language] ?: return Result(text, emptyList())
        val found = mutableListOf<Found>()
        var current = text
        for ((regex, entry) in dictionary.specials) {
            current = regex.replace(current) { m ->
                found += Found(m.value.trim(), entry)
                val group = if (entry.replacement.contains("$1")) m.groups[1]?.value.orEmpty() else ""
                matchCase(m.value, entry.replacement.replace("$1", group))
            }
        }
        val combined = dictionary.combined
        if (combined != null) {
            current = combined.replace(current) { m ->
                val index = (1..dictionary.combinedEntries.size).firstOrNull { m.groups[it] != null }
                if (index == null) {
                    m.value
                } else {
                    val entry = dictionary.combinedEntries[index - 1]
                    found += Found(m.value, entry)
                    if (entry.replacement == "=") m.value else matchCase(m.value, entry.replacement)
                }
            }
        }
        return Result(current, found.distinctBy { it.entry.term.lowercase() + "|" + it.entry.meaning })
    }

    private fun matchCase(original: String, replacement: String): String {
        val first = original.trimStart().firstOrNull() ?: return replacement
        return if (first.isUpperCase()) replacement.replaceFirstChar { it.uppercase() } else replacement
    }
}
