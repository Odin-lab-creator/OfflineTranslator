"""8-битный саундтрек и звуки PIXEL APOCALYPSE (синтез: треугольник, прямоугольник, шум — как в ретро-приставках).

build_audio(cut, path) — дорожка для монтажа: голос (voice.mp3) + чиптюн-музыка по актам + 8-битные SFX.
cut: dict(v0, v1, hook, tail) — кусок озвучки [v0, v1], перед ним зацепка hook секунд, после — карточка tail секунд.
"""
import subprocess
import wave

import numpy as np

import episode1 as ep

SR = 44100
BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
A4 = 440.0


def hz(n):  # MIDI → Гц
    return A4 * 2 ** ((n - 69) / 12)


# ------------------------------------------------------------------ осцилляторы
def tri(f, n, ph=0.0):
    t = (np.arange(n) / SR * f + ph) % 1
    return (4 * np.abs(t - 0.5) - 1) * 0.9          # «ступенчатый» треугольник
def sq(f, n, duty=0.5):
    t = (np.arange(n) / SR * f) % 1
    return np.where(t < duty, 1.0, -1.0)


def noise(n, seed=0, period=1):
    r = np.random.default_rng(seed).choice([-1.0, 1.0], size=n // period + 1)
    return np.repeat(r, period)[:n]


def env(n, a=0.005, d=0.08, s=0.6, r=0.05, hold=None):
    t = np.arange(n) / SR
    hold = (n / SR - r) if hold is None else hold
    e = np.where(t < a, t / max(a, 1e-6), 1.0)
    e = np.where(t >= a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)), e)
    e = np.where(t > hold, e * np.clip(1 - (t - hold) / max(r, 1e-6), 0, 1), e)
    return e


def add(buf, t, sig):
    i = int(t * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    j0 = max(0, -i); i = max(0, i)
    seg = sig[j0:j0 + len(buf) - i]
    buf[i:i + len(seg)] += seg


# ------------------------------------------------------------------ музыка
PROG = [(57, [57, 60, 64]), (53, [53, 57, 60]), (50, [50, 53, 57]), (52, [52, 56, 59])]  # Am F Dm E
MOTIF = [69, 72, 71, 64, 69, 67, 65, 64]   # мрачная фраза (A4 C5 B4 E4 A4 G4 F4 E4)


def section(tv):
    """Интенсивность и характер по времени озвучки."""
    if tv < 17.0: return "intro"
    if tv < 33.7: return "rule"
    if tv < 50.4: return "door"
    if tv < 60.3: return "rule"
    if tv < 90.6: return "radio"
    if tv < 105.7: return "tension"
    return "finale"


def music(dur, v0, hook):
    """Музыка на всю длину ролика; tv = v0 + (t - hook) — время озвучки."""
    n = int(dur * SR)
    m = np.zeros(n)
    nb = int(dur / BEAT) + 2
    for b in range(nb):
        t = b * BEAT
        tv = v0 + (t - hook)
        sec = section(max(0.0, tv)) if t >= hook else "hook"
        bar, beat = divmod(b, 4)
        root, chord = PROG[bar % 4]
        L = int(BEAT * SR)
        # бас — треугольник
        if sec != "hook" and not (sec in ("intro", "radio") and beat == 3):
            add(m, t, tri(hz(root - 12), L) * env(L, d=0.25, s=0.5, r=0.08) * 0.35)
        # арпеджио — узкий прямоугольник 12.5%
        if sec in ("rule", "door", "tension", "finale") or (sec in ("intro", "radio") and bar % 2 == 0):
            for k in range(2):
                note = chord[(beat * 2 + k) % 3] + 12
                L2 = int(BEAT / 2 * SR)
                add(m, t + k * BEAT / 2, sq(hz(note), L2, 0.125) * env(L2, d=0.06, s=0.2, r=0.03) * 0.07)
        # мелодия — 25%
        if sec in ("rule", "finale") and bar % 2 == 1:
            note = MOTIF[(bar * 4 + beat) % len(MOTIF)]
            add(m, t, sq(hz(note), L, 0.25) * env(L, d=0.3, s=0.35, r=0.1) * 0.07)
        # гул в радио-сцене — расстроенные квадраты
        if sec == "radio" and beat == 0:
            L4 = int(BAR * SR)
            add(m, t, (sq(hz(root - 24), L4, 0.5) + sq(hz(root - 24) * 1.006, L4, 0.5)) * env(L4, a=0.4, d=1, s=0.8, r=0.6) * 0.035)
        # ударные: бочка (свип треугольника), малый (шум), хэт
        if sec in ("door", "tension", "finale", "rule"):
            if beat in (0, 2) or (sec == "finale" and beat == 3):
                Lk = int(0.18 * SR); tt = np.arange(Lk) / SR
                kick = np.sin(2 * np.pi * np.cumsum(np.interp(tt, [0, 0.12], [160, 45])) / SR)
                add(m, t, kick * np.exp(-tt * 22) * 0.45)
            if sec in ("finale", "tension") and beat in (1, 3):
                Ls = int(0.12 * SR)
                add(m, t, noise(Ls, b, 2) * np.exp(-np.arange(Ls) / SR * 30) * 0.12)
            if sec != "rule" or beat % 2:
                Lh = int(0.03 * SR)
                add(m, t + BEAT / 2, noise(Lh, b + 7, 1) * np.exp(-np.arange(Lh) / SR * 120) * 0.05)
        # сердцебиение в двери и напряжении
        if sec in ("door", "tension"):
            for off in (0.0, 0.18):
                Lk = int(0.12 * SR); tt = np.arange(Lk) / SR
                add(m, t + off, np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 30) * 0.3)
    # плавный вход
    m *= np.clip(np.arange(n) / SR / 1.0, 0, 1)
    return m


