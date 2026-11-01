package com.example.offlinetranslator

import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.inputmethodservice.InputMethodService
import android.text.InputType
import android.text.TextUtils
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Клавиатура-переводчик: пишете на своём языке в любом мессенджере, нажимаете «Перевести» —
 * текст в поле заменяется переводом. Если в поле текст на языке собеседника, он переводится
 * на ваш язык. «↶» возвращает исходный текст.
 */
class TranslateKeyboardService : InputMethodService(), KeyboardView.Listener {
    private val scope = MainScope()
    private var keyboard: KeyboardView? = null
    private var directionView: TextView? = null
    private var statusView: TextView? = null
    private var undoView: TextView? = null
    private var translateView: TextView? = null
    private var job: Job? = null

    /** Для «↶»: что было в поле до перевода и что стало. */
    private var undoOriginal: String? = null
    private var undoTranslated: String? = null

    private val settings by lazy { AppSettings.get(applicationContext) }
    private val prefs by lazy { getSharedPreferences("keyboard", MODE_PRIVATE) }

    private val gold = 0xFFD4AF5A.toInt()
    private val muted = 0xFF8D90A0.toInt()
    private val bg = 0xFF0E1015.toInt()
    private val onGold = 0xFF14110A.toInt()

    private fun dp(v: Float) = (v * resources.displayMetrics.density).toInt()

