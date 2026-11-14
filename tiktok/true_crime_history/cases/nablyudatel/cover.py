"""Обложки «Наблюдатель» под TikTok (правила из «Птичьего короба»).

Сетка профиля показывает центр 3:4 — y 240…1680 из 1920, а нижние ~15% плитки закрывает строка
«просмотры · дата». Поэтому весь текст сверху: название y≈300, плашка «TRUE CRIME HISTORY» сразу под ним,
ниже y≈1420 ничего важного.
python3 cover.py → covers/cover_NN.png и covers/grid_preview.png (как в профиле, с плашкой просмотров)
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import build

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
GRID_TOP, GRID_BOT = 240, 1680
OVERLAY = 0.15


def fit(path, cx=0.5, cy=0.5, zoom=1.0):
    im = Image.open(path).convert("RGB")
    r = max(W / im.width, H / im.height) * zoom
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x = int(min(max(0, cx * im.width - W / 2), im.width - W))
    y = int(min(max(0, cy * im.height - H / 2), im.height - H))
    return im.crop((x, y, x + W, y + H))


def put(img, spr, x, y):
    img.alpha_composite(spr, (int(x) // 2 * 2, int(y) // 2 * 2))


def title(im, y):
    a = build.pixel_sprite("НАБЛЮ", 80, build.WHITE)
    b = build.pixel_sprite("ДАТЕЛЬ", 80, build.RED)
    gap = -10                     # контуры половинок накладываются — буквы стоят как в одном слове
    x0 = (W - a.width - gap - b.width) / 2
    put(im, a, x0, y)
    put(im, b, x0 + a.width + gap, y)
    return a.height


def badge(im, y):
    t = build.pixel_sprite("TRUE CRIME HISTORY", 48, build.WHITE)
    pad_x, pad_y = 30, 24
    bw, bh = t.width + 2 * pad_x, t.height + 2 * pad_y
    x0 = (W - bw) // 2 // 2 * 2
    d = ImageDraw.Draw(im)
    d.rectangle([x0 + 10, y + 10, x0 + bw + 10, y + bh + 10], fill=(0, 0, 0, 200))
    d.rectangle([x0 - 6, y - 6, x0 + bw + 6, y + bh + 6], fill=(0, 0, 0, 255))
    d.rectangle([x0, y, x0 + bw, y + bh], fill=(*build.PURPLE, 255))
    put(im, t, x0 + pad_x, y + pad_y)


def make(scene, cx=0.5, cy=0.5, zoom=1.0):
    im = fit(os.path.join(HERE, "frames", f"{scene:02d}.jpg"), cx, cy, zoom)
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    a *= 1 - 0.6 * np.clip((0.33 - yy) / 0.2, 0, 1)            # затемнить верх под надписи
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    h = title(im, 300)
    badge(im, 300 + h + 44)
    im = im.convert("RGB")
    im.save(os.path.join(HERE, "covers", f"cover_{scene:02d}.png"))
    return im


def grid_tile(im, w=300):
    tile = im.crop((0, GRID_TOP, W, GRID_BOT)).resize((w, w * 4 // 3), Image.LANCZOS)
    a = np.asarray(tile).astype(np.float32)
    h = tile.height
    yy = np.linspace(0, 1, h)[:, None, None]
    a *= 1 - 0.55 * np.clip((yy - (1 - OVERLAY)) / OVERLAY, 0, 1)
    tile = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(tile)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    d.text((8, h - 26), "▷ 521 · 14 нояб.", font=f, fill="white")
    d.text((w - 42, h - 26), "3:00", font=f, fill="white")
    return tile


if __name__ == "__main__":
    picks = [(1, 0.5, 0.62, 1.12), (46, 0.5, 0.5, 1.0), (13, 0.35, 0.58, 1.12)]
    ims = [make(*p) for p in picks]
    tiles = [grid_tile(im) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 310 + 10, tiles[0].height + 20), (0, 0, 0))
    for i, t in enumerate(tiles):
        prev.paste(t, (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", "grid_preview.png"))
    full = Image.new("RGB", (len(ims) * 370 + 10, 660), (0, 0, 0))
    for i, im in enumerate(ims):
        full.paste(im.resize((360, 640)), (10 + i * 370, 10))
    full.save(os.path.join(HERE, "covers", "covers_full.png"))
    print("готово")
