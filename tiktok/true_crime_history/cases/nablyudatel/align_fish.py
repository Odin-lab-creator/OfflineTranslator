"""Тайминг слов для озвучки Fish Audio без распознавания речи (лимит STT ElevenLabs кончился).
Есть отдельная запись каждой сцены и её место в vo.mp3 (voice_user/scenes.json). Внутри сцены:
паузы в голосе сопоставляются со знаками препинания, слова раскладываются по слогам того, что произносится
(«2014» звучит как «две тысячи четырнадцатый» — у него и слогов больше).
python3 align_fish.py → voice_user/NN.json (время каждого символа от начала vo.mp3, формат ElevenLabs)
"""
import json
import os
import re

import numpy as np

from script import SCENES
from voice_fish import OUT, SR, load_trimmed

SAY = {"2014": "две тысячи четырнадцатый", "2019-м": "две тысячи девятнадцатом", "400": "четыреста",
       "true": "тру", "crime": "крайм", "history": "хистори"}
VOW = set("аеёиоуыэюяaeiouy")
BREAK = set(",.!?:;—…»")


def syl(word):
    w = re.sub(r"[^\w-]", "", word.lower())
    w = SAY.get(w, w)
    return max(0.4, sum(c in VOW for c in w))


def silences(a, min_len=0.08):
    hop = int(SR * 0.01)
    rms = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, "same")[::hop])
    thr = np.percentile(rms, 90) * 10 ** (-22 / 20)
    quiet = rms < thr
    out, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_len and i > 3 and j < len(quiet) - 3:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def scene_words(n, text, t0, t1, audio):
    words = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]
    w = np.array([syl(x[2]) for x in words], float)
    brk = [k for k, x in enumerate(words[:-1]) if x[2][-1] in BREAK or (k + 1 < len(words) and words[k + 1][2] == "—")]
    dur = t1 - t0
    cum = np.concatenate([[0], np.cumsum(w)]) / w.sum() * dur          # пропорциональное время границ слов
    sil = sorted(silences(audio), key=lambda s: s[0] - s[1])            # длинные паузы — первыми
    assigned = {}
    for s0, s1 in sil:
        mid = (s0 + s1) / 2
        best = min((b for b in brk if b not in assigned), key=lambda b: abs(cum[b + 1] - mid), default=None)
        if best is not None and abs(cum[best + 1] - mid) < 0.7:
            assigned[best] = (s0, s1)
    # отрезки речи между выбранными паузами; внутри — по слогам
    cuts = sorted(assigned)
    spans, a, w0 = [], 0.0, 0
    for b in cuts:
        spans.append((w0, b + 1, a, assigned[b][0]))
        a, w0 = assigned[b][1], b + 1
    spans.append((w0, len(words), a, dur))
    times = []
    for k0, k1, s, e in spans:
        ww = w[k0:k1]
        c = np.concatenate([[0], np.cumsum(ww)]) / ww.sum() * (e - s) + s
        times += [(t0 + c[i], t0 + c[i + 1]) for i in range(len(ww))]
    return words, times, len(assigned), len(brk)


def main():
    marks = json.load(open(os.path.join(OUT, "scenes.json")))
    stats = []
    for n, _, marked in SCENES:
        text = marked.replace("**", "")
        t0, t1 = marks[str(n)]
        words, times, got, nb = scene_words(n, text, t0, t1, load_trimmed(n))
        st, en = [None] * len(text), [None] * len(text)
        for (p0, p1, _), (a, b) in zip(words, times):
            L = p1 - p0
            for k in range(L):
                st[p0 + k], en[p0 + k] = a + (b - a) * k / L, a + (b - a) * (k + 1) / L
        last = t0
        for k in range(len(text)):                       # пробелы — время соседей
            if st[k] is None:
                st[k] = en[k] = last
            last = en[k]
        json.dump({"characters": list(text), "character_start_times_seconds": st,
                   "character_end_times_seconds": en}, open(os.path.join(OUT, f"{n:02d}.json"), "w"), ensure_ascii=False)
        stats.append(f"{n}:{got}/{nb}")
    print("паузы найдены/знаков:", " ".join(stats))


if __name__ == "__main__":
    main()
