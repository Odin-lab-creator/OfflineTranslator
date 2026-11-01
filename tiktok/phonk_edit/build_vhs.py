#!/usr/bin/env python3
"""Фонк-эдит «Jxned J — Check Yourself», винтажная версия: VHS / старая видеокамера.

cd tiktok/phonk_edit && python3 build_vhs.py [preview]

Склейки и раскладка планов — из build_edit.py (сетка 140 BPM). Кадр 4:3 по центру вертикали на чёрном.
Картинка проходит «кассету»: ореолы, растекание цвета, двойные контуры, шум, строки-помехи, дрожь строк,
полоса трекинга, чересстрочность, «рыбий глаз» на части планов. В центре — полупрозрачная готическая «Jxned».
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv = sys.argv[:]
sys.argv = sys.argv[:1]
import build_edit as be  # noqa: E402
sys.argv = _argv
be.SLOTS[0]["src"] = 116.5
import glitch as dg  # noqa: E402  цифровой глитч поверх VHS
for _j, _s in enumerate(be.SLOTS[1:5]):
    _s["intro_beat"] = True
    _s["intro_idx"] = _j
_gprev = None
for _k, _s in enumerate(be.SLOTS[5:]):
    _s["drop_idx"] = _k        # город сверху без текста исходника («PRESENTS» в начале ролика)

PREVIEW = len(sys.argv) > 1 and sys.argv[1] == "preview"
OUT = os.path.join(HERE, "phonk_check_yourself_vhs3.mp4")
VW, VH = 480, 360                 # разрешение «кассеты»
FPS = be.FPS
GOTHIC = os.path.join(HERE, "fonts", "PirataOne-Regular.ttf")
XX = np.arange(VW)[None, :]
RNG = np.random.default_rng(11)


# ---------------------------------------------------------------- геометрия
def crop43(src, zoom=1.0):
    h = be.SH / zoom
    w = h * 4 / 3
    cx, cy = be.SW / 2, be.SH / 2
    im = Image.fromarray(src).crop((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    return np.asarray(im.resize((VW, VH), Image.BILINEAR), np.float32)


_fish = None


def fisheye(img, k=0.28):
    global _fish
    if _fish is None:
        yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
        nx, ny = (xx - VW / 2) / (VW / 2), (yy - VH / 2) / (VH / 2)
        r2 = nx * nx + ny * ny
        f = 1 / (1 + k * r2) * (1 + k * 0.55)
        sx = np.clip((nx * f * VW / 2 + VW / 2), 0, VW - 1).astype(int)
        sy = np.clip((ny * f * VH / 2 + VH / 2), 0, VH - 1).astype(int)
        _fish = (sy, sx, np.clip(1.25 - 0.55 * r2, 0.15, 1)[..., None])
    sy, sx, v = _fish
    return img[sy, sx] * v


# ---------------------------------------------------------------- надпись
_logo = None


def logo():
    """«Jxned» готическим шрифтом, белым; альфа применяется при наложении."""
    global _logo
    if _logo is None:
        L = Image.new("L", (VW, VH), 0)
        d = ImageDraw.Draw(L)
        f = ImageFont.truetype(GOTHIC, 118)
        w = d.textlength("Jxned", font=f)
        d.text(((VW - w) / 2, VH / 2 - 78), "Jxned", font=f, fill=255)
        _logo = np.asarray(L.filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None] / 255
    return _logo


# ---------------------------------------------------------------- кассета
def hblur(x, n):
    k = np.ones(n) / n
    pad = np.pad(x, ((0, 0), (n // 2, n // 2), (0, 0)) if x.ndim == 3 else ((0, 0), (n // 2, n // 2)), mode="edge")
    c = np.cumsum(pad, axis=1)
    c = np.concatenate([np.zeros_like(c[:, :1]), c], axis=1)
    return (c[:, n:] - c[:, :-n]) / n


_prev = None


def vhs(img, t, i, glitch=0.0):
    global _prev
    x = img.copy()
    # ореолы вокруг светлого
    br = np.clip(x - 185, 0, None)
    bl = Image.fromarray(np.clip(br * 3, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
    x += np.asarray(bl, np.float32) * 0.55
    # YIQ
    R, G, B = x[..., 0], x[..., 1], x[..., 2]
    Y = 0.299 * R + 0.587 * G + 0.114 * B
    I = 0.596 * R - 0.274 * G - 0.322 * B
    Q = 0.211 * R - 0.523 * G + 0.312 * B
    # яркость: мягкость + «двойные контуры» старой камеры
    Ys = hblur(Y, 3)
    Y = Ys + 0.7 * (Ys - hblur(Ys, 9))
    # цвет: размыт по горизонтали и сдвинут вправо
    sh = 4 + int(10 * glitch)
    I = np.roll(hblur(I, 11), sh, axis=1) * 1.1
    Q = np.roll(hblur(Q, 11), sh, axis=1) * 1.1
    # шум
    r = np.random.default_rng(i)
    Y += r.normal(0, 5.5, Y.shape)
    cn = np.asarray(Image.fromarray(r.normal(128, 40, (VH // 8, VW // 16)).clip(0, 255).astype(np.uint8))
                    .resize((VW, VH), Image.BILINEAR), np.float32) - 128
    I += cn * 0.12
    # обратно в RGB, «плёночный» цвет: приподнятый чёрный, холодный оттенок
    R = Y + 0.956 * I + 0.621 * Q
    G = Y - 0.272 * I - 0.647 * Q
    B = Y - 1.106 * I + 1.703 * Q
    x = np.stack([R * 0.97, G * 1.0, B * 1.07], -1)
    x = 14 + x * 0.9
    # дрожь строк
    shift = np.round(1.3 * np.sin(np.arange(VH) * 0.045 + t * 6.0) + r.normal(0, 0.5, VH)).astype(int)
    if glitch > 0:
        y0 = int(r.integers(0, VH - 60)); hgt = int(20 + 40 * glitch)
        shift[y0:y0 + hgt] += int(r.integers(12, 30)) * (1 if r.random() < 0.5 else -1)
    shift[-7:] += r.integers(6, 16, 7)                      # шум переключения головок внизу
    idx = (XX - shift[:, None]) % VW
    x = x[np.arange(VH)[:, None], idx]
    x[-7:] += r.normal(0, 25, (7, VW, 1))
    # строки-помехи
    for _ in range(int(r.integers(0, 4)) + int(6 * glitch)):
        y = int(r.integers(0, VH)); x0 = int(r.integers(0, VW // 2)); x1 = x0 + int(r.integers(VW // 4, VW))
        x[y, x0:x1] += np.array([45, 12, 30]) * r.uniform(0.4, 1.0)
    # чересстрочность: нечётные строки — наполовину из прошлого кадра
    if _prev is not None:
        x[1::2] = x[1::2] * 0.55 + _prev[1::2] * 0.45
    _prev = x.copy()
    return np.clip(x, 0, 255)


# ---------------------------------------------------------------- жёсткий VHS (акценты)
def heavy(x, h, te, i):
    """Сильный сбой кассеты поверх обработанного кадра; h — сила 0…1."""
    if h <= 0.01:
        return x
    r = np.random.default_rng(5000 + i)
    amp = 7 * h
    sh = np.round(amp * np.sin(np.arange(VH) * 0.09 + te * 23) + r.normal(0, 1.5 * h, VH)).astype(int)
    for _ in range(int(1 + 3 * h)):                         # полосы трекинга
        y0 = int(r.integers(0, VH - 30)); hh = int(r.integers(8, 34))
        sh[y0:y0 + hh] += int(r.integers(15, 45) * h) * (1 if r.random() < 0.5 else -1)
    idx = (XX - sh[:, None]) % VW
    x = x[np.arange(VH)[:, None], idx]
    off = int(round(8 * h))                                 # разъезд цветов
    x[..., 0] = np.roll(x[..., 0], off, axis=1)
    x[..., 2] = np.roll(x[..., 2], -off, axis=1)
    x = x * (1 - 0.12 * h) + r.normal(0, 18 * h, (VH, VW, 1))
    if h > 0.6 and r.random() < 0.35:                       # на миг «выпадает» строка картинки
        y0 = int(r.integers(0, VH - 12)); x[y0:y0 + int(r.integers(3, 12))] = r.uniform(120, 230)
    return np.clip(x, 0, 255)


def heavy_level(slot, k, lt, dur):
    fx = slot["fx"]
    if "drop_idx" not in slot:                                         # вступление: чисто, затем нарастающий сбой
        return 0.3 + 0.2 * slot["intro_idx"] if slot.get("intro_beat") else 0.0
    if fx == "drop":
        return 1.0 if lt < 0.25 else max(0.0, 1 - (lt - 0.25) / 0.25)
    if fx == "strong":
        return 1.0 if lt < 0.12 else max(0.0, 1 - (lt - 0.12) / 0.2)
    if fx in ("whip", "double"):
        return max(0.0, 0.55 - lt / 0.25)
    if slot.get("drop_idx", -1) % 8 == 7 and lt > dur - be.BEAT:      # срыв перед новой фразой (каждые 4 такта)
        return 0.85
    return 0.0


# ---------------------------------------------------------------- кадры
FISH = {"strong", "mirror"}


def render_slot(slot, prev_frames=None):
    dur = slot["t1"] - slot["t0"]
    fx = slot["fx"]
    frames = be.decode(slot["src"], dur) if fx != "double" or prev_frames is None else prev_frames
    out = []
    n0, n1 = int(round(slot["t0"] * FPS)), int(round(slot["t1"] * FPS))
    for i in range(n0, n1):
        te = i / FPS
        lt = te - slot["t0"]
        g = dg.plan(slot, lt, dur, be.BEAT, FPS)
        src = frames[0 if g["stutter"] else min(len(frames) - 1, int(lt * be.SFPS))]
        impact = fx in ("drop", "strong")
        z = slot.get("zoom0", 1.0)
        if te >= be.DROP:
            z += (0.16 if impact else 0.07) * (1 - be.ease(lt / (0.3 if impact else 0.2)))
        img = crop43(src, z)
        if fx in FISH:
            img = fisheye(img)
        if fx == "whip":
            img = be.whip(img, 1 - lt / 0.14) if hasattr(be, "whip") else img
        # надпись в центре, полупрозрачная, с лёгким мерцанием
        a = (0.26 + 0.03 * math.sin(te * 23)) * be.ease(te / 1.5)
        img = img * (1 - logo() * a) + 255 * logo() * a
        if impact:
            img = be.shake(img, 9 * math.exp(-lt * 9), i)
        glitch = 1.0 if impact and lt < 0.12 else (0.5 if fx in ("double", "whip") and lt < 0.08 else 0.0)
        img = vhs(img, te, i, glitch)
        img = heavy(img, heavy_level(slot, i, lt, dur), te, i)
        global _gprev
        if g["kinds"]:
            img = dg.apply(img, _gprev, g, 9000 + i)
        _gprev = img.copy()
        if fx == "drop" and lt < 2 / FPS:
            img = 255 - img
        if fx == "drop" and 2 / FPS <= lt < 4 / FPS:
            img = img * 0.3 + 255 * 0.7
        if fx == "fadein":
            img = img * be.ease(lt / 1.2)
        if fx == "flash_end" and lt > dur - 2 / FPS:
            img = img * 0.35 + 255 * 0.65
        if fx == "end" and lt > dur - 0.5:
            img = img * max(0.0, (dur - lt) / 0.5)
        out.append(np.clip(img, 0, 255).astype(np.uint8))
    return out, frames


def main():
    global _prev
    print(f"эдит {be.DUR:.2f} с, планов {len(be.SLOTS)}", flush=True)
    if PREVIEW:
        picks = [0, 2, 5, 6, 7, 11, 17, 18, 21, 25, 30, 36]
        tiles = []
        for k in picks:
            _prev = None
            fr, _ = render_slot(be.SLOTS[k])
            tiles.append(Image.fromarray(fr[min(len(fr) - 1, 14)]))
        sheet = Image.new("RGB", (VW * 4, VH * 3))
        for j, t in enumerate(tiles):
            sheet.paste(t, ((j % 4) * VW, (j // 4) * VH))
        sheet.save(os.path.join(HERE, "preview_vhs.png"))
        print("preview_vhs.png")
        return
    wav = OUT + ".wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{be.T0:.4f}", "-t", f"{be.DUR:.4f}", "-i", be.TRACK,
                    "-af", f"afade=t=in:d=0.12,afade=t=out:st={be.DUR - 0.6:.3f}:d=0.6", wav], check=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-vf", "scale=1080:810:flags=bilinear,pad=1080:1920:0:555:black",
           "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
           "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev = None
    for k, s in enumerate(be.SLOTS):
        frames, prev = render_slot(s, prev)
        for f in frames:
            p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
