package com.example.offlinetranslator

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.os.Handler
import android.os.Looper
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View

/**
 * Клавиатура, нарисованная на одном View: русская ЙЦУКЕН, английская QWERTY и две страницы символов.
 * Долгое нажатие на верхний ряд — цифры, «е» — «ё», «ь» — «ъ», 🌐 — выбор другой клавиатуры.
 */
@SuppressLint("ViewConstructor")
class KeyboardView(context: Context, private val listener: Listener) : View(context) {

    interface Listener {
        fun onText(text: String)
        fun onBackspace()
        fun onEnter()
        fun onLanguageChanged(russian: Boolean)
        fun onPicker()
        fun haptics(): Boolean
    }

    enum class Action { CHAR, SHIFT, BACKSPACE, ENTER, SPACE, SYMBOLS, LETTERS, SYM_MORE, SYM_BACK, GLOBE }

    class Key(
        val label: String,
        val action: Action = Action.CHAR,
        val weight: Float = 1f,
        val alt: String? = null
    ) {
        val bounds = RectF()
    }

    private class Row(val keys: List<Key>, val stretch: Boolean)

    private enum class Page { RU, EN, SYM1, SYM2 }

    private enum class Shift { OFF, ONCE, LOCK }

    private val density = resources.displayMetrics.density
    private fun dp(v: Float) = v * density

    private var russian = true
    private var page = Page.RU
    private var shift = Shift.OFF
    private var lastShiftTap = 0L

    /** Подпись клавиши Enter: ↵ или действие поля («Отпр.», «Найти»…). */
    var enterLabel: String = "↵"
        set(value) {
            field = value
            invalidate()
        }

    private val digits = listOf("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")

    private fun letters(chars: String, withDigits: Boolean = false, alts: Map<String, String> = emptyMap()) =
        chars.map { it.toString() }.mapIndexed { i, c ->
            Key(c, alt = alts[c] ?: if (withDigits) digits.getOrNull(i) else null)
        }

    private fun bottomRow(lettersPage: Boolean): Row = Row(
        listOf(
            if (lettersPage) Key("?123", Action.SYMBOLS, 1.5f) else Key(if (russian) "АБВ" else "ABC", Action.LETTERS, 1.5f),
            Key("🌐", Action.GLOBE, 1.1f),
            Key(",", alt = "!"),
            Key(if (russian) "Русский" else "English", Action.SPACE, 4.6f),
            Key(".", alt = "?"),
            Key("↵", Action.ENTER, 1.8f)
        ),
        stretch = true
    )

    private val pages: Map<Page, List<Row>> by lazy {
        val ruAlts = mapOf("е" to "ё", "ь" to "ъ")
        mapOf(
            Page.RU to listOf(
                Row(letters("йцукенгшщзх", withDigits = true), false),
                Row(letters("фывапролджэ"), false),
                Row(listOf(Key("⇧", Action.SHIFT)) + letters("ячсмитьбю", alts = ruAlts) + Key("⌫", Action.BACKSPACE), false)
            ),
            Page.EN to listOf(
                Row(letters("qwertyuiop", withDigits = true), false),
                Row(letters("asdfghjkl"), false),
                Row(listOf(Key("⇧", Action.SHIFT, 1.5f)) + letters("zxcvbnm") + Key("⌫", Action.BACKSPACE, 1.5f), false)
            ),
            Page.SYM1 to listOf(
                Row(digits.map { Key(it) }, false),
                Row(listOf("@", "#", "₽", "_", "&", "-", "+", "(", ")", "/").map { Key(it) }, false),
                Row(
                    listOf(Key("=\\<", Action.SYM_MORE, 1.5f)) +
                        listOf("*", "\"", "'", ":", ";", "!", "?").map { Key(it) } +
                        Key("⌫", Action.BACKSPACE, 1.5f),
                    false
                )
            ),
            Page.SYM2 to listOf(
                Row(listOf("~", "`", "|", "•", "√", "π", "÷", "×", "§", "∆").map { Key(it) }, false),
                Row(listOf("€", "$", "£", "¥", "^", "°", "=", "{", "}", "\\").map { Key(it) }, false),
                Row(
                    listOf(Key("?123", Action.SYM_BACK, 1.5f)) +
                        listOf("%", "©", "®", "[", "]", "<", ">").map { Key(it) } +
                        Key("⌫", Action.BACKSPACE, 1.5f),
                    false
                )
            )
        )
    }

