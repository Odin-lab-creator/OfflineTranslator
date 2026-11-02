#!/usr/bin/env python3
"""Пробы способов оживления кадров (PixelLab API) → variants/.

v2: кусок кадра 256×256 с Денисом анимируется PixMiniMax (вырезанный герой) + чистая подложка без него (inpaint).
v3: весь кадр, уменьшенный до 144×256, анимируется PixMiniMax целиком (как «видео из картинки», только мельче).
v4: кадр с окном делится на слои: Денис (remove-background) и подложка без него (inpaint) — для параллакса.
"""
import base64
import io
import json
import os
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import api  # noqa: E402

PRO = os.path.join(HERE, "test_pro")
OUT = os.path.join(HERE, "variants")
os.makedirs(OUT, exist_ok=True)
KICK_BOX = (52, 170, 308, 426)          # x0, y0, x1, y1 в кадре 04_kick_wide
WIN_BOX = (0, 240, 360, 640)            # кусок 02_window с Денисом (не больше 400 по стороне)


def img_b64(im):
    return api.b64png(im)


def decode_any(x):
    b = x["base64"] if isinstance(x, dict) else x
    return Image.open(io.BytesIO(base64.b64decode(b))).convert("RGBA")


def post_retry(path, body, tries=5):
    for a in range(tries):
        try:
            return api.post(path, body)
        except RuntimeError as e:
            print(path, "повтор:", str(e)[:120], flush=True)
            time.sleep(8)
    raise RuntimeError(path)


def job_images(r):
    j = api.wait_job(r["background_job_id"], every=5, limit=2400)
    lr = j.get("last_response") or {}
    if j["status"] != "completed":
        raise RuntimeError(str(lr)[:300])
    ims = lr.get("images") or ([lr["image"]] if "image" in lr else [])
    return [decode_any(x) for x in ims], j.get("usage")


def start_all():
    kick = Image.open(os.path.join(PRO, "04_kick_wide.png")).convert("RGB")
    crop = kick.crop(KICK_BOX)
    small = kick.resize((144, 256), Image.LANCZOS)
    win = Image.open(os.path.join(PRO, "02_window.png")).convert("RGB").crop(WIN_BOX)
    jobs = {}
    jf = os.path.join(OUT, "jobs.json")
    if os.path.exists(jf):
        jobs = json.load(open(jf))
    if "v2_anim" in jobs:
        pass
    else:
        jobs["v2_anim"] = post_retry("/animate-pixminimax", {
        "first_frame": img_b64(crop), "frame_count": 24, "no_background": True, "seed": 3,
        "description": "kicks the heavy door hard with his right foot, pulls the leg back, kicks again harder, "
                       "then rams the door with his shoulder and steps back",
        "subject_description": "a man in a grey hoodie and dark jeans seen from behind",
        "initial_pose": "standing on his left leg with the right foot raised, kicking a door",
        "direction": "north"})
        json.dump(jobs, open(jf, "w"))
    if "v3_anim" not in jobs:
        jobs["v3_anim"] = post_retry("/animate-pixminimax", {
        "first_frame": img_b64(small), "frame_count": 24, "no_background": False, "seed": 3,
        "description": "the man kicks the door hard again and again, the door shakes, dust falls, the camera stays still",
        "subject_description": "a man in a grey hoodie in a dim entrance hall, seen from behind",
        "direction": "north"})
        json.dump(jobs, open(jf, "w"))
    if not os.path.exists(os.path.join(OUT, "v2_cut.png")):
        r = post_retry("/remove-background", {"image": img_b64(crop), "image_size": {"width": 256, "height": 256},
                                          "background_removal_task": "remove_complex_background",
                                          "text": "a man in a grey hoodie and dark jeans"})
        decode_any(r.get("image") or r["images"][0]).save(os.path.join(OUT, "v2_cut.png"))
    if os.path.exists(os.path.join(OUT, "v4_cut.png")):
        return jobs
    r = post_retry("/remove-background", {"image": img_b64(win), "image_size": {"width": 360, "height": 400},
                                          "background_removal_task": "remove_complex_background",
                                          "text": "a man in a grey hoodie seen from behind, holding window bars"})
    decode_any(r.get("image") or r["images"][0]).save(os.path.join(OUT, "v4_cut.png"))
    print("вырезки готовы", flush=True)
    return jobs


def clean_plate(src, box, cut_path, desc, out_name):
    """Убираем Дениса: маска = его силуэт, расширенный на 3 px; inpaint-v3 дорисовывает фон."""
    if os.path.exists(os.path.join(OUT, out_name)):
        return
    im = Image.open(os.path.join(PRO, src)).convert("RGB").crop(box)
    a = np.asarray(Image.open(os.path.join(OUT, cut_path)))[..., 3] > 40
    m = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))
    m.save(os.path.join(OUT, out_name.replace(".png", "_mask.png")))
    sz = {"width": im.width, "height": im.height}
    r = post_retry("/inpaint-v3", {"description": desc, "inpainting_image": {"image": img_b64(im), "size": sz},
                                   "mask_image": {"image": img_b64(m.convert("RGB")), "size": sz}, "seed": 4})
    ims, usage = job_images(r)
    ims[0].convert("RGB").save(os.path.join(OUT, out_name))
    print(out_name, usage, flush=True)


if __name__ == "__main__":
    jobs = start_all()
    clean_plate("04_kick_wide.png", KICK_BOX, "v2_cut.png",
                "empty dirty tiled floor in front of a heavy closed metal entrance door, nobody there", "v2_plate.png")
    clean_plate("02_window.png", WIN_BOX, "v4_cut.png",
                "window with thick welded metal bars, empty grey city street outside, window sill, radiator, nobody there",
                "v4_plate.png")
    for name, r in jobs.items():
        ims, usage = job_images(r)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for k, im in enumerate(ims):
            im.save(os.path.join(d, f"{k:02d}.png"))
        print(name, len(ims), ims[0].size, usage, flush=True)
