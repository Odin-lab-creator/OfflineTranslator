package com.example.offlinetranslator

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import com.googlecode.tesseract.android.TessBaseAPI
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
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext

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

    /** Какой алфавит распознавать: из настройки или, в режиме «Авто», по исходному языку. */
    fun resolveScript(setting: OcrScript, sourceLang: String): OcrScript =
        if (setting != OcrScript.AUTO) setting else when (sourceLang) {
            in Languages.cyrillic -> OcrScript.CYRILLIC
            TranslateLanguage.CHINESE -> OcrScript.CHINESE
            TranslateLanguage.JAPANESE -> OcrScript.JAPANESE
            TranslateLanguage.KOREAN -> OcrScript.KOREAN
            else -> OcrScript.LATIN
        }

    /** Распознаёт текст на картинке и склеивает строки абзацев, чтобы перевод был связным. */
    suspend fun recognize(context: Context, uri: Uri, script: OcrScript, sourceLang: String): String =
        if (script == OcrScript.CYRILLIC) {
            recognizeWithTesseract(context, uri, sourceLang)
        } else {
            recognizeWithMlKit(context, uri, script)
        }

    private suspend fun recognizeWithMlKit(context: Context, uri: Uri, script: OcrScript): String {
        val image = InputImage.fromFilePath(context, uri)
        val recognizer: TextRecognizer = when (script) {
            OcrScript.CHINESE -> TextRecognition.getClient(ChineseTextRecognizerOptions.Builder().build())
            OcrScript.JAPANESE -> TextRecognition.getClient(JapaneseTextRecognizerOptions.Builder().build())
            OcrScript.KOREAN -> TextRecognition.getClient(KoreanTextRecognizerOptions.Builder().build())
            else -> TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        }
        val result = try {
            recognizer.process(image).await()
        } finally {
            recognizer.close()
        }
        val cjk = script == OcrScript.CHINESE || script == OcrScript.JAPANESE
        return joinBlocks(result, separator = if (cjk) "" else " ")
    }

    // ---- Кириллица: Tesseract, модели tessdata_fast кладутся в APK при сборке ----

    private suspend fun recognizeWithTesseract(context: Context, uri: Uri, sourceLang: String): String =
        withContext(Dispatchers.Default) {
            val dataPath = ensureTessData(context)
            val bitmap = loadBitmap(context, uri)
            val api = TessBaseAPI()
            try {
                val langs = if (sourceLang == "uk") "ukr+rus+eng" else "rus+ukr+eng"
                check(api.init(dataPath, langs)) { "не удалось загрузить модель кириллицы" }
                api.setImage(bitmap)
                val raw = api.getUTF8Text().orEmpty()
                raw.split(Regex("\\n\\s*\\n"))
                    .map { paragraph -> paragraph.lines().map { it.trim() }.filter { it.isNotEmpty() }.joinToString(" ") }
                    .filter { it.isNotBlank() }
                    .joinToString("\n")
                    .trim()
            } finally {
                api.recycle()
                bitmap.recycle()
            }
        }

    private suspend fun ensureTessData(context: Context): String = withContext(Dispatchers.IO) {
        val root = File(context.filesDir, "tesseract")
        val tessdata = File(root, "tessdata").apply { mkdirs() }
        val assets = context.assets.list("tessdata").orEmpty()
        check(assets.isNotEmpty()) { "модели кириллицы не найдены в приложении" }
        assets.forEach { name ->
            val target = File(tessdata, name)
            if (!target.exists() || target.length() == 0L) {
                context.assets.open("tessdata/$name").use { input ->
                    target.outputStream().use { input.copyTo(it) }
                }
            }
        }
        root.absolutePath
    }

    private suspend fun loadBitmap(context: Context, uri: Uri): Bitmap = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        var sample = 1
        while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 2600) sample *= 2
        val decoded = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample })
        } ?: error("не удалось открыть изображение")
        val orientation = try {
            resolver.openInputStream(uri)?.use {
                ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            } ?: ExifInterface.ORIENTATION_NORMAL
        } catch (e: Exception) {
            ExifInterface.ORIENTATION_NORMAL
        }
        val degrees = when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> 90f
            ExifInterface.ORIENTATION_ROTATE_180 -> 180f
            ExifInterface.ORIENTATION_ROTATE_270 -> 270f
            else -> 0f
        }
        val upright = if (degrees == 0f) decoded else {
            val rotated = Bitmap.createBitmap(
                decoded, 0, 0, decoded.width, decoded.height,
                Matrix().apply { postRotate(degrees) }, true
            )
            if (rotated != decoded) decoded.recycle()
            rotated
        }
        if (upright.config == Bitmap.Config.ARGB_8888) upright else {
            val copy = upright.copy(Bitmap.Config.ARGB_8888, false)
            upright.recycle()
            copy
        }
    }

    fun joinBlocks(result: Text, separator: String = " "): String =
        result.textBlocks
            .joinToString("\n") { block -> block.lines.joinToString(separator) { it.text } }
            .trim()
}
