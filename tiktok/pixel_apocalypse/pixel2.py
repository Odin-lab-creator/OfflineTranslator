"""PIXEL APOCALYPSE v2 — «бункерный» dark pixel art (зелёная гамма, кладка, трубы, ореолы ламп).

Конвейер кадра:
  1. сцена рисуется в RGB на холсте 270x480 (цветами палитры + фактурный шум);
  2. освещение: зелёный эмбиент * тёплые источники + ореолы;
  3. квантование в фиксированную палитру с упорядоченным дизерингом Bayer 4x4;
  4. увеличение x4 nearest neighbor → 1080x1920, пиксели чёткие.
"""
import numpy as np
from PIL import Image, ImageDraw

W, H = 270, 480          # «мир» сцены
CW, CH = 180, 320         # кадр камеры → x6 = 1080x1920
OUT_W = 1080

PALETTE = {
    # зелёная основа (камень, металл, тени)
    "G0": "080d0b", "G1": "0e1712", "G2": "152119", "G3": "1d2c23", "G4": "27392d",
    "G5": "334838", "G6": "445c48", "G7": "5a735b", "G8": "778f73",
    # мох / олива
    "M0": "262c1c", "M1": "363f26", "M2": "4d5a33",
    # ржавчина / красный
    "R0": "261312", "R1": "3f1d1a", "R2": "5e2a23", "R3": "80392d", "R4": "a05440",
    # тёплый свет
    "O0": "573318", "O1": "87521f", "O2": "b57f2d", "O3": "d9ad4f", "O4": "eedb92",
    # кость / светлый бетон
    "E0": "5f5e4b", "E1": "8a8869", "E2": "b7b392",
    # кожа, волосы
    "S0": "4a3027", "S1": "75503d", "S2": "9c7155", "S3": "bb9070",
    "H0": "22170f", "H1": "41301f",
    # серо-фиолетовая ткань, кожа сапог
    "P0": "2b2b35", "P1": "454552", "P2": "676777", "P3": "8b8b98",
    "B0": "20170f", "B1": "3a2a1d", "B2": "56402d",
    # заражённые
    "Z0": "3f4a37", "Z1": "5f6e52", "Z2": "829072",
}
NAMES = list(PALETTE)
PAL = np.array([[int(PALETTE[n][i:i + 2], 16) for i in (0, 2, 4)] for n in NAMES], np.float32)


def col(name):
    return np.array([int(PALETTE[name][i:i + 2], 16) for i in (0, 2, 4)], np.float32)


BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16 - 0.5
BT = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W]
YY, XX = np.mgrid[0:H, 0:W]


