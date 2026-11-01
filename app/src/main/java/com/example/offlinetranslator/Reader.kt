package com.example.offlinetranslator

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.mutableStateListOf
import java.io.ByteArrayInputStream
import java.io.File
import java.net.URLDecoder
import java.nio.ByteBuffer
import java.nio.charset.Charset
import java.nio.charset.CodingErrorAction
import java.util.zip.ZipInputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import org.jsoup.parser.Parser

/** Книга или статья в читалке. Текст хранится на телефоне по абзацам. */
data class Book(
    val id: Long,
    val title: String,
    val language: String,
    val paragraphs: Int,
    val position: Int,
    val added: Long
)

/** Библиотека читалки и разбор файлов: EPUB, FB2, TXT, HTML и статьи по ссылке. */
class ReaderStore private constructor(context: Context) {
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences("reader", Context.MODE_PRIVATE)
    private val dir = File(app.filesDir, "reader").apply { mkdirs() }

    val books = mutableStateListOf<Book>()

    init {
        try {
            val array = JSONArray(prefs.getString("books", "[]") ?: "[]")
            for (i in 0 until array.length()) {
                val o = array.getJSONObject(i)
                books += Book(
                    o.getLong("id"), o.getString("title"), o.getString("language"),
                    o.getInt("paragraphs"), o.optInt("position"), o.optLong("added")
                )
            }
        } catch (e: Exception) {
            // пустая библиотека
        }
    }

    private fun save() {
        val array = JSONArray()
        books.forEach {
            array.put(
                JSONObject().put("id", it.id).put("title", it.title).put("language", it.language)
                    .put("paragraphs", it.paragraphs).put("position", it.position).put("added", it.added)
            )
        }
        prefs.edit().putString("books", array.toString()).apply()
    }

    fun paragraphs(book: Book): List<String> =
        try {
            File(dir, "${book.id}.txt").readLines().filter { it.isNotBlank() }
        } catch (e: Exception) {
            emptyList()
        }

    fun savePosition(id: Long, position: Int) {
        val index = books.indexOfFirst { it.id == id }
        if (index < 0 || books[index].position == position) return
        books[index] = books[index].copy(position = position)
        save()
    }

    fun delete(id: Long) {
        books.removeAll { it.id == id }
        File(dir, "$id.txt").delete()
        save()
    }

    private suspend fun add(title: String, paragraphs: List<String>): Book {
        val clean = paragraphs.map { it.replace(Regex("\\s+"), " ").trim() }.filter { it.isNotEmpty() }
        check(clean.isNotEmpty()) { "в файле не найден текст" }
        val sample = clean.joinToString(" ").take(3000)
        val language = try {
            TranslationEngine.detect(sample)
        } catch (e: Exception) {
            null
        } ?: "en"
        val id = System.currentTimeMillis()
        withContext(Dispatchers.IO) { File(dir, "$id.txt").writeText(clean.joinToString("\n")) }
        val book = Book(id, title.ifBlank { clean.first().take(60) }, language, clean.size, 0, id)
        books.add(0, book)
        save()
        return book
    }

    suspend fun addText(text: String): Book {
        val parsed = withContext(Dispatchers.Default) { plainParagraphs(text) }
        return add(parsed.firstOrNull()?.take(60).orEmpty(), parsed)
    }

    suspend fun addUrl(url: String): Book {
        val (title, paragraphs) = withContext(Dispatchers.IO) {
            val doc = Jsoup.connect(url.trim())
                .userAgent("Mozilla/5.0 (Linux; Android 14) ValhallaTranslate")
                .timeout(20000)
                .followRedirects(true)
                .get()
            doc.title() to articleParagraphs(doc)
        }
        return add(title, paragraphs)
    }

