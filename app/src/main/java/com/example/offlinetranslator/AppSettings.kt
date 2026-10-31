package com.example.offlinetranslator

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

enum class ThemeMode(val label: String) {
    DARK("Тёмная: Вальхалла"),
    LIGHT("Светлая: пергамент"),
    SYSTEM("Как в системе")
}

class AppSettings(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var themeMode by mutableStateOf(
        ThemeMode.entries.getOrElse(prefs.getInt("theme_v2", 0)) { ThemeMode.DARK }
    )
        private set

    fun updateTheme(mode: ThemeMode) {
        themeMode = mode
        prefs.edit().putInt("theme_v2", mode.ordinal).apply()
    }
}
