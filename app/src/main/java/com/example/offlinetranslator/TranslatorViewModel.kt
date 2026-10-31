package com.example.offlinetranslator

import android.app.Application
import android.net.Uri
import android.speech.tts.TextToSpeech
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
    var backTranslation by mutableStateOf("")
        private set

    // Обновления
    var update by mutableStateOf<UpdateInfo?>(null)
        private set
    var updateProgress by mutableStateOf<Float?>(null)
        private set
    var updateMessage by mutableStateOf("")
        private set

    private var job: Job? = null
    private var historyJob: Job? = null

    init {
        refreshDownloaded()
        if (System.currentTimeMillis() - settings.lastUpdateCheck > 6 * 60 * 60 * 1000L) {
            checkForUpdates(manual = false)
        }
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
        backTranslation = ""
        status = ""
        busy = false
    }

    /** Выбор пары языков из недавних. */
    fun setPair(src: String, dst: String) {
        source = src
        target = dst
        settings.lastSource = src
        settings.lastTarget = dst
        retranslateIfAuto()
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
        backTranslation = ""
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
            backTranslation = ""
            status = ""
            settings.rememberPair(src, dst)
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
                val script = TranslationEngine.resolveScript(settings.ocrScript, source)
                status = "Распознаю текст (${script.label.lowercase()})…"
                val text = TranslationEngine.recognize(getApplication<Application>(), uri, script, source)
                if (text.isEmpty()) {
                    status = "Текст не найден. Сейчас распознаётся: ${script.label.lowercase()}. " +
                        "Для русского текста выберите исходный язык «Русский» или смените алфавит в настройках."
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

    /** Текст, надиктованный голосом: сразу переводим (при необходимости скачав модели). */
    fun voiceInput(text: String) {
        val clean = text.trim()
        if (clean.isEmpty()) return
        input = clean.take(MAX_INPUT)
        translate()
    }

    fun reportStatus(message: String) {
        status = message
    }

    // ---- Озвучка перевода ----

    private var tts: TextToSpeech? = null
    private var ttsReady = false

    /** Озвучивает текст. toggle = true: повторное нажатие останавливает речь. */
    fun speak(text: String, lang: String, toggle: Boolean = true) {
        if (text.isBlank()) return
        val engine = tts
        if (engine == null) {
            tts = TextToSpeech(getApplication<Application>()) { state ->
                ttsReady = state == TextToSpeech.SUCCESS
                if (ttsReady) speak(text, lang, toggle = false) else status = "Синтез речи недоступен на этом устройстве"
            }
            return
        }
        if (!ttsReady) return
        if (toggle && engine.isSpeaking) {
            engine.stop()
            return
        }
        val result = engine.setLanguage(Languages.locale(lang))
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            status = "Нет голоса для языка «${Languages.name(lang)}». Его можно установить в настройках Android: " +
                "Общие настройки → Язык и ввод → Синтез речи."
            return
        }
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "valhalla")
    }

    override fun onCleared() {
        tts?.stop()
        tts?.shutdown()
        super.onCleared()
    }

    /** Обратный перевод: проверяем, что смысл не потерялся. */
    fun checkBackTranslation() {
        val text = output.trim()
        if (text.isEmpty() || source == target) return
        viewModelScope.launch {
            backTranslation = "…"
            backTranslation = try {
                TranslationEngine.translate(target, source, text, settings.wifiOnly)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                "не удалось: ${e.localizedMessage ?: "ошибка"}"
            }
        }
    }

    // ---- Обновления приложения ----

    fun checkForUpdates(manual: Boolean) {
        viewModelScope.launch {
            if (manual) updateMessage = "Проверяю…"
            try {
                val info = Updater.check()
                settings.lastUpdateCheck = System.currentTimeMillis()
                update = info
                updateMessage = when {
                    info != null -> ""
                    manual -> "Установлена последняя версия ${BuildConfig.VERSION_NAME}"
                    else -> ""
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (manual) updateMessage = "Не удалось проверить: ${e.localizedMessage ?: "нет интернета"}"
            }
        }
    }

    fun dismissUpdate() {
        update = null
    }

    fun installUpdate() {
        val info = update ?: return
        val app = getApplication<Application>()
        if (!Updater.canInstall(app)) {
            updateMessage = "Разрешите установку из этого источника и нажмите «Обновить» ещё раз"
            Updater.openInstallPermission(app)
            return
        }
        if (updateProgress != null) return
        viewModelScope.launch {
            updateProgress = 0f
            updateMessage = "Скачиваю версию ${info.versionName}…"
            try {
                val file = Updater.download(app, info) { progress -> updateProgress = progress }
                updateMessage = ""
                Updater.install(app, file)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                updateMessage = "Не удалось скачать обновление: ${e.localizedMessage ?: "ошибка"}"
            } finally {
                updateProgress = null
            }
        }
    }
}
