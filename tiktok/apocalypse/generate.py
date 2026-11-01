#!/usr/bin/env python3
"""Генератор вертикального TikTok-ролика в жанре апокалипсиса (9:16, 1080x1920, ~24 c).

Всё рисуется процедурно (numpy + Pillow), звук синтезируется, сборка — ffmpeg.
Запуск:  python3 tiktok/apocalypse/generate.py  [выходной.mp4]
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 720, 1280          # рендер; ffmpeg апскейлит до 1080x1920
FPS = 30
DUR = 24.0
SR = 44100
NFRAMES = int(DUR * FPS)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "apocalypse_tiktok.mp4")

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_fc = {}


def font(size, mono=False):
    key = (size, mono)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FONT_M if mono else FONT_B, size)
    return _fc[key]


rng = np.random.default_rng(1337)

# Тайминг сцен (секунды)
S_ALERT, S_CITY, S_BLAST, S_WASTE, S_RADIO = 0.0, 4.0, 8.5, 13.0, 19.0


# --------------------------------------------------------------------- utils
def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def vgrad(top, bottom, h=H, w=W):
    t = np.linspace(0, 1, h)[:, None, None]
    g = np.array(top, float)[None, None] * (1 - t) + np.array(bottom, float)[None, None] * t
    return np.repeat(g, w, axis=1)


yy, xx = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.clip(1.15 - 0.55 * _d ** 1.6, 0.25, 1.0)[..., None]
GRAIN = [rng.normal(0, 1, (H, W, 1)).astype(np.float32) for _ in range(8)]
SCAN = (1 - 0.18 * (np.arange(H) % 4 < 2))[:, None, None]


def text_center(draw, y, txt, size, fill=(255, 255, 255), stroke=5, mono=False, chars=None, x=None):
    if chars is not None:
        txt = txt[:chars]
    f = font(size, mono)
    lines = txt.split("\n")
    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=f, stroke_width=stroke)
        tw = bb[2] - bb[0]
        px = (W - tw) / 2 if x is None else x
        draw.text((px, y + i * size * 1.25), line, font=f, fill=fill,
                  stroke_width=stroke, stroke_fill=(0, 0, 0))


def typed(txt, t0, t, cps=22):
    return int(max(0, (t - t0) * cps))


def caption_box(img, y, txt, size, t0, t, cps=22, color=(255, 255, 255)):
    """Субтитр в стиле TikTok: полупрозрачная плашка + печатающийся текст."""
    n = typed(txt, t0, t, cps)
    if n <= 0:
        return
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(size)
    lines = txt.split("\n")
    widths = [d.textbbox((0, 0), l, font=f)[2] for l in lines]
    bw = max(widths) + 60
    bh = len(lines) * size * 1.25 + 40
    d.rounded_rectangle(((W - bw) / 2, y - 20, (W + bw) / 2, y - 20 + bh), 22, fill=(0, 0, 0, 150))
    img.alpha_composite(ov)
    text_center(ImageDraw.Draw(img), y, txt, size, fill=color, stroke=3, chars=n)


# -------------------------------------------------------------- static layers
def make_skyline(seed, base_y, hmin, hmax, color, ruined=False, windows=False):
    r = np.random.default_rng(seed)
    img = Image.new("RGBA", (W + 200, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = -20
    wins = []
    while x < W + 200:
        bw = int(r.integers(45, 120))
        bh = int(r.integers(hmin, hmax))
        top = base_y - bh
        if ruined:
            pts = [(x, base_y), (x, top + r.integers(0, 60))]
            for k in range(1, 5):
                pts.append((x + bw * k / 5, top + r.integers(0, 140)))
            pts += [(x + bw, top + r.integers(30, 120)), (x + bw, base_y)]
            d.polygon(pts, fill=color)
        else:
            d.rectangle((x, top, x + bw, base_y), fill=color)
            if r.random() < 0.3:
                d.rectangle((x + bw / 2 - 2, top - 50, x + bw / 2 + 2, top), fill=color)
            if windows:
                for wy in range(top + 14, base_y - 10, 22):
                    for wx in range(x + 8, x + bw - 10, 16):
                        if r.random() < 0.45:
                            wins.append((wx, wy, r.random()))
        x += bw + int(r.integers(-10, 8))
    return img, wins


CITY_BACK, _ = make_skyline(1, 1000, 250, 520, (40, 30, 60, 255))
CITY_FRONT, CITY_WINS = make_skyline(2, 1080, 180, 640, (14, 10, 22, 255), windows=True)
RUIN_BACK, _ = make_skyline(3, 960, 120, 360, (70, 52, 40, 255), ruined=True)
RUIN_FRONT, _ = make_skyline(4, 1010, 60, 260, (35, 25, 20, 255), ruined=True)

ASH = rng.random((260, 4))  # x, y, speed, size


def draw_ash(img, t, color=(200, 190, 180), count=260, wind=40):
    d = ImageDraw.Draw(img)
    for i in range(count):
        x0, y0, sp, sz = ASH[i % len(ASH)]
        y = (y0 * H + t * (60 + sp * 120)) % H
        x = (x0 * W + t * wind + 18 * math.sin(t * 1.3 + i)) % W
        r = 1 + sz * 3
        a = int(120 + 120 * sz)
        d.ellipse((x - r, y - r, x + r, y + r), fill=color + (a,))


def post(arr, t, grain=10.0, shake=0.0, vign=True, chroma=0):
    if shake > 0:
        dx, dy = (rng.normal(0, shake, 2)).astype(int)
        arr = np.roll(arr, (dy, dx), axis=(0, 1))
    if chroma:
        arr = arr.copy()
        arr[..., 0] = np.roll(arr[..., 0], chroma, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -chroma, axis=1)
    if vign:
        arr = arr * VIGNETTE
    arr = arr + GRAIN[int(t * FPS) % len(GRAIN)] * grain
    return np.clip(arr, 0, 255).astype(np.uint8)


def to_rgba(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


# --------------------------------------------------------------------- scenes
def scene_alert(t):
    lt = t - S_ALERT
    flash = 0.5 + 0.5 * math.sin(lt * 2 * math.pi * 1.6)
    bg = vgrad((25 + 50 * flash, 0, 0), (5, 0, 0))
    img = to_rgba(bg)
    d = ImageDraw.Draw(img)
    # мигающая полоса
    d.rectangle((0, 170, W, 290), fill=(int(180 + 75 * flash), 0, 0, 255))
    text_center(d, 200, "⚠ ЭКСТРЕННОЕ ОПОВЕЩЕНИЕ ⚠", 33, stroke=3)
    text_center(d, 420, "СИСТЕМА ГРАЖДАНСКОЙ\nОБОРОНЫ", 44, fill=(255, 220, 220), stroke=3, mono=True)
    msg = "ВСЕМ ЖИТЕЛЯМ\nНЕМЕДЛЕННО\nПРОЙТИ\nВ УКРЫТИЯ"
    text_center(d, 640, msg, 70, fill=(255, 255, 255), stroke=6, chars=typed(msg, 0.6, lt, 14))
    if lt > 2.6:
        text_center(d, 1120, "ЭТО НЕ УЧЕНИЯ", 52, fill=(255, 60, 60) if flash > 0.5 else (255, 255, 255), stroke=4)
    arr = np.asarray(img.convert("RGB"), np.float32) * SCAN
    # глитч: сдвиг горизонтальных полос
    if rng.random() < 0.45:
        for _ in range(rng.integers(1, 5)):
            y0 = int(rng.integers(0, H - 80)); h = int(rng.integers(8, 80))
            arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], int(rng.integers(-60, 60)), axis=1)
    return post(arr, t, grain=14, chroma=int(rng.integers(2, 9)))


def scene_city(t, blast=None):
    """Вечерний город; blast — локальное время после вспышки (None — до взрыва)."""
    lt = t - S_CITY
    if blast is None:
        sky = vgrad((30, 40, 90), (230, 120, 80))
    else:
        k = ease(blast / 1.5)
        sky = vgrad(lerp(np.array((30, 40, 90)), np.array((90, 25, 10)), k),
                    lerp(np.array((230, 120, 80)), np.array((255, 150, 40)), k))
    img = to_rgba(sky)
    d = ImageDraw.Draw(img)
    # солнце
    d.ellipse((W / 2 - 110, 720, W / 2 + 110, 940), fill=(255, 200, 140, 255))
    pan = int(lt * 12)
    if blast is not None:
        draw_mushroom(img, blast)
    img.alpha_composite(CITY_BACK, (-100 - pan // 2, 0))
    front = CITY_FRONT.copy()
    fd = ImageDraw.Draw(front)
    lights_on = blast is None or blast < 0.05
    if lights_on:
        for (wx, wy, rv) in CITY_WINS:
            if rv < 0.75 or (math.sin(t * 3 + rv * 50) > 0):
                fd.rectangle((wx, wy, wx + 7, wy + 10), fill=(255, 210, 120, 255))
    img.alpha_composite(front, (-100 - pan, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 1078, W, H), fill=(8, 6, 10, 255))
    if blast is None:
        caption_box(img, 260, "Нам сказали:\n«это просто учения»", 46, S_CITY + 0.4, t)
        if lt > 2.6:
            caption_box(img, 470, "Мы поверили.", 46, S_CITY + 2.6, t, color=(255, 210, 120))
        arr = np.asarray(img.convert("RGB"), np.float32)
        return post(arr, t, grain=8)
    # после вспышки
    if blast > 1.2:
        draw_ash(img, t, color=(90, 80, 70), count=int(min(260, (blast - 1.2) * 120)))
    if blast > 0.9:
        caption_box(img, 1110, "06:17", 80, S_BLAST + 0.9, t, cps=12, color=(255, 230, 200))
    if blast > 2.0:
        caption_box(img, 140, "Небо стало белым.", 46, S_BLAST + 2.0, t)
    arr = np.asarray(img.convert("RGB"), np.float32)
    # вспышка
    fl = math.exp(-blast * 2.2) if blast >= 0 else 0
    arr = arr * (1 - fl) + 255 * fl
    shake = 22 * math.exp(-max(0, blast - 0.6) * 1.2) if blast > 0.6 else 0
    return post(arr, t, grain=12, shake=shake, chroma=int(shake / 4))


def draw_mushroom(img, b):
    if b < 0.15:
        return
    k = ease((b - 0.15) / 3.5)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = W / 2
    ground = 960
    top = lerp(ground - 60, 290, k)
    # ножка
    sw = lerp(20, 70, k)
    for i in range(14):
        yv = lerp(ground, top + 60, i / 13)
        r = sw * (1.2 - 0.3 * i / 13) + 6 * math.sin(b * 3 + i)
        c = (int(lerp(255, 120, i / 13)), int(lerp(170, 60, i / 13)), 30, 230)
        d.ellipse((cx - r, yv - r, cx + r, yv + r), fill=c)
    # шапка
    cap = lerp(40, 260, k)
    for i in range(22):
        ang = i / 22 * 2 * math.pi + b * 0.4
        rx = cap * (0.55 + 0.45 * abs(math.cos(ang)))
        px = cx + math.cos(ang) * rx * 0.9
        py = top + math.sin(ang) * cap * 0.35
        r = cap * 0.42
        heat = 0.5 + 0.5 * math.sin(ang * 3 + b * 2)
        c = (int(lerp(160, 255, heat)), int(lerp(50, 140, heat)), int(lerp(20, 40, heat)), 235)
        d.ellipse((px - r, py - r, px + r, py + r), fill=c)
    # раскалённое ядро
    rc = cap * 0.5
    d.ellipse((cx - rc, top - rc * 0.6, cx + rc, top + rc * 0.6), fill=(255, 230, 150, 220))
    # кольцо ударной волны
    ring = lerp(60, 520, ease(b / 2.5))
    d.ellipse((cx - ring, ground - ring * 0.18, cx + ring, ground + ring * 0.18),
              outline=(255, 220, 180, int(200 * (1 - ease(b / 2.5)))), width=6)
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(layer)


def draw_survivor(d, x, base, t, scale=1.0):
    s = scale
    ph = t * 4.0
    c = (6, 5, 5, 255)
    hip = (x, base - 120 * s)
    for sgn in (1, -1):
        a = math.sin(ph) * 0.45 * sgn
        knee = (hip[0] + math.sin(a) * 55 * s, hip[1] + math.cos(a) * 55 * s)
        foot = (knee[0] + math.sin(a - 0.25 * abs(a)) * 60 * s, knee[1] + 60 * s)
        d.line([hip, knee, foot], fill=c, width=int(16 * s), joint="curve")
    bob = abs(math.sin(ph)) * 4 * s
    sh = (x, base - 230 * s - bob)
    # плащ/торс
    d.polygon([(sh[0] - 32 * s, sh[1]), (sh[0] + 32 * s, sh[1]),
               (hip[0] + 40 * s, hip[1] + 25 * s), (hip[0] - 45 * s, hip[1] + 30 * s)], fill=c)
    # рюкзак
    d.rounded_rectangle((sh[0] - 62 * s, sh[1] + 5 * s, sh[0] - 22 * s, sh[1] + 85 * s), 8, fill=c)
    # руки
    for sgn in (1, -1):
        a = -math.sin(ph) * 0.4 * sgn
        hand = (sh[0] + math.sin(a) * 90 * s, sh[1] + math.cos(a) * 90 * s)
        d.line([(sh[0], sh[1] + 10 * s), hand], fill=c, width=int(13 * s))
    # голова + противогаз
    hc = (sh[0] + 4 * s, sh[1] - 32 * s)
    d.ellipse((hc[0] - 26 * s, hc[1] - 30 * s, hc[0] + 26 * s, hc[1] + 26 * s), fill=c)
    d.ellipse((hc[0] + 14 * s, hc[1] + 2 * s, hc[0] + 44 * s, hc[1] + 30 * s), fill=c)  # фильтр
    d.ellipse((hc[0] + 6 * s, hc[1] - 12 * s, hc[0] + 18 * s, hc[1]), fill=(170, 40, 20, 255))  # стекло
    # капюшон
    d.pieslice((hc[0] - 34 * s, hc[1] - 40 * s, hc[0] + 30 * s, hc[1] + 30 * s), 150, 330, fill=c)


def scene_waste(t):
    lt = t - S_WASTE
    sky = vgrad((60, 50, 45), (170, 120, 70))
    img = to_rgba(sky)
    d = ImageDraw.Draw(img)
    # мутное солнце
    sun = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sun).ellipse((430, 380, 590, 540), fill=(255, 210, 160, 160))
    img.alpha_composite(sun.filter(ImageFilter.GaussianBlur(25)))
    pan = int(lt * 10)
    img.alpha_composite(RUIN_BACK, (-50 - pan // 3, 0))
    img.alpha_composite(RUIN_FRONT, (-100 - pan // 2, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 1005, W, H), fill=(45, 34, 26, 255))
    # дорога/трещины
    for i in range(6):
        y = 1040 + i * 45
        d.line((0, y, W, y + (i % 2) * 15), fill=(30, 22, 18, 255), width=3)
    draw_survivor(d, lerp(-60, W * 0.62, ease(lt / 6.0)), 1130, t, 1.25)
    draw_ash(img, t, color=(210, 200, 190), wind=-60)
    # HUD дозиметра
    hud = ImageDraw.Draw(img)
    dose = 4.7 + 0.6 * math.sin(t * 7) + rng.random() * 0.4
    hud.rounded_rectangle((26, 60, 330, 150), 14, fill=(0, 0, 0, 200), outline=(120, 255, 90, 255), width=3)
    hud.text((44, 76), f"☢ {dose:4.2f} мЗв/ч", font=font(34, True), fill=(120, 255, 90, 255))
    if int(t * 4) % 2 == 0:
        hud.ellipse((300, 70, 316, 86), fill=(255, 40, 40, 255))
    text_center(ImageDraw.Draw(img), 230, "ДЕНЬ 347", 104 if lt < 0.3 else 96,
                fill=(255, 235, 210), stroke=7)
    if lt > 1.4:
        caption_box(img, 420, "Я всё ещё жив.", 50, S_WASTE + 1.4, t)
    if lt > 3.4:
        caption_box(img, 560, "Вода — 2 литра.\nФильтров — 1.", 42, S_WASTE + 3.4, t, color=(255, 200, 140))
    arr = np.asarray(img.convert("RGB"), np.float32)
    # тёплая выжженная цветокоррекция
    arr = arr * np.array([1.08, 0.97, 0.85])
    return post(arr, t, grain=16, shake=1.2)


def scene_radio(t):
    lt = t - S_RADIO
    static_amt = clamp01(1 - lt / 1.2)
    noise = rng.integers(0, 255, (H // 4, W // 4, 1), dtype=np.uint8).repeat(4, 0).repeat(4, 1)
    base = np.repeat(noise, 3, axis=2).astype(np.float32)
    dark = np.zeros((H, W, 3), np.float32)
    arr = base * static_amt + dark * (1 - static_amt)
    img = to_rgba(arr)
    d = ImageDraw.Draw(img)
    if lt > 0.8:
        # индикатор частоты
        d.rounded_rectangle((110, 180, W - 110, 280), 16, outline=(255, 170, 40, 255), width=3, fill=(20, 12, 0, 255))
        text_center(d, 200, "147.3 МГц", 50, fill=(255, 170, 40), stroke=0, mono=True)
        # осциллограмма голоса
        pts = []
        for x in range(60, W - 60, 6):
            amp = 50 * math.sin(x * 0.05 + t * 20) * math.sin(x * 0.013 + t * 3) * (0.5 + 0.5 * math.sin(t * 9))
            pts.append((x, 400 + amp))
        d.line(pts, fill=(255, 170, 40, 255), width=4)
    if lt > 1.3:
        caption_box(img, 560, "Если ты это слышишь —\nты не один.", 48, S_RADIO + 1.3, t)
    if lt > 3.0:
        text_center(ImageDraw.Draw(img), 900, "☢ ПОДПИШИСЬ ☢", 70,
                    fill=(255, 60, 40) if int(t * 3) % 2 else (255, 230, 60), stroke=6)
        text_center(ImageDraw.Draw(img), 1000, "чтобы выжить", 52, fill=(255, 255, 255), stroke=5)
    arr = np.asarray(img.convert("RGB"), np.float32) * SCAN
    return post(arr, t, grain=10, chroma=3 if static_amt > 0 else 0)


def render(t):
    if t < S_CITY:
        fr = scene_alert(t)
        # переход: шум в конце
        if t > S_CITY - 0.25:
            fr = np.clip(fr * 0.3 + rng.integers(0, 255, fr.shape) * 0.7, 0, 255).astype(np.uint8)
        return fr
    if t < S_BLAST:
        return scene_city(t)
    if t < S_WASTE:
        fr = scene_city(t, blast=t - S_BLAST)
        if t > S_WASTE - 0.5:  # затемнение
            fr = (fr * clamp01((S_WASTE - t) / 0.5)).astype(np.uint8)
        return fr
    if t < S_RADIO:
        fr = scene_waste(t)
        if t < S_WASTE + 0.5:
            fr = (fr * clamp01((t - S_WASTE) / 0.5)).astype(np.uint8)
        return fr
    return scene_radio(t)


# ---------------------------------------------------------------------- audio
def lp_fast(x, cutoff):
    """Простой ФНЧ через FFT."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def env(tt, a, b, fade=0.05):
    e = np.clip((tt - a) / fade, 0, 1) * np.clip((b - tt) / fade, 0, 1)
    return e


