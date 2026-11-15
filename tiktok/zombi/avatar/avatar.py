#!/usr/bin/env python3
"""Аватарки аккаунта (1080×1080, в TikTok показываются кругом). python3 avatar.py → avatar_1..3.png + preview.png"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bunker"))
import scene  # noqa: E402

S = 1080


def bunker():
    """Ночь: зомби скребёт люк, внизу в погребе при фонарике сидит герой."""
    scene.zombie_list = lambda n, t: [(150, "walk", 0.3, 1), (330, "walk", 0.7, -1), (238, "crouch", 0.3, -1)]
    img, _ = scene.world(2, 1.0, 2.0, ("hero=250,364,sit,1",))
    return img.crop((142, 216, 322, 396)).resize((S, S), Image.NEAREST)


def portrait(kind, pose, bg_night=True):
    """Крупно голова и плечи персонажа на ночном фоне."""
    spr = scene.person(kind, pose, 0.3)
    cx0 = 9 if kind == "zombie" else 7
    head = spr.crop((cx0, 9, cx0 + 36, 45))                              # голова и плечи, 36×36
    k = 26
    big = head.resize((36 * k, 36 * k), Image.NEAREST)
    bgw = 36
    bg = Image.new("RGB", (bgw, bgw))
    d = ImageDraw.Draw(bg)
    for y in range(bgw):                                                 # ночное небо полосами
        t = y / bgw
        d.line([(0, y), (bgw, y)], fill=(int(10 + 22 * t), int(14 + 24 * t), int(34 + 36 * t)))
    d.ellipse([24, 4, 31, 11], fill=(232, 232, 210))                      # луна
    for i, (x, h) in enumerate(((2, 12), (8, 16), (30, 14), (34, 10))):  # ёлки
        d.polygon([(x, bgw - h), (x - 4, bgw), (x + 4, bgw)], fill=(16, 32, 34))
    for x, y in ((5, 6), (14, 3), (19, 9), (11, 13)):
        d.point((x, y), fill=(200, 200, 220))
    bg = bg.resize((S, S), Image.NEAREST).convert("RGBA")
    off = ((S - big.width) // 2, S - big.height + 26)
    bg.paste(big, off, big)
    if kind == "zombie":                                                  # свечение красного глаза
        glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        a = np.asarray(big)
        ys, xs = np.where((a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 3] > 0))
        if len(xs):
            cx, cy = off[0] + xs.mean(), off[1] + ys.mean()
            ImageDraw.Draw(glow).ellipse([cx - 130, cy - 130, cx + 130, cy + 130], fill=(255, 40, 30, 170))
            bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(50)))
            bg.paste(big, off, big)
    return bg.convert("RGB")


def circle_preview(ims, size=300):
    out = Image.new("RGB", (len(ims) * (size + 40) + 40, size + 90), (18, 18, 20))
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    small = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(small).ellipse([0, 0, 95, 95], fill=255)
    for i, im in enumerate(ims):
        out.paste(im.resize((size, size), Image.LANCZOS), (40 + i * (size + 40), 20), m)
        d = ImageDraw.Draw(out)
        d.text((40 + i * (size + 40) + size // 2 - 4, size + 40), str(i + 1), fill=(255, 220, 90))
    return out


if __name__ == "__main__":
    ims = [bunker(), portrait("zombie", "walk"), portrait("hero", "stand")]
    for i, im in enumerate(ims):
        im.save(os.path.join(HERE, f"avatar_{i + 1}.png"))
    circle_preview(ims).save(os.path.join(HERE, "preview.png"))
    print("готово")
