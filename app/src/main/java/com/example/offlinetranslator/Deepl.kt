package com.example.offlinetranslator

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

class DeeplException(message: String) : IOException(message)

enum class Formality(val label: String, val api: String) {
    DEFAULT("Как решит DeepL", "default"),
    MORE("На «вы», вежливо", "prefer_more"),
    LESS("На «ты», по-дружески", "prefer_less")
}

/**
 * Онлайн-перевод через DeepL API (по желанию). Нужен свой ключ: бесплатный план даёт
 * 500 000 символов в месяц. Без интернета или при ошибке перевод идёт офлайн, как обычно.
 */
object Deepl {
    @Volatile
    var enabled = false

    @Volatile
    var key = ""

    @Volatile
    var formality = Formality.DEFAULT

    /** Последняя ошибка, чтобы показать её в настройках. */
    @Volatile
    var lastError = ""

    private var app: Context? = null

    private val supported = setOf(
        "ar", "bg", "cs", "da", "de", "el", "en", "es", "et", "fi", "fr", "he", "hu", "id", "it",
        "ja", "ko", "lt", "lv", "no", "nl", "pl", "pt", "ro", "ru", "sk", "sl", "sv", "th", "tr",
        "uk", "vi", "zh"
    )

    fun init(context: Context) {
        app = context.applicationContext
    }

    private fun host(): String =
        if (key.trim().endsWith(":fx")) "https://api-free.deepl.com" else "https://api.deepl.com"

    private fun online(): Boolean {
        val context = app ?: return false
        return try {
            val cm = context.getSystemService(ConnectivityManager::class.java) ?: return false
            val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
            caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
        } catch (e: Exception) {
            false
        }
    }

    /** Можно ли сейчас перевести эту пару через DeepL. */
    fun usable(source: String, target: String): Boolean =
        enabled && key.isNotBlank() && source in supported && target in supported && online()

    private fun sourceCode(lang: String) = if (lang == "no") "NB" else lang.uppercase()

    private fun targetCode(lang: String) = when (lang) {
        "en" -> "EN-US"
        "pt" -> "PT-BR"
        "zh" -> "ZH-HANS"
        "no" -> "NB"
        else -> lang.uppercase()
    }

    suspend fun translate(source: String, target: String, text: String): String = withContext(Dispatchers.IO) {
        val (masked, withGlossary) = Glossary.maskXml(text, source, target)
        val body = JSONObject()
            .put("text", JSONArray().put(if (withGlossary) masked else text))
            .put("source_lang", sourceCode(source))
            .put("target_lang", targetCode(target))
        if (formality != Formality.DEFAULT) body.put("formality", formality.api)
        if (withGlossary) {
            body.put("tag_handling", "xml")
            body.put("ignore_tags", JSONArray().put("keep"))
        }
        val response = request("/v2/translate", body.toString())
        val result = JSONObject(response).getJSONArray("translations").getJSONObject(0).getString("text")
        lastError = ""
        if (withGlossary) Glossary.unmaskXml(result) else result
    }

    /** Сколько символов израсходовано в этом месяце: пара (использовано, лимит). */
    suspend fun usage(): Pair<Long, Long> = withContext(Dispatchers.IO) {
        val json = JSONObject(request("/v2/usage", null))
        json.optLong("character_count") to json.optLong("character_limit")
    }

    private fun request(path: String, body: String?): String {
        val connection = URL(host() + path).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 7000
            connection.readTimeout = 15000
            connection.setRequestProperty("Authorization", "DeepL-Auth-Key ${key.trim()}")
            connection.setRequestProperty("User-Agent", "ValhallaTranslate/${BuildConfig.VERSION_NAME}")
            if (body != null) {
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            if (code !in 200..299) {
                val message = when (code) {
                    403 -> "DeepL: неверный ключ"
                    456 -> "DeepL: лимит символов на этот месяц исчерпан"
                    429 -> "DeepL: слишком много запросов, попробуйте позже"
                    400 -> "DeepL: эта пара языков не поддерживается"
                    else -> "DeepL: ошибка $code"
                }
                lastError = message
                throw DeeplException(message)
            }
            return connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } catch (e: IOException) {
            if (e !is DeeplException) lastError = "DeepL недоступен: ${e.localizedMessage ?: "нет связи"}"
            throw e
        } finally {
            connection.disconnect()
        }
    }
}
