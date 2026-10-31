package com.example.offlinetranslator

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

    fun translate() {
        val text = input.trim()
        if (text.isEmpty()) {
            output = ""
            return
        }
        if (source == target) {
            output = text
            return
        }
        viewModelScope.launch {
            busy = true
            try {
                val t = translatorFor(source, target)
                status = "Проверяю языковую модель (при первом запуске скачивается)…"
                t.downloadModelIfNeeded(DownloadConditions.Builder().build()).await()
                status = ""
                output = t.translate(text).await()
            } catch (e: Exception) {
                status = "Ошибка: ${e.localizedMessage ?: "не удалось перевести"}. " +
                    "Если модель ещё не скачана — нужен интернет."
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
