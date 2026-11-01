#!/usr/bin/env python3
"""«72 ЧАСА» — серия 1. Вертикальный TikTok (1080x1920) под озвучку voice.mp3.

Тайминги фраз берутся из timings.json (собирается align.py по паузам в озвучке).
Графика и звуковые эффекты генерируются процедурно, сборка — ffmpeg.
Запуск:  python3 tiktok/series/episode1.py [выход.mp4]
"""
import json
import math
import os
import re
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "episode1_72_chasa.mp4")
VOICE = os.path.join(HERE, "voice.mp3")
W, H = 720, 1280
FPS = 30
SR = 44100
VOICE_END = 116.61
DUR = 120.5
NFRAMES = int(DUR * FPS)

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_fc = {}


def font(size, mono=False):
    k = (size, mono)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT_M if mono else FONT_B, int(size))
    return _fc[k]


# ------------------------------------------------------------------ timings
LINES = json.load(open(os.path.join(HERE, "timings.json"), encoding="utf8"))
VOW = re.compile("[аеёиоуыэюяАЕЁИОУЫЭЮЯ]")


def _words():
    out = []
    for li, L in enumerate(LINES):
        ws = L["text"].split()
        syl = [max(1, len(VOW.findall(w))) for w in ws]
        tot = sum(syl)
        t = L["start"]
        span = L["end"] - L["start"]
        for w, s in zip(ws, syl):
            d = span * s / tot
            out.append(dict(w=w, s=t, e=t + d, line=li))
            t += d
    return out


WORDS = _words()


def line_t(prefix):
    """Время начала строки, начинающейся с prefix."""
    for L in LINES:
        if L["text"].startswith(prefix):
            return L["start"]
    raise KeyError(prefix)


def word_t(prefix, after=0.0):
    for w in WORDS:
        if w["s"] >= after - 0.01 and w["w"].strip("«»,.!?…").lower().startswith(prefix.lower()):
            return w["s"]
    raise KeyError(prefix)


# ключевые моменты
T_RULE1 = line_t("Правило номер один")
T_ITEMS = line_t("Тебе нужны")
T_PHONE = line_t("Заряди")
T_WATER = line_t("Вода важнее")
T_TRUST = line_t("Но есть")
T_KNOCK = line_t("Стук")
T_FRIEND = line_t("«Эй")
T_THREE = line_t("Три удара")
T_IKNOW = line_t("«Я знаю")
T_RULE2 = line_t("Правило номер два")
T_NIGHT = line_t("Наступает")
T_MSG1 = line_t("«Всем")
T_LOST = line_t("Сигнал")
T_TUNE = line_t("Ты настраиваешь")
T_MSG2 = line_t("«Если")
T_RULE3 = line_t("Правило номер три")
T_OFF = line_t("Ты выключаешь")
T_VIBR = line_t("Внезапно")
T_SCREEN = line_t("На экране")
T_DONT = line_t("«НЕ СМОТРИ")
T_EYES = line_t("Ты медленно")
T_NOONE = line_t("На улице")
T_CREAK = line_t("Но за твоей")
T_WORST = line_t("И знаешь")
T_LAST = line_t("И станешь")
ITEM_T = [word_t(p, T_ITEMS) for p in ("вода", "консервы", "аптечка", "фонарь", "батарейки")]

R = np.random.default_rng(0)  # пересоздаётся на каждый кадр


# -------------------------------------------------------------------- utils
def lerp(a, b, t):
    return a + (b - a) * t


def c01(x):
    return max(0.0, min(1.0, x))


def ease(t):
    t = c01(t)
    return t * t * (3 - 2 * t)


def back(t):
    """Пружинящее появление 0→1 с перелётом."""
    t = c01(t)
    s = 1.7
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def vgrad(top, bottom):
    k = np.linspace(0, 1, H)[:, None, None]
    g = np.array(top, np.float32)[None, None] * (1 - k) + np.array(bottom, np.float32)[None, None] * k
    return np.repeat(g, W, axis=1)


