package com.example.offlinetranslator

import android.content.ActivityNotFoundException
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.mlkit.nl.translate.TranslateLanguage
import kotlinx.coroutines.launch

/**
 * Режим разговора: экран делится пополам. Верхняя половина повёрнута к собеседнику.
 * Каждый говорит на своём языке, перевод появляется у другого и звучит вслух.
 */
@Composable
fun ConversationScreen(vm: TranslatorViewModel, settings: AppSettings, onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val view = LocalView.current
    val scope = rememberCoroutineScope()

    val defaultMine = if (vm.source == TranslateLanguage.RUSSIAN || vm.target == TranslateLanguage.RUSSIAN) {
        TranslateLanguage.RUSSIAN
    } else vm.source
    val defaultTheirs = when {
        defaultMine == vm.source -> vm.target
        else -> vm.source
    }.let { if (it == defaultMine) Languages.otherTarget(defaultMine, it) else it }

    var myLang by rememberSaveable { mutableStateOf(defaultMine) }
    var theirLang by rememberSaveable { mutableStateOf(defaultTheirs) }
    var myText by rememberSaveable { mutableStateOf("") }
    var theirText by rememberSaveable { mutableStateOf("") }
    var myHint by rememberSaveable { mutableStateOf("Нажмите «Говорить» и скажите фразу") }
    var theirHint by rememberSaveable { mutableStateOf("Press the button and speak") }
    var busy by remember { mutableStateOf(false) }
    var speakAloud by rememberSaveable { mutableStateOf(true) }
    var listening by remember { mutableStateOf(0) } // 1 — я, 2 — собеседник
    var typing by remember { mutableStateOf(0) }
    var typed by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }

    DisposableEffect(Unit) {
        view.keepScreenOn = true
        onDispose { view.keepScreenOn = false }
    }

    fun handle(fromMe: Boolean, text: String) {
        val clean = text.trim()
        if (clean.isEmpty()) return
        val src = if (fromMe) myLang else theirLang
        val dst = if (fromMe) theirLang else myLang
        if (fromMe) {
            myText = clean
            myHint = "Вы сказали"
        } else {
            theirText = clean
            theirHint = "Said"
        }
        scope.launch {
            busy = true
            error = ""
            try {
                val result = TranslationEngine.translate(src, dst, clean, settings.wifiOnly)
                if (fromMe) {
                    theirText = result
                    theirHint = Languages.name(dst)
                } else {
                    myText = result
                    myHint = "Собеседник говорит"
                }
                vm.history.add(src, dst, clean, result)
                if (speakAloud) vm.speak(result, dst, toggle = false)
            } catch (e: Exception) {
                error = "Не удалось перевести: ${e.localizedMessage ?: "ошибка"}. " +
                    "Если модель ещё не скачана, нужен интернет."
            } finally {
                busy = false
            }
        }
    }

    val speech = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val heard = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        val side = listening
        listening = 0
        if (heard != null) handle(fromMe = side == 1, text = heard)
    }

    fun listen(fromMe: Boolean) {
        val lang = if (fromMe) myLang else theirLang
        listening = if (fromMe) 1 else 2
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, Languages.locale(lang).toLanguageTag())
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            .putExtra(RecognizerIntent.EXTRA_PROMPT, Languages.name(lang))
        try {
            speech.launch(intent)
        } catch (e: ActivityNotFoundException) {
            listening = 0
            error = "На телефоне нет службы распознавания речи. Можно писать текстом: «Написать»."
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
    ) {
        // Половина собеседника (перевёрнута)
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .rotate(180f)
        ) {
            ConversationHalf(
                language = theirLang,
                onLanguage = { theirLang = it },
                hint = theirHint,
                text = theirText,
                speakLabel = "Speak",
                writeLabel = "Type",
                busy = busy,
                onSpeak = { listen(fromMe = false) },
                onWrite = {
                    typed = ""
                    typing = 2
                },
                downloaded = vm.downloaded
            )
        }

        Column(
            Modifier
                .fillMaxWidth()
                .background(p.card)
                .padding(horizontal = 12.dp, vertical = 4.dp)
        ) {
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth(), color = p.gold, trackColor = p.bg)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                LinkText("← Выйти", p.gold, 14.sp, onClick = onBack)
                LinkText(if (speakAloud) "🔊 Озвучка: вкл" else "Озвучка: выкл", p.gold, 14.sp) {
                    speakAloud = !speakAloud
                }
                LinkText("⇅", p.gold, 20.sp) {
                    val l = myLang
                    myLang = theirLang
                    theirLang = l
                }
            }
            if (error.isNotEmpty()) Text(error, color = p.muted, fontSize = 12.sp)
        }

        // Моя половина
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            ConversationHalf(
                language = myLang,
                onLanguage = { myLang = it },
                hint = myHint,
                text = myText,
                speakLabel = "Говорить",
                writeLabel = "Написать",
                busy = busy,
                onSpeak = { listen(fromMe = true) },
                onWrite = {
                    typed = ""
                    typing = 1
                },
                downloaded = vm.downloaded
            )
        }
    }

    if (typing != 0) {
        val fromMe = typing == 1
        AlertDialog(
            onDismissRequest = { typing = 0 },
            title = {
                Text(
                    if (fromMe) "Ваша фраза" else "Фраза собеседника",
                    color = p.gold,
                    fontFamily = FontFamily.Serif
                )
            },
            text = {
                TextField(
                    value = typed,
                    onValueChange = { typed = it },
                    placeholder = { Text(Languages.name(if (fromMe) myLang else theirLang)) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = TextFieldDefaults.colors(
                        focusedTextColor = p.text,
                        unfocusedTextColor = p.text,
                        focusedContainerColor = p.bg,
                        unfocusedContainerColor = p.bg,
                        cursorColor = p.gold,
                        focusedIndicatorColor = p.gold,
                        unfocusedIndicatorColor = p.goldDim
                    )
                )
            },
            confirmButton = {
                LinkText("Перевести", p.gold, 15.sp) {
                    typing = 0
                    handle(fromMe, typed)
                }
            },
            dismissButton = { LinkText("Отмена", p.muted, 15.sp) { typing = 0 } },
            containerColor = p.card
        )
    }
}

