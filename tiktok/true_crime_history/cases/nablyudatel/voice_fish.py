"""Озвучка «Наблюдателя» через Fish Audio (выбрал владелец: голос «Молодой Аналитик», модель speech-1.5 —
у неё по-русски правильные ударения; s1 ошибается даже со знаками ударения, «+» ломает речь).
python3 voice_fish.py        → voice_user/vo.mp3 (весь текст script.voice_text() одной записью)
python3 voice_fish.py --stt  → voice_user/stt.json (тайминг слов, ElevenLabs scribe_v1)
Дальше: python3 align_user.py && python3 build.py --user
Ключи подставляет сетевой прокси (сетевые секреты среды), в коде их нет.
"""
import json
import os
import subprocess
import sys

from script import voice_text

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voice_user")
VOICE, MODEL = "868377a7b08f4c0d9acf8c9f059571aa", "speech-1.5"


def tts():
    os.makedirs(OUT, exist_ok=True)
    req = os.path.join(OUT, "_req.json")
    json.dump({"text": voice_text(), "reference_id": VOICE, "format": "mp3", "mp3_bitrate": 192, "latency": "normal"},
              open(req, "w"), ensure_ascii=False)
    tmp = os.path.join(OUT, "_vo.mp3")
    code = subprocess.run(["curl", "-sS", "-m", "1200", "-o", tmp, "-w", "%{http_code}", "-X", "POST",
                           "https://api.fish.audio/v1/tts", "-H", "Authorization: Bearer proxy-injected",
                           "-H", "Content-Type: application/json", "-H", f"model: {MODEL}", "--data", f"@{req}"],
                          capture_output=True, text=True).stdout
    os.remove(req)
    assert code == "200", open(tmp, errors="replace").read()[:500]
    os.replace(tmp, os.path.join(OUT, "vo.mp3"))
    print("vo.mp3 готов")


def stt():
    r = subprocess.run(["curl", "-sS", "-m", "600", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text",
                        "-H", "xi-api-key: proxy-injected", "-F", f"file=@{os.path.join(OUT, 'vo.mp3')}",
                        "-F", "model_id=scribe_v1", "-F", "language_code=rus", "-F", "timestamps_granularity=word"],
                       capture_output=True, text=True).stdout
    d = json.loads(r)
    assert "words" in d, r[:500]
    json.dump(d, open(os.path.join(OUT, "stt.json"), "w"), ensure_ascii=False)
    print("stt.json готов, слов:", sum(w.get("type") == "word" for w in d["words"]))


if __name__ == "__main__":
    stt() if "--stt" in sys.argv else tts()
