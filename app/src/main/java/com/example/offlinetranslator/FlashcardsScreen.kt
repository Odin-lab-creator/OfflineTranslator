package com.example.offlinetranslator

import android.content.Context
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject

/**
 * Интервальное повторение для карточек из избранного (система Лейтнера):
 * чем лучше вы помните слово, тем реже оно попадается.
 */
class StudyStore private constructor(context: Context) {
    private val prefs = context.getSharedPreferences("study", Context.MODE_PRIVATE)
    private val boxes = mutableMapOf<Long, Pair<Int, Long>>()

    init {
        try {
            val json = JSONObject(prefs.getString("cards", "{}") ?: "{}")
            json.keys().forEach { key ->
                val o = json.getJSONObject(key)
                boxes[key.toLong()] = o.getInt("b") to o.getLong("d")
            }
        } catch (e: Exception) {
            boxes.clear()
        }
    }

    fun due(id: Long): Long = boxes[id]?.second ?: 0L
    fun box(id: Long): Int = boxes[id]?.first ?: 0

    fun answer(id: Long, remembered: Boolean) {
        val box = if (remembered) (box(id) + 1).coerceAtMost(INTERVAL_DAYS.lastIndex) else 0
        val delay = if (remembered) INTERVAL_DAYS[box] * DAY else 60_000L
        boxes[id] = box to (System.currentTimeMillis() + delay)
        save()
    }

    private fun save() {
        val json = JSONObject()
        boxes.forEach { (id, value) ->
            json.put(id.toString(), JSONObject().put("b", value.first).put("d", value.second))
        }
        prefs.edit().putString("cards", json.toString()).apply()
    }

    companion object {
        private val INTERVAL_DAYS = listOf(0L, 1L, 3L, 7L, 14L, 30L)
        private const val DAY = 24 * 60 * 60 * 1000L

        @Volatile
        private var instance: StudyStore? = null

        fun get(context: Context): StudyStore =
            instance ?: synchronized(this) {
                instance ?: StudyStore(context.applicationContext).also { instance = it }
            }
    }
}

@Composable
fun FlashcardsScreen(vm: TranslatorViewModel, onBack: () -> Unit) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val study = remember { StudyStore.get(context) }
    var reversed by rememberSaveable { mutableStateOf(false) }
    var revealed by remember { mutableStateOf(false) }
    var practiceAll by remember { mutableStateOf(false) }
    var round by remember { mutableIntStateOf(0) }
    var doneToday by remember { mutableIntStateOf(0) }
    val seen = remember { mutableStateListOf<Long>() }

    val favorites = vm.history.entries.filter { it.favorite }
    val now = remember(round) { System.currentTimeMillis() }
    val queue = favorites
        .filter { it.id !in seen && (practiceAll || study.due(it.id) <= now) }
        .sortedBy { study.due(it.id) }
    val card = queue.firstOrNull()

    Column(
        Modifier
            .fillMaxSize()
            .background(p.bg)
            .systemBarsPadding()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        ScreenHeader("Карточки", onBack)
        GoldDivider()
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TabChip("Оригинал → перевод", !reversed) {
                reversed = false
                revealed = false
            }
            TabChip("Перевод → оригинал", reversed) {
                reversed = true
                revealed = false
            }
        }

        when {
            favorites.isEmpty() -> Text(
                "Карточки делаются из избранного. Отмечайте ☆ полезные переводы — и они появятся здесь.",
                color = p.muted,
                fontSize = 15.sp,
                lineHeight = 22.sp
            )
            card == null -> {
                Text(
                    "На сегодня всё повторено" + if (doneToday > 0) " — карточек: $doneToday." else ".",
                    color = p.gold,
                    fontFamily = FontFamily.Serif,
                    fontSize = 20.sp
                )
                val next = favorites.minOfOrNull { study.due(it.id) } ?: 0L
                val hours = ((next - System.currentTimeMillis()) / 3_600_000L).coerceAtLeast(0)
                Text(
                    if (hours < 24) "Следующие карточки примерно через $hours ч." else "Следующие карточки через ${hours / 24} дн.",
                    color = p.muted,
                    fontSize = 14.sp
                )
                OutlineGoldButton("Повторить всё ещё раз", modifier = Modifier.fillMaxWidth()) {
                    seen.clear()
                    practiceAll = true
                    round++
                }
            }
            else -> {
                Text(
                    "Осталось: ${queue.size} · уровень ${study.box(card.id)} из 5",
                    color = p.muted,
                    fontSize = 13.sp
                )
                val front = if (reversed) card.result else card.text
                val back = if (reversed) card.text else card.result
                val frontLang = if (reversed) card.target else card.source
                val backLang = if (reversed) card.source else card.target
                Box(
                    Modifier
                        .fillMaxWidth()
                        .heightIn(min = 260.dp)
                        .valhallaCard(p, border = if (revealed) p.gold else p.goldDim)
                        .clickable { revealed = true }
                        .padding(20.dp),
                    contentAlignment = Alignment.Center
                ) {
                    AnimatedContent(
                        targetState = revealed,
                        transitionSpec = { fadeIn() togetherWith fadeOut() },
                        label = "card"
                    ) { open ->
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(Languages.name(frontLang).uppercase(), color = p.muted, fontSize = 11.sp, letterSpacing = 2.sp)
                            Text(
                                front,
                                color = p.text,
                                fontSize = 22.sp,
                                lineHeight = 29.sp,
                                textAlign = TextAlign.Center,
                                modifier = Modifier.padding(top = 6.dp)
                            )
                            if (open) {
                                Text(
                                    Languages.name(backLang).uppercase(),
                                    color = p.muted,
                                    fontSize = 11.sp,
                                    letterSpacing = 2.sp,
                                    modifier = Modifier.padding(top = 20.dp)
                                )
                                Text(
                                    back,
                                    color = p.result,
                                    fontFamily = FontFamily.Serif,
                                    fontSize = 24.sp,
                                    lineHeight = 31.sp,
                                    textAlign = TextAlign.Center,
                                    modifier = Modifier.padding(top = 6.dp)
                                )
                            } else {
                                Text(
                                    "Вспомните перевод и нажмите на карточку",
                                    color = p.muted,
                                    fontSize = 13.sp,
                                    modifier = Modifier.padding(top = 20.dp)
                                )
                            }
                        }
                    }
                }
                if (revealed) {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        IconTap(ValhallaIcons.Speaker, "Озвучить", p.gold) { vm.speak(back, backLang) }
                        OutlineGoldButton("Не помню", modifier = Modifier.weight(1f)) {
                            study.answer(card.id, remembered = false)
                            if (practiceAll) seen.add(card.id)
                            revealed = false
                            round++
                        }
                        GoldButton("Помню", modifier = Modifier.weight(1f)) {
                            study.answer(card.id, remembered = true)
                            if (practiceAll) seen.add(card.id)
                            revealed = false
                            doneToday++
                            round++
                        }
                    }
                } else {
                    GoldButton("Показать перевод", modifier = Modifier.fillMaxWidth()) { revealed = true }
                }
            }
        }
    }
}
