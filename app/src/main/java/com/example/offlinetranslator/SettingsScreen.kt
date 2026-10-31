package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SettingsScreen(
    settings: AppSettings,
    vm: TranslatorViewModel,
    onBack: () -> Unit,
    onOpenModels: () -> Unit
) {
    val p = LocalPalette.current
    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ScreenHeader("Настройки", onBack)
        GoldDivider()

        SectionLabel("Тема")
        ChoiceCard(
            options = ThemeMode.entries,
            selected = settings.themeMode,
            label = { it.label },
            onSelect = settings::updateTheme
        )

        SectionLabel("Размер шрифта перевода")
        ChoiceCard(
            options = FontSize.entries,
            selected = settings.fontSize,
            label = { it.label },
            onSelect = settings::updateFontSize
        )

        SectionLabel("Перевод")
        Column(Modifier.fillMaxWidth().valhallaCard(p)) {
            SwitchRow(
                "Автоперевод при вводе",
                "Перевод появляется сам через полсекунды после ввода",
                settings.autoTranslate,
                settings::updateAutoTranslate
            )
            SwitchRow(
                "Скачивать модели только по Wi-Fi",
                "Экономит мобильный интернет",
                settings.wifiOnly,
                settings::updateWifiOnly
            )
            SwitchRow(
                "Вибрация при нажатиях",
                "Лёгкий отклик кнопок",
                settings.haptics,
                settings::updateHaptics
            )
        }

        SectionLabel("Текст на картинках и камере")
        ChoiceCard(
            options = OcrScript.entries,
            selected = settings.ocrScript,
            label = { it.label },
            onSelect = settings::updateOcrScript
        )

        SectionLabel("Языковые модели")
        OutlineGoldButton(
            "Управлять моделями",
            modifier = Modifier.fillMaxWidth(),
            onClick = onOpenModels
        )

        SectionLabel("Обновления")
        Column(
            Modifier
                .fillMaxWidth()
                .valhallaCard(p)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("Установлена версия ${BuildConfig.VERSION_NAME}", color = p.text, fontSize = 15.sp)
            val info = vm.update
            if (info != null) {
                Text("Доступна версия ${info.versionName}", color = p.gold, fontSize = 15.sp)
                GoldButton(
                    vm.updateProgress?.let { "Скачиваю ${(it * 100).toInt()}%" } ?: "Обновить",
                    modifier = Modifier.fillMaxWidth(),
                    enabled = vm.updateProgress == null
                ) { vm.installUpdate() }
            } else {
                OutlineGoldButton(
                    "Проверить обновления",
                    modifier = Modifier.fillMaxWidth(),
                    height = 46
                ) { vm.checkForUpdates(manual = true) }
            }
            if (vm.updateMessage.isNotEmpty()) Text(vm.updateMessage, color = p.muted, fontSize = 13.sp)
        }

        SectionLabel("О приложении")
        Text(
            "Valhalla Translate ${BuildConfig.VERSION_NAME}\n\n" +
                "Переводит прямо на устройстве (Google ML Kit). Интернет нужен только для первой " +
                "загрузки языковых моделей.\n\n" +
                "Перевод из любого приложения: выделите текст и выберите «Valhalla Translate» в меню.\n\n" +
                "Перевод по скриншоту: кнопка «Скриншот» или «Поделиться → Valhalla Translate» из галереи.\n\n" +
                "Алфавит «Авто» выбирается по исходному языку: для русского или украинского текста " +
                "поставьте исходным «Русский» или «Украинский».\n\n" +
                "Голосовой ввод использует службу распознавания речи телефона, озвучка — синтез речи Android.",
            color = p.text,
            fontSize = 14.sp,
            lineHeight = 21.sp
        )
    }
}

@Composable
fun <T> ChoiceCard(
    options: List<T>,
    selected: T,
    label: (T) -> String,
    onSelect: (T) -> Unit
) {
    val p = LocalPalette.current
    val tap = rememberTap()
    Column(Modifier.fillMaxWidth().valhallaCard(p)) {
        options.forEach { option ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .selectable(
                        selected = selected == option,
                        onClick = {
                            tap()
                            onSelect(option)
                        },
                        role = Role.RadioButton
                    )
                    .padding(horizontal = 16.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                RadioButton(
                    selected = selected == option,
                    onClick = null,
                    colors = RadioButtonDefaults.colors(selectedColor = p.gold, unselectedColor = p.muted)
                )
                Spacer(Modifier.width(12.dp))
                Text(label(option), color = p.text, fontSize = 15.sp)
            }
        }
    }
}

@Composable
fun SwitchRow(title: String, subtitle: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    val p = LocalPalette.current
    val tap = rememberTap()
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = p.text, fontSize = 15.sp)
            Text(subtitle, color = p.muted, fontSize = 12.sp)
        }
        Switch(
            checked = checked,
            onCheckedChange = {
                tap()
                onChange(it)
            },
            colors = SwitchDefaults.colors(
                checkedThumbColor = p.onGold,
                checkedTrackColor = p.gold,
                uncheckedThumbColor = p.muted,
                uncheckedTrackColor = p.card,
                uncheckedBorderColor = p.goldDim
            )
        )
    }
}
