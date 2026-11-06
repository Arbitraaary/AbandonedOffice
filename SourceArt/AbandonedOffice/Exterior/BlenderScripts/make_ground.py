"""Tileable ground textures (python3): grass 4 m, dirt 2.5 m, mask (R: dirt patches, G: macro brightness) 50 m."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
N = 2048; R = random.Random(9)
def tnoise(n, k, seed):
    r = np.random.RandomState(seed); g = r.rand(k, k)
    img = Image.fromarray((np.tile(g, (3, 3)) * 255).astype(np.uint8)).resize((n * 3, n * 3), Image.BICUBIC)
    return np.asarray(img, np.float32)[n:2 * n, n:2 * n] / 255
def fbm(n, k0, octv, seed):
    o = np.zeros((n, n)); a = 1; t = 0
    for i in range(octv): o += tnoise(n, k0 * 2 ** i, seed + i) * a; t += a; a *= 0.5
    return o / t
def nmap(h, s):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * s; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * s
    n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True); n = n * 0.5 + 0.5; n[..., 1] = 1 - n[..., 1]
    return n
def save(a, p, mode=None): Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(p)
# ---- dirt
base = fbm(N, 8, 6, 1)
dirt = np.array([0.20, 0.16, 0.11]) + (np.array([0.33, 0.27, 0.19]) - np.array([0.20, 0.16, 0.11])) * base[..., None]
peb = Image.new("L", (N, N), 0); pd = ImageDraw.Draw(peb)
for _ in range(2500):
    x, y, r = R.uniform(0, N), R.uniform(0, N), R.uniform(2, 7)
    for dx in (-N, 0, N):
        for dy in (-N, 0, N): pd.ellipse([x - r + dx, y - r + dy, x + r + dx, y + r + dy], fill=int(R.uniform(120, 255)))
pb = np.asarray(peb.filter(ImageFilter.GaussianBlur(1)), np.float32) / 255
dirt = dirt * (1 - 0.6 * (pb > 0.3)[..., None]) + np.array([0.42, 0.40, 0.36]) * 0.6 * (pb > 0.3)[..., None] * pb[..., None]
hd = base * 0.6 + pb * 0.8 + fbm(N, 64, 3, 5) * 0.3
save(dirt, "tex/T_GroundDirt_BC.png"); save(nmap(hd, 3), "tex/T_GroundDirt_N.png")
# ---- grass (top-down: soil showing through dense dry/green blades)
g = Image.new("RGB", (N, N)); gd = ImageDraw.Draw(g)
soil = (dirt * 0.8 * 255).astype(np.uint8); g = Image.fromarray(soil); gd = ImageDraw.Draw(g)
hgt = Image.new("L", (N, N), 0); hd2 = ImageDraw.Draw(hgt)
dry = fbm(N, 6, 4, 20)
for _ in range(60000):
    x, y = R.uniform(0, N), R.uniform(0, N)
    dval = dry[int(y) % N, int(x) % N]
    if R.random() < dval * 0.9 + 0.1:
        c = (int(R.uniform(110, 160)), int(R.uniform(100, 140)), int(R.uniform(50, 80)))      # straw
    else:
        c = (int(R.uniform(55, 95)), int(R.uniform(75, 115)), int(R.uniform(30, 55)))       # green
    ang = R.uniform(0, 6.28); L = R.uniform(14, 40)
    ex, ey = x + math.cos(ang) * L, y + math.sin(ang) * L
    for dx in (-N, 0, N):
        for dy in (-N, 0, N):
            if -50 < x + dx < N + 50 and -50 < y + dy < N + 50:
                gd.line([(x + dx, y + dy), (ex + dx, ey + dy)], fill=c, width=R.choice([2, 3]))
                hd2.line([(x + dx, y + dy), (ex + dx, ey + dy)], fill=int(R.uniform(150, 255)), width=2)
ga = np.asarray(g, np.float32) / 255
ga *= (0.85 + 0.3 * fbm(N, 16, 3, 30))[..., None]
save(ga, "tex/T_GroundGrass_BC.png"); save(nmap(np.asarray(hgt, np.float32) / 255 * 0.6, 2.5), "tex/T_GroundGrass_N.png")
# ---- mask
m = np.clip((fbm(1024, 4, 5, 40) - 0.52) * 4, 0, 1)
mac = fbm(1024, 3, 4, 50)
save(np.dstack([m, mac, np.zeros_like(m)]), "tex/T_GroundMask.png")
print("ground ok")
