"""MDX-Net (Kim Vocal 2) на numpy + onnxruntime: вокал из стерео-трека.
python3 -I sep.py model.onnx вход.mp3 выход_вокал.wav выход_минус.wav
"""
import subprocess
import sys
import time

import numpy as np
import onnxruntime as ort

SR, NFFT, HOP, DIMF, DIMT = 44100, 7680, 1024, 3072, 256
NB = NFFT // 2 + 1
CHUNK = HOP * (DIMT - 1)
TRIM = NFFT // 2
WIN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(NFFT) / NFFT)        # периодическое окно Ханна, как torch


def stft(x):                                   # x: [2, CHUNK] → [4, DIMF, DIMT]
    p = np.pad(x, ((0, 0), (NFFT // 2, NFFT // 2)), mode="reflect")
    idx = np.arange(DIMT)[:, None] * HOP + np.arange(NFFT)[None, :]
    S = np.fft.rfft(p[:, idx] * WIN, axis=-1)  # [2, T, NB]
    S = S.transpose(0, 2, 1)                   # [2, NB, T]
    out = np.stack([S.real, S.imag], 1).reshape(4, NB, DIMT)[:, :DIMF]
    return out.astype(np.float32)


def istft(spec):                               # [4, DIMF, DIMT] → [2, CHUNK]
    full = np.zeros((4, NB, DIMT), np.float64)
    full[:, :DIMF] = spec
    full = full.reshape(2, 2, NB, DIMT)
    C = (full[:, 0] + 1j * full[:, 1]).transpose(0, 2, 1)             # [2, T, NB]
    fr = np.fft.irfft(C, n=NFFT, axis=-1) * WIN
    L = NFFT + HOP * (DIMT - 1)
    y = np.zeros((2, L)); w = np.zeros(L)
    for t in range(DIMT):
        y[:, t * HOP:t * HOP + NFFT] += fr[:, t]
        w[t * HOP:t * HOP + NFFT] += WIN ** 2
    y = y[:, NFFT // 2:NFFT // 2 + CHUNK] / np.maximum(w[NFFT // 2:NFFT // 2 + CHUNK], 1e-8)
    return y


def main(model, src, out_voc, out_inst):
    mix = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                                       capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    mix = mix.reshape(-1, 2).T
    n = mix.shape[1]
    sess = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    gen = CHUNK - 2 * TRIM
    pad = gen + TRIM - (n % gen)
    m = np.concatenate([np.zeros((2, TRIM)), mix, np.zeros((2, pad))], 1)
    step = int(0.75 * CHUNK)
    res = np.zeros_like(m); div = np.zeros(m.shape[1])
    win = np.hanning(CHUNK)
    t0 = time.time()
    starts = list(range(0, m.shape[1], step))
    for k, i in enumerate(starts):
        part = m[:, i:i + CHUNK]
        L = part.shape[1]
        if L < CHUNK:
            part = np.concatenate([part, np.zeros((2, CHUNK - L))], 1)
        spec = stft(part)
        spec[:, :3] = 0
        pos = sess.run(None, {"input": spec[None]})[0][0]
        neg = sess.run(None, {"input": -spec[None]})[0][0]
        pred = 0.5 * pos - 0.5 * neg                                    # «денойз»: среднее по x и −x
        y = istft(pred)
        res[:, i:i + L] += (y * win)[:, :L]
        div[i:i + L] += win[:L]
        print(f"  {k + 1}/{len(starts)}  {time.time() - t0:.0f} с", flush=True)
    voc = (res / np.maximum(div, 1e-8))[:, TRIM:TRIM + n]
    inst = mix - voc
    for arr, path in ((voc, out_voc), (inst, out_inst)):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                        "-c:a", "pcm_s24le", path], input=arr.T.astype(np.float32).tobytes(), check=True)
    print("готово", round(n / SR, 1), "с")


if __name__ == "__main__":
    main(*sys.argv[1:5])
