package com.example.offlinetranslator

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import java.util.Locale

class Palette(
    val bg: Color,
    val card: Color,
    val cardBorder: Color,
    val gold: Color,
    val goldDim: Color,
    val text: Color,
    val muted: Color,
    val result: Color,
    val onGold: Color
)

val DarkPalette = Palette(
    bg = Color(0xFF12141A),
    card = Color(0xFF1B1E27),
    cardBorder = Color(0xFF2E3340),
    gold = Color(0xFFD4AF5A),
    goldDim = Color(0xFF5A4A22),
    text = Color(0xFFE8E4D8),
    muted = Color(0xFF8D90A0),
    result = Color(0xFFF2EBD3),
    onGold = Color(0xFF12141A)
)

val LightPalette = Palette(
    bg = Color(0xFFF6F1E4),
    card = Color(0xFFFFFFFF),
    cardBorder = Color(0xFFD9D0B8),
    gold = Color(0xFF9A7B2F),
    goldDim = Color(0xFFC9B77F),
    text = Color(0xFF2A2A2A),
    muted = Color(0xFF6F6A5A),
    result = Color(0xFF2A2418),
    onGold = Color(0xFFFFFFFF)
)

val LocalPalette = staticCompositionLocalOf { DarkPalette }

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val settings = AppSettings(applicationContext)
        setContent {
            val dark = when (settings.themeMode) {
                ThemeMode.SYSTEM -> isSystemInDarkTheme()
                ThemeMode.LIGHT -> false
                ThemeMode.DARK -> true
            }
            val p = if (dark) DarkPalette else LightPalette
            val scheme = if (dark) {
                darkColorScheme(
                    primary = p.gold, background = p.bg, surface = p.bg,
                    surfaceContainer = p.card, onSurface = p.text, onBackground = p.text
                )
            } else {
                lightColorScheme(
                    primary = p.gold, background = p.bg, surface = p.bg,
                    surfaceContainer = p.card, onSurface = p.text, onBackground = p.text
                )
            }
            SideEffect {
                val c = WindowCompat.getInsetsController(window, window.decorView)
                c.isAppearanceLightStatusBars = !dark
                c.isAppearanceLightNavigationBars = !dark
            }
            CompositionLocalProvider(LocalPalette provides p) {
                MaterialTheme(colorScheme = scheme) {
                    Surface(Modifier.fillMaxSize(), color = p.bg) {
                        var showSettings by rememberSaveable { mutableStateOf(false) }
                        if (showSettings) {
                            BackHandler { showSettings = false }
                            SettingsScreen(settings) { showSettings = false }
                        } else {
                            TranslatorScreen(onOpenSettings = { showSettings = true })
                        }
                    }
                }
            }
        }
    }
}

private fun langName(code: String): String =
    Locale(code).getDisplayLanguage(Locale("ru")).replaceFirstChar { it.uppercase() }

@Composable
private fun LinkText(
    label: String,
    color: Color,
    size: TextUnit = 13.sp,
    onClick: () -> Unit
) {
    Text(
        label,
        color = color,
        fontSize = size,
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 6.dp, vertical = 8.dp)
    )
}

