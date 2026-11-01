package com.example.offlinetranslator

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

const val ACTION_OPEN_FLASHCARDS = "com.example.offlinetranslator.OPEN_FLASHCARDS"

/** Виджет «Слово дня»: каждый день новое слово из избранного, «↻» — следующее. */
class WordWidget : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, appWidgetIds: IntArray) {
        render(context, manager, appWidgetIds)
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION_NEXT) {
            val prefs = context.getSharedPreferences("word_widget", Context.MODE_PRIVATE)
            prefs.edit().putInt("offset", prefs.getInt("offset", 0) + 1).apply()
            refresh(context)
            return
        }
        super.onReceive(context, intent)
    }

    companion object {
        private const val ACTION_NEXT = "com.example.offlinetranslator.WORD_NEXT"

        /** Обновить все виджеты «Слово дня» (например, после добавления в избранное). */
        fun refresh(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, WordWidget::class.java))
            if (ids.isNotEmpty()) render(context, manager, ids)
        }

        private fun render(context: Context, manager: AppWidgetManager, ids: IntArray) {
            val history = HistoryStore.get(context)
            val favorites = history.entries.filter { it.favorite && it.text.length <= 80 }
            val pool = favorites.ifEmpty { history.entries.filter { it.text.length <= 40 }.take(30) }
            val prefs = context.getSharedPreferences("word_widget", Context.MODE_PRIVATE)
            val day = (System.currentTimeMillis() / 86_400_000L).toInt()
            val entry = if (pool.isEmpty()) null else {
                val index = Math.floorMod(day + prefs.getInt("offset", 0), pool.size)
                pool[index]
            }

            val open = PendingIntent.getActivity(
                context,
                40,
                Intent(context, MainActivity::class.java)
                    .setAction(ACTION_OPEN_FLASHCARDS)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            val next = PendingIntent.getBroadcast(
                context,
                41,
                Intent(context, WordWidget::class.java).setAction(ACTION_NEXT),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )

            ids.forEach { id ->
                val views = RemoteViews(context.packageName, R.layout.widget_word)
                if (entry == null) {
                    views.setTextViewText(R.id.word_text, "Valhalla")
                    views.setTextViewText(R.id.word_translation, "Отмечайте переводы звёздочкой ★ — они будут появляться здесь")
                    views.setTextViewText(R.id.word_pair, "")
                } else {
                    views.setTextViewText(R.id.word_text, entry.text)
                    views.setTextViewText(R.id.word_translation, entry.result)
                    views.setTextViewText(
                        R.id.word_pair,
                        "${Languages.name(entry.source)} → ${Languages.name(entry.target)}"
                    )
                }
                views.setOnClickPendingIntent(R.id.word_root, open)
                views.setOnClickPendingIntent(R.id.word_next, next)
                manager.updateAppWidget(id, views)
            }
        }
    }
}
