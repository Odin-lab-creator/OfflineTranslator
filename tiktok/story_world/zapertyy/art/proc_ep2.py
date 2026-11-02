#!/usr/bin/env python3
"""Кадры серии 2 с русским текстом, нарисованные кодом в пиксельной сетке 216×384 (как кадры Pro):
proc/e2_note.png — записка на столе, proc/e2_list.png — список жильцов, зачёркнутый красным маркером.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "proc")
W, H = 216, 384
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
rng = np.random.default_rng(7)


def noise(a, amp):
    return np.clip(a + rng.normal(0, amp, a.shape[:2])[..., None], 0, 255)


def text(a, s, x, y, size, color, bold=False, jitter=0):
    f = ImageFont.truetype(FONT_B if bold else FONT, size)
    m = Image.new("1", (W, size + 6), 0)
    d = ImageDraw.Draw(m)
    d.fontmode = "1"
    d.text((0, 0), s, font=f, fill=1)
    g = np.asarray(m, bool)
    ys, xs = np.nonzero(g)
    if jitter:                                                 # «рукописная» неровность
        ys = ys + (np.sin(xs * 0.35) * jitter).round().astype(int)
    ok = (ys + y < H) & (xs + x < W)
    a[ys[ok] + y, xs[ok] + x] = color
    return d.textlength(s, font=f)


def vignette(a, k=0.55):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    return a * np.clip(1.1 - k * r2, 0.35, 1)[..., None]


def note():
    a = np.zeros((H, W, 3), np.float32)
    for y in range(H):                                        # доски стола
        plank = (y // 26) % 3
        base = np.array([[70, 48, 34], [62, 43, 30], [76, 52, 36]][plank], np.float32)
        a[y] = base[None] + (6 * np.sin(np.arange(W) * 0.07 + y * 0.9 + plank))[:, None]
        if y % 26 == 0:
            a[y] = (34, 24, 18)
    a = noise(a, 4)
    x0, y0, x1, y1 = 40, 140, 178, 236                        # лист бумаги + тень
    a[y0 + 3:y1 + 3, x0 + 3:x1 + 3] *= 0.55
    a[y0:y1, x0:x1] = (214, 206, 186)
    a[y0:y1, x0:x1] = noise(a[y0:y1, x0:x1], 4)
    for yy in range(y0 + 22, y1, 14):                         # линовка
        a[yy, x0 + 4:x1 - 4] = (180, 186, 196)
    ink = (38, 46, 92)
    for k, s in enumerate(["Взял воду и еду.", "Денис, кв. 9.", "Верну."]):
        text(a, s, x0 + 8, y0 + 10 + k * 14 + 1, 11, ink, jitter=1)
    a[248:252, 60:150] = (24, 24, 30)                         # ручка
    a[248:252, 150:156] = (170, 160, 60)
    a[249:251, 56:60] = (200, 200, 200)
    return vignette(a)


NAMES = [("Гусев В. П.", 1), ("Ильина Т. С.", 2), ("Захаровы", 3), ("Морозов И. А.", 4), ("Петренко", 5),
         ("Абдуллаевы", 6), ("Ким Л.", 7), ("Лебедева Н. И.", 8), ("Кравцов Д.", 9), ("Ткаченко", 10),
         ("Орлов С. В.", 11), ("Соколовы", 12), ("Белова А. М.", 13), ("Гончар", 14)]


def strike(a, x0, x1, y, seed):
    r = np.random.default_rng(seed)
    red = (178, 34, 30)
    dy = r.uniform(-1.5, 1.5)
    for x in range(x0, x1):
        yy = int(round(y + dy * (x - x0) / (x1 - x0) + 0.6 * np.sin(x * 0.3 + seed)))
        a[yy, x] = red


def residents():
    a = np.zeros((H, W, 3), np.float32)
    a[:] = (62, 70, 58)                                       # стена подъезда
    a = noise(a, 7)
    for k in range(6):                                        # потёки
        x = int(rng.uniform(0, W))
        a[:, x:x + 2] *= 0.88
    x0, y0, x1, y1 = 22, 40, 196, 360
    a[y0 + 4:y1 + 4, x0 + 4:x1 + 4] *= 0.5
    a[y0:y1, x0:x1] = (206, 200, 182)
    a[y0:y1, x0:x1] = noise(a[y0:y1, x0:x1], 5)
    a[y0 - 4:y0 + 6, 90:128] = (196, 190, 150)                # скотч
    ink = (30, 32, 40)
    f = ImageFont.truetype(FONT_B, 10)
    w = ImageDraw.Draw(Image.new("1", (1, 1))).textlength("ПОДЪЕЗД 1. ЖИЛЬЦЫ", font=f)
    text(a, "ПОДЪЕЗД 1. ЖИЛЬЦЫ", int((W - w) / 2), y0 + 8, 10, ink, bold=True)
    a[y0 + 23, x0 + 8:x1 - 8] = ink
    for k, (name, apt) in enumerate(NAMES[:13]):
        y = y0 + 32 + k * 22
        text(a, f"кв. {apt}", x0 + 8, y, 10, ink)
        text(a, name, x0 + 54, y, 10, ink)
        strike(a, x0 + 6, x1 - 8, y + 7, k)
    return vignette(a, 0.45)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(note().astype(np.uint8)).save(os.path.join(OUT, "e2_note.png"))
    Image.fromarray(residents().astype(np.uint8)).save(os.path.join(OUT, "e2_list.png"))
    print("готово")