@Composable
fun TranslatorScreen(
    onOpenSettings: () -> Unit,
    vm: TranslatorViewModel = viewModel()
) {
    val p = LocalPalette.current
    val clipboard = LocalClipboardManager.current
    val focus = LocalFocusManager.current
    val context = LocalContext.current
    var copied by remember { mutableStateOf(false) }
    LaunchedEffect(vm.output) { copied = false }

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
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top
        ) {
            Column {
                Text(
                    "VALHALLA",
                    color = p.gold,
                    fontFamily = FontFamily.Serif,
                    fontSize = 24.sp,
                    letterSpacing = 3.sp
                )
                Text(
                    "TRANSLATE",
                    color = p.muted,
                    fontSize = 12.sp,
                    letterSpacing = 5.sp
                )
            }
            LinkText("⚙", p.gold, 24.sp, onOpenSettings)
        }
        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(p.goldDim)
        )

        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            LangPicker(vm.source, vm.languages, Modifier.weight(1f)) { vm.source = it }
            Text(
                "⇄",
                color = p.gold,
                fontSize = 24.sp,
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .clickable { vm.swapLanguages() }
                    .padding(horizontal = 12.dp, vertical = 6.dp)
            )
            LangPicker(vm.target, vm.languages, Modifier.weight(1f)) { vm.target = it }
        }

        val cardShape = RoundedCornerShape(8.dp)
        Column(
            Modifier
                .fillMaxWidth()
                .clip(cardShape)
                .background(p.card)
                .border(1.dp, p.cardBorder, cardShape)
                .padding(bottom = 6.dp)
        ) {
            TextField(
                value = vm.input,
                onValueChange = { if (it.length <= 5000) vm.input = it },
                placeholder = { Text("Введите текст") },
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 150.dp),
                colors = TextFieldDefaults.colors(
                    focusedTextColor = p.text,
                    unfocusedTextColor = p.text,
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    cursorColor = p.gold,
                    focusedPlaceholderColor = p.muted,
                    unfocusedPlaceholderColor = p.muted
                )
            )
            Text(
                "${vm.input.length} / 5000",
                color = p.muted,
                fontSize = 12.sp,
                modifier = Modifier
                    .align(Alignment.End)
                    .padding(end = 14.dp, bottom = 2.dp)
            )
            Row(Modifier.padding(horizontal = 6.dp)) {
                LinkText("Вставить", p.muted) {
                    clipboard.getText()?.let { vm.input = it.text.take(5000) }
                }
                LinkText("Очистить", p.muted) {
                    vm.input = ""
                    vm.output = ""
                }
                LinkText("Определить язык", p.muted) { vm.detectLanguage() }
            }
        }

        Box(
            Modifier
                .fillMaxWidth()
                .height(52.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(p.gold)
                .clickable(enabled = !vm.busy) {
                    focus.clearFocus()
                    vm.translate()
                },
            contentAlignment = Alignment.Center
        ) {
            Text(
                if (vm.busy) "Перевожу…" else "Перевести",
                color = p.onGold,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium
            )
        }

        if (vm.busy) {
            LinearProgressIndicator(
                Modifier.fillMaxWidth(),
                color = p.gold,
                trackColor = p.card
            )
        }
        if (vm.status.isNotEmpty()) {
            Text(vm.status, color = p.muted, fontSize = 12.sp)
        }

        if (vm.output.isNotEmpty()) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(cardShape)
                    .background(p.card)
                    .border(1.dp, p.gold, cardShape)
                    .padding(16.dp)
            ) {
                SelectionContainer {
                    Text(
                        vm.output,
                        color = p.result,
                        fontFamily = FontFamily.Serif,
                        fontSize = 24.sp,
                        lineHeight = 32.sp
                    )
                }
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    LinkText(if (copied) "Скопировано ✓" else "Копировать", p.gold, 14.sp) {
                        clipboard.setText(AnnotatedString(vm.output))
                        copied = true
                    }
                    Text("·", color = p.gold, fontSize = 14.sp)
                    LinkText("Поделиться", p.gold, 14.sp) {
                        val send = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, vm.output)
                        }
                        context.startActivity(Intent.createChooser(send, null))
                    }
                }
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun LangPicker(
    selected: String,
    options: List<String>,
    modifier: Modifier = Modifier,
    onSelect: (String) -> Unit
) {
    val p = LocalPalette.current
    var expanded by remember { mutableStateOf(false) }
    val shape = RoundedCornerShape(6.dp)
    Box(modifier) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(46.dp)
                .clip(shape)
                .border(1.dp, p.goldDim, shape)
                .clickable { expanded = true },
            contentAlignment = Alignment.Center
        ) {
            Text(langName(selected), color = p.text, fontSize = 15.sp, maxLines = 1)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { code ->
                DropdownMenuItem(
                    text = { Text(langName(code), color = p.text) },
                    onClick = {
                        onSelect(code)
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
fun SettingsScreen(settings: AppSettings, onBack: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(8.dp)
    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LinkText("← Назад", p.gold, 15.sp, onBack)
            Spacer(Modifier.width(8.dp))
            Text(
                "Настройки",
                color = p.gold,
                fontFamily = FontFamily.Serif,
                fontSize = 22.sp
            )
        }
        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(p.goldDim)
        )

        Text("Тема", color = p.muted, fontSize = 13.sp, letterSpacing = 2.sp)
        Column(
            Modifier
                .fillMaxWidth()
                .clip(shape)
                .background(p.card)
                .border(1.dp, p.cardBorder, shape)
        ) {
            ThemeMode.entries.forEach { mode ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .selectable(
                            selected = settings.themeMode == mode,
                            onClick = { settings.updateTheme(mode) },
                            role = Role.RadioButton
                        )
                        .padding(horizontal = 16.dp, vertical = 14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    RadioButton(
                        selected = settings.themeMode == mode,
                        onClick = null,
                        colors = RadioButtonDefaults.colors(
                            selectedColor = p.gold,
                            unselectedColor = p.muted
                        )
                    )
                    Spacer(Modifier.width(12.dp))
                    Text(mode.label, color = p.text, fontSize = 15.sp)
                }
            }
        }

        Text("О приложении", color = p.muted, fontSize = 13.sp, letterSpacing = 2.sp)
        Text(
            "Valhalla Translate переводит прямо на устройстве (Google ML Kit). " +
                "Интернет нужен только для первой загрузки языковых моделей.",
            color = p.text,
            fontSize = 14.sp,
            lineHeight = 21.sp
        )
    }
}
