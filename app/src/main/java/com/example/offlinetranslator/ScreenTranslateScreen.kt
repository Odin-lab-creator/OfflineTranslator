package com.example.offlinetranslator

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect

/** Экран включения перевода экрана поверх других приложений. */
@Composable
fun ScreenTranslateScreen(onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    var canOverlay by remember { mutableStateOf(Settings.canDrawOverlays(context)) }
    var message by remember { mutableStateOf("") }

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        canOverlay = Settings.canDrawOverlays(context)
    }

    val consent = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val data = result.data
        if (result.resultCode == Activity.RESULT_OK && data != null) {
            val intent = Intent(context, ScreenTranslateService::class.java)
                .putExtra(ScreenTranslateService.EXTRA_CODE, result.resultCode)
                .putExtra(ScreenTranslateService.EXTRA_DATA, data)
            ContextCompat.startForegroundService(context, intent)
            message = "Готово! Сверните приложение — золотая кнопка с руной будет поверх экрана."
        } else {
            message = "Без разрешения на запись экрана перевод экрана не работает."
        }
    }
    val notifications = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) {
        startCapture(context) { consent.launch(it) }
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
        ScreenHeader("Перевод экрана", onBack)
        GoldDivider()
        Text(
            "Поверх всех приложений появится золотая кнопка с руной. Нажмите её — текст на экране " +
                "распознается и перевод появится прямо поверх оригинала. Нажатие в любом месте закрывает перевод.\n\n" +
                "Кнопку можно перетаскивать. Долгое нажатие на неё выключает перевод экрана.\n\n" +
                "Язык перевода — тот, что выбран справа на главном экране. Алфавит берётся из настроек распознавания.",
            color = p.text,
            fontSize = 15.sp,
            lineHeight = 22.sp
        )

        SectionLabel("Шаг 1 · показ поверх других приложений")
        if (canOverlay) {
            Text("✓ Разрешено", color = p.gold, fontSize = 15.sp)
        } else {
            OutlineGoldButton("Разрешить показ поверх приложений", modifier = Modifier.fillMaxWidth(), height = 46) {
                context.startActivity(
                    Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
                )
            }
            Text(
                "Откроются настройки Android: включите переключатель для Valhalla Translate и вернитесь.",
                color = p.muted,
                fontSize = 13.sp
            )
        }

        SectionLabel("Шаг 2 · включить")
        if (ScreenTranslateService.running) {
            Text("Перевод экрана работает", color = p.gold, fontFamily = FontFamily.Serif, fontSize = 18.sp)
            OutlineGoldButton("Выключить", modifier = Modifier.fillMaxWidth(), height = 46) {
                context.startService(
                    Intent(context, ScreenTranslateService::class.java)
                        .setAction(ScreenTranslateService.ACTION_STOP)
                )
            }
        } else {
            GoldButton("Включить перевод экрана", modifier = Modifier.fillMaxWidth(), enabled = canOverlay) {
                message = ""
                val needsNotifications = Build.VERSION.SDK_INT >= 33 &&
                    ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                    PackageManager.PERMISSION_GRANTED
                if (needsNotifications) {
                    notifications.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else {
                    startCapture(context) { consent.launch(it) }
                }
            }
            Text(
                "Android спросит разрешение на запись экрана — выберите «Весь экран». " +
                    "Оно действует, пока перевод экрана включён.",
                color = p.muted,
                fontSize = 13.sp
            )
        }
        if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 14.sp)
    }
}

private fun startCapture(context: Context, launch: (Intent) -> Unit) {
    val manager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    launch(manager.createScreenCaptureIntent())
}
