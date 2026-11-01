package com.example.offlinetranslator

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Подпись под переводом: транскрипция латиницей, если она есть. */
@Composable
fun ReadingText(text: String, lang: String, modifier: Modifier = Modifier) {
    val settings = AppSettings.current()
    if (!settings.transcription) return
    val reading = remember(text, lang) { Transcription.of(text, lang) } ?: return
    val p = LocalPalette.current
    SelectionContainer {
        Text(
            reading,
            color = p.muted,
            fontSize = 14.sp,
            fontStyle = FontStyle.Italic,
            lineHeight = 19.sp,
            modifier = modifier
        )
    }
}

/** Блок «Ещё языки»: перевод той же фразы сразу на несколько языков. */
@Composable
fun ExtraTargetsSection(vm: TranslatorViewModel) {
    val settings = AppSettings.current()
    val p = LocalPalette.current
    val clipboard = LocalClipboardManager.current
    var picking by remember { mutableStateOf(false) }
    if (vm.output.isBlank() && settings.extraTargets.isEmpty()) return

    Column(
        Modifier
            .fillMaxWidth()
            .valhallaCard(p)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(
                "ЕЩЁ ЯЗЫКИ",
                color = p.muted,
                fontSize = 11.sp,
                letterSpacing = 2.sp,
                modifier = Modifier.weight(1f)
            )
            if (settings.extraTargets.size < 5) {
                LinkText("+ Добавить", p.gold, 14.sp) { picking = true }
            }
        }
        if (settings.extraTargets.isEmpty()) {
            Text(
                "Добавьте языки, и каждая фраза будет сразу переведена и на них — удобно в поездках.",
                color = p.muted,
                fontSize = 13.sp
            )
        }
        val results = vm.extraOutputs.toMap()
        settings.extraTargets.forEach { lang ->
            val text = results[lang].orEmpty()
            Column(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(Languages.name(lang), color = p.gold, fontSize = 13.sp, modifier = Modifier.weight(1f))
                    if (text.isNotBlank() && text != "…") {
                        IconTap(ValhallaIcons.Speaker, "Озвучить", p.gold) { vm.speak(text, lang) }
                        LinkText("Копировать", p.muted, 12.sp) { clipboard.setText(AnnotatedString(text)) }
                    }
                    LinkText("✕", p.muted, 14.sp) { vm.removeExtraTarget(lang) }
                }
                if (text.isNotBlank()) {
                    SelectionContainer {
                        Text(text, color = p.result, fontFamily = FontFamily.Serif, fontSize = 18.sp, lineHeight = 24.sp)
                    }
                    ReadingText(text, lang)
                }
            }
        }
    }

    if (picking) {
        LanguagePickerDialog(
            title = "Ещё один язык",
            selected = "",
            downloaded = vm.downloaded,
            onDismiss = { picking = false },
            onSelect = {
                picking = false
                if (it != vm.target && it !in settings.extraTargets) vm.addExtraTarget(it)
            }
        )
    }
}
