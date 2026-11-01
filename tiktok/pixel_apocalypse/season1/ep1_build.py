#!/usr/bin/env python3
"""«ТИХИЕ», серия 1 «Четыре секунды» — сборка видео (STYLE_LOCK v3).

cd tiktok/pixel_apocalypse && python3 season1/ep1_build.py [preview]

Озвучка: season1/ep1/voice/*.mp3 (ElevenLabs: рассказчик — Brian, Вера — Lily, Глеб — Will).
Таймлайн строится по реальной длине фраз; картинка, субтитры, музыка и звуки идут под голос.
"""
import json
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
PREVIEW = len(sys.argv) > 1 and sys.argv[1] == "preview"
sys.argv = [sys.argv[0], "full"]
import video_v4 as v4  # noqa: E402  (подключает автоподбор кегля крупного текста)
import video_v3 as v  # noqa: E402
import chiptune as ct  # noqa: E402

CW, CH, SC, FPS, SR = v.CW, v.CH, v.SC, v.FPS, ct.SR
VO = os.path.join(HERE, "ep1", "voice")
OUT = os.path.join(HERE, "ep1", "tikhie_ep1.mp4")
LINES = {l["id"]: l for l in json.load(open(os.path.join(VO, "lines.json"), encoding="utf8"))}


# ------------------------------------------------------------------ голос
def load(id_):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(VO, id_ + ".mp3"), "-f", "f32le", "-ac", "1",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).astype(np.float64)
    env = np.abs(a) > 0.02 * np.abs(a).max()
    idx = np.nonzero(env)[0]
    s, e = max(0, idx[0] - int(0.03 * SR)), min(len(a), idx[-1] + int(0.08 * SR))
    return a[s:e]


def radio_fx(a):
    X = np.fft.rfft(a)
    f = np.fft.rfftfreq(len(a), 1 / SR)
    X *= (f > 350) & (f < 3200)
    y = np.fft.irfft(X, len(a))
    y = np.tanh(y * 2.2) / 2.2
    return y + np.random.default_rng(5).normal(0, 0.012, len(y))


AUDIO = {k: load(k) for k in LINES}
for k in AUDIO:
    if LINES[k]["who"] == "vera":
        AUDIO[k] = radio_fx(AUDIO[k])

# ------------------------------------------------------------------ таймлайн
SEQ = [("line", "n0", 0.55), ("line", "n1", 0.5), ("line", "n2", 0.6), ("line", "n3", 0.3), ("card", "note1", 2.6),
       ("line", "n4", 0.8), ("line", "n5", 0.5), ("line", "v0", 0.5), ("line", "v1", 0.8), ("line", "v2", 0.6),
       ("line", "n6", 0.8), ("knock", None, 1.3), ("slide", None, 0.8), ("card", "note2", 2.4), ("line", "n7", 0.6),
       ("peep", None, 1.3), ("line", "g0", 0.5), ("line", "n8", 0.7), ("line", "n9", 0.7), ("end", None, 3.8)]
NOTES = {"note1": ("ТЫ УЖЕ ЗАБЫЛ.", "НЕ СЛУШАЙ ЕГО."), "note2": ("ОТКРОЙ.", "ОНИ ИДУТ К ТЕБЕ.")}
EV = []
t = 0.25
for kind, key, gap in SEQ:
    dur = len(AUDIO[key]) / SR if kind == "line" else 0.0
    EV.append(dict(kind=kind, key=key, t0=t, t1=t + dur, gap=gap))
    t += dur + gap
DUR = t
E = {(e["key"] or e["kind"]): e for e in EV}


def at(key):
    return E[key]["t0"]


def end(key):
    return E[key]["t1"]


# сцены: (начало, конец, имя)
SCENES = [(0.0, at("n2") - 0.25, "street"), (at("n2") - 0.25, at("n3") - 0.2, "store"),
          (at("n3") - 0.2, at("n5") - 0.2, "door1"), (at("n5") - 0.2, at("knock") - 0.15, "radio"),
          (at("knock") - 0.15, at("peep"), "door2"), (at("peep"), at("end"), "peep"), (at("end"), DUR, "end")]

