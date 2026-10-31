"""Генерирует иконку приложения из рисунка в корне репозитория.

Запуск: python3 tools/make_icons.py <рисунок.png>
Создаёт слои адаптивной иконки (фон и передний план) и обычные иконки
для старых Android во всех плотностях в app/src/main/res/mipmap-*.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "app" / "src" / "main" / "res"
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
CROP = 0.075        # срезаем закруглённую рамку с чёрными углами
ART_SCALE = 254 / 432  # доля рисунка в слое 108dp: руна и плитки целиком входят даже в круглую маску


def load_art(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    c = int(min(w, h) * CROP)
    return im.crop((c, c, w - c, h - c))


def background(art: Image.Image, size: int) -> Image.Image:
    bg = art.resize((size, size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(size / 18))
    return ImageEnhance.Brightness(bg).enhance(0.55)


def feather_mask(size: int, edge: float = 0.07) -> Image.Image:
    """Мягко гасим края квадрата рисунка, чтобы он сливался с размытым фоном."""
    mask = Image.new("L", (size, size), 0)
    px = mask.load()
    fade = max(1, int(size * edge))
    for y in range(size):
        for x in range(size):
            d = min(x, y, size - 1 - x, size - 1 - y)
            px[x, y] = 255 if d >= fade else int(255 * d / fade)
    return mask


def foreground(art: Image.Image, size: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s = int(size * ART_SCALE)
    piece = art.resize((s, s), Image.LANCZOS).convert("RGBA")
    piece.putalpha(feather_mask(s))
    off = (size - s) // 2
    layer.alpha_composite(piece, (off, off))
    return layer


def legacy(art: Image.Image, size: int, round_icon: bool) -> Image.Image:
    """Иконка для Android 6–7: рисунок без рамки в своей маске."""
    big = size * 4
    icon = art.resize((big, big), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(mask)
    if round_icon:
        draw.ellipse((0, 0, big - 1, big - 1), fill=255)
    else:
        draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.22), fill=255)
    icon.putalpha(mask)
    return icon.resize((size, size), Image.LANCZOS)


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else next(ROOT.glob("*.png"))
    art = load_art(source)
    for name, scale in DENSITIES.items():
        out = RES / f"mipmap-{name}"
        out.mkdir(parents=True, exist_ok=True)
        layer = int(108 * scale)
        background(art, layer).save(out / "ic_launcher_background.png")
        foreground(art, layer).save(out / "ic_launcher_foreground.png")
        legacy(art, int(48 * scale), False).save(out / "ic_launcher.png")
        legacy(art, int(48 * scale), True).save(out / "ic_launcher_round.png")
        print(name, layer)


if __name__ == "__main__":
    main()
