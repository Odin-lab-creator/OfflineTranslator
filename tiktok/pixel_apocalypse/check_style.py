#!/usr/bin/env python3
"""Проверка кадров на соответствие STYLE_LOCK.md (PIXEL APOCALYPSE).

python3 check_style.py КАДРЫ...            # текущий стиль: вариант А (PixelLab), пиксель 10×10
python3 check_style.py --legacy КАДРЫ...   # старые процедурные кадры: пиксель 6×6, палитра pixel2

Проверяет то, что можно проверить автоматически:
  1. формат 9:16, ровно 1080x1920;
  2. единый размер пикселя: кадр целиком из одноцветных блоков (без сглаживания и размытия);
  3. все цвета — из зафиксированной палитры;
  4. яркие насыщенные цвета (сюжетные акценты) занимают ≤ 4% кадра.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pixellab"))

import master_palette as mp  # noqa: E402

SIZE = (1080, 1920)
MAX_ACCENT = 0.04
MODE = {"pixel": 10, "legacy": False}


def _palette():
    if MODE["legacy"]:
        from pixel2 import PALETTE
        accents = {"O3", "O4", "R4", "R5", "E2"}
        return {tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)): (n in accents) for n, h in PALETTE.items()}
    return {tuple(int(v) for v in c): mp.is_accent(c) for c in mp.colors()}


def check(path, pixel=None):
    pixel = pixel or MODE["pixel"]
    errs = []
    img = Image.open(path).convert("RGB")
    if img.size != SIZE:
        return [f"размер {img.size}, нужен {SIZE}"], {}
    a = np.asarray(img)
    blocks = a.reshape(SIZE[1] // pixel, pixel, SIZE[0] // pixel, pixel, 3)
    ref = blocks[:, :1, :, :1]
    bad = (blocks != ref).any(axis=(1, 3, 4)).sum()
    if bad:
        errs.append(f"{bad} блоков {pixel}x{pixel} не одноцветные (сглаживание/размытие)")
    art = ref[:, 0, :, 0].reshape(-1, 3)
    pal = _palette()
    cols, counts = np.unique(art, axis=0, return_counts=True)
    acc, n_ok, off = 0.0, 0, []
    for c, n in zip(map(tuple, cols), counts):
        c = tuple(int(v) for v in c)
        if c not in pal:
            off.append(c)
        else:
            n_ok += 1
            acc += pal[c] * n / len(art)
    if off:
        errs.append(f"{len(off)} цветов не из палитры, например " + ", ".join("#%02x%02x%02x" % c for c in off[:3]))
    if acc > MAX_ACCENT:
        errs.append(f"яркие акценты занимают {acc:.1%} кадра (> {MAX_ACCENT:.0%})")
    return errs, {"цветов": n_ok, "акценты": f"{acc:.1%}"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--legacy", action="store_true", help="старый стиль: пиксель 6x6, палитра pixel2")
    a = ap.parse_args()
    if a.legacy:
        MODE.update(pixel=6, legacy=True)
        sys.path.insert(0, HERE)
    ok = True
    for p in a.files:
        errs, info = check(p)
        ok &= not errs
        print(f"[{'OK ' if not errs else 'FAIL'}] {p}  {info}")
        for e in errs:
            print("       -", e)
    sys.exit(0 if ok else 1)