def rgba(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


yy, xx = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIGN = np.clip(1.15 - 0.55 * _d ** 1.6, 0.2, 1.0)[..., None].astype(np.float32)
_g = np.random.default_rng(5)
GRAIN = [_g.normal(0, 1, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]
SCAN = (1 - 0.15 * (np.arange(H) % 4 < 2))[:, None, None].astype(np.float32)


def text_c(d, y, txt, size, fill=(255, 255, 255), stroke=4, mono=False, x=None, anchor_mid=True):
    f = font(size, mono)
    for i, line in enumerate(txt.split("\n")):
        bb = d.textbbox((0, 0), line, font=f, stroke_width=stroke)
        tw = bb[2] - bb[0]
        px = (W - tw) / 2 if x is None else (x - tw / 2 if anchor_mid else x)
        d.text((px, y + i * size * 1.22), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def glow(img, draw_fn, radius=18, strength=1):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        img.alpha_composite(g)
    img.alpha_composite(layer)


def zoom(arr, z, cx=W / 2, cy=H / 2):
    if abs(z - 1) < 1e-3:
        return arr
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    w2, h2 = W / z, H / z
    cx = min(max(cx, w2 / 2), W - w2 / 2)
    cy = min(max(cy, h2 / 2), H - h2 / 2)
    box = (cx - w2 / 2, cy - h2 / 2, cx + w2 / 2, cy + h2 / 2)
    return np.asarray(im.resize((W, H), Image.BILINEAR, box=box), np.float32)


# --------------------------------------------------------- static backdrops
def skyline(seed, base, hmin, hmax, color, ruined=False):
    r = np.random.default_rng(seed)
    img = Image.new("RGBA", (W + 200, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = -20
    wins = []
    while x < W + 200:
        bw = int(r.integers(50, 120)); bh = int(r.integers(hmin, hmax)); top = base - bh
        if ruined:
            pts = [(x, base), (x, top + r.integers(0, 60))] + \
                  [(x + bw * k / 5, top + r.integers(0, 120)) for k in range(1, 5)] + \
                  [(x + bw, top + r.integers(20, 100)), (x + bw, base)]
            d.polygon(pts, fill=color)
        else:
            d.rectangle((x, top, x + bw, base), fill=color)
            for wy in range(top + 14, base - 10, 24):
                for wx in range(x + 8, x + bw - 10, 16):
                    if r.random() < 0.2:
                        wins.append((wx, wy, r.random()))
        x += bw + int(r.integers(-10, 8))
    return img, wins


CITY_B, _ = skyline(11, 900, 250, 520, (60, 25, 25, 255), ruined=True)
CITY_F, CITY_W = skyline(12, 980, 150, 560, (14, 8, 10, 255))
ASH = np.random.default_rng(9).random((220, 4))


def ash(img, t, color=(220, 200, 180), n=220, wind=30):
    d = ImageDraw.Draw(img)
    for i in range(n):
        x0, y0, sp, sz = ASH[i]
        y = (y0 * H + t * (50 + sp * 110)) % H
        x = (x0 * W + t * wind + 15 * math.sin(t * 1.2 + i)) % W
        r = 1 + sz * 2.6
        d.ellipse((x - r, y - r, x + r, y + r), fill=color + (int(90 + 140 * sz),))


# -------------------------------------------------------------- props
def draw_phone(d, cx, cy, s=1.0, screen=(20, 20, 30)):
    w, h = 300 * s, 600 * s
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), int(40 * s), fill=(15, 15, 18, 255),
                        outline=(80, 80, 90, 255), width=int(4 * s))
    d.rounded_rectangle((cx - w / 2 + 14 * s, cy - h / 2 + 14 * s, cx + w / 2 - 14 * s, cy + h / 2 - 14 * s),
                        int(30 * s), fill=screen + (255,))
    d.rounded_rectangle((cx - 40 * s, cy - h / 2 + 24 * s, cx + 40 * s, cy - h / 2 + 44 * s), 10, fill=(0, 0, 0, 255))
    return (cx - w / 2 + 14 * s, cy - h / 2 + 14 * s, cx + w / 2 - 14 * s, cy + h / 2 - 14 * s)


def item_icon(d, k, cx, cy, s=1.0, a=255):
    if k == 0:  # вода
        d.rounded_rectangle((cx - 40 * s, cy - 70 * s, cx + 40 * s, cy + 90 * s), int(22 * s), fill=(80, 170, 255, a),
                            outline=(200, 235, 255, a), width=int(4 * s))
        d.rectangle((cx - 18 * s, cy - 100 * s, cx + 18 * s, cy - 70 * s), fill=(30, 90, 220, a))
        d.rectangle((cx - 40 * s, cy - 10 * s, cx + 40 * s, cy + 30 * s), fill=(255, 255, 255, a))
        d.text((cx - 28 * s, cy - 8 * s), "H₂O", font=font(30 * s), fill=(30, 90, 220, a))
    elif k == 1:  # консервы
        d.rectangle((cx - 55 * s, cy - 60 * s, cx + 55 * s, cy + 60 * s), fill=(160, 160, 170, a))
        d.ellipse((cx - 55 * s, cy - 75 * s, cx + 55 * s, cy - 45 * s), fill=(210, 210, 220, a))
        d.rectangle((cx - 55 * s, cy - 25 * s, cx + 55 * s, cy + 35 * s), fill=(200, 60, 40, a))
        d.text((cx - 42 * s, cy - 20 * s), "ТУШ.", font=font(32 * s), fill=(255, 230, 200, a))
    elif k == 2:  # аптечка
        d.rounded_rectangle((cx - 75 * s, cy - 55 * s, cx + 75 * s, cy + 65 * s), int(16 * s), fill=(220, 40, 40, a))
        d.rectangle((cx - 30 * s, cy - 75 * s, cx + 30 * s, cy - 55 * s), outline=(220, 40, 40, a), width=int(8 * s))
        d.rectangle((cx - 12 * s, cy - 35 * s, cx + 12 * s, cy + 45 * s), fill=(255, 255, 255, a))
        d.rectangle((cx - 40 * s, cy - 7 * s, cx + 40 * s, cy + 17 * s), fill=(255, 255, 255, a))
    elif k == 3:  # фонарь
        d.polygon([(cx + 30 * s, cy - 20 * s), (cx + 160 * s, cy - 70 * s), (cx + 160 * s, cy + 70 * s),
                   (cx + 30 * s, cy + 20 * s)], fill=(255, 240, 160, a // 3))
        d.rounded_rectangle((cx - 90 * s, cy - 18 * s, cx + 10 * s, cy + 18 * s), int(8 * s), fill=(50, 50, 55, a))
        d.polygon([(cx + 10 * s, cy - 18 * s), (cx + 35 * s, cy - 30 * s), (cx + 35 * s, cy + 30 * s),
                   (cx + 10 * s, cy + 18 * s)], fill=(70, 70, 75, a))
        d.ellipse((cx + 26 * s, cy - 30 * s, cx + 42 * s, cy + 30 * s), fill=(255, 250, 200, a))
    elif k == 4:  # батарейки
        for off in (-35, 35):
            x = cx + off * s
            d.rectangle((x - 26 * s, cy - 70 * s, x + 26 * s, cy + 70 * s), fill=(30, 30, 30, a))
            d.rectangle((x - 26 * s, cy - 70 * s, x + 26 * s, cy - 20 * s), fill=(240, 180, 30, a))
            d.rectangle((x - 9 * s, cy - 82 * s, x + 9 * s, cy - 70 * s), fill=(190, 190, 190, a))
            d.text((x - 10 * s, cy + 10 * s), "+", font=font(34 * s), fill=(240, 180, 30, a))


ITEM_NAMES = ["ВОДА", "КОНСЕРВЫ", "АПТЕЧКА", "ФОНАРЬ", "БАТАРЕЙКИ"]


def silhouette(d, cx, base, s=1.0, col=(5, 3, 3, 255), eye=None):
    """Фигура в капюшоне и противогазе, анфас."""
    d.polygon([(cx - 120 * s, base), (cx - 95 * s, base - 330 * s), (cx - 60 * s, base - 390 * s),
               (cx + 60 * s, base - 390 * s), (cx + 95 * s, base - 330 * s), (cx + 120 * s, base)], fill=col)
    hc = (cx, base - 460 * s)
    d.ellipse((hc[0] - 72 * s, hc[1] - 90 * s, hc[0] + 72 * s, hc[1] + 80 * s), fill=col)
    d.ellipse((hc[0] - 40 * s, hc[1] + 30 * s, hc[0] + 40 * s, hc[1] + 105 * s), fill=col)  # фильтр
    if eye:
        for sx in (-1, 1):
            ex, ey = hc[0] + sx * 30 * s, hc[1] - 5 * s
            d.ellipse((ex - 20 * s, ey - 16 * s, ex + 20 * s, ey + 16 * s), fill=eye)


# ------------------------------------------------------------ scenes
def sc_intro(t):
    """0 – 17 c: пробуждение, рухнувший город, таймер 72 часа."""
    if t < 4.5:
        # комната, рассвет за окном, открытие глаз
        img = rgba(vgrad((25, 20, 30), (10, 8, 12)))
        d = ImageDraw.Draw(img)
        glow(img, lambda g: g.rectangle((200, 260, 520, 640), fill=(255, 120, 50, 230)), 40)
        d.rectangle((200, 260, 520, 640), outline=(20, 15, 15, 255), width=16)
        d.line((360, 260, 360, 640), fill=(20, 15, 15, 255), width=12)
        d.line((200, 450, 520, 450), fill=(20, 15, 15, 255), width=12)
        img.alpha_composite(CITY_B.crop((100, 300, 420, 680)).resize((304, 364)), (208, 268))
        d.rectangle((60, 930, 660, 1280), fill=(30, 25, 35, 255))  # кровать
        d.rounded_rectangle((90, 880, 330, 980), 30, fill=(200, 200, 210, 255))
        arr = np.asarray(img.convert("RGB"), np.float32)
        blur = max(0.0, 1 - t / 2.5)
        if blur > 0:
            arr = np.asarray(Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(14 * blur)), np.float32)
        # веки
        op = ease(t / 1.2) * 0.6 + (ease((t - 1.6) / 0.6) * 0.4 if t > 1.6 else 0)
        if 2.4 < t < 2.6:
            op *= 0.2  # моргание
        lid = int((H / 2) * (1 - op))
        if lid > 0:
            arr[:lid] = 0
            arr[H - lid:] = 0
        img = rgba(arr)
        if t > 1.6:
            d = ImageDraw.Draw(img)
            a = int(255 * ease((t - 1.6) / 0.5) * c01((4.6 - t) / 0.4))
            ov = Image.new("RGBA", img.size); od = ImageDraw.Draw(ov)
            text_c(od, 110, "72 ЧАСА", 92, fill=(255, 60, 40, a), stroke=6)
            text_c(od, 225, "СЕРИЯ 1 · ПЕРВЫЕ ЧАСЫ", 30, fill=(255, 255, 255, a), stroke=3)
            img.alpha_composite(ov)
        return img, dict(grain=10)
    if t < 9.5:
        lt = t - 4.5
        k = ease(lt / 2)
        img = rgba(vgrad((50, 15, 10), (230, 90, 30)))
        d = ImageDraw.Draw(img)
        # дым
        sm = Image.new("RGBA", img.size); sd = ImageDraw.Draw(sm)
        for i in range(9):
            x = (i * 97 + t * 15) % (W + 200) - 100
            y = 450 - (t * 20 + i * 60) % 300
            sd.ellipse((x - 120, y - 80, x + 120, y + 80), fill=(30, 20, 20, 140))
        img.alpha_composite(sm.filter(ImageFilter.GaussianBlur(30)))
        img.alpha_composite(CITY_B, (-60 - int(t * 6), 0))
        fr = CITY_F.copy(); fd = ImageDraw.Draw(fr)
        for wx, wy, rv in CITY_W:
            if rv < 0.25:
                fl = 0.6 + 0.4 * math.sin(t * 9 + rv * 80)
                fd.rectangle((wx, wy, wx + 8, wy + 11), fill=(255, int(120 * fl), 20, 255))
        img.alpha_composite(fr, (-100 - int(t * 10), 0))
        d = ImageDraw.Draw(img)
        d.rectangle((0, 978, W, H), fill=(10, 6, 6, 255))
        ash(img, t, color=(255, 160, 90), n=120, wind=60)
        # штампы
        stamps = [(word_t("Связи"), "НЕТ СЕТИ", (255, 70, 50), -8, 200),
                  (word_t("Магазины"), "ЗАКРЫТО", (255, 200, 40), 6, 370),
                  (word_t("паника"), "ПАНИКА", (255, 255, 255), -4, 540)]
        for ts, txt, col, ang, y in stamps:
            if t >= ts:
                sc = 1 + 1.5 * (1 - ease((t - ts) / 0.18))
                lay = Image.new("RGBA", (520, 150)); ld = ImageDraw.Draw(lay)
                ld.rounded_rectangle((10, 10, 510, 140), 18, outline=col + (255,), width=10, fill=(0, 0, 0, 120))
                text_c(ld, 30, txt, 76, fill=col + (255,), stroke=0, x=260)
                lay = lay.rotate(ang, expand=True, resample=Image.BICUBIC)
                lay = lay.resize((int(lay.width * sc * 0.8), int(lay.height * sc * 0.8)))
                img.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(y - lay.height / 2 + 60)))
        return img, dict(grain=12, shake=2)
    # таймер 72:00:00
    lt = t - 9.5
    img = rgba(vgrad((20, 0, 0), (0, 0, 0)))
    secs = 72 * 3600 - max(0.0, lt - 0.6) * 3600 * 0.6
    hh, rem = divmod(int(secs), 3600); mm, ss = divmod(rem, 60)
    s = f"{hh:02d}:{mm:02d}:{ss:02d}"
    pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
    glow(img, lambda g: text_c(g, 470, s, 120, fill=(255, int(40 + 60 * pulse), 30, 255), stroke=0, mono=True), 22, 2)
    d = ImageDraw.Draw(img)
    text_c(d, 640, "ДО ТОГО, ЧТО БУДЕТ ДАЛЬШЕ", 34, fill=(255, 200, 190), stroke=2)
    if t > line_t("И первая"):
        k = ease((t - line_t("И первая")) / 0.4)
        text_c(d, 760, "ОШИБКА = КОНЕЦ", 60, fill=(255, 255, 255, int(255 * k)), stroke=4)
    z = 1 + 0.03 * lt
    return img, dict(grain=12, zoom=z, chroma=2, scan=True)


def rule_card(t, t0, num, sub):
    lt = t - t0
    img = rgba(vgrad((120, 0, 0), (15, 0, 0)))
    d = ImageDraw.Draw(img)
    for i in range(-10, 30):  # предупреждающие полосы
        x = i * 60 + (lt * 80) % 60
        d.polygon([(x, 0), (x + 30, 0), (x - 30, 60), (x - 60, 60)], fill=(255, 200, 0, 255))
        d.polygon([(x, H - 60), (x + 30, H - 60), (x - 30, H), (x - 60, H)], fill=(255, 200, 0, 255))
    sc = 1 + 2.5 * (1 - ease(lt / 0.2))
    lay = Image.new("RGBA", (W, 420)); ld = ImageDraw.Draw(lay)
    text_c(ld, 20, "ПРАВИЛО", 90, stroke=6)
    text_c(ld, 130, f"№{num}", 220, fill=(255, 220, 40, 255), stroke=8)
    lay = lay.resize((int(W * sc), int(420 * sc)))
    img.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(380 - (lay.height - 420) / 2)))
    if lt > 0.5:
        text_c(ImageDraw.Draw(img), 850, sub, 44, fill=(255, 255, 255, int(255 * ease((lt - 0.5) / 0.3))), stroke=4)
    return img, dict(grain=10, shake=10 * max(0, 1 - lt / 0.4))


