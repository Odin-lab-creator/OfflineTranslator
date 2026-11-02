#!/usr/bin/env python3
"""Грубые превью других стилей для кинокомикса (без генераций) → styles/.

1. Нуар-комикс: чёрно-белые чернила + растр (halftone) + один акцентный цвет — фильтр по кадру Pro.
2. Карандашный набросок (как «This War of Mine»): графит, бумага, сепия — фильтр по кадру Pro.
3. Силуэты в тумане (как Limbo/Inside): сцена нарисована кодом, Денис — силуэт из спрайта.
Настоящая генерация в выбранном стиле (Gemini / FLUX) будет заметно лучше фильтров.
"""
import os

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "styles")
SRC = os.path.join(HERE, "pro360", "e2c_kitchen.png")
W, H = 1080, 1200


def smooth_source():
    im = Image.open(SRC).convert("RGB")
    return im.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.2))


def noir():
    im = smooth_source()
    g = np.asarray(ImageOps.autocontrast(im.convert("L"), cutoff=2)).astype(np.float32) / 255
    g = np.clip((g - 0.12) * 1.45, 0, 1)
    yy, xx = np.mgrid[0:H, 0:W]
    cell = 9                                                    # растр: точки по сетке под 45°
    u, v = (xx + yy) / cell, (xx - yy) / cell
    d = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    dots = d < (1 - g) * 0.62
    ink = np.where(g < 0.18, 0.0, np.where(g > 0.78, 1.0, np.where(dots, 0.0, 1.0)))
    edges = np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))) > 38
    ink[edges] = 0
    out = np.stack([ink * 236, ink * 230, ink * 214], -1)
    rgb = np.asarray(im).astype(np.float32)                    # акцент: тёплый свет холодильника — в красно-оранжевый
    warm = (rgb[..., 0] > rgb[..., 2] + 45) & (rgb[..., 0] > 110)
    out[warm & (ink > 0)] = (214, 72, 38)
    return Image.fromarray(out.astype(np.uint8))


def sketch():
    im = smooth_source().convert("L").filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(im).astype(np.float32)
    inv = np.asarray(ImageOps.invert(im).filter(ImageFilter.GaussianBlur(14))).astype(np.float32)
    dodge = np.clip(a * 255 / (256 - inv), 0, 255)              # карандашный контур (color dodge)
    tone = np.asarray(im.filter(ImageFilter.GaussianBlur(4))).astype(np.float32)
    tone = np.clip((tone - 20) * 1.25, 0, 255)
    t = np.minimum(dodge, 255) / 255 * (0.35 + 0.65 * tone / 255)
    yy, xx = np.mgrid[0:H, 0:W]
    hatch = (((xx + yy) % 8) < 2) & (t < 0.45)                   # штриховка в тенях
    t = np.where(hatch, t * 0.7, t)
    r = np.random.default_rng(3)
    paper = np.asarray(Image.fromarray(np.clip(r.normal(128, 10, (H, W)), 0, 255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) - 128
    t = np.clip(t + paper / 900, 0, 1)
    out = np.stack([t * 226 + 18, t * 212 + 15, t * 182 + 12], -1)
    vig = np.clip(1.12 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2), 0.55, 1)[..., None]
    return Image.fromarray(np.clip(out * vig, 0, 255).astype(np.uint8))


def limbo():
    r = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fog = 0.62 + 0.25 * np.exp(-((xx - 760) ** 2 + (yy - 330) ** 2) / (2 * 260 ** 2)) - 0.18 * (yy / H)
    img = np.repeat((fog * 255)[..., None], 3, 2)
    for k in range(6):                                          # лучи света из окна
        ang = -0.55 + k * 0.08
        d = np.abs((xx - 820) * np.cos(ang) + (yy - 180) * np.sin(ang))
        img += (np.clip(1 - d / 18, 0, 1) * 18 * (yy > 180))[..., None]

    def rect(x0, y0, x1, y1, c):
        img[int(y0):int(y1), int(x0):int(x1)] = c

    sil = 14
    rect(0, 930, W, H, sil)                                     # пол
    for x in (60, 330, 600):                                    # открытые двери — тёмные проёмы с косяками
        rect(x, 330, x + 18, 930, 40)
        rect(x + 170, 330, x + 188, 930, 40)
        rect(x, 312, x + 188, 330, 40)
        rect(x + 18, 330, x + 170, 930, 70 + r.integers(0, 20))
    rect(700, 120, 980, 140, 30)                                # окно в конце коридора
    rect(700, 120, 714, 420, 30)
    rect(966, 120, 980, 420, 30)
    for k in range(4):                                          # провода с потолка
        x = 120 + k * 260
        for y in range(0, 160 + k * 30):
            img[y, int(x + 14 * np.sin(y / 40)):int(x + 14 * np.sin(y / 40)) + 3] = sil
    rect(250, 860, 345, 930, sil)                               # чемодан и игрушка
    rect(280, 845, 315, 860, sil)
    yy2, xx2 = np.mgrid[0:H, 0:W]
    toy = ((xx2 - 400) ** 2 + (yy2 - 905) ** 2) < 26 ** 2
    img[toy] = sil
    sp = Image.open(os.path.join(HERE, "src", "denis128", "Idle__animations__shout__east__frame_007.png")).convert("RGBA")
    sp = sp.crop(sp.getbbox()).resize((sp.getbbox()[2] - sp.getbbox()[0], sp.getbbox()[3] - sp.getbbox()[1]))
    a = np.asarray(sp.resize((sp.width * 5, sp.height * 5), Image.LANCZOS))[..., 3] > 110
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))) > 120
    hy, hx = a.shape
    y0, x0 = 935 - hy, 520
    img[y0:y0 + hy, x0:x0 + hx][a] = 6
    img += r.normal(0, 5, (H, W, 1))                            # зерно
    vig = np.clip(1.15 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2), 0.3, 1)[..., None]
    img = img * vig
    img = img * np.array([0.95, 0.98, 1.0])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    items = [("1_noir", noir()), ("2_sketch", sketch()), ("3_limbo", limbo())]
    orig = Image.open(SRC).convert("RGB").resize((W, H), Image.NEAREST)
    for n, im in items:
        im.save(os.path.join(OUT, f"{n}.png"))
    S = Image.new("RGB", (4 * 548, 600), (24, 24, 28))
    for k, im in enumerate([orig] + [i for _, i in items]):
        S.paste(im.resize((540, 600)), (k * 548, 0))
    S.save(os.path.join(OUT, "styles_sheet.png"))
    print("готово")
