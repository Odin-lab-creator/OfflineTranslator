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
# «Птичий короб» озвучен «Олегом» на модели Multilingual v2 (сверено по звуку с роликом).
# Владелец: «быстрее и выразительнее, как в Птичьем коробе» → ниже стабильность, выше «стиль», скорость 1.08.
SPEED = 1.0                                   # ресемплинг после записи (1.0 — не трогать)
SETTINGS = {"stability": 0.35, "similarity_boost": 0.8, "style": 0.45, "use_speaker_boost": True, "speed": 1.08}

# Текст для озвучки с ударениями: «+» сразу после ударной гласной (превращается в знак ударения U+0301).
# Цифры и латиница — словами. Субтитры берутся из script.py.
STRESSED = [
    "«Кловерфи+лд, де+сять». Сюже+т за мину+ту.",
    "Мише+ль ссо+рится с женихо+м и но+чью уезжа+ет из го+рода.",
    "На пусто+й тра+ссе в её маши+ну вреза+ется грузови+к.",
    "Она+ прихо+дит в себя+ в бето+нной ко+мнате, прико+ванная к стене+.",
    "Хозя+ин бу+нкера Го+вард говори+т, что спас ей жизнь.",
    "Снару+жи была+ ата+ка, и во+здух отра+влен.",
    "В бу+нкере пря+чется ещё сосе+д Э+ммет.",
    "Мише+ль не ве+рит и пыта+ется сбежа+ть.",
    "Но за две+рью же+нщина в я+звах умоля+ет её впусти+ть.",
    "Зна+чит, Го+вард говори+л пра+вду.",
    "Втроём они+ игра+ют в насто+лки и смо+трят ста+рые фи+льмы.",
    "Го+вард пока+зывает фо+то свое+й до+чери Ме+ган.",
    "Но в вентиля+ции Мише+ль нахо+дит нацара+панное сло+во «хелп»",
    "и серьгу+ пропа+вшей де+вушки. Ме+ган ему+ не дочь.",
    "Мише+ль и Э+ммет понима+ют: настоя+щий монстр — Го+вард.",
    "Тайко+м они+ шьют защи+тный костю+м из што+рки для ду+ша.",
    "Го+вард нахо+дит ма+ску. Э+ммет берёт вину+ на себя+,",
    "и Го+вард стреля+ет в него+.",
    "Мише+ль надева+ет костю+м и бежи+т.",
    "Го+вард броса+ется сле+дом, и она+ опроки+дывает на него+ бо+чку с кислото+й.",
    "Бу+нкер вспы+хивает, и Мише+ль выбира+ется нару+жу.",
    "Она+ снима+ет ма+ску: во+здух чи+стый, пою+т пти+цы.",
    "Неуже+ли Го+вард всё вы+думал?",
    "Но в не+бе виси+т огро+мный инопла+нетный кора+бль.",
    "Из него+ выполза+ет тварь и броса+ется за Мише+ль.",
    "Кора+бль поднима+ет её маши+ну в во+здух,",
    "но Мише+ль броса+ет в него+ буты+лку ви+ски с горя+щей тря+пкой.",
    "Кора+бль взрыва+ется.",
    "По ра+дио вы+живших зову+т в укры+тие, а Мише+ль е+дет туда+, где идёт бой.",
    "А ты бы оста+лся в бу+нкере с Го+вардом и+ли вы+шел нару+жу? Пиши+ в коммента+риях!",
]


def stress(t):
    """«+» стоит сразу после ударной гласной → знак ударения U+0301 на этой гласной."""
    return t.replace("+", "\u0301")


LINES = [stress(t) for t in STRESSED]
assert len(LINES) == len(SCENES)


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
        json.dump({"text": "\n".join(LINES), "model_id": MODEL, "voice_settings": SETTINGS}, open(req, "w"), ensure_ascii=False)
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
    # строки сцен по переводам строк в произнесённом тексте (знаки ударения могут прийти отдельными символами)
    cuts = [-1] + [i for i, c in enumerate(said) if c == "\n"] + [len(said)]
    assert len(cuts) - 1 == len(SCENES), (len(cuts) - 1, "строк вместо", len(SCENES))
    os.makedirs(OUT, exist_ok=True)
    for k, (n, _, marked) in enumerate(SCENES):
        a, b = cuts[k] + 1, cuts[k + 1]
        cs, ce = map_to_script(plain(marked), said[a:b], st[a:b], en[a:b])
        cs, ce = [x / SPEED for x in cs], [x / SPEED for x in ce]
        json.dump({"characters": list(plain(marked)), "character_start_times_seconds": cs,
                   "character_end_times_seconds": ce}, open(os.path.join(OUT, f"{n:02d}.json"), "w"), ensure_ascii=False)
    vo = os.path.join(OUT, "vo.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", f"asetrate={round(44100 * SPEED)},aresample=44100",
                    "-c:a", "libmp3lame", "-b:a", "192k", vo], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vo],
                         capture_output=True, text=True).stdout.strip()
    print("одна запись:", dur, "с")


if __name__ == "__main__":
    main()
