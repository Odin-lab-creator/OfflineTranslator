#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», тестовые кадры по методичке «Сто метров»: фоны pixflux строго сбоку + Денис-спрайт + общая палитра 48.

python3 frames_sto.py  →  sto/test/sto_01…05.png (1080×1920) и sto/test/sheet.png
Сцена 180×200 арт-пикселей ×6 = 1080×1200 по центру вертикального кадра; сверху титр, снизу субтитры.
"""
import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
STO = os.path.join(HERE, "sto")
DEN = os.path.join(HERE, "src", "denis128")
OUT = os.path.join(STO, "test")
SW, SH, K = 180, 200, 6
W, H = 1080, 1920
TOPY = (H - SH * K) // 2
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
C_TEXT, C_DARK, C_HI = (236, 230, 214), (10, 10, 12), (240, 196, 120)


def anim(name, k):
    return Image.open(os.path.join(DEN, f"Idle__animations__{name}__frame_{k:03d}.png")).convert("RGBA")


def rot(v):
    return Image.open(os.path.join(DEN, f"Idle__rotations__{v}.png")).convert("RGBA")


def bg(name):
    return Image.open(os.path.join(STO, f"bg_{name}.png")).convert("RGB")


# кадр: фон, окно камеры по x, спрайт, x центра, линия ступней, отражение, затемнение, титр, субтитр
SHOTS = [
    dict(n="01", bg="room", cx=0, spr=lambda: anim("getup__east", 0), x=116, feet=197,
         title="ДЕНЬ 1", sub="Первое, что я услышал, — тишину."),
    dict(n="02", bg="room", cx=140, spr=lambda: rot("north"), x=92, feet=190,
         sub="Решётки. Восемь лет живу на третьем этаже. Здесь никогда не было решёток."),
    dict(n="03", bg="corridor", cx=80, spr=lambda: anim("shout__east", 7), x=120, feet=176, flip=True,
         sub="— Эй! Есть кто живой?"),
    dict(n="04", bg="hall", cx=0, spr=lambda: anim("kick__north", 2), x=95, feet=196,
         title="ПОПЫТКА №1: ДВЕРЬ", sub="Я толкал. Тянул. Бил плечом, ногой, всем телом."),
    dict(n="05", bg="hall", cx=0, spr=lambda: anim("slide__south", 11), x=95, feet=194, dark=0.45,
         sub="…Или чтобы никто не вошёл."),
]


def palette(images, n=48, seed=0):
    px = []
    for im in images:
        a = np.asarray(im.convert("RGBA")).reshape(-1, 4)
        px.append(a[a[:, 3] > 127][:, :3])
    px = np.concatenate(px).astype(np.float32)
    rng = np.random.default_rng(seed)
    px = px[rng.choice(len(px), min(50000, len(px)), replace=False)]
    c = px[rng.choice(len(px), n, replace=False)]
    for _ in range(20):
        lab = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        for k in range(n):
            m = px[lab == k]
            if len(m):
                c[k] = m.mean(0)
    return c


def quantize(im, pal):
    a = np.asarray(im.convert("RGBA")).copy()
    rgb = a[..., :3].reshape(-1, 3).astype(np.float32)
    idx = ((rgb[:, None] - pal[None]) ** 2).sum(-1).argmin(1)
    a[..., :3] = pal[idx].round().astype(np.uint8).reshape(a.shape[0], a.shape[1], 3)
    return Image.fromarray(a, "RGBA")


def text_layer(title, sub):
    """Текст на сетке 3×3 (вдвое мельче арт-пикселя сцены), с тёмным контуром."""
    g = Image.new("RGBA", (W // 3, H // 3), (0, 0, 0, 0))

    def line(s, y, sz, col):
        f = ImageFont.truetype(FONT, sz)
        m = Image.new("1", g.size, 0)
        d = ImageDraw.Draw(m)
        d.fontmode = "1"
        w = d.textlength(s, font=f)
        d.text(((g.width - w) // 2, y), s, font=f, fill=1)
        mm = np.asarray(m, bool)
        o = mm.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                o |= np.roll(np.roll(mm, dy, 0), dx, 1)
        arr = np.asarray(g).copy()
        arr[o & ~mm] = (*C_DARK, 255)
        arr[mm] = (*col, 255)
        return Image.fromarray(arr, "RGBA")

    def wrap(s, sz, width):
        f = ImageFont.truetype(FONT, sz)
        d = ImageDraw.Draw(Image.new("1", (1, 1)))
        out, cur = [], ""
        for w_ in s.split():
            t = (cur + " " + w_).strip()
            if d.textlength(t, font=f) <= width:
                cur = t
            else:
                out.append(cur)
                cur = w_
        return out + [cur]

    if title:
        g = line(title, 60, 20, C_HI)
    if sub:
        y = (TOPY + SH * K) // 3 + 22
        for ln in wrap(sub, 16, g.width - 30):
            g = line(ln, y, 16, C_TEXT)
            y += 22
    return g.resize((W, H), Image.NEAREST)


def render(s, pal):
    sc = quantize(bg(s["bg"]).crop((s["cx"], 0, s["cx"] + SW, SH)), pal)
    spr = quantize(s["spr"](), pal)
    if s.get("flip"):
        spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
    a = np.asarray(spr)
    ys, xs = np.nonzero(a[..., 3] > 127)
    x0 = s["x"] - (xs.min() + xs.max()) // 2
    y0 = s["feet"] - ys.max()
    sc.alpha_composite(spr, (int(x0), int(y0)))
    scene = np.asarray(sc.convert("RGB")).astype(np.float32)
    if s.get("dark"):
        scene *= 1 - s["dark"]
    frame = Image.new("RGB", (W, H), C_DARK)
    frame.paste(Image.fromarray(scene.astype(np.uint8)).resize((SW * K, SH * K), Image.NEAREST), (0, TOPY))
    frame = frame.convert("RGBA")
    frame.alpha_composite(text_layer(s.get("title"), s.get("sub")))
    return frame.convert("RGB")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    srcs = [bg(n) for n in ("room", "corridor", "hall")] + [s["spr"]() for s in SHOTS]
    pal = palette(srcs)
    Image.fromarray(pal.round().astype(np.uint8)[None]).resize((48 * 10, 10), Image.NEAREST).save(
        os.path.join(OUT, "palette48.png"))
    frames = []
    for s in SHOTS:
        im = render(s, pal)
        im.save(os.path.join(OUT, f"sto_{s['n']}.png"))
        frames.append(im)
    sheet = Image.new("RGB", (5 * 364, 640), (24, 24, 28))
    for k, im in enumerate(frames):
        sheet.paste(im.resize((360, 640)), (k * 364, 0))
    sheet.save(os.path.join(OUT, "sheet.png"))
    print("готово:", OUT)