# ------------------------------------------------------------------ субтитры по словам
VOW = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
WORDS = []
for e in EV:
    if e["kind"] != "line":
        continue
    words = LINES[e["key"]]["text"].replace("[whispers] ", "").split()
    syl = [max(1, sum(ch in VOW for ch in w)) for w in words]
    span, tt = e["t1"] - e["t0"], e["t0"]
    for w, s in zip(words, syl):
        d = span * s / sum(syl)
        WORDS.append(dict(w=w, s=tt, e=tt + d, who=LINES[e["key"]]["who"], line=e["key"]))
        tt += d
PAGES, cur = [], []
for i, w in enumerate(WORDS):
    cur.append(w)
    nxt = WORDS[i + 1] if i + 1 < len(WORDS) else None
    if len(cur) >= 3 or len(" ".join(x["w"] for x in cur)) > 15 or w["w"][-1] in ".,!?…»" or not nxt or nxt["line"] != w["line"]:
        PAGES.append(cur); cur = []


def captions(art, tt):
    pt = v.PixelText(art)
    for i, p in enumerate(PAGES):
        e_ = p[-1]["e"] + 0.25
        if i + 1 < len(PAGES):
            e_ = min(e_, PAGES[i + 1][0]["s"])
        if not (p[0]["s"] - 0.05 <= tt < e_):
            continue
        other = p[0]["who"] != "narrator"
        sz, lines, ln = 11, [], []
        for w in p:
            if ln and pt.width(" ".join(x["w"] for x in ln + [w]), sz) > CW - 6:
                lines.append(ln); ln = [w]
            else:
                ln.append(w)
        lines.append(ln)
        y = 172 if len(lines) == 1 else 160
        for ln in lines[:2]:
            x = (CW - pt.width(" ".join(w["w"] for w in ln), sz)) // 2
            for w in ln:
                act = w["s"] - 0.03 <= tt < w["e"]
                pt.put(x, y, w["w"], sz, v.C_HI if act else (v.C_RED if other else v.C_TEXT))
                x += pt.width(w["w"] + " ", sz)
            y += sz + 2
        return


# ------------------------------------------------------------------ детали сцен
C_CHALK = tuple(int(c) for c in min(v.PAL, key=lambda c: abs(c.mean() - 170) + 3 * (c.max() - c.min())))
C_PAPER = v.C_TEXT


def tally(img, cam, tt):
    """47 черт мелом над стеллажом склада (x 56–92, y 38–50); последняя появляется на глазах."""
    n = 46 + (1 if tt >= at("n2") + 0.5 else 0)
    k = 0
    for row, y0 in enumerate((38, 45)):
        x = 56
        while k < n and x < 93:
            for j in range(4):
                if k >= n:
                    break
                xx = x + j - cam
                if 0 <= xx < CW:
                    img[y0:y0 + 5, xx] = C_CHALK
                k += 1
            if k < n and k % 5 == 4:
                for j in range(5):
                    xx = x - 1 + j - cam
                    if 0 <= xx < CW:
                        img[y0 + 4 - j, xx] = C_CHALK
                k += 1
            x += 7
        if k >= n:
            break


def door_note(img, cam):
    x0 = 74 - cam
    if x0 + 9 < 0:
        return
    img[112:119, max(0, x0):max(0, x0 + 9)] = C_PAPER
    for y in (114, 116):
        img[y, max(0, x0 + 1):max(0, x0 + 7)] = v.C_DARK


def slide_note(img, cam, tt):
    k = v.ease((tt - at("slide")) / 0.7)
    x = int(84 - 20 * k) - cam
    img[166:168, max(0, x):max(0, x + 8)] = C_PAPER


def peep_mask(art):
    yy, xx = np.mgrid[0:CH, 0:CW]
    d = np.sqrt((xx - CW / 2) ** 2 + (yy - 100) ** 2)
    art[d > 46] = v.C_DARK
    ring = (d > 43) & (d <= 46)
    tmp = art.astype(np.float32)
    tmp[ring] *= 0.35
    return v.quantize(tmp, dither=0)         # кольцо глазка тоже в палитре


