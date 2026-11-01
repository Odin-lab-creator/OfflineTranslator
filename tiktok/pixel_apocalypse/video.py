#!/usr/bin/env python3
"""PIXEL APOCALYPSE — серия 1 «72 ЧАСА» в пиксельном стиле, под озвучку tiktok/series/voice.mp3.

cd tiktok/pixel_apocalypse && python3 video.py [выход.mp4]

Каждый кадр видео проходит тот же конвейер, что и стоп-кадры (STYLE_LOCK.md):
освещённая сцена → «камера» 180x320 (сдвиги только на целые арт-пиксели) → эффекты →
виньетка/яркость → Bayer-дизеринг → палитра → x6 nearest = 1080x1920.
Субтитры — пиксельный шрифт на той же сетке 6x6. Звук — дорожка серии 1 (голос + музыка + SFX).
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "series"))
_argv = sys.argv[:]
sys.argv = sys.argv[:1]
import episode1 as ep  # noqa: E402  (тайминги слов и звуковая дорожка)
sys.argv = _argv

from pixel2 import CH, CW, PAL, PALETTE, col, finalize  # noqa: E402
import test_frames2 as f2  # noqa: E402
import test_frames3 as f3  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pixel_apocalypse_ep1.mp4")
FPS = 30
DUR = ep.DUR
NFR = int(DUR * FPS)
SCALE = 1080 // CW
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def C(name):
    return tuple(int(PALETTE[name][i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ сцены
def _radio_off():
    s = f2.frame_radio()
    s.rect(114, 344, 129, 350, "G3"); s.emis[344:351, 114:130] = False
    s.lights = [l for l in s.lights if not (l[0] == 121 and l[1] == 347)]
    return s


BUILD = {
    "wake": f2.frame_wake, "supplies": f2.frame_supplies, "door": f2.frame_door,
    "radio": f2.frame_radio, "radio_off": _radio_off,
    "window_empty": lambda: f2.frame_window(with_zombie=False), "window_zombie": f2.frame_window,
    "street": f3.frame_surface, "shop": f3.frame_shop, "checkpoint": f3.frame_checkpoint,
    "forest": f3.frame_forest, "night": f3.frame_night_road,
}
_cache = {}


def lit(name):
    if name not in _cache:
        _cache[name] = BUILD[name]().lit()
    return _cache[name]


# ------------------------------------------------------------- раскадровка
T = {k: getattr(ep, k) for k in dir(ep) if k.startswith("T_")}
KNOCKS = [T["T_KNOCK"] + 0.1, T["T_KNOCK"] + 0.35, T["T_KNOCK"] + 0.6,
          T["T_THREE"] + 0.75, T["T_THREE"] + 1.05, T["T_THREE"] + 1.35]
END = ep.VOICE_END - 0.2
T_SUDDEN = ep.line_t("И вдруг")

# (начало, конец, сцена, камера от, камера до, параметры)
SHOTS = [
    (0.0, 4.6, "wake", (84, 56), (84, 96), dict(fx="dust", fade_in=1.0, title=("72 ЧАСА", "СЕРИЯ 1"))),
    (4.6, 6.1, "street", (24, 110), (40, 110), dict(fx="ash")),
    (6.1, 7.7, "shop", (40, 110), (54, 110), dict(fx="dust")),
    (7.7, 9.4, "checkpoint", (30, 110), (48, 110), dict(fx="ash")),
    (9.4, 13.8, "forest", (60, 40), (45, 110), dict(fx="dust")),
    (13.8, 17.0, "night", (64, 110), (84, 110), dict(fx="embers")),
    (17.0, T["T_ITEMS"] - 2.1, "supplies", (34, 96), (34, 96), dict(rule="ПРАВИЛО №1", fx="dust")),
    (T["T_ITEMS"] - 2.1, T["T_PHONE"], "supplies", (14, 96), (66, 100), dict(fx="dust")),
    (T["T_PHONE"], T["T_WATER"], "supplies", (66, 100), (84, 100), dict(fx="dust")),
    (T["T_WATER"], T["T_TRUST"], "supplies", (22, 112), (28, 108), dict(fx="dust")),
    (T["T_TRUST"], T["T_KNOCK"] - 0.1, "door", (12, 0), (12, 96), dict(fx="dust")),
    (T["T_KNOCK"] - 0.1, T_SUDDEN, "door", (12, 100), (16, 100), dict(knock=True)),
    (T_SUDDEN, T["T_RULE2"], "door", (16, 100), (44, 104), dict(knock=True, dim_after=(T["T_IKNOW"], 0.72))),
    (T["T_RULE2"], ep.line_t("Не теряй"), "door", (30, 100), (30, 100), dict(rule="ПРАВИЛО №2")),
    (ep.line_t("Не теряй"), T["T_NIGHT"], "door", (44, 92), (24, 100), dict(fx="dust", fade_out=0.4)),
    (T["T_NIGHT"], T["T_MSG1"], "radio", (40, 20), (28, 100), dict(fx="dust", fade_in=0.4)),
    (T["T_MSG1"], T["T_LOST"], "radio", (28, 100), (44, 104), dict(fx="dust", flicker=0.02)),
    (T["T_LOST"], T["T_MSG2"], "radio", (44, 104), (44, 104), dict(static=True)),
    (T["T_MSG2"], T["T_RULE3"], "radio", (44, 104), (30, 100), dict(fx="dust", flicker=0.02)),
    (T["T_RULE3"], ep.line_t("Проверяй"), "radio", (30, 100), (30, 100), dict(rule="ПРАВИЛО №3")),
    (ep.line_t("Проверяй"), T["T_OFF"], "checkpoint", (64, 110), (30, 110), dict(fx="ash")),
    (T["T_OFF"], T["T_OFF"] + 0.45, "radio", (30, 100), (30, 100), dict()),
    (T["T_OFF"] + 0.45, T["T_EYES"], "radio_off", (30, 100), (44, 116), dict(phone=True)),
    (T["T_EYES"], T["T_CREAK"], "window_empty", (90, 96), (84, 92), dict(fx="dust")),
    (T["T_CREAK"], T["T_WORST"], "window_zombie", (84, 92), (8, 96), dict(creak=True, pan_from=T["T_CREAK"] + 0.6)),
    (T["T_WORST"], T["T_LAST"], "night", (90, 110), (62, 110), dict(fx="embers")),
    (T["T_LAST"], END, "window_zombie", (0, 104), (0, 116), dict(dim=0.85)),
    (END, DUR, None, None, None, dict(endcard=True)),
]


def ease(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


# ------------------------------------------------------------- эффекты
def particles(view, t, kind, cam):
    h, w = view.shape[:2]
    rng = np.random.default_rng(7)
    if kind == "ash":
        P = rng.random((70, 3))
        for x0, y0, sp in P:
            y = int((y0 * h + t * (14 + sp * 18)) % h)
            x = int((x0 * w + t * 6 + 3 * math.sin(t * 1.3 + x0 * 9)) % w)
            view[y, x] = col("E0") if sp > 0.5 else col("G6")
    elif kind == "dust":
        P = rng.random((26, 3))
        for x0, y0, sp in P:
            y = int((y0 * h + t * (3 + sp * 4)) % h)
            x = int((x0 * w + 4 * math.sin(t * 0.7 + y0 * 11)) % w)
            view[y, x] = view[y, x] * 0.4 + col("E1") * 0.6
    elif kind == "embers":
        P = rng.random((34, 3))
        for x0, y0, sp in P:
            y = int((y0 * h - t * (10 + sp * 16)) % h)
            x = int((x0 * w * 0.6 + w * 0.3 + 5 * math.sin(t * 2 + x0 * 7)) % w)
            if (int(t * 10) + int(x0 * 50)) % 5:
                view[y, x] = col("O2") if sp > 0.4 else col("O1")


def glow(view, cx, cy, r, c, k):
    h, w = view.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    view += (np.exp(-d * 2.2) * k)[..., None] * np.array(c, np.float32)[None, None]


def phone(view, t, cam):
    """Телефон на полу рядом с героем: вибрирует, экран светится, затем краснеет."""
    px, py = 96 - cam[0], 390 - cam[1]
    vib = T["T_VIBR"] <= t < T["T_SCREEN"]
    if vib and int(t * 30) % 2:
        px += 1
    on = t >= T["T_VIBR"]
    red = t >= T["T_DONT"]
    view[py:py + 5, px:px + 14] = col("G0")
    view[py + 1:py + 4, px + 1:px + 13] = col("R4" if red else ("E2" if on else "G2"))
    view[py + 1, px + 2:px + 12] = col("R5" if red else ("O4" if on else "G3"))
    if on:
        glow(view, px + 7, py + 1, 34, (1.0, 0.4, 0.3) if red else (0.75, 0.9, 0.85), 95 if red else 80)


def static(view, t):
    rng = np.random.default_rng(int(t * 30))
    h, w = view.shape[:2]
    m = rng.random((h, w)) < 0.08
    m[:h // 3] = False
    view[m] = view[m] * 0.5 + col("E1") * 0.5
    sl = int(rng.integers(0, h - 6))
    view[sl:sl + 2] = np.roll(view[sl:sl + 2], int(rng.integers(-4, 5)), axis=1)


# ------------------------------------------------------------- текст
_fonts = {}


def font(sz):
    if sz not in _fonts:
        _fonts[sz] = ImageFont.truetype(FONT, sz)
    return _fonts[sz]


class PixelText:
    """Пиксельный текст на арт-сетке: глифы без сглаживания + контур 1 px из палитры (G0)."""

    def __init__(self, art):
        self.art = art
        self._m = Image.new("1", (CW, CH), 0)
        self.d = ImageDraw.Draw(self._m)
        self.d.fontmode = "1"

    def width(self, s, sz):
        return self.d.textlength(s, font=font(sz))

    def put(self, x, y, s, sz, fill):
        m = Image.new("1", (CW, CH), 0)
        dd = ImageDraw.Draw(m); dd.fontmode = "1"
        dd.text((int(x), int(y)), s, font=font(sz), fill=1)
        g = np.asarray(m, bool)
        o = g.copy()
        o[1:] |= g[:-1]; o[:-1] |= g[1:]; o[:, 1:] |= g[:, :-1]; o[:, :-1] |= g[:, 1:]
        o[1:, 1:] |= g[:-1, :-1]; o[:-1, :-1] |= g[1:, 1:]; o[1:, :-1] |= g[:-1, 1:]; o[:-1, 1:] |= g[1:, :-1]
        self.art[o & ~g] = C("G0")
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
        sz = 11
        while sz > 8 and pt.width(" ".join(words), sz) > CW - 12:
            sz -= 1
        x = (CW - pt.width(" ".join(words), sz)) // 2
        for w in p:
            active = w["s"] - 0.03 <= t < w["e"]
            c = C("O3") if active else (C("R5") if quote else C("E2"))
            pt.put(x, 262, w["w"], sz, c)
            x += pt.width(w["w"] + " ", sz)
        return


# ------------------------------------------------------------- кадр
def shot_at(t):
    for s in SHOTS:
        if s[0] <= t < s[1]:
            return s
    return SHOTS[-1]


def render(i):
    t = i / FPS
    t0, t1, name, c0, c1, o = shot_at(t)
    if o.get("endcard"):
        k = ease((t - t0) / 0.6)
        art = np.zeros((CH, CW, 3), np.uint8) + np.array(C("G0"), np.uint8)
        pt = PixelText(art)
        if k > 0.3:
            pt.center(104, "72 ЧАСА", 26, C("R4"))
        if t - t0 > 0.8:
            pt.center(146, "СЕРИЯ 2", 14, C("E2"))
            pt.center(166, "ЧУЖИЕ У ДВЕРИ", 12, C("O3"))
        if t - t0 > 1.6 and int(t * 2) % 2:
            pt.center(230, "ПОДПИШИСЬ", 12, C("E1"))
        return np.asarray(Image.fromarray(art).resize((CW * SCALE, CH * SCALE), Image.NEAREST)).tobytes()

    k = (t - t0) / max(1e-6, t1 - t0)
    if "pan_from" in o:
        k = (t - o["pan_from"]) / max(1e-6, t1 - o["pan_from"])
    e = ease(k)
    cx = int(round(c0[0] + (c1[0] - c0[0]) * e))
    cy = int(round(c0[1] + (c1[1] - c0[1]) * e))
    # тряска на целые пиксели
    if o.get("knock"):
        for kt in KNOCKS:
            if 0 <= t - kt < 0.16:
                cx += int(2 * math.sin((t - kt) * 90)); cy += int(1 * math.cos((t - kt) * 70))
    if o.get("creak") and 0 <= t - (T["T_CREAK"] + 0.5) < 0.5:
        cx += int(round(math.sin(t * 60)))
    if o.get("static"):
        cx += int(np.random.default_rng(i).integers(-1, 2))
    cx = max(0, min(270 - CW, cx)); cy = max(0, min(480 - CH, cy))
    view = lit(name)[cy:cy + CH, cx:cx + CW].copy()
    if o.get("fx"):
        particles(view, t, o["fx"], (cx, cy))
    if o.get("phone"):
        phone(view, t, (cx, cy))
    if o.get("static"):
        static(view, t)
    b = 1.0
    if o.get("fade_in"):
        b *= ease((t - t0) / o["fade_in"])
    if o.get("fade_out"):
        b *= ease((t1 - t) / o["fade_out"])
    if o.get("flicker"):
        b *= 1 + o["flicker"] * math.sin(t * 37) * math.sin(t * 13)
    if o.get("rule"):
        b *= 0.38
    if o.get("dim"):
        b *= o["dim"]
    if o.get("dim_after") and t >= o["dim_after"][0]:
        b *= 1 - (1 - o["dim_after"][1]) * ease((t - o["dim_after"][0]) / 0.8)
    art = finalize(view, brightness=b, fast=True)
    pt = PixelText(art)
    if o.get("rule"):
        lt = t - t0
        pt.center(120 - int(14 * (1 - ease(lt / 0.2))), o["rule"], 20, C("O3"))
    else:
        if o.get("title") and 0.4 <= t < t1 - 0.2:
            pt.center(34, o["title"][0], 26, C("R4"))
            pt.center(66, o["title"][1], 11, C("E2"))
        captions(art, t)
    return np.asarray(Image.fromarray(art).resize((CW * SCALE, CH * SCALE), Image.NEAREST)).tobytes()


def main():
    wav = OUT + ".wav"
    print("Звук…", flush=True)
    ep.make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW * SCALE}x{CH * SCALE}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    only = os.environ.get("FRAMES")
    rng_ = range(NFR) if not only else range(*map(int, only.split(":")))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for j, fr in enumerate(pool.imap(render, rng_, chunksize=15)):
            p.stdin.write(fr)
            if j % 300 == 0:
                print(f"  {j}/{len(rng_)}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
