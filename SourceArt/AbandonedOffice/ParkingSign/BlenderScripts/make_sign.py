"""Blue 'P' parking sign face (1024x1024), faded and scratched."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
N = 1024
rng = np.random.default_rng(5)
im = Image.new("RGB", (N, N), (238, 238, 236)); d = ImageDraw.Draw(im)
d.rounded_rectangle([0, 0, N - 1, N - 1], radius=60, fill=(238, 238, 236))          # white border
d.rounded_rectangle([34, 34, N - 35, N - 35], radius=40, fill=(18, 82, 160))       # blue field
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 820)
layer = Image.new("L", (N, N), 0); ld = ImageDraw.Draw(layer)
ld.text((N / 2, N / 2 + 20), "P", font=F, fill=255, anchor="mm")
im.paste((238, 238, 236), (0, 0), layer)
a = np.asarray(im, np.float32) / 255
def fbm(scale, octv=5):
    out = np.zeros((N, N), np.float32); amp = 1
    for o in range(octv):
        n = scale * 2 ** o
        g = rng.random((n, n)).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(g).resize((N, N), Image.BICUBIC)); amp *= 0.5
    out -= out.min(); return out / out.max()
fade = fbm(3)
blue = (a[..., 2] > a[..., 0] + 0.2)
# sun-faded film: blue goes paler/greyer, unevenly; stronger towards the top
yy = np.linspace(1, 0, N)[:, None]
f = np.clip(0.25 + 0.45 * fade + 0.2 * yy, 0, 1)
a[blue] = a[blue] * (1 - 0.45 * f[blue, None]) + np.array([0.45, 0.55, 0.65]) * 0.45 * f[blue, None]
# scratches (thin bright lines through the film)
sc = Image.new("L", (N, N), 0); sd = ImageDraw.Draw(sc)
for _ in range(90):
    x, y = rng.uniform(0, N, 2); ang = rng.uniform(-0.6, 0.6) + (math.pi / 2 if rng.random() < 0.3 else 0)
    L = rng.uniform(30, 260)
    sd.line([x, y, x + L * math.cos(ang), y + L * math.sin(ang)], fill=int(rng.uniform(120, 255)), width=int(rng.integers(1, 3)))
scr = np.asarray(sc.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
a = a * (1 - scr[..., None] * 0.6) + scr[..., None] * 0.6 * np.array([0.72, 0.72, 0.70])
# peeling film near edges and in patches -> bare aluminium
peel = (fbm(10) > 0.82) | ((fbm(24) > 0.72) & (np.minimum.reduce([np.arange(N)[None, :].repeat(N, 0), np.arange(N)[:, None].repeat(N, 1),
        N - 1 - np.arange(N)[None, :].repeat(N, 0), N - 1 - np.arange(N)[:, None].repeat(N, 1)]) < 60))
a[peel] = np.array([0.55, 0.56, 0.57]) * (0.85 + 0.15 * fade[peel, None])
# rust from the two bolt holes + dirt streaks running down
for cy in (0.12, 0.88):
    cx, cyy = N / 2, cy * N
    yy2, xx2 = np.mgrid[0:N, 0:N]
    streak = np.exp(-((xx2 - cx) / 14) ** 2) * np.clip((yy2 - cyy) / 260, 0, 1) * np.exp(-np.clip(yy2 - cyy, 0, None) / 300)
    halo = np.exp(-((xx2 - cx) ** 2 + (yy2 - cyy) ** 2) / (2 * 22 ** 2))
    r = np.clip(streak * (0.6 + 0.4 * fbm(30, 3)) + halo, 0, 1)
    a = a * (1 - 0.7 * r[..., None]) + 0.7 * r[..., None] * np.array([0.35, 0.16, 0.06])
    yy2 = None
dirt = fbm(6)
a = a * (1 - 0.18 * dirt[..., None]) + 0.18 * dirt[..., None] * np.array([0.3, 0.28, 0.24])
# bolt holes
dd = ImageDraw.Draw(img := Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
for cy in (0.12, 0.88):
    dd.ellipse([N / 2 - 14, cy * N - 14, N / 2 + 14, cy * N + 14], fill=(60, 58, 55))
img.save("tex/sign_face.png")
print("ok")
