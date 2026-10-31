package com.example.offlinetranslator

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import java.util.Locale

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(Modifier.fillMaxSize()) { TranslatorScreen() }
            }
        }
    }
}

private fun langName(code: String): String =
    Locale(code).getDisplayLanguage(Locale("ru")).replaceFirstChar { it.uppercase() }

@Composable
fun TranslatorScreen(vm: TranslatorViewModel = viewModel()) {
    Column(
        Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Офлайн переводчик", style = MaterialTheme.typography.headlineSmall)

        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            LanguagePicker(vm.source, vm.languages, Modifier.weight(1f)) { vm.source = it }
            IconButton(onClick = vm::swapLanguages) { Text("⇄", style = MaterialTheme.typography.titleLarge) }
            LanguagePicker(vm.target, vm.languages, Modifier.weight(1f)) { vm.target = it }
        }

        OutlinedTextField(
            value = vm.input,
            onValueChange = { vm.input = it },
            label = { Text("Текст") },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 120.dp)
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = vm::translate, enabled = !vm.busy) { Text("Перевести") }
            OutlinedButton(onClick = vm::detectLanguage) { Text("Определить язык") }
        }

        if (vm.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        if (vm.status.isNotEmpty()) {
            Text(vm.status, style = MaterialTheme.typography.bodySmall)
        }

        if (vm.output.isNotEmpty()) {
            Card(Modifier.fillMaxWidth()) {
                SelectionContainer {
                    Text(
                        vm.output,
                        Modifier.padding(16.dp),
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
            }
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
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
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