@Composable
private fun ConversationHalf(
    language: String,
    onLanguage: (String) -> Unit,
    hint: String,
    text: String,
    speakLabel: String,
    writeLabel: String,
    busy: Boolean,
    onSpeak: () -> Unit,
    onWrite: () -> Unit,
    downloaded: Set<String>
) {
    val p = LocalPalette.current
    Column(
        Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        LanguageButton(language, "Язык", downloaded, Modifier.fillMaxWidth(), onLanguage)
        HalfText(hint, text)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            IconLabelButton(ValhallaIcons.Mic, speakLabel, Modifier.weight(1f), !busy, onSpeak)
            OutlineGoldButton(writeLabel, height = 46, enabled = !busy, onClick = onWrite)
        }
    }
}

@Composable
private fun ColumnScope.HalfText(hint: String, text: String) {
    val p = LocalPalette.current
    Column(
        Modifier
            .weight(1f)
            .fillMaxWidth()
            .valhallaCard(p)
            .verticalScroll(rememberScrollState())
            .padding(14.dp),
        verticalArrangement = Arrangement.Center
    ) {
        Text(hint.uppercase(), color = p.muted, fontSize = 11.sp, letterSpacing = 2.sp)
        Text(
            text,
            color = if (text.isEmpty()) Color.Transparent else p.result,
            fontFamily = FontFamily.Serif,
            fontSize = if (text.length < 80) 26.sp else 20.sp,
            lineHeight = if (text.length < 80) 34.sp else 27.sp,
            textAlign = TextAlign.Start,
            modifier = Modifier.padding(top = 6.dp)
        )
    }
}
