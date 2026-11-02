#!/usr/bin/env python3
"""«ЗАПЕРТЫЙ» по методичке «Сто метров»: вид строго сбоку, pixflux-фоны, герой v3 88px, анимации v3 по 12 кадров.

python3 gen_sto.py hero              → создаёт Дениса (v3, 88, side, тонкая обводка, средняя детализация)
python3 gen_sto.py bg [ИМЯ ...]      → sto/bg_<имя>.png (pixflux: side, basic shading, medium detail, lineless)
python3 gen_sto.py obj [ИМЯ ...]     → sto/obj_<имя>.png (прозрачный фон, тонкая обводка)
python3 gen_sto.py anim              → запускает анимации героя (v3, 12 кадров)
python3 gen_sto.py pull              → выгружает героя и анимации в sto/denis/
"""
import io
import json
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import api  # noqa: E402
from gen_bg import decode  # noqa: E402

OUT = os.path.join(HERE, "sto")
STATE = os.path.join(OUT, "state.json")
NO = (", abandoned and dusty, gloomy muted colors: dark olive green, grey, dirty brown, faded colors, dim grey light, "
      "no people, no text, no letters")

HERO = ("young man thirty one years old, messy dark brown hair, short dark stubble, tired pale face, plain grey hoodie, "
        "ripped dark blue jeans, worn white sneakers, no backpack, no bag, nothing on his back, empty hands, no weapon")

BGS = {   # имя: (ширина, высота, промпт)
    "room": (360, 200, "2D side-scroller game background, flat side elevation with no perspective, interior of a small "
                       "old soviet apartment living room seen from the side, worn wallpaper, an old sofa on the left, "
                       "a small table with a phone and pill packs, an overturned chair, a round wall clock, on the right "
                       "a window with thick metal bars welded outside the glass, grey daylight, parquet floor strip "
                       "along the very bottom"),
    "corridor": (360, 200, "2D side-scroller game background, flat side elevation with no perspective, dim apartment "
                           "building corridor seen from the side, three apartment doors standing wide open along the "
                           "wall, an abandoned suitcase and a plush toy bunny on the floor, peeling green paint, "
                           "electric meter box, tiled floor strip along the very bottom"),
    "hall": (180, 200, "2D side-scroller game background, flat side elevation with no perspective, ground floor "
                       "entrance hall of an old apartment building, a heavy closed metal entrance door in the middle of "
                       "the back wall, intercom panel next to it, a row of metal mailboxes on the left, thin line of "
                       "daylight under the door, dim, dirty tiled floor strip along the very bottom"),
    "street": (360, 200, "2D side-scroller game background, flat side elevation with no perspective, empty city street "
                         "outside, abandoned cars with open doors standing on the road, a baby stroller lying on its side, "
                         "a plastic bag on the asphalt, nine-storey grey apartment blocks behind, overcast sky"),
    "stairs": (360, 200, "2D side-scroller game background, flat side elevation with no perspective, stairwell of an old "
                         "apartment building seen from the side, a concrete staircase going down from the upper left to a "
                         "landing on the lower right, metal railing with a wooden handrail, green painted walls with "
                         "chipped paint, a big red painted arrow pointing down on the wall, small dirty window, "
                         "landing floor strip along the very bottom"),
}
OBJS = {  # имя: (ширина, высота, промпт)
    "lying": (96, 40, "young man lying flat on his back with his face up towards the ceiling, seen exactly from the side, "
                      "head on the left, feet on the right, one hand on his forehead, messy dark brown hair, stubble, plain grey hoodie, ripped dark blue jeans, "
                      "white sneakers, no blood, no objects"),
    "phone": (64, 96, "close-up of a man's hand in a grey sleeve holding a black smartphone with a completely dead black "
                      "screen, seen from the front, no text"),
    "watch": (96, 64, "close-up of a man's wrist in a grey hoodie sleeve with an old mechanical wristwatch, the hands "
                      "stopped at twenty to four, seen from above, no text"),
    "pills": (96, 64, "a few empty pill blister packs, an old glass thermometer and an empty glass lying together, "
                      "seen from slightly above, no text"),
    "tap": (64, 96, "an old chrome kitchen faucet with a single water drop hanging from the spout, seen from the side, "
                    "no text"),
    "weld": (96, 96, "close-up of a thick vertical metal bar welded to a metal window frame, shiny fresh weld seam, "
                     "a man's hand gripping the bar, no text"),
    "intercom": (64, 96, "old metal intercom panel with a dark dead screen and a keypad, a finger pressing a button, "
                         "no text, no letters"),
    "crack": (96, 128, "close-up of the edge of a heavy dark metal door with a narrow bright gap of daylight, a thick "
                       "rusty iron strip welded across the gap, rough weld seam, no text"),
}
ANIMS = {  # имя: (направление, описание)
    "shout": ("east", "cups both hands around his mouth and shouts loudly, leaning forward a little, then listens, "
                      "no objects, no other people"),
    "kick": ("north", "kicks hard forward into the empty air with his right foot, pulls the leg back and kicks again, "
                      "straining, empty space in front of him, no door, no objects, no other people"),
    "sit": ("south", "leans his back against the door behind him and slowly slides down to sit on the floor, hugs his "
                     "knees and lowers his head, exhausted, no objects, no other people"),
    "bars": ("east", "grabs the window bars in front of him with both hands and shakes them hard, empty hands, "
                     "no objects attached, no other people"),
}


