#!/usr/bin/env python3
"""Озвучка серии (потоком /stream — длинный запрос без потока прокси обрывает с 502) голосом «Олег» (ElevenLabs, модель eleven_v3) ОДНОЙ записью + распознавание слов (scribe_v1).
python3 voice_eleven.py 1   →  ep1_voice/vo.mp3 + ep1_voice/stt.json
Ключ подставляет прокси среды (заголовок xi-api-key: proxy-injected)."""
import importlib
import json
import os
import sys
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE_ID = "MWyJiWDobXN8FX3CJTdE"            # «Oleg» из библиотеки ElevenLabs
API = "https://api.elevenlabs.io/v1"


def post(url, data, ctype):
    r = urllib.request.Request(url, data=data, method="POST")
    r.add_header("xi-api-key", "proxy-injected")
    r.add_header("Content-Type", ctype)
    with urllib.request.urlopen(r, timeout=600) as resp:
        return resp.read()


def main(ep):
    m = importlib.import_module(f"ep{ep}")
    out = os.path.join(HERE, m.VOICE)
    os.makedirs(out, exist_ok=True)
    text = "\n".join(t.replace("**", "") for _, _, t, _ in m.SCENES)
    body = {"text": text, "model_id": "eleven_v3", "voice_settings": {"stability": 0.5}}
    audio = post(f"{API}/text-to-speech/{VOICE_ID}/stream?output_format=mp3_44100_128", json.dumps(body).encode(), "application/json")
    mp3 = os.path.join(out, "vo.mp3")
    open(mp3, "wb").write(audio)
    print("озвучка:", mp3, len(audio) // 1024, "КБ", len(text), "симв.")
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("model_id", "scribe_v1"), ("language_code", "rus"), ("timestamps_granularity", "word")):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="vo.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                 + audio + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    stt = post(f"{API}/speech-to-text", b"".join(parts), f"multipart/form-data; boundary={b}")
    json.dump(json.loads(stt), open(os.path.join(out, "stt.json"), "w"), ensure_ascii=False, indent=1)
    print("слова:", os.path.join(out, "stt.json"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1")
