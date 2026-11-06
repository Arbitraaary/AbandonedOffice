"""Cooler textures (python3 + PIL + numpy): bottle RGBA (GlassUV: u around, v up the bottle) and the taped note."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
R = random.Random(11); rs = np.random.RandomState(11)
N = 1024

def fbm(n, octaves=5, seed=0, tile_u=True):
    out = np.zeros((n, n)); amp = 1.0; tot = 0
    r = np.random.RandomState(seed)
    for o in range(octaves):
        k = 4 * 2 ** o
        g = r.rand(k, k)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
        out += np.asarray(img, np.float32) / 255 * amp; tot += amp; amp *= 0.5
    return out / tot

v = np.linspace(1, 0, N)[:, None] * np.ones((1, N))          # row 0 = top of the bottle (its upturned base)
rgb = np.zeros((N, N, 3)); a = np.zeros((N, N))
rgb[:] = (0.60, 0.75, 0.86); a[:] = 0.20
n1 = fbm(N, 6, 1); n2 = fbm(N, 5, 2); n3 = fbm(N, 4, 3)
# dust settling on the upturned base and shoulders
dust = np.clip((n1 - 0.45) * 3, 0, 1) * np.clip((v - 0.55) * 2.5, 0, 1) + np.clip((n2 - 0.6) * 2.5, 0, 1) * 0.35
rgb = rgb * (1 - dust[..., None]) + np.array([0.56, 0.53, 0.48]) * dust[..., None]; a = np.maximum(a, 0.2 + 0.5 * dust)
# vertical grime streaks
st = np.zeros(N)
for _ in range(40):
    c = R.randint(0, N - 1); w = R.randint(2, 9); st[max(0, c - w):c + w] += R.uniform(0.1, 0.4)
streak = np.clip(st[None, :] * (0.4 + n3), 0, 1) * np.clip(1.2 - v, 0, 1)
rgb = rgb * (1 - 0.35 * streak[..., None]) + np.array([0.35, 0.33, 0.28]) * 0.35 * streak[..., None]; a = np.maximum(a, 0.2 + 0.25 * streak)
# dried water line + greenish film down in the neck end (the bottle stood upside down until it ran dry)
wl = 0.24 + 0.012 * np.sin(np.linspace(0, 6 * math.pi, N))[None, :] + 0.01 * (n2 - 0.5)
band = np.exp(-((v - wl) / 0.006) ** 2) * (0.6 + 0.4 * n1)
rgb = rgb * (1 - band[..., None]) + np.array([0.82, 0.8, 0.74]) * band[..., None]; a = np.maximum(a, 0.2 + 0.45 * band)
alg = np.clip((n3 - 0.5) * 3, 0, 1) * np.clip((wl - v) * 8, 0, 1)
rgb = rgb * (1 - 0.6 * alg[..., None]) + np.array([0.30, 0.38, 0.22]) * 0.6 * alg[..., None]; a = np.maximum(a, 0.2 + 0.3 * alg)
img = Image.fromarray((np.dstack([np.clip(rgb, 0, 1), np.clip(a, 0, 1)]) * 255).astype(np.uint8), "RGBA")
d = ImageDraw.Draw(img)
# torn paper label remnant
lx0, lx1, ly0, ly1 = int(0.55 * N), int(0.78 * N), int(0.40 * N), int(0.58 * N)
pts = []
for k in range(24): pts.append((lx0 + (lx1 - lx0) * k / 23, ly0 + R.uniform(-8, 22) * (1 if k % 5 else 2)))
for k in range(12): pts.append((lx1 + R.uniform(-30, 6), ly0 + (ly1 - ly0) * k / 11))
for k in range(24): pts.append((lx1 - (lx1 - lx0) * k / 23, ly1 + R.uniform(-22, 8)))
pts.append((lx0 + 4, ly1 - 30)); pts.append((lx0 + 18, ly0 + 40))
d.polygon(pts, fill=(160, 150, 126, 245))
d.rectangle([lx0, int(ly0 + (ly1 - ly0) * 0.35), lx1 - 25, int(ly0 + (ly1 - ly0) * 0.55)], fill=(92, 112, 138, 245))
for k in range(3):
    yy = int(ly0 + (ly1 - ly0) * (0.7 + 0.08 * k)); d.line([(lx0 + 30, yy), (lx0 + 30 + R.randint(60, 140), yy)], fill=(80, 78, 72, 250), width=5)
# crack with branches (whitish, stress-crazed plastic)
def crack(x, y, ang, L, w, depth=0):
    p = [(x, y)]
    for _ in range(int(L / 6)):
        ang += R.uniform(-0.35, 0.35); x += math.cos(ang) * 6; y += math.sin(ang) * 6; p.append((x, y))
        if depth < 2 and R.random() < 0.05: crack(x, y, ang + R.choice([-1, 1]) * R.uniform(0.6, 1.2), L * 0.35, max(1, w - 1), depth + 1)
    d.line(p, fill=(235, 238, 240, 235), width=w)
    d.line(p, fill=(220, 225, 230, 120), width=w + 4)
crack(0.3 * N, 0.25 * N, math.pi / 2 + 0.2, 0.42 * N, 3)
crack(0.3 * N, 0.25 * N, -math.pi / 2 + 0.3, 0.12 * N, 2)
img.save("tex/bottle.png")

# taped note: OUT OF ORDER in shaky marker capitals
note = Image.new("L", (768, 512), 255); nd = ImageDraw.Draw(note)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf", 120)
def shaky(text, x, y):
    for ch in text:
        if ch == " ": x += 45; continue
        g = Image.new("L", (160, 170), 0); ImageDraw.Draw(g).text((15, 5), ch, font=font, fill=255)
        g = g.rotate(R.uniform(-8, 8), resample=Image.BICUBIC)
        note.paste(0, (int(x), int(y + R.uniform(-8, 8))), g); x += font.getlength(ch) * R.uniform(0.92, 1.05)
shaky("OUT OF", 150, 70); shaky("ORDER", 160, 230)
nd.line([(150, 420), (600, 405)], fill=0, width=10)
note = note.filter(ImageFilter.GaussianBlur(1.4)); note.save("tex/note.png")
print("ok")