def act(img, spr, x, feet, cam, name=None, flip=False, dark=0.0, fps=None, tt=0.0, t0=0.0):
    fr, f_feet, cxc = v.sprite(*spr)
    n = int((tt - t0) * (fps or v.ANIM_FPS.get(spr[0], 6)))
    f = fr[min(n, len(fr) - 1)] if spr[0] in v.ONCE else fr[n % len(fr)]
    v.blit(img, f, f_feet, cxc, x, feet, cam, flip, dark)


M_ROT = ("mira_rot:0", "mira_rot:0")
Z_FRONT = ("zombie_rot:0", "zombie_rot:0")
Z_RIGHT = ("zombie_rot:2", "zombie_rot:2")


def frame(i):
    tt = i / FPS
    name = next(s[2] for s in SCENES if s[0] <= tt < s[1]) if tt < DUR else "end"
    s0, s1 = next((s[0], s[1]) for s in SCENES if s[2] == name)
    k = (tt - s0) / max(1e-6, s1 - s0)
    b, changed, text = 1.0, False, []
    if name == "end":
        art = np.zeros((CH, CW, 3), np.uint8) + np.array(v.C_DARK, np.uint8)
        pt = v.PixelText(art); lt = tt - s0
        if lt > 0.3:
            pt.center(60, "ТИХИЕ", 20, v.C_RED)
        if lt > 1.0:
            pt.center(92, "СЕРИЯ 2", 11, v.C_TEXT)
            pt.center(108, "«СВОЙ»", 11, v.C_HI)
        if lt > 1.8 and int(tt * 2) % 2:
            pt.center(146, "ПОДПИШИСЬ", 11, v.C_TEXT)
        return art
    if name == "street":
        cam = int(round(52 - 52 * v.ease((tt - end("n0")) / (s1 - end("n0"))))) if tt > end("n0") else 52
        img = v.bg("night_street")[:, cam:cam + CW].copy()
        v4.palette_cycle(img, "night_street", cam, tt)
        for x, d in ((70, 0.45), (104, 0.25), (138, 0.4), (30, 0.55)):
            act(img, Z_RIGHT, x, 172, cam, dark=d)
        v.particles(img, tt, "ash")
        if tt < end("n0") + 0.3:
            b = 0.8 + 0.12 * math.sin(tt * 6); changed = True
    elif name == "store":
        cam = int(round(14 + 12 * v.ease(k)))
        img = v.bg("storeroom")[:, cam:cam + CW].copy()
        v4.palette_cycle(img, "storeroom", cam, tt)
        tally(img, cam, tt)
        act(img, v.H_IDLE, 40, 150, cam, tt=tt, t0=s0)
        v.particles(img, tt, "dust")
    elif name in ("door1", "door2"):
        cam = 24 if name == "door2" else int(round(24 + 8 * v.ease(k)))
        if name == "door2":
            for kt in (at("knock") + 0.1, at("knock") + 0.45, at("knock") + 0.8):
                if 0 <= tt - kt < 0.16:
                    cam += int(2 * math.sin((tt - kt) * 90))
        cam = max(0, min(52, cam))
        img = v.bg("corridor")[:, cam:cam + CW].copy()
        v4.palette_cycle(img, "corridor", cam, tt)
        if name == "door1":
            door_note(img, cam)
        else:
            v.door_strip(img, cam, 0.0); changed = True
            if tt >= at("slide"):
                slide_note(img, cam, tt)
        act(img, v.H_IDLE, 30, 168, cam, tt=tt, t0=s0)
        v.particles(img, tt, "dust")
        for key in ("note1", "note2"):
            if at(key) <= tt < at(key) + E[key]["gap"]:
                b = 0.35; changed = True; text.append(NOTES[key])
    elif name == "radio":
        cam = int(round(52 - 42 * v.ease((tt - s0) / max(1e-6, at("v0") - s0)))) if tt < at("v0") else int(round(10 + 6 * v.ease((tt - at("v0")) / (s1 - at("v0")))))
        img = v.bg("radio")[:, cam:cam + CW].copy()
        v4.palette_cycle(img, "radio", cam, tt)
        on = at("v0") - 0.3 <= tt < end("v2") + 0.2
        v.radio_dial(img, cam, "flicker" if on else "on", tt); changed = True
        act(img, v.H_CROUCH, 82, 150, cam, flip=True, tt=tt, t0=s0)
        if at("v0") - 0.3 <= tt < at("v0") + 0.25:
            v.static_fx(img, i)
        if tt >= at("n6"):
            b = 0.8
        text.append(("03:20",) if tt < at("v0") else ())
    elif name == "peep":
        img = v.bg("corridor")[:, 20:20 + CW].copy() * 0.8
        z_step = 0 if tt < at("n8") else (8 if tt < at("n9") else 18)
        zd = 0.68 if tt < at("n8") else (0.5 if tt < at("n9") else 0.3)
        for x in (24, 86):                       # Тихие — в конце коридора, по краям, в тени
            act(img, Z_FRONT, x + 20, 128 + z_step, 20, dark=zd)
        act(img, M_ROT, 54 + 20, 178, 20)        # Мира — у самой двери
        if tt >= at("n9"):
            img[..., 0] = np.minimum(255, img[..., 0] * 1.25 + 20); b = 0.9 + 0.1 * math.sin(tt * 20)
        if tt >= at("n8") and int(tt * 30) % 9 == 0:
            img = np.roll(img, 1, axis=1)
        changed = True
    if b != 1.0:
        img = img * b
    art = v.quantize(img, dither=12 if changed else 0)
    if name == "peep":
        art = peep_mask(art)
    pt = v.PixelText(art)
    for tx in text:
        if len(tx) == 2:
            pt.center(70, tx[0], 13, v.C_TEXT)
            pt.center(90, tx[1], 13, v.C_RED)
        elif len(tx) == 1:
            pt.put(CW - pt.width(tx[0], 9) - 4, 4, tx[0], 9, v.C_TEXT)
    if name == "street" and at("n1") <= tt < at("n1") + 2.6:
        pt.center(20, "ТИХИЕ", 20, v.C_RED)
        pt.center(46, "СЕРИЯ 1", 9, v.C_TEXT)
    if name == "peep" and tt >= at("n9"):
        pt.center(52, "4", 30, v.C_RED)
    captions(art, tt)
    return art


