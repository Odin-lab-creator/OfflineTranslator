package com.example.offlinetranslator

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.zip.ZipInputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.vosk.LibVosk
import org.vosk.LogLevel
import org.vosk.Model

/**
 * Офлайн-распознавание речи (Vosk): голосовой ввод без интернета и живые субтитры.
 * Модели (~40–50 МБ на язык) скачиваются по одной с GitHub.
 */
object Voice {
    class Available(val lang: String, val bytes: Long)

    private const val BASE = "https://github.com/Odin-lab-creator/OfflineTranslator/releases/download/voice-models/"

    var available by mutableStateOf<List<Available>>(emptyList())
        private set
    var downloaded by mutableStateOf<Set<String>>(emptySet())
        private set
    val progress = mutableStateMapOf<String, Float>()

    private var dir: File? = null
    private var loadedLang: String? = null
    private var loadedModel: Model? = null

    fun init(context: Context) {
        if (dir != null) return
        val d = File(context.filesDir, "vosk").apply { mkdirs() }
        dir = d
        downloaded = d.listFiles().orEmpty()
            .filter { it.isDirectory && File(it, ".ready").exists() }
            .map { it.name }
            .toSet()
        try {
            val cached = File(d, "index.json")
            if (cached.exists()) available = parseIndex(cached.readText())
        } catch (e: Exception) {
            // нет кэша
        }
    }

    private fun parseIndex(raw: String): List<Available> {
        val models = JSONObject(raw).getJSONArray("models")
        return (0 until models.length()).map {
            val o = models.getJSONObject(it)
            Available(o.getString("lang"), o.optLong("size"))
        }
    }

    suspend fun refreshIndex() = withContext(Dispatchers.IO) {
        val connection = URL(BASE + "index.json").openConnection() as HttpURLConnection
        val text = try {
            connection.connectTimeout = 10000
            connection.readTimeout = 20000
            if (connection.responseCode !in 200..299) error("сервер ответил ${connection.responseCode}")
            connection.inputStream.use { it.readBytes().decodeToString() }
        } finally {
            connection.disconnect()
        }
        val list = parseIndex(text)
        dir?.let { File(it, "index.json").writeText(text) }
        withContext(Dispatchers.Main) { available = list }
    }

    fun isAvailable(lang: String) = available.any { it.lang == lang }

    fun isReady(lang: String) = lang in downloaded

    suspend fun download(lang: String) {
        val d = dir ?: return
        if (progress.containsKey(lang)) return
        progress[lang] = 0f
        try {
            withContext(Dispatchers.IO) {
                val target = File(d, lang)
                target.deleteRecursively()
                target.mkdirs()
                val connection = URL("$BASE$lang.zip").openConnection() as HttpURLConnection
                connection.connectTimeout = 10000
                connection.readTimeout = 30000
                try {
                    if (connection.responseCode !in 200..299) error("сервер ответил ${connection.responseCode}")
                    val total = connection.contentLengthLong.takeIf { it > 0 }
                        ?: available.firstOrNull { it.lang == lang }?.bytes ?: 0L
                    var read = 0L
                    val counting = object : java.io.FilterInputStream(connection.inputStream) {
                        override fun read(b: ByteArray, off: Int, len: Int): Int {
                            val n = super.read(b, off, len)
                            if (n > 0) {
                                read += n
                                if (total > 0) progress[lang] = (read.toFloat() / total).coerceIn(0f, 1f)
                            }
                            return n
                        }
                    }
                    val root = target.canonicalPath + File.separator
                    ZipInputStream(counting.buffered(65536)).use { zip ->
                        while (true) {
                            val entry = zip.nextEntry ?: break
                            // В архиве всё лежит в папке vosk-model-…: убираем её.
                            val relative = entry.name.substringAfter('/', "")
                            if (relative.isEmpty()) continue
                            val out = File(target, relative)
                            if (!out.canonicalPath.startsWith(root)) continue
                            if (entry.isDirectory) {
                                out.mkdirs()
                            } else {
                                out.parentFile?.mkdirs()
                                out.outputStream().use { zip.copyTo(it, 65536) }
                            }
                        }
                    }
                    File(target, ".ready").writeText("ok")
                } catch (e: Exception) {
                    target.deleteRecursively()
                    throw e
                } finally {
                    connection.disconnect()
                }
            }
            downloaded = downloaded + lang
        } finally {
            progress.remove(lang)
        }
    }

    fun delete(lang: String) {
        synchronized(this) {
            if (loadedLang == lang) {
                loadedModel?.close()
                loadedModel = null
                loadedLang = null
            }
        }
        dir?.let { File(it, lang).deleteRecursively() }
        downloaded = downloaded - lang
    }

    /** Загружает модель языка (несколько секунд). Держим в памяти одну модель. */
    suspend fun model(lang: String): Model = withContext(Dispatchers.IO) {
        synchronized(this@Voice) {
            loadedModel?.takeIf { loadedLang == lang }?.let { return@withContext it }
            loadedModel?.close()
            loadedModel = null
            loadedLang = null
            LibVosk.setLogLevel(LogLevel.WARNINGS)
            val path = File(dir ?: error("нет папки моделей"), lang)
            check(File(path, ".ready").exists()) { "модель речи не скачана" }
            val created = Model(path.absolutePath)
            loadedModel = created
            loadedLang = lang
            created
        }
    }

    /** Текст из ответа Vosk: {"text": "..."} или {"partial": "..."}. */
    fun textOf(json: String?): String =
        try {
            val o = JSONObject(json ?: "{}")
            o.optString("text").ifEmpty { o.optString("partial") }.trim()
        } catch (e: Exception) {
            ""
        }
}
