"""offline check of place_exterior.layout(): stub 'unreal', run, draw a top-down map."""
import sys, types, random, math
u = types.ModuleType("unreal")
class _Any:
    def __getattr__(self, k): return _Any()
    def __call__(self, *a, **k): return _Any()
u.EditorAssetLibrary = _Any(); u.get_editor_subsystem = lambda *a: _Any(); u.EditorActorSubsystem = None; u.UnrealEditorSubsystem = None
u.log = print; u.log_warning = print
sys.modules["unreal"] = u
import runpy
mod = runpy.run_path("place_exterior.py", run_name="test")
from PIL import Image, ImageDraw
cars = [dict(key="car%d" % i, length=450, width=180) for i in range(5)]
for case, (bmin, bmax, side, ent, land) in enumerate([((-1500, -1000), (1500, 1000), "-Y", 300, (-15000, -14000, 15000, 9000)), ((0, 0), (3200, 3200), "+Y", 900, (-10000, -8000, 13000, 12000))]):
    items, Z = mod["layout"](bmin, bmax, side, ent, random.Random(7), cars, land)
    F = Z["frame"]
    S = 0.03; OX, OY = 450 - (land[0] + land[2]) / 2 * 0.03, 450 + (land[1] + land[3]) / 2 * 0.03
    im = Image.new("RGB", (900, 900), (60, 56, 44)); d = ImageDraw.Draw(im)
    P = lambda x, y: (OX + x * S, OY - y * S)
    d.rectangle([P(land[0], land[3]), P(land[2], land[1])], outline=(255, 255, 255))
    d.rectangle([P(bmin[0], bmax[1]), P(bmax[0], bmin[1])], fill=(150, 150, 160))
    def rect(x, y, yaw, L, Wd, col):
        r = math.radians(yaw); c, s_ = math.cos(r), math.sin(r)
        pts = [(x + c * dx - s_ * dy, y + s_ * dx + c * dy) for dx, dy in ((-L/2, -Wd/2), (L/2, -Wd/2), (L/2, Wd/2), (-L/2, Wd/2))]
        d.polygon([P(*p) for p in pts], fill=col)
    size = {"tile": (800, 800, (70, 70, 72)), "line": (500, 12, (220, 220, 210)), "curb": (200, 15, (170, 170, 160)),
            "stop": (180, 20, (190, 190, 180)), "stop_broken": (180, 20, (190, 150, 150)), "barrier": (420, 30, (220, 180, 0)),
            "booth": (200, 150, (120, 140, 200)), "sign": (40, 40, (0, 100, 255)), "cone": (40, 40, (255, 120, 0)),
            "jersey": (200, 60, (200, 200, 200)), "dumpster": (140, 100, (40, 140, 60)), "container": (606, 244, (40, 80, 160)),
            "lamp": (60, 60, (255, 255, 0)), "lamp_broken": (60, 60, (255, 120, 0)), "post": (20, 20, (255, 255, 255))}
    pivot_x = {"fence": 300, "fence_dmg": 300, "gate": 800}
    for it in sorted(items, key=lambda i: 0 if i["key"] == "tile" else 1):
        x, y = F.world(it["a"], it["d"]) if "a" in it else (it["x"], it["y"])
        k = it["key"]
        if k in pivot_x:
            r_ = math.radians(it["yaw"]); L_ = pivot_x[k]
            col = (230, 230, 230) if k == "fence" else ((255, 80, 80) if k == "fence_dmg" else (0, 255, 255))
            d.line([P(x, y), P(x + math.cos(r_) * L_, y + math.sin(r_) * L_)], fill=col, width=2)
            ox_, oy_ = x + math.cos(r_) * L_ / 2, y + math.sin(r_) * L_ / 2
            nx_, ny_ = math.cos(r_ - math.pi / 2), math.sin(r_ - math.pi / 2)   # local -Y = outside
            d.line([P(ox_, oy_), P(ox_ + nx_ * 150, oy_ + ny_ * 150)], fill=(255, 0, 255), width=1)
        elif k in size: rect(x, y, it["yaw"], *size[k])
        elif k.startswith("car"): rect(x, y, it["yaw"], 450, 180, (140, 60, 40))
        elif k.startswith("tree") or k == "bush":
            r = {"tree_a": 300, "tree_b": 250, "tree_dead": 180, "bush": 90}[k] * it["scale"] * S
            px, py = P(x, y); d.ellipse([px - r, py - r, px + r, py + r], outline=(40, 160, 40) if k != "tree_dead" else (120, 90, 60), width=2)
        elif k.startswith("grass"):
            px, py = P(x, y); d.point((px, py), fill=(120, 170, 60))
        elif k.startswith("weed"):
            px, py = P(x, y); d.point((px, py), fill=(140, 200, 60))
    ex, ey = F.world(Z["a_ent"], 0); px, py = P(ex, ey); d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(255, 0, 0))
    im.save("out/layout_%d.png" % case)
    from collections import Counter
    print(case, Counter(i["key"] if not i["key"].startswith("car") else "car" for i in items))
