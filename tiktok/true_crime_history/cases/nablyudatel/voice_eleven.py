"""Озвучка «Наблюдателя» голосом «Олег» (ElevenLabs, «Oleg — Calm, Natural and Clear», выбрал владелец).
Каждая сцена отдельно (с соседними фразами — для связной интонации), endpoint with-timestamps сразу отдаёт
время каждой буквы — распознавание речи не нужно. Паузы между сценами — как в voice_fish.py (PAUSE, LONG).
python3 voice_eleven.py → voice_eleven/scenes/NN.mp3 + NN.json (готовые не переозвучиваются; удали — переозвучит)
                        → voice_user/vo.mp3 + voice_user/NN.json (тайминг символов текста сценария от начала записи)
Дальше: python3 build.py --user.  Ключ подставляет сетевой прокси.
"""
import base64
import difflib
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from script import SCENES, plain, voice_line
from voice_fish import LONG, PAUSE

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(HERE, "voice_eleven", "scenes")
OUT = os.path.join(HERE, "voice_user")
VOICE, MODEL = "MWyJiWDobXN8FX3CJTdE", "eleven_multilingual_v2"
SR = 44100
LINES = [voice_line(t) for _, _, t in SCENES]


def tts_scene(k):
    n = SCENES[k][0]
    mp3, js = os.path.join(SC, f"{n:02d}.mp3"), os.path.join(SC, f"{n:02d}.json")
    if os.path.exists(mp3) and os.path.exists(js):
        return n, "есть"
    body = {"text": LINES[k], "model_id": MODEL,
            "previous_text": " ".join(LINES[max(0, k - 2):k]) or None,
            "next_text": " ".join(LINES[k + 1:k + 2]) or None}
    req = os.path.join(SC, f"_{n:02d}.req")
    json.dump({a: b for a, b in body.items() if b}, open(req, "w"), ensure_ascii=False)
    r = subprocess.run(["curl", "-sS", "-m", "300", "-X", "POST",
                        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_192",
                        "-H", "xi-api-key: proxy-injected", "-H", "Content-Type: application/json", "--data", f"@{req}"],
                       capture_output=True, text=True).stdout
    os.remove(req)
    try:
        d = json.loads(r)
        audio = base64.b64decode(d["audio_base64"])
    except Exception:
        return n, f"ошибка: {r[:300]}"
    open(mp3, "wb").write(audio)
    json.dump(d["alignment"], open(js, "w"), ensure_ascii=False)
    return n, "ok"


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def words_with_spans(text):
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]


def norm(w):
    return re.sub(r"[^\w]", "", w.lower().replace("ё", "е"))


def map_to_script(script_text, said, st, en):
    """Время слов произнесённого текста → время символов текста сценария (там «2014», а сказано словами)."""
    sw, vw = words_with_spans(script_text), words_with_spans(said)
    vt = [(st[a], en[b - 1]) for a, b, _ in vw]
    times = [None] * len(sw)
    sm = difflib.SequenceMatcher(a=[norm(x[2]) for x in sw], b=[norm(x[2]) for x in vw], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                times[i1 + d] = vt[j1 + d]
        elif i2 > i1 and j2 > j1:                         # «2014» ← «две тысячи четырнадцатый»: делим отрезок
            a, b = vt[j1][0], vt[j2 - 1][1]
            for d in range(i2 - i1):
                times[i1 + d] = (a + (b - a) * d / (i2 - i1), a + (b - a) * (d + 1) / (i2 - i1))
    last = 0.0
    for i in range(len(times)):                           # на всякий случай — пропуски по соседям
        if times[i] is None:
            times[i] = (last, last + 0.05)
        last = times[i][1]
    cs, ce = [None] * len(script_text), [None] * len(script_text)
    for (p0, p1, _), (a, b) in zip(sw, times):
        for q in range(p1 - p0):
            cs[p0 + q], ce[p0 + q] = a + (b - a) * q / (p1 - p0), a + (b - a) * (q + 1) / (p1 - p0)
    last = 0.0
    for q in range(len(script_text)):
        if cs[q] is None:
            cs[q] = ce[q] = last
        last = ce[q]
    return cs, ce


def assemble():
    os.makedirs(OUT, exist_ok=True)
    parts, t = [], 0.0
    for k, (n, _, marked) in enumerate(SCENES):
        al = json.load(open(os.path.join(SC, f"{n:02d}.json")))
        said = "".join(al["characters"])
        st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
        a = decode(os.path.join(SC, f"{n:02d}.mp3"))
        speech = [i for i, c in enumerate(said) if not c.isspace()]
        c0 = max(0.0, st[speech[0]] - 0.04)                # обрезаем тишину по краям по самой разметке
        c1 = min(len(a) / SR, en[speech[-1]] + 0.12)
        a = a[int(c0 * SR):int(c1 * SR)]
        cs, ce = map_to_script(plain(marked), said, [x - c0 + t for x in st], [x - c0 + t for x in en])
        json.dump({"characters": list(plain(marked)), "character_start_times_seconds": cs,
                   "character_end_times_seconds": ce}, open(os.path.join(OUT, f"{n:02d}.json"), "w"), ensure_ascii=False)
        gap = np.zeros(int(LONG.get(n, PAUSE) * SR), np.float32)
        parts += [a, gap]
        t += (len(a) + len(gap)) / SR
    tmp = os.path.join(OUT, "_vo.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "192k", tmp], input=np.concatenate(parts).tobytes(), check=True)
    os.replace(tmp, os.path.join(OUT, "vo.mp3"))
    print(f"vo.mp3: {t:.1f} с")


if __name__ == "__main__":
    os.makedirs(SC, exist_ok=True)
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(tts_scene, range(len(SCENES))))
    bad = [r for r in res if r[1] not in ("ok", "есть")]
    print("озвучено:", sum(r[1] == "ok" for r in res), "уже было:", sum(r[1] == "есть" for r in res))
    assert not bad, bad
    assemble()
