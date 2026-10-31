package com.example.offlinetranslator

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Окно, которое открывается из меню выделенного текста в любом приложении
 * («Valhalla Translate»). Показывает перевод поверх приложения.
 */
class ProcessTextActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val text = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString()?.trim().orEmpty()
        val readOnly = intent.getBooleanExtra(Intent.EXTRA_PROCESS_TEXT_READONLY, true)
        if (text.isEmpty()) {
            finish()
            return
        }
        val settings = AppSettings.get(applicationContext)

        setContent {
            ValhallaTheme(isDarkTheme(settings)) {
                val p = LocalPalette.current
                val clipboard = LocalClipboardManager.current
                var source by remember { mutableStateOf(settings.lastSource) }
                var target by remember { mutableStateOf(settings.lastTarget) }
                var result by remember { mutableStateOf("") }
                var status by remember { mutableStateOf("") }
                var busy by remember { mutableStateOf(true) }
                var detected by remember { mutableStateOf(false) }
                var copied by remember { mutableStateOf(false) }

                LaunchedEffect(source, target) {
                    busy = true
                    copied = false
                    try {
                        if (!detected) {
                            detected = true
                            val code = try {
                                TranslationEngine.detect(text)
                            } catch (e: Exception) {
                                null
                            }
                            if (code != null && code != source) {
                                source = code
                                target = Languages.otherTarget(code, target)
                                return@LaunchedEffect
                            }
                        }
                        status = "Перевожу…"
                        result = TranslationEngine.translate(source, target, text, settings.wifiOnly)
                        status = ""
                        settings.lastTarget = target
                        HistoryStore.get(applicationContext).add(source, target, text, result)
                    } catch (e: Exception) {
                        status = "Не удалось перевести: ${e.localizedMessage ?: "ошибка"}. " +
                            "Если модель ещё не скачана, нужен интернет."
                    } finally {
                        busy = false
                    }
                }

                Box(
                    Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.5f))
                        .clickable(
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null
                        ) { finish() },
                    contentAlignment = Alignment.BottomCenter
                ) {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .navigationBarsPadding()
                            .padding(12.dp)
                            .valhallaCard(p, border = p.gold)
                            .clickable(
                                interactionSource = remember { MutableInteractionSource() },
                                indication = null
                            ) { }
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("VALHALLA", color = p.gold, fontFamily = FontFamily.Serif, fontSize = 16.sp, letterSpacing = 3.sp)
                            LinkText("Закрыть", p.muted) { finish() }
                        }
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            LanguageButton(source, "С какого языка", emptySet(), Modifier.weight(1f)) {
                                source = it
                            }
                            Text("→", color = p.gold, fontSize = 20.sp, modifier = Modifier.padding(horizontal = 10.dp))
                            LanguageButton(target, "На какой язык", emptySet(), Modifier.weight(1f)) {
                                target = it
                            }
                        }
                        Text(
                            text,
                            color = p.muted,
                            fontSize = 14.sp,
                            maxLines = 3,
                            overflow = TextOverflow.Ellipsis
                        )
                        if (busy) {
                            LinearProgressIndicator(Modifier.fillMaxWidth(), color = p.gold, trackColor = p.card)
                        }
                        if (status.isNotEmpty()) Text(status, color = p.muted, fontSize = 12.sp)
                        if (result.isNotEmpty()) {
                            SelectionContainer {
                                Text(
                                    result,
                                    color = p.result,
                                    fontFamily = FontFamily.Serif,
                                    fontSize = 22.sp,
                                    lineHeight = 30.sp,
                                    modifier = Modifier
                                        .heightIn(max = 320.dp)
                                        .verticalScroll(rememberScrollState())
                                )
                            }
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                LinkText(if (copied) "Скопировано ✓" else "Копировать", p.gold, 14.sp) {
                                    clipboard.setText(AnnotatedString(result))
                                    copied = true
                                }
                                if (!readOnly) {
                                    LinkText("Заменить", p.gold, 14.sp) {
                                        setResult(
                                            Activity.RESULT_OK,
                                            Intent().putExtra(Intent.EXTRA_PROCESS_TEXT, result)
                                        )
                                        finish()
                                    }
                                }
                                LinkText("В приложении", p.gold, 14.sp) {
                                    startActivity(
                                        Intent(this@ProcessTextActivity, MainActivity::class.java)
                                            .setAction(Intent.ACTION_SEND)
                                            .setType("text/plain")
                                            .putExtra(Intent.EXTRA_TEXT, text)
                                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                                    )
                                    finish()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
