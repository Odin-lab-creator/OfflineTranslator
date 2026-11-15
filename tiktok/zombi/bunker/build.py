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

from scene import world, BW, BH, K
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, W, H = 30, 1080, 1920
PIXEL = os.path.join(HERE, "fonts", "PressStart2P-Regular.ttf")
RUSSO = os.path.join(HERE, "fonts", "RussoOne-Regular.ttf")
WHITE, YELLOW, RED, NIGHTY = (255, 255, 255), (255, 214, 64), (232, 44, 44), (255, 222, 150)
CPS = 14.8                     # символов в секунду для теста
LEAD = 0.4                     # пауза до первого слова
SCENE_GAP = 0.35
TAIL = 3.2                     # концовка «ЧТО ТАМ ВНИЗУ?»
FADE = 0.45                    # плавная смена сцен
WORD_Y, LINE_Y = 1470, 1600    # крупное слово и мелкая строка (над подписью TikTok)
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


# ---------- надписи ----------
SPR = {}


def txt(text, size, color, stroke=None):
    """Слово шрифтом Russo One: чёрная обводка и мягкая тень."""
    key = ("txt", text, size, color)
    if key in SPR:
        return SPR[key]
    stroke = stroke or max(3, size // 12)
    f = ImageFont.truetype(RUSSO, size)
    x0, y0, x1, y1 = f.getbbox(text, stroke_width=stroke)
    pad = 14
    im = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - x0 + 3, pad - y0 + 6), text, font=f, fill=(0, 0, 0, 160), stroke_width=stroke,
                            stroke_fill=(0, 0, 0, 160))
    sh = sh.filter(ImageFilter.GaussianBlur(4))
    ImageDraw.Draw(im).text((pad - x0, pad - y0), text, font=f, fill=color, stroke_width=stroke, stroke_fill=(10, 8, 10))
    SPR[key] = Image.alpha_composite(sh, im)
    return SPR[key]


def fit(text, size, maxw=980):
    f = ImageFont.truetype(RUSSO, size)
    w = f.getlength(text)
    return int(size * min(1.0, maxw / max(1, w)))


def small(text, size=38):
    key = ("small", text, size)
    if key not in SPR:
        f = ImageFont.truetype(RUSSO, size)
        x0, y0, x1, y1 = f.getbbox(text, stroke_width=4)
        im = Image.new("RGBA", (x1 - x0 + 8, y1 - y0 + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - x0, 4 - y0), text, font=f, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
        SPR[key] = im
    return SPR[key]


def paste_c(img, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if alpha < 1.0:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def label_num(label):
    m = re.match(r"(\D+)(\d+)", label)
    return (m.group(1), int(m.group(2))) if m else (label, None)


# ---------- кадр ----------
G = {}


def frame(fi):
    T = fi / FPS
    scenes = G["scenes"]
    i = max(j for j, s in enumerate(scenes) if s["start"] <= T or j == 0)
    s = scenes[i]
    p = min(1.0, (T - s["start"]) / max(0.01, s["end"] - s["start"]))
    img = world(s["n"], p, T)
    if i > 0 and T - s["start"] < FADE:     # плавная смена
        prev = world(scenes[i - 1]["n"], 1.0, T)
        k = (T - s["start"]) / FADE
        img = Image.blend(prev, img, k * k * (3 - 2 * k))
    img = img.resize((BW * K, BH * K), Image.NEAREST).convert("RGB")
    # тряска на стуке и трещине
    shake = 0
    if s["n"] == 20 and p > 0.25:
        shake = 6
    elif s["n"] in (14, 19) and (T * 1.3) % 1 < 0.35:
        shake = 3
    if shake:
        r = random.Random(fi)
        img = img.transform(img.size, Image.AFFINE, (1, 0, r.randint(-shake, shake), 0, 1, r.randint(-shake, shake)))
    # виньетка
    img = Image.fromarray((np.asarray(img).astype(np.float32) * G["vig"]).astype(np.uint8))
    if G["clean"]:
        return img.tobytes()
    img = img.convert("RGBA")
    # счётчик дней (крутится при смене)
    word, num = label_num(s["label"])
    col = NIGHTY if "НОЧЬ" in s["label"] else WHITE
    if num is not None and i > 0:
        pw, pn = label_num(scenes[i - 1]["label"])
        k = min(1.0, (T - s["start"]) / 0.6)
        if pn is not None and pn != num:
            num = int(round(pn + (num - pn) * (1 - (1 - k) ** 2)))
    hud = txt(f"{word.strip()} {num}" if num is not None else word, 52, col)
    img.paste(hud, (44, 50), hud)
    # название в начале
    if i == 0:
        a = 1.0 if p < 0.85 else max(0.0, 1 - (p - 0.85) / 0.15)
        k1 = min(1.0, T / 0.5)
        paste_c(img, txt("100 ДНЕЙ", 124, WHITE), W / 2, 330, scale=0.85 + 0.15 * (1 - (1 - k1) ** 3), alpha=a * k1)
        if T > 0.5:
            k2 = min(1.0, (T - 0.5) / 0.4)
            paste_c(img, txt("В БУНКЕРЕ", 124, RED), W / 2, 470, scale=1.25 - 0.25 * (1 - (1 - k2) ** 3), alpha=a * k2)
    # концовка
    last = scenes[-1]
    tend = last["words"][-1]["t1"] + 0.5
    if T > tend:
        k = min(1.0, (T - tend) / 0.4)
        e = 1 - (1 - k) ** 3
        paste_c(img, txt("ЧТО ТАМ", 116, WHITE), W / 2, 330, scale=0.8 + 0.2 * e, alpha=k)
        paste_c(img, txt("ВНИЗУ?", 140, RED), W / 2, 470, scale=0.8 + 0.2 * e, alpha=k)
        if T > tend + 0.6:
            paste_c(img, small("часть 2 — скоро", 46), W / 2, 590)
    # имя героини
    if s["n"] in NAMES:
        name, w0, x, y = NAMES[s["n"]]
        tw = next((w["t0"] for w in s["words"] if w["raw"].strip(".,") == w0), None)
        if tw is not None and T >= tw:
            k = min(1.0, (T - tw) / 0.25)
            paste_c(img, txt(name, 44, YELLOW), x * K, y * K - 40 + 20 * (1 - k), alpha=k)
    # субтитры
    cur = next((w for w in s["words"] if w["t0"] <= T < w["show"]), None)
    if cur is not None:
        k = min(1.0, (T - cur["t0"]) / 0.12)
        e = 1 - (1 - k) ** 3
        spr = txt(cur["text"], fit(cur["text"], 92), YELLOW if cur["key"] else WHITE)
        paste_c(img, spr, W / 2, WORD_Y + 10 * (1 - e), scale=0.88 + 0.12 * e, alpha=0.35 + 0.65 * e)
        paste_c(img, small(cur["line"]), W / 2, LINE_Y)
    return img.convert("RGB").tobytes()


def init(scenes, clean, preview):
    G["scenes"], G["clean"], G["preview"] = scenes, clean, preview
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.5
    G["vig"] = np.clip(v, 0.55, 1)[..., None].astype(np.float32)


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
