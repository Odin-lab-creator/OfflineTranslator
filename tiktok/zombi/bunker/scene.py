"""Мир «Бункера»: разрез земли сбоку, рисуется кодом в пикселях 270×480 и увеличивается ×4 → 1080×1920.
world(n, p, t) — кадр сцены n (1…20), p — прогресс внутри сцены 0…1, t — общее время (для анимации)."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

BW, BH, K = 270, 480, 4
GY = 150                                    # линия земли
NIGHT = {2, 6, 11, 18, 19, 20}
EVENING = {1}

# --- комнаты (x0, y0, x1, y1) ---
CELLAR = (92, 156, 140, 182)
SHAFT1 = (110, 182, 122, 200)
ROOM1 = (56, 200, 192, 232)
SHAFT2 = (166, 232, 178, 262)
ROOM2 = (80, 262, 200, 294)
EXT2 = (200, 266, 214, 294)                # прокоп к бетону
ANYA = (218, 256, 270, 298)                 # чужой бункер (бетон)
HATCH_X = 110
ROCK_Y = 304

SKIN, HOOD, HOOD2, JEANS, BOOT = (238, 194, 150), (52, 112, 196), (36, 80, 150), (66, 62, 70), (44, 32, 26)
CAP = (232, 120, 34)
ANYA_C = dict(skin=(236, 190, 150), top=(64, 124, 82), top2=(44, 92, 60), legs=(70, 70, 78), hair=(34, 26, 24))
OUT = (22, 18, 16)


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# ---------- люди ----------
def person(kind, pose, phase, facing=1):
    """Человечек 24×24 RGBA с обводкой. kind: hero / anya / zombie. pose: stand walk dig sit up pedal crouch."""
    facing = 1                               # рисуем лицом вправо, отражение — снаружи
    im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fx = 12                                  # ось
    feet = 22
    if kind == "zombie":
        skin, top, top2, legs, hair = (136, 172, 104), (96, 84, 76), (74, 64, 58), (64, 70, 60), (60, 70, 46)
    elif kind == "anya":
        skin, top, top2, legs, hair = ANYA_C["skin"], ANYA_C["top"], ANYA_C["top2"], ANYA_C["legs"], ANYA_C["hair"]
    else:
        skin, top, top2, legs, hair = SKIN, HOOD, HOOD2, JEANS, HOOD
    sit = pose in ("sit", "pedal")
    crouch = pose == "crouch"
    # ноги
    if sit:
        hip = feet - 6
        if pose == "pedal":
            a = phase * 2 * math.pi
            for s in (0, math.pi):
                kx, ky = fx + 3 + 2 * math.cos(a + s), feet - 2 + 2 * math.sin(a + s)
                d.line([(fx, hip), (fx + 3, hip - 1), (kx, ky)], fill=legs, width=2)
        else:
            d.rectangle([fx - 2, hip - 1, fx + 4, hip + 1], fill=legs)
            d.rectangle([fx + 3, hip, fx + 4, feet], fill=legs)
            d.rectangle([fx + 3, feet - 1, fx + 5, feet], fill=BOOT)
        top_y = hip - 7
    else:
        hip = feet - 5 + (2 if crouch else 0)
        sw = int(round(2 * math.sin(phase * 2 * math.pi))) if pose == "walk" else 0
        d.rectangle([fx - 2 + sw, hip, fx - 1 + sw, feet], fill=legs)
        d.rectangle([fx + 1 - sw, hip, fx + 2 - sw, feet], fill=legs)
        d.rectangle([fx - 2 + sw, feet - 1, fx - 1 + sw + facing, feet], fill=BOOT if kind != "zombie" else (50, 44, 40))
        d.rectangle([fx + 1 - sw, feet - 1, fx + 2 - sw + facing, feet], fill=BOOT if kind != "zombie" else (50, 44, 40))
        top_y = hip - 7
    lean = 1 if kind == "zombie" else 0
    # тело
    d.rectangle([fx - 3, top_y, fx + 3, hip], fill=top)
    d.rectangle([fx - 3, top_y, fx - 2, hip], fill=top2)
    if kind == "zombie":                     # рваная одежда
        d.point([(fx + 1, hip - 2), (fx - 1, top_y + 3)], fill=(150, 60, 50))
    # голова
    hx = fx + lean * facing
    hy = top_y - 6
    d.rectangle([hx - 3, hy, hx + 3, hy + 5], fill=skin)
    if kind == "hero":                       # оранжевая шапка
        d.rectangle([hx - 3, hy - 2, hx + 3, hy + 1], fill=CAP)
        d.rectangle([hx - 3, hy + 1, hx + 3, hy + 1], fill=(196, 92, 24))
        d.rectangle([hx - 3, hy + 2, hx - 2, hy + 4], fill=(70, 46, 30))
    elif kind == "anya":
        d.rectangle([hx - 3, hy - 1, hx + 3, hy + 1], fill=hair)
        d.rectangle([hx - 3 * facing - facing, hy, hx - 2 * facing, hy + 4], fill=hair)
        d.rectangle([hx - 5 * facing, hy + 1, hx - 4 * facing, hy + 6], fill=hair)   # хвост
    else:
        d.rectangle([hx - 3, hy - 1, hx + 2, hy], fill=hair)
    ex = hx + 1 * facing + (1 if facing > 0 else -1)
    d.point([(ex, hy + 2)], fill=(200, 30, 30) if kind == "zombie" else (20, 16, 16))
    # руки
    sh = (fx + facing, top_y + 2)
    if kind == "zombie" and not crouch:
        d.line([sh, (fx + 7 * facing, top_y + 2)], fill=skin, width=2)
    elif crouch:
        y = top_y - 6 + int(2 * math.sin(phase * 2 * math.pi * 2))
        d.line([sh, (fx + 4 * facing, y)], fill=skin, width=2)
    elif pose == "dig":
        a = 0.5 + 0.9 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi))
        hx2, hy2 = sh[0] + 5 * facing * math.cos(a), sh[1] + 5 * math.sin(a)
        d.line([sh, (hx2, hy2)], fill=top, width=2)
        ex2, ey2 = hx2 + 6 * facing * math.cos(a + 0.6), hy2 + 6 * math.sin(a + 0.6)
        d.line([(hx2 - 3 * facing * math.cos(a + 0.6), hy2 - 3 * math.sin(a + 0.6)), (ex2, ey2)], fill=(130, 90, 50), width=1)
        d.rectangle([ex2 - 1, ey2 - 1, ex2 + 1, ey2 + 1], fill=(170, 176, 184))
    elif pose == "up":
        d.line([sh, (fx + 2 * facing, top_y - 8)], fill=top, width=2)
        d.line([(fx - facing, top_y + 2), (fx - 1 * facing, top_y - 8)], fill=top, width=2)
    elif pose == "knife":
        d.line([sh, (fx + 5 * facing, top_y + 3)], fill=top, width=2)
        d.line([(fx + 5 * facing, top_y + 2), (fx + 8 * facing, top_y)], fill=(200, 205, 212), width=1)
    elif sit or pose == "pedal":
        d.line([sh, (fx + 5 * facing, top_y + 4)], fill=top, width=2)
    else:
        sw = int(round(1.5 * math.sin(phase * 2 * math.pi))) if pose == "walk" else 0
        d.line([sh, (fx + facing + sw, top_y + 6)], fill=top2, width=2)
    if facing < 0:
        pass
    a = np.asarray(im)
    m = a[..., 3] > 0
    ring = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ring |= np.roll(np.roll(m, dy, 0), dx, 1)
    out = np.zeros_like(a)
    out[ring] = (*OUT, 255)
    out[m] = a[m]
    return Image.fromarray(out, "RGBA")


def put(img, spr, x, feet_y):
    img.paste(spr, (int(x) - 12, int(feet_y) - 22), spr)


# ---------- статичный мир ----------
def noise_dots(d, box, cols, n, seed):
    r = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = r.randrange(x0, x1), r.randrange(y0, y1)
        d.point((x, y), fill=r.choice(cols))


def pine(d, x, base, h, col=(40, 104, 62), dark=(30, 82, 50), snow=False):
    d.rectangle([x - 1, base - h // 3, x + 1, base], fill=(84, 58, 40))
    tiers = 4
    for i in range(tiers):
        ty = base - h // 4 - i * h // 5
        w = (tiers - i) * h // 9 + 3
        d.polygon([(x, ty - h // 3), (x - w, ty), (x + w, ty)], fill=col)
        d.polygon([(x, ty - h // 3), (x - w, ty), (x - w // 3, ty)], fill=dark)


_ST = {}


def static_layer(night):
    if night not in _ST:
        _ST[night] = _static(night)
    return _ST[night]


def _static(night):
    im = Image.new("RGB", (BW, BH))
    d = ImageDraw.Draw(im)
    # земля в разрезе
    layers = [(GY, (112, 74, 46)), (GY + 40, (98, 64, 40)), (GY + 100, (84, 56, 36)), (ROCK_Y, (66, 62, 66))]
    for i, (y, c) in enumerate(layers):
        y1 = layers[i + 1][0] if i + 1 < len(layers) else BH
        d.rectangle([0, y, BW, y1], fill=c)
        noise_dots(d, (0, y, BW, y1), [lerp(c, (0, 0, 0), 0.18), lerp(c, (255, 255, 255), 0.08)], 900, i)
    r = random.Random(7)
    for _ in range(70):                       # камни
        x, y = r.randrange(0, BW), r.randrange(ROCK_Y + 2, BH)
        s = r.randrange(3, 9)
        d.ellipse([x, y, x + s, y + s * 0.7], fill=(88, 84, 90), outline=(48, 46, 50))
    for _ in range(25):
        x, y = r.randrange(0, BW), r.randrange(GY + 20, ROCK_Y - 6)
        d.ellipse([x, y, x + 4, y + 3], fill=(120, 110, 100), outline=(70, 60, 50))
    # корни под деревьями
    for x in (200, 226, 252):
        for k in range(4):
            pts = [(x, GY)]
            px, py = x, GY
            for _ in range(5):
                px += r.randint(-4, 4); py += r.randint(3, 6)
                pts.append((px, py))
            d.line(pts, fill=(70, 46, 30))
    d.rectangle([0, GY, BW, GY + 2], fill=(76, 142, 58))
    d.rectangle([0, GY + 3, BW, GY + 3], fill=(54, 108, 44))
    return im


# ---------- кадр ----------
def sky(d, kind, t):
    tops = {"day": ((92, 148, 206), (176, 210, 232)), "night": ((8, 12, 30), (30, 36, 64)),
            "evening": ((60, 50, 90), (236, 128, 72))}
    a, b = tops[kind]
    for y in range(GY):
        d.line([(0, y), (BW, y)], fill=lerp(a, b, y / GY))
    if kind == "night":
        r = random.Random(3)
        for i in range(60):
            x, y = r.randrange(BW), r.randrange(GY - 40)
            if (math.sin(t * 2 + i) > -0.6):
                d.point((x, y), fill=(200, 205, 230))
        d.ellipse([200, 34, 214, 48], fill=(236, 236, 214))
    elif kind == "day":
        d.ellipse([206, 30, 222, 46], fill=(255, 240, 180))
        for i, (cx, cy, w) in enumerate(((40, 52, 34), (150, 34, 26), (110, 70, 22))):
            x = (cx + t * (2 + i)) % (BW + 60) - 30
            d.ellipse([x, cy, x + w, cy + 8], fill=(236, 242, 248)); d.ellipse([x + w // 4, cy - 5, x + w * 3 // 4, cy + 5], fill=(236, 242, 248))
    else:
        d.ellipse([150, 98, 176, 124], fill=(255, 196, 120))


def city(d, kind, burning, t):
    col = {"day": (130, 150, 172), "night": (22, 26, 44), "evening": (96, 62, 82)}[kind]
    r = random.Random(11)
    x = 0
    while x < 95:
        w, h = r.randrange(8, 16), r.randrange(14, 40)
        d.rectangle([x, GY - 12 - h, x + w, GY - 12], fill=col)
        if kind != "day":
            for wy in range(GY - 10 - h, GY - 14, 5):
                if r.random() < 0.25:
                    d.point((x + 2 + r.randrange(max(1, w - 4)), wy), fill=(250, 200, 110))
        x += w + 1
    if burning:
        for i in range(5):
            fx = 10 + i * 18
            fy = GY - 40 - (i % 2) * 8
            fl = 3 + int(2 * math.sin(t * 9 + i))
            d.ellipse([fx - fl, fy - fl * 2, fx + fl, fy + 2], fill=(255, 120, 40))
            d.ellipse([fx - 1, fy - fl, fx + 1, fy + 1], fill=(255, 220, 120))
            for k in range(4):
                sy = fy - 8 - k * 7 - (t * 6) % 7
                d.ellipse([fx - 3 + k, sy - 3, fx + 3 + k, sy + 3], fill=(70, 60, 64))


def house(d, kind):
    wall, roof = (128, 92, 62), (96, 52, 44)
    d.rectangle([4, 112, 62, GY], fill=wall)
    for y in range(114, GY, 4):
        d.line([(4, y), (62, y)], fill=(104, 74, 50))
    d.polygon([(0, 114), (33, 88), (66, 114)], fill=roof)
    d.polygon([(40, 96), (52, 106), (44, 106)], fill=(30, 22, 26))         # дыра в крыше
    d.rectangle([12, 122, 24, 134], fill=(255, 210, 120) if kind == "evening" else (40, 50, 62))
    d.line([(12, 122), (24, 134)], fill=(70, 50, 40)); d.line([(24, 122), (12, 134)], fill=(70, 50, 40))
    d.rectangle([38, 126, 50, GY], fill=(70, 46, 32))
    for x in range(68, 100, 6):                                              # забор
        d.rectangle([x, 134, x + 3, GY], fill=(150, 112, 74))
    d.line([(66, 138), (100, 138)], fill=(120, 88, 58))
    d.line([(66, 145), (100, 145)], fill=(120, 88, 58))


def room(d, box, finished, depth=1.0, side="right", seed=0):
    x0, y0, x1, y1 = box
    if depth <= 0:
        return
    if side == "right":
        x1 = x0 + int((x1 - x0) * depth)
    elif side == "down":
        y1 = y0 + int((y1 - y0) * depth)
    d.rectangle([x0, y0, x1, y1], fill=(46, 32, 24))
    noise_dots(d, (x0, y0, x1 + 1, y1 + 1), [(56, 40, 30), (38, 26, 20)], (x1 - x0) * (y1 - y0) // 10, seed)
    if finished:
        for x in range(x0, x1, 5):
            d.rectangle([x, y0 + 2, x + 4, y1 - 3], fill=(116, 82, 52))
            d.line([(x, y0 + 2), (x, y1 - 3)], fill=(84, 58, 36))
            d.point((x + 2, y0 + 5), fill=(70, 50, 34)); d.point((x + 2, y1 - 6), fill=(70, 50, 34))
        d.rectangle([x0, y1 - 2, x1, y1], fill=(92, 64, 40))
        d.line([(x0, y0 + 1), (x1, y0 + 1)], fill=(84, 58, 36))


def ladder(d, x, y0, y1):
    d.line([(x, y0), (x, y1)], fill=(150, 108, 64)); d.line([(x + 6, y0), (x + 6, y1)], fill=(150, 108, 64))
    for y in range(y0 + 2, y1, 4):
        d.line([(x, y), (x + 6, y)], fill=(126, 88, 52))


def glow(L, x, y, r, s, col):
    """Добавить тёплый свет в карту освещения."""
    yy, xx = np.ogrid[0:BH, 0:BW]
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * r * r)) * s
    for i in range(3):
        L[..., i] += g * col[i]


def tunnel(d, p):
    """Второй выход: из комнаты 1 вправо-вверх к оврагу."""
    a, b = (190, 222), (248, 158)
    n = int(40 * p)
    for i in range(n + 1):
        k = i / 40
        x, y = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        d.ellipse([x - 4, y - 5, x + 4, y + 4], fill=(46, 32, 24))
    return a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p


def zombie_list(n, t):
    """(x, поза, фаза, направление) для зомби на поверхности."""
    zs = []
    if n == 11:                               # толпа у люка
        r = random.Random(5)
        for i in range(13):
            x = 78 + i * 7 + r.randint(-3, 3) + math.sin(t * 1.3 + i) * 2
            zs.append((x, "walk", (t * 0.8 + i * 0.37) % 1, -1 if x > 116 else 1))
        return zs
    count = {1: 3, 2: 5, 6: 3, 18: 3, 19: 3, 20: 3}.get(n, 2)
    for i in range(count):
        v = 6 + i * 2.5
        span = 300
        x = (i * 97 + v * t * (1 if i % 2 == 0 else -1)) % span - 15
        zs.append((x, "walk", (t * 1.2 + i * 0.31) % 1, 1 if i % 2 == 0 else -1))
    if n == 6:
        zs.append((HATCH_X + 3, "crouch", (t * 1.5) % 1, -1))
    return zs


def world(n, p, t):
    kind = "night" if n in NIGHT else "evening" if n in EVENING else "day"
    img = static_layer(kind == "night").copy()
    d = ImageDraw.Draw(img)
    sky(d, kind, t)
    city(d, kind, n <= 2, t)
    # дальний лес
    for x in range(100, 280, 9):
        pine(d, x, GY + 1, 26 + (x * 7) % 12, col=(52, 96, 80) if kind != "night" else (20, 36, 40),
             dark=(42, 82, 68) if kind != "night" else (16, 28, 34))
    house(d, kind)
    # ---- подземелье ----
    room(d, CELLAR, False, seed=1)
    for sx in (96, 132):                      # полки с банками в погребе
        d.line([(sx - 2, 166), (sx + 6, 166)], fill=(110, 80, 50))
        for k in range(3):
            d.rectangle([sx - 1 + k * 3, 162, sx + k * 3, 165], fill=(190, 90, 60))
    dig1 = 0 if n < 4 else (p if n == 4 else 1)
    if dig1:
        room(d, SHAFT1, False, min(1, dig1 * 2.5), side="down", seed=2)
        if dig1 > 0.4:
            room(d, ROOM1, n >= 5, (dig1 - 0.4) / 0.6, side="right", seed=3)
        ladder(d, 112, 176, 200 if dig1 > 0.4 else int(182 + 18 * dig1 * 2.5))
    ladder(d, 112, GY - 1, 176)
    dig2 = 0 if n < 8 else (p if n == 8 else 1)
    if dig2:
        room(d, SHAFT2, False, min(1, dig2 * 2.5), side="down", seed=4)
        if dig2 > 0.4:
            room(d, ROOM2, n >= 9, (dig2 - 0.4) / 0.6, side="right", seed=5)
        ladder(d, 168, 230, 262 if dig2 > 0.4 else int(232 + 30 * dig2 * 2.5))
    tun = 0 if n < 12 else (p if n == 12 else 1)
    tun_tip = tunnel(d, tun) if tun else None
    ext = 0 if n < 13 else (min(1, p * 1.6) if n == 13 else 1)
    if ext:
        room(d, EXT2, False, ext, side="right", seed=6)
    if n >= 13 and ext >= 1:                  # бетон чужого бункера
        d.rectangle([214, 258, 218, 296], fill=(132, 132, 138))
        for y in range(260, 296, 6):
            d.line([(214, y), (218, y)], fill=(104, 104, 110))
    if n >= 15:
        d.rectangle([ANYA[0] - 4, ANYA[1] - 4, ANYA[2], ANYA[3] + 2], fill=(132, 132, 138))
        d.rectangle(ANYA, fill=(70, 72, 80))
        for x in range(ANYA[0], ANYA[2], 10):
            d.line([(x, ANYA[1]), (x, ANYA[3])], fill=(60, 62, 70))
        d.rectangle([ANYA[0], ANYA[3] - 2, ANYA[2], ANYA[3]], fill=(96, 98, 104))
        d.rectangle([212, 276, 220, 294], fill=(46, 32, 24))                 # пролом
        for k, (cx, cy) in enumerate([(213, 275), (219, 274), (221, 280), (211, 290)]):
            d.rectangle([cx, cy, cx + 1, cy + 1], fill=(150, 150, 156))
        # её лаз наверх
        if n >= 16:
            for i in range(30):
                k = i / 29
                d.ellipse([262 + 6 * k - 5, 256 - 100 * k - 5, 262 + 6 * k + 5, 256 - 100 * k + 4], fill=(46, 32, 24))
        d.rectangle([224, 284, 240, 290], fill=(90, 70, 110))                # её спальник
    # мебель и вещи
    lamp_on = n > 10 or (n == 10 and p > 0.55)
    if n >= 5:
        d.rectangle([66, 224, 92, 229], fill=(156, 70, 60)); d.rectangle([66, 222, 72, 225], fill=(220, 214, 196))  # матрас
        d.rectangle([98, 224, 100, 229], fill=(120, 84, 52))
        if not lamp_on:
            d.rectangle([98, 221, 99, 223], fill=(240, 236, 220)); d.point((98, 220), fill=(255, 200, 80))
    if n >= 9:                                # полка с консервами, печка, труба
        d.line([(124, 212), (150, 212)], fill=(84, 58, 36))
        d.line([(124, 220), (150, 220)], fill=(84, 58, 36))
        for k in range(8):
            d.rectangle([125 + k * 3, 208 + (k % 2) * 8, 126 + k * 3, 211 + (k % 2) * 8], fill=(180, 186, 196))
        d.rectangle([172, 216, 184, 229], fill=(60, 60, 66)); d.rectangle([175, 222, 181, 226], fill=(240, 120, 40))
        d.rectangle([177, GY + 2, 179, 216], fill=(80, 80, 86))
    if n >= 8 and (n > 8 or p > 0.7):         # ручей
        k = 1 if n > 8 else (p - 0.7) / 0.3
        d.rectangle([80, 276, 82, 294], fill=(60, 120, 190))
        d.rectangle([82, 290, 82 + int(26 * k), 294], fill=(70, 140, 210))
        for i in range(4):
            yy = 276 + ((t * 30 + i * 5) % 16)
            d.point((83 + i % 2, yy), fill=(170, 210, 250))
    if n >= 10:                               # велогенератор и лампа
        bx = 120
        d.ellipse([bx - 5, 284, bx + 5, 294], outline=(30, 30, 30)); d.ellipse([bx + 9, 284, bx + 19, 294], outline=(30, 30, 30))
        d.line([(bx, 289), (bx + 8, 282), (bx + 14, 289)], fill=(190, 40, 40))
        d.line([(bx + 8, 282), (bx + 8, 279)], fill=(190, 40, 40))
        d.line([(bx + 14, 289), (bx + 13, 270)], fill=(30, 30, 30))
        d.line([(bx + 13, 270), (150, 264)], fill=(30, 30, 30))
        d.line([(150, 264), (150, 268)], fill=(30, 30, 30))
        d.line([(110, 202), (110, 206)], fill=(30, 30, 30))
        on = lamp_on and (n != 10 or math.sin(t * 40) > -0.3 or p > 0.7)
        d.rectangle([149, 268, 151, 270], fill=(255, 236, 150) if on else (120, 120, 110))
        d.rectangle([109, 206, 111, 208], fill=(255, 236, 150) if on else (120, 120, 110))
    if n >= 17:                               # грядки, кролики, радио
        for gx in range(150, 198, 8):
            d.rectangle([gx, 288, gx + 6, 293], fill=(92, 62, 40))
            for k in range(3):
                d.line([(gx + 1 + k * 2, 288), (gx + 1 + k * 2, 284 - (k % 2) * 2)], fill=(90, 190, 80))
        d.rectangle([150, 264, 196, 265], fill=(200, 110, 230))
        d.rectangle([150, 214, 166, 229], outline=(150, 150, 150))
        for k, rx in enumerate((153, 160)):
            ry = 226 - int(abs(math.sin(t * 3 + k)) * 2)
            d.rectangle([rx, ry, rx + 3, ry + 2], fill=(236, 232, 226)); d.point((rx + 1, ry - 1), fill=(236, 232, 226))
        d.rectangle([138, 223, 146, 229], fill=(70, 74, 60)); d.line([(144, 223), (147, 216)], fill=(40, 40, 40))
    if n >= 18:                               # стол
        d.rectangle([110, 222, 136, 224], fill=(140, 100, 62))
        d.line([(112, 224), (112, 229)], fill=(110, 78, 48)); d.line([(134, 224), (134, 229)], fill=(110, 78, 48))
        d.rectangle([121, 218, 125, 221], fill=(232, 170, 60))
        d.rectangle([116, 219, 117, 221], fill=(240, 236, 220)); d.point((116, 218), fill=(255, 200, 80))
    # ---- поверхность ----
    gd = 0 if n < 4 else (p if n == 4 else 1)
    for i, gx in enumerate(range(132, 176, 9)):        # грядки и кучки земли
        h = int(4 * min(1, gd * 2 - i * 0.2)) if gd else 0
        d.rectangle([gx, GY - 2, gx + 7, GY], fill=(92, 62, 40))
        if h > 0:
            d.polygon([(gx - 1, GY - 2), (gx + 3, GY - 2 - h), (gx + 8, GY - 2)], fill=(112, 76, 46))
    metal = n > 7 or (n == 7 and p > 0.45)
    d.rectangle([HATCH_X - 6, GY - 2, HATCH_X + 8, GY], fill=(120, 124, 132) if metal else (120, 84, 50))
    if metal:
        d.line([(HATCH_X - 4, GY - 1), (HATCH_X + 6, GY - 1)], fill=(80, 82, 90))
    if n >= 9:                                # куст, прячущий трубу
        d.ellipse([170, GY - 9, 188, GY + 1], fill=(48, 110, 52)); d.ellipse([174, GY - 12, 186, GY - 2], fill=(60, 130, 60))
        if kind == "day":
            for k in range(4):
                sy = GY - 14 - k * 6 - (t * 8) % 6
                c = 150 + k * 18
                d.ellipse([177 - 2 + k, sy - 2, 177 + 2 + k, sy + 2], fill=(c, c, c))
    if n >= 12:                               # овраг
        d.polygon([(238, GY), (244, GY + 8), (256, GY + 8), (262, GY)], fill=(46, 32, 24))
    for x, s in ((204, 54), (230, 62), (258, 50)):
        pine(d, x, GY, s)
    # ---- люди под землёй ----
    ph = (t * 1.6) % 1
    H = {}
    if n == 1:
        H["hero"] = (200 - 82 * min(1, p * 1.4), GY, "walk", -1)
    elif n == 2:
        H["hero"] = (122, 182, "sit", 1)
    elif n == 3:
        H["hero"] = (120, 182, "stand", 1)
    elif n == 4:
        y = 182 + 18 * min(1, dig1 * 2.5) if dig1 < 0.4 else 232
        x = 120 if dig1 < 0.4 else ROOM1[0] + (ROOM1[2] - ROOM1[0]) * (dig1 - 0.4) / 0.6 - 6
        H["hero"] = (max(x, 66), y, "dig", 1)
    elif n == 5:
        H["hero"] = (80, 232, "sit", 1)
    elif n == 6:
        H["hero"] = (118, 232, "stand", -1)
    elif n == 7:
        H["hero"] = (118, 182, "up", 1)
    elif n == 8:
        y = 232 + 30 * min(1, dig2 * 2.5) if dig2 < 0.4 else 294
        x = 172 if dig2 < 0.4 else ROOM2[0] + (ROOM2[2] - ROOM2[0]) * (dig2 - 0.4) / 0.6
        H["hero"] = (min(max(x, 92), 194), y, "dig", -1 if dig2 >= 0.4 else 1)
    elif n == 9:
        H["hero"] = (164, 232, "stand", 1)
    elif n == 10:
        H["hero"] = (127, 294, "pedal", 1)
    elif n == 11:
        H["hero"] = (80, 232, "sit", 1)
    elif n == 12:
        H["hero"] = (tun_tip[0] - 6, tun_tip[1] + 6, "dig", 1)
    elif n == 13:
        H["hero"] = (EXT2[0] + (EXT2[2] - EXT2[0]) * ext - 4, 294, "dig", 1)
    elif n in (14,):
        H["hero"] = (206, 294, "stand", 1)
    elif n in (15, 16):
        H["hero"] = (204, 294, "stand", 1)
        H["anya"] = (232, 296, "knife" if n == 15 else "stand", -1)
    elif n == 17:
        H["hero"] = (170, 294, "dig", 1)
        H["anya"] = (142, 232, "stand", 1)
    elif n == 18:
        H["hero"] = (106, 232, "sit", 1)
        H["anya"] = (140, 232, "sit", -1)
    else:
        H["hero"] = (120, 294, "stand", 1)
        H["anya"] = (136, 294, "stand", -1)
    for who, (x, y, pose, f) in H.items():
        spr = person(who, pose, ph if pose != "pedal" else (t * 1.2) % 1, f)
        if f < 0:
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        put(img, spr, x, y)
    for x, pose, phz, f in zombie_list(n, t):
        spr = person("zombie", pose, phz, f)
        if f < 0:
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        put(img, spr, x, GY)
    # ---- свет ----
    a = np.asarray(img).astype(np.float32) / 255
    amb_sky = {"day": 1.0, "evening": 0.92, "night": 0.62}[kind]
    amb_ground = {"day": 0.82, "evening": 0.7, "night": 0.42}[kind]
    L = np.zeros((BH, BW, 3), np.float32)
    L[:GY] = amb_sky
    L[GY:] = amb_ground
    warm = (1.0, 0.78, 0.45)
    lamp = (1.0, 0.92, 0.7)
    if kind == "night":
        L[:GY] *= np.array([0.85, 0.9, 1.25])
    if n in (2,):
        glow(L, 128, 176, 14, 0.9, (1.0, 0.95, 0.8))
    if 5 <= n and not lamp_on:
        glow(L, 99, 220, 22, 0.9, warm)
    if lamp_on:
        glow(L, 110, 210, 34, 0.9, lamp)
        glow(L, 150, 272, 34, 0.9, lamp)
    if n >= 9:
        glow(L, 178, 224, 12, 0.7, (1.0, 0.6, 0.3))
    if n >= 15:
        glow(L, 244, 270, 20, 0.6, (0.8, 0.9, 1.0))
    if n >= 17:
        glow(L, 172, 278, 20, 0.5, (0.9, 0.6, 1.0))
    if n >= 18:
        glow(L, 116, 216, 16, 0.6, warm)
    out = np.clip(a * L, 0, 1)
    img = Image.fromarray((out * 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    if n == 11:                               # свет из щелей люка
        for k, dx in enumerate((-5, 0, 6)):
            al = int(70 + 30 * math.sin(t * 3 + k))
            d.polygon([(HATCH_X + dx, GY - 1), (HATCH_X + dx - 10, GY - 80), (HATCH_X + dx + 8, GY - 80)], fill=(255, 230, 150, al))
    if n == 6:                                # сыплется земля
        for i in range(10):
            yy = 182 + ((t * 40 + i * 9) % 48)
            d.point((112 + (i * 5) % 12, yy), fill=(140, 100, 60, 255))
    if n in (14, 19):                         # стук: расходящиеся круги
        cx, cy = (214, 280) if n == 14 else (128, 310)
        ph3 = (t * 1.3) % 1
        if ph3 < 0.6:
            for k in range(3):
                rr = 4 + ((ph3 * 3 - k * 0.5) % 1.5) * 14
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, 140))
    if n == 13 and ext >= 1:                  # искры от лопаты
        for i in range(5):
            if math.sin(t * 25 + i) > 0.3:
                d.point((212 + i % 3, 276 + i * 2), fill=(255, 230, 120, 255))
    if n == 20:                               # трещина и глаза
        crack = [(126, 296), (122, 304), (130, 314), (124, 326), (132, 338), (128, 350)]
        m = max(2, int(len(crack) * min(1, p * 1.5)))
        d.line(crack[:m], fill=(10, 8, 10, 255), width=2)
        if p > 0.75:
            for ex in (124, 131):
                d.rectangle([ex, 340, ex + 1, 341], fill=(255, 40, 30, 255))
    return img


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "test"
    for n in range(1, 21):
        world(n, 0.8, 1.0).resize((BW * K, BH * K), Image.NEAREST).save(f"{out}_{n:02d}.png")
