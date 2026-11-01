#!/usr/bin/env python3
"""PIXEL APOCALYPSE v2 — тестовые кадры «72 ЧАСА» в «бункерном» стиле.

cd tiktok/pixel_apocalypse && python3 test_frames2.py  →  frames_v2/*.png (1080x1920)
"""
import math
import os
import sys

import numpy as np
from PIL import Image

from characters import hero_sit, hero_stand, zombie
from pixel2 import H, W, XX, YY, Scene, col, value_noise

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames_v2")
os.makedirs(OUT, exist_ok=True)


# ================================================================ окружение
def stone_wall(s, x0, y0, x1, y1, seed, tones=("G4", "G5", "G4", "G3"), moss=0.35):
    r = np.random.default_rng(seed)
    nz = value_noise(seed, 3, 1.0)
    big = value_noise(seed + 1, 40, 1.0)
    s.rect(x0, y0, x1, y1, "G1")
    y = y0
    while y < y1:
        bh = int(r.integers(9, 15))
        x = x0 - int(r.integers(0, 20))
        while x < x1:
            bw = int(r.integers(14, 32))
            bx0, by0, bx1, by1 = max(x, x0), y, min(x + bw - 2, x1), min(y + bh - 2, y1)
            if bx1 > bx0 + 1 and by1 > by0 + 1:
                tone = tones[int(r.integers(0, len(tones)))]
                m = (XX >= bx0) & (XX <= bx1) & (YY >= by0) & (YY <= by1)
                s.fill(m, tone, noise=nz + big * 0.6, amp=0.16)
                s.rect(bx0, by0, bx1, by0, "G6")                      # верхняя грань — свет
                s.rect(bx0, by0, bx0, by1, "G5")
                s.rect(bx0, by1, bx1, by1, "G2")                      # нижняя — тень
                s.rect(bx1, by0, bx1, by1, "G3")
                if r.random() < 0.18 and bx1 - bx0 > 3:               # скол / трещина
                    cx, cy = int(r.integers(bx0 + 2, bx1)), int(r.integers(by0 + 1, by1))
                    s.line([(cx, cy), (cx + int(r.integers(-4, 5)), by1)], "G2")
            x += bw
        y += bh
    if moss:
        m = (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1) & (big + nz * 0.3 > 1 - moss * 1.6)
        s.blend(m, "M1", 0.55)


def bricks(s, x0, y0, x1, y1, seed):
    r = np.random.default_rng(seed)
    nz = value_noise(seed, 2, 1.0)
    s.rect(x0, y0, x1, y1, "G2")
    for j, y in enumerate(range(y0, y1, 5)):
        off = 0 if j % 2 else 5
        for x in range(x0 - off, x1, 10):
            m = (XX >= max(x, x0)) & (XX <= min(x + 8, x1)) & (YY >= y) & (YY <= min(y + 3, y1))
            s.fill(m, ["R2", "R1", "R2", "R3"][int(r.integers(0, 4))], noise=nz, amp=0.12)
            s.rect(max(x, x0), y, min(x + 8, x1), y, "R3")
    # рваный край
    for x in range(x0, x1 + 1):
        k = int(abs(math.sin(x * 0.7 + seed)) * 4)
        s.rect(x, y0, x, y0 + k, "G4")
        s.rect(x, y1 - k, x, y1, "G4")


def pipe_h(s, y, x0, x1, th, ramp=("G0", "G6", "G5", "G4", "G3", "G2"), flange=46, seed=0):
    rows = np.linspace(0, len(ramp) - 1, th).round().astype(int)
    for i in range(th):
        s.rect(x0, y + i, x1, y + i, ramp[rows[i]])
    s.rect(x0, y + th, x1, y + th, "G0")
    for fx in range(x0 + (seed * 13) % flange, x1, flange):
        s.rect(fx, y - 2, fx + 4, y + th + 2, "G0")
        s.rect(fx + 1, y - 1, fx + 3, y + th + 1, ramp[2])
        s.rect(fx + 1, y - 1, fx + 1, y + th + 1, ramp[1])
        s.px(fx + 2, y, "E1"); s.px(fx + 2, y + th, "E0")


