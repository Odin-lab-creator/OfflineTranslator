"""Обложка TikTok 1080×1920: всё важное в центральной зоне 3:4 (y 240–1680), её видно в сетке профиля.
python3 cover.py → covers/cover_A.png (сцена 29), covers/cover_B.png (сцена 01), covers/compare.png
"""
import os
import numpy as np
from PIL import Image, ImageDraw
import build

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920


def put(img, spr, cx, cy):
    x, y = int(cx - spr.width / 2) // 2 * 2, int(cy - spr.height / 2) // 2 * 2
    img.alpha_composite(spr, (x, y))


def cover(scene, out):
    im = build.scene_image(scene).convert("RGBA")              # 9:16 с запасом ×1.1
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    shade = 1 - 0.55 * np.clip((0.42 - yy) / 0.25, 0, 1) - 0.6 * np.clip((yy - 0.66) / 0.2, 0, 1)
    a[..., :3] *= shade                                        # темнее сверху и снизу под надписи
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    cell = 80
    title = build.pixel_sprite("Я —", cell, build.WHITE)
    gap = cell // 2 * 2
    red = build.pixel_sprite("ЛЕГЕНДА", cell, build.RED)
    tw = title.width + gap + red.width
    x0 = (W - tw) // 2 // 2 * 2
    im.alpha_composite(title, (x0, 330)); im.alpha_composite(red, (x0 + title.width + gap, 330))
    d = ImageDraw.Draw(im)
    d.rectangle([x0, 330 + red.height + 22, x0 + tw, 330 + red.height + 31], fill=(255, 255, 255, 255))
    put(im, build.pixel_sprite("СЮЖЕТ", 112, build.PURPLE), W / 2, 1420)
    put(im, build.pixel_sprite("ЗА МИНУТУ", 64, build.WHITE), W / 2, 1545)
    im.convert("RGB").save(out)
    return im


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "covers"), exist_ok=True)
    a = cover(29, os.path.join(HERE, "covers", "cover_A.png"))
    b = cover(1, os.path.join(HERE, "covers", "cover_B.png"))
    cmp = Image.new("RGB", (W + 40, 1440 + 20), (20, 20, 20))
    for i, im in enumerate((a, b)):                           # как в сетке профиля: центр 3:4
        cmp.paste(im.crop((0, 240, W, 1680)).convert("RGB").resize((W // 2, 720)), (10 + i * (W // 2 + 20), 10))
    cmp.crop((0, 0, W + 40, 740)).save(os.path.join(HERE, "covers", "compare.png"))
    print("готово")
