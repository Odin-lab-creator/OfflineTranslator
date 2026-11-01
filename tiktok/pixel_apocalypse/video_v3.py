#!/usr/bin/env python3
"""PIXEL APOCALYPSE v3 — серия 1 «72 ЧАСА» на ассетах PixelLab (STYLE_LOCK v3).

cd tiktok/pixel_apocalypse && python3 video_v3.py [выход.mp4]

Кадр 108×192 арт-пикселей → ×10 = 1080×1920. Фоны 160×192 (камера ездит целыми пикселями),
персонажи 64px. Чистые кадры не меняют ни одного пикселя ассетов; затемнения, свечение и
частицы проходят через главную палитру (с дизерингом Bayer только там, где меняется яркость).
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pixellab"))
sys.path.insert(0, os.path.join(HERE, "..", "series"))
_argv = sys.argv[:]
sys.argv = sys.argv[:1]
import episode1 as ep  # noqa: E402  тайминги слов, звук
sys.argv = _argv
import master_palette as mp  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pixel_apocalypse_ep1_v3.mp4")
A = os.path.join(HERE, "pixellab", "assets")
CW, CH, SC = 108, 192, 10
FPS = 30
DUR = ep.DUR
NFR = int(DUR * FPS)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ------------------------------------------------------------------ палитра
PAL = mp.colors().astype(np.float32)
WTS = mp.WTS
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16 - 0.5
BT = np.tile(BAYER, (CH // 4, CW // 4 + 1))[:CH, :CW, None]
_LUT = None


def lut():
    global _LUT
    if _LUT is None:
        g = np.arange(64, dtype=np.float32) * 4 + 2
        cube = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1).reshape(-1, 3)
        idx = np.empty(len(cube), np.int16)
        for i in range(0, len(cube), 16384):
            ch = cube[i:i + 16384]
            idx[i:i + 16384] = (((ch[:, None] - PAL[None]) ** 2) * WTS).sum(-1).argmin(1)
        _LUT = idx.reshape(64, 64, 64)
    return _LUT


def quantize(img, dither=0.0):
    x = img + BT * dither if dither else img
    q = np.clip(x, 0, 255).astype(np.int32) >> 2
    return PAL[lut()[q[..., 0], q[..., 1], q[..., 2]]].astype(np.uint8)


def pick(pred, key):
    cs = [tuple(int(v) for v in c) for c in PAL if pred(c)]
    return max(cs, key=key)


def _hsv(c):
    r, g, b = [v / 255 for v in c]
    mx, mn = max(r, g, b), min(r, g, b)
    return mx, (mx - mn) / mx if mx else 0


C_TEXT = pick(lambda c: _hsv(c)[1] < 0.25, key=lambda c: sum(c))                      # светлый «кость»
C_HI = pick(lambda c: c[0] > c[1] > c[2] and _hsv(c)[1] > 0.4, key=lambda c: c[0] + c[1])  # оранж
C_RED = pick(lambda c: c[0] > 1.6 * c[1] and c[0] > 1.6 * c[2], key=lambda c: c[0])     # красный
C_DARK = tuple(int(v) for v in PAL[PAL.sum(1).argmin()])
C_ASH = pick(lambda c: _hsv(c)[1] < 0.2 and 90 < sum(c) / 3 < 150, key=lambda c: -abs(sum(c) / 3 - 120))
C_EMBER = C_HI


# ------------------------------------------------------------------ ассеты
def _rgba(path):
    return np.asarray(Image.open(path).convert("RGBA"))


_cache = {}


def bg(name):
    k = "bg_" + name
    if k not in _cache:
        _cache[k] = _rgba(os.path.join(A, f"bg_{name}.png"))[..., :3].astype(np.float32)
    return _cache[k]


def frames(name):
    """Кадры спрайта: папка assets/<name>/ или ракурс <rot>:<n>. Возвращает (кадры, ступни_y, центр_x)."""
    if name in _cache:
        return _cache[name]
    if ":" in name:
        d, n = name.split(":")
        fr = [_rgba(os.path.join(A, d, f"{int(n):03d}.png"))]
    else:
        d = os.path.join(A, name)
        fr = [_rgba(os.path.join(d, f)) for f in sorted(os.listdir(d))] if os.path.isdir(d) else None
    if fr is None:
        _cache[name] = None
        return None
    feet = max(int(np.nonzero((f[..., 3] >= 128).any(1))[0].max()) for f in fr)
    _cache[name] = (fr, feet, fr[0].shape[1] // 2)
    return _cache[name]


def sprite(name, fallback):
    return frames(name) or frames(fallback)


# ------------------------------------------------------------------ тайминги
T = {k: getattr(ep, k) for k in dir(ep) if k.startswith("T_")}
KNOCKS = [T["T_KNOCK"] + 0.1, T["T_KNOCK"] + 0.35, T["T_KNOCK"] + 0.6,
          T["T_THREE"] + 0.75, T["T_THREE"] + 1.05, T["T_THREE"] + 1.35]
END = ep.VOICE_END - 0.2
T_SUDDEN = ep.line_t("И вдруг")
FLOOR = {"corridor": 168, "storeroom": 152, "radio": 150, "window": 176, "night_street": 172}

H_IDLE = ("hero_idle", "hero_rot:2")
H_WALK = ("hero_walk", "hero_rot:2")
H_CROUCH = ("hero_crouch", "hero_rot:2")
Z_WALK = ("zombie_walk", "zombie_rot:2")
Z_IDLE = ("zombie_rot:2", "zombie_rot:2")


def act(spr, x0, x1=None, flip=False, fps=8, feet=None, dark=0.0, t_from=None):
    return dict(spr=spr, x0=x0, x1=x0 if x1 is None else x1, flip=flip, fps=fps, feet=feet, dark=dark, t_from=t_from)


# (начало, конец, фон, камера x от, до, актёры, параметры)
SHOTS = [
    (0.0, 4.6, "window", 52, 44, [act(H_IDLE, 110)], dict(fade_in=1.0, title=True, fx="dust")),
    (4.6, 9.4, "night_street", 0, 52, [act(Z_WALK, 100, 80, flip=True, fps=6), act(Z_WALK, 128, 108, flip=True, fps=6, dark=0.35)],
     dict(fx="ash")),
    (9.4, 13.8, "night_street", 0, 30, [act(H_WALK, -10, 70)], dict(fx="ash")),
    (13.8, 17.0, "night_street", 40, 52, [act(H_CROUCH, 62), act(Z_WALK, 150, 126, flip=True, fps=6)], dict(fx="embers")),
    (17.0, T["T_ITEMS"] - 2.1, "storeroom", 20, 20, [act(H_IDLE, 46)], dict(rule="ПРАВИЛО №1")),
    (T["T_ITEMS"] - 2.1, T["T_PHONE"], "storeroom", 0, 52, [act(H_IDLE, 46)], dict(fx="dust")),
    (T["T_PHONE"], T["T_WATER"], "storeroom", 52, 36, [act(H_IDLE, 46)], dict(fx="dust")),
    (T["T_WATER"], T["T_TRUST"], "storeroom", 36, 44, [act(H_IDLE, 46)], dict(fx="dust")),
    (T["T_TRUST"], T["T_KNOCK"] - 0.1, "corridor", 52, 24, [act(H_IDLE, 30)], dict(fx="dust")),
    (T["T_KNOCK"] - 0.1, T_SUDDEN, "corridor", 24, 24, [act(H_IDLE, 30)], dict(knock=True, door=True)),
    (T_SUDDEN, T["T_RULE2"], "corridor", 24, 34, [act(H_IDLE, 30)], dict(knock=True, door=True, dim_after=(T["T_IKNOW"], 0.7))),
    (T["T_RULE2"], ep.line_t("Не теряй"), "corridor", 30, 30, [act(H_IDLE, 30)], dict(rule="ПРАВИЛО №2", door=True)),
    (ep.line_t("Не теряй"), T["T_NIGHT"], "corridor", 34, 10, [act(H_IDLE, 30)], dict(door=True, fade_out=0.4, fx="dust")),
    (T["T_NIGHT"], T["T_MSG1"], "radio", 52, 6, [act(H_CROUCH, 82, flip=True)], dict(fade_in=0.4, radio="on", fx="dust")),
    (T["T_MSG1"], T["T_LOST"], "radio", 6, 16, [act(H_CROUCH, 82, flip=True)], dict(radio="flicker")),
    (T["T_LOST"], T["T_MSG2"], "radio", 16, 16, [act(H_CROUCH, 82, flip=True)], dict(radio="static", static=True)),
    (T["T_MSG2"], T["T_RULE3"], "radio", 16, 6, [act(H_CROUCH, 82, flip=True)], dict(radio="flicker")),
    (T["T_RULE3"], ep.line_t("Проверяй"), "radio", 10, 10, [act(H_CROUCH, 82, flip=True)], dict(rule="ПРАВИЛО №3", radio="on")),
    (ep.line_t("Проверяй"), T["T_OFF"], "night_street", 52, 0, [act(Z_WALK, 120, 96, flip=True, fps=6, dark=0.2)], dict(fx="ash")),
    (T["T_OFF"], T["T_OFF"] + 0.45, "radio", 10, 10, [act(H_CROUCH, 82, flip=True)], dict(radio="on")),
    (T["T_OFF"] + 0.45, T["T_EYES"], "radio", 10, 22, [act(H_CROUCH, 82, flip=True)], dict(radio="off", phone=True, dim=0.8)),
    (T["T_EYES"], T["T_CREAK"], "window", 52, 48, [act(H_IDLE, 110)], dict(fx="dust")),
    (T["T_CREAK"], T["T_WORST"], "window", 48, 0, [act(H_IDLE, 110), act(Z_IDLE, 34, feet=165, dark=0.25, t_from=T["T_CREAK"] + 1.0)],
     dict(creak=True, pan_from=T["T_CREAK"] + 0.6)),
    (T["T_WORST"], T["T_LAST"], "night_street", 52, 40, [act(H_CROUCH, 66), act(Z_WALK, 150, 120, flip=True, fps=6),
                                                     act(Z_WALK, 175, 150, flip=True, fps=5, dark=0.35)], dict(fx="embers")),
    (T["T_LAST"], END, "window", 0, 0, [act(Z_IDLE, 34, feet=165, dark=0.1)], dict(dim=0.85)),
    (END, DUR, None, 0, 0, [], dict(endcard=True)),
]


def ease(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


# ------------------------------------------------------------------ эффекты
def particles(img, t, kind):
    rng = np.random.default_rng(3)
    if kind == "ash":
        for x0, y0, sp in rng.random((45, 3)):
            y = int((y0 * CH + t * (10 + sp * 12)) % CH); x = int((x0 * CW + t * 4 + 2 * math.sin(t + x0 * 9)) % CW)
            img[y, x] = C_ASH
    elif kind == "dust":
        for x0, y0, sp in rng.random((14, 3)):
            y = int((y0 * CH + t * (2 + sp * 3)) % CH); x = int((x0 * CW + 3 * math.sin(t * 0.7 + y0 * 11)) % CW)
            img[y, x] = img[y, x] * 0.4 + np.array(C_TEXT) * 0.6
    elif kind == "embers":
        for x0, y0, sp in rng.random((22, 3)):
            y = int((y0 * CH - t * (8 + sp * 10)) % CH); x = int((x0 * CW + 4 * math.sin(t * 2 + x0 * 7)) % CW)
            if (int(t * 10) + int(x0 * 50)) % 5:
                img[y, x] = C_EMBER


def glow(img, cx, cy, r, c, k):
    yy, xx = np.mgrid[0:CH, 0:CW]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    img += (np.exp(-d * 2.2) * k)[..., None] * np.array(c, np.float32)


def radio_dial(img, cam, mode, t):
    """Шкала радио на фоне: x 35–45, y 112–121 (координаты фона)."""
    x0, x1 = 35 - cam, 46 - cam
    if x1 <= 0:
        return
    sl = img[112:122, max(0, x0):max(0, x1)]
    warm = (sl[..., 0] > sl[..., 2] + 30)
    if mode == "off":
        sl[warm] *= 0.35
    elif mode in ("flicker", "static"):
        k = 0.75 + 0.25 * math.sin(t * 23) * math.sin(t * 7) if mode == "flicker" else (0.4 if int(t * 12) % 3 == 0 else 1.0)
        sl[warm] *= k


def door_strip(img, cam, t):
    """Полоска света под дверью коридора (x 56–104, y 165) и тени ног после «Эй!»."""
    y = 165
    xs = np.arange(56, 105) - cam
    xs = xs[(xs >= 0) & (xs < CW)]
    col = C_RED if t >= T["T_IKNOW"] else C_HI
    img[y, xs] = col
    if t >= T["T_FRIEND"] - 0.2:
        for fx in (70, 86):
            for x in range(fx, fx + 6):
                if 0 <= x - cam < CW:
                    img[y, x - cam] = C_DARK
    glow(img, 80 - cam, y, 18, (1.0, 0.7, 0.4) if t < T["T_IKNOW"] else (1.0, 0.3, 0.25), 45)


def phone(img, cam, t):
    px, py = 96 - cam, FLOOR["radio"] - 2
    if T["T_VIBR"] <= t < T["T_SCREEN"] and int(t * 30) % 2:
        px += 1
    on, red = t >= T["T_VIBR"], t >= T["T_DONT"]
    img[py:py + 2, px:px + 7] = C_DARK
    img[py, px + 1:px + 6] = C_RED if red else (C_TEXT if on else C_DARK)
    if on:
        glow(img, px + 3, py, 22, (1.0, 0.35, 0.3) if red else (0.75, 0.9, 0.85), 85)


def static_fx(img, i):
    rng = np.random.default_rng(i)
    m = rng.random((CH, CW)) < 0.07
    m[: CH // 3] = False
    img[m] = img[m] * 0.4 + np.array(C_TEXT) * 0.6


# ------------------------------------------------------------------ текст
_fonts = {}


def font(sz):
    if sz not in _fonts:
        _fonts[sz] = ImageFont.truetype(FONT, sz)
    return _fonts[sz]


class PixelText:
    def __init__(self, art):
        self.art = art
        self.d = ImageDraw.Draw(Image.new("1", (CW, CH)))
        self.d.fontmode = "1"

    def width(self, s, sz):
        return self.d.textlength(s, font=font(sz))

    def put(self, x, y, s, sz, fill):
        m = Image.new("1", (CW, CH), 0)
        dd = ImageDraw.Draw(m); dd.fontmode = "1"
        dd.text((int(x), int(y)), s, font=font(sz), fill=1)
        g = np.asarray(m, bool)
        o = g.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                o |= np.roll(np.roll(g, dy, 0), dx, 1)
        self.art[o & ~g] = C_DARK
        self.art[g] = fill

    def center(self, y, s, sz, fill):
        self.put((CW - self.width(s, sz)) // 2, y, s, sz, fill)


def captions(art, t):
    pt = PixelText(art)
    for i, p in enumerate(ep.PAGES):
        end = p[-1]["e"] + 0.25
        if i + 1 < len(ep.PAGES):
            end = min(end, ep.PAGES[i + 1][0]["s"])
        if not (p[0]["s"] - 0.05 <= t < end):
            continue
        quote = ep.LINES[p[0]["line"]]["text"].startswith("«")
        words = [w["w"] for w in p]
        sz = 9
        while sz > 7 and pt.width(" ".join(words), sz) > CW - 6:
            sz -= 1
        x = (CW - pt.width(" ".join(words), sz)) // 2
        for w in p:
            active = w["s"] - 0.03 <= t < w["e"]
            pt.put(x, 176, w["w"], sz, C_HI if active else (C_RED if quote else C_TEXT))
            x += pt.width(w["w"] + " ", sz)
        return


# ------------------------------------------------------------------ кадр
def shot_at(t):
    for s in SHOTS:
        if s[0] <= t < s[1]:
            return s
    return SHOTS[-1]


def blit(img, fr, feet, cx_canvas, wx, wy, cam, flip, dark):
    a = fr[..., 3] >= 128
    rgb = fr[..., :3].astype(np.float32)
    if flip:
        a, rgb = a[:, ::-1], rgb[:, ::-1]
        cx_canvas = fr.shape[1] - cx_canvas
    ys, xs = np.nonzero(a)
    X = xs + int(wx) - cx_canvas - cam
    Y = ys + int(wy) - feet
    ok = (X >= 0) & (X < CW) & (Y >= 0) & (Y < CH)
    img[Y[ok], X[ok]] = rgb[ys[ok], xs[ok]] * (1 - dark)


def render(i):
    t = i / FPS
    t0, t1, name, c0, c1, actors, o = shot_at(t)
    if o.get("endcard"):
        art = np.zeros((CH, CW, 3), np.uint8) + np.array(C_DARK, np.uint8)
        pt = PixelText(art)
        lt = t - t0
        if lt > 0.2:
            pt.center(64, "72 ЧАСА", 18, C_RED)
        if lt > 0.8:
            pt.center(92, "СЕРИЯ 2", 10, C_TEXT)
            pt.center(106, "ЧУЖИЕ У ДВЕРИ", 9, C_HI)
        if lt > 1.6 and int(t * 2) % 2:
            pt.center(140, "ПОДПИШИСЬ", 9, C_TEXT)
        return np.asarray(Image.fromarray(art).resize((CW * SC, CH * SC), Image.NEAREST)).tobytes()

    k = (t - t0) / max(1e-6, t1 - t0)
    if "pan_from" in o:
        k = (t - o["pan_from"]) / max(1e-6, t1 - o["pan_from"])
    cam = int(round(c0 + (c1 - c0) * ease(k)))
    if o.get("knock"):
        for kt in KNOCKS:
            if 0 <= t - kt < 0.16:
                cam += int(2 * math.sin((t - kt) * 90))
    if o.get("creak") and 0 <= t - (T["T_CREAK"] + 0.5) < 0.5:
        cam += int(round(math.sin(t * 60)))
    if o.get("static"):
        cam += int(np.random.default_rng(i).integers(-1, 2))
    cam = max(0, min(160 - CW, cam))
    img = bg(name)[:, cam:cam + CW].copy()
    changed = False
    if o.get("radio") and name == "radio":
        radio_dial(img, cam, o["radio"], t); changed = True
    if o.get("door") and name == "corridor":
        door_strip(img, cam, t); changed = True
    for a in actors:
        if a["t_from"] is not None and t < a["t_from"]:
            continue
        spr = sprite(*a["spr"])
        fr, feet, cxc = spr
        f = fr[int((t - t0) * a["fps"]) % len(fr)]
        wx = a["x0"] + (a["x1"] - a["x0"]) * min(1.0, max(0.0, (t - t0) / max(1e-6, t1 - t0)))
        wy = a["feet"] if a["feet"] is not None else FLOOR[name]
        blit(img, f, feet, cxc, wx, wy, cam, a["flip"], a["dark"])
    if o.get("phone"):
        phone(img, cam, t); changed = True
    if o.get("static"):
        static_fx(img, i); changed = True
    if o.get("fx"):
        particles(img, t, o["fx"])
    b = 1.0
    if o.get("fade_in"):
        b *= ease((t - t0) / o["fade_in"])
    if o.get("fade_out"):
        b *= ease((t1 - t) / o["fade_out"])
    if o.get("rule"):
        b *= 0.4
    if o.get("dim"):
        b *= o["dim"]
    if o.get("dim_after") and t >= o["dim_after"][0]:
        b *= 1 - (1 - o["dim_after"][1]) * ease((t - o["dim_after"][0]) / 0.8)
    if b != 1.0:
        img *= b; changed = True
    art = quantize(img, dither=12 if changed else 0)
    pt = PixelText(art)
    if o.get("rule"):
        lt = t - t0
        pt.center(70 - int(10 * (1 - ease(lt / 0.2))), o["rule"], 13, C_HI)
    else:
        if o.get("title") and 0.4 <= t < t1 - 0.2:
            pt.center(14, "72 ЧАСА", 18, C_RED)
            pt.center(38, "СЕРИЯ 1", 9, C_TEXT)
        captions(art, t)
    return np.asarray(Image.fromarray(art).resize((CW * SC, CH * SC), Image.NEAREST)).tobytes()


def main():
    wav = OUT + ".wav"
    print("Звук…", flush=True)
    ep.make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW * SC}x{CH * SC}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    lut()
    with Pool(os.cpu_count()) as pool:
        for j, fr in enumerate(pool.imap(render, range(NFR), chunksize=15)):
            p.stdin.write(fr)
            if j % 600 == 0:
                print(f"  {j}/{NFR}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
