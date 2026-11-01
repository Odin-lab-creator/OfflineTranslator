"""Мини-клиент ElevenLabs (Text to Speech).

Ключ подставляет сетевой прокси среды (сетевой секрет для api.elevenlabs.io, заголовок xi-api-key).
Запасной вариант — переменная окружения ELEVENLABS_API_KEY. В коде и репозитории ключа нет.
"""
import json
import os
import urllib.error
import urllib.request

BASE = "https://api.elevenlabs.io/v1"

VOICES = {
    "brian": "nPczCjzI2devNBz1zQrb",   # Deep, Resonant and Comforting
    "roger": "CwhRBWXzGAHq8TQ4Fs17",   # Laid-Back, Casual, Resonant
    "george": "JBFqnCBsd6RMkjVDRZzb",  # Warm, Captivating Storyteller
    "will": "bIHbv24MWmeRgasZH58o",    # Relaxed Optimist (young)
    "chris": "iP95p4xoKVk53GoZ742B",   # Charming, Down-to-Earth
    "liam": "TX3LPaxmHKxFdv7VOQHJ",    # young
    "lily": "pFZP5JQG7iQjIQuC4Bku",    # Velvety Actress
    "sarah": "EXAVITQu4vr4xnSDxMaL",   # Mature, Reassuring
    "alice": "Xb7hH8MSUJpSbSDYk0k2",
}


def _req(method, path, body=None, raw=False):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        r.add_header("xi-api-key", key)
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} → {e.code}: {e.read()[:400].decode(errors='replace')}") from None
    return data if raw else json.loads(data)


def balance():
    s = _req("GET", "/user/subscription")
    return s["character_limit"] - s["character_count"]


def tts(text, voice, path, model="eleven_multilingual_v2", stability=0.5, similarity=0.8, style=0.0, speed=1.0):
    vid = VOICES.get(voice, voice)
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": stability, "similarity_boost": similarity, "style": style,
                               "use_speaker_boost": True, "speed": speed}}
    audio = _req("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", body, raw=True)
    with open(path, "wb") as f:
        f.write(audio)
    return path
