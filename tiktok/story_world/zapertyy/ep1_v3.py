#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 «Заперт» — рабочая версия v3 на comic_engine.

python3 ep1_v3.py  →  zapertyy_ep1_v3.mp4
Кадры — самые детальные Pro 360×640 (art/test_pro), в видео видна их часть 360×400 (×3 → 1080×1200).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import comic_engine as ce
from ep1_lines import LINES, path

HERE = os.path.dirname(os.path.abspath(__file__))
C_PAINT = (168, 58, 46)


def stairs_paint(a):
    """Надпись краской над стрелкой на стене лестницы."""
    f = ImageFont.truetype(ce.FONT, 12)
    m = Image.new("1", (130, 18), 0)
    d = ImageDraw.Draw(m)
    d.fontmode = "1"
    d.text((0, 0), "К АВТОБУСАМ", font=f, fill=1)
    ys, xs = np.nonzero(np.asarray(m, bool))
    a[ys + 268, xs + 32] = C_PAINT
    return a


ce.Episode.patch["14_stairs"] = stairs_paint

ep = ce.Episode([(i, t, kw) for i, _, t, kw in LINES], path, os.path.join(HERE, "zapertyy_ep1_v3.mp4"))
ep.voice_fx["12"] = "echo"
for i in ("13", "14", "15", "16", "17"):
    ep.voice_fx[i] = "reverb"

# Зацепка: чёрный экран, удары
ep.shot(None)
for k in range(3):
    ep.fx("bang", 0.15 + k * 0.6)
ep.wait(1.9)
ep.say("00", 0.35)
ep.title("ЗАПЕРТЫЙ · СЕРИЯ 1", 1.9)
ep.wait(1.9)

# Очнулся
ep.shot("01_wake", (1.0, 180, 430), (1.15, 230, 450), eyelids=True, dust=True)
ep.fx("ring")
ep.title("ДЕНЬ 1", 3.2, at=ep.t + 0.8)
ep.wait(0.8)
ep.say("01", 0.5)
ep.say("02", 0.4)

# Встал, огляделся
ep.shot("06_stand", (1.3, 190, 330), (1.15, 185, 350), dust=True)
ep.say("03", 0.35)
t04 = ep.say("04", 0.0)
c04 = ep.chunk_times("04", t04)
ep.shot("07_phone", (1.0, 180, 300), (1.1, 150, 340), at=c04[1][0])
t_mid = c04[2][0] if len(c04) > 2 else c04[1][1]
ep.shot("08_watch", (1.0, 180, 320), (1.2, 225, 300), at=t_mid)
ep.wait(0.45)
ep.shot("09_pills", (1.0, 180, 330), (1.12, 220, 320), dust=True)
ep.say("05", 0.35)
ep.shot("10_tap", (1.0, 180, 330), (1.12, 190, 300))
ep.fx("drip")
ep.wait(0.35)
ep.say("06", 0.15)
ep.fx("drip")
ep.wait(0.6)
ep.fx("drip")
ep.wait(0.4)

# Окно
ep.shot("02_window", (1.0, 180, 300), (1.1, 180, 280), dust=True)
ep.fx("whoosh", ep.t + 0.1)
ep.wait(0.4)
ep.say("07", 0.3)
ep.shot("11_weld", (1.0, 180, 360), (1.1, 170, 350), rattle=True)
for k in range(6):
    ep.fx("rattle", ep.t + 0.1 + k * 0.32)
ep.say("08", 0.3)
ep.shot("02_window", (1.2, 180, 220), (1.35, 180, 200), dust=True)
ep.wait(0.2)
ep.say("09", 0.5)

# Коридор
ep.shot("13_door", (1.0, 180, 360), (1.1, 185, 370))
ep.fx("creak")
ep.wait(0.4)
ep.say("10", 0.35)
ep.shot("03_corridor", (1.1, 200, 400), (1.3, 240, 400), dust=True, shake=True)
ep.say("11", 0.4)
ep.shakes.append(ep.t)
ep.say("12", 1.2)
ep.say("13", 0.4)

# Лестница
ep.shot("14_stairs", (1.1, 160, 330), (1.1, 190, 400), dust=True)
for k in range(8):
    ep.fx("step", ep.t + 0.2 + k * 0.45)
ep.wait(0.5)
ep.say("14", 0.4)

# Дверь подъезда
ep.shot("15_intercom", (1.0, 200, 330), (1.12, 280, 330))
ep.fx("rattle", ep.t + 0.4)
ep.fx("rattle", ep.t + 1.1)
ep.wait(0.3)
ep.say("15", 0.2)
ep.shot("04_kick", (1.06, 185, 380), (1.12, 195, 380), kick=True)
ep.kicks = [ep.t + d for d in (0.0, 0.55, 1.05, 1.75, 2.3, 2.75)]
for t in ep.kicks:
    ep.fx("bang", t)
ep.wait(0.4)
ep.say("16", 0.3)
ep.shot("16_crack", (1.0, 180, 320), (1.2, 230, 300))
ep.wait(0.3)
ep.say("17", 0.5)

# Финал
ep.shot("05_end", (1.35, 230, 440), (1.15, 205, 420), fade=True)
T_END = ep.t
ep.fx("slide", ep.t + 0.2)
ep.wait(0.3)
ep.say("18", 0.8)
ep.say("19", 0.5)
ep.title("ПОПЫТКА №1: ДВЕРЬ — ПРОВАЛ", 2.4)
ep.wait(2.4)
ep.title("ЧТО БЫ ВЫ СДЕЛАЛИ ПЕРВЫМ?", 3.0)
ep.wait(3.0)
ep.finish()

if __name__ == "__main__":
    ep.build(swell_from=T_END - 25)
