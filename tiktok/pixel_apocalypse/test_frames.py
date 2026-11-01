#!/usr/bin/env python3
"""Тестовые кадры PIXEL APOCALYPSE по сценарию «72 ЧАСА» (серия 1).

python3 tiktok/pixel_apocalypse/test_frames.py  →  frames/*.png (1080x1920)
"""
import os

import numpy as np
from PIL import Image

from pixel import (BT, H, P, W, XX, YY, Canvas, infected, rng, survivor_back,
                   survivor_crouch, survivor_sit)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------ общие элементы
def wall(c, y0, y1, base=("K2", "K1"), seed=0, paper=True):
    c.vgrad(0, y0, W - 1, y1, list(base))
    r = rng(seed)
    if paper:  # выцветшие обои — вертикальные полосы
        for x in range(4, W, 12):
            c.dither((XX == x) & (YY >= y0) & (YY <= y1), "K1", 0.6)
        for _ in range(6):  # отслоившиеся куски
            x, y = r.integers(0, W - 20), r.integers(y0, y1 - 30)
            w, h = r.integers(6, 18), r.integers(8, 26)
            c.rect(x, y, x + w, y + h, "N1")
            c.rect(x, y + h, x + w, y + h, "K0")
    for _ in range(4):  # трещины
        x, y = int(r.integers(0, W)), int(r.integers(y0, y1 - 40))
        pts = [(x, y)]
        for _ in range(5):
            x += int(r.integers(-4, 5)); y += int(r.integers(4, 9)); pts.append((x, y))
        c.line(pts, "K0")


def floor_planks(c, y0, seed=1, cols=("B1", "B0")):
    c.vgrad(0, y0, W - 1, H - 1, list(cols))
    r = rng(seed)
    y, step = y0, 5
    while y < H:
        c.rect(0, y, W - 1, y, "K0")
        for x in range(int(r.integers(0, 30)), W, int(r.integers(30, 60))):
            c.rect(x, y, x, y + step, "K0")
        y += step; step += 2


def debris(c, x0, x1, y0, y1, n, seed, cols=("K3", "K4", "B2", "K2")):
    r = rng(seed)
    for _ in range(n):
        x, y = int(r.integers(x0, x1)), int(r.integers(y0, y1))
        w, h = int(r.integers(1, 5)), int(r.integers(1, 3))
        c.rect(x, y, x + w, y + h, cols[int(r.integers(0, len(cols)))])


def city_skyline(c, x0, x1, base, seed, fires=True, col="K1"):
    r = rng(seed)
    x = x0
    while x < x1:
        w = int(r.integers(10, 26)); h = int(r.integers(30, 110))
        top = base - h
        pts = [(x, base), (x, top + int(r.integers(0, 8)))]
        if r.random() < 0.6:  # обрушенный верх
            for k in range(1, 4):
                pts.append((x + w * k / 4, top + int(r.integers(0, 22))))
        pts += [(x + w, top + int(r.integers(0, 10))), (x + w, base)]
        c.poly(pts, col)
        for wy in range(top + 6, base - 4, 6):
            for wx in range(x + 2, x + w - 2, 4):
                v = r.random()
                if fires and v < 0.05:
                    c.rect(wx, wy, wx + 1, wy + 2, "O2")
                elif v < 0.25:
                    c.rect(wx, wy, wx + 1, wy + 2, "K0")
        x += w + int(r.integers(-2, 3))


def smoke(c, cx, base, top, width, seed, cols=("K2", "K3")):
    r = rng(seed)
    for y in range(top, base, 3):
        k = (y - top) / max(1, base - top)
        w = width * (1.6 - k) + r.integers(-3, 4)
        x = cx + np.sin(y * 0.07 + seed) * 8 * (1 - k)
        m = ((XX - x) / (w + 0.5)) ** 2 + ((YY - y) / 4.5) ** 2 <= 1
        c.dither(m, cols[0], 0.7)
        c.dither(m & (XX < x - w * 0.2), cols[1], 0.3)


