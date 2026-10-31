package com.example.offlinetranslator

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Перевод крупно на весь экран, чтобы показать собеседнику. Экран не гаснет. */
@Composable
fun ShowScreen(text: String, language: String, onBack: () -> Unit, onSpeak: () -> Unit) {
    val p = LocalPalette.current
    val view = LocalView.current
    var flipped by rememberSaveable { mutableStateOf(false) }
    val angle by animateFloatAsState(if (flipped) 180f else 0f, label = "flip")

    DisposableEffect(Unit) {
        view.keepScreenOn = true
        onDispose { view.keepScreenOn = false }
    }

    val size = when {
        text.length < 20 -> 60
        text.length < 60 -> 46
        text.length < 150 -> 36
        text.length < 400 -> 28
        else -> 22
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(16.dp)
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            LinkText("← Назад", p.gold, 16.sp, onClick = onBack)
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconTap(ValhallaIcons.Speaker, "Озвучить", p.gold, onSpeak)
                LinkText("⟲ Перевернуть", p.gold, 16.sp) { flipped = !flipped }
            }
        }
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .rotate(angle),
            contentAlignment = Alignment.Center
        ) {
            Column(
                Modifier.verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    Languages.name(language).uppercase(),
                    color = p.muted,
                    fontSize = 12.sp,
                    letterSpacing = 3.sp
                )
                Text(
                    text,
                    color = p.result,
                    fontFamily = FontFamily.Serif,
                    fontSize = size.sp,
                    lineHeight = (size * 1.25f).sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 12.dp)
                )
            }
        }
    }
}