def sc_rule1(t):
    if t < T_ITEMS - 1.9:
        return rule_card(t, T_RULE1, 1, "ТОЛЬКО НУЖНОЕ")
    if t < T_ITEMS:
        # «Забудь о бесполезных вещах»: хлам перечёркивается
        img = rgba(vgrad((35, 35, 40), (12, 12, 15)))
        d = ImageDraw.Draw(img)
        junk = ["ПРИСТАВКА", "ДУХИ", "НОУТБУК", "ДЕНЬГИ?"]
        st = T_ITEMS - 1.9
        for i, j in enumerate(junk):
            y = 300 + i * 150
            text_c(d, y, j, 64, fill=(170, 170, 170), stroke=3)
            k = ease((t - st - 0.25 * i) / 0.25)
            if k > 0:
                d.line((150, y + 40, 150 + 420 * k, y + 40), fill=(255, 40, 40, 255), width=12)
        return img, dict(grain=10)
    if t < T_WATER:
        img = rgba(vgrad((28, 36, 40), (8, 10, 12)))
        d = ImageDraw.Draw(img)
        # стол
        d.rectangle((0, 820, W, H), fill=(55, 40, 30, 255))
        for i in range(5):
            d.line((0, 860 + i * 70, W, 860 + i * 70), fill=(45, 32, 24, 255), width=3)
        if t < T_PHONE:
            pos = [(180, 330), (520, 330), (180, 620), (520, 620), (360, 960)]
            for k, ts in enumerate(ITEM_T):
                if t >= ts - 0.05:
                    s = back((t - ts + 0.05) / 0.35)
                    cx, cy = pos[k]
                    glow(img, lambda g, k=k, cx=cx, cy=cy, s=s: item_icon(g, k, cx, cy, s * 1.1), 14)
                    text_c(ImageDraw.Draw(img), cy + 110, ITEM_NAMES[k], 30, fill=(255, 230, 120), stroke=3,
                           x=cx)
                    if ts <= t < ts + 0.3:
                        dd = ImageDraw.Draw(img)
                        dd.text((cx + 70, cy - 120), "✓", font=font(70), fill=(80, 255, 120, 255))
            return img, dict(grain=10)
        # телефон: зарядка + офлайн-карты
        lt = t - T_PHONE
        scr = draw_phone(d, W / 2, 560, 1.15)
        sx0, sy0, sx1, sy1 = scr
        maps_t = word_t("Скачай", T_PHONE) - T_PHONE
        if lt < maps_t:
            lvl = c01(lt / maps_t)
            d.rounded_rectangle((W / 2 - 80, 400, W / 2 + 80, 640), 18, outline=(255, 255, 255, 255), width=8)
            d.rectangle((W / 2 - 30, 380, W / 2 + 30, 400), fill=(255, 255, 255, 255))
            hh = 220 * (0.1 + 0.9 * lvl)
            d.rectangle((W / 2 - 66, 630 - hh, W / 2 + 66, 630), fill=(70, 230, 100, 255))
            d.text((W / 2 - 22, 470), "⚡", font=font(70), fill=(255, 255, 255, 255))
            text_c(d, 690, f"{int(10 + 90 * lvl)}%", 54, stroke=0)
        else:
            k = c01((lt - maps_t) / (T_WATER - T_PHONE - maps_t - 0.2))
            for gx in range(int(sx0), int(sx1), 40):
                d.line((gx, sy0, gx, sy1), fill=(60, 80, 70, 255), width=2)
            for gy in range(int(sy0), int(sy1), 40):
                d.line((sx0, gy, sx1, gy), fill=(60, 80, 70, 255), width=2)
            d.line((sx0 + 20, sy1 - 120, W / 2, 520, sx1 - 30, 380), fill=(255, 200, 60, 255), width=10)
            d.ellipse((W / 2 - 18, 470, W / 2 + 18, 506), fill=(255, 60, 40, 255))
            d.polygon([(W / 2 - 18, 490), (W / 2 + 18, 490), (W / 2, 530)], fill=(255, 60, 40, 255))
            d.rounded_rectangle((sx0 + 20, sy1 - 80, sx1 - 20, sy1 - 50), 12, fill=(40, 40, 50, 255))
            d.rounded_rectangle((sx0 + 20, sy1 - 80, sx0 + 20 + (sx1 - sx0 - 40) * k, sy1 - 50), 12,
                                fill=(70, 200, 255, 255))
            text_c(d, sy1 - 130, "ОФЛАЙН-КАРТА", 26, stroke=0)
        return img, dict(grain=8)
    # «Вода важнее…»
    lt = t - T_WATER
    img = rgba(vgrad((5, 25, 50), (0, 5, 15)))
    d = ImageDraw.Draw(img)
    for i in range(40):
        x = (i * 53) % W
        y = H - ((t * 90 + i * 77) % H)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(120, 200, 255, 160), width=2)
    s = 2.4 + 0.15 * math.sin(t * 2)
    glow(img, lambda g: item_icon(g, 0, W / 2, 560, s), 40, 2)
    if t > T_WATER - 1:
        text_c(ImageDraw.Draw(img), 160, "ВОДА > ВСЁ", 84, fill=(140, 210, 255), stroke=6)
    return img, dict(grain=8, zoom=1 + 0.02 * lt)


