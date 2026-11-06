# 5 yellowed index cards with illegible handwriting, stacked vertically in one image (512 x 1280)
from PIL import Image, ImageDraw, ImageFilter
import random, math, numpy as np
W, H = 512, 256
im = Image.new("RGB", (W, H * 5)); d = ImageDraw.Draw(im)
for k in range(5):
    rnd = random.Random(40 + k)
    y0 = k * H
    base = (int(206 - rnd.random() * 20), int(196 - rnd.random() * 20), int(160 - rnd.random() * 25))
    d.rectangle([0, y0, W, y0 + H], fill=base)
    for yy in (y0 + 80, y0 + 150, y0 + 220):
        d.line([20, yy, W - 20, yy], fill=(170, 160, 150), width=2)
    ink = rnd.choice([(40, 45, 90), (35, 35, 40), (90, 35, 35)])
    for line in range(rnd.randint(1, 2)):
        x = 40; yb = y0 + 70 + line * 70
        while x < rnd.randint(250, 460):
            wl = rnd.randint(40, 110)
            pts = [(x + t, yb - 10 - 22 * abs(math.sin(t * 0.21 + rnd.random() * 3)) * rnd.uniform(0.4, 1)) for t in range(0, wl, 3)]
            d.line(pts, fill=ink, width=5); x += wl + rnd.randint(14, 28)
    if k == 2:                                   # torn/missing corner, tape
        d.polygon([(W - 120, y0), (W, y0), (W, y0 + 90)], fill=(60, 60, 58))
    if k == 4:
        d.rectangle([0, y0, W, y0 + H], fill=(150, 145, 128))     # faded, almost blank card
        d.line([(60, y0 + 120), (300, y0 + 110)], fill=(120, 110, 100), width=5)
im = im.filter(ImageFilter.GaussianBlur(1.2))
a = np.array(im, np.float32)
rng = np.random.default_rng(1)
a *= (0.92 + 0.08 * rng.random(a.shape[:2]))[..., None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save("labels/labels.png")
print("ok")
