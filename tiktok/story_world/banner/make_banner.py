#!/usr/bin/env python3
"""Шапка YouTube-канала story world: 2560×1440, вся надпись в безопасной зоне.

python3 make_banner.py  →  youtube_banner.png      (загружать в YouTube)
                           youtube_banner_zones.png (превью: что видно на ТВ, компьютере и телефоне)

Зоны YouTube: ТВ видит всё 2560×1440; компьютер — полосу 2560×423 по центру;
телефон — только середину 1546×423. Поэтому надпись должна целиком влезать в 1546×423.

В исходнике (banner_src.png, 2560×423) слово WORLD обрезано снизу: старую надпись стираем
(cv2.inpaint), рисуем новую тем же стилем (плитный шрифт Alfa Slab One, OFL, крупный пиксель)
и ставим её по центру полосы. Сверху и снизу для ТВ полоса продолжается размытым фоном.
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "AlfaSlabOne-Regular.ttf")
W, H, BAND = 2560, 1440, 423
BAND_Y = (H - BAND) // 2                     # 508: верх полосы, видимой на компьютере
SAFE_W = 1546                                # что видно на телефоне
P = 4                                        # размер «пикселя» надписи
CAP = 140                                    # высота букв, px
GAP = 18                                     # между STORY и WORLD, px
RNG = np.random.default_rng(7)


# ---------- 1. стираем старую надпись ----------
def erase_old_logo(src):
    a = src.astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(2), a.min(2)
    grey = (mn > 120) & (mx - mn < 50)                       # STORY: светло-серый камень
    orange = (r > 170) & (r - b > 90) & (g > 60)             # WORLD и тире: оранжевый
    # только там, где стояли буквы старой надписи (иначе маска цепляет закат и плащ)
    boxes = [(950, 125, 1660, 292), (860, 288, 1722, 423), (700, 345, 860, 392), (1720, 345, 1880, 392)]
    zone = np.zeros(mx.shape, bool)
    near = np.zeros(mx.shape, bool)
    for x0, y0, x1, y1 in boxes:
        zone[y0:y1, x0:x1] = True
        near[max(0, y0 - 16):y1 + 16, max(0, x0 - 16):x1 + 16] = True
    text = ((grey | orange) & zone).astype(np.uint8) * 255
    text = cv2.morphologyEx(text, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    mask = cv2.dilate(text, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))   # с обводкой и тенью
    mask[~near] = 0
    bgr = cv2.cvtColor(src, cv2.COLOR_RGB2BGR)
    out = cv2.inpaint(bgr, mask, 9, cv2.INPAINT_TELEA)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB), mask


# ---------- 2. новая надпись в крупный пиксель ----------
def text_mask(word, cap_px):
    """Маска слова в низком разрешении (1 px = P px на экране), высота заглавных cap_px."""
    size = 10
    while True:
        f = ImageFont.truetype(FONT, size)
        x0, y0, x1, y1 = f.getbbox("H")
        if y1 - y0 >= cap_px:
            break
        size += 1
    track = 1
    widths = [f.getbbox(ch)[2] for ch in word]
    w = sum(widths) + track * (len(word) - 1) + 8
    img = Image.new("L", (w, cap_px + 12), 0)
    d = ImageDraw.Draw(img)
    x = 4
    for ch, cw in zip(word, widths):
        d.text((x, 6 - y0), ch, font=f, fill=255)
        x += cw + track
    m = np.asarray(img) > 127
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def dilate(m, n=1):
    k = np.ones((2 * n + 1, 2 * n + 1), np.uint8)
    return cv2.dilate(m.astype(np.uint8), k).astype(bool)


def paint(mask, top, mid, bot, crack, light, outline):
    """Заливка буквы: вертикальный градиент, светлая кромка сверху, тёмная снизу, сколы и трещины."""
    h, w = mask.shape
    t = np.linspace(0, 1, h)[:, None, None]
    top, mid, bot = (np.array(c, float) for c in (top, mid, bot))
    grad = np.where(t < 0.5, top + (mid - top) * (t / 0.5), mid + (bot - mid) * ((t - 0.5) / 0.5))
    rgb = np.broadcast_to(grad, (h, w, 3)).copy()
    # сколы: мелкие пятна тёмного цвета
    spots = RNG.random((h, w)) < 0.012
    spots = dilate(spots, 0) | (dilate(RNG.random((h, w)) < 0.0025, 1) & (RNG.random((h, w)) < 0.5))
    rgb[spots] = rgb[spots] * 0.55 + np.array(crack) * 0.45
    # трещины: короткие ломаные линии
    for _ in range(max(2, w // 16)):
        y, x = RNG.integers(2, h - 2), RNG.integers(1, w - 1)
        for _ in range(RNG.integers(3, 7)):
            if 0 <= y < h and 0 <= x < w:
                rgb[y, x] = crack
            y += RNG.integers(-1, 2)
            x += RNG.choice([-1, 1])
    # фаска: верхний ряд светлее, нижний темнее
    up = mask & ~np.roll(mask, 1, 0)
    dn = mask & ~np.roll(mask, -1, 0)
    rgb[up] = rgb[up] * 0.4 + np.array(light) * 0.6
    rgb[dn] = rgb[dn] * 0.6
    # обводка и тень
    out = np.zeros((h + 6, w + 6, 4), float)
    m = np.pad(mask, 3)
    ring = dilate(m, 1)
    shadow = np.roll(np.roll(dilate(m, 1), 2, 0), 1, 1)
    out[shadow] = (8, 4, 10, 235)
    out[ring] = (*outline, 255)
    out[3:-3, 3:-3][mask] = np.concatenate([rgb[mask], np.full((mask.sum(), 1), 255.0)], 1)
    return out


def dash(w, h):
    m = np.ones((h, w), bool)
    m[0, :1] = m[-1, :1] = m[0, -1:] = m[-1, -1:] = False                 # срезанные углы
    return m


def build_logo():
    cap = CAP // P
    story = paint(text_mask("STORY", cap), (238, 234, 242), (205, 199, 214), (150, 143, 162),
                  (104, 96, 118), (255, 255, 255), (28, 22, 34))
    world = paint(text_mask("WORLD", cap), (255, 205, 70), (255, 152, 32), (222, 96, 24),
                  (170, 70, 16), (255, 236, 150), (46, 18, 6))
    dw, dh = 34, 5
    d = paint(dash(dw, dh), (255, 200, 70), (255, 150, 30), (220, 95, 24), (220, 95, 24),
              (255, 236, 150), (46, 18, 6))
    gap_d = 9
    lw = max(story.shape[1], world.shape[1] + 2 * (d.shape[1] + gap_d))
    lh = story.shape[0] + GAP // P + world.shape[0]
    logo = np.zeros((lh, lw, 4), float)

    def put(img, y, x):
        h, w = img.shape[:2]
        a = img[..., 3:4] / 255
        logo[y:y + h, x:x + w] = img * a + logo[y:y + h, x:x + w] * (1 - a)

    put(story, 0, (lw - story.shape[1]) // 2)
    wy = story.shape[0] + GAP // P
    wx = (lw - world.shape[1]) // 2
    put(world, wy, wx)
    dy = wy + world.shape[0] // 2 - d.shape[0] // 2
    put(d, dy, wx - gap_d - d.shape[1])
    put(d, dy, wx + world.shape[1] + gap_d)
    big = np.repeat(np.repeat(logo, P, 0), P, 1)                           # крупный пиксель
    return big


# ---------- 3. сборка полосы ----------
def compose_band(src):
    band, _ = erase_old_logo(src)
    logo = build_logo()
    lh, lw = logo.shape[:2]
    y0 = (BAND - lh) // 2
    x0 = (W - lw) // 2
    assert lw <= SAFE_W - 60, f"надпись шире безопасной зоны: {lw}"
    assert y0 >= 20, f"надпись не влезает по высоте: {lh}"
    a = np.zeros((BAND, W), np.float32)
    a[y0:y0 + lh, x0:x0 + lw] = logo[..., 3] / 255
    glow = cv2.GaussianBlur(cv2.dilate(a, np.ones((41, 41), np.uint8)), (0, 0), 28)
    out = band.astype(np.float32) * (1 - 0.72 * np.clip(glow * 1.3, 0, 1))[..., None]
    reg = out[y0:y0 + lh, x0:x0 + lw]
    al = logo[..., 3:4] / 255
    out[y0:y0 + lh, x0:x0 + lw] = logo[..., :3] * al + reg * (1 - al)
    return np.clip(out, 0, 255).astype(np.uint8), (x0, y0, lw, lh)


# ---------- 4. продолжение для ТВ ----------
def extend(band):
    cover = cv2.resize(band, (int(W * H / BAND), H), interpolation=cv2.INTER_AREA)
    cx = (cover.shape[1] - W) // 2
    cover = cv2.GaussianBlur(cover[:, cx:cx + W].astype(np.float32), (0, 0), 45) * 0.42
    canvas = cover.copy()
    sig = [2, 6, 18, 50, 140]
    for side in ("top", "bot"):
        row = band[:6].mean(0) if side == "top" else band[-6:].mean(0)
        levels = [cv2.GaussianBlur(row[None].astype(np.float32), (0, 0), s)[0] for s in sig]
        n = BAND_Y if side == "top" else H - BAND_Y - BAND
        for dd in range(n):
            s = 10 + dd * 0.6
            k = np.clip(np.interp(np.log(s), np.log(sig), np.arange(len(sig))), 0, len(sig) - 1)
            i = int(k); f = k - i
            r = levels[i] * (1 - f) + levels[min(i + 1, len(sig) - 1)] * f
            wgt = 0.85 * np.exp(-dd / 110)
            dark = 1 - 0.55 * dd / n
            y = BAND_Y - 1 - dd if side == "top" else BAND_Y + BAND + dd
            canvas[y] = (r * dark) * wgt + cover[y] * (1 - wgt)
    canvas[BAND_Y:BAND_Y + BAND] = band
    v = np.abs(np.arange(H) - H / 2) / (H / 2)                                  # лёгкая виньетка к краям ТВ
    canvas *= (1 - 0.35 * np.clip((v - 0.35) / 0.65, 0, 1) ** 1.5)[:, None, None]
    return np.clip(canvas, 0, 255).astype(np.uint8)


def zones_preview(img, logo_box):
    pv = Image.fromarray(img).resize((W // 2, H // 2), Image.LANCZOS).convert("RGBA")
    ov = Image.new("RGBA", pv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    s = 0.5
    d.rectangle([0, BAND_Y * s, W * s - 1, (BAND_Y + BAND) * s], outline=(80, 200, 255, 255), width=3)
    x0 = (W - SAFE_W) // 2
    d.rectangle([x0 * s, BAND_Y * s, (x0 + SAFE_W) * s, (BAND_Y + BAND) * s], outline=(120, 255, 120, 255), width=3)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    for txt, xy, col in (("ТВ: вся картинка", (12, 10), (255, 255, 255)),
                         ("компьютер", (12, BAND_Y * s + 8), (80, 200, 255)),
                         ("телефон (безопасная зона)", (x0 * s + 8, (BAND_Y + BAND) * s - 30), (120, 255, 120))):
        d.text(xy, txt, font=f, fill=(*col, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    return Image.alpha_composite(pv, ov).convert("RGB")


if __name__ == "__main__":
    src = np.asarray(Image.open(os.path.join(HERE, "banner_src.png")).convert("RGB"))
    assert src.shape[:2] == (BAND, W), src.shape
    band, box = compose_band(src)
    img = extend(band)
    out = os.path.join(HERE, "youtube_banner.png")
    Image.fromarray(img).save(out, optimize=True)
    mb = os.path.getsize(out) / 1e6
    if mb > 6:                                                                  # лимит YouTube 6 МБ
        out = os.path.join(HERE, "youtube_banner.jpg")
        Image.fromarray(img).save(out, quality=95)
        mb = os.path.getsize(out) / 1e6
    Image.fromarray(band).save(os.path.join(HERE, "preview_desktop.png"))
    x0 = (W - SAFE_W) // 2
    Image.fromarray(band[:, x0:x0 + SAFE_W]).save(os.path.join(HERE, "preview_phone.png"))
    zones_preview(img, box).save(os.path.join(HERE, "youtube_banner_zones.png"))
    print(out, f"{mb:.2f} МБ", "надпись:", box)