def state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(s):
    os.makedirs(OUT, exist_ok=True)
    json.dump(s, open(STATE, "w"), indent=1)


def pixflux(desc, w, h, no_bg, outline, seed=7):
    body = {"description": desc, "image_size": {"width": w, "height": h}, "view": "side",
            "shading": "basic shading", "detail": "medium detail", "outline": outline,
            "text_guidance_scale": 8, "no_background": no_bg, "seed": seed}
    for a in range(6):
        try:
            r = api.post("/create-image-pixflux-background", body)
            j = api.wait_job(r["background_job_id"], every=5, limit=900)
            return decode(j["last_response"]), j.get("usage")
        except (RuntimeError, KeyError) as e:
            print("повтор:", str(e)[:100], flush=True)
            time.sleep(6)
    raise RuntimeError(desc[:40])


def cmd_hero():
    r = api.post("/create-character-v3", {"description": HERO, "image_size": {"width": 88, "height": 88},
                                          "view": "side", "outline": "single color black outline",
                                          "detail": "medium detail", "seed": 31, "name": "Denis sto"})
    s = state()
    s["hero"] = r["character_id"]
    save_state(s)
    print("герой:", r["character_id"], api.wait_job(r["background_job_id"])["status"])


def cmd_anim(only=None):
    s = state()
    s.setdefault("anim_jobs", {})
    for name, (d, desc) in ANIMS.items():
        if only and name not in only:
            continue
        r = api.post("/characters/animations", {"character_id": s["hero"], "mode": "v3", "frame_count": 12,
                                                "action_description": desc, "directions": [d], "animation_name": name})
        s["anim_jobs"][name] = r.get("background_job_ids")
        print(name, "запущена", flush=True)
    save_state(s)


def cmd_pull():
    s = state()
    for name, ids in s.get("anim_jobs", {}).items():
        for j in ids:
            print(name, api.wait_job(j, every=10, limit=2400)["status"], flush=True)
    raw = api.get(f"/characters/{s['hero']}/zip", raw=True, timeout=180)
    d = os.path.join(OUT, "denis")
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            if n.lower().endswith(".png"):
                open(os.path.join(d, n.replace("/", "__")), "wb").write(z.read(n))
    print("выгружено в", d)


if __name__ == "__main__":
    what, names = sys.argv[1], sys.argv[2:]
    os.makedirs(OUT, exist_ok=True)
    if what == "hero":
        cmd_hero()
    elif what == "anim":
        cmd_anim(names)
    elif what == "pull":
        cmd_pull()
    elif what == "bg":
        for n in names or list(BGS):
            w, h, p = BGS[n]
            img, u = pixflux(p + NO, w, h, False, "lineless")
            img.convert("RGB").save(os.path.join(OUT, f"bg_{n}.png"))
            print(n, u, flush=True)
    elif what == "obj":
        for n in names or list(OBJS):
            w, h, p = OBJS[n]
            img, u = pixflux(p, w, h, True, "single color black outline")
            img.save(os.path.join(OUT, f"obj_{n}.png"))
            print(n, u, flush=True)
