"""Booth textures: SECURITY sign (1024x256) and glass atlas (1536x512 RGBA: front broken | side cracked | door dirty)."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
rng = np.random.default_rng(8)
def fbm(w, h, scale, octv=5):
    out = np.zeros((h, w), np.float32); amp = 1
    for o in range(octv):
        n = scale * 2 ** o
        g = rng.random((max(2, int(n * h / w)), n)).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC)); amp *= 0.5
    out -= out.min(); return out / out.max()
# --- sign
W, H = 1024, 256
im = Image.new("RGB", (W, H), (28, 52, 92)); d = ImageDraw.Draw(im)
d.rectangle([8, 8, W - 9, H - 9], outline=(220, 220, 215), width=6)
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 150)
d.text((W / 2, H / 2 + 6), "SECURITY", font=F, fill=(225, 225, 220), anchor="mm")
a = np.asarray(im, np.float32) / 255
f = fbm(W, H, 4)
a = a * (0.75 + 0.25 * f[..., None]) + (1 - f[..., None]) * 0.12 * np.array([0.5, 0.5, 0.5])
streak = fbm(W, H, 40, 3) * np.linspace(0.2, 1, H)[:, None]
a = a * (1 - 0.35 * (streak > 0.55)[..., None] * streak[..., None]) + 0.0
peel = fbm(W, H, 12) > 0.8
a[peel] = np.array([0.62, 0.62, 0.6])
Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save("tex/booth_sign.png")
# --- glass panes
PW, PH = 512, 512
def pane(kind):
    rgb = np.ones((PH, PW, 3), np.float32) * np.array([0.55, 0.58, 0.56])
    dirt = fbm(PW, PH, 4)
    grime = np.clip(dirt * 0.8 + np.linspace(0, 0.5, PH)[:, None] * 0.6, 0, 1)
    alpha = 0.18 + 0.55 * grime ** 1.5                                           # dusty, more at the bottom
    rgb = rgb * (1 - grime[..., None] * 0.6) + grime[..., None] * 0.6 * np.array([0.35, 0.32, 0.27])
    # rain streak marks
    st = fbm(PW, PH, 60, 2)
    alpha += 0.12 * (st > 0.7)
    lines = Image.new("L", (PW, PH), 0); ld = ImageDraw.Draw(lines)
    if kind in ("broken", "cracked"):
        cx, cy = (PW * 0.45, PH * 0.42) if kind == "broken" else (PW * 0.7, PH * 0.3)
        for k in range(14):                                                      # radial cracks
            ang = k * 2 * math.pi / 14 + rng.uniform(-0.2, 0.2)
            x, y = cx, cy; pts = [(x, y)]
            for s in range(int(rng.integers(4, 9))):
                ang += rng.uniform(-0.35, 0.35); L = rng.uniform(25, 70)
                x += L * math.cos(ang); y += L * math.sin(ang); pts.append((x, y))
            ld.line(pts, fill=255, width=2)
        for r in (40, 90, 150):                                                  # concentric cracks
            poly = [(cx + r * (1 + rng.uniform(-0.2, 0.2)) * math.cos(t), cy + r * (1 + rng.uniform(-0.2, 0.2)) * math.sin(t))
                    for t in np.linspace(0, 2 * math.pi, 18)]
            ld.line(poly, fill=200, width=1)
    cr = np.asarray(lines.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255
    rgb = rgb * (1 - cr[..., None]) + cr[..., None] * np.array([0.85, 0.87, 0.86])
    alpha = np.clip(alpha + cr * 0.6, 0, 1)
    if kind == "broken":                                                         # jagged hole, shards left in the frame
        hole = Image.new("L", (PW, PH), 0); hd = ImageDraw.Draw(hole)
        pts = []
        for t in np.linspace(0, 2 * math.pi, 26, endpoint=False):
            r = rng.uniform(150, 330)
            pts.append((PW * 0.47 + r * math.cos(t) * 1.05, PH * 0.45 + r * math.sin(t) * 0.95))
        hd.polygon(pts, fill=255)
        hm = np.asarray(hole, np.float32) / 255
        alpha = alpha * (1 - hm)
    return np.dstack([rgb, alpha])
atlas = np.concatenate([pane("broken"), pane("cracked"), pane("dirty")], 1)
Image.fromarray((np.clip(atlas, 0, 1) * 255).astype(np.uint8), "RGBA").save("tex/booth_glass.png")
print("ok")