def pipe_v(s, x, y0, y1, th, ramp=("G0", "G6", "G5", "G4", "G3", "G2"), flange=50):
    cols_ = np.linspace(0, len(ramp) - 1, th).round().astype(int)
    for i in range(th):
        s.rect(x + i, y0, x + i, y1, ramp[cols_[i]])
    s.rect(x + th, y0, x + th, y1, "G0")
    for fy in range(y0 + 20, y1, flange):
        s.rect(x - 2, fy, x + th + 2, fy + 4, "G0")
        s.rect(x - 1, fy + 1, x + th + 1, fy + 3, ramp[2])
        s.rect(x - 1, fy + 1, x + th + 1, fy + 1, ramp[1])


RUST = ("R0", "R4", "R3", "R2", "R1", "R0")


def cable(s, x0, y0, x1, y1, sag, c="G0", w=1):
    pts = []
    for i in range(41):
        t = i / 40
        pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)))
    s.line(pts, c, w)


def cobweb(s, x, y, size, sx=1, sy=1, seed=0):
    r = np.random.default_rng(seed)
    angs = np.linspace(0.05, math.pi / 2 - 0.05, 6)
    spokes = [(x + sx * size * math.cos(a), y + sy * size * math.sin(a)) for a in angs]
    m = np.zeros((H, W), bool)
    for p in spokes:
        m |= Scene.mask(lambda d, p=p: d.line([(x, y), p], fill=255))
    for k in (0.3, 0.5, 0.72, 0.92):
        pts = [(x + sx * size * k * math.cos(a), y + sy * size * k * math.sin(a) + r.integers(0, 2)) for a in angs]
        m |= Scene.mask(lambda d, pts=pts: d.line(pts, fill=255))
    s.blend(m, "E1", 0.45)


def ceiling(s, y1, seed):
    r = np.random.default_rng(seed)
    s.rect(0, 0, W - 1, y1, "G1")
    s.rect(0, y1 - 6, W - 1, y1, "G3"); s.rect(0, y1 - 6, W - 1, y1 - 6, "G5"); s.rect(0, y1, W - 1, y1, "G0")
    for x in range(4, W, 9):
        s.px(x, y1 - 3, "G6")
    for x in range(0, W, 30):  # балки с раскосами
        s.line([(x, 0), (x + 30, y1 - 7)], "G2", 2)
        s.line([(x + 30, 0), (x, y1 - 7)], "G2", 2)
        s.rect(x, 0, x + 2, y1 - 7, "G3")


def floor(s, y, seed, deck=("G6", "G4", "G3")):
    r = np.random.default_rng(seed)
    s.rect(0, y, W - 1, y, deck[0])
    s.rect(0, y + 1, W - 1, y + 6, deck[1], noise=value_noise(seed, 2), amp=0.12)
    s.rect(0, y + 7, W - 1, y + 8, "G0")
    for x in range(6, W, 18):
        s.px(x, y + 3, "G6"); s.px(x + 1, y + 3, "G2")
    s.rect(0, y + 9, W - 1, H - 1, "G0")
    for x in range(0, W, 4):  # решётка под настилом
        s.rect(x, y + 9, x, H - 1, "G2")
    for yy in range(y + 16, H, 11):
        s.rect(0, yy, W - 1, yy, "G2")
    for x in range(10, W, 62):  # опоры
        s.rect(x, y + 9, x + 5, H - 1, "G3"); s.rect(x, y + 9, x, H - 1, "G5")
        s.line([(x + 5, y + 12), (x + 40, H - 1)], "G2", 2)


def rubble(s, x0, x1, ybase, seed, n=40, tones=("G3", "G4", "G2", "G5", "E0")):
    r = np.random.default_rng(seed)
    for _ in range(n):
        x = int(r.integers(x0, x1)); w = int(r.integers(2, 7)); h = int(r.integers(1, 4))
        s.rect(x, ybase - h, x + w, ybase, tones[int(r.integers(0, len(tones)))])
        s.rect(x, ybase - h, x + w, ybase - h, "G6" if r.random() < 0.5 else "G5")