def sc_door(t):
    """Доверие / стук в дверь."""
    if t < T_KNOCK:
        lt = t - T_TRUST
        img = rgba(vgrad((15, 15, 20), (0, 0, 0)))
        d = ImageDraw.Draw(img)
        # чужие глаза в темноте
        for i, (x, y) in enumerate([(160, 380), (540, 300), (420, 760), (210, 980), (580, 1050)]):
            k = ease((lt - i * 0.35) / 0.4)
            if k > 0 and int(t * 5 + i) % 13:
                for ox in (-18, 18):
                    d.ellipse((x + ox - 7, y - 4, x + ox + 7, y + 4), fill=(255, 230, 150, int(255 * k)))
        text_c(d, 560, "КОМУ ВЕРИТЬ?", 72, fill=(255, 255, 255, int(255 * ease(lt / 0.5))), stroke=5)
        return img, dict(grain=14)
    knocks = [T_KNOCK + 0.1, T_KNOCK + 0.35, T_KNOCK + 0.6, T_THREE + 0.75, T_THREE + 1.05, T_THREE + 1.35]
    sh = sum(14 * math.exp(-(t - k) * 14) for k in knocks if t >= k)
    img = rgba(vgrad((30, 25, 22), (8, 6, 5)))
    d = ImageDraw.Draw(img)
    # дверь
    dx0, dy0, dx1, dy1 = 150, 180, 570, 1080
    d.rectangle((dx0 - 25, dy0 - 25, dx1 + 25, dy1), fill=(20, 15, 12, 255))
    d.rectangle((dx0, dy0, dx1, dy1), fill=(70, 45, 30, 255))
    for (a, b, c, e) in [(185, 220, 535, 560), (185, 610, 535, 1040)]:
        d.rectangle((a, b, c, e), outline=(50, 32, 20, 255), width=10)
    d.ellipse((490, 620, 525, 655), fill=(190, 170, 110, 255))
    d.ellipse((345, 330, 375, 360), fill=(10, 10, 10, 255), outline=(150, 150, 150, 255), width=4)  # глазок
    # полоска света под дверью и тени ног
    lc = (255, 210, 120) if t < T_IKNOW else (255, 40, 30)
    glow(img, lambda g: g.rectangle((dx0, dy1 - 6, dx1, dy1 + 4), fill=lc + (255,)), 16, 2)
    d = ImageDraw.Draw(img)
    if t > T_FRIEND - 0.2:
        off = 10 * math.sin(t * 3) if t < T_THREE else 0
        for fx in (290, 400):
            d.rectangle((fx + off, dy1 - 6, fx + 45 + off, dy1 + 4), fill=(0, 0, 0, 255))
    d.rectangle((0, dy1 + 4, W, H), fill=(15, 12, 10, 255))
    # слова «ТУК»
    for k in knocks:
        if k <= t < k + 0.45:
            a = int(255 * (1 - (t - k) / 0.45))
            x = 250 + (hash(round(k, 2)) % 220)
            ImageDraw.Draw(img).text((x, 420 + (hash(k) % 300)), "ТУК", font=font(64),
                                     fill=(255, 255, 255, a), stroke_width=4, stroke_fill=(0, 0, 0))
    z = 1.0
    if t > T_IKNOW - 3:
        z = 1 + 0.35 * ease((t - (T_IKNOW - 3)) / 4)
    dark = 0.0 if t < line_t("И вдруг") else 0.35 * ease((t - line_t("И вдруг")) / 2)
    return img, dict(grain=14, shake=sh, zoom=z, zoom_c=(360, 400), dark=dark,
                     tint=(1.2, 0.7, 0.7) if t > T_IKNOW else None)


