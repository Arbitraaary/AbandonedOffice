"""A4 sheet textures for the abandoned office (1024 atlas).
Atlas layout (UV):  front page  x 0..724, y 0..1024  (A4 1:1.414)
                    back side   x 730..1020, y 0..410
                    edge colour x 730..1020, y 420..440
Writes T_PaperA4_{A,B,C}_BC.png, T_PaperA4_N.png (DirectX), T_PaperA4_ORM.png
"""
import random, math, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "tex"
os.makedirs(OUT, exist_ok=True)
S = 2                                   # draw at 2x, then downsample
PW, PH = 724 * S, 1024 * S              # page
FD = "/usr/share/fonts/truetype"
serif = lambda s: ImageFont.truetype(f"{FD}/liberation/LiberationSerif-Regular.ttf", s * S)
sans_b = lambda s: ImageFont.truetype(f"{FD}/liberation/LiberationSans-Bold.ttf", s * S)
sans = lambda s: ImageFont.truetype(f"{FD}/liberation/LiberationSans-Regular.ttf", s * S)

INK = (62, 60, 60)
SYL = ["ra", "to", "mel", "vi", "na", "ost", "ke", "lu", "dor", "pa", "sen", "ri", "ka", "mo", "tel", "us", "ber", "an"]
def word(rnd):
    return "".join(rnd.choice(SYL) for _ in range(rnd.randint(1, 4)))
def line_text(rnd, n):
    return " ".join(word(rnd) for _ in range(n))

def text_block(d, rnd, x0, y, x1, lines, size=7, lh=11, col=INK):
    f = serif(size)
    for i in range(lines):
        s = ""
        while d.textlength(s + " " + word(rnd), font=f) < (x1 - x0) * S:
            s += " " + word(rnd)
        if i == lines - 1:
            s = s[: int(len(s) * rnd.uniform(0.3, 0.8))]
        d.text((x0 * S, y * S), s.strip(), font=f, fill=col)
        y += lh
    return y + 8

def squiggle(d, rnd, x, y, w, col, width=2, amp=6):
    pts = [(x * S + k * S, y * S + amp * S * math.sin(k * 0.35 + rnd.random()) * rnd.uniform(0.3, 1))
           for k in range(0, w, 3)]
    d.line(pts, fill=col, width=width * S)

