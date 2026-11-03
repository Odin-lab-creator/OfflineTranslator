"""«ЗАПЕРТЫЙ — история за минуту»: текст рассказчика и генерация озвучки ElevenLabs с разметкой времени слов.

python3 minute_lines.py  → voice/NN.mp3 + voice/NN.json (время начала и конца каждого символа)
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "season1")))

VOICE = "brian"
OUT = os.path.join(HERE, "voice")

LINES = [
    ("01", "Он очнулся на полу собственной квартиры. И сразу понял: что-то не так."),
    ("02", "Денису тридцать один. Третий этаж, девятая квартира."),
    ("03", "Телефон мёртвый. Света нет. Часы встали без двадцати четыре."),
    ("04", "Из крана — две капли. И тишина."),
    ("05", "Он подошёл к окну — и замер. Решётки. Которых здесь никогда не было."),
    ("06", "Сварка свежая. И варили снаружи."),
    ("07", "Двери соседей распахнуты настежь. Будто все уходили бегом."),
    ("08", "Он кричит в подъезд. Отвечает только эхо."),
    ("09", "На стене стрелка: «К автобусам». Каким ещё автобусам?"),
    ("10", "Внизу дверь подъезда. Он бьёт её снова и снова."),
    ("11", "А в щели видно: дверь не заперта. Её заварили."),
    ("12", "Город пуст. Дом закрыт. А он остался внутри."),
    ("13", "Как выбраться из дома, которого больше нет на карте? Подпишись — узнаешь в следующей серии."),
]


def path(i, ext="mp3"):
    return os.path.join(OUT, f"{i}.{ext}")


if __name__ == "__main__":
    import eleven
    os.makedirs(OUT, exist_ok=True)
    need = [(i, t) for i, t in LINES if not os.path.exists(path(i))]
    print("символов:", sum(len(t) for _, t in need), "на счету:", eleven.balance())
    vid = eleven.VOICES[VOICE]
    for i, text in need:
        body = {"text": text, "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.42, "similarity_boost": 0.8, "style": 0.3,
                                   "use_speaker_boost": True, "speed": 1.05}}
        r = eleven._req("POST", f"/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128", body)
        open(path(i), "wb").write(base64.b64decode(r["audio_base64"]))
        json.dump(r["alignment"], open(path(i, "json"), "w"), ensure_ascii=False)
        print(i, "ok", flush=True)
