package com.example.offlinetranslator

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import java.io.File

/** Камера: наводим на текст, снимаем, и снимок переводится на главном экране. */
@Composable
fun CameraScreen(
    vm: TranslatorViewModel,
    settings: AppSettings,
    onBack: () -> Unit,
    onCaptured: (Uri) -> Unit
) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
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
    val imageCapture = remember {
        ImageCapture.Builder()
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .build()
    }
    val previewView = remember {
        PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER }
    }

    DisposableEffect(hasPermission, lifecycleOwner) {
        if (!hasPermission) return@DisposableEffect onDispose { }
        val future = ProcessCameraProvider.getInstance(context)
        var provider: ProcessCameraProvider? = null
        future.addListener({
            try {
                val cameraProvider = future.get()
                provider = cameraProvider
                val preview = Preview.Builder().build()
                preview.setSurfaceProvider(previewView.surfaceProvider)
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageCapture
                )
            } catch (e: Exception) {
                error = "Не удалось открыть камеру: ${e.localizedMessage ?: "ошибка"}"
            }
        }, ContextCompat.getMainExecutor(context))
        onDispose { provider?.unbindAll() }
    }

    fun capture() {
        if (capturing) return
        capturing = true
        error = ""
        context.cacheDir.listFiles()
            ?.filter { it.name.startsWith("camera_") }
            ?.forEach { it.delete() }
        val file = File(context.cacheDir, "camera_${System.currentTimeMillis()}.jpg")
        imageCapture.takePicture(
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

    val script = TranslationEngine.resolveScript(settings.ocrScript, vm.source)

    Box(
        Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        if (hasPermission) {
            AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())
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
                        "Если окно не появляется, включите доступ в настройках Android: Приложения → Valhalla Translate → Разрешения.",
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
                .background(Color.Black.copy(alpha = 0.45f))
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            ScreenHeader("Камера", onBack)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "${Languages.name(vm.source)} → ${Languages.name(vm.target)}",
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
            }
        }
    }
}
