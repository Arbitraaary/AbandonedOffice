"""Tileable bark (python3): tex/T_Bark_{BC,N,ORM}.png 1024, covers 0.5 m around x 1.0 m along a branch."""
import numpy as np
from PIL import Image
N = 1024
def tnoise(kx, ky, seed):
    r = np.random.RandomState(seed); g = r.rand(ky, kx)
    big = np.tile(g, (3, 3))
    img = Image.fromarray((big * 255).astype(np.uint8)).resize((N * 3, N * 3), Image.BICUBIC)
    return np.asarray(img, np.float32)[N:2 * N, N:2 * N] / 255
# vertical ridges: noise much finer across (x) than along (y)
ridge = sum(tnoise(24 * 2 ** o, 3 * 2 ** o, 10 + o) * 0.5 ** o for o in range(4)) / 1.875
warp = tnoise(6, 6, 30)
fis = np.abs(ridge - 0.5 + (warp - 0.5) * 0.3)
fis = np.clip(1 - fis * 6, 0, 1) ** 2                    # deep fissures
plates = tnoise(16, 6, 40)
lich = np.clip((tnoise(10, 10, 50) - 0.6) * 4, 0, 1) * np.clip((tnoise(40, 40, 51) - 0.3) * 3, 0, 1)
col = np.zeros((N, N, 3))
c0, c1 = np.array([0.30, 0.27, 0.23]), np.array([0.50, 0.47, 0.42])
col[:] = c0 + (c1 - c0) * plates[..., None]
col *= (1 - 0.55 * fis[..., None])
col = col * (1 - 0.5 * lich[..., None]) + np.array([0.40, 0.44, 0.30]) * 0.5 * lich[..., None]
h = plates * 0.5 - fis * 1.2 + tnoise(128, 128, 60) * 0.2
gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 4; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 4
n = np.dstack([-gx, gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True); n = n * 0.5 + 0.5; n[..., 1] = 1 - n[..., 1]
orm = np.dstack([1 - fis * 0.7, np.full_like(h, 0.92), np.zeros_like(h)])
for a, p in ((col, "BC"), (n, "N"), (orm, "ORM")):
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(f"tex/T_Bark_{p}.png")
print("bark ok")
