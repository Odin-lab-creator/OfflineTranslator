#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1 — тестовая версия в стиле канала story world (как ролик про Мирона).

python3 ep1_sw.py [preview]  →  zapertyy_ep1_sw.mp4 (1080×1920, 30 к/с)

Сверху сцена: яркий пиксель-арт, вид сбоку (фоны art/sw, Денис art/sto/denis с анимациями).
Снизу панель: крупная надпись «караоке» (сказанные слова белые / цветные, ещё не сказанные — серые),
под ней «бумажные» элементы: шкала дней, записка от руки, список. Метки в углу, схема, выбор в конце.
Озвучка — voice/ep1 (×1.06), шумы — comic_engine.
"""
import functools
import glob
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import comic_engine as ce
from ep1_lines import LINES, path as vpath

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "art")
SWD = os.path.join(ART, "sw")
DEN = os.path.join(ART, "sto", "denis")
OUT = os.path.join(HERE, "zapertyy_ep1_sw.mp4")
FPS = 30
W, H, SCENE_H = 1080, 1920, 1140

F_CAP = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_SANS = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
F_HAND = os.path.join(HERE, "fonts", "Caveat-Medium.ttf")
DAY, NIGHT = (44, 50, 33), (16, 14, 30)
WHITE, GREY, YELLOW, RED = (246, 244, 238), (122, 120, 132), (247, 190, 44), (232, 62, 62)
BLUE, GREEN = (70, 146, 236), (60, 200, 120)
PAPER, PAPER_LINE, INK, NUM = (247, 241, 231), (216, 210, 200), (38, 34, 30), (150, 146, 140)
C_PAINT = (176, 52, 44)


@functools.lru_cache(None)
def font(p, s):
    return ImageFont.truetype(p, s)


# ------------------------------------------------------------------ ресурсы
@functools.lru_cache(None)
def bg(name):
    a = np.asarray(Image.open(os.path.join(SWD, name)).convert("RGB")).copy()
    rows = np.nonzero(a.mean((1, 2)) >= 16)[0]
    a = a[rows.min():rows.max() + 1].copy()
    if name == "bg_stairs.png":                                # надпись краской и стрелка вниз
        f = ImageFont.truetype(F_CAP, 11)
        m = Image.new("1", (120, 16), 0)
        d = ImageDraw.Draw(m)
        d.fontmode = "1"
        d.text((0, 0), "К АВТОБУСАМ", font=f, fill=1)
        ys, xs = np.nonzero(np.asarray(m, bool))
        a[ys + 34, xs + 128] = C_PAINT
        cx = 162
        a[54:84, cx - 2:cx + 2] = C_PAINT
        for k in range(10):
            a[80 + k, cx - 10 + k:cx + 10 - k] = C_PAINT
    return Image.fromarray(a)


@functools.lru_cache(None)
def anim(name):
    fs = sorted(glob.glob(os.path.join(DEN, f"Idle__animations__{name}__frame_*.png")))
    fr = [Image.open(f).convert("RGBA") for f in fs]
    floor = max(int(np.nonzero(np.asarray(f)[..., 3] > 127)[0].max()) for f in fr)
    return fr, floor


@functools.lru_cache(None)
def obj(name):
    im = Image.open(os.path.join(ART, "sto", f"obj_{name}.png")).convert("RGBA")
    if name == "weld":                                         # рукав — серый, как толстовка
        a = np.asarray(im).copy()
        rgb = a[..., :3].astype(int)
        red = (rgb[..., 0] > rgb[..., 1] + 40) & (rgb[..., 0] > rgb[..., 2] + 40) & (a[..., 3] > 0)
        lum = (rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11) * 0.9 + 25
        a[red, 0] = lum[red]
        a[red, 1] = lum[red]
        a[red, 2] = np.minimum(255, lum[red] * 1.06)
        im = Image.fromarray(a, "RGBA")
    return im


# ------------------------------------------------------------------ таймлайн
ep = ce.Episode([(i, t, kw) for i, _, t, kw in LINES], vpath, OUT)
ep.voice_fx["12"] = "echo"
for i in ("13", "14", "15", "16", "17"):
    ep.voice_fx[i] = "reverb"
WIDGETS, TAGS, KICKS = [], [], []
ACCENT = {"00": {"дверь": RED}, "01": {"тишину": YELLOW, "мир": RED}, "02": {"кровь": RED}, "03": {"денис": YELLOW},
          "04": {"суток": YELLOW}, "05": {"болел": RED}, "06": {"всё": RED}, "07": {"решётки": RED, "решёток": RED},
          "08": {"свежие": YELLOW}, "09": {"человека": RED}, "10": {"заперта": YELLOW}, "11": {"бегом": YELLOW},
          "12": {"живой": YELLOW}, "13": {"никто": RED}, "14": {"автобусам": YELLOW}, "15": {"обесточен": YELLOW},
          "16": {"стена": RED}, "17": {"заварили": RED}, "18": {"вышел": RED}, "19": {"вошёл": RED}}


def scene(at=None, **kw):
    ep.shot("s", at=at, **kw)


def widget(kind, data, t0, t1=None):
    WIDGETS.append([t0, t1, kind, data])


def close_widgets(t):
    for w in WIDGETS:
        if w[1] is None:
            w[1] = t


def tag(text, col, t0, t1):
    TAGS.append((t0, t1, text, col))


def kicks(t0, n, fps=10, loop=13, hit=8.5):
    return [t0 + (k * loop + hit) / fps for k in range(n)]


# 00 · зацепка: ночь, удары в дверь
scene(bg="bg_hall.png", cam=0, night=True, actors=[("kick-c5cfb681__north", 92, 92, 178, 0, 99, 10, True)])
KICKS += kicks(0.0, 3)
for t in KICKS:
    ep.fx("bang", t)
ep.wait(2.6)
ep.say("00", 0.6)
# 01–02 · очнулся
scene(bg="bg_room.png", cam=0, lying=(104, 199))
T = ep.t
tag("ДЕНЬ 1", BLUE, T, T + 9)
widget("timeline", 1, T)
ep.fx("ring")
ep.wait(0.6)
ep.say("01", 0.5)
ep.say("02", 0.4)
close_widgets(ep.t)
# 03 · встал
scene(bg="bg_room.png", cam=20, actors=[("breathing_idle__east", 150, 150, 199, 0, 99, 3, True)])
widget("note", ["Денис Кравцов. 31 год. Кв. 9"], ep.t)
ep.say("03", 0.4)
close_widgets(ep.t)
# 04–06 · что я знаю
T = ep.t
tag("ЧТО Я ЗНАЮ", YELLOW, T, T + 4)
t04 = ep.say("04", 0.0)
c04 = ep.chunk_times("04", t04)
widget("list", (["Связи нет", "Света нет"], 1), T, c04[1][0])
scene(bg="bg_room.png", cam=20, at=c04[1][0], insert="phone", label="НЕТ СЕТИ")
widget("list", (["Связи нет", "Света нет"], 1), c04[1][0], c04[2][0])
scene(at=c04[2][0], bg="bg_room.png", cam=20, insert="watch", label="3:40")
widget("list", (["Связи нет", "Света нет", "Часы стоят"], 2), c04[2][0])
ep.wait(0.45)
close_widgets(ep.t)
scene(bg="bg_room.png", cam=20, insert="pills", label="ЖАРОПОНИЖАЮЩЕЕ")
widget("list", (["Связи нет", "Света нет", "Часы стоят"], 2), ep.t)
ep.say("05", 0.35)
close_widgets(ep.t)
scene(bg="bg_room.png", cam=20, insert="tap", label="СУХО")
widget("list", (["Связи нет", "Света нет", "Часы стоят", "Воды нет"], 3), ep.t)
ep.fx("drip")
ep.wait(0.35)
ep.say("06", 0.15)
ep.fx("drip")
ep.wait(0.6)
ep.fx("drip")
ep.wait(0.4)
close_widgets(ep.t)
# 07–09 · окно
scene(bg="bg_room.png", cam=96, actors=[("breathing_idle__north", 190, 190, 199, 0, 99, 3, True)])
T = ep.t
tag("3 ЭТАЖ", BLUE, T, T + 5)
widget("note", ["Решётки снаружи."], T)
ep.fx("whoosh", ep.t + 0.1)
ep.wait(0.3)
ep.say("07", 0.3)
close_widgets(ep.t)
scene(bg="bg_room.png", cam=96, insert="weld", label="СВЕЖИЕ ШВЫ", rattle=True)
widget("note", ["Решётки снаружи. Швы свежие."], ep.t)
for k in range(6):
    ep.fx("rattle", ep.t + 0.1 + k * 0.32)
ep.say("08", 0.3)
scene(bg="bg_street.png", cam=60, bars=True)
ep.wait(0.2)
ep.say("09", 0.5)
close_widgets(ep.t)
# 10–13 · коридор
T = ep.t
scene(bg="v1/bg_corridor.png", cam=112, actors=[("walking__east", 96, 176, 176, 0.2, 2.6, 10, True),
                                                 ("breathing_idle__east", 176, 176, 176, 2.6, 99, 3, True)])
for k in range(7):
    ep.fx("step", T + 0.3 + k * 0.34)
ep.fx("creak", T)
widget("list", (["Связи нет", "Света нет", "Часы стоят", "Воды нет"], 3), T)
ep.wait(0.3)
ep.say("10", 0.35)
ep.say("11", 0.4)
close_widgets(ep.t)
widget("list", (["Связи нет", "Света нет", "Воды нет", "Соседей нет"], 3), ep.t)
T = ep.t
scene(bg="v1/bg_corridor.png", cam=112, actors=[("shout__east", 176, 176, 176, 0, 1.6, 8, False),
                                                 ("breathing_idle__east", 176, 176, 176, 1.6, 99, 3, True)],
      shake_at=(0.0, 1.0))
ep.say("12", 1.2)
ep.say("13", 0.4)
close_widgets(ep.t)
# 14 · лестница
T = ep.t
scene(bg="bg_stairs.png", cam=40, actors=[("walking__east", 30, 150, 210, 0.0, 3.6, 10, True),
                                           ("breathing_idle__east", 150, 150, 210, 3.6, 99, 3, True)])
for k in range(10):
    ep.fx("step", T + 0.2 + k * 0.34)
widget("timeline", 1, T)
ep.wait(0.4)
ep.say("14", 0.4)
close_widgets(ep.t)
# 15–17 · дверь подъезда
T = ep.t
scene(bg="bg_hall.png", cam=0, actors=[("walking__east", -20, 88, 178, 0.0, 2.2, 10, True),
                                        ("breathing_idle__north", 92, 92, 178, 2.2, 99, 3, True)])
for k in range(6):
    ep.fx("step", T + 0.2 + k * 0.34)
tag("ПОПЫТКА №1", RED, T, T + 99)
widget("list", (["Дверь подъезда", "", "", ""], 0, ()), T)
ep.wait(1.6)
t15 = ep.say("15", 0.2)
c15 = ep.chunk_times("15", t15)
if len(c15) > 1:
    scene(at=c15[1][0], bg="bg_hall.png", cam=0, insert="intercom", label="НЕ ГОРИТ")
    ep.fx("rattle", c15[1][0] + 0.3)
T = ep.t
scene(bg="bg_hall.png", cam=0, actors=[("kick-c5cfb681__north", 92, 92, 178, 0, 3.9, 10, True),
                                        ("breathing_idle__north", 92, 92, 178, 3.9, 99, 3, True)], kick=True)
KK = kicks(T, 3)
KICKS += KK
for t in KK:
    ep.fx("bang", t)
ep.wait(0.4)
ep.say("16", 0.3)
close_widgets(ep.t)
TAGS[-1] = (TAGS[-1][0], ep.t, TAGS[-1][2], TAGS[-1][3])
scene(bg="bg_hall.png", cam=0, insert="crack", label="ЗАВАРЕНО")
widget("list", (["Дверь подъезда", "", "", ""], 0, (0,)), ep.t)
ep.wait(0.3)
ep.say("17", 0.5)
close_widgets(ep.t)
# 18 · схема
scene(diagram=True, night=True)
T_DIA = ep.t
ep.say("18", 0.8)
T_DIA_END = ep.t
# 19 · финал
scene(bg="bg_hall.png", cam=0, night=True, actors=[("sit__south", 92, 92, 178, 0, 99, 5, False)])
T_END = ep.t
ep.fx("slide", ep.t + 0.2)
ep.wait(0.3)
ep.say("19", 0.6)
T_Q = ep.t
widget("timeline", 1, T_END)
ep.wait(4.2)
close_widgets(ep.t)
ep.finish()
TOTAL = ep.total
for k, s in enumerate(ep.shots):                             # время конца каждой сцены
    s[1] = ep.shots[k + 1][0] if k + 1 < len(ep.shots) else TOTAL


# ------------------------------------------------------------------ сцена
def put(art, im, x, feet, floor):
    art.alpha_composite(im, (int(round(x - im.width / 2)), int(round(feet - floor))))


def scene_frame(s, t):
    t0, t1, _, _, _, ex = s
    lt = t - t0
    if ex.get("diagram"):
        return None
    b = bg(ex["bg"])
    sc = max(SCENE_H / b.height, W / b.width)
    cw = int(round(W / sc))
    art = b.convert("RGBA")
    if ex.get("lying"):
        im = obj("lying")
        x, feet = ex["lying"]
        art.alpha_composite(im, (x - im.width // 2, feet - 31))
    for name, x0, x1, feet, a0, a1, fps, loop in ex.get("actors", []):
        if not (a0 <= lt < a1):
            continue
        fr, floor = anim(name)
        u = min(1.0, (lt - a0) / max(1e-6, (a1 - a0))) if x0 != x1 else 0
        k = int((lt - a0) * fps)
        k = k % len(fr) if loop else min(k, len(fr) - 1)
        put(art, fr[k], x0 + (x1 - x0) * u, feet, floor)
    cam = ex.get("cam", 0)
    cam = int(min(max(0, cam), b.width - cw))
    crop = art.crop((cam, 0, cam + cw, b.height)).convert("RGB")
    img = crop.resize((W, int(round(b.height * sc))), Image.NEAREST)
    a = np.asarray(img)[:SCENE_H].astype(np.float32)
    if ex.get("bars"):                                         # решётка поверх улицы
        for x in range(70, W, 190):
            a[:, x:x + 30] = a[:, x:x + 30] * 0.1 + 14
            a[:, x + 6:x + 11] = a[:, x + 6:x + 11] * 0.4 + 70
        a[:40] = 26
        a[SCENE_H - 60:] = a[SCENE_H - 60:] * 0.2 + 20
    if ex.get("insert"):
        a = a * 0.3 + np.array(DAY) * 0.15
    if ex.get("night"):
        a = a * 0.42 + np.array((6, 8, 26))
    dx = 0
    if ex.get("kick") or ex.get("night"):
        for x in KICKS:
            if 0 <= t - x < 0.14:
                dx = int(np.random.default_rng(int(t * 1000)).integers(-12, 13))
    if "shake_at" in ex and ex["shake_at"][0] <= lt < ex["shake_at"][1]:
        dx = int(np.random.default_rng(int(t * 1000)).integers(-5, 6))
    if ex.get("rattle"):
        for x in ep.rattles:
            if 0 <= t - x < 0.1:
                dx = int(np.random.default_rng(int(t * 1000)).integers(-8, 9))
    if dx:
        a = np.roll(a, dx, 1)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if ex.get("insert"):
        o = obj(ex["insert"])
        o = o.crop(o.getbbox())
        f = max(2, int(min(820 / o.width, 760 / o.height)))
        o = o.resize((o.width * f, o.height * f), Image.NEAREST)
        out.paste(o, ((W - o.width) // 2, (SCENE_H - o.height) // 2 + 40), o)
        d = ImageDraw.Draw(out)
        fm = font(F_MONO, 34)
        tw = d.textlength(ex["label"], font=fm)
        x0, y0 = (W - tw) / 2 - 22, 150
        d.rectangle((x0, y0, x0 + tw + 44, y0 + 70), fill=(14, 15, 24), outline=WHITE, width=4)
        d.text((x0 + 22, y0 + 15), ex["label"], font=fm, fill=WHITE)
    return out


def diagram_img(t):
    img = Image.new("RGB", (W, SCENE_H), NIGHT)
    d = ImageDraw.Draw(img)
    fm = font(F_MONO, 36)
    k_vis = int((t - T_DIA) / max(0.1, (T_DIA_END - T_DIA - 0.8)) * 4) + 1

    def box(cx, cy, text, col):
        tw = d.textlength(text, font=fm)
        d.rectangle((cx - tw / 2 - 26, cy - 38, cx + tw / 2 + 26, cy + 38), fill=(14, 15, 24), outline=col, width=5)
        d.text((cx - tw / 2, cy - 24), text, font=fm, fill=WHITE)

    rows = [("ОКНА", "РЕШЁТКИ"), ("ДВЕРЬ", "ЗАВАРЕНА"), ("ГОРОД", "ПУСТ")]
    for k, (l, r) in enumerate(rows[:k_vis]):
        y = 230 + k * 210
        d.line((300, y, 770, y), fill=BLUE, width=5)
        if k_vis >= 4:
            d.line((770, y, 770, 940), fill=RED, width=5)
        box(300, y, l, BLUE)
        box(770, y, r, BLUE)
    if k_vis >= 4:
        d.line((90, 940, 990, 940), fill=RED, width=5)
        box(540, 940, "КТО-ТО ПОСТАРАЛСЯ", RED)
    return img


# ------------------------------------------------------------------ панель
def words_of(text):
    return [w for w in text.split() if w]


def karaoke(t):
    for a, b, text in ep.subs:
        if a <= t < b:
            i = next(i for t0, i in ep.said if t0 <= a + 1e-6 and a < t0 + ep.dur[i] + 0.01)
            ws = words_of(text)
            total = sum(len(w) + 1 for w in ws)
            acc, out = 0, []
            for w in ws:
                ts = a + (b - 0.12 - a) * acc / total
                acc += len(w) + 1
                key = w.lower().strip(".,!?…:;«»—\"")
                col = ACCENT.get(i, {}).get(key, WHITE) if t >= ts else GREY
                out.append((w.upper(), col))
            return tuple(out)
    return ()


def draw_caption(d, words, y=1196):
    size = 74
    f = font(F_CAP, size)

    def layout(f):
        lines, cur = [], []
        for w in words:
            test = " ".join(x for x, _ in cur + [w])
            if cur and d.textlength(test, font=f) > 980:
                lines.append(cur)
                cur = [w]
            else:
                cur.append(w)
        lines.append(cur)
        return lines

    lines = layout(f)
    if len(lines) > 2:
        size = 62
        f = font(F_CAP, size)
        lines = layout(f)
    lh = int(size * 1.16)
    for k, ln in enumerate(lines):
        total = d.textlength(" ".join(x for x, _ in ln), font=f)
        x = (W - total) / 2
        for w, col in ln:
            d.text((x, y + k * lh), w, font=f, fill=col)
            x += d.textlength(w + " ", font=f)


def draw_timeline(d, day, marks=(1, 4, 7, 10)):
    x0, x1, yl, ylab = 122, 962, 1609, 1530
    pos = lambda v: x0 + (x1 - x0) * (v - 1) / 9
    d.line((x0, yl, x1, yl), fill=(70, 66, 84), width=5)
    d.line((x0, yl, pos(day), yl), fill=RED, width=5)
    fl, fb = font(F_MONO, 30), font(F_MONO, 34)
    for v in marks:
        if v == day:
            continue
        d.rectangle((pos(v) - 9, yl - 9, pos(v) + 9, yl + 9), fill=RED if v < day else (70, 66, 84))
        d.text((pos(v) - d.textlength(str(v), font=fl) / 2, ylab), str(v), font=fl, fill=GREY)
    lab = f"ДЕНЬ {day}"
    tw = d.textlength(lab, font=fb)
    d.text((min(max(pos(day) - tw / 2, x0 - 40), x1 + 40 - tw), ylab - 2), lab, font=fb, fill=WHITE)
    d.rectangle((pos(day) - 15, yl - 15, pos(day) + 15, yl + 15), fill=RED)


def draw_note(d, lines, y=1452):
    d.rectangle((112, y, 968, y + 112), fill=PAPER, outline=(210, 209, 194), width=3)
    d.text((150, y + 22), " ".join(lines), font=font(F_HAND, 58), fill=INK)


def draw_list(d, items, current, strike=(), y=1452):
    d.rectangle((112, y, 968, y + 330), fill=PAPER, outline=(210, 209, 194), width=3)
    fn, fh = font(F_SANS, 36), font(F_HAND, 56)
    for k in range(4):
        ry = y + 14 + k * 78
        d.text((152, ry + 14), str(k + 1), font=fn, fill=RED if k == current else NUM)
        if k < len(items) and items[k]:
            d.text((214, ry + 2), items[k], font=fh, fill=INK)
            if k in strike:
                w = d.textlength(items[k], font=fh)
                d.line((210, ry + 42, 220 + w, ry + 36), fill=RED, width=6)
        if k < 3:
            d.line((140, ry + 74, 940, ry + 74), fill=PAPER_LINE, width=3)


def draw_tag(d, text, col):
    f = font(F_MONO, 34)
    tw = d.textlength(text, font=f)
    d.rectangle((49, 49, 49 + tw + 44, 49 + 74), fill=(14, 15, 24), outline=col, width=5)
    d.text((71, 65), text, font=f, fill=WHITE)


def draw_choice(d):
    f = font(F_CAP, 46)
    for k, (text, col) in enumerate((("ИСКАТЬ ВОДУ", GREEN), ("ЛОМАТЬ ДВЕРЬ", RED))):
        x0 = 70 + k * 490
        d.rectangle((x0, 110, x0 + 450, 262), fill=(14, 15, 24), outline=col, width=6)
        tw = d.textlength(text, font=f)
        d.text((x0 + 225 - tw / 2, 160), text, font=f, fill=WHITE)


@functools.lru_cache(512)
def panel(night, words, widget_state, tag_state, ending):
    img = Image.new("RGB", (W, H - SCENE_H), NIGHT if night else DAY)
    d = ImageDraw.Draw(img)
    if ending:
        draw_caption_static(d)
    elif words:
        draw_caption(_Shift(d), words)
    if widget_state:
        kind, data = widget_state
        dd = _Shift(d)
        if kind == "timeline":
            draw_timeline(dd, data)
        elif kind == "note":
            draw_note(dd, list(data))
        elif kind == "list":
            items, cur = data[0], data[1]
            strike = data[2] if len(data) > 2 else ()
            draw_list(dd, list(items), cur, strike)
    return img


class _Shift:
    """Рисование в координатах всего кадра на изображении панели (сдвиг на SCENE_H)."""

    def __init__(self, d):
        self.d = d

    def textlength(self, *a, **k):
        return self.d.textlength(*a, **k)

    def text(self, xy, *a, **k):
        self.d.text((xy[0], xy[1] - SCENE_H), *a, **k)

    def line(self, xy, **k):
        self.d.line([v - SCENE_H if i % 2 else v for i, v in enumerate(xy)], **k)

    def rectangle(self, xy, **k):
        self.d.rectangle([v - SCENE_H if i % 2 else v for i, v in enumerate(xy)], **k)


def draw_caption_static(d):
    draw_caption(_Shift(d), (("А", WHITE), ("ЧТО", WHITE), ("БЫ", WHITE), ("ВЫ", WHITE), ("СДЕЛАЛИ", WHITE),
                             ("ПЕРВЫМ?", YELLOW)))


def tolist(x):
    return tuple(tolist(v) if isinstance(v, (list, tuple)) else v for v in x) if isinstance(x, (list, tuple)) else x


def render(t):
    s = next((s for s in ep.shots if s[0] <= t < s[1]), ep.shots[-1])
    ex = s[5]
    sc = diagram_img(t) if ex.get("diagram") else scene_frame(s, t)
    frame = Image.new("RGB", (W, H), NIGHT if ex.get("night") else DAY)
    frame.paste(sc, (0, 0))
    ending = t >= T_Q
    w = next(((k, tolist(dv)) for t0, t1, k, dv in WIDGETS if t0 <= t < t1), None)
    frame.paste(panel(bool(ex.get("night")), karaoke(t), w, None, ending), (0, SCENE_H))
    d = ImageDraw.Draw(frame)
    d.rectangle((0, SCENE_H - 3, W, SCENE_H + 3), fill=(10, 8, 18))
    tg = next(((x, c) for t0, t1, x, c in TAGS if t0 <= t < t1), None)
    if tg and not ex.get("insert"):
        draw_tag(d, *tg)
    if ending:
        draw_choice(d)
    a = np.asarray(frame)
    if t > TOTAL - 0.6:
        a = (a * max(0.0, (TOTAL - t) / 0.6)).astype(np.uint8)
    return a.tobytes()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        ts = [(s[0] + s[1]) / 2 for s in ep.shots] + [T_Q + 2]
        tiles = [Image.frombytes("RGB", (W, H), render(t)).resize((180, 320)) for t in ts]
        S = Image.new("RGB", (10 * 182, ((len(tiles) + 9) // 10) * 322), (40, 40, 40))
        for k, im in enumerate(tiles):
            S.paste(im, ((k % 10) * 182, (k // 10) * 322))
        S.save("/tmp/claude-0/-home-user-OfflineTranslator/1bcc3a57-a47c-5559-bc85-610f89fa5a3e/scratchpad/ep1sw_prev.png")
        print("TOTAL", round(TOTAL, 1), "сцен", len(ep.shots))
        return
    wav = OUT + ".wav"
    ep.build_audio(wav, swell_from=T_DIA - 20)
    nf = int(TOTAL * FPS)
    print(f"длительность {TOTAL:.1f} с, кадров {nf}", flush=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for buf in pool.imap(render, [f / FPS for f in range(nf)], chunksize=30):
            p.stdin.write(buf)
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("Готово:", OUT)


if __name__ == "__main__":
    main()
