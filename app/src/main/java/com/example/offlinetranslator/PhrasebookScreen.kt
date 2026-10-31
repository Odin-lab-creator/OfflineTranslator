package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.mlkit.nl.translate.TranslateLanguage

/** Переводы фраз разговорника, чтобы не переводить их заново при каждом открытии. */
private val phraseCache = mutableStateMapOf<String, String>()

@Composable
fun PhrasebookScreen(
    vm: TranslatorViewModel,
    settings: AppSettings,
    onBack: () -> Unit,
    onShow: (String, String) -> Unit
) {
    val p = LocalPalette.current
    val clipboard = LocalClipboardManager.current
    val initial = listOf(vm.source, vm.target).firstOrNull { it != TranslateLanguage.RUSSIAN }
        ?: TranslateLanguage.ENGLISH
    var target by rememberSaveable { mutableStateOf(initial) }
    var categoryIndex by rememberSaveable { mutableStateOf(0) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    val category = Phrasebook.categories[categoryIndex]

    LaunchedEffect(target, categoryIndex) {
        error = ""
        val missing = category.phrases.filter { phraseCache["$target|$it"] == null }
        if (missing.isEmpty()) return@LaunchedEffect
        busy = true
        try {
            for (phrase in missing) {
                phraseCache["$target|$phrase"] =
                    TranslationEngine.translate(TranslateLanguage.RUSSIAN, target, phrase, settings.wifiOnly)
            }
            vm.refreshDownloaded()
        } catch (e: Exception) {
            error = "Не удалось перевести: ${e.localizedMessage ?: "ошибка"}. " +
                "Для первой загрузки моделей нужен интернет."
        } finally {
            busy = false
        }
    }

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
                ScreenHeader("Разговорник", onBack)
                GoldDivider()
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Русский →", color = p.text, fontSize = 15.sp)
                    Spacer(Modifier.padding(start = 10.dp))
                    LanguageButton(
                        selected = target,
                        title = "Язык перевода",
                        downloaded = vm.downloaded,
                        modifier = Modifier.weight(1f),
                        onSelect = { if (it != TranslateLanguage.RUSSIAN) target = it }
                    )
                }
                Row(
                    Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Phrasebook.categories.forEachIndexed { index, c ->
                        TabChip(c.title, index == categoryIndex) { categoryIndex = index }
                    }
                }
                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth(), color = p.gold, trackColor = p.card)
                if (error.isNotEmpty()) Text(error, color = p.muted, fontSize = 13.sp)
            }
        }
        items(category.phrases, key = { "$target|$it" }) { phrase ->
            val translated = phraseCache["$target|$phrase"]
            Column(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p)
                    .padding(start = 14.dp, end = 6.dp, top = 12.dp, bottom = 2.dp)
            ) {
                Text(phrase, color = p.muted, fontSize = 14.sp)
                Text(
                    translated ?: "…",
                    color = p.result,
                    fontFamily = FontFamily.Serif,
                    fontSize = 20.sp,
                    lineHeight = 27.sp
                )
                if (translated != null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconTap(ValhallaIcons.Speaker, "Озвучить", p.gold) {
                            vm.speak(translated, target)
                        }
                        LinkText("Показать", p.gold, 14.sp) { onShow(translated, target) }
                        LinkText("Копировать", p.gold, 14.sp) {
                            clipboard.setText(AnnotatedString(translated))
                        }
                    }
                } else {
                    Spacer(Modifier.height(10.dp))
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}
