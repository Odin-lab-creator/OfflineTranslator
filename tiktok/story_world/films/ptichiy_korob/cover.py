"""Обложки «Птичий короб» под TikTok.

Правило (по сетке профиля): TikTok показывает в сетке центр 3:4 — y 240…1680 из 1920,
а нижние ~15% плитки (y > ~1460) закрывает строка «просмотры · дата · длительность».
Поэтому ВСЕ надписи — сверху: название y≈300, плашка «СЮЖЕТ ЗА МИНУТУ» сразу под ним.
Ниже y=1420 — ничего важного.

python3 cover.py → covers/cover_NN.png и covers/grid_preview.png (как в профиле, с плашкой просмотров)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ya_legenda"))
import build, cover2  # noqa: E402

W, H = 1080, 1920
GRID_TOP, GRID_BOT = 240, 1680      # что видно в сетке профиля
OVERLAY = 0.15                      # доля плитки снизу под просмотрами и датой
TITLE = "«ПТИЧИЙ КОРОБ»"


def fit(path, cx=0.5, cy=0.5):
    im = Image.open(path).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x = int(min(max(0, cx * im.width - W / 2), im.width - W))
    y = int(min(max(0, cy * im.height - H / 2), im.height - H))
    return im.crop((x, y, x + W, y + H))


def make(scene, cx=0.5, cy=0.5):
    im = Image.open(os.path.join(HERE, "frames", f"{scene:02d}.jpg"))
    im = fit(os.path.join(HERE, "frames", f"{scene:02d}.jpg"), cx, cy)
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    a *= 1 - 0.6 * np.clip((0.33 - yy) / 0.2, 0, 1)            # затемнить верх под надписи
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    t = build.pixel_sprite(TITLE, 64, build.WHITE)
    cover2.put(im, t, (W - t.width) / 2, 300)
    cover2.badge(im, 300 + t.height + 40)
    out = os.path.join(HERE, "covers", f"cover_{scene:02d}.png")
    im.convert("RGB").save(out)
    return im.convert("RGB")


def grid_tile(im, w=300):
    """Плитка как в профиле: центр 3:4 и плашка просмотров снизу."""
    tile = im.crop((0, GRID_TOP, W, GRID_BOT)).resize((w, w * 4 // 3), Image.LANCZOS)
    a = np.asarray(tile).astype(np.float32)
    h = tile.height
    yy = np.linspace(0, 1, h)[:, None, None]
    a *= 1 - 0.55 * np.clip((yy - (1 - OVERLAY)) / OVERLAY, 0, 1)
    tile = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(tile)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    d.text((8, h - 26), "▷ 521 · 9 нояб.", font=f, fill="white")
    d.text((w - 42, h - 26), "1:36", font=f, fill="white")
    return tile


if __name__ == "__main__":
    picks = [(22, 0.5, 0.45), (25, 0.5, 0.5), (1, 0.5, 0.5)]
    ims = [make(*p) for p in picks]
    tiles = [grid_tile(im) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 310 + 10, tiles[0].height + 20), (0, 0, 0))
    for i, t in enumerate(tiles):
        prev.paste(t, (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", "grid_preview.png"))
    print("готово")
