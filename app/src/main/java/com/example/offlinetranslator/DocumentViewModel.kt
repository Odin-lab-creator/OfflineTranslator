package com.example.offlinetranslator

import android.app.Application
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Перевод документов (PDF и TXT). Работа продолжается, даже если уйти с экрана. */
class DocumentViewModel(app: Application) : AndroidViewModel(app) {
    private val settings = AppSettings.get(app)

    var fileName by mutableStateOf("")
        private set
    var original by mutableStateOf("")
        private set
    var translated by mutableStateOf("")
        private set
    var source by mutableStateOf("")
        private set
    var target by mutableStateOf(settings.lastTarget)
        private set
    var progress by mutableStateOf<Float?>(null)
        private set
    var status by mutableStateOf("")
        private set

    private var job: Job? = null

    fun changeTarget(code: String) {
        target = code
    }

    fun cancel() {
        job?.cancel()
        progress = null
        status = "Остановлено"
    }

    fun open(uri: Uri, sourceHint: String) {
        job?.cancel()
        job = viewModelScope.launch {
            val app = getApplication<Application>()
            fileName = displayName(uri)
            original = ""
            translated = ""
            progress = 0f
            try {
                val type = app.contentResolver.getType(uri).orEmpty()
                val isPdf = type == "application/pdf" || fileName.endsWith(".pdf", ignoreCase = true)
                val raw = if (isPdf) {
                    readPdf(uri, sourceHint)
                } else {
                    status = "Читаю файл…"
                    withContext(Dispatchers.IO) {
                        app.contentResolver.openInputStream(uri)?.use { it.readBytes().toString(Charsets.UTF_8) }
                    }.orEmpty()
                }
                val text = raw.trim().take(MAX_DOCUMENT)
                if (text.isEmpty()) {
                    status = "В файле не найден текст"
                    progress = null
                    return@launch
                }
                original = text
                translateAll(text, sourceHint)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                status = "Не удалось обработать файл: ${e.localizedMessage ?: "ошибка"}"
                progress = null
            }
        }
    }

    /** Повторить перевод уже открытого документа (например, на другой язык). */
    fun retranslate() {
        val text = original
        if (text.isEmpty()) return
        job?.cancel()
        job = viewModelScope.launch {
            try {
                translateAll(text, source.ifEmpty { settings.lastSource })
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                status = "Не удалось перевести: ${e.localizedMessage ?: "ошибка"}"
                progress = null
            }
        }
    }

    private suspend fun readPdf(uri: Uri, sourceHint: String): String {
        val app = getApplication<Application>()
        val script = TranslationEngine.resolveScript(settings.ocrScript, sourceHint)
        val descriptor = app.contentResolver.openFileDescriptor(uri, "r") ?: error("не удалось открыть PDF")
        val pages = StringBuilder()
        descriptor.use { fd ->
            PdfRenderer(fd).use { renderer ->
                val count = minOf(renderer.pageCount, MAX_PAGES)
                for (index in 0 until count) {
                    status = "Распознаю страницу ${index + 1} из $count…"
                    progress = index.toFloat() / count * 0.4f
                    val bitmap = withContext(Dispatchers.Default) {
                        renderer.openPage(index).use { page ->
                            val scale = 1600f / page.width
                            val width = 1600
                            val height = (page.height * scale).toInt().coerceAtLeast(1)
                            Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888).also {
                                it.eraseColor(Color.WHITE)
                                page.render(it, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                            }
                        }
                    }
                    try {
                        val text = TranslationEngine.recognizeBitmap(app, bitmap, script, sourceHint)
                        if (text.isNotBlank()) pages.append(text).append("\n\n")
                    } finally {
                        bitmap.recycle()
                    }
                }
                if (renderer.pageCount > MAX_PAGES) {
                    pages.append("[Переведены первые $MAX_PAGES страниц из ${renderer.pageCount}]")
                }
            }
        }
        return pages.toString()
    }

    private suspend fun translateAll(text: String, sourceHint: String) {
        status = "Определяю язык…"
        val detected = try {
            TranslationEngine.detect(text.take(1000))
        } catch (e: Exception) {
            null
        }
        source = detected ?: sourceHint
        if (source == target) target = Languages.otherTarget(source, target)

        val chunks = chunk(text)
        val out = StringBuilder()
        chunks.forEachIndexed { index, part ->
            status = "Перевожу: ${index + 1} из ${chunks.size}"
            progress = 0.4f + 0.6f * index / chunks.size
            out.append(
                if (part.isBlank()) part
                else TranslationEngine.translate(source, target, part, settings.wifiOnly)
            ).append("\n\n")
            translated = out.toString().trim()
        }
        translated = out.toString().trim()
        status = "Готово: ${Languages.name(source)} → ${Languages.name(target)}"
        progress = null
    }

    /** Режем текст по абзацам на куски до ~1000 символов, чтобы перевод шёл частями. */
    private fun chunk(text: String): List<String> {
        val paragraphs = text.split(Regex("\\n\\s*\\n")).map { it.trim() }.filter { it.isNotEmpty() }
        val result = mutableListOf<String>()
        paragraphs.forEach { paragraph ->
            if (paragraph.length <= 1000) {
                result.add(paragraph)
            } else {
                val sentence = StringBuilder()
                paragraph.split(Regex("(?<=[.!?…])\\s+")).forEach { s ->
                    if (sentence.length + s.length > 1000 && sentence.isNotEmpty()) {
                        result.add(sentence.toString().trim())
                        sentence.clear()
                    }
                    sentence.append(s).append(' ')
                }
                if (sentence.isNotBlank()) result.add(sentence.toString().trim())
            }
        }
        return result
    }

    private fun displayName(uri: Uri): String {
        val app = getApplication<Application>()
        return try {
            app.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0) else null
            }
        } catch (e: Exception) {
            null
        } ?: "документ"
    }

    companion object {
        const val MAX_PAGES = 50
        const val MAX_DOCUMENT = 200_000
    }
}
