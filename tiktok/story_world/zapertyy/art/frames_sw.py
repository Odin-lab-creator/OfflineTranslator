#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ» в стиле канала story world (как ролик про Мирона): тестовые кадры 1080×1920.

python3 frames_sw.py  →  sw/test/sw_01…06.png и sw/test/sheet.png

Сверху сцена (яркий пиксель-арт, вид сбоку, 1080×1140), снизу панель: крупная надпись с выделенными словами
и «бумажный» элемент — шкала дней, записка от руки, список. Метка в углу (ДЕНЬ 1, ПОПЫТКА №1), схемы.
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SW = os.path.join(HERE, "sw")
DEN = os.path.join(HERE, "sto", "denis")
FONTS = os.path.join(HERE, "..", "fonts")
OUT = os.path.join(SW, "test")
W, H, SCENE_H = 1080, 1920, 1140

F_CAP = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_SANS = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
F_HAND = os.path.join(FONTS, "Caveat-Medium.ttf")

DAY_PANEL, NIGHT_PANEL = (44, 50, 33), (16, 14, 30)
WHITE, GREY, YELLOW, RED = (246, 244, 238), (135, 133, 145), (247, 190, 44), (232, 62, 62)
BLUE, GREEN = (70, 146, 236), (60, 200, 120)
PAPER, PAPER_LINE, INK, NUM = (247, 241, 231), (216, 210, 200), (38, 34, 30), (150, 146, 140)


def font(path, size):
    return ImageFont.truetype(path, size)


# ------------------------------------------------------------------ сцена
def scene_img(name):
    a = np.asarray(Image.open(os.path.join(SW, name)).convert("RGB"))
    m = a.mean((1, 2))
    rows = np.nonzero(m >= 16)[0]                              # срезаем чёрные полосы pixflux
    return Image.fromarray(a[rows.min():rows.max() + 1])


def sprite(path, flip=False):
    im = Image.open(path).convert("RGBA")
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def compose_scene(bg, cam_x, sprites, tint=None):
    """bg — картинка сцены, cam_x — левый край окна камеры (в арт-пикселях), sprites — [(картинка, x центра, y ступней)].
    Масштаб — по высоте сцены (1140 px), ближайший сосед: пиксели остаются квадратиками."""
    s = SCENE_H / bg.height
    cw = int(round(W / s))
    art = bg.copy().convert("RGBA")
    for im, x, feet in sprites:
        a = np.asarray(im)[..., 3] > 127
        ys, xs = np.nonzero(a)
        art.alpha_composite(im, (int(x - (xs.min() + xs.max()) / 2), int(feet - ys.max())))
    crop = art.crop((cam_x, 0, cam_x + cw, bg.height)).convert("RGB")
    out = crop.resize((W, SCENE_H), Image.NEAREST)
    if tint is not None:
        a = np.asarray(out).astype(np.float32) * tint[0] + np.array(tint[1])
        out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return out


# ------------------------------------------------------------------ панель
def caption(d, segs, y=1196, size=74, maxw=980):
    """segs — [(текст, цвет)]: строка из цветных кусков, перенос по словам, по центру."""
    f = font(F_CAP, size)
    words = []
    for text, col in segs:
        for w_ in text.split(" "):
            if w_:
                words.append((w_, col))
    lines, cur = [], []
    for w_ in words:
        test = " ".join(x for x, _ in cur + [w_])
        if cur and d.textlength(test, font=f) > maxw:
            lines.append(cur)
            cur = [w_]
        else:
            cur.append(w_)
    lines.append(cur)
    for k, ln in enumerate(lines):
        total = d.textlength(" ".join(x for x, _ in ln), font=f)
        x = (W - total) / 2
        for i, (w_, col) in enumerate(ln):
            d.text((x, y + k * 86), w_, font=f, fill=col)
            x += d.textlength(w_ + " ", font=f)