    suspend fun addUri(uri: Uri): Book {
        val (title, paragraphs) = withContext(Dispatchers.IO) {
            val name = displayName(uri)
            val bytes = app.contentResolver.openInputStream(uri)?.use { input ->
                val buffer = java.io.ByteArrayOutputStream()
                val chunk = ByteArray(65536)
                var total = 0
                while (true) {
                    val n = input.read(chunk)
                    if (n < 0) break
                    total += n
                    check(total < 60_000_000) { "файл слишком большой" }
                    buffer.write(chunk, 0, n)
                }
                buffer.toByteArray()
            } ?: error("не удалось открыть файл")
            parseFile(name, bytes)
        }
        return add(title, paragraphs)
    }

    private fun displayName(uri: Uri): String =
        try {
            app.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0) else null
            }
        } catch (e: Exception) {
            null
        } ?: uri.lastPathSegment.orEmpty()

    private fun parseFile(name: String, bytes: ByteArray): Pair<String, List<String>> {
        val lower = name.lowercase()
        val isZip = bytes.size > 4 && bytes[0] == 'P'.code.toByte() && bytes[1] == 'K'.code.toByte()
        val baseTitle = name.substringBeforeLast('.').substringBeforeLast(".fb2")
        if (isZip) {
            val entries = unzip(bytes)
            if (entries.containsKey("META-INF/container.xml")) return epub(entries, baseTitle)
            val fb2 = entries.entries.firstOrNull { it.key.lowercase().endsWith(".fb2") }
            if (fb2 != null) return fb2(fb2.value, baseTitle)
            val txt = entries.entries.firstOrNull { it.key.lowercase().endsWith(".txt") }
            if (txt != null) return baseTitle to plainParagraphs(decodeText(txt.value))
            error("в архиве нет книги (EPUB, FB2 или TXT)")
        }
        return when {
            lower.endsWith(".fb2") || String(bytes, 0, minOf(bytes.size, 400), Charsets.ISO_8859_1).contains("FictionBook") ->
                fb2(bytes, baseTitle)
            lower.endsWith(".html") || lower.endsWith(".htm") || lower.endsWith(".xhtml") -> {
                val doc = Jsoup.parse(ByteArrayInputStream(bytes), null, "")
                doc.title().ifBlank { baseTitle } to articleParagraphs(doc)
            }
            lower.endsWith(".pdf") -> error("PDF открывается в разделе «Документы»")
            else -> baseTitle to plainParagraphs(decodeText(bytes))
        }
    }

    private fun unzip(bytes: ByteArray): Map<String, ByteArray> {
        val result = LinkedHashMap<String, ByteArray>()
        var total = 0L
        ZipInputStream(ByteArrayInputStream(bytes)).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                if (!entry.isDirectory) {
                    val data = zip.readBytes()
                    total += data.size
                    check(total < 150_000_000) { "архив слишком большой" }
                    result[entry.name] = data
                }
            }
        }
        return result
    }

    private fun epub(entries: Map<String, ByteArray>, fallbackTitle: String): Pair<String, List<String>> {
        val container = Jsoup.parse(String(entries.getValue("META-INF/container.xml"), Charsets.UTF_8), "", Parser.xmlParser())
        val opfPath = container.selectFirst("rootfile")?.attr("full-path") ?: error("повреждённый EPUB")
        val opfBytes = entries[opfPath] ?: error("повреждённый EPUB")
        val opf = Jsoup.parse(String(opfBytes, Charsets.UTF_8), "", Parser.xmlParser())
        val base = opfPath.substringBeforeLast('/', "")
        val manifest = opf.select("manifest > item").associate { it.attr("id") to it.attr("href") }
        val title = opf.selectFirst("dc|title")?.text()?.takeIf { it.isNotBlank() } ?: fallbackTitle
        val paragraphs = mutableListOf<String>()
        opf.select("spine > itemref").forEach { ref ->
            val href = manifest[ref.attr("idref")] ?: return@forEach
            val decoded = try {
                URLDecoder.decode(href.substringBefore('#'), "UTF-8")
            } catch (e: Exception) {
                href
            }
            val path = resolve(base, decoded)
            val data = entries[path] ?: entries.entries.firstOrNull { it.key.endsWith(decoded) }?.value ?: return@forEach
            val doc = Jsoup.parse(String(data, Charsets.UTF_8))
            paragraphs += blocks(doc.body() ?: return@forEach)
        }
        return title to paragraphs
    }

    private fun resolve(base: String, href: String): String {
        val parts = (if (base.isEmpty()) emptyList() else base.split('/')).toMutableList()
        href.split('/').forEach { part ->
            when (part) {
                ".." -> if (parts.isNotEmpty()) parts.removeAt(parts.size - 1)
                ".", "" -> Unit
                else -> parts += part
            }
        }
        return parts.joinToString("/")
    }

    private fun fb2(bytes: ByteArray, fallbackTitle: String): Pair<String, List<String>> {
        val doc = Jsoup.parse(ByteArrayInputStream(bytes), null, "", Parser.xmlParser())
        val title = doc.selectFirst("book-title")?.text()?.takeIf { it.isNotBlank() } ?: fallbackTitle
        val body = doc.selectFirst("body") ?: error("в FB2 нет текста")
        val paragraphs = body.select("p, subtitle, v").map { it.text() }
        return title to paragraphs
    }

    companion object {
        @Volatile
        private var instance: ReaderStore? = null

        fun get(context: Context): ReaderStore =
            instance ?: synchronized(this) {
                instance ?: ReaderStore(context).also { instance = it }
            }

        /** Текст: UTF-8, а если не подходит — Windows-1251 (частая кодировка русских TXT). */
        fun decodeText(bytes: ByteArray): String {
            val utf8 = Charsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
            return try {
                utf8.decode(ByteBuffer.wrap(bytes)).toString().removePrefix("﻿")
            } catch (e: Exception) {
                String(bytes, Charset.forName("windows-1251"))
            }
        }

        fun plainParagraphs(text: String): List<String> {
            val normalized = text.replace("\r\n", "\n").replace('\r', '\n')
            val lines = normalized.lines()
            val blank = lines.count { it.isBlank() }
            return if (blank > lines.size / 8) {
                normalized.split(Regex("\\n\\s*\\n")).map { it.replace('\n', ' ') }
            } else {
                lines
            }.map { it.trim() }.filter { it.isNotEmpty() }
        }

        private val blockTags = setOf("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "dt", "dd", "figcaption")

        private val blockSelector = blockTags.joinToString(", ")

        /** Абзацы из HTML без повторов вложенных блоков. */
        fun blocks(root: Element): List<String> {
            val result = mutableListOf<String>()
            fun walk(element: Element) {
                val tag = element.tagName().lowercase()
                if (tag in blockTags) {
                    val text = element.text().trim()
                    if (text.isNotEmpty()) result += text
                    return
                }
                val nested = element.select(blockSelector)
                if (nested.isEmpty()) {
                    val text = element.text().trim()
                    if (text.isNotEmpty()) result += text
                    return
                }
                val own = element.ownText().trim()
                if (own.isNotEmpty()) result += own
                element.children().forEach { walk(it) }
            }
            walk(root)
            return result
        }

        /** Основной текст статьи: <article>, <main> или блок с наибольшим количеством абзацев. */
        fun articleParagraphs(doc: Document): List<String> {
            doc.select("script, style, noscript, nav, header, footer, aside, form, button, svg, iframe").remove()
            val body = doc.body() ?: return emptyList()
            val root = doc.selectFirst("article") ?: doc.selectFirst("main") ?: run {
                var best: Element? = null
                var bestScore = 0
                body.select("div, section").forEach { candidate ->
                    val score = candidate.children().filter { it.tagName() == "p" }.sumOf { it.text().length }
                    if (score > bestScore) {
                        bestScore = score
                        best = candidate
                    }
                }
                best
            } ?: body
            val title = doc.selectFirst("h1")?.text()
            val paragraphs = blocks(root)
            return if (title != null && paragraphs.firstOrNull() != title) listOf(title) + paragraphs else paragraphs
        }
    }
}
