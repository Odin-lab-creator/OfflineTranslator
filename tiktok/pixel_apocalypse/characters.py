"""Детальные спрайты персонажей PIXEL APOCALYPSE v2.

Спрайт собирается из частей тела/одежды (полигоны на сетке пикселей). Каждый материал —
рампа из 4 тонов: тон выбирается по положению пикселя поперёк формы (свет спереди-справа),
затем выборочный контур (тёмный тон на стыке с деталью «поверх»), внешний чёрный контур
и ручные детали (глаза, складки, молния, шнурки).
"""
import numpy as np
from PIL import Image, ImageDraw

from pixel2 import col

RAMPS = {
    "skin": ["S0", "S1", "S2", "S3"], "hair": ["H0", "H0", "H1", "H2"],
    "jacket": ["R1", "R2", "R3", "R4"], "sleeve": ["R1", "R2", "R3", "R4"], "cuff": ["R0", "R1", "R2", "R3"],
    "pack": ["M0", "M1", "M2", "M3"], "roll": ["G2", "G3", "G4", "G6"],
    "strap": ["B0", "B1", "B2", "B3"], "boots": ["B0", "B1", "B2", "B3"],
    "pants": ["P0", "P1", "P2", "P3"], "glove": ["H0", "H1", "H2", "B3"],
    "metal": ["G5", "G6", "G8", "E2"], "pipe": ["G1", "G4", "E0", "E1"],
    "sole": ["G0", "G1", "G1", "G2"],
    "zskin": ["Z0", "Z1", "Z2", "Z3"], "zfar": ["G3", "Z0", "Z1", "Z2"],
    "rag": ["G2", "G3", "E0", "E1"], "zpants": ["P0", "P0", "P1", "P2"],
    "zhair": ["G0", "G1", "G2", "G3"], "blood": ["R0", "R1", "R2", "R3"],
    "mouth": ["G0", "R0", "R0", "R1"],
}


def shift(a, dy, dx, fill):
    out = np.full_like(a, fill)
    h, w = a.shape
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = a[ys, xs]
    return out


class SpriteBuilder:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.mat = np.full((h, w), "", object)
        self.z = np.zeros((h, w), int)
        self.tone = np.zeros((h, w), int)
        self.over = {}       # ручные пиксели: (x, y) -> имя цвета
        self.emis = set()
        self.folds = []      # (mask, tone)
        self.k = 0

    def _mask(self, fn):
        m = Image.new("L", (self.w, self.h), 0)
        fn(ImageDraw.Draw(m))
        return np.asarray(m) > 0

    def _put(self, m, mat):
        self.k += 1
        self.mat[m] = mat; self.z[m] = self.k
        return m

    def poly(self, pts, mat):
        return self._put(self._mask(lambda d: d.polygon(pts, fill=255)), mat)

    def ell(self, cx, cy, rx, ry, mat):
        return self._put(self._mask(lambda d: d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)), mat)

    def rect(self, x0, y0, x1, y1, mat):
        return self._put(self._mask(lambda d: d.rectangle((x0, y0, x1, y1), fill=255)), mat)

    def line(self, pts, mat, w=1):
        return self._put(self._mask(lambda d: d.line(pts, fill=255, width=w)), mat)

    def fold(self, pts, tone=0):
        self.folds.append((self._mask(lambda d: d.line(pts, fill=255)), tone))

    def px(self, x, y, c, emissive=False):
        self.over[(x, y)] = c
        if emissive:
            self.emis.add((x, y))

    def build(self, light=1):
        m, h, w = self.mat, self.h, self.w
        # 1) тон по положению поперёк формы (свет справа при light=1)
        for y in range(h):
            x = 0
            while x < w:
                if m[y, x] == "":
                    x += 1; continue
                x2 = x
                while x2 + 1 < w and m[y, x2 + 1] == m[y, x]:
                    x2 += 1
                n = x2 - x + 1
                for i in range(n):
                    r = (i + 0.5) / n if light > 0 else 1 - (i + 0.5) / n
                    t = 3 if r > 0.74 else 2 if r > 0.3 else 1
                    if n >= 6 and r < 0.12:
                        t = 0
                    if n <= 2:
                        t = 2
                    self.tone[y, x + i] = t
                x = x2 + 1
        # верх формы чуть светлее (свет сверху)
        for y in range(1, h):
            same = (m[y] != "") & (m[y - 1] != m[y])
            self.tone[y][same] = np.minimum(self.tone[y][same] + 1, 3)
        # 2) складки
        for fm, t in self.folds:
            fm = fm & (m != "")
            self.tone[fm] = t
        # 3) выборочный контур: стык с деталью, лежащей поверх
        solid = m != ""
        edge = np.zeros_like(solid)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nm = shift(m, dy, dx, "")
            nz = shift(self.z, dy, dx, 0)
            edge |= solid & (nm != "") & (nm != m) & (nz > self.z)
        self.tone[edge] = 0
        # 4) цвет
        rgb = np.zeros((h, w, 3), np.float32)
        for y in range(h):
            for x in range(w):
                if solid[y, x]:
                    rgb[y, x] = col(RAMPS[m[y, x]][self.tone[y, x]])
        for (x, y), c in self.over.items():
            rgb[y, x] = col(c); solid[y, x] = True
        # 5) внешний контур
        out = np.zeros_like(solid)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            out |= shift(solid, dy, dx, False)
        out &= ~solid
        rgb[out] = col("G0")
        alpha = solid | out
        emis = np.zeros_like(solid)
        for (x, y) in self.emis:
            emis[y, x] = True
        return rgb, alpha, emis