def sc_rule2(t):
    if t < line_t("Не теряй"):
        return rule_card(t, T_RULE2, 2, "ХОЛОДНАЯ ГОЛОВА")
    img = rgba(vgrad((25, 25, 30), (5, 5, 8)))
    d = ImageDraw.Draw(img)
    text_c(d, 150, "ЧЕК-ЛИСТ: КТО-ТО У ДВЕРИ", 36, fill=(255, 210, 60), stroke=3)
    items = [(line_t("Не теряй"), "✓", "Не паникуй", (80, 255, 120)),
             (line_t("Не открывай"), "✗", "Не открывай\nавтоматически", (255, 70, 60)),
             (line_t("Сначала"), "?", "Оцени ситуацию", (255, 210, 60)),
             (line_t("Не подвергай"), "!", "Без лишнего риска", (255, 140, 40))]
    for i, (ts, ic, txt, col) in enumerate(items):
        if t >= ts:
            k = back((t - ts) / 0.35)
            y = 290 + i * 200
            x = lerp(-500, 60, k)
            d.rounded_rectangle((x, y, x + 600, y + 160), 24, fill=(40, 40, 48, 255), outline=col + (255,), width=5)
            d.ellipse((x + 25, y + 35, x + 115, y + 125), fill=col + (255,))
            d.text((x + 70, y + 80), ic, font=font(60), fill=(0, 0, 0, 255), anchor="mm")
            ImageDraw.Draw(img).multiline_text((x + 140, y + 80), txt, font=font(40), fill=(255, 255, 255, 255),
                                               anchor="lm", spacing=4)
    return img, dict(grain=8)


def radio(d, t, needle, lamp=1.0):
    d.rounded_rectangle((110, 560, 610, 900), 30, fill=(70, 45, 30, 255), outline=(30, 20, 12, 255), width=8)
    for gx in range(150, 330, 22):  # решётка
        for gy in range(600, 860, 22):
            d.ellipse((gx, gy, gx + 12, gy + 12), fill=(30, 20, 14, 255))
    d.rounded_rectangle((350, 600, 580, 690), 10, fill=(int(60 + 170 * lamp), int(40 + 120 * lamp), 20, 255))
    for i in range(12):
        x = 365 + i * 18
        d.line((x, 610, x, 625 if i % 2 else 635), fill=(40, 25, 10, 255), width=2)
    nx = 365 + needle * 200
    d.line((nx, 605, nx, 685), fill=(200, 20, 20, 255), width=4)
    for cx in (410, 520):
        d.ellipse((cx - 40, 730, cx + 40, 810), fill=(30, 20, 14, 255))
        a = t * 0.8
        d.line((cx, 770, cx + 32 * math.cos(a), 770 + 32 * math.sin(a)), fill=(150, 150, 150, 255), width=4)
    d.line((540, 560, 660, 300), fill=(120, 120, 120, 255), width=6)


