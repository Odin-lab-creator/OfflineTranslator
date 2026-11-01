package com.example.offlinetranslator

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.launch

/** Читалка: книги и статьи, нажатие на слово — словарь, долгое нажатие на абзац — перевод абзаца. */
@Composable
fun ReaderScreen(vm: TranslatorViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    val store = remember { ReaderStore.get(context) }
    var openId by rememberSaveable { mutableStateOf<Long?>(null) }
    val book = store.books.firstOrNull { it.id == openId }
    if (book == null) {
        LibraryView(store, vm, onBack) { openId = it.id }
    } else {
        BackHandler { openId = null }
        BookView(store, book, vm) { openId = null }
    }
}

@Composable
private fun LibraryView(store: ReaderStore, vm: TranslatorViewModel, onBack: () -> Unit, onOpen: (Book) -> Unit) {
    val p = LocalPalette.current
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var url by rememberSaveable { mutableStateOf("") }

    fun load(block: suspend () -> Book) {
        if (busy) return
        busy = true
        message = ""
        scope.launch {
            try {
                onOpen(block())
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message = "Не удалось открыть: ${e.localizedMessage ?: "ошибка"}"
            } finally {
                busy = false
            }
        }
    }

    val pickFile = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) load { store.addUri(uri) }
    }

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
                ScreenHeader("Читалка", onBack)
                GoldDivider()
                Text(
                    "Книги и статьи на иностранном языке. Нажмите на слово — словарь и перевод, " +
                        "удерживайте абзац — перевод всего абзаца. Место чтения запоминается.",
                    color = p.muted,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                GoldButton("Открыть файл (EPUB, FB2, TXT, HTML)", Modifier.fillMaxWidth(), enabled = !busy) {
                    pickFile.launch(arrayOf("*/*"))
                }
                ValhallaTextField(url, { url = it }, "Ссылка на статью: https://…", Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlineGoldButton("Открыть ссылку", Modifier.weight(1f), enabled = !busy && url.isNotBlank(), height = 44) {
                        val address = url.trim().let { if (it.startsWith("http")) it else "https://$it" }
                        load { store.addUrl(address) }
                    }
                    OutlineGoldButton("Из буфера", Modifier.weight(1f), enabled = !busy, height = 44) {
                        val text = clipboard.getText()?.text.orEmpty()
                        if (text.isBlank()) message = "В буфере обмена нет текста" else load { store.addText(text) }
                    }
                }
                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth(), color = p.gold, trackColor = p.card)
                if (message.isNotEmpty()) Text(message, color = p.gold, fontSize = 13.sp)
                if (store.books.isNotEmpty()) SectionLabel("Библиотека")
            }
        }
        items(store.books, key = { it.id }) { book ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p)
                    .clickable { onOpen(book) }
                    .padding(start = 14.dp, end = 4.dp, top = 10.dp, bottom = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(book.title, color = p.text, fontSize = 16.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    val percent = if (book.paragraphs > 0) book.position * 100 / book.paragraphs else 0
                    Text("${Languages.name(book.language)} · прочитано $percent%", color = p.muted, fontSize = 12.sp)
                }
                LinkText("✕", p.muted, 16.sp) { store.delete(book.id) }
            }
        }
        item { Text("", Modifier.padding(bottom = 12.dp)) }
    }
}

@Composable
private fun BookView(store: ReaderStore, book: Book, vm: TranslatorViewModel, onClose: () -> Unit) {
    val p = LocalPalette.current
    val settings = AppSettings.current()
    val scope = rememberCoroutineScope()
    val paragraphs = remember(book.id) { store.paragraphs(book) }
    val state = rememberLazyListState(initialFirstVisibleItemIndex = book.position.coerceIn(0, maxOf(0, paragraphs.size - 1)))
    val translations = remember(book.id) { mutableStateMapOf<Int, String>() }
    var language by remember(book.id) { mutableStateOf(book.language) }
    var wordQuery by remember { mutableStateOf<WordQuery?>(null) }
    val target = settings.myLanguage.let { if (it == language) Languages.otherTarget(language, it) else it }

    LaunchedEffect(book.id) {
        snapshotFlow { state.firstVisibleItemIndex }
            .debounce(800)
            .collect { store.savePosition(book.id, it) }
    }
    DisposableEffect(book.id) {
        onDispose { store.savePosition(book.id, state.firstVisibleItemIndex) }
    }
    wordQuery?.let { WordSheet(it, vm) { wordQuery = null } }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
    ) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            ScreenHeader(book.title.take(28), onClose)
            Row(verticalAlignment = Alignment.CenterVertically) {
                LanguageButton(language, "Язык книги", vm.downloaded, Modifier.weight(1f)) { language = it }
                Text("→ ${Languages.name(target)}", color = p.muted, fontSize = 14.sp, modifier = Modifier.padding(start = 10.dp))
            }
        }
        GoldDivider()
        LazyColumn(
            state = state,
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            itemsIndexed(paragraphs) { index, paragraph ->
                Column(Modifier.padding(horizontal = 18.dp, vertical = 2.dp)) {
                    WordTapText(
                        paragraph,
                        style = TextStyle(color = p.text, fontFamily = FontFamily.Serif, fontSize = 19.sp, lineHeight = 28.sp),
                        onLongPress = {
                            if (translations.containsKey(index)) {
                                translations.remove(index)
                            } else {
                                translations[index] = "…"
                                scope.launch {
                                    translations[index] = try {
                                        TranslationEngine.translate(language, target, paragraph, settings.wifiOnly)
                                    } catch (e: CancellationException) {
                                        throw e
                                    } catch (e: Exception) {
                                        "Не удалось перевести: ${e.localizedMessage ?: "ошибка"}"
                                    }
                                }
                            }
                        }
                    ) { word -> wordQuery = WordQuery(word, language, target) }
                    translations[index]?.let { translated ->
                        Text(
                            translated,
                            color = p.gold,
                            fontFamily = FontFamily.Serif,
                            fontStyle = FontStyle.Italic,
                            fontSize = 17.sp,
                            lineHeight = 25.sp,
                            modifier = Modifier.padding(top = 6.dp)
                        )
                    }
                }
            }
            item { Text("", Modifier.padding(bottom = 40.dp)) }
        }
    }
}
