#!/usr/bin/env python3
"""PIXEL APOCALYPSE — тестовые кадры улиц (продолжение «72 ЧАСОВ»: герой выходит на поверхность).

cd tiktok/pixel_apocalypse && python3 test_frames3.py  →  frames_v3/*.png (1080x1920)
Стиль — строго по STYLE_LOCK.md (движок pixel2, персонажи characters).
"""
import math
import os
import sys

import numpy as np
from PIL import Image

from characters import hero_crouch, hero_stand, hero_walk, zombie
from pixel2 import H, W, XX, YY, Scene, col, value_noise
from test_frames2 import cable, rubble, stone_wall

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames_v3")
os.makedirs(OUT, exist_ok=True)
GROUND = 395
CAM = (45, 110)  # окно камеры 180x320 в мире 270x480: видно x 45..225, y 110..430


# ================================================================ улица
def sky(s, y0, y1, cols, emissive=True):
    k = np.clip((YY - y0) / max(1, y1 - y0), 0, 1)
    stops = [col(c) for c in cols]
    seg = k * (len(stops) - 1)
    i = np.minimum(seg.astype(int), len(stops) - 2)
    f = (seg - i)[..., None]
    a = np.stack(stops)[i]; b = np.stack(stops)[i + 1]
    m = YY <= y1
    s.rgb[m] = (a * (1 - f) + b * f)[m]
    if emissive:
        s.emis |= m


def highrise(s, x0, x1, top, base, seed, tone="G2", win="G0", lit=0.0, ruined=True):
    """Многоэтажка: рваный верх, сетка окон, обнажённые перекрытия."""
    r = np.random.default_rng(seed)
    pts = [(x0, base), (x0, top + int(r.integers(0, 10)))]
    if ruined:
        n = 5
        for j in range(1, n):
            pts.append((x0 + (x1 - x0) * j / n, top + int(r.integers(0, 40))))
    pts += [(x1, top + int(r.integers(0, 25))), (x1, base)]
    m = Scene.mask(lambda d: d.polygon(pts, fill=255))
    s.fill(m, tone, noise=value_noise(seed, 3), amp=0.12)
    for y in range(top + 6, base - 4, 9):          # этажи
        for x in range(x0 + 3, x1 - 3, 6):
            if m[y, x] and m[min(y + 5, H - 1), x]:
                v = r.random()
                c = "O2" if v < lit else win if v < 0.85 else "G3"
                s.rect(x, y, x + 2, y + 4, c, emissive=c == "O2")
        if r.random() < 0.3:
            s.rect(x0, y - 2, x1, y - 2, "G4")
    # срез обрушения: плиты и арматура
    ys = min(p[1] for p in pts[2:-2]) if ruined else top
    for j in range(3):
        y = ys + 6 + j * 9
        s.line([(x0 + 2, y), (x1 - 4, y + int(r.integers(-2, 3)))], "G4")
    for _ in range(6):
        x = int(r.integers(x0 + 2, x1 - 2))
        colm = np.nonzero(m[:, x])[0]
        if not len(colm):
            continue
        y = int(colm[0])
        s.line([(x, y), (x + int(r.integers(-3, 4)), y - int(r.integers(3, 8)))], "G5")
    return m


def road(s, y, seed, wet=False):
    r = np.random.default_rng(seed)
    s.rect(0, y, W - 1, y + 3, "E0"); s.rect(0, y, W - 1, y, "E1")        # бордюр
    s.rect(0, y + 4, W - 1, H - 1, "P0", noise=value_noise(seed, 2), amp=0.2)
    for x in range(int(r.integers(0, 20)), W, 34):                         # разметка
        if r.random() < 0.75:
            s.rect(x, y + 20, x + 14, y + 21, "E0")
    for _ in range(14):                                                    # трещины
        x, yy_ = int(r.integers(0, W)), int(r.integers(y + 5, H - 2))
        pts = [(x, yy_)]
        for _ in range(4):
            x += int(r.integers(2, 7)); yy_ += int(r.integers(-2, 3)); pts.append((x, yy_))
        s.line(pts, "G0")
    for _ in range(3):                                                     # выбоины
        x, yy_ = int(r.integers(10, W - 20)), int(r.integers(y + 10, H - 10))
        s.ell(x, yy_, int(r.integers(4, 9)), 2, "G1")
        s.rect(x - 3, yy_ - 2, x + 3, yy_ - 2, "P1")


