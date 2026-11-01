#!/usr/bin/env python3
"""Логотип канала story world: выживший в противогазе (аватарка v2_1) + пиксельная надпись STORY WORLD.

python3 logo.py  →  logo/*.png (прозрачный фон, пиксели без сглаживания) + logo/preview.png

Все размеры — в арт-пикселях исходника аватарки (72×72); при сохранении каждый арт-пиксель = SCALE×SCALE.
"""
import os
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "avatar", "gen", "gasmask_pixflux_s22.png")
OUT = os.path.join(HERE, "logo")
SCALE = 12

BLACK = (0, 0, 0)
INK = (27, 33, 39)
CREAM = (244, 209, 183)
PEACH = (231, 156, 127)
RUST = (212, 106, 77)
DEEP = (202, 88, 70)

# ------------------------------------------------------------------ персонаж
def cutout():
    """RGBA 72×72: персонаж без фона (заливка фона от краёв, контур замыкается расширением на 1 px)."""
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    dark = a.sum(-1) < 70
    bar = dark.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            bar |= np.roll(np.roll(dark, dy, 0), dx, 1)
    bg = np.zeros((H, W), bool)
    q = deque((y, x) for y in range(H) for x in range(W) if (y == 0 or x in (0, W - 1)) and not bar[y, x])
    for y, x in q:
        bg[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not bg[ny, nx] and not bar[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    bgcols = {tuple(c) for c in a[bg]}
    isbg = np.array([[tuple(a[y, x]) in bgcols for x in range(W)] for y in range(H)])
    for _ in range(2):                                   # вернуть фону кольцо у контура
        grow = np.zeros_like(bg)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            grow |= np.roll(np.roll(bg, dy, 0), dx, 1)
        bg |= grow & ~dark & isbg
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = a
    rgba[..., 3] = np.where(bg, 0, 255)
    return rgba, a.astype(np.uint8)


def disk(n, cx, cy, r):
    yy, xx = np.mgrid[0:n, 0:n]
    return (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r


def badge():
    """Круглый значок: фон аватарки в круге, кольцо, капюшон выходит за верх круга."""
    ch, full = cutout()
    pad = 6
    N = 72 + 2 * pad
    cx, cy, r = N / 2, N / 2 + 4, 31.5
    can = np.zeros((N, N, 4), np.uint8)
    inner = disk(N, cx, cy, r)
    ring = disk(N, cx, cy, r + 3) & ~inner
    edge_out = disk(N, cx, cy, r + 4) & ~disk(N, cx, cy, r + 3)
    edge_in = ring & ~disk(N, cx, cy, r + 1)
    can[edge_out] = (*BLACK, 255)
    can[ring] = (*RUST, 255)
    can[ring & ~disk(N, cx, cy, r + 2)] = (*DEEP, 255)
    can[edge_in & ~disk(N, cx, cy, r + 1)] = (*BLACK, 255)
    sub = np.zeros((N, N, 4), np.uint8)
    sub[pad:pad + 72, pad:pad + 72, :3] = full
    sub[pad:pad + 72, pad:pad + 72, 3] = 255
    can[inner] = sub[inner]
    chp = np.zeros((N, N, 4), np.uint8)
    chp[pad:pad + 72, pad:pad + 72] = ch
    keep = (chp[..., 3] > 0) & (inner | (np.arange(N)[:, None] < cy))
    can[keep] = chp[keep]
    return trim(can)


def character():
    ch, _ = cutout()
    return trim(ch)


# ------------------------------------------------------------------ надпись
GLYPHS = {                                                # жирный пиксельный шрифт: вертикали 2 px, горизонтали 1 px
    "S": [".#####.", "##...##", "##.....", ".#####.", ".....##", "##...##", ".#####."],
    "T": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
    "O": [".#####.", "##...##", "##...##", "##...##", "##...##", "##...##", ".#####."],
    "R": ["######.", "##...##", "##...##", "######.", "##.##..", "##..##.", "##...##"],
    "Y": ["##..##", "##..##", "##..##", ".####.", "..##..", "..##..", "..##.."],
    "W": ["##...##", "##...##", "##...##", "##.#.##", "#######", "###.###", "##...##"],
    "L": ["##....", "##....", "##....", "##....", "##....", "##....", "######"],
    "D": ["#####..", "##..##.", "##...##", "##...##", "##...##", "##..##.", "#####.."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
}
K = 2                                                     # пиксель шрифта = 2×2 арт-пикселя


def text_mask(s):
    cols = []
    for i, ch in enumerate(s):
        g = np.array([[c == "#" for c in row] for row in GLYPHS[ch]])
        cols.append(g)
        if i < len(s) - 1:
            cols.append(np.zeros((7, 1), bool))
    m = np.concatenate(cols, 1)
    return np.kron(m, np.ones((K, K), bool))


def dilate(m, n=1):
    o = m.copy()
    for _ in range(n):
        p = np.pad(o, 1)
        o = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:]
    return o


def wordmark(lines):
    """Надпись строками: заливка сверху вниз кремовый → персиковый → ржавый, чёрный контур, тень вниз."""
    ms = [text_mask(s) for s in lines]
    w = max(m.shape[1] for m in ms)
    gap = 4
    h = sum(m.shape[0] for m in ms) + gap * (len(ms) - 1)
    M = np.zeros((h, w), bool)
    rowcol = np.zeros((h, 3), np.uint8)
    y = 0
    for m in ms:
        x = (w - m.shape[1]) // 2
        M[y:y + m.shape[0], x:x + m.shape[1]] = m
        grad = [CREAM] * 3 + [PEACH] * 4 + [RUST] * 4 + [DEEP] * 3
        rowcol[y:y + m.shape[0]] = grad[: m.shape[0]]
        y += m.shape[0] + gap
    P = 3
    M = np.pad(M, P)
    rowcol = np.pad(rowcol, ((P, P), (0, 0)))
    outline = dilate(M) & ~M
    shadow = np.roll(dilate(M), 2, 0) & ~dilate(M)
    can = np.zeros((*M.shape, 4), np.uint8)
    can[shadow] = (*INK, 255)
    can[outline] = (*BLACK, 255)
    ys, xs = np.nonzero(M)
    can[ys, xs, :3] = rowcol[ys]
    can[ys, xs, 3] = 255
    return trim(can)


# ------------------------------------------------------------------ сборка
def trim(c):
    ys, xs = np.nonzero(c[..., 3])
    return c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def compose(parts, vertical, gap, align="center"):
    if vertical:
        W = max(p.shape[1] for p in parts)
        H = sum(p.shape[0] for p in parts) + gap * (len(parts) - 1)
    else:
        W = sum(p.shape[1] for p in parts) + gap * (len(parts) - 1)
        H = max(p.shape[0] for p in parts)
    can = np.zeros((H, W, 4), np.uint8)
    o = 0
    for p in parts:
        if vertical:
            x, y = (W - p.shape[1]) // 2, o
            o += p.shape[0] + gap
        else:
            x, y = o, (H - p.shape[0]) // 2
            o += p.shape[1] + gap
        sl = can[y:y + p.shape[0], x:x + p.shape[1]]
        m = p[..., 3] > 0
        sl[m] = p[m]
    return can


def save(c, name, margin=2):
    c = np.pad(c, ((margin, margin), (margin, margin), (0, 0)))
    im = Image.fromarray(c, "RGBA")
    im = im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)
    p = os.path.join(OUT, name)
    im.save(p)
    print(p, im.size)
    return im


def preview(ims):
    W = max(i.width for i in ims) + 80
    H = sum(i.height for i in ims) + 40 * (len(ims) + 1)
    S = Image.new("RGB", (W * 2, H))
    S.paste((18, 18, 20), (0, 0, W, H))
    S.paste((240, 240, 240), (W, 0, 2 * W, H))
    y = 40
    for i in ims:
        S.paste(i, (40, y), i)
        S.paste(i, (W + 40, y), i)
        y += i.height + 40
    S.thumbnail((2400, 2400))
    S.save(os.path.join(OUT, "preview.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    b = badge()
    one = wordmark(["STORY WORLD"])
    two = wordmark(["STORY", "WORLD"])
    ims = [
        save(compose([b, two], vertical=False, gap=6), "logo_horizontal.png"),
        save(compose([b, one], vertical=True, gap=5), "logo_vertical.png"),
        save(b, "logo_badge.png"),
        save(one, "logo_text.png"),
        save(character(), "logo_character.png"),
    ]
    preview(ims)
