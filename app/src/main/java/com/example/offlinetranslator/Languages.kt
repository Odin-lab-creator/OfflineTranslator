package com.example.offlinetranslator

import com.google.mlkit.nl.translate.TranslateLanguage
import java.util.Locale

/** Все языки, которые умеет переводить ML Kit, с названиями по-русски. */
object Languages {
    private val russian = Locale("ru")

    val all: List<String> by lazy {
        TranslateLanguage.getAllLanguages().sortedBy { name(it) }
    }

    val cyrillic = setOf("ru", "uk", "be", "bg", "mk")

    fun name(code: String): String {
        val display = Locale(code).getDisplayLanguage(russian)
        val result = if (display.isBlank() || display.equals(code, ignoreCase = true)) code else display
        return result.replaceFirstChar { it.uppercase() }
    }

    fun locale(code: String): Locale = Locale(code)

    /** Если исходный язык совпал с целевым, подбирает разумный другой целевой. */
    fun otherTarget(source: String, preferred: String): String = when {
        source != preferred -> preferred
        source == TranslateLanguage.RUSSIAN -> TranslateLanguage.ENGLISH
        else -> TranslateLanguage.RUSSIAN
    }
}
