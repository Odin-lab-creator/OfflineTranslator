package com.example.offlinetranslator

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService

fun hasPermission(context: Context, permission: String) =
    ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

/** Окно голосового ввода без интернета (Vosk). */
@Composable
fun OfflineVoiceDialog(lang: String, onResult: (String) -> Unit, onDismiss: () -> Unit) {
    val p = LocalPalette.current
    val scope = rememberCoroutineScope()
    var heard by remember { mutableStateOf("") }
    var partial by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Загружаю модель речи…") }
    var service by remember { mutableStateOf<SpeechService?>(null) }
    var recognizer by remember { mutableStateOf<Recognizer?>(null) }

    DisposableEffect(lang) {
        val job = scope.launch {
            try {
                val model = Voice.model(lang)
                val rec = Recognizer(model, 16000f)
                recognizer = rec
                val s = SpeechService(rec, 16000f)
                service = s
                status = "Говорите: ${Languages.name(lang)}"
                s.startListening(object : RecognitionListener {
                    override fun onPartialResult(hypothesis: String?) {
                        partial = Voice.textOf(hypothesis)
                    }

                    override fun onResult(hypothesis: String?) {
                        val text = Voice.textOf(hypothesis)
                        if (text.isNotEmpty()) heard = (heard + " " + text).trim()
                        partial = ""
                    }

                    override fun onFinalResult(hypothesis: String?) {
                        val text = Voice.textOf(hypothesis)
                        if (text.isNotEmpty() && !heard.endsWith(text)) heard = (heard + " " + text).trim()
                        partial = ""
                    }

                    override fun onError(exception: Exception?) {
                        status = "Ошибка микрофона: ${exception?.localizedMessage ?: ""}"
                    }

                    override fun onTimeout() = Unit
                })
            } catch (e: Exception) {
                status = "Не удалось запустить распознавание: ${e.localizedMessage ?: "ошибка"}"
            }
        }
        onDispose {
            job.cancel()
            service?.stop()
            service?.shutdown()
            recognizer?.close()
        }
    }

    Dialog(onDismissRequest = onDismiss) {
        Column(
            Modifier
                .fillMaxWidth()
                .valhallaCard(p, border = p.gold)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text(status, color = p.muted, fontSize = 13.sp)
            Text(
                (heard + " " + partial).trim().ifEmpty { "…" },
                color = p.text,
                fontFamily = FontFamily.Serif,
                fontSize = 22.sp,
                modifier = Modifier.heightIn(min = 80.dp)
            )
            Text("Без интернета · Vosk", color = p.goldDim, fontSize = 11.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlineGoldButton("Отмена", Modifier.weight(1f), height = 46) { onDismiss() }
                GoldButton("Готово", Modifier.weight(1f)) {
                    val text = (heard + " " + partial).trim()
                    if (text.isNotEmpty()) onResult(text) else onDismiss()
                }
            }
        }
    }
}

