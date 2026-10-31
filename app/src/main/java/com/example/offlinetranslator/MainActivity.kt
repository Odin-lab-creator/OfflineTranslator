package com.example.offlinetranslator

import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import java.util.Locale

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
            val context = LocalContext.current
            val colors = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && settings.dynamicColor) {
                if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
            } else {
                if (dark) darkColorScheme() else lightColorScheme()
            }
            SideEffect {
                val controller = WindowCompat.getInsetsController(window, window.decorView)
                controller.isAppearanceLightStatusBars = !dark
                controller.isAppearanceLightNavigationBars = !dark
            }
            MaterialTheme(colorScheme = colors) {
                Surface(
                    Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
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

private fun langName(code: String): String =
    Locale(code).getDisplayLanguage(Locale("ru")).replaceFirstChar { it.uppercase() }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TranslatorScreen(
    onOpenSettings: () -> Unit,
    vm: TranslatorViewModel = viewModel()
) {
    val clipboard = LocalClipboardManager.current
    val focus = LocalFocusManager.current
    val context = LocalContext.current
    var copied by remember { mutableStateOf(false) }
    LaunchedEffect(vm.output) { copied = false }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Офлайн переводчик") },
                actions = { TextButton(onClick = onOpenSettings) { Text("⚙ Настройки") } }
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                LanguagePicker(vm.source, vm.languages, Modifier.weight(1f)) { vm.source = it }
                IconButton(onClick = vm::swapLanguages) {
                    Text("⇄", style = MaterialTheme.typography.titleLarge)
                }
                LanguagePicker(vm.target, vm.languages, Modifier.weight(1f)) { vm.target = it }
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    OutlinedTextField(
                        value = vm.input,
                        onValueChange = { vm.input = it },
                        label = { Text("Текст") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 140.dp)
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        TextButton(onClick = {
                            clipboard.getText()?.let { vm.input = it.text }
                        }) { Text("Вставить") }
                        TextButton(onClick = {
                            vm.input = ""
                            vm.output = ""
                        }) { Text("Очистить") }
                        TextButton(onClick = vm::detectLanguage) { Text("Определить язык") }
                    }
                }
            }

            Button(
                onClick = {
                    focus.clearFocus()
                    vm.translate()
                },
                enabled = !vm.busy,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Text(if (vm.busy) "Перевожу…" else "Перевести")
            }

            if (vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (vm.status.isNotEmpty()) {
                Text(
                    vm.status,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            if (vm.output.isNotEmpty()) {
                Card(
                    Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.secondaryContainer
                    )
                ) {
                    Column(Modifier.padding(16.dp)) {
                        SelectionContainer {
                            Text(vm.output, style = MaterialTheme.typography.bodyLarge)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            TextButton(onClick = {
                                clipboard.setText(AnnotatedString(vm.output))
                                copied = true
                            }) { Text(if (copied) "Скопировано ✓" else "Копировать") }
                            TextButton(onClick = {
                                val send = Intent(Intent.ACTION_SEND).apply {
                                    type = "text/plain"
                                    putExtra(Intent.EXTRA_TEXT, vm.output)
                                }
                                context.startActivity(Intent.createChooser(send, null))
                            }) { Text("Поделиться") }
                        }
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun LanguagePicker(
    selected: String,
    options: List<String>,
    modifier: Modifier = Modifier,
    onSelect: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier) {
        FilledTonalButton(
            onClick = { expanded = true },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(langName(selected), maxLines = 1)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { code ->
                DropdownMenuItem(
                    text = { Text(langName(code)) },
                    onClick = {
                        onSelect(code)
                        expanded = false
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(settings: AppSettings, onBack: () -> Unit) {
    val dynamicSupported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Настройки") },
                navigationIcon = { TextButton(onClick = onBack) { Text("← Назад") } }
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Тема", style = MaterialTheme.typography.titleMedium)
            Card(Modifier.fillMaxWidth()) {
                Column {
                    ThemeMode.entries.forEach { mode ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .selectable(
                                    selected = settings.themeMode == mode,
                                    onClick = { settings.updateTheme(mode) },
                                    role = Role.RadioButton
                                )
                                .padding(horizontal = 16.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(selected = settings.themeMode == mode, onClick = null)
                            Spacer(Modifier.width(12.dp))
                            Text(mode.label)
                        }
                    }
                }
            }

            Card(Modifier.fillMaxWidth()) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Динамические цвета")
                        Text(
                            if (dynamicSupported) "Цвета берутся из обоев (Android 12+)"
                            else "Недоступно на этой версии Android",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(
                        checked = settings.dynamicColor && dynamicSupported,
                        onCheckedChange = { settings.updateDynamic(it) },
                        enabled = dynamicSupported
                    )
                }
            }

            Text("О приложении", style = MaterialTheme.typography.titleMedium)
            Text(
                "Перевод выполняется на устройстве (Google ML Kit). " +
                    "Интернет нужен только для первой загрузки языковых моделей.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
