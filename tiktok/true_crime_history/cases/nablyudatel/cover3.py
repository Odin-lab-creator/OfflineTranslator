"""Обложка «Наблюдатель» v3 — атмосферная ночная: холодная цветокоррекция, туман, виньетка, тёплые окна,
одно крупное название со свечением (Handjet) и маленькая подпись канала. Никаких лент, бумажек и кругов.
Сетка TikTok: важное в y 240…1460 (cover.py).  python3 cover3.py [кадр с туманом] → covers/v3_*.png + covers/v3_grid.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from cover import grid_tile, W, H
from cover2 import handjet, text_mask, dilate

HERE = os.path.dirname(os.path.abspath(__file__))
RED = (232, 34, 40)


def grade(a):
    """Ночь: тени в холодный сине-зелёный, светлое тёплое (окна) не трогаем, контраст, туман снизу, виньетка."""
    a = a / 255.0
    lum = a.mean(2, keepdims=True)
    warm = np.clip((a[..., :1] - a[..., 2:3]) * 3, 0, 1) * np.clip(lum * 2, 0, 1)      # огни окон
    cold = a * np.array([0.62, 0.80, 1.05]) ** 1.0
    cold = np.clip((cold - 0.04) * 1.18, 0, 1) ** 1.15                                  # глубже тени
    a = cold * (1 - warm) + np.clip(a * 1.15, 0, 1) * warm
    hh, ww = a.shape[:2]
    yy = np.linspace(0, 1, hh)[:, None, None]
    xx = np.linspace(-1, 1, ww)[None, :, None]
    fog = np.clip((yy - 0.55) / 0.4, 0, 1) ** 1.5 * 0.22
    a = a * (1 - fog) + np.array([0.55, 0.62, 0.72]) * fog
    a *= 1 - 0.75 * np.clip((0.30 - yy) / 0.22, 0, 1)                                   # тёмное небо под название
    a *= 1 - 0.55 * np.clip(np.hypot(xx * 0.9, (yy - 0.52) * 1.6) - 0.55, 0, 1)        # виньетка
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def glow_title(text, size):
    """Белые пиксельные буквы, тонкий тёмный контур и красное свечение вокруг."""
    face = text_mask(text, handjet(size, 900), pad=90)
    out_m = dilate(face, 4)
    glow = Image.fromarray((dilate(face, 10) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(26))
    g = np.asarray(glow, np.float32) / 255 * 0.95
    rgba = np.zeros(face.shape + (4,), np.float32)
    rgba[..., :3] = RED
    rgba[..., 3] = g * 255
    rgba[out_m] = (10, 6, 8, 255)
    rgba[face] = (250, 246, 240, 255)
    return Image.fromarray(rgba.clip(0, 255).astype(np.uint8), "RGBA")


def label(text, size, color, spacing=10):
    f = handjet(size, 600)
    w = int(sum(f.getlength(c) for c in text) + spacing * (len(text) - 1)) + 8
    im = Image.new("RGBA", (w, int(size * 1.3)), (0, 0, 0, 0))
    d, x = ImageDraw.Draw(im), 4
    for c in text:
        d.text((x, im.height // 2), c, font=f, fill=color, anchor="lm", fontmode="1")
        x += f.getlength(c) + spacing
    return im


def make(src, name, shift=0):
    im = Image.open(src).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x = (im.width - W) // 2
    im = im.crop((x, 0, x + W, H))
    if shift:                                         # поднять картинку, чтобы низ не прятался под просмотрами
        base = Image.new("RGB", (W, H), (6, 8, 12))
        base.paste(im, (0, -shift))
        fade = np.asarray(base, np.float32)
        yy = np.arange(H)[:, None, None]
        edge = H - shift
        fade *= np.clip(1 - (yy - (edge - 120)) / 120, 0, 1) * (yy >= edge - 120) + (yy < edge - 120)
        im = Image.fromarray(fade.astype(np.uint8))
    im = Image.fromarray(grade(np.asarray(im, np.float32))).convert("RGBA")
    t = glow_title("НАБЛЮДАТЕЛЬ", 230)
    tw = W - 40                                       # буквы ~980 px, свечение может уходить за край
    t = t.resize((tw + 180, round(t.height * (tw + 180) / t.width)), Image.NEAREST)
    lab = label("TRUE CRIME HISTORY", 46, (225, 225, 232, 255))
    y_lab = 262
    im.alpha_composite(lab, ((W - lab.width) // 2, y_lab))
    d = ImageDraw.Draw(im)
    for sx in (-1, 1):                                # красные точки по бокам подписи, «запись»
        cx = W // 2 + sx * (lab.width // 2 + 26)
        d.rectangle([cx - 7, y_lab + lab.height // 2 - 7, cx + 7, y_lab + lab.height // 2 + 7], fill=(*RED, 255))
    im.alpha_composite(t, ((W - t.width) // 2, y_lab + lab.height - 92))
    im = im.convert("RGB")
    im.save(os.path.join(HERE, "covers", f"v3_{name}.png"))
    return im


if __name__ == "__main__":
    # кадр с туманом — 5.5 с клипа 01: ffmpeg -ss 5.5 -i clips/01.mp4 -frames:v 1 covers/src_01fog.jpg
    S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "covers", "src_01fog.jpg")
    srcs = [(os.path.join(HERE, "frames", "46.jpg"), "46", 0),
            (os.path.join(HERE, "frames", "01.jpg"), "01", 200)]
    if S:
        srcs.insert(1, (S, "01fog", 200))
    ims = [make(*s) for s in srcs]
    tiles = [grid_tile(im) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 310 + 10, tiles[0].height + 20), (0, 0, 0))
    for i, tl in enumerate(tiles):
        prev.paste(tl, (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", "v3_grid.png"))
    full = Image.new("RGB", (len(ims) * 370 + 10, 660), (0, 0, 0))
    for i, im in enumerate(ims):
        full.paste(im.resize((360, 640)), (10 + i * 370, 10))
    full.save(os.path.join(HERE, "covers", "v3_full.png"))
    print("готово")
