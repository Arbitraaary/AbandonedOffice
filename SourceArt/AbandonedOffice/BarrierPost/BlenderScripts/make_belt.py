"""Tileable 'DO NOT ENTER' barrier belt textures. One tile = 0.40 m of 50 mm belt (2048 x 256).
Writes T_BarrierBelt_BC.png, T_BarrierBelt_ORM.png (1024x128), T_BarrierBelt_N.png (DirectX)."""
import numpy as np, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H = 2048, 256
F = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 120)
YEL, BLK = (232, 184, 24), (22, 22, 22)
im = Image.new("RGB", (W, H), YEL); d = ImageDraw.Draw(im)
# black edge lines
d.rectangle([0, 0, W, 14], fill=BLK); d.rectangle([0, H - 15, W, H], fill=BLK)
# two text blocks per tile, separated by diagonal hazard stripes
seg = W // 2
for k in range(2):
    x0 = k * seg
    for s in range(4):                                     # stripe block at the start of each half
        sx = x0 + 20 + s * 52
        d.polygon([(sx, H - 15), (sx + 26, H - 15), (sx + 26 + 90, 14), (sx + 90, 14)], fill=BLK)
    txt = "DO NOT ENTER"
    layer = Image.new("L", (1400, 300), 0); ld = ImageDraw.Draw(layer)
    ld.text((10, 150), txt, font=F, fill=255, anchor="lm")
    layer = layer.crop(layer.getbbox())
    tw, th = layer.size
    nh = 150; nw = min(int(tw * nh / th), seg - 360)        # tall, condensed lettering
    layer = layer.resize((nw, nh), Image.LANCZOS)
    tx = int(x0 + 320 + (seg - 340 - layer.size[0]) / 2); ty = int(H / 2 - layer.size[1] / 2)
    im.paste(BLK, (tx, ty), layer)
im = im.filter(ImageFilter.GaussianBlur(0.8))
a = np.asarray(im, np.float32) / 255.0
rng = np.random.default_rng(3)
def tile_noise(scale_x, scale_y, oct=4):
    out = np.zeros((H, W), np.float32); amp = 1
    for o in range(oct):
        nx, ny = scale_x * 2 ** o, scale_y * 2 ** o
        g = rng.random((ny, nx)).astype(np.float32)
        g = np.concatenate([g, g[:, :1]], 1); g = np.concatenate([g, g[:1]], 0)   # wrap -> tileable
        big = np.asarray(Image.fromarray(g).resize((W + W // nx, H + H // ny), Image.BICUBIC))
        out += amp * big[:H, :W]; amp *= 0.5
    out -= out.min(); return out / (out.max() + 1e-6)
fade = tile_noise(8, 2)
a = a * (0.86 + 0.14 * fade[..., None])                                     # sun-faded, uneven
ink_wear = tile_noise(40, 6) > 0.82                                          # print rubbed off
black = a.mean(-1) < 0.25
a[black & ink_wear] = a[black & ink_wear] * 0.4 + np.array(YEL) / 255 * 0.6 * 0.85
dirt = tile_noise(16, 3)
a = a * (1 - 0.22 * dirt[..., None]) + 0.22 * dirt[..., None] * np.array([0.32, 0.30, 0.26])
yy = np.arange(H)[:, None] / H
edge = np.exp(-((np.minimum(yy, 1 - yy)) / 0.06) ** 2)                       # grimy, frayed edges
a = a * (1 - 0.35 * edge[..., None])
Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save("tex/T_BarrierBelt_BC.png")
# weave normal + ORM
x = np.arange(W)[None, :]; y = np.arange(H)[:, None]
h = 0.5 * np.sin(x * 2 * np.pi / 8) * np.sin(y * 2 * np.pi / 8) + 0.6 * tile_noise(64, 8, 3)
gy, gx = np.gradient(h.astype(np.float32))
n = np.stack([-gx * 1.5, gy * 1.5, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).resize((1024, 128), Image.BILINEAR).save("tex/T_BarrierBelt_N.png")
rough = 0.62 + 0.25 * dirt
orm = np.stack([np.ones_like(rough) * (1 - 0.3 * edge[:, :1].repeat(W, 1)), rough, np.zeros_like(rough)], -1)
Image.fromarray((np.clip(orm, 0, 1) * 255).astype(np.uint8)).resize((1024, 128), Image.BILINEAR).save("tex/T_BarrierBelt_ORM.png")
print("ok")
