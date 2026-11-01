#!/usr/bin/env python3
"""Проверка кадров на соответствие STYLE_LOCK.md (PIXEL APOCALYPSE).

python3 check_style.py frames_v2/*.png

Проверяет то, что можно проверить автоматически:
  1. формат 9:16, ровно 1080x1920;
  2. единый размер пикселя: кадр состоит из одноцветных блоков 6x6 (никакого сглаживания и размытия);
  3. все цвета взяты из зафиксированной палитры (никаких «лишних» оттенков и мягких градиентов);
  4. яркие сюжетные акценты (лампы, огонь, глаза) занимают малую долю кадра.
"""
import sys

import numpy as np
from PIL import Image

from pixel2 import PALETTE

PIXEL = 6
SIZE = (1080, 1920)
ACCENTS = {"O3", "O4", "R4", "R5", "E2"}   # яркие тона — только как сюжетный акцент
MAX_ACCENT = 0.04                          # не более 4% кадра

PAL = {tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)): n for n, h in PALETTE.items()}


def check(path):
    errs = []
    img = Image.open(path).convert("RGB")
    if img.size != SIZE:
        errs.append(f"размер {img.size}, нужен {SIZE}")
        return errs, {}
    a = np.asarray(img)
    blocks = a.reshape(SIZE[1] // PIXEL, PIXEL, SIZE[0] // PIXEL, PIXEL, 3)
    ref = blocks[:, :1, :, :1]
    bad = (blocks != ref).any(axis=(1, 3, 4)).sum()
    if bad:
        errs.append(f"{bad} блоков {PIXEL}x{PIXEL} не одноцветные (сглаживание/размытие)")
    art = ref[:, 0, :, 0].reshape(-1, 3)
    cols, counts = np.unique(art, axis=0, return_counts=True)
    names = {}
    for c, n in zip(map(tuple, cols), counts):
        if c not in PAL:
            errs.append(f"цвет #{c[0]:02x}{c[1]:02x}{c[2]:02x} не из палитры")
        else:
            names[PAL[c]] = n / len(art)
    acc = sum(v for k, v in names.items() if k in ACCENTS)
    if acc > MAX_ACCENT:
        errs.append(f"яркие акценты занимают {acc:.1%} кадра (> {MAX_ACCENT:.0%})")
    return errs, {"цветов": len(names), "акценты": f"{acc:.1%}"}


if __name__ == "__main__":
    ok = True
    for p in sys.argv[1:]:
        errs, info = check(p)
        status = "OK " if not errs else "FAIL"
        ok &= not errs
        print(f"[{status}] {p}  {info}")
        for e in errs:
            print("       -", e)
    sys.exit(0 if ok else 1)
