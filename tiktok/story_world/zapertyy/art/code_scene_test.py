#!/usr/bin/env python3
"""Проба: кадр целиком нарисован кодом (без нейросетей) в сетке 360×400, как кадры Pro.

Сцена финала серии 3: ночь, окно девятого этажа, свеча на подоконнике, за окном тёмный город до горизонта.
python3 code_scene_test.py  →  code_test/night_window.png (кадр), night_window_1080.png (в компоновке видео),
                               night_window.mp4 (5 с: свеча мерцает, звёзды мигают)
"""
import os
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "code_test")
W, H = 360, 400
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def dither_mix(c0, c1, t, yy, xx):
    """Смешение двух цветов с упорядоченным дизерингом (t — доля второго цвета, 0…1)."""
    th = BAYER[yy % 4, xx % 4]
    return np.where((t > th)[..., None], np.array(c1), np.array(c0))


def ramp(cols, t, yy, xx):
    """Градиент по списку цветов с дизерингом между соседними ступенями."""
    n = len(cols) - 1
    s = np.clip(t, 0, 0.9999) * n
    i = s.astype(int)
    f = s - i
    out = np.zeros(t.shape + (3,))
    for k in range(n):
        m = i == k
        if m.any():
            out[m] = dither_mix(cols[k], cols[k + 1], f, yy, xx)[m]
    return out


def scene(t=0.0, seed=4):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    img = np.zeros((H, W, 3))
    # --- окно: проём
    wx0, wy0, wx1, wy1 = 46, 34, 314, 300
    # небо
    sky = ramp([(6, 8, 18), (10, 14, 30), (16, 22, 42), (26, 34, 54)], (yy - wy0) / (wy1 - wy0), yy, xx)
    img[:] = sky
    # звёзды
    rs = np.random.default_rng(11)
    for _ in range(140):
        x, y = rs.integers(wx0, wx1), rs.integers(wy0, wy0 + 150)
        b = rs.uniform(0.3, 1.0) * (0.75 + 0.25 * np.sin(t * rs.uniform(2, 5) + rs.uniform(0, 6)))
        img[y, x] = np.array([190, 200, 225]) * b
    # город: три слоя силуэтов, все окна тёмные
    layers = [((22, 28, 44), 175, 60, 25, (30, 36, 54)), ((15, 19, 32), 205, 85, 40, (21, 26, 40)),
              ((9, 11, 20), 240, 110, 55, (14, 17, 28))]
    for col, base, hmax, wmin, wincol in layers:
        x = wx0 - 10
        while x < wx1 + 10:
            w = int(r.integers(wmin, wmin + 40))
            h = int(r.integers(hmax // 3, hmax))
            top = base - h
            img[top:wy1, max(x, 0):min(x + w, W)] = col
            if r.random() < 0.4:                               # антенна / бак на крыше
                ax = x + int(r.integers(3, max(4, w - 4)))
                img[top - int(r.integers(4, 12)):top, ax:ax + 1] = col
            for wy in range(top + 6, wy1, 9):                  # тёмные окна, кое-где выбитые
                for wxp in range(x + 4, x + w - 4, 7):
                    if 0 <= wxp < W:
                        c = wincol if r.random() > 0.08 else (col[0] // 2, col[1] // 2, col[2] // 2)
                        img[wy:wy + 4, wxp:wxp + 3] = c
            x += w + int(r.integers(0, 8))
    # --- стена вокруг окна
    wall = ramp([(18, 16, 15), (28, 24, 21), (36, 31, 27)], np.clip(yy / H, 0, 1), yy, xx)
    m = np.ones((H, W), bool)
    m[wy0:wy1, wx0:wx1] = False
    img[m] = wall[m]
    noise = r.normal(0, 3, (H, W, 1))
    img[m] += noise[m]
    # рама, перекладины, подоконник
    frame_c = (40, 36, 33)
    img[wy0 - 6:wy0, wx0 - 6:wx1 + 6] = frame_c
    img[wy0:wy1, wx0 - 6:wx0] = frame_c
    img[wy0:wy1, wx1:wx1 + 6] = frame_c
    img[wy0:wy1, (wx0 + wx1) // 2 - 3:(wx0 + wx1) // 2 + 3] = frame_c
    img[wy0 + 90:wy0 + 96, wx0:wx1] = frame_c
    sill_y = wy1
    img[sill_y:sill_y + 10, wx0 - 18:wx1 + 18] = (58, 50, 44)
    img[sill_y + 10:sill_y + 14, wx0 - 18:wx1 + 18] = (30, 26, 23)
    # --- свеча и её свет (мерцание)
    cx, cy = 230, sill_y - 2
    fl = 1.0 + 0.08 * np.sin(t * 13.0) + 0.05 * np.sin(t * 29.0 + 1.3)
    d = np.sqrt(((xx - cx) / 1.0) ** 2 + ((yy - (cy - 26)) / 1.15) ** 2)
    glow = np.clip(1 - d / (150 * fl), 0, 1) ** 2.2
    warm = np.array([255, 150, 70])
    lit = img + glow[..., None] * warm * 0.55
    steps = np.floor(glow * 6) / 6                              # свет ступенями — по-пиксельному
    img = img * (1 - steps[..., None] * 0.15) + steps[..., None] * warm * 0.35
    img = np.where((glow > 0.02)[..., None], img * 0.6 + lit * 0.4, img)
    img[cy - 22:cy, cx - 4:cx + 4] = (226, 214, 190)            # свеча
    img[cy - 22:cy, cx + 2:cx + 4] = (196, 182, 160)
    img[cy - 4:cy, cx - 6:cx + 6] = (120, 104, 86)              # блюдце
    fh = int(round(7 * fl))
    img[cy - 22 - fh:cy - 22, cx - 1:cx + 2] = (255, 196, 90)   # пламя
    img[cy - 22 - fh + 2:cy - 23, cx:cx + 1] = (255, 244, 200)
    img[cy - 23:cy - 22, cx - 2:cx + 3] = (255, 170, 60)
    # отражение пламени в стекле
    img[cy - 60:cy - 54, cx + 30:cx + 32] = (120, 80, 40)
    # спички на подоконнике
    img[sill_y + 3:sill_y + 5, 120:136] = (150, 120, 80)
    img[sill_y + 3:sill_y + 5, 136:139] = (90, 30, 26)
    return np.clip(img, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fr = scene(0.0)
    Image.fromarray(fr).save(os.path.join(OUT, "night_window.png"))
    big = Image.fromarray(fr).resize((1080, 1200), Image.NEAREST)
    canvas = Image.new("RGB", (1080, 1920), (10, 9, 12))
    canvas.paste(big, (0, 360))
    canvas.save(os.path.join(OUT, "night_window_1080.png"))
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                          os.path.join(OUT, "night_window.mp4")], stdin=subprocess.PIPE)
    for k in range(150):
        f = Image.fromarray(scene(k / 30)).resize((1080, 1200), Image.NEAREST)
        c = Image.new("RGB", (1080, 1920), (10, 9, 12))
        c.paste(f, (0, 360))
        p.stdin.write(c.tobytes())
    p.stdin.close()
    p.wait()
    print("готово:", OUT)
