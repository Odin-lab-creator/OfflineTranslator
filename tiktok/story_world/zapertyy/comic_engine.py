"""Движок кинокомикса «ЗАПЕРТЫЙ» (общий для серий): кадры PixelLab + камера + эффекты + титры + звук.

Компоновка 1080×1920: картинка 1080×1200 посередине, сверху чёрная полоса с титрами, снизу — с субтитрами.
Кадры ищутся (по порядку) в art/pro360 и art/proc360 (360×400 — видимая часть, мелкий пиксель, ×6),
art/pro270 (270×300, ×8), art/proc (рисованные кодом 216×384, ×10),
art/test_pro (Pro 360×640, ×6), art/pro216 (216×384, ×6). База увеличена так, что при масштабе 1 кадр
уменьшается ровно вдвое — пиксели остаются чёткими.
Координаты камеры — в «виртуальной» сетке 360×640: (масштаб, центр x, центр y).

Пример — см. ep2_comic.py.
"""
import functools
import os
import subprocess
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "art")
DIRS = [(os.path.join(ART, "pro360"), 6), (os.path.join(ART, "proc360"), 6), (os.path.join(ART, "pro270"), 8), (os.path.join(ART, "proc"), 10), (os.path.join(ART, "test_pro"), 6),
        (os.path.join(ART, "pro216"), 6)]
FPS, SR = 30, 44100
W, H = 1080, 1920
BAND_H, BAND_Y = 1200, 360
GW, GH = 360, 640
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
C_TEXT, C_DARK, C_HI = (236, 230, 214), (10, 9, 12), (240, 196, 120)
XF = 0.35
rng = np.random.default_rng(3)


# ------------------------------------------------------------------ звук: синтез шумов
def load_audio(p, tempo=1.0):
    af = ["-af", f"atempo={tempo}"] if tempo != 1.0 else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, *af, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def env(n, a=0.002, d=0.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def lowpass(s, k):
    return np.convolve(s, np.ones(k) / k, "same")


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


def _bang():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n) * env(n, 0.001, 0.03) * 0.8 + np.sin(2 * np.pi * 58 * t) * env(n, 0.002, 0.25) * 0.9
    for f, a in ((211, 0.25), (347, 0.18), (523, 0.12), (811, 0.06)):
        s += np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.5) * a
    return reverb(s * 0.7, 1.0, 0.3)


def _drip():
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    f = 1400 * np.exp(-t * 9) + 500
    return reverb(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.05) * 0.35, 0.4, 0.25)


def _step():
    n = int(SR * 0.09)
    return lowpass(rng.normal(0, 1, n) * env(n, 0.002, 0.018), 12) * 0.5


def _creak():
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    f = 330 + 120 * np.sin(2 * np.pi * 1.3 * t) + rng.normal(0, 25, n).cumsum() * 0.002
    return lowpass(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.05 * np.sin(np.pi * t / t[-1]), 6)


def _rattle():
    n = int(SR * 0.25)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n) * env(n, 0.001, 0.04) * 0.4
    for f in (640, 910, 1330):
        s += np.sin(2 * np.pi * f * t) * env(n, 0.001, 0.12) * 0.12
    return s


def _whoosh():
    n = int(SR * 0.5)
    return lowpass(rng.normal(0, 1, n) * np.sin(np.pi * np.arange(n) / n) ** 2, 30) * 0.25


def _slide():
    n = int(SR * 1.6)
    return lowpass(rng.normal(0, 1, n) * np.sin(np.pi * np.arange(n) / n) * 0.12, 20)


def _pour(sec=1.6):
    """Льющаяся вода: шум с «бульканьем»."""
    n = int(SR * sec)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n)
    s = s - lowpass(s, 6)                                   # убрать низ
    s = lowpass(s, 3)
    gurgle = 0.6 + 0.4 * np.sin(2 * np.pi * (7 + 3 * np.sin(2 * np.pi * 0.7 * t)) * t)
    edge = np.clip(t / 0.08, 0, 1) * np.clip((sec - t) / 0.25, 0, 1)
    return s * gurgle * edge * 0.18


def _gulp():
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f = 160 * np.exp(-t * 6) + 70
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.005, 0.06) * 0.5


def _clink():
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1870, 0.3), (2630, 0.2), (3910, 0.1)))
    return s * env(n, 0.0005, 0.08) * 0.5


def _thump():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 70 * t) * env(n, 0.002, 0.07) + lowpass(rng.normal(0, 1, n), 20) * env(n, 0.001, 0.03)) * 0.6


def _scribble():
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    s = rng.normal(0, 1, n)
    s = s - lowpass(s, 10)
    am = (np.sin(2 * np.pi * 9 * t) > 0.2) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.3 * t))
    return lowpass(s, 2) * am * 0.06


SFX = {"bang": _bang(), "drip": _drip(), "step": _step(), "creak": _creak(), "rattle": _rattle(), "whoosh": _whoosh(),
       "slide": _slide(), "pour": _pour(), "pour_long": _pour(4.0), "gulp": _gulp(), "clink": _clink(),
       "thump": _thump(), "scribble": _scribble()}


