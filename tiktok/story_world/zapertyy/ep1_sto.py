#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 — версия по методичке «Сто метров» (вид сбоку, экран игры в вертикальном кадре).

python3 ep1_sto.py  →  zapertyy_ep1_sto.mp4 (1080×1920, 30 к/с)

Сцена 180×200 арт-пикселей ×6 = 1080×1200 по центру; сверху титры, снизу субтитры (сцену не закрывают).
Фоны — pixflux (art/sto, вид сбоку, без перспективы), Денис 128px с анимациями v3 (art/src/denis128),
крупные планы — предметы pixflux (art/sto/obj_*). Всё сведено к общей палитре 48 цветов.
Камера едет по панорамам с точностью до экранного пикселя. Озвучка и шумы — из ep1_build.py.
"""
import functools
import glob
import os
import subprocess
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import ep1_build as base

HERE = base.HERE
STO = os.path.join(HERE, "art", "sto")
DEN = os.path.join(HERE, "art", "src", "denis128")
OUT = os.path.join(HERE, "zapertyy_ep1_sto.mp4")
FPS, SR = 30, base.SR
W, H = 1080, 1920
SW, SH, K = 180, 200, 6
BAND_Y = (H - SH * K) // 2
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
C_TEXT, C_DARK, C_HI, C_PAINT = (236, 230, 214), (10, 10, 12), (240, 196, 120), (150, 40, 34)
DUR = base.DUR


# ------------------------------------------------------------------ палитра и ресурсы
def _load(path):
    return Image.open(path).convert("RGBA")


def _fix(name, im):
    a = np.asarray(im).copy()
    if name == "bg_stairs":                                  # стрелка вниз (меньше) + надпись над ней
        y0, y1, x0, x1 = 51, 170, 237, 310
        reg = a[y0:y1, x0:x1].copy()
        rgb = reg[..., :3].astype(int)
        red = (rgb[..., 0] > rgb[..., 1] + 50) & (rgb[..., 0] > rgb[..., 2] + 50)
        wall = a[y0:y1, 200:237]
        fill = np.concatenate([wall, wall, wall], 1)[:, :x1 - x0]
        a[y0:y1, x0:x1] = fill
        arr = Image.fromarray(np.where(red[..., None], reg, 0).astype(np.uint8)[::-1], "RGBA")
        msk = Image.fromarray((red[::-1] * 255).astype(np.uint8))
        nh = 92
        arr, msk = arr.resize((x1 - x0, nh), Image.NEAREST), msk.resize((x1 - x0, nh), Image.NEAREST)
        sub = a[y1 - nh:y1, x0:x1]
        mm = np.asarray(msk) > 0
        sub[mm] = np.asarray(arr)[mm]
        f = ImageFont.truetype(FONT, 10)
        m = Image.new("1", (100, 14), 0)
        d = ImageDraw.Draw(m)
        d.fontmode = "1"
        w = d.textlength("К АВТОБУСАМ", font=f)
        d.text((0, 0), "К АВТОБУСАМ", font=f, fill=1)
        g = np.asarray(m, bool)
        ys, xs = np.nonzero(g)
        a[ys + 58, xs + int((x0 + x1) / 2 - w / 2)] = (*C_PAINT, 255)
    if name == "obj_weld":                                   # рукав — серый, как толстовка
        rgb = a[..., :3].astype(int)
        red = (rgb[..., 0] > rgb[..., 1] + 40) & (rgb[..., 0] > rgb[..., 2] + 40) & (a[..., 3] > 0)
        lum = (rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11) * 0.9 + 25
        a[red, 0] = lum[red]
        a[red, 1] = lum[red]
        a[red, 2] = np.minimum(255, lum[red] * 1.06)
    return Image.fromarray(a, "RGBA")


SOURCES = {n: os.path.join(STO, f"{n}.png") for n in
           ("bg_room", "bg_corridor", "bg_hall", "bg_street", "bg_stairs", "obj_phone", "obj_watch", "obj_pills",
            "obj_tap", "obj_weld", "obj_intercom", "obj_crack")}


@functools.lru_cache(1)
def palette(n=48):
    px = []
    for name, p in SOURCES.items():
        a = np.asarray(_fix(name, _load(p))).reshape(-1, 4)
        px.append(a[a[:, 3] > 127][:, :3])
    for f in sorted(glob.glob(os.path.join(DEN, "*.png")))[::6]:
        a = np.asarray(_load(f)).reshape(-1, 4)
        px.append(a[a[:, 3] > 127][:, :3])
    px = np.concatenate(px).astype(np.float32)
    rng = np.random.default_rng(0)
    px = px[rng.choice(len(px), 60000, replace=False)]
    c = px[rng.choice(len(px), n, replace=False)]
    for _ in range(20):
        lab = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        for k in range(n):
            m = px[lab == k]
            if len(m):
                c[k] = m.mean(0)
    return c


def quantize(a):
    pal = palette()
    rgb = a[..., :3].reshape(-1, 3).astype(np.float32)
    idx = np.empty(len(rgb), int)
    for s in range(0, len(rgb), 20000):
        idx[s:s + 20000] = ((rgb[s:s + 20000, None] - pal[None]) ** 2).sum(-1).argmin(1)
    out = a.copy()
    out[..., :3] = pal[idx].round().astype(np.uint8).reshape(a.shape[0], a.shape[1], 3)
    return out


@functools.lru_cache(None)
def img(name):
    return quantize(np.asarray(_fix(name, _load(SOURCES[name]))))


@functools.lru_cache(None)
def anim(name):
    fs = sorted(glob.glob(os.path.join(DEN, f"Idle__animations__{name}__frame_*.png")))
    fr = [quantize(np.asarray(_load(f))) for f in fs]
    floor = max(int(np.nonzero(f[..., 3] > 127)[0].max()) for f in fr)
    return fr, floor


@functools.lru_cache(None)
def rot(v):
    return quantize(np.asarray(_load(os.path.join(DEN, f"Idle__rotations__{v}.png"))))


# ------------------------------------------------------------------ таймлайн
tl = base.TL()
SC = []                        # [t0, t1, тип, параметры]


def scene(kind, **kw):
    if SC:
        SC[-1][1] = tl.t
    SC.append([tl.t, None, kind, kw])


def walk_steps(t0, t1):
    t = t0
    while t < t1:
        tl.fx("step", t)
        t += 0.34


scene("black")
for k in range(3):
    tl.fx("bang", 0.15 + k * 0.6)
tl.wait(1.9)
tl.say("00", 0.35)
tl.titles.append((tl.t, tl.t + 1.7, "ЗАПЕРТЫЙ", 60))
tl.titles.append((tl.t + 0.3, tl.t + 1.7, "СЕРИЯ 1", 88))
tl.wait(1.9)

scene("room_wake")
tl.fx("ring")
tl.titles.append((tl.t + 0.8, tl.t + 4.5, "ДЕНЬ 1", 70))
tl.wait(0.8)
tl.say("01", 0.5)
tl.say("02", 0.4)
scene("room_getup")
tl.say("03", 0.35)
t04 = tl.say("04", 0.0)
c04 = base.chunk_times("04", t04)
SC[-1][1] = c04[1][0]
SC.append([c04[1][0], None, "insert", dict(obj="obj_phone")])
t_mid = c04[2][0] if len(c04) > 2 else c04[1][1]
SC[-1][1] = t_mid
SC.append([t_mid, None, "insert", dict(obj="obj_watch")])
tl.t += 0.45
scene("insert", obj="obj_pills")
tl.say("05", 0.35)
scene("insert", obj="obj_tap", drip=True)
tl.fx("drip")
tl.wait(0.35)
tl.say("06", 0.15)
tl.fx("drip")
tl.wait(0.6)
tl.fx("drip")
tl.wait(0.4)

scene("room_window")
T_WIN = tl.t
walk_steps(tl.t + 0.1, tl.t + 2.4)
tl.fx("whoosh", tl.t + 2.6)
tl.wait(0.4)
tl.say("07", 0.3)
T_SHAKE = tl.t - 1.6
for k in range(6):
    tl.fx("rattle", T_SHAKE + k * 0.27)
scene("insert", obj="obj_weld", rattle=True)
for k in range(6):
    tl.fx("rattle", tl.t + 0.1 + k * 0.32)
tl.say("08", 0.3)
scene("street")
tl.wait(0.3)
tl.say("09", 0.5)

scene("corridor")
T_CORR = tl.t
tl.fx("creak")
walk_steps(tl.t + 0.3, tl.t + 3.6)
tl.wait(0.4)
tl.say("10", 0.35)
tl.say("11", 0.4)
T_SHOUT = tl.t
tl.say("12", 1.2)
tl.say("13", 0.4)

scene("stairs")
T_STAIRS = tl.t
walk_steps(tl.t + 0.1, tl.t + 4.6)
tl.wait(0.5)
tl.say("14", 0.5)

scene("hall_walk")
T_HALL = tl.t
walk_steps(tl.t + 0.1, tl.t + 2.6)
tl.wait(1.4)
t15 = tl.say("15", 0.2)
c15 = base.chunk_times("15", t15)
if len(c15) > 1:                                             # «Домофон не горит…» — крупный план домофона
    SC[-1][1] = c15[1][0]
    SC.append([c15[1][0], None, "insert", dict(obj="obj_intercom")])
    tl.fx("rattle", c15[1][0] + 0.3)
scene("hall_kick")
T_KICK = tl.t
KICK_FPS, KICK_N, KICK_LOOPS = 12, 14, 3
KICKS = [T_KICK + (c * KICK_N + f) / KICK_FPS for c in range(KICK_LOOPS) for f in (2, 7)]
for t in KICKS:
    tl.fx("bang", t)
tl.wait(0.4)
tl.say("16", 0.3)
scene("hall_crouch")
tl.wait(0.8)
scene("insert", obj="obj_crack")
tl.say("17", 0.5)
scene("hall_end")
tl.fx("slide", tl.t + 0.3)
tl.wait(0.3)
tl.say("18", 0.8)
tl.say("19", 0.5)
tl.titles.append((tl.t, tl.t + 2.4, "ПОПЫТКА №1: ДВЕРЬ — ПРОВАЛ", 70))
tl.wait(2.4)
tl.titles.append((tl.t, tl.t + 3.0, "ЧТО БЫ ВЫ СДЕЛАЛИ ПЕРВЫМ?", 70))
tl.wait(3.0)
SC[-1][1] = tl.t
TOTAL = tl.t

SUBS = []
for t0, i in tl.voice:
    for a, b, c in base.chunk_times(i, t0):
        SUBS.append((a, b + 0.12, c))
RATTLES = [t for t, s in tl.sfx if s == "rattle"]


# ------------------------------------------------------------------ сцены
def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def frame_of(name, lt, fps=12, loop=True, frames=None):
    fr, floor = anim(name)
    seq = frames if frames is not None else list(range(len(fr)))
    k = int(lt * fps)
    k = seq[k % len(seq)] if loop else seq[min(k, len(seq) - 1)]
    return fr[k], floor


def put(canvas, a, x, feet, floor=None, flip=False):
    """Спрайт на холст сцены (координаты фона). floor=None — по рамке (повороты 128)."""
    if flip:
        a = a[:, ::-1]
    m = a[..., 3] > 127
    ys, xs = np.nonzero(m)
    if floor is None:
        ax, ay = (xs.min() + xs.max()) // 2, ys.max()
    else:
        ax, ay = a.shape[1] // 2, floor
    X, Y = xs + int(round(x)) - ax, ys + int(round(feet)) - ay
    ok = (X >= 0) & (X < canvas.shape[1]) & (Y >= 0) & (Y < canvas.shape[0])
    canvas[Y[ok], X[ok]] = a[ys[ok], xs[ok], :3]


def walker(canvas, lt, t0, t1, x0, x1, y0, y1, flip=False):
    """Идёт из (x0,y0) в (x1,y1) между t0 и t1 (локальное время сцены)."""
    u = min(1.0, max(0.0, (lt - t0) / (t1 - t0)))
    a, fl = frame_of("walking__east", lt - t0, fps=12)
    put(canvas, a, lerp(x0, x1, u), lerp(y0, y1, u), fl, flip)


def idle(canvas, lt, x, feet, d="east"):
    a, fl = frame_of(f"breathing_idle__{d}", lt, fps=3)
    put(canvas, a, x, feet, fl)


def band_scene(name, cam):
    bgimg = img(name)
    return bgimg[..., :3].copy(), cam


def scene_art(t):
    """→ (холст фона с героем, позиция камеры по x в арт-пикселях, доп. эффекты)."""
    for t0, t1, kind, kw in SC:
        if t0 <= t < t1:
            break
    lt, dur = t - t0, t1 - t0
    fx = {}
    if kind == "black":
        return None, 0, {"black": True}
    if kind == "insert":
        return None, 0, {"insert": kw["obj"], "lt": lt, "shake": kw.get("rattle")}
    if kind == "room_wake":
        c, _ = band_scene("bg_room", 0)
        fr, fl = anim("getup__east")
        put(c, fr[0], 116, 197, fl)
        fx["eyelids"] = max(0.0, 1 - lt / 2.4)
        return c, 20, fx
    if kind == "room_getup":
        c, _ = band_scene("bg_room", 0)
        if lt < 14 / 4.0:
            a, fl = frame_of("getup__east", lt, fps=4, loop=False)
            put(c, a, 116, 197, fl)
        else:
            idle(c, lt, 116, 197)
        return c, lerp(20, 50, ease(lt / dur)), fx
    if kind == "room_window":
        c, _ = band_scene("bg_room", 0)
        if lt < 2.4:
            walker(c, lt, 0.0, 2.4, 116, 230, 197, 192)
        elif lt < 2.7:
            put(c, rot("north-east"), 230, 192)
        else:
            a, fl = frame_of("shakebars__north", lt - 2.7, fps=12)
            put(c, a, 230, 192, fl)
        return c, lerp(50, 140, ease(lt / 2.6)), fx
    if kind == "street":
        c, _ = band_scene("bg_street", 0)
        return c, lerp(0, 180, ease(lt / dur)), {"bars": True}
    if kind == "corridor":
        c, _ = band_scene("bg_corridor", 0)
        if lt < 3.6:
            walker(c, lt, 0.3, 3.6, -30, 150, 176, 176)
        elif T_SHOUT - t0 <= lt < T_SHOUT - t0 + 1.6:
            a, fl = frame_of("shout__east", lt - (T_SHOUT - t0), fps=9, loop=False)
            put(c, a, 150, 176, fl)
        else:
            idle(c, lt, 150, 176)
        sh = int(np.random.default_rng(int(t * 1000)).integers(-1, 2)) if T_SHOUT <= t < T_SHOUT + 0.9 else 0
        return c, lerp(0, 75, ease(lt / 4.0)) + sh, fx
    if kind == "stairs":
        c, _ = band_scene("bg_stairs", 0)
        if lt < 3.0:
            walker(c, lt, 0.0, 3.0, 30, 190, 78, 170)
        elif lt < 4.6:
            walker(c, lt, 3.0, 4.6, 190, 260, 170, 170)
        else:
            idle(c, lt, 260, 170)
        return c, lerp(0, 175, ease(lt / 5.0)), fx
    if kind == "hall_walk":
        c, _ = band_scene("bg_hall", 0)
        if lt < 2.6:
            walker(c, lt, 0.0, 2.6, -30, 95, 196, 196)
        elif lt < 3.0:
            put(c, rot("north-east"), 95, 196)
        else:
            idle(c, lt, 95, 196, "north")
        return c, 0, fx
    if kind == "hall_kick":
        c, _ = band_scene("bg_hall", 0)
        if lt < KICK_LOOPS * KICK_N / KICK_FPS:
            a, fl = frame_of("kick__north", lt, fps=KICK_FPS)
            put(c, a, 95, 196, fl)
        else:
            idle(c, lt, 95, 196, "north")
        sh = 0
        for x in KICKS:
            if 0 <= t - x < 0.15:
                sh = int(np.random.default_rng(int(t * 1000)).integers(-2, 3))
        return c, sh, fx
    if kind == "hall_crouch":
        c, _ = band_scene("bg_hall", 0)
        a, _ = frame_of("crouching__north", lt, fps=8, loop=False)
        put(c, a, 95, 196)
        return c, 0, fx
    if kind == "hall_end":
        c, _ = band_scene("bg_hall", 0)
        a, fl = frame_of("slide__south", lt, fps=4, loop=False)
        put(c, a, 95, 194, fl)
        fx["dark"] = min(1.0, lt / 9.0) * 0.6
        return c, 0, fx
    return None, 0, {"black": True}


@functools.lru_cache(16)
def insert_band(obj):
    o = img(obj)
    sc = int(min(1000 / o.shape[1], 1100 / o.shape[0]))
    band = np.zeros((SH * K, SW * K, 3), np.float32)
    yy, xx = np.mgrid[0:SH * K, 0:SW * K].astype(np.float32)
    r = np.sqrt(((xx - SW * K / 2) / (SW * K / 2)) ** 2 + ((yy - SH * K / 2) / (SH * K / 2)) ** 2)
    band[:] = (np.clip(1 - r * 0.8, 0, 1) * 34 + 10)[..., None]
    big = np.asarray(Image.fromarray(o, "RGBA").resize((o.shape[1] * sc, o.shape[0] * sc), Image.NEAREST))
    y0, x0 = (SH * K - big.shape[0]) // 2, (SW * K - big.shape[1]) // 2
    al = big[..., 3:4] / 255.0
    reg = band[y0:y0 + big.shape[0], x0:x0 + big.shape[1]]
    reg[:] = reg * (1 - al) + big[..., :3] * al
    return band


def band_image(t):
    c, cam, fx = scene_art(t)
    if fx.get("black"):
        return np.full((SH * K, SW * K, 3), C_DARK, np.float32)
    if "insert" in fx:
        b = insert_band(fx["insert"]).copy()
        dy = int(fx["lt"] * 6) % 2 if False else 0
        if fx.get("shake"):
            for x in RATTLES:
                if 0 <= t - x < 0.1:
                    b = np.roll(b, int(np.random.default_rng(int(t * 1000)).integers(-6, 7)), 1)
        return np.roll(b, dy, 0)
    cam = float(np.clip(cam, -2, c.shape[1] - SW + 2))
    ci = int(np.floor(cam))
    win = np.zeros((SH, SW + 1, 3), np.uint8)
    win[:] = C_DARK
    x0, x1 = max(0, ci), min(c.shape[1], ci + SW + 1)
    win[:, x0 - ci:x1 - ci] = c[:, x0:x1]
    big = win.repeat(K, 0).repeat(K, 1).astype(np.float32)
    off = int(round((cam - ci) * K))
    b = big[:, off:off + SW * K]
    if fx.get("bars"):                                        # решётка окна поверх улицы
        for x in range(60, SW * K, 190):
            b[:, x:x + 26] = b[:, x:x + 26] * 0.12 + 18
            b[:, x + 4:x + 8] = b[:, x + 4:x + 8] * 0.5 + 60
        b[:36] = 22
        b[-36:] = 22
    if fx.get("eyelids", 0) > 0:
        h = int(SH * K / 2 * fx["eyelids"] ** 0.6)
        b[:h] = 0
        b[SH * K - h:] = 0
    if fx.get("dark"):
        b *= 1 - fx["dark"]
    return b


# ------------------------------------------------------------------ текст
def text_mask(s, sz):
    f = ImageFont.truetype(FONT, sz)
    d = ImageDraw.Draw(Image.new("1", (1, 1)))
    w = int(d.textlength(s, font=f)) + 2
    m = Image.new("1", (w, sz + 5), 0)
    dd = ImageDraw.Draw(m)
    dd.fontmode = "1"
    dd.text((1, 0), s, font=f, fill=1)
    return np.asarray(m, bool)


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


def draw_line(ui, s, y, sz, col):
    g = text_mask(s, sz)
    h, w = g.shape
    x0 = (ui.shape[1] - w) // 2
    o = np.zeros((h + 2, w + 2), bool)
    for dy in range(3):
        for dx in range(3):
            o[dy:dy + h, dx:dx + w] |= g
    reg = ui[y - 1:y + h + 1, x0 - 1:x0 + w + 1]
    reg[o[: reg.shape[0], : reg.shape[1]]] = (*C_DARK, 255)
    reg = ui[y:y + h, x0:x0 + w]
    reg[g[: reg.shape[0], : reg.shape[1]]] = (*col, 255)


@functools.lru_cache(256)
def ui_layer(sub, titles):
    ui = np.zeros((H // 3, W // 3, 4), np.uint8)
    if sub:
        y = (BAND_Y + SH * K) // 3 + 18
        for ln in wrap(sub, 19, W // 3 - 30):
            draw_line(ui, ln, y, 19, C_TEXT)
            y += 25
    for text, y in titles:
        for k, ln in enumerate(wrap(text, 18, W // 3 - 30)):
            draw_line(ui, ln, y + k * 24, 18, C_HI)
    return np.asarray(Image.fromarray(ui, "RGBA").resize((W, H), Image.NEAREST))


def render(t):
    frame = np.zeros((H, W, 3), np.float32)
    frame[:] = C_DARK
    frame[BAND_Y:BAND_Y + SH * K] = band_image(t)
    sub = next((s for a, b, s in SUBS if a <= t < b), "")
    titles = tuple((x, y) for p, q, x, y in tl.titles if p <= t < q)
    if sub or titles:
        ui = ui_layer(sub, titles)
        m = ui[..., 3] > 0
        frame[m] = ui[..., :3][m]
    if t > TOTAL - 0.7:
        frame *= max(0.0, (TOTAL - t) / 0.7)
    return np.clip(frame, 0, 255).astype(np.uint8).tobytes()


# ------------------------------------------------------------------ звук и сборка
def build_audio(path):
    n = int(SR * (TOTAL + 1))
    mix = np.zeros(n)
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.35 * t) + 0.4 * np.sin(2 * np.pi * 82.4 * t))
    drone *= 0.035 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t)) * np.clip(t / 6, 0, 1)
    drone *= 1 + 1.2 * np.clip((t - T_KICK + 15) / 20, 0, 1) * np.clip((TOTAL - t) / 3, 0, 1)
    mix += drone + np.convolve(rng.normal(0, 1, n), np.ones(400) / 400, "same") * 0.06
    for t0, i in tl.voice:
        v = base.VOICE[i]
        if i == "12":
            v = base.echo(v)
        elif i in ("13", "14", "15", "16", "17"):
            v = base.reverb(v, 0.5, 0.12)
        k = int(t0 * SR)
        mix[k:k + len(v)] += v[: n - k]
    for t0, s in tl.sfx:
        k = int(t0 * SR)
        if s == "ring":
            m = int(SR * 5)
            tt = np.arange(m) / SR
            mix[k:k + m] += np.sin(2 * np.pi * 5800 * tt) * 0.015 * np.exp(-tt / 2.0)
            continue
        a = base.SFX[s]
        mix[k:k + len(a)] += a[: n - k]
    mix /= max(1e-6, np.abs(mix).max()) / 0.9
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=mix.astype(np.float32).tobytes(), check=True)


def _warm(_):
    palette()
    for n in SOURCES:
        img(n)
    return 0


def main():
    _warm(0)
    wav = OUT + ".wav"
    build_audio(wav)
    nf = int(TOTAL * FPS)
    print(f"длительность {TOTAL:.1f} с, кадров {nf}", flush=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(render, [f / FPS for f in range(nf)], chunksize=30):
            p.stdin.write(buf)
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
