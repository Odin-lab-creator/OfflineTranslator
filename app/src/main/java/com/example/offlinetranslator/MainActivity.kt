package com.example.offlinetranslator

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel

enum class Screen { TRANSLATE, HISTORY, SETTINGS, MODELS }

const val ACTION_PICK_SCREENSHOT = "com.example.offlinetranslator.PICK_SCREENSHOT"

class MainActivity : ComponentActivity() {

    private var incoming by mutableStateOf<Incoming?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        if (savedInstanceState == null) incoming = incomingFrom(intent)
        val settings = AppSettings.get(applicationContext)
        setContent {
            val dark = isDarkTheme(settings)
            SideEffect {
                val c = WindowCompat.getInsetsController(window, window.decorView)
                c.isAppearanceLightStatusBars = !dark
                c.isAppearanceLightNavigationBars = !dark
            }
            ValhallaTheme(dark) {
                Surface(Modifier.fillMaxSize(), color = LocalPalette.current.bg) {
                    val vm: TranslatorViewModel = viewModel()
                    var screenName by rememberSaveable { mutableStateOf(Screen.TRANSLATE.name) }
                    val screen = Screen.valueOf(screenName)
                    fun go(target: Screen) {
                        screenName = target.name
                    }

                    LaunchedEffect(incoming) {
                        if (incoming != null) go(Screen.TRANSLATE)
                    }

                    when (screen) {
                        Screen.TRANSLATE -> TranslatorScreen(
                            vm = vm,
                            incoming = incoming,
                            onIncomingHandled = { incoming = null },
                            onOpenHistory = { go(Screen.HISTORY) },
                            onOpenSettings = { go(Screen.SETTINGS) }
                        )
                        Screen.HISTORY -> {
                            BackHandler { go(Screen.TRANSLATE) }
                            HistoryScreen(
                                history = vm.history,
                                onBack = { go(Screen.TRANSLATE) },
                                onOpen = {
                                    vm.restore(it)
                                    go(Screen.TRANSLATE)
                                }
                            )
                        }
                        Screen.SETTINGS -> {
                            BackHandler { go(Screen.TRANSLATE) }
                            SettingsScreen(
                                settings = settings,
                                onBack = { go(Screen.TRANSLATE) },
                                onOpenModels = { go(Screen.MODELS) }
                            )
                        }
                        Screen.MODELS -> {
                            BackHandler { go(Screen.SETTINGS) }
                            ModelsScreen(vm, settings) { go(Screen.SETTINGS) }
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        incomingFrom(intent)?.let { incoming = it }
    }

    private fun incomingFrom(intent: Intent?): Incoming? {
        if (intent == null) return null
        if (intent.action == ACTION_PICK_SCREENSHOT) return Incoming.PickScreenshot
        if (intent.action != Intent.ACTION_SEND) return null
        val type = intent.type ?: return null
        return when {
            type.startsWith("image/") -> {
                val uri = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
                } else {
                    intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
                }
                uri?.let { Incoming.Image(it) }
            }
            type.startsWith("text/") -> {
                intent.getStringExtra(Intent.EXTRA_TEXT)
                    ?.takeIf { it.isNotBlank() }
                    ?.let { Incoming.Shared(it) }
            }
            else -> null
        }
    }
}
