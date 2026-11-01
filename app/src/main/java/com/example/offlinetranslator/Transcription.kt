package com.example.offlinetranslator

import android.os.Build

/**
 * Транскрипция латиницей: пиньинь для китайского, чтение корейского, арабского, греческого,
 * хинди, тайского и других письменностей. Работает офлайн (ICU, Android 10+).
 * Для латиницы и кириллицы не нужна. Японский с иероглифами не поддерживается:
 * у кандзи несколько чтений, и ICU читает их по-китайски.
 */
object Transcription {
    private val cache = HashMap<String, Any?>()

    private fun idFor(lang: String): String? = when (lang) {
        "zh" -> "Han-Latin"
        "ja" -> "Hiragana-Latin; Katakana-Latin"
        "ko" -> "Hangul-Latin"
        "ar", "fa", "ur" -> "Arabic-Latin"
        "he" -> "Hebrew-Latin"
        "el" -> "Greek-Latin"
        "hi", "mr" -> "Devanagari-Latin"
        "bn" -> "Bengali-Latin"
        "gu" -> "Gujarati-Latin"
        "kn" -> "Kannada-Latin"
        "ta" -> "Tamil-Latin"
        "te" -> "Telugu-Latin"
        "th" -> "Thai-Latin"
        "ka" -> "Georgian-Latin"
        else -> null
    }

    private val han = Regex("\\p{IsHan}")
    private val latinOrCyrillic = Regex("^[\\p{IsLatin}\\p{IsCyrillic}\\p{N}\\p{P}\\p{S}\\s]*$")

    /** Нужна ли транскрипция для этого языка вообще. */
    fun supported(lang: String): Boolean = Build.VERSION.SDK_INT >= 29 && idFor(lang) != null

    /** Транскрипция текста или null, если она не нужна или недоступна. */
    fun of(text: String, lang: String): String? {
        if (Build.VERSION.SDK_INT < 29) return null
        val clean = text.trim()
        if (clean.isEmpty() || latinOrCyrillic.matches(clean)) return null
        val id = idFor(lang) ?: return null
        if (lang == "ja" && han.containsMatchIn(clean)) return null
        val transliterator = synchronized(cache) {
            cache.getOrPut(id) {
                try {
                    android.icu.text.Transliterator.getInstance(id)
                } catch (e: Exception) {
                    try {
                        android.icu.text.Transliterator.getInstance("Any-Latin")
                    } catch (e2: Exception) {
                        null
                    }
                }
            }
        } as? android.icu.text.Transliterator ?: return null
        val result = try {
            transliterator.transliterate(clean.take(2000))
        } catch (e: Exception) {
            return null
        }
        return result.replace(Regex("[ \\t]+"), " ").trim().takeIf { it.isNotEmpty() && it != clean }
    }
}
