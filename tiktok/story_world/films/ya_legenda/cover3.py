"""Обложки v3: плашка «СЮЖЕТ ЗА МИНУТУ» как в v2, три варианта названия фильма на кадре D (вожак).
python3 cover3.py → covers/cover_D1.png, D2, D3, covers/compare3.png
"""
import os
from PIL import Image, ImageDraw, ImageFont
import build, cover2

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
OSW = os.path.join(HERE, "fonts", "Oswald.ttf")


def oswald(size):
    f = ImageFont.truetype(OSW, size)
    f.set_variation_by_name(b"Bold")
    return f


def logo(im):
    """1: как логотип фильма в референсе — узкий шрифт, «Я —» белым, «ЛЕГЕНДА» красным, черта."""
    d = ImageDraw.Draw(im)
    f = oswald(140)
    a, b = "Я — ", "ЛЕГЕНДА"
    w = f.getlength(a + b)
    x = (W - w) / 2
    d.text((x, 290), a, font=f, fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
    d.text((x + f.getlength(a), 290), b, font=f, fill=build.RED, stroke_width=6, stroke_fill=(0, 0, 0))
    d.rectangle([x, 505, x + w, 513], fill=(255, 255, 255))


def white_pixel(im):
    """2: одной строкой мелким белым пиксельным шрифтом над плашкой — название как подпись."""
    t = build.pixel_sprite("«Я — ЛЕГЕНДА»", 56, build.WHITE)
    cover2.put(im, t, (W - t.width) / 2, 1370)


def plate(im):
    """3: название на чёрной плашке в тон фиолетовой."""
    t = build.pixel_sprite("Я — ЛЕГЕНДА", 64, build.WHITE)
    pad_x, pad_y = 36, 26
    bw, bh = t.width + 2 * pad_x, t.height + 2 * pad_y
    x0, y = (W - bw) // 2 // 2 * 2, 330
    d = ImageDraw.Draw(im)
    d.rectangle([x0 + 10, y + 10, x0 + bw + 10, y + bh + 10], fill=(0, 0, 0, 200))
    d.rectangle([x0 - 6, y - 6, x0 + bw + 6, y + bh + 6], fill=(255, 255, 255, 255))
    d.rectangle([x0, y, x0 + bw, y + bh], fill=(14, 12, 18, 255))
    cover2.put(im, t, x0 + pad_x, y + pad_y)


if __name__ == "__main__":
    ims = []
    for name, fn in (("D1", logo), ("D2", white_pixel), ("D3", plate)):
        im = cover2.shade(cover2.frame(13, 0.55, 0.40, 1.15))
        fn(im)
        cover2.badge(im, 1480)
        im.convert("RGB").save(os.path.join(HERE, "covers", f"cover_{name}.png"))
        ims.append(im)
    cmp = Image.new("RGB", (3 * 360 + 40, 480 + 20), (20, 20, 20))
    for i, im in enumerate(ims):
        cmp.paste(im.crop((0, 240, W, 1680)).convert("RGB").resize((360, 480)), (10 + i * 370, 10))
    cmp.save(os.path.join(HERE, "covers", "compare3.png"))
    print("готово")
