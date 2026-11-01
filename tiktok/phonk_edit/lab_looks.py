#!/usr/bin/env python3
"""Лаборатория эффектов: одни и те же кадры через разные «винтажные» обработки + варианты надписи.

cd tiktok/phonk_edit && python3 lab_looks.py  →  lab/looks_1.png, lab/looks_2.png, lab/logos.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = sys.argv[:1]
import build_edit as be  # noqa: E402
import build_vhs as bv  # noqa: E402

VW, VH = bv.VW, bv.VH
OUTD = os.path.join(HERE, "lab")
os.makedirs(OUTD, exist_ok=True)
SHOTS = [(182.9, "Ferrari"), (196.3, "Lamborghini"), (88.9, "ночная трасса")]
YY, XX = np.mgrid[0:VH, 0:VW].astype(np.float32)
NX, NY = (XX - VW / 2) / (VW / 2), (YY - VH / 2) / (VH / 2)
R2 = NX ** 2 + NY ** 2


def frame(t):
    return bv.crop43(be.decode(t, 0.1)[0])


def with_logo(img, a=0.26):
    L = bv.logo()
    return img * (1 - L * a) + 255 * L * a


def vhs(img, i=0, glitch=0.0):
    bv._prev = None
    return bv.vhs(img, 1.3 + i * 0.37, 1000 + i, glitch)


def grain(img, sigma, seed, size=2):
    r = np.random.default_rng(seed)
    g = r.normal(0, sigma, (VH // size + 1, VW // size + 1))
    g = np.asarray(Image.fromarray(g.astype(np.float32)).resize((VW, VH), Image.BILINEAR))
    return img + g[..., None]


def rounded(img, rad=26):
    m = Image.new("L", (VW, VH), 0)
    ImageDraw.Draw(m).rounded_rectangle((4, 4, VW - 5, VH - 5), rad, fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(3)), np.float32)[..., None] / 255
    return img * m


# ------------------------------------------------------------------ варианты
def look_film(img, i):
    x = with_logo(img)
    x = x * np.array([1.10, 1.0, 0.82]) + np.array([18, 8, 0])          # тёплая плёнка
    lum = x.mean(-1, keepdims=True)
    x = lum + (x - lum) * 0.85
    x = (x / 255) ** 1.08 * 255
    r = np.random.default_rng(50 + i)
    leak = np.exp(-(((XX - VW * 0.95) / 140) ** 2 + ((YY - VH * 0.2) / 120) ** 2))[..., None]
    x = x + leak * np.array([120, 50, 0])                                  # засветка
    x = grain(x, 11, 70 + i)
    for _ in range(25):                                                    # пыль
        cx, cy = r.integers(0, VW), r.integers(0, VH)
        x[max(0, cy - 1):cy + 1, max(0, cx - 1):cx + 1] = 240 if r.random() < 0.5 else 15
    for _ in range(2):                                                     # царапины
        sx = int(r.integers(20, VW - 20))
        x[:, sx] = x[:, sx] * 0.5 + 200 * 0.5
    x = np.roll(x, (int(r.integers(-2, 3)), int(r.integers(-1, 2))), (0, 1))   # дрожание кадра в окне
    x = x * np.clip(1.2 - 0.6 * R2, 0.2, 1)[..., None]
    return rounded(np.clip(x, 0, 255))


def look_nightcam(img, i):
    x = with_logo(img)
    lum = x.mean(-1, keepdims=True)
    x = np.concatenate([lum * 0.55, lum * 1.15 + 10, lum * 0.6], -1)     # зелёная ночная камера
    br = np.clip(x - 150, 0, None)
    bl = Image.fromarray(np.clip(br * 2, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))
    x = x + np.asarray(bl, np.float32) * 0.9
    x = vhs(np.clip(x, 0, 255), i)
    return x * np.clip(1.25 - 0.7 * R2, 0.15, 1)[..., None]


def look_heavy(img, i):
    bv._prev = None
    x = with_logo(img)
    x = bv.vhs(x, 2.0 + i, 2000 + i, glitch=0.7)
    x = np.roll(x, 6, axis=1) * np.array([1.0, 0.95, 1.0])
    # «волна» по строкам
    sh = np.round(6 * np.sin(np.arange(VH) * 0.09 + i)).astype(int)
    idx = (np.arange(VW)[None, :] - sh[:, None]) % VW
    return x[np.arange(VH)[:, None], idx]


def look_bwred(img, i):
    x = with_logo(img)
    R, G, B = x[..., 0], x[..., 1], x[..., 2]
    red = np.clip((R - np.maximum(G, B) * 1.35) / 60, 0, 1)[..., None]
    lum = (0.3 * R + 0.59 * G + 0.11 * B)[..., None]
    bw = np.clip((lum - 128) * 1.45 + 120, 0, 255).repeat(3, -1)
    x = bw * (1 - red) + x * np.array([1.15, 0.6, 0.6]) * red
    x = grain(x, 9, 90 + i)
    return vhs(np.clip(x, 0, 255), i) * np.clip(1.2 - 0.55 * R2, 0.2, 1)[..., None]


def look_crt(img, i):
    x = vhs(with_logo(img), i)
    x = bv.fisheye(x, 0.12)
    x = x * (1 - 0.35 * (np.arange(VH) % 2))[:, None, None]               # строки развёртки
    mask = np.ones((VH, VW, 3), np.float32) * 0.78
    for c in range(3):
        mask[:, c::3, c] = 1.15                                            # сетка RGB
    x = x * mask
    glow = np.asarray(Image.fromarray(np.clip(x, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32)
    x = x * 0.8 + glow * 0.45
    return rounded(x, 40)


def look_skate(img, i):
    x = with_logo(img)
    x = bv.fisheye(x, 0.55)
    x = vhs(x, i)
    circle = np.clip((1.12 - np.sqrt(NX ** 2 * 0.75 + NY ** 2)) * 8, 0, 1)[..., None]
    return x * circle


LOOKS = [("1. Текущий VHS", lambda img, i: vhs(with_logo(img), i)), ("2. Плёнка 8 мм", look_film),
         ("3. Ночная камера", look_nightcam), ("4. Жёсткий VHS", look_heavy),
         ("5. Ч/б + красный", look_bwred), ("6. ЭЛТ-телевизор", look_crt), ("7. Скейт-камера", look_skate)]


def label(img, text):
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    d.rectangle((0, 0, d.textlength(text, font=f) + 12, 26), fill=(0, 0, 0))
    d.text((6, 3), text, font=f, fill=(255, 220, 80))
    return im


def sheet(rows, path):
    tw, th = 400, 300
    S = Image.new("RGB", (tw * 3 + 8, th * len(rows) + 4 * (len(rows) - 1)), (40, 40, 40))
    for r, (name, fn) in enumerate(rows):
        for c, img in enumerate(SRC):
            out = fn(img.copy(), r * 3 + c)
            tile = label(out, name if c == 0 else "").resize((tw, th), Image.BILINEAR)
            S.paste(tile, (c * (tw + 4), r * (th + 4)))
    S.save(path)
    return path


# ------------------------------------------------------------------ надпись
def logos():
    base = vhs(frame(SHOTS[2][0]), 9)
    f = ImageFont.truetype(bv.GOTHIC, 118)

    def layer(fill_fn, extra=None):
        L = Image.new("L", (VW, VH), 0)
        d = ImageDraw.Draw(L)
        w = d.textlength("Jxned", font=f)
        d.text(((VW - w) / 2, VH / 2 - 78), "Jxned", font=f, fill=255)
        return np.asarray(L, np.float32)[..., None] / 255

    L = layer(None)
    blur = lambda m, r: np.asarray(Image.fromarray((m[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)[..., None] / 255
    out = []
    out.append(("A. Белая, 26% (сейчас)", base * (1 - L * 0.26) + 255 * L * 0.26))
    g = blur(L, 8)
    x = base + g * np.array([160, 0, 20]) * 0.9
    out.append(("B. Красное свечение", x * (1 - L * 0.55) + np.array([200, 20, 30]) * L * 0.55))
    grad = np.linspace(1.0, 0.45, VH)[:, None, None]
    chrome = np.concatenate([235 * grad, 238 * grad, 245 * grad], -1)
    edge = np.clip(blur(L, 1.5) * 3 - L * 3, 0, 1)
    x = base * (1 - edge * 0.8)
    out.append(("C. Хром с контуром", x * (1 - L * 0.7) + chrome * L * 0.7))
    g = blur(L, 6)
    x = base + g * 120
    out.append(("D. Тёмная со свечением", x * (1 - L * 0.75)))
    return out


def logo_sheet(path):
    items = logos()
    tw, th = 480, 360
    S = Image.new("RGB", (tw * 2 + 4, th * 2 + 4), (40, 40, 40))
    for k, (name, img) in enumerate(items):
        S.paste(label(img, name), ((k % 2) * (tw + 4), (k // 2) * (th + 4)))
    S.save(path)


if __name__ == "__main__":
    SRC = [frame(t) for t, _ in SHOTS]
    print(sheet(LOOKS[:4], os.path.join(OUTD, "looks_1.png")))
    print(sheet(LOOKS[4:], os.path.join(OUTD, "looks_2.png")))
    logo_sheet(os.path.join(OUTD, "logos.png")); print("logos.png")
