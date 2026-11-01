#!/usr/bin/env python3
"""Файлы для загрузки в PixelLab: палитра и образцы стиля/персонажей в РОДНОМ разрешении (без увеличения).

cd tiktok/pixel_apocalypse && python3 pixellab/make_refs.py  →  pixellab/refs/
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from characters import hero_stand, zombie  # noqa: E402
from pixel2 import CH, CW, PALETTE, finalize  # noqa: E402
import test_frames2 as f2  # noqa: E402
import test_frames3 as f3  # noqa: E402

OUT = os.path.join(HERE, "refs")
os.makedirs(OUT, exist_ok=True)


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


def palettes():
    names = list(PALETTE)
    # 1 пиксель = 1 цвет: Aseprite → Palette → Load, PixelLab → color image / Force colors
    Image.fromarray(np.array([[rgb(PALETTE[n]) for n in names]], np.uint8)).save(os.path.join(OUT, "palette_1px.png"))
    # крупные плашки — посмотреть глазами
    sw = Image.new("RGB", (8 * 16, ((len(names) + 7) // 8) * 16))
    for i, n in enumerate(names):
        sw.paste(rgb(PALETTE[n]), ((i % 8) * 16, (i // 8) * 16, (i % 8) * 16 + 16, (i // 8) * 16 + 16))
    sw.save(os.path.join(OUT, "palette_swatches.png"))
    with open(os.path.join(OUT, "palette.gpl"), "w") as f:
        f.write("GIMP Palette\nName: PIXEL APOCALYPSE\nColumns: 8\n#\n")
        for n in names:
            r, g, b = rgb(PALETTE[n]); f.write(f"{r:3d} {g:3d} {b:3d}\t{n}\n")
    with open(os.path.join(OUT, "palette.hex"), "w") as f:
        f.write("\n".join(PALETTE[n] for n in names) + "\n")


def sprite_png(spr, size, path):
    """Спрайт по центру холста size x size, ступни на нижней строке; фон прозрачный."""
    rgb_, a, _ = spr
    h, w = a.shape
    can = np.zeros((size, size, 4), np.uint8)
    x0, y0 = (size - w) // 2, size - h
    can[y0:, x0:x0 + w, :3][a] = rgb_[a].astype(np.uint8)
    can[y0:, x0:x0 + w, 3][a] = 255
    Image.fromarray(can, "RGBA").save(path)


def scene_crop(scene, cam, path, size=(CW, CH)):
    lit = scene.lit()
    x, y = cam
    art = finalize(lit[y:y + size[1], x:x + size[0]], vignette=0.0)
    Image.fromarray(art).save(path)


if __name__ == "__main__":
    palettes()
    sprite_png(hero_stand(), 128, os.path.join(OUT, "hero_ref_128.png"))
    sprite_png(hero_stand(pipe=True), 128, os.path.join(OUT, "hero_pipe_ref_128.png"))
    sprite_png(zombie(), 128, os.path.join(OUT, "zombie_ref_128.png"))
    # образцы стиля: полный кадр 180x320 и вырезка 200x200 (лимит инструментов со style image)
    door, street = f2.frame_door(), f3.frame_surface()
    scene_crop(door, (12, 100), os.path.join(OUT, "style_bunker_180x320.png"))
    scene_crop(street, (45, 110), os.path.join(OUT, "style_street_180x320.png"))
    scene_crop(door, (20, 200), os.path.join(OUT, "style_bunker_200.png"), (200, 200))
    scene_crop(street, (35, 220), os.path.join(OUT, "style_street_200.png"), (200, 200))
    for f in sorted(os.listdir(OUT)):
        print(" ", f)