def sc_radio(t):
    lt = t - T_NIGHT
    img = rgba(vgrad((10, 14, 30), (2, 2, 6)))
    d = ImageDraw.Draw(img)
    # окно с луной
    d.rectangle((70, 120, 330, 420), fill=(25, 35, 60, 255), outline=(5, 5, 10, 255), width=12)
    glow(img, lambda g: g.ellipse((220, 160, 290, 230), fill=(230, 230, 210, 255)), 20)
    d = ImageDraw.Draw(img)
    d.line((200, 120, 200, 420), fill=(5, 5, 10, 255), width=10)
    d.rectangle((0, 900, W, H), fill=(18, 14, 12, 255))
    needle = 0.3
    if t > T_TUNE:
        needle = 0.3 + 0.45 * ease((t - T_TUNE) / 1.2) + 0.03 * math.sin(t * 13) * (t < T_MSG2)
    lamp = 0.8 + 0.2 * math.sin(t * 17) * (T_LOST < t < T_MSG2)
    glow(img, lambda g: g.ellipse((300, 560, 640, 760), fill=(255, 150, 40, int(60 * lamp))), 60)
    radio(ImageDraw.Draw(img), t, needle, lamp)
    d = ImageDraw.Draw(img)
    voice_on = (T_MSG1 <= t < T_LOST) or (T_MSG2 <= t < T_RULE3)
    col = (120, 255, 140) if t < T_LOST else (255, 70, 50)
    if t >= T_MSG1:
        # осциллограмма
        pts = []
        amp_m = 60 if voice_on else 10
        for x in range(40, W - 40, 5):
            nz = R.normal(0, 1) * (25 if T_LOST <= t < T_MSG2 else 3)
            amp = amp_m * math.sin(x * 0.05 + t * 25) * abs(math.sin(x * 0.011 + t * 4)) + nz
            pts.append((x, 1000 + amp))
        glow(img, lambda g: g.line(pts, fill=col + (255,), width=4), 8)
        d = ImageDraw.Draw(img)
        lbl = "ПЕРЕДАЧА №1" if t < T_LOST else ("ПОИСК…" if t < T_MSG2 else "ПЕРЕДАЧА №2")
        f = f"{lerp(104.2, 147.3, c01((needle - 0.3) / 0.45)):.1f} МГц"
        text_c(d, 470, f, 46, fill=(255, 190, 60), stroke=3, mono=True)
        text_c(d, 1080, lbl, 34, fill=col, stroke=3, mono=True)
    if t >= T_MSG2 + 1.0:
        ov = Image.new("RGBA", img.size); od = ImageDraw.Draw(ov)
        lay = Image.new("RGBA", (560, 140)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle((5, 5, 555, 135), 14, outline=(255, 40, 40, 230), width=8)
        text_c(ld, 30, "НЕ ВЕРЬ №1", 70, fill=(255, 40, 40, 230), stroke=0, x=280)
        lay = lay.rotate(-7, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(lay, (int(W / 2 - lay.width / 2), 170))
    stat = 0.0
    if T_LOST <= t < T_MSG2:
        stat = 0.55 * (1 - ease((t - T_TUNE - 0.6) / 1.2))
    return img, dict(grain=14, static=stat, scan=True, chroma=2 if stat else 0)


def sc_rule3(t):
    if t < line_t("Проверяй"):
        return rule_card(t, T_RULE3, 3, "ПРОВЕРЯЙ ВСЁ")
    img = rgba(vgrad((20, 20, 26), (4, 4, 6)))
    d = ImageDraw.Draw(img)
    text_c(d, 170, "ПРОВЕРЯЙ\nИНФОРМАЦИЮ", 70, fill=(255, 220, 60), stroke=5)
    rumors = ["«Воду отравили»", "«Армия ушла»", "«Мост взорван»", "«Помощи не будет»"]
    st = line_t("В мире")
    for i, r in enumerate(rumors):
        ts = st + i * 0.9
        if t >= ts:
            k = back((t - ts) / 0.3)
            y = 480 + i * 130
            d.rounded_rectangle((90, y, 630, y + 100), 50, fill=(45, 45, 55, 255))
            d.text((W / 2, y + 50), r, font=font(int(38 * k) + 1), fill=(230, 230, 230, 255), anchor="mm")
    if t >= st + 3.2:
        lay = Image.new("RGBA", (560, 160)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle((5, 5, 555, 155), 14, outline=(255, 40, 40, 255), width=10)
        text_c(ld, 32, "СЛУХИ", 92, fill=(255, 40, 40, 255), stroke=0, x=280)
        lay = lay.rotate(12, expand=True, resample=Image.BICUBIC)
        k = 1 + 1.5 * (1 - ease((t - st - 3.2) / 0.15))
        lay = lay.resize((int(lay.width * k), int(lay.height * k)))
        img.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(700 - lay.height / 2)))
    return img, dict(grain=8)


def sc_phone(t):
    if t < T_EYES:
        img = rgba(vgrad((6, 6, 10), (0, 0, 0)))
        d = ImageDraw.Draw(img)
        if t < T_VIBR:
            # радио гаснет
            lamp = 1 - ease((t - T_OFF) / 0.6)
            radio(d, t, 0.75, lamp)
            arr = np.asarray(img.convert("RGB"), np.float32) * (0.35 + 0.65 * lamp)
            return rgba(arr), dict(grain=16)
        vib = 6 * math.sin(t * 90) if t < T_SCREEN else 0
        if t < T_SCREEN:
            # телефон на столе светится
            d.rectangle((0, 820, W, H), fill=(20, 15, 12, 255))
            glow(img, lambda g: g.ellipse((160, 700, 560, 960), fill=(120, 160, 255, 90)), 50)
            d = ImageDraw.Draw(img)
            d.polygon([(250 + vib, 760), (480 + vib, 760), (520 + vib, 900), (210 + vib, 900)], fill=(15, 15, 18, 255))
            d.polygon([(262 + vib, 768), (468 + vib, 768), (505 + vib, 890), (225 + vib, 890)], fill=(110, 150, 240, 255))
            for k in range(3):
                r = 60 + ((t * 120 + k * 40) % 120)
                d.arc((365 - r + vib, 830 - r * 0.6, 365 + r + vib, 830 + r * 0.6), 180, 360,
                      fill=(150, 180, 255, int(200 * (1 - (r - 60) / 120))), width=4)
            text_c(d, 380, "BZZZ", 80, fill=(150, 180, 255), stroke=4)
            return img, dict(grain=14)
        # экран телефона крупно
        scr = draw_phone(d, W / 2, 640, 1.9, screen=(10, 12, 20))
        x0, y0, x1, y1 = scr
        d = ImageDraw.Draw(img)
        text_c(d, y0 + 80, "Неизвестный номер", 34, fill=(200, 200, 210), stroke=0)
        text_c(d, y0 + 130, "+7 ••• ••• •• ••", 30, fill=(130, 130, 140), stroke=0)
        if t >= T_SCREEN + 0.6:
            d.rounded_rectangle((x0 + 30, y0 + 230, x1 - 80, y0 + 330), 30, fill=(50, 50, 60, 255))
            d.text((x0 + 60, y0 + 280), "…", font=font(60), fill=(200, 200, 200, 255), anchor="lm")
        if t >= T_DONT:
            k = back((t - T_DONT) / 0.3)
            d.rounded_rectangle((x0 + 30, y0 + 230, x1 - 30, y0 + 430), 34, fill=(200, 30, 30, 255))
            d.multiline_text(((x0 + x1) / 2, y0 + 330), "НЕ СМОТРИ\nВ ОКНО", font=font(int(56 * k) + 1),
                             fill=(255, 255, 255, 255), anchor="mm", align="center")
        z = 1 + 0.08 * ease((t - T_SCREEN) / 4)
        return img, dict(grain=10, zoom=z, zoom_c=(W / 2, 560))
    # окно, пустая улица, скрип
    lt = t - T_EYES
    img = rgba(vgrad((8, 10, 22), (2, 2, 6)))
    d = ImageDraw.Draw(img)
    # вид за окном
    win = Image.new("RGBA", (440, 640))
    wd = ImageDraw.Draw(win)
    wd.rectangle((0, 0, 440, 640), fill=(15, 20, 35, 255))
    for x, h in [(0, 300), (90, 420), (200, 260), (300, 380)]:
        wd.rectangle((x, 640 - h, x + 100, 640), fill=(6, 7, 12, 255))
    lampk = 1 if (int(t * 7) % 11) else 0.2
    wd.line((330, 640, 330, 380), fill=(30, 30, 30, 255), width=8)
    wd.ellipse((300, 360, 360, 400), fill=(255, 220, 140, int(255 * lampk)))
    wd.polygon([(310, 390), (350, 390), (420, 640), (240, 640)], fill=(255, 220, 140, int(50 * lampk)))
    img.alpha_composite(win, (140, 220))
    d = ImageDraw.Draw(img)
    d.rectangle((140, 220, 580, 860), outline=(4, 4, 6, 255), width=26)
    d.line((360, 220, 360, 860), fill=(4, 4, 6, 255), width=18)
    d.line((140, 540, 580, 540), fill=(4, 4, 6, 255), width=18)
    if T_NOONE <= t < T_CREAK:
        text_c(d, 960, "НИКОГО", 64, fill=(180, 190, 220), stroke=4)
    dark = 0.0
    if t >= T_CREAK:
        k = ease((t - T_CREAK) / 2.2)
        dark = 0.55 * k
        # силуэт за спиной — в отражении стекла
        sil = Image.new("RGBA", img.size); sd = ImageDraw.Draw(sil)
        silhouette(sd, 470, 1000, 0.85, col=(0, 0, 0, int(230 * k)),
                   eye=(255, 30, 20, int(255 * k)) if t > T_CREAK + 1.6 else None)
        img.alpha_composite(sil)
    z = 1 + 0.12 * ease(lt / 6)
    return img, dict(grain=16, zoom=z, dark=dark, shake=3 if T_CREAK + 0.5 < t < T_CREAK + 1.6 else 0)


def sc_end(t):
    if t < VOICE_END - 0.2:
        lt = t - T_WORST
        img = rgba(vgrad((40, 0, 0), (0, 0, 0)))
        d = ImageDraw.Draw(img)
        ash(img, t, color=(255, 120, 100), n=100, wind=-30)
        s = 1.0 + 0.35 * ease(lt / 10)
        eye = (255, 40, 20, 255) if t > T_LAST else (120, 20, 10, 255)
        glow(img, lambda g: silhouette(g, W / 2, H + 60, s * 1.2, col=(0, 0, 0, 255), eye=eye), 25)
        if t > line_t("Ты никогда") and t < T_LAST:
            text_c(ImageDraw.Draw(img), 170, "ВЫЖИВАЮЩИЙ", 64, fill=(255, 255, 255), stroke=5)
        if t >= T_LAST:
            k = ease((t - T_LAST) / 0.3)
            text_c(ImageDraw.Draw(img), 170, "УГРОЗА", 96, fill=(255, 40, 30, int(255 * k)), stroke=6)
        gl = t >= T_LAST and R.random() < 0.4
        return img, dict(grain=14, chroma=6 if gl else 1, glitch=gl, scan=True)
    # финальная карточка
    lt = t - (VOICE_END - 0.2)
    img = rgba(vgrad((10, 0, 0), (0, 0, 0)))
    d = ImageDraw.Draw(img)
    a = int(255 * ease(lt / 0.4))
    text_c(d, 330, "72 ЧАСА", 110, fill=(255, 50, 40, a), stroke=6)
    text_c(d, 480, "серия 1 из ?", 40, fill=(255, 255, 255, a), stroke=3)
    if lt > 0.8:
        text_c(d, 720, "СЕРИЯ 2:", 50, fill=(255, 220, 60), stroke=4)
        text_c(d, 790, "«ЧУЖИЕ У ДВЕРИ»", 54, fill=(255, 255, 255), stroke=4)
    if lt > 1.6:
        col = (255, 60, 40) if int(t * 3) % 2 else (255, 230, 60)
        text_c(d, 990, "☢ ПОДПИШИСЬ ☢", 68, fill=col, stroke=6)
        text_c(d, 1080, "чтобы не пропустить", 38, stroke=3)
    return img, dict(grain=10, scan=True)


SCENES = [(17.0, sc_intro), (T_TRUST, sc_rule1), (T_RULE2, sc_door), (T_NIGHT, sc_rule2),
          (T_RULE3, sc_radio), (T_OFF, sc_rule3), (T_WORST, sc_phone), (1e9, sc_end)]
SCENE_STARTS = [0.0] + [e for e, _ in SCENES[:-1]]


# ------------------------------------------------------------- captions & HUD
PAGES = []
for li, L in enumerate(LINES):
    ws = [w for w in WORDS if w["line"] == li]
    page = []
    for w in ws:
        page.append(w)
        if len(page) >= 3 or len(" ".join(p["w"] for p in page)) > 14 or w["w"][-1] in ".,!?…»":
            PAGES.append(page); page = []
    if page:
        PAGES.append(page)


def captions(img, t):
    for i, p in enumerate(PAGES):
        end = p[-1]["e"] + 0.25
        if i + 1 < len(PAGES):
            end = min(end, PAGES[i + 1][0]["s"])
        if p[0]["s"] - 0.05 <= t < end:
            quote = LINES[p[0]["line"]]["text"].startswith("«")
            d = ImageDraw.Draw(img)
            f = font(58)
            txt = " ".join(w["w"] for w in p)
            tw = d.textlength(txt, font=f)
            if tw > W - 60:
                f = font(int(58 * (W - 60) / tw)); tw = d.textlength(txt, font=f)
            x = (W - tw) / 2
            y = 1110
            pop = back((t - p[0]["s"] + 0.05) / 0.15)
            y += (1 - pop) * 20
            for w in p:
                active = w["s"] - 0.03 <= t < w["e"]
                done = t >= w["e"]
                col = (255, 225, 40) if active else ((255, 255, 255) if done or not active else (255, 255, 255))
                if quote:
                    col = (255, 90, 70) if active else (255, 190, 180)
                d.text((x, y), w["w"], font=f, fill=col + (255,), stroke_width=6, stroke_fill=(0, 0, 0))
                x += d.textlength(w["w"] + " ", font=f)
            return


def hours_left(t):
    pts = [(9.5, 72.0), (17, 71.5), (50, 63), (60.3, 49), (90.5, 40), (105.7, 38.5), (116.6, 37.0)]
    if t < pts[0][0]:
        return None
    for (a, ha), (b, hb) in zip(pts, pts[1:]):
        if t < b:
            return lerp(ha, hb, (t - a) / (b - a))
    return None


def hud(img, t):
    h = hours_left(t)
    if h is None or (9.5 <= t < 17):
        return
    secs = h * 3600
    hh, rem = divmod(int(secs), 3600); mm, ss = divmod(rem, 60)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((24, 40, 290, 108), 14, fill=(0, 0, 0, 170), outline=(255, 60, 40, 255), width=3)
    if int(t * 2) % 2:
        d.ellipse((40, 64, 58, 82), fill=(255, 40, 30, 255))
    d.text((70, 52), f"{hh:02d}:{mm:02d}:{ss:02d}", font=font(40, True), fill=(255, 90, 60, 255))
    d.text((W - 24, 60), "72 ЧАСА · S1", font=font(24), fill=(255, 255, 255, 200), anchor="ra")


# ------------------------------------------------------------- frame render
def render(i):
    global R
    t = i / FPS
    R = np.random.default_rng(i)
    k = 0
    while t >= SCENES[k][0]:
        k += 1
    img, fx = SCENES[k][1](t)
    arr = np.asarray(img.convert("RGB"), np.float32)
    if fx.get("tint"):
        arr = arr * np.array(fx["tint"], np.float32)
    if fx.get("zoom"):
        cx, cy = fx.get("zoom_c", (W / 2, H / 2))
        arr = zoom(arr, fx["zoom"], cx, cy)
    if fx.get("static"):
        nz = R.integers(0, 255, (H // 4, W // 4, 1)).repeat(4, 0).repeat(4, 1).astype(np.float32)
        arr = arr * (1 - fx["static"]) + nz * fx["static"]
    if fx.get("glitch"):
        for _ in range(int(R.integers(1, 5))):
            y0 = int(R.integers(0, H - 80)); hh = int(R.integers(8, 80))
            arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(R.integers(-60, 60)), axis=1)
    if fx.get("dark"):
        arr = arr * (1 - fx["dark"])
    sh = fx.get("shake", 0)
    if sh > 0.5:
        dx, dy = R.normal(0, sh, 2).astype(int)
        arr = np.roll(arr, (dy, dx), axis=(0, 1))
    ch = fx.get("chroma", 0)
    if ch:
        arr[..., 0] = np.roll(arr[..., 0], ch, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -ch, axis=1)
    if fx.get("scan"):
        arr = arr * SCAN
    arr = arr * VIGN + GRAIN[i % len(GRAIN)] * fx.get("grain", 10) * 0.6
    # мягкий переход между сценами (вспышка-затемнение 0.12 c)
    for s0 in SCENE_STARTS[1:]:
        if abs(t - s0) < 0.12:
            arr = arr * (abs(t - s0) / 0.12)
    out = rgba(arr)
    captions(out, t)
    hud(out, t)
    return np.asarray(out.convert("RGB"), np.uint8).tobytes()


# -------------------------------------------------------------------- audio
def lp(x, cut):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cut) ** 4)
    return np.fft.irfft(X, len(x))


