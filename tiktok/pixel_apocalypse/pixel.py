"""PIXEL APOCALYPSE — общий движок пиксель-арта канала.

Все кадры рисуются на холсте 216x384 индексами фиксированной палитры и
увеличиваются x5 «ближайшим соседом» до 1080x1920 — пиксели остаются чёткими.
Градиенты и свет — только упорядоченным дизерингом (Bayer 4x4), как в 16-bit играх.
"""
import numpy as np
from PIL import Image, ImageDraw

W, H, SCALE = 216, 384, 5

# ------------------------------------------------------------------ палитра
# Рампы от тёмного к светлому. Других цветов в кадрах нет.
RAMPS = {
    "K": ["0a0b0c", "131517", "1d2023", "2a2e31", "3c4144", "555a5c", "73776f"],   # чёрный → серый
    "N": ["0e1710", "16241a", "213424", "2f4630", "425a3c", "5c7049"],             # тёмно-зелёный
    "B": ["1a120d", "281c14", "3a2a1c", "523b27", "6b5034", "86683f"],             # грязно-коричневый
    "R": ["240d0c", "3d1513", "5e201c", "802f25"],                                 # приглушённый красный
    "O": ["4e2911", "7a4318", "9c5f22", "b57a33", "c79a52"],                       # тусклый оранжевый
}
PAL, NAME = [], {}
for k, ramp in RAMPS.items():
    for i, hx in enumerate(ramp):
        NAME[f"{k}{i}"] = len(PAL)
        PAL.append(tuple(int(hx[j:j + 2], 16) for j in (0, 2, 4)))
PAL_ARR = np.array(PAL, np.uint8)
P = NAME  # короткий доступ: P["N2"]

# сдвиги по рампе: светлее / темнее
UP = np.arange(len(PAL)); DOWN = np.arange(len(PAL)); WARM = np.arange(len(PAL))
for k, ramp in RAMPS.items():
    for i in range(len(ramp)):
        me = NAME[f"{k}{i}"]
        UP[me] = NAME[f"{k}{min(i + 1, len(ramp) - 1)}"]
        DOWN[me] = NAME[f"{k}{max(i - 1, 0)}"]
# коричневый при сильном тёплом свете переходит в оранжевый
UP[NAME["B5"]] = NAME["O3"]; UP[NAME["O4"]] = NAME["O4"]
# тёплый свет «окрашивает» серые и зелёные в коричневые того же уровня
for i in range(7):
    WARM[NAME[f"K{i}"]] = NAME[f"B{min(i, 5)}"]
for i in range(6):
    WARM[NAME[f"N{i}"]] = NAME[f"B{i}"] if i < 2 else NAME[f"N{i}"]
