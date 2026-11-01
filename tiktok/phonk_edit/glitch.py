"""Цифровой глитч поверх VHS: блоки (датамош), RGB-сдвиг, сортировка пикселей, постеризация, заикание.

Все функции работают с кадром float32 (VH×VW×3, 0…255) после «кассеты».
"""
import numpy as np


def rgb_split(x, amt):
    dx, dy = int(round(7 * amt)), int(round(2 * amt))
    y = x.copy()
    y[..., 0] = np.roll(np.roll(x[..., 0], dx, 1), dy, 0)
    y[..., 2] = np.roll(np.roll(x[..., 2], -dx, 1), -dy, 0)
    return y


def blocks(x, prev, amt, seed):
    """Квадраты съезжают, меняют каналы или застревают из прошлого кадра."""
    r = np.random.default_rng(seed)
    H, W = x.shape[:2]
    y = x.copy()
    for _ in range(int(6 + 34 * amt)):
        bw, bh = int(r.choice([16, 24, 32, 48])), int(r.choice([8, 16, 16, 24]))
        x0, y0 = int(r.integers(0, W - bw)), int(r.integers(0, H - bh))
        kind = r.random()
        if kind < 0.45:
            sx = int(np.clip(x0 + r.integers(-60, 61), 0, W - bw)); sy = int(np.clip(y0 + r.integers(-20, 21), 0, H - bh))
            y[y0:y0 + bh, x0:x0 + bw] = x[sy:sy + bh, sx:sx + bw]
        elif kind < 0.7 and prev is not None:
            y[y0:y0 + bh, x0:x0 + bw] = prev[y0:y0 + bh, x0:x0 + bw]
        elif kind < 0.88:
            y[y0:y0 + bh, x0:x0 + bw] = x[y0:y0 + bh, x0:x0 + bw][..., [2, 0, 1]]
        else:
            y[y0:y0 + bh, x0:x0 + bw] = (x[y0:y0 + bh, x0:x0 + bw] // 64) * 64 + 32
    return y


def pixel_sort(x, amt, seed, thresh=150):
    """Светлые участки строк вытягиваются в полосы (сортировка по яркости)."""
    r = np.random.default_rng(seed)
    H, W = x.shape[:2]
    y = x.copy()
    y0 = int(r.integers(0, H // 2)); y1 = min(H, y0 + int(H * (0.25 + 0.5 * amt)))
    lum = x.mean(-1)
    for row in range(y0, y1):
        m = np.nonzero(lum[row] > thresh)[0]
        if len(m) < 8:
            continue
        a, b = m[0], m[-1] + 1
        seg = y[row, a:b]
        order = np.argsort(seg.mean(-1))[::-1]
        y[row, a:b] = seg[order]
    return y


def posterize(x, levels=4):
    step = 256 / levels
    return np.floor(x / step) * step + step / 2


def plan(slot, lt, dur, beat, fps):
    """Какой глитч и какой силы в этот момент плана. Возвращает dict(kinds, amt, stutter)."""
    fx, k = slot["fx"], slot.get("drop_idx", -1)
    g = dict(kinds=(), amt=0.0, stutter=False)
    if slot.get("intro_beat") and lt < 2 / fps:                      # разгон: каждый удар — рассыпание
        return dict(kinds=("blocks", "rgb"), amt=0.8, stutter=False)
    if fx == "strong" and 0.24 <= lt < 0.24 + 3 / fps:               # после жёсткого VHS — цифровой «хвост»
        return dict(kinds=("rgb", "blocks"), amt=0.7, stutter=False)
    if fx == "double":
        return dict(kinds=("sort",) if lt < 0.25 else (), amt=0.8, stutter=lt < 3 / fps)
    if fx == "whip" and lt < 5 / fps:
        return dict(kinds=("blocks",), amt=1.0, stutter=False)
    if k >= 0 and k % 8 == 7 and lt > dur - 3 / fps:                 # конец фразы: сортировка + постеризация
        return dict(kinds=("sort", "poster"), amt=1.0, stutter=False)
    if fx == "" and k >= 0 and k % 2 == 1 and beat <= lt < beat + 2 / fps:   # слабая доля — короткий щелчок
        return dict(kinds=("blocks", "rgb"), amt=0.5, stutter=False)
    return g


def apply(x, prev, g, seed):
    if "blocks" in g["kinds"]:
        x = blocks(x, prev, g["amt"], seed)
    if "sort" in g["kinds"]:
        x = pixel_sort(x, g["amt"], seed)
    if "rgb" in g["kinds"]:
        x = rgb_split(x, g["amt"])
    if "poster" in g["kinds"]:
        x = posterize(x, 4)
    return np.clip(x, 0, 255)