def timeline(d, day, marks=(1, 4, 7, 10)):
    x0, x1, yl, ylab = 122, 962, 1609, 1530
    pos = lambda v: x0 + (x1 - x0) * (v - 1) / 9
    d.line((x0, yl, x1, yl), fill=(70, 66, 84), width=5)
    d.line((x0, yl, pos(day), yl), fill=RED, width=5)
    fl, fb = font(F_MONO, 30), font(F_MONO, 34)
    for v in marks:
        if v == day:
            continue
        c = RED if v < day else (70, 66, 84)
        d.rectangle((pos(v) - 9, yl - 9, pos(v) + 9, yl + 9), fill=c)
        lab = str(v)
        d.text((pos(v) - d.textlength(lab, font=fl) / 2, ylab), lab, font=fl, fill=GREY)
    lab = f"ДЕНЬ {day}"
    tw = d.textlength(lab, font=fb)
    lx = min(max(pos(day) - tw / 2, x0 - 40), x1 + 40 - tw)
    d.text((lx, ylab - 2), lab, font=fb, fill=WHITE)
    d.rectangle((pos(day) - 15, yl - 15, pos(day) + 15, yl + 15), fill=RED)


def paper(d, box):
    d.rectangle(box, fill=PAPER, outline=(210, 209, 194), width=3)


def note(d, text, y=1452):
    paper(d, (112, y, 968, y + 112))
    d.text((150, y + 22), text, font=font(F_HAND, 58), fill=INK)


def checklist(d, items, current, y=1452, strike=()):
    paper(d, (112, y, 968, y + 330))
    fn, fh = font(F_SANS, 36), font(F_HAND, 56)
    for k in range(4):
        ry = y + 14 + k * 78
        n = str(k + 1)
        d.text((152, ry + 14), n, font=fn, fill=RED if k == current else NUM)
        if k < len(items) and items[k]:
            d.text((214, ry + 2), items[k], font=fh, fill=INK)
            if k in strike:
                w = d.textlength(items[k], font=fh)
                d.line((210, ry + 42, 220 + w, ry + 36), fill=RED, width=6)
        if k < 3:
            d.line((140, ry + 74, 940, ry + 74), fill=PAPER_LINE, width=3)


def tag(d, text, xy=(49, 49), border=BLUE, size=34):
    f = font(F_MONO, size)
    tw = d.textlength(text, font=f)
    x, y = xy
    d.rectangle((x, y, x + tw + 44, y + size + 40), fill=(14, 15, 24), outline=border, width=5)
    d.text((x + 22, y + 16), text, font=f, fill=WHITE)


def choice(d, left, right):
    f = font(F_CAP, 44)
    for k, (text, col) in enumerate(((left, GREEN), (right, RED))):
        x0 = 80 + k * 480
        d.rectangle((x0, 110, x0 + 440, 260), fill=(14, 15, 24), outline=col, width=6)
        tw = d.textlength(text, font=f)
        d.text((x0 + 220 - tw / 2, 160), text, font=f, fill=WHITE)


def diagram(d):
    """Схема на тёмном фоне: что я знаю → вывод."""
    fm = font(F_MONO, 34)

    def box(cx, cy, text, col):
        tw = d.textlength(text, font=fm)
        d.rectangle((cx - tw / 2 - 24, cy - 34, cx + tw / 2 + 24, cy + 34), fill=(14, 15, 24), outline=col, width=5)
        d.text((cx - tw / 2, cy - 22), text, font=fm, fill=WHITE)

    rows = [("ОКНА", "РЕШЁТКИ"), ("ДВЕРЬ", "ЗАВАРЕНА"), ("ГОРОД", "ПУСТ")]
    for k, (a, b) in enumerate(rows):
        y = 210 + k * 190
        d.line((300, y, 760, y), fill=BLUE, width=5)
        d.line((760, y, 760, 860), fill=RED, width=5)
        box(300, y, a, BLUE)
        box(760, y, b, BLUE)
    d.line((540, 860, 980, 860), fill=RED, width=5)
    d.line((100, 860, 540, 860), fill=RED, width=5)
    box(540, 860, "КТО-ТО ПОСТАРАЛСЯ", RED)


