#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 «Заперт» — сборка черновой версии видео (концепт).

python3 ep1_build.py  →  zapertyy_ep1.mp4 (1080×1920, 24 к/с)

Картинка: фоны и Денис из PixelLab (art/src), кадр 108×192 арт-пикселей ×10, субтитры — слой с пикселем 5×5.
Звук: озвучка ElevenLabs (voice/ep1, см. ep1_lines.py) + синтезированные шумы (удары, капли, шаги, гул).
Таймлайн строится от реальной длины фраз.
"""
import functools
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "art"))
import frames_ep1 as fe  # noqa: E402
from ep1_lines import LINES, path as vpath  # noqa: E402

OUT = os.path.join(HERE, "zapertyy_ep1.mp4")
FPS, SR = 24, 44100
CW, CH, TOP, BAND, UI = fe.CW, fe.CH, fe.TOP, fe.BAND, fe.UI
SRC = fe.SRC
VIEW_H = CH - BAND


# ------------------------------------------------------------------ звук
def load_audio(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


DUR = {i: len(load_audio(vpath(i))) / SR for i, *_ in LINES}
TEXT = {i: t for i, _, t, _ in LINES}
rng = np.random.default_rng(3)


def env(n, a=0.002, d=0.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def sfx_bang():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n) * env(n, 0.001, 0.03) * 0.8
    s += np.sin(2 * np.pi * 58 * t) * env(n, 0.002, 0.25) * 0.9
    for f, a in ((211, 0.25), (347, 0.18), (523, 0.12), (811, 0.06)):
        s += np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.5) * a
    return s * 0.7


def sfx_drip():
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    f = 1400 * np.exp(-t * 9) + 500
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.05) * 0.35
    return reverb(s, 0.4, 0.25)


def sfx_step():
    n = int(SR * 0.09)
    s = rng.normal(0, 1, n) * env(n, 0.002, 0.018)
    s = np.convolve(s, np.ones(12) / 12, "same")
    return s * 0.5


def sfx_creak():
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    f = 330 + 120 * np.sin(2 * np.pi * 1.3 * t) + rng.normal(0, 25, n).cumsum() * 0.002
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.05 * np.sin(np.pi * t / t[-1])
    return np.convolve(s, np.ones(6) / 6, "same")


def reverb(s, length=0.8, mix=0.35):
    n = int(SR * length)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR / (length / 4))
    ir /= np.abs(ir).sum() / 8
    wet = np.convolve(s, ir)
    out = np.zeros(len(wet))
    out[: len(s)] += s * (1 - mix)
    out += wet * mix
    return out


def echo(s, taps=((0.28, 0.45), (0.6, 0.28), (1.0, 0.15), (1.5, 0.07))):
    out = np.zeros(len(s) + int(SR * 1.8))
    out[: len(s)] += s
    for d, a in taps:
        k = int(SR * d)
        out[k:k + len(s)] += s * a
    return out


# ------------------------------------------------------------------ таймлайн
class TL:
    def __init__(self):
        self.t = 0.0
        self.voice = []      # (t, id)
        self.sfx = []        # (t, name)
        self.scenes = []     # (t0, t1, name, extra)
        self.titles = []     # (t0, t1, text, y)

    def say(self, i, gap_after=0.55):
        self.voice.append((self.t, i))
        self.t += DUR[i] + gap_after

    def wait(self, s):
        self.t += s


tl = TL()
cur = {}


def scene(name, **kw):
    if tl.scenes:
        t0, _, n, k = tl.scenes[-1]
        tl.scenes[-1] = (t0, tl.t, n, k)
    tl.scenes.append((tl.t, None, name, kw))


# Зацепка
scene("black")
for k in range(3):
    tl.sfx.append((0.2 + k * 0.7, "bang"))
tl.wait(2.3)
tl.say("00", 0.5)
tl.titles.append((tl.t, tl.t + 2.0, "ЗАПЕРТЫЙ", 150))
tl.titles.append((tl.t + 0.4, tl.t + 2.0, "СЕРИЯ 1", 175))
tl.wait(2.3)
# Очнулся
scene("wake")
tl.sfx.append((tl.t, "ring"))
T_WAKE = tl.t
tl.titles.append((tl.t + 1.0, tl.t + 4.5, "ДЕНЬ 1", 12))
tl.wait(0.9)
tl.say("01", 0.6)
tl.say("02", 0.5)
# Встал
scene("stand")
tl.wait(0.5)
tl.say("03")
tl.say("04")
tl.say("05", 0.5)
tl.sfx.append((tl.t, "drip"))
tl.wait(0.35)
tl.say("06", 0.2)
tl.sfx.append((tl.t, "drip"))
tl.wait(0.7)
# Окно
scene("window")
tl.wait(0.5)
tl.say("07")
tl.say("08", 0.4)
scene("street")
tl.wait(0.4)
tl.say("09", 0.6)
# Коридор
scene("corridor")
T_CORR = tl.t
tl.sfx.append((tl.t, "creak"))
tl.wait(0.5)
tl.say("10")
tl.say("11", 0.5)
T_SHOUT = tl.t
tl.say("12", 1.3)
tl.say("13", 0.5)
# Лестница
scene("stairs")
T_STAIRS = tl.t
tl.wait(0.6)
tl.say("14", 0.5)
# Дверь
scene("door")
T_DOOR = tl.t
tl.wait(0.5)
tl.say("15", 0.3)
T_HITS = tl.t
for k, dt in enumerate((0.0, 0.55, 1.05, 1.75, 2.3, 2.75)):
    tl.sfx.append((T_HITS + dt, "bang"))
tl.wait(0.4)
tl.say("16", 0.5)
scene("crack")
tl.wait(0.4)
tl.say("17", 0.6)
scene("end")
T_END = tl.t
tl.wait(0.4)
tl.say("18", 1.0)
tl.say("19", 0.6)
tl.titles.append((tl.t, tl.t + 2.6, "ПОПЫТКА №1: ДВЕРЬ — ПРОВАЛ", 150))
tl.wait(2.6)
tl.titles.append((tl.t, tl.t + 3.2, "ЧТО БЫ ВЫ СДЕЛАЛИ ПЕРВЫМ?", 150))
tl.wait(3.2)
scene("_")
TOTAL = tl.t
SCENES = tl.scenes[:-1]
WALKS = {  # сцена: (начало, конец, x от, x до, линия ступней в координатах фона)
    "corridor": (T_CORR + 0.3, T_CORR + 2.3, -12, 52, 158),
    "stairs": (T_STAIRS + 0.1, T_STAIRS + 1.6, 4, 52, 177),
    "door": (T_DOOR + 0.1, T_DOOR + 1.3, 6, 50, 184),
}


# ------------------------------------------------------------------ картинка
@functools.lru_cache(None)
def bg_full(name):
    im = np.asarray(Image.open(os.path.join(SRC, f"bg_{name}.png")).convert("RGB")).copy()
    if name == "room":                                     # решётка на окне (прутья снаружи стекла)
        dark, hi = fe.pal((38, 38, 42)), fe.pal((120, 120, 124))
        for x in range(90, 137, 8):
            im[60:111, x] = hi
            im[60:111, x + 1] = dark
        im[84, 88:138] = dark
    return im


def view(name, cam, dy=0, dx=0):
    im = bg_full(name)
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = fe.C_DARK
    c = int(np.clip(round(cam + dx), 0, im.shape[1] - CW))
    y0 = int(np.clip(TOP + dy, 0, im.shape[0] - VIEW_H))
    art[:VIEW_H] = im[y0:y0 + VIEW_H, c:c + CW]
    return art


@functools.lru_cache(None)
def spr(kind):
    if kind == "lying":
        return np.asarray(fe.lying())
    if kind.startswith("walk"):
        k = int(kind[4:])
        return np.asarray(Image.open(os.path.join(SRC, "denis_final",
                                                  f"Idle__animations__walking__east__frame_{k:03d}.png")).convert("RGBA"))
    return np.asarray(fe.sprite(kind))


def blit(art, a, cx, feet, anchor=None):
    m = a[..., 3] > 127
    ys, xs = np.nonzero(m)
    ax = anchor if anchor is not None else (xs.min() + xs.max()) // 2
    x0, y0 = int(cx) - ax, int(feet) - ys.max()
    X, Y = xs + x0, ys + y0
    ok = (X >= 0) & (X < CW) & (Y >= 0) & (Y < VIEW_H)
    art[Y[ok], X[ok]] = a[ys[ok], xs[ok], :3]


def hero_walk(art, t, w, face_after="east"):
    t0, t1, xa, xb, feet = w
    if t < t0:
        return
    if t < t1:
        u = (t - t0) / (t1 - t0)
        blit(art, spr(f"walk{int((t - t0) * 10) % 8}"), xa + (xb - xa) * u, feet - TOP, anchor=47)
    else:
        blit(art, spr(face_after), xb, feet - TOP)


def crack_art(t):
    """Крупный план: щель у петель, снаружи поперёк двери приварена полоса железа."""
    P = fe.pal
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = fe.C_DARK
    door, door2, light = P((52, 56, 58)), P((70, 74, 76)), P((236, 226, 196))
    rust, rust2, bead = P((120, 62, 40)), P((84, 44, 34)), P((170, 160, 150))
    art[:VIEW_H, :50] = door
    art[:VIEW_H, 60:] = door2
    art[:VIEW_H, 50:60] = P((14, 12, 16))
    art[:VIEW_H, 54:56] = light                         # дневной свет в щели
    for y in range(10, VIEW_H, 34):                     # заклёпки/фактура двери
        art[y:y + 2, 20:22] = door2
        art[y + 12:y + 14, 80:82] = door
    yb = 70
    art[yb:yb + 16, 40:72] = rust                       # полоса железа поперёк щели
    art[yb + 13:yb + 16, 40:72] = rust2
    for x in range(41, 71, 3):                          # сварной шов
        art[yb - 2:yb, x:x + 2] = bead
        art[yb + 16:yb + 18, x + 1:x + 3] = bead
    if int(t * 3) % 2 == 0:                             # дрожащий блик в щели
        art[20:24, 54:56] = P((255, 244, 214))
    return art


def frame_art(t):
    for t0, t1, name, _ in SCENES:
        if t0 <= t < t1:
            break
    lt = t - t0
    if name == "black":
        return np.full((CH, CW, 3), fe.C_DARK, np.uint8), name, lt
    if name == "wake":
        art = view("room", 0)
        blit(art, spr("lying"), 40, 178 - TOP)
        k = max(0.0, 1 - lt / 2.2)                          # веки открываются
        if k > 0:
            h = int(VIEW_H / 2 * k ** 0.6)
            art[:h] = fe.C_DARK
            art[VIEW_H - h:VIEW_H] = fe.C_DARK
        return art, name, lt
    if name == "stand":
        cam = min(20, lt * 0.6)
        art = view("room", cam)
        blit(art, spr("south-east"), 44 - cam, 178 - TOP - (1 if int(lt / 0.7) % 2 else 0))
        return art, name, lt
    if name == "window":
        art = view("room", 52)
        blit(art, spr("north"), 62, 170 - TOP)
        return art, name, lt
    if name == "street":
        return view("window", 14 + lt * 3.2, dy=-int(min(lt, 8) * 1.5)), name, lt
    if name == "corridor":
        sh = 0
        if T_SHOUT <= t < T_SHOUT + 1.0:
            sh = rng.integers(-1, 2)
        art = view("corridor", 26, dx=sh)
        hero_walk(art, t, WALKS["corridor"], "south-west")
        return art, name, lt
    if name == "stairs":
        art = view("stairs", 40)
        fe_txt(art)
        hero_walk(art, t, WALKS["stairs"])
        return art, name, lt
    if name == "door":
        dx, push = 0, 0
        for d in (0.0, 0.55, 1.05, 1.75, 2.3, 2.75):
            if 0 <= t - (T_HITS + d) < 0.12:
                dx, push = rng.integers(-2, 3), 3
        art = view("entrance_wide", 52, dx=dx)
        if t >= T_HITS:
            blit(art, spr("east"), 50 + push, 184 - TOP)
        else:
            hero_walk(art, t, WALKS["door"])
        return art, name, lt
    if name == "crack":
        return crack_art(t), name, lt
    if name == "end":
        art = view("entrance_wide", 52)
        blit(art, spr("west"), 46, 184 - TOP)
        k = min(1.0, lt / 9.0) * 0.65                     # медленно темнеет
        art[:VIEW_H] = (art[:VIEW_H] * (1 - k) + np.array(fe.C_DARK) * k).astype(np.uint8)
        return art, name, lt
    return np.full((CH, CW, 3), fe.C_DARK, np.uint8), name, lt


def fe_txt(art):
    txt, y = "К АВТОБУСАМ", 52 - TOP
    fe.put_text(art, txt, y, 9, fe.C_RED, outline=False)
    cx = CW // 2
    for k in range(7):
        art[y + 13 + k, cx - 1:cx + 1] = fe.C_RED
    for k in range(4):
        art[y + 17 + k, cx - 4 + k:cx + 4 - k] = fe.C_RED


# ------------------------------------------------------------------ субтитры
def chunks(text, limit=46):
    parts, cur = [], ""
    for w in text.split():
        cur = (cur + " " + w).strip()
        if (cur[-1] in ".?!…:" and len(cur) > 20) or (cur[-1] == "," and len(cur) > 30) or len(cur) > limit:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    merged = []
    for p in parts:
        if merged and len(merged[-1]) + len(p) < limit:
            merged[-1] += " " + p
        else:
            merged.append(p)
    return merged


SUBS = []
for t0, i in tl.voice:
    cs = chunks(TEXT[i])
    total = sum(len(c) for c in cs)
    t = t0
    for c in cs:
        d = DUR[i] * len(c) / total
        SUBS.append((t, t + d + 0.15, c))
        t += d


@functools.lru_cache(512)
def ui_layer(sub, titles):
    ui = np.zeros((CH * UI, CW * UI, 4), np.uint8)
    if sub:
        fe.subtitle(ui, sub)
    for text, y in titles:
        for k, ln in enumerate(fe.wrap(text, 15, width=CW * UI - 16)):
            fe.ui_text(ui, ln, y + k * 19, 15, fe.C_HI)
    return ui


def render_frame(t):
    art, name, lt = frame_art(t)
    sub = next((s for a, b, s in SUBS if a <= t < b), "")
    titles = tuple((x, y) for a, b, x, y in tl.titles if a <= t < b)
    ui = ui_layer(sub, titles)
    big = art.repeat(UI, 0).repeat(UI, 1)
    m = ui[..., 3] > 0
    big[m] = ui[..., :3][m]
    if t > TOTAL - 0.6:                                     # затемнение в конце
        big = (big * max(0.0, (TOTAL - t) / 0.6)).astype(np.uint8)
    return big


# ------------------------------------------------------------------ сборка
def build_audio(path):
    n = int(SR * (TOTAL + 1))
    mix = np.zeros(n)
    t = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.35 * t) + 0.4 * np.sin(2 * np.pi * 82.4 * t))
    drone *= 0.035 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t))
    drone *= np.clip(t / 6, 0, 1)
    tone = np.convolve(rng.normal(0, 1, n), np.ones(400) / 400, "same") * 0.06
    mix += drone + tone
    for t0, i in tl.voice:
        v = load_audio(vpath(i))
        if i == "12":
            v = echo(v)
        elif i in ("13", "14", "15", "16", "17"):
            v = reverb(v, 0.5, 0.12)
        k = int(t0 * SR)
        mix[k:k + len(v)] += v[: n - k] * 1.0
    S = {"bang": reverb(sfx_bang(), 1.0, 0.3), "drip": sfx_drip(), "creak": sfx_creak()}
    for t0, s in tl.sfx:
        if s == "ring":
            k = int(t0 * SR)
            m = int(SR * 5)
            tt = np.arange(m) / SR
            mix[k:k + m] += np.sin(2 * np.pi * 5800 * tt) * 0.015 * np.exp(-tt / 2.0)
            continue
        a = S[s]
        k = int(t0 * SR)
        mix[k:k + len(a)] += a[: n - k]
    for w in WALKS.values():                                 # шаги
        tt = w[0]
        while tt < w[1]:
            k = int(tt * SR)
            a = sfx_step()
            mix[k:k + len(a)] += a
            tt += 0.4
    mix /= max(1e-6, np.abs(mix).max()) / 0.9
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=mix.astype(np.float32).tobytes(), check=True)


def main():
    wav = OUT + ".wav"
    build_audio(wav)
    nf = int(TOTAL * FPS)
    print(f"длительность {TOTAL:.1f} с, кадров {nf}", flush=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW * UI}x{CH * UI}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=neighbor",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(nf):
        p.stdin.write(render_frame(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
