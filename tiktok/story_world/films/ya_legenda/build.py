#!/usr/bin/env python3
"""«Я — легенда» · Сюжет фильма за минуту — сборка ролика 1080×1920 для TikTok.

Картинки сцен: frames/01.png … frames/29.png (png/jpg/webp, любой размер 9:16). Нет картинки — серая заглушка.
Голос: voice/NN.mp3 + voice/NN.json (разметка символов ElevenLabs).
python3 build.py [--preview]   →  ya_legenda.mp4 (или ya_legenda_preview.mp4 в 540×960)

Что в кадре: медленный наезд камеры, слова субтитров по одному под голос, ключевые фразы (**…** в script.py)
крупно в две строки — вторая фиолетовая, буквы печатаются под голос; жёлтые имена героев (LABELS),
переход «рваная бумага», точечный растр на тёмных местах. Интро: «Я — ЛЕГЕНДА» по буквам и «СЮЖЕТ / ЗА МИНУТУ».
"""
import argparse
import glob
import json
import math
import os
import subprocess
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
W, H = 1080, 1920
RUSSO = os.path.join(HERE, "fonts", "RussoOne-Regular.ttf")
OSWALD = os.path.join(HERE, "fonts", "Oswald.ttf")
WHITE, PURPLE, YELLOW, RED, BLACK = (255, 255, 255), (138, 61, 255), (255, 210, 58), (226, 38, 44), (0, 0, 0)
GAP = 0.14                                  # пауза между фразами
EXTRA_GAP = {25: 0.35, 26: 0.25, 28: 0.55}  # дольше после сцены N
TAIL = 1.2                                  # конец после последней фразы
TEAR_AT = {2, 5, 11, 18, 22, 27, 29}        # сцены, на которые входим «рваной бумагой» (остальные — склейка)
# жёлтые имена: сцена → [(имя, x, y) в долях кадра]; заполняются по готовым картинкам
LABELS = {
    6: [("Сэм", 0.28, 0.46), ("Невилл", 0.58, 0.47)],
    7: [("Невилл", 0.25, 0.65)],
    8: [("Невилл", 0.40, 0.54)],
    9: [("Сэм", 0.26, 0.55), ("Невилл", 0.50, 0.45)],
    10: [("Невилл", 0.47, 0.32)],
    11: [("Марли", 0.36, 0.72), ("Зои", 0.62, 0.66)],
    12: [("Невилл", 0.75, 0.48)],
    13: [("Вожак", 0.53, 0.09)],
    14: [("Невилл", 0.67, 0.24)],
    15: [("Невилл", 0.36, 0.14)],
    16: [("Сэм", 0.40, 0.24)],
    17: [("Сэм", 0.22, 0.55), ("Невилл", 0.48, 0.36)],
    18: [("Невилл", 0.55, 0.22)],
    19: [("Анна", 0.38, 0.50), ("Итан", 0.70, 0.46)],
    20: [("Анна", 0.24, 0.12), ("Невилл", 0.76, 0.12)],
    22: [("Невилл", 0.67, 0.40)],
    23: [("Невилл", 0.24, 0.10), ("Анна", 0.80, 0.20)],
    24: [("Анна", 0.20, 0.25), ("Итан", 0.42, 0.27)],
    25: [("Невилл", 0.28, 0.20), ("Вожак", 0.72, 0.09)],
    27: [("Анна", 0.22, 0.63), ("Итан", 0.40, 0.69)],
}


# ---------- текст и разметка ----------
def font(path, size, bold=False):
    f = ImageFont.truetype(path, size)
    if path == OSWALD:
        f.set_variation_by_name(b"Bold")
    return f