# ------------------------------------------------------------------ кадры
def frame(scene, panel, draw_panel, scene_tags=None):
    img = Image.new("RGB", (W, H), panel)
    if scene is not None:
        img.paste(scene, (0, 0))
        dd = ImageDraw.Draw(img)
        dd.rectangle((0, SCENE_H, W, SCENE_H + 6), fill=(12, 10, 20))
    d = ImageDraw.Draw(img)
    draw_panel(d)
    if scene_tags:
        scene_tags(d)
    return img


def build():
    room, corr, hall = scene_img("bg_room.png"), scene_img("v1/bg_corridor.png"), scene_img("bg_hall.png")
    lying = sprite(os.path.join(HERE, "sto", "obj_lying.png"))
    back = sprite(os.path.join(DEN, "Idle__rotations__north.png"))
    shout = sprite(os.path.join(DEN, "Idle__animations__shout__east__frame_006.png"))
    kick = sprite(os.path.join(DEN, "Idle__animations__kick-c5cfb681__north__frame_010.png"))
    sit = sprite(os.path.join(DEN, "Idle__animations__sit__south__frame_012.png"))
    frames = []

    sc = compose_scene(room, 0, [(lying, 104, 199)])
    frames.append(frame(sc, DAY_PANEL, lambda d: (
        caption(d, [("ПЕРВОЕ, ЧТО Я УСЛЫШАЛ\u00a0—", WHITE), ("ТИШИНУ.", YELLOW)]), timeline(d, 1)),
        lambda d: tag(d, "ДЕНЬ 1")))

    sc = compose_scene(room, 96, [(back, 190, 199)])
    frames.append(frame(sc, DAY_PANEL, lambda d: (
        caption(d, [("ЗДЕСЬ НИКОГДА НЕ БЫЛО", WHITE), ("РЕШЁТОК.", RED)]),
        note(d, "Решётки снаружи. Швы свежие.")),
        lambda d: tag(d, "3 ЭТАЖ")))

    sc = compose_scene(corr, 112, [(shout, 176, 176)])
    frames.append(frame(sc, DAY_PANEL, lambda d: (
        caption(d, [("ЭЙ! ЕСТЬ КТО", WHITE), ("ЖИВОЙ?", YELLOW)]),
        checklist(d, ["Света нет", "Воды нет", "Соседей нет", ""], 2)),
        lambda d: tag(d, "ЧТО Я ЗНАЮ", border=YELLOW)))

    sc = compose_scene(hall, 0, [(kick, 92, 178)])
    frames.append(frame(sc, DAY_PANEL, lambda d: (
        caption(d, [("ОНА ДАЖЕ", WHITE), ("НЕ ДРОГНУЛА.", GREY)]),
        checklist(d, ["Дверь подъезда", "", "", ""], 0, strike=(0,))),
        lambda d: tag(d, "ПОПЫТКА №1", border=RED)))

    frames.append(frame(None, NIGHT_PANEL, lambda d: (
        diagram(d), caption(d, [("ЧТОБЫ ОТСЮДА НИКТО", WHITE), ("НЕ ВЫШЕЛ.", RED)]), timeline(d, 1))))

    sc = compose_scene(hall, 0, [(sit, 92, 178)], tint=(0.42, (6, 8, 26)))
    frames.append(frame(sc, NIGHT_PANEL, lambda d: (
        caption(d, [("А ЧТО БЫ ВЫ СДЕЛАЛИ", WHITE), ("ПЕРВЫМ?", YELLOW)]), timeline(d, 1)),
        lambda d: choice(d, "ИСКАТЬ ВОДУ", "ЛОМАТЬ ДВЕРЬ")))
    return frames


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    frames = build()
    for k, im in enumerate(frames, 1):
        im.save(os.path.join(OUT, f"sw_{k:02d}.png"))
    sheet = Image.new("RGB", (len(frames) * 364, 640), (30, 30, 34))
    for k, im in enumerate(frames):
        sheet.paste(im.resize((360, 640), Image.LANCZOS), (k * 364, 0))
    sheet.save(os.path.join(OUT, "sheet.png"))
    print("готово:", OUT)
