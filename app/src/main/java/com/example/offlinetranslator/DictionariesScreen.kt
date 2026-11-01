package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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

/** Экран «Словари»: скачать или удалить офлайн-словари для пар языков. */
@Composable
fun DictionariesScreen(onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val settings = AppSettings.current()
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        Dictionary.init(context)
        try {
            Dictionary.refreshIndex()
        } catch (e: Exception) {
            if (Dictionary.available.isEmpty()) message = "Нужен интернет, чтобы загрузить список словарей"
        }
    }
    val mine = settings.myLanguage
    val sorted = Dictionary.available.sortedWith(
        compareByDescending<Dictionary.Available> { it.pair in Dictionary.downloaded }
            .thenByDescending { it.pair.contains(mine) }
            .thenBy { Languages.name(it.pair.substringBefore('-')) }
    )

    LazyColumn(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item {
            Column(Modifier.padding(top = 12.dp, bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                ScreenHeader("Словари", onBack)
                GoldDivider()
                Text(
                    "Словарь показывает все значения слова, часть речи и произношение — без интернета. " +
                        "Открывается кнопкой «Словарь», словами под переводом и в читалке. " +
                        "Данные: WikDict и Викисловарь (CC BY-SA).",
                    color = p.muted,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 13.sp)
            }
        }
        items(sorted, key = { it.pair }) { item ->
            val source = item.pair.substringBefore('-')
            val target = item.pair.substringAfter('-')
            val progress = Dictionary.progress[item.pair]
            val has = item.pair in Dictionary.downloaded
            Column(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p, border = if (has) p.goldDim else p.cardBorder)
                    .padding(start = 14.dp, end = 6.dp, top = 8.dp, bottom = 8.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("${Languages.name(source)} → ${Languages.name(target)}", color = p.text, fontSize = 15.sp)
                        Text(
                            "${"%,d".format(item.entries).replace(',', ' ')} статей · ${formatMb(item.bytes)}",
                            color = p.muted,
                            fontSize = 12.sp
                        )
                    }
                    when {
                        progress != null -> Text("${(progress * 100).toInt()}%", color = p.gold, fontSize = 14.sp, modifier = Modifier.width(56.dp))
                        has -> LinkText("Удалить", p.muted, 13.sp) { Dictionary.delete(item.pair) }
                        else -> LinkText("Скачать", p.gold, 14.sp) {
                            scope.launch {
                                try {
                                    Dictionary.download(item.pair)
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
                        modifier = Modifier.fillMaxWidth().padding(top = 6.dp, end = 8.dp),
                        color = p.gold,
                        trackColor = p.bg
                    )
                }
            }
        }
        item { Text("", Modifier.padding(bottom = 12.dp)) }
    }
}
