"""Paper atlas for the cork board + clock face (python3 + PIL + numpy).
papers.png 2048x2048, regions (u0, v0, u1, v1 in 0..1, v up) are written to tex/regions.txt"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
R = random.Random(5)
S = 2048
atlas = Image.new("RGB", (S, S), (200, 196, 180)); d = ImageDraw.Draw(atlas)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"; FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
regions = {}
def region(name, x0, y0, x1, y1):           # pixel box, y down
    regions[name] = (x0 / S, 1 - y1 / S, x1 / S, 1 - y0 / S)

def scrib_line(dr, x, y, length, h=14, w=3, col=(40, 40, 50)):
    """one line of tiny illegible 'text': word blobs"""
    xx = x
    while xx < x + length - 20:
        wl = R.randint(25, 80)
        pts = [(xx + t, y + h * 0.5 * math.sin(t * R.uniform(0.4, 0.7)) * R.uniform(0.3, 1)) for t in range(0, wl, 3)]
        dr.line(pts, fill=col, width=w); xx += wl + R.randint(10, 18)

# ---- calendar page (A4 portrait) 0..700 x 0..990
cx0, cy0 = 20, 20
d.rectangle([cx0, cy0, cx0 + 700, cy0 + 990], fill=(222, 216, 196))
d.rectangle([cx0 + 30, cy0 + 30, cx0 + 670, cy0 + 380], fill=(120, 140, 150))      # faded photo area
for k in range(12):                                                                  # abstract hills/sky
    y = cy0 + 220 + k * 12 + int(30 * math.sin(k))
    d.polygon([(cx0 + 30, cy0 + 380), (cx0 + 30, y), (cx0 + 350, y - 60 + k * 5), (cx0 + 670, y + 20), (cx0 + 670, cy0 + 380)],
              fill=(110 + k * 6, 128 + k * 4, 112 + k * 2))
font = ImageFont.truetype(FB, 64); d.text((cx0 + 210, cy0 + 405), "03  2019", font=font, fill=(150, 60, 50))
f2 = ImageFont.truetype(FR, 26)
for c, n in enumerate("MTWTFSS"): d.text((cx0 + 55 + c * 88, cy0 + 500), n, font=f2, fill=(60, 60, 60))
for r in range(5):
    for c in range(7):
        x, y = cx0 + 40 + c * 88, cy0 + 545 + r * 82
        d.rectangle([x, y, x + 82, y + 76], outline=(150, 145, 130), width=2)
        day = r * 7 + c - 3
        if 1 <= day <= 31: d.text((x + 6, y + 4), str(day), font=f2, fill=(70, 70, 70))
        if day in (8, 14, 21): d.ellipse([x + 4, y + 2, x + 70, y + 70], outline=(170, 40, 40), width=5)   # circled days
        if day > 14 and day < 29 and R.random() < 0.6:                                                    # crossed-off days
            d.line([(x + 8, y + 8), (x + 74, y + 68)], fill=(40, 50, 90), width=4); d.line([(x + 74, y + 8), (x + 8, y + 68)], fill=(40, 50, 90), width=4)
region("calendar", cx0, cy0, cx0 + 700, cy0 + 990)

# ---- memo sheet (A4) 740..1440 x 20..1010
mx0, my0 = 740, 20
d.rectangle([mx0, my0, mx0 + 700, my0 + 990], fill=(226, 222, 206))
d.rectangle([mx0 + 50, my0 + 60, mx0 + 330, my0 + 90], fill=(60, 60, 70))
scrib_line(d, mx0 + 50, my0 + 130, 260, 10, 3)
d.rectangle([mx0 + 50, my0 + 200, mx0 + 650, my0 + 206], fill=(90, 90, 100))
for k in range(18):
    scrib_line(d, mx0 + 50, my0 + 250 + k * 38, R.randint(380, 600), 12, 3)
d.line([(mx0 + 420, my0 + 920), (mx0 + 470, my0 + 890), (mx0 + 520, my0 + 930), (mx0 + 600, my0 + 900)], fill=(30, 40, 110), width=5)   # signature
region("memo", mx0, my0, mx0 + 700, my0 + 990)

# ---- tear-off flyer (A5) 1470..1960 x 20..710 with 7 tabs at the bottom
fx0, fy0 = 1470, 20
d.rectangle([fx0, fy0, fx0 + 490, fy0 + 690], fill=(214, 220, 200))
d.rectangle([fx0 + 30, fy0 + 40, fx0 + 460, fy0 + 140], fill=(40, 90, 130))
for k in range(8): scrib_line(d, fx0 + 40, fy0 + 190 + k * 40, R.randint(260, 410), 12, 3)
for k in range(7):
    x = fx0 + 10 + k * 67
    d.line([(x, fy0 + 540), (x, fy0 + 690)], fill=(120, 120, 120), width=2)
    for j in range(3): d.line([(x + 30, fy0 + 560 + j * 40), (x + 30, fy0 + 590 + j * 40)], fill=(50, 50, 60), width=4)
region("flyer", fx0, fy0, fx0 + 490, fy0 + 690)

# ---- photos: faded landscape + faded office group (silhouettes only)
px0, py0 = 1470, 740
d.rectangle([px0, py0, px0 + 520, py0 + 360], fill=(236, 232, 222))
for k in range(320):
    y = py0 + 20 + k
    t = k / 320; d.line([(px0 + 20, y), (px0 + 500, y)], fill=(int(150 + 40 * t), int(170 + 10 * t), int(180 - 40 * t)))
d.polygon([(px0 + 20, py0 + 260), (px0 + 160, py0 + 160), (px0 + 300, py0 + 230), (px0 + 420, py0 + 150), (px0 + 500, py0 + 210), (px0 + 500, py0 + 340), (px0 + 20, py0 + 340)], fill=(110, 130, 100))
region("photo1", px0, py0, px0 + 520, py0 + 360)
qx0, qy0 = 1470, 1130
d.rectangle([qx0, qy0, qx0 + 520, qy0 + 360], fill=(236, 232, 222))
d.rectangle([qx0 + 20, qy0 + 20, qx0 + 500, qy0 + 340], fill=(170, 160, 140))
d.rectangle([qx0 + 20, qy0 + 20, qx0 + 500, qy0 + 120], fill=(190, 185, 170))
for k in range(6):                                    # people as soft blobs, faces unreadable
    x = qx0 + 70 + k * 75; y = qy0 + 150 + (k % 2) * 20
    d.ellipse([x - 22, y - 26, x + 22, y + 20], fill=(150, 125, 105))
    d.rounded_rectangle([x - 36, y + 18, x + 36, y + 190], 20, fill=[(60, 70, 90), (90, 80, 70), (50, 55, 60)][k % 3])
region("photo2", qx0, qy0, qx0 + 520, qy0 + 360)

# ---- sticky notes 4 colours x scribble, 300px each, row at y 1060
cols = [(222, 206, 110), (226, 170, 180), (170, 214, 160), (222, 206, 110)]
for k, c in enumerate(cols):
    x0, y0 = 20 + k * 340, 1060
    d.rectangle([x0, y0, x0 + 300, y0 + 300], fill=c)
    for j in range(R.randint(3, 5)): scrib_line(d, x0 + 25, y0 + 60 + j * 50, R.randint(150, 250), 22, 7, (30, 30, 60))
    region(f"sticky{k}", x0, y0, x0 + 300, y0 + 300)

# ---- clock face 1000x1000 at (20, 1040+...) -> put at x 20..1000, y 1400..2020 is too small; use 1000..2040 x 1500..? -> 620 px
fx, fy, fs = 20, 1400, 620
face = Image.new("RGB", (1000, 1000), (225, 222, 210)); fd = ImageDraw.Draw(face)
fd.ellipse([20, 20, 980, 980], outline=(30, 30, 30), width=10)
for k in range(60):
    a = math.radians(k * 6); r0 = 440 if k % 5 else 400
    fd.line([(500 + r0 * math.sin(a), 500 - r0 * math.cos(a)), (500 + 465 * math.sin(a), 500 - 465 * math.cos(a))], fill=(30, 30, 30), width=12 if k % 5 == 0 else 4)
fn = ImageFont.truetype(FB, 96)
for h in range(1, 13):
    a = math.radians(h * 30); x, y = 500 + 330 * math.sin(a), 500 - 330 * math.cos(a)
    t = str(h); w = fn.getlength(t); fd.text((x - w / 2, y - 58), t, font=fn, fill=(30, 30, 30))
fa = np.asarray(face, np.float32) / 255
yy, xx = np.mgrid[0:1000, 0:1000]
stain = np.exp(-(((xx - 330) / 260) ** 2 + ((yy - 720) / 200) ** 2))                    # water stain from below
ring = np.exp(-((np.sqrt(((xx - 330) / 260) ** 2 + ((yy - 720) / 200) ** 2) - 1.0) / 0.06) ** 2)
fa = fa * (1 - 0.25 * stain[..., None]) * np.array([1, 0.97, 0.88]) ** stain[..., None]
fa = fa * (1 - 0.3 * ring[..., None] * np.array([0.4, 0.6, 1.0]))
fa = fa * np.array([1.0, 0.97, 0.9])                                                     # yellowed
face = Image.fromarray((np.clip(fa, 0, 1) * 255).astype(np.uint8)).resize((fs, fs), Image.LANCZOS)
atlas.paste(face, (fx, fy)); region("clockface", fx, fy, fx + fs, fy + fs)

atlas = atlas.filter(ImageFilter.GaussianBlur(0.8))
# overall yellowing / grime noise
a = np.asarray(atlas, np.float32) / 255
n = np.asarray(Image.fromarray((np.random.RandomState(3).rand(64, 64) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC), np.float32) / 255
a = a * (0.9 + 0.1 * n[..., None]) * np.array([1.0, 0.97, 0.88])
Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save("tex/papers.png")
with open("tex/regions.txt", "w") as f:
    for k, v in regions.items(): f.write(k + " " + " ".join(f"{x:.5f}" for x in v) + "\n")
print(regions.keys())