def value_noise(seed, cell, amp=1.0):
    r = np.random.default_rng(seed)
    gh, gw = H // cell + 2, W // cell + 2
    g = r.random((gh, gw)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((gw * cell, gh * cell), Image.BILINEAR)
    return (np.asarray(im, np.float32)[:H, :W] / 255 - 0.5) * 2 * amp


class Scene:
    def __init__(self, base="G1"):
        self.rgb = np.zeros((H, W, 3), np.float32) + col(base)
        self.emis = np.zeros((H, W), bool)      # самосветящиеся пиксели (лампы, огонь)
        self.actor = np.zeros((H, W), bool)     # персонажи: всегда читаются на тёмном фоне
        self.lights = []
        self.ambient = np.array([0.62, 0.72, 0.66], np.float32)
        self.actor_min = 0.82

    # ---------------------------------------------------------------- маски
    @staticmethod
    def mask(fn):
        m = Image.new("L", (W, H), 0)
        fn(ImageDraw.Draw(m))
        return np.asarray(m) > 0

    def fill(self, m, c, noise=None, amp=0.0, emissive=False):
        c = col(c) if isinstance(c, str) else np.asarray(c, np.float32)
        if noise is not None:
            v = c[None, None] * (1 + noise[..., None] * amp)
            self.rgb[m] = v[m]
        else:
            self.rgb[m] = c
        if emissive:
            self.emis |= m

    def rect(self, x0, y0, x1, y1, c, **kw):
        x0, x1 = sorted((int(round(x0)), int(round(x1)))); y0, y1 = sorted((int(round(y0)), int(round(y1))))
        m = (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)
        self.fill(m, c, **kw); return m

    def poly(self, pts, c, **kw):
        m = self.mask(lambda d: d.polygon([tuple(map(round, p)) for p in pts], fill=255))
        self.fill(m, c, **kw); return m

    def line(self, pts, c, w=1, **kw):
        m = self.mask(lambda d: d.line([tuple(map(round, p)) for p in pts], fill=255, width=w))
        self.fill(m, c, **kw); return m

    def ell(self, cx, cy, rx, ry, c, **kw):
        m = (((XX - cx) / (rx + 0.5)) ** 2 + ((YY - cy) / (ry + 0.5)) ** 2) <= 1
        self.fill(m, c, **kw); return m

    def px(self, x, y, c, emissive=False):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H:
            self.rgb[y, x] = col(c)
            if emissive:
                self.emis[y, x] = True

    def mul(self, m, k):
        self.rgb[m] *= k

    def blend(self, m, c, a):
        a = a if np.ndim(a) == 0 else a[m][..., None]
        self.rgb[m] = self.rgb[m] * (1 - a) + col(c)[None] * a

    # ---------------------------------------------------------------- свет
    def add_light(self, x, y, r, intensity=1.0, color=(1.0, 0.72, 0.42), halo=True, ry=None):
        self.lights.append((x, y, r, ry or r, intensity, np.array(color, np.float32), halo))

    def render(self, vignette=0.55, crop=None):
        lum = np.zeros((H, W, 3), np.float32) + self.ambient
        glow = np.zeros((H, W, 3), np.float32)
        for x, y, r, ry, inten, c, halo in self.lights:
            d = np.sqrt(((XX - x) / r) ** 2 + ((YY - y) / ry) ** 2)
            f = np.clip(1 - d, 0, 1) ** 1.6
            lum += f[..., None] * c * inten * 1.4
            if halo:
                g = np.exp(-d * 5.5) * inten
                glow += g[..., None] * c * 120
        lum[self.actor] = np.maximum(lum[self.actor], self.actor_min)
        out = self.rgb * lum + glow
        out[self.emis] = self.rgb[self.emis] + glow[self.emis] * 0.3
        if crop:  # «камера»: окно CW x CH
            cx0, cy0 = crop
            out = out[cy0:cy0 + CH, cx0:cx0 + CW]
        h, w = out.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        out = out * np.clip(1 - vignette * np.clip(d - 0.45, 0, None) ** 1.5, 0.15, 1)[..., None]
        out += np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w, None] * 14
        flat = out.reshape(-1, 3)
        wts = np.array([0.35, 0.45, 0.2], np.float32)
        idx = np.empty(len(flat), np.int32)
        for i in range(0, len(flat), 40000):
            ch = flat[i:i + 40000]
            dist = (((ch[:, None, :] - PAL[None]) ** 2) * wts).sum(-1)
            idx[i:i + 40000] = dist.argmin(1)
        return PAL[idx].reshape(h, w, 3).astype(np.uint8)

    def save(self, path, crop=None):
        img = Image.fromarray(self.render(crop=crop), "RGB")
        sc = OUT_W // img.width
        img.resize((img.width * sc, img.height * sc), Image.NEAREST).save(path)
        return img

    # ---------------------------------------------------------------- спрайты
    def sprite(self, rows, keys, x, y, flip=False, dark=0.0):
        """rows — ASCII-арт; (x, y) — левый нижний угол."""
        h = len(rows); w = max(len(r) for r in rows)
        for j, r in enumerate(rows):
            r = r.ljust(w, ".")
            if flip:
                r = r[::-1]
            for i, ch in enumerate(r):
                if ch == ".":
                    continue
                px, py = x + i, y - h + 1 + j
                if 0 <= px < W and 0 <= py < H:
                    self.rgb[py, px] = col(keys[ch]) * (1 - dark)
                    self.actor[py, px] = dark < 0.3
                    if ch == "X":
                        self.emis[py, px] = True


# ======================================================================= ГЕРОЙ
# Красная куртка с высоким воротом, оливковый рюкзак, серые штаны, тёмные волосы.
HERO_KEYS = {"o": "G0", "h": "H0", "H": "H1", "s": "S1", "S": "S2", "L": "S3", "e": "G0",
             "r": "R2", "R": "R3", "Q": "R4", "n": "M0", "N": "M1", "k": "B0", "K": "E1",
             "g": "P0", "G": "P1", "W": "P2", "b": "B0", "B": "B2", "m": "R1"}

