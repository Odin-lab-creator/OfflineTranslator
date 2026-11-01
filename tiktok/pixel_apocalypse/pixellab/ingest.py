#!/usr/bin/env python3
"""Приёмка ассетов из PixelLab → родные пиксели + палитра PIXEL APOCALYPSE.

python3 pixellab/ingest.py ФАЙЛЫ... [--frames N] [--name ИМЯ]

  * PNG / GIF / WebP; анимация — многокадровый GIF/WebP или горизонтальный лист кадров (--frames N);
  * сам определяет масштаб экспорта (x1…x12) и возвращает картинку к арт-пикселям;
  * переводит цвета в палитру STYLE_LOCK (без дизеринга — у PixelLab он уже свой);
  * фон (без прозрачности) → assets/<имя>.png, ждём 270x320 (камера ездит) или 180x320;
    спрайт (с прозрачностью) → assets/<имя>.png или assets/<имя>/000.png… , холст ≤ 128x128;
  * превью ×6 в assets/_preview/, фоны проверяются check_style.
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

from pixel2 import PAL, WTS  # noqa: E402
import check_style  # noqa: E402

ASSETS = os.environ.get("PIXELLAB_ASSETS", os.path.join(HERE, "assets"))
PREVIEW = os.path.join(ASSETS, "_preview")
BG_SIZES = {(270, 320), (180, 320)}
SPRITE_MAX = 128


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


def to_palette(a):
    """RGBA → (палитровый RGB, маска непрозрачности, доля сильно изменённых пикселей)."""
    rgb = a[..., :3].astype(np.float32)
    alpha = a[..., 3] >= 128
    flat = rgb.reshape(-1, 3)
    d = (((flat[:, None, :] - PAL[None]) ** 2) * WTS).sum(-1)
    idx = d.argmin(1)
    err = np.sqrt(d[np.arange(len(idx)), idx] / WTS.mean()).reshape(alpha.shape)
    q = PAL[idx].reshape(rgb.shape).astype(np.uint8)
    moved = float((err[alpha] > 18).mean()) if alpha.any() else 0.0
    return q, alpha, moved


def save_rgba(q, alpha, path):
    out = np.zeros(q.shape[:2] + (4,), np.uint8)
    out[..., :3] = q; out[..., 3] = alpha * 255
    Image.fromarray(out, "RGBA").save(path)


def ingest(path, frames=None, name=None):
    name = name or re.sub(r"[^a-z0-9_]+", "_", os.path.splitext(os.path.basename(path))[0].lower()).strip("_")
    fr = load_frames(path, frames)
    s = detect_scale(fr[0])
    fr = [f[s // 2::s, s // 2::s] for f in fr]
    h, w = fr[0].shape[:2]
    sprite = (fr[0][..., 3] < 128).any()
    report = [f"{os.path.basename(path)} → {name}: x{s} → {w}x{h}, {'спрайт' if sprite else 'фон'}, кадров {len(fr)}"]
    worst = 0.0
    outs = []
    for i, f in enumerate(fr):
        q, alpha, moved = to_palette(f)
        worst = max(worst, moved)
        if not sprite:
            alpha[:] = True
        outs.append((q, alpha))
    if worst > 0.25:
        report.append(f"  ! {worst:.0%} пикселей заметно ушли от палитры — включите Force colors с palette_1px.png")
    if sprite and max(w, h) > SPRITE_MAX:
        report.append(f"  ! холст спрайта {w}x{h} больше {SPRITE_MAX} — герой должен быть ~106 px на холсте 128x128")
    if not sprite and (w, h) not in BG_SIZES:
        report.append(f"  ! фон {w}x{h}: нужен 270x320 (или 180x320) — пиксели не совпадут с сеткой кадра")
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
    Image.fromarray(strip).resize((strip.shape[1] * 6, strip.shape[0] * 6), Image.NEAREST).save(pv)
    if not sprite:
        crop = outs[0][0][:320, :180]
        if crop.shape[:2] == (320, 180):
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
    a = ap.parse_args()
    os.makedirs(ASSETS, exist_ok=True)
    for p in a.files:
        for line in ingest(p, a.frames, a.name if len(a.files) == 1 else None):
            print(line)
