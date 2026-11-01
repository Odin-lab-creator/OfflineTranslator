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
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioPlaybackCaptureConfiguration
import android.media.AudioRecord
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import androidx.annotation.RequiresApi
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import org.vosk.Recognizer

/**
 * Живые субтитры: слушает звук других приложений (видео, подкасты), распознаёт речь офлайн
 * и показывает перевод внизу экрана поверх всех приложений. Нужен Android 10+.
 */
class LiveCaptionService : Service() {
    private val scope = MainScope()
    private val main = Handler(Looper.getMainLooper())
    private var projection: MediaProjection? = null
    private var record: AudioRecord? = null
    private var recognizer: Recognizer? = null
    private var worker: Thread? = null
    @Volatile
    private var listening = false

    private lateinit var windowManager: WindowManager
    private var panel: View? = null
    private var originalView: TextView? = null
    private var translatedView: TextView? = null
    private val lines = ArrayDeque<String>()
    private var source = "en"
    private var target = "ru"

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (projection != null || Build.VERSION.SDK_INT < 29) {
            if (projection == null) stopSelf()
            return START_NOT_STICKY
        }
        startAsForeground()
        val settings = AppSettings.get(applicationContext)
        source = intent?.getStringExtra(EXTRA_SOURCE) ?: "en"
        target = settings.myLanguage.let { if (it == source) Languages.otherTarget(source, it) else it }
        val resultCode = intent?.getIntExtra(EXTRA_CODE, 0) ?: 0
        val data: Intent? = if (Build.VERSION.SDK_INT >= 33) {
            intent?.getParcelableExtra(EXTRA_DATA, Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra(EXTRA_DATA)
        }
        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val mp = data?.let { manager.getMediaProjection(resultCode, it) }
        if (mp == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        projection = mp
        mp.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                stopSelf()
            }
        }, main)
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        showPanel()
        running = true
        scope.launch {
            try {
                setOriginal("Загружаю модель речи…")
                val model = Voice.model(source)
                recognizer = Recognizer(model, SAMPLE_RATE.toFloat())
                startCapture(mp)
                setOriginal("Слушаю звук: ${Languages.name(source)} → ${Languages.name(target)}")
            } catch (e: Exception) {
                setOriginal("Не удалось запустить: ${e.localizedMessage ?: "ошибка"}")
            }
        }
        return START_NOT_STICKY
    }

    @SuppressLint("MissingPermission")
    @RequiresApi(29)
    private fun startCapture(mp: MediaProjection) {
        val config = AudioPlaybackCaptureConfiguration.Builder(mp)
            .addMatchingUsage(AudioAttributes.USAGE_MEDIA)
            .addMatchingUsage(AudioAttributes.USAGE_GAME)
            .addMatchingUsage(AudioAttributes.USAGE_UNKNOWN)
            .build()
        val format = AudioFormat.Builder()
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setSampleRate(SAMPLE_RATE)
            .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
            .build()
        val minBuffer = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val audio = AudioRecord.Builder()
            .setAudioFormat(format)
            .setBufferSizeInBytes(maxOf(minBuffer, SAMPLE_RATE * 2))
            .setAudioPlaybackCaptureConfig(config)
            .build()
        check(audio.state == AudioRecord.STATE_INITIALIZED) { "звук недоступен" }
        record = audio
        audio.startRecording()
        listening = true
        val rec = recognizer ?: return
        worker = Thread {
            val buffer = ShortArray(4000)
            var lastPartial = ""
            while (listening) {
                val n = audio.read(buffer, 0, buffer.size)
                if (n <= 0) continue
                val done = try {
                    rec.acceptWaveForm(buffer, n)
                } catch (e: Exception) {
                    false
                }
                if (done) {
                    val text = Voice.textOf(rec.result)
                    lastPartial = ""
                    if (text.isNotBlank()) main.post { onSentence(text) }
                } else {
                    val partial = Voice.textOf(rec.partialResult)
                    if (partial != lastPartial) {
                        lastPartial = partial
                        main.post { setOriginal(partial) }
                    }
                }
            }
        }.apply {
            name = "valhalla-captions"
            start()
        }
    }

    private fun onSentence(text: String) {
        setOriginal(text)
        scope.launch {
            val translated = try {
                TranslationEngine.translate(source, target, text, allowOnline = false)
            } catch (e: Exception) {
                "[$text]"
            }
            lines.addLast(translated)
            while (lines.size > 2) lines.removeFirst()
            translatedView?.text = lines.joinToString("\n")
        }
    }

    private fun setOriginal(text: String) {
        originalView?.text = text
    }

    // ---- Панель субтитров ----

    private fun dp(v: Float) = (v * resources.displayMetrics.density).toInt()

    @SuppressLint("ClickableViewAccessibility")
    private fun showPanel() {
        val gold = 0xFFD4AF5A.toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14f), dp(8f), dp(14f), dp(10f))
            background = GradientDrawable().apply {
                cornerRadius = dp(12f).toFloat()
                setColor(0xE6101218.toInt())
                setStroke(dp(1f), 0xFF5A4A22.toInt())
            }
        }
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val original = TextView(this).apply {
            setTextColor(0xFF8D90A0.toInt())
            textSize = 13f
            maxLines = 2
        }
        val close = TextView(this).apply {
            text = "✕"
            setTextColor(gold)
            textSize = 18f
            setPadding(dp(12f), 0, 0, 0)
            setOnClickListener { stopSelf() }
        }
        header.addView(original, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        header.addView(close)
        val translated = TextView(this).apply {
            setTextColor(0xFFF2EBD6.toInt())
            textSize = 19f
            typeface = Typeface.SERIF
            setPadding(0, dp(4f), 0, 0)
            maxLines = 4
        }
        root.addView(header)
        root.addView(translated)
        originalView = original
        translatedView = translated

        val type = if (Build.VERSION.SDK_INT >= 26) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            type,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM
            y = dp(90f)
            horizontalMargin = 0.03f
        }
        // Панель можно двигать вверх-вниз пальцем.
        var startY = 0f
        var startParamY = 0
        root.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    startY = event.rawY
                    startParamY = params.y
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.y = (startParamY - (event.rawY - startY)).toInt().coerceAtLeast(0)
                    runCatching { windowManager.updateViewLayout(root, params) }
                    true
                }
                else -> false
            }
        }
        try {
            windowManager.addView(root, params)
            panel = root
        } catch (e: Exception) {
            stopSelf()
        }
    }

    private fun startAsForeground() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(NotificationChannel(CHANNEL, "Живые субтитры", NotificationManager.IMPORTANCE_LOW))
        }
        val stop = PendingIntent.getService(
            this,
            2,
            Intent(this, LiveCaptionService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_rune)
            .setContentTitle("Живые субтитры включены")
            .setContentText("Перевод звука из видео и подкастов")
            .setOngoing(true)
            .addAction(0, "Выключить", stop)
            .build()
        val type = when {
            Build.VERSION.SDK_INT >= 30 ->
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            Build.VERSION.SDK_INT >= 29 -> ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            else -> 0
        }
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, type)
    }

    override fun onDestroy() {
        running = false
        listening = false
        scope.cancel()
        worker?.join(500)
        record?.let {
            runCatching { it.stop() }
            it.release()
        }
        record = null
        recognizer?.close()
        recognizer = null
        panel?.let { runCatching { windowManager.removeView(it) } }
        panel = null
        projection?.stop()
        projection = null
        super.onDestroy()
    }

    companion object {
        const val EXTRA_CODE = "code"
        const val EXTRA_DATA = "data"
        const val EXTRA_SOURCE = "source"
        const val ACTION_STOP = "com.example.offlinetranslator.STOP_CAPTIONS"
        private const val CHANNEL = "live_captions"
        private const val NOTIFICATION_ID = 31
        private const val SAMPLE_RATE = 16000

        @Volatile
        var running = false
            private set
    }
}
