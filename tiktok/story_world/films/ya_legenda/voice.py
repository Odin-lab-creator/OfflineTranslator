"""Озвучка «Я — легенда» (ElevenLabs, голос Brian) с разметкой времени символов.
python3 voice.py → voice/NN.mp3 + voice/NN.json (alignment); уже готовые сцены не переозвучиваются.
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "season1")))
from script import SCENES  # noqa: E402

VOICE, OUT = "brian", os.path.join(HERE, "voice")


def path(n, ext="mp3"):
    return os.path.join(OUT, f"{n:02d}.{ext}")


if __name__ == "__main__":
    import eleven
    os.makedirs(OUT, exist_ok=True)
    need = [(n, t.replace("**", "")) for n, _, t in SCENES if not os.path.exists(path(n))]
    print("символов:", sum(len(t) for _, t in need), "на счету:", eleven.balance(), flush=True)
    vid = eleven.VOICES[VOICE]
    for n, text in need:
        body = {"text": text, "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.35,
                                   "use_speaker_boost": True, "speed": 1.1}}
        r = eleven._req("POST", f"/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128", body)
        open(path(n), "wb").write(base64.b64decode(r["audio_base64"]))
        json.dump(r["alignment"], open(path(n, "json"), "w"), ensure_ascii=False)
        print(n, "ok", flush=True)
    print("осталось:", eleven.balance())
