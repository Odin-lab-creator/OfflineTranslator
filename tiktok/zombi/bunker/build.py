#!/usr/bin/env python3
"""«100 ДНЕЙ В БУНКЕРЕ» — сборка ролика 1080×1920. Мир рисует scene.py (кодом, без картинок и Veo).
python3 build.py            тест: тайминг без голоса (14.8 симв/с) → bunker_test.mp4
python3 build.py --user     под озвучку владельца: voice_user/vo.mp3 + voice_user/stt.json → bunker.mp4
python3 build.py --clean    без надписей (только мир)
--preview                   540×960 для быстрой проверки
"""
import argparse
import difflib
import json
import math
import os
import random
import re
import subprocess
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from scene import world, BW, BH, BAYER
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, W, H = 30, 1080, 1920
PIXEL = os.path.join(HERE, "fonts", "PressStart2P-Regular.ttf")
RUSSO = os.path.join(HERE, "fonts", "RussoOne-Regular.ttf")
WHITE, YELLOW, RED, NIGHTY, PURPLE = (255, 255, 255), (255, 210, 58), (226, 38, 44), (255, 222, 150), (158, 88, 255)
CPS = 14.8                     # символов в секунду для теста
LEAD = 0.4                     # пауза до первого слова
SCENE_GAP = 0.35
TAIL = 3.2                     # концовка «ЧТО ТАМ ВНИЗУ?»
FADE = 0.5                     # пиксельное растворение при смене сцен
CAM_MOVE = 0.9                 # переезд камеры между сценами
WORD_Y, KEY_Y = 1500, 1420      # слово по одному; ключевая фраза в две строки
NAMES = {15: ("АНЯ", "Аня", 468, 524)}   # жёлтое имя: сцена → (надпись, слово, x, y в мире)


def clean(w):
    return "".join(c for c in w if c.isalnum() or c == "-").upper()


def words_of(marked):
    out, key = [], False
    for tok in re.split(r"(\*\*)", marked):
        if tok == "**":
            key = not key
            continue
        for w in tok.split():
            if clean(w):
                out.append({"raw": w, "text": clean(w), "key": key})
    return out


# ---------- тайминг ----------
def timeline_test():
    t, scenes = LEAD, []
    for n, label, marked in SCENES:
        ws = words_of(marked)
        s0 = t
        for w in ws:
            w["t0"] = t
            t += (len(w["raw"]) + 1) / CPS
            if w["raw"][-1] in ".!?:—":
                t += 0.22
            elif w["raw"][-1] == ",":
                t += 0.08
            w["t1"] = t
        scenes.append({"n": n, "label": label, "start": s0, "words": ws})
        t += SCENE_GAP
    return finish(scenes)


def timeline_user():
    stt = json.load(open(os.path.join(HERE, "voice_user", "stt.json")))
    heard = [w for w in stt["words"] if w.get("type", "word") == "word" and clean(w["text"])]
    allw, scenes = [], []
    for n, label, marked in SCENES:
        ws = words_of(marked)
        scenes.append({"n": n, "label": label, "words": ws})
        allw += ws
    sm = difflib.SequenceMatcher(None, [w["text"].replace("Ё", "Е") for w in allw],
                                 [clean(w["text"]).replace("Ё", "Е") for w in heard], autojunk=False)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            allw[a + k]["t0"], allw[a + k]["t1"] = heard[b + k]["start"] + LEAD, heard[b + k]["end"] + LEAD
    for i, w in enumerate(allw):            # слова без пары — между соседями
        if "t0" not in w:
            prev = next((allw[j]["t1"] for j in range(i - 1, -1, -1) if "t1" in allw[j]), LEAD)
            nxt = next((allw[j]["t0"] for j in range(i + 1, len(allw)) if "t0" in allw[j]), prev + 0.4)
            w["t0"], w["t1"] = prev, max(prev + 0.05, (prev + nxt) / 2)
    for i, s in enumerate(scenes):
        s["start"] = 0.0 if i == 0 else max(scenes[i - 1]["words"][-1]["t1"] + 0.02, s["words"][0]["t0"] - 0.25)
    return finish(scenes)


