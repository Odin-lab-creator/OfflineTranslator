"""Обложка «Наблюдатель» v2 — «афиша»: объёмное название шрифтом Handjet (пиксельный, узкий, вся кириллица;
у Pixelify Sans нет русских «О» и «П» — не брать),
лента «TRUE CRIME HISTORY» как полицейская, цитата из письма на полоске бумаги, красный круг вокруг Наблюдателя.
Правила сетки TikTok те же (cover.py): всё важное в y 240…1420.
python3 cover2.py → covers/v2_NN.png + covers/v2_grid.png
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cover import fit, grid_tile, W, H

HERE = os.path.dirname(os.path.abspath(__file__))
HANDJET = os.path.join(HERE, "fonts", "Handjet.ttf")
RED, DARKRED, YELLOW, PAPER = (226, 38, 44), (96, 8, 14), (255, 210, 58), (236, 230, 214)


def handjet(size, weight=900, shape=2):
    f = ImageFont.truetype(HANDJET, size)
    f.set_variation_by_axes([weight, 1, shape])
    return f


def text_mask(text, f, pad=40):
    x0, y0, x1, y1 = f.getbbox(text)
    m = Image.new("L", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), 0)
    ImageDraw.Draw(m).text((pad - x0, pad - y0), text, font=f, fill=255, fontmode="1")
    return np.asarray(m) > 0


def dilate(a, r):
    out = a.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(a, dy, 0), dx, 1)
    return out


def block_title(text, size, depth=14, step=2):
    """Объёмные буквы: лицо полосами (белый → розовый → красный), тёмно-красная «глубина» вниз, чёрный контур."""
    face = text_mask(text, handjet(size), pad=40 + depth * step)
    ext = np.zeros_like(face)
    for i in range(1, depth + 1):
        ext |= np.roll(face, i * step, 0)
    body = face | ext
    outline = dilate(body, 6)
    h = face.shape[0]
    ys = np.where(face.any(1))[0]
    top, bot = ys.min(), ys.max()
    band = np.clip((np.arange(h) - top) / max(1, bot - top), 0, 1)
    cols = np.array([(255, 255, 255), (255, 214, 214), (255, 120, 120), RED], np.float32)
    idx = np.minimum((band * 4).astype(int), 3)              # 4 ровные полосы — без плавного градиента
    rgba = np.zeros(face.shape + (4,), np.uint8)
    rgba[outline] = (0, 0, 0, 255)
    rgba[ext & ~face] = (*DARKRED, 255)
    rows = cols[idx][:, None, :].repeat(face.shape[1], 1)
    rgba[face, :3] = rows[face].astype(np.uint8)
    rgba[face, 3] = 255
    ys, xs = np.where(rgba[..., 3] > 0)
    return Image.fromarray(rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")


def tape(text, width, angle):
    """Полицейская лента: жёлтая полоса, чёрные края, повторяющийся текст пиксельным шрифтом."""
    f = handjet(64, 800)
    unit = f"{text}   ●   "
    band = Image.new("RGBA", (width + 400, 92), (*YELLOW, 255))
    d = ImageDraw.Draw(band)
    d.rectangle([0, 0, band.width, 7], fill=(0, 0, 0, 255))
    d.rectangle([0, band.height - 8, band.width, band.height], fill=(0, 0, 0, 255))
    x = -60
    while x < band.width:
        d.text((x, 46), unit, font=f, fill=(0, 0, 0, 255), anchor="lm", fontmode="1")
        x += int(f.getlength(unit))
    return band.rotate(angle, resample=Image.NEAREST, expand=True)


def note(text, angle):
    """Полоска бумаги с цитатой из письма."""
    f = handjet(84, 700)
    tw = int(f.getlength(text))
    im = Image.new("RGBA", (tw + 70, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([8, 8, im.width, im.height], fill=(0, 0, 0, 140))                 # тень
    d.rectangle([0, 0, im.width - 8, im.height - 8], fill=(*PAPER, 255))
    d.text((31, 46), text, font=f, fill=(30, 26, 26, 255), anchor="lm", fontmode="1")
    return im.rotate(angle, resample=Image.NEAREST, expand=True)


def ring(im, cx, cy, rx, ry, k=4):
    """Красный «маркерный» круг, нарисованный крупными пикселями."""
    s = Image.new("RGBA", (W // k, H // k), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    for off, col in ((1, (0, 0, 0, 200)), (0, (*RED, 255))):
        d.ellipse([(cx - rx) / k + off, (cy - ry) / k + off, (cx + rx) / k + off, (cy + ry) / k + off],
                  outline=col, width=3)
    im.alpha_composite(s.resize((W, H), Image.NEAREST))


def make(scene, cx, cy, zoom, circle=None, name=None):
    im = fit(os.path.join(HERE, "frames", f"{scene:02d}.jpg"), cx, cy, zoom)
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(-1, 1, W)[None, :, None]
    a *= 1 - 0.65 * np.clip((0.45 - yy) / 0.3, 0, 1)                 # тёмный верх под надписи
    a *= 1 - 0.35 * np.clip(np.hypot(xx, (yy - 0.5) * 2) - 0.8, 0, 1)  # виньетка
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    if circle:
        ring(im, *circle)
    t = tape("TRUE CRIME HISTORY", W, 3)
    im.alpha_composite(t, ((W - t.width) // 2, 300 - t.height // 2))
    title = block_title("НАБЛЮДАТЕЛЬ", 250)
    if title.width > W - 60:
        title = title.resize((W - 60, round(title.height * (W - 60) / title.width)), Image.NEAREST)
    im.alpha_composite(title, ((W - title.width) // 2, 380))
    n = note("«ТЕПЕРЬ МОЯ ОЧЕРЕДЬ»", -2)
    im.alpha_composite(n, ((W - n.width) // 2, 380 + title.height + 30))
    im = im.convert("RGB")
    im.save(os.path.join(HERE, "covers", f"v2_{name or scene:02}.png" if isinstance(name or scene, int) else f"v2_{name}.png"))
    return im


if __name__ == "__main__":
    ims = [make(13, 0.35, 0.62, 1.12, circle=(252, 1045, 128, 195), name=13),
           make(1, 0.5, 0.55, 1.0, name=1),
           make(46, 0.5, 0.5, 1.0, name=46)]
    tiles = [grid_tile(im) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 310 + 10, tiles[0].height + 20), (0, 0, 0))
    for i, t in enumerate(tiles):
        prev.paste(t, (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", "v2_grid.png"))
    full = Image.new("RGB", (len(ims) * 370 + 10, 660), (0, 0, 0))
    for i, im in enumerate(ims):
        full.paste(im.resize((360, 640)), (10 + i * 370, 10))
    full.save(os.path.join(HERE, "covers", "v2_full.png"))
    print("готово")
