#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ»: тестовые кадры целиком через PixelLab Pro (generate-image-v2), 360×640 → 1080×1920 (×3).

python3 gen_test_pro.py [ИМЯ ...] [--seed N]  →  test_pro/<имя>.png и test_pro/<имя>_1080.png
Денис передаётся образцами (спрайты 128px: спереди, сбоку, со спины) — чтобы был узнаваем в каждом кадре.
"""
import argparse
import base64
import io
import os
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import api  # noqa: E402

OUT = os.path.join(HERE, "test_pro")
DEN = os.path.join(HERE, "src", "denis128")
W, H = 360, 640
STYLE = ("cinematic detailed pixel art, 16-bit adventure game cutscene, moody soft lighting, muted gloomy palette: "
         "dark olive green, grey, dirty brown, charcoal, rust red, faded orange, vertical 9:16 composition, "
         "post-apocalyptic, empty world, no text, ")
HERO = ("the main character Denis: 31 year old man, messy dark brown hair, short stubble, grey hoodie, ripped dark blue "
        "jeans, white sneakers, ")

SHOTS = {
    "01_wake": "Denis lying on his back on the wooden floor of a dim old soviet apartment living room, just waking up, "
               "one hand on his head, an overturned chair and a broken mug near him, pale grey daylight falls through a "
               "barred window and casts striped shadows of the bars across his body, dust in the air, camera low near the floor",
    "02_window": "Denis seen from behind, standing at a window and gripping thick welded metal bars with both hands, "
                 "outside the window an empty grey city street with abandoned cars with open doors and a toppled baby "
                 "stroller, nine-storey apartment blocks across the street, overcast sky, silhouette against the window light",
    "03_corridor": "Denis standing in a dim apartment building corridor, hands cupped around his mouth, shouting, three "
                   "neighbours' apartment doors wide open, an abandoned suitcase and a plush toy bunny on the tiled floor, "
                   "peeling green walls, dusty light from a small window, echo, loneliness",
    "04_kick": "Denis seen from behind, back to the camera, kicking hard with his foot at a heavy locked metal entrance door "
               "of an apartment building ground floor hall, dust flying, metal mailboxes on the left wall, intercom panel, "
               "thin line of daylight under the door, dim, dramatic",
    "05_end": "Denis sitting on the floor with his back against a heavy welded-shut metal entrance door, knees up, head "
              "down, arms on knees, exhausted, thin bright line of daylight under the door, dark ground floor hall, "
              "mailboxes on the wall, lonely and quiet",
    "06_stand": "Denis standing in the middle of a dim old soviet apartment living room, holding his head with one hand, "
                "looking around confused, an overturned chair and a broken mug on the floor, pale grey light and striped "
                "shadows from a barred window",
    "07_phone": "close-up of Denis's hand in a grey hoodie sleeve holding a black smartphone with a completely dead black "
                "screen, thumb pressing the power button, an old light switch on the wallpapered wall behind, dim room",
    "08_watch": "extreme close-up of Denis's left wrist in a grey hoodie sleeve with an old mechanical wristwatch, "
                "the hands stopped at twenty to four, scratched glass, dust, dim grey light",
    "09_pills": "close-up of an old wooden table with empty pill blister packs, an old glass thermometer and an empty glass, "
                "dust and crumbs, grey daylight from a window",
    "10_tap": "close-up of Denis's hand turning the handle of an old kitchen faucet over a metal sink, a single water drop "
              "falling from the tap, rust stains, dim kitchen",
    "11_weld": "close-up of Denis's hands gripping thick metal window bars, shiny fresh weld seams where the bars are welded "
               "to the window frame, grey light, empty street blurred outside the glass",
    "13_door": "Denis opening the front door of his apartment from inside, the door creaking open into a dim stairwell "
               "landing, seen from the apartment hallway behind him, coats on hooks, shoes on the floor",
    "14_stairs": "Denis walking down a dim concrete stairwell of a soviet apartment building, one hand on the handrail, "
                 "a big red painted arrow pointing down on the green wall, peeling paint, small dirty window, dusty light",
    "15_intercom": "close-up of Denis's finger pressing a button on a dead intercom panel next to a heavy metal entrance door, "
                   "the intercom display is dark, dim ground floor hall",
    "16_crack": "extreme close-up of the narrow gap between a heavy metal entrance door and its frame near the hinges, "
                "bright daylight through the gap, outside a thick rusty iron strip is welded across the door, rough fresh "
                "weld seam, dark metal, dust",
}


def b64(path):
    im = Image.open(path).convert("RGBA")
    return {"image": api.b64png(im), "size": {"width": im.width, "height": im.height},
            "usage_description": "the main character Denis: keep his face, hair, beard, grey hoodie, ripped jeans and sneakers"}


def run(names, seed):
    refs = [b64(os.path.join(DEN, f"Idle__rotations__{v}.png")) for v in ("south", "east", "north")]
    jobs = {}
    for n in names:
        body = {"description": STYLE + HERO + SHOTS[n], "image_size": {"width": W, "height": H},
                "no_background": False, "reference_images": refs, "seed": seed}
        for a in range(5):
            try:
                jobs[n] = api.post("/generate-image-v2", body)["background_job_id"]
                print(n, "запущен", flush=True)
                break
            except RuntimeError as e:
                print(n, "повтор:", str(e)[:100], flush=True)
                time.sleep(8)
    os.makedirs(OUT, exist_ok=True)
    for n, j in jobs.items():
        r = api.wait_job(j, every=8, limit=1800)
        lr = r.get("last_response") or {}
        ims = lr.get("images") or ([lr["image"]] if "image" in lr else [])
        if r["status"] != "completed" or not ims:
            print(n, "НЕ ВЫШЛО:", str(lr)[:300], flush=True)
            continue
        im = ims[0]
        raw = base64.b64decode(im["base64"] if isinstance(im, dict) else im)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.save(os.path.join(OUT, f"{n}.png"))
        img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(os.path.join(OUT, f"{n}_1080.png"))
        print(n, img.size, r.get("usage"), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(SHOTS))
    ap.add_argument("--seed", type=int, default=21)
    a = ap.parse_args()
    run(a.names, a.seed)