def finish(scenes):
    for i, s in enumerate(scenes):
        s["start"] = 0.0 if i == 0 else s["start"]
        s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else s["words"][-1]["t1"] + TAIL
        ws = s["words"]
        for j, w in enumerate(ws):           # слово держится до следующего
            w["show"] = ws[j + 1]["t0"] if j + 1 < len(ws) else min(w["t1"] + 0.5, s["end"])
        # мелкая строка: по предложениям; длинное — пополам по запятой/тире или по середине
        sents, cur = [], []
        for w in ws:
            cur.append(w)
            if w["raw"][-1] in ".!?:":
                sents.append(cur); cur = []
        if cur:
            sents.append(cur)
        chunks = []
        def split(c):
            ln = lambda c: sum(len(x["raw"]) + 1 for x in c)
            if ln(c) <= 34 or len(c) < 2:
                chunks.append(c); return
            best = min(range(1, len(c)), key=lambda j: abs(ln(c[:j]) - ln(c) / 2) -
                       (6 if c[j - 1]["raw"][-1] in ",—" or c[j]["raw"] == "—" else 0))
            split(c[:best]); split(c[best:])
        for c in sents:
            split(c)
        for c in chunks:
            line = " ".join(x["raw"] for x in c).replace("**", "")
            for x in c:
                x["line"] = line
    return scenes


# ---------- надписи (пиксельный шрифт, как в «Сюжете фильма») ----------
SPR = {}


def pix(text, k, color):
    """Пиксельное слово: шрифт 8 px без сглаживания, чёрная обводка в 1 «пиксель», тень, увеличение ×k."""
    key = (text, k, color)
    if key in SPR:
        return SPR[key]
    f = ImageFont.truetype(PIXEL, 8)
    w = int(f.getlength(text)) + 4
    m = Image.new("L", (w, 12), 0)
    ImageDraw.Draw(m).text((2, 2), text, font=f, fill=255, fontmode="1")
    a = np.asarray(m) > 0
    ring = np.zeros_like(a)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ring |= np.roll(np.roll(a, dy, 0), dx, 1)
    sh = np.roll(np.roll(ring, 1, 0), 1, 1) & ~ring
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[sh] = (0, 0, 0, 150)
    rgba[ring] = (0, 0, 0, 255)
    rgba[a] = (*color, 255)
    ys, xs = np.where(rgba[..., 3] > 0)
    rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray(rgba, "RGBA")
    SPR[key] = im.resize((im.width * k, im.height * k), Image.NEAREST)
    return SPR[key]


def kfit(text, k, maxw=W - 90):
    while k > 2 and (len(text) * 8 + 2) * k > maxw:
        k -= 1
    return k


