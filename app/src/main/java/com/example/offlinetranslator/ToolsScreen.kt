package com.example.offlinetranslator

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class Tool(val title: String, val subtitle: String, val open: () -> Unit)

/** Экран «☰ Инструменты»: всё, что не помещается на главный экран. */
@Composable
fun ToolsScreen(tools: List<Tool>, onBack: () -> Unit) {
    val p = LocalPalette.current
    val tap = rememberTap()
    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Инструменты", onBack)
        GoldDivider()
        tools.forEach { tool ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .valhallaCard(p)
                    .clickable {
                        tap()
                        tool.open()
                    }
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(tool.title, color = p.gold, fontFamily = FontFamily.Serif, fontSize = 19.sp)
                    Text(tool.subtitle, color = p.muted, fontSize = 13.sp, lineHeight = 18.sp)
                }
                Text("›", color = p.gold, fontSize = 26.sp)
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}
