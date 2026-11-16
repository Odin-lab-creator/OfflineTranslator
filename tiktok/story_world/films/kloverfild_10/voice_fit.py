"""Озвучка «Олег» на модели v3 (правильные ударения) + темп как в «Птичьем коробе» без изменения голоса:
длинные паузы v3 сжимаются до PAUSE_MAX, сами слова не ускоряются и тон не меняется.
python3 voice_fit.py [whole.mp3 whole.json] → voice_user/vo.mp3 + voice_user/NN.json → build.py --user
"""
import json
import os
import subprocess
import sys

import numpy as np

from script import SCENES, plain
from voice_eleven import map_to_script

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice_user")
SR = 44100
PAUSE_MAX = 0.38          # паузы длиннее — сжимаются до этой длины (середина вырезается)


def main(mp3, js):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                     capture_output=True).stdout, np.float32)
    w = int(0.01 * SR)
    e = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, w)])
    sil = e < np.percentile(e, 95) * 0.04
    keep, knots_o, knots_n = [], [0.0], [0.0]
    pos, new_t, i = 0, 0.0, 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]:
                j += 1
            dur = (j - i) * 0.01
            if dur > PAUSE_MAX:
                a = i * w + int(PAUSE_MAX / 2 * SR)          # оставляем по половине паузы с краёв
                b = j * w - int(PAUSE_MAX / 2 * SR)
                keep.append(x[pos:a]); new_t += (a - pos) / SR
                knots_o += [a / SR, b / SR]; knots_n += [new_t, new_t]
                pos = b
            i = j
        else:
            i += 1
    keep.append(x[pos:]); new_t += (len(x) - pos) / SR
    knots_o.append(len(x) / SR); knots_n.append(new_t)
    warp = lambda t: float(np.interp(t, knots_o, knots_n))
    y = np.concatenate(keep)
    al = json.load(open(js))
    said = "".join(al["characters"])
    st = [warp(t) for t in al["character_start_times_seconds"]]
    en = [warp(t) for t in al["character_end_times_seconds"]]
    cuts = [-1] + [i for i, c in enumerate(said) if c == "\n"] + [len(said)]
    assert len(cuts) - 1 == len(SCENES)
    os.makedirs(OUT, exist_ok=True)
    for k, (n, _, marked) in enumerate(SCENES):
        a, b = cuts[k] + 1, cuts[k + 1]
        cs, ce = map_to_script(plain(marked), said[a:b], st[a:b], en[a:b])
        json.dump({"characters": list(plain(marked)), "character_start_times_seconds": cs,
                   "character_end_times_seconds": ce}, open(os.path.join(OUT, f"{n:02d}.json"), "w"), ensure_ascii=False)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(OUT, "vo.mp3")], input=y.astype(np.float32).tobytes(), check=True)
    chars = sum(len(plain(t)) for _, _, t in SCENES)
    print(f"было {len(x) / SR:.1f} с → стало {len(y) / SR:.1f} с, темп {chars / (len(y) / SR):.1f} симв/с")


if __name__ == "__main__":
    a = sys.argv[1:] or [os.path.join(HERE, "voice_eleven", "whole_v3.mp3"), os.path.join(HERE, "voice_eleven", "whole_v3.json")]
    main(*a)