_HEAD = [
    "......ooooo.........",
    ".....ohhhhhoo.......",
    "....ohhHHHHhho......",
    "....ohhhHHHHhho.....",
    "...ohhhhhhhhhho.....",
    "...ohhhhhhhSSSo.....",
    "...ohhhhhhSSLLo.....",
    "...ohhhsShSSSLLo....",
    "...ohhsSSSSeSSLo....",
    "....ohSsSSSSSSLLo...",
    "....ohsSSSSSSSso....",
    ".....osSSSSSmsoo....",
    ".....ossSSSSSo......",
    "......osssSsso......",
    ".....ooossssooo.....",
]
_TORSO = [
    "....orrRrsssRRQo....",
    "...onnrRRRRRRRQQo...",
    "..onNNnrRRRRRRQQo...",
    "..onNNnrRRRRrRQQo...",
    "..onNNnorRRRrRRQo...",
    "..onNNnorRRrRRRQo...",
    "..onNNnorRRrRRRQo...",
    "..onNNnorRRrRRRQo...",
    "..onNnnorRRrRRRQo...",
    "..onNnnorRRrRRQQo...",
    "..onnnnorRRrRRQQo...",
    "...ooooorRRrRRQQo...",
    ".......orRRrRRRQo...",
    ".......okkkrkKkko...",
    ".......orRRrRRRQo...",
    ".......orRRrRRRQo...",
    ".......orrRrRRrro...",
    ".......oogGrRQgoo...",
    ".......ogGGoSSLo....",
    ".......ogGGoSSSo....",
    ".......ogGGWosoo....",
]
_LEG = [".......ogGgoWGo.....", ".......ogGgoGWo....."]
_FEET = [
    ".......ogGgoGWGo....",
    ".......ogggoGGGo....",
    ".......obbbobBBo....",
    "......obbbBobbBBo...",
    "......obbbBobbbBBo..",
    "......oooooooooooo..",
]
HERO_STAND = _HEAD + _TORSO + [_LEG[i % 2] for i in range(20)] + _FEET   # 62 px
HERO_HAND = (13, -26)  # положение кисти относительно (x, y) спрайта стоя

HERO_SIT = _HEAD + _TORSO[:13] + [
    ".......okkkrkKkko..oooo...",
    ".......orRRrRRSSo.oWWWGo..",
    ".......orRRrRRSLooWWWWGGo.",
    ".......orrRrRooWWWWWGGgGo.",
    ".......ogGGGGWWWWGGGgooGGo",
    ".......ogGGGGGGGGGgo..oGGo",
    ".......ogggGGGGGgo....oGGo",
    ".......ooooooooo......oGGo",
    "......................oGGo",
    ".....................obbBo",
    "....................obbbBBo",
    "....................ooooooo",
]

# ================================================================== ЗАРАЖЁННЫЙ
ZOMBIE_KEYS = {"o": "G0", "Z": "Z1", "z": "Z0", "L": "Z2", "X": "R4", "m": "R0",
               "T": "B1", "t": "B0", "P": "P1", "p": "P0"}
ZOMBIE = [
    "..........ooooo.......",
    ".........oZZLZzo......",
    "........oZZLLZZzo.....",
    "........ozZZZZZZZo....",
    "........ozZZZZXZZo....",
    "........ozzZZZZZmo....",
    ".........ozzZZmmmo....",
    "..........ozzzzzo.....",
    "......oooooozzoo......",
    "....ooTTTTttoo........",
    "...oTTTTTTTTto........",
    "..oTTTtTTTTTTto.......",
    "..oTTTtTTTTTTTZo......",
    "..otTTtTTTTTTTZZo.....",
    "..otTTtTTzTTTozZZo....",
    "..otTTtoTTTTTo.ozZo...",
    "..otttooTTzTTo..ozZo..",
    "...ozZo.oTTTTo...ozZo.",
    "...ozZo.otTTTo....oZZo",
    "...ozZo.otttto....ozZo",
    "...ozZo.oPPPPo.....oZo",
    "....oZZoPPpPPo.....ooo",
    "....oZooPPopPPo.......",
    ".....oo.oPPopPPo......",
] + ["........oPPo.oPPo....." if i % 2 else "........oPpo.oPPo....." for i in range(18)] + [
    "........ozzo..oPPo....",
    ".......ozzzo..ozzo....",
    ".......ooooo.ozzzzo...",
    ".............oooooo...",
]
