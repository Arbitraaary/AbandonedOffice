# Generic, unreadable office page textures (no real text/brands)
from PIL import Image, ImageDraw, ImageFilter
import random, sys
OUT = sys.argv[1]
W, H = 1024, 1448
def base(col=(244, 242, 236)):
    im = Image.new("RGB", (W, H), col); return im, ImageDraw.Draw(im)
def words(d, x0, x1, y, h=7, col=(80, 80, 86), rnd=random):
    x = x0
    while x < x1 - 30:
        w = rnd.randint(14, 70)
        if x + w > x1: break
        d.rectangle([x, y, x + w, y + h], fill=col)
        x += w + rnd.randint(7, 11)
def paragraph(d, y, lines, rnd, x0=110, x1=914, lh=21):
    for i in range(lines):
        end = x1 if i < lines - 1 else rnd.randint(x0 + 150, x1)
        words(d, x0, end, y, rnd=rnd); y += lh
    return y + 16
def page_print(seed):
    rnd = random.Random(seed); im, d = base()
    d.rectangle([110, 90, 260, 140], fill=(40, 70, 120))          # generic logo block
    words(d, 600, 914, 100, col=(90, 90, 95), rnd=rnd); words(d, 650, 914, 122, col=(90, 90, 95), rnd=rnd)
    d.rectangle([110, 200, 600, 222], fill=(30, 30, 35))           # title bar
    y = 270
    while y < 1150:
        y = paragraph(d, y, rnd.randint(3, 7), rnd)
    d.line([110, 1300, 914, 1300], fill=(150, 150, 150), width=2)
    words(d, 110, 500, 1320, col=(120, 120, 125), rnd=rnd)
    return im
def page_table(seed):
    rnd = random.Random(seed); im, d = base((246, 245, 240))
    d.rectangle([110, 90, 914, 130], fill=(40, 70, 120))
    words(d, 110, 600, 170, rnd=rnd)
    cols = [110, 300, 520, 700, 914]
    for r in range(28):
        y = 230 + r * 36
        d.line([110, y, 914, y], fill=(170, 175, 185), width=2)
        if r % 2: d.rectangle([111, y + 1, 913, y + 35], fill=(232, 236, 242))
        for c in range(4):
            words(d, cols[c] + 10, cols[c] + rnd.randint(60, cols[c + 1] - cols[c] - 10), y + 13, h=8, rnd=rnd)
    for x in cols: d.line([x, 230, x, 230 + 28 * 36], fill=(170, 175, 185), width=2)
    return im
def page_ruled(seed):
    rnd = random.Random(seed); im, d = base((247, 246, 238))
    for y in range(160, H - 60, 44): d.line([0, y, W, y], fill=(150, 180, 215), width=2)
    d.line([130, 0, 130, H], fill=(225, 120, 120), width=2)
    ink = (35, 50, 120)
    for y in range(160, rnd.randint(700, 1300), 44):           # handwriting-like squiggles
        x = 150 + rnd.randint(0, 30)
        while x < rnd.randint(650, 950):
            pts = []; wl = rnd.randint(30, 110)
            for k in range(0, wl, 4):
                pts.append((x + k, y - 8 - rnd.randint(0, 22) * (1 if k % 8 else 0.3)))
            d.line(pts, fill=ink, width=3); x += wl + rnd.randint(14, 30)
    return im
def sticky(seed):
    rnd = random.Random(seed); im = Image.new("RGB", (W, W), (238, 212, 92)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 90], fill=(226, 198, 80))
    ink = (25, 30, 60)
    for y in range(260, 760, 120):
        x = 120
        while x < rnd.randint(500, 880):
            pts = [(x + k, y - rnd.randint(0, 50)) for k in range(0, rnd.randint(60, 160), 10)]
            d.line(pts, fill=ink, width=7); x += 200
    return im
for name, fn in [("page_print_a", lambda: page_print(1)), ("page_print_b", lambda: page_print(2)),
                 ("page_table", lambda: page_table(3)), ("page_ruled", lambda: page_ruled(4)),
                 ("sticky", lambda: sticky(5))]:
    fn().filter(ImageFilter.GaussianBlur(0.7)).save(f"{OUT}/{name}.png")
print("ok")
