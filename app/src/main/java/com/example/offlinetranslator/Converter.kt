package com.example.offlinetranslator

import android.content.Context
import java.net.HttpURLConnection
import java.net.URL
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Цены и единицы: находит в тексте цены в иностранной валюте, мили, футы, фунты, °F и т. п.
 * и пересчитывает в привычные: рубли (или свою валюту), километры, метры, килограммы, °C.
 * Курсы валют обновляются, когда есть интернет (ЦБ РФ, запасной источник — open.er-api.com),
 * и хранятся на телефоне.
 */
object Converter {
    /** Сколько рублей стоит одна единица валюты. */
    private val rubPer = HashMap<String, Double>()
    var ratesDate: String = ""
        private set
    private var prefs: android.content.SharedPreferences? = null

    val homeCurrencies = listOf("RUB", "USD", "EUR", "KZT", "BYN", "UAH", "UZS", "AMD", "GEL", "AZN", "KGS", "TRY", "CNY")

    private val symbols = mapOf(
        "RUB" to "₽", "USD" to "$", "EUR" to "€", "GBP" to "£", "JPY" to "¥", "CNY" to "¥", "TRY" to "₺",
        "INR" to "₹", "KRW" to "₩", "ILS" to "₪", "THB" to "฿", "VND" to "₫", "UAH" to "₴", "KZT" to "₸",
        "GEL" to "₾", "AZN" to "₼", "PHP" to "₱", "PLN" to "zł", "CZK" to "Kč", "BYN" to "Br", "UZS" to "сум",
        "AMD" to "֏", "KGS" to "сом", "BRL" to "R$", "CHF" to "CHF", "AED" to "AED"
    )

    fun init(context: Context) {
        if (prefs != null) return
        val p = context.getSharedPreferences("rates", Context.MODE_PRIVATE)
        prefs = p
        try {
            val json = JSONObject(p.getString("rates", "{}") ?: "{}")
            json.keys().forEach { rubPer[it] = json.getDouble(it) }
            ratesDate = p.getString("date", "").orEmpty()
        } catch (e: Exception) {
            // курсов ещё нет
        }
        rubPer["RUB"] = 1.0
    }

    fun hasRates() = rubPer.size > 5

