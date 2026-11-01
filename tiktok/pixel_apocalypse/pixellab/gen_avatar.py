#!/usr/bin/env python3
"""Аватарки канала через PixelLab (pixflux, главная палитра канала): 72×72 арт-пикселя → 1080×1080 (×15).

python3 pixellab/gen_avatar.py [КОНЦЕПТ ...] [--seed N] [--model pixflux|pixen]
→ ../avatar/gen/<концепт>_s<seed>.png (исходник 72×72) и ../avatar/<концепт>_s<seed>.png (1080×1080)
"""
import argparse
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import api  # noqa: E402
from gen_bg import decode, palette_image  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "avatar")
SIZE = 72

STYLE = ("16-bit pixel art, dark post-apocalyptic survival game, bold readable shapes, strong silhouette, "
         "centered composition, muted gloomy palette: dark olive green, muted grey, dirty brown, charcoal black, "
         "rust red, faded orange, ")

CONCEPTS = {
    "gasmask": "close-up portrait of a survivor wearing an old gas mask and a dark hood, front view, head and shoulders, "
               "round mask lenses reflecting orange fire, rust red scarf, ruined city and orange glow behind",
    "sunset": "lone survivor with a big backpack seen from behind, small dark silhouette standing on rubble, "
              "huge red-orange setting sun, black silhouettes of ruined skyscrapers, smoke",
    "skull": "emblem of a skull wearing a gas mask, front view, glowing green eye lenses, cracked, "
             "dark background, game icon",
    "hood": "close-up portrait of a hooded survivor, front view, face half in shadow, dirt and scratches on the face, "
            "glowing orange eyes reflection from a fire, collapsed buildings behind, night",
    "hand": "rotten zombie hand reaching up out of rubble towards the viewer, full moon behind, dark night sky, "
            "game icon",
}


def generate(name, seed, model):
    desc = STYLE + CONCEPTS[name]
    body = {"description": desc, "image_size": {"width": SIZE, "height": SIZE},
            "detail": "highly detailed", "outline": "single color black outline", "seed": seed}
    if model == "pixflux":
        body.update({"shading": "detailed shading", "text_guidance_scale": 8,
                     "color_image": api.b64png(palette_image())})
    r = api.post(f"/create-image-{model}", body)
    img = decode(r).convert("RGB")
    tag = f"{name}_{model}_s{seed}"
    os.makedirs(os.path.join(OUT, "gen"), exist_ok=True)
    img.save(os.path.join(OUT, "gen", tag + ".png"))
    img.resize((SIZE * 15, SIZE * 15), Image.NEAREST).save(os.path.join(OUT, tag + ".png"))
    return tag, img.size, r.get("usage")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(CONCEPTS))
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--model", default="pixflux", choices=["pixflux", "pixen"])
    a = ap.parse_args()
    for n in a.names:
        try:
            print(*generate(n, a.seed, a.model), flush=True)
        except Exception as e:  # noqa: BLE001
            print(n, "ОШИБКА", e, flush=True)