# ===================================================================== ГЕРОЙ
def _hero_head(b, dx=0, dy=0):
    P = lambda pts: [(x + dx, y + dy) for x, y in pts]
    b.poly(P([(23, 6), (29, 4), (33, 7), (34, 10), (36, 13), (34, 14), (34, 16), (33, 17), (34, 19),
              (31, 21), (28, 22), (24, 21), (21, 16), (21, 9)]), "skin")
    b.poly(P([(19, 7), (22, 2), (28, 0), (33, 2), (35, 6), (33, 7), (30, 6), (27, 8), (25, 10),
              (24, 14), (22, 18), (20, 17), (18, 12)]), "hair")
    b.ell(24 + dx, 13 + dy, 2, 3, "skin")
    # лицо: бровь, глаз, нос, рот, щетина
    for x in (30, 31, 32):
        b.px(x + dx, 9 + dy, "H0")
    b.px(31 + dx, 11 + dy, "G0"); b.px(32 + dx, 11 + dy, "E1"); b.px(31 + dx, 12 + dy, "S1")
    b.px(34 + dx, 15 + dy, "S0"); b.px(32 + dx, 18 + dy, "S0"); b.px(33 + dx, 18 + dy, "S1")
    for x, y in ((26, 19), (28, 20), (30, 20), (27, 21), (29, 19), (31, 19), (25, 17)):
        b.px(x + dx, y + dy, "H1")
    b.px(23 + dx, 13 + dy, "S0")
    b.rect(24 + dx, 20 + dy, 29 + dx, 25 + dy, "skin")


def _hero_torso(b, dx=0, dy=0, backpack=True):
    P = lambda pts: [(x + dx, y + dy) for x, y in pts]
    if backpack:
        b.poly(P([(6, 27), (17, 25), (18, 56), (9, 58), (5, 50)]), "pack")
        b.ell(11 + dx, 24 + dy, 7, 4, "roll")
        b.fold(P([(6, 35), (17, 33)]), 0)
        b.fold(P([(8, 44), (15, 43)]), 1)
        b.px(12 + dx, 35 + dy, "E1"); b.px(12 + dx, 36 + dy, "G6")
    b.poly(P([(16, 27), (33, 26), (35, 33), (35, 50), (34, 60), (17, 60), (16, 48), (15, 34)]), "jacket")
    b.poly(P([(21, 22), (30, 22), (32, 28), (20, 29)]), "jacket")
    b.fold(P([(21, 28), (31, 27)]), 0)
    b.line(P([(34, 29), (35, 59)]), "metal")
    b.poly(P([(18, 45), (24, 45), (24, 53), (18, 53)]), "jacket")
    b.fold(P([(18, 47), (24, 47)]), 0)
    b.fold(P([(19, 36), (21, 42)]), 1)
    if backpack:
        b.poly(P([(23, 26), (26, 26), (29, 46), (26, 47)]), "strap")
        b.px(27 + dx, 40 + dy, "E1")
    b.rect(16 + dx, 60 + dy, 34 + dx, 62 + dy, "strap")
    b.rect(31 + dx, 60 + dy, 34 + dx, 62 + dy, "metal")
    b.rect(13 + dx, 60 + dy, 18 + dx, 70 + dy, "strap")