def paste_c(img, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.NEAREST)
    if alpha < 1.0:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(spr, (int(cx - spr.width / 2) // 2 * 2, int(cy - spr.height / 2) // 2 * 2), spr)


def pop(t, t0, d=0.12):
    p = min(1, max(0, (t - t0) / d))
    return 0.7 + 0.3 * p + 0.12 * math.sin(p * math.pi), p


def typed(w, t):
    """Сколько букв слова уже «напечатано» к моменту t."""
    n = len(w["text"])
    k = int(n * min(1, max(0, (t - w["t0"]) / max(0.05, w["t1"] - w["t0"]))) + 0.999)
    return w["text"][:k]


def captions(img, s, t):
    ws = s["words"]
    key = [w for w in ws if w["key"]]
    if key and key[0]["t0"] - 0.05 <= t <= key[-1]["t1"] + 0.45:      # ключевая фраза: две строки, вторая фиолетовая
        half = math.ceil(len(key) / 2)
        lines = [key[:half], key[half:]] if len(key) > 1 else [key]
        cols = [WHITE, PURPLE] if len(lines) == 2 else [PURPLE]
        k = min(kfit(" ".join(w["text"] for w in ln), 10) for ln in lines)
        ys = [KEY_Y, KEY_Y + int(8 * k * 1.35)] if len(lines) == 2 else [KEY_Y + 50]
        for ln, col, y in zip(lines, cols, ys):
            shown = " ".join(x for x in (typed(w, t) for w in ln) if x)
            if shown:
                full = pix(" ".join(w["text"] for w in ln), k, col)
                im = pix(shown, k, col)
                img.paste(im, (int(W / 2 - full.width / 2) // 2 * 2, int(y - im.height / 2) // 2 * 2), im)
        return
    cur = None
    for i, w in enumerate(ws):
        nxt = ws[i + 1]["t0"] if i + 1 < len(ws) else w["t1"] + 0.35
        if not w["key"] and w["t0"] <= t < max(nxt, w["t1"]):
            cur = w
    if cur:
        sc, _ = pop(t, cur["t0"], 0.1)
        paste_c(img, pix(cur["text"], kfit(cur["text"], 6), WHITE), W / 2, WORD_Y, sc)


def title(img, lines, t0, t):
    """Заголовок по буквам: [(текст, цвет, k, y)], буквы печатаются за ~0.9 с."""
    total = sum(len(x[0]) for x in lines)
    n = int(total * min(1, max(0, (t - t0) / 0.9)))
    for txt, col, k, y in lines:
        cell = 8 * k
        x0 = W / 2 - len(txt) * cell / 2
        for i, ch in enumerate(txt[:n]):
            if ch != " ":
                paste_c(img, pix(ch, k, col), x0 + i * cell + cell / 2, y)
        n -= len(txt)
        if n <= 0:
            break


def label_num(label):
    m = re.match(r"(\D+)(\d+)", label)
    return (m.group(1).strip(), int(m.group(2))) if m else (label, None)


# ---------- камера ----------
VW, VH, S3 = 360, 640, 3        # видимая часть мира 360×640, пиксель ×3 → 1080×1920


def cam_target(f):
    return (min(max(f[0], VW / 2), BW - VW / 2), min(max(f[1] - 110, VH / 2), BH - VH / 2))


def halftone():
    yy, xx = np.mgrid[0:H, 0:W]
    step = 9
    d = np.hypot((xx % step) - step / 2, (yy % step) - step / 2)
    return np.clip(2.2 - d, 0, 1).astype(np.float32)


# ---------- кадр ----------
G = {}


def frame(fi):
    T = fi / FPS
    scenes = G["scenes"]
    i = max(j for j, s in enumerate(scenes) if s["start"] <= T or j == 0)
    s = scenes[i]
    p = min(1.0, (T - s["start"]) / max(0.01, s["end"] - s["start"]))
    img, focus = world(s["n"], p, T)
    cx, cy = cam_target(focus)
    if i > 0:
        k = (T - s["start"]) / CAM_MOVE
        if k < 1:                            # камера плавно переезжает к новой сцене
            e = k * k * (3 - 2 * k)
            px, py = G["endcam"][i - 1]
            cx, cy = px + (cx - px) * e, py + (cy - py) * e
        if T - s["start"] < FADE:            # пиксельное «растворение» старой сцены
            prev, _ = world(scenes[i - 1]["n"], 1.0, T)
            k = (T - s["start"]) / FADE
            m = (BAYER < k)[..., None]
            img = Image.fromarray(np.where(m, np.asarray(img), np.asarray(prev)))
    # тряска на стуке и трещине
    if s["n"] == 20 and p > 0.25:
        r = random.Random(fi); cx += r.randint(-2, 2); cy += r.randint(-2, 2)
    elif s["n"] in (14, 19) and (T * 1.3) % 1 < 0.35:
        r = random.Random(fi); cx += r.randint(-1, 1)
    x0, y0 = int(round(cx * S3 - W / 2)), int(round(cy * S3 - H / 2))
    x0, y0 = min(max(x0, 0), BW * S3 - W), min(max(y0, 0), BH * S3 - H)
    # вырезаем только нужный кусок и увеличиваем ×3 без сглаживания
    wx0, wy0 = x0 // S3, y0 // S3
    part = img.crop((wx0, wy0, wx0 + VW + 1, wy0 + VH + 1)).resize(((VW + 1) * S3, (VH + 1) * S3), Image.NEAREST)
    part = part.crop((x0 - wx0 * S3, y0 - wy0 * S3, x0 - wx0 * S3 + W, y0 - wy0 * S3 + H))
    fr = np.asarray(part).astype(np.float32)
    lum = fr.mean(2, keepdims=True) / 255   # точечный растр на тёмных местах, как в фильмах
    fr = fr * (1 - 0.2 * G["dots"][..., None] * np.clip(1 - lum * 1.6, 0, 1))
    fr *= G["vig"]
    if s["n"] == 1:
        fr *= 0.85
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
    if G["clean"]:
        return img.convert("RGB").tobytes()
    # счётчик дней (крутится при смене)
    word, num = label_num(s["label"])
    col = NIGHTY if "НОЧЬ" in s["label"] else WHITE
    if num is not None and i > 0:
        pw, pn = label_num(scenes[i - 1]["label"])
        k = min(1.0, (T - s["start"]) / 0.6)
        if pn is not None and pn != num:
            num = int(round(pn + (num - pn) * (1 - (1 - k) ** 2)))
    hud = pix(f"{word} {num}" if num is not None else word, 5, col)
    img.paste(hud, (50, 64), hud)
    if i == 0:
        title(img, [("100 ДНЕЙ", WHITE, 9, 330), ("В БУНКЕРЕ", RED, 9, 430)], 0.15, T)
    last = scenes[-1]
    tend = last["words"][-1]["t1"] + 0.5
    if T > tend:
        title(img, [("ЧТО ТАМ", WHITE, 10, 360), ("ВНИЗУ?", RED, 12, 480)], tend, T)
        if T > tend + 1.0:
            paste_c(img, pix("ЧАСТЬ 2 — СКОРО", 5, PURPLE), W / 2, 590)
    if s["n"] in NAMES:                      # жёлтое имя над героиней
        name, w0, wx, wy = NAMES[s["n"]]
        tw = next((w["t0"] for w in s["words"] if w["raw"].strip(".,") == w0), None)
        if tw is not None and T >= tw:
            sc, a = pop(T, tw, 0.15)
            paste_c(img, pix(name, 4, YELLOW), wx * S3 - x0, wy * S3 - y0, sc, a)
    if i > 0 or T > 1.2:
        captions(img, s, T)
    return img.convert("RGB").tobytes()


def init(scenes, clean, preview):
    G["scenes"], G["clean"], G["preview"] = scenes, clean, preview
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.3 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.5
    G["vig"] = np.clip(v, 0.6, 1)[..., None].astype(np.float32)
    G["dots"] = halftone()
    G["endcam"] = [cam_target(world(s["n"], 1.0, s["end"])[1]) for s in scenes]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", action="store_true")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--frames", type=str, default="", help="только кадры: секунды через запятую → png")
    a = ap.parse_args()
    scenes = timeline_user() if a.user else timeline_test()
    total = scenes[-1]["end"]
    init(scenes, a.clean, a.preview)
    if a.frames:
        for sec in a.frames.split(","):
            Image.frombytes("RGB", (W, H), frame(int(float(sec) * FPS))).save(os.path.join(HERE, f"frame_{sec}.png"))
        return
    name = "bunker" if a.user else "bunker_test"
    name += "_clean" if a.clean else ""
    name += "_preview" if a.preview else ""
    out = os.path.join(HERE, name + ".mp4")
    nf = int(total * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if a.user:
        cmd += ["-itsoffset", str(LEAD), "-i", os.path.join(HERE, "voice_user", "vo.mp3"), "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "192k", "-shortest"]
    if a.preview:
        cmd += ["-vf", "scale=540:960:flags=neighbor"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=init, initargs=(scenes, a.clean, a.preview)) as pool:
        for k, buf in enumerate(pool.imap(frame, range(nf), chunksize=6)):
            ff.stdin.write(buf)
            if k % 300 == 0:
                print(f"{k}/{nf}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(out, f"{total:.1f} с")


if __name__ == "__main__":
    main()