    private var rows: List<Row> = emptyList()

    private val rowHeight = dp(54f)
    private val gap = dp(3f)
    private val corner = dp(7f)

    private val keyPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER }
    private val altPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.RIGHT
        textSize = dp(10f)
    }

    private val colorBg = 0xFF0E1015.toInt()
    private val colorKey = 0xFF1F2330.toInt()
    private val colorSpecial = 0xFF2B3040.toInt()
    private val colorPressed = 0xFF3A4157.toInt()
    private val colorText = 0xFFE8E4D8.toInt()
    private val colorMuted = 0xFF8D90A0.toInt()
    private val colorGold = 0xFFD4AF5A.toInt()
    private val colorOnGold = 0xFF14110A.toInt()

    init {
        isHapticFeedbackEnabled = true
        rebuild()
    }

    fun setRussian(value: Boolean) {
        russian = value
        page = if (value) Page.RU else Page.EN
        rebuild()
    }

    /** Заглавная буква в начале предложения. */
    fun setAutoShift(on: Boolean) {
        if (shift == Shift.LOCK) return
        val wanted = if (on) Shift.ONCE else Shift.OFF
        if (shift != wanted) {
            shift = wanted
            invalidate()
        }
    }

    private fun rebuild() {
        val base = pages.getValue(page)
        rows = base + bottomRow(page == Page.RU || page == Page.EN)
        layoutKeys()
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val width = MeasureSpec.getSize(widthMeasureSpec)
        val height = (rowHeight * 4 + dp(8f)).toInt()
        setMeasuredDimension(width, height)
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        layoutKeys()
    }

    private fun layoutKeys() {
        val w = width.toFloat()
        if (w <= 0f) return
        val units = if (page == Page.RU) 11f else 10f
        var top = dp(4f)
        rows.forEach { row ->
            val total = row.keys.sumOf { it.weight.toDouble() }.toFloat()
            val unit = if (row.stretch) w / total else w / units
            var left = if (row.stretch) 0f else (w - unit * total) / 2f
            row.keys.forEach { key ->
                val kw = unit * key.weight
                key.bounds.set(left + gap, top + gap, left + kw - gap, top + rowHeight - gap)
                left += kw
            }
            top += rowHeight
        }
    }

    private fun isSpecial(key: Key) = key.action != Action.CHAR && key.action != Action.SPACE

    private fun shownLabel(key: Key): String = when (key.action) {
        Action.CHAR -> if (shift != Shift.OFF && key.label.length == 1) key.label.uppercase() else key.label
        Action.ENTER -> enterLabel
        Action.SHIFT -> if (shift == Shift.LOCK) "⇪" else "⇧"
        else -> key.label
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(colorBg)
        val pressed = active.values.map { it.key }.toSet()
        rows.forEach { row ->
            row.keys.forEach { key ->
                val isEnter = key.action == Action.ENTER
                val shiftOn = key.action == Action.SHIFT && shift != Shift.OFF
                keyPaint.color = when {
                    key in pressed -> colorPressed
                    isEnter -> colorGold
                    shiftOn -> colorSpecial
                    isSpecial(key) -> colorSpecial
                    else -> colorKey
                }
                canvas.drawRoundRect(key.bounds, corner, corner, keyPaint)
                val label = shownLabel(key)
                textPaint.color = when {
                    isEnter -> colorOnGold
                    shiftOn -> colorGold
                    key.action == Action.SPACE -> colorMuted
                    else -> colorText
                }
                textPaint.typeface = if (key.action == Action.CHAR) Typeface.DEFAULT else Typeface.DEFAULT_BOLD
                textPaint.textSize = when {
                    key.action == Action.SPACE -> dp(13f)
                    label.length > 2 -> dp(14f)
                    key.action == Action.CHAR -> dp(22f)
                    else -> dp(20f)
                }
                val y = key.bounds.centerY() - (textPaint.descent() + textPaint.ascent()) / 2f
                canvas.drawText(label, key.bounds.centerX(), y, textPaint)
                val alt = key.alt
                if (alt != null && key.action == Action.CHAR) {
                    altPaint.color = colorMuted
                    canvas.drawText(alt, key.bounds.right - dp(5f), key.bounds.top + dp(12f), altPaint)
                }
            }
        }
    }

    // ---- Нажатия ----

    private class Press(val key: Key) {
        var longFired = false
    }

    private val active = HashMap<Int, Press>()
    private val handler = Handler(Looper.getMainLooper())
    private var repeatRunnable: Runnable? = null
    private var longRunnable: Runnable? = null

    private fun keyAt(x: Float, y: Float): Key? {
        rows.forEach { row ->
            row.keys.forEach { key ->
                val b = key.bounds
                if (y >= b.top - gap && y <= b.bottom + gap && x >= b.left - gap && x <= b.right + gap) return key
            }
        }
        return null
    }

    private fun tick() {
        if (listener.haptics()) performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val index = event.actionIndex
                val id = event.getPointerId(index)
                val key = keyAt(event.getX(index), event.getY(index)) ?: return true
                // Быстрый набор двумя пальцами: предыдущую букву вводим сразу.
                active.keys.toList().forEach { other -> release(other, commit = true) }
                press(id, key)
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP -> {
                release(event.getPointerId(event.actionIndex), commit = true)
            }
            MotionEvent.ACTION_CANCEL -> {
                active.keys.toList().forEach { release(it, commit = false) }
            }
        }
        return true
    }

    private fun press(id: Int, key: Key) {
        val press = Press(key)
        active[id] = press
        tick()
        cancelTimers()
        when (key.action) {
            Action.BACKSPACE -> {
                listener.onBackspace()
                press.longFired = true
                val repeat = object : Runnable {
                    override fun run() {
                        listener.onBackspace()
                        handler.postDelayed(this, 55)
                    }
                }
                repeatRunnable = repeat
                handler.postDelayed(repeat, 420)
            }
            else -> {
                val hasLong = key.alt != null || key.action == Action.GLOBE || key.action == Action.SPACE
                if (hasLong) {
                    val long = Runnable {
                        press.longFired = true
                        tick()
                        when (key.action) {
                            Action.GLOBE, Action.SPACE -> listener.onPicker()
                            else -> commitChar(key.alt.orEmpty())
                        }
                    }
                    longRunnable = long
                    handler.postDelayed(long, 380)
                }
            }
        }
        invalidate()
    }

    private fun cancelTimers() {
        repeatRunnable?.let { handler.removeCallbacks(it) }
        longRunnable?.let { handler.removeCallbacks(it) }
        repeatRunnable = null
        longRunnable = null
    }

    private fun release(id: Int, commit: Boolean) {
        val press = active.remove(id) ?: return
        cancelTimers()
        if (commit && !press.longFired) perform(press.key)
        invalidate()
    }

    private fun commitChar(text: String) {
        if (text.isEmpty()) return
        val out = if (shift != Shift.OFF && text.length == 1) text.uppercase() else text
        listener.onText(out)
        if (shift == Shift.ONCE) {
            shift = Shift.OFF
            invalidate()
        }
    }

    private fun perform(key: Key) {
        when (key.action) {
            Action.CHAR -> commitChar(key.label)
            Action.SPACE -> listener.onText(" ")
            Action.ENTER -> listener.onEnter()
            Action.BACKSPACE -> Unit
            Action.SHIFT -> {
                val now = System.currentTimeMillis()
                shift = when (shift) {
                    Shift.OFF -> Shift.ONCE
                    Shift.ONCE -> if (now - lastShiftTap < 350) Shift.LOCK else Shift.OFF
                    Shift.LOCK -> Shift.OFF
                }
                lastShiftTap = now
            }
            Action.SYMBOLS, Action.SYM_BACK -> {
                page = Page.SYM1
                rebuild()
            }
            Action.SYM_MORE -> {
                page = Page.SYM2
                rebuild()
            }
            Action.LETTERS -> {
                page = if (russian) Page.RU else Page.EN
                rebuild()
            }
            Action.GLOBE -> {
                russian = !russian
                page = if (russian) Page.RU else Page.EN
                shift = Shift.OFF
                listener.onLanguageChanged(russian)
                rebuild()
            }
        }
        invalidate()
    }

    override fun onDetachedFromWindow() {
        cancelTimers()
        active.clear()
        super.onDetachedFromWindow()
    }
}