def wall_lamp(s, x, y, on=True, inten=1.0):
    s.rect(x - 1, y - 9, x + 1, y - 4, "G2")
    s.rect(x - 4, y - 4, x + 4, y - 3, "G0")
    s.ell(x, y + 2, 3, 5, "O3" if on else "G3", emissive=on)
    if on:
        s.ell(x, y + 1, 1, 2, "O4", emissive=True)
    for dx in (-3, 0, 3):
        s.rect(x + dx, y - 3, x + dx, y + 7, "G0")
    s.rect(x - 4, y + 7, x + 4, y + 8, "G0")
    if on:
        s.add_light(x, y + 2, 90, inten)


def hero(s, cx, y, pipe=False, dark=0.0):
    """Герой стоя (лицом вправо); cx — центр спрайта, y — линия пола."""
    s.paste(hero_stand(pipe), cx, y, dark=dark)


# ================================================================== КАДР 3
def frame_door():
    """«Стук в дверь. — Эй! Открой! У меня раненый друг!»"""
    s = Scene()
    stone_wall(s, 0, 60, W - 1, 396, 3)
    bricks(s, 18, 150, 96, 200, 5)
    bricks(s, 190, 300, 262, 352, 6)
    ceiling(s, 36, 1)
    pipe_h(s, 46, 0, W - 1, 9, seed=1)
    pipe_h(s, 62, 0, 200, 6, ramp=RUST, seed=2)
    pipe_h(s, 120, 0, W - 1, 5, seed=3)
    s.rect(196, 62, 202, 120, "R2"); s.rect(196, 62, 196, 120, "R4")  # колено ржавой трубы
    pipe_v(s, 236, 56, 396, 8)
    s.ell(240, 300, 7, 7, "G0"); s.ell(240, 300, 5, 5, "R3"); s.ell(240, 300, 2, 2, "G0")  # вентиль
    for x0, x1, sg in [(0, 70, 26), (60, 150, 34), (140, 230, 22), (150, 270, 40)]:
        cable(s, x0, 70, x1, 72, sg)
    for x0, x1, sg in [(30, 120, 18), (120, 200, 26)]:
        cable(s, x0, 126, x1, 128, sg, "G0")
    cobweb(s, 0, 37, 34, 1, 1, 1)
    cobweb(s, W - 1, 37, 30, -1, 1, 2)
    # дверь
    dx0, dy0, dx1, dy1 = 104, 238, 168, 395
    s.rect(dx0 - 7, dy0 - 7, dx1 + 7, dy1, "G0")
    s.rect(dx0 - 6, dy0 - 6, dx1 + 6, dy1, "G4"); s.rect(dx0 - 6, dy0 - 6, dx1 + 6, dy0 - 6, "G6")
    s.rect(dx0, dy0, dx1, dy1, "G3", noise=value_noise(9, 2), amp=0.15)
    s.rect(dx0, dy0, dx0, dy1, "G5")
    s.rect(dx0 + 6, dy0 + 6, dx1 - 6, dy0 + 6, "G2"); s.rect(dx0 + 6, dy0 + 6, dx0 + 6, dy1 - 8, "G2")
    s.rect(dx0 + 14, dy0 + 14, dx1 - 14, dy0 + 34, "G0")  # окошко с решёткой
    for gx in range(dx0 + 17, dx1 - 14, 5):
        s.rect(gx, dy0 + 14, gx + 1, dy0 + 34, "G4")
    s.rect(dx1 - 12, dy0 + 82, dx1 - 6, dy0 + 92, "G0"); s.rect(dx1 - 11, dy0 + 84, dx1 - 7, dy0 + 85, "G6")
    for i in range(10):  # потёки ржавчины
        x = dx0 + 8 + i * 6
        s.blend((XX == x) & (YY > dy0 + 36) & (YY < dy0 + 50 + (i * 37) % 60), "R2", 0.5)
    # полоска света под дверью и тени ног
    s.rect(dx0, dy1 - 1, dx1, dy1, "O3", emissive=True)
    for fx in (122, 140):
        s.rect(fx, dy1 - 1, fx + 7, dy1, "G0")
    s.add_light(136, dy1 + 2, 70, 0.9, ry=26)
    wall_lamp(s, 70, 232, inten=0.8)
    wall_lamp(s, 206, 220, on=False)
    floor(s, 396, 4)
    rubble(s, 0, 60, 396, 7, 30)
    rubble(s, 176, 230, 396, 8, 25)
    hero(s, 56, 395, pipe=True)
    s.ambient = np.array([0.5, 0.62, 0.55], np.float32)
    return s


