"""Обложки TikTok v2: крупный герой, огромное «ЛЕГЕНДА», плашка «СЮЖЕТ ЗА МИНУТУ».
python3 cover2.py → covers/cover_C.png, cover_D.png, cover_E.png, covers/compare2.png
"""
import os
import numpy as np
from PIL import Image, ImageDraw
import build

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920


def frame(scene, cx, cy, zoom):
    """Кадр сцены с приближением zoom вокруг точки (cx, cy) в долях картинки."""
    for ext in ("png", "jpg"):
        p = os.path.join(HERE, "frames", f"{scene:02d}.{ext}")
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
    cw = im.width / zoom
    ch = cw * 16 / 9
    if ch > im.height:
        ch = im.height; cw = ch * 9 / 16
    x = min(max(0, cx * im.width - cw / 2), im.width - cw)
    y = min(max(0, cy * im.height - ch / 2), im.height - ch)
    return im.crop((int(x), int(y), int(x + cw), int(y + ch))).resize((W, H), Image.LANCZOS)


def shade(im, top=0.6, bottom=0.7):
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(-1, 1, W)[None, :, None]
    k = 1 - top * np.clip((0.40 - yy) / 0.28, 0, 1) - bottom * np.clip((yy - 0.62) / 0.22, 0, 1)
    k = k * (1 - 0.35 * np.abs(xx) ** 2)                           # виньетка по краям
    return Image.fromarray((a * k).clip(0, 255).astype(np.uint8)).convert("RGBA")


def put(img, spr, x, y):
    img.alpha_composite(spr, (int(x) // 2 * 2, int(y) // 2 * 2))


def title(im):
    small = build.pixel_sprite("Я —", 64, build.WHITE)
    big = build.pixel_sprite("ЛЕГЕНДА", 128, build.RED)
    put(im, small, (W - small.width) / 2, 300)
    put(im, big, (W - big.width) / 2, 300 + small.height + 24)


def badge(im, y):
    t = build.pixel_sprite("СЮЖЕТ ЗА МИНУТУ", 48, build.WHITE)
    pad_x, pad_y = 36, 26
    bw, bh = t.width + 2 * pad_x, t.height + 2 * pad_y
    x0 = (W - bw) // 2 // 2 * 2
    d = ImageDraw.Draw(im)
    d.rectangle([x0 + 10, y + 10, x0 + bw + 10, y + bh + 10], fill=(0, 0, 0, 200))     # пиксельная тень
    d.rectangle([x0 - 6, y - 6, x0 + bw + 6, y + bh + 6], fill=(0, 0, 0, 255))         # чёрная рамка
    d.rectangle([x0, y, x0 + bw, y + bh], fill=(*build.PURPLE, 255))
    put(im, t, x0 + pad_x, y + pad_y)


def make(name, scene, cx, cy, zoom):
    im = shade(frame(scene, cx, cy, zoom))
    title(im)
    badge(im, 1480)
    im.convert("RGB").save(os.path.join(HERE, "covers", f"cover_{name}.png"))
    return im


if __name__ == "__main__":
    vs = [("C", 23, 0.30, 0.42, 1.55), ("D", 13, 0.55, 0.40, 1.15), ("E", 9, 0.45, 0.62, 1.35)]
    ims = [make(*v) for v in vs]
    cmp = Image.new("RGB", (3 * 360 + 40, 480 + 20), (20, 20, 20))
    for i, im in enumerate(ims):
        cmp.paste(im.crop((0, 240, W, 1680)).convert("RGB").resize((360, 480)), (10 + i * 370, 10))
    cmp.save(os.path.join(HERE, "covers", "compare2.png"))
    print("готово")
