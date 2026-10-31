package com.example.offlinetranslator

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.addPathNodes
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight

/** Простые контурные иконки (пути Material Icons, Apache 2.0), окрашиваются в золото. */
object ValhallaIcons {
    private fun icon(name: String, vararg paths: String): ImageVector {
        val builder = ImageVector.Builder(
            name = name,
            defaultWidth = 24.dp,
            defaultHeight = 24.dp,
            viewportWidth = 24f,
            viewportHeight = 24f
        )
        paths.forEach { builder.addPath(pathData = addPathNodes(it), fill = SolidColor(Color.Black)) }
        return builder.build()
    }

    val Mic: ImageVector by lazy {
        icon(
            "Mic",
            "M12,14c1.66,0 2.99,-1.34 2.99,-3L15,5c0,-1.66 -1.34,-3 -3,-3S9,3.34 9,5v6c0,1.66 1.34,3 3,3z" +
                "M17.3,11c0,3 -2.54,5.1 -5.3,5.1S6.7,14 6.7,11L5,11c0,3.41 2.72,6.23 6,6.72L11,21h2v-3.28" +
                "c3.28,-0.48 6,-3.3 6,-6.72h-1.7z"
        )
    }

    val Speaker: ImageVector by lazy {
        icon(
            "Speaker",
            "M3,9v6h4l5,5V4L7,9H3z" +
                "M16.5,12c0,-1.77 -1.02,-3.29 -2.5,-4.03v8.05c1.48,-0.73 2.5,-2.25 2.5,-4.02z" +
                "M14,3.23v2.06c2.89,0.86 5,3.54 5,6.71s-2.11,5.85 -5,6.71v2.06c4.01,-0.91 7,-4.49 7,-8.77" +
                "s-2.99,-7.86 -7,-8.77z"
        )
    }

    val Camera: ImageVector by lazy {
        icon(
            "Camera",
            "M12,12m-3.2,0a3.2,3.2 0,1 1,6.4 0a3.2,3.2 0,1 1,-6.4 0",
            "M9,2L7.17,4H4c-1.1,0 -2,0.9 -2,2v12c0,1.1 0.9,2 2,2h16c1.1,0 2,-0.9 2,-2V6c0,-1.1 -0.9,-2 -2,-2" +
                "h-3.17L15,2H9zM12,17c-2.76,0 -5,-2.24 -5,-5s2.24,-5 5,-5 5,2.24 5,5 -2.24,5 -5,5z"
        )
    }

    val Image: ImageVector by lazy {
        icon(
            "Image",
            "M21,19V5c0,-1.1 -0.9,-2 -2,-2H5c-1.1,0 -2,0.9 -2,2v14c0,1.1 0.9,2 2,2h14c1.1,0 2,-0.9 2,-2z" +
                "M8.5,13.5l2.5,3.01L14.5,12l4.5,6H5l3.5,-4.5z"
        )
    }
}

/** Контурная кнопка с иконкой и короткой подписью. */
@Composable
fun IconLabelButton(
    icon: ImageVector,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    onClick: () -> Unit
) {
    val p = LocalPalette.current
    val tap = rememberTap()
    val color = if (enabled) p.gold else p.muted
    Box(
        modifier
            .height(46.dp)
            .clip(ButtonShape)
            .border(1.dp, if (enabled) p.goldDim else p.cardBorder, ButtonShape)
            .clickable(enabled = enabled) {
                tap()
                onClick()
            }
            .padding(horizontal = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(6.dp))
            Text(label, color = color, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
        }
    }
}

/** Маленькая иконка-кнопка без рамки. */
@Composable
fun IconTap(icon: ImageVector, description: String, color: Color, onClick: () -> Unit) {
    val tap = rememberTap()
    Box(
        Modifier
            .clip(ButtonShape)
            .clickable {
                tap()
                onClick()
            }
            .padding(8.dp)
    ) {
        Icon(icon, contentDescription = description, tint = color, modifier = Modifier.size(22.dp))
    }
}
