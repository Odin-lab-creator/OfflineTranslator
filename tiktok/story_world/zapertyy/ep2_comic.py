#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 2 «Вода» — кинокомикс на comic_engine.

python3 ep2_comic.py  →  zapertyy_ep2.mp4
Кадры: art/pro270/e2b_*.png (PixelLab Pro 270×300 — ровно видимая часть видео), art/proc/e2_note.png и e2_list.png (рисованы кодом, proc_ep2.py).
"""
import os

import comic_engine as ce
from ep2_lines import LINES, path

HERE = os.path.dirname(os.path.abspath(__file__))

ep = ce.Episode(LINES, path, os.path.join(HERE, "zapertyy_ep2.mp4"))
for i in ("16", "17", "18"):
    ep.voice_fx[i] = "reverb"

# Зацепка: пересохшие губы
ep.shot("e2b_lips", (1.3, 190, 330), (1.45, 185, 345))
ep.wait(0.4)
ep.say("00", 0.3)
ep.fx("gulp", ep.t - 0.2)
ep.title("ЗАПЕРТЫЙ · СЕРИЯ 2", 2.0)
ep.wait(1.6)

# Утро
ep.shot("e2b_bed", (1.2, 200, 300), (1.0, 180, 320), dust=True)
ep.title("ДЕНЬ 2", 3.5, at=ep.t + 0.4)
ep.wait(0.4)
ep.say("01", 0.4)
ep.say("02", 0.5)

# Кухня
ep.shot("e2b_kitchen", (1.15, 200, 260), (1.0, 180, 320))
t = ep.say("03", 0.35)
ep.fx("pour", t + 0.2)
for k in range(3):
    ep.fx("gulp", t + 1.6 + k * 0.32)
ep.wait(0.8)
t = ep.say("04", 0.3)
ep.fx("thump", t - 0.1)
ep.fx("thump", t + 2.6)
ep.say("05", 0.45)

# Бачок
ep.shot("e2b_toilet", (1.0, 180, 320), (1.15, 170, 340))
ep.fx("thump", ep.t + 0.1)
ep.wait(0.3)
ep.say("06", 0.35)
t = ep.say("07", 0.4)
ep.fx("pour", t + 0.3)
ep.fx("gulp", ep.t)
ep.fx("gulp", ep.t + 0.35)
ep.wait(1.0)
ep.shot("e2b_doors", (1.0, 180, 320), (1.15, 150, 330))
ep.say("08", 0.5)

# Обход квартир
ep.shot("e2b_neighbor", (1.0, 180, 320), (1.12, 220, 320))
ep.fx("creak", ep.t + 0.1)
for k in range(4):
    ep.fx("step", ep.t + 0.4 + k * 0.4)
ep.wait(0.3)
ep.say("09", 0.4)
ep.shot("e2b_radiator", (1.0, 180, 320), (1.2, 150, 380))
ep.fx("pour_long", ep.t + 0.2)
ep.wait(0.6)
ep.say("10", 1.0)
ep.shot("e2b_boiler", (1.0, 180, 320), (1.15, 170, 360))
ep.fx("pour_long", ep.t + 0.2)
ep.fx("pour_long", ep.t + 3.6)
ep.wait(0.8)
ep.say("11", 1.5)

# Еда
ep.shot("e2b_cupboard", (1.0, 180, 320), (1.2, 250, 300))
ep.fx("creak", ep.t + 0.1)
t = ep.t + 0.3
for k, item in enumerate(["+ 4 банки тушёнки", "+ гречка", "+ сухари", "+ мёд"]):
    ep.title(item, 1.4, at=t + k * 1.4, y=46)
    ep.fx("clink", t + k * 1.4)
ep.wait(0.3)
ep.say("12", 1.2)
ep.shot("e2_note", (1.25, 180, 320), (1.45, 180, 315))
ep.fx("scribble", ep.t + 0.1)
ep.wait(1.2)
ep.say("13", 1.0)

# Запасы
ep.shot("e2b_supplies", (1.0, 180, 320), (1.15, 190, 330), dust=True)
for k in range(3):
    ep.fx("clink", ep.t + 0.2 + k * 0.45)
ep.wait(1.0)
ep.say("14", 0.6)
t = ep.say("15", 0.3)
ep.title("ПРАВИЛО №1: СНАЧАЛА ВОДА. ПОТОМ ЕДА. ПОТОМ ВСЁ ОСТАЛЬНОЕ.", ep.t - t + 2.2, at=t)
ep.wait(1.9)

# Список жильцов
ep.shot("e2b_mailbox", (1.0, 180, 320), (1.2, 240, 260))
T_LIST = ep.t
for k in range(5):
    ep.fx("step", ep.t + 0.2 + k * 0.4)
ep.wait(0.4)
ep.say("16", 0.3)
ep.shot("e2_list", (1.25, 180, 170), (1.25, 180, 470))
ep.wait(0.8)
ep.say("17", 1.4)
ep.shot("e2_list", (1.3, 175, 413), (1.45, 168, 413))
ep.wait(0.6)
ep.say("18", 1.2)
ep.title("ЧТО ЗНАЧИТ ЭТОТ КРАСНЫЙ МАРКЕР? ПИШИТЕ ВЕРСИИ", 3.6)
ep.wait(3.6)
ep.finish()

if __name__ == "__main__":
    ep.build(swell_from=T_LIST - 10)
