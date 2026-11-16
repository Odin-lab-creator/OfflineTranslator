"""Озвучка «Кловерфилд, 10» голосом «Олег» (ElevenLabs «Oleg — Calm, Natural and Clear»), весь текст ОДНОЙ записью,
модель Multilingual v2 — как в «Птичьем коробе», потоком /stream/with-timestamps (обычный запрос прокси рвёт
через 30 с). Тайминг букв приходит сразу — распознавание не нужно. Ключ подставляет сетевой прокси.
python3 voice_eleven.py → voice_eleven/whole.mp3 + whole.json → voice_user/vo.mp3 + voice_user/NN.json → build.py --user
"""
import base64
import difflib
import json
import os
import re
import subprocess

from script import SCENES, plain

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice_user")
VOICE, MODEL = "MWyJiWDobXN8FX3CJTdE", "eleven_multilingual_v2"   # как в «Птичьем коробе» (сверено по звуку)
# как читать цифры и латиницу (субтитры остаются как в сценарии)
# «Птичий короб» озвучен «Олегом» на модели Multilingual v2 без ускорения (сверено по звуку с роликом):
# v2 сама читает быстрее и ровнее, чем v3. SPEED оставлен на случай, если понадобится подогнать темп.
SPEED = 1.0
VOICE_FIX = [("«Кловерфилд, 10»", "«Кловерфилд, десять»"), ("«HELP»", "«хелп»")]


def voice_line(t):
    t = plain(t)
    for a, b in VOICE_FIX:
        t = t.replace(a, b)
    return t


LINES = [voice_line(t) for _, _, t in SCENES]


def norm(w):
    return re.sub(r"[^\w]", "", w.lower().replace("ё", "е"))


def map_to_script(script_text, said, st, en):
    """Время слов произнесённого текста → время символов текста сценария («10» сказано словом «десять»)."""
    sw = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", script_text)]
    vw = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", said)]
    vt = [(st[a], en[b - 1]) for a, b, _ in vw]
    times = [None] * len(sw)
    sm = difflib.SequenceMatcher(a=[norm(x[2]) for x in sw], b=[norm(x[2]) for x in vw], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                times[i1 + d] = vt[j1 + d]
        elif i2 > i1 and j2 > j1:
            a, b = vt[j1][0], vt[j2 - 1][1]
            for d in range(i2 - i1):
                times[i1 + d] = (a + (b - a) * d / (i2 - i1), a + (b - a) * (d + 1) / (i2 - i1))
    last = st[0] if st else 0.0
    for i in range(len(times)):
        if times[i] is None:
            times[i] = (last, last + 0.05)
        last = times[i][1]
    cs, ce = [None] * len(script_text), [None] * len(script_text)
    for (p0, p1, _), (a, b) in zip(sw, times):
        for q in range(p1 - p0):
            cs[p0 + q], ce[p0 + q] = a + (b - a) * q / (p1 - p0), a + (b - a) * (q + 1) / (p1 - p0)
    last = times[0][0] if times else 0.0
    for q in range(len(script_text)):
        if cs[q] is None:
            cs[q] = ce[q] = last
        last = ce[q]
    return cs, ce


def main():
    d0 = os.path.join(HERE, "voice_eleven")
    os.makedirs(d0, exist_ok=True)
    mp3, js = os.path.join(d0, "whole.mp3"), os.path.join(d0, "whole.json")
    if not (os.path.exists(mp3) and os.path.exists(js)):
        req = os.path.join(d0, "_whole.req")
        json.dump({"text": "\n".join(LINES), "model_id": MODEL}, open(req, "w"), ensure_ascii=False)
        r = subprocess.run(["curl", "-sS", "-N", "-m", "900", "-X", "POST",
                            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/stream/with-timestamps"
                            "?output_format=mp3_44100_192",
                            "-H", "xi-api-key: proxy-injected", "-H", "Content-Type: application/json", "--data", f"@{req}"],
                           capture_output=True, text=True).stdout
        os.remove(req)
        audio, al = b"", {"characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []}
        for line in r.splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            assert "audio_base64" in d, line[:300]
            audio += base64.b64decode(d["audio_base64"] or "")
            for key in al:
                al[key] += (d.get("alignment") or {}).get(key, [])
        open(mp3, "wb").write(audio)
        json.dump(al, open(js, "w"), ensure_ascii=False)
    al = json.load(open(js))
    said, st, en = "".join(al["characters"]), al["character_start_times_seconds"], al["character_end_times_seconds"]
    assert said == "\n".join(LINES), "разметка не совпала с текстом"
    os.makedirs(OUT, exist_ok=True)
    pos = 0
    for k, (n, _, marked) in enumerate(SCENES):
        L = len(LINES[k])
        cs, ce = map_to_script(plain(marked), LINES[k], st[pos:pos + L], en[pos:pos + L])
        cs, ce = [x / SPEED for x in cs], [x / SPEED for x in ce]
        json.dump({"characters": list(plain(marked)), "character_start_times_seconds": cs,
                   "character_end_times_seconds": ce}, open(os.path.join(OUT, f"{n:02d}.json"), "w"), ensure_ascii=False)
        pos += L + 1
    vo = os.path.join(OUT, "vo.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", f"asetrate={round(44100 * SPEED)},aresample=44100",
                    "-c:a", "libmp3lame", "-b:a", "192k", vo], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vo],
                         capture_output=True, text=True).stdout.strip()
    print("одна запись:", dur, "с")


if __name__ == "__main__":
    main()
