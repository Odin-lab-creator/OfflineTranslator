#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», серия 1: фоны через PixelLab (pixflux, главная палитра канала) и выгрузка героя.

python3 gen_ep1.py bg [ИМЯ ...] [--seed N]   → src/bg_<имя>.png (160×192)
python3 gen_ep1.py hero CHARACTER_ID          → src/denis/<направление>.png (ждёт готовности, тянет ZIP)
"""
import argparse
import io
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PL = os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")
sys.path.insert(0, os.path.abspath(PL))
import api  # noqa: E402
from gen_bg import decode, palette_image  # noqa: E402

SRC = os.path.join(HERE, "src")
STYLE = ("16-bit pixel art, side view screenshot of a dark post-apocalyptic side-scrolling survival game, "
         "muted gloomy palette: dark olive green, muted grey, dirty brown, charcoal black, rust red, faded orange, "
         "no people, no characters, empty scene, flat floor along the bottom of the image, ")

SCENES = {
    "room": "small old soviet apartment living room interior, grey daylight, window on the right with thick metal bars "
            "welded outside the glass, old sofa on the left, small table with pill blisters and a phone, overturned chair, "
            "broken mug on the floor, plaid blanket on the floor, round wall clock, worn wallpaper, parquet floor",
    "window": "view from a third floor apartment window through thick vertical metal bars, empty city street below, "
              "abandoned cars with open doors standing in the middle of the road, a baby stroller lying on its side, "
              "plastic bag on the asphalt, grey overcast sky, nine-storey soviet apartment blocks across the street",
    "corridor": "dim apartment building corridor landing, three apartment doors wide open, an abandoned suitcase, "
                "a plush toy bunny and scattered clothes on the tiled floor, peeling green painted walls, "
                "electric meter box, dim daylight from a small window",
    "stairs": "soviet apartment building stairwell, concrete stairs going down to the left, metal railing with wooden "
              "handrail, green painted walls with chipped paint, a big hand-drawn arrow pointing down painted on the wall, "
              "small dirty window, dim light",
    "entrance": "ground floor entrance vestibule of a soviet apartment building, heavy metal entrance door on the right "
                "with an intercom panel, row of metal mailboxes on the left wall with a paper list pinned above, "
                "tiled floor, thin line of daylight under the door, dim",
    "entrance_wide": "wide shot of a small ground floor entrance hall of a soviet apartment building seen from far away, "
                     "low ceiling, the heavy metal entrance door is small on the right side of the back wall, "
                     "intercom panel next to the door, row of small metal mailboxes on the left wall with a paper list, "
                     "lots of empty tiled floor in the foreground, thin line of daylight under the door, dim",
}


def gen_bg(name, seed):
    body = {"description": STYLE + SCENES[name], "image_size": {"width": 160, "height": 192}, "view": "side",
            "detail": "highly detailed", "shading": "detailed shading", "outline": "selective outline",
            "text_guidance_scale": 8, "color_image": api.b64png(palette_image()), "seed": seed}
    img = decode(api.post("/create-image-pixflux", body))
    os.makedirs(SRC, exist_ok=True)
    p = os.path.join(SRC, f"bg_{name}.png")
    img.save(p)
    return p


def pull_hero(cid, out="denis"):
    t0 = time.time()
    while True:
        try:
            raw = api.get(f"/characters/{cid}/zip", raw=True, timeout=180)
            if raw[:2] == b"PK":
                break
        except RuntimeError as e:
            if time.time() - t0 > 900:
                raise
            print("ждём:", str(e)[:120], flush=True)
        time.sleep(15)
    d = os.path.join(SRC, out)
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            if n.lower().endswith(".png"):
                target = os.path.join(d, n.replace("/", "__"))
                with open(target, "wb") as f:
                    f.write(z.read(n))
                print(target)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["bg", "hero"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--seed", type=int, default=41)
    a = ap.parse_args()
    if a.what == "bg":
        for n in a.args or list(SCENES):
            try:
                print(gen_bg(n, a.seed), flush=True)
            except Exception as e:  # noqa: BLE001
                print(n, "ОШИБКА", e, flush=True)
    else:
        pull_hero(a.args[0], *(a.args[1:2]))
