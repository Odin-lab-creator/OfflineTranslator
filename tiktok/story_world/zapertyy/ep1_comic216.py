#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 — экономная версия кинокомикса: главные кадры PixelLab Pro 216×384 (art/pro216, 15 генераций),
крупные планы предметов — готовые из первой версии (art/test_pro, 360×640).

python3 ep1_comic216.py  →  zapertyy_ep1_v2.mp4 (1080×1920, 30 к/с)

Каждая фраза озвучки ложится на свой кадр. Камера медленно едет/приближается (плавно, с замедлением),
пыль в свете, дрожь и «толчок» камеры на ударах, растворения между кадрами, пиксельные субтитры (сетка 3×3).
Озвучка — voice/ep1 (ElevenLabs, ×1.06), шумы и гул — из ep1_build.py.
"""
import functools
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import ep1_build as base

HERE = base.HERE
SRC = os.path.join(HERE, "art", "test_pro")
OUT = os.path.join(HERE, "zapertyy_ep1_v2.mp4")
SRC216 = os.path.join(HERE, "art", "pro216")
MAIN = {"01_wake", "06_stand", "02_window", "13_door", "03_corridor", "14_stairs", "04_kick", "05_end"}
FPS, SR = 30, base.SR
W, H = 1080, 1920
GW, GH = 360, 640                 # сетка кадра PixelLab
UP = 4                            # база для камеры: 1440×2560
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
C_TEXT, C_DARK, C_HI = (236, 230, 214), (10, 9, 12), (240, 196, 120)
C_PAINT = (168, 58, 46)
DUR, TEXT = base.DUR, base.TEXT

# ------------------------------------------------------------------ таймлайн
tl = base.TL()
SHOTS = []          # [t0, t1, image, cam0, cam1, extra]


def shot(img, cam0, cam1, **extra):
    if SHOTS:
        SHOTS[-1][1] = tl.t
    SHOTS.append([tl.t, None, img, cam0, cam1, extra])


# камера: (масштаб, центр x, центр y) в координатах кадра 360×640
shot(None, (1, 180, 320), (1, 180, 320))
for k in range(3):
    tl.fx("bang", 0.15 + k * 0.6)
tl.wait(1.9)
tl.say("00", 0.35)
tl.titles.append((tl.t, tl.t + 1.7, "ЗАПЕРТЫЙ", 290))
tl.titles.append((tl.t + 0.3, tl.t + 1.7, "СЕРИЯ 1", 312))
tl.wait(1.9)

shot("01_wake", (1.0, 180, 330), (1.22, 185, 410), eyelids=True, dust=True)
tl.fx("ring")
tl.titles.append((tl.t + 0.8, tl.t + 4.0, "ДЕНЬ 1", 60))
tl.wait(0.8)
tl.say("01", 0.5)
tl.say("02", 0.4)

shot("06_stand", (1.18, 120, 250), (1.0, 180, 320), dust=True)
tl.say("03", 0.35)
t04 = tl.say("04", 0.0)
c04 = base.chunk_times("04", t04)
SHOTS[-1][1] = c04[1][0]
tl.t, t_end04 = c04[1][0], tl.t
SHOTS.append([tl.t, None, "07_phone", (1.0, 180, 330), (1.12, 140, 360), {}])
tl.t = c04[2][0] if len(c04) > 2 else (c04[1][0] + c04[1][1]) / 2
SHOTS[-1][1] = tl.t
SHOTS.append([tl.t, None, "08_watch", (1.05, 200, 320), (1.25, 225, 300), {}])
tl.t = t_end04 + 0.45

shot("09_pills", (1.2, 120, 400), (1.2, 230, 330), dust=True)
tl.say("05", 0.35)
shot("10_tap", (1.0, 180, 330), (1.15, 190, 300))
tl.fx("drip")
tl.wait(0.35)
tl.say("06", 0.15)
tl.fx("drip")
tl.wait(0.6)
tl.fx("drip")
tl.wait(0.4)

shot("02_window", (1.0, 180, 330), (1.1, 180, 300), dust=True)
tl.fx("whoosh", tl.t + 0.1)
tl.wait(0.4)
tl.say("07", 0.3)
shot("11_weld", (1.05, 180, 330), (1.12, 170, 340), rattle=True)
for k in range(6):
    tl.fx("rattle", tl.t + 0.1 + k * 0.32)
tl.say("08", 0.3)
shot("02_window", (1.15, 180, 250), (1.32, 180, 205), dust=True)
tl.wait(0.2)
tl.say("09", 0.5)

shot("13_door", (1.0, 180, 330), (1.12, 170, 320))
tl.fx("creak")
tl.wait(0.4)
tl.say("10", 0.35)
shot("03_corridor", (1.0, 180, 330), (1.16, 210, 370), dust=True)
tl.say("11", 0.4)
T_SHOUT = tl.t
tl.say("12", 1.2)
tl.say("13", 0.4)

shot("14_stairs", (1.15, 150, 230), (1.15, 180, 380), dust=True, paint=True)
for k in range(8):
    tl.fx("step", tl.t + 0.2 + k * 0.45)
tl.wait(0.5)
tl.say("14", 0.4)

shot("15_intercom", (1.0, 200, 330), (1.12, 290, 330))
tl.fx("rattle", tl.t + 0.4)
tl.fx("rattle", tl.t + 1.1)
tl.wait(0.3)
tl.say("15", 0.2)

shot("04_kick", (1.06, 185, 330), (1.12, 190, 330), kick=True)
T_KICK = tl.t
KICKS = [T_KICK + d for d in (0.0, 0.55, 1.05, 1.75, 2.3, 2.75)]
for t in KICKS:
    tl.fx("bang", t)
tl.wait(0.4)
tl.say("16", 0.3)

shot("16_crack", (1.0, 180, 320), (1.2, 230, 300))
tl.wait(0.3)
tl.say("17", 0.5)

shot("05_end", (1.2, 250, 420), (1.0, 180, 330), fade=True)
T_END = tl.t
tl.fx("slide", tl.t + 0.2)
tl.wait(0.3)
tl.say("18", 0.8)
tl.say("19", 0.5)
tl.titles.append((tl.t, tl.t + 2.4, "ПОПЫТКА №1: ДВЕРЬ — ПРОВАЛ", 290))
tl.wait(2.4)
tl.titles.append((tl.t, tl.t + 3.0, "ЧТО БЫ ВЫ СДЕЛАЛИ ПЕРВЫМ?", 290))
tl.wait(3.0)
SHOTS[-1][1] = tl.t
TOTAL = tl.t

SUBS = []
for t0, i in tl.voice:
    for a, b, c in base.chunk_times(i, t0):
        SUBS.append((a, b + 0.12, c))
RATTLES = [t for t, s in tl.sfx if s == "rattle"]


# ------------------------------------------------------------------ картинка
@functools.lru_cache(4)
def big(name):
    main = name in MAIN
    im = Image.open(os.path.join(SRC216 if main else SRC, f"{name}.png")).convert("RGB")
    a = np.asarray(im).copy()
    for x in range(a.shape[1]):                               # белые поля по краям у части кадров
        if a[:, x].mean() > 245:
            src = 5 if x < a.shape[1] // 2 else a.shape[1] - 6
            a[:, x] = a[:, src]
    if name == "14_stairs":                                   # надпись краской над стрелкой
        f = ImageFont.truetype(FONT, 9)
        m = Image.new("1", (100, 14), 0)
        d = ImageDraw.Draw(m)
        d.fontmode = "1"
        d.text((0, 0), "К АВТОБУСАМ", font=f, fill=1)
        g = np.asarray(m, bool)
        ys, xs = np.nonzero(g)
        a[ys + 70, xs + 14] = C_PAINT
    k = 6 if main else UP
    return Image.fromarray(a).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def jitter(t, times, dur=0.14, amp=10.0):
    for x in times:
        if 0 <= t - x < dur:
            k = 1 - (t - x) / dur
            r = np.random.default_rng(int(t * 1000))
            return r.uniform(-amp, amp, 2) * k, k
    return np.zeros(2), 0.0


def camera_frame(s, t):
    t0, t1, name, c0, c1, ex = s
    u = ease((t - t0) / max(1e-6, t1 - t0))
    z = c0[0] + (c1[0] - c0[0]) * u
    cx = c0[1] + (c1[1] - c0[1]) * u
    cy = c0[2] + (c1[2] - c0[2]) * u
    off = np.zeros(2)
    if ex.get("kick"):
        o, k = jitter(t, KICKS, 0.18, 2.5)
        off += o
        z += 0.04 * k
    if ex.get("rattle"):
        off += jitter(t, RATTLES, 0.1, 1.2)[0]
    if name == "03_corridor" and T_SHOUT <= t < T_SHOUT + 0.9:
        off += np.random.default_rng(int(t * 1000)).uniform(-0.8, 0.8, 2)
    img = big(name)
    BW, BH = img.size
    sx, sy = BW / GW, BH / GH
    cw, ch = BW / z, BH / z
    x0 = np.clip((cx + off[0]) * sx - cw / 2, 0, BW - cw)
    y0 = np.clip((cy + off[1]) * sy - ch / 2, 0, BH - ch)
    fr = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    a = np.asarray(fr).astype(np.float32)
    if ex.get("dust"):
        a = dust(a, t, t0)
    if ex.get("eyelids"):
        k = max(0.0, 1 - (t - t0) / 2.4)
        if k > 0:
            h = int(H / 2 * k ** 0.6)
            a[:h] = 0
            a[H - h:] = 0
    if ex.get("fade"):
        k = min(1.0, (t - t0) / 9.0) * 0.6
        a *= 1 - k
    return a


def dust(a, t, t0):
    r = np.random.default_rng(11)
    n = 70
    px, py = r.uniform(0, W, n), r.uniform(0, H * 0.8, n)
    vx, vy = r.uniform(-6, 6, n), r.uniform(-14, -3, n)
    ph = r.uniform(0, 6.28, n)
    lt = t - t0
    for k in range(n):
        x = int((px[k] + vx[k] * lt) % W)
        y = int((py[k] + vy[k] * lt) % H)
        al = 0.25 + 0.2 * np.sin(lt * 1.3 + ph[k])
        a[y:y + 3, x:x + 3] = a[y:y + 3, x:x + 3] * (1 - al) + 235 * al
    return a


@functools.lru_cache(1)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    return np.clip(1.08 - 0.28 * r2, 0.55, 1)[..., None]


def shot_at(t):
    for i, s in enumerate(SHOTS):
        if s[0] <= t < s[1]:
            return i
    return len(SHOTS) - 1


XF = 0.35


def picture(t):
    i = shot_at(t)
    s = SHOTS[i]
    if s[2] is None:
        return np.zeros((H, W, 3), np.float32)
    a = camera_frame(s, t)
    if i > 0 and t - s[0] < XF and SHOTS[i - 1][2] is not None:
        u = (t - s[0]) / XF
        a = camera_frame(SHOTS[i - 1], s[0] - 1e-3) * (1 - u) + a * u
    return a * vignette()


# ------------------------------------------------------------------ текст (пиксельный, сетка 3×3)
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
    lines, cur = [], ""
    for w_ in s.split():
        tt = (cur + " " + w_).strip()
        if d.textlength(tt, font=f) <= width:
            cur = tt
        else:
            lines.append(cur)
            cur = w_
    return lines + [cur]


def draw_line(ui, s, cy, sz, color):
    g = text_mask(s, sz)
    h, w = g.shape
    x0 = (GW - w) // 2
    o = np.zeros((h + 2, w + 2), bool)
    for dy in range(3):
        for dx in range(3):
            o[dy:dy + h, dx:dx + w] |= g
    reg = ui[cy - 1:cy + h + 1, x0 - 1:x0 + w + 1]
    reg[o[: reg.shape[0], : reg.shape[1]]] = (*C_DARK, 255)
    reg = ui[cy:cy + h, x0:x0 + w]
    reg[g[: reg.shape[0], : reg.shape[1]]] = (*color, 255)


@functools.lru_cache(256)
def ui_layer(sub, titles):
    ui = np.zeros((GH, GW, 4), np.uint8)
    if sub:
        lines = wrap(sub, 16, GW - 30)
        y = 450 - 11 * len(lines)
        for ln in lines:
            draw_line(ui, ln, y, 16, C_TEXT)
            y += 22
    for text, y in titles:
        for k, ln in enumerate(wrap(text, 17, GW - 40)):
            draw_line(ui, ln, y + k * 24, 17, C_HI)
    big_ = Image.fromarray(ui, "RGBA").resize((W, H), Image.NEAREST)
    return np.asarray(big_)


def render(t):
    a = picture(t)
    sub = next((s for x, y, s in SUBS if x <= t < y), "")
    titles = tuple((x, y) for p, q, x, y in tl.titles if p <= t < q)
    if sub or titles:
        ui = ui_layer(sub, titles)
        m = ui[..., 3] > 0
        a[m] = ui[..., :3][m]
    if t > TOTAL - 0.7:
        a *= max(0.0, (TOTAL - t) / 0.7)
    return np.clip(a, 0, 255).astype(np.uint8).tobytes()


# ------------------------------------------------------------------ звук
def build_audio(path):
    n = int(SR * (TOTAL + 1))
    mix = np.zeros(n)
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.35 * t) + 0.4 * np.sin(2 * np.pi * 82.4 * t))
    drone *= 0.035 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t)) * np.clip(t / 6, 0, 1)
    swell = np.clip((t - T_KICK + 15) / 20, 0, 1) * np.clip((TOTAL - t) / 3, 0, 1)
    drone *= 1 + 1.2 * swell
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


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for s in SHOTS[1:]:
            tm = (s[0] + s[1]) / 2
            Image.frombytes("RGB", (W, H), render(tm)).resize((270, 480)).save(
                os.path.join("/tmp", f"cm_{tm:06.1f}.png"))
        return
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
