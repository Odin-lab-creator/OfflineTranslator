"""Главная палитра PIXEL APOCALYPSE (вариант А, PixelLab).

Палитра не придумывается заранее, а собирается из одобренных ассетов PixelLab:
каждый новый цвет либо «прилипает» к уже существующему (если ближе TOL), либо добавляется.
Так все ассеты делят один набор цветов, а палитра остаётся ограниченной (CAP).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "palette_master.json")
TOL = 8.0     # цвета ближе этого считаются одним
CAP = 96      # предел размера палитры
WTS = np.array([0.35, 0.45, 0.2], np.float32)


def dist(a, b):
    """Взвешенное расстояние между наборами RGB: a (N,3) × b (M,3) → (N,M)."""
    d = ((a[:, None, :].astype(np.float32) - b[None].astype(np.float32)) ** 2 * WTS).sum(-1)
    return np.sqrt(d / WTS.mean())


def load():
    if not os.path.exists(PATH):
        return []
    with open(PATH, encoding="utf8") as f:
        return json.load(f)


def colors(entries=None):
    entries = load() if entries is None else entries
    return np.array([[int(e["hex"][i:i + 2], 16) for i in (0, 2, 4)] for e in entries], np.uint8).reshape(-1, 3)


def save(entries):
    with open(PATH, "w", encoding="utf8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)


def absorb(cols, counts, source, strict=False):
    """Присоединить цвета ассета к палитре. Возвращает (таблица замены {rgb: rgb}, добавлено, записи)."""
    entries = load()
    pal = colors(entries)
    order = np.argsort(-counts)
    mapping, added = {}, 0
    for i in order:
        c = cols[i]
        if len(pal):
            d = dist(c[None], pal)[0]
            j = int(d.argmin())
            if d[j] <= TOL or strict:
                mapping[tuple(int(v) for v in c)] = tuple(int(v) for v in pal[j])
                continue
        entries.append({"hex": "%02x%02x%02x" % tuple(int(v) for v in c), "src": source})
        pal = np.vstack([pal, c[None]]) if len(pal) else c[None].astype(np.uint8)
        mapping[tuple(int(v) for v in c)] = tuple(int(v) for v in c)
        added += 1
    return mapping, added, entries


def is_accent(rgb):
    """Яркий насыщенный цвет — допустим только как сюжетный акцент."""
    r, g, b = [v / 255 for v in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    s = 0 if mx == 0 else (mx - mn) / mx
    return mx > 0.78 and s > 0.5
