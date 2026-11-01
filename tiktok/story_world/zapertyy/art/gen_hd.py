#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ», HD-версия графики: кадр 216×384 арт-пикселя (пиксель 5×5 на экране).

python3 gen_hd.py [ИМЯ ...] [--seed N]  →  src_hd/<имя>.png
Фоны 320×384 (камера ездит), крупные планы 216×336. Без принудительной палитры — плавнее светотень.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import api  # noqa: E402
from gen_bg import decode  # noqa: E402

OUT = os.path.join(HERE, "src_hd")
STYLE = ("detailed 16-bit pixel art, side view screenshot of a dark post-apocalyptic side-scrolling adventure game, "
         "fine pixels, soft lighting, muted gloomy palette: dark olive green, muted grey, dirty brown, charcoal black, "
         "rust red, faded orange, no people, no characters, empty scene, flat floor along the bottom of the image, ")
CLOSE = ("detailed 16-bit pixel art, dark post-apocalyptic adventure game cutscene, fine pixels, soft lighting, "
         "muted gloomy palette, no text, ")

SCENES = {
    "bg_room": "small old soviet apartment living room, grey daylight, big window on the right side with thick dark metal "
               "bars welded outside the glass, clearly visible bars, old green sofa on the left, small table with pill "
               "blisters and a phone, overturned chair, broken mug on the floor, plaid blanket on the floor, round wall "
               "clock, worn wallpaper, parquet floor with a red rug",
    "bg_window": "view from a third floor apartment window through thick vertical metal bars, empty city street below, "
                 "abandoned cars with open doors standing in the middle of the road, a baby stroller lying on its side, "
                 "plastic bag on the asphalt, grey overcast sky, nine-storey soviet apartment blocks across the street",
    "bg_corridor": "dim apartment building corridor landing, three apartment doors wide open, an abandoned suitcase, "
                   "a plush toy bunny and scattered clothes on the tiled floor, peeling green painted walls, "
                   "electric meter box, dim daylight from a small window",
    "bg_stairs": "soviet apartment building stairwell, concrete stairs going down, metal railing with wooden handrail, "
                 "green painted walls with chipped paint, small dirty window, dim light, a doorway on the right",
    "bg_entrance": "wide shot of a ground floor entrance hall of a soviet apartment building, the heavy metal entrance door "
                   "in the center of the back wall, intercom panel next to the door, row of metal mailboxes on the left "
                   "wall with a paper list pinned above, empty tiled floor in the foreground, thin line of daylight under "
                   "the door, dim",
    "cu_watch": "extreme close-up of a pale-skinned man's wrist in a grey hoodie sleeve with an old mechanical wristwatch, cracked glass, "
                "hands stopped at 3:40, dim grey light, dust",
    "cu_pills": "extreme close-up of a wooden table top with empty pill blister packs, an old glass thermometer, "
                "a dead black smartphone, crumbs, grey daylight",
    "cu_tap": "extreme close-up of an old kitchen faucet over a metal sink, a single water drop falling from the tap, "
              "dim grey light, rust stains",
    "cu_weld": "extreme close-up of thick vertical rusty iron bars outside a window, the bars are freshly welded to a metal "
               "frame, bright shiny fresh weld seams where the bars meet the frame, a man's hand in a grey sleeve gripping "
               "one bar, grey daylight behind",
    "cu_crack": "extreme close-up of a narrow gap between a heavy metal door and its frame near the hinges, bright daylight "
                "through the gap, through the gap you see a thick rusty iron bar welded across the outside of the door, glowing fresh weld seam, dark metal door, dramatic light",
}


def gen(name, seed):
    if name.startswith("cu_"):
        desc, size = CLOSE + SCENES[name], (216, 336)
    else:
        desc, size = STYLE + SCENES[name], (320, 384)
    body = {"description": desc, "image_size": {"width": size[0], "height": size[1]},
            "detail": "highly detailed", "shading": "highly detailed shading", "outline": "selective outline",
            "text_guidance_scale": 8, "seed": seed}
    if not name.startswith("cu_"):
        body["view"] = "side"
    for attempt in range(6):
        try:
            r = api.post("/create-image-pixflux-background", body)
            j = api.wait_job(r["background_job_id"], every=5, limit=900)
            if j["status"] != "completed":
                raise RuntimeError(str(j.get("last_response"))[:200])
            img = decode(j["last_response"])
            break
        except (RuntimeError, KeyError) as e:
            print(name, "повтор:", str(e)[:120], flush=True)
            time.sleep(8)
    else:
        raise RuntimeError(name)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{name}.png")
    img.save(p)
    return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(SCENES))
    ap.add_argument("--seed", type=int, default=61)
    a = ap.parse_args()
    for n in a.names:
        print(gen(n, a.seed), flush=True)
