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
    """Камера наблюдения (утверждена): надписи рисует build.cover_overlay — те же, что в заставке ролика."""
    im.alpha_composite(build.cover_overlay())


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
