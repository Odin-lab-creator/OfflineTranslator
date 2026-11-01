package com.example.offlinetranslator

import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

private fun isWordChar(c: Char) = c.isLetterOrDigit() || c == '\'' || c == '’' || c == '-' || c.code == 0x301

private fun isIdeograph(c: Char): Boolean {
    val block = Character.UnicodeBlock.of(c)
    return block == Character.UnicodeBlock.CJK_UNIFIED_IDEOGRAPHS ||
        block == Character.UnicodeBlock.HIRAGANA ||
        block == Character.UnicodeBlock.KATAKANA ||
        block == Character.UnicodeBlock.HANGUL_SYLLABLES
}

/** Слово в тексте по позиции символа. */
fun wordAt(text: String, offset: Int): String? {
    if (text.isEmpty()) return null
    var i = offset.coerceIn(0, text.length - 1)
    if (!isWordChar(text[i]) && i > 0 && isWordChar(text[i - 1])) i--
    if (!isWordChar(text[i])) return null
    if (isIdeograph(text[i])) return text[i].toString()
    var start = i
    while (start > 0 && isWordChar(text[start - 1]) && !isIdeograph(text[start - 1])) start--
    var end = i
    while (end < text.length - 1 && isWordChar(text[end + 1]) && !isIdeograph(text[end + 1])) end++
    return text.substring(start, end + 1).trim('-', '\'', '’').takeIf { w -> w.any { it.isLetter() } }
}

/** Все слова текста по порядку, без повторов. */
fun wordsOf(text: String, limit: Int = 40): List<String> {
    val result = LinkedHashMap<String, String>()
    Regex("[\\p{L}\\p{M}][\\p{L}\\p{M}'’-]*").findAll(text).forEach { m ->
        val w = m.value.trim('-', '\'', '’')
        if (w.isNotEmpty() && result.size < limit) result.putIfAbsent(w.lowercase(), w)
    }
    return result.values.toList()
}

/** Текст, в котором нажатие на слово открывает словарь. */
@Composable
fun WordTapText(
    text: String,
    style: TextStyle,
    modifier: Modifier = Modifier,
    onLongPress: (() -> Unit)? = null,
    onWord: (String) -> Unit
) {
    var layout by remember { mutableStateOf<TextLayoutResult?>(null) }
    Text(
        text,
        style = style,
        onTextLayout = { layout = it },
        modifier = modifier.pointerInput(text, onLongPress) {
            detectTapGestures(
                onLongPress = if (onLongPress != null) { _: Offset -> onLongPress() } else null,
                onTap = { position ->
                    val l = layout ?: return@detectTapGestures
                    wordAt(text, l.getOffsetForPosition(position))?.let(onWord)
                }
            )
        }
    )
}

/** Ряд слов-кнопок: «По словам» под переводом. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun WordChips(text: String, onWord: (String) -> Unit) {
    val p = LocalPalette.current
    val words = remember(text) { wordsOf(text) }
    if (words.size < 2) return
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("ПО СЛОВАМ", color = p.muted, fontSize = 11.sp, letterSpacing = 2.sp)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            words.forEach { word ->
                Text(
                    word,
                    color = p.text,
                    fontSize = 14.sp,
                    modifier = Modifier
                        .clip(ButtonShape)
                        .border(1.dp, p.goldDim, ButtonShape)
                        .clickable { onWord(word) }
                        .padding(horizontal = 10.dp, vertical = 5.dp)
                )
            }
        }
    }
}

/** Что показать в карточке слова. */
class WordQuery(val word: String, val source: String, val target: String)

