package com.example.offlinetranslator

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Перевод входящих уведомлений: сообщение на иностранном языке сразу показывается
 * отдельным уведомлением с переводом на родной язык. Только офлайн — переписка никуда не уходит.
 */
class NotificationTranslateService : NotificationListenerService() {
    private val scope = MainScope()

    /** Уже переведённые тексты, чтобы не дублировать при обновлениях уведомления. */
    private val seen = object : LinkedHashMap<String, Boolean>(64, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Boolean>?): Boolean = size > 300
    }

    /** Ключ исходного уведомления → номер нашего уведомления с переводом. */
    private val posted = HashMap<String, Int>()
    private var nextId = 7000

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val settings = AppSettings.get(applicationContext)
        if (!settings.notifyTranslate) return
        if (sbn.packageName == packageName) return
        if (!settings.notifyAllApps && sbn.packageName !in MESSENGERS) return
        val notification = sbn.notification ?: return
        if (notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return
        if (sbn.isOngoing) return
        val (sender, text) = extract(notification) ?: return
        if (text.count { it.isLetter() } < 3) return
        val dedupe = sbn.packageName + "|" + text
        if (seen.containsKey(dedupe)) return
        seen[dedupe] = true

        scope.launch {
            try {
                val target = settings.myLanguage
                val source = TranslationEngine.detect(text) ?: return@launch
                if (source == target) return@launch
                val downloaded = TranslationEngine.downloadedLanguages()
                if (source !in downloaded || target !in downloaded) return@launch
                val translated = TranslationEngine.translate(
                    source, target, text.take(2000), settings.wifiOnly, allowOnline = false
                )
                if (translated.isBlank() || translated.equals(text, ignoreCase = true)) return@launch
                show(sbn, sender, text, translated, source)
            } catch (e: Exception) {
                // не получилось — просто не показываем перевод
            }
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        val id = posted.remove(sbn.key) ?: return
        try {
            NotificationManagerCompat.from(this).cancel(id)
        } catch (e: Exception) {
            // ничего страшного
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private fun extract(notification: Notification): Pair<String, String>? {
        try {
            val style = NotificationCompat.MessagingStyle.extractMessagingStyleFromNotification(notification)
            val last = style?.messages?.lastOrNull()
            val text = last?.text?.toString().orEmpty()
            if (text.isNotBlank()) {
                val sender = last?.person?.name?.toString()
                    ?: style?.conversationTitle?.toString()
                    ?: ""
                return sender to text
            }
        } catch (e: Exception) {
            // не стиль переписки — читаем обычные поля
        }
        val extras = notification.extras ?: return null
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString().orEmpty()
        return if (text.isBlank()) null else title to text
    }

    private fun appName(sbn: StatusBarNotification): String {
        try {
            @Suppress("DEPRECATION")
            val info = sbn.notification.extras?.get("android.appInfo") as? ApplicationInfo
            if (info != null) return info.loadLabel(packageManager).toString()
        } catch (e: Exception) {
            // попробуем по имени пакета
        }
        return try {
            packageManager.getApplicationLabel(packageManager.getApplicationInfo(sbn.packageName, 0)).toString()
        } catch (e: Exception) {
            sbn.packageName
        }
    }

    private fun show(sbn: StatusBarNotification, sender: String, original: String, translated: String, source: String) {
        val manager = getSystemService(NotificationManager::class.java) ?: return
        ensureChannel(this, manager)
        val id = posted.getOrPut(sbn.key) { nextId++ }
        val title = listOf(appName(sbn), sender).filter { it.isNotBlank() }.distinct().joinToString(" · ")
        val builder = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_rune)
            .setColor(0xFFD4AF5A.toInt())
            .setContentTitle(title)
            .setContentText(translated)
            .setSubText("перевод")
            .setStyle(
                NotificationCompat.BigTextStyle()
                    .bigText(translated + "\n\n" + Languages.name(source) + ": " + original)
            )
            .setAutoCancel(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setSilent(true)
        sbn.notification.contentIntent?.let { builder.setContentIntent(it) }
        try {
            manager.notify(id, builder.build())
        } catch (e: Exception) {
            // нет разрешения на уведомления
        }
    }

    companion object {
        const val CHANNEL = "notification_translations"

        val MESSENGERS = setOf(
            "org.telegram.messenger", "org.telegram.messenger.web", "org.telegram.plus",
            "org.thunderdog.challegram", "com.whatsapp", "com.whatsapp.w4b", "com.viber.voip",
            "com.facebook.orca", "com.facebook.mlite", "com.instagram.android", "org.thoughtcrime.securesms",
            "com.vkontakte.android", "ru.oneme.app", "com.discord", "com.tencent.mm", "jp.naver.line.android",
            "com.kakao.talk", "com.snapchat.android", "com.skype.raider", "com.microsoft.teams", "com.Slack",
            "com.google.android.apps.messaging", "com.samsung.android.messaging", "com.imo.android.imoim",
            "com.zhiliaoapp.musically", "com.ss.android.ugc.trill", "com.twitter.android", "com.reddit.frontpage",
            "com.google.android.gm", "com.linkedin.android", "com.facebook.katana", "ch.threema.app",
            "im.vector.app", "com.wire", "com.icq.mobile.client", "ru.ok.android", "com.tinder", "com.bumble.app",
            "com.badoo.mobile", "com.hellotalk", "com.tandem"
        )

        fun ensureChannel(context: Context, manager: NotificationManager) {
            if (Build.VERSION.SDK_INT < 26) return
            if (manager.getNotificationChannel(CHANNEL) != null) return
            val channel = NotificationChannel(CHANNEL, "Переводы уведомлений", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Перевод входящих сообщений на иностранном языке"
                setSound(null, null)
                enableVibration(false)
            }
            manager.createNotificationChannel(channel)
        }

        fun hasAccess(context: Context): Boolean =
            NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)

        fun component(context: Context) = ComponentName(context, NotificationTranslateService::class.java)
    }
}
