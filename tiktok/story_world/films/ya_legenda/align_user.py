"""Своя озвучка: voice_user/vo.mp3 + распознавание voice_user/stt.json (ElevenLabs STT, тайминг слов)
→ voice_user/NN.json в формате разметки ElevenLabs (время каждого символа, от начала записи).
python3 align_user.py
"""
import difflib
import json
import os
import re

from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice_user")


def norm(w):
    w = w.lower().replace("ё", "е").replace("э", "е")
    w = {"times": "таймс", "square": "сквер"}.get(re.sub(r"[^\w-]", "", w), w)
    return re.sub(r"[^\w]", "", w)


def main():
    stt = [w for w in json.load(open(os.path.join(OUT, "stt.json")))["words"] if w.get("type") == "word"]
    sw = []                                               # слова сценария: (сцена, позиция в тексте, текст)
    for n, _, marked in SCENES:
        plain = marked.replace("**", "")
        for m in re.finditer(r"\S+", plain):
            for part in m.group().split("-") if "таймс-сквер" in m.group().lower() else [m.group()]:
                if norm(part):
                    sw.append([n, m.start(), m.end(), norm(part), None, None])
    a, b = [x[3] for x in sw], [norm(w["text"]) for w in stt]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for i, j, size in sm.get_matching_blocks():
        for k in range(size):
            sw[i + k][4], sw[i + k][5] = stt[j + k]["start"], stt[j + k]["end"]
    matched = sum(x[4] is not None for x in sw)
    for i, x in enumerate(sw):                            # пропуски — по соседям
        if x[4] is None:
            prev = next((sw[k][5] for k in range(i - 1, -1, -1) if sw[k][5] is not None), 0.0)
            nxt = next((sw[k][4] for k in range(i + 1, len(sw)) if sw[k][4] is not None), prev + 0.4)
            x[4], x[5] = prev, max(prev + 0.05, nxt)
    print(f"совпало слов: {matched} из {len(sw)}")
    for n, _, marked in SCENES:
        plain = marked.replace("**", "")
        st, en = [None] * len(plain), [None] * len(plain)
        words = {}
        for x in sw:
            if x[0] == n:
                s0, e0 = words.get((x[1], x[2]), (x[4], x[5]))
                words[(x[1], x[2])] = (min(s0, x[4]), max(e0, x[5]))
        for (p0, p1), (t0, t1) in words.items():
            L = p1 - p0
            for k in range(L):
                st[p0 + k] = t0 + (t1 - t0) * k / L
                en[p0 + k] = t0 + (t1 - t0) * (k + 1) / L
        last = min(t for t in st if t is not None)
        for k in range(len(plain)):                       # пробелы и знаки — время соседей
            if st[k] is None:
                st[k] = en[k] = last
            last = en[k]
        json.dump({"characters": list(plain), "character_start_times_seconds": st,
                   "character_end_times_seconds": en}, open(os.path.join(OUT, f"{n:02d}.json"), "w"), ensure_ascii=False)
    print("готово")


if __name__ == "__main__":
    main()