/** Нижняя карточка слова: словарная статья, перевод, озвучка, «в карточки». */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WordSheet(query: WordQuery, vm: TranslatorViewModel, onDismiss: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val settings = AppSettings.current()
    val clipboard = LocalClipboardManager.current
    val scope = rememberCoroutineScope()
    val sheet = rememberModalBottomSheetState(skipPartiallyExpanded = false)
    var machine by remember(query) { mutableStateOf("") }
    var entries by remember(query) { mutableStateOf<List<Dictionary.Entry>?>(null) }
    var message by remember(query) { mutableStateOf("") }
    var saved by remember(query) { mutableStateOf(false) }
    val source = query.source
    val target = query.target
    val pair = Dictionary.pairOf(source, target)
    val hasDictionary = pair in Dictionary.downloaded

    LaunchedEffect(query, hasDictionary) {
        Dictionary.init(context)
        entries = try {
            Dictionary.lookup(query.word, source, target)
        } catch (e: Exception) {
            emptyList()
        }
        if (Dictionary.available.isEmpty()) {
            try {
                Dictionary.refreshIndex()
            } catch (e: Exception) {
                // без интернета список словарей недоступен
            }
        }
    }
    LaunchedEffect(query) {
        machine = try {
            if (source == target) "" else TranslationEngine.translate(source, target, query.word, settings.wifiOnly)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            ""
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheet,
        containerColor = p.card,
        contentColor = p.text
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .heightIn(max = 560.dp)
                .verticalScroll(rememberScrollState())
                .navigationBarsPadding()
                .padding(start = 20.dp, end = 20.dp, bottom = 20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                SelectionContainer(Modifier.weight(1f)) {
                    Text(query.word, color = p.gold, fontFamily = FontFamily.Serif, fontSize = 28.sp)
                }
                IconTap(ValhallaIcons.Speaker, "Озвучить", p.gold) { vm.speak(query.word, source) }
            }
            val reading = remember(query) { Transcription.of(query.word, source) }
            if (reading != null) Text(reading, color = p.muted, fontSize = 14.sp, fontStyle = FontStyle.Italic)
            Text("${Languages.name(source)} → ${Languages.name(target)}", color = p.muted, fontSize = 12.sp)
            if (machine.isNotBlank()) {
                Text(
                    buildAnnotatedString {
                        withStyle(SpanStyle(color = p.muted)) { append("Перевод: ") }
                        withStyle(SpanStyle(color = p.result)) { append(machine) }
                    },
                    fontSize = 18.sp
                )
            }
            GoldDivider()

            val list = entries
            when {
                list == null -> LinearProgressIndicator(Modifier.fillMaxWidth(), color = p.gold, trackColor = p.bg)
                list.isNotEmpty() -> list.forEach { entry -> DictionaryEntryView(entry) }
                hasDictionary -> Text("В словаре этого слова нет.", color = p.muted, fontSize = 14.sp)
                else -> {
                    val info = Dictionary.info(source, target)
                    val progress = Dictionary.progress[pair]
                    if (info != null) {
                        Text(
                            "Словарь ${Languages.name(source)} → ${Languages.name(target)}: все значения, " +
                                "часть речи и произношение — без интернета.",
                            color = p.text,
                            fontSize = 14.sp
                        )
                        if (progress != null) {
                            LinearProgressIndicator(
                                progress = { progress },
                                modifier = Modifier.fillMaxWidth(),
                                color = p.gold,
                                trackColor = p.bg
                            )
                        } else {
                            OutlineGoldButton(
                                "Скачать словарь (${formatMb(info.bytes)})",
                                Modifier.fillMaxWidth(),
                                height = 44
                            ) {
                                scope.launch {
                                    message = try {
                                        Dictionary.download(pair)
                                        ""
                                    } catch (e: Exception) {
                                        "Не удалось скачать: ${e.localizedMessage ?: "ошибка"}"
                                    }
                                }
                            }
                        }
                    } else {
                        Text(
                            "Для этой пары языков словаря пока нет — показан машинный перевод.",
                            color = p.muted,
                            fontSize = 13.sp
                        )
                    }
                }
            }
            if (message.isNotEmpty()) Text(message, color = p.muted, fontSize = 13.sp)

            Row(verticalAlignment = Alignment.CenterVertically) {
                LinkText(if (saved) "★ В карточках" else "☆ В карточки", p.gold, 14.sp) {
                    if (!saved) {
                        val meaning = entries?.firstOrNull()?.senses?.firstOrNull()?.translations?.take(3)?.joinToString(", ")
                            ?.let { stripStress(it) }
                            ?: machine
                        if (meaning.isNotBlank()) {
                            val entry = vm.history.find(source, target, query.word)
                                ?: vm.history.add(source, target, query.word, meaning)
                            if (entry != null && !entry.favorite) vm.history.toggleFavorite(entry.id)
                            saved = true
                        }
                    }
                }
                LinkText("Копировать", p.gold, 14.sp) {
                    clipboard.setText(AnnotatedString(listOf(query.word, machine).filter { it.isNotBlank() }.joinToString(" — ")))
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

fun stripStress(text: String): String = text.replace("́", "")

fun formatMb(bytes: Long): String =
    if (bytes <= 0) "?" else if (bytes < 1_000_000) "${bytes / 1000} КБ" else "%.1f МБ".format(bytes / 1_000_000.0)

@Composable
private fun DictionaryEntryView(entry: Dictionary.Entry) {
    val p = LocalPalette.current
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            buildAnnotatedString {
                withStyle(SpanStyle(color = p.text)) { append(entry.word) }
                val pos = Dictionary.posLabel(entry.pos)
                val gender = Dictionary.genderLabel(entry.gender)
                val tags = listOf(pos, gender).filter { it.isNotEmpty() }.joinToString(", ")
                if (tags.isNotEmpty()) withStyle(SpanStyle(color = p.gold, fontStyle = FontStyle.Italic)) { append("  $tags") }
            },
            fontSize = 17.sp
        )
        if (entry.pronunciation.isNotBlank()) {
            Text(entry.pronunciation, color = p.muted, fontSize = 13.sp)
        }
        entry.senses.forEachIndexed { index, sense ->
            Text(
                buildAnnotatedString {
                    withStyle(SpanStyle(color = p.muted)) { append("${index + 1}. ") }
                    withStyle(SpanStyle(color = p.result)) { append(sense.translations.joinToString(", ")) }
                    if (sense.glosses.isNotEmpty()) {
                        withStyle(SpanStyle(color = p.muted, fontStyle = FontStyle.Italic)) {
                            append("  (" + sense.glosses.joinToString("; ") + ")")
                        }
                    }
                },
                fontSize = 15.sp,
                lineHeight = 21.sp
            )
        }
        Spacer(Modifier.height(4.dp))
        Spacer(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(p.cardBorder)
        )
    }
}
