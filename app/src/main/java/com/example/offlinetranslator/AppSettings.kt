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

    var ocrScript by mutableStateOf(
        OcrScript.entries.getOrElse(prefs.getInt("ocr_script", 0)) { OcrScript.AUTO }
    )
        private set

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
