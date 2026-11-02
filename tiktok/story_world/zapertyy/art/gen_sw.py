#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ» в стиле канала story world (как ролик про Мирона): яркий чистый пиксель-арт, вид сбоку.

python3 gen_sw.py [ИМЯ ...] [--seed N]  →  sw/bg_<имя>.png
Фоны — pixflux (1 генерация): вид строго сбоку, без перспективы, полоса пола внизу, без людей и текста.
Герой — уже готовый Денис 88px (sto/denis, v3) с анимациями.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import api  # noqa: E402
from gen_bg import decode  # noqa: E402

OUT = os.path.join(HERE, "sw")
STYLE = ("2D side-scroller game background, flat side elevation with no perspective, clean bright colorful pixel art, "
         "crisp readable shapes, cartoon game style, ")
TAIL = ", no people, no characters, no text, no letters"

BGS = {  # имя: (ширина, высота, сцена)
    "room": (360, 224, "interior of a small old apartment living room abandoned in a hurry, wallpaper with a pattern, "
                       "a sofa on the left, an overturned chair, a broken mug and a blanket on the wooden floor, a small "
                       "table with pill packs and a phone, a round wall clock, on the right a window with thick black "
                       "vertical prison-like iron bars welded outside the glass, clearly visible bars, soft grey daylight, wooden floor strip along the very bottom"),
    "corridor": (360, 224, "apartment building stair landing corridor, three apartment doors standing wide open, an "
                           "abandoned suitcase and a plush toy bunny on the tiled floor, two-tone painted walls green "
                           "below and cream above, an electric meter box, tiled floor strip along the very bottom"),
    "hall": (180, 192, "ground floor entrance hall of an old apartment building, a heavy closed dark metal entrance door "
                       "in the middle, an intercom panel next to it, a row of metal mailboxes on the left wall, a thin "
                       "line of daylight under the door, tiled floor strip along the very bottom"),
    "street": (360, 192, "empty city street seen through nothing, abandoned cars with open doors on the road, a baby "
                         "stroller lying on its side, nine-storey apartment blocks behind, overcast sky, asphalt strip "
                         "along the very bottom"),
}


def gen(name, seed):
    w, h, scene = BGS[name]
    body = {"description": STYLE + scene + TAIL, "image_size": {"width": w, "height": h}, "view": "side",
            "shading": "basic shading", "detail": "highly detailed", "outline": "selective outline",
            "text_guidance_scale": 8, "no_background": False, "seed": seed}
    for a in range(6):
        try:
            r = api.post("/create-image-pixflux-background", body)
            j = api.wait_job(r["background_job_id"], every=5, limit=900)
            img = decode(j["last_response"]).convert("RGB")
            os.makedirs(OUT, exist_ok=True)
            p = os.path.join(OUT, f"bg_{name}.png")
            img.save(p)
            return p, j.get("usage")
        except (RuntimeError, KeyError) as e:
            print(name, "повтор:", str(e)[:100], flush=True)
            time.sleep(6)
    raise RuntimeError(name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(BGS))
    ap.add_argument("--seed", type=int, default=12)
    a = ap.parse_args()
    for n in a.names:
        print(*gen(n, a.seed), flush=True)