def make_audio(path):
    n = int(DUR * SR)
    tt = np.arange(n) / SR
    mix = np.zeros(n)
    ar = np.random.default_rng(7)

    # Фоновый гул-дрон на протяжении всего ролика
    drone = sum(np.sin(2 * np.pi * f * tt + p) for f, p in ((41.2, 0), (41.7, 1), (55.0, 2), (82.4, 3)))
    drone *= 0.10 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.15 * tt))
    mix += drone * np.clip(tt / 1.0, 0, 1)

    # 1) Сирена гражданской обороны
    freq = 520 + 300 * (0.5 - 0.5 * np.cos(2 * np.pi * tt / 2.0))
    siren = np.sin(2 * np.pi * np.cumsum(freq) / SR)
    siren = np.sign(siren) * np.abs(siren) ** 0.6
    mix += 0.22 * siren * env(tt, 0, S_CITY, 0.2)
    # пики EAS-сигнала
    eas = (np.sin(2 * np.pi * 853 * tt) + np.sin(2 * np.pi * 960 * tt)) * 0.5
    mix += 0.12 * eas * env(tt, 0.0, 0.9, 0.02)

    # 2) Город: тихий ветер + мрачная мелодия (минор)
    wind = lp_fast(ar.normal(0, 1, n), 500) * 0.6
    mix += wind * env(tt, S_CITY, S_BLAST, 0.5) * 0.5
    notes = [220.0, 261.6, 246.9, 196.0]
    for i, f in enumerate(notes):
        a = S_CITY + i * 1.1
        e = env(tt, a, a + 1.05, 0.08) * np.exp(-np.clip(tt - a, 0, None) * 1.2)
        mix += 0.14 * e * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt))

    # 3) Взрыв: удар + рокот
    bt = np.clip(tt - S_BLAST, 0, None)
    boom_noise = lp_fast(ar.normal(0, 1, n), 140)
    boom = boom_noise * np.exp(-bt * 0.9) * (tt >= S_BLAST)
    sub = np.sin(2 * np.pi * (45 * bt - 8 * bt ** 2 / 2)) * np.exp(-bt * 1.5) * (tt >= S_BLAST)
    crack = ar.normal(0, 1, n) * np.exp(-bt * 12) * (tt >= S_BLAST)
    mix += (2.2 * boom + 0.9 * sub + 0.6 * crack) * env(tt, S_BLAST, S_WASTE, 0.02)
    # высокий звон в ушах
    mix += 0.05 * np.sin(2 * np.pi * 3800 * tt) * env(tt, S_BLAST + 0.3, S_BLAST + 3.5, 1.0)

    # 4) Пустошь: ветер + счётчик Гейгера
    wind2 = lp_fast(ar.normal(0, 1, n), 900)
    mix += 0.45 * wind2 * env(tt, S_WASTE, S_RADIO, 0.6) * (0.7 + 0.3 * np.sin(tt * 1.7))
    clicks = np.zeros(n)
    rate = 9.0
    tcur = S_WASTE
    while tcur < S_RADIO:
        tcur += ar.exponential(1 / rate)
        i = int(tcur * SR)
        if i + 200 < n:
            clicks[i:i + 200] += np.exp(-np.arange(200) / 18) * ar.choice([-1, 1])
    mix += 0.5 * clicks
    for i, f in enumerate([110.0, 130.8, 98.0]):  # мрачные аккорды
        a = S_WASTE + i * 2.0
        e = env(tt, a, a + 2.0, 0.4)
        mix += 0.06 * e * sum(np.sin(2 * np.pi * f * m * tt) for m in (1, 1.5, 2))

    # 5) Радио: статика -> голос-«морзе»
    static = ar.normal(0, 1, n) * (1 - np.clip((tt - S_RADIO) / 1.2, 0, 1)) * (tt >= S_RADIO)
    mix += 0.35 * static
    morse = "·−·· ·· ·−−· ·· −−−"
    tc = S_RADIO + 1.2
    for ch in morse:
        if ch == " ":
            tc += 0.18; continue
        L = 0.07 if ch == "·" else 0.2
        mix += 0.12 * np.sin(2 * np.pi * 700 * tt) * env(tt, tc, tc + L, 0.005)
        tc += L + 0.07
    # финальный удар
    ft = np.clip(tt - (S_RADIO + 3.0), 0, None)
    mix += 1.2 * boom_noise * np.exp(-ft * 2.5) * (tt >= S_RADIO + 3.0)

    # мастер
    mix *= np.clip((DUR - tt) / 0.8, 0, 1)
    mix = np.tanh(mix * 1.3)
    mix /= np.max(np.abs(mix)) + 1e-9
    data = (mix * 0.9 * 32767).astype(np.int16)
    stereo = np.stack([data, data], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(stereo.tobytes())


# ----------------------------------------------------------------------- main
def main():
    wav = OUT + ".wav"
    print("Синтез звука…")
    make_audio(wav)
    print("Рендер кадров…")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-vf", "scale=1080:1920:flags=lanczos",
           "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(NFRAMES):
        fr = render(i / FPS)
        p.stdin.write(fr.tobytes())
        if i % 60 == 0:
            print(f"  {i}/{NFRAMES}")
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