# ------------------------------------------------------------------ текст
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


def draw_line(ui, s, y, sz, color):
    g = text_mask(s, sz)
    h, w = g.shape
    x0 = (ui.shape[1] - w) // 2
    o = np.zeros((h + 2, w + 2), bool)
    for dy in range(3):
        for dx in range(3):
            o[dy:dy + h, dx:dx + w] |= g
    reg = ui[y - 1:y + h + 1, x0 - 1:x0 + w + 1]
    reg[o[: reg.shape[0], : reg.shape[1]]] = (*C_DARK, 255)
    reg = ui[y:y + h, x0:x0 + w]
    reg[g[: reg.shape[0], : reg.shape[1]]] = (*color, 255)


def chunks(text, limit=46):
    parts, cur = [], ""
    for w_ in text.split():
        cur = (cur + " " + w_).strip()
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


# ------------------------------------------------------------------ серия
class Episode:
    patch = {}                                                # имя кадра → функция правки массива (надписи и т. п.)
    def __init__(self, lines, voice_path, out, tempo=1.06):
        self.out = out
        self.voice = {i: load_audio(voice_path(i), tempo) for i, *_ in lines}
        self.dur = {i: len(v) / SR for i, v in self.voice.items()}
        self.text = {ln[0]: ln[1] for ln in lines}
        self.t = 0.0
        self.said, self.sfx, self.titles, self.shots = [], [], [], []
        self.voice_fx = {}                                    # id → "echo" | "reverb"
        self.kicks, self.shakes = [], []

    # таймлайн
    def say(self, i, gap=0.45):
        t0 = self.t
        self.said.append((t0, i))
        self.t += self.dur[i] + gap
        return t0

    def wait(self, s):
        self.t += s

    def fx(self, name, at=None):
        self.sfx.append((self.t if at is None else at, name))

    def title(self, text, dur, at=None, y=46):
        t0 = self.t if at is None else at
        self.titles.append((t0, t0 + dur, text, y))

    def shot(self, img, cam0=(1, 180, 320), cam1=None, at=None, **extra):
        t0 = self.t if at is None else at
        if self.shots:
            self.shots[-1][1] = t0
        self.shots.append([t0, None, img, cam0, cam1 or cam0, extra])

    def chunk_times(self, i, t0):
        cs = chunks(self.text[i])
        total = sum(len(c) for c in cs)
        out, t = [], t0
        for c in cs:
            d = self.dur[i] * len(c) / total
            out.append((t, t + d, c))
            t += d
        return out

    def finish(self):
        self.shots[-1][1] = self.t
        self.total = self.t
        self.subs = []
        for t0, i in self.said:
            for a, b, c in self.chunk_times(i, t0):
                self.subs.append((a, b + 0.12, c))
        self.rattles = [t for t, s in self.sfx if s == "rattle"]

    # картинка
    @staticmethod
    @functools.lru_cache(4)
    def big(name):
        for d, k in DIRS:
            p = os.path.join(d, f"{name}.png")
            if os.path.exists(p):
                a = np.asarray(Image.open(p).convert("RGB")).copy()
                for x in range(a.shape[1]):                   # белые поля по краям у части кадров
                    if a[:, x].mean() > 245:
                        a[:, x] = a[:, 5 if x < a.shape[1] // 2 else a.shape[1] - 6]
                if Episode.patch.get(name):
                    a = Episode.patch[name](a)
                return Image.fromarray(a).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)
        raise FileNotFoundError(name)

    def _jitter(self, t, times, dur, amp):
        for x in times:
            if 0 <= t - x < dur:
                k = 1 - (t - x) / dur
                return np.random.default_rng(int(t * 1000)).uniform(-amp, amp, 2) * k, k
        return np.zeros(2), 0.0

    def camera(self, s, t):
        t0, t1, name, c0, c1, ex = s
        u = (t - t0) / max(1e-6, t1 - t0)
        u = min(1.0, max(0.0, u))
        u = u * u * (3 - 2 * u)
        z, cx, cy = (c0[j] + (c1[j] - c0[j]) * u for j in range(3))
        off = np.zeros(2)
        if ex.get("kick"):
            o, k = self._jitter(t, self.kicks, 0.18, 2.5)
            off += o
            z += 0.04 * k
        if ex.get("rattle"):
            off += self._jitter(t, self.rattles, 0.1, 1.2)[0]
        if ex.get("shake"):
            off += self._jitter(t, self.shakes, 0.6, 1.0)[0]
        img = self.big(name)
        BW, BH = img.size
        cw = BW / z
        ch = cw * BAND_H / W
        x0 = np.clip((cx + off[0]) * BW / GW - cw / 2, 0, BW - cw)
        y0 = np.clip((cy + off[1]) * BH / GH - ch / 2, 0, BH - ch)
        a = np.asarray(img.resize((W, BAND_H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))).astype(np.float32)
        if ex.get("dust"):
            a = self.dust(a, t - t0)
        if ex.get("eyelids"):
            k = max(0.0, 1 - (t - t0) / 2.4)
            if k > 0:
                h = int(BAND_H / 2 * k ** 0.6)
                a[:h] = 0
                a[BAND_H - h:] = 0
        if ex.get("fade"):
            a *= 1 - min(1.0, (t - t0) / 9.0) * 0.6
        if ex.get("overlay"):
            a = ex["overlay"](a, t - t0)
        return a

    @staticmethod
    def dust(a, lt):
        r = np.random.default_rng(11)
        n = 70
        px, py = r.uniform(0, W, n), r.uniform(0, BAND_H * 0.85, n)
        vx, vy = r.uniform(-6, 6, n), r.uniform(-14, -3, n)
        ph = r.uniform(0, 6.28, n)
        for k in range(n):
            x, y = int((px[k] + vx[k] * lt) % W), int((py[k] + vy[k] * lt) % BAND_H)
            al = 0.25 + 0.2 * np.sin(lt * 1.3 + ph[k])
            a[y:y + 3, x:x + 3] = a[y:y + 3, x:x + 3] * (1 - al) + 235 * al
        return a

    @staticmethod
    @functools.lru_cache(1)
    def vignette():
        yy, xx = np.mgrid[0:BAND_H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - BAND_H / 2) / (BAND_H / 2)) ** 2
        return np.clip(1.08 - 0.28 * r2, 0.55, 1)[..., None]

    def picture(self, t):
        i = next((k for k, s in enumerate(self.shots) if s[0] <= t < s[1]), len(self.shots) - 1)
        s = self.shots[i]
        if s[2] is None:
            return np.zeros((BAND_H, W, 3), np.float32)
        a = self.camera(s, t)
        if i > 0 and t - s[0] < XF and self.shots[i - 1][2] is not None:
            u = (t - s[0]) / XF
            a = self.camera(self.shots[i - 1], s[0] - 1e-3) * (1 - u) + a * u
        return a * self.vignette()

    @functools.lru_cache(256)
    def ui_layer(self, sub, titles):
        ui = np.zeros((H // 3, W // 3, 4), np.uint8)
        if sub:
            y = (BAND_Y + BAND_H) // 3 + 16
            for ln in wrap(sub, 18, W // 3 - 30):
                draw_line(ui, ln, y, 18, C_TEXT)
                y += 25
        ys = {}
        for text, y in titles:
            y = ys.get(y, y)
            lines = wrap(text, 18, W // 3 - 30)
            for k, ln in enumerate(lines):
                draw_line(ui, ln, y + k * 26, 18, C_HI)
        return np.asarray(Image.fromarray(ui, "RGBA").resize((W, H), Image.NEAREST))

    def render(self, t):
        a = np.zeros((H, W, 3), np.float32)
        a[:] = C_DARK
        a[BAND_Y:BAND_Y + BAND_H] = self.picture(t)
        sub = next((s for x, y, s in self.subs if x <= t < y), "")
        titles = tuple((x, y) for p, q, x, y in self.titles if p <= t < q)
        if sub or titles:
            ui = self.ui_layer(sub, titles)
            m = ui[..., 3] > 0
            a[m] = ui[..., :3][m]
        if t > self.total - 0.7:
            a *= max(0.0, (self.total - t) / 0.7)
        return np.clip(a, 0, 255).astype(np.uint8).tobytes()

    # звук
    def build_audio(self, path, swell_from=None):
        n = int(SR * (self.total + 1))
        mix = np.zeros(n)
        t = np.arange(n) / SR
        r = np.random.default_rng(5)
        drone = np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.35 * t) + 0.4 * np.sin(2 * np.pi * 82.4 * t)
        drone *= 0.035 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t)) * np.clip(t / 6, 0, 1)
        if swell_from is not None:
            drone *= 1 + 1.2 * np.clip((t - swell_from) / 20, 0, 1) * np.clip((self.total - t) / 3, 0, 1)
        mix += drone + np.convolve(r.normal(0, 1, n), np.ones(400) / 400, "same") * 0.06
        for t0, i in self.said:
            v = self.voice[i]
            kind = self.voice_fx.get(i)
            if kind == "echo":
                v = echo(v)
            elif kind == "reverb":
                v = reverb(v, 0.5, 0.12)
            k = int(t0 * SR)
            mix[k:k + len(v)] += v[: n - k]
        for t0, s in self.sfx:
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

    def build(self, swell_from=None):
        wav = self.out + ".wav"
        self.build_audio(wav, swell_from)
        nf = int(self.total * FPS)
        print(f"длительность {self.total:.1f} с, кадров {nf}", flush=True)
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", self.out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for buf in pool.imap(self.render, [f / FPS for f in range(nf)], chunksize=30):
                p.stdin.write(buf)
        p.stdin.close()
        p.wait()
        os.remove(wav)
        print("Готово:", self.out)