def _hero_arm_down(b, dx=0, dy=0):
    P = lambda pts: [(x + dx, y + dy) for x, y in pts]
    b.poly(P([(24, 28), (31, 27), (32, 43), (25, 44)]), "sleeve")
    b.poly(P([(25, 43), (32, 42), (33, 55), (27, 56)]), "sleeve")
    b.fold(P([(26, 44), (31, 43)]), 0)
    b.fold(P([(28, 48), (30, 50)]), 1)
    b.rect(27 + dx, 54 + dy, 33 + dx, 57 + dy, "cuff")
    b.ell(30 + dx, 60 + dy, 3, 4, "glove")
    b.px(33 + dx, 61 + dy, "H1")


def _hero_legs(b):
    b.poly([(17, 63), (25, 63), (24, 82), (23, 98), (17, 98), (17, 82)], "pants")
    b.poly([(24, 63), (34, 63), (34, 80), (33, 98), (26, 98), (26, 80)], "pants")
    b.rect(29, 75, 34, 82, "strap")
    b.poly([(18, 68), (22, 68), (22, 76), (18, 76)], "pants")
    b.fold([(18, 70), (22, 70)], 0)
    b.fold([(27, 86), (31, 87)], 1); b.fold([(18, 85), (21, 86)], 1)
    b.fold([(27, 66), (29, 72)], 1)
    b.poly([(16, 96), (24, 96), (25, 104), (14, 104)], "boots")
    b.poly([(26, 96), (33, 96), (38, 101), (38, 104), (26, 104)], "boots")
    b.rect(13, 104, 39, 105, "sole")
    for x, y in ((29, 98), (31, 99), (33, 100)):
        b.px(x, y, "E1")


def hero_stand(pipe=False):
    b = SpriteBuilder(52, 106)
    _hero_legs(b)
    _hero_torso(b)
    _hero_head(b)
    if pipe:
        b.poly([(24, 28), (31, 27), (32, 43), (25, 44)], "sleeve")
        b.line([(37, 60), (45, 8)], "pipe", 2)
        b.poly([(25, 43), (31, 40), (38, 34), (41, 38), (33, 47), (27, 48)], "sleeve")
        b.fold([(26, 44), (30, 42)], 0)
        b.rect(36, 34, 40, 39, "cuff")
        b.ell(41, 37, 3, 3, "glove")
    else:
        _hero_arm_down(b)
    return b.build()


def hero_sit():
    b = SpriteBuilder(62, 76)
    dy = -30  # поднимаем верх так, чтобы таз был у пола
    b.poly([(16, 66 + 0), (30, 58), (46, 44), (52, 48), (37, 66), (30, 72), (16, 72)], "pants")
    b.poly([(46, 46), (52, 46), (54, 68), (48, 68)], "pants")
    b.rect(48, 52, 54, 58, "strap")
    b.fold([(36, 56), (42, 52)], 1)
    b.poly([(46, 66), (55, 66), (60, 71), (60, 74), (46, 74)], "boots")
    b.rect(45, 74, 61, 75, "sole")
    b.px(50, 68, "E1"); b.px(52, 69, "E1")
    # торс и голова (без рюкзака — он снят), сдвинуты вниз на 4 и влево на 2
    P = lambda pts: [(x - 2, y + 4) for x, y in pts]
    b.poly(P([(16, 27), (33, 26), (35, 33), (35, 50), (34, 62), (17, 64), (16, 48), (15, 34)]), "jacket")
    b.poly(P([(21, 22), (30, 22), (32, 28), (20, 29)]), "jacket")
    b.fold(P([(21, 28), (31, 27)]), 0)
    b.line(P([(34, 29), (35, 60)]), "metal")
    b.fold(P([(19, 36), (21, 42)]), 1)
    b.rect(14, 64, 32, 66, "strap"); b.rect(29, 64, 32, 66, "metal")
    _hero_head(b, dx=-2, dy=4)
    # рука лежит на колене
    b.poly(P([(24, 28), (31, 27), (32, 43), (25, 44)]), "sleeve")
    b.poly([(24, 44), (30, 42), (45, 43), (45, 49), (27, 50)], "sleeve")
    b.fold([(25, 46), (29, 44)], 0)
    b.rect(41, 43, 45, 49, "cuff")
    b.ell(48, 45, 3, 3, "glove")
    return b.build()


