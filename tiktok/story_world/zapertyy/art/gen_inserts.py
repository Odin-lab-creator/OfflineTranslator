#!/usr/bin/env python3
"""Дешёвые вставки-крупные планы (pixflux, 1 генерация) в палитре главных кадров серии.

python3 gen_inserts.py [ИМЯ ...] [--seed N]  →  pro216/ins_<имя>.png (216×384)
Палитра (48 цветов) снимается с главных кадров pro216/*.png — так вставки совпадают по цвету.
"""
import argparse
import glob
import os
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "pixel_apocalypse", "pixellab")))
import api  # noqa: E402
from gen_bg import decode  # noqa: E402

DIR = os.path.join(HERE, "pro216")
STYLE = ("cinematic detailed pixel art, 16-bit adventure game cutscene close-up, moody soft lighting, muted gloomy "
         "palette, post-apocalyptic, no text, ")
INSERTS = {
    "phone": "close-up of a man's hand in a grey hoodie sleeve holding a black smartphone with a dead black screen, "
             "an old light switch on the wallpapered wall behind, dim room",
    "watch": "extreme close-up of a man's wrist in a grey hoodie sleeve with an old mechanical wristwatch, hands stopped "
             "at twenty to four, scratched glass, dim grey light",
    "pills": "close-up of an old wooden table with empty pill blister packs, an old glass thermometer and an empty glass, "
             "dust and crumbs, grey daylight",
    "tap": "close-up of an old kitchen faucet over a metal sink, a single water drop falling from the tap, rust stains, "
           "a hand on the tap handle, dim kitchen",
    "weld": "close-up of two hands gripping thick metal window bars, shiny fresh weld seams where the bars are welded to "
            "the window frame, grey light, empty street blurred outside",
    "intercom": "close-up of a finger pressing a button on a dead intercom panel on a dirty wall next to a heavy metal "
                "door, dark display, dim",
    "crack": "extreme close-up of a narrow gap between a heavy metal door and its frame near the hinges, bright daylight "
             "through the gap, outside a thick rusty iron strip is welded across the door, rough weld seam",
}


def palette(n=48, seed=0):
    px = np.concatenate([np.asarray(Image.open(f).convert("RGB")).reshape(-1, 3)
                         for f in sorted(glob.glob(os.path.join(DIR, "[0-9][0-9]_*.png")))
                         if not f.endswith("_1080.png")]).astype(np.float32)
    rng = np.random.default_rng(seed)
    px = px[rng.choice(len(px), min(60000, len(px)), replace=False)]
    c = px[rng.choice(len(px), n, replace=False)]
    for _ in range(25):                                         # k-средних
        lab = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        for k in range(n):
            m = px[lab == k]
            if len(m):
                c[k] = m.mean(0)
    return Image.fromarray(c.round().astype(np.uint8)[None], "RGB")


def match_colors(img, strength=0.7):
    """Подгонка цвета вставки к главным кадрам: среднее и разброс по каналам, частично."""
    ref = np.concatenate([np.asarray(Image.open(f).convert("RGB")).reshape(-1, 3)
                          for f in sorted(glob.glob(os.path.join(DIR, "[0-9][0-9]_*.png")))
                          if not f.endswith("_1080.png")]).astype(np.float32)
    a = np.asarray(img).astype(np.float32)
    m, s = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-3
    rm, rs = ref.mean(0), ref.std(0)
    b = (a - m) / s * rs + rm
    out = a * (1 - strength) + b * strength
    return Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8))


def gen(name, seed, pal):
    body = {"description": STYLE + INSERTS[name], "image_size": {"width": 216, "height": 384},
            "detail": "highly detailed", "shading": "highly detailed shading", "outline": "selective outline",
            "text_guidance_scale": 8, "seed": seed}
    if pal is not None:
        body["color_image"] = api.b64png(pal)
    for a in range(6):
        try:
            r = api.post("/create-image-pixflux-background", body)
            j = api.wait_job(r["background_job_id"], every=5, limit=900)
            img = match_colors(decode(j["last_response"]).convert("RGB"))
            img.save(os.path.join(DIR, f"ins_{name}.png"))
            return j.get("usage")
        except (RuntimeError, KeyError) as e:
            print(name, "повтор:", str(e)[:100], flush=True)
            time.sleep(6)
    raise RuntimeError(name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=list(INSERTS))
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--palette", action="store_true", help="принудительная палитра (темнее)")
    a = ap.parse_args()
    pal = palette() if a.palette else None
    for n in a.names:
        print(n, gen(n, a.seed, pal), flush=True)
