"""Exterior textures (python3 + PIL + numpy).
  tex/T_Asphalt_{BC,N,ORM}.png  2048 tileable, covers 4 x 4 m
  tex/T_Foliage.png             2048 RGBA atlas: 4 leaf clusters | grass clump | dry weed | ivy-ish leaves
  tex/foliage_regions.txt
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
R = random.Random(3); RS = np.random.RandomState(3)
N = 2048

def tnoise(n, k, seed):
    """tileable value noise: random k x k grid, bicubic upsample with wrap"""
    r = np.random.RandomState(seed); g = r.rand(k, k)
    big = np.tile(g, (3, 3))
    img = Image.fromarray((big * 255).astype(np.uint8)).resize((n * 3, n * 3), Image.BICUBIC)
    a = np.asarray(img, np.float32)[n:2 * n, n:2 * n] / 255
    return a
def fbm(n, k0, octaves, seed, gain=0.5):
    out = np.zeros((n, n)); amp = 1; tot = 0
    for o in range(octaves):
        out += tnoise(n, k0 * 2 ** o, seed + o) * amp; tot += amp; amp *= gain
    return out / tot

# ------------------------------------------------------------------ asphalt
base = fbm(N, 8, 6, 10)
fine = RS.rand(N, N)
agg = (fine > 0.985).astype(np.float32)                                    # light stone chips
agg = np.asarray(Image.fromarray((agg * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
dark = (fine < 0.02).astype(np.float32)
col = np.zeros((N, N, 3))
c0 = np.array([0.20, 0.20, 0.19]); c1 = np.array([0.32, 0.315, 0.30])
col[:] = c0 + (c1 - c0) * base[..., None]
col = col * (1 - 0.5 * agg[..., None]) + np.array([0.42, 0.41, 0.38]) * 0.5 * agg[..., None]
col *= (1 - 0.35 * dark[..., None])
# worn / faded patches, oil stains, dirt
patch = np.clip((fbm(N, 4, 4, 20) - 0.55) * 4, 0, 1)
col = col * (1 - 0.35 * patch[..., None]) + np.array([0.33, 0.32, 0.30]) * 0.35 * patch[..., None]
oil = np.clip((fbm(N, 6, 4, 30) - 0.66) * 6, 0, 1)
col *= (1 - 0.45 * oil[..., None])
dirt = np.clip((fbm(N, 5, 5, 40) - 0.5) * 3, 0, 1)
col = col * (1 - 0.3 * dirt[..., None]) + np.array([0.24, 0.21, 0.16]) * 0.3 * dirt[..., None]
# cracks (drawn with wrap) + crack fill moss
crack = Image.new("L", (N, N), 0); cd = ImageDraw.Draw(crack)
def crack_line(x, y, ang, L, w, depth=0):
    pts = [(x, y)]
    for _ in range(int(L / 10)):
        ang += R.uniform(-0.22, 0.22); x += math.cos(ang) * 10; y += math.sin(ang) * 10; pts.append((x, y))
        if depth < 2 and R.random() < 0.06: crack_line(x, y, ang + R.choice([-1, 1]) * R.uniform(0.7, 1.4), L * 0.4, max(1, w - 1), depth + 1)
    for dx in (-N, 0, N):
        for dy in (-N, 0, N):
            cd.line([(px + dx, py + dy) for px, py in pts], fill=255, width=w)
for _ in range(5): crack_line(R.uniform(0, N), R.uniform(0, N), R.uniform(0, 6.28), R.uniform(700, 1600), R.randint(3, 6))
# alligator cracking patch
for _ in range(60):
    cx, cy = R.uniform(1200, 1700), R.uniform(300, 800)
    crack_line(cx, cy, R.uniform(0, 6.28), R.uniform(60, 160), 2, 2)
cr = np.asarray(crack, np.float32) / 255
crb = np.asarray(crack.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
col = col * (1 - 0.75 * cr[..., None])
moss = np.clip(crb * 2.5, 0, 1) * np.clip((fbm(N, 8, 3, 50) - 0.45) * 3, 0, 1)
col = col * (1 - 0.6 * moss[..., None]) + np.array([0.12, 0.15, 0.06]) * 0.6 * moss[..., None]
# height -> normal (DirectX: green flipped)
h = base * 0.4 + fbm(N, 64, 3, 60) * 0.6 + agg * 0.5 - cr * 1.5 - crb * 0.5
gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 2.5; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 2.5
nrm = np.dstack([-gx, gy, np.ones_like(h)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
nrm_img = (nrm * 0.5 + 0.5)
nrm_img[..., 1] = 1 - nrm_img[..., 1]
ao = np.clip(1 - crb * 0.8 - dark * 0.2, 0, 1)
rough = np.clip(0.88 - 0.25 * oil + 0.05 * base - 0.1 * agg, 0, 1)
orm = np.dstack([ao, rough, np.zeros_like(ao)])
def save(a, p): Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(p)
save(col, "tex/T_Asphalt_BC.png"); save(nrm_img, "tex/T_Asphalt_N.png"); save(orm, "tex/T_Asphalt_ORM.png")

# ------------------------------------------------------------------ foliage atlas
F = Image.new("RGBA", (N, N), (0, 0, 0, 0)); fd = ImageDraw.Draw(F)
regions = {}
def leaf(d, x, y, ang, L, W, col):
    pts = []
    for k in range(13):
        t = k / 12; w = W * math.sin(math.pi * t) ** 0.8
        pts.append((t * L, w))
    pts += [(t, -w) for t, w in reversed(pts[1:-1])]
    ca, sa = math.cos(ang), math.sin(ang)
    P = [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]
    d.polygon(P, fill=col)
    d.line([(x, y), (x + L * ca * 0.95, y + L * sa * 0.95)], fill=tuple(max(0, c - 25) for c in col[:3]) + (255,), width=2)
def jitter(c, s=18):
    return tuple(int(max(0, min(255, v + R.uniform(-s, s)))) for v in c) + (255,)
PAL = [(104, 130, 56), (124, 146, 64), (90, 116, 50), (146, 148, 70), (166, 140, 64), (136, 104, 54)]   # dusty, partly autumn
for k in range(3):                                     # leaf clusters on twigs, 1024 x 1024 cells
    ox, oy = (k % 2) * 1024, (k // 2) * 1024

    cx, cy = ox + 512, oy + 540
    twig = [(cx, oy + 1000)]
    tips = []
    for b in range(R.randint(5, 7)):                  # twig fan
        ang = -math.pi / 2 + R.uniform(-1.1, 1.1); L = R.uniform(280, 430)
        sx, sy = cx + R.uniform(-30, 30), oy + 1000 - R.uniform(0, 260)
        ex, ey = sx + math.cos(ang) * L, sy + math.sin(ang) * L
        fd.line([(sx, sy), (ex, ey)], fill=(70, 55, 40, 255), width=6); tips.append((sx, sy, ex, ey))
    fd.line([(cx, oy + 1000), (cx, oy + 760)], fill=(70, 55, 40, 255), width=10)
    for sx, sy, ex, ey in tips:
        for j in range(R.randint(14, 22)):
            t = R.uniform(0.25, 1.0); x, y = sx + (ex - sx) * t, sy + (ey - sy) * t
            leaf(fd, x, y, R.uniform(0, 6.28), R.uniform(70, 120), R.uniform(24, 38),
                 jitter(PAL[R.randint(0, 2) if k < 2 else R.randint(0, 5)]))
    regions[f"leaf{k}"] = (ox, oy, ox + 1024, oy + 1024)
# grass clump (bottom-right quadrant top half) and dry weed (bottom half)
gx0, gy0 = 1024, 1024
for j in range(70):
    bx = gx0 + 512 + R.uniform(-260, 260); h = R.uniform(250, 480); lean = R.uniform(-120, 120)
    c = jitter((118, 136, 62) if R.random() < 0.6 else (176, 160, 96), 20)
    pts = [(bx - 7, gy0 + 510), (bx + lean * 0.5, gy0 + 510 - h * 0.6), (bx + lean, gy0 + 510 - h), (bx + lean * 0.5 + 4, gy0 + 510 - h * 0.6), (bx + 7, gy0 + 510)]
    fd.polygon(pts, fill=c)
regions["grass"] = (gx0, gy0, gx0 + 1024, gy0 + 512)
wy0 = 1536
for j in range(10):
    bx = gx0 + 512 + R.uniform(-300, 300); h = R.uniform(280, 470); lean = R.uniform(-60, 60)
    fd.line([(bx, wy0 + 510), (bx + lean, wy0 + 510 - h)], fill=(120, 100, 60, 255), width=5)
    for s in range(R.randint(4, 7)):
        t = R.uniform(0.2, 1); x, y = bx + lean * t, wy0 + 510 - h * t
        ang = -math.pi / 2 + R.uniform(-1.3, 1.3)
        leaf(fd, x, y, ang, R.uniform(50, 90), R.uniform(12, 20), jitter((130, 116, 62), 22))
    fd.ellipse([bx + lean - 16, wy0 + 510 - h - 16, bx + lean + 16, wy0 + 510 - h + 16], fill=jitter((150, 120, 70), 15))   # seed head
regions["weed"] = (gx0, wy0, gx0 + 1024, wy0 + 512)
# light shading/variation, then dilate colour into transparent area (no dark fringes in mips)
a = np.asarray(F, np.float32) / 255
rgb, al = a[..., :3], a[..., 3]
sh = fbm(N, 16, 3, 70)
rgb = rgb * (0.97 + 0.2 * sh[..., None])
fill = np.array(Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)), np.float32) / 255
rgb = np.where(al[..., None] > 0.5, rgb, fill)
out = np.dstack([np.clip(rgb, 0, 1), al])
Image.fromarray((out * 255).astype(np.uint8), "RGBA").save("tex/T_Foliage.png")
with open("tex/foliage_regions.txt", "w") as f:
    for k, (x0, y0, x1, y1) in regions.items():
        f.write(f"{k} {x0 / N:.5f} {1 - y1 / N:.5f} {x1 / N:.5f} {1 - y0 / N:.5f}\n")
print("ok", regions)