    override fun onCreateInputView(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
        }
        root.addView(createBar())
        val view = KeyboardView(this, this)
        view.setRussian(prefs.getBoolean("russian", true))
        keyboard = view
        root.addView(view, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val nav = insets.getInsets(WindowInsetsCompat.Type.navigationBars())
            v.setPadding(0, 0, 0, nav.bottom)
            insets
        }
        return root
    }

    private fun createBar(): View {
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(8f), dp(4f), dp(8f), dp(2f))
        }
        val rune = TextView(this).apply {
            text = "ᛉ"
            setTextColor(gold)
            textSize = 18f
            typeface = Typeface.SERIF
            setPadding(dp(6f), 0, dp(8f), 0)
        }
        val direction = TextView(this).apply {
            setTextColor(gold)
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(10f), dp(8f), dp(10f), dp(8f))
            background = GradientDrawable().apply {
                cornerRadius = dp(6f).toFloat()
                setStroke(dp(1f), 0xFF5A4A22.toInt())
            }
            setOnClickListener { nextTarget() }
        }
        val status = TextView(this).apply {
            setTextColor(muted)
            textSize = 12f
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
            setPadding(dp(10f), 0, dp(6f), 0)
        }
        val undo = TextView(this).apply {
            text = "↶"
            setTextColor(gold)
            textSize = 22f
            setPadding(dp(10f), 0, dp(12f), 0)
            visibility = View.GONE
            contentDescription = "Вернуть исходный текст"
            setOnClickListener { undo() }
        }
        val translate = TextView(this).apply {
            text = "Перевести"
            setTextColor(onGold)
            textSize = 15f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(16f), dp(9f), dp(16f), dp(9f))
            background = GradientDrawable().apply {
                cornerRadius = dp(6f).toFloat()
                setColor(gold)
            }
            setOnClickListener { translateField() }
        }
        bar.addView(rune)
        bar.addView(direction)
        bar.addView(status, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        bar.addView(undo)
        bar.addView(translate)
        directionView = direction
        statusView = status
        undoView = undo
        translateView = translate
        updateDirection()
        return bar
    }

    private fun targets(): List<String> = settings.keyboardTargets.ifEmpty { listOf("en") }

    private fun currentTarget(): String {
        val list = targets()
        val saved = prefs.getString("target", null)
        return if (saved != null && saved in list) saved else list.first()
    }

    private fun nextTarget() {
        val list = targets()
        if (list.size < 2) {
            setStatus("Языки меняются в приложении: Инструменты → Клавиатура")
            return
        }
        val index = list.indexOf(currentTarget())
        prefs.edit().putString("target", list[(index + 1) % list.size]).apply()
        updateDirection()
    }

    private fun updateDirection() {
        directionView?.text = "${settings.myLanguage.uppercase()} ⇄ ${currentTarget().uppercase()}"
    }

    private fun setStatus(text: String) {
        statusView?.text = text
    }

    override fun onStartInputView(info: EditorInfo, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        updateDirection()
        if (!restarting) {
            setStatus("")
            undoOriginal = null
            undoView?.visibility = View.GONE
        }
        keyboard?.enterLabel = enterLabel(info)
        val password = isPassword(info)
        translateView?.alpha = if (password) 0.4f else 1f
        updateShift()
    }

    private fun isPassword(info: EditorInfo?): Boolean {
        val type = info?.inputType ?: return false
        val variation = type and InputType.TYPE_MASK_VARIATION
        return variation == InputType.TYPE_TEXT_VARIATION_PASSWORD ||
            variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
            variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD ||
            variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD
    }

    private fun enterAction(info: EditorInfo?): Int {
        val options = info?.imeOptions ?: return EditorInfo.IME_ACTION_NONE
        if (options and EditorInfo.IME_FLAG_NO_ENTER_ACTION != 0) return EditorInfo.IME_ACTION_NONE
        return options and EditorInfo.IME_MASK_ACTION
    }

    private fun enterLabel(info: EditorInfo?): String = when (enterAction(info)) {
        EditorInfo.IME_ACTION_SEND -> "➤"
        EditorInfo.IME_ACTION_SEARCH -> "⌕"
        EditorInfo.IME_ACTION_GO -> "→"
        EditorInfo.IME_ACTION_NEXT -> "⇥"
        EditorInfo.IME_ACTION_DONE -> "✓"
        else -> "↵"
    }

    private fun updateShift() {
        val ic = currentInputConnection ?: return
        val info = currentInputEditorInfo ?: return
        val type = info.inputType
        val isText = type and InputType.TYPE_MASK_CLASS == InputType.TYPE_CLASS_TEXT
        val caps = isText && type != InputType.TYPE_NULL && ic.getCursorCapsMode(type) != 0
        keyboard?.setAutoShift(caps)
    }

    // ---- KeyboardView.Listener ----

    override fun onText(text: String) {
        val ic = currentInputConnection ?: return
        if (text == " ") {
            // Двойной пробел после слова — точка.
            val before = ic.getTextBeforeCursor(2, 0)?.toString().orEmpty()
            if (before.length == 2 && before[1] == ' ' && before[0].isLetterOrDigit()) {
                ic.deleteSurroundingText(1, 0)
                ic.commitText(". ", 1)
                updateShift()
                return
            }
        }
        ic.commitText(text, 1)
        updateShift()
    }

    override fun onBackspace() {
        val ic = currentInputConnection ?: return
        val selected = ic.getSelectedText(0)
        if (!selected.isNullOrEmpty()) {
            ic.commitText("", 1)
        } else {
            sendDownUpKeyEvents(KeyEvent.KEYCODE_DEL)
        }
        updateShift()
    }

    override fun onEnter() {
        val ic = currentInputConnection ?: return
        val action = enterAction(currentInputEditorInfo)
        if (action != EditorInfo.IME_ACTION_NONE && action != EditorInfo.IME_ACTION_UNSPECIFIED) {
            ic.performEditorAction(action)
        } else {
            ic.commitText("\n", 1)
        }
        updateShift()
    }

    override fun onLanguageChanged(russian: Boolean) {
        prefs.edit().putBoolean("russian", russian).apply()
    }

    override fun onPicker() {
        val imm = getSystemService(InputMethodManager::class.java)
        imm?.showInputMethodPicker()
    }

    override fun haptics(): Boolean = settings.haptics

    // ---- Перевод ----

    /** Весь текст поля или выделенный фрагмент. */
    private fun readField(): Pair<String, Boolean>? {
        val ic = currentInputConnection ?: return null
        val selected = ic.getSelectedText(0)?.toString()
        if (!selected.isNullOrBlank()) return selected to true
        val before = ic.getTextBeforeCursor(MAX_INPUT, 0)?.toString().orEmpty()
        val after = ic.getTextAfterCursor(MAX_INPUT, 0)?.toString().orEmpty()
        val all = before + after
        return if (all.isBlank()) null else all to false
    }

    private fun replaceField(text: String, selectionOnly: Boolean) {
        val ic = currentInputConnection ?: return
        ic.beginBatchEdit()
        if (!selectionOnly) {
            val before = ic.getTextBeforeCursor(MAX_INPUT, 0)?.length ?: 0
            val after = ic.getTextAfterCursor(MAX_INPUT, 0)?.length ?: 0
            ic.deleteSurroundingText(before, after)
        }
        ic.commitText(text, 1)
        ic.endBatchEdit()
    }

    private fun translateField() {
        if (isPassword(currentInputEditorInfo)) {
            setStatus("В полях паролей перевод отключён")
            return
        }
        val (text, selectionOnly) = readField() ?: run {
            setStatus("Напишите текст, затем нажмите «Перевести»")
            return
        }
        job?.cancel()
        job = scope.launch {
            val mine = settings.myLanguage
            val target = currentTarget()
            setStatus("Перевожу…")
            translateView?.alpha = 0.6f
            try {
                val detected = try {
                    TranslationEngine.detect(text)
                } catch (e: Exception) {
                    null
                }
                val source = detected ?: mine
                val destination = if (source == target) mine else target
                if (source == destination) {
                    setStatus("Текст уже на языке «${Languages.name(destination)}»")
                    return@launch
                }
                val translated = TranslationEngine.translate(source, destination, text, settings.wifiOnly)
                replaceField(translated, selectionOnly)
                undoOriginal = text
                undoTranslated = translated
                undoView?.visibility = View.VISIBLE
                setStatus("${source.uppercase()} → ${destination.uppercase()}")
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                setStatus("Не удалось: ${e.localizedMessage ?: "ошибка"}. Нужны скачанные модели языков")
            } finally {
                translateView?.alpha = 1f
                updateShift()
            }
        }
    }

    private fun undo() {
        val original = undoOriginal ?: return
        val translated = undoTranslated.orEmpty()
        val ic = currentInputConnection ?: return
        val selected = ic.getSelectedText(0)?.toString()
        if (!selected.isNullOrEmpty() && selected == translated) {
            ic.commitText(original, 1)
        } else {
            val before = ic.getTextBeforeCursor(MAX_INPUT, 0)?.toString().orEmpty()
            val after = ic.getTextAfterCursor(MAX_INPUT, 0)?.toString().orEmpty()
            val all = before + after
            if (all == translated) {
                replaceField(original, selectionOnly = false)
            } else if (before.endsWith(translated)) {
                ic.beginBatchEdit()
                ic.deleteSurroundingText(translated.length, 0)
                ic.commitText(original, 1)
                ic.endBatchEdit()
            } else {
                setStatus("Текст уже изменился — вернуть не получится")
                return
            }
        }
        undoOriginal = null
        undoView?.visibility = View.GONE
        setStatus("Исходный текст возвращён")
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