def fire(c, x, y, w, h, seed):
    r = rng(seed)
    for i in range(w):
        fh = int(h * (0.4 + 0.6 * r.random()) * (1 - abs(i - w / 2) / (w / 1.6)))
        if fh <= 0:
            continue
        c.rect(x + i, y - fh, x + i, y, "O1")
        c.rect(x + i, y - int(fh * 0.6), x + i, y, "O2")
        c.rect(x + i, y - int(fh * 0.3), x + i, y, "O3")
    c.rect(x + w // 2 - 1, y - 2, x + w // 2 + 1, y, "O4")


# ===================================================================== КАДР 1
def frame1():
    """«Ты проснулся, а цивилизация рухнула.» — комната, окно на горящий город."""
    c = Canvas("K0")
    wall(c, 0, 300, seed=11)
    # окно
    wx0, wy0, wx1, wy1 = 40, 58, 176, 232
    inside = (XX > wx0) & (XX < wx1) & (YY > wy0) & (YY < wy1)
    c.vgrad(wx0, wy0, wx1, wy1, ["R0", "R1", "R2", "O0", "O1", "O2"], where=inside)
    sm = Canvas(transparent=True)
    for i, (cx, top) in enumerate([(70, 70), (128, 60), (160, 100)]):
        smoke(sm, cx, 200, top, 12 + i * 3, 30 + i)
    sm.a[~inside] = -1
    c.paste(sm, outline=None)
    sky = Canvas(transparent=True)
    city_skyline(sky, wx0, wx1, 232, 5, col="K2")
    sky.shade(0.0)
    sky.a[~inside] = -1
    c.paste(sky, outline=None)
    front = Canvas(transparent=True)
    city_skyline(front, wx0 - 10, wx1 + 10, 236, 9, col="K1")
    front.a[~inside] = -1
    c.paste(front, outline=None)
    for fx, fy in [(60, 231), (102, 231), (148, 231)]:
        fire(c, fx, fy, 14, 18, fx)
    c.light(100, 232, 90, 1.4, warm=True, where=inside, ry=40)
    # рама, разбитое стекло, занавески
    c.rect(wx0 - 6, wy0 - 6, wx1 + 6, wy0, "B1"); c.rect(wx0 - 6, wy1, wx1 + 6, wy1 + 6, "B1")
    c.rect(wx0 - 6, wy0 - 6, wx0, wy1 + 6, "B1"); c.rect(wx1, wy0 - 6, wx1 + 6, wy1 + 6, "B1")
    c.rect(107, wy0, 109, wy1, "B1"); c.rect(wx0, 144, wx1, 146, "B1")
    c.rect(wx0 - 8, wy1 + 4, wx1 + 8, wy1 + 9, "B2")  # подоконник
    c.line([(150, 59), (160, 80), (156, 96), (170, 110)], "K5")
    c.line([(160, 80), (175, 78)], "K5")
    c.poly([(150, 59), (175, 59), (175, 76), (160, 80)], "K0")  # дыра
    for side, (x0, x1) in enumerate([(26, 52), (164, 190)]):
        pts = [(x0, 48), (x1, 48), (x1 - (6 if side == 0 else 0), 250), (x0 + (0 if side == 0 else 6), 262)]
        c.poly(pts, "N1")
        for fx in range(x0 + 3, x1 - 2, 5):
            c.line([(fx, 50), (fx + (1 if side else -1), 258)], "N0")
    c.rect(20, 44, 196, 47, "K3")
    # пол, кровать, мусор
    floor_planks(c, 300, 3)
    patch = Canvas._mask(lambda d: d.polygon([(48, 300), (172, 300), (210, 384), (16, 384)], fill=255))
    c.dither(patch, "B2", np.clip(1 - (YY - 300) / 100, 0, 1) * 0.8)
    c.rect(0, 268, 58, 300, "B1"); c.rect(0, 258, 52, 270, "K4")
    c.poly([(0, 255), (46, 252), (56, 262), (52, 272), (0, 274)], "N1")
    c.rect(4, 246, 22, 254, "K5")
    debris(c, 60, 210, 304, 380, 40, 7)
    c.rect(170, 330, 186, 342, "B3"); c.rect(172, 332, 184, 340, "K1")  # упавшая рамка
    c.line([(173, 333), (183, 339)], "K4")
    c.rect(32, 340, 36, 352, "N3"); c.rect(33, 337, 35, 340, "N4")  # бутылка
    # герой
    c.paste(survivor_back(108, 352))
    c.light(108, 232, 130, 1.6, warm=True, where=YY > 232)
    c.light(108, 150, 70, 0.8, warm=True)
    c.vignette(2.4)
    return c


# ===================================================================== КАДР 2
def frame2():
    """«Тебе нужны вода, консервы, аптечка, фонарь и запасные батарейки.» — стол в убежище."""
    c = Canvas("K0")
    c.vgrad(0, 0, W - 1, 230, ["K2", "K1"])
    for y in range(6, 230, 14):  # бетонные блоки
        c.rect(0, y, W - 1, y, "K0")
        off = 0 if (y // 14) % 2 else 14
        for x in range(off, W, 28):
            c.rect(x, y, x, y + 13, "K0")
    c.dither((YY < 230) & (XX < 40), "N1", 0.25)  # плесень
    # полка с банками
    c.rect(14, 92, 202, 96, "B2"); c.rect(14, 97, 202, 98, "B0")
    r = rng(4)
    x = 20
    while x < 196:
        w = int(r.integers(9, 15)); h = int(r.integers(14, 26))
        col = ["K4", "N3", "B3", "K3"][int(r.integers(0, 4))]
        c.rect(x, 91 - h, x + w, 91, col)
        c.rect(x, 91 - h + 4, x + w, 91 - h + 8, ["R1", "N2", "B2"][int(r.integers(0, 3))])
        c.rect(x, 91 - h, x + w, 91 - h, "K5")
        x += w + 3
    # стол
    c.poly([(0, 232), (W - 1, 232), (W - 1, 384), (0, 384)], "B2")
    for y in range(240, 384, 18):
        c.rect(0, y, W - 1, y, "B1")
    c.rect(0, 226, W - 1, 232, "B3")
    # вода — две канистры
    for jx in (22, 52):
        c.rect(jx, 168, jx + 24, 228, "N3"); c.rect(jx + 2, 172, jx + 22, 226, "N4")
        c.rect(jx + 2, 196, jx + 22, 226, "N3")  # уровень воды
        c.rect(jx + 8, 160, jx + 16, 168, "K3"); c.rect(jx + 3, 174, jx + 5, 220, "N5")
    # консервы
    for i, (cx, cy) in enumerate([(88, 228), (101, 228), (94, 214)]):
        c.rect(cx - 6, cy - 14, cx + 6, cy, "K4"); c.rect(cx - 6, cy - 10, cx + 6, cy - 4, "R1")
        c.rect(cx - 6, cy - 14, cx + 6, cy - 14, "K5")
    # аптечка
    c.rect(116, 196, 152, 228, "K5"); c.rect(116, 196, 152, 199, "K6")
    c.rect(131, 203, 137, 223, "R2"); c.rect(124, 210, 144, 216, "R2")
    c.rect(128, 191, 140, 196, "K3")
    # фонарь и луч
    cone = Canvas._mask(lambda d: d.polygon([(180, 212), (216, 186), (216, 240), (180, 218)], fill=255))
    c.dither(cone, "O1", np.clip(1.1 - (XX - 180) / 40, 0, 1) * 0.6)
    c.dither(cone, "O3", np.clip(0.6 - (XX - 180) / 40, 0, 1) * 0.6)
    c.rect(160, 210, 176, 220, "K1"); c.rect(176, 208, 180, 222, "K3"); c.rect(180, 210, 181, 220, "O4")
    # батарейки
    for bx in (150, 158, 166):
        c.rect(bx, 248, bx + 5, 268, "K1"); c.rect(bx, 248, bx + 5, 253, "O1"); c.rect(bx + 2, 246, bx + 3, 247, "K5")
    # телефон с офлайн-картой
    c.rect(36, 262, 80, 330, "K0"); c.rect(39, 266, 77, 326, "N1")
    for gy in range(270, 326, 7):
        c.rect(39, gy, 77, gy, "N2")
    for gx in range(44, 77, 8):
        c.rect(gx, 266, gx, 326, "N2")
    c.line([(40, 316), (55, 300), (60, 285), (76, 272)], "N4", 2)
    c.rect(57, 290, 60, 294, "R3")
    # свеча
    c.rect(100, 262, 108, 290, "K5"); c.rect(103, 256, 105, 261, "O3"); c.px(104, 255, "O4")
    c.rect(96, 288, 112, 292, "K3")
    # рюкзак героя
    c.poly([(128, 300), (190, 296), (200, 384), (120, 384)], "B2")
    c.rect(132, 300, 188, 316, "B3"); c.rect(156, 316, 162, 330, "K4")
    c.poly([(140, 296), (176, 294), (170, 286), (146, 288)], "N2")  # спальник
    c.rect(188, 330, 192, 384, "R2")  # шарф свисает
    debris(c, 0, 120, 340, 384, 18, 9, cols=("B1", "B3", "K3"))
    c.light(104, 258, 95, 1.8, warm=True)
    c.light(196, 214, 40, 1.4, warm=True)
    c.light(58, 296, 26, 0.9, warm=False)
    c.vignette(2.0)
    return c


# ===================================================================== КАДР 3
def frame3():
    """«Стук в дверь. — Эй! Открой!» — тёмный коридор, тени ног за дверью."""
    c = Canvas("K0")
    wall(c, 0, 318, base=("K1", "K2", "K1"), seed=21)
    dx0, dy0, dx1, dy1 = 66, 110, 150, 318
    c.rect(dx0 - 8, dy0 - 8, dx1 + 8, dy1, "B0")
    c.rect(dx0, dy0, dx1, dy1, "B2")
    for (a, b, cc, d) in [(74, 120, 142, 196), (74, 206, 142, 308)]:
        c.rect(a, b, cc, d, "B1"); c.rect(a + 2, b + 2, cc - 2, d - 2, "B2")
    c.ell(136, 214, 3, 3, "K5"); c.rect(134, 218, 138, 222, "K4")
    c.ell(108, 150, 2, 2, "K0")
    # замки и цепочка
    c.rect(140, 170, 146, 176, "K4"); c.line([(146, 173), (156, 178), (160, 175)], "K5")
    # полоска света под дверью и тени ног
    c.rect(dx0, dy1 - 1, dx1, dy1 + 1, "O3")
    c.poly([(dx0, dy1 + 2), (dx1, dy1 + 2), (dx1 + 34, H - 1), (dx0 - 34, H - 1)], "B1")
    c.dither((YY > dy1) & (XX > dx0 - 40) & (XX < dx1 + 40), "O0", 0.35)
    for fx in (90, 114):
        c.rect(fx, dy1 - 1, fx + 9, dy1 + 1, "K0")
        c.poly([(fx, dy1 + 2), (fx + 9, dy1 + 2), (fx + 14, H - 1), (fx - 4, H - 1)], "K0")
    floor_planks(c, 319, 5, cols=("B0", "K0"))
    c.poly([(dx0, dy1 + 2), (dx1, dy1 + 2), (dx1 + 34, H - 1), (dx0 - 34, H - 1)], "B1")
    c.dither((YY > dy1) & (XX > dx0 - 40) & (XX < dx1 + 40), "O0", 0.35)
    for fx in (90, 114):
        c.poly([(fx, dy1 + 2), (fx + 9, dy1 + 2), (fx + 16, H - 1), (fx - 6, H - 1)], "K0")
    # стул подпирает ручку
    c.line([(152, 218), (182, 300)], "B3", 3); c.line([(170, 230), (190, 300)], "B3", 3)
    c.rect(150, 214, 172, 218, "B3")
    # вешалка, картина, мусор
    c.rect(10, 120, 34, 122, "B3")
    c.poly([(14, 122), (30, 122), (32, 190), (12, 192)], "K2")
    c.rect(176, 90, 204, 126, "B2"); c.rect(179, 93, 201, 123, "N1"); c.line([(180, 120), (190, 104), (200, 112)], "N2")
    debris(c, 0, W, 330, 384, 24, 13)
    # герой присел слева, с трубой
    c.paste(survivor_crouch(34, 364))
    c.light(108, 322, 80, 2.0, warm=True, ry=55)
    c.light(108, 318, 40, 1.0, warm=True)
    c.shade(1.0, where=YY < 100)
    c.vignette(2.6)
    return c


# ===================================================================== КАДР 4
def frame4():
    """«Наступает вторая ночь. Ты сидишь в темноте и слушаешь радио.»"""
    c = Canvas("K0")
    wall(c, 0, 300, base=("K1", "K2", "K1"), seed=31)
    # заколоченное окно с лунными щелями
    wx0, wy0, wx1, wy1 = 108, 64, 196, 178
    c.rect(wx0, wy0, wx1, wy1, "K0")
    c.vgrad(wx0, wy0, wx1, wy1, ["K0", "K1"], where=(XX > wx0) & (XX < wx1))
    c.ell(176, 84, 6, 6, "K6"); c.ell(178, 82, 5, 5, "K5")
    planks = [(70, -4), (92, 3), (116, -2), (142, 5), (164, -3)]
    for py, tilt in planks:
        c.poly([(wx0 - 6, py), (wx1 + 6, py + tilt), (wx1 + 6, py + tilt + 14), (wx0 - 6, py + 14)], "B2")
        c.line([(wx0 - 6, py + 3), (wx1 + 6, py + tilt + 3)], "B3")
        c.px(wx0 - 2, py + 7, "K5"); c.px(wx1 + 2, py + tilt + 7, "K5")
    c.rect(wx0 - 8, wy0 - 6, wx1 + 8, wy0 - 2, "B1")
    floor_planks(c, 300, 7, cols=("B1", "B0"))
    # лунный свет из щелей ложится полосами на пол
    for i, gy in enumerate((84, 106, 132, 156)):
        m = Canvas._mask(lambda d, i=i: d.polygon([(104 - i * 22, 304), (116 - i * 22, 304),
                                                   (86 - i * 26, 384), (72 - i * 26, 384)], fill=255))
        c.moon(m, 0.7)
        c.dither((XX > 108) & (XX < 196) & (YY >= gy - 1) & (YY <= gy), "K3", 0.5)
    # спальник, винтовка, консервы
    c.poly([(140, 330), (212, 322), (216, 372), (132, 380)], "N1")
    c.line([(140, 340), (212, 332)], "N0"); c.line([(136, 360), (214, 352)], "N0")
    c.line([(18, 300), (34, 210)], "K1", 3); c.line([(30, 230), (32, 224)], "B3", 4)
    c.rect(26, 250, 30, 262, "B2")
    c.rect(150, 300, 158, 312, "K4"); c.rect(150, 304, 158, 308, "R1")
    # герой сидит у стены
    c.paste(survivor_sit(50, 338))
    # радио
    c.rect(86, 310, 124, 336, "B2"); c.rect(86, 310, 124, 312, "B3")
    for gx in range(89, 102, 3):
        for gy in range(316, 334, 3):
            c.px(gx, gy, "B0")
    c.rect(104, 316, 121, 323, "O2"); c.rect(112, 316, 112, 323, "R3")
    c.ell(108, 330, 2, 2, "K4"); c.ell(117, 330, 2, 2, "K4")
    c.line([(120, 310), (138, 270)], "K4")
    # огарок свечи
    c.rect(130, 330, 134, 338, "K5"); c.px(132, 328, "O3"); c.px(132, 327, "O4")
    c.light(112, 320, 60, 1.9, warm=True)
    c.light(132, 328, 30, 1.2, warm=True)
    c.vignette(2.4)
    return c


# ===================================================================== КАДР 5
def frame5():
    """«НЕ СМОТРИ В ОКНО» … «за твоей спиной раздаётся скрип пола»."""
    c = Canvas("K0")
    wall(c, 0, 304, base=("K1", "K2", "K1"), seed=41)
    # окно на ночную улицу
    wx0, wy0, wx1, wy1 = 96, 60, 204, 236
    ins = (XX > wx0) & (XX < wx1) & (YY > wy0) & (YY < wy1)
    c.vgrad(wx0, wy0, wx1, wy1, ["K0", "N0", "K1"], where=ins)
    st = Canvas(transparent=True)
    city_skyline(st, wx0 - 4, wx1 + 4, 206, 17, fires=False, col="K0")
    st.rect(wx0, 206, wx1, wy1, "K1")
    st.rect(wx0, 214, wx1, 215, "K2")
    st.rect(124, 226, 160, 236, "K2"); st.rect(130, 220, 152, 226, "K2")  # брошенная машина
    st.rect(132, 222, 140, 225, "K0"); st.ell(130, 236, 3, 3, "K0"); st.ell(154, 236, 3, 3, "K0")
    st.line([(184, 236), (184, 160)], "K3", 2); st.line([(184, 160), (176, 156)], "K3", 2)
    st.rect(172, 156, 178, 159, "O3")
    st.a[~ins] = -1
    c.paste(st, outline=None)
    cone = Canvas._mask(lambda d: d.polygon([(172, 160), (178, 160), (198, 236), (150, 236)], fill=255)) & ins
    c.dither(cone, "O0", np.clip((236 - YY) / 90, 0, 1) * 0.5)
    c.light(175, 160, 14, 1.2, warm=True, where=ins)
    c.rect(wx0 - 6, wy0 - 6, wx1 + 6, wy0, "B1"); c.rect(wx0 - 6, wy1, wx1 + 6, wy1 + 6, "B1")
    c.rect(wx0 - 6, wy0, wx0, wy1, "B1"); c.rect(wx1, wy0, wx1 + 6, wy1, "B1")
    c.rect(149, wy0, 151, wy1, "B1"); c.rect(wx0, 146, wx1, 148, "B1")
    c.rect(wx0 - 8, wy1 + 4, wx1 + 8, wy1 + 9, "B2")
    # дверной проём слева, из темноты выходит заражённый
    c.rect(4, 120, 62, 304, "K0")
    c.rect(0, 114, 4, 304, "B1"); c.rect(62, 114, 68, 304, "B1"); c.rect(0, 112, 68, 116, "B1")
    zm = infected(38, 304)
    zm.shade(2.6)
    eyes = [(int(38 - 6 * 1.6), int(304 - 53 * 1.6)), (int(38 - 1 * 1.6), int(304 - 53 * 1.6))]
    for x, y in eyes:  # глаза остаются видны
        zm.a[y, x:x + 2] = P["R3"]
    c.paste(zm, outline=None)
    for x, y in eyes:
        c.dither((abs(XX - x) <= 2) & (abs(YY - y) <= 1) & (c.a == P["K0"]), "R0", 0.6)
    floor_planks(c, 305, 9, cols=("B1", "B0"))
    c.rect(54, 318, 82, 319, "K3")  # скрипнувшая доска
    c.line([(60, 314), (62, 310)], "K4"); c.line([(70, 312), (73, 308)], "K4")
    debris(c, 70, W, 312, 384, 22, 21)
    # герой у окна, спиной
    c.paste(survivor_back(150, 344))
    c.light(150, 250, 80, 1.4, warm=False, where=(YY > 236), ry=110)
    c.vignette(2.6)
    return c


FRAMES = [
    ("01_probuzhdenie.png", frame1),
    ("02_pripasy.png", frame2),
    ("03_stuk_v_dver.png", frame3),
    ("04_vtoraya_noch_radio.png", frame4),
    ("05_ne_smotri_v_okno.png", frame5),
]

if __name__ == "__main__":
    small = []
    for name, fn in FRAMES:
        img = fn().save(os.path.join(OUT, name))
        small.append(img)
        print("✓", name)
    sheet = Image.new("RGB", (W * len(small) * 2 + 8 * (len(small) - 1), H * 2), (0, 0, 0))
    for i, im in enumerate(small):
        sheet.paste(im.resize((W * 2, H * 2), Image.NEAREST), (i * (W * 2 + 8), 0))
    sheet.save(os.path.join(OUT, "contact_sheet.png"))
