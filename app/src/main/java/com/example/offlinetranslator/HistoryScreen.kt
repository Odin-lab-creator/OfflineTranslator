package com.example.offlinetranslator

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.ui.platform.LocalContext
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HistoryScreen(
    history: HistoryStore,
    onBack: () -> Unit,
    onOpen: (HistoryEntry) -> Unit
) {
    val p = LocalPalette.current
    val clipboard = LocalClipboardManager.current
    var favoritesOnly by rememberSaveable { mutableStateOf(false) }
    var query by rememberSaveable { mutableStateOf("") }
    var confirmClear by remember { mutableStateOf(false) }
    var menu by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    val context = LocalContext.current
    val exportFile = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        if (uri != null) {
            message = try {
                context.contentResolver.openOutputStream(uri)?.use { it.write(history.exportJson().toByteArray()) }
                "Сохранено записей: ${history.entries.size}"
            } catch (e: Exception) {
                "Не удалось сохранить: ${e.localizedMessage ?: "ошибка"}"
            }
        }
    }
    val importFile = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            message = try {
                val raw = context.contentResolver.openInputStream(uri)?.use { it.readBytes().toString(Charsets.UTF_8) }
                    .orEmpty()
                "Добавлено записей: ${history.importJson(raw)}"
            } catch (e: Exception) {
                "Не удалось прочитать файл: ${e.localizedMessage ?: "это не файл истории"}"
            }
        }
    }
    val dateFormat = remember { SimpleDateFormat("d MMM, HH:mm", Locale("ru")) }

    val shown = history.entries.filter { entry ->
        (!favoritesOnly || entry.favorite) &&
            (query.isBlank() ||
                entry.text.contains(query.trim(), ignoreCase = true) ||
                entry.result.contains(query.trim(), ignoreCase = true))
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
                ScreenHeader("История", onBack) {
                    Box {
                        LinkText("⋮", p.gold, 22.sp) { menu = true }
                        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(
                                text = { Text("Экспорт в файл", color = p.text) },
                                onClick = {
                                    menu = false
                                    exportFile.launch("valhalla_history.json")
                                }
                            )
                            DropdownMenuItem(
                                text = { Text("Импорт из файла", color = p.text) },
                                onClick = {
                                    menu = false
                                    importFile.launch(arrayOf("application/json", "text/plain", "application/octet-stream"))
                                }
                            )
                            if (history.entries.any { !it.favorite }) {
                                DropdownMenuItem(
                                    text = { Text("Очистить историю", color = p.text) },
                                    onClick = {
                                        menu = false
                                        confirmClear = true
                                    }
                                )
                            }
                        }
                    }
                }
                if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 13.sp)
                GoldDivider()
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    TabChip("Все", !favoritesOnly) { favoritesOnly = false }
                    TabChip("★ Избранное", favoritesOnly) { favoritesOnly = true }
                }
                TextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text("Поиск по истории") },
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
            }
        }

        if (shown.isEmpty()) {
            item {
                Text(
                    when {
                        query.isNotBlank() -> "Ничего не найдено"
                        favoritesOnly -> "В избранном пока пусто. Нажмите ☆ у перевода, чтобы сохранить его."
                        else -> "История пока пуста. Переводы будут появляться здесь."
                    },
                    color = p.muted,
                    fontSize = 14.sp,
                    modifier = Modifier.padding(vertical = 24.dp)
                )
            }
        }

        items(shown, key = { it.id }) { entry ->
            Column(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p, border = if (entry.favorite) p.goldDim else p.cardBorder)
                    .clickable { onOpen(entry) }
                    .padding(start = 14.dp, end = 8.dp, top = 12.dp, bottom = 4.dp)
            ) {
                Text(
                    "${Languages.name(entry.source)} → ${Languages.name(entry.target)} · ${dateFormat.format(Date(entry.time))}",
                    color = p.muted,
                    fontSize = 11.sp
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    entry.text,
                    color = p.text,
                    fontSize = 14.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    entry.result,
                    color = p.result,
                    fontFamily = FontFamily.Serif,
                    fontSize = 18.sp,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    LinkText(if (entry.favorite) "★" else "☆", p.gold, 18.sp) {
                        history.toggleFavorite(entry.id)
                    }
                    LinkText("Копировать", p.gold) {
                        clipboard.setText(AnnotatedString(entry.result))
                    }
                    Spacer(Modifier.weight(1f))
                    LinkText("Удалить", p.muted) { history.delete(entry.id) }
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }

    if (confirmClear) {
        AlertDialog(
            onDismissRequest = { confirmClear = false },
            title = { Text("Очистить историю?", color = p.gold, fontFamily = FontFamily.Serif) },
            text = { Text("Избранное останется.", color = p.text) },
            confirmButton = {
                LinkText("Очистить", p.gold, 15.sp) {
                    history.clearHistory()
                    confirmClear = false
                }
            },
            dismissButton = {
                LinkText("Отмена", p.muted, 15.sp) { confirmClear = false }
            },
            containerColor = p.card
        )
    }
}

@Composable
fun TabChip(label: String, selected: Boolean, onClick: () -> Unit) {
    val p = LocalPalette.current
    OutlineGoldButton(
        label,
        height = 38,
        onClick = onClick,
        modifier = if (selected) Modifier.background(p.card, ButtonShape) else Modifier
    )
}
