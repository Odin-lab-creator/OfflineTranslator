#!/usr/bin/env python3
"""Генерация фонов 160×192 через PixelLab API для серии 1 (сокращённый набор из 5 сцен).

python3 pixellab/gen_bg.py ИМЯ [--model pixflux|pixen] [--seed N] [--suffix _try2]
→ pixellab/source/bg_<имя><suffix>.png (исходник), затем приёмка ingest.py.

pixflux — с принудительной палитрой (главная палитра персонажей), ширина 160 (кратно 4);
pixen   — новая модель без палитры (цвета подгоняются при приёмке).
"""
import argparse
import base64
import io
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import api  # noqa: E402
import master_palette as mp  # noqa: E402

STYLE = ("16-bit pixel art, side view screenshot of a dark post-apocalyptic side-scrolling survival game, "
         "muted gloomy palette: dark olive green, muted grey, dirty brown, charcoal black, rust red, faded orange, "
         "no people, no characters, empty scene, flat floor along the bottom of the image, ")

SCENES = {
    "corridor": "underground bunker corridor, mossy green stone brick wall, heavy metal door with a small barred window "
                "in the middle, thin warm light strip under the door, caged wall lamp with warm glow, rusty pipes and "
                "hanging cables under the ceiling, cobwebs, metal grate floor",
    "storeroom": "underground bunker storeroom, damp green stone brick wall, metal shelves with canned food and jars, "
                 "wooden table with two water jugs, canned food, a first aid kit, batteries and a flashlight, "
                 "caged wall lamp with warm glow, pipes under the ceiling",
    "radio": "basement room at night, dark stone wall, boarded-up window with pale moonlight through the gaps, "
             "old radio with a glowing orange dial on a wooden crate, candle stub, sleeping bag on the floor",
    "window": "dark apartment room at night, window on the right with an empty night street outside, a single street "
              "lamp and an abandoned car, dark open doorway on the left, peeling wallpaper, wooden floor",
    "night_street": "night city street, collapsed highway overpass with a broken concrete span, burning wrecked car "
                    "in the middle of the road, embers and smoke, dark ruined skyscrapers, full moon, cracked asphalt",
}


def palette_image():
    cols = mp.colors()
    return Image.fromarray(cols[None].astype(np.uint8), "RGB")


def decode(resp):
    img = resp.get("image") or (resp.get("images") or [None])[0]
    if isinstance(img, dict) and "base64" in img:
        return Image.open(io.BytesIO(base64.b64decode(img["base64"]))).convert("RGBA")
    raise RuntimeError(f"нет картинки в ответе: {str(resp)[:300]}")


def generate(name, model="pixflux", seed=7, suffix=""):
    desc = STYLE + SCENES[name]
    if model == "pixflux":
        body = {"description": desc, "image_size": {"width": 160, "height": 192}, "view": "side",
                "detail": "highly detailed", "shading": "detailed shading", "outline": "selective outline",
                "text_guidance_scale": 8, "color_image": api.b64png(palette_image()), "seed": seed}
        r = api.post("/create-image-pixflux", body)
        img = decode(r)
    else:
        body = {"description": desc, "image_size": {"width": 160, "height": 192}, "view": "side",
                "detail": "highly detailed", "outline": "selective outline", "seed": seed}
        r = api.post("/create-image-pixen", body)
        img = decode(r)
    out = os.path.join(HERE, "source", f"bg_{name}{suffix}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    return out, r.get("usage"), img.size


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=list(SCENES))
    ap.add_argument("--model", default="pixflux", choices=["pixflux", "pixen"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    path, usage, size = generate(a.name, a.model, a.seed, a.suffix)
    print(path, size, "usage:", usage)
