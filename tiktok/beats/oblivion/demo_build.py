"""Oblivion (98 BPM): к рендеру двух мелодий Serum добавляет аккорды, 808 и простые барабаны, чтобы услышать гармонию.

python3 -I demo_build.py <рендер.mp3> <папка>  →  oblivion_harmony_demo.mp3, oblivion_chords.mid, oblivion_808.mid
Гармония по мелодии 1 (держит До 2 такта, потом Си 2 такта): | Cmaj7 | Cmaj7 | Em9 | Em9 |  — VI → i в ми миноре.
"""
import struct
import subprocess
import sys

import numpy as np

SR, BPM = 44100, 98
BEAT = 60 / BPM
BAR = 4 * BEAT
# имя, нота 808 (MIDI), аккорд (MIDI); во FL 60 = C5
CHORDS = [("Cmaj7", 36, [48, 55, 59, 64]), ("Em9", 40, [52, 55, 59, 62, 66])]
PROG = [0, 0, 1, 1]                                   # по тактам, цикл 4 такта


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def render(src, out):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    bars = 8
    n = int(round(bars * BAR * SR))
    t = np.arange(n) / SR
    pad, b808, drums = np.zeros(n), np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(1)
    for k in range(bars):
        _, root, notes = CHORDS[PROG[k % 4]]
        a0, a1 = int(k * BAR * SR), int((k + 1) * BAR * SR)
        tt = t[a0:a1] - k * BAR
        env = np.clip(tt / 0.3, 0, 1) * np.clip((BAR - tt) / 0.25, 0, 1)
        for m in notes:
            f = hz(m)
            pad[a0:a1] += (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)
                           + 0.5 * np.sin(2 * np.pi * f * 1.003 * tt)) * env * 0.03
        for hit, dur in ((0.0, 2.4 * BEAT), (2.5 * BEAT, 1.4 * BEAT)):        # 808: доля 1 и «и» после 3-й
            h0 = a0 + int(hit * SR)
            h1 = min(a1, h0 + int(dur * SR))
            th = np.arange(h1 - h0) / SR
            f = hz(root) * (1 + 0.9 * np.exp(-th * 45))
            e = np.clip(th / 0.003, 0, 1) * np.exp(-th / 1.3) * np.clip((dur - th) / 0.05, 0, 1)
            b808[h0:h1] += np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * e * 0.42
        for j in range(8):                                                     # хэты восьмыми
            h0, m = a0 + int(j * BEAT / 2 * SR), int(SR * 0.05)
            nz = rng.normal(0, 1, m)
            nz -= np.convolve(nz, np.ones(4) / 4, "same")
            drums[h0:h0 + m] += nz * np.exp(-np.arange(m) / SR / 0.012) * (0.04 if j % 2 else 0.065)
        for j in (1, 3):                                                       # снэйр на 2 и 4
            h0, m = a0 + int(j * BEAT * SR), int(SR * 0.18)
            th = np.arange(m) / SR
            drums[h0:h0 + m] += (rng.normal(0, 1, m) * np.exp(-th / 0.05) * 0.16
                                 + np.sin(2 * np.pi * 190 * th) * np.exp(-th / 0.04) * 0.14)
    mel = np.zeros(n)
    mel[:min(n, len(x))] = x[:n]
    mix = mel / (np.abs(mel).max() + 1e-9) * 0.55 + pad + b808 + drums
    mix /= np.abs(mix).max() / 0.92
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-b:a", "256k",
                    f"{out}/oblivion_harmony_demo.mp3"], input=mix.astype(np.float32).tobytes(), check=True)


def vlq(v):
    b = [v & 0x7F]
    v >>= 7
    while v:
        b.insert(0, (v & 0x7F) | 0x80)
        v >>= 7
    return bytes(b)


def midi(path, events, ppq=96):
    events.sort(key=lambda e: (e[0], e[1] == 0x90))
    data, last = b"", 0
    for tk, st, note, vel in events:
        data += vlq(tk - last) + bytes([st, note, vel])
        last = tk
    trk = data + b"\x00\xff\x2f\x00"
    tempo = b"\x00\xff\x51\x03" + struct.pack(">I", int(60e6 / BPM))[1:] + b"\x00\xff\x2f\x00"
    open(path, "wb").write(b"MThd" + struct.pack(">IHHH", 6, 1, 2, ppq)
                           + b"MTrk" + struct.pack(">I", len(tempo)) + tempo
                           + b"MTrk" + struct.pack(">I", len(trk)) + trk)


def midis(out, ppq=96):
    bar = 4 * ppq
    chords, bass = [], []
    for k in range(4):
        _, root, notes = CHORDS[PROG[k]]
        if k % 2 == 0:                                                         # аккорд держится 2 такта
            for m in notes:
                chords += [(k * bar, 0x90, m, 80), ((k + 2) * bar - 1, 0x80, m, 0)]
        for hit, dur in ((0, int(2.4 * ppq)), (int(2.5 * ppq), int(1.4 * ppq))):
            bass += [(k * bar + hit, 0x90, root, 100), (k * bar + hit + dur, 0x80, root, 0)]
    midi(f"{out}/oblivion_chords.mid", chords)
    midi(f"{out}/oblivion_808.mid", bass)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
    midis(sys.argv[2])
    print("готово")
