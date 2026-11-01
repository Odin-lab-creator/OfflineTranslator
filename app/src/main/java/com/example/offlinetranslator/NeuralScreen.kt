package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

/** Экран «Улучшенный движок (бета)»: нейросетевые модели Opus-MT. */
@Composable
fun NeuralScreen(onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val settings = AppSettings.current()
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        Neural.init(context)
        try {
            Neural.refreshIndex()
        } catch (e: Exception) {
            if (Neural.available.isEmpty()) message = "Нужен интернет, чтобы загрузить список моделей"
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Улучшенный движок", onBack)
        GoldDivider()
        Text(
            "Бета. Нейросети Opus-MT переводят точнее обычного офлайн-движка, особенно длинные фразы, " +
                "но работают медленнее (около секунды на предложение) и занимают ~100 МБ на направление. " +
                "Всё работает без интернета. Если для пары нет своей модели, перевод идёт через английский " +
                "(например, немецкий → английский → русский). Живая камера всегда использует быстрый движок.",
            color = p.text,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )
        Column(Modifier.fillMaxWidth().valhallaCard(p)) {
            SwitchRow(
                "Использовать нейросеть",
                "Для пар языков, модели которых скачаны",
                settings.neural,
                settings::updateNeural
            )
        }
        if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 13.sp)
        SectionLabel("Модели")
        Neural.available
            .sortedWith(compareByDescending<Neural.Available> { it.pair in Neural.downloaded }.thenByDescending { it.pair.contains(settings.myLanguage) })
            .forEach { item ->
                val source = item.pair.substringBefore('-')
                val target = item.pair.substringAfter('-')
                val progress = Neural.progress[item.pair]
                val has = item.pair in Neural.downloaded
                Column(
                    Modifier
                        .fillMaxWidth()
                        .valhallaCard(p, border = if (has) p.goldDim else p.cardBorder)
                        .padding(start = 14.dp, end = 6.dp, top = 6.dp, bottom = 6.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("${Languages.name(source)} → ${Languages.name(target)}", color = p.text, fontSize = 15.sp)
                            Text(formatMb(item.bytes), color = p.muted, fontSize = 12.sp)
                        }
                        when {
                            progress != null -> Text("${(progress * 100).toInt()}%", color = p.gold, fontSize = 14.sp, modifier = Modifier.padding(end = 10.dp))
                            has -> LinkText("Удалить", p.muted, 13.sp) { scope.launch { Neural.delete(item.pair) } }
                            else -> LinkText("Скачать", p.gold, 14.sp) {
                                scope.launch {
                                    try {
                                        Neural.download(item.pair)
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
        Text("Модели: Opus-MT, Helsinki-NLP (CC BY 4.0). Движок: ONNX Runtime.", color = p.muted, fontSize = 11.sp)
    }
}