def render(i):
    return np.asarray(Image.fromarray(frame(i)).resize((CW * SC, CH * SC), Image.NEAREST)).tobytes()


# ------------------------------------------------------------------ звук
def music():
    n = int(DUR * SR)
    m = np.zeros(n)
    beat = 60 / 66
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (50, [50, 53, 57]), (52, [52, 56, 59])]
    for b in range(int(DUR / beat) + 1):
        tt = b * beat
        if tt >= at("end"):
            break
        root, chord = prog[(b // 4) % 4]
        L = int(beat * SR)
        tense = tt >= at("knock")
        if not (at("v0") - 0.5 <= tt < end("v2") + 0.5):
            ct.add(m, tt, ct.tri(ct.hz(root - 12), L) * ct.env(L, d=0.3, s=0.4, r=0.1) * (0.3 if tense else 0.22))
        if tt < at("knock") and b % 2 == 0 and not (at("v0") - 0.5 <= tt < end("n6")):
            for j in range(2):
                L2 = int(beat / 2 * SR)
                ct.add(m, tt + j * beat / 2, ct.sq(ct.hz(chord[(b + j) % 3] + 12), L2, 0.125) * ct.env(L2, d=0.06, s=0.2, r=0.03) * 0.06)
        if b % 4 == 0:
            L4 = int(4 * beat * SR)
            ct.add(m, tt, (ct.sq(ct.hz(root - 24), L4) + ct.sq(ct.hz(root - 24) * 1.006, L4)) * ct.env(L4, a=0.5, d=1, s=0.8, r=0.6) * 0.03)
    # сердцебиение после стука, учащается к «Четыре»
    tt, bpm = at("knock"), 70.0
    while tt < at("n9"):
        for off in (0.0, 0.17):
            Lk = int(0.12 * SR); x = np.arange(Lk) / SR
            ct.add(m, tt + off, np.sin(2 * np.pi * 55 * x) * np.exp(-x * 30) * 0.38)
        bpm = 70 + 50 * (tt - at("knock")) / max(1, at("n9") - at("knock"))
        tt += 60 / bpm
    # тонкий звон в глазке
    L = int((at("n9") - at("peep")) * SR); x = np.arange(L) / SR
    ct.add(m, at("peep"), ct.sq(1760, L, 0.5) * 0.008 * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * x)))
    m *= np.clip(np.arange(n) / SR / 0.8, 0, 1)
    return m