def page_memo(rnd):
    im = Image.new("RGB", (PW, PH), (255, 255, 255)); d = ImageDraw.Draw(im)
    d.rectangle([60 * S, 52 * S, 150 * S, 78 * S], fill=(58, 78, 104))            # generic logo block
    d.text((160 * S, 54 * S), word(rnd).upper(), font=sans_b(9), fill=(58, 78, 104))
    d.text((160 * S, 70 * S), line_text(rnd, 3), font=sans(6), fill=(110, 110, 110))
    d.line([60 * S, 92 * S, 664 * S, 92 * S], fill=(150, 150, 150), width=S)
    d.text((60 * S, 120 * S), line_text(rnd, 3).upper(), font=sans_b(8), fill=INK)
    y = 150
    while y < 760:
        y = text_block(d, rnd, 60, y, 664, rnd.randint(3, min(8, max(3, (850 - y) // 11))))
    squiggle(d, rnd, 70, 905, 150, (40, 50, 110), 2, 8)                          # signature
    d.text((70 * S, 925 * S), line_text(rnd, 2), font=serif(7), fill=INK)
    # faded round stamp
    st = Image.new("L", (PW, PH), 0); sd = ImageDraw.Draw(st)
    cx, cy, r = 520 * S, 900 * S, 52 * S
    sd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=4 * S)
    sd.ellipse([cx - r + 12 * S, cy - r + 12 * S, cx + r - 12 * S, cy + r - 12 * S], outline=255, width=2 * S)
    sd.text((cx - 30 * S, cy - 8 * S), word(rnd).upper()[:6], font=sans_b(10), fill=255)
    st = st.rotate(rnd.uniform(-25, 25), center=(cx, cy)).filter(ImageFilter.GaussianBlur(S))
    im.paste((150, 55, 60), mask=st.point(lambda v: int(v * 0.55)))
    return im

def page_report(rnd):
    im = Image.new("RGB", (PW, PH), (255, 255, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, PW, 40 * S], fill=(70, 86, 108))
    d.text((60 * S, 12 * S), line_text(rnd, 2).upper(), font=sans_b(8), fill=(225, 228, 232))
    y = text_block(d, rnd, 60, 70, 664, 4)
    # table
    cols = [60, 230, 380, 520, 664]
    for r in range(14):
        yy = (y + r * 20) * S
        if r == 0: d.rectangle([60 * S, yy, 664 * S, yy + 20 * S], fill=(205, 210, 218))
        d.line([60 * S, yy, 664 * S, yy], fill=(160, 160, 165), width=S)
        for c in range(4):
            txt = word(rnd) if c == 0 else f"{rnd.randint(10, 9999):,}".replace(",", " ")
            d.text(((cols[c] + 6) * S, yy + 5 * S), txt, font=sans(7) if r else sans_b(7), fill=INK)
    for x in cols: d.line([x * S, y * S, x * S, (y + 14 * 20) * S], fill=(160, 160, 165), width=S)
    y += 14 * 20 + 30
    # bar chart
    base = y + 170
    d.line([80 * S, base * S, 640 * S, base * S], fill=INK, width=S)
    for k in range(9):
        h = rnd.randint(30, 160)
        d.rectangle([(100 + k * 60) * S, (base - h) * S, (135 + k * 60) * S, base * S],
                    fill=(90, 110, 140) if k % 3 else (140, 150, 160))
    y = base + 30
    text_block(d, rnd, 60, y, 664, 5)
    d.text((600 * S, 990 * S), f"- {rnd.randint(2, 19)} -", font=sans(7), fill=(120, 120, 120))
    return im

def page_form(rnd):
    im = Image.new("RGB", (PW, PH), (255, 255, 255)); d = ImageDraw.Draw(im)
    d.text((60 * S, 50 * S), line_text(rnd, 2).upper(), font=sans_b(9), fill=INK)
    d.text((60 * S, 74 * S), line_text(rnd, 6), font=sans(7), fill=(100, 100, 100))
    y = 110
    blue = (45, 60, 125)
    for r in range(12):
        d.text((60 * S, y * S), word(rnd).capitalize() + ":", font=sans(8), fill=INK)
        d.rectangle([200 * S, (y - 4) * S, 664 * S, (y + 16) * S], outline=(140, 140, 145), width=S)
        if rnd.random() < 0.75:
            squiggle(d, rnd, 210, y + 7, rnd.randint(80, 380), blue, 2, 4)
        y += 34
    y += 10
    for r in range(6):                                     # checkboxes
        for c in range(3):
            x = 60 + c * 200
            d.rectangle([x * S, y * S, (x + 12) * S, (y + 12) * S], outline=INK, width=S)
            if rnd.random() < 0.4:
                d.line([(x + 2) * S, (y + 6) * S, (x + 5) * S, (y + 10) * S, (x + 12) * S, (y - 2) * S], fill=blue, width=2 * S)
            d.text(((x + 20) * S, y * S), word(rnd), font=sans(8), fill=INK)
        y += 26
    y = text_block(d, rnd, 60, y + 20, 664, 7, size=6, lh=9, col=(90, 90, 90))
    d.line([60 * S, 930 * S, 300 * S, 930 * S], fill=INK, width=S)
    squiggle(d, rnd, 80, 915, 160, blue, 2, 7)
    return im

# ---------------------------------------------------------------- ageing (numpy)
def fbm(h, w, rnd, octaves=5, base=8):
    out = np.zeros((h, w), np.float32); amp = 1.0
    for o in range(octaves):
        n = base * 2 ** o
        small = np.array([[rnd.random() for _ in range(n)] for _ in range(max(2, int(n * h / w)))], np.float32)
        out += amp * np.array(Image.fromarray(small).resize((w, h), Image.BICUBIC))
        amp *= 0.5
    out -= out.min(); out /= out.max() + 1e-6
    return out

def age(page_rgb, rnd, stain=None):
    h, w = page_rgb.shape[:2]
    ink = 1.0 - page_rgb / 255.0                           # ink amount per channel
    paper = np.array([0.80, 0.78, 0.72])                   # grey-cream, matches the grey/stone office
    mott = fbm(h, w, rnd, 5, 4)[..., None]
    col = paper * (0.93 + 0.10 * mott)
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (0.06 * w)
    col = col * (1 - 0.12 * np.clip(1 - edge, 0, 1)[..., None] * np.array([0.6, 0.8, 1.3]))   # yellowed edges
    fade = 0.78 + 0.18 * fbm(h, w, rnd, 3, 3)[..., None]   # faded, uneven toner
    col = col * (1 - ink * fade * 0.92)
    if stain == "coffee":
        cx, cy, r = rnd.uniform(0.25, 0.75) * w, rnd.uniform(0.15, 0.4) * h, 0.11 * w
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = np.exp(-((d - r) / (0.012 * w)) ** 2) * 0.35 + (d < r) * 0.06
        ring *= 0.6 + 0.4 * fbm(h, w, rnd, 3, 6)
        col = col * (1 - ring[..., None] * np.array([0.25, 0.45, 0.75]))
    if stain == "water":
        m = fbm(h, w, rnd, 4, 3)
        blot = np.clip((m - 0.62) * 8, 0, 1)
        edge_l = np.clip(1 - np.abs(m - 0.62) * 40, 0, 1)
        col = col * (1 - (blot * 0.05 + edge_l * 0.12)[..., None] * np.array([0.3, 0.5, 0.8]))
    if stain == "shoe":                                    # faint dusty generic tread print
        sole = Image.new("L", (w, h), 0); sd = ImageDraw.Draw(sole)
        cx, cy = w * 0.55, h * 0.62
        for k in range(16):
            yk = cy - 0.28 * h + k * 0.026 * h
            half = 0.085 * w * (1 - abs(k - 6) / 14)
            sd.rectangle([cx - half, yk, cx + half, yk + 0.012 * h], fill=255)
        sole = sole.rotate(rnd.uniform(-30, 30), center=(cx, cy)).filter(ImageFilter.GaussianBlur(2))
        sm = np.array(sole, np.float32) / 255 * (0.5 + 0.5 * fbm(h, w, rnd, 4, 10))
        col = col * (1 - 0.0 * sm[..., None]) + sm[..., None] * 0.18 * (np.array([0.42, 0.40, 0.37]) - col)
    dust = fbm(h, w, rnd, 6, 16)
    speck = (np.array([[rnd.random() for _ in range(w // 4)] for _ in range(h // 4)]) > 0.996).astype(np.float32)
    speck = np.array(Image.fromarray(speck).resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8)) if False else Image.fromarray(speck).resize((w, h), Image.BILINEAR))
    col = col * (1 - 0.06 * dust[..., None]) * (1 - 0.18 * speck[..., None])
    # middle fold (sheet was folded in half once)
    fold = np.exp(-((yy - h * 0.5) / (0.004 * h)) ** 2)
    col = col * (1 - 0.10 * fold[..., None])
    return np.clip(col, 0, 1)

def build_variant(name, fn, stain, seed):
    rnd = random.Random(seed)
    page = fn(rnd).resize((724, 1024), Image.LANCZOS)      # downsample -> small text becomes illegible
    page = page.filter(ImageFilter.GaussianBlur(0.85))
    front = age(np.array(page, np.float32), rnd, stain)
    # back side: blank paper, faint mirrored show-through, more dust
    back_src = np.array(page.transpose(Image.FLIP_LEFT_RIGHT).resize((290, 410), Image.LANCZOS), np.float32)
    back_src = 255 - (255 - back_src) * 0.08
    back = age(back_src, rnd, None) * 0.96
    atlas = np.zeros((1024, 1024, 3), np.float32)
    atlas[:, :] = front[:, -1:].mean() if False else np.array([0.74, 0.72, 0.66])
    atlas[:, :724] = front
    atlas[0:410, 730:1020] = back
    atlas[420:440, 730:1020] = np.array([0.70, 0.68, 0.62])
    Image.fromarray((atlas ** (1 / 1.0) * 255).astype(np.uint8)).save(f"{OUT}/T_PaperA4_{name}_BC.png")

def build_normal_orm(seed=99):
    rnd = random.Random(seed)
    N = 1024
    H = np.zeros((N, N), np.float32)
    # wrinkles: thin random creases in the page area
    img = Image.new("L", (N, N), 128); d = ImageDraw.Draw(img)
    for _ in range(60):
        x0, y0 = rnd.uniform(0, 724), rnd.uniform(0, 1024)
        a = rnd.uniform(0, math.pi); L = rnd.uniform(30, 220)
        d.line([x0, y0, x0 + L * math.cos(a), y0 + L * math.sin(a)], fill=int(128 + 120 * rnd.uniform(0.3, 1.0) * rnd.choice((-1, 1))), width=1)
    H += (np.array(img.filter(ImageFilter.GaussianBlur(1.6)), np.float32) - 128) / 40.0
    H += 0.8 * np.exp(-((np.arange(N)[:, None] - 512) / 3.0) ** 2) * (np.arange(N)[None, :] < 724)   # middle fold
    H += 0.6 * fbm(N, N, rnd, 4, 6)
    H[:, 724:] = H[:, 724:] * 0.4
    gy, gx = np.gradient(H)
    k = 2.5
    n = np.stack([-gx * k, gy * k, np.ones_like(H)], -1)        # DirectX (Unreal): +Y down
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(f"{OUT}/T_PaperA4_N.png")
    rough = 0.84 + 0.08 * fbm(512, 512, rnd, 4, 6)
    ao = 1.0 - 0.15 * np.clip(-np.array(Image.fromarray(H).resize((512, 512))), 0, 1)
    orm = np.stack([ao, rough, np.zeros_like(rough)], -1)
    Image.fromarray((np.clip(orm, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/T_PaperA4_ORM.png")

build_variant("A", page_memo, "coffee", 1)
build_variant("B", page_report, "water", 2)
build_variant("C", page_form, "shoe", 3)
build_normal_orm()
print("ok")
