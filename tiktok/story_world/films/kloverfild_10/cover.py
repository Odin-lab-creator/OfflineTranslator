"""Обложки «Кловерфилд, 10» под TikTok (правило как у «Птичьего короба»).

Сетка профиля показывает центр 3:4 (y 240…1680), низ плитки (~15%) закрывает «просмотры · дата».
Поэтому всё сверху: название y≈300, плашка «СЮЖЕТ ЗА МИНУТУ» сразу под ним, ниже y=1420 — ничего важного.

python3 cover.py → covers/cover_NN.png и covers/grid_preview.png
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ya_legenda"))
sys.path.insert(0, os.path.join(HERE, "..", "ptichiy_korob"))
import build, cover2  # noqa: E402
from cover import grid_tile  # noqa: E402  (плитка профиля из «Птичьего короба»)

W, H = 1080, 1920


def frame(scene, cx, cy, zoom):
    im = Image.open(os.path.join(HERE, "frames", f"{scene:02d}.jpg")).convert("RGB")
    r = max(W / im.width, H / im.height) * zoom
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x = int(min(max(0, cx * im.width - W / 2), im.width - W))
    y = int(min(max(0, cy * im.height - H / 2), im.height - H))
    return im.crop((x, y, x + W, y + H))


def title(im, y, size=56):
    a = build.pixel_sprite("«КЛОВЕРФИЛД,", size, build.WHITE)
    b = build.pixel_sprite("10»", size, build.RED)
    gap = size * 0.6
    x = (W - a.width - gap - b.width) / 2
    cover2.put(im, a, x, y)
    cover2.put(im, b, x + a.width + gap, y)
    return max(a.height, b.height)


def make(scene, cx=0.5, cy=0.5, zoom=1.0, dark=0.6):
    im = frame(scene, cx, cy, zoom)
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    a *= 1 - dark * np.clip((0.33 - yy) / 0.2, 0, 1)            # затемнить верх под надписи
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    h = title(im, 300)
    cover2.badge(im, 300 + h + 40)
    im = im.convert("RGB")
    im.save(os.path.join(HERE, "covers", f"cover_{scene:02d}.png"))
    return im


if __name__ == "__main__":
    picks = [(24, 0.5, 0.5, 1.0), (26, 0.5, 0.5, 1.0), (9, 0.6, 0.35, 1.25)]
    ims = [make(*p) for p in picks]
    tiles = [grid_tile(im) for im in ims]
    prev = Image.new("RGB", (len(tiles) * 310 + 10, tiles[0].height + 20), (0, 0, 0))
    for i, t in enumerate(tiles):
        prev.paste(t, (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", "grid_preview.png"))
    print("готово")