def car(s, x, y, seed, body="R2", flat=True, burnt=False):
    """Брошенный легковой автомобиль в профиль, ~120x44, (x, y) — левый край, низ колёс."""
    r = np.random.default_rng(seed)
    bd = "G2" if burnt else body
    s.poly([(x + 2, y - 10), (x + 4, y - 26), (x + 30, y - 28), (x + 46, y - 44), (x + 84, y - 44),
            (x + 100, y - 28), (x + 118, y - 25), (x + 120, y - 12), (x + 116, y - 8), (x + 4, y - 8)], bd,
           noise=value_noise(seed, 2), amp=0.15)
    s.line([(x + 4, y - 26), (x + 30, y - 28), (x + 46, y - 44), (x + 84, y - 44), (x + 100, y - 28), (x + 118, y - 25)], "R4" if not burnt else "G4")
    for (a, b) in ((49, 64), (68, 84)):                                     # окна
        s.poly([(x + a, y - 41), (x + b, y - 41), (x + b + (12 if b > 70 else 0), y - 29), (x + a - (12 if a < 50 else 0), y - 29)], "G1")
    s.line([(x + 52, y - 39), (x + 57, y - 32)], "E0"); s.px(x + 74, y - 37, "E1")
    s.line([(x + 66, y - 44), (x + 66, y - 10)], "G0")                      # дверь
    s.line([(x + 34, y - 28), (x + 34, y - 10)], "G0"); s.line([(x + 98, y - 28), (x + 98, y - 10)], "G0")
    s.rect(x + 2, y - 14, x + 118, y - 13, "G0")
    s.rect(x + 114, y - 22, x + 119, y - 18, "E1" if not burnt else "G3")
    for _ in range(14 if not burnt else 30):                               # ржавчина
        px_, py_ = int(r.integers(x + 6, x + 114)), int(r.integers(y - 26, y - 9))
        s.rect(px_, py_, px_ + int(r.integers(1, 4)), py_ + 1, "R1" if not burnt else "G1")
    for wx in (x + 22, x + 96):
        s.ell(wx, y - 6, 9, 9 if not (flat and wx > x + 50) else 7, "G0")
        s.ell(wx, y - 6, 4, 4, "G4"); s.px(wx, y - 6, "G6")
        s.rect(wx - 12, y - 16, wx + 12, y - 15, "G1")
    s.rect(x - 2, y + 1, x + 122, y + 2, "G0")                               # тень


