package com.example.offlinetranslator

import android.content.Context
import androidx.compose.runtime.mutableStateListOf
import org.json.JSONArray
import org.json.JSONObject

data class HistoryEntry(
    val id: Long,
    val source: String,
    val target: String,
    val text: String,
    val result: String,
    val time: Long,
    val favorite: Boolean
)

/** История переводов и избранное. Хранится на устройстве, новые записи сверху. */
class HistoryStore private constructor(context: Context) {
    private val prefs = context.getSharedPreferences("history", Context.MODE_PRIVATE)

    val entries = mutableStateListOf<HistoryEntry>()

    init {
        load()
    }

    /** Добавляет перевод в историю и возвращает его запись. */
    fun add(source: String, target: String, text: String, result: String): HistoryEntry? {
        val t = text.trim()
        val r = result.trim()
        if (t.isEmpty() || r.isEmpty()) return null
        val now = System.currentTimeMillis()

        // Тот же текст уже был: поднимаем запись наверх, сохраняя отметку избранного.
        val same = entries.indexOfFirst { it.text == t && it.source == source && it.target == target }
        if (same >= 0) {
            val updated = entries[same].copy(result = r, time = now)
            entries.removeAt(same)
            entries.add(0, updated)
            save()
            return updated
        }

        // Пользователь продолжает печатать ту же фразу: обновляем последнюю запись, а не плодим новые.
        val last = entries.firstOrNull()
        if (last != null && !last.favorite && last.source == source && last.target == target &&
            now - last.time < 60_000 && (t.startsWith(last.text) || last.text.startsWith(t))
        ) {
            val updated = last.copy(text = t, result = r, time = now)
            entries[0] = updated
            save()
            return updated
        }

        val entry = HistoryEntry(now, source, target, t, r, now, favorite = false)
        entries.add(0, entry)
        trim()
        save()
        return entry
    }

    fun find(source: String, target: String, text: String): HistoryEntry? =
        entries.firstOrNull { it.text == text.trim() && it.source == source && it.target == target }

    fun toggleFavorite(id: Long) {
        val index = entries.indexOfFirst { it.id == id }
        if (index < 0) return
        entries[index] = entries[index].copy(favorite = !entries[index].favorite)
        save()
    }

    fun delete(id: Long) {
        entries.removeAll { it.id == id }
        save()
    }

    /** Удаляет всё, кроме избранного. */
    fun clearHistory() {
        entries.removeAll { !it.favorite }
        save()
    }

    private fun trim() {
        var regular = 0
        val keep = entries.filter { it.favorite || ++regular <= MAX_ENTRIES }
        if (keep.size != entries.size) {
            entries.clear()
            entries.addAll(keep)
        }
    }

    private fun load() {
        val raw = prefs.getString("entries", null) ?: return
        try {
            val array = JSONArray(raw)
            for (i in 0 until array.length()) {
                val o = array.getJSONObject(i)
                entries.add(
                    HistoryEntry(
                        id = o.getLong("id"),
                        source = o.getString("s"),
                        target = o.getString("t"),
                        text = o.getString("x"),
                        result = o.getString("r"),
                        time = o.getLong("time"),
                        favorite = o.optBoolean("f", false)
                    )
                )
            }
        } catch (e: Exception) {
            entries.clear()
        }
    }

    private fun save() {
        val array = JSONArray()
        entries.forEach {
            array.put(
                JSONObject()
                    .put("id", it.id)
                    .put("s", it.source)
                    .put("t", it.target)
                    .put("x", it.text)
                    .put("r", it.result)
                    .put("time", it.time)
                    .put("f", it.favorite)
            )
        }
        prefs.edit().putString("entries", array.toString()).apply()
    }

    companion object {
        private const val MAX_ENTRIES = 300

        @Volatile
        private var instance: HistoryStore? = null

        fun get(context: Context): HistoryStore =
            instance ?: synchronized(this) {
                instance ?: HistoryStore(context.applicationContext).also { instance = it }
            }
    }
}