# ------------------------------------------------------------------ 8-битные SFX
def sfx_knock(seed=0):
    L = int(0.12 * SR)
    return noise(L, seed, 6) * np.exp(-np.arange(L) / SR * 45) * 0.7 + sq(90, L, 0.5) * np.exp(-np.arange(L) / SR * 30) * 0.4


def sfx_stab():
    L = int(0.6 * SR)
    e = np.exp(-np.arange(L) / SR * 5)
    return (sq(hz(45), L, 0.5) + sq(hz(52), L, 0.25) * 0.6) * e * 0.35 + noise(L, 3, 4) * np.exp(-np.arange(L) / SR * 20) * 0.3


def sfx_static(dur, seed=1):
    L = int(dur * SR)
    gate = np.repeat(np.random.default_rng(seed).random(L // 400 + 1) > 0.3, 400)[:L]
    return noise(L, seed, 3) * gate * 0.25


def sfx_sweep(f0, f1, dur, duty=0.5, vol=0.2):
    L = int(dur * SR); tt = np.arange(L) / SR
    f = np.interp(tt, [0, dur], [f0, f1])
    ph = np.cumsum(f) / SR % 1
    return np.where(ph < duty, 1.0, -1.0) * vol * np.clip((dur - tt) / 0.05, 0, 1)


def sfx_buzz(dur):
    L = int(dur * SR); tt = np.arange(L) / SR
    return sq(110, L, 0.5) * ((tt * 1.6) % 1 < 0.6) * 0.22


def sfx_ping():
    a = sq(hz(88), int(0.09 * SR), 0.5) * 0.18
    b = sq(hz(83), int(0.14 * SR), 0.5) * 0.18
    return np.concatenate([a, b])


def sfx_creak():
    L = int(1.1 * SR); tt = np.arange(L) / SR
    f = 70 + 25 * np.sin(tt * 9) + 30 * tt
    ph = np.cumsum(f) / SR % 1
    return np.where(ph < 0.3, 1.0, -1.0) * 0.12 * np.clip(tt / 0.1, 0, 1) * np.clip((1.1 - tt) / 0.2, 0, 1)


def sfx_hit():
    L = int(1.4 * SR); tt = np.arange(L) / SR
    return sfx_sweep(140, 30, 1.4, 0.5, 0.45) * np.exp(-tt * 2) + noise(L, 9, 8) * np.exp(-tt * 6) * 0.35


def sfx_stinger():
    out = np.zeros(int(1.4 * SR))
    for k, nte in enumerate([76, 72, 69, 63]):
        L = int(0.16 * SR)
        add(out, k * 0.13, sq(hz(nte), L, 0.25) * env(L, d=0.08, s=0.3, r=0.03) * 0.25)
    add(out, 0.55, sfx_hit()[: int(0.8 * SR)])
    return out


# ------------------------------------------------------------------ сборка
def voice(v0, v1):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", ep.VOICE, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    v = v[int(v0 * SR):int(v1 * SR)]
    return v / (np.max(np.abs(v)) + 1e-9)


def build_audio(cut, path):
    v0, v1, hook, tail = cut["v0"], cut["v1"], cut["hook"], cut["tail"]
    dur = hook + (v1 - v0) + tail
    n = int(dur * SR)
    vo = np.zeros(n); add(vo, hook, voice(v0, v1))
    win = int(0.15 * SR)
    venv = np.sqrt(np.convolve(vo ** 2, np.ones(win) / win, "same"))
    duck = 1 - 0.6 * np.clip(venv / 0.12, 0, 1)
    mus = music(dur, v0, hook)
    fx = np.zeros(n)
    T = {k: getattr(ep, k) for k in dir(ep) if k.startswith("T_")}
    at = lambda tv: hook + tv - v0                               # время озвучки → время ролика
    inside = lambda tv: v0 <= tv < v1
    ev = []
    for k in (T["T_KNOCK"] + 0.1, T["T_KNOCK"] + 0.35, T["T_KNOCK"] + 0.6, T["T_THREE"] + 0.75, T["T_THREE"] + 1.05, T["T_THREE"] + 1.35):
        ev.append((k, sfx_knock(int(k * 10))))
    for r in (T["T_RULE1"], T["T_RULE2"], T["T_RULE3"]):
        ev.append((r, sfx_stab()))
    ev += [(T["T_LOST"], sfx_static(T["T_TUNE"] + 1.2 - T["T_LOST"])), (T["T_TUNE"], sfx_sweep(300, 1500, 1.2, 0.25, 0.12)),
           (T["T_VIBR"], sfx_buzz(T["T_SCREEN"] - T["T_VIBR"])), (T["T_DONT"], sfx_ping()),
           (T["T_CREAK"] + 0.5, sfx_creak()), (T["T_LAST"], sfx_hit())]
    for tv, s in ev:
        if inside(tv):
            add(fx, at(tv), s)
    add(fx, 0.0, sfx_stinger() * (1.0 if cut.get("hook_kind") == "teaser" else 0.6))
    if cut.get("hook_kind") == "part2":
        for k in (0.2, 0.45, 0.7):
            add(fx, k, sfx_knock(int(k * 100)))
    add(fx, hook + (v1 - v0), sfx_hit())                         # удар на финальной карточке
    mix = vo * 1.0 + mus * 0.55 * duck + fx * 0.6
    mix *= np.clip((dur - np.arange(n) / SR) / 1.2, 0, 1)
    mix = np.tanh(mix * 1.15)
    mix /= np.max(np.abs(mix)) + 1e-9
    data = (mix * 0.95 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.stack([data, data], 1).tobytes())
    return dur