def sprite(text, size, color, stroke, path=RUSSO):
    """Слово с обводкой → RGBA-картинка (кешируется вызывающим)."""
    f = font(path, size)
    x0, y0, x1, y1 = f.getbbox(text, stroke_width=stroke)
    im = Image.new("RGBA", (x1 - x0 + 4, y1 - y0 + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - x0, 2 - y0), text, font=f, fill=color, stroke_width=stroke, stroke_fill=BLACK)
    return im


def clean(word):
    return "".join(ch for ch in word if ch.isalnum() or ch in "-ё").upper()


def load_scene(n, marked):
    a = json.load(open(os.path.join(HERE, "voice", f"{n:02d}.json")))
    chars, st, en = a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"]
    plain = marked.replace("**", "")
    assert "".join(chars) == plain, (n, "".join(chars), plain)
    key = np.zeros(len(plain), bool)          # какие символы — ключевая фраза
    i, inside = 0, False
    for part in marked.split("**"):
        if inside:
            key[i:i + len(part)] = True
        i += len(part)
        inside = not inside
    words, cur = [], None                     # слово: текст, начало, конец, ключевое?, символы с временами
    for k, ch in enumerate(plain):
        if ch.isspace():
            cur = None
            continue
        if cur is None:
            cur = {"chars": [], "key": bool(key[k])}
            words.append(cur)
        cur["chars"].append((ch, st[k], en[k]))
    out = []
    for w in words:
        txt = clean("".join(c for c, _, _ in w["chars"]))
        if not txt:
            continue
        out.append({"text": txt, "t0": w["chars"][0][1], "t1": w["chars"][-1][2], "key": w["key"],
                    "chars": [(c.upper(), s) for c, s, _ in w["chars"] if clean(c)]})
    return out


def timeline():
    t, scenes = 0.25, []
    for n, names, marked in SCENES:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    os.path.join(HERE, "voice", f"{n:02d}.mp3")], capture_output=True, text=True).stdout)
        words = load_scene(n, marked)
        for w in words:
            w["t0"] += t; w["t1"] += t
            w["chars"] = [(c, s + t) for c, s in w["chars"]]
        scenes.append({"n": n, "start": t, "voice": t, "dur": dur, "words": words})
        t += dur + GAP + EXTRA_GAP.get(n, 0)
    for i, s in enumerate(scenes):
        s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else s["voice"] + s["dur"] + TAIL
    return scenes


# ---------- картинки ----------
def scene_image(n):
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = os.path.join(HERE, "frames", f"{n:02d}.{ext}")
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            break
    else:
        im = Image.new("RGB", (540, 960), (40, 42, 50))
        d = ImageDraw.Draw(im)
        for y in range(960):
            d.line([(0, y), (540, y)], fill=(int(30 + 30 * y / 960), int(32 + 26 * y / 960), int(44 + 20 * y / 960)))
        f = font(RUSSO, 60)
        d.text((270, 480), f"СЦЕНА {n:02d}", font=f, fill=(150, 150, 165), anchor="mm")
    # под 9:16 с запасом под наезд камеры (×1.1)
    tw, th = int(W * 1.1), int(H * 1.1)
    r = max(tw / im.width, th / im.height)
    im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    x, y = (im.width - tw) // 2, (im.height - th) // 2
    return im.crop((x, y, x + tw, y + th))


def halftone():
    yy, xx = np.mgrid[0:H, 0:W]
    step = 9
    d = np.hypot((xx % step) - step / 2, (yy % step) - step / 2)
    return np.clip(2.2 - d, 0, 1).astype(np.float32)


# ---------- кадр ----------
G = {}


def init(scenes, scale):
    G["scenes"], G["scale"] = scenes, scale
    G["img"], G["spr"] = {}, {}
    G["dots"] = halftone()
    rng = np.random.default_rng(5)
    G["tear"] = {s["n"]: np.cumsum(rng.normal(0, 3.2, H)).clip(-40, 40) for s in scenes}


def img(n):
    if n not in G["img"]:
        G["img"][n] = scene_image(n)
    return G["img"][n]


