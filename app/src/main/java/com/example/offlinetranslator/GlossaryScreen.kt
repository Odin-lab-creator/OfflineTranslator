package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Поле ввода в стиле приложения. */
@Composable
fun ValhallaTextField(
    value: String,
    onChange: (String) -> Unit,
    placeholder: String,
    modifier: Modifier = Modifier,
    singleLine: Boolean = true,
    password: Boolean = false
) {
    val p = LocalPalette.current
    TextField(
        value = value,
        onValueChange = onChange,
        placeholder = { Text(placeholder) },
        singleLine = singleLine,
        keyboardOptions = if (password) KeyboardOptions(keyboardType = KeyboardType.Password) else KeyboardOptions.Default,
        modifier = modifier.valhallaCard(p),
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
}

/** Экран «Глоссарий»: свои переводы имён, терминов и названий. */
@Composable
fun GlossaryScreen(vm: TranslatorViewModel, onBack: () -> Unit) {
    val p = LocalPalette.current
    var source by rememberSaveable { mutableStateOf(vm.source) }
    var target by rememberSaveable { mutableStateOf(vm.target) }
    var term by rememberSaveable { mutableStateOf("") }
    var translation by rememberSaveable { mutableStateOf("") }

    LazyColumn(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Column(Modifier.padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                ScreenHeader("Глоссарий", onBack)
                GoldDivider()
                Text(
                    "Имена, термины и названия, которые нужно всегда переводить определённым образом. " +
                        "Звёздочка в конце — любое окончание: «вальхалл*» найдёт «Вальхаллы» и «Вальхалле».",
                    color = p.muted,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    LanguageButton(source, "С какого языка", vm.downloaded, Modifier.weight(1f)) { source = it }
                    Text("→", color = p.gold, fontSize = 20.sp, modifier = Modifier.padding(horizontal = 10.dp))
                    LanguageButton(target, "На какой язык", vm.downloaded, Modifier.weight(1f)) { target = it }
                }
                ValhallaTextField(term, { term = it }, "Термин, например: Valhalla", Modifier.fillMaxWidth())
                ValhallaTextField(translation, { translation = it }, "Перевод, например: Вальхалла", Modifier.fillMaxWidth())
                GoldButton(
                    "Добавить",
                    modifier = Modifier.fillMaxWidth(),
                    enabled = term.isNotBlank() && translation.isNotBlank() && source != target
                ) {
                    Glossary.add(source, target, term, translation)
                    term = ""
                    translation = ""
                }
                if (Glossary.entries.isNotEmpty()) SectionLabel("Мои термины")
            }
        }
        items(Glossary.entries, key = { it.id }) { entry ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p)
                    .padding(start = 14.dp, end = 4.dp, top = 6.dp, bottom = 6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        buildAnnotatedString {
                            withStyle(SpanStyle(color = p.text)) { append(entry.term) }
                            withStyle(SpanStyle(color = p.muted)) { append("  →  ") }
                            withStyle(SpanStyle(color = p.gold)) { append(entry.translation) }
                        },
                        fontSize = 16.sp
                    )
                    Text(
                        "${Languages.name(entry.source)} → ${Languages.name(entry.target)}",
                        color = p.muted,
                        fontSize = 12.sp
                    )
                }
                LinkText("✕", p.muted, 16.sp) { Glossary.delete(entry.id) }
            }
        }
        item { Text("", modifier = Modifier.padding(bottom = 16.dp)) }
    }
}
