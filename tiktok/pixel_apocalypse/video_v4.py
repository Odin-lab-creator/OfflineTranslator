#!/usr/bin/env python3
"""PIXEL APOCALYPSE — серия 1 «72 ЧАСА», монтаж v4 (на основе video_v3).

python3 video_v4.py part1|part2|full|covers

Что добавлено к v3:
  * зацепка в первые 1,5 с (заражённый в проёме + «НЕ СМОТРИ В ОКНО»; для части 2 — стук и «ЧАСТЬ 2»);
  * деление на две части: часть 1 обрывается на «Я знаю, что ты там…» → «ОТКРЫЛ БЫ?»;
  * 8-битная музыка и звуки (chiptune.py);
  * мерцание огня и ламп сменой цветов палитры (palette cycling) — пиксели остаются палитровыми;
  * крупные субтитры (11 px, до двух строк);
  * обложки для TikTok (covers).
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MODE = sys.argv[1] if len(sys.argv) > 1 else "full"
sys.argv = sys.argv[:1]
import video_v3 as v  # noqa: E402
from video_v3 import CW, CH, SC, FPS, ep, PAL  # noqa: E402
import chiptune  # noqa: E402

_center = v.PixelText.center


def _center_fit(self, y, s, sz, fill):
    """Крупный текст всегда помещается в кадр: уменьшаем кегль, пока не влезет с полями."""
    while sz > 7 and self.width(s, sz) > CW - 6:
        sz -= 1
    _center(self, y, s, sz, fill)


v.PixelText.center = _center_fit

HOOK = 1.6
TAIL = 4.0
CUTS = {
    "full": dict(v0=0.0, v1=v.END, hook=HOOK, tail=TAIL, hook_kind="teaser", end="series2"),
    "part1": dict(v0=0.0, v1=v.T["T_RULE2"] - 0.3, hook=HOOK, tail=TAIL, hook_kind="teaser", end="cliff"),
    "part2": dict(v0=v.T["T_RULE2"] - 0.3, v1=v.END, hook=HOOK, tail=TAIL, hook_kind="part2", end="series2"),
}


# ------------------------------------------------------------------ palette cycling
def _lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


WARM = sorted([tuple(int(x) for x in c) for c in PAL if c[0] > c[1] >= c[2] - 5 and c[0] - c[2] > 45 and _lum(c) > 70], key=_lum)
WARM_ARR = np.array(WARM, np.float32)
_WIDX = {c: i for i, c in enumerate(WARM)}
CYCLE = {  # фон: (область y0..y1, амплитуда, характер)
    "night_street": ((100, 180), 1.6, "fire"),
    "corridor": ((60, 120), 1.0, "lamp"),
    "storeroom": ((40, 110), 1.0, "lamp"),
    "window": ((50, 110), 1.0, "lamp"),
    "radio": ((100, 145), 1.0, "candle"),
}
_cyc = {}


def cycle_map(name):
    if name not in _cyc:
        img = v.bg(name).astype(np.int32)
        idx = np.full(img.shape[:2], -1, np.int32)
        (y0, y1), _, _ = CYCLE.get(name, ((0, 0), 0, ""))
        for y in range(y0, min(y1, CH)):
            for x in range(img.shape[1]):
                c = tuple(int(q) for q in img[y, x])
                if c in _WIDX and _lum(c) > 95:
                    idx[y, x] = _WIDX[c]
        _cyc[name] = idx
    return _cyc[name]


def palette_cycle(img, name, cam, t):
    if name not in CYCLE or not len(WARM):
        return
    idx = cycle_map(name)[:, cam:cam + CW]
    m = idx >= 0
    if not m.any():
        return
    _, amp, kind = CYCLE[name]
    tq = math.floor(t * 10) / 10                         # мерцание 10 раз в секунду, как в играх
    yy, xx = np.nonzero(m)
    if kind == "fire":
        off = np.round(amp * np.sin(tq * 12 + (xx + cam) * 0.9 + yy * 1.3) * np.sin(tq * 7.3 + (xx + cam) * 0.4))
    else:
        flick = math.sin(tq * 17) * math.sin(tq * 5.1)
        off = np.full(len(xx), -1.0 if flick > 0.82 else (-0.0 if kind == "lamp" else round(0.6 * math.sin(tq * 9))))
    j = np.clip(idx[yy, xx] + off.astype(int), 0, len(WARM) - 1)
    img[yy, xx] = WARM_ARR[j]


# ------------------------------------------------------------------ субтитры
def captions(art, t):
    pt = v.PixelText(art)
    for i, p in enumerate(ep.PAGES):
        end = p[-1]["e"] + 0.25
        if i + 1 < len(ep.PAGES):
            end = min(end, ep.PAGES[i + 1][0]["s"])
        if not (p[0]["s"] - 0.05 <= t < end):
            continue
        quote = ep.LINES[p[0]["line"]]["text"].startswith("«")
        sz = 11
        lines, cur = [], []
        for w in p:
            trial = " ".join(x["w"] for x in cur + [w])
            if cur and pt.width(trial, sz) > CW - 6:
                lines.append(cur); cur = [w]
            else:
                cur.append(w)
        lines.append(cur)
        if len(lines) > 2:
            sz = 9
        y = 172 if len(lines) == 1 else 160
        for ln in lines[:2]:
            x = (CW - pt.width(" ".join(w["w"] for w in ln), sz)) // 2
            for w in ln:
                active = w["s"] - 0.03 <= t < w["e"]
                pt.put(x, y, w["w"], sz, v.C_HI if active else (v.C_RED if quote else v.C_TEXT))
                x += pt.width(w["w"] + " ", sz)
            y += sz + 2
        return


# ------------------------------------------------------------------ кадры
def scene_frame(tv, i, with_text=True):
    """Кадр основной части по времени озвучки tv (логика v3 + palette cycling + новые субтитры)."""
    t0, t1, name, c0, c1, actors, o = v.shot_at(tv)
    if o.get("endcard"):
        return None
    k = (tv - t0) / max(1e-6, t1 - t0)
    if "pan_from" in o:
        k = (tv - o["pan_from"]) / max(1e-6, t1 - o["pan_from"])
    cam = int(round(c0 + (c1 - c0) * v.ease(k)))
    if o.get("knock"):
        for kt in v.KNOCKS:
            if 0 <= tv - kt < 0.16:
                cam += int(2 * math.sin((tv - kt) * 90))
    if o.get("creak") and 0 <= tv - (v.T["T_CREAK"] + 0.5) < 0.5:
        cam += int(round(math.sin(tv * 60)))
    if o.get("static"):
        cam += int(np.random.default_rng(i).integers(-1, 2))
    cam = max(0, min(160 - CW, cam))
    img = v.bg(name)[:, cam:cam + CW].copy()
    palette_cycle(img, name, cam, tv)
    changed = False
    if o.get("radio") and name == "radio":
        v.radio_dial(img, cam, o["radio"], tv); changed = True
    if o.get("door") and name == "corridor":
        v.door_strip(img, cam, tv); changed = True
    for a in actors:
        if a["t_from"] is not None and tv < a["t_from"]:
            continue
        fr, feet, cxc = v.sprite(*a["spr"])
        n = int((tv - t0) * a["fps"])
        f = fr[min(n, len(fr) - 1)] if a["once"] else fr[n % len(fr)]
        wx = a["x0"] + (a["x1"] - a["x0"]) * min(1.0, max(0.0, (tv - t0) / max(1e-6, t1 - t0)))
        wy = a["feet"] if a["feet"] is not None else v.FLOOR[name]
        v.blit(img, f, feet, cxc, wx, wy, cam, a["flip"], a["dark"])
    if o.get("phone"):
        v.phone(img, cam, tv); changed = True
    if o.get("static"):
        v.static_fx(img, i); changed = True
    if o.get("fx"):
        v.particles(img, tv, o["fx"])
    b = 1.0
    if o.get("fade_in"):
        b *= v.ease((tv - t0) / o["fade_in"])
    if o.get("fade_out"):
        b *= v.ease((t1 - tv) / o["fade_out"])
    if o.get("rule"):
        b *= 0.4
    if o.get("dim"):
        b *= o["dim"]
    if o.get("dim_after") and tv >= o["dim_after"][0]:
        b *= 1 - (1 - o["dim_after"][1]) * v.ease((tv - o["dim_after"][0]) / 0.8)
    if b != 1.0:
        img *= b; changed = True
    art = v.quantize(img, dither=12 if changed else 0)
    if with_text:
        pt = v.PixelText(art)
        if o.get("rule"):
            pt.center(70 - int(10 * (1 - v.ease((tv - t0) / 0.2))), o["rule"], 13, v.C_HI)
        else:
            if o.get("title") and 0.4 <= tv < t1 - 0.2:
                pt.center(14, "72 ЧАСА", 18, v.C_RED)
                pt.center(38, "СЕРИЯ 1", 9, v.C_TEXT)
            captions(art, tv)
    return art


def still(name, cam, actors, dim=1.0, red=0.0):
    img = v.bg(name)[:, cam:cam + CW].copy()
    for spr, wx, feet, flip, dark in actors:
        fr, f_feet, cxc = v.sprite(*spr)
        v.blit(img, fr[0], f_feet, cxc, wx, feet if feet else v.FLOOR[name], cam, flip, dark)
    if red:
        img[..., 0] = img[..., 0] * (1 - red) + 255 * red * 0.55
    img *= dim
    return v.quantize(img, dither=12)


def hook_frame(kind, t, i):
    if kind == "teaser":
        pulse = 0.5 + 0.5 * math.sin(t * 14)
        art = still("window", 0, [(v.Z_IDLE, 34, 165, False, 0.0)], dim=0.55 + 0.15 * pulse, red=0.25 * pulse)
        pt = v.PixelText(art)
        if t > 0.15:
            pt.center(70, "НЕ СМОТРИ", 15, v.C_TEXT)
        if t > 0.6:
            pt.center(92, "В ОКНО", 18, v.C_RED)
        if int(t * 20) % 7 == 0:                         # глитч-полоса
            y = int((t * 97) % (CH - 6)); art[y:y + 3] = np.roll(art[y:y + 3], 4, axis=1)
        return art
    shake = int(2 * math.sin(t * 90)) if any(0 <= t - k < 0.16 for k in (0.2, 0.45, 0.7)) else 0
    art = still("corridor", max(0, min(52, 24 + shake)), [(v.H_IDLE, 30, None, False, 0.0)], dim=0.45)
    pt = v.PixelText(art)
    pt.center(56, "72 ЧАСА", 18, v.C_RED)
    pt.center(82, "ЧАСТЬ 2", 13, v.C_HI)
    return art


def end_frame(kind, t):
    if kind == "cliff":
        art = still("corridor", 24, [(v.H_IDLE, 30, None, False, 0.0)], dim=0.35)
        pt = v.PixelText(art)
        if t > 0.2:
            pt.center(52, "ОТКРЫЛ БЫ?", 15, v.C_RED)
        if t > 1.0:
            pt.center(84, "ЧАСТЬ 2", 13, v.C_HI)
            pt.center(102, "УЖЕ СКОРО", 10, v.C_TEXT)
        if t > 1.8 and int(t * 2) % 2:
            pt.center(140, "ПОДПИШИСЬ", 11, v.C_TEXT)
        return art
    art = np.zeros((CH, CW, 3), np.uint8) + np.array(v.C_DARK, np.uint8)
    pt = v.PixelText(art)
    if t > 0.2:
        pt.center(60, "72 ЧАСА", 18, v.C_RED)
    if t > 0.8:
        pt.center(88, "СЕРИЯ 2", 11, v.C_TEXT)
        pt.center(104, "ЧУЖИЕ У ДВЕРИ", 10, v.C_HI)
    if t > 1.6 and int(t * 2) % 2:
        pt.center(140, "ПОДПИШИСЬ", 11, v.C_TEXT)
    return art


CUT = CUTS.get(MODE, CUTS["full"])


def render(i):
    t = i / FPS
    c = CUT
    main = c["v1"] - c["v0"]
    if t < c["hook"]:
        art = hook_frame(c["hook_kind"], t, i)
    elif t < c["hook"] + main:
        art = scene_frame(c["v0"] + (t - c["hook"]), i)
    else:
        art = end_frame(c["end"], t - c["hook"] - main)
    return np.asarray(Image.fromarray(art).resize((CW * SC, CH * SC), Image.NEAREST)).tobytes()


def covers():
    out = []
    for kind, sub, bottom in (("part1", "СЕРИЯ 1 · ЧАСТЬ 1", "НЕ СМОТРИ В ОКНО"), ("part2", "СЕРИЯ 1 · ЧАСТЬ 2", "ОН ЗА ДВЕРЬЮ"),
                              ("full", "СЕРИЯ 1", "НЕ СМОТРИ В ОКНО")):
        if kind == "part2":
            art = still("corridor", 24, [(v.H_IDLE, 30, None, False, 0.0)], dim=0.8)
        else:
            art = still("window", 18, [(v.Z_IDLE, 40, 165, False, 0.15), (v.H_IDLE, 104, None, False, 0.0)], dim=0.9)
        pt = v.PixelText(art)
        pt.center(10, "72 ЧАСА", 20, v.C_RED)
        pt.center(36, sub, 9, v.C_TEXT)
        pt.center(166, bottom, 10, v.C_HI)
        p = os.path.join(HERE, f"cover_ep1_{kind}.png")
        Image.fromarray(art).resize((CW * SC, CH * SC), Image.NEAREST).save(p)
        out.append(p)
    return out


def main():
    if MODE == "covers":
        for p in covers():
            print(p)
        return
    out = os.path.join(HERE, f"pixel_apocalypse_ep1_{MODE}.mp4")
    wav = out + ".wav"
    print("Звук…", flush=True)
    dur = chiptune.build_audio(CUT, wav)
    nfr = int(dur * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW * SC}x{CH * SC}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    v.lut()
    with Pool(os.cpu_count()) as pool:
        for j, fr in enumerate(pool.imap(render, range(nfr), chunksize=15)):
            p.stdin.write(fr)
            if j % 600 == 0:
                print(f"  {j}/{nfr}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("Готово:", out, f"{dur:.1f} c")


if __name__ == "__main__":
    main()