/** Экран «Голос офлайн и субтитры». */
@Composable
fun VoiceScreen(vm: TranslatorViewModel, onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val settings = AppSettings.current()
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf("") }
    var captionLang by rememberSaveable { mutableStateOf(if (settings.myLanguage == "en") "de" else "en") }
    var captionsOn by remember { mutableStateOf(LiveCaptionService.running) }
    var canOverlay by remember { mutableStateOf(Build.VERSION.SDK_INT < 23 || Settings.canDrawOverlays(context)) }

    LaunchedEffect(Unit) {
        Voice.init(context)
        try {
            Voice.refreshIndex()
        } catch (e: Exception) {
            if (Voice.available.isEmpty()) message = "Нужен интернет, чтобы загрузить список голосовых моделей"
        }
    }
    LaunchedEffect(Unit) {
        while (true) {
            captionsOn = LiveCaptionService.running
            canOverlay = Build.VERSION.SDK_INT < 23 || Settings.canDrawOverlays(context)
            delay(1000)
        }
    }

    val consent = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val data = result.data
        if (result.resultCode == Activity.RESULT_OK && data != null) {
            ContextCompat.startForegroundService(
                context,
                Intent(context, LiveCaptionService::class.java)
                    .putExtra(LiveCaptionService.EXTRA_CODE, result.resultCode)
                    .putExtra(LiveCaptionService.EXTRA_DATA, data)
                    .putExtra(LiveCaptionService.EXTRA_SOURCE, captionLang)
            )
            message = "Субтитры включены. Откройте видео — перевод появится внизу экрана."
        } else {
            message = "Без разрешения на запись экрана субтитры не работают."
        }
    }
    fun askConsent() {
        val manager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        consent.launch(manager.createScreenCaptureIntent())
    }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
        if (granted[Manifest.permission.RECORD_AUDIO] == true || hasPermission(context, Manifest.permission.RECORD_AUDIO)) {
            askConsent()
        } else {
            message = "Нужно разрешение на запись звука"
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        ScreenHeader("Голос и субтитры", onBack)
        GoldDivider()

        SectionLabel("Живые субтитры")
        Text(
            "Приложение слушает звук видео, подкастов и игр и показывает перевод внизу экрана поверх " +
                "всех приложений. Распознавание и перевод — без интернета. Звонки переводить нельзя, " +
                "а некоторые приложения запрещают захват звука.",
            color = p.text,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )
        if (Build.VERSION.SDK_INT < 29) {
            Text("Нужен Android 10 или новее.", color = p.gold, fontSize = 14.sp)
        } else {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Язык речи", color = p.muted, fontSize = 14.sp, modifier = Modifier.padding(end = 10.dp))
                LanguageButton(captionLang, "Язык речи в видео", Voice.downloaded, Modifier.weight(1f)) { captionLang = it }
            }
            val ready = Voice.isReady(captionLang)
            when {
                captionsOn -> {
                    Text("Субтитры работают", color = p.gold, fontFamily = FontFamily.Serif, fontSize = 18.sp)
                    OutlineGoldButton("Выключить", Modifier.fillMaxWidth(), height = 46) {
                        context.startService(Intent(context, LiveCaptionService::class.java).setAction(LiveCaptionService.ACTION_STOP))
                    }
                }
                !ready -> Text(
                    if (Voice.isAvailable(captionLang)) "Сначала скачайте голосовую модель «${Languages.name(captionLang)}» ниже."
                    else "Для языка «${Languages.name(captionLang)}» нет голосовой модели.",
                    color = p.gold,
                    fontSize = 13.sp
                )
                !canOverlay -> OutlineGoldButton("Разрешить показ поверх приложений", Modifier.fillMaxWidth(), height = 46) {
                    context.startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}")))
                }
                else -> GoldButton("Включить субтитры", Modifier.fillMaxWidth()) {
                    message = ""
                    val needed = buildList {
                        if (!hasPermission(context, Manifest.permission.RECORD_AUDIO)) add(Manifest.permission.RECORD_AUDIO)
                        if (Build.VERSION.SDK_INT >= 33 && !hasPermission(context, Manifest.permission.POST_NOTIFICATIONS)) {
                            add(Manifest.permission.POST_NOTIFICATIONS)
                        }
                    }
                    if (needed.isEmpty()) askConsent() else permissions.launch(needed.toTypedArray())
                }
            }
        }
        if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 13.sp)

        SectionLabel("Голосовой ввод без интернета")
        Column(Modifier.fillMaxWidth().valhallaCard(p)) {
            SwitchRow(
                "Распознавать речь офлайн",
                "Кнопка «Голос» работает без интернета, если модель языка скачана. Иначе — через Google.",
                settings.offlineVoice,
                settings::updateOfflineVoice
            )
        }

        SectionLabel("Голосовые модели")
        val mine = settings.myLanguage
        Voice.available
            .sortedWith(compareByDescending<Voice.Available> { it.lang in Voice.downloaded }.thenByDescending { it.lang == mine }.thenBy { Languages.name(it.lang) })
            .forEach { item ->
                val progress = Voice.progress[item.lang]
                val has = item.lang in Voice.downloaded
                Column(
                    Modifier
                        .fillMaxWidth()
                        .valhallaCard(p, border = if (has) p.goldDim else p.cardBorder)
                        .padding(start = 14.dp, end = 6.dp, top = 6.dp, bottom = 6.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(Languages.name(item.lang), color = p.text, fontSize = 15.sp)
                            Text(formatMb(item.bytes), color = p.muted, fontSize = 12.sp)
                        }
                        when {
                            progress != null -> Text("${(progress * 100).toInt()}%", color = p.gold, fontSize = 14.sp, modifier = Modifier.padding(end = 10.dp))
                            has -> LinkText("Удалить", p.muted, 13.sp) { Voice.delete(item.lang) }
                            else -> LinkText("Скачать", p.gold, 14.sp) {
                                scope.launch {
                                    try {
                                        Voice.download(item.lang)
                                    } catch (e: Exception) {
                                        message = "Не удалось скачать: ${e.localizedMessage ?: "ошибка"}"
                                    }
                                }
                            }
                        }
                    }
                    if (progress != null) {
                        LinearProgressIndicator(
                            progress = { progress },
                            modifier = Modifier.fillMaxWidth().padding(top = 4.dp, end = 8.dp),
                            color = p.gold,
                            trackColor = p.bg
                        )
                    }
                }
            }
        Text("Распознавание речи: Vosk (Alpha Cephei), Apache 2.0.", color = p.muted, fontSize = 11.sp)
    }
}
