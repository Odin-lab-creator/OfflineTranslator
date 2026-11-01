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

    private val slavicEndings = listOf(
        "лась", "лось", "лись", "лся", "ла", "ло", "ли", "л",
        "иться", "аться", "яться", "ешься", "ется", "ются", "утся", "ятся", "атся",
        "ями", "ами", "ого", "его", "ому", "ему", "ыми", "ими", "ешь", "ишь", "ете", "ите", "ала", "ало", "али",
        "ила", "ило", "или", "ела", "ело", "ели", "ов", "ев", "ей", "ой", "ом", "ем", "ам", "ям", "ах", "ях",
        "ый", "ий", "ая", "яя", "ое", "ее", "ые", "ие", "ую", "юю", "ым", "им", "ых", "их", "ет", "ит", "ут",
        "ют", "ат", "ят", "ал", "ил", "ел", "ся", "сь", "а", "я", "ы", "и", "у", "ю", "е", "о", "ь", "й"
    )
    private val slavicLemmaEndings = listOf(
        "", "а", "я", "о", "е", "ь", "й", "ый", "ий", "ой", "ть", "ать", "ять", "ить", "еть", "ться",
        "аться", "иться", "ость", "ка", "ок"
    )

    /** Возможные начальные формы для русского и родственных языков: «кошки» → «кошка», «домами» → «дом». */
    private fun slavicCandidates(word: String): List<String> {
        val result = LinkedHashSet<String>()
        slavicEndings.filter { word.endsWith(it) && word.length - it.length >= 2 }.forEach { ending ->
            val base = word.dropLast(ending.length)
            slavicLemmaEndings.forEach { result += base + it }
        }
        result.remove(word)
        return result.toList().take(400)
    }

    private fun queryForms(db: SQLiteDatabase, keys: List<String>, exact: String): List<Entry> {
        if (keys.isEmpty()) return emptyList()
        val result = mutableListOf<Entry>()
        val placeholders = keys.joinToString(",") { "?" }
        db.rawQuery(
            "SELECT e.word, e.pos, e.gender, e.pronun, e.senses, max(f.w) AS w FROM form f " +
                "JOIN entry e ON e.id = f.entry_id WHERE f.form IN ($placeholders) " +
                "GROUP BY e.id ORDER BY (lower(e.word) = ?) DESC, w DESC, e.importance DESC LIMIT 8",
            (keys + exact).toTypedArray()
        ).use { c ->
            while (c.moveToNext()) result += entryFrom(c)
        }
        return result
    }

    private fun entryFrom(c: android.database.Cursor): Entry {
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
        return Entry(c.getString(0), c.getString(1).orEmpty(), c.getString(2).orEmpty(), c.getString(3).orEmpty(), senses)
    }

    /** Убирает повторы: «собака» и «соба́ка» — одно слово (оставляем вариант с ударением). */
    private fun dedupe(items: List<String>): List<String> {
        val byKey = LinkedHashMap<String, String>()
        items.forEach { item ->
            val key = normalize(item)
            val prev = byKey[key]
            if (prev == null || (!prev.contains('\u0301') && item.contains('\u0301'))) byKey[key] = item
        }
        return byKey.values.toList()
    }

    private fun merge(list: List<Entry>): List<Entry> {
        val out = LinkedHashMap<String, Entry>()
        list.forEach { e ->
            val cleaned = Entry(e.word, e.pos, e.gender, e.pronunciation, e.senses.map { Sense(it.glosses, dedupe(it.translations)) })
            val key = normalize(e.word) + "|" + e.pos
            val prev = out[key]
            if (prev == null) {
                out[key] = cleaned
            } else {
                val known = prev.senses.flatMap { s -> s.translations.map { normalize(it) } }.toSet()
                val extra = cleaned.senses.mapNotNull { s ->
                    val fresh = s.translations.filter { normalize(it) !in known }
                    if (fresh.isEmpty()) null else Sense(s.glosses, fresh)
                }
                val word = if (e.word.contains('\u0301') && !prev.word.contains('\u0301')) e.word else prev.word
                out[key] = Entry(
                    word, prev.pos, prev.gender.ifEmpty { e.gender },
                    prev.pronunciation.ifEmpty { e.pronunciation }, prev.senses + extra
                )
            }
        }
        return out.values.toList()
    }

    /** Похожие слова по началу: для языков, где в словаре нет словоформ. */
    private fun prefixForms(db: SQLiteDatabase, key: String): List<Entry> {
        for (cut in 1..minOf(3, key.length - 3)) {
            val stem = key.dropLast(cut)
            val keys = mutableListOf<String>()
            db.rawQuery(
                "SELECT DISTINCT form FROM form WHERE form >= ? AND form < ? AND length(form) <= ? LIMIT 50",
                arrayOf(stem, stem + "\uFFFF", (key.length + 2).toString())
            ).use { c -> while (c.moveToNext()) keys += c.getString(0) }
            if (keys.isNotEmpty()) {
                val best = keys.sortedBy { kotlin.math.abs(it.length - key.length) }.take(6)
                val found = queryForms(db, best, key)
                if (found.isNotEmpty()) return found.take(3)
            }
        }
        return emptyList()
    }

    /** Статьи для слова: точные совпадения и словоформы, самые важные сверху. */
    suspend fun lookup(word: String, source: String, target: String): List<Entry> = withContext(Dispatchers.IO) {
        val db = database(pairOf(source, target)) ?: return@withContext emptyList()
        val key = normalize(word).trim('\'', '’', '-')
        if (key.isEmpty()) return@withContext emptyList()
        var result = queryForms(db, listOf(key), key)
        if (result.isEmpty() && source in setOf("ru", "uk", "be", "bg", "pl", "cs")) {
            result = queryForms(db, slavicCandidates(key), key)
        }
        if (result.isEmpty() && key.length >= 5) result = prefixForms(db, key)
        merge(result)
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