    private fun get(url: String): String {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 8000
            connection.readTimeout = 12000
            if (connection.responseCode !in 200..299) error("ответ ${connection.responseCode}")
            return connection.inputStream.use { it.readBytes().decodeToString() }
        } finally {
            connection.disconnect()
        }
    }

    /** Обновляет курсы раз в 12 часов (нужен интернет). */
    suspend fun refreshRates(force: Boolean = false) = withContext(Dispatchers.IO) {
        val p = prefs ?: return@withContext
        if (!force && System.currentTimeMillis() - p.getLong("updated", 0L) < 12 * 3600_000L && hasRates()) return@withContext
        val fresh = HashMap<String, Double>()
        var date = ""
        try {
            val cbr = JSONObject(get("https://www.cbr-xml-daily.ru/daily_json.js"))
            date = cbr.optString("Date").take(10)
            val valute = cbr.getJSONObject("Valute")
            valute.keys().forEach { code ->
                val o = valute.getJSONObject(code)
                fresh[code] = o.getDouble("Value") / o.optDouble("Nominal", 1.0)
            }
        } catch (e: Exception) {
            // попробуем запасной источник
        }
        try {
            val er = JSONObject(get("https://open.er-api.com/v6/latest/USD"))
            val rates = er.getJSONObject("rates")
            val rubPerUsd = fresh["USD"] ?: rates.getDouble("RUB")
            rates.keys().forEach { code ->
                val perUsd = rates.getDouble(code)
                if (perUsd > 0 && !fresh.containsKey(code)) fresh[code] = rubPerUsd / perUsd
            }
            if (date.isEmpty()) date = er.optString("time_last_update_utc").take(16)
        } catch (e: Exception) {
            // нет второго источника
        }
        if (fresh.size > 5) {
            fresh["RUB"] = 1.0
            withContext(Dispatchers.Main) {
                rubPer.clear()
                rubPer.putAll(fresh)
                ratesDate = date
            }
            val json = JSONObject()
            fresh.forEach { (k, v) -> json.put(k, v) }
            p.edit().putString("rates", json.toString()).putString("date", date)
                .putLong("updated", System.currentTimeMillis()).apply()
        }
    }

    // ---- Числа ----

    private const val NUMBER = "\\d{1,3}(?:[ \\u00A0\\u202F,.'’]\\d{3})+(?:[.,]\\d{1,2})?|\\d+(?:[.,]\\d{1,2})?"

    /** «1,299.99» → 1299.99; «1.299,99» → 1299.99; «12,50» → 12.5; «1 299» → 1299. */
    fun parseNumber(raw: String): Double? {
        val s = raw.replace(Regex("[ \\u00A0\\u202F'’]"), "")
        val lastDot = s.lastIndexOf('.')
        val lastComma = s.lastIndexOf(',')
        val last = maxOf(lastDot, lastComma)
        val normalized = if (last >= 0 && s.length - last - 1 in 1..2) {
            s.substring(0, last).replace(".", "").replace(",", "") + "." + s.substring(last + 1)
        } else {
            s.replace(".", "").replace(",", "")
        }
        return normalized.toDoubleOrNull()
    }

    private val format = DecimalFormat("#,##0.##", DecimalFormatSymbols(Locale("ru")))
    private val formatInt = DecimalFormat("#,##0", DecimalFormatSymbols(Locale("ru")))

    private fun pretty(value: Double): String =
        if (kotlin.math.abs(value) >= 100) formatInt.format(value) else format.format(value)

    // ---- Валюты ----

    private val currencyBefore = listOf(
        "US\\$" to "USD", "A\\$" to "AUD", "C\\$" to "CAD", "HK\\$" to "HKD", "S\\$" to "SGD", "NZ\\$" to "NZD",
        "R\\$" to "BRL", "\\$" to "USD", "€" to "EUR", "£" to "GBP", "¥" to "JPY", "₺" to "TRY", "₹" to "INR",
        "₩" to "KRW", "₪" to "ILS", "฿" to "THB", "₫" to "VND", "₴" to "UAH", "₸" to "KZT", "₾" to "GEL",
        "₼" to "AZN", "₱" to "PHP", "CHF" to "CHF", "Rp" to "IDR", "RM" to "MYR"
    )
    private val currencyAfter = listOf(
        "€" to "EUR", "zł" to "PLN", "Kč" to "CZK", "Ft" to "HUF", "lei" to "RON", "TL" to "TRY", "₺" to "TRY",
        "元" to "CNY", "円" to "JPY", "원" to "KRW", "₫" to "VND", "₴" to "UAH", "грн" to "UAH", "₸" to "KZT",
        "тг" to "KZT", "₾" to "GEL", "лари" to "GEL", "₼" to "AZN", "֏" to "AMD", "драм" to "AMD", "сум" to "UZS",
        "сом" to "KGS", "лв" to "BGN", "din" to "RSD", "дин" to "RSD", "kn" to "EUR", "Br" to "BYN", "руб" to "RUB",
        "₽" to "RUB", "\\$" to "USD", "£" to "GBP", "¥" to "JPY", "₹" to "INR", "฿" to "THB", "baht" to "THB",
        "AED" to "AED", "dirham" to "AED", "SAR" to "SAR", "EGP" to "EGP"
    )
    private val isoCodes = listOf(
        "USD", "EUR", "GBP", "JPY", "CNY", "TRY", "INR", "KRW", "THB", "VND", "UAH", "KZT", "GEL", "AZN", "AMD",
        "UZS", "KGS", "BYN", "PLN", "CZK", "HUF", "RON", "BGN", "RSD", "CHF", "SEK", "NOK", "DKK", "AED", "SAR",
        "EGP", "ILS", "IDR", "MYR", "SGD", "HKD", "AUD", "CAD", "NZD", "BRL", "MXN", "ARS", "ZAR", "PHP", "QAR"
    )

    private val beforeRegex by lazy {
        val alternatives = currencyBefore.joinToString("|") { "(" + it.first + ")" } + "|" +
            isoCodes.joinToString("|") { "($it)" }
        Regex("(?<![\\p{L}])(?:$alternatives)\\s?($NUMBER)")
    }
    private val afterRegex by lazy {
        val alternatives = currencyAfter.joinToString("|") { "(" + it.first + ")" } + "|" +
            isoCodes.joinToString("|") { "($it)" }
        Regex("($NUMBER)\\s?(?:$alternatives)(?![\\p{L}])", RegexOption.IGNORE_CASE)
    }

    private fun codeFromGroups(m: MatchResult, offset: Int, list: List<Pair<String, String>>): String? {
        list.forEachIndexed { i, pair -> if (m.groups[offset + i] != null) return pair.second }
        isoCodes.forEachIndexed { i, code -> if (m.groups[offset + list.size + i] != null) return code }
        return null
    }

    class Found(val original: String, val converted: String)

    private fun homeSymbol(home: String) = symbols[home] ?: home

    /** Все пересчёты в тексте: цены в свою валюту и единицы в метрические. */
    fun convertAll(text: String, home: String = "RUB", sourceLang: String = ""): List<Found> {
        val result = mutableListOf<Found>()
        val seen = HashSet<IntRange>()
        fun overlaps(r: IntRange) = seen.any { it.first <= r.last && r.first <= it.last }

        if (hasRates()) {
            val homeRate = rubPer[home] ?: 1.0
            beforeRegex.findAll(text).forEach { m ->
                var code = codeFromGroups(m, 1, currencyBefore) ?: return@forEach
                if (code == "JPY" && sourceLang == "zh") code = "CNY"
                val numberGroup = 1 + currencyBefore.size + isoCodes.size
                val amount = parseNumber(m.groups[numberGroup]?.value ?: return@forEach) ?: return@forEach
                if (code == home) return@forEach
                val rate = rubPer[code] ?: return@forEach
                result += Found(m.value.trim(), "≈ ${pretty(amount * rate / homeRate)} ${homeSymbol(home)}")
                seen += m.range
            }
            afterRegex.findAll(text).forEach { m ->
                if (overlaps(m.range)) return@forEach
                val amount = parseNumber(m.groups[1]?.value ?: return@forEach) ?: return@forEach
                var code = codeFromGroups(m, 2, currencyAfter) ?: return@forEach
                if (code == "JPY" && sourceLang == "zh") code = "CNY"
                if (code == home) return@forEach
                val rate = rubPer[code] ?: return@forEach
                result += Found(m.value.trim(), "≈ ${pretty(amount * rate / homeRate)} ${homeSymbol(home)}")
                seen += m.range
            }
        }

        units.forEach { (regex, convert) ->
            regex.findAll(text).forEach { m ->
                if (overlaps(m.range)) return@forEach
                val amount = parseNumber(m.groups[1]?.value ?: return@forEach) ?: return@forEach
                val negative = m.value.trimStart().startsWith("-") || m.value.trimStart().startsWith("−")
                result += Found(m.value.trim(), convert(if (negative) -amount else amount))
                seen += m.range
            }
        }
        return result.distinctBy { it.original }
    }

    private fun unit(pattern: String) =
        Regex("(?<![\\p{L}\\d])[-−]?($NUMBER)\\s?(?:$pattern)(?![\\p{L}])", RegexOption.IGNORE_CASE)

    private val units: List<Pair<Regex, (Double) -> String>> by lazy {
        listOf(
            Regex("(?<![\\p{L}\\d])[-−]?($NUMBER)\\s?(?:°\\s?F|℉)(?![\\p{L}])") to { f: Double -> "≈ ${pretty((f - 32) * 5 / 9)} °C" },
            unit("mph|miles per hour") to { v: Double -> "≈ ${pretty(v * 1.609344)} км/ч" },
            unit("sq\\.?\\s?ft|square feet|ft²") to { v: Double -> "≈ ${pretty(v * 0.092903)} м²" },
            unit("fl\\.?\\s?oz") to { v: Double -> "≈ ${pretty(v * 29.5735)} мл" },
            unit("mi|miles?") to { v: Double -> "≈ ${pretty(v * 1.609344)} км" },
            unit("ft|feet|foot") to { v: Double -> "≈ ${pretty(v * 0.3048)} м" },
            unit("yd|yards?") to { v: Double -> "≈ ${pretty(v * 0.9144)} м" },
            unit("inch(?:es)?|in\\.|″") to { v: Double -> "≈ ${pretty(v * 2.54)} см" },
            unit("lbs?|pounds?") to { v: Double -> "≈ ${pretty(v * 0.45359237)} кг" },
            unit("oz|ounces?") to { v: Double -> "≈ ${pretty(v * 28.349523)} г" },
            unit("gal|gallons?") to { v: Double -> "≈ ${pretty(v * 3.785411)} л" },
            unit("qt|quarts?") to { v: Double -> "≈ ${pretty(v * 0.946353)} л" },
            unit("pints?") to { v: Double -> "≈ ${pretty(v * 0.473176)} л" }
        )
    }
}
