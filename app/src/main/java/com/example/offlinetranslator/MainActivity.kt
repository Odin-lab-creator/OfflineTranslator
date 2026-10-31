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

enum class Screen { TRANSLATE, HISTORY, SETTINGS, MODELS, CAMERA, SHOW, TOOLS, CONVERSATION, PHRASEBOOK, DOCUMENTS, HANDWRITING, FLASHCARDS }

const val ACTION_PICK_SCREENSHOT = "com.example.offlinetranslator.PICK_SCREENSHOT"
const val ACTION_OPEN_CAMERA = "com.example.offlinetranslator.OPEN_CAMERA"

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
                    var showText by rememberSaveable { mutableStateOf("") }
                    var showLang by rememberSaveable { mutableStateOf("") }
                    var showFrom by rememberSaveable { mutableStateOf(Screen.TRANSLATE.name) }
                    val screen = Screen.valueOf(screenName)
                    fun go(target: Screen) {
                        screenName = target.name
                    }
                    fun show(text: String, lang: String) {
                        showText = text
                        showLang = lang
                        showFrom = screenName
                        go(Screen.SHOW)
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
                            onOpenSettings = { go(Screen.SETTINGS) },
                            onOpenCamera = { go(Screen.CAMERA) },
                            onOpenTools = { go(Screen.TOOLS) },
                            onShow = { show(it, vm.target) }
                        )
                        Screen.SHOW -> {
                            val back = { go(Screen.valueOf(showFrom)) }
                            BackHandler(onBack = back)
                            ShowScreen(
                                text = showText,
                                language = showLang,
                                onBack = back,
                                onSpeak = { vm.speak(showText, showLang) }
                            )
                        }
                        Screen.TOOLS -> {
                            BackHandler { go(Screen.TRANSLATE) }
                            ToolsScreen(
                                tools = listOf(
                                    Tool("Разговор", "Экран на двоих: каждый говорит на своём языке, перевод звучит вслух") {
                                        go(Screen.CONVERSATION)
                                    },
                                    Tool("Разговорник", "Готовые фразы для поездок: такси, отель, кафе, магазин, экстренные случаи") {
                                        go(Screen.PHRASEBOOK)
                                    },
                                    Tool("Камера", "Снимок или живой перевод прямо в видоискателе") {
                                        go(Screen.CAMERA)
                                    },
                                    Tool("Документы", "Перевод PDF и TXT целиком, с сохранением в файл") {
                                        go(Screen.DOCUMENTS)
                                    },
                                    Tool("Рукописный ввод", "Пишите пальцем — удобно для иероглифов и незнакомых алфавитов") {
                                        go(Screen.HANDWRITING)
                                    },
                                    Tool("Карточки", "Учите слова из избранного: сложные повторяются чаще") {
                                        go(Screen.FLASHCARDS)
                                    },
                                    Tool("Языковые модели", "Скачать языки заранее, чтобы переводить без интернета") {
                                        go(Screen.MODELS)
                                    }
                                ),
                                onBack = { go(Screen.TRANSLATE) }
                            )
                        }
                        Screen.DOCUMENTS -> {
                            BackHandler { go(Screen.TOOLS) }
                            DocumentScreen(vm, onBack = { go(Screen.TOOLS) })
                        }
                        Screen.HANDWRITING -> {
                            BackHandler { go(Screen.TOOLS) }
                            HandwritingScreen(
                                vm = vm,
                                settings = settings,
                                onBack = { go(Screen.TOOLS) },
                                onDone = { go(Screen.TRANSLATE) }
                            )
                        }
                        Screen.FLASHCARDS -> {
                            BackHandler { go(Screen.TOOLS) }
                            FlashcardsScreen(vm, onBack = { go(Screen.TOOLS) })
                        }
                        Screen.CONVERSATION -> {
                            BackHandler { go(Screen.TOOLS) }
                            ConversationScreen(vm, settings) { go(Screen.TOOLS) }
                        }
                        Screen.PHRASEBOOK -> {
                            BackHandler { go(Screen.TOOLS) }
                            PhrasebookScreen(
                                vm = vm,
                                settings = settings,
                                onBack = { go(Screen.TOOLS) },
                                onShow = { text, lang -> show(text, lang) }
                            )
                        }
                        Screen.CAMERA -> {
                            BackHandler { go(Screen.TRANSLATE) }
                            CameraScreen(
                                vm = vm,
                                settings = settings,
                                onBack = { go(Screen.TRANSLATE) },
                                onCaptured = { uri ->
                                    go(Screen.TRANSLATE)
                                    vm.translateImage(uri)
                                }
                            )
                        }
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
                                vm = vm,
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
        if (intent.action == ACTION_OPEN_CAMERA) return Incoming.OpenCamera
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
