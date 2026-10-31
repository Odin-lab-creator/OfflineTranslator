package com.example.offlinetranslator

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Что пришло в приложение извне: картинка, текст или просьба сразу открыть выбор скриншота. */
sealed class Incoming {
    data class Image(val uri: Uri) : Incoming()
    data class Shared(val text: String) : Incoming()
    data object PickScreenshot : Incoming()
    data object OpenCamera : Incoming()
}

@Composable
fun TranslatorScreen(
    vm: TranslatorViewModel,
    incoming: Incoming?,
    onIncomingHandled: () -> Unit,
    onOpenHistory: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenCamera: () -> Unit
) {
    val p = LocalPalette.current
    val clipboard = LocalClipboardManager.current
    val focus = LocalFocusManager.current
    val context = LocalContext.current
    var copied by remember { mutableStateOf(false) }
    LaunchedEffect(vm.output) { copied = false }

    val pickImage = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        if (uri != null) vm.translateImage(uri)
    }
    val openPicker = {
        focus.clearFocus()
        pickImage.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
    }

    val speech = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val heard = result.data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()
        if (heard != null) vm.voiceInput(heard)
    }
    val startVoice = {
        focus.clearFocus()
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, Languages.locale(vm.source).toLanguageTag())
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            .putExtra(RecognizerIntent.EXTRA_PROMPT, "Говорите: ${Languages.name(vm.source)}")
        try {
            speech.launch(intent)
        } catch (e: ActivityNotFoundException) {
            vm.reportStatus("На телефоне нет службы распознавания речи (обычно это приложение Google).")
        }
    }

    LaunchedEffect(incoming) {
        when (incoming) {
            is Incoming.Image -> vm.translateImage(incoming.uri)
            is Incoming.Shared -> vm.translateIncoming(incoming.text)
            Incoming.PickScreenshot -> openPicker()
            Incoming.OpenCamera -> onOpenCamera()
            null -> return@LaunchedEffect
        }
        onIncomingHandled()
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
                Text("TRANSLATE", color = p.muted, fontSize = 12.sp, letterSpacing = 5.sp)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                LinkText("История", p.gold, 15.sp, onClick = onOpenHistory)
                LinkText("⚙", p.gold, 24.sp, onClick = onOpenSettings)
            }
        }
        GoldDivider()

        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            LanguageButton(
                selected = vm.source,
                title = "С какого языка",
                downloaded = vm.downloaded,
                modifier = Modifier.weight(1f),
                onSelect = vm::changeSource
            )
            Text(
                "⇄",
                color = p.gold,
                fontSize = 24.sp,
                modifier = Modifier
                    .clip(ButtonShape)
                    .clickable { vm.swapLanguages() }
                    .padding(horizontal = 12.dp, vertical = 6.dp)
            )
            LanguageButton(
                selected = vm.target,
                title = "На какой язык",
                downloaded = vm.downloaded,
                modifier = Modifier.weight(1f),
                onSelect = vm::changeTarget
            )
        }

        Column(
            Modifier
                .fillMaxWidth()
                .valhallaCard(p)
                .padding(bottom = 6.dp)
        ) {
            TextField(
                value = vm.input,
                onValueChange = vm::updateInput,
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
                "${vm.input.length} / $MAX_INPUT",
                color = p.muted,
                fontSize = 12.sp,
                modifier = Modifier
                    .align(Alignment.End)
                    .padding(end = 14.dp, bottom = 2.dp)
            )
            Row(Modifier.padding(horizontal = 6.dp)) {
                LinkText("Вставить", p.muted) {
                    clipboard.getText()?.let { vm.updateInput(it.text) }
                }
                LinkText("Очистить", p.muted) { vm.clear() }
                LinkText("Определить язык", p.muted) { vm.detectLanguage() }
            }
        }

        GoldButton(
            if (vm.busy) "Перевожу…" else "Перевести",
            modifier = Modifier.fillMaxWidth(),
            enabled = !vm.busy
        ) {
            focus.clearFocus()
            vm.translate()
        }
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            IconLabelButton(ValhallaIcons.Mic, "Голос", Modifier.weight(1f), !vm.busy, startVoice)
            IconLabelButton(ValhallaIcons.Image, "Скриншот", Modifier.weight(1.25f), !vm.busy, openPicker)
            IconLabelButton(ValhallaIcons.Camera, "Камера", Modifier.weight(1f), !vm.busy, onOpenCamera)
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

        AnimatedVisibility(
            visible = vm.output.isNotEmpty(),
            enter = fadeIn(tween(250)) + expandVertically(tween(250)),
            exit = fadeOut(tween(150)) + shrinkVertically(tween(150))
        ) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p, border = p.gold)
                    .padding(16.dp)
            ) {
                SelectionContainer {
                    Text(
                        vm.output,
                        color = p.result,
                        fontFamily = FontFamily.Serif,
                        fontSize = 24.sp,
                        lineHeight = 32.sp,
                        modifier = Modifier.animateContentSize(tween(200))
                    )
                }
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconTap(ValhallaIcons.Speaker, "Озвучить", p.gold) {
                        vm.speak(vm.output, vm.target)
                    }
                    LinkText(if (vm.isCurrentFavorite()) "★" else "☆", p.gold, 18.sp) {
                        vm.toggleFavoriteCurrent()
                    }
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