def spr(key, *args):
    if key not in G["spr"]:
        G["spr"][key] = sprite(*args)
    return G["spr"][key]


def camera(s, t, i):
    """Наезд: чётные сцены приближаются, нечётные отъезжают; лёгкий сдвиг."""
    im = img(s["n"])
    p = min(1, max(0, (t - s["start"]) / max(0.1, s["end"] - s["start"])))
    p = p * p * (3 - 2 * p) * 0.6 + p * 0.4
    z = 1.0 + 0.08 * (p if i % 2 == 0 else 1 - p)
    cw, ch = im.width / z, im.height / z
    dx = (im.width - cw) * (0.5 + 0.25 * math.sin(i * 1.7) * (p - 0.5))
    dy = (im.height - ch) * 0.5
    crop = im.crop((int(dx), int(dy), int(dx + cw), int(dy + ch)))
    return np.asarray(crop.resize((W, H), Image.BILINEAR), dtype=np.float32)


def paste(frame, im, cx, cy, alpha=1.0, scale=1.0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    a = np.asarray(im, dtype=np.float32)
    x0, y0 = int(cx - im.width / 2), int(cy - im.height / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + im.width), min(H, y0 + im.height)
    if xa >= xb or ya >= yb:
        return
    part = a[ya - y0:yb - y0, xa - x0:xb - x0]
    al = part[..., 3:4] / 255 * alpha
    frame[ya:yb, xa:xb] = part[..., :3] * al + frame[ya:yb, xa:xb] * (1 - al)


def pop(t, t0, d=0.12):
    """Появление с лёгким «прыжком» масштаба."""
    p = min(1, max(0, (t - t0) / d))
    return 0.7 + 0.3 * p + 0.12 * math.sin(p * math.pi), p


def captions(frame, s, t):
    words = s["words"]
    # ключевые фразы: все ключевые слова сцены одной группой
    key = [w for w in words if w["key"]]
    if key and key[0]["t0"] - 0.05 <= t <= key[-1]["t1"] + 0.45:
        half = math.ceil(len(key) / 2)
        lines = [key[:half], key[half:]] if len(key) > 1 else [key]
        cols = [WHITE, PURPLE] if len(lines) == 2 else [PURPLE]
        size = 118
        for ln in lines:                              # ужать, если строка не влезает
            full = " ".join(w["text"] for w in ln)
            while sprite(full, size, WHITE, 9).width > W - 90 and size > 60:
                size -= 6
        ys = [1120, 1120 + size + 6] if len(lines) == 2 else [1180]
        for ln, col, y in zip(lines, cols, ys):
            shown = []
            for w in ln:
                typed = "".join(c for c, st in w["chars"] if st <= t)
                if typed:
                    shown.append(typed if len(typed) < len(w["text"]) else w["text"])
            if shown:
                txt = " ".join(shown)
                full = " ".join(w["text"] for w in ln)
                fs = spr(("full", full, size), full, size, col, 9)
                im = spr(("k", txt, size, col), txt, size, col, 9)
                left = W / 2 - fs.width / 2                   # строка растёт слева направо, без прыжков центра
                paste(frame, im, left + im.width / 2, y)
        return
    # обычные слова по одному
    cur = None
    for i, w in enumerate(words):
        nxt = words[i + 1]["t0"] if i + 1 < len(words) else w["t1"] + 0.35
        if not w["key"] and w["t0"] <= t < max(nxt, w["t1"]):
            cur = w
    if cur:
        sc, _ = pop(t, cur["t0"], 0.1)
        paste(frame, spr(("w", cur["text"]), cur["text"], 70, WHITE, 7), W / 2, 1500, 1.0, sc)


def labels(frame, s, t):
    for j, (name, fx, fy) in enumerate(LABELS.get(s["n"], [])):
        t0 = s["start"] + 0.15 + 0.12 * j
        if t >= t0:
            sc, p = pop(t, t0, 0.15)
            paste(frame, spr(("l", name), name.upper(), 44, YELLOW, 6), fx * W, fy * H, p, sc)


def intro(frame, s, t):
    """Сцена 1: «Я — ЛЕГЕНДА» по буквам сверху и «СЮЖЕТ / ЗА МИНУТУ» под голос."""
    words = s["words"]
    title = [w for w in words if w["text"] in ("Я", "ЛЕГЕНДА")]
    sub = [w for w in words if w["text"] in ("СЮЖЕТ", "ЗА", "МИНУТУ")]
    # заголовок: буквы появляются с начала голоса, до конца слова «легенда»
    t_a, t_b = s["voice"] - 0.1, title[-1]["t1"] if title else s["voice"] + 1
    letters = list("Я — ЛЕГЕНДА")
    k = int(len(letters) * min(1, max(0, (t - t_a) / max(0.2, t_b - t_a)))) if t >= t_a else 0
    size = 190
    while font(OSWALD, size).getlength("Я — ЛЕГЕНДА") > W - 150:
        size -= 4
    f = font(OSWALD, size)
    x = W / 2 - f.getlength("Я — ЛЕГЕНДА") / 2
    for i, ch in enumerate(letters[:k]):
        col = WHITE if i < 3 else RED
        im = spr(("t", ch, col, size), ch, size, col, 8, OSWALD) if ch != " " else None
        if im:
            paste(frame, im, x + f.getlength(ch) / 2, 300)
        x += f.getlength(ch)
    if k == len(letters):                             # черта под заголовком
        frame[420:428, 90:W - 90] = frame[420:428, 90:W - 90] * 0.2 + np.array(WHITE, np.float32) * 0.8
    # «СЮЖЕТ» фиолетовым и «ЗА МИНУТУ» белым, печатаются под голос
    for txt, col, y, size, ws in (("СЮЖЕТ", PURPLE, 1180, 170, sub[:1]), ("ЗА МИНУТУ", WHITE, 1340, 104, sub[1:])):
        typed = "".join(c for w in ws for c, st in w["chars"] if st <= t)
        if len(ws) == 2 and typed and sub[1]["t1"] <= t:
            typed = "ЗА МИНУТУ"
        elif len(ws) == 2 and len(typed) > 2:
            typed = typed[:2] + " " + typed[2:]
        if typed:
            fs = spr(("full", txt, size), txt, size, col, 10)
            im = spr(("i", typed, col, size), typed, size, col, 10)
            paste(frame, im, W / 2 - fs.width / 2 + im.width / 2, y)


def render(fi):
    t = fi / FPS
    scenes = G["scenes"]
    i = max(j for j, s in enumerate(scenes) if s["start"] <= t) if t >= scenes[0]["start"] else 0
    s = scenes[i]
    frame = camera(s, t, i)
    # переход «рваная бумага»: новая сцена заезжает справа
    if s["n"] in TEAR_AT and i > 0 and t < s["start"] + 0.32:
        p = (t - s["start"]) / 0.32
        p = 1 - (1 - p) ** 3
        old = camera(scenes[i - 1], t, i - 1)
        edge = (W * (1 - p) + G["tear"][s["n"]]).astype(int)
        xs = np.arange(W)[None, :]
        new_mask = xs >= edge[:, None]
        paper = (xs >= edge[:, None] - 16) & ~new_mask
        shadow = np.clip(1 - (edge[:, None] - 16 - xs) / 60, 0, 1) * (xs < edge[:, None] - 16)
        out = np.where(new_mask[..., None], frame, old * (1 - 0.45 * shadow[..., None]))
        out[paper] = (238, 232, 220)
        frame = out
    # точечный растр на тёмных местах
    lum = frame.mean(2, keepdims=True) / 255
    frame = frame * (1 - 0.22 * G["dots"][..., None] * np.clip(1 - lum * 1.6, 0, 1))
    if s["n"] == 1:
        frame *= 0.82                                 # притемнить под надписи интро
        intro(frame, s, t)
    else:
        labels(frame, s, t)
        captions(frame, s, t)
    if t < 0.25:                                      # из чёрного
        frame *= t / 0.25
    out = np.clip(frame, 0, 255).astype(np.uint8)
    if G["scale"] != 1:
        out = np.asarray(Image.fromarray(out).resize((int(W * G["scale"]), int(H * G["scale"])), Image.BILINEAR))
    return out.tobytes()


# ---------- звук ----------
def audio(scenes, total, sr=44100):
    n = int(total * sr)
    mix = np.zeros(n, np.float32)
    for s in scenes:
        v = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "voice", f"{s['n']:02d}.mp3"),
                                          "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout,
                          np.float32)
        a = int(s["voice"] * sr)
        mix[a:a + len(v)] += v[:n - a]
    t = np.arange(n) / sr
    rng = np.random.default_rng(3)
    # тёмный гул: ля минор, медленное дыхание
    drone = sum(np.sin(2 * np.pi * f * t + ph) * g for f, ph, g in ((55, 0, 1), (82.4, 1, .55), (110, 2, .35), (130.8, 3, .18)))
    drone *= 0.6 + 0.4 * np.sin(2 * np.pi * t / 7.5)
    noise = np.convolve(rng.normal(0, 1, n), np.ones(400) / 400, "same") * 6
    bed = (drone * 0.022 + noise * 0.01).astype(np.float32)
    bed *= np.clip(t / 2, 0, 1) * np.clip((total - t) / 1.5, 0, 1)
    mix += bed
    for s in scenes:                                  # шорох на «рваной бумаге»
        if s["n"] in TEAR_AT and s["n"] > 1:
            a = int(s["start"] * sr); m = int(0.35 * sr)
            w = rng.normal(0, 1, m) * np.exp(-np.linspace(0, 5, m)) * np.linspace(1.4, 0.2, m)
            w = np.diff(np.concatenate([[0], w]))
            mix[a:a + m] += (w * 0.09).astype(np.float32)[:n - a]
        if s["n"] == 26:                              # взрыв
            a = int((s["start"] - 0.05) * sr); m = int(2.2 * sr); tt = np.arange(m) / sr
            boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tt * 3) + 28) / sr) * np.exp(-tt * 2.2)
            boom += np.convolve(rng.normal(0, 1, m), np.ones(30) / 30, "same") * np.exp(-tt * 3) * 2.5
            mix[a:a + m] += (boom * 0.5).astype(np.float32)[:n - a]
    mix /= max(1e-6, np.abs(mix).max()) / 0.92
    return mix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="540×960, быстро")
    a = ap.parse_args()
    scenes = timeline()
    total = scenes[-1]["end"]
    nfr = int(total * FPS)
    scale = 0.5 if a.preview else 1
    out = os.path.join(HERE, "ya_legenda_preview.mp4" if a.preview else "ya_legenda.mp4")
    wav = os.path.join(HERE, "_audio.f32")
    audio(scenes, total).tofile(wav)
    have = sorted(glob.glob(os.path.join(HERE, "frames", "*.*")))
    print(f"длина {total:.1f} с, кадров {nfr}, картинок в frames/: {len(have)} из {len(scenes)}", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{int(W * scale)}x{int(H * scale)}", "-r", str(FPS), "-i", "-",
                           "-f", "f32le", "-ar", "44100", "-ac", "1", "-i", wav,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "23" if a.preview else "17",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=init, initargs=(scenes, scale)) as pool:
        for k, fr in enumerate(pool.imap(render, range(nfr), chunksize=8)):
            ff.stdin.write(fr)
            if k % 300 == 0:
                print(f"  {k}/{nfr}", flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("готово:", out)


if __name__ == "__main__":
    main()
