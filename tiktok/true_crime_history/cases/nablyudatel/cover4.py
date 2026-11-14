"""Обложка «Наблюдатель» v4 — кадр v3 с туманом (владельцу понравился), разные варианты надписи.
python3 cover4.py → covers/v4_A…D.png + covers/v4_grid.png
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import build
from cover import grid_tile, W, H
from cover2 import handjet, text_mask, dilate
from cover3 import grade

HERE = os.path.dirname(os.path.abspath(__file__))
RED, WHITE = (232, 34, 40), (246, 244, 238)
SRC, SHIFT = os.path.join(HERE, "covers", "src_01fog.jpg"), 200


def background():
    im = Image.open(SRC).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x = (im.width - W) // 2
    im = im.crop((x, 0, x + W, H))
    base = Image.new("RGB", (W, H), (6, 8, 12))
    base.paste(im, (0, -SHIFT))
    a = np.asarray(base, np.float32)
    yy = np.arange(H)[:, None, None]
    edge = H - SHIFT
    a *= np.where(yy < edge - 120, 1, np.clip(1 - (yy - (edge - 120)) / 120, 0, 1))
    return Image.fromarray(grade(a)).convert("RGBA")


def mask_img(m, color):
    rgba = np.zeros(m.shape + (4,), np.uint8)
    rgba[m] = (*color, 255)
    return Image.fromarray(rgba, "RGBA")


def crop_alpha(im):
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > 0)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def spaced(text, f, spacing, color):
    w = int(sum(f.getlength(c) for c in text) + spacing * (len(text) - 1)) + 20
    im = Image.new("RGBA", (w, int(f.size * 1.6)), (0, 0, 0, 0))
    d, x = ImageDraw.Draw(im), 10
    for c in text:
        d.text((x, im.height // 2), c, font=f, fill=(*color, 255), anchor="lm", fontmode="1")
        x += f.getlength(c) + spacing
    return crop_alpha(im)


def shadowed(sp, off=8, alpha=170):
    out = Image.new("RGBA", (sp.width + off, sp.height + off), (0, 0, 0, 0))
    sh = Image.new("RGBA", sp.size, (0, 0, 0, alpha))
    out.paste(sh, (off, off), sp)
    out.alpha_composite(sp, (0, 0))
    return out


def var_A(im):
    """Камера наблюдения: уголки видоискателя, ● REC, дата, название пиксельным шрифтом из ролика."""
    d = ImageDraw.Draw(im)
    m, L, t = 70, 90, 8
    top, bot = 250, 1440
    for x0, y0, sx, sy in ((m, top, 1, 1), (W - m, top, -1, 1), (m, bot, 1, -1), (W - m, bot, -1, -1)):
        d.rectangle(sorted([x0, x0 + sx * L]) + [0, 0][:0] and [min(x0, x0 + sx * L), min(y0, y0 + sy * t), max(x0, x0 + sx * L), max(y0, y0 + sy * t)], fill=(*WHITE, 230))
        d.rectangle([min(x0, x0 + sx * t), min(y0, y0 + sy * L), max(x0, x0 + sx * t), max(y0, y0 + sy * L)], fill=(*WHITE, 230))
    rec = build.pixel_sprite("REC", 32, WHITE)
    d.ellipse([m + 30, top + 40, m + 62, top + 72], fill=(*RED, 255))
    im.alpha_composite(rec, (m + 76, top + 40))
    ts = build.pixel_sprite("06.2014", 32, WHITE)
    im.alpha_composite(ts, (W - m - 30 - ts.width, top + 40))
    a = build.pixel_sprite("НАБЛЮ", 80, WHITE)
    b = build.pixel_sprite("ДАТЕЛЬ", 80, RED)
    x0 = (W - a.width - b.width + 20) // 2          # половинки вплотную: контуры накладываются
    im.alpha_composite(a, (x0, 380))
    im.alpha_composite(b, (x0 + a.width - 20, 380))
    s = build.pixel_sprite("TRUE CRIME HISTORY", 32, (200, 200, 210))
    im.alpha_composite(s, ((W - s.width) // 2, 380 + a.height + 30))


def var_B(im):
    """Минимализм: высокие тонкие пиксельные буквы с разрядкой, без свечения."""
    t = spaced("НАБЛЮДАТЕЛЬ", handjet(200, 350), 22, WHITE)
    t = t.resize((min(t.width, W - 120), round(t.height * min(t.width, W - 120) / t.width)), Image.NEAREST)
    im.alpha_composite(shadowed(t), ((W - t.width) // 2, 330))
    s = spaced("TRUE CRIME HISTORY", handjet(40, 500), 12, (190, 190, 200))
    im.alpha_composite(s, ((W - s.width) // 2, 285))
    d = ImageDraw.Draw(im)
    y = 330 + t.height + 34
    d.rectangle([W // 2 - 60, y, W // 2 + 60, y + 6], fill=(*RED, 255))


def var_C(im):
    """Как заставка в ролике: Press Start 2P, «НАБЛЮ» белым, «ДАТЕЛЬ» красным, плашка канала."""
    a = build.pixel_sprite("НАБЛЮ", 96, WHITE)
    b = build.pixel_sprite("ДАТЕЛЬ", 96, RED)
    total = a.width + b.width - 24
    if total > W - 60:
        k = (W - 60) / total
        a = a.resize((round(a.width * k), round(a.height * k)), Image.NEAREST)
        b = b.resize((round(b.width * k), round(b.height * k)), Image.NEAREST)
        total = a.width + b.width - 24
    x0 = (W - total) // 2
    im.alpha_composite(shadowed(a, 10, 200), (x0, 300))
    im.alpha_composite(shadowed(b, 10, 200), (x0 + a.width - 24, 300))
    s = build.pixel_sprite("TRUE CRIME HISTORY", 32, (210, 210, 220))
    im.alpha_composite(s, ((W - s.width) // 2, 300 + a.height + 36))


def var_D(im):
    """Красное табло из точек (Handjet «круги») со свечением — как светящаяся вывеска в тумане."""
    f = handjet(220, 800, 12)
    face = text_mask("НАБЛЮДАТЕЛЬ", f, pad=80)
    glow = Image.fromarray((dilate(face, 6) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(22))
    g = np.asarray(glow, np.float32) / 255
    rgba = np.zeros(face.shape + (4,), np.float32)
    rgba[..., :3] = RED
    rgba[..., 3] = g * 200
    rgba[face] = (255, 70, 70, 255)
    t = crop_alpha(Image.fromarray(rgba.astype(np.uint8), "RGBA"))
    t = t.resize((W - 20, round(t.height * (W - 20) / t.width)), Image.NEAREST)
    im.alpha_composite(t, ((W - t.width) // 2, 300))
    s = spaced("TRUE CRIME HISTORY", handjet(40, 500), 12, (200, 200, 210))
    im.alpha_composite(s, ((W - s.width) // 2, 300 + t.height + 6))


if __name__ == "__main__":
    ims = []
    for name, fn in (("A", var_A), ("B", var_B), ("C", var_C), ("D", var_D)):
        im = background()
        fn(im)
        im = im.convert("RGB")
        im.save(os.path.join(HERE, "covers", f"v4_{name}.png"))
        ims.append(im)
    tiles = [grid_tile(im, 260) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 270 + 10, tiles[0].height + 60), (0, 0, 0))
    d = ImageDraw.Draw(prev)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    for i, tl in enumerate(tiles):
        prev.paste(tl, (10 + i * 270, 50))
        d.text((10 + i * 270 + 120, 10), "ABCD"[i], font=f, fill="white")
    prev.save(os.path.join(HERE, "covers", "v4_grid.png"))
    print("готово")
