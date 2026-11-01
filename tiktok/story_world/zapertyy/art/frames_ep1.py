#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1: тестовые кадры 1080×1920 и раскадровка.

python3 frames_ep1.py  →  test/ep1_01.png … ep1_06.png, test/storyboard_ep1.png

Кадр 108×192 арт-пикселей, пиксель 10×10 (как в канале). Фоны 160×192 — камера берёт кусок шириной 108,
верхние TOP строк (потолок) срезаются, внизу — тёмная полоса под субтитры.
Денис — спрайт PixelLab 64px в родном масштабе 1:1. Надписи на стенах — по сетке кадра;
субтитры и титры — интерфейсный слой с пикселем 5×5 (вдвое мельче), чтобы текст читался.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import master_palette as mp  # noqa: E402

SRC = os.path.join(HERE, "src")
OUT = os.path.join(HERE, "test")
CW, CH, PX = 108, 192, 10
TOP, BAND = 26, 26          # срез сверху и полоса субтитров снизу
UI = 2                      # интерфейсный слой: пиксель PX/UI
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PAL = mp.colors().astype(int)


def pal(rgb):
    return tuple(int(v) for v in PAL[np.argmin(((PAL - np.array(rgb)) ** 2).sum(1))])


C_TEXT, C_DARK, C_RED, C_HI = pal((236, 230, 214)), pal((12, 10, 14)), pal((170, 46, 38)), pal((240, 190, 110))


def sprite(view):
    p = os.path.join(SRC, "denis_edit", f"{view}.png")
    if not os.path.exists(p):
        p = os.path.join(SRC, "denis", f"Idle__rotations__{view}.png")
    return Image.open(p).convert("RGBA")


def lying():
    """Лежит на спине: вид сбоку, повёрнутый на 90° (голова слева, лицо вверх)."""
    return sprite("east").rotate(90, expand=True)


def put(art, spr, cx, feet):
    a = np.asarray(spr)
    ys, xs = np.nonzero(a[..., 3] > 127)
    x0 = cx - (xs.min() + xs.max()) // 2
    y0 = feet - ys.max()
    for y, x in zip(ys, xs):
        X, Y = x + x0, y + y0
        if 0 <= X < CW and 0 <= Y < CH:
            art[Y, X] = a[y, x, :3]


# ------------------------------------------------------------------ пиксельный текст
_fonts = {}


def font(sz):
    if sz not in _fonts:
        _fonts[sz] = ImageFont.truetype(FONT, sz)
    return _fonts[sz]


def text_mask(s, sz):
    d = ImageDraw.Draw(Image.new("1", (1, 1)))
    w = int(d.textlength(s, font=font(sz))) + 2
    m = Image.new("1", (w, sz + 4), 0)
    dd = ImageDraw.Draw(m)
    dd.fontmode = "1"
    dd.text((1, 0), s, font=font(sz), fill=1)
    return np.asarray(m, bool)


def put_text(art, s, cy, sz, color, x=None, outline=True):
    g = text_mask(s, sz)
    h, w = g.shape
    x0 = (CW - w) // 2 if x is None else x
    sl = (slice(cy, cy + h), slice(x0, x0 + w))
    if outline:
        o = np.zeros_like(g)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                o |= np.roll(np.roll(g, dy, 0), dx, 1)
        reg = art[sl]
        reg[o[: reg.shape[0], : reg.shape[1]] & ~g[: reg.shape[0], : reg.shape[1]]] = C_DARK
    reg = art[sl]
    reg[g[: reg.shape[0], : reg.shape[1]]] = color


def wrap(s, sz, width=CW - 8):
    d = ImageDraw.Draw(Image.new("1", (1, 1)))
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font(sz)) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def ui_text(ui, s, cy, sz, color):
    g = text_mask(s, sz)
    h, w = g.shape
    W = ui.shape[1]
    x0 = (W - w) // 2
    o = np.zeros_like(g)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(g, dy, 0), dx, 1)
    reg = ui[cy:cy + h, x0:x0 + w]
    reg[(o & ~g)[: reg.shape[0], : reg.shape[1]]] = (*C_DARK, 255)
    reg[g[: reg.shape[0], : reg.shape[1]]] = (*color, 255)


