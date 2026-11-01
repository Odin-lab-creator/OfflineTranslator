#!/usr/bin/env python3
"""Аватарка TikTok-канала PIXEL APOCALYPSE из готовых ассетов PixelLab (без новых генераций).

python3 avatar.py  →  avatar/avatar_A.png, avatar_B.png, avatar_C.png (1080×1080) + avatar/preview.png

Сетка 45×45 арт-пикселей, пиксель 24×24 (крупнее, чем в видео, чтобы читалось в маленьком круге).
Персонажи и фон — в родном масштабе 1:1, все цвета — из главной палитры.
Луна из фона «ночная улица» стоит за головой — светлый круг вокруг тёмного силуэта.
"""
import os

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "pixellab", "assets")
OUT = os.path.join(HERE, "avatar")
N, PX = 45, 24
MOON = (90, 31)                      # центр луны в bg_night_street (160×192)


def sprite(name):
    return Image.open(os.path.join(A, name)).convert("RGBA")


def sky(moon_at):
    """Кусок неба N×N так, чтобы луна оказалась в точке moon_at кадра."""
    bg = Image.open(os.path.join(A, "bg_night_street.png")).convert("RGBA")
    x0, y0 = MOON[0] - moon_at[0], MOON[1] - moon_at[1]
    return bg.crop((x0, y0, x0 + N, y0 + N))


def put(canvas, spr, head, at):
    """Ставит спрайт так, чтобы точка head (центр головы в спрайте) попала в at."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(spr, (at[0] - head[0], at[1] - head[1]), spr)
    canvas.alpha_composite(layer)


def variant_a():                      # выживший: лицо в круге луны
    c = sky((22, 17))
    put(c, sprite("hero_rot/000.png"), (31, 10), (22, 17))
    return c


def variant_b():                      # заражённый: красные глаза на фоне луны
    c = sky((22, 17))
    put(c, sprite("zombie_rot/000.png"), (31, 11), (22, 17))
    return c


def variant_c():                      # встреча: герой и заражённый лицом к лицу под луной
    c = sky((22, 14))
    put(c, sprite("hero_rot/002.png"), (32, 10), (13, 20))
    put(c, sprite("zombie_rot/006.png"), (27, 10), (32, 20))
    return c


def big(img):
    return img.convert("RGB").resize((N * PX, N * PX), Image.NEAREST)


def circle(img, size):
    im = img.resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), m.resize((size, size), Image.LANCZOS))
    return out


def preview(items):
    """Как будет выглядеть в профиле (360), в ленте (110) и в комментариях (44), на тёмной и светлой теме."""
    W = 40 + len(items) * 600
    S = Image.new("RGB", (W, 900), (22, 24, 28))
    ImageDraw.Draw(S).rectangle((0, 450, W, 900), fill=(245, 245, 245))
    for k, (name, img) in enumerate(items):
        x = 40 + k * 600
        for y0 in (40, 490):
            S.paste(c := circle(img, 360), (x, y0), c)
            S.paste(c := circle(img, 110), (x + 400, y0 + 40), c)
            S.paste(c := circle(img, 44), (x + 433, y0 + 200), c)
    return S


def check_palette(img):
    import sys
    sys.path.insert(0, os.path.join(HERE, "pixellab"))
    import master_palette as mp
    pal = {tuple(int(v) for v in c) for c in mp.colors()}
    used = {tuple(p) for p in np.asarray(img.convert("RGB")).reshape(-1, 3)}
    return len(used), len(used - pal)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    items = [("A", variant_a()), ("B", variant_b()), ("C", variant_c())]
    for name, img in items:
        p = os.path.join(OUT, f"avatar_{name}.png")
        big(img).save(p)
        n, off = check_palette(img)
        print(p, f"цветов {n}, вне палитры {off}")
    preview([(n, big(i)) for n, i in items]).save(os.path.join(OUT, "preview.png"))
    print(os.path.join(OUT, "preview.png"))
