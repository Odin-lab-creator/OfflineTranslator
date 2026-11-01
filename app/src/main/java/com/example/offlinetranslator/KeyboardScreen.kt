package com.example.offlinetranslator

import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.view.inputmethod.InputMethodManager
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay

private fun keyboardEnabled(context: Context): Boolean {
    val imm = context.getSystemService(InputMethodManager::class.java) ?: return false
    return imm.enabledInputMethodList.any { it.packageName == context.packageName }
}

private fun keyboardSelected(context: Context): Boolean {
    val current = Settings.Secure.getString(context.contentResolver, Settings.Secure.DEFAULT_INPUT_METHOD).orEmpty()
    return current.startsWith(context.packageName + "/")
}

/** Экран настройки клавиатуры-переводчика. */
@Composable
fun KeyboardScreen(vm: TranslatorViewModel, onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val settings = AppSettings.current()
    var enabled by remember { mutableStateOf(keyboardEnabled(context)) }
    var selected by remember { mutableStateOf(keyboardSelected(context)) }
    var test by rememberSaveable { mutableStateOf("") }
    var picking by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        while (true) {
            enabled = keyboardEnabled(context)
            selected = keyboardSelected(context)
            delay(1000)
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        ScreenHeader("Клавиатура", onBack)
        GoldDivider()
        Text(
            "Своя клавиатура с кнопкой «Перевести». Пишете по-русски в Telegram, WhatsApp или любом " +
                "другом приложении, нажимаете «Перевести» — и в поле уже текст на языке собеседника. " +
                "Если вставить в поле сообщение собеседника, оно переведётся на ваш язык. «↶» возвращает исходный текст.",
            color = p.text,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )

        SectionLabel("Шаг 1. Включить")
        Text(
            if (enabled) "✓ Клавиатура включена" else "В списке клавиатур включите «Valhalla: клавиатура-переводчик». " +
                "Android покажет стандартное предупреждение для любой сторонней клавиатуры — " +
                "Valhalla ничего не отправляет в интернет (кроме DeepL, если вы его включили).",
            color = if (enabled) p.gold else p.muted,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
        if (!enabled) {
            GoldButton("Открыть список клавиатур", Modifier.fillMaxWidth()) {
                try {
                    context.startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } catch (e: Exception) {
                    vm.reportStatus("Откройте: Настройки → Общие настройки → Список клавиатур")
                }
            }
        }

        SectionLabel("Шаг 2. Выбрать")
        Text(
            if (selected) "✓ Сейчас используется Valhalla. Вернуться к своей клавиатуре — удерживайте 🌐 или пробел."
            else "Переключитесь на Valhalla. Обратно — так же, удерживая 🌐 или пробел на клавиатуре Valhalla.",
            color = if (selected) p.gold else p.muted,
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
        OutlineGoldButton("Выбрать клавиатуру", Modifier.fillMaxWidth(), enabled = enabled, height = 46) {
            context.getSystemService(InputMethodManager::class.java)?.showInputMethodPicker()
        }

        SectionLabel("Мой язык")
        LanguageButton(settings.myLanguage, "Мой язык", vm.downloaded, Modifier.fillMaxWidth()) {
            settings.updateMyLanguage(it)
        }

        SectionLabel("Языки собеседников")
        Column(Modifier.fillMaxWidth().valhallaCard(p).padding(vertical = 4.dp)) {
            settings.keyboardTargets.forEach { lang ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(start = 16.dp, end = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(Languages.name(lang), color = p.text, fontSize = 15.sp, modifier = Modifier.weight(1f))
                    if (settings.keyboardTargets.size > 1) {
                        LinkText("✕", p.muted, 16.sp) { settings.updateKeyboardTargets(settings.keyboardTargets - lang) }
                    }
                }
            }
            LinkText("+ Добавить язык", p.gold, 14.sp, Modifier.padding(start = 10.dp)) { picking = true }
        }
        Text(
            "Кнопка «RU ⇄ EN» на клавиатуре переключает язык собеседника. Модели языков должны быть скачаны.",
            color = p.muted,
            fontSize = 12.sp
        )

        SectionLabel("Попробовать")
        ValhallaTextField(
            test,
            { test = it },
            "Напишите что-нибудь и нажмите «Перевести»",
            Modifier
                .fillMaxWidth()
                .heightIn(min = 100.dp),
            singleLine = false
        )
    }

    if (picking) {
        LanguagePickerDialog(
            title = "Язык собеседника",
            selected = "",
            downloaded = vm.downloaded,
            onDismiss = { picking = false },
            onSelect = {
                picking = false
                if (it != settings.myLanguage) settings.updateKeyboardTargets(settings.keyboardTargets + it)
            }
        )
    }
}