def env(tt, a, b, fade=0.05):
    return np.clip((tt - a) / fade, 0, 1) * np.clip((b - tt) / fade, 0, 1)


def make_audio(path):
    n = int(DUR * SR)
    tt = np.arange(n) / SR
    ar = np.random.default_rng(3)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", VOICE, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    voice = np.zeros(n); voice[:min(n, len(v))] = v[:n]
    voice /= np.max(np.abs(voice)) + 1e-9
    # огибающая голоса для «дакинга» музыки
    win = int(0.15 * SR)
    venv = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, "same"))
    duck = 1 - 0.55 * np.clip(venv / 0.12, 0, 1)

    bed = np.zeros(n)
    # дрон
    bed += 0.16 * sum(np.sin(2 * np.pi * f * tt + p) for f, p in ((36.7, 0), (37.1, 1), (55.0, 2), (73.4, 3)))
    # пульс-сердцебиение, учащается к финалу
    bpm = np.interp(tt, [0, 60, 100, 116, DUR], [58, 66, 80, 110, 60])
    phase = np.cumsum(bpm / 60 / SR) % 1
    for off in (0.0, 0.18):
        p = (phase - off) % 1
        bed += 0.5 * np.sin(2 * np.pi * 50 * p) * np.exp(-p * 28)
    # ветер
    bed += 0.25 * lp(ar.normal(0, 1, n), 400) * (env(tt, 4.5, 9.5, 0.8) + env(tt, 98, 106, 1.0))
    # тревожные аккорды по частям
    chords = [(0, 17, [110, 130.8, 164.8]), (17, 33.6, [98, 116.5, 146.8]), (33.6, 50.3, [92.5, 110, 138.6]),
              (50.3, 60.3, [98, 116.5, 146.8]), (60.3, 90.5, [82.4, 98, 123.5]), (90.5, 105.7, [77.8, 92.5, 116.5]),
              (105.7, 117, [73.4, 87.3, 110])]
    for a, b, fs in chords:
        e = env(tt, a, b, 1.0)
        bed += 0.05 * e * sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) for f in fs)
    bed *= np.clip(tt / 1.5, 0, 1) * np.clip((DUR - tt) / 2.0, 0, 1)

    sfx = np.zeros(n)
    noise_lp = lp(ar.normal(0, 1, n), 150)

    def hit(t0, amp=1.0, decay=3.0):
        bt = np.clip(tt - t0, 0, None); m = tt >= t0
        sfx[:] += amp * m * (noise_lp * np.exp(-bt * decay) * 2.5 +
                             np.sin(2 * np.pi * (55 * bt - 10 * bt ** 2)) * np.exp(-bt * 4) * 0.8)

    def click(t0, amp=0.4, f=1800):
        i = int(t0 * SR); L = int(0.04 * SR)
        if 0 <= i < n - L:
            k = np.arange(L) / SR
            sfx[i:i + L] += amp * np.sin(2 * np.pi * f * k) * np.exp(-k * 120)

    def knock(t0):
        i = int(t0 * SR); L = int(0.25 * SR)
        k = np.arange(L) / SR
        s = (np.sin(2 * np.pi * 95 * k) + 0.6 * np.sin(2 * np.pi * 180 * k)) * np.exp(-k * 30)
        s += lp(ar.normal(0, 1, L), 900) * np.exp(-k * 60) * 0.8
        sfx[i:i + L] += 1.1 * s

    hit(0.0, 1.2, 1.2)
    for st in (word_t("Связи"), word_t("Магазины"), word_t("паника")):
        hit(st, 0.5, 6)
    hit(9.5, 0.7, 2)
    for tr in (T_RULE1, T_RULE2, T_RULE3):
        hit(tr, 1.0, 2.5)
    for it in ITEM_T:
        click(it, 0.5, 1500)
    for k in (T_KNOCK + 0.1, T_KNOCK + 0.35, T_KNOCK + 0.6, T_THREE + 0.75, T_THREE + 1.05, T_THREE + 1.35):
        knock(k)
    # радио: шипение, потеря сигнала, свип настройки
    hiss = ar.normal(0, 1, n)
    sfx += 0.05 * hiss * env(tt, T_NIGHT + 2, T_OFF, 0.3)
    sfx += 0.35 * hiss * env(tt, T_LOST, T_TUNE + 1.3, 0.1)
    sw = np.sin(2 * np.pi * np.cumsum(np.interp(tt, [T_TUNE, T_TUNE + 1.2], [300, 2400])) / SR)
    sfx += 0.08 * sw * env(tt, T_TUNE, T_TUNE + 1.2, 0.1)
    # вибрация телефона
    bz = np.sin(2 * np.pi * 160 * tt) * (np.sin(2 * np.pi * 1.6 * tt) > 0)
    sfx += 0.35 * bz * env(tt, T_VIBR, T_SCREEN, 0.05)
    click(T_DONT, 0.5, 1200); click(T_DONT + 0.08, 0.5, 1600)
    # скрип пола
    ct = T_CREAK + 0.5
    cf = np.interp(tt, [ct, ct + 1.2], [70, 130])
    saw = (np.cumsum(cf / SR) % 1) * 2 - 1
    sfx += 0.25 * lp(saw, 1200) * env(tt, ct, ct + 1.2, 0.15) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt))
    hit(T_LAST, 0.6, 1.5)
    hit(VOICE_END - 0.2, 1.4, 1.0)
    # звон в ушах в финале
    sfx += 0.03 * np.sin(2 * np.pi * 3600 * tt) * env(tt, VOICE_END, DUR, 0.5)

    mix = voice * 1.0 + bed * 0.22 * duck + sfx * 0.32
    mix = np.tanh(mix * 1.1)
    mix /= np.max(np.abs(mix)) + 1e-9
    data = (mix * 0.95 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.stack([data, data], 1).tobytes())


def main():
    wav = OUT + ".wav"
    print("Звук…")
    make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-vf", "scale=1080:1920:flags=lanczos",
           "-c:v", "libx264", "-preset", "medium", "-crf", "25", "-maxrate", "3M", "-bufsize", "6M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    only = os.environ.get("FRAMES")  # отладка: FRAMES=a:b
    rng_ = range(NFRAMES) if not only else range(*map(int, only.split(":")))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for j, fr in enumerate(pool.imap(render, rng_, chunksize=6)):
            p.stdin.write(fr)
            if j % 300 == 0:
                print(f"  {j}/{len(rng_)}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
