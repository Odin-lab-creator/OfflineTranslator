package com.example.offlinetranslator

import android.content.Context
import android.net.Uri
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.languageid.LanguageIdentification
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.tasks.await

/**
 * Общий «движок» для всех экранов: перевод, языковые модели, определение языка и распознавание текста.
 * Вызывается из главного потока (корутины на Main).
 */
object TranslationEngine {
    private var translator: Translator? = null
    private var translatorKey: String? = null

    private val modelManager by lazy { RemoteModelManager.getInstance() }
    private val languageId by lazy { LanguageIdentification.getClient() }

    private fun translatorFor(src: String, dst: String): Translator {
        val key = "$src-$dst"
        val current = translator
        if (current != null && key == translatorKey) return current
        current?.close()
        val created = Translation.getClient(
            TranslatorOptions.Builder()
                .setSourceLanguage(src)
                .setTargetLanguage(dst)
                .build()
        )
        translator = created
        translatorKey = key
        return created
    }

    private fun conditions(wifiOnly: Boolean): DownloadConditions =
        DownloadConditions.Builder().apply { if (wifiOnly) requireWifi() }.build()

    /** Скачанные языковые модели. Английский встроен всегда. */
    suspend fun downloadedLanguages(): Set<String> =
        modelManager.getDownloadedModels(TranslateRemoteModel::class.java).await()
            .map { it.language }
            .toSet() + TranslateLanguage.ENGLISH

    suspend fun translate(src: String, dst: String, text: String, wifiOnly: Boolean = false): String {
        if (src == dst) return text
        val t = translatorFor(src, dst)
        t.downloadModelIfNeeded(conditions(wifiOnly)).await()
        return t.translate(text).await()
    }

    suspend fun download(lang: String, wifiOnly: Boolean) {
        modelManager.download(TranslateRemoteModel.Builder(lang).build(), conditions(wifiOnly)).await()
    }

    suspend fun delete(lang: String) {
        if (translatorKey?.split("-")?.contains(lang) == true) {
            translator?.close()
            translator = null
            translatorKey = null
        }
        modelManager.deleteDownloadedModel(TranslateRemoteModel.Builder(lang).build()).await()
    }

    /** Определяет язык текста. Возвращает код языка или null, если не уверен. */
    suspend fun detect(text: String): String? {
        val code = languageId.identifyLanguage(text).await()
        return code.takeIf { it != "und" && it in Languages.all }
    }

    /** Распознаёт текст на картинке и склеивает строки абзацев, чтобы перевод был связным. */
    suspend fun recognize(context: Context, uri: Uri): String {
        val image = InputImage.fromFilePath(context, uri)
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        val result = try {
            recognizer.process(image).await()
        } finally {
            recognizer.close()
        }
        return joinBlocks(result)
    }

    fun joinBlocks(result: Text): String =
        result.textBlocks
            .joinToString("\n") { block -> block.lines.joinToString(" ") { it.text } }
            .trim()
}