def sfx():
    n = int(DUR * SR)
    f = np.zeros(n)
    ct.add(f, 0.0, ct.sfx_hit() * 0.7)
    # мел по стене
    for j in range(3):
        L = int(0.07 * SR)
        ct.add(f, at("n2") + 0.45 + j * 0.06, ct.noise(L, 30 + j, 2) * np.exp(-np.arange(L) / SR * 25) * 0.12)
    ct.add(f, at("note1"), ct.sfx_stab() * 0.6)
    ct.add(f, at("v0") - 0.3, ct.sfx_static(0.6))
    ct.add(f, at("v0"), ct.sfx_static(end("v2") - at("v0")) * 0.18)
    for kt in (0.1, 0.45, 0.8):
        ct.add(f, at("knock") + kt, ct.sfx_knock(int(kt * 100)) * 1.2)
    L = int(0.6 * SR)
    ct.add(f, at("slide"), ct.noise(L, 77, 3) * np.hanning(L) * 0.08)
    ct.add(f, at("note2"), ct.sfx_stab() * 0.6)
    ct.add(f, at("n9"), ct.sfx_hit())
    ct.add(f, at("end") + 0.2, ct.sfx_stinger() * 0.6)
    return f


def build_audio(path):
    n = int(DUR * SR)
    vo = np.zeros(n)
    for e in EV:
        if e["kind"] == "line":
            a = AUDIO[e["key"]] / (np.abs(AUDIO[e["key"]]).max() + 1e-9)
            gain = {"narrator": 1.0, "vera": 0.9, "gleb": 0.85}[LINES[e["key"]]["who"]]
            ct.add(vo, e["t0"], a * gain)
    win = int(0.15 * SR)
    venv = np.sqrt(np.convolve(vo ** 2, np.ones(win) / win, "same"))
    duck = 1 - 0.6 * np.clip(venv / 0.12, 0, 1)
    mix = vo + music() * 0.6 * duck + sfx() * 0.6
    mix *= np.clip((DUR - np.arange(n) / SR) / 1.0, 0, 1)
    mix = np.tanh(mix * 1.1); mix /= np.abs(mix).max() + 1e-9
    d = (mix * 0.95 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.stack([d, d], 1).tobytes())


def main():
    print(f"длительность {DUR:.1f} с, сцен {len(SCENES)}", flush=True)
    if PREVIEW:
        keys = ["n0", "n1", "n2", "n3", "note1", "n5", "v1", "knock", "note2", "peep", "n8", "n9", "end"]
        ims = [Image.fromarray(frame(int((at(k) + 0.6) * FPS))) for k in keys]
        sheet = Image.new("RGB", (CW * len(ims), CH))
        for j, im in enumerate(ims):
            sheet.paste(im, (j * CW, 0))
        sheet.resize((sheet.width * 2, CH * 2), Image.NEAREST).save(os.path.join(HERE, "ep1", "preview_sheet.png"))
        print("превью сохранено")
        return
    wav = OUT + ".wav"
    build_audio(wav)
    nfr = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW * SC}x{CH * SC}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    v.lut()
    with Pool(os.cpu_count()) as pool:
        for j, fr in enumerate(pool.imap(render, range(nfr), chunksize=15)):
            p.stdin.write(fr)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
