package com.example.offlinetranslator

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.util.TypedValue
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.google.mlkit.vision.common.InputImage
import kotlin.math.abs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * Перевод экрана поверх любого приложения: плавающая кнопка делает снимок экрана,
 * распознаёт текст и показывает перевод прямо поверх оригинала.
 */
class ScreenTranslateService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private lateinit var windowManager: WindowManager
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var bubble: View? = null
    private var bubbleParams: WindowManager.LayoutParams? = null
    private var resultView: View? = null
    private var working = false
    private var screenWidth = 0
    private var screenHeight = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (projection != null) return START_NOT_STICKY

        startAsForeground()
        val resultCode = intent?.getIntExtra(EXTRA_CODE, 0) ?: 0
        val data: Intent? = if (Build.VERSION.SDK_INT >= 33) {
            intent?.getParcelableExtra(EXTRA_DATA, Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra(EXTRA_DATA)
        }
        if (data == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val mp = manager.getMediaProjection(resultCode, data)
        if (mp == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        projection = mp
        mp.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                stopSelf()
            }
        }, Handler(Looper.getMainLooper()))

        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = realMetrics()
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        val imageReader = ImageReader.newInstance(screenWidth, screenHeight, PixelFormat.RGBA_8888, 2)
        reader = imageReader
        display = mp.createVirtualDisplay(
            "valhalla-screen",
            screenWidth,
            screenHeight,
            metrics.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader.surface,
            null,
            null
        )
        showBubble()
        running = true
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        running = false
        scope.cancel()
        removeResult()
        bubble?.let { runCatching { windowManager.removeView(it) } }
        bubble = null
        display?.release()
        reader?.close()
        projection?.stop()
        projection = null
        super.onDestroy()
    }

    // ---- Уведомление ----

    private fun startAsForeground() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL, "Перевод экрана", NotificationManager.IMPORTANCE_LOW)
            )
        }
        val stop = PendingIntent.getService(
            this,
            1,
            Intent(this, ScreenTranslateService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_rune)
            .setContentTitle("Перевод экрана включён")
            .setContentText("Нажмите на золотую кнопку, чтобы перевести экран")
            .setOngoing(true)
            .addAction(0, "Выключить", stop)
            .build()
        val type = if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION else 0
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, type)
    }

    // ---- Плавающая кнопка ----

    private fun overlayType(): Int =
        if (Build.VERSION.SDK_INT >= 26) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

    private fun dp(value: Float): Int =
        TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, value, resources.displayMetrics).toInt()

    @SuppressLint("ClickableViewAccessibility")
    private fun showBubble() {
        val size = dp(56f)
        val view = ImageView(this).apply {
            setImageResource(R.drawable.ic_rune)
            setColorFilter(GOLD)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            setPadding(dp(13f), dp(13f), dp(13f), dp(13f))
            contentDescription = "Перевести экран"
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(BG)
                setStroke(dp(2f), GOLD)
            }
            elevation = dp(6f).toFloat()
        }
        val params = WindowManager.LayoutParams(
            size,
            size,
            overlayType(),
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = screenWidth - size - dp(12f)
            y = screenHeight / 3
        }
        val slop = ViewConfiguration.get(this).scaledTouchSlop
        var downX = 0f
        var downY = 0f
        var startX = 0
        var startY = 0
        var downTime = 0L
        var moved = false
        view.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    downX = event.rawX
                    downY = event.rawY
                    startX = params.x
                    startY = params.y
                    downTime = System.currentTimeMillis()
                    moved = false
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - downX
                    val dy = event.rawY - downY
                    if (abs(dx) > slop || abs(dy) > slop) moved = true
                    if (moved) {
                        params.x = (startX + dx).toInt()
                        params.y = (startY + dy).toInt()
                        windowManager.updateViewLayout(v, params)
                    }
                }
                MotionEvent.ACTION_UP -> {
                    if (!moved) {
                        if (System.currentTimeMillis() - downTime > 700) stopSelf() else translateScreen()
                    }
                }
            }
            true
        }
        windowManager.addView(view, params)
        bubble = view
        bubbleParams = params
    }

    // ---- Снимок экрана, распознавание и перевод ----

    private fun translateScreen() {
        if (working) return
        if (resultView != null) {
            removeResult()
            return
        }
        working = true
        val settings = AppSettings.get(this)
        scope.launch {
            try {
                bubble?.visibility = View.INVISIBLE
                delay(250)
                val bitmap = grabFrame()
                bubble?.visibility = View.VISIBLE
                if (bitmap == null) {
                    showPanel("Не удалось получить изображение экрана. Попробуйте ещё раз.")
                    return@launch
                }
                bubble?.alpha = 0.5f
                val script = TranslationEngine.resolveScript(settings.ocrScript, settings.lastSource)
                if (script == OcrScript.CYRILLIC) {
                    val text = TranslationEngine.recognizeBitmap(this@ScreenTranslateService, bitmap, script, settings.lastSource)
                    bitmap.recycle()
                    if (text.isBlank()) {
                        showPanel("Текст на экране не найден")
                        return@launch
                    }
                    val source = TranslationEngine.detect(text) ?: settings.lastSource
                    val target = Languages.otherTarget(source, settings.lastTarget)
                    val translated = TranslationEngine.translate(source, target, text, settings.wifiOnly)
                    HistoryStore.get(this@ScreenTranslateService).add(source, target, text, translated)
                    showPanel(translated)
                    return@launch
                }
                val recognizer = TranslationEngine.mlKitRecognizer(script)
                val result = try {
                    recognizer.process(InputImage.fromBitmap(bitmap, 0)).await()
                } finally {
                    recognizer.close()
                    bitmap.recycle()
                }
                val separator = TranslationEngine.lineSeparator(script)
                val blocks = result.textBlocks.mapNotNull { block ->
                    val box = block.boundingBox ?: return@mapNotNull null
                    val text = block.lines.joinToString(separator) { it.text }.trim()
                    if (text.length < 2) null else Triple(text, box, block.lines.size.coerceAtLeast(1))
                }
                if (blocks.isEmpty()) {
                    showPanel("Текст на экране не найден")
                    return@launch
                }
                val all = blocks.joinToString(" ") { it.first }
                val source = TranslationEngine.detect(all) ?: settings.lastSource
                val target = Languages.otherTarget(source, settings.lastTarget)
                val translated = blocks.map { (text, box, lines) ->
                    Triple(TranslationEngine.translate(source, target, text, settings.wifiOnly), box, lines)
                }
                showBoxes(translated)
            } catch (e: Exception) {
                bubble?.visibility = View.VISIBLE
                showPanel("Не удалось перевести: ${e.localizedMessage ?: "ошибка"}. Для первой загрузки модели нужен интернет.")
            } finally {
                bubble?.alpha = 1f
                working = false
            }
        }
    }

    private suspend fun grabFrame(): Bitmap? {
        val imageReader = reader ?: return null
        var image = imageReader.acquireLatestImage()
        var tries = 0
        while (image == null && tries < 10) {
            delay(80)
            image = imageReader.acquireLatestImage()
            tries++
        }
        if (image == null) return null
        return try {
            val plane = image.planes[0]
            val pixelStride = plane.pixelStride
            val rowPadding = plane.rowStride - pixelStride * image.width
            val padded = Bitmap.createBitmap(
                image.width + rowPadding / pixelStride,
                image.height,
                Bitmap.Config.ARGB_8888
            )
            padded.copyPixelsFromBuffer(plane.buffer)
            val cropped = Bitmap.createBitmap(padded, 0, 0, image.width, image.height)
            if (cropped != padded) padded.recycle()
            cropped
        } finally {
            image.close()
        }
    }

    private fun overlayParams(): WindowManager.LayoutParams =
        WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            overlayType(),
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            if (Build.VERSION.SDK_INT >= 28) {
                layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            }
        }

    /** Переводы поверх тех мест, где был текст. Нажатие в любом месте закрывает. */
    private fun showBoxes(items: List<Triple<String, android.graphics.Rect, Int>>) {
        removeResult()
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.argb(70, 0, 0, 0))
            setOnClickListener { removeResult() }
        }
        items.forEach { (text, box, lines) ->
            val lineHeight = box.height().toFloat() / lines
            val textPx = (lineHeight * 0.62f).coerceIn(dp(10f).toFloat(), dp(26f).toFloat())
            val label = TextView(this).apply {
                this.text = text
                setTextColor(RESULT)
                setTextSize(TypedValue.COMPLEX_UNIT_PX, textPx)
                minWidth = box.width()
                maxWidth = (box.width() * 1.6f).toInt().coerceAtMost(screenWidth)
                setPadding(dp(4f), dp(2f), dp(4f), dp(2f))
                background = GradientDrawable().apply {
                    cornerRadius = dp(4f).toFloat()
                    setColor(Color.argb(235, 18, 20, 26))
                    setStroke(dp(1f), GOLD_DIM)
                }
            }
            val lp = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                leftMargin = box.left
                topMargin = box.top
            }
            root.addView(label, lp)
        }
        root.addView(closeHint(), FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
        ).apply { bottomMargin = dp(48f) })
        windowManager.addView(root, overlayParams())
        resultView = root
        bubble?.let { windowManager.removeView(it); windowManager.addView(it, bubbleParams) }
    }

    /** Перевод одним блоком внизу экрана (для кириллицы и сообщений). */
    private fun showPanel(message: String) {
        removeResult()
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.argb(110, 0, 0, 0))
            setOnClickListener { removeResult() }
        }
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18f), dp(16f), dp(18f), dp(16f))
            background = GradientDrawable().apply {
                cornerRadius = dp(12f).toFloat()
                setColor(BG)
                setStroke(dp(1f), GOLD)
            }
        }
        card.addView(TextView(this).apply {
            text = "VALHALLA"
            setTextColor(GOLD)
            typeface = Typeface.SERIF
            letterSpacing = 0.2f
            textSize = 14f
        })
        val scroll = ScrollView(this)
        scroll.addView(TextView(this).apply {
            text = message
            setTextColor(RESULT)
            typeface = Typeface.SERIF
            textSize = 20f
            setTextIsSelectable(false)
            setPadding(0, dp(8f), 0, dp(8f))
        })
        card.addView(scroll, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { height = minOf(dp(360f), screenHeight / 2).coerceAtLeast(dp(80f)) })
        card.addView(closeHint())
        root.addView(card, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.BOTTOM
        ).apply {
            leftMargin = dp(12f)
            rightMargin = dp(12f)
            bottomMargin = dp(48f)
        })
        windowManager.addView(root, overlayParams())
        resultView = root
    }

    private fun closeHint(): TextView = TextView(this).apply {
        text = "Нажмите в любом месте, чтобы закрыть"
        setTextColor(MUTED)
        textSize = 12f
        gravity = Gravity.CENTER
        setPadding(dp(10f), dp(6f), dp(10f), dp(6f))
    }

    private fun removeResult() {
        resultView?.let { runCatching { windowManager.removeView(it) } }
        resultView = null
    }

    private fun realMetrics(): DisplayMetrics {
        val metrics = DisplayMetrics()
        if (Build.VERSION.SDK_INT >= 30) {
            val bounds = windowManager.currentWindowMetrics.bounds
            metrics.widthPixels = bounds.width()
            metrics.heightPixels = bounds.height()
            metrics.densityDpi = resources.displayMetrics.densityDpi
        } else {
            @Suppress("DEPRECATION")
            windowManager.defaultDisplay.getRealMetrics(metrics)
        }
        return metrics
    }

    companion object {
        const val EXTRA_CODE = "code"
        const val EXTRA_DATA = "data"
        const val ACTION_STOP = "com.example.offlinetranslator.STOP_SCREEN"
        private const val CHANNEL = "screen_translate"
        private const val NOTIFICATION_ID = 7
        private val GOLD = Color.rgb(0xD4, 0xAF, 0x5A)
        private val GOLD_DIM = Color.rgb(0x5A, 0x4A, 0x22)
        private val BG = Color.rgb(0x12, 0x14, 0x1A)
        private val RESULT = Color.rgb(0xF2, 0xEB, 0xD3)
        private val MUTED = Color.rgb(0x8D, 0x90, 0xA0)

        /** Работает ли сейчас перевод экрана (для экрана настроек). */
        var running by mutableStateOf(false)
            private set
    }
}
