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
    "04_kick_wide": "wide shot of a ground floor entrance hall of an old apartment building, Denis small in the frame, "
                    "seen from behind, back to the camera, standing in front of a heavy locked metal entrance door, about "
                    "to kick it, lots of empty tiled floor around him, metal mailboxes on the left wall, intercom panel, "
                    "thin line of daylight under the door, dim, dramatic",
    # ---- серия 2 «Вода» (главный объект — в середине кадра по высоте: видно полосу 216×240)
    "e2_lips": "extreme close-up of Denis's face from the side, cracked dry lips, his throat moving as he swallows, "
               "stubble, exhausted, dim grey light, the face in the middle of the frame",
    "e2_kitchen": "Denis in a dim old soviet kitchen greedily drinking from the spout of an old kettle, the door of a dark "
                  "warm fridge open beside him, dirty dishes, grey daylight, Denis in the middle of the frame",
    "e2_toilet": "Denis in a small old tiled bathroom lifting the porcelain lid of a toilet cistern, clear water inside, "
                 "a mug in his other hand, dim light, Denis in the middle of the frame",
    "e2_doors": "Denis standing in a dim apartment building corridor holding a bucket and a cooking pot, looking at the "
                "neighbours' apartment doors standing wide open, peeling green walls, Denis in the middle of the frame",
    "e2_neighbor": "Denis carrying a bucket stepping quietly into a stranger's dark apartment hallway, pairs of slippers "
                   "on the doormat, family photos on the wall, coats on hooks, Denis in the middle of the frame",
    "e2_radiator": "close-up of Denis's hand in a grey hoodie sleeve opening a valve on an old cast iron radiator, rusty "
                   "orange water pouring into a metal bucket below, dim light, in the middle of the frame",
    "e2_boiler": "Denis kneeling under a white electric water boiler on a bathroom wall, opening the drain tap, a steady "
                 "stream of clear water pouring into a big cooking pot, dim light, Denis in the middle of the frame",
    "e2_cupboard": "Denis opening a kitchen cupboard in a stranger's dark kitchen, shelves with cans of stewed meat, a bag "
                   "of buckwheat, a bag of rusks and a jar of honey, Denis in the middle of the frame",
    "e2_supplies": "Denis sitting at his kitchen table counting on his fingers, in front of him a row of plastic bottles "
                   "and cooking pots full of water and several cans of food, grey daylight from a barred window, "
                   "Denis in the middle of the frame",
    "e2_mailbox": "Denis standing at a wall of old metal mailboxes in a dim ground floor hall, reading a paper list pinned "
                  "on the wall, his finger on the paper, the heavy welded entrance door nearby, Denis in the middle of "
                  "the frame",
    # ---- серия 2, крупнее и детальнее: кадр 270×300 целиком виден в видео
    "e2b_bed": "medium close-up of Denis sitting on the edge of an unmade bed in the morning, elbows on his knees, head "
               "low, tired, grey daylight through a barred window draws striped shadows across him, dust in the air",
    "e2b_kitchen": "medium close-up of Denis greedily drinking water from the spout of an old dented kettle, eyes closed, "
                   "a dark open fridge behind him, old soviet kitchen, grey light",
    "e2b_toilet": "close-up of Denis's hands lifting the heavy porcelain lid of a toilet cistern, clear water inside "
                  "reflecting light, his face above looking down in relief, old cracked tiled bathroom",
    "e2b_supplies": "medium close-up of Denis at his kitchen table counting on his fingers, in front of him plastic "
                    "bottles and cooking pots full of water and cans of stewed meat, grey light from a barred window",
    "e2b_mailbox": "medium close-up of Denis from the side reading a paper list pinned on a wall of old metal mailboxes, "
                   "his finger on the paper, shocked face, dim ground floor hall",
}


def b64(path):
    im = Image.open(path).convert("RGBA")
    return {"image": api.b64png(im), "size": {"width": im.width, "height": im.height},
            "usage_description": "the main character Denis: keep his face, hair, beard, grey hoodie, ripped jeans and sneakers"}


def run(names, seed, size=(W, H), out=None):
    global OUT
    OUT = out or OUT
    refs = [b64(os.path.join(DEN, f"Idle__rotations__{v}.png")) for v in ("south", "east", "north")]
    jobs = {}
    for n in names:
        body = {"description": STYLE + HERO + SHOTS[n], "image_size": {"width": size[0], "height": size[1]},
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
        img.resize((img.width * (1080 // img.width), img.height * (1080 // img.width)), Image.NEAREST).save(
            os.path.join(OUT, f"{n}_1080.png"))
        print(n, img.size, r.get("usage"), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(SHOTS))
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--small", action="store_true", help="экономный размер 216×384 (15 генераций вместо 25)")
    ap.add_argument("--band", action="store_true", help="кадр 270×300 — ровно видимая часть видео (×4 = 1080×1200)")
    a = ap.parse_args()
    if a.band:
        run(a.names, a.seed, (270, 300), os.path.join(HERE, "pro270"))
    elif a.small:
        run(a.names, a.seed, (216, 384), os.path.join(HERE, "pro216"))
    else:
        run(a.names, a.seed)
