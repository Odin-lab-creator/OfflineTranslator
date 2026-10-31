package com.example.offlinetranslator

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.google.mlkit.nl.translate.TranslateLanguage

enum class ThemeMode(val label: String) {
    DARK("Тёмная: Вальхалла"),
    LIGHT("Светлая: пергамент"),
    SYSTEM("Как в системе")
}

enum class FontSize(val label: String, val sp: Int) {
    SMALL("Маленький", 18),
    MEDIUM("Средний", 24),
    LARGE("Крупный", 30),
    HUGE("Очень крупный", 36)
}

enum class OcrScript(val label: String) {
    AUTO("Авто: по исходному языку"),
    LATIN("Латиница"),
    CYRILLIC("Кириллица"),
    CHINESE("Китайский"),
    JAPANESE("Японский"),
    KOREAN("Корейский")
}

/** Настройки приложения. Один экземпляр на всё приложение, значения сразу сохраняются. */
class AppSettings private constructor(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var themeMode by mutableStateOf(
        ThemeMode.entries.getOrElse(prefs.getInt("theme_v2", 0)) { ThemeMode.DARK }
    )
        private set

    var autoTranslate by mutableStateOf(prefs.getBoolean("auto_translate", true))
        private set

    var haptics by mutableStateOf(prefs.getBoolean("haptics", true))
        private set

    var wifiOnly by mutableStateOf(prefs.getBoolean("wifi_only", false))
        private set

    /** Распознавать сленг и сокращения перед переводом. */
    var slang by mutableStateOf(prefs.getBoolean("slang", true))
        private set

    var ocrScript by mutableStateOf(
        OcrScript.entries.getOrElse(prefs.getInt("ocr_script", 0)) { OcrScript.AUTO }
    )
        private set

    var fontSize by mutableStateOf(
        FontSize.entries.getOrElse(prefs.getInt("font_size", 1)) { FontSize.MEDIUM }
    )
        private set

    /** Недавние пары языков, например en→ru. Новые сверху, не больше четырёх. */
    var recentPairs by mutableStateOf(
        prefs.getString("recent_pairs", null).orEmpty()
            .split(",")
            .mapNotNull { pair ->
                val parts = pair.split(">")
                if (parts.size == 2 && parts[0].isNotBlank() && parts[1].isNotBlank()) parts[0] to parts[1] else null
            }
    )
        private set

    var lastUpdateCheck: Long
        get() = prefs.getLong("last_update_check", 0L)
        set(value) {
            prefs.edit().putLong("last_update_check", value).apply()
        }

    var lastSource: String = prefs.getString("last_source", null) ?: TranslateLanguage.ENGLISH
        set(value) {
            field = value
            prefs.edit().putString("last_source", value).apply()
        }

    var lastTarget: String = prefs.getString("last_target", null) ?: TranslateLanguage.RUSSIAN
        set(value) {
            field = value
            prefs.edit().putString("last_target", value).apply()
        }

    init {
        Slang.load(context)
        Slang.enabled = slang
    }

    fun updateSlang(value: Boolean) {
        slang = value
        Slang.enabled = value
        prefs.edit().putBoolean("slang", value).apply()
    }

    fun updateFontSize(value: FontSize) {
        fontSize = value
        prefs.edit().putInt("font_size", value.ordinal).apply()
    }

    fun rememberPair(source: String, target: String) {
        if (source == target) return
        val pair = source to target
        if (recentPairs.firstOrNull() == pair) return
        recentPairs = (listOf(pair) + recentPairs.filter { it != pair }).take(4)
        prefs.edit()
            .putString("recent_pairs", recentPairs.joinToString(",") { "${it.first}>${it.second}" })
            .apply()
    }

    fun updateTheme(mode: ThemeMode) {
        themeMode = mode
        prefs.edit().putInt("theme_v2", mode.ordinal).apply()
    }

    fun updateAutoTranslate(value: Boolean) {
        autoTranslate = value
        prefs.edit().putBoolean("auto_translate", value).apply()
    }

    fun updateHaptics(value: Boolean) {
        haptics = value
        prefs.edit().putBoolean("haptics", value).apply()
    }

    fun updateWifiOnly(value: Boolean) {
        wifiOnly = value
        prefs.edit().putBoolean("wifi_only", value).apply()
    }

    fun updateOcrScript(value: OcrScript) {
        ocrScript = value
        prefs.edit().putInt("ocr_script", value.ordinal).apply()
    }

    companion object {
        @Volatile
        private var instance: AppSettings? = null

        fun get(context: Context): AppSettings =
            instance ?: synchronized(this) {
                instance ?: AppSettings(context.applicationContext).also { instance = it }
            }

        @Composable
        fun current(): AppSettings = get(LocalContext.current)
    }
}
