"""frames_src/ (картинки как пришли из Flow) → frames/ (для сборки).
Flow пишет на письмах читаемую «рыбу» (Lorem ipsum, Sincerely…). Размываем её вдоль строк:
остаются серые «напечатанные» полоски, читать нечего. Остальные кадры копируются без изменений.
python3 fix_frames.py [--check]  (--check: сохранить крупные фрагменты до/после в /tmp-папку проверки)
"""
import os
import shutil
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, DST = os.path.join(HERE, "frames_src"), os.path.join(HERE, "frames")

# кадр: (x0, y0, x1, y1 — где лежит письмо, угол строк в градусах (+ = вверх вправо), длина мазка[, контур листа])
LETTERS = {
    "09":  (30, 390, 650, 1025, 16, 21),
    "09b": (40, 380, 500, 990, 0, 21),
    "14":  (40, 380, 465, 990, 0, 21),
    "40":  (40, 380, 465, 990, 0, 21),
    "15":  (225, 610, 415, 750, 4, 11),
    "39":  (95, 605, 415, 730, 4, 13),
    "20":  (25, 650, 260, 840, -8, 11, [(36, 668), (172, 678), (246, 830), (100, 819)]),
}


def line_kernel(length, angle):
    k = np.zeros((length, length), np.float32)
    c = length // 2
    a = np.deg2rad(angle)
    dx, dy = np.cos(a), -np.sin(a)
    for t in np.linspace(-c, c, length * 3):
        k[int(round(c + t * dy)), int(round(c + t * dx))] = 1
    return k / k.sum()


def smear(img, box):
    x0, y0, x1, y1, angle, length = box[:6]
    roi = img[y0:y1, x0:x1].astype(np.float32)
    hsv = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    paper = ((hsv[..., 2] > 120) & (hsv[..., 1] < 90)).astype(np.uint8)
    # бумага + буквы внутри неё: закрываем дырки от строк
    closed = cv2.morphologyEx(paper, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(closed)
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))  # только сам лист, без конверта рядом
    mask = (lab == big).astype(np.uint8)
    # крупные тёмные пятна (тени, пламя) не трогаем — размываем только тонкие строки
    dark = (hsv[..., 2] < 110).astype(np.uint8)
    blobs = cv2.dilate(cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)), np.ones((9, 9), np.uint8))
    mask[blobs > 0] = 0
    if len(box) > 6:  # лист рядом со светлой одеждой: ограничиваем контуром
        poly = np.zeros_like(mask)
        cv2.fillPoly(poly, [np.array(box[6], np.int32) - [x0, y0]], 1)
        mask &= poly
    mask = cv2.erode(mask, np.ones((7, 7), np.uint8)).astype(np.float32)
    k = line_kernel(length, angle)
    m3 = mask[..., None]
    num = cv2.filter2D(roi * m3, -1, k)
    den = cv2.filter2D(mask, -1, k)[..., None]
    blurred = num / np.maximum(den, 1e-3)
    # лёгкое вертикальное смягчение, чтобы штрихи букв не проступали
    blurred = cv2.GaussianBlur(blurred, (0, 0), 0.8)
    out = roi * (1 - m3) + blurred * m3
    img[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)
    return img


if __name__ == "__main__":
    os.makedirs(DST, exist_ok=True)
    check = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--check" else None
    for name in sorted(os.listdir(SRC)):
        stem = name.rsplit(".", 1)[0]
        src, dst = os.path.join(SRC, name), os.path.join(DST, name)
        if stem in LETTERS:
            img = smear(cv2.imread(src), LETTERS[stem])
            cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            shutil.copyfile(src, dst)
    # нет картинки 06 («трое детей, комната для каждого») — берём детей из кадра 13 крупно, без Наблюдателя слева
    if not os.path.exists(os.path.join(SRC, "06.jpg")):
        im = cv2.imread(os.path.join(SRC, "13.jpg"))[230:998, 336:768]
        cv2.imwrite(os.path.join(DST, "06.jpg"), cv2.resize(im, (768, 1365), interpolation=cv2.INTER_LANCZOS4),
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
    if "--check" in sys.argv:
        out = sys.argv[sys.argv.index("--check") + 1]
        os.makedirs(out, exist_ok=True)
        for stem, (x0, y0, x1, y1, *_r) in LETTERS.items():  # noqa
            a = cv2.imread(os.path.join(SRC, stem + ".jpg"))[y0:y1, x0:x1]
            b = cv2.imread(os.path.join(DST, stem + ".jpg"))[y0:y1, x0:x1]
            cv2.imwrite(os.path.join(out, stem + ".png"), np.hstack([a, b]))
    print(len(os.listdir(DST)), "кадров в frames/, письма размыты:", ", ".join(LETTERS))
