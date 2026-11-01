package com.example.offlinetranslator

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.text.Normalizer
import java.util.zip.GZIPInputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * Офлайн-словари (WikDict / Викисловарь): все значения слова, часть речи, произношение.
 * Скачиваются по одному на пару языков с GitHub, хранятся на телефоне.
 */
object Dictionary {
    class Sense(val glosses: List<String>, val translations: List<String>)

    class Entry(
        val word: String,
        val pos: String,
        val gender: String,
        val pronunciation: String,
        val senses: List<Sense>
    )

    class Available(val pair: String, val entries: Int, val bytes: Long)

    private const val BASE = "https://github.com/Odin-lab-creator/OfflineTranslator/releases/download/dictionaries/"

    /** Пары, которые можно скачать (из index.json). */
    var available by mutableStateOf<List<Available>>(emptyList())
        private set

    /** Скачанные пары. */
    var downloaded by mutableStateOf<Set<String>>(emptySet())
        private set

    /** Прогресс скачивания: пара → 0..1. */
    val progress = mutableStateMapOf<String, Float>()

    private val open = HashMap<String, SQLiteDatabase>()
    private var dir: File? = null

    fun init(context: Context) {
        if (dir != null) return
        val d = File(context.filesDir, "dict").apply { mkdirs() }
        dir = d
        downloaded = d.listFiles().orEmpty().filter { it.name.endsWith(".db") }.map { it.name.removeSuffix(".db") }.toSet()
        try {
            val cached = File(d, "index.json")
            if (cached.exists()) available = parseIndex(cached.readText())
        } catch (e: Exception) {
            // нет кэша — загрузим позже
        }
    }

    private fun parseIndex(raw: String): List<Available> {
        val pairs = JSONObject(raw).getJSONArray("pairs")
        return (0 until pairs.length()).map {
            val o = pairs.getJSONObject(it)
            Available(o.getString("pair"), o.optInt("entries"), o.optLong("gz"))
        }
    }

    /** Обновляет список доступных словарей (нужен интернет). */
    suspend fun refreshIndex() = withContext(Dispatchers.IO) {
        val text = fetch(BASE + "index.json").decodeToString()
        val list = parseIndex(text)
        dir?.let { File(it, "index.json").writeText(text) }
        withContext(Dispatchers.Main) { available = list }
    }

