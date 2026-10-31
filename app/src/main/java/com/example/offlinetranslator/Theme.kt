package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class Palette(
    val bg: Color,
    val card: Color,
    val cardBorder: Color,
    val gold: Color,
    val goldDim: Color,
    val text: Color,
    val muted: Color,
    val result: Color,
    val onGold: Color
)

val DarkPalette = Palette(
    bg = Color(0xFF12141A),
    card = Color(0xFF1B1E27),
    cardBorder = Color(0xFF2E3340),
    gold = Color(0xFFD4AF5A),
    goldDim = Color(0xFF5A4A22),
    text = Color(0xFFE8E4D8),
    muted = Color(0xFF8D90A0),
    result = Color(0xFFF2EBD3),
    onGold = Color(0xFF12141A)
)

val LightPalette = Palette(
    bg = Color(0xFFF6F1E4),
    card = Color(0xFFFFFFFF),
    cardBorder = Color(0xFFD9D0B8),
    gold = Color(0xFF9A7B2F),
    goldDim = Color(0xFFC9B77F),
    text = Color(0xFF2A2A2A),
    muted = Color(0xFF6F6A5A),
    result = Color(0xFF2A2418),
    onGold = Color(0xFFFFFFFF)
)

val LocalPalette = staticCompositionLocalOf { DarkPalette }

val CardShape: Shape = RoundedCornerShape(8.dp)
val ButtonShape: Shape = RoundedCornerShape(6.dp)

@Composable
fun isDarkTheme(settings: AppSettings): Boolean = when (settings.themeMode) {
    ThemeMode.SYSTEM -> isSystemInDarkTheme()
    ThemeMode.LIGHT -> false
    ThemeMode.DARK -> true
}

@Composable
fun ValhallaTheme(dark: Boolean, content: @Composable () -> Unit) {
    val p = if (dark) DarkPalette else LightPalette
    val scheme = if (dark) {
        darkColorScheme(
            primary = p.gold, onPrimary = p.onGold,
            background = p.bg, onBackground = p.text,
            surface = p.bg, onSurface = p.text, onSurfaceVariant = p.muted,
            surfaceContainer = p.card, surfaceContainerHigh = p.card,
            surfaceContainerHighest = p.card, surfaceContainerLow = p.card,
            outline = p.goldDim
        )
    } else {
        lightColorScheme(
            primary = p.gold, onPrimary = p.onGold,
            background = p.bg, onBackground = p.text,
            surface = p.bg, onSurface = p.text, onSurfaceVariant = p.muted,
            surfaceContainer = p.card, surfaceContainerHigh = p.card,
            surfaceContainerHighest = p.card, surfaceContainerLow = p.card,
            outline = p.goldDim
        )
    }
    CompositionLocalProvider(LocalPalette provides p) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}

/** Карточка в стиле «Вальхалла»: фон карточки и тонкая рамка. */
fun Modifier.valhallaCard(p: Palette, border: Color = p.cardBorder): Modifier =
    this.clip(CardShape).background(p.card).border(1.dp, border, CardShape)

/** Лёгкая вибрация при нажатиях, если она включена в настройках. */
@Composable
fun rememberTap(): () -> Unit {
    val haptic = LocalHapticFeedback.current
    val settings = AppSettings.current()
    return {
        if (settings.haptics) haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
    }
}

@Composable
fun LinkText(
    label: String,
    color: Color,
    size: TextUnit = 13.sp,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val tap = rememberTap()
    Text(
        label,
        color = color,
        fontSize = size,
        modifier = modifier
            .clip(RoundedCornerShape(4.dp))
            .clickable {
                tap()
                onClick()
            }
            .padding(horizontal = 6.dp, vertical = 8.dp)
    )
}

@Composable
fun GoldButton(
    text: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    onClick: () -> Unit
) {
    val p = LocalPalette.current
    val tap = rememberTap()
    Box(
        modifier
            .height(52.dp)
            .clip(ButtonShape)
            .background(if (enabled) p.gold else p.goldDim)
            .clickable(enabled = enabled) {
                tap()
                onClick()
            }
            .padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(text, color = p.onGold, fontSize = 16.sp, fontWeight = FontWeight.Medium, maxLines = 1)
    }
}

@Composable
fun OutlineGoldButton(
    text: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    height: Int = 52,
    onClick: () -> Unit
) {
    val p = LocalPalette.current
    val tap = rememberTap()
    Box(
        modifier
            .height(height.dp)
            .clip(ButtonShape)
            .border(1.dp, if (enabled) p.gold else p.goldDim, ButtonShape)
            .clickable(enabled = enabled) {
                tap()
                onClick()
            }
            .padding(horizontal = 14.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text,
            color = if (enabled) p.gold else p.muted,
            fontSize = 15.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 1
        )
    }
}

@Composable
fun GoldDivider() {
    val p = LocalPalette.current
    Box(
        Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(p.goldDim)
    )
}

@Composable
fun SectionLabel(text: String) {
    val p = LocalPalette.current
    Text(text.uppercase(), color = p.muted, fontSize = 12.sp, letterSpacing = 2.sp)
}

/** Заголовок вложенного экрана: «← Назад» и название. */
@Composable
fun ScreenHeader(title: String, onBack: () -> Unit, actions: @Composable () -> Unit = {}) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LinkText("←", p.gold, 22.sp, onClick = onBack)
            Spacer(Modifier.width(4.dp))
            Text(title, color = p.gold, fontFamily = FontFamily.Serif, fontSize = 22.sp)
        }
        actions()
    }
}
