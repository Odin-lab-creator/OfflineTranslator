"""Мир «Бункера»: разрез земли сбоку. Рисуется кодом в пикселях 540×960 и увеличивается ×2 → 1080×1920.
world(n, p, t) — кадр сцены n (1…20), p — прогресс внутри сцены 0…1, t — общее время (для анимации)."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

BW, BH, K = 540, 960, 2
GY = 300                                    # линия земли
NIGHT = {2, 6, 11, 18, 19, 20}
EVENING = {1}

# --- комнаты (x0, y0, x1, y1) ---
CELLAR = (184, 312, 280, 364)
SHAFT1 = (218, 364, 246, 400)
ROOM1 = (112, 400, 384, 464)
SHAFT2 = (330, 464, 358, 524)
ROOM2 = (160, 524, 400, 588)
EXT2 = (400, 532, 428, 588)                 # прокоп к бетону
ANYA = (444, 516, 540, 592)                 # чужой бункер (бетон)
HATCH_X = 232
ROCK_Y = 612
F_CELLAR, F_ROOM1, F_ROOM2 = 364, 462, 586  # уровни пола

OUT = (24, 18, 16)
PEOPLE = {
    "hero": dict(skin=(238, 194, 150), top=(52, 112, 196), top2=(36, 82, 150), top3=(92, 150, 220),
                 legs=(66, 62, 74), boot=(52, 36, 28), hair=(232, 120, 34), hair2=(190, 86, 24)),
    "anya": dict(skin=(236, 188, 150), top=(64, 128, 84), top2=(44, 94, 60), top3=(96, 160, 110),
                 legs=(70, 70, 80), boot=(48, 36, 30), hair=(40, 30, 28), hair2=(26, 20, 18)),
    "zombie": dict(skin=(136, 172, 104), top=(98, 86, 78), top2=(74, 64, 58), top3=(120, 108, 98),
                   legs=(64, 70, 62), boot=(50, 44, 40), hair=(58, 66, 44), hair2=(44, 50, 34)),
}


_B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 + 1 / 32
BAYER = np.tile(_B4, (BH // 4, BW // 4))      # для пиксельных переходов света и неба


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


# ---------- люди ----------
_PC = {}


def person(kind, pose, phase):
    """Человечек ~44 px на холсте 48×60 (ступни на y=56), лицом вправо, с обводкой. Кадры кешируются."""
    key = (kind, pose, round(phase * 24) % 24)
    if key in _PC:
        return _PC[key]
    ph = key[2] / 24
    c = PEOPLE[kind]
    im = Image.new("RGBA", (48, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, feet = 24, 56
    zomb = kind == "zombie"
    s1 = math.sin(ph * 2 * math.pi)
    sit, crouch = pose in ("sit", "pedal"), pose == "crouch"
    bob = 0
    # ---- ноги ----
    if sit:
        hip = feet - 12
        if pose == "pedal":
            a = ph * 2 * math.pi
            for s, col in ((math.pi, c["top2"]), (0, c["legs"])):
                fx, fy = x + 8 + 5 * math.cos(a + s), feet - 5 + 5 * math.sin(a + s)
                kx, ky = x + 8, hip - 4 + 2 * math.sin(a + s)
                d.line([(x, hip), (kx, ky), (fx, fy)], fill=c["legs"], width=4)
                d.rectangle([fx - 1, fy - 1, fx + 4, fy + 1], fill=c["boot"])
        else:
            d.rectangle([x - 4, hip - 2, x + 9, hip + 2], fill=c["legs"])
            d.rectangle([x + 6, hip, x + 9, feet - 2], fill=c["legs"])
            d.rectangle([x + 6, feet - 3, x + 12, feet], fill=c["boot"])
        top_y = hip - 15
    else:
        hip = feet - 12 + (4 if crouch else 0)
        amp = 5 if pose == "walk" else 0
        bob = int(round(abs(s1) * 1.2)) if pose == "walk" else 0
        for sgn, col in ((-1, c["legs"]), (1, lerp(c["legs"], (0, 0, 0), 0.25))):
            fx = x + sgn * amp * s1
            lift = max(0, -sgn * s1) * 3 if pose == "walk" else 0
            d.line([(x + sgn, hip - bob), (fx, feet - 2 - lift)], fill=col, width=4)
            d.rectangle([fx - 2, feet - 3 - lift, fx + 4, feet - lift], fill=c["boot"])
        if crouch:
            d.rectangle([x - 2, hip - 2, x + 6, hip + 2], fill=c["legs"])
        top_y = hip - 15 - bob
    hunch = 2 if zomb else 0
    # ---- тело ----
    d.rounded_rectangle([x - 7, top_y, x + 7, hip + 1 - bob], 3, fill=c["top"])
    d.rectangle([x - 7, top_y + 2, x - 4, hip - bob], fill=c["top2"])
    if kind == "hero":
        d.line([(x + 2, top_y + 2), (x + 2, hip - 1 - bob)], fill=c["top3"])
        d.rectangle([x + 3, top_y + 9, x + 6, top_y + 11], fill=c["top2"])
        d.rectangle([x - 8, top_y + 2, x - 5, top_y + 12], fill=(92, 70, 52))     # рюкзак
    elif kind == "anya":
        d.rectangle([x - 7, top_y + 11, x + 7, top_y + 12], fill=(60, 50, 40))    # ремень
        d.point([(x + 4, top_y + 4), (x + 4, top_y + 7)], fill=c["top3"])
    else:
        d.polygon([(x - 7, hip - bob), (x - 4, hip - 4 - bob), (x - 1, hip - bob)], fill=(0, 0, 0, 0))
        d.rectangle([x + 1, top_y + 5, x + 3, top_y + 8], fill=(150, 56, 48))
        d.point([(x - 3, top_y + 10), (x + 5, top_y + 3)], fill=c["top3"])
    # ---- голова ----
    hx, hy = x + 1 + hunch, top_y - 13 + (hunch // 2)
    d.rounded_rectangle([hx - 7, hy, hx + 7, hy + 13], 3, fill=c["skin"])
    d.rectangle([hx - 7, hy + 4, hx - 5, hy + 12], fill=lerp(c["skin"], (0, 0, 0), 0.15))
    ex = hx + 3
    if kind == "hero":                       # шапка с отворотом и помпоном
        d.rounded_rectangle([hx - 8, hy - 3, hx + 7, hy + 4], 3, fill=c["hair"])
        d.rectangle([hx - 8, hy + 3, hx + 7, hy + 5], fill=c["hair2"])
        d.ellipse([hx - 4, hy - 7, hx + 1, hy - 2], fill=(240, 236, 226))
        d.rectangle([hx - 7, hy + 6, hx - 5, hy + 10], fill=(110, 72, 44))
    elif kind == "anya":
        d.rounded_rectangle([hx - 8, hy - 2, hx + 7, hy + 4], 3, fill=c["hair"])
        d.rectangle([hx - 8, hy + 2, hx - 4, hy + 11], fill=c["hair"])
        d.ellipse([hx - 13, hy + 1, hx - 7, hy + 7], fill=c["hair2"])            # пучок/хвост
        d.rectangle([hx - 12, hy + 6, hx - 9, hy + 14], fill=c["hair2"])
    else:
        d.rectangle([hx - 7, hy - 1, hx + 3, hy + 2], fill=c["hair"])
        d.point([(hx + 5, hy), (hx - 2, hy - 2)], fill=c["hair"])
    if zomb:
        d.rectangle([ex - 1, hy + 5, ex + 2, hy + 7], fill=(60, 70, 50))
        d.rectangle([ex, hy + 6, ex + 1, hy + 7], fill=(230, 40, 30))
        d.rectangle([hx + 2, hy + 10, hx + 6, hy + 11], fill=(70, 30, 30))
    else:
        blink = (ph * 7) % 1 < 0.05
        d.rectangle([ex, hy + 6, ex + 1, hy + 7 if not blink else hy + 6], fill=(28, 22, 22))
        d.line([(ex - 1, hy + 4), (ex + 2, hy + 4)], fill=lerp(c["hair2"], (0, 0, 0), 0.3))
        d.line([(hx + 3, hy + 10), (hx + 5, hy + 10)], fill=(176, 110, 96))
    # ---- руки ----
    sh = (x + 2, top_y + 4)
    hand = c["skin"]
    def arm(pts, col=c["top"]):
        d.line(pts, fill=col, width=4)
        hx2, hy2 = pts[-1]
        d.rectangle([hx2 - 2, hy2 - 2, hx2 + 2, hy2 + 2], fill=hand)
    if zomb and not crouch:
        sway = 2 * math.sin(ph * 2 * math.pi + 1)
        arm([sh, (x + 16, top_y + 4 + sway)])
        arm([(x - 1, top_y + 5), (x + 13, top_y + 7 - sway)], c["top2"])
    elif crouch:
        y = top_y - 10 + 4 * math.sin(ph * 4 * math.pi)
        arm([sh, (x + 10, y)])
        arm([(x - 1, top_y + 5), (x + 7, y + 3)], c["top2"])
    elif pose == "dig":
        a = 0.35 + 1.1 * (0.5 + 0.5 * s1)
        ax, ay = sh[0] + 9 * math.cos(a), sh[1] + 9 * math.sin(a)
        b = a + 0.5
        h0 = (ax - 9 * math.cos(b), ay - 9 * math.sin(b))
        h1 = (ax + 12 * math.cos(b), ay + 12 * math.sin(b))
        d.line([h0, h1], fill=(140, 96, 54), width=2)
        d.polygon([(h1[0] - 3, h1[1] - 2), (h1[0] + 4, h1[1] + 1), (h1[0] + 1, h1[1] + 7), (h1[0] - 4, h1[1] + 4)],
                  fill=(176, 182, 192), outline=(120, 124, 134))
        arm([sh, (ax, ay)])
    elif pose == "up":
        arm([sh, (x + 5, top_y - 16 + 2 * s1)])
        arm([(x - 1, top_y + 5), (x - 1, top_y - 15 - 2 * s1)], c["top2"])
    elif pose == "knife":
        arm([sh, (x + 12, top_y + 6)])
        d.line([(x + 13, top_y + 5), (x + 19, top_y + 1)], fill=(214, 220, 228), width=2)
    elif pose == "ear":
        arm([sh, (x + 11, top_y - 2)])
    elif sit or pose == "pedal":
        arm([sh, (x + 10, top_y + 9)])
    else:
        sw = 3 * s1 if pose == "walk" else 0.6 * s1
        arm([sh, (x + 2 + sw, top_y + 13)], c["top2"] if pose != "walk" else c["top"])
    # ---- обводка ----
    a = np.asarray(im)
    m = a[..., 3] > 0
    ring = m.copy()
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        ring |= np.roll(np.roll(m, dy, 0), dx, 1)
    out = np.zeros_like(a)
    out[ring] = (*OUT, 255)
    out[m] = a[m]
    _PC[key] = Image.fromarray(out, "RGBA")
    return _PC[key]


def put(img, kind, pose, phase, x, feet_y, facing=1):
    spr = person(kind, pose, phase)
    if facing < 0:
        spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
    img.paste(spr, (int(round(x)) - 24, int(round(feet_y)) - 56), spr)


# ---------- статичный мир ----------
def noise_dots(d, box, cols, n, seed, size=1):
    r = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = r.randrange(x0, max(x0 + 1, x1)), r.randrange(y0, max(y0 + 1, y1))
        s = r.randrange(size) if size > 1 else 0
        d.rectangle([x, y, x + s, y], fill=r.choice(cols))


def pine(d, x, base, h, col=(40, 104, 62), dark=(28, 80, 48), light=(66, 136, 80), snow=False):
    d.rectangle([x - 3, base - h // 3, x + 2, base], fill=(84, 58, 40))
    d.rectangle([x - 3, base - h // 3, x - 2, base], fill=(64, 44, 30))
    tiers = 6
    for i in range(tiers):
        ty = base - h // 5 - i * h // 8
        w = (tiers - i) * h // 15 + 4
        th = h // 4
        d.polygon([(x, ty - th), (x - w, ty), (x + w, ty)], fill=col)
        d.polygon([(x, ty - th), (x - w, ty), (x - w // 3, ty)], fill=dark)
        d.line([(x + 1, ty - th + 2), (x + w - 2, ty - 1)], fill=light)
        d.line([(x - w + 1, ty), (x + w - 1, ty)], fill=dark)


def rock(d, x, y, s, base=(92, 88, 96)):
    pts = [(x, y + s * 0.4), (x + s * 0.3, y), (x + s * 0.8, y + s * 0.05), (x + s, y + s * 0.5),
           (x + s * 0.7, y + s * 0.75), (x + s * 0.2, y + s * 0.72)]
    d.polygon(pts, fill=base, outline=lerp(base, (0, 0, 0), 0.45))
    d.line([(x + s * 0.3, y + 1), (x + s * 0.75, y + s * 0.08)], fill=lerp(base, (255, 255, 255), 0.25))


_ST = {}


def static_layer():
    if "g" not in _ST:
        _ST["g"] = _static()
    return _ST["g"]


def _static():
    im = Image.new("RGB", (BW, BH))
    d = ImageDraw.Draw(im)
    layers = [(GY, (114, 76, 48)), (GY + 84, (100, 66, 42)), (GY + 200, (86, 58, 38)), (ROCK_Y, (62, 58, 64))]
    r = random.Random(7)
    for i, (y, c) in enumerate(layers):
        y1 = layers[i + 1][0] if i + 1 < len(layers) else BH
        # волнистая граница слоя
        pts = [(0, BH)] + [(x, y + 4 * math.sin(x / 37 + i) + 2 * math.sin(x / 11 + i * 2)) for x in range(0, BW + 6, 6)] + [(BW, BH)]
        d.polygon(pts, fill=c)
        noise_dots(d, (0, y, BW, y1 + 6), [lerp(c, (0, 0, 0), 0.16), lerp(c, (0, 0, 0), 0.08),
                                            lerp(c, (255, 255, 255), 0.07)], 5200, i, size=3)
        for _ in range(26):                   # горизонтальные прожилки
            sx, sy = r.randrange(BW), r.randrange(y + 4, y1)
            d.line([(sx, sy), (sx + r.randrange(10, 40), sy)], fill=lerp(c, (0, 0, 0), 0.12))
    for _ in range(120):
        rock(d, r.randrange(-8, BW), r.randrange(ROCK_Y + 6, BH), r.randrange(8, 22), (86 + r.randrange(14),) * 2 + (94,))
    for _ in range(40):
        rock(d, r.randrange(0, BW), r.randrange(GY + 40, ROCK_Y - 16), r.randrange(5, 10), (126, 114, 102))
    for x in (400, 452, 504):                # корни под деревьями
        for k in range(6):
            pts, px, py = [(x, GY)], x, GY
            for _ in range(7):
                px += r.randint(-7, 7); py += r.randint(5, 11)
                pts.append((px, py))
            d.line(pts, fill=(74, 48, 32), width=2 if k < 2 else 1)
    return im


# ---------- небо и поверхность ----------
def sky(d, kind, t):
    tops = {"day": ((88, 146, 208), (180, 214, 236)), "night": ((8, 12, 30), (32, 38, 68)),
            "evening": ((56, 46, 92), (240, 132, 74))}
    a, b = tops[kind]
    steps = 7                                 # небо ступенями с точечным переходом, как в пиксель-арте
    k = (np.arange(GY, dtype=np.float32)[:, None] / GY) ** 1.2 * steps
    k = np.floor(k + BAYER[:GY]) / steps
    k = np.clip(k, 0, 1)[..., None]
    arr = np.array(a, np.float32) + (np.array(b, np.float32) - np.array(a, np.float32)) * k
    d._image.paste(Image.fromarray(arr.astype(np.uint8)).im, (0, 0, BW, GY))
    if kind == "night":
        r = random.Random(3)
        for i in range(120):
            x, y = r.randrange(BW), r.randrange(GY - 70)
            tw = 0.5 + 0.5 * math.sin(t * (1.5 + i % 5 * 0.4) + i)
            v = int(120 + 120 * tw)
            d.point((x, y), fill=(v, v, min(255, v + 20)))
            if i % 17 == 0:
                d.point([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], fill=(v // 2, v // 2, v // 2 + 20))
        d.ellipse([396, 64, 428, 96], fill=(236, 236, 214))
        d.ellipse([404, 72, 412, 80], fill=(214, 214, 196)); d.ellipse([414, 84, 420, 90], fill=(214, 214, 196))
    elif kind == "day":
        d.ellipse([408, 56, 444, 92], fill=(255, 244, 196))
        d.ellipse([414, 62, 438, 86], fill=(255, 250, 220))
        for i, (cx, cy, w) in enumerate(((80, 104, 70), (300, 66, 52), (220, 140, 44), (480, 150, 60))):
            x = (cx + t * (3 + i * 1.3)) % (BW + 120) - 60
            col, sh = (242, 246, 250), (210, 222, 236)
            d.ellipse([x, cy, x + w, cy + 16], fill=sh)
            d.ellipse([x + w * 0.2, cy - 10, x + w * 0.65, cy + 12], fill=col)
            d.ellipse([x + w * 0.45, cy - 6, x + w * 0.85, cy + 10], fill=col)
            d.rectangle([x + 4, cy + 8, x + w - 4, cy + 14], fill=sh)
    else:
        d.ellipse([290, 196, 342, 248], fill=(255, 196, 120))
        d.ellipse([300, 206, 332, 238], fill=(255, 218, 150))


def city(d, kind, burning, t):
    col = {"day": (138, 158, 182), "night": (24, 28, 48), "evening": (100, 64, 86)}[kind]
    r = random.Random(11)
    x = 0
    while x < 200:
        w, h = r.randrange(16, 30), r.randrange(30, 84)
        top = GY - 22 - h
        d.rectangle([x, top, x + w, GY - 20], fill=col)
        if r.random() < 0.3:
            d.rectangle([x + w // 2 - 1, top - 10, x + w // 2 + 1, top], fill=col)
        for wy in range(top + 5, GY - 26, 8):
            for wx in range(x + 3, x + w - 3, 6):
                lit = kind != "day" and r.random() < 0.18
                d.rectangle([wx, wy, wx + 2, wy + 3], fill=(250, 200, 110) if lit else lerp(col, (0, 0, 0), 0.15))
        x += w + 2
    if burning:
        for i in range(6):
            fx = 18 + i * 32
            fy = GY - 80 - (i % 2) * 18
            fl = 6 + 2.5 * math.sin(t * 7 + i) + 1.5 * math.sin(t * 13 + i * 2)
            d.ellipse([fx - fl, fy - fl * 2.2, fx + fl, fy + 3], fill=(255, 110, 36))
            d.ellipse([fx - fl * 0.5, fy - fl * 1.2, fx + fl * 0.5, fy + 2], fill=(255, 200, 90))
            for k in range(6):
                q = ((t * 0.5 + k / 6 + i * 0.13) % 1)
                sy = fy - 14 - q * 70
                rr = 4 + q * 8
                g = int(80 - q * 30)
                d.ellipse([fx - rr + q * 20, sy - rr, fx + rr + q * 20, sy + rr], fill=(g, g - 8, g - 4))


def house(d, kind):
    wall, roof = (132, 94, 62), (100, 54, 46)
    d.rectangle([8, 224, 124, GY], fill=wall)
    for y in range(226, GY, 7):
        d.line([(8, y), (124, y)], fill=(108, 76, 50))
    d.rectangle([92, 176, 104, 210], fill=(110, 70, 56)); d.rectangle([90, 172, 106, 177], fill=(80, 50, 40))
    d.polygon([(0, 228), (66, 176), (132, 228)], fill=roof)
    for k in range(5):
        y = 188 + k * 9
        hw = (y - 176) * 66 / 52
        d.line([(66 - hw, y), (66 + hw, y)], fill=(80, 42, 36))
    d.polygon([(80, 192), (102, 212), (88, 212)], fill=(30, 22, 26))         # дыра в крыше
    win = (255, 210, 120) if kind == "evening" else (44, 54, 66)
    d.rectangle([22, 242, 48, 268], fill=(84, 60, 40)); d.rectangle([25, 245, 45, 265], fill=win)
    d.line([(25, 245), (45, 265)], fill=(84, 60, 40), width=2); d.line([(45, 245), (25, 265)], fill=(84, 60, 40), width=2)
    d.rectangle([74, 250, 100, GY], fill=(72, 48, 34)); d.rectangle([94, 274, 96, 276], fill=(200, 170, 80))
    for i, x in enumerate(range(134, 200, 11)):                              # забор
        h = 30 if i != 3 else 18
        d.rectangle([x, GY - h, x + 6, GY], fill=(152, 114, 76))
        d.rectangle([x, GY - h, x + 1, GY], fill=(124, 92, 60))
        d.polygon([(x, GY - h), (x + 3, GY - h - 4), (x + 6, GY - h)], fill=(152, 114, 76))
    d.rectangle([130, GY - 22, 200, GY - 20], fill=(124, 90, 60))
    d.rectangle([130, GY - 10, 200, GY - 8], fill=(124, 90, 60))


def grass(d, kind, t, x0=0, x1=BW):
    g1, g2 = (78, 146, 60), (56, 112, 46)
    d.rectangle([x0, GY - 1, x1, GY + 3], fill=g1)
    d.rectangle([x0, GY + 4, x1, GY + 6], fill=g2)
    r = random.Random(21)
    for x in range(x0, x1, 3):
        h = r.randrange(2, 7)
        sw = math.sin(t * 1.5 + x * 0.07) * 1.2
        d.line([(x, GY), (x + sw, GY - h)], fill=g1 if r.random() < 0.6 else (100, 170, 70))


def room(d, box, finished, depth=1.0, side="right", seed=0):
    x0, y0, x1, y1 = box
    if depth <= 0:
        return
    if side == "right":
        x1 = x0 + int((x1 - x0) * min(1, depth))
    elif side == "down":
        y1 = y0 + int((y1 - y0) * min(1, depth))
    d.rounded_rectangle([x0, y0, x1, y1], 4, fill=(48, 33, 25))
    noise_dots(d, (x0 + 2, y0 + 2, x1 - 1, y1 - 1), [(58, 41, 31), (40, 27, 21), (64, 46, 34)],
               (x1 - x0) * (y1 - y0) // 12, seed, size=3)
    if finished:
        for i, x in enumerate(range(x0 + 2, x1 - 4, 10)):
            sh = (118, 84, 54) if i % 3 else (110, 78, 50)
            d.rectangle([x, y0 + 6, x + 9, y1 - 6], fill=sh)
            d.line([(x, y0 + 6), (x, y1 - 6)], fill=(82, 56, 36))
            for gy in range(y0 + 12, y1 - 8, 9):                             # волокна
                d.point((x + 3 + (gy * 7 + i) % 5, gy), fill=(100, 70, 44))
            d.point((x + 4, y0 + 9), fill=(60, 50, 44)); d.point((x + 4, y1 - 10), fill=(60, 50, 44))
        d.rectangle([x0, y0, x1, y0 + 5], fill=(96, 66, 42))                   # балка
        d.line([(x0, y0 + 5), (x1, y0 + 5)], fill=(66, 44, 28))
        for px in (x0 + 2, x1 - 7):                                          # стойки
            d.rectangle([px, y0, px + 5, y1], fill=(104, 72, 46))
            d.line([(px + 5, y0), (px + 5, y1)], fill=(70, 48, 30))
        d.rectangle([x0, y1 - 5, x1, y1], fill=(94, 64, 40))                   # пол
        d.line([(x0, y1 - 5), (x1, y1 - 5)], fill=(128, 92, 58))


def ladder(d, x, y0, y1):
    d.rectangle([x, y0, x + 2, y1], fill=(156, 112, 66)); d.rectangle([x + 12, y0, x + 14, y1], fill=(156, 112, 66))
    for y in range(int(y0) + 4, int(y1), 8):
        d.rectangle([x + 2, y, x + 12, y + 1], fill=(130, 90, 54))


def tunnel(d, p):
    """Второй выход: из комнаты 1 вправо-вверх к оврагу."""
    a, b = (380, 446), (496, 314)
    n = int(80 * p)
    for i in range(n + 1):
        k = i / 80
        x, y = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        d.ellipse([x - 8, y - 10, x + 8, y + 8], fill=(48, 33, 25))
    for i in range(0, n, 6):
        k = i / 80
        x, y = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        d.line([(x - 6, y + 7), (x + 6, y + 7)], fill=(96, 66, 42), width=2)
    return a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p


def zombie_list(n, t):
    """(x, поза, фаза, направление) для зомби на поверхности."""
    zs = []
    if n == 11:                               # толпа у люка
        r = random.Random(5)
        for i in range(15):
            x = 150 + i * 13 + r.randint(-4, 4) + math.sin(t * 0.9 + i) * 4
            zs.append((x, "walk", (t * 0.6 + i * 0.37) % 1, -1 if x > HATCH_X else 1))
        return zs
    count = {1: 3, 2: 5, 6: 3, 18: 3, 19: 3, 20: 3}.get(n, 2)
    for i in range(count):
        v = (11 + i * 4) * (1 if i % 2 == 0 else -1)
        span = BW + 80
        x = (i * 197 + v * t) % span - 40
        zs.append((x, "walk", (abs(v) * t / 22 + i * 0.31) % 1, 1 if v > 0 else -1))
    if n == 6:
        zs.append((HATCH_X + 6, "crouch", (t * 0.8) % 1, -1))
    return zs


def glow(L, x, y, r, s, col):
    x0, x1, y0, y1 = max(0, int(x - 3 * r)), min(BW, int(x + 3 * r)), max(0, int(y - 3 * r)), min(BH, int(y + 3 * r))
    yy, xx = np.ogrid[y0:y1, x0:x1]
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * r * r)) * s
    L[y0:y1, x0:x1] += g[..., None] * np.array(col, np.float32)


def flick(t, seed=0):
    return 0.9 + 0.06 * math.sin(t * 11 + seed) + 0.04 * math.sin(t * 23 + seed * 3)


# ---------- кадр ----------
def world(n, p, t):
    kind = "night" if n in NIGHT else "evening" if n in EVENING else "day"
    img = static_layer().copy()
    d = ImageDraw.Draw(img)
    sky(d, kind, t)
    city(d, kind, n <= 2, t)
    far = (54, 98, 84) if kind != "night" else (20, 36, 42)
    far2 = (44, 84, 72) if kind != "night" else (16, 28, 34)
    for x in range(200, 560, 17):
        pine(d, x, GY + 1, 50 + (x * 7) % 22, col=far, dark=far2, light=lerp(far, (255, 255, 255), 0.08))
    house(d, kind)
    # ---- подземелье ----
    room(d, CELLAR, False, seed=1)
    for sx in (192, 256):                     # полки с банками в погребе
        d.rectangle([sx - 2, 334, sx + 22, 336], fill=(112, 80, 50))
        for k in range(4):
            d.rounded_rectangle([sx + k * 5, 324, sx + 3 + k * 5, 333], 1, fill=(196, 92, 60 + k * 10))
            d.point((sx + 1 + k * 5, 326), fill=(240, 180, 150))
    dig1 = 0 if n < 4 else (p if n == 4 else 1)
    if dig1:
        room(d, SHAFT1, False, dig1 * 2.5, side="down", seed=2)
        if dig1 > 0.4:
            room(d, ROOM1, n >= 5, (dig1 - 0.4) / 0.6, side="right", seed=3)
        ladder(d, 225, 352, 400 if dig1 > 0.4 else 364 + 36 * dig1 * 2.5)
    ladder(d, 225, GY - 2, 352)
    dig2 = 0 if n < 8 else (p if n == 8 else 1)
    if dig2:
        room(d, SHAFT2, False, dig2 * 2.5, side="down", seed=4)
        if dig2 > 0.4:
            room(d, ROOM2, n >= 9, (dig2 - 0.4) / 0.6, side="right", seed=5)
        ladder(d, 337, 458, 524 if dig2 > 0.4 else 464 + 60 * dig2 * 2.5)
    tun = 0 if n < 12 else (p if n == 12 else 1)
    tun_tip = tunnel(d, tun) if tun else None
    ext = 0 if n < 13 else (min(1, p * 1.6) if n == 13 else 1)
    if ext:
        room(d, EXT2, False, ext, side="right", seed=6)
    if n >= 13 and ext >= 1:                  # бетон чужого бункера
        d.rectangle([428, 520, 444, 592], fill=(134, 134, 140))
        for y in range(522, 592, 10):
            d.line([(428, y), (444, y)], fill=(108, 108, 114))
        noise_dots(d, (428, 520, 444, 592), [(150, 150, 156), (116, 116, 122)], 60, 9)
    if n >= 15:
        x0, y0, x1, y1 = ANYA
        d.rectangle([x0 - 16, y0 - 8, x1, y1 + 6], fill=(134, 134, 140))
        noise_dots(d, (x0 - 16, y0 - 8, x1, y1 + 6), [(150, 150, 156), (116, 116, 122)], 300, 10)
        d.rectangle(ANYA, fill=(72, 74, 82))
        for x in range(x0, x1, 20):
            d.line([(x, y0), (x, y1)], fill=(62, 64, 72))
        d.rectangle([x0, y1 - 4, x1, y1], fill=(98, 100, 106))
        d.rounded_rectangle([424, 548, 446, 588], 5, fill=(48, 33, 25))   # пролом
        for cx, cy in ((427, 545), (439, 543), (446, 556), (422, 580), (445, 586)):
            d.rectangle([cx, cy, cx + 2, cy + 2], fill=(156, 156, 162))
        if n >= 16:                           # её лаз наверх
            for i in range(60):
                k = i / 59
                cx, cy = 528 + 10 * k, 516 - 210 * k
                d.ellipse([cx - 9, cy - 9, cx + 9, cy + 8], fill=(48, 33, 25))
        d.rounded_rectangle([458, 572, 504, 584], 3, fill=(96, 72, 120))     # её спальник
        d.rectangle([506, 560, 520, 584], fill=(80, 84, 70))                 # ящик
    # мебель и вещи
    lamp_on = n > 10 or (n == 10 and p > 0.55)
    if n >= 5:
        d.rounded_rectangle([130, 446, 186, 458], 3, fill=(160, 70, 60))     # матрас
        d.rectangle([130, 446, 186, 449], fill=(186, 92, 78))
        d.rounded_rectangle([132, 441, 148, 449], 3, fill=(224, 218, 200))
        d.rectangle([196, 446, 202, 458], fill=(122, 86, 54))                # тумбочка
        if not lamp_on or n >= 18:
            d.rectangle([197, 438, 200, 446], fill=(240, 236, 220))
            fl = int(2 + math.sin(t * 13) * 0.8)
            d.ellipse([197, 432 - fl, 200, 437], fill=(255, 200, 80))
    if n >= 9:                                # полка с консервами, печка, труба
        for sy in (426, 444):
            d.rectangle([250, sy, 304, sy + 2], fill=(90, 62, 38))
            for k in range(8):
                if (k + sy) % 5 != 0:
                    d.rectangle([252 + k * 6, sy - 9, 256 + k * 6, sy - 1], fill=(184, 190, 200))
                    d.rectangle([252 + k * 6, sy - 6, 256 + k * 6, sy - 4], fill=(200, 70, 60) if k % 2 else (230, 180, 60))
        d.rounded_rectangle([342, 430, 370, 462], 3, fill=(58, 58, 64))
        d.rectangle([348, 444, 364, 454], fill=(30, 26, 26))
        fl = 0.5 + 0.5 * math.sin(t * 9)
        d.rectangle([350, 448 - int(fl * 2), 362, 454], fill=(240, 120, 40)); d.rectangle([353, 450, 359, 454], fill=(255, 200, 90))
        d.rectangle([353, GY + 4, 358, 430], fill=(84, 84, 90)); d.line([(353, GY + 4), (353, 430)], fill=(110, 110, 118))
    if n >= 8 and (n > 8 or p > 0.7):         # ручей
        k = 1 if n > 8 else ease((p - 0.7) / 0.3)
        d.rectangle([160, 548, 166, 586], fill=(56, 116, 190))
        d.rectangle([166, 578, 166 + int(56 * k), 586], fill=(66, 136, 210))
        d.line([(168, 578), (166 + int(56 * k), 578)], fill=(150, 200, 240))
        for i in range(8):
            yy = 548 + ((t * 50 + i * 5) % 34)
            d.point((162 + i % 3, yy), fill=(180, 220, 255))
    if n >= 10:                               # велогенератор и лампы
        bx = 240
        for wx in (bx - 10, bx + 18):
            d.ellipse([wx - 10, 566, wx + 10, 586], outline=(34, 34, 34), width=2)
            a = t * 6
            d.line([(wx, 576), (wx + 8 * math.cos(a), 576 + 8 * math.sin(a))], fill=(120, 120, 120))
        d.line([(bx - 10, 576), (bx + 4, 562), (bx + 18, 576)], fill=(196, 44, 44), width=2)
        d.line([(bx + 4, 562), (bx + 3, 556)], fill=(196, 44, 44), width=2)
        d.rectangle([bx - 2, 554, bx + 8, 556], fill=(40, 40, 40))
        d.line([(bx + 18, 576), (bx + 18, 540), (300, 530)], fill=(34, 34, 34))
        d.line([(300, 524), (300, 532)], fill=(34, 34, 34)); d.line([(220, 400), (220, 410)], fill=(34, 34, 34))
        on = lamp_on and (n != 10 or math.sin(t * 40) > -0.3 or p > 0.7)
        for lx, ly in ((300, 532), (220, 410)):
            d.ellipse([lx - 3, ly, lx + 3, ly + 6], fill=(255, 238, 160) if on else (120, 120, 110))
    if n >= 17:                               # грядки, кролики, радио
        for gx in range(300, 396, 16):
            d.rectangle([gx, 574, gx + 13, 586], fill=(94, 64, 42)); d.rectangle([gx, 574, gx + 13, 575], fill=(70, 48, 32))
            for k in range(4):
                h = 6 + (k * 3 + gx) % 5
                sw = math.sin(t * 2 + gx + k) * 0.8
                d.line([(gx + 2 + k * 3, 574), (gx + 2 + k * 3 + sw, 574 - h)], fill=(90, 192, 82))
                d.point((gx + 2 + k * 3 + sw, 574 - h), fill=(140, 230, 110))
        d.rectangle([300, 528, 392, 530], fill=(210, 120, 240))
        d.rectangle([300, 428, 332, 458], outline=(160, 160, 160))
        for k in range(1, 4):
            d.line([(300 + k * 8, 428), (300 + k * 8, 458)], fill=(130, 130, 130))
        for k, rx in enumerate((306, 318)):
            ry = 452 - int(abs(math.sin(t * 2.4 + k)) * 4)
            d.ellipse([rx, ry - 2, rx + 8, ry + 4], fill=(238, 234, 228))
            d.ellipse([rx + 5, ry - 5, rx + 10, ry], fill=(238, 234, 228))
            d.line([(rx + 7, ry - 9), (rx + 7, ry - 5)], fill=(238, 234, 228), width=2)
            d.point((rx + 8, ry - 3), fill=(200, 60, 80))
        d.rounded_rectangle([272, 446, 292, 458], 2, fill=(74, 78, 62))
        d.ellipse([275, 449, 281, 455], fill=(40, 40, 40)); d.rectangle([284, 449, 289, 451], fill=(200, 180, 90))
        d.line([(289, 446), (296, 432)], fill=(40, 40, 40))
    if n >= 18:                               # стол
        d.rectangle([214, 440, 268, 444], fill=(144, 102, 64)); d.line([(214, 444), (268, 444)], fill=(100, 70, 44))
        d.rectangle([218, 444, 221, 458], fill=(112, 78, 48)); d.rectangle([261, 444, 264, 458], fill=(112, 78, 48))
        d.rounded_rectangle([238, 430, 248, 440], 2, fill=(232, 170, 60)); d.rectangle([238, 433, 248, 436], fill=(200, 80, 50))
        d.rectangle([226, 432, 229, 440], fill=(240, 236, 220))
        fl = int(2 + math.sin(t * 13 + 1) * 0.8)
        d.ellipse([226, 426 - fl, 229, 431], fill=(255, 200, 80))
    # ---- поверхность ----
    grass(d, kind, t)
    gd = 0 if n < 4 else (p if n == 4 else 1)
    for i, gx in enumerate(range(262, 350, 18)):       # грядки и кучки земли
        d.rectangle([gx, GY - 4, gx + 14, GY], fill=(94, 64, 42))
        h = 9 * ease(gd * 2 - i * 0.2) if gd else 0
        if h > 0.5:
            d.polygon([(gx - 2, GY - 3), (gx + 7, GY - 3 - h), (gx + 16, GY - 3)], fill=(114, 78, 48))
            d.line([(gx + 2, GY - 4 - h * 0.5), (gx + 7, GY - 3 - h)], fill=(134, 96, 62))
    metal = n > 7 or (n == 7 and p > 0.45)
    hc = (124, 128, 136) if metal else (124, 86, 52)
    d.rectangle([HATCH_X - 14, GY - 4, HATCH_X + 16, GY + 1], fill=hc)
    d.line([(HATCH_X - 14, GY - 4), (HATCH_X + 16, GY - 4)], fill=lerp(hc, (255, 255, 255), 0.25))
    if metal:
        for bx in (HATCH_X - 10, HATCH_X + 12):
            d.point((bx, GY - 2), fill=(70, 72, 80))
        d.rectangle([HATCH_X - 2, GY - 7, HATCH_X + 4, GY - 4], fill=(90, 92, 100))
    else:
        for bx in range(HATCH_X - 12, HATCH_X + 16, 7):
            d.line([(bx, GY - 4), (bx, GY)], fill=(96, 66, 40))
    if n >= 9:                                # куст, прячущий трубу
        d.ellipse([336, GY - 18, 376, GY + 2], fill=(46, 108, 52)); d.ellipse([344, GY - 26, 372, GY - 4], fill=(60, 132, 62))
        d.ellipse([350, GY - 22, 360, GY - 14], fill=(84, 160, 80))
        if kind == "day":
            for k in range(6):
                q = (t * 0.35 + k / 6) % 1
                sy = GY - 30 - q * 80
                rr = 3 + q * 7
                c = int(170 + q * 60)
                d.ellipse([355 - rr + q * 16, sy - rr, 355 + rr + q * 16, sy + rr], fill=(c, c, c))
    if n >= 12:                               # овраг
        d.polygon([(472, GY - 1), (486, GY + 16), (510, GY + 16), (524, GY - 1)], fill=(48, 33, 25))
    for x, s in ((404, 108), (456, 124), (512, 100)):
        pine(d, x, GY, s)
    # ---- люди ----
    ph = (t * 1.3) % 1
    H = {}
    if n == 1:
        k = ease(min(1, p * 1.5))
        H["hero"] = (400 - 168 * k, GY, "walk" if k < 1 else "stand", -1)
    elif n == 2:
        H["hero"] = (250, F_CELLAR, "sit", 1)
    elif n == 3:
        H["hero"] = (246, F_CELLAR, "stand", 1)
    elif n == 4:
        if dig1 < 0.4:
            H["hero"] = (244, 364 + 36 * min(1, dig1 * 2.5), "dig", 1)
        else:
            H["hero"] = (max(132, ROOM1[0] + (ROOM1[2] - ROOM1[0]) * (dig1 - 0.4) / 0.6 - 14), F_ROOM1, "dig", 1)
    elif n == 5:
        H["hero"] = (162, F_ROOM1 - 6, "sit", 1)
    elif n == 6:
        H["hero"] = (244, F_ROOM1, "up", -1)
    elif n == 7:
        H["hero"] = (244, F_CELLAR, "up", 1)
    elif n == 8:
        if dig2 < 0.4:
            H["hero"] = (346, 464 + 60 * min(1, dig2 * 2.5), "dig", 1)
        else:
            H["hero"] = (min(max(ROOM2[0] + (ROOM2[2] - ROOM2[0]) * (dig2 - 0.4) / 0.6, 190), 386), F_ROOM2, "dig", -1)
    elif n == 9:
        H["hero"] = (326, F_ROOM1, "stand", 1)
    elif n == 10:
        H["hero"] = (244, F_ROOM2 - 8, "pedal", 1)
    elif n == 11:
        H["hero"] = (162, F_ROOM1 - 6, "sit", 1)
    elif n == 12:
        H["hero"] = (tun_tip[0] - 12, tun_tip[1] + 10, "dig", 1)
    elif n == 13:
        H["hero"] = (EXT2[0] + (EXT2[2] - EXT2[0]) * ext - 12, F_ROOM2, "dig", 1)
    elif n == 14:
        H["hero"] = (412, F_ROOM2, "ear", 1)
    elif n in (15, 16):
        H["hero"] = (404, F_ROOM2, "stand", 1)
        H["anya"] = (468, 588, "knife" if n == 15 else "stand", -1)
    elif n == 17:
        H["hero"] = (340, F_ROOM2, "dig", 1)
        H["anya"] = (266, F_ROOM1, "stand", 1)
    elif n == 18:
        H["hero"] = (206, F_ROOM1 - 6, "sit", 1)
        H["anya"] = (276, F_ROOM1 - 6, "sit", -1)
    else:
        H["hero"] = (238, F_ROOM2, "stand", 1)
        H["anya"] = (270, F_ROOM2, "stand", -1)
    xs = [v[0] for v in H.values()]
    ys = [v[1] for v in H.values()]
    focus = (sum(xs) / len(xs), sum(ys) / len(ys))
    for who, (x, y, pose, f) in H.items():
        put(img, who, pose, (t * 0.9) % 1 if pose == "pedal" else (t * 0.55) % 1 if pose in ("stand", "sit", "ear", "knife") else ph, x, y, f)
        if pose == "dig":                     # летящие комья земли
            for i in range(4):
                q = (ph * 2 + i * 0.25) % 1
                dx = (16 + q * 22) * f
                dy = -10 - 26 * q + 40 * q * q
                d.rectangle([x + dx, y + dy, x + dx + 2, y + dy + 2], fill=(132, 92, 56))
    for x, pose, phz, f in zombie_list(n, t):
        put(img, "zombie", pose, phz, x, GY, f)
    # ---- свет ----
    a = np.asarray(img).astype(np.float32) / 255
    amb_sky = {"day": 1.0, "evening": 0.94, "night": 0.66}[kind]
    amb_ground = {"day": 0.84, "evening": 0.72, "night": 0.44}[kind]
    L = np.empty((BH, BW, 3), np.float32)
    L[:GY] = amb_sky
    L[GY:] = amb_ground
    if kind == "night":
        L[:GY] *= np.array([0.85, 0.9, 1.25], np.float32)
        L[GY:] *= np.array([0.9, 0.92, 1.08], np.float32)
    warm, lamp = (1.0, 0.76, 0.42), (1.0, 0.92, 0.7)
    if n == 2:
        glow(L, 256, 344, 28, 0.9 * flick(t), (1.0, 0.95, 0.8))
    if n >= 5 and (not lamp_on or n >= 18):
        glow(L, 199, 436, 40, 0.85 * flick(t), warm)
    if lamp_on:
        glow(L, 220, 420, 70, 0.85, lamp)
        glow(L, 300, 544, 70, 0.85, lamp)
    if n >= 9:
        glow(L, 356, 448, 24, 0.7 * flick(t, 2), (1.0, 0.6, 0.3))
    if n >= 15:
        glow(L, 490, 548, 40, 0.6, (0.8, 0.9, 1.0))
    if n >= 17:
        glow(L, 346, 556, 40, 0.5, (0.9, 0.6, 1.0))
    if n >= 18:
        glow(L, 228, 428, 34, 0.6 * flick(t, 5), warm)
    L = 1.3 * np.tanh(L / 1.3)              # мягкий потолок света — без пересвета
    L = np.floor(L * 6 + BAYER[..., None]) / 6  # свет ступенями с точечным переходом
    out = np.clip(a * L, 0, 1)
    img = Image.fromarray((out * 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    if lamp_on or n >= 5:                     # пылинки в свете
        r = random.Random(4)
        for i in range(18):
            bx, by = r.choice(((130, 404, 250, 56), (180, 528, 210, 54)))[:2], None
            box = (130, 404, 250, 56) if i % 2 == 0 else (180, 528, 210, 54)
            x = box[0] + (r.random() * box[2] + t * 4 * (0.5 + r.random())) % box[2]
            y = box[1] + (r.random() * box[3] + math.sin(t * 0.8 + i) * 6) % box[3]
            d.point((x, y), fill=(255, 240, 200, 110))
    if n == 11:                               # свет из щелей люка
        for k, dx in enumerate((-10, 0, 12)):
            al = int(60 + 25 * math.sin(t * 2 + k))
            d.polygon([(HATCH_X + dx, GY - 3), (HATCH_X + dx - 22, GY - 170), (HATCH_X + dx + 16, GY - 170)], fill=(255, 230, 150, al))
    if n == 6:                                # сыплется земля
        for i in range(16):
            yy = 364 + ((t * 60 + i * 13) % 96)
            d.rectangle([226 + (i * 7) % 20, yy, 227 + (i * 7) % 20, yy + 1], fill=(150, 108, 64, 255))
    if n in (14, 19):                         # стук: расходящиеся круги
        cx, cy = (436, 560) if n == 14 else (256, 640)
        ph3 = (t * 1.3) % 1
        if ph3 < 0.6:
            for k in range(3):
                rr = 6 + ((ph3 * 3 - k * 0.5) % 1.5) * 28
                al = int(160 * (1 - rr / 48))
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, max(0, al)), width=2)
    if n == 13 and ext >= 1:                  # искры от лопаты
        for i in range(8):
            if math.sin(t * 25 + i * 1.7) > 0.4:
                d.rectangle([424 + i % 4 * 2, 548 + i * 3, 425 + i % 4 * 2, 549 + i * 3], fill=(255, 230, 120, 255))
    if n == 20:                               # трещина и глаза
        crack = [(252, 588), (244, 604), (258, 624), (246, 648), (262, 672), (254, 700)]
        k = ease(p * 1.6) * (len(crack) - 1)
        m = int(k)
        pts = crack[:m + 1]
        if m < len(crack) - 1:
            a0, b0 = crack[m], crack[m + 1]
            f = k - m
            pts.append((a0[0] + (b0[0] - a0[0]) * f, a0[1] + (b0[1] - a0[1]) * f))
        if len(pts) > 1:
            d.line(pts, fill=(8, 6, 8, 255), width=4)
            d.line([(x + 2, y) for x, y in pts], fill=(110, 104, 112, 255), width=1)
        if p > 0.72:
            al = int(255 * ease((p - 0.72) / 0.12))
            for ex in (244, 262):
                d.rectangle([ex, 684, ex + 3, 686], fill=(255, 40, 30, al))
                d.rectangle([ex - 2, 682, ex + 5, 688], fill=(255, 40, 30, al // 4))
    return img, focus


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "test"
    for n in range(1, 21):
        world(n, 0.8, 1.0)[0].resize((BW * K, BH * K), Image.NEAREST).save(f"{out}_{n:02d}.png")