    private fun fetch(url: String): ByteArray {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 10000
            connection.readTimeout = 20000
            connection.instanceFollowRedirects = true
            if (connection.responseCode !in 200..299) error("сервер ответил ${connection.responseCode}")
            return connection.inputStream.use { it.readBytes() }
        } finally {
            connection.disconnect()
        }
    }

    fun pairOf(source: String, target: String) = "$source-$target"

    fun isAvailable(source: String, target: String) = available.any { it.pair == pairOf(source, target) }

    fun info(source: String, target: String) = available.firstOrNull { it.pair == pairOf(source, target) }

    fun isDownloaded(source: String, target: String) = pairOf(source, target) in downloaded

    suspend fun download(pair: String) {
        val d = dir ?: return
        if (progress.containsKey(pair)) return
        progress[pair] = 0f
        try {
            withContext(Dispatchers.IO) {
                val connection = URL("$BASE$pair.db.gz").openConnection() as HttpURLConnection
                connection.connectTimeout = 10000
                connection.readTimeout = 30000
                try {
                    if (connection.responseCode !in 200..299) error("сервер ответил ${connection.responseCode}")
                    val total = connection.contentLengthLong.takeIf { it > 0 } ?: (info(pair.substringBefore('-'), pair.substringAfter('-'))?.bytes ?: 0L)
                    val tmp = File(d, "$pair.tmp")
                    var read = 0L
                    val counting = object : java.io.FilterInputStream(connection.inputStream) {
                        override fun read(b: ByteArray, off: Int, len: Int): Int {
                            val n = super.read(b, off, len)
                            if (n > 0) {
                                read += n
                                if (total > 0) progress[pair] = (read.toFloat() / total).coerceIn(0f, 1f)
                            }
                            return n
                        }
                    }
                    GZIPInputStream(counting, 65536).use { input ->
                        tmp.outputStream().use { input.copyTo(it, 65536) }
                    }
                    check(tmp.renameTo(File(d, "$pair.db"))) { "не удалось сохранить словарь" }
                } finally {
                    connection.disconnect()
                }
            }
            downloaded = downloaded + pair
        } finally {
            progress.remove(pair)
        }
    }

    fun delete(pair: String) {
        synchronized(open) { open.remove(pair)?.close() }
        dir?.let { File(it, "$pair.db").delete() }
        downloaded = downloaded - pair
    }

    private fun database(pair: String): SQLiteDatabase? {
        if (pair !in downloaded) return null
        synchronized(open) {
            open[pair]?.let { return it }
            val file = File(dir ?: return null, "$pair.db")
            if (!file.exists()) return null
            val db = SQLiteDatabase.openDatabase(file.path, null, SQLiteDatabase.OPEN_READONLY)
            open[pair] = db
            return db
        }
    }

    fun normalize(text: String): String {
        val decomposed = Normalizer.normalize(text.trim().lowercase(), Normalizer.Form.NFD)
            .replace("́", "")
            .replace("̀", "")
        return Normalizer.normalize(decomposed, Normalizer.Form.NFC).replace('ё', 'е')
    }

    /** Статьи для слова: точные совпадения и словоформы, самые важные сверху. */
    suspend fun lookup(word: String, source: String, target: String): List<Entry> = withContext(Dispatchers.IO) {
        val db = database(pairOf(source, target)) ?: return@withContext emptyList()
        val key = normalize(word)
        if (key.isEmpty()) return@withContext emptyList()
        val keys = listOf(key, key.trim('\'', '’', '-')).distinct()
        val result = mutableListOf<Entry>()
        val placeholders = keys.joinToString(",") { "?" }
        db.rawQuery(
            "SELECT e.word, e.pos, e.gender, e.pronun, e.senses, max(f.w) AS w FROM form f " +
                "JOIN entry e ON e.id = f.entry_id WHERE f.form IN ($placeholders) " +
                "GROUP BY e.id ORDER BY (lower(e.word) = ?) DESC, w DESC, e.importance DESC LIMIT 8",
            (keys + key).toTypedArray()
        ).use { c ->
            while (c.moveToNext()) {
                val senses = try {
                    val array = JSONArray(c.getString(4))
                    (0 until array.length()).map { i ->
                        val o = array.getJSONObject(i)
                        val s = o.optJSONArray("s") ?: JSONArray()
                        val t = o.optJSONArray("t") ?: JSONArray()
                        Sense(
                            (0 until s.length()).map { s.getString(it) },
                            (0 until t.length()).map { t.getString(it) }
                        )
                    }
                } catch (e: Exception) {
                    emptyList()
                }
                result += Entry(c.getString(0), c.getString(1).orEmpty(), c.getString(2).orEmpty(), c.getString(3).orEmpty(), senses)
            }
        }
        result
    }

    fun posLabel(pos: String): String = when (pos.lowercase()) {
        "noun" -> "сущ."
        "verb" -> "гл."
        "adjective" -> "прил."
        "adverb" -> "нареч."
        "pronoun" -> "мест."
        "preposition" -> "предл."
        "conjunction" -> "союз"
        "interjection" -> "межд."
        "numeral", "number" -> "числ."
        "particle" -> "част."
        "article" -> "артикль"
        "phrase", "idiom", "phraseologicalunit" -> "выраж."
        "propernoun", "proper noun" -> "имя собств."
        "abbreviation", "initialism", "acronym" -> "сокр."
        "prefix" -> "приставка"
        "suffix" -> "суффикс"
        "" -> ""
        else -> pos.lowercase()
    }

    fun genderLabel(gender: String): String = when (gender.lowercase()) {
        "masculine" -> "м. р."
        "feminine" -> "ж. р."
        "neuter" -> "ср. р."
        "commongender" -> "общ. р."
        else -> ""
    }
}