# ================================================================ ЗАРАЖЁННЫЙ
def zombie():
    b = SpriteBuilder(58, 106)
    # дальняя рука — за телом
    b.poly([(30, 30), (36, 29), (47, 42), (44, 46)], "zfar")
    b.poly([(44, 42), (47, 41), (53, 52), (50, 54)], "zfar")
    # ноги
    b.poly([(18, 62), (26, 62), (24, 82), (22, 97), (16, 97), (17, 80)], "zpants")
    b.poly([(25, 62), (34, 60), (38, 78), (36, 97), (29, 97), (30, 80)], "zpants")
    b.fold([(31, 70), (34, 74)], 0); b.fold([(19, 80), (22, 83)], 1)
    b.ell(33, 86, 2, 3, "zskin")  # дыра на колене
    b.poly([(14, 96), (23, 96), (24, 104), (12, 104)], "zskin")
    b.poly([(29, 96), (37, 96), (42, 101), (42, 104), (29, 104)], "zskin")
    b.rect(11, 104, 43, 105, "sole")
    for x in (38, 40):
        b.px(x, 102, "Z0")
    # сгорбленный торс в рваной рубахе: горб сзади, плечи вперёд
    b.poly([(12, 34), (18, 24), (28, 22), (38, 28), (40, 40), (37, 50), (36, 62), (31, 59), (27, 64),
            (22, 60), (17, 64), (14, 52)], "rag")
    b.poly([(20, 38), (23, 37), (24, 41), (21, 43)], "zskin")
    b.poly([(28, 51), (31, 50), (32, 54), (29, 55), (28, 53)], "zskin")
    b.poly([(32, 33), (37, 34), (37, 42), (34, 47), (32, 41)], "blood")
    b.line([(35, 45), (35, 52)], "blood")
    b.fold([(16, 32), (20, 46)], 1); b.fold([(26, 28), (28, 40)], 1); b.fold([(22, 50), (26, 56)], 1)
    # шея и голова вытянуты вперёд и опущены ниже плеч
    b.poly([(33, 26), (38, 25), (41, 33), (35, 34)], "zskin")
    D = lambda pts: [(x + 5, y + 10) for x, y in pts]
    b.poly(D([(30, 14), (36, 12), (42, 15), (44, 20), (43, 24), (41, 27), (36, 28), (32, 26), (30, 21)]), "zskin")
    b.poly(D([(29, 14), (34, 9), (40, 10), (43, 14), (37, 14), (33, 17), (31, 21)]), "zhair")
    b.ell(44, 28, 2, 1, "mouth")
    b.px(45, 28, "R4", emissive=True); b.px(44, 28, "R3", emissive=True)
    b.poly(D([(38, 23), (43, 23), (42, 26), (38, 25)]), "mouth")
    b.px(44, 33, "E1"); b.px(46, 33, "E1"); b.px(45, 36, "E0")
    b.px(38, 30, "Z0"); b.px(40, 34, "Z0"); b.px(48, 31, "Z0")
    # ближняя рука тянется вперёд
    b.poly([(28, 28), (36, 27), (44, 40), (39, 44)], "rag")
    b.poly([(37, 40), (43, 38), (52, 49), (48, 53)], "zskin")
    b.fold([(40, 44), (44, 46)], 1)
    for (x0, y0, x1, y1) in ((49, 52, 54, 58), (51, 51, 56, 56), (48, 53, 50, 59)):
        b.line([(x0, y0), (x1, y1)], "zskin")
    b.ell(41, 46, 1, 1, "blood")
    return b.build()


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames_v2", "characters_sheet.png")
    sprites = [hero_stand(), hero_stand(pipe=True), hero_sit(), zombie()]
    Wd = sum(s[1].shape[1] for s in sprites) + 10 * (len(sprites) + 1)
    Hd = max(s[1].shape[0] for s in sprites) + 20
    sheet = np.zeros((Hd, Wd, 3), np.uint8) + np.array([46, 60, 50], np.uint8)
    x = 10
    for rgb, a, _ in sprites:
        h, w = a.shape
        y0 = Hd - 10 - h
        sheet[y0:y0 + h, x:x + w][a] = rgb[a].astype(np.uint8)
        x += w + 10
    Image.fromarray(sheet).resize((Wd * 6, Hd * 6), Image.NEAREST).save(out)
    print(out)
