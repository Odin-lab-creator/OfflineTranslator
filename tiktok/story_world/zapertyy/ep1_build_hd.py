#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 — HD-версия: вдвое больше пикселей, плавнее движение.

python3 ep1_build_hd.py  →  zapertyy_ep1_hd.mp4 (1080×1920, 30 к/с)

Кадр 216×384 арт-пикселя (пиксель 5×5 на экране), фоны 320×384 и крупные планы 216×336 (art/src_hd),
Денис 128px с анимациями PixelLab (art/src/denis128). Таймлайн, озвучка и звук — из ep1_build.py.
Плавность: 30 к/с, анимации 12 к/с, камера с замедлением, переходы-растворения между сценами.
"""
import functools
import glob
import os
import subprocess

import numpy as np
from PIL import Image

import ep1_build as base

HERE = base.HERE
fe = base.fe
OUT = os.path.join(HERE, "zapertyy_ep1_hd.mp4")
FPS = 30
CW, CH, BAND = 216, 384, 52
VIEW_H = CH - BAND
SRC_HD = os.path.join(HERE, "art", "src_hd")
DEN = os.path.join(HERE, "art", "src", "denis128")
K, TOTAL = base.K, base.TOTAL
rng = np.random.default_rng(7)

# --- удары ногой в дверь: звук по кадрам удара (кадр 2 — нога, кадр 7 — плечо), 3 повтора по 14 кадров
KICK_FPS, KICK_N = 12, 14
KICK_LOOPS = 3
base.tl.sfx = [(t, s) for t, s in base.tl.sfx if not (s == "bang" and t >= K["push"])]
BANGS = []
for c in range(KICK_LOOPS):
    for f in (2, 7):
        BANGS.append(K["push"] + (c * KICK_N + f) / KICK_FPS)
base.tl.sfx += [(t, "bang") for t in BANGS]
RATTLES = [t for t, s in base.tl.sfx if s == "rattle"]

# --- раскладка сцен (координаты фона 320×384): верх кадра, камера, линия ступней
LAYOUT = {
    "room": dict(bg="bg_room", y0=0),
    "street": dict(bg="bg_window", y0=24),
    "corridor": dict(bg="bg_corridor", y0=30, cam=50, feet=335),
    "stairs": dict(bg="bg_stairs", y0=40, cam=90, feet=350),
    "door": dict(bg="bg_entrance", y0=20, cam=52, feet=300),
}
WALKS = {
    "corridor": (K["corr"] + 0.3, K["corr"] + 2.6, 10, 150),
    "stairs": (K["stairs"] + 0.1, K["stairs"] + 1.9, 100, 200),
    "door": (K["door"] + 0.1, K["door"] + 2.2, 60, 160),
}
# шаги под новую походку
base.tl.sfx = [(t, s) for t, s in base.tl.sfx if s != "step"]
for w in WALKS.values():
    tt = w[0]
    while tt < w[1]:
        base.tl.sfx.append((tt, "step"))
        tt += 0.34


# ------------------------------------------------------------------ ресурсы
@functools.lru_cache(None)
def bg(name):
    return np.asarray(Image.open(os.path.join(SRC_HD, f"{name}.png")).convert("RGB"))


@functools.lru_cache(None)
def closeup(name):
    im = np.asarray(Image.open(os.path.join(SRC_HD, f"{name}.png")).convert("RGB"))
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = fe.C_DARK
    h = min(VIEW_H, im.shape[0])
    art[:h] = im[(im.shape[0] - h) // 2:(im.shape[0] - h) // 2 + h, :CW]
    return art


@functools.lru_cache(None)
def anim(name):
    fs = sorted(glob.glob(os.path.join(DEN, f"Idle__animations__{name}__frame_*.png")))
    return [np.asarray(Image.open(f).convert("RGBA")) for f in fs]


@functools.lru_cache(None)
def floor_row(name):
    return max(int(np.nonzero(a[..., 3] > 127)[0].max()) for a in anim(name))


@functools.lru_cache(None)
def rot(view_):
    return np.asarray(Image.open(os.path.join(DEN, f"Idle__rotations__{view_}.png")).convert("RGBA"))


def view(name, cam, y0, dx=0):
    im = bg(name)
    art = np.zeros((CH, CW, 3), np.uint8)
    art[:] = fe.C_DARK
    c = int(np.clip(round(cam + dx), 0, im.shape[1] - CW))
    art[:VIEW_H] = im[y0:y0 + VIEW_H, c:c + CW]
    return art, c


def blit(art, a, x, feet, anchor="canvas", floor=None):
    """x, feet — в координатах кадра. anchor: canvas (центр холста, общий пол анимации) или box (по рамке)."""
    m = a[..., 3] > 127
    ys, xs = np.nonzero(m)
    if anchor == "canvas":
        ax, ay = a.shape[1] // 2, floor
    else:
        ax, ay = (xs.min() + xs.max()) // 2, ys.max()
    x0, y0 = int(round(x)) - ax, int(round(feet)) - ay
    X, Y = xs + x0, ys + y0
    ok = (X >= 0) & (X < CW) & (Y >= 0) & (Y < VIEW_H)
    art[Y[ok], X[ok]] = a[ys[ok], xs[ok], :3]


def frame_of(name, lt, fps=12, loop=True, frames=None):
    seq = frames if frames is not None else list(range(len(anim(name))))
    k = int(lt * fps)
    return anim(name)[seq[k % len(seq)] if loop else seq[min(k, len(seq) - 1)]]


def put_anim(art, name, lt, x, feet, fps=12, loop=True, frames=None):
    blit(art, frame_of(name, lt, fps, loop, frames), x, feet, floor=floor_row(name))


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def shake_at(t, times, dur=0.12, amp=3):
    for x in times:
        if 0 <= t - x < dur:
            return int(rng.integers(-amp, amp + 1))
    return 0


def walk(art, t, scene, cam, y0, after):
    t0, t1, xa, xb = WALKS[scene]
    feet = LAYOUT[scene]["feet"] - y0
    if t < t0:
        return
    if t < t1:
        x = xa + (xb - xa) * (t - t0) / (t1 - t0)
        put_anim(art, "walking__east", t - t0, x - cam, feet, fps=12)
    else:
        after(art, xb - cam, feet, t - t1)


def idle_east(art, x, feet, lt):
    put_anim(art, "breathing_idle__east", lt, x, feet, fps=3)


def wall_text(art, cam, y0):
    m = fe.text_mask("К АВТОБУСАМ", 18)
    x0, yy = 150 - cam, 140 - y0
    h, w = m.shape
    sub = art[yy:yy + h, x0:x0 + w]
    sub[m[: sub.shape[0], : sub.shape[1]]] = fe.C_RED
    cx = x0 + w // 2
    art[yy + h + 2:yy + h + 16, cx - 2:cx + 2] = fe.C_RED
    for k in range(7):
        art[yy + h + 12 + k, cx - 7 + k:cx + 7 - k] = fe.C_RED


# ------------------------------------------------------------------ сцены
def scene_at(t):
    for i, (t0, t1, name, _) in enumerate(base.SCENES):
        if t0 <= t < t1:
            return i, t0, t1, name
    return len(base.SCENES) - 1, *base.SCENES[-1][:3]


def frame_art(t):
    i, t0, t1, name = scene_at(t)
    lt, dur = t - t0, t1 - t0
    if name == "black":
        return np.full((CH, CW, 3), fe.C_DARK, np.uint8)
    if name.startswith("cu_"):
        art = closeup(name).copy()
        if name == "cu_weld":
            dx = shake_at(t, RATTLES, 0.1, 2)
            if dx:
                art[:VIEW_H] = np.roll(art[:VIEW_H], dx, 1)
        else:                                               # лёгкий наезд камеры: сдвиг на 1 пиксель раз в секунду
            dy = int(min(lt, 6) * 1.0)
            art[:VIEW_H] = np.roll(art[:VIEW_H], -dy // 3, 0)
        return art
    if name == "wake":
        art, c = view("bg_room", 70, 0)
        blit(art, anim("getup__east")[0], 150 - c, 318, floor=floor_row("getup__east"))
        k = max(0.0, 1 - lt / 2.4)                           # веки открываются
        if k > 0:
            h = int(VIEW_H / 2 * k ** 0.6)
            art[:h] = fe.C_DARK
            art[VIEW_H - h:VIEW_H] = fe.C_DARK
        return art
    if name == "stand":
        cam = 70 + 19 * ease(lt / dur)
        art, c = view("bg_room", cam, 0)
        if lt < 14 / 4.0:                                    # медленно садится, держась за голову, и встаёт
            put_anim(art, "getup__east", lt, 150 - c, 318, fps=4.0, loop=False)
        else:
            idle_east(art, 150 - c, 318, lt)
        return art
    if name == "window":
        art, c = view("bg_room", 89, 0)
        bob = 1 if int(lt / 0.8) % 2 else 0
        blit(art, rot("north-east"), 232 - c, 300 - bob, anchor="box")
        return art
    if name == "street":
        L = LAYOUT["street"]
        u = ease(lt / dur)
        art, _ = view(L["bg"], 40 + 50 * u, int(L["y0"] - 20 * u))
        return art
    if name in ("corridor", "stairs"):
        L = LAYOUT[name]
        dx = 0
        if name == "corridor" and K["shout"] <= t < K["shout"] + 1.0:
            dx = int(rng.integers(-1, 2))
        art, c = view(L["bg"], L["cam"], L["y0"], dx)
        if name == "stairs":
            wall_text(art, c, L["y0"])
        after = (lambda a, x, f, l: blit(a, rot("south-west"), x, f, anchor="box")) if name == "corridor" \
            else (lambda a, x, f, l: idle_east(a, x, f, l))
        walk(art, t, name, c, L["y0"], after)
        return art
    if name == "door":
        L = LAYOUT["door"]
        art, c = view(L["bg"], L["cam"], L["y0"], shake_at(t, BANGS))
        feet = L["feet"] - L["y0"]
        if t < K["push"] - 0.4:
            walk(art, t, "door", c, L["y0"], lambda a, x, f, l: idle_east(a, x, f, l))
        elif t < K["push"]:                                  # поворачивается спиной к нам, к двери
            blit(art, rot("north-east" if t < K["push"] - 0.2 else "north"), 160 - c, feet, anchor="box")
        elif t < K["push"] + KICK_LOOPS * KICK_N / KICK_FPS:
            put_anim(art, "kick__north", t - K["push"], 160 - c, feet, fps=KICK_FPS)
        else:
            put_anim(art, "breathing_idle__north", t - K["push"], 160 - c, feet, fps=3)
        return art
    if name == "crouch":
        L = LAYOUT["door"]
        art, c = view(L["bg"], L["cam"], L["y0"])
        a = frame_of("crouching__north", lt, fps=10, loop=False)
        blit(art, a, 160 - c, L["feet"] - L["y0"], anchor="box")
        return art
    if name == "end":
        L = LAYOUT["door"]
        art, c = view(L["bg"], L["cam"], L["y0"])
        put_anim(art, "slide__south", lt, 160 - c, 285 - L["y0"], fps=4, loop=False)
        k = min(1.0, lt / 8.0) * 0.65
        art[:VIEW_H] = (art[:VIEW_H] * (1 - k) + np.array(fe.C_DARK) * k).astype(np.uint8)
        return art
    return np.full((CH, CW, 3), fe.C_DARK, np.uint8)


XFADE = 0.25


def picture(t):
    art = frame_art(t)
    i, t0, _, name = scene_at(t)
    if i > 0 and t - t0 < XFADE and name != "black":        # растворение из прошлой сцены
        prev = frame_art(t0 - 1e-3)
        u = (t - t0) / XFADE
        art = (prev * (1 - u) + art * u).astype(np.uint8)
    return art


@functools.lru_cache(512)
def ui_layer(sub, titles):
    ui = np.zeros((CH, CW, 4), np.uint8)
    if sub:
        fe.subtitle(ui, sub)
    for text, y in titles:
        for k, ln in enumerate(fe.wrap(text, 15, width=CW - 16)):
            fe.ui_text(ui, ln, y + k * 19, 15, fe.C_HI)
    return ui


def render_frame(t):
    art = picture(t)
    sub = next((s for a, b, s in base.SUBS if a <= t < b), "")
    titles = tuple((x, y) for a, b, x, y in base.tl.titles if a <= t < b)
    ui = ui_layer(sub, titles)
    m = ui[..., 3] > 0
    art[m] = ui[..., :3][m]
    if t > TOTAL - 0.6:
        art = (art * max(0.0, (TOTAL - t) / 0.6)).astype(np.uint8)
    return art


def main():
    wav = OUT + ".wav"
    base.build_audio(wav)
    nf = int(TOTAL * FPS)
    print(f"длительность {TOTAL:.1f} с, кадров {nf}", flush=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=neighbor",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
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
