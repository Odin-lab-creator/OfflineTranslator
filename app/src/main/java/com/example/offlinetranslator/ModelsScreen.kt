package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.mlkit.nl.translate.TranslateLanguage
import kotlinx.coroutines.launch

@Composable
fun ModelsScreen(vm: TranslatorViewModel, settings: AppSettings, onBack: () -> Unit) {
    val p = LocalPalette.current
    val scope = rememberCoroutineScope()
    var working by remember { mutableStateOf(setOf<String>()) }
    var message by remember { mutableStateOf("") }
    var query by remember { mutableStateOf("") }

    LaunchedEffect(Unit) { vm.refreshDownloaded() }

    fun download(code: String) {
        scope.launch {
            working = working + code
            message = "Скачиваю: ${Languages.name(code)}…"
            try {
                TranslationEngine.download(code, settings.wifiOnly)
                message = "Готово: ${Languages.name(code)} работает без интернета"
            } catch (e: Exception) {
                message = "Не удалось скачать ${Languages.name(code)}: ${e.localizedMessage ?: "ошибка"}" +
                    if (settings.wifiOnly) ". Включена загрузка только по Wi-Fi." else ""
            } finally {
                working = working - code
                vm.refreshDownloaded()
            }
        }
    }

    fun delete(code: String) {
        scope.launch {
            working = working + code
            try {
                TranslationEngine.delete(code)
                message = "Удалено: ${Languages.name(code)}"
            } catch (e: Exception) {
                message = "Не удалось удалить ${Languages.name(code)}"
            } finally {
                working = working - code
                vm.refreshDownloaded()
            }
        }
    }

    val filtered = Languages.all.filter {
        query.isBlank() || Languages.name(it).contains(query.trim(), ignoreCase = true)
    }
    val ready = filtered.filter { it in vm.downloaded }
    val others = filtered.filter { it !in vm.downloaded }

    LazyColumn(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Column(
                Modifier.padding(top = 12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ScreenHeader("Языковые модели", onBack)
                GoldDivider()
                Text(
                    "Скачанная модель позволяет переводить с этим языком без интернета. " +
                        "Каждая занимает около 30 МБ. Английский встроен.",
                    color = p.muted,
                    fontSize = 13.sp,
                    lineHeight = 19.sp
                )
                TextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text("Поиск языка") },
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .valhallaCard(p),
                    colors = TextFieldDefaults.colors(
                        focusedTextColor = p.text,
                        unfocusedTextColor = p.text,
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent,
                        cursorColor = p.gold,
                        focusedPlaceholderColor = p.muted,
                        unfocusedPlaceholderColor = p.muted
                    )
                )
                if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 13.sp)
            }
        }
        if (ready.isNotEmpty()) {
            item { SectionLabel("Скачано (${ready.size})") }
            items(ready, key = { "r_$it" }) { code ->
                ModelRow(
                    code = code,
                    downloaded = true,
                    busy = code in working,
                    onDownload = { },
                    onDelete = { delete(code) }
                )
            }
        }
        item { SectionLabel("Можно скачать (${others.size})") }
        items(others, key = { "o_$it" }) { code ->
            ModelRow(
                code = code,
                downloaded = false,
                busy = code in working,
                onDownload = { download(code) },
                onDelete = { }
            )
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
private fun ModelRow(
    code: String,
    downloaded: Boolean,
    busy: Boolean,
    onDownload: () -> Unit,
    onDelete: () -> Unit
) {
    val p = LocalPalette.current
    Row(
        Modifier
            .fillMaxWidth()
            .valhallaCard(p)
            .padding(start = 14.dp, end = 6.dp, top = 4.dp, bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(Languages.name(code), color = p.text, fontSize = 15.sp)
            Text(
                when {
                    busy -> "в работе…"
                    downloaded && code == TranslateLanguage.ENGLISH -> "встроен"
                    downloaded -> "работает офлайн"
                    else -> "нужна загрузка"
                },
                color = p.muted,
                fontSize = 12.sp
            )
        }
        when {
            busy -> Text("…", color = p.gold, fontSize = 18.sp, modifier = Modifier.padding(12.dp))
            code == TranslateLanguage.ENGLISH -> Unit
            downloaded -> LinkText("Удалить", p.muted, 14.sp, onClick = onDelete)
            else -> LinkText("Скачать", p.gold, 14.sp, onClick = onDownload)
        }
    }
}
