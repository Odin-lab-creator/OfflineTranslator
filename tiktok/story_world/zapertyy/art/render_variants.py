#!/usr/bin/env python3
"""Ролики-пробы 4 способов оживления → variants/v1..v4.mp4 и variants/compare.mp4 (2×2 с подписями)."""
import glob
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(HERE, "variants")
PRO = os.path.join(HERE, "test_pro")
EP = os.path.join(HERE, "..", "zapertyy_ep1_comic.mp4")
W, H, FPS, DUR = 1080, 1920, 30, 6.0
KICK_BOX = (52, 170)
WIN_Y = 240
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def writer(path, w=W, h=H):
    return subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)


def v1():
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "91.2", "-t", str(DUR), "-i", EP, "-c:v", "libx264",
                    "-crf", "20", "-c:a", "aac", os.path.join(V, "v1.mp4")], check=True)


def v2():
    base = Image.open(os.path.join(PRO, "04_kick_wide.png")).convert("RGBA")
    base.paste(Image.open(os.path.join(V, "v2_plate.png")).convert("RGBA"), KICK_BOX)
    fr = [Image.open(f).convert("RGBA") for f in sorted(glob.glob(os.path.join(V, "v2b_anim", "*.png")))]
    p = writer(os.path.join(V, "v2.mp4"))
    for i in range(int(DUR * FPS)):
        k = int(i / FPS * 12) % len(fr)
        im = base.copy()
        im.alpha_composite(fr[k], KICK_BOX)
        p.stdin.write(im.convert("RGB").resize((W, H), Image.NEAREST).tobytes())
    p.stdin.close()
    p.wait()


def v3():
    fr = [Image.open(f).convert("RGB") for f in sorted(glob.glob(os.path.join(V, "v3_anim", "*.png")))]
    p = writer(os.path.join(V, "v3.mp4"))
    for i in range(int(DUR * FPS)):
        k = int(i / FPS * 12) % len(fr)
        p.stdin.write(fr[k].resize((W, H), Image.NEAREST).tobytes())
    p.stdin.close()
    p.wait()


def v4():
    bg = Image.open(os.path.join(PRO, "02_window.png")).convert("RGBA")
    bg.paste(Image.open(os.path.join(V, "v4_plate.png")).convert("RGBA"), (0, WIN_Y))
    hero = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    hero.alpha_composite(Image.open(os.path.join(V, "v4_cut.png")).convert("RGBA"), (0, WIN_Y))
    BG = bg.resize((W, H), Image.NEAREST)
    HE = hero.resize((W, H), Image.NEAREST)
    win = np.zeros((H, W, 1), np.float32)                     # область окна — для мерцания света
    win[int(0.05 * H):int(0.62 * H), int(0.08 * W):int(0.92 * W)] = 1
    rng = np.random.default_rng(4)
    n = 60
    px, py = rng.uniform(0, W, n), rng.uniform(0, H * 0.7, n)
    vx, vy = rng.uniform(-8, 8, n), rng.uniform(-16, -4, n)
    p = writer(os.path.join(V, "v4.mp4"))
    for i in range(int(DUR * FPS)):
        t = i / FPS
        u = t / DUR
        u = u * u * (3 - 2 * u)
        zb, zh = 1.0 + 0.04 * u, 1.0 + 0.11 * u               # передний план приближается быстрее фона
        sb, sh = 8 * u, -14 * u                              # и едет в другую сторону
        breathe = 1 + 0.006 * np.sin(2 * np.pi * 0.35 * t)

        def tf(img, z, sx, zy=1.0):
            cx, cy = W / 2 + sx, H * 0.95
            a, e = 1 / z, 1 / (z * zy)
            return img.transform((W, H), Image.AFFINE, (a, 0, cx - a * cx, 0, e, cy - e * cy), Image.BILINEAR)

        im = tf(BG, zb, sb)
        arr = np.asarray(im.convert("RGB")).astype(np.float32)
        arr *= 1 + win * (0.04 * np.sin(t * 2.1) + 0.02 * np.sin(t * 7.3))
        fg = tf(HE, zh, sh, breathe)
        f = np.asarray(fg).astype(np.float32)
        al = f[..., 3:4] / 255
        arr = arr * (1 - al) + f[..., :3] * al
        for k in range(n):
            x, y = int((px[k] + vx[k] * t) % W), int((py[k] + vy[k] * t) % H)
            arr[y:y + 3, x:x + 3] = arr[y:y + 3, x:x + 3] * 0.6 + 235 * 0.4
        p.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()


def compare():
    labels = ["1 · Кинокомикс (сейчас)", "2 · Анимация героя PixelLab", "3 · Весь кадр движется", "4 · Параллакс + живой кадр"]
    ins = sum([["-i", os.path.join(V, f"v{k}.mp4")] for k in range(1, 5)], [])
    draw = ",".join([])
    f = []
    for k in range(4):
        f.append(f"[{k}:v]scale=540:960,drawbox=x=0:y=0:w=540:h=64:color=black@0.6:t=fill,"
                 f"drawtext=fontfile={FONT}:text='{labels[k]}':fontcolor=0xF0C478:fontsize=30:x=16:y=16[p{k}]")
    f.append("[p0][p1]hstack[top];[p2][p3]hstack[bot];[top][bot]vstack[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(f), "-map", "[out]", "-map", "0:a?",
                    "-t", str(DUR), "-c:v", "libx264", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    os.path.join(V, "compare.mp4")], check=True)
    return draw


if __name__ == "__main__":
    v1()
    v2()
    v3()
    v4()
    compare()
    print("готово:", V)
