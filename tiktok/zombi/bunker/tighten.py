#!/usr/bin/env python3
"""Укоротить длинные паузы в озвучке: каждая пауза между словами > MAXP сжимается до MAXP
(драматичные — до DRAMA). python3 tighten.py 1 → ep1_voice/vo_tight.wav + stt_tight.json"""
import importlib
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
MAXP, DRAMA = 0.45, 0.8
DRAMA_AFTER = {"удара,", "пауза,", "Тишина.", "потом", "три.", "бетон."}


def main(ep):
    m = importlib.import_module(f"ep{ep}")
    d = os.path.join(HERE, m.VOICE)
    a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(d, "vo.mp3"), "-ac", "1", "-ar", str(SR),
                                      "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
    stt = json.load(open(os.path.join(d, "stt.json")))
    ws = [w for w in stt["words"] if w.get("type") == "word"]
    cuts = []                                       # (начало, конец) вырезаемых кусков тишины
    for w, nx in zip(ws, ws[1:]):
        gap = nx["start"] - w["end"]
        keep = DRAMA if w["text"] in DRAMA_AFTER else MAXP
        if gap > keep + 0.05:
            mid = w["end"] + keep / 2
            cuts.append((mid, mid + gap - keep))
    out, pos, shift, fade = [], 0, [], int(0.01 * SR)
    removed = 0.0
    for c0, c1 in cuts:
        i0, i1 = int(c0 * SR), int(c1 * SR)
        seg = a[pos:i0].copy()
        if len(out) and len(seg) > fade:
            seg[:fade] *= np.linspace(0, 1, fade)
        if len(seg) > fade:
            seg[-fade:] *= np.linspace(1, 0, fade)
        out.append(seg)
        removed += c1 - c0
        shift.append((c1, removed))
        pos = i1
    tail = a[pos:].copy()
    tail[:fade] *= np.linspace(0, 1, fade)
    out.append(tail)
    res = np.concatenate(out)

    def remap(t):
        r = 0.0
        for c1, rem in shift:
            if t >= c1:
                r = rem
        return t - r
    for w in stt["words"]:
        w["start"], w["end"] = remap(w["start"]), remap(w["end"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    os.path.join(d, "vo_tight.wav")], input=res.astype(np.float32).tobytes(), check=True)
    json.dump(stt, open(os.path.join(d, "stt_tight.json"), "w"), ensure_ascii=False, indent=1)
    print(f"было {len(a) / SR:.1f} с, стало {len(res) / SR:.1f} с, вырезано пауз {removed:.1f} с")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1")
