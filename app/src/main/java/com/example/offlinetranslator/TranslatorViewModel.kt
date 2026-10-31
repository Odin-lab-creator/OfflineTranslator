package com.example.offlinetranslator

import android.content.Context
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.languageid.LanguageIdentification
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class TranslatorViewModel : ViewModel() {

    val languages: List<String> = listOf(
        TranslateLanguage.ENGLISH, TranslateLanguage.RUSSIAN,
        TranslateLanguage.UKRAINIAN, TranslateLanguage.GERMAN,
        TranslateLanguage.FRENCH, TranslateLanguage.SPANISH,
        TranslateLanguage.ITALIAN, TranslateLanguage.PORTUGUESE,
        TranslateLanguage.POLISH, TranslateLanguage.TURKISH,
        TranslateLanguage.CHINESE, TranslateLanguage.JAPANESE,
        TranslateLanguage.KOREAN, TranslateLanguage.ARABIC
    )

    var input by mutableStateOf("")
    var output by mutableStateOf("")
    var source by mutableStateOf(TranslateLanguage.ENGLISH)
    var target by mutableStateOf(TranslateLanguage.RUSSIAN)
    var status by mutableStateOf("")
    var busy by mutableStateOf(false)

    private var translator: Translator? = null
    private var translatorKey: String? = null

    private fun translatorFor(src: String, dst: String): Translator {
        val key = "$src-$dst"
        if (key != translatorKey) {
            translator?.close()
            translator = Translation.getClient(
                TranslatorOptions.Builder()
                    .setSourceLanguage(src)
                    .setTargetLanguage(dst)
                    .build()
            )
            translatorKey = key
        }
        return translator!!
    }

    fun swapLanguages() {
        val s = source
        source = target
        target = s
        val i = input
        input = output
        output = i
    }

    private suspend fun runTranslation(text: String) {
        if (source == target) {
            output = text
            return
        }
        val t = translatorFor(source, target)
        status = "Проверяю языковую модель (при первом запуске скачивается)…"
        t.downloadModelIfNeeded(DownloadConditions.Builder().build()).await()
        status = ""
        output = t.translate(text).await()
    }

    private fun errorText(e: Exception): String =
        "Ошибка: ${e.localizedMessage ?: "не удалось перевести"}. " +
            "Если модель ещё не скачана — нужен интернет."

    fun translate() {
        val text = input.trim()
        if (text.isEmpty()) {
            output = ""
            return
        }
        viewModelScope.launch {
            busy = true
            try {
                runTranslation(text)
            } catch (e: Exception) {
                status = errorText(e)
            } finally {
                busy = false
            }
        }
    }

    /** Распознаёт текст на картинке, определяет язык и сразу переводит. */
    fun translateImage(context: Context, uri: Uri) {
        viewModelScope.launch {
            busy = true
            output = ""
            try {
                status = "Распознаю текст на изображении…"
                val image = InputImage.fromFilePath(context, uri)
                val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
                val result = try {
                    recognizer.process(image).await()
                } finally {
                    recognizer.close()
                }
                val text = result.textBlocks
                    .joinToString("\n") { block -> block.lines.joinToString(" ") { it.text } }
                    .trim()
                if (text.isEmpty()) {
                    status = "Текст не найден. Распознаётся латиница: английский, немецкий, французский и др."
                    return@launch
                }
                input = text.take(5000)
                status = "Определяю язык…"
                val code = try {
                    LanguageIdentification.getClient().identifyLanguage(input).await()
                } catch (e: Exception) {
                    "und"
                }
                if (code != "und" && code in languages) {
                    source = code
                    if (source == target) {
                        target = if (code == TranslateLanguage.RUSSIAN) TranslateLanguage.ENGLISH
                        else TranslateLanguage.RUSSIAN
                    }
                }
                status = ""
                runTranslation(input)
            } catch (e: Exception) {
                status = errorText(e)
            } finally {
                busy = false
            }
        }
    }

    fun detectLanguage() {
        val text = input.trim()
        if (text.isEmpty()) return
        viewModelScope.launch {
            try {
                val code = LanguageIdentification.getClient().identifyLanguage(text).await()
                if (code != "und" && code in languages) source = code
                else status = "Не удалось определить язык"
            } catch (e: Exception) {
                status = "Ошибка определения языка"
            }
        }
    }

    fun deleteModel(lang: String) {
        viewModelScope.launch {
            try {
                RemoteModelManager.getInstance()
                    .deleteDownloadedModel(TranslateRemoteModel.Builder(lang).build())
                    .await()
                status = "Модель удалена"
            } catch (e: Exception) {
                status = "Не удалось удалить модель"
            }
        }
    }

    override fun onCleared() {
        translator?.close()
        super.onCleared()
    }
}
