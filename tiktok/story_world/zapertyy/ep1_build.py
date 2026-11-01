#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 «Заперт» — сборка видео.

python3 ep1_build.py  →  zapertyy_ep1.mp4 (1080×1920, 24 к/с, около 2:00)

Картинка: фоны, крупные планы и анимации Дениса из PixelLab (art/src), кадр 108×192 арт-пикселей ×10,
субтитры и титры — слой с пикселем 5×5. Звук: озвучка ElevenLabs (voice/ep1, ускорена ×1.06)
+ синтезированные шумы. Таймлайн строится от реальной длины фраз.
"""
import functools
import glob
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
TEMPO = 1.06
CW, CH, TOP, BAND, UI = fe.CW, fe.CH, fe.TOP, fe.BAND, fe.UI
SRC = fe.SRC
VIEW_H = CH - BAND
rng = np.random.default_rng(3)


# ------------------------------------------------------------------ звук
def load_audio(p, tempo=1.0):
    af = ["-af", f"atempo={tempo}"] if tempo != 1.0 else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, *af, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


VOICE = {i: load_audio(vpath(i), TEMPO) for i, *_ in LINES}
DUR = {i: len(v) / SR for i, v in VOICE.items()}
TEXT = {i: t for i, _, t, _ in LINES}


def env(n, a=0.002, d=0.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


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


def sfx_bang():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n) * env(n, 0.001, 0.03) * 0.8
    s += np.sin(2 * np.pi * 58 * t) * env(n, 0.002, 0.25) * 0.9
    for f, a in ((211, 0.25), (347, 0.18), (523, 0.12), (811, 0.06)):
        s += np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.5) * a
    return reverb(s * 0.7, 1.0, 0.3)


def sfx_drip():
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    f = 1400 * np.exp(-t * 9) + 500
    return reverb(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.05) * 0.35, 0.4, 0.25)


def sfx_step():
    n = int(SR * 0.09)
    s = rng.normal(0, 1, n) * env(n, 0.002, 0.018)
    return np.convolve(s, np.ones(12) / 12, "same") * 0.5


def sfx_creak():
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    f = 330 + 120 * np.sin(2 * np.pi * 1.3 * t) + rng.normal(0, 25, n).cumsum() * 0.002
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.05 * np.sin(np.pi * t / t[-1])
    return np.convolve(s, np.ones(6) / 6, "same")


def sfx_rattle():
    n = int(SR * 0.25)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n) * env(n, 0.001, 0.04) * 0.4
    for f in (640, 910, 1330):
        s += np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.12) * 0.12
    return s


def sfx_whoosh():                                           # штора / резкое движение
    n = int(SR * 0.5)
    s = rng.normal(0, 1, n) * np.sin(np.pi * np.arange(n) / n) ** 2
    return np.convolve(s, np.ones(30) / 30, "same") * 0.25


def sfx_slide():                                            # спина по металлу
    n = int(SR * 1.6)
    s = rng.normal(0, 1, n) * np.sin(np.pi * np.arange(n) / n) * 0.12
    return np.convolve(s, np.ones(20) / 20, "same")


SFX = {"bang": sfx_bang(), "drip": sfx_drip(), "creak": sfx_creak(), "rattle": sfx_rattle(),
       "whoosh": sfx_whoosh(), "slide": sfx_slide(), "step": sfx_step()}


# ------------------------------------------------------------------ таймлайн
class TL:
    def __init__(self):
        self.t = 0.0
        self.voice, self.sfx, self.scenes, self.titles = [], [], [], []

    def say(self, i, gap=0.45):
        self.voice.append((self.t, i))
        t0 = self.t
        self.t += DUR[i] + gap
        return t0

    def wait(self, s):
        self.t += s

    def scene(self, name, **kw):
        if self.scenes:
            self.scenes[-1][1] = self.t
        self.scenes.append([self.t, None, name, kw])

    def fx(self, name, t=None):
        self.sfx.append((self.t if t is None else t, name))


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


def chunk_times(i, t0):
    cs = chunks(TEXT[i])
    total = sum(len(c) for c in cs)
    out, t = [], t0
    for c in cs:
        d = DUR[i] * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


tl = TL()
K = {}                                                      # ключевые моменты

# Зацепка: чёрный экран, удары
tl.scene("black")
for k in range(3):
    tl.fx("bang", 0.15 + k * 0.6)
tl.wait(1.9)
tl.say("00", 0.35)
tl.titles.append((tl.t, tl.t + 1.6, "ЗАПЕРТЫЙ", 150))
tl.titles.append((tl.t + 0.3, tl.t + 1.6, "СЕРИЯ 1", 175))
tl.wait(1.8)
# Очнулся
tl.scene("wake")
tl.fx("ring")
tl.titles.append((tl.t + 0.8, tl.t + 4.0, "ДЕНЬ 1", 12))
tl.wait(0.8)
tl.say("01", 0.5)
tl.say("02", 0.3)
# Встал, огляделся
tl.scene("stand")
tl.say("03", 0.4)
t04 = tl.say("04", 0.0)
c04 = chunk_times("04", t04)
tl.scenes[-1][1] = c04[1][0]
tl.scenes.append([c04[1][0], None, "cu_watch", {}])
tl.wait(0.4)
tl.scene("cu_pills")
tl.say("05", 0.35)
tl.scene("cu_tap")
tl.fx("drip")
tl.wait(0.3)
tl.say("06", 0.15)
tl.fx("drip")
tl.wait(0.6)
tl.fx("drip")
tl.wait(0.4)
# Окно
tl.scene("window")
tl.fx("whoosh", tl.t + 0.2)
tl.wait(0.4)
tl.say("07", 0.3)
tl.scene("cu_weld")
for k in range(6):
    tl.fx("rattle", tl.t + 0.1 + k * 0.32)
tl.say("08", 0.3)
tl.scene("street")
tl.wait(0.3)
tl.say("09", 0.5)
# Коридор
tl.scene("corridor")
K["corr"] = tl.t
tl.fx("creak")
tl.wait(0.4)
tl.say("10", 0.35)
tl.say("11", 0.4)
K["shout"] = tl.t
tl.say("12", 1.2)
tl.say("13", 0.4)
# Лестница
tl.scene("stairs")
K["stairs"] = tl.t
tl.wait(0.5)
tl.say("14", 0.4)
# Дверь
tl.scene("door")
K["door"] = tl.t
tl.wait(0.3)
tl.say("15", 0.2)
K["push"] = tl.t
for c in range(3):                                          # удар плечом и ногой в каждом цикле
    tl.fx("bang", K["push"] + c * 1.0 + 0.25)
    tl.fx("bang", K["push"] + c * 1.0 + 0.75)
tl.wait(0.3)
tl.say("16", 0.2)
tl.scene("crouch")
tl.wait(0.7)
tl.scene("cu_crack")
tl.say("17", 0.4)
# Финал
tl.scene("end")
tl.fx("slide", tl.t + 0.3)
tl.wait(0.3)
tl.say("18", 0.8)
tl.say("19", 0.5)
tl.titles.append((tl.t, tl.t + 2.3, "ПОПЫТКА №1: ДВЕРЬ — ПРОВАЛ", 140))
tl.wait(2.3)
tl.titles.append((tl.t, tl.t + 2.8, "ЧТО БЫ ВЫ СДЕЛАЛИ ПЕРВЫМ?", 140))
tl.wait(2.8)
tl.scene("_")
TOTAL = tl.t
SCENES = tl.scenes[:-1]

WALKS = {  # сцена: (начало, конец, x от, x до, линия ступней в координатах фона)
    "corridor": (K["corr"] + 0.3, K["corr"] + 2.3, -12, 52, 158),
    "stairs": (K["stairs"] + 0.1, K["stairs"] + 1.6, 4, 52, 177),
    "door": (K["door"] + 0.1, K["door"] + 1.2, 10, 50, 184),
}
for w in WALKS.values():
    tt = w[0]
    while tt < w[1]:
        tl.fx("step", tt)
        tt += 0.4


# ------------------------------------------------------------------ картинка
@functools.lru_cache(None)
def bg_full(name):
    im = np.asarray(Image.open(os.path.join(SRC, f"bg_{name}.png")).convert("RGB")).copy()
    if name == "room":                                      # решётка на окне (прутья снаружи стекла)
        dark, hi = fe.pal((38, 38, 42)), fe.pal((120, 120, 124))
        for x in range(90, 137, 8):
            im[60:111, x] = hi
            im[60:111, x + 1] = dark
        im[84, 88:138] = dark
    return im


def view(name, cam, dx=0, dy=0):
    im = bg_full(name)
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = fe.C_DARK
    c = int(np.clip(round(cam + dx), 0, im.shape[1] - CW))
    y0 = int(np.clip(TOP + dy, 0, im.shape[0] - VIEW_H))
    art[:VIEW_H] = im[y0:y0 + VIEW_H, c:c + CW]
    return art


@functools.lru_cache(None)
def closeup(name):
    im = np.asarray(Image.open(os.path.join(SRC, f"{name}.png")).convert("RGB"))
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = fe.C_DARK
    h = min(VIEW_H, im.shape[0])
    art[:h] = im[(im.shape[0] - h) // 2:(im.shape[0] - h) // 2 + h, :CW]
    return art


@functools.lru_cache(None)
def anim(name):
    fs = sorted(glob.glob(os.path.join(SRC, "denis_final", f"Idle__animations__{name}__frame_*.png")))
    return [np.asarray(Image.open(f).convert("RGBA")) for f in fs]


@functools.lru_cache(None)
def rot(view_):
    return np.asarray(fe.sprite(view_))


def blit(art, a, cx, feet, flip=False, canvas=True):
    """Анимации (холст 96): центр холста x=47, пол — строка 78. Повороты (холст 64): по рамке."""
    if flip:
        a = a[:, ::-1]
    m = a[..., 3] > 127
    ys, xs = np.nonzero(m)
    if canvas:
        ax, ay = (a.shape[1] - 1 - 47 if flip else 47), 78
    else:
        ax, ay = (xs.min() + xs.max()) // 2, ys.max()
    x0, y0 = int(round(cx)) - ax, int(round(feet)) - ay
    X, Y = xs + x0, ys + y0
    ok = (X >= 0) & (X < CW) & (Y >= 0) & (Y < VIEW_H)
    art[Y[ok], X[ok]] = a[ys[ok], xs[ok], :3]


def play(name, lt, fps=8, frames=None, loop=True):
    seq = frames if frames is not None else list(range(len(anim(name))))
    k = int(lt * fps)
    k = k % len(seq) if loop else min(k, len(seq) - 1)
    return anim(name)[seq[k]]


def idle(lt):
    return play("breathing_idle__east", lt, fps=2.5, frames=[1, 2, 3, 2])


def walk_or_stand(art, t, w, after=None):
    t0, t1, xa, xb, feet = w
    if t < t0:
        return
    if t < t1:
        u = (t - t0) / (t1 - t0)
        blit(art, play("walking__east", t - t0, fps=10), xa + (xb - xa) * u, feet - TOP)
    elif after is not None:
        blit(art, rot(after), xb, feet - TOP, canvas=False)
    else:
        blit(art, idle(t - t1), xb, feet - TOP)


def shake_at(t, times, dur=0.12, amp=2):
    for x in times:
        if 0 <= t - x < dur:
            return int(rng.integers(-amp, amp + 1))
    return 0


BANGS = [t for t, s in tl.sfx if s == "bang" and t > 10]
RATTLES = [t for t, s in tl.sfx if s == "rattle"]


def frame_art(t):
    for t0, t1, name, _ in SCENES:
        if t0 <= t < t1:
            break
    lt = t - t0
    dark = np.full((CH, CW, 3), fe.C_DARK, np.uint8)
    if name == "black":
        return dark
    if name.startswith("cu_"):
        art = closeup(name).copy()
        if name == "cu_weld":                                # рука трясёт прут
            dx = shake_at(t, RATTLES, 0.1, 1)
            if dx:
                art[:VIEW_H] = np.roll(art[:VIEW_H], dx, 1)
        return art
    if name == "wake":
        art = view("room", 0)
        blit(art, anim("getup__east")[2], 44, 178 - TOP)
        k = max(0.0, 1 - lt / 2.2)                           # веки открываются
        if k > 0:
            h = int(VIEW_H / 2 * k ** 0.6)
            art[:h] = fe.C_DARK
            art[VIEW_H - h:VIEW_H] = fe.C_DARK
        return art
    if name == "stand":
        cam = min(16, lt * 0.8)
        art = view("room", cam)
        if lt < 3.0:                                         # садится, держась за голову, встаёт
            a = play("getup__east", lt, fps=2.0, frames=[2, 3, 4, 5, 6, 7], loop=False)
        else:
            a = idle(lt)
        blit(art, a, 44 - cam, 178 - TOP)
        return art
    if name == "window":
        art = view("room", 52)
        if lt < 1.0:
            blit(art, rot("north"), 62, 170 - TOP, canvas=False)
        else:
            blit(art, play("bars__north", lt - 1.0, fps=8, frames=[1, 2, 3, 4, 5, 6, 7]), 62, 170 - TOP)
        return art
    if name == "street":
        return view("window", 14 + lt * 3.0, dy=-int(min(lt, 8) * 1.5))
    if name == "corridor":
        sh = int(rng.integers(-1, 2)) if K["shout"] <= t < K["shout"] + 1.0 else 0
        art = view("corridor", 26, dx=sh)
        walk_or_stand(art, t, WALKS["corridor"], after="south-west")
        return art
    if name == "stairs":
        art = view("stairs", 40)
        wall_text(art)
        walk_or_stand(art, t, WALKS["stairs"])
        return art
    if name == "door":
        art = view("entrance_wide", 52, dx=shake_at(t, BANGS))
        if t < K["push"]:
            walk_or_stand(art, t, WALKS["door"])
        elif t < K["push"] + 3.0:
            blit(art, play("push__east", t - K["push"], fps=8), 50, 184 - TOP)
        else:
            blit(art, idle(t - K["push"]), 50, 184 - TOP)
        return art
    if name == "crouch":
        art = view("entrance_wide", 52)
        blit(art, play("crouching__east", lt, fps=8, loop=False), 52, 184 - TOP, canvas=False)
        return art
    if name == "end":
        art = view("entrance_wide", 52)
        blit(art, play("slide__east", lt, fps=4, loop=False), 62, 184 - TOP, flip=True)
        k = min(1.0, lt / 8.0) * 0.65                        # медленно темнеет
        art[:VIEW_H] = (art[:VIEW_H] * (1 - k) + np.array(fe.C_DARK) * k).astype(np.uint8)
        return art
    return dark


def wall_text(art):
    txt, y = "К АВТОБУСАМ", 52 - TOP
    fe.put_text(art, txt, y, 9, fe.C_RED, outline=False)
    cx = CW // 2
    for k in range(7):
        art[y + 13 + k, cx - 1:cx + 1] = fe.C_RED
    for k in range(4):
        art[y + 17 + k, cx - 4 + k:cx + 4 - k] = fe.C_RED


# ------------------------------------------------------------------ субтитры и титры
SUBS = []
for t0, i in tl.voice:
    for a, b, c in chunk_times(i, t0):
        SUBS.append((a, b + 0.12, c))


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
    art = frame_art(t)
    sub = next((s for a, b, s in SUBS if a <= t < b), "")
    titles = tuple((x, y) for a, b, x, y in tl.titles if a <= t < b)
    ui = ui_layer(sub, titles)
    big = art.repeat(UI, 0).repeat(UI, 1)
    m = ui[..., 3] > 0
    big[m] = ui[..., :3][m]
    if t > TOTAL - 0.6:
        big = (big * max(0.0, (TOTAL - t) / 0.6)).astype(np.uint8)
    return big


# ------------------------------------------------------------------ сборка
def build_audio(path):
    n = int(SR * (TOTAL + 1))
    mix = np.zeros(n)
    t = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.35 * t) + 0.4 * np.sin(2 * np.pi * 82.4 * t))
    drone *= 0.035 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t)) * np.clip(t / 6, 0, 1)
    swell = np.clip((t - K["door"]) / 20, 0, 1) * np.clip((TOTAL - t) / 3, 0, 1)     # напряжение к финалу
    drone *= 1 + 1.2 * swell
    tone = np.convolve(rng.normal(0, 1, n), np.ones(400) / 400, "same") * 0.06
    mix += drone + tone
    for t0, i in tl.voice:
        v = VOICE[i]
        if i == "12":
            v = echo(v)
        elif i in ("13", "14", "15", "16", "17"):
            v = reverb(v, 0.5, 0.12)
        k = int(t0 * SR)
        mix[k:k + len(v)] += v[: n - k]
    for t0, s in tl.sfx:
        k = int(t0 * SR)
        if s == "ring":
            m = int(SR * 5)
            tt = np.arange(m) / SR
            mix[k:k + m] += np.sin(2 * np.pi * 5800 * tt) * 0.015 * np.exp(-tt / 2.0)
            continue
        a = SFX[s]
        mix[k:k + len(a)] += a[: n - k]
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
