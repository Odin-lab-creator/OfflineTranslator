#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ — история за минуту»: короткий ролик в стиле «История за минуту».

python3 minute_build.py [preview]  →  zapertyy_minute.mp4 (1080×1920, 60 к/с)

Кадры на весь экран (PixelLab Pro 360×640 из art/test_pro), медленный наезд камеры, пыль;
субтитры по одному слову точно по голосу (разметка ElevenLabs), заголовок и имена по буквам;
переходы: перелистывание страницы, рывок вбок, кадр, разрезанный по диагонали на две панели.
Звук: рассказчик (voice/), музыка и шумы синтезированы кодом.
"""
import functools
import json
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import comic_engine as ce  # noqa: E402  (шумы и звуковые утилиты)
from minute_lines import LINES, path  # noqa: E402

PRO = os.path.join(ROOT, "art", "test_pro")
OUT = os.path.join(HERE, "zapertyy_minute.mp4")
W, H, FPS, SR = 1080, 1920, 60, 44100
F_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
YELLOW, WHITE, BLACK = (255, 208, 64), (250, 248, 244), (8, 8, 10)
KEY = {"денису", "решётки", "снаружи", "эхо", "автобусам", "заварили", "внутри", "подпишись", "серии"}
XF = 0.38                                                  # длительность перехода


# ------------------------------------------------------------------ голос и слова
def load_line(i):
    v = ce.load_audio(path(i))
    al = json.load(open(path(i, "json")))
    words, cur, t0, t1 = [], "", None, None
    for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                words.append((cur, t0, t1))
            cur, t0 = "", None
            continue
        if t0 is None:
            t0 = a
        cur += ch
        t1 = b
    if cur:
        words.append((cur, t0, t1))
    return v, words


VOICE = {i: load_line(i) for i, _ in LINES}


def clean(w):
    return w.strip(".,!?…:;«»\"—–-").strip()


# ------------------------------------------------------------------ таймлайн
class T:
    t = 0.0


said, words_tl, sfx, shots, cards = [], [], [], [], []


def say(i, gap=0.35):
    v, ws = VOICE[i]
    t0 = T.t
    said.append((t0, i))
    for w, a, b in ws:
        c = clean(w)
        if c:
            words_tl.append((t0 + a, t0 + b, c))
    T.t += len(v) / SR + gap
    return t0, ws


def word_time(t0, ws, text, nth=0):
    hits = [a for w, a, b in ws if clean(w).lower() == text]
    return t0 + hits[min(nth, len(hits) - 1)]


def shot(img, cam0, cam1, trans="curl", at=None, **ex):
    t0 = T.t if at is None else at
    if shots:
        shots[-1]["t1"] = t0
    shots.append(dict(t0=t0, t1=None, img=img, c0=cam0, c1=cam1, trans=trans, ex=ex))


KICKS, RATTLES = [], []

shot("01_wake", (1.0, 180, 360), (1.18, 200, 420), trans=None, eyelids=True, dust=True)
cards.append((0.0, 3.4, "title"))
T.t = 0.7
say("01", 0.3)
shot("06_stand", (1.15, 185, 330), (1.0, 180, 320), dust=True)
t, ws = say("02")
cards.append((t, t + 2.6, "Денис"))
shot(("07_phone", "08_watch"), (1.05, 180, 300), (1.15, 170, 320), trans="split")
say("03")
shot("10_tap", (1.0, 180, 330), (1.12, 190, 300), trans="whip")
t, ws = say("04", 0.4)
sfx.append((word_time(t, ws, "капли") + 0.1, "drip"))
sfx.append((word_time(t, ws, "капли") + 0.55, "drip"))
shot("02_window", (1.0, 180, 330), (1.15, 180, 290), dust=True)
t, ws = say("05")
sfx.append((word_time(t, ws, "решётки") - 0.1, "rattle"))
shot("11_weld", (1.0, 180, 340), (1.12, 175, 330), trans="whip", rattle=True)
t, ws = say("06")
for k in range(4):
    RATTLES.append(t + 0.2 + k * 0.35)
shot(("13_door", "03_corridor"), (1.0, 180, 340), (1.12, 190, 350), trans="split")
sfx.append((T.t + 0.1, "creak"))
say("07")
shot("03_corridor", (1.1, 200, 360), (1.25, 230, 330), trans="whip", shout=True, dust=True)
t, ws = say("08", 0.45)
SHOUT = word_time(t, ws, "кричит")
shot("14_stairs", (1.15, 160, 300), (1.15, 185, 420), dust=True, paint=True)
for k in range(8):
    sfx.append((T.t + 0.15 + k * 0.42, "step"))
say("09")
shot("04_kick", (1.05, 185, 360), (1.12, 195, 360), trans="whip", kick=True)
t, ws = say("10", 0.4)
for w in ("бьёт", "снова"):
    KICKS.append(word_time(t, ws, w))
KICKS.append(word_time(t, ws, "снова", 1))
for k in KICKS:
    sfx.append((k, "bang"))
shot("16_crack", (1.0, 180, 320), (1.2, 225, 300))
t, ws = say("11", 0.45)
shot("05_end", (1.25, 215, 430), (1.05, 190, 400), fade=True, trans="whip")
sfx.append((T.t + 0.2, "slide"))
say("12", 0.5)
shot("05_end", (1.05, 190, 400), (1.0, 180, 380), trans=None, fade_full=True)
say("13", 0.3)
cards.append((T.t - 1.2, T.t + 2.4, "end"))
T.t += 2.4
shots[-1]["t1"] = T.t
TOTAL = T.t
for s in shots[1:]:
    if s["trans"]:
        sfx.append((s["t0"] - XF / 2, "flip" if s["trans"] == "curl" else "whoosh"))


# ------------------------------------------------------------------ картинка
@functools.lru_cache(8)
def base(name):
    a = np.asarray(Image.open(os.path.join(PRO, f"{name}.png")).convert("RGB")).copy()
    for x in range(a.shape[1]):                                  # белые поля по краям у части кадров
        if a[:, x].mean() > 245:
            a[:, x] = a[:, 5 if x < a.shape[1] // 2 else a.shape[1] - 6]
    if name == "14_stairs":                                       # надпись краской над стрелкой
        f = ImageFont.truetype(ce.FONT, 12)
        m = Image.new("1", (130, 18), 0)
        d = ImageDraw.Draw(m)
        d.fontmode = "1"
        d.text((0, 0), "К АВТОБУСАМ", font=f, fill=1)
        ys, xs = np.nonzero(np.asarray(m, bool))
        a[ys + 268, xs + 32] = (168, 58, 46)
    return Image.fromarray(a).resize((a.shape[1] * 6, a.shape[0] * 6), Image.NEAREST)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def jitter(t, times, dur, amp):
    for x in times:
        if 0 <= t - x < dur:
            k = 1 - (t - x) / dur
            return np.random.default_rng(int(t * 1000)).uniform(-amp, amp, 2) * k
    return np.zeros(2)


def camera(name, c0, c1, u, off=(0, 0), extra_zoom=0.0):
    img = base(name)
    BW, BH = img.size
    z, cx, cy = (c0[j] + (c1[j] - c0[j]) * ease(u) for j in range(3))
    z += extra_zoom
    cw, ch = BW / z, BH / z
    x0 = np.clip((cx + off[0]) * BW / 360 - cw / 2, 0, BW - cw)
    y0 = np.clip((cy + off[1]) * BH / 640 - ch / 2, 0, BH - ch)
    return np.asarray(img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))).astype(np.float32)


@functools.lru_cache(1)
def split_masks():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    line = 0.56 * H - (xx / W) * 0.14 * H                        # диагональ панелей
    top = yy < line - 9
    bot = yy > line + 9
    return top, bot


def dust(a, lt):
    r = np.random.default_rng(11)
    n = 80
    px, py = r.uniform(0, W, n), r.uniform(0, H, n)
    vx, vy = r.uniform(-8, 8, n), r.uniform(-22, -5, n)
    ph = r.uniform(0, 6.28, n)
    for k in range(n):
        x, y = int((px[k] + vx[k] * lt) % W), int((py[k] + vy[k] * lt) % H)
        al = 0.25 + 0.2 * np.sin(lt * 1.3 + ph[k])
        a[y:y + 4, x:x + 4] = a[y:y + 4, x:x + 4] * (1 - al) + 235 * al
    return a


def shot_image(s, t):
    lt = t - s["t0"]
    u = lt / max(1e-6, s["t1"] - s["t0"])
    ex = s["ex"]
    off, ez = np.zeros(2), 0.0
    if ex.get("kick"):
        off += jitter(t, KICKS, 0.2, 3.0)
        for x in KICKS:
            if 0 <= t - x < 0.2:
                ez = 0.05 * (1 - (t - x) / 0.2)
    if ex.get("rattle"):
        off += jitter(t, RATTLES, 0.12, 1.5)
    if ex.get("shout") and 0 <= t - SHOUT < 0.8:
        off += np.random.default_rng(int(t * 1000)).uniform(-1, 1, 2)
    if isinstance(s["img"], tuple):                               # две панели по диагонали
        top, bot = split_masks()
        a = np.zeros((H, W, 3), np.float32) + 10
        k = ease(lt / 0.4)
        A = camera(s["img"][0], s["c0"], s["c1"], u, off + (0, -40))
        B = camera(s["img"][1], s["c0"], s["c1"], u, off + (0, 40))
        dx = int((1 - k) * W)
        A = np.roll(A, -dx, 1)
        B = np.roll(B, dx, 1)
        if dx:
            A[:, W - dx:] = 10
            B[:, :dx] = 10
        a[top] = A[top]
        a[bot] = B[bot]
    else:
        a = camera(s["img"], s["c0"], s["c1"], u, off, ez)
    if ex.get("dust"):
        a = dust(a, lt)
    if ex.get("eyelids"):
        k = max(0.0, 1 - lt / 2.2)
        if k > 0:
            h = int(H / 2 * k ** 0.6)
            a[:h] = 0
            a[H - h:] = 0
    if ex.get("fade"):
        a *= 1 - 0.35 * ease(u)
    if ex.get("fade_full"):
        a *= 0.65 - 0.25 * ease(u)
    return a


def curl(A, B, u):
    """Перелистывание: страница загибается справа налево, видна светлая изнанка."""
    fx = int(W * 1.15 * (1 - ease(u)) - W * 0.08)
    out = A.copy()
    if fx < W:
        x0 = max(0, fx)
        out[:, x0:] = B[:, x0:]
        sh = np.clip((np.arange(W) - fx) / 90.0, 0, 1)[None, :, None]      # тень на новой странице у сгиба
        out[:, x0:] *= (0.55 + 0.45 * sh[:, x0:])
    cw = int(70 + 160 * (1 - ease(u)))
    a0, a1 = max(0, fx - cw), max(0, min(W, fx))
    if a1 > a0:
        g = np.linspace(0, 1, a1 - a0)[None, :, None]
        paper = 205 + 45 * np.sin(g * np.pi)                                 # изнанка страницы с объёмом
        out[:, a0:a1] = paper
        out[:, max(0, a0 - 14):a0] *= 0.6                                    # тень от загиба на старой странице
    return out


def whip(A, B, u):
    k = ease(u)
    dx = int(k * W)
    out = np.zeros_like(A)
    out[:, :W - dx] = A[:, dx:]
    out[:, W - dx:] = B[:, :dx]
    blur = np.zeros_like(out)
    for s in range(-24, 25, 8):
        blur += np.roll(out, s, 1)
    return blur / 7


def picture(t):
    i = next((k for k, s in enumerate(shots) if s["t0"] <= t < s["t1"]), len(shots) - 1)
    s = shots[i]
    a = shot_image(s, t)
    if i + 1 < len(shots) and shots[i + 1]["trans"] and t > s["t1"] - XF / 2:
        n = shots[i + 1]
        u = (t - (n["t0"] - XF / 2)) / XF
        B = shot_image(n, n["t0"] + 1e-3)
        a = curl(a, B, u) if n["trans"] == "curl" else whip(a, B, u) if n["trans"] == "whip" else a
    if i > 0 and s["trans"] and t < s["t0"] + XF / 2:
        p = shots[i - 1]
        u = (t - (s["t0"] - XF / 2)) / XF
        A = shot_image(p, s["t0"] - 1e-3)
        a = curl(A, a, u) if s["trans"] == "curl" else whip(A, a, u) if s["trans"] == "whip" else a
    return a


# ------------------------------------------------------------------ текст
@functools.lru_cache(None)
def font(size):
    return ImageFont.truetype(F_BLACK, size)


@functools.lru_cache(4096)
def text_sprite(text, size, color, stroke):
    f = font(size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t_, r, b = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 8, b - t_ + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t_), text, font=f, fill=color, stroke_width=stroke, stroke_fill=BLACK)
    return im


@functools.lru_cache(4096)
def glyph_sprite(ch, size, color, stroke):
    """Буква на холсте общей высоты (по метрикам шрифта): у всех букв одна линия строки."""
    f = font(size)
    asc, desc = f.getmetrics()
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = int(d.textlength(ch, font=f)) + 2 * stroke + 8
    im = Image.new("RGBA", (w, asc + desc + 2 * stroke + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 + stroke, 4 + stroke), ch, font=f, fill=color, stroke_width=stroke, stroke_fill=BLACK)
    return im


def pop(lt, dur=0.14):
    if lt >= dur:
        return 1.0
    u = lt / dur
    return 0.55 + 0.6 * u - 0.15 * u * u * 2 if u < 0.7 else 1.12 - 0.12 * (u - 0.7) / 0.3


def paste_center(frame, sp, cx, cy, scale=1.0, angle=0.0):
    if scale != 1.0:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.BILINEAR)
    if angle:
        sp = sp.rotate(angle, expand=True, resample=Image.BICUBIC)
    frame.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))


def letters(frame, text, t0, t, cx, cy, size, color, step=0.055):
    f = font(size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    total = d.textlength(text, font=f)
    x = cx - total / 2
    for k, ch in enumerate(text):
        w = d.textlength(ch, font=f)
        lt = t - (t0 + k * step)
        if lt >= 0 and ch.strip():
            sc = pop(lt, 0.16)
            ang = 0 if lt > 0.16 else (1 - lt / 0.16) * (12 if k % 2 else -12)
            paste_center(frame, glyph_sprite(ch, size, color, max(6, size // 14)), x + w / 2, cy, sc, ang)
        x += w


def overlay(frame, t):
    for a, b, kind in cards:
        if not (a <= t < b):
            continue
        fade = min(1.0, (b - t) / 0.3)
        if fade <= 0:
            continue
        if kind == "title":
            letters(frame, "ЗАПЕРТЫЙ", a + 0.25, t, W / 2, 330, 150, YELLOW)
            letters(frame, "История за минуту", a + 0.85, t, W / 2, 470, 62, WHITE, 0.03)
        elif kind == "end":
            letters(frame, "ЗАПЕРТЫЙ", a, t, W / 2, 420, 150, YELLOW)
            letters(frame, "Серия 1 уже в профиле", a + 0.5, t, W / 2, 560, 58, WHITE, 0.03)
        else:
            letters(frame, kind, a, t, W / 2, 330, 120, YELLOW, 0.07)
    w = next(((s, txt) for s, e, txt in reversed(words_tl) if s <= t < max(e + 0.25, s + 0.3)), None)
    if w:
        s, txt = w
        col = YELLOW if txt.lower() in KEY else WHITE
        paste_center(frame, text_sprite(txt.lower(), 92, col, 9), W / 2, 1390, pop(t - s))


def render(t):
    a = picture(t)
    frame = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    overlay(frame, t)
    out = np.asarray(frame.convert("RGB"))
    if t > TOTAL - 0.5:
        out = (out * max(0.0, (TOTAL - t) / 0.5)).astype(np.uint8)
    return out.tobytes()


# ------------------------------------------------------------------ звук
def flip_sfx():
    n = int(SR * 0.35)
    r = np.random.default_rng(2)
    s = r.normal(0, 1, n)
    s = s - ce.lowpass(s, 4)
    env = np.exp(-np.arange(n) / SR / 0.09) * np.clip(np.arange(n) / (SR * 0.01), 0, 1)
    crackle = (r.random(n) > 0.995) * r.normal(0, 3, n)
    return (s * env * 0.25 + ce.lowpass(crackle, 3) * env * 0.3)


def music(n):
    """Тёмная пульсация 84 BPM: бас-пэд по аккордам Am–F–C–G, мягкая бочка, перебор."""
    t = np.arange(n) / SR
    bpm = 84
    beat = 60 / bpm
    bar = beat * 4
    chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (130.8, 164.8, 196.0), (196.0, 246.9, 293.7)]
    out = np.zeros(n)
    for k in range(int(n / SR / bar) + 1):
        c = chords[k % 4]
        a0, a1 = int(k * bar * SR), min(n, int((k + 1) * bar * SR))
        if a0 >= n:
            break
        tt = t[a0:a1] - k * bar
        env = np.clip(tt / 0.4, 0, 1) * np.clip((bar - tt) / 0.4, 0, 1)
        pad = sum(np.sin(2 * np.pi * f / 2 * t[a0:a1]) + 0.5 * np.sin(2 * np.pi * f / 2 * 1.003 * t[a0:a1]) for f in c)
        out[a0:a1] += pad * env * 0.035
        out[a0:a1] += np.sin(2 * np.pi * c[0] / 4 * t[a0:a1]) * env * 0.08           # бас
        for j in range(8):                                                           # перебор восьмыми
            s0 = a0 + int(j * beat / 2 * SR)
            m = int(SR * 0.3)
            if s0 + m > n:
                break
            f = c[j % 3] * (2 if j % 4 == 3 else 1)
            tt2 = np.arange(m) / SR
            out[s0:s0 + m] += np.sin(2 * np.pi * f * tt2) * np.exp(-tt2 / 0.12) * 0.045
        for j in range(4):                                                           # мягкая бочка
            s0 = a0 + int(j * beat * SR)
            m = int(SR * 0.25)
            if s0 + m > n:
                break
            tt2 = np.arange(m) / SR
            out[s0:s0 + m] += np.sin(2 * np.pi * (50 + 60 * np.exp(-tt2 * 30)) * tt2) * np.exp(-tt2 / 0.09) * 0.22
    return out


def build_audio(p):
    n = int(SR * (TOTAL + 1))
    voice = np.zeros(n)
    for t0, i in said:
        v = VOICE[i][0]
        k = int(t0 * SR)
        voice[k:k + len(v)] += v[: n - k]
    m = music(n)
    envv = np.convolve(np.abs(voice), np.ones(int(SR * 0.25)) / (SR * 0.25), "same")   # приглушение музыки под голос
    duck = 1 - 0.55 * np.clip(envv / 0.05, 0, 1)
    tt = np.arange(n) / SR
    m *= duck * np.clip(tt / 1.5, 0, 1) * np.clip((TOTAL - tt) / 1.5, 0, 1)
    fx = np.zeros(n)
    SFX = dict(ce.SFX, flip=flip_sfx())
    for t0, s in sfx:
        k = int(t0 * SR)
        a = SFX[s]
        fx[k:k + len(a)] += a[: n - k] * (0.7 if s == "bang" else 1.0)
    mix = voice * 1.0 + m + fx * 0.8
    mix /= max(1e-6, np.abs(mix).max()) / 0.92
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", p],
                   input=mix.astype(np.float32).tobytes(), check=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        ts = [1.2, 2.6] + [s["t0"] + 0.9 for s in shots[1:]] + [shots[2]["t0"] - 0.05, shots[3]["t0"] - 0.02, TOTAL - 1.0]
        tiles = [Image.frombytes("RGB", (W, H), render(t)).resize((180, 320)) for t in ts]
        S = Image.new("RGB", (9 * 182, ((len(tiles) + 8) // 9) * 322), (40, 40, 40))
        for k, im in enumerate(tiles):
            S.paste(im, ((k % 9) * 182, (k // 9) * 322))
        S.save("/tmp/claude-0/-home-user-OfflineTranslator/1bcc3a57-a47c-5559-bc85-610f89fa5a3e/scratchpad/minute_prev.png")
        print("TOTAL", round(TOTAL, 1))
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
