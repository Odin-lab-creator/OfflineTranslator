#!/usr/bin/env python3
"""Приёмка ассетов из PixelLab → родные пиксели + палитра PIXEL APOCALYPSE.

python3 pixellab/ingest.py ФАЙЛЫ... [--frames N] [--name ИМЯ] [--strict]

  * PNG / GIF / WebP; анимация — многокадровый GIF/WebP или горизонтальный лист кадров (--frames N);
  * сам определяет масштаб экспорта (x1…x12) и возвращает картинку к арт-пикселям;
  * цвета присоединяются к главной палитре (pixellab/palette_master.json): близкие «прилипают»
    к уже существующим, новые добавляются; --strict — только существующие цвета;
  * фон (без прозрачности) → assets/<имя>.png, ждём 162x192 (камера ездит) или 108x192;
    спрайт (с прозрачностью) → assets/<имя>.png или assets/<имя>/000.png…, персонаж 64x64
    (анимации PixelLab могут быть на холсте крупнее — до 128);
  * превью ×10 в assets/_preview/, фоны проверяются check_style.
"""
import argparse
import os
import re
import sys

import numpy as np
from PIL import Image, ImageSequence

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import check_style  # noqa: E402
import master_palette as mp  # noqa: E402

ASSETS = os.environ.get("PIXELLAB_ASSETS", os.path.join(HERE, "assets"))
PREVIEW = os.path.join(ASSETS, "_preview")
BG_SIZES = {(160, 192), (162, 192), (108, 192)}
SPRITE_MAX = 128
PX = 10


def load_frames(path, frames=None):
    im = Image.open(path)
    out = [np.asarray(f.convert("RGBA")).copy() for f in ImageSequence.Iterator(im)]
    if frames and len(out) == 1:
        sheet = out[0]
        w = sheet.shape[1] // frames
        out = [sheet[:, i * w:(i + 1) * w] for i in range(frames)]
    return out


def detect_scale(a, tol=10):
    """Наибольший s, при котором кадр состоит из одноцветных блоков s×s."""
    h, w = a.shape[:2]
    for s in range(12, 1, -1):
        if h % s or w % s:
            continue
        b = a.reshape(h // s, s, w // s, s, 4).astype(int)
        ref = b[:, :1, :, :1]
        uni = np.abs(b - ref).max(axis=(1, 3, 4)) <= tol
        busy = (b[..., 3] > 0).any(axis=(1, 3))      # учитываем только блоки, где что-то нарисовано
        ok = uni[busy].mean() if busy.any() else uni.mean()
        if ok >= 0.97:
            return s
    return 1


def remap(frames, name, strict=False):
    """Присоединить цвета ассета к главной палитре и перекрасить кадры по таблице замены."""
    px = np.concatenate([f[..., :3][f[..., 3] >= 128] for f in frames])
    cols, counts = np.unique(px, axis=0, return_counts=True)
    mapping, added, entries = mp.absorb(cols, counts, name, strict=strict)
    keys = np.array(list(mapping.keys()), np.int64)
    vals = np.array(list(mapping.values()), np.uint8)
    lut = {int(k[0]) << 16 | int(k[1]) << 8 | int(k[2]): i for i, k in enumerate(keys)}
    out = []
    for f in frames:
        alpha = f[..., 3] >= 128
        q = np.zeros(f.shape[:2] + (3,), np.uint8)
        code = (f[..., 0].astype(np.int64) << 16) | (f[..., 1].astype(np.int64) << 8) | f[..., 2]
        for y, x in zip(*np.nonzero(alpha)):
            q[y, x] = vals[lut[int(code[y, x])]]
        out.append((q, alpha))
    changed = sum(1 for k, v in mapping.items() if k != v)
    return out, added, changed, entries


def save_rgba(q, alpha, path):
    out = np.zeros(q.shape[:2] + (4,), np.uint8)
    out[..., :3] = q; out[..., 3] = alpha * 255
    Image.fromarray(out, "RGBA").save(path)


def ingest(path, frames=None, name=None, strict=False):
    name = name or re.sub(r"[^a-z0-9_]+", "_", os.path.splitext(os.path.basename(path))[0].lower()).strip("_")
    fr = load_frames(path, frames)
    s = detect_scale(fr[0])
    fr = [f[s // 2::s, s // 2::s] for f in fr]
    h, w = fr[0].shape[:2]
    sprite = (fr[0][..., 3] < 128).any()
    report = [f"{os.path.basename(path)} → {name}: x{s} → {w}x{h}, {'спрайт' if sprite else 'фон'}, кадров {len(fr)}"]
    if not sprite:
        for f in fr:
            f[..., 3] = 255
    outs, added, changed, entries = remap(fr, name, strict)
    report.append(f"  палитра: +{added} новых цветов, {changed} прилипли к существующим → всего {len(entries)}")
    if len(entries) > mp.CAP:
        report.append(f"  ! в главной палитре {len(entries)} цветов (> {mp.CAP}) — ассет слишком «пёстрый», нужен --strict или перегенерация")
    if sprite and max(w, h) > SPRITE_MAX:
        report.append(f"  ! холст спрайта {w}x{h} больше {SPRITE_MAX}")
    if not sprite and (w, h) not in BG_SIZES:
        report.append(f"  ! фон {w}x{h}: нужен 162x192 (или 108x192) — пиксели не совпадут с сеткой кадра")
    os.makedirs(PREVIEW, exist_ok=True)
    if len(outs) == 1:
        save_rgba(*outs[0], os.path.join(ASSETS, name + ".png"))
    else:
        d = os.path.join(ASSETS, name); os.makedirs(d, exist_ok=True)
        for i, (q, a) in enumerate(outs):
            save_rgba(q, a, os.path.join(d, f"{i:03d}.png"))
    # превью ×6
    bg = np.array([14, 23, 18], np.uint8)
    tiles = []
    for q, a in outs[:8]:
        t = np.where(a[..., None], q, bg)
        tiles.append(t)
    strip = np.concatenate(tiles, axis=1)
    pv = os.path.join(PREVIEW, name + ".png")
    Image.fromarray(strip).resize((strip.shape[1] * PX, strip.shape[0] * PX), Image.NEAREST).save(pv)
    mp.save(entries)
    if not sprite:
        crop = outs[0][0][:192, :108]
        if crop.shape[:2] == (192, 108):
            tmp = os.path.join(PREVIEW, name + "_check.png")
            Image.fromarray(crop).resize((1080, 1920), Image.NEAREST).save(tmp)
            errs, info = check_style.check(tmp)
            report.append(f"  стиль: {'OK' if not errs else 'FAIL'} {info}" + "".join(f"\n    - {e}" for e in errs[:3]))
            os.remove(tmp)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--frames", type=int, help="лист кадров: число кадров по горизонтали")
    ap.add_argument("--name", help="имя ассета (по умолчанию — имя файла)")
    ap.add_argument("--strict", action="store_true", help="не добавлять новых цветов в палитру")
    a = ap.parse_args()
    os.makedirs(ASSETS, exist_ok=True)
    for p in a.files:
        for line in ingest(p, a.frames, a.name if len(a.files) == 1 else None, a.strict):
            print(line)