COLD = np.arange(len(PAL))  # лунный свет — в серо-зелёные
for i in range(6):
    COLD[NAME[f"B{i}"]] = NAME[f"K{min(i + 1, 6)}"]

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16
BT = np.tile(BAYER, (H // 4, W // 4))
YY, XX = np.mgrid[0:H, 0:W]


def c(name):
    return P[name]


class Canvas:
    def __init__(self, fill="K0", transparent=False):
        self.a = np.full((H, W), -1 if transparent else P[fill], np.int16)

    # ---------- маски
    @staticmethod
    def _mask(draw_fn):
        m = Image.new("L", (W, H), 0)
        draw_fn(ImageDraw.Draw(m))
        return np.asarray(m) > 0

    def poly(self, pts, col):
        m = self._mask(lambda d: d.polygon([tuple(map(round, p)) for p in pts], fill=255))
        self.a[m] = P[col]; return m

    def rect(self, x0, y0, x1, y1, col):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1)))
        self.a[max(0, y0):max(0, y1 + 1), max(0, x0):max(0, x1 + 1)] = P[col]

    def ell(self, cx, cy, rx, ry, col):
        m = (((XX - cx) / (rx + 0.5)) ** 2 + ((YY - cy) / (ry + 0.5)) ** 2) <= 1
        self.a[m] = P[col]; return m

    def line(self, pts, col, w=1):
        m = self._mask(lambda d: d.line([tuple(map(round, p)) for p in pts], fill=255, width=w))
        self.a[m] = P[col]; return m

    def px(self, x, y, col):
        if 0 <= x < W and 0 <= y < H:
            self.a[int(y), int(x)] = P[col]

    # ---------- заливки с дизерингом
    def vgrad(self, x0, y0, x1, y1, cols, where=None):
        h = max(1, y1 - y0)
        v = np.clip((YY - y0) / h, 0, 1) * (len(cols) - 1)
        i = np.floor(v).astype(int); f = v - i
        i2 = np.minimum(i + np.where(f > BT, 1, 0), len(cols) - 1)
        idx = np.array([P[c_] for c_ in cols])[i2]
        m = (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)
        if where is not None:
            m &= where
        self.a[m] = idx[m]

    def dither(self, mask, col, density):
        """Заполнить долю density маски цветом col (паттерн Bayer)."""
        d = density if np.ndim(density) else np.full((H, W), density)
        m = mask & (BT < d)
        self.a[m] = P[col]

    # ---------- свет и тень
    def _shift(self, amount, table, where=None):
        steps = np.floor(np.clip(amount, 0, 6) + BT - 0.5).astype(int)
        if where is not None:
            steps[~where] = 0
        solid = self.a >= 0
        for s in range(1, int(steps.max()) + 1 if steps.size else 1):
            m = (steps >= s) & solid
            self.a[m] = table[self.a[m]]

    def light(self, cx, cy, r, strength=2.0, warm=True, where=None, ry=None):
        ry = ry or r
        d = np.sqrt(((XX - cx) / r) ** 2 + ((YY - cy) / ry) ** 2)
        amt = strength * np.clip(1 - d, 0, 1)
        solid = self.a >= 0
        if warm:
            m = (amt / max(strength, 1e-6) > BT * 0.7 + 0.15) & solid
            if where is not None:
                m &= where
            self.a[m] = WARM[self.a[m]]
        self._shift(amt, UP, where)

    def moon(self, mask, strength=1.0):
        solid = (self.a >= 0) & mask
        self.a[solid] = COLD[self.a[solid]]
        self._shift(np.full((H, W), strength), UP, mask)

    def shade(self, amount, where=None):
        self._shift(amount if np.ndim(amount) else np.full((H, W), amount), DOWN, where)

    def vignette(self, strength=2.2, power=2.0):
        d = np.sqrt(((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)
        self.shade(strength * np.clip(d - 0.55, 0, None) ** power * 2)

    # ---------- слои
    def paste(self, layer, outline="K0"):
        m = layer.a >= 0
        if outline:
            o = np.zeros_like(m)
            o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
            self.a[o & ~m] = P[outline]
        self.a[m] = layer.a[m]

    def save(self, path):
        img = Image.fromarray(PAL_ARR[np.clip(self.a, 0, None)], "RGB")
        img.resize((W * SCALE, H * SCALE), Image.NEAREST).save(path)
        return img


def rng(seed):
    return np.random.default_rng(seed)


# =================================================================== персонажи
K = 1.6  # единый масштаб персонажей во всех кадрах


def survivor_back(x, y, k=K):
    """Главный герой со спины: зелёная парка с капюшоном, рюкзак, красный шарф."""
    L = Canvas(transparent=True)
    L.rect(x - 7 * k, y - 4 * k, x - 2 * k, y, "K1"); L.rect(x + 2 * k, y - 4 * k, x + 7 * k, y, "K1")
    L.rect(x - 6 * k, y - 24 * k, x - 2 * k, y - 5 * k, "K3"); L.rect(x + 2 * k, y - 24 * k, x + 6 * k, y - 5 * k, "K3")
    L.rect(x - 6 * k, y - 14 * k, x - 2 * k, y - 13 * k, "K2"); L.rect(x + 2 * k, y - 11 * k, x + 6 * k, y - 10 * k, "K2")  # складки
    L.poly([(x - 10 * k, y - 50 * k), (x + 10 * k, y - 50 * k), (x + 11 * k, y - 22 * k), (x + 9 * k, y - 18 * k), (x - 9 * k, y - 18 * k), (x - 11 * k, y - 22 * k)], "N2")
    for sg in (-1, 1):
        L.poly([(x + 10 * k * sg, y - 49 * k), (x + 13 * k * sg, y - 46 * k), (x + 14 * k * sg, y - 28 * k), (x + 11 * k * sg, y - 27 * k), (x + 9 * k * sg, y - 40 * k)], "N2")
        L.rect(x + 11 * k * sg, y - 28 * k, x + 14 * k * sg, y - 24 * k, "K1")
    L.rect(x - 9 * k, y - 23 * k, x + 9 * k, y - 22 * k, "N1")  # пояс парки
    L.rect(x - 7 * k, y - 47 * k, x + 7 * k, y - 27 * k, "B2"); L.rect(x - 7 * k, y - 48 * k, x + 7 * k, y - 41 * k, "B3")
    L.rect(x - 5 * k, y - 36 * k, x + 5 * k, y - 29 * k, "B1"); L.rect(x - 1 * k, y - 41 * k, x + 1 * k, y - 39 * k, "K4")
    L.rect(x - 9 * k, y - 53 * k, x + 9 * k, y - 49 * k, "N1")
    for i in range(-8, 9, 4):
        L.rect(x + i * k, y - 53 * k, x + i * k, y - 49 * k, "N0")
    L.ell(x, y - 58 * k, 6 * k, 7 * k, "N2"); L.rect(x - 6 * k, y - 52 * k, x + 6 * k, y - 50 * k, "R2")
    L.poly([(x + 3 * k, y - 50 * k), (x + 6 * k, y - 50 * k), (x + 7 * k, y - 41 * k), (x + 5 * k, y - 42 * k)], "R1")
    L.shade(1.0, where=(XX < x - 3 * k) & (L.a >= 0))
    L.shade(0.6, where=(XX < x + 1 * k) & (XX >= x - 3 * k) & (L.a >= 0))
    return L


def survivor_crouch(x, y, k=K):
    """Герой в профиль, присел, в противогазе, с трубой в руке (смотрит вправо)."""
    L = Canvas(transparent=True)
    L.poly([(x - 5 * k, y - 16 * k), (x - 1 * k, y - 12 * k), (x - 5 * k, y - 2 * k), (x - 10 * k, y - 2 * k)], "K3")
    L.rect(x - 12 * k, y - 3 * k, x - 5 * k, y, "K1")
    L.poly([(x - 4 * k, y - 18 * k), (x + 8 * k, y - 22 * k), (x + 11 * k, y - 18 * k), (x + 10 * k, y - 3 * k), (x + 5 * k, y - 3 * k), (x + 5 * k, y - 15 * k), (x - 2 * k, y - 11 * k)], "K3")
    L.rect(x + 4 * k, y - 3 * k, x + 12 * k, y, "K1")
    L.poly([(x - 13 * k, y - 37 * k), (x - 6 * k, y - 38 * k), (x - 4 * k, y - 19 * k), (x - 13 * k, y - 19 * k)], "B2")
    L.rect(x - 13 * k, y - 38 * k, x - 6 * k, y - 33 * k, "B3")
    L.poly([(x - 7 * k, y - 37 * k), (x + 2 * k, y - 39 * k), (x + 5 * k, y - 20 * k), (x - 6 * k, y - 14 * k)], "N2")
    L.ell(x + 3 * k, y - 44 * k, 5 * k, 6 * k, "N2")
    L.ell(x + 7 * k, y - 43 * k, 3 * k, 4 * k, "K3"); L.ell(x + 9 * k, y - 39 * k, 2 * k, 2 * k, "K4")
    L.px(x + 7 * k, y - 45 * k, "O2"); L.px(x + 8 * k, y - 45 * k, "O1")
    L.rect(x - 2 * k, y - 38 * k, x + 5 * k, y - 37 * k, "R2")
    L.line([(x + 14 * k, y - 50 * k), (x + 9 * k, y - 21 * k)], "K4", max(1, round(2 * k))); L.line([(x + 14 * k, y - 50 * k), (x + 13 * k, y - 44 * k)], "K5", max(1, round(1 * k)))
    L.line([(x, y - 34 * k), (x + 10 * k, y - 28 * k)], "N2", max(1, round(3 * k))); L.rect(x + 9 * k, y - 30 * k, x + 12 * k, y - 26 * k, "K1")
    L.shade(1.0, where=(XX < x - 1 * k) & (L.a >= 0))
    return L


def survivor_sit(x, y, k=K):
    """Герой сидит на полу у стены, колени подняты, лицом вправо."""
    L = Canvas(transparent=True)
    L.poly([(x - 2 * k, y - 6 * k), (x + 10 * k, y - 18 * k), (x + 13 * k, y - 15 * k), (x + 3 * k, y)], "K3")
    L.poly([(x + 10 * k, y - 18 * k), (x + 14 * k, y - 17 * k), (x + 15 * k, y - 1 * k), (x + 11 * k, y - 1 * k)], "K3")
    L.rect(x + 11 * k, y - 3 * k, x + 19 * k, y, "K1")
    L.poly([(x - 7 * k, y - 31 * k), (x + 2 * k, y - 32 * k), (x + 4 * k, y - 2 * k), (x - 7 * k, y - 2 * k)], "N2")
    L.rect(x - 7 * k, y - 3 * k, x + 3 * k, y, "N1")
    L.ell(x - 1 * k, y - 37 * k, 5 * k, 6 * k, "N2")
    L.ell(x + 3 * k, y - 36 * k, 3 * k, 4 * k, "K3"); L.ell(x + 5 * k, y - 32 * k, 2 * k, 2 * k, "K4")
    L.px(x + 3 * k, y - 38 * k, "O2"); L.px(x + 4 * k, y - 38 * k, "O1")
    L.rect(x - 5 * k, y - 32 * k, x + 3 * k, y - 31 * k, "R2")
    L.line([(x, y - 27 * k), (x + 11 * k, y - 19 * k)], "N2", max(1, round(3 * k))); L.rect(x + 10 * k, y - 21 * k, x + 13 * k, y - 18 * k, "K1")
    L.shade(1.0, where=(XX < x - 2 * k) & (L.a >= 0))
    return L


def infected(x, y, eyes=True, k=K):
    """Заражённый: сутулый, рваная одежда, серо-зелёная кожа, тусклые красные глаза."""
    L = Canvas(transparent=True)
    L.rect(x - 7 * k, y - 3 * k, x - 3 * k, y, "K3"); L.rect(x + 3 * k, y - 3 * k, x + 8 * k, y, "K3")
    L.poly([(x - 7 * k, y - 24 * k), (x - 1 * k, y - 24 * k), (x - 2 * k, y - 3 * k), (x - 7 * k, y - 3 * k)], "B1")
    L.poly([(x + 1 * k, y - 24 * k), (x + 7 * k, y - 24 * k), (x + 8 * k, y - 3 * k), (x + 3 * k, y - 3 * k)], "B1")
    L.rect(x - 7 * k, y - 8 * k, x - 4 * k, y - 6 * k, "N3")  # дыра в штанине
    L.poly([(x - 10 * k, y - 46 * k), (x + 8 * k, y - 48 * k), (x + 10 * k, y - 22 * k), (x + 4 * k, y - 20 * k), (x + 1 * k, y - 23 * k), (x - 4 * k, y - 20 * k), (x - 9 * k, y - 23 * k)], "B2")
    L.rect(x - 3 * k, y - 38 * k, x + 1 * k, y - 35 * k, "N3"); L.rect(x + 3 * k, y - 30 * k, x + 6 * k, y - 28 * k, "R1")
    L.poly([(x - 10 * k, y - 45 * k), (x - 14 * k, y - 38 * k), (x - 15 * k, y - 16 * k), (x - 12 * k, y - 15 * k), (x - 11 * k, y - 36 * k)], "N3")
    L.poly([(x + 8 * k, y - 47 * k), (x + 13 * k, y - 40 * k), (x + 14 * k, y - 18 * k), (x + 11 * k, y - 17 * k), (x + 10 * k, y - 38 * k)], "N3")
    for fx in (-15, -13, 12, 14):
        L.rect(x + fx * k, y - 15 * k, x + fx * k, y - 12 * k, "N3")
    L.ell(x - 3 * k, y - 52 * k, 6 * k, 6 * k, "N4"); L.rect(x - 7 * k, y - 49 * k, x + 1 * k, y - 47 * k, "N3")
    L.rect(x - 5 * k, y - 47 * k, x - 1 * k, y - 46 * k, "R0")
    if eyes:
        L.px(x - 6 * k, y - 53 * k, "R3"); L.px(x - 1 * k, y - 53 * k, "R3")
    L.shade(1.0, where=(XX < x) & (L.a >= 0))
    return L
