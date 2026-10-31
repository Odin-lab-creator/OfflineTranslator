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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Блок «Сленг» под переводом: что означает каждое найденное выражение. */
@Composable
fun SlangFoundList(found: List<Slang.Found>, modifier: Modifier = Modifier) {
    if (found.isEmpty()) return
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("СЛЕНГ", color = p.muted, fontSize = 11.sp, letterSpacing = 2.sp)
        found.forEach { item ->
            Text(
                buildAnnotatedString {
                    withStyle(SpanStyle(color = p.gold, fontWeight = FontWeight.Medium)) { append(item.original) }
                    withStyle(SpanStyle(color = p.text)) { append(" — " + item.entry.meaning) }
                },
                fontSize = 14.sp,
                lineHeight = 19.sp
            )
        }
    }
}

/** Экран «Словарь сленга»: все выражения, которые распознаёт приложение. */
@Composable
fun SlangDictionaryScreen(onBack: () -> Unit) {
    val p = LocalPalette.current
    var language by rememberSaveable { mutableStateOf("en") }
    var query by rememberSaveable { mutableStateOf("") }
    val entries = Slang.entries(language)
        .distinctBy { it.term.lowercase() + "|" + it.meaning }
        .filter {
            query.isBlank() ||
                it.term.contains(query.trim(), ignoreCase = true) ||
                it.meaning.contains(query.trim(), ignoreCase = true)
        }
        .sortedBy { it.term.lowercase() }

    LazyColumn(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item {
            Column(
                Modifier.padding(top = 12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ScreenHeader("Словарь сленга", onBack)
                GoldDivider()
                Text(
                    "Эти выражения распознаются автоматически: перед переводом они заменяются обычными словами, " +
                        "а под переводом появляется пояснение. Работает без интернета.",
                    color = p.muted,
                    fontSize = 13.sp,
                    lineHeight = 19.sp
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TabChip("Английский", language == "en") { language = "en" }
                    TabChip("Русский", language == "ru") { language = "ru" }
                }
                TextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text("Поиск: no cap, кринж, «честно»…") },
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
                Text("Выражений: ${entries.size}", color = p.muted, fontSize = 12.sp)
            }
        }
        items(entries, key = { it.term + "|" + it.pattern }) { entry ->
            Column(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p)
                    .padding(horizontal = 14.dp, vertical = 10.dp)
            ) {
                Text(entry.term, color = p.gold, fontSize = 16.sp, fontWeight = FontWeight.Medium)
                Text(entry.meaning, color = p.text, fontSize = 14.sp, lineHeight = 19.sp)
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}