def tree(s, x, y, h, seed, bare=False):
    r = np.random.default_rng(seed)
    s.poly([(x - 3, y), (x + 3, y), (x + 2, y - h), (x - 1, y - h)], "B1")
    s.line([(x - 3, y), (x - 3, y - h)], "B0"); s.line([(x + 2, y), (x + 1, y - h)], "B2")
    for _ in range(4):
        by = y - int(r.integers(h // 2, h)); d = int(r.choice([-1, 1]))
        s.line([(x, by), (x + d * int(r.integers(10, 20)), by - int(r.integers(6, 14)))], "B1", 2)
    if bare:
        return
    for _ in range(int(h / 3)):
        cx = x + int(r.integers(-h // 3, h // 3)); cy = y - h + int(r.integers(-h // 4, h // 6))
        rx = int(r.integers(6, 13)); ry = int(r.integers(5, 9))
        s.ell(cx, cy, rx, ry, ["M1", "G4", "M0"][int(r.integers(0, 3))])
        s.ell(cx + 2, cy - 2, max(2, rx - 4), max(2, ry - 3), "M2")


def vines(s, x0, x1, ytop, ybot, seed, density=0.4):
    r = np.random.default_rng(seed)
    for x in range(x0, x1, 3):
        if r.random() < density:
            L = int(r.integers(10, ybot - ytop))
            s.line([(x, ytop), (x + int(r.integers(-2, 3)), ytop + L)], "M0")
            for yv in range(ytop, ytop + L, 3):
                if r.random() < 0.6:
                    s.px(x + int(r.integers(-1, 2)), yv, ["M1", "M2", "G5"][int(r.integers(0, 3))])


def grass(s, x0, x1, y, seed, hmax=8, dens=0.7):
    r = np.random.default_rng(seed)
    for x in range(x0, x1):
        if r.random() < dens:
            h = int(r.integers(2, hmax))
            s.line([(x, y), (x + int(r.integers(-1, 2)), y - h)], ["M1", "M2", "G5", "M0"][int(r.integers(0, 4))])


def sandbags(s, x0, x1, y, rows, seed):
    r = np.random.default_rng(seed)
    for j in range(rows):
        off = 0 if j % 2 else 6
        for x in range(x0 - off, x1, 12):
            cy = y - 4 - j * 7
            s.ell(x + 6, cy, 6, 4, "G0")
            s.ell(x + 6, cy, 5, 3, ["B2", "E0", "B1"][int(r.integers(0, 3))])
            s.rect(x + 3, cy - 3, x + 8, cy - 3, "E1")


def barrier(s, x, y, w=30):
    s.poly([(x, y), (x + 4, y - 8), (x + 8, y - 26), (x + w - 8, y - 26), (x + w - 4, y - 8), (x + w, y)], "E0",
           noise=value_noise(x, 2), amp=0.15)
    s.rect(x + 8, y - 26, x + w - 8, y - 26, "E1")
    for i in range(3):
        s.poly([(x + 6 + i * 8, y - 2), (x + 10 + i * 8, y - 2), (x + 14 + i * 8, y - 22), (x + 10 + i * 8, y - 22)], "R2")
    s.rect(x, y + 1, x + w, y + 1, "G0")


def barbed_wire(s, x0, x1, y):
    for x in range(x0, x1, 8):
        s.ell(x + 4, y, 5, 4, "G0")
        s.ell(x + 4, y, 4, 3, "G6")
        s.ell(x + 4, y, 3, 2, "G0")
    s.line([(x0, y), (x1, y)], "G6")


def ground_strip(s, y, seed):
    s.rect(0, y, W - 1, y + 2, "G3"); s.rect(0, y, W - 1, y, "G5")


# ================================================================ КАДР 1
def frame_surface():
    """День 3. Выход на поверхность: руины, пустая улица, рассвет."""
    s = Scene()
    sky(s, 0, 330, ["G1", "G2", "R1", "O0", "O1"])
    for i, (x0, x1, top) in enumerate([(30, 70, 140), (88, 120, 110), (150, 196, 150), (200, 236, 120)]):
        highrise(s, x0, x1, top, 340, 10 + i, tone="G2", win="G1")
    highrise(s, 20, 96, 170, 395, 21, tone="G4", win="G1", lit=0.0)
    highrise(s, 190, 270, 200, 395, 22, tone="G3", win="G1")
    s.rect(90, 300, 196, 395, "G3", noise=value_noise(3, 2), amp=0.1)        # дальний квартал
    for x in range(94, 194, 9):
        for y in range(306, 380, 12):
            s.rect(x, y, x + 4, y + 6, "G1")
    s.rect(40, 330, 76, 334, "G1"); s.line([(40, 330), (76, 320)], "G5")    # балкон обрушен
    road(s, GROUND, 4)
    # открытый люк убежища
    s.ell(78, GROUND + 14, 12, 3, "G0"); s.ell(78, GROUND + 13, 10, 2, "G0")
    s.poly([(52, GROUND + 18), (66, GROUND + 18), (64, GROUND + 14), (54, GROUND + 14)], "G5")
    car(s, 140, GROUND + 12, 5, body="R1")
    rubble(s, 40, 130, GROUND + 4, 6, 25, tones=("G3", "G4", "E0", "P1"))
    s.paste(hero_walk(), 100, GROUND + 10)
    s.add_light(170, 300, 200, 0.55, halo=False, ry=150)
    s.ambient = np.array([0.55, 0.6, 0.55], np.float32)
    return s


# ================================================================ КАДР 2
def frame_shop():
    """Заброшенный магазин: пустые полки, разбитая витрина."""
    s = Scene()
    s.rect(0, 0, W - 1, GROUND, "G3", noise=value_noise(31, 2) + value_noise(32, 30) * 0.5, amp=0.14)
    s.rect(0, 100, W - 1, 104, "G1")
    for x in range(0, W, 24):  # плитка потолка, провисшие панели
        s.rect(x, 104, x, 116, "G2")
    s.poly([(150, 104), (190, 104), (184, 130), (158, 122)], "E0")
    cable(s, 120, 104, 150, 140, 0); s.rect(140, 140, 168, 143, "G5"); s.rect(140, 144, 168, 145, "E1")
    # разбитая витрина слева — улица
    wx0, wx1, wy0, wy1 = 46, 104, 150, 330
    sky(s, wy0, wy1, ["G3", "G5", "E0"], emissive=False)
    ins = (XX > wx0) & (XX < wx1) & (YY > wy0) & (YY < wy1)
    out = ~ins & (YY <= wy1)
    s.rgb[out] = col("G3")
    s.rect(0, 0, W - 1, 100, "G1")
    s.emis |= ins
    m = Scene.mask(lambda d: d.polygon([(wx0, 330), (wx0, 260), (60, 250), (78, 270), (wx1, 240), (wx1, 330)], fill=255)) & ins
    s.rgb[m] = col("G1")
    s.poly([(wx0, 150), (70, 150), (58, 176), (wx0, 190)], "G5")                 # осколки стекла
    s.poly([(wx1, 150), (88, 150), (96, 172), (wx1, 196)], "G5")
    s.line([(70, 150), (58, 176), (wx0, 190)], "E1"); s.line([(88, 150), (96, 172), (wx1, 196)], "E1")
    for x0 in (wx0 - 5, wx1):
        s.rect(x0, wy0 - 5, x0 + 5, wy1 + 8, "G2"); s.rect(x0, wy0 - 5, x0, wy1 + 8, "G5")
    s.rect(wx0 - 5, wy0 - 6, wx1 + 5, wy0 - 1, "G2")
    s.rect(wx0 - 8, wy1 + 2, wx1 + 8, GROUND, "G2", noise=value_noise(5, 2), amp=0.15)
    s.add_light(75, 240, 120, 0.7, color=(0.7, 0.85, 0.8), halo=False, ry=150)
    # стеллажи
    for sx0, sx1 in ((120, 196), (204, 270)):
        for sy in (200, 245, 290, 335):
            s.rect(sx0, sy, sx1, sy + 2, "G5"); s.rect(sx0, sy, sx1, sy, "G7"); s.rect(sx0, sy + 3, sx1, sy + 3, "G0")
        s.rect(sx0, 170, sx0 + 2, GROUND, "G4"); s.rect(sx1 - 2, 170, sx1, GROUND, "G4")
    rr = np.random.default_rng(8)
    for sx0, sx1 in ((120, 196), (204, 270)):
        for sy in (200, 245, 290, 335):
            x = sx0 + 5
            while x < sx1 - 10:
                if rr.random() < 0.25:
                    h = int(rr.integers(8, 14))
                    s.rect(x, sy - h, x + 7, sy - 1, ["R2", "M2", "E0", "B2"][int(rr.integers(0, 4))])
                    s.rect(x, sy - h, x + 7, sy - h, "E1")
                    x += 10
                else:
                    x += 12
    s.poly([(204, 335), (262, 300), (270, 305), (214, 340)], "G4")               # упавшая полка
    # тележка
    s.rect(18, 352, 44, 372, "G0"); s.rect(20, 354, 42, 370, "G2")
    for gx in range(22, 42, 4):
        s.rect(gx, 354, gx, 370, "G6")
    s.line([(44, 352), (50, 344)], "G6"); s.ell(24, 388, 3, 3, "G0"); s.ell(40, 388, 3, 3, "G0")
    s.line([(22, 372), (24, 386)], "G6"); s.line([(40, 372), (40, 386)], "G6")
    # пол: плитка, мусор, пакеты
    s.rect(0, GROUND, W - 1, H - 1, "E0", noise=value_noise(7, 2), amp=0.15)
    for x in range(0, W, 12):
        s.rect(x, GROUND, x, H - 1, "G4")
    for y in range(GROUND, H, 12):
        s.rect(0, y, W - 1, y, "G4")
    rubble(s, 50, 230, GROUND + 6, 9, 40, tones=("E1", "G4", "R2", "B1", "E0"))
    s.paste(hero_stand(), 112, GROUND + 6)
    s.ambient = np.array([0.5, 0.58, 0.54], np.float32)
    return s


# ================================================================ КАДР 3
def frame_checkpoint():
    """Брошенный военный блокпост."""
    s = Scene()
    sky(s, 0, 340, ["G2", "G3", "G4", "E0"])
    for i, (x0, x1, top) in enumerate([(20, 60, 170), (70, 104, 140), (180, 230, 160)]):
        highrise(s, x0, x1, top, 340, 40 + i, tone="G3", win="G2")
    s.rect(0, 340, W - 1, GROUND, "G3")
    # вышка с прожектором
    s.line([(196, GROUND), (204, 250)], "G1", 3); s.line([(236, GROUND), (228, 250)], "G1", 3)
    s.line([(198, 330), (234, 290)], "G1"); s.line([(234, 330), (198, 290)], "G1")
    s.rect(192, 236, 240, 252, "M1"); s.rect(192, 236, 240, 236, "M2"); s.rect(196, 240, 236, 246, "G0")
    s.poly([(188, 236), (244, 236), (236, 226), (196, 226)], "G2")
    s.ell(206, 232, 4, 3, "G6"); s.ell(206, 232, 2, 2, "E0")
    # армейский грузовик слева
    s.rect(20, 316, 96, 372, "M1", noise=value_noise(2, 2), amp=0.15)
    for x in range(26, 96, 12):
        s.line([(x, 316), (x, 372)], "M0")
    s.rect(20, 316, 96, 318, "M2")
    s.rect(98, 336, 128, 380, "M1"); s.poly([(98, 336), (120, 336), (128, 352), (98, 352)], "G1")
    s.rect(14, 372, 130, 382, "G1")
    for wx in (36, 62, 112):
        s.ell(wx, 384, 10, 10, "G0"); s.ell(wx, 384, 4, 4, "G4")
    road(s, GROUND, 6)
    sandbags(s, 120, 200, GROUND + 6, 4, 3)
    barbed_wire(s, 120, 200, GROUND - 26)
    barrier(s, 196, GROUND + 6, 34); barrier(s, 232, GROUND + 6, 34)
    # шлагбаум сломан
    s.line([(140, GROUND - 40), (220, GROUND - 70)], "E0", 3)
    for i in range(5):
        s.line([(140 + i * 16, GROUND - 40 - i * 6), (148 + i * 16, GROUND - 43 - i * 6)], "R2", 3)
    s.rect(136, GROUND - 46, 142, GROUND + 6, "G2")
    # каска и автомат на мешках
    s.ell(160, GROUND - 26, 6, 4, "M1"); s.rect(154, GROUND - 26, 166, GROUND - 25, "M0")
    s.line([(172, GROUND - 24), (192, GROUND - 28)], "G0", 2); s.rect(180, GROUND - 26, 183, GROUND - 22, "G0")
    s.paste(hero_stand(pipe=True), 92, GROUND + 10)
    s.ambient = np.array([0.6, 0.66, 0.6], np.float32)
    return s


# ================================================================ КАДР 4
def frame_forest():
    """Лес поглощает город: деревья сквозь асфальт, лианы на фасадах."""
    s = Scene()
    sky(s, 0, 300, ["G3", "G5", "G6", "E0"])
    highrise(s, 60, 110, 130, 360, 51, tone="G3", win="G1")
    highrise(s, 150, 210, 160, 360, 52, tone="G3", win="G1")
    vines(s, 60, 110, 150, 360, 1, 0.5); vines(s, 150, 210, 180, 360, 2, 0.5)
    highrise(s, 0, 70, 200, GROUND, 53, tone="G4", win="G1", ruined=False)
    vines(s, 0, 72, 200, GROUND, 3, 0.8)
    s.rect(196, 230, 270, GROUND, "G4", noise=value_noise(9, 2), amp=0.12)
    for x in range(200, 268, 10):
        for y in range(240, 380, 14):
            s.rect(x, y, x + 5, y + 8, "G1")
    vines(s, 196, 270, 230, GROUND, 4, 0.7)
    tree(s, 160, GROUND + 4, 120, 7)
    tree(s, 90, GROUND - 10, 70, 8)
    road(s, GROUND, 9)
    m = YY > GROUND + 4
    s.blend(m & (value_noise(11, 6) > 0.0), "M1", 0.7)                   # мох по асфальту
    car(s, 120, GROUND + 18, 12, body="G4")
    vines(s, 126, 236, GROUND - 26, GROUND + 6, 5, 0.6)
    grass(s, 0, W, GROUND + 18, 3, 10, 0.8)
    grass(s, 0, W, H - 30, 4, 14, 0.9)
    for (bx, by) in ((70, 160), (78, 156), (180, 140)):                    # птицы
        s.line([(bx - 2, by + 1), (bx, by), (bx + 2, by + 1)], "G0")
    for i in range(3):                                                    # солнечные лучи
        m = Scene.mask(lambda d, i=i: d.polygon([(130 + i * 30, 110), (140 + i * 30, 110), (110 + i * 30, 430), (90 + i * 30, 430)], fill=255))
        s.blend(m, "E0", 0.12)
    s.paste(hero_walk(), 104, GROUND + 18)
    s.add_light(150, 120, 220, 0.4, color=(0.9, 0.95, 0.75), halo=False, ry=260)
    s.ambient = np.array([0.6, 0.68, 0.58], np.float32)
    return s


# ================================================================ КАДР 5
def frame_night_road():
    """Ночь. Обрушенная эстакада, горящая машина, заражённые на дороге — герой прячется."""
    s = Scene()
    sky(s, 0, 330, ["G0", "G1", "G2"])
    s.ell(196, 150, 7, 7, "E1", emissive=True); s.ell(198, 148, 6, 6, "E2", emissive=True)
    for i, (x0, x1, top) in enumerate([(10, 50, 180), (60, 94, 150), (200, 250, 170)]):
        highrise(s, x0, x1, top, 340, 60 + i, tone="G1", win="G0", lit=0.03)
    # эстакада с обрушенным пролётом
    s.rect(0, 280, 110, 292, "G3"); s.rect(0, 280, 110, 280, "G5"); s.rect(0, 293, 110, 296, "G1")
    s.poly([(110, 280), (124, 286), (130, 330), (118, 334), (108, 296)], "G3")
    s.rect(170, 280, 270, 292, "G3"); s.rect(170, 280, 270, 280, "G5"); s.rect(170, 293, 270, 296, "G1")
    s.poly([(170, 280), (160, 300), (164, 302), (172, 292)], "G3")
    for x in (112, 118, 165):
        s.line([(x, 290), (x + 3, 300)], "G5")
    for x in (40, 220):
        s.rect(x, 296, x + 12, GROUND, "G2"); s.rect(x, 296, x, GROUND, "G4")
    rubble(s, 110, 170, GROUND, 13, 40, tones=("G3", "G2", "G4", "E0"))
    road(s, GROUND, 14)
    # горящая машина между героем и заражёнными
    car(s, 96, GROUND + 14, 15, burnt=True)
    r = np.random.default_rng(3)
    for j in range(70):
        x = 116 + j
        h = int(18 * (0.5 + 0.5 * math.sin(j * 0.6)) * (1 - abs(j - 35) / 40) + r.integers(0, 6))
        s.rect(x, GROUND - 30 - h, x, GROUND - 30, "O1", emissive=True)
        s.rect(x, GROUND - 30 - h // 2, x, GROUND - 30, "O2", emissive=True)
        s.rect(x, GROUND - 30 - h // 5, x, GROUND - 30, "O3", emissive=True)
    for y in range(160, GROUND - 40, 2):
        w = 6 + (GROUND - y) * 0.06
        m = ((XX - 152 - math.sin(y * 0.06) * 6) / w) ** 2 + ((YY - y) / 3) ** 2 <= 1
        s.blend(m, "G1", 0.6)
    s.add_light(152, GROUND - 40, 130, 1.2)
    # герой прячется за машиной, заражённые бредут с той стороны
    s.paste(hero_crouch(), 92, GROUND + 14)
    s.paste(zombie(), 226, GROUND + 10, flip=True)
    s.paste(zombie(), 262, GROUND + 4, flip=True, dark=0.25)
    s.ambient = np.array([0.3, 0.38, 0.4], np.float32)
    return s


FRAMES = [
    ("01_vyhod_na_poverhnost.png", frame_surface, CAM),
    ("02_zabroshennyi_magazin.png", frame_shop, CAM),
    ("03_blokpost.png", frame_checkpoint, CAM),
    ("04_les_v_gorode.png", frame_forest, CAM),
    ("05_noch_zarazhennye.png", frame_night_road, (64, 110)),
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
