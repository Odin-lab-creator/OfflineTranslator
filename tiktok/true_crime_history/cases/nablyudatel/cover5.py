"""Обложка «Наблюдатель» v5 — доработка варианта A (запись камеры наблюдения), который выбрал владелец.
Шрифт Handjet (узкий пиксельный, как экранные надписи видеокамеры) вместо Press Start; VHS: красно-голубое
двоение букв, строки развёртки, шум; экранные надписи камеры: ● REC, время, дата, батарея, CAM.
python3 cover5.py → covers/v5_1.png, v5_2.png + covers/v5_grid.png
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cover import grid_tile, W, H
from cover2 import handjet, text_mask
from cover4 import background, crop_alpha

HERE = os.path.dirname(os.path.abspath(__file__))
RED, WHITE = (236, 36, 40), (244, 244, 236)


def osd(text, size, color=WHITE, weight=700, shape=2, spacing=4):
    """Надпись камеры: пиксельные буквы с тонкой тёмной тенью."""
    f = handjet(size, weight, shape)
    w = int(sum(f.getlength(c) for c in text) + spacing * len(text)) + 20
    m = Image.new("L", (w, int(size * 1.5)), 0)
    d, x = ImageDraw.Draw(m), 6
    for c in text:
        d.text((x, m.height // 2), c, font=f, fill=255, anchor="lm", fontmode="1")
        x += f.getlength(c) + spacing
    a = np.asarray(m) > 0
    rgba = np.zeros(a.shape + (4,), np.uint8)
    sh = np.roll(np.roll(a, 3, 0), 3, 1) & ~a
    rgba[sh] = (0, 0, 0, 160)
    rgba[a] = (*color, 255)
    return crop_alpha(Image.fromarray(rgba, "RGBA"))


def vhs_title(text, size, weight=900, shape=2, split=7):
    """Крупное название: белое, с красным и голубым смещением (как на старой плёнке) и мягкой тенью."""
    face = text_mask(text, handjet(size, weight, shape), pad=40)
    h, w = face.shape
    rgba = np.zeros((h, w, 4), np.float32)
    shadow = np.roll(np.roll(face, 10, 0), 6, 1)
    rgba[shadow] = (0, 0, 0, 150)
    rgba[np.roll(face, -split, 1)] = (255, 40, 60, 220)
    cy = np.roll(face, split, 1)
    rgba[cy] = (40, 220, 255, 200)
    rgba[face] = (*WHITE, 255)
    return crop_alpha(Image.fromarray(rgba.astype(np.uint8), "RGBA"))


def vhs_finish(im):
    """Строки развёртки, лёгкий шум и чуть приподнятые чёрные — как кадр с кассеты."""
    a = np.asarray(im.convert("RGB"), np.float32)
    a[::4] *= 0.82
    rng = np.random.default_rng(7)
    a += rng.normal(0, 7, a.shape[:2])[..., None]
    a = a * 0.94 + 8
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def frame_marks(im, top, bot, m=64, L=84, t=7):
    d = ImageDraw.Draw(im)
    for x0, y0, sx, sy in ((m, top, 1, 1), (W - m, top, -1, 1), (m, bot, 1, -1), (W - m, bot, -1, -1)):
        d.rectangle([min(x0, x0 + sx * L), min(y0, y0 + sy * t), max(x0, x0 + sx * L), max(y0, y0 + sy * t)], fill=(*WHITE, 235))
        d.rectangle([min(x0, x0 + sx * t), min(y0, y0 + sy * L), max(x0, x0 + sx * t), max(y0, y0 + sy * L)], fill=(*WHITE, 235))


def battery(im, x, y):
    d = ImageDraw.Draw(im)
    d.rectangle([x, y, x + 58, y + 28], outline=(*WHITE, 255), width=4)
    d.rectangle([x + 58, y + 8, x + 64, y + 20], fill=(*WHITE, 255))
    for i in range(3):
        d.rectangle([x + 8 + i * 16, y + 8, x + 18 + i * 16, y + 20], fill=(*WHITE, 255))


def make(name, title_shape):
    im = background()
    top, bot, m = 248, 1446, 64
    frame_marks(im, top, bot, m)
    d = ImageDraw.Draw(im)
    # верхняя строка камеры: ● REC слева, батарея справа
    d.ellipse([m + 34, top + 36, m + 66, top + 68], fill=(*RED, 255))
    rec = osd("REC", 52)
    im.alpha_composite(rec, (m + 80, top + 52 - rec.height // 2))
    battery(im, W - m - 34 - 64, top + 38)
    # название
    t = vhs_title("НАБЛЮДАТЕЛЬ", 230, 900, title_shape)
    k = (W - 2 * m - 60) / t.width
    t = t.resize((round(t.width * k), round(t.height * k)), Image.NEAREST)
    ty = top + 112
    im.alpha_composite(t, ((W - t.width) // 2, ty))
    sub = osd("TRUE CRIME HISTORY", 46, (215, 215, 225), 600, 2, 10)
    im.alpha_composite(sub, ((W - sub.width) // 2, ty + t.height + 22))
    # нижняя строка камеры (выше плашки просмотров в профиле): CAM 02 слева, дата и время справа
    cam = osd("CAM 02", 46)
    im.alpha_composite(cam, (m + 34, bot - 40 - cam.height))
    ts = osd("06.2014  23:47", 46)
    im.alpha_composite(ts, (W - m - 34 - ts.width, bot - 40 - ts.height))
    out = vhs_finish(im)
    out.save(os.path.join(HERE, "covers", f"v5_{name}.png"))
    return out


if __name__ == "__main__":
    ims = [make("1", 2), make("2", 12)]
    tiles = [grid_tile(im, 300) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 310 + 10, tiles[0].height + 20), (0, 0, 0))
    for i, tl in enumerate(tiles):
        prev.paste(tl, (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", "v5_grid.png"))
    print("готово")
