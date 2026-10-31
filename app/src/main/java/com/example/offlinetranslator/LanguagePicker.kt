package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties

/** Кнопка с названием языка, открывающая окно выбора с поиском. */
@Composable
fun LanguageButton(
    selected: String,
    title: String,
    downloaded: Set<String>,
    modifier: Modifier = Modifier,
    onSelect: (String) -> Unit
) {
    val p = LocalPalette.current
    val tap = rememberTap()
    var open by remember { mutableStateOf(false) }
    Box(
        modifier
            .height(46.dp)
            .clip(ButtonShape)
            .border(1.dp, p.goldDim, ButtonShape)
            .clickable {
                tap()
                open = true
            },
        contentAlignment = Alignment.Center
    ) {
        Text(Languages.name(selected), color = p.text, fontSize = 15.sp, maxLines = 1)
    }
    if (open) {
        LanguagePickerDialog(
            title = title,
            selected = selected,
            downloaded = downloaded,
            onDismiss = { open = false },
            onSelect = {
                open = false
                onSelect(it)
            }
        )
    }
}

@Composable
fun LanguagePickerDialog(
    title: String,
    selected: String,
    downloaded: Set<String>,
    onDismiss: () -> Unit,
    onSelect: (String) -> Unit
) {
    val p = LocalPalette.current
    var query by remember { mutableStateOf("") }
    val filtered = Languages.all.filter {
        query.isBlank() ||
            Languages.name(it).contains(query.trim(), ignoreCase = true) ||
            it.startsWith(query.trim(), ignoreCase = true)
    }
    val ready = filtered.filter { it in downloaded }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Column(
            Modifier
                .fillMaxWidth(0.92f)
                .fillMaxHeight(0.82f)
                .clip(CardShape)
                .background(p.bg)
                .border(1.dp, p.goldDim, CardShape)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(title, color = p.gold, fontFamily = FontFamily.Serif, fontSize = 20.sp)
                LinkText("Закрыть", p.muted, onClick = onDismiss)
            }
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
            LazyColumn(
                Modifier
                    .fillMaxWidth()
                    .weight(1f)
            ) {
                if (ready.isNotEmpty()) {
                    item { PickerHeader("Скачанные — работают без интернета") }
                    items(ready, key = { "d_$it" }) { code ->
                        LanguageRow(code, code == selected, true) { onSelect(code) }
                    }
                }
                item { PickerHeader("Все языки (${filtered.size})") }
                items(filtered, key = { "a_$it" }) { code ->
                    LanguageRow(code, code == selected, code in downloaded) { onSelect(code) }
                }
            }
        }
    }
}

@Composable
private fun PickerHeader(text: String) {
    val p = LocalPalette.current
    Text(
        text.uppercase(),
        color = p.muted,
        fontSize = 11.sp,
        letterSpacing = 2.sp,
        modifier = Modifier.padding(top = 12.dp, bottom = 4.dp)
    )
}

@Composable
private fun LanguageRow(code: String, isSelected: Boolean, isDownloaded: Boolean, onClick: () -> Unit) {
    val p = LocalPalette.current
    val tap = rememberTap()
    Row(
        Modifier
            .fillMaxWidth()
            .clip(ButtonShape)
            .background(if (isSelected) p.card else Color.Transparent)
            .clickable {
                tap()
                onClick()
            }
            .padding(horizontal = 10.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            Languages.name(code),
            color = if (isSelected) p.gold else p.text,
            fontSize = 16.sp,
            modifier = Modifier.weight(1f)
        )
        if (isDownloaded) Text("скачан", color = p.muted, fontSize = 12.sp)
        if (isSelected) {
            Spacer(Modifier.padding(start = 8.dp))
            Text("✓", color = p.gold, fontSize = 16.sp)
        }
    }
}
