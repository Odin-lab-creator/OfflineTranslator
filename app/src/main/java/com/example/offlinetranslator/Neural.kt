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
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Улучшенный офлайн-движок (бета): нейросети Opus-MT (Helsinki-NLP), ~100 МБ на направление.
 * Если прямой модели нет, переводит через английский (например, de → en → ru).
 */
object Neural {
    class Available(val pair: String, val bytes: Long)

    private const val BASE = "https://github.com/Odin-lab-creator/OfflineTranslator/releases/download/neural-models/"

    @Volatile
    var enabled = true

    var available by mutableStateOf<List<Available>>(emptyList())
        private set
    var downloaded by mutableStateOf<Set<String>>(emptySet())
        private set
    val progress = mutableStateMapOf<String, Float>()

    private var dir: File? = null
    private val loaded = LinkedHashMap<String, NeuralMt>()
    private val lock = Mutex()

    fun init(context: Context) {
        if (dir != null) return
        val d = File(context.filesDir, "neural").apply { mkdirs() }
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
            Available(o.getString("pair"), o.optLong("size"))
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

    /** Цепочка моделей для пары: прямая или через английский. */
    private fun route(source: String, target: String): List<String>? {
        val direct = "$source-$target"
        if (direct in downloaded) return listOf(direct)
        if (source != "en" && target != "en" && "$source-en" in downloaded && "en-$target" in downloaded) {
            return listOf("$source-en", "en-$target")
        }
        return null
    }

    fun ready(source: String, target: String): Boolean = enabled && source != target && route(source, target) != null

    suspend fun download(pair: String) {
        val d = dir ?: return
        if (progress.containsKey(pair)) return
        progress[pair] = 0f
        try {
            withContext(Dispatchers.IO) {
                val target = File(d, pair)
                target.deleteRecursively()
                target.mkdirs()
                val connection = URL("$BASE$pair.zip").openConnection() as HttpURLConnection
                connection.connectTimeout = 10000
                connection.readTimeout = 30000
                try {
                    if (connection.responseCode !in 200..299) error("сервер ответил ${connection.responseCode}")
                    val total = connection.contentLengthLong.takeIf { it > 0 }
                        ?: available.firstOrNull { it.pair == pair }?.bytes ?: 0L
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
                    val root = target.canonicalPath + File.separator
                    ZipInputStream(counting.buffered(65536)).use { zip ->
                        while (true) {
                            val entry = zip.nextEntry ?: break
                            val name = entry.name.removePrefix("./")
                            if (name.isEmpty()) continue
                            val out = File(target, name)
                            if (!out.canonicalPath.startsWith(root)) continue
                            if (entry.isDirectory) {
                                out.mkdirs()
                            } else {
                                out.parentFile?.mkdirs()
                                out.outputStream().use { zip.copyTo(it, 65536) }
                            }
                        }
                    }
                    check(File(target, "encoder.onnx").exists() && File(target, "decoder.onnx").exists()) { "архив модели повреждён" }
                    File(target, ".ready").writeText("ok")
                } catch (e: Exception) {
                    target.deleteRecursively()
                    throw e
                } finally {
                    connection.disconnect()
                }
            }
            downloaded = downloaded + pair
        } finally {
            progress.remove(pair)
        }
    }

    suspend fun delete(pair: String) {
        lock.withLock {
            loaded.remove(pair)?.close()
        }
        withContext(Dispatchers.IO) { dir?.let { File(it, pair).deleteRecursively() } }
        downloaded = downloaded - pair
    }

    private fun model(pair: String): NeuralMt {
        loaded[pair]?.let { return it }
        val folder = File(dir ?: error("нет папки моделей"), pair)
        val threads = Runtime.getRuntime().availableProcessors().coerceIn(2, 4)
        val created = NeuralMt(folder, threads)
        loaded[pair] = created
        while (loaded.size > 2) {
            val eldest = loaded.entries.first()
            loaded.remove(eldest.key)
            eldest.value.close()
        }
        return created
    }

    private val sentenceEnd = Regex("(?<=[.!?…。！？])\\s+")

    private fun translateWith(mt: NeuralMt, text: String): String =
        text.split('\n').joinToString("\n") { line ->
            if (line.isBlank()) line else {
                line.trim().split(sentenceEnd).filter { it.isNotBlank() }.joinToString(" ") { sentence ->
                    // Очень длинные «предложения» режем по запятым, чтобы модель не теряла смысл.
                    if (sentence.length <= 400) mt.translate(sentence) else {
                        sentence.chunked(380).joinToString(" ") { mt.translate(it) }
                    }
                }
            }
        }

    /** Перевод нейросетью. Вызывать, только если ready(source, target). */
    suspend fun translate(source: String, target: String, text: String): String =
        lock.withLock {
            withContext(Dispatchers.Default) {
                val chain = route(source, target) ?: error("нет нейросетевой модели")
                var current = text
                chain.forEach { pair -> current = translateWith(model(pair), current) }
                current
            }
        }
}
