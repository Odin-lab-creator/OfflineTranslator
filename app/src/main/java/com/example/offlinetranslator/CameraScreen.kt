package com.example.offlinetranslator

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Rect
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.mlkit.vision.MlKitAnalyzer
import androidx.camera.view.CameraController
import androidx.camera.view.LifecycleCameraController
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import java.io.File
import kotlinx.coroutines.launch

private class LiveBlock(val text: String, val box: Rect, val lines: Int)

/**
 * Камера: снимок с переводом на главном экране или живой режим,
 * в котором перевод появляется прямо поверх текста в видоискателе.
 */
@Composable
fun CameraScreen(
    vm: TranslatorViewModel,
    settings: AppSettings,
    onBack: () -> Unit,
    onCaptured: (Uri) -> Unit
) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val density = LocalDensity.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    val tap = rememberTap()

    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    var asked by remember { mutableStateOf(false) }
    val requestPermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasPermission = granted
        asked = true
    }
    LaunchedEffect(Unit) {
        if (!hasPermission) requestPermission.launch(Manifest.permission.CAMERA)
    }

    var capturing by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    var scriptMenu by remember { mutableStateOf(false) }
    var live by rememberSaveable { mutableStateOf(false) }
    var prices by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        Converter.init(context)
        try {
            Converter.refreshRates()
        } catch (e: Exception) {
            // без интернета — сохранённые курсы
        }
    }
    var blocks by remember { mutableStateOf<List<LiveBlock>>(emptyList()) }
    var liveSource by remember { mutableStateOf(vm.source) }
    var liveStatus by remember { mutableStateOf("") }
    val translations = remember { mutableStateMapOf<String, String>() }
    val inFlight = remember { mutableSetOf<String>() }

    val controller = remember {
        LifecycleCameraController(context).apply {
            cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            setEnabledUseCases(CameraController.IMAGE_CAPTURE or CameraController.IMAGE_ANALYSIS)
            imageCaptureMode = ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY
        }
    }
    val previewView = remember {
        PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER }
    }

    DisposableEffect(hasPermission, lifecycleOwner) {
        if (!hasPermission) return@DisposableEffect onDispose { }
        try {
            controller.bindToLifecycle(lifecycleOwner)
            previewView.controller = controller
        } catch (e: Exception) {
            error = "Не удалось открыть камеру: ${e.localizedMessage ?: "ошибка"}"
        }
        onDispose { controller.unbind() }
    }

    val baseScript = TranslationEngine.resolveScript(settings.ocrScript, vm.source)
    // Для цен и единиц хватает латиницы и цифр — работает и для кириллических вывесок.
    val script = if (prices && baseScript == OcrScript.CYRILLIC) OcrScript.LATIN else baseScript

    // Живой режим: распознаём кадры и переводим каждый блок текста.
    DisposableEffect(live, prices, script, hasPermission) {
        if (!live || !hasPermission || script == OcrScript.CYRILLIC) {
            controller.clearImageAnalysisAnalyzer()
            blocks = emptyList()
            liveStatus = if (live && script == OcrScript.CYRILLIC) {
                "Живой режим не поддерживает кириллицу — используйте снимок"
            } else ""
            return@DisposableEffect onDispose { }
        }
        val recognizer = TranslationEngine.mlKitRecognizer(script)
        val executor = ContextCompat.getMainExecutor(context)
        val separator = TranslationEngine.lineSeparator(script)
        var lastUpdate = 0L
        var lastDetect = 0L
        controller.setImageAnalysisAnalyzer(
            executor,
            MlKitAnalyzer(
                listOf(recognizer),
                CameraController.COORDINATE_SYSTEM_VIEW_REFERENCED,
                executor
            ) { result ->
                val now = System.currentTimeMillis()
                if (now - lastUpdate < 400) return@MlKitAnalyzer
                lastUpdate = now
                val text = result.getValue(recognizer) ?: return@MlKitAnalyzer
                blocks = text.textBlocks.mapNotNull { block ->
                    val box = block.boundingBox ?: return@mapNotNull null
                    val joined = block.lines.joinToString(separator) { it.text }.trim()
                    if (joined.length < 2) null else LiveBlock(joined, box, block.lines.size.coerceAtLeast(1))
                }
                val all = blocks.joinToString(" ") { it.text }
                if (all.length > 12 && now - lastDetect > 2500) {
                    lastDetect = now
                    scope.launch {
                        val code = try {
                            TranslationEngine.detect(all)
                        } catch (e: Exception) {
                            null
                        }
                        if (code != null && code != vm.target) liveSource = code
                    }
                }
                if (prices) return@MlKitAnalyzer
                blocks.forEach { block ->
                    val key = "$liveSource>${vm.target}|${block.text}"
                    if (translations[key] == null && inFlight.add(key)) {
                        scope.launch {
                            try {
                                if (liveSource !in vm.downloaded || vm.target !in vm.downloaded) {
                                    liveStatus = "Скачиваю языковую модель…"
                                }
                                translations[key] = TranslationEngine.translate(
                                    liveSource, vm.target, block.text, settings.wifiOnly, allowOnline = false
                                )
                                liveStatus = ""
                            } catch (e: Exception) {
                                liveStatus = "Нужна модель «${Languages.name(liveSource)}» — для загрузки нужен интернет"
                            } finally {
                                inFlight.remove(key)
                            }
                        }
                    }
                }
            }
        )
        onDispose {
            controller.clearImageAnalysisAnalyzer()
            recognizer.close()
        }
    }

    fun capture() {
        if (capturing) return
        capturing = true
        error = ""
        context.cacheDir.listFiles()
            ?.filter { it.name.startsWith("camera_") }
            ?.forEach { it.delete() }
        val file = File(context.cacheDir, "camera_${System.currentTimeMillis()}.jpg")
        controller.takePicture(
            ImageCapture.OutputFileOptions.Builder(file).build(),
            ContextCompat.getMainExecutor(context),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    capturing = false
                    onCaptured(Uri.fromFile(file))
                }

                override fun onError(exception: ImageCaptureException) {
                    capturing = false
                    error = "Не удалось сделать снимок: ${exception.localizedMessage ?: "ошибка"}"
                }
            }
        )
    }

    Box(
        Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        if (hasPermission) {
            AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

            // Цены и единицы поверх текста
            if (prices) {
                blocks.forEach { block ->
                    val found = Converter.convertAll(block.text, settings.homeCurrency, liveSource)
                    if (found.isEmpty()) return@forEach
                    Text(
                        found.joinToString("\n") { "${it.original}  ${it.converted}" },
                        color = p.gold,
                        fontSize = 15.sp,
                        lineHeight = 19.sp,
                        modifier = Modifier
                            .offset { IntOffset(block.box.left, block.box.bottom) }
                            .clip(RoundedCornerShape(4.dp))
                            .background(Color(0xEE121418))
                            .border(1.dp, p.gold, RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 3.dp)
                    )
                }
            }

            // Переводы поверх текста
            if (!prices) blocks.forEach { block ->
                val translated = translations["$liveSource>${vm.target}|${block.text}"] ?: return@forEach
                val lineHeightPx = block.box.height().toFloat() / block.lines
                val fontSp = with(density) { (lineHeightPx * 0.62f).toSp() }.value.coerceIn(10f, 26f)
                Text(
                    translated,
                    color = p.result,
                    fontSize = fontSp.sp,
                    lineHeight = (fontSp * 1.2f).sp,
                    modifier = Modifier
                        .offset { IntOffset(block.box.left, block.box.top) }
                        .widthIn(
                            min = with(density) { block.box.width().toDp() },
                            max = with(density) { (block.box.width() * 1.6f).toDp() }
                        )
                        .clip(RoundedCornerShape(4.dp))
                        .background(Color(0xE6121418))
                        .border(1.dp, p.goldDim, RoundedCornerShape(4.dp))
                        .padding(horizontal = 4.dp, vertical = 2.dp)
                )
            }
        } else {
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(32.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "Чтобы переводить через камеру, разрешите доступ к ней.",
                    color = p.text,
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(16.dp))
                OutlineGoldButton(if (asked) "Разрешить ещё раз" else "Разрешить") {
                    requestPermission.launch(Manifest.permission.CAMERA)
                }
                if (asked) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Если окно не появляется, включите доступ в настройках Android: " +
                            "Приложения → Valhalla Translate → Разрешения.",
                        color = p.muted,
                        fontSize = 12.sp,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        Column(
            Modifier
                .fillMaxWidth()
                .systemBarsPadding()
                .background(Color.Black.copy(alpha = 0.5f))
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            ScreenHeader("Камера", onBack)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "${Languages.name(if (live) liveSource else vm.source)} → ${Languages.name(vm.target)}",
                    color = Color.White,
                    fontSize = 13.sp
                )
                Spacer(Modifier.weight(1f))
                Box {
                    LinkText("Алфавит: ${script.label.lowercase()} ▾", p.gold, 13.sp) { scriptMenu = true }
                    DropdownMenu(expanded = scriptMenu, onDismissRequest = { scriptMenu = false }) {
                        OcrScript.entries.forEach { option ->
                            DropdownMenuItem(
                                text = {
                                    Text(
                                        option.label,
                                        color = if (option == settings.ocrScript) p.gold else p.text
                                    )
                                },
                                onClick = {
                                    settings.updateOcrScript(option)
                                    scriptMenu = false
                                }
                            )
                        }
                    }
                }
            }
            if (liveStatus.isNotEmpty()) Text(liveStatus, color = p.gold, fontSize = 12.sp)
        }

        Column(
            Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .systemBarsPadding()
                .padding(bottom = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            if (error.isNotEmpty()) {
                Text(
                    error,
                    color = Color.White,
                    fontSize = 13.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .clip(ButtonShape)
                        .background(Color.Black.copy(alpha = 0.6f))
                        .padding(10.dp)
                )
            }
            if (hasPermission) {
                Row(
                    Modifier
                        .clip(ButtonShape)
                        .background(Color.Black.copy(alpha = 0.55f))
                        .padding(4.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    TabChip("Снимок", !live) {
                        live = false
                        prices = false
                    }
                    TabChip("Живой перевод", live && !prices) {
                        live = true
                        prices = false
                    }
                    TabChip("Цены", prices) {
                        live = true
                        prices = true
                    }
                }
                if (!live) {
                    Text(
                        if (capturing) "Снимаю…" else "Наведите на текст и нажмите",
                        color = Color.White,
                        fontSize = 14.sp,
                        fontFamily = FontFamily.Serif,
                        modifier = Modifier
                            .clip(ButtonShape)
                            .background(Color.Black.copy(alpha = 0.45f))
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                    )
                    Box(
                        Modifier
                            .size(76.dp)
                            .clip(CircleShape)
                            .border(3.dp, p.gold, CircleShape)
                            .clickable(enabled = !capturing) {
                                tap()
                                capture()
                            }
                            .padding(8.dp)
                            .clip(CircleShape)
                            .background(if (capturing) p.goldDim else p.gold)
                    )
                } else {
                    Text(
                        if (prices) {
                            if (Converter.hasRates()) "Цены → ${settings.homeCurrency}, мили → км, °F → °C"
                            else "Единицы → метрические. Для цен нужен интернет один раз — загрузить курсы"
                        } else "Перевод появляется поверх текста",
                        color = Color.White,
                        fontSize = 14.sp,
                        fontFamily = FontFamily.Serif,
                        modifier = Modifier
                            .clip(ButtonShape)
                            .background(Color.Black.copy(alpha = 0.45f))
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                    )
                }
            }
        }
    }
}
