"""Tileable chain-link RGBA (python3): tex/T_ChainLink.png 1024, covers 1 x 1 m (diamond ~6 cm), weathered galvanised wire."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
N = 1024; P = 64                          # pattern period in px (16 diamonds per metre)
al = Image.new("L", (N, N), 0); d = ImageDraw.Draw(al)
for k in range(-2, N // P + 3):
    x = k * P
    d.line([(x, 0), (x + N, N)], fill=255, width=4)          # two wire directions
    d.line([(x, N), (x + N, 0)], fill=255, width=4)
    d.line([(x - N, 0), (x, N)], fill=255, width=4)
    d.line([(x - N, N), (x, 0)], fill=255, width=4)
a = np.asarray(al, np.float32) / 255
rs = np.random.RandomState(4)
def tn(k, seed):
    g = np.random.RandomState(seed).rand(k, k)
    img = Image.fromarray((np.tile(g, (3, 3)) * 255).astype(np.uint8)).resize((N * 3, N * 3), Image.BICUBIC)
    return np.asarray(img, np.float32)[N:2 * N, N:2 * N] / 255
rust = np.clip((tn(6, 1) * 0.6 + tn(24, 2) * 0.4 - 0.5) * 3, 0, 1)
col = np.zeros((N, N, 3)); col[:] = (0.52, 0.53, 0.52)
col = col * (1 - rust[..., None]) + np.array([0.32, 0.17, 0.08]) * rust[..., None]
col *= (0.8 + 0.3 * tn(48, 3))[..., None]
# a few broken links (holes in alpha)
for _ in range(25):
    cx, cy = rs.randint(0, N), rs.randint(0, N)
    yy, xx = np.ogrid[:N, :N]
    a[(xx - cx) ** 2 + (yy - cy) ** 2 < 12 ** 2] *= 0.0
rgb = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8))
fill = rgb  # colour everywhere already (no dark fringe in mips)
out = np.dstack([np.asarray(fill, np.float32) / 255, a])
Image.fromarray((out * 255).astype(np.uint8), "RGBA").save("tex/T_ChainLink.png")
print("chainlink ok")
