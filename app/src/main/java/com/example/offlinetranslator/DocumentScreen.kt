package com.example.offlinetranslator

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import java.io.File

private const val PREVIEW_CHARS = 20_000

@Composable
fun DocumentScreen(
    vm: TranslatorViewModel,
    onBack: () -> Unit,
    doc: DocumentViewModel = viewModel()
) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    var showOriginal by rememberSaveable { mutableStateOf(false) }
    var message by rememberSaveable { mutableStateOf("") }

    val pick = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            showOriginal = false
            message = ""
            doc.open(uri, vm.source)
        }
    }
    val baseName = doc.fileName.substringBeforeLast('.').ifBlank { "документ" }
    val save = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) { uri ->
        if (uri != null) {
            message = try {
                context.contentResolver.openOutputStream(uri)?.use { it.write(doc.translated.toByteArray()) }
                "Сохранено"
            } catch (e: Exception) {
                "Не удалось сохранить: ${e.localizedMessage ?: "ошибка"}"
            }
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
        ScreenHeader("Документы", onBack)
        GoldDivider()
        Text(
            "PDF или TXT. Страницы PDF распознаются как изображения (до ${DocumentViewModel.MAX_PAGES} страниц), " +
                "поэтому подходят и сканы. Алфавит берётся из настроек распознавания.",
            color = p.muted,
            fontSize = 13.sp,
            lineHeight = 19.sp
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Перевести на:", color = p.text, fontSize = 15.sp)
            Spacer(Modifier.padding(start = 10.dp))
            LanguageButton(doc.target, "Язык перевода", vm.downloaded, Modifier.weight(1f), doc::changeTarget)
        }
        GoldButton(
            if (doc.progress != null) "Идёт перевод…" else "Выбрать файл",
            modifier = Modifier.fillMaxWidth(),
            enabled = doc.progress == null
        ) { pick.launch(arrayOf("application/pdf", "text/plain")) }

        val progress = doc.progress
        if (progress != null) {
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth(),
                color = p.gold,
                trackColor = p.card
            )
        }
        if (doc.status.isNotEmpty()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(doc.status, color = p.muted, fontSize = 13.sp, modifier = Modifier.weight(1f))
                if (progress != null) LinkText("Остановить", p.gold, 13.sp) { doc.cancel() }
            }
        }

        if (doc.original.isNotEmpty() && progress == null && doc.translated.isNotEmpty()) {
            OutlineGoldButton(
                "Перевести заново на ${Languages.name(doc.target)}",
                modifier = Modifier.fillMaxWidth(),
                height = 44
            ) { doc.retranslate() }
        }

        if (doc.translated.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TabChip("Перевод", !showOriginal) { showOriginal = false }
                TabChip("Оригинал", showOriginal) { showOriginal = true }
            }
            val full = if (showOriginal) doc.original else doc.translated
            Column(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p, border = if (showOriginal) p.cardBorder else p.gold)
                    .padding(16.dp)
            ) {
                Text(doc.fileName, color = p.muted, fontSize = 12.sp)
                Spacer(Modifier.height(6.dp))
                SelectionContainer {
                    Text(
                        full.take(PREVIEW_CHARS),
                        color = if (showOriginal) p.text else p.result,
                        fontFamily = if (showOriginal) FontFamily.Default else FontFamily.Serif,
                        fontSize = 16.sp,
                        lineHeight = 23.sp
                    )
                }
                if (full.length > PREVIEW_CHARS) {
                    Text(
                        "… показаны первые ${PREVIEW_CHARS / 1000} тыс. символов. Весь текст — в сохранённом файле.",
                        color = p.muted,
                        fontSize = 12.sp
                    )
                }
            }
            if (progress == null) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    LinkText("Сохранить TXT", p.gold, 14.sp) { save.launch("${baseName}_${doc.target}.txt") }
                    LinkText("Поделиться", p.gold, 14.sp) {
                        try {
                            val dir = File(context.cacheDir, "shared").apply { mkdirs() }
                            val file = File(dir, "${baseName}_${doc.target}.txt")
                            file.writeText(doc.translated)
                            val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
                            val send = Intent(Intent.ACTION_SEND)
                                .setType("text/plain")
                                .putExtra(Intent.EXTRA_STREAM, uri)
                                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            context.startActivity(Intent.createChooser(send, null))
                        } catch (e: Exception) {
                            message = "Не удалось поделиться: ${e.localizedMessage ?: "ошибка"}"
                        }
                    }
                    if (doc.translated.length < 100_000) {
                        LinkText("Копировать", p.gold, 14.sp) {
                            clipboard.setText(AnnotatedString(doc.translated))
                            message = "Скопировано"
                        }
                    }
                }
            }
            if (message.isNotEmpty()) Text(message, color = p.muted, fontSize = 13.sp)
        }
        Spacer(Modifier.height(16.dp))
    }
}
