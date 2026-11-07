"""Обложки «Тихое место»: картинка из Flow + пиксельная строка «ТИХОЕ МЕСТО» сверху и плашка «СЮЖЕТ ЗА МИНУТУ».
python3 cover.py → covers/cover_boy.png, covers/cover_regan.png, covers/compare.png
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ya_legenda"))
import build, cover2  # noqa: E402

W, H = 1080, 1920


def fit(path):
    im = Image.open(path).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def make(name):
    im = cover2.shade(fit(os.path.join(HERE, "covers", "src", f"{name}.jpg")), top=0.35, bottom=0.5)
    t = build.pixel_sprite("«ТИХОЕ МЕСТО»", 64, build.WHITE)
    cover2.put(im, t, (W - t.width) / 2, 270)
    cover2.badge(im, 1480)
    im.convert("RGB").save(os.path.join(HERE, "covers", f"cover_{name}.png"))
    return im


if __name__ == "__main__":
    ims = [make(n) for n in ("boy", "regan")]
    cmp = Image.new("RGB", (4 * 270 + 50, 540), (20, 20, 20))
    for i, im in enumerate(ims):
        cmp.paste(im.convert("RGB").resize((270, 480)), (10 + i * 560, 30))
        cmp.paste(im.crop((0, 240, W, 1680)).convert("RGB").resize((270, 360)), (290 + i * 560, 90))
    cmp.save(os.path.join(HERE, "covers", "compare.png"))
    print("готово")
