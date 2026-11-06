#!/usr/bin/env python3
"""«Я — легенда»: кадры через PixelLab Pro (generate-image-v2).

python3 gen.py refs                 → refs/<герой>.png   (128×128, 4 варианта за 10 генераций, берём первый)
python3 gen.py 01 09 21 [--seed N]  → scenes/NN.png      (360×640, 25 генераций; ×3 = 1080×1920)
Герои передаются образцами из refs/, чтобы были одинаковыми во всех сценах.
"""
import argparse
import base64
import io
import os
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "pixel_apocalypse", "pixellab")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import api  # noqa: E402
from prompts import SCENES  # noqa: E402

REFS_DIR, SCENES_DIR = os.path.join(HERE, "refs"), os.path.join(HERE, "scenes")
STYLE = ("cinematic detailed pixel art, 16-bit adventure game cutscene, fine pixel detail, dramatic lighting, "
         "muted desaturated palette, vertical 9:16 composition, no text, no letters, ")

CHARS = {  # образец: описание (оно же подставляется в сцены вместо имени)
    "neville": "a fit Black man in his late 30s with short cropped hair and a short dark beard, grey hoodie, "
               "olive cargo pants, brown boots",
    "sam": "a German Shepherd dog with a tan and black coat and a red collar",
    "anna": "a woman in her early 30s with long dark wavy hair, olive field jacket, jeans",
    "ethan": "a quiet 10-year-old boy with short brown hair in an oversized blue hoodie",
    "alpha": "the leader of infected creatures: bald, pale grey skin, gaunt muscular body, bloodshot eyes, "
             "wide screaming mouth, bare chest, torn dark trousers",
    "zoe": "a Black woman in her early 30s with curly shoulder-length hair in a beige coat",
    "marley": "a 6-year-old girl with braids in a pink jacket",
}
REF_OF = {"R1": ["neville"], "R2": ["sam"], "R3": ["anna", "ethan"], "R4": ["alpha"], "R5": ["zoe", "marley"]}
# как герои названы в промтах сцен → чем заменить
NAMES = [("Robert's", "the man's"), ("Robert", "the man (" + CHARS["neville"] + ")"),
         ("the woman with long dark hair", "the woman (" + CHARS["anna"] + ")"),
         ("the boy in the blue hoodie", "the boy (" + CHARS["ethan"] + ")")]


def save_first(job, path, scale=None):
    r = api.wait_job(job, every=8, limit=1800)
    lr = r.get("last_response") or {}
    ims = lr.get("images") or ([lr["image"]] if "image" in lr else [])
    if r["status"] != "completed" or not ims:
        print(os.path.basename(path), "НЕ ВЫШЛО:", str(lr)[:300], flush=True)
        return None
    out = []
    for i, im in enumerate(ims):
        raw = base64.b64decode(im["base64"] if isinstance(im, dict) else im)
        img = Image.open(io.BytesIO(raw))
        p = path if i == 0 else path.replace(".png", f"_v{i + 1}.png")
        img.save(p)
        out.append(p)
    print(os.path.basename(path), img.size, len(ims), "вар.", r.get("usage"), flush=True)
    return out


def post(body, name):
    for a in range(6):
        try:
            return api.post("/generate-image-v2", body)["background_job_id"]
        except RuntimeError as e:
            print(name, "повтор:", str(e)[:120], flush=True)
            time.sleep(8)
    raise RuntimeError(name)


def gen_refs(seed):
    os.makedirs(REFS_DIR, exist_ok=True)
    jobs = {}
    for k, d in CHARS.items():
        body = {"description": "pixel art character, full body, front view, standing, detailed, " + d,
                "image_size": {"width": 128, "height": 128}, "no_background": True, "seed": seed}
        jobs[k] = post(body, k)
    for k, j in jobs.items():
        save_first(j, os.path.join(REFS_DIR, f"{k}.png"))


def ref_img(k):
    im = Image.open(os.path.join(REFS_DIR, f"{k}.png")).convert("RGBA")
    return {"image": api.b64png(im), "size": {"width": im.width, "height": im.height},
            "usage_description": f"{k}: {CHARS[k]}. Keep the look of this character"}


def gen_scenes(nums, seed):
    os.makedirs(SCENES_DIR, exist_ok=True)
    by = {n: (refs, p) for n, refs, p in SCENES}
    jobs = {}
    for n in nums:
        refs, p = by[n]
        for a, b in NAMES:
            p = p.replace(a, b)
        keys = [k for r in refs.split() for k in REF_OF[r]]
        body = {"description": STYLE + p, "image_size": {"width": 360, "height": 640}, "no_background": False,
                "reference_images": [ref_img(k) for k in keys], "seed": seed}
        jobs[n] = post(body, f"{n:02d}")
        print(f"{n:02d} запущена, образцы: {keys}", flush=True)
    for n, j in jobs.items():
        save_first(j, os.path.join(SCENES_DIR, f"{n:02d}.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="+")
    ap.add_argument("--seed", type=int, default=31)
    a = ap.parse_args()
    if a.what == ["refs"]:
        gen_refs(a.seed)
    else:
        gen_scenes([int(x) for x in a.what], a.seed)
    print(api.balance()["subscription"]["generations"], "генераций осталось")