def subtitle(ui, s, sz=13):
    lines = wrap(s, sz, width=CW * UI - 12)
    lh = sz + 3
    y = (CH - BAND) * UI + (BAND * UI - lh * len(lines)) // 2
    for ln in lines:
        ui_text(ui, ln, y, sz, C_TEXT)
        y += lh


# ------------------------------------------------------------------ кадры
def bg(name, cam):
    im = np.asarray(Image.open(os.path.join(SRC, f"bg_{name}.png")).convert("RGB")).copy()
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = C_DARK
    art[:CH - BAND] = im[TOP:TOP + CH - BAND, cam:cam + CW]
    return art


SHOTS = [
    dict(n="01", tc="0:05", name="Очнулся", bg="room", cam=0,
         hero=("lying", 40, 178), title="ДЕНЬ 1",
         sub="Первое, что я услышал, — тишину. Будто кто-то выключил весь мир."),
    dict(n="02", tc="0:42", name="Окно", bg="room", cam=52,
         hero=("north", 62, 170),
         sub="Решётки. Восемь лет живу на третьем этаже. Здесь никогда не было решёток."),
    dict(n="03", tc="0:55", name="Улица за решёткой", bg="window", cam=26,
         sub="Машины брошены посреди дороги. И ни одного человека."),
    dict(n="04", tc="1:08", name="Коридор", bg="corridor", cam=26,
         hero=("south-west", 52, 158),
         sub="— Эй! Есть кто живой?"),
    dict(n="05", tc="1:20", name="Лестница", bg="stairs", cam=40,
         hero=("east", 46, 177), wall=("К АВТОБУСАМ", 52),
         sub="На стене кто-то написал: «К автобусам». Каким ещё автобусам?"),
    dict(n="06", tc="1:40", name="Дверь подъезда", bg="entrance_wide", cam=52,
         hero=("east", 56, 184), title="ПОПЫТКА №1: ДВЕРЬ",
         sub="Она даже не дрогнула. Как будто это не дверь, а стена."),
]


def render(s):
    art = bg(s["bg"], s["cam"])
    ui = np.zeros((CH * UI, CW * UI, 4), np.uint8)
    if "wall" in s:
        txt, y = s["wall"]
        y -= TOP
        put_text(art, txt, y, 9, C_RED, outline=False)
        cx = CW // 2
        for k in range(7):                                   # стрелка вниз краской
            art[y + 13 + k, cx - 1:cx + 1] = C_RED
        for k in range(4):
            art[y + 17 + k, cx - 4 + k:cx + 4 - k] = C_RED
    if "hero" in s:
        view, cx, feet = s["hero"]
        put(art, lying() if view == "lying" else sprite(view), cx, feet - TOP)
    if "title" in s:
        ui_text(ui, s["title"], 10, 16, C_HI)
    subtitle(ui, s["sub"])
    base = Image.fromarray(art).resize((CW * PX, CH * PX), Image.NEAREST).convert("RGBA")
    over = Image.fromarray(ui, "RGBA").resize((CW * PX, CH * PX), Image.NEAREST)
    base.alpha_composite(over)
    return base.convert("RGB")


def storyboard(frames):
    tw, th = 324, 576
    cols = 3
    rows = (len(frames) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 20) + 20, rows * (th + 70) + 20), (24, 24, 28))
    d = ImageDraw.Draw(S)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19)
    for k, (s, im) in enumerate(zip(SHOTS, frames)):
        x, y = 20 + (k % cols) * (tw + 20), 20 + (k // cols) * (th + 70)
        S.paste(im.resize((tw, th), Image.NEAREST), (x, y))
        d.text((x, y + th + 10), f"{s['n']} · {s['tc']} · {s['name']}", font=f, fill=(240, 200, 120))
    return S


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    frames = []
    for s in SHOTS:
        im = render(s)
        im.save(os.path.join(OUT, f"ep1_{s['n']}.png"))
        frames.append(im)
    storyboard(frames).save(os.path.join(OUT, "storyboard_ep1.png"))
    print("готово:", OUT)
