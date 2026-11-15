"""Озвучка «Наблюдателя» через Fish Audio — по сценам, с паузами (как «аудиокнига» на сайте, только точнее).
Голос «Инциденты» (выбрал владелец), модель speech-1.5: у неё по-русски правильные ударения
(s1 ошибается даже со знаками ударения, «+» ломает речь).
python3 voice_fish.py           → voice_fish/scenes/NN.mp3 (готовые не переозвучиваются; удали файл — переозвучит)
                                  → voice_user/vo.mp3 (сцены подряд, тишина по краям обрезана, паузы из PAUSE)
                                  → voice_user/stt.json (тайминг слов, ElevenLabs scribe_v1)
Дальше: python3 align_user.py && python3 build.py --user
Ключи подставляет сетевой прокси (сетевые секреты среды), в коде их нет.
"""
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from script import SCENES, voice_line

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(HERE, "voice_fish", "scenes")
OUT = os.path.join(HERE, "voice_user")
VOICE, MODEL = "eb8f01ad512e4f1d9d3e0b524174ee8b", "speech-1.5"
SR = 44100
PAUSE = 0.30                                   # обычная пауза после сцены, с
LONG = {1: 0.6, 8: 0.6, 12: 0.8, 13: 0.6, 14: 0.9, 18: 0.5, 23: 0.8, 24: 0.6, 25: 0.6, 31: 0.5, 35: 0.5,
        38: 0.5, 40: 0.9, 42: 0.5, 43: 0.9, 44: 0.6, 45: 0.8}   # драматичные места — подольше


def tts_scene(n, text):
    dst = os.path.join(SC, f"{n:02d}.mp3")
    if os.path.exists(dst):
        return n, "есть"
    req, tmp = os.path.join(SC, f"_{n:02d}.json"), os.path.join(SC, f"_{n:02d}.mp3")
    json.dump({"text": text, "reference_id": VOICE, "format": "mp3", "mp3_bitrate": 192, "latency": "normal"},
              open(req, "w"), ensure_ascii=False)
    code = subprocess.run(["curl", "-sS", "-m", "300", "-o", tmp, "-w", "%{http_code}", "-X", "POST",
                           "https://api.fish.audio/v1/tts", "-H", "Authorization: Bearer proxy-injected",
                           "-H", "Content-Type: application/json", "-H", f"model: {MODEL}", "--data", f"@{req}"],
                          capture_output=True, text=True).stdout
    os.remove(req)
    if code != "200":
        return n, f"ошибка {code}: {open(tmp, errors='replace').read()[:200]}"
    os.replace(tmp, dst)
    return n, "ok"


def load_trimmed(n):
    """Сцена → моно float32, тишина в начале и в конце обрезана."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(SC, f"{n:02d}.mp3"), "-af",
                          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
                          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse",
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def assemble():
    os.makedirs(OUT, exist_ok=True)
    parts, marks, t = [], {}, 0.0
    for n, _, _ in SCENES:
        a = load_trimmed(n)
        marks[n] = [round(t, 3), round(t + len(a) / SR, 3)]
        gap = np.zeros(int(LONG.get(n, PAUSE) * SR), np.float32)
        parts += [a, gap]
        t += (len(a) + len(gap)) / SR
    audio = np.concatenate(parts)
    tmp = os.path.join(OUT, "_vo.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "192k", tmp], input=audio.tobytes(), check=True)
    os.replace(tmp, os.path.join(OUT, "vo.mp3"))
    json.dump(marks, open(os.path.join(OUT, "scenes.json"), "w"))
    print(f"vo.mp3: {t:.1f} с")


def stt():
    r = subprocess.run(["curl", "-sS", "-m", "600", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text",
                        "-H", "xi-api-key: proxy-injected", "-F", f"file=@{os.path.join(OUT, 'vo.mp3')}",
                        "-F", "model_id=scribe_v1", "-F", "language_code=rus", "-F", "timestamps_granularity=word"],
                       capture_output=True, text=True).stdout
    d = json.loads(r)
    assert "words" in d, r[:500]
    json.dump(d, open(os.path.join(OUT, "stt.json"), "w"), ensure_ascii=False)
    print("stt.json: слов", sum(w.get("type") == "word" for w in d["words"]))


if __name__ == "__main__":
    os.makedirs(SC, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda x: tts_scene(x[0], voice_line(x[2])), SCENES))
    bad = [r for r in res if r[1] not in ("ok", "есть")]
    print("озвучено сцен:", sum(r[1] == "ok" for r in res), "уже было:", sum(r[1] == "есть" for r in res))
    assert not bad, bad
    assemble()
    stt()
