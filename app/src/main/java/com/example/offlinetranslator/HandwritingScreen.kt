package com.example.offlinetranslator

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.vision.digitalink.DigitalInkRecognition
import com.google.mlkit.vision.digitalink.DigitalInkRecognitionModel
import com.google.mlkit.vision.digitalink.DigitalInkRecognitionModelIdentifier
import com.google.mlkit.vision.digitalink.DigitalInkRecognizerOptions
import com.google.mlkit.vision.digitalink.Ink
import kotlinx.coroutines.delay
import kotlinx.coroutines.tasks.await

private class TimedPoint(val offset: Offset, val time: Long)

/** Подбирает модель рукописного ввода для языка (ML Kit Digital Ink). */
private fun inkModelFor(code: String): DigitalInkRecognitionModel? {
    val tags = when (code) {
        "zh" -> listOf("zh-Hani-CN", "zh-CN", "zh")
        "ja" -> listOf("ja", "ja-JP")
        "ko" -> listOf("ko", "ko-KR")
        "en" -> listOf("en-US", "en")
        else -> listOf(code, "$code-${code.uppercase()}")
    }
    for (tag in tags) {
        val id = try {
            DigitalInkRecognitionModelIdentifier.fromLanguageTag(tag)
        } catch (e: Exception) {
            null
        }
        if (id != null) return DigitalInkRecognitionModel.builder(id).build()
    }
    return null
}

/**
 * Рукописный ввод: пишете пальцем, текст распознаётся и переводится.
 * Особенно полезно для иероглифов.
 */
@Composable
fun HandwritingScreen(vm: TranslatorViewModel, settings: AppSettings, onBack: () -> Unit, onDone: () -> Unit) {
    val p = LocalPalette.current
    var language by rememberSaveable { mutableStateOf(vm.source) }
    var buffer by rememberSaveable { mutableStateOf("") }
    val strokes = remember { mutableStateListOf<List<TimedPoint>>() }
    var current by remember { mutableStateOf<List<TimedPoint>>(emptyList()) }
    var candidates by remember { mutableStateOf<List<String>>(emptyList()) }
    var status by remember { mutableStateOf("") }
    var ready by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var version by remember { mutableIntStateOf(0) }
    val model = remember(language) { inkModelFor(language) }
    val recognizer = remember(model) {
        model?.let { DigitalInkRecognition.getClient(DigitalInkRecognizerOptions.builder(it).build()) }
    }

    DisposableEffect(recognizer) {
        onDispose { recognizer?.close() }
    }

    // Модель для языка скачивается один раз (~20 МБ).
    LaunchedEffect(model) {
        ready = false
        candidates = emptyList()
        if (model == null) {
            status = "Для языка «${Languages.name(language)}» нет рукописной модели. Выберите другой язык."
            return@LaunchedEffect
        }
        val manager = RemoteModelManager.getInstance()
        try {
            if (!manager.isModelDownloaded(model).await()) {
                loading = true
                status = "Скачиваю модель рукописного ввода (один раз, около 20 МБ)…"
                val conditions = DownloadConditions.Builder().apply { if (settings.wifiOnly) requireWifi() }.build()
                manager.download(model, conditions).await()
            }
            status = "Пишите в рамке пальцем"
            ready = true
        } catch (e: Exception) {
            status = "Не удалось скачать модель: ${e.localizedMessage ?: "нужен интернет"}"
        } finally {
            loading = false
        }
    }

    // Распознаём, когда пользователь сделал паузу.
    LaunchedEffect(version, ready) {
        if (!ready || strokes.isEmpty() || recognizer == null) return@LaunchedEffect
        delay(700)
        val builder = Ink.builder()
        strokes.forEach { stroke ->
            val sb = Ink.Stroke.builder()
            stroke.forEach { sb.addPoint(Ink.Point.create(it.offset.x, it.offset.y, it.time)) }
            builder.addStroke(sb.build())
        }
        candidates = try {
            recognizer.recognize(builder.build()).await().candidates.map { it.text }.distinct().take(6)
        } catch (e: Exception) {
            emptyList()
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Рукописный ввод", onBack)
        GoldDivider()
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Язык письма:", color = p.text, fontSize = 15.sp)
            LanguageButton(
                language,
                "Язык письма",
                vm.downloaded,
                Modifier
                    .padding(start = 10.dp)
                    .weight(1f)
            ) {
                language = it
                strokes.clear()
                version++
            }
        }
        if (loading) LinearProgressIndicator(Modifier.fillMaxWidth(), color = p.gold, trackColor = p.card)
        if (status.isNotEmpty()) Text(status, color = p.muted, fontSize = 13.sp)

        Box(
            Modifier
                .fillMaxWidth()
                .heightIn(min = 120.dp)
                .valhallaCard(p)
                .padding(14.dp)
        ) {
            Text(
                buffer.ifEmpty { "Здесь появится написанный текст" },
                color = if (buffer.isEmpty()) p.muted else p.result,
                fontFamily = FontFamily.Serif,
                fontSize = 24.sp,
                lineHeight = 31.sp
            )
        }

        Row(
            Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            candidates.forEach { candidate ->
                OutlineGoldButton(candidate, height = 40) {
                    buffer += candidate
                    strokes.clear()
                    candidates = emptyList()
                }
            }
        }

        Canvas(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .valhallaCard(p, border = p.goldDim)
                .pointerInput(ready) {
                    if (!ready) return@pointerInput
                    detectDragGestures(
                        onDragStart = { start ->
                            current = listOf(TimedPoint(start, System.currentTimeMillis()))
                        },
                        onDrag = { change, _ ->
                            current = current + TimedPoint(change.position, System.currentTimeMillis())
                        },
                        onDragEnd = {
                            if (current.size > 1) strokes.add(current)
                            current = emptyList()
                            version++
                        },
                        onDragCancel = { current = emptyList() }
                    )
                }
        ) {
            (strokes + listOf(current)).forEach { stroke ->
                if (stroke.size > 1) {
                    val path = Path().apply {
                        moveTo(stroke.first().offset.x, stroke.first().offset.y)
                        stroke.drop(1).forEach { lineTo(it.offset.x, it.offset.y) }
                    }
                    drawPath(
                        path,
                        color = p.gold,
                        style = Stroke(width = 6.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
                    )
                }
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            LinkText("Пробел", p.gold, 14.sp) { buffer += " " }
            LinkText("⌫", p.gold, 18.sp) { buffer = buffer.dropLast(1) }
            LinkText("Стереть рисунок", p.muted, 14.sp) {
                strokes.clear()
                candidates = emptyList()
            }
            LinkText("Очистить", p.muted, 14.sp) {
                buffer = ""
                strokes.clear()
                candidates = emptyList()
            }
        }
        GoldButton(
            "Перевести",
            modifier = Modifier.fillMaxWidth(),
            enabled = buffer.isNotBlank()
        ) {
            vm.changeSource(language)
            vm.updateInput(buffer)
            vm.translate()
            onDone()
        }
    }
}
