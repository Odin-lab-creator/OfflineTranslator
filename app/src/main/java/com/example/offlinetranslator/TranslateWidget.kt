package com.example.offlinetranslator

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

/** Виджет на рабочий стол: три кнопки — перевод текста, скриншота и через камеру. */
class TranslateWidget : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, appWidgetIds: IntArray) {
        appWidgetIds.forEach { id ->
            val views = RemoteViews(context.packageName, R.layout.widget_translate)
            views.setOnClickPendingIntent(R.id.widget_text, open(context, 1, null))
            views.setOnClickPendingIntent(R.id.widget_screenshot, open(context, 2, ACTION_PICK_SCREENSHOT))
            views.setOnClickPendingIntent(R.id.widget_camera, open(context, 3, ACTION_OPEN_CAMERA))
            manager.updateAppWidget(id, views)
        }
    }

    private fun open(context: Context, requestCode: Int, action: String?): PendingIntent {
        val intent = Intent(context, MainActivity::class.java)
            .setAction(action ?: Intent.ACTION_MAIN)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
    }
}
