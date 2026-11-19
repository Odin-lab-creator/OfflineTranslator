#!/usr/bin/env python3
"""Обложка серии для TikTok. python3 cover.py 1 → covers/ep1_cover.png + covers/ep1_tile.png (как в профиле)

Правило сетки профиля: видна середина 3:4 (y 240…1680 из 1920), нижние ~15% плитки закрывает строка
«просмотры · дата». Поэтому всё важное — сверху: название y≈300…560, сцена в середине, ниже y≈1420 — ничего важного."""
import importlib
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import build
import scene

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
GRID_TOP, GRID_BOT, OVERLAY = 240, 1680, 0.15
# серия → (этап мира, ночь?, верх-лево кадра в мире x0, y0, время от удара, текст-крючок, зомби [(x, поза, фаза, взгляд)])
SHOTS = {1: (6, True, 52, 4, None, "", [(120, "walk", 0.25, 1), (172, "walk", 0.7, 1), (300, "walk", 0.6, -1),
                                          (372, "walk", 0.1, -1), (238, "crouch", 0.3, -1)], ()),
         2: (16, True, 270, 252, None, "", None,
             ("-bike", "night", "dooropen", "eyes", "hero=440,586,stand,1", "anya=500,588,give,1"), 4),
         3: (16, False, 120, 47, None, "", None,
             ("dooropen", "grate", "garden", "clay", "zdig", "dirtfall", "hero=296,462,up,1", "anya=326,462,stand,-1"), 3),
         4: (16, True, 130, 47, None, "", None,
             ("dooropen", "grate", "clay", "lamp", "-tunnel", "night", "radio", "ceilinghole", "dirtfall", "sacks",
              "hero=330,462,dig,-1", "anya=262,462,stand,1"), 3),
         5: (16, False, 270, 425, None, "", None,
             ("dooropen", "clay", "lamp", "-tunnel", "radio", "patched", "breach", "rope", "manyeyes",
              "hero=330,758,stand,1", "anya=298,758,stand,1", "father=400,758,give,-1"), 4)}


def make(ep):
    m = importlib.import_module(f"ep{ep}")
    build.EP = m
    stage, night, x0, y0, kage, hook, zombies, flags = SHOTS[ep][:8]
    k = SHOTS[ep][8] if len(SHOTS[ep]) > 8 else 3                       # крупность пикселя (3 — как в ролике)
    if night:
        scene.NIGHT.add(stage)
    if zombies:
        scene.zombie_list = lambda n, t: zombies
    drop = {f[1:] for f in flags if f.startswith("-")}
    off = tuple(f for f in tuple(m.OFF) + tuple(flags) if f not in drop and not f.startswith("-"))
    img, _ = scene.world(stage, 1.0, 3.3, off, kage)
    view = img.crop((x0, y0, x0 + W // k, y0 + H // k)).resize((W, H), Image.NEAREST)
    a = np.asarray(view).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    a *= 1 - 0.55 * np.clip((0.34 - yy) / 0.2, 0, 1)                    # притемнить верх под название
    xx = np.linspace(-1, 1, W)[None, :, None]
    a *= np.clip(1 - 0.35 * (xx ** 2 + ((yy - 0.45) * 2) ** 2) ** 1.5, 0.55, 1)
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    for (text, color, _, font), y in zip(m.TITLE, (300, 435, 560)):
        build.paste_c(im, build.logo(text, color, font), W / 2, y)
    if hook:                                                            # «тук-тук» у стены
        sx, sy = (432 - x0) * 3, (548 - y0) * 3
        build.paste_c(im, build.pix(hook, 4, build.YELLOW), sx - 140, sy - 150)
    im = im.convert("RGB")
    os.makedirs(os.path.join(HERE, "covers"), exist_ok=True)
    im.save(os.path.join(HERE, "covers", f"ep{ep}_cover.png"))
    return im


def tile(im, w=300, views="▷ 1 024 · 15 нояб.", dur="1:26"):
    t = im.crop((0, GRID_TOP, W, GRID_BOT)).resize((w, w * 4 // 3), Image.LANCZOS)
    a = np.asarray(t).astype(np.float32)
    h = t.height
    yy = np.linspace(0, 1, h)[:, None, None]
    a *= 1 - 0.55 * np.clip((yy - (1 - OVERLAY)) / OVERLAY, 0, 1)
    t = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(t)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    d.text((8, h - 26), views, font=f, fill="white")
    d.text((w - 42, h - 26), dur, font=f, fill="white")
    return t


if __name__ == "__main__":
    ep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    im = make(ep)
    mp4 = os.path.join(HERE, f"bunker_ep{ep}.mp4")
    dur = "1:26"
    if os.path.exists(mp4):
        import subprocess
        sec = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                                   capture_output=True, text=True).stdout or 86)
        dur = f"{int(sec // 60)}:{int(sec % 60):02d}"
    t = tile(im, dur=dur)
    prev = Image.new("RGB", (3 * 310 + 10, t.height + 20), (0, 0, 0))
    for i in range(3):                                                  # три плитки в ряд, как в профиле
        prev.paste(t if i == 0 else Image.new("RGB", t.size, (40, 40, 44)), (10 + i * 310, 10))
    prev.save(os.path.join(HERE, "covers", f"ep{ep}_tile.png"))
    print("готово")
