#!/usr/bin/env python3
"""Фонк-эдит под трек «Jxned J — Check Yourself» из ролика с суперкарами.

cd tiktok/phonk_edit && python3 build_edit.py [preview]
Входы (не в git): input/source.mp4 (854×362, 25 к/с), input/track.mp3 (140 BPM, первый бит 0.023 с).
Выход: phonk_check_yourself.mp4 — 1080×1920, 30 с (такты 6–23 трека: 2 такта разгона + 16 тактов дропа).

Кадр: широкая «киношная» полоса по центру + размытый фон; на сильных долях — врыв на весь экран.
Эффекты в бит: вспышка, негатив, тряска, зум-удар, дубли, зеркало, размытый рывок.
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "input", "source.mp4")
TRACK = os.path.join(HERE, "input", "track.mp3")
OUT = os.path.join(HERE, "phonk_check_yourself.mp4")
PREVIEW = len(sys.argv) > 1 and sys.argv[1] == "preview"

W, H = 540, 960            # внутренний кадр, на выходе ×2 = 1080×1920
FPS = 30
SW, SH, SFPS = 854, 362, 25
BEAT = 60 / 140
BAR = 4 * BEAT
T0 = 0.023 + 6 * BAR       # начало эдита в треке: такт 6 (2 такта до дропа)
DUR = 18 * BAR             # 30.86 с
DROP = 2 * BAR             # дроп от начала эдита
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---------------------------------------------------------------- раскладка планов
# (время в источнике, флаги). Разгон: такт 0 — один план, такт 1 — 4 удара.
INTRO = [(6.3, "fadein"), (62.1, ""), (113.8, ""), (169.6, ""), (203.0, "flash_end")]
# Дроп: 32 полутакта (по 2 удара). Сильные такты трека — нечётные → полутакты 2, 6, 10, … (+ сам дроп 0).
DROPS = [
    (25.0, "drop"), (88.8, ""), (182.8, "strong"), (131.5, ""),
    (178.4, ""), (178.4, "double"), (196.0, "strong"), (187.5, ""),
    (160.6, ""), (148.0, "whip"), (165.5, "strong"), (93.3, ""),
    (84.5, "mirror"), (74.0, ""), (233.1, "strong"), (218.0, ""),
    (44.6, ""), (41.6, "whip"), (255.0, "strong"), (259.0, ""),
    (262.8, ""), (262.8, "double"), (26.8, "strong"), (114.3, "whip"),
    (170.1, ""), (136.5, "mirror"), (184.6, "strong"), (243.0, ""),
    (228.5, ""), (231.3, ""), (197.6, "strong"), (100.0, "end"),
]
SLOTS = []
SLOTS.append(dict(t0=0.0, t1=BAR, src=INTRO[0][0], fx=INTRO[0][1]))
for k in range(4):
    SLOTS.append(dict(t0=BAR + k * BEAT, t1=BAR + (k + 1) * BEAT, src=INTRO[k + 1][0], fx=INTRO[k + 1][1], zoom0=1.0 + 0.06 * k))
for k, (src, fx) in enumerate(DROPS):
    SLOTS.append(dict(t0=DROP + k * 2 * BEAT, t1=DROP + (k + 1) * 2 * BEAT, src=src, fx=fx))


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- источник
def decode(t, dur):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", SRC, "-t", f"{dur + 0.2:.3f}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8)
    n = len(fr) // (SW * SH * 3)
    return fr[: n * SW * SH * 3].reshape(n, SH, SW, 3)


def grade(img):
    """Ночной фонк-цвет: контраст, лёгкий холод в тенях, сочные огни."""
    x = img.astype(np.float32) / 255
    x = np.clip((x - 0.5) * 1.18 + 0.5, 0, 1)
    lum = x.mean(-1, keepdims=True)
    x = lum + (x - lum) * 1.12
    x[..., 2] += 0.05 * (1 - lum[..., 0])
    x[..., 0] -= 0.02 * (1 - lum[..., 0])
    return np.clip(x * 255, 0, 255)


VIG = None


def vignette():
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        VIG = np.clip(1.15 - 0.45 * d ** 2, 0.35, 1)[..., None]
    return VIG


def band_frame(src, zoom=1.0, mirror=False):
    """Широкий кадр на всю ширину по центру + размытый затемнённый фон."""
    cw = SH * W / H
    bg = Image.fromarray(src[:, int(SW / 2 - cw / 2):int(SW / 2 + cw / 2)]).resize((54, 96), Image.BILINEAR)
    bg = bg.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
    out = np.asarray(bg, np.float32) * 0.32
    bh = W                                   # квадратный кадр 1:1 по центру (≈56% высоты экрана)
    zw = zh = SH / zoom
    crop = Image.fromarray(src).crop((SW / 2 - zw / 2, SH / 2 - zh / 2, SW / 2 + zw / 2, SH / 2 + zh / 2))
    band = np.asarray(crop.resize((W, bh), Image.BICUBIC), np.float32)
    if mirror:
        band[:, W // 2:] = band[:, :W // 2][:, ::-1]
    y0 = (H - bh) // 2
    out[y0:y0 + bh] = band
    out[y0 - 2:y0] = 0
    out[y0 + bh:y0 + bh + 2] = 0
    return out


def full_frame(src, zoom=1.0):
    """Врыв на весь экран: вертикальная вырезка 9:16 из центра."""
    cw, ch = SH * W / H / zoom, SH / zoom
    crop = Image.fromarray(src).crop((SW / 2 - cw / 2, SH / 2 - ch / 2, SW / 2 + cw / 2, SH / 2 + ch / 2))
    return np.asarray(crop.resize((W, H), Image.BICUBIC), np.float32)


def shake(img, amp, seed):
    if amp < 0.5:
        return img
    r = np.random.default_rng(seed)
    dx, dy = r.normal(0, amp, 2).astype(int)
    return np.roll(np.roll(img, dy, 0), dx, 1)


def whip(img, k):
    """Размытый рывок по горизонтали (k: 1 → 0)."""
    if k <= 0:
        return img
    acc = np.zeros_like(img)
    n = 7
    for j in range(n):
        acc += np.roll(img, int((j - n // 2) * 14 * k), axis=1)
    return acc / n


# ---------------------------------------------------------------- текст
_f = {}


def font(sz):
    if sz not in _f:
        _f[sz] = ImageFont.truetype(FONT, sz)
    return _f[sz]


def spaced(d, cx, y, s, sz, fill, sp=2, shadow=True):
    f = font(sz)
    w = sum(d.textlength(c, font=f) for c in s) + sp * (len(s) - 1)
    x = cx - w / 2
    for c in s:
        if shadow:
            d.text((x + 2, y + 2), c, font=f, fill=(0, 0, 0))
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + sp


def overlay_text(img, te, glitch):
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    if te < DROP:
        a = int(255 * ease(te / 0.6))
        spaced(d, W / 2, 96, "JXNED J", 54, (255, 255, 255, a), 4)
        spaced(d, W / 2, 160, "CHECK YOURSELF", 26, (220, 40, 60), 6)
    else:
        off = 3 if glitch else 0
        if off:
            spaced(d, W / 2 - off, 168, "JXNED J — CHECK YOURSELF", 18, (255, 0, 60), 3, False)
            spaced(d, W / 2 + off, 168, "JXNED J — CHECK YOURSELF", 18, (0, 200, 255), 3, False)
        spaced(d, W / 2, 168, "JXNED J — CHECK YOURSELF", 18, (235, 235, 235), 3)
    return np.asarray(im, np.float32)


# ---------------------------------------------------------------- кадр
def render_slot(slot, prev=None):
    dur = slot["t1"] - slot["t0"]
    frames = decode(slot["src"], dur) if slot["fx"] != "double" or prev is None else prev
    out = []
    n0, n1 = int(round(slot["t0"] * FPS)), int(round(slot["t1"] * FPS))
    for i in range(n0, n1):
        te = i / FPS
        lt = te - slot["t0"]
        src = frames[min(len(frames) - 1, int(lt * SFPS))]
        fx = slot["fx"]
        impact = fx in ("drop", "strong")
        if impact and lt < BEAT:
            img = full_frame(src, zoom=1.0 + 0.12 * (1 - ease(lt / BEAT)))
        else:
            z = slot.get("zoom0", 1.0)
            if slot["t0"] >= DROP:
                z += 0.12 * (1 - ease(lt / 0.22))
            img = band_frame(src, zoom=z, mirror=(fx == "mirror"))
        img = grade(img)
        if fx == "whip":
            img = whip(img, 1 - lt / 0.14)
        if impact:
            img = shake(img, 14 * math.exp(-lt * 9), i)
            if lt < 3 / FPS:
                img = 255 - img                     # негатив на ударе
        if fx == "drop" and lt < 2 / FPS:
            img = img * 0.2 + 255 * 0.8             # белая вспышка дропа
        if fx == "double" and lt < 2 / FPS:
            img = img * 1.4
        if fx == "fadein":
            img = img * ease(lt / 1.2)
        if fx == "flash_end" and lt > dur - 2 / FPS:
            img = img * 0.3 + 255 * 0.7
        if fx == "end" and lt > dur - 0.5:
            img = img * max(0.0, (dur - lt) / 0.5)
        img = img * vignette()
        img = overlay_text(img, te, glitch=impact and lt < 0.15)
        out.append(np.clip(img, 0, 255).astype(np.uint8))
    return out, frames


def main():
    print(f"эдит {DUR:.2f} с, планов {len(SLOTS)}", flush=True)
    if PREVIEW:
        picks = [0, 2, 5, 6, 7, 11, 17, 18, 21, 25, 30, 36]
        tiles = []
        for k in picks:
            s = SLOTS[k]
            fr, _ = render_slot(s)
            tiles.append(Image.fromarray(fr[min(len(fr) - 1, 16)]).resize((180, 320)))
        sh = Image.new("RGB", (180 * len(tiles), 320))
        for j, t in enumerate(tiles):
            sh.paste(t, (j * 180, 0))
        sh.save(os.path.join(HERE, "preview.png"))
        print("preview.png")
        return
    wav = OUT + ".wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{T0:.4f}", "-t", f"{DUR:.4f}", "-i", TRACK,
                    "-af", f"afade=t=in:d=0.12,afade=t=out:st={DUR - 0.6:.3f}:d=0.6", wav], check=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=lanczos,unsharp=5:5:0.6", "-c:v", "libx264",
           "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
           "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev = None
    for k, s in enumerate(SLOTS):
        frames, prev = render_slot(s, prev)
        for f in frames:
            p.stdin.write(f.tobytes())
        if k % 8 == 0:
            print(f"  план {k}/{len(SLOTS)}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