# ================================================================== КАДР 1
def frame_wake():
    """«Ты проснулся, а цивилизация рухнула.»"""
    s = Scene()
    nz = value_noise(11, 2)
    s.rect(0, 40, W - 1, 396, "G4", noise=nz + value_noise(12, 30) * 0.6, amp=0.14)  # штукатурка
    for x in range(0, W, 14):  # выцветшие обои
        s.blend((XX >= x) & (XX < x + 7) & (YY > 40) & (YY < 396), "G5", 0.35)
    r = np.random.default_rng(3)
    for _ in range(7):  # отваливающиеся куски
        x, y = int(r.integers(0, W - 30)), int(r.integers(60, 330))
        s.poly([(x, y), (x + 20, y + 3), (x + 16, y + 26), (x + 2, y + 18)], "G2")
        s.line([(x, y), (x + 20, y + 3)], "G6")
    stone_wall(s, 0, 300, 40, 396, 4, moss=0.2)
    ceiling(s, 34, 2)
    pipe_h(s, 42, 0, W - 1, 6, ramp=RUST, seed=4)
    # окно на горящий город
    wx0, wy0, wx1, wy1 = 120, 120, 250, 300
    ins = (XX > wx0) & (XX < wx1) & (YY > wy0) & (YY < wy1)
    k = np.clip((YY - wy0) / (wy1 - wy0), 0, 1)
    sky = np.stack([lerp_c("R1", "O1", k ** 1.3)[c] for c in range(3)], -1)
    s.rgb[ins] = sky[ins]; s.emis |= ins
    rr = np.random.default_rng(7)
    for layer, (tone, base, hmin, hmax) in enumerate([("G2", 300, 40, 120), ("G1", 300, 20, 80)]):
        x = wx0 - 10
        while x < wx1 + 10:
            bw = int(rr.integers(10, 24)); bh = int(rr.integers(hmin, hmax))
            pts = [(x, base), (x, base - bh)] + [(x + bw * j / 4, base - bh + int(rr.integers(0, 14))) for j in range(1, 4)] + [(x + bw, base - bh + 6), (x + bw, base)]
            m = Scene.mask(lambda d, pts=pts: d.polygon(pts, fill=255)) & ins
            s.rgb[m] = col(tone)
            for wy in range(base - bh + 6, base - 4, 6):
                for wxx in range(x + 2, x + bw - 2, 4):
                    if rr.random() < 0.08 and ins[wy, wxx]:
                        s.rect(wxx, wy, wxx + 1, wy + 2, "O2", emissive=True)
            x += bw
    for i in range(2):  # дым
        cx = wx0 + 30 + i * 60
        for y in range(wy0, 290, 2):
            w = 6 + (300 - y) * 0.12 + math.sin(y * 0.1 + i) * 3
            m = ((XX - cx - math.sin(y * 0.05 + i) * 6) / w) ** 2 + ((YY - y) / 3) ** 2 <= 1
            s.blend(m & ins, "G3", 0.3)
    for fx in (138, 176, 214, 236):  # пожары
        for j in range(12):
            h = int(14 * (1 - abs(j - 6) / 7) * (0.6 + 0.4 * math.sin(fx + j * 2)))
            s.rect(fx + j, 299 - h, fx + j, 299, "O2", emissive=True)
            s.rect(fx + j, 299 - h // 2, fx + j, 299, "O3", emissive=True)
    s.rect(wx0 - 6, wy0 - 6, wx1 + 6, wy0 - 1, "B1"); s.rect(wx0 - 6, wy1, wx1 + 6, wy1 + 7, "B1")
    s.rect(wx0 - 6, wy0, wx0, wy1, "B1"); s.rect(wx1, wy0, wx1 + 6, wy1, "B1")
    s.rect(184, wy0, 186, wy1, "B1"); s.rect(wx0, 208, wx1, 210, "B1")
    s.rect(wx0 - 8, wy1 + 6, wx1 + 8, wy1 + 9, "B2"); s.rect(wx0 - 8, wy1 + 6, wx1 + 8, wy1 + 6, "E0")
    s.line([(222, 121), (232, 150), (226, 168), (249, 180)], "E1")
    s.poly([(222, 121), (249, 121), (249, 146), (232, 150)], "G0")
    for x0, x1 in [(104, 128), (242, 262)]:  # шторы
        s.poly([(x0, 104), (x1, 104), (x1 - 4, 318), (x0 + 3, 326)], "M1")
        for fx in range(x0 + 3, x1 - 2, 4):
            s.line([(fx, 106), (fx + 1, 320)], "M0")
        s.line([(x0 + 1, 106), (x0 + 1, 322)], "M2")
    s.rect(98, 100, 268, 102, "G5")
    # лампа на проводе (разбита)
    cable(s, 60, 34, 62, 92, 0)
    s.poly([(52, 92), (72, 92), (68, 100), (56, 100)], "G3"); s.rect(52, 92, 72, 92, "G6")
    # кровать
    s.rect(4, 352, 96, 368, "B1"); s.rect(4, 352, 96, 352, "B2")
    s.rect(6, 340, 94, 352, "E0"); s.rect(6, 340, 94, 340, "E1")
    s.poly([(30, 336), (96, 340), (92, 356), (24, 352)], "M1")
    s.rect(8, 332, 28, 341, "E1")
    s.rect(4, 320, 9, 395, "B1"); s.rect(92, 360, 96, 395, "B1")
    cobweb(s, 0, 35, 30, 1, 1, 4)
    floor(s, 396, 5, deck=("B2", "B1", "B0"))
    rubble(s, 100, 260, 396, 9, 30, tones=("G3", "E0", "B1", "G4"))
    hero(s, 152, 395)
    s.add_light(185, 230, 150, 1.0, halo=False, ry=190)
    s.add_light(185, 300, 120, 0.7, ry=80)
    s.ambient = np.array([0.42, 0.5, 0.46], np.float32)
    return s


def lerp_c(a, b, k):
    ca, cb = col(a), col(b)
    return [ca[i] + (cb[i] - ca[i]) * k for i in range(3)]


# ================================================================== КАДР 2
def frame_supplies():
    """«Тебе нужны вода, консервы, аптечка, фонарь и запасные батарейки.»"""
    s = Scene()
    stone_wall(s, 0, 50, W - 1, 396, 21)
    ceiling(s, 34, 3)
    pipe_h(s, 40, 0, W - 1, 7, seed=5)
    pipe_h(s, 54, 60, W - 1, 5, ramp=RUST, seed=6)
    for x0, x1, sg in [(0, 90, 20), (80, 190, 30), (170, 270, 24)]:
        cable(s, x0, 62, x1, 64, sg)
    cobweb(s, W - 1, 35, 36, -1, 1, 5)
    # стеллаж
    sx0, sx1 = 120, 262
    for sy in (120, 175, 230):
        s.rect(sx0, sy, sx1, sy + 3, "G5"); s.rect(sx0, sy, sx1, sy, "G7"); s.rect(sx0, sy + 4, sx1, sy + 4, "G0")
    for x in (sx0, sx1 - 3):
        s.rect(x, 96, x + 3, 300, "G4"); s.rect(x, 96, x, 300, "G6")
    rr = np.random.default_rng(2)
    for sy in (120, 175, 230):
        x = sx0 + 6
        while x < sx1 - 12:
            kind = rr.random()
            if kind < 0.5:   # банки
                h = int(rr.integers(10, 16)); w = 8
                lab = ["R2", "M2", "E0", "R3"][int(rr.integers(0, 4))]
                s.rect(x, sy - h, x + w, sy - 1, "G6"); s.rect(x, sy - h + 3, x + w, sy - 4, lab)
                s.rect(x, sy - h, x + w, sy - h, "E1"); s.rect(x, sy - h, x, sy - 1, "G7")
            elif kind < 0.8:  # стеклянные банки
                h = int(rr.integers(14, 22)); w = 9
                s.rect(x, sy - h, x + w, sy - 1, "G5"); s.rect(x + 1, sy - h + 5, x + w - 1, sy - 2, ["M2", "R2", "O1"][int(rr.integers(0, 3))])
                s.rect(x, sy - h, x + w, sy - h + 2, "G3"); s.rect(x + 2, sy - h + 4, x + 2, sy - 3, "G8")
            else:            # пусто / коробка
                w = 14
                if rr.random() < 0.6:
                    s.rect(x, sy - 12, x + w, sy - 1, "B1"); s.rect(x, sy - 12, x + w, sy - 12, "B2")
            x += w + 3
    # стол
    s.rect(70, 348, 262, 354, "B2"); s.rect(70, 348, 262, 348, "B2"); s.rect(70, 355, 262, 356, "G0")
    s.rect(72, 357, 77, 395, "B1"); s.rect(254, 357, 259, 395, "B1")
    # вода: две пятилитровки
    for jx in (84, 104):
        s.rect(jx, 314, jx + 16, 347, "G6"); s.rect(jx + 1, 328, jx + 15, 346, "G7")
        s.rect(jx + 2, 316, jx + 3, 344, "E2"); s.rect(jx + 5, 308, jx + 11, 313, "R3")
    # консервы
    for cx, cy in [(128, 347), (139, 347), (133, 335)]:
        s.rect(cx, cy - 11, cx + 9, cy, "G7"); s.rect(cx, cy - 8, cx + 9, cy - 3, "R2"); s.rect(cx, cy - 11, cx + 9, cy - 11, "E1")
    # аптечка
    s.rect(154, 326, 182, 347, "E1"); s.rect(154, 326, 182, 326, "E2"); s.rect(154, 347, 182, 347, "E0")
    s.rect(166, 330, 170, 343, "R3"); s.rect(161, 334, 175, 338, "R3"); s.rect(163, 322, 173, 325, "G3")
    # батарейки
    for bx in (188, 193, 198):
        s.rect(bx, 335, bx + 3, 347, "G1"); s.rect(bx, 335, bx + 3, 338, "O1"); s.px(bx + 1, 334, "E1")
    # фонарь, светит вправо
    s.rect(208, 338, 226, 346, "G2"); s.rect(208, 338, 226, 338, "G5"); s.rect(226, 336, 230, 348, "G4")
    s.rect(230, 337, 231, 347, "O4", emissive=True)
    cone = Scene.mask(lambda d: d.polygon([(231, 337), (269, 320), (269, 335), (231, 347)], fill=255))
    s.blend(cone, "O1", np.clip(1 - (XX - 231) / 40, 0, 1) * 0.55)
    s.add_light(236, 342, 60, 0.9, ry=40)
    wall_lamp(s, 160, 250, inten=1.0)
    floor(s, 396, 6)
    rubble(s, 120, 250, 396, 3, 18)
    hero(s, 62, 395)
    s.ambient = np.array([0.46, 0.56, 0.5], np.float32)
    return s


# ================================================================== КАДР 4
def frame_radio():
    """«Наступает вторая ночь. Ты сидишь в темноте и слушаешь радио.»"""
    s = Scene()
    stone_wall(s, 0, 50, W - 1, 396, 31)
    bricks(s, 30, 90, 110, 140, 9)
    ceiling(s, 34, 4)
    pipe_h(s, 40, 0, W - 1, 8, seed=7)
    pipe_v(s, 16, 48, 396, 6)
    for x0, x1, sg in [(20, 130, 30), (110, 270, 34)]:
        cable(s, x0, 50, x1, 52, sg)
    # заколоченное окно, лунный свет
    wx0, wy0, wx1, wy1 = 150, 120, 240, 220
    s.rect(wx0, wy0, wx1, wy1, "G0")
    s.ell(192, 138, 6, 6, "E2", emissive=True)
    for i, (py, tilt) in enumerate([(126, -3), (146, 4), (168, -2), (190, 3), (208, -4)]):
        s.poly([(wx0 - 8, py), (wx1 + 8, py + tilt), (wx1 + 8, py + tilt + 12), (wx0 - 8, py + 12)], "B1")
        s.line([(wx0 - 8, py), (wx1 + 8, py + tilt)], "B2")
        s.px(wx0 - 4, py + 6, "E1"); s.px(wx1 + 4, py + tilt + 6, "E1")
    s.rect(wx0 - 10, wy1 + 12, wx1 + 10, wy1 + 15, "G5")
    s.add_light(196, 170, 120, 0.55, color=(0.55, 0.75, 0.8), halo=False, ry=150)
    for i, gy in enumerate((139, 160, 182, 202)):  # лучи из щелей на пол
        m = Scene.mask(lambda d, gy=gy, i=i: d.polygon([(wx0 + 4, gy), (wx1 - 4, gy), (130 - i * 24, 396), (96 - i * 24, 396)], fill=255))
        s.blend(m, "G7", 0.12)
    # спальник, ящик, радио, свеча, винтовка
    s.poly([(150, 395), (160, 376), (262, 374), (266, 395)], "M1"); s.line([(160, 376), (262, 374)], "M2")
    s.line([(170, 384), (260, 383)], "M0")
    s.rect(90, 362, 140, 395, "B1"); s.rect(90, 362, 140, 362, "B2"); s.line([(90, 362), (140, 395)], "B0")
    s.rect(96, 340, 132, 361, "R1"); s.rect(96, 340, 132, 340, "R3")
    for gx in range(99, 112, 3):
        for gy in range(344, 360, 3):
            s.px(gx, gy, "R0")
    s.rect(114, 344, 129, 350, "O3", emissive=True); s.rect(121, 344, 121, 350, "R3")
    s.ell(118, 355, 2, 2, "G6"); s.ell(126, 355, 2, 2, "G6")
    s.line([(130, 340), (146, 304)], "G6")
    s.add_light(121, 347, 80, 1.0)
    s.rect(144, 386, 147, 395, "E1"); s.px(145, 384, "O3", emissive=True); s.px(145, 383, "O4", emissive=True)
    s.add_light(145, 384, 40, 0.6)
    s.line([(244, 395), (258, 300)], "G0", 3); s.line([(250, 345), (252, 335)], "B2", 4)
    floor(s, 396, 7)
    s.paste(hero_sit(), 60, 395)
    s.ambient = np.array([0.36, 0.46, 0.44], np.float32)
    return s


# ================================================================== КАДР 5
def frame_window():
    """«НЕ СМОТРИ В ОКНО» … «за твоей спиной раздаётся скрип пола»."""
    s = Scene()
    nz = value_noise(41, 2)
    s.rect(0, 40, W - 1, 396, "G4", noise=nz + value_noise(42, 30) * 0.6, amp=0.14)
    for x in range(0, W, 14):
        s.blend((XX >= x) & (XX < x + 7) & (YY > 40) & (YY < 396), "G5", 0.35)
    ceiling(s, 34, 5)
    pipe_h(s, 42, 0, W - 1, 6, seed=8)
    cobweb(s, W - 1, 35, 34, -1, 1, 6)
    # окно на ночную улицу
    wx0, wy0, wx1, wy1 = 150, 130, 256, 300
    ins = (XX > wx0) & (XX < wx1) & (YY > wy0) & (YY < wy1)
    s.rect(wx0, wy0, wx1, wy1, "G1"); s.emis |= ins
    rr = np.random.default_rng(5)
    x = wx0
    while x < wx1:
        bw = int(rr.integers(14, 26)); bh = int(rr.integers(40, 110))
        m = (XX >= x) & (XX < x + bw) & (YY > 268 - bh) & (YY <= 268) & ins
        s.rgb[m] = col("G0")
        x += bw + 2
    s.rect(wx0, 268, wx1, wy1, "G2"); s.rect(wx0, 274, wx1, 274, "G4")
    s.rect(196, 284, 232, 296, "G3"); s.rect(202, 277, 226, 284, "G3"); s.rect(206, 279, 214, 283, "G0")
    s.ell(203, 296, 3, 3, "G0"); s.ell(226, 296, 3, 3, "G0")
    s.rect(176, 200, 177, 299, "G4"); s.rect(170, 198, 178, 200, "G4")
    s.rect(168, 200, 172, 203, "O3")
    cone = Scene.mask(lambda d: d.polygon([(166, 204), (174, 204), (194, 299), (148, 299)], fill=255)) & ins
    s.blend(cone, "O1", np.clip((YY - 200) / 140, 0, 1) * 0.45)
    s.rect(wx0 - 6, wy0 - 6, wx1 + 6, wy0 - 1, "B1"); s.rect(wx0 - 6, wy1, wx1 + 6, wy1 + 7, "B1")
    s.rect(wx0 - 6, wy0, wx0, wy1, "B1"); s.rect(wx1, wy0, wx1 + 6, wy1, "B1")
    s.rect(202, wy0, 204, wy1, "B1"); s.rect(wx0, 214, wx1, 216, "B1")
    s.rect(wx0 - 8, wy1 + 6, wx1 + 8, wy1 + 9, "B2")
    s.add_light(200, 240, 140, 0.45, color=(0.55, 0.75, 0.8), halo=False, ry=200)
    # тёмный дверной проём слева, в нём заражённый
    s.rect(52, 240, 114, 395, "G0")
    s.rect(46, 234, 52, 395, "B1"); s.rect(114, 234, 120, 395, "B1"); s.rect(46, 230, 120, 235, "B1")
    s.rect(47, 234, 47, 395, "B2")
    s.paste(zombie(), 84, 395, dark=0.15)
    s.add_light(110, 330, 50, 0.25, color=(0.55, 0.75, 0.8), halo=False)
    floor(s, 396, 8, deck=("B2", "B1", "B0"))
    s.rect(122, 395, 146, 395, "E0")  # скрипнувшая доска
    s.line([(128, 392), (130, 388)], "G6"); s.line([(138, 391), (141, 387)], "G6")
    rubble(s, 110, 260, 396, 12, 20, tones=("G3", "E0", "B1"))
    hero(s, 180, 395)
    s.ambient = np.array([0.32, 0.42, 0.42], np.float32)
    return s


# имя файла, сцена, левый верхний угол камеры 180x320
FRAMES = [
    ("01_probuzhdenie.png", frame_wake, (84, 96)),
    ("02_pripasy.png", frame_supplies, (34, 96)),
    ("03_stuk_v_dver.png", frame_door, (12, 100)),
    ("04_vtoraya_noch_radio.png", frame_radio, (28, 100)),
    ("05_ne_smotri_v_okno.png", frame_window, (60, 96)),
]

if __name__ == "__main__":
    only = sys.argv[1:]
    small = []
    for name, fn, cam in FRAMES:
        if only and not any(o in name for o in only):
            continue
        small.append(fn().save(os.path.join(OUT, name), crop=cam))
        print("✓", name)
    if not only:
        sw, sh = small[0].width * 2, small[0].height * 2
        sheet = Image.new("RGB", (sw * len(small) + 8 * (len(small) - 1), sh))
        for i, im in enumerate(small):
            sheet.paste(im.resize((sw, sh), Image.NEAREST), (i * (sw + 8), 0))
        sheet.save(os.path.join(OUT, "contact_sheet.png"))
