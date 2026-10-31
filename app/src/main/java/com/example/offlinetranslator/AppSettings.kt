package com.example.offlinetranslator

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

enum class ThemeMode(val label: String) {
    SYSTEM("Как в системе"),
    LIGHT("Светлая"),
    DARK("Тёмная")
}

class AppSettings(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var themeMode by mutableStateOf(
        ThemeMode.entries.getOrElse(prefs.getInt("theme", 0)) { ThemeMode.SYSTEM }
    )
        private set

    var dynamicColor by mutableStateOf(prefs.getBoolean("dynamic", true))
        private set

    fun updateTheme(mode: ThemeMode) {
        themeMode = mode
        prefs.edit().putInt("theme", mode.ordinal).apply()
    }

    fun updateDynamic(value: Boolean) {
        dynamicColor = value
        prefs.edit().putBoolean("dynamic", value).apply()
    }
}
