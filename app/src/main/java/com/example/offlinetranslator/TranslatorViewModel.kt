package com.example.offlinetranslator

import android.app.Application
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

const val MAX_INPUT = 5000

class TranslatorViewModel(app: Application) : AndroidViewModel(app) {
    private val settings = AppSettings.get(app)
    val history = HistoryStore.get(app)

    var input by mutableStateOf("")
        private set
    var output by mutableStateOf("")
        private set
    var source by mutableStateOf(settings.lastSource)
        private set
    var target by mutableStateOf(settings.lastTarget)
        private set
    var status by mutableStateOf("")
        private set
    var busy by mutableStateOf(false)
        private set
    var downloaded by mutableStateOf<Set<String>>(emptySet())
        private set

    private var job: Job? = null
    private var historyJob: Job? = null

    init {
        refreshDownloaded()
    }

    fun refreshDownloaded() {
        viewModelScope.launch {
            downloaded = try {
                TranslationEngine.downloadedLanguages()
            } catch (e: Exception) {
                downloaded
            }
        }
    }

    private fun pairReady(): Boolean =
        source == target || (source in downloaded && target in downloaded)

    fun updateInput(text: String) {
        input = text.take(MAX_INPUT)
        if (input.isBlank()) {
            clear()
            return
        }
        if (settings.autoTranslate) scheduleAuto()
    }

    fun clear() {
        job?.cancel()
        historyJob?.cancel()
        input = ""
        output = ""
        status = ""
        busy = false
    }

    fun changeSource(code: String) {
        source = code
        settings.lastSource = code
        retranslateIfAuto()
    }

    fun changeTarget(code: String) {
        target = code
        settings.lastTarget = code
        retranslateIfAuto()
    }

    fun swapLanguages() {
        val s = source
        source = target
        target = s
        settings.lastSource = source
        settings.lastTarget = target
        if (output.isNotBlank()) {
            input = output
            output = ""
        }
        retranslateIfAuto()
    }

    private fun retranslateIfAuto() {
        if (input.isNotBlank() && settings.autoTranslate) scheduleAuto(immediate = true)
    }

    private fun scheduleAuto(immediate: Boolean = false) {
        job?.cancel()
        job = viewModelScope.launch {
            if (!immediate) delay(600)
            val text = input.trim()
            if (text.isEmpty()) return@launch
            if (!pairReady()) {
                status = "Для автоперевода нужна модель «${Languages.name(source)} → ${Languages.name(target)}». " +
                    "Нажмите «Перевести», чтобы скачать её."
                return@launch
            }
            runTranslation(text, saveNow = false)
        }
    }

    /** Автоперевод попадает в историю, только когда пользователь перестал печатать. */
    private fun rememberInHistory(src: String, dst: String, text: String, result: String, now: Boolean) {
        historyJob?.cancel()
        if (now) {
            history.add(src, dst, text, result)
            return
        }
        historyJob = viewModelScope.launch {
            delay(2500)
            history.add(src, dst, text, result)
        }
    }

    /** Звёздочка у текущего перевода. */
    fun isCurrentFavorite(): Boolean =
        output.isNotBlank() && history.find(source, target, input)?.favorite == true

    fun toggleFavoriteCurrent() {
        if (output.isBlank() || input.isBlank()) return
        historyJob?.cancel()
        val entry = history.find(source, target, input) ?: history.add(source, target, input, output) ?: return
        history.toggleFavorite(entry.id)
    }

    /** Открывает запись из истории на главном экране. */
    fun restore(entry: HistoryEntry) {
        job?.cancel()
        historyJob?.cancel()
        source = entry.source
        target = entry.target
        settings.lastSource = source
        settings.lastTarget = target
        input = entry.text
        output = entry.result
        status = ""
        busy = false
    }

    /** Ручной перевод по кнопке: при необходимости скачивает модели. */
    fun translate() {
        val text = input.trim()
        if (text.isEmpty()) {
            output = ""
            return
        }
        job?.cancel()
        job = viewModelScope.launch {
            busy = true
            try {
                runTranslation(text)
            } finally {
                busy = false
            }
        }
    }

    private suspend fun runTranslation(text: String, saveNow: Boolean = true) {
        try {
            if (!pairReady()) status = "Скачиваю языковую модель (один раз, около 30 МБ)…"
            val src = source
            val dst = target
            val result = TranslationEngine.translate(src, dst, text, settings.wifiOnly)
            output = result
            status = ""
            if (!pairReady()) refreshDownloaded()
            rememberInHistory(src, dst, text, result, saveNow)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            status = errorText(e)
        }
    }

    private fun errorText(e: Exception): String {
        val wifiHint = if (settings.wifiOnly) " Включена загрузка только по Wi-Fi." else ""
        return "Ошибка: ${e.localizedMessage ?: "не удалось перевести"}. " +
            "Если модель ещё не скачана, нужен интернет.$wifiHint"
    }

    /** Текст, пришедший из другого приложения: определяем язык и сразу переводим. */
    fun translateIncoming(text: String) {
        val clean = text.trim().take(MAX_INPUT)
        if (clean.isEmpty()) return
        job?.cancel()
        job = viewModelScope.launch {
            busy = true
            output = ""
            input = clean
            try {
                detectAndApply(clean)
                runTranslation(clean)
            } finally {
                busy = false
            }
        }
    }

    /** Распознаёт текст на картинке, определяет язык и сразу переводит. */
    fun translateImage(uri: Uri) {
        job?.cancel()
        job = viewModelScope.launch {
            busy = true
            output = ""
            try {
                status = "Распознаю текст на изображении…"
                val text = TranslationEngine.recognize(getApplication<Application>(), uri)
                if (text.isEmpty()) {
                    status = "Текст не найден. Распознаётся латиница: английский, немецкий, французский и др."
                    return@launch
                }
                input = text.take(MAX_INPUT)
                status = "Определяю язык…"
                detectAndApply(input)
                status = ""
                runTranslation(input)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                status = "Не удалось прочитать изображение: ${e.localizedMessage ?: "ошибка"}"
            } finally {
                busy = false
            }
        }
    }

    private suspend fun detectAndApply(text: String) {
        val code = try {
            TranslationEngine.detect(text)
        } catch (e: Exception) {
            null
        } ?: return
        source = code
        settings.lastSource = code
        if (source == target) {
            target = Languages.otherTarget(source, target)
            settings.lastTarget = target
        }
    }

    fun detectLanguage() {
        val text = input.trim()
        if (text.isEmpty()) return
        viewModelScope.launch {
            val code = try {
                TranslationEngine.detect(text)
            } catch (e: Exception) {
                null
            }
            if (code == null) {
                status = "Не удалось определить язык"
            } else {
                changeSource(code)
                status = "Язык: ${Languages.name(code)}"
            }
        }
    }
}
