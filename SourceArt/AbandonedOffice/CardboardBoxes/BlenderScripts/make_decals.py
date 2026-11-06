"""Decal images for the cardboard boxes (system python3 + PIL)."""
import random, math
from PIL import Image, ImageDraw, ImageFilter
R = random.Random(7)
def _cr(P, n=8):
    P = [P[0]] + P + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    return out

def scribble(path, words_per_line=(3, 2), size=(1024, 512), width=11, seed=1):
    """hasty marker handwriting: random letter-like strokes, slanted, nothing readable"""
    R.seed(seed)
    im = Image.new("L", size, 255); d = ImageDraw.Draw(im)
    W, H = size; y0 = H * 0.36; xh = 46; slant = 0.25
    for line, nw in enumerate(words_per_line):
        x = 60 + R.uniform(0, 40); y = y0 + line * H * 0.36
        for w in range(nw):
            P = [(x, y)]
            for li in range(R.randint(3, 6)):
                lw = R.uniform(26, 44); kind = R.random()
                top = y - xh * R.uniform(0.8, 1.1)
                if kind < 0.18: top = y - xh * 2.0                     # ascender
                P.append((x + lw * 0.3, top)); P.append((x + lw * R.uniform(0.4, 0.7), y - R.uniform(0, 8)))
                if kind > 0.85: P.append((x + lw * 0.6, y + xh * 0.9)); P.append((x + lw * 0.75, y))   # descender
                if 0.4 < kind < 0.6: P.append((x + lw * 0.2, y - xh * 0.5))                           # loop back
                x += lw; P.append((x, y - R.uniform(0, 10)))
            pts = [(px + (y - py) * slant, py) for px, py in _cr(P)]
            d.line(pts, fill=0, width=width, joint="curve")
            if R.random() < 0.4:
                cx = R.uniform(P[0][0], x); d.line([(cx - 14, y - xh * 1.3), (cx + 22, y - xh * 1.35)], fill=0, width=width - 2)
            x += R.uniform(40, 65)
        if line == 0:
            d.line([(60, y + 30), (x - 40, y + 22 + R.uniform(-8, 8))], fill=0, width=width - 3)
    im = im.filter(ImageFilter.GaussianBlur(1.6)); im.save(path)

def printed(path):
    """flexo print: 'this side up' arrows + illegible maker's circle stamp"""
    im = Image.new("L", (512, 512), 255); d = ImageDraw.Draw(im)
    for ox in (70, 190):
        d.polygon([(ox, 150), (ox + 45, 70), (ox + 90, 150)], fill=0)
        d.rectangle([ox + 30, 150, ox + 60, 250], fill=0)
    d.rectangle([60, 270, 290, 290], fill=0)
    d.ellipse([320, 80, 480, 240], outline=0, width=8); d.ellipse([345, 105, 455, 215], outline=0, width=4)
    for k in range(5):
        yy = 125 + k * 18; d.line([(365, yy), (435, yy)], fill=0, width=5)
    for k in range(3):
        d.line([(60, 340 + k * 34), (60 + R.uniform(250, 400), 340 + k * 34)], fill=0, width=12)
    im = im.filter(ImageFilter.GaussianBlur(2.2))
    im = Image.eval(im, lambda v: min(255, int(v * 1.0 + R.uniform(0, 0))))
    im.save(path)

def label(path):
    """printed shipping label: text blocks + barcode, slightly faded"""
    im = Image.new("L", (512, 384), 255); d = ImageDraw.Draw(im)
    d.rectangle([12, 12, 499, 371], outline=60, width=4)
    for k in range(4):
        d.rectangle([30, 34 + k * 30, 30 + R.uniform(160, 330), 50 + k * 30], fill=70)
    d.rectangle([30, 160, 480, 166], fill=70)
    x = 40
    while x < 470:
        w = R.choice([3, 3, 5, 8]); d.rectangle([x, 190, x + w, 300], fill=30); x += w + R.choice([3, 4, 6])
    d.rectangle([40, 315, 300, 335], fill=90)
    im = im.filter(ImageFilter.GaussianBlur(1.0)); im.save(path)

scribble("tex/marker_a.png", (3, 2), seed=3)
scribble("tex/marker_b.png", (2, 2), size=(1024, 512), width=13, seed=9)
printed("tex/print.png")
label("tex/label.png")
print("ok")

# ---------------------------------------------------------------- whole-face ink maps (ink projected on the box walls)
def face(path, w_m, h_m, items, px_per_m=2000):
    W, H = int(w_m * px_per_m), int(h_m * px_per_m)
    im = Image.new("L", (W, H), 255)
    for src, u0, u1, v0, v1, rot in items:
        s = Image.open(src).convert("L")
        from PIL import ImageOps
        bb = ImageOps.invert(s).point(lambda v: 255 if v > 40 else 0).getbbox()
        s = s.crop((max(0, bb[0] - 10), max(0, bb[1] - 10), min(s.width, bb[2] + 10), min(s.height, bb[3] + 10)))
        s = s.rotate(rot, resample=Image.BICUBIC, expand=True, fillcolor=255)
        bw, bh = int((u1 - u0) * W), int((v1 - v0) * H)
        sc = min(bw / s.width, bh / s.height); s = s.resize((max(1, int(s.width * sc)), max(1, int(s.height * sc))), Image.LANCZOS)
        x, y = int(u0 * W), int((1 - v1) * H)
        im.paste(Image.fromarray(__import__("numpy").minimum(__import__("numpy").array(im.crop((x, y, x + s.width, y + s.height))),
                                                             __import__("numpy").array(s))), (x, y))
    im.save(path)

face("tex/face_closed_front.png", 0.50, 0.34, [("tex/marker_a.png", 0.08, 0.72, 0.38, 0.86, -3), ("tex/print.png", 0.74, 0.95, 0.6, 0.92, 0)])
face("tex/face_open_front.png", 0.45, 0.30, [("tex/marker_b.png", 0.14, 0.86, 0.42, 0.85, 2)])
face("tex/face_crushed_front.png", 0.55, 0.40, [("tex/marker_b.png", 0.24, 0.9, 0.45, 0.86, -6), ("tex/print.png", 0.04, 0.24, 0.62, 0.9, 0)])
face("tex/face_crushed_side.png", 0.40, 0.40, [("tex/print.png", 0.55, 0.85, 0.6, 0.9, 0)])
print("faces ok")
