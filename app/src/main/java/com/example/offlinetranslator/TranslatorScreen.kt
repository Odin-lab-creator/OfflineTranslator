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
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.size
import androidx.compose.ui.res.painterResource
import androidx.compose.material3.Icon
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
    onOpenCamera: () -> Unit,
    onOpenTools: () -> Unit,
    onShow: (String) -> Unit
) {
    val settings = AppSettings.current()
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
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    painterResource(R.drawable.ic_rune),
                    contentDescription = null,
                    tint = p.gold,
                    modifier = Modifier.size(30.dp)
                )
                Spacer(Modifier.width(8.dp))
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
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                LinkText("☰", p.gold, 22.sp, onClick = onOpenTools)
                LinkText("История", p.gold, 15.sp, onClick = onOpenHistory)
                LinkText("⚙", p.gold, 24.sp, onClick = onOpenSettings)
            }
        }
        GoldDivider()

        UpdateBanner(vm)

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

        val pairs = settings.recentPairs.filter { it != (vm.source to vm.target) }
        if (pairs.isNotEmpty()) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                pairs.forEach { (src, dst) ->
                    OutlineGoldButton(
                        "${src.uppercase()} → ${dst.uppercase()}",
                        height = 34
                    ) { vm.setPair(src, dst) }
                }
            }
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
            ReadingText(vm.input, vm.source, Modifier.padding(horizontal = 16.dp))
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
                if (vm.viaDeepl) {
                    Text("DeepL · онлайн", color = p.muted, fontSize = 11.sp, letterSpacing = 1.sp)
                    Spacer(Modifier.height(4.dp))
                }
                SelectionContainer {
                    Text(
                        vm.output,
                        color = p.result,
                        fontFamily = FontFamily.Serif,
                        fontSize = settings.fontSize.sp.sp,
                        lineHeight = (settings.fontSize.sp * 4 / 3).sp,
                        modifier = Modifier.animateContentSize(tween(200))
                    )
                }
                ReadingText(vm.output, vm.target, Modifier.padding(top = 6.dp))
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
                Row(verticalAlignment = Alignment.CenterVertically) {
                    LinkText("Показать собеседнику", p.gold, 14.sp) { onShow(vm.output) }
                    LinkText("Обратный перевод", p.muted, 14.sp) { vm.checkBackTranslation() }
                }
                if (vm.backTranslation.isNotEmpty()) {
                    Text(
                        "Обратно: ${vm.backTranslation}",
                        color = p.muted,
                        fontSize = 14.sp,
                        modifier = Modifier.padding(horizontal = 6.dp)
                    )
                }
                SlangFoundList(vm.slangFound, Modifier.padding(start = 6.dp, end = 6.dp, top = 8.dp))
            }
        }
        ExtraTargetsSection(vm)
        Spacer(Modifier.height(16.dp))
    }
}

/** Плашка «Доступна новая версия» с кнопкой установки. */
@Composable
fun UpdateBanner(vm: TranslatorViewModel) {
    val p = LocalPalette.current
    val info = vm.update
    AnimatedVisibility(
        visible = info != null || vm.updateProgress != null,
        enter = fadeIn() + expandVertically(),
        exit = fadeOut() + shrinkVertically()
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .valhallaCard(p, border = p.gold)
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                "Доступна версия ${info?.versionName.orEmpty()}",
                color = p.gold,
                fontFamily = FontFamily.Serif,
                fontSize = 18.sp
            )
            if (!info?.notes.isNullOrBlank()) {
                Text(info?.notes.orEmpty(), color = p.muted, fontSize = 13.sp)
            }
            val progress = vm.updateProgress
            if (progress != null) {
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier.fillMaxWidth(),
                    color = p.gold,
                    trackColor = p.bg
                )
            }
            if (vm.updateMessage.isNotEmpty()) Text(vm.updateMessage, color = p.muted, fontSize = 12.sp)
            Row(verticalAlignment = Alignment.CenterVertically) {
                GoldButton(
                    if (progress != null) "Скачиваю ${(progress * 100).toInt()}%" else "Обновить",
                    modifier = Modifier.weight(1f),
                    enabled = progress == null
                ) { vm.installUpdate() }
                LinkText("Позже", p.muted, 14.sp) { vm.dismissUpdate() }
            }
        }
    }
}
