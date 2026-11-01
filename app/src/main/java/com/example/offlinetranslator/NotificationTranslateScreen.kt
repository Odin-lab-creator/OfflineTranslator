package com.example.offlinetranslator

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LifecycleResumeEffect

private enum class NotifyScope(val label: String) {
    MESSENGERS("Только мессенджеры и почта"),
    ALL("Все приложения")
}

fun openAppDetails(context: Context) {
    try {
        context.startActivity(
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + context.packageName))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    } catch (e: Exception) {
        // нет экрана сведений о приложении
    }
}

/** Экран «Перевод уведомлений». */
@Composable
fun NotificationTranslateScreen(vm: TranslatorViewModel, onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val settings = AppSettings.current()
    var access by remember { mutableStateOf(NotificationTranslateService.hasAccess(context)) }
    LifecycleResumeEffect(Unit) {
        access = NotificationTranslateService.hasAccess(context)
        onPauseOrDispose { }
    }
    val notifications = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }

    fun openAccess() {
        val detail = if (Build.VERSION.SDK_INT >= 30) {
            Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS)
                .putExtra(
                    Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME,
                    NotificationTranslateService.component(context).flattenToString()
                )
        } else null
        val list = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        try {
            context.startActivity(detail ?: list)
        } catch (e: Exception) {
            try {
                context.startActivity(list)
            } catch (e2: Exception) {
                vm.reportStatus("Откройте вручную: Настройки → Уведомления → Доступ к уведомлениям")
            }
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        ScreenHeader("Перевод уведомлений", onBack)
        GoldDivider()
        Text(
            "Сообщения на иностранном языке из Telegram, WhatsApp и других приложений сразу " +
                "приходят вторым уведомлением — уже с переводом. Нажмите на него, и откроется переписка.\n\n" +
                "Переводится только офлайн: текст сообщений никуда не отправляется. " +
                "Нужны скачанные модели языков собеседника и вашего языка.",
            color = p.text,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )

        Column(Modifier.fillMaxWidth().valhallaCard(p)) {
            SwitchRow(
                "Переводить уведомления",
                if (access) "Доступ к уведомлениям есть" else "Нужен доступ к уведомлениям",
                settings.notifyTranslate
            ) { on ->
                settings.updateNotifyTranslate(on)
                if (on) {
                    if (Build.VERSION.SDK_INT >= 33 &&
                        ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                        PackageManager.PERMISSION_GRANTED
                    ) {
                        notifications.launch(Manifest.permission.POST_NOTIFICATIONS)
                    }
                    if (!access) openAccess()
                }
            }
        }

        if (!access) {
            GoldButton("Дать доступ к уведомлениям", Modifier.fillMaxWidth()) { openAccess() }
            Text(
                "Если Android пишет «Ограниченная настройка» (так бывает с приложениями не из магазина):\n" +
                    "1. Нажмите кнопку ниже — откроются сведения о приложении.\n" +
                    "2. Нажмите ⋮ в правом верхнем углу → «Разрешить ограниченные настройки».\n" +
                    "3. Вернитесь сюда и снова нажмите «Дать доступ».",
                color = p.muted,
                fontSize = 13.sp,
                lineHeight = 19.sp
            )
            OutlineGoldButton("Сведения о приложении", Modifier.fillMaxWidth(), height = 46) { openAppDetails(context) }
        }

        SectionLabel("Мой язык — на него переводить")
        LanguageButton(settings.myLanguage, "Мой язык", vm.downloaded, Modifier.fillMaxWidth()) {
            settings.updateMyLanguage(it)
        }

        SectionLabel("Какие приложения")
        ChoiceCard(
            options = NotifyScope.entries,
            selected = if (settings.notifyAllApps) NotifyScope.ALL else NotifyScope.MESSENGERS,
            label = { it.label },
            onSelect = { settings.updateNotifyAllApps(it == NotifyScope.ALL) }
        )

        val missing = settings.myLanguage !in vm.downloaded
        if (missing) {
            Text(
                "Модель языка «${Languages.name(settings.myLanguage)}» ещё не скачана — скачайте её в разделе «Языковые модели».",
                color = p.gold,
                fontSize = 13.sp
            )
        }
    }
}
