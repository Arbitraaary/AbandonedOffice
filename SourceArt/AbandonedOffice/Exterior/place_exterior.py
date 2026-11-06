"""
Lay out the whole map around the abandoned office on the CURRENT level (OfficeMap):
a fenced compound (chain-link with barbed wire, some sections broken / leaning / down), parking lot with old cars
in front of the entrance, a long driveway to the gate with the checkpoint (guard booth, broken barrier, concrete blocks),
a public road outside the gate across the map, street lamps, containers and dumpsters in the yard,
groves inside the fence, a forest belt out to the edge of the landscape, grass everywhere, ivy on the walls.

Run in Unreal Editor with OfficeMap open (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Exterior/place_exterior.py"

Safe to re-run: everything it placed before (tag AO_Exterior) is removed first. One Ctrl+Z undoes a run.
Tweak the settings below (seed, entrance side, how many cars / trees) and run again.
"""
import math
import os
import random
import runpy
import unreal

# ================================================================= settings
SEED = 7                 # change for a different arrangement
FRONT = "auto"           # entrance side: "auto" | "camera" | "+X" | "-X" | "+Y" | "-Y"
                         #   auto   = door / barrier post closest to the outer wall, else "camera"
                         #   camera = the side of the building you are looking at in the viewport
CAR_FILL = 0.45          # share of parking stalls with a car in them
TREE_SPACING = 1300.0    # cm between trees in the ring right around the building (sparse - keeps the office readable)
TREE_RING = (900.0, 2000.0)   # distance band from the walls for that ring
GROVES = 7               # clumps of trees inside the fenced compound
FOREST_MAX = 260         # trees outside the fence, out to the edge of the landscape
BELT = (900.0, 4200.0)   # dense tree wall just outside the fence (distance band, cm) - hides the empty horizon
BELT_TREES = 520
BELT_GAP = 560.0         # min distance between belt trees
FOG = True               # light grey distance haze (ExponentialHeightFog) so nothing ends in a hard horizon line
WEEDS = 90
USE_IVY = True
GRASS_PATCHES = 520      # clumps of tall grass spread over the whole map
GROUND_MATERIAL = True   # put the dry-grass / dirt material M_AbandonedGround on the landscape
YARD = (4500.0, 4000.0, 4000.0)   # fenced compound: free ground beside / behind / in front of the lot (cm), clamped to the landscape
ROAD = True              # public road outside the gate, across the whole map

TAG = "AO_Exterior"
ROOT = "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice"
AO = "/Game/_Game/Environment/AbandonedOffice"
M = {
    "tile": AO + "/Exterior/SM_AsphaltTile_8m", "line": AO + "/Exterior/SM_ParkingLine", "curb": AO + "/Exterior/SM_Curb",
    "stop": AO + "/Exterior/SM_WheelStop", "stop_broken": AO + "/Exterior/SM_WheelStop_Broken",
    "tree_a": AO + "/Exterior/SM_Tree_Broadleaf_A", "tree_b": AO + "/Exterior/SM_Tree_Broadleaf_B",
    "tree_dead": AO + "/Exterior/SM_Tree_Dead", "bush": AO + "/Exterior/SM_Bush",
    "weed_grass": AO + "/Exterior/SM_Weeds_Grass", "weed_tall": AO + "/Exterior/SM_Weeds_Tall",
    "grass_a": AO + "/Exterior/SM_GrassPatch_A", "grass_b": AO + "/Exterior/SM_GrassPatch_B",
    "ground": AO + "/Materials/M_AbandonedGround",
    "fence": AO + "/Exterior/SM_Fence_Panel", "fence_dmg": AO + "/Exterior/SM_Fence_PanelDamaged",
    "post": AO + "/Exterior/SM_Fence_Post", "gate": AO + "/Exterior/SM_FenceGate_8m",
    "lamp": AO + "/Exterior/SM_StreetLamp", "lamp_broken": AO + "/Exterior/SM_StreetLamp_Broken",
    "jersey": AO + "/Exterior/SM_JerseyBarrier", "dumpster": AO + "/Exterior/SM_Dumpster", "container": AO + "/Exterior/SM_Container20",
    "booth": AO + "/Parking/SM_GuardBooth", "barrier": AO + "/Parking/SM_BoomBarrierBroken",
    "sign": AO + "/Parking/SM_ParkingSignBent", "cone": AO + "/TrafficCone/SM_TrafficCone",
}
KITS = {"Exterior": ["tile", "line", "curb", "stop", "stop_broken", "tree_a", "tree_b", "tree_dead", "bush", "weed_grass", "weed_tall",
                     "grass_a", "grass_b", "ground", "fence", "fence_dmg", "post", "gate", "lamp", "lamp_broken",
                     "jersey", "dumpster", "container"],
        "ParkingGate": ["booth", "barrier"], "ParkingSign": ["sign"], "TrafficCone": ["cone"]}
CARS = ["/Game/RustyCarsFree/Geometries/SM_asset_%02d" % i for i in range(5)]
IVY = ["/Game/RustyCarsFree/Geometries/SM_ivy_%02d" % i for i in range(12)]
SHELL = ("SM_Wall", "SM_roof", "SM_Floor", "SM_floor", "SM_glass", "SM_Door", "SM_door", "SM_Stair")

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


def log(msg):
    unreal.log("[AbandonedOffice/Exterior] " + msg)


def warn(msg):
    unreal.log_warning("[AbandonedOffice/Exterior] " + msg)


# ================================================================= pure layout (no Unreal calls; tested offline)
class Frame:
    """building-side frame: a = along the wall (t), d = away from the wall (n); origin on the wall line"""
    def __init__(self, ox, oy, nx, ny):
        self.ox, self.oy, self.nx, self.ny = ox, oy, nx, ny
        self.tx, self.ty = -ny, nx

    def world(self, a, d):
        return (self.ox + self.tx * a + self.nx * d, self.oy + self.ty * a + self.ny * d)

    def yaw_t(self):
        return math.degrees(math.atan2(self.ty, self.tx))

    def yaw_n(self):
        return math.degrees(math.atan2(self.ny, self.nx))


def layout(bmin, bmax, side, entrance, rng, cars, land=None):
    """
    bmin/bmax: building footprint (x, y) in cm; side: '+X' | '-X' | '+Y' | '-Y'; entrance: coordinate along that wall.
    cars: list of dicts {key, length, width} (length = long axis, cm). land: landscape (x0, y0, x1, y1) or None.
    Returns (items, zones). item = dict(key, a, d | x, y, yaw, roll, scale, group, ground: 'lot'|'terrain'|'drive', label)
    All lot items use frame coords (a, d); trees etc. use world (x, y).
    """
    cx, cy = (bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2
    if side in ("+X", "-X"):
        sgn = 1 if side == "+X" else -1
        F = Frame(bmax[0] if sgn > 0 else bmin[0], cy, sgn, 0)
        a_lo, a_hi = sorted(((bmin[1] - cy) * F.ty, (bmax[1] - cy) * F.ty))
        a_ent = (entrance - cy) * F.ty
    else:
        sgn = 1 if side == "+Y" else -1
        F = Frame(cx, bmax[1] if sgn > 0 else bmin[1], 0, sgn)
        a_lo, a_hi = sorted(((bmin[0] - cx) * F.tx, (bmax[0] - cx) * F.tx))
        a_ent = (entrance - cx) * F.tx
    side_len = a_hi - a_lo
    T = 800.0
    ntw = max(3, min(6, int(round(side_len * 0.9 / T))))
    W = ntw * T
    a0 = min(max(a_ent - W / 2, a_lo - 400), a_hi + 400 - W)
    D0, ntd = 100.0, 3
    LOT_D = D0 + ntd * T                                       # far edge of the lot
    items = []

    def add(key, group, label, yaw=0.0, roll=0.0, scale=1.0, ground="lot", **pos):
        items.append(dict(key=key, group=group, label=label, yaw=yaw, roll=roll, scale=scale, ground=ground, **pos))

    # ---- asphalt
    for i in range(ntw):
        for j in range(ntd):
            add("tile", "Parking", "Asphalt_%d_%d" % (i, j), yaw=F.yaw_t(), a=a0 + T / 2 + i * T, d=D0 + T / 2 + j * T)
    drive_a = a0 + W - T / 2 if a_ent <= a0 + W / 2 else a0 + T / 2     # driveway at the lot end away from the door
    # ---- compound (frame coords) clamped to the landscape
    depth = (bmax[0] - bmin[0]) if side in ("+X", "-X") else (bmax[1] - bmin[1])
    if land:
        cs = []
        for x, y in ((land[0], land[1]), (land[2], land[1]), (land[0], land[3]), (land[2], land[3])):
            rx, ry = x - F.ox, y - F.oy
            cs.append((rx * F.tx + ry * F.ty, rx * F.nx + ry * F.ny))
        LA0, LA1 = min(c[0] for c in cs), max(c[0] for c in cs); LD0, LD1 = min(c[1] for c in cs), max(c[1] for c in cs)
    else:
        LA0, LA1, LD0, LD1 = a_lo - 20000, a_hi + 20000, -depth - 20000, LOT_D + 20000
    A_L = max(min(a_lo, a0) - YARD[0], LA0 + 1500); A_R = min(max(a_hi, a0 + W) + YARD[0], LA1 - 1500)
    A_L = min(A_L, a0 - 800, a_lo - 800); A_R = max(A_R, a0 + W + 800, a_hi + 800)
    D_B = min(max(-depth - YARD[1], LD0 + 1500), -depth - 800)
    ndrive = int(max(2, round(min(YARD[2], LD1 - 3200 - LOT_D) / T)))
    D_F = LOT_D + ndrive * T                                     # front fence line / gate
    road = ROAD and D_F + 1600 < LD1 - 200
    slabs = {}

    def slab(sid, a, d):
        slabs[sid] = (a, d); return "slab:" + sid
    for j in range(ndrive):
        add("tile", "Parking", "Driveway_%d" % j, yaw=F.yaw_t(), a=drive_a, d=LOT_D + T / 2 + j * T, ground=slab("d%d" % j, drive_a, LOT_D + T / 2 + j * T))
    drive_slab = lambda d: "slab:d%d" % max(0, min(ndrive - 1, int((d - LOT_D) // T)))
    # ---- stalls: two rows, cars nose-in
    SW, SD = 260.0, 500.0
    rows = [(D0 + 250.0, D0 + 250.0 + SD), (LOT_D - 450.0 - SD, LOT_D - 450.0)]
    n_st = int((W - 300) // SW)
    s0 = a0 + (W - n_st * SW) / 2
    stalls = []
    for r, (d1, d2) in enumerate(rows):
        for k in range(n_st + 1):
            if r == 1 and abs((s0 + k * SW) - drive_a) < T / 2 - 50:
                continue                                         # keep the driveway mouth clear
            add("line", "Parking", "Line_%d_%d" % (r, k), yaw=F.yaw_n(), a=s0 + k * SW, d=(d1 + d2) / 2)
        for k in range(n_st):
            ac = s0 + (k + 0.5) * SW
            if r == 1 and abs(ac - drive_a) < T / 2:
                continue
            stalls.append((r, ac, d1, d2))
            u = rng.random()
            if u < 0.55:
                stop_d = d1 + 60 if r == 0 else d2 - 60
                key = "stop_broken" if u < 0.12 else "stop"
                add(key, "Parking", "WheelStop_%d_%d" % (r, k), yaw=F.yaw_t() + rng.uniform(-6, 6) + (180 if rng.random() < 0.5 else 0),
                    a=ac + rng.uniform(-15, 15), d=stop_d + rng.uniform(-8, 8))
    # ---- cars
    if cars:
        free = stalls[:]; rng.shuffle(free)
        ncar = int(len(free) * CAR_FILL)
        for c, (r, ac, d1, d2) in enumerate(free[:ncar]):
            car = cars[c % len(cars)] if c < len(cars) else rng.choice(cars)
            nose = 0 if r == 0 else 180                           # nose towards the row's end line
            yaw = F.yaw_n() + 180 + nose + rng.uniform(-7, 7) + (180 if rng.random() < 0.25 else 0)
            add(car["key"], "Cars", "OldCar_%02d" % c, yaw=yaw, a=ac + rng.uniform(-30, 30), d=(d1 + d2) / 2 + rng.uniform(-40, 40))
        # one left across the aisle at an angle, one dumped on the dirt next to the lot
        car = rng.choice(cars)
        add(car["key"], "Cars", "OldCar_Aisle", yaw=F.yaw_t() + rng.choice([-1, 1]) * rng.uniform(25, 40),
            a=a0 + W * rng.uniform(0.3, 0.6), d=(rows[0][1] + rows[1][0]) / 2)
        car = rng.choice(cars)
        side_a = a0 - 450 if drive_a > a0 + W / 2 else a0 + W + 450
        add(car["key"], "Cars", "OldCar_Dirt", yaw=F.yaw_n() + rng.uniform(-20, 20), a=side_a, d=LOT_D * 0.55, ground="terrain")
    # ---- curbs around the lot (gaps: entrance path, driveway mouth), some missing / shoved
    def curb_run(a1, d1, a2, d2, name, skip=None):
        L = math.hypot(a2 - a1, d2 - d1); n = int(L // 200)
        yaw = F.yaw_t() if abs(d2 - d1) < 1 else F.yaw_n()
        for k in range(n):
            t = (k + 0.5) / n
            a, d = a1 + (a2 - a1) * t, d1 + (d2 - d1) * t
            if skip and skip(a, d):
                continue
            if rng.random() < 0.07:
                continue
            j = rng.uniform(-2.5, 2.5) if rng.random() > 0.08 else rng.uniform(10, 25)
            add("curb", "Parking", "%s_%02d" % (name, k), yaw=yaw + j, a=a, d=d)
    curb_run(a0, D0, a0 + W, D0, "CurbNear", skip=lambda a, d: abs(a - a_ent) < 250)
    curb_run(a0, LOT_D, a0 + W, LOT_D, "CurbFar", skip=lambda a, d: abs(a - drive_a) < T / 2)
    curb_run(a0, D0, a0, LOT_D, "CurbL")
    curb_run(a0 + W, D0, a0 + W, LOT_D, "CurbR")
    # ---- gate + checkpoint just inside it
    dl, dr = drive_a - T / 2, drive_a + T / 2
    out_side = -1 if drive_a > a0 + W / 2 else 1                 # booth stands on the side facing the yard
    edge_a = dl if out_side < 0 else dr
    add("gate", "Checkpoint", "Gate", yaw=F.yaw_t(), a=dl, d=D_F, ground="terrain")
    bar_d = D_F - 600
    add("barrier", "Checkpoint", "BoomBarrier", yaw=F.yaw_t() if out_side < 0 else F.yaw_t() + 180, a=edge_a + out_side * 60, d=bar_d,
        ground=drive_slab(bar_d))
    add("booth", "Checkpoint", "GuardBooth", yaw=(F.yaw_t() if out_side < 0 else F.yaw_t() + 180) - 90,
        a=edge_a + out_side * 330, d=bar_d - 150, ground="terrain")
    add("sign", "Checkpoint", "ParkingSign", yaw=F.yaw_n() - 90 + rng.uniform(-15, 15), a=edge_a + out_side * 120, d=LOT_D + 150, ground="terrain")
    for k in range(5):
        cd = bar_d + rng.uniform(-300, 350)
        add("cone", "Checkpoint", "Cone_%d" % k, yaw=rng.uniform(0, 360), roll=90 if k == 2 else 0,
            a=drive_a + rng.uniform(-T / 2 + 80, T / 2 - 80), d=cd, ground=drive_slab(cd))
    for k, (da, dd, jy) in enumerate([(-220, -1300, 8), (230, -1700, -12), (-200, -2300, 4), (out_side * 520, -400, 90)]):
        cd = D_F + dd                                              # concrete blocks: a chicane on the driveway
        add("jersey", "Checkpoint", "Jersey_%d" % k, yaw=F.yaw_t() + jy + rng.uniform(-6, 6), a=drive_a + da, d=cd,
            ground=drive_slab(cd) if abs(da) < T / 2 else "terrain")
    # ---- perimeter fence: walk each edge so the barbed-wire arms lean outside
    def fence_edge(start, end, yaw, name, gate_gap=None):
        (a1, d1), (a2, d2) = start, end
        L = math.hypot(a2 - a1, d2 - d1); n = int(L // 300)
        ea, ed = (a2 - a1) / L, (d2 - d1) / L
        for k in range(n):
            a, d = a1 + ea * 300 * k, d1 + ed * 300 * k
            if gate_gap and gate_gap[0] - 300 < a < gate_gap[1]:
                continue
            u = rng.random()
            if u < 0.05:
                continue                                           # section gone
            key, roll = ("fence_dmg", 0.0) if u < 0.20 else ("fence", 0.0)
            if 0.20 <= u < 0.28: roll = rng.choice([-1, 1]) * rng.uniform(8, 16)        # leaning
            if 0.28 <= u < 0.33: key, roll = "fence_dmg", rng.choice([-1, 1]) * 84         # flattened
            add(key, "Fence", "%s_%03d" % (name, k), yaw=yaw + rng.uniform(-1.5, 1.5), roll=roll, a=a, d=d, ground="terrain")
    fence_edge((A_L, D_F), (A_R, D_F), F.yaw_t(), "FenceFront", gate_gap=(dl, dr))
    fence_edge((A_R, D_F), (A_R, D_B), F.yaw_n() + 180, "FenceRight")
    fence_edge((A_R, D_B), (A_L, D_B), F.yaw_t() + 180, "FenceBack")
    fence_edge((A_L, D_B), (A_L, D_F), F.yaw_n(), "FenceLeft")
    for k, (a, d) in enumerate(((A_L, D_F), (A_R, D_F), (A_R, D_B), (A_L, D_B), (dl - 1, D_F), (dr + 1, D_F))):
        add("post", "Fence", "FencePost_%d" % k, yaw=F.yaw_t(), a=a, d=d, ground="terrain")
    # ---- road outside the gate + connector
    d_r = D_F + 1200
    road_a = []
    if road:
        add("tile", "Road", "RoadLink", yaw=F.yaw_t(), a=drive_a, d=D_F + T / 2, ground=slab("link", drive_a, D_F + T / 2))
        k0 = int(math.floor((LA0 + 200 - drive_a) / T)); k1 = int(math.ceil((LA1 - 200 - drive_a) / T))
        for kk in range(max(k0, -60), min(k1, 60) + 1):
            a = drive_a + kk * T
            if a - T / 2 < LA0 or a + T / 2 > LA1:
                continue
            road_a.append(a)
            sid = "r%d" % kk
            add("tile", "Road", "Road_%03d" % (kk + 60), yaw=F.yaw_t(), a=a, d=d_r, ground=slab(sid, a, d_r))
            for h in (-250, 250):                                 # dashed centre line
                if rng.random() < 0.85:
                    add("line", "Road", "RoadLine_%03d_%d" % (kk + 60, h > 0), yaw=F.yaw_t(), a=a + h, d=d_r, ground="slab:" + sid)
        for k, a in enumerate(road_a[::3]):                       # street lamps between fence and road, arms over the road
            if rng.random() < 0.12:
                continue
            key = "lamp_broken" if rng.random() < 0.25 else "lamp"
            add(key, "Road", "RoadLamp_%02d" % k, yaw=F.yaw_n() + 90 + (rng.uniform(-8, 8) if key == "lamp" else rng.uniform(-40, 40)),
                a=a + rng.uniform(-100, 100), d=D_F + 600, ground="terrain")
    for k, dd in enumerate(range(int(LOT_D + 500), int(D_F - 300), 1700)):   # lamps along the driveway, alternating sides
        sgn = -1 if k % 2 == 0 else 1
        key = "lamp_broken" if rng.random() < 0.25 else "lamp"
        yaw = (F.yaw_t() + 90) if sgn < 0 else (F.yaw_t() - 90)
        add(key, "Checkpoint", "DriveLamp_%02d" % k, yaw=yaw + rng.uniform(-6, 6), a=drive_a + sgn * 520, d=dd, ground="terrain")
    # ---- yard props: containers on the side away from the driveway, dumpsters behind, blocks
    yard_side = -1 if drive_a > a0 + W / 2 else 1
    ya = (a_lo - 1700) if yard_side < 0 else (a_hi + 1700)
    for k in range(3):
        add("container", "Yard", "Container_%d" % k, yaw=F.yaw_n() + rng.uniform(-6, 6) + (90 if k == 2 else 0),
            a=ya + yard_side * (k % 2) * 380 + (yard_side * 900 if k == 2 else 0), d=-depth * (0.25 + 0.3 * k) + rng.uniform(-150, 150),
            ground="terrain")
    for k in range(3):
        add("dumpster", "Yard", "Dumpster_%d" % k, yaw=F.yaw_t() + 180 + rng.uniform(-15, 15),
            a=a_lo + (a_hi - a_lo) * (0.2 + 0.3 * k) + rng.uniform(-100, 100), d=-depth - 220, ground="terrain")
    for k in range(3):
        add("jersey", "Yard", "YardJersey_%d" % k, yaw=F.yaw_n() + rng.uniform(-20, 20),
            a=ya + yard_side * (1700 + 210 * k), d=-depth * 0.5 + rng.uniform(-60, 60), ground="terrain")
    # ---- weeds through the cracks / along the curbs, walls and fence
    for k in range(WEEDS):
        u = rng.random()
        if u < 0.35:
            a, d = rng.uniform(a0 + 50, a0 + W - 50), rng.uniform(D0 + 30, LOT_D - 30); g = "lot"
        elif u < 0.55:
            e = rng.choice([D0 + 25, LOT_D - 25]); a, d = rng.uniform(a0, a0 + W), e; g = "lot"
        elif u < 0.75:
            a, d = rng.uniform(a_lo - 300, a_hi + 300), rng.uniform(20, 90); g = "terrain"
        else:
            a, d = drive_a + rng.choice([-1, 1]) * rng.uniform(380, 430), rng.uniform(LOT_D, D_F); g = "terrain"
        add(rng.choice(["weed_grass", "weed_grass", "weed_tall"]), "Weeds", "Weeds_%03d" % k, yaw=rng.uniform(0, 360),
            scale=rng.uniform(0.7, 1.35), a=a, d=d, ground=g)
    # ---- trees
    def frame_of(x, y):
        rx, ry = x - F.ox, y - F.oy
        return rx * F.tx + ry * F.ty, rx * F.nx + ry * F.ny

    def blocked(a, d, margin=0.0):
        if a0 - 350 - margin < a < a0 + W + 350 + margin and -300 - margin < d < LOT_D + 300 + margin:
            return True                                            # lot
        if abs(a - drive_a) < T / 2 + 350 + margin and LOT_D - 300 < d < D_F + (T + 200 if road else 300):
            return True                                            # driveway + link
        if road and d_r - T / 2 - 350 - margin < d < d_r + T / 2 + 350 + margin and LA0 < a < LA1:
            return True                                            # road
        if a_lo - 200 - margin < a < a_hi + 200 + margin and -depth - 200 - margin < d < 200 + margin:
            return True                                            # building
        return False
    inside = lambda a, d, m=300: A_L + m < a < A_R - m and D_B + m < d < D_F - m
    placed = []
    for it in items:                                             # keep trees off cars, checkpoint and yard props
        if it["group"] in ("Cars", "Checkpoint", "Yard") and "a" in it:
            placed.append(F.world(it["a"], it["d"]))

    def try_tree(x, y, kinds, label, min_gap=600, need=None):
        a, d = frame_of(x, y)
        if blocked(a, d) or (need is not None and not need(a, d)):
            return False
        if any((x - px) ** 2 + (y - py) ** 2 < min_gap ** 2 for px, py in placed):
            return False
        placed.append((x, y))
        key = rng.choices([k for k, _ in kinds], [w for _, w in kinds])[0]
        add(key, "Trees", label, yaw=rng.uniform(0, 360), scale=rng.uniform(0.85, 1.25), x=x, y=y, ground="terrain")
        return True
    MIX = [("tree_a", 0.38), ("tree_b", 0.32), ("tree_dead", 0.2), ("bush", 0.1)]
    per = 2 * ((bmax[0] - bmin[0]) + (bmax[1] - bmin[1]) + 4 * TREE_RING[1])
    nring = int(per / TREE_SPACING)
    n0 = len(placed)
    for k in range(nring * 5):                                    # sparse ring right around the office
        if len(placed) - n0 >= nring:
            break
        off = rng.uniform(*TREE_RING)
        x0, x1, y0, y1 = bmin[0] - off, bmax[0] + off, bmin[1] - off, bmax[1] + off
        s = rng.uniform(0, 2 * (x1 - x0) + 2 * (y1 - y0))
        if s < x1 - x0: x, y = x0 + s, y0
        elif s < 2 * (x1 - x0): x, y = x0 + s - (x1 - x0), y1
        elif s < 2 * (x1 - x0) + (y1 - y0): x, y = x0, y0 + s - 2 * (x1 - x0)
        else: x, y = x1, y0 + s - 2 * (x1 - x0) - (y1 - y0)
        try_tree(x, y, MIX, "Tree_%02d" % k, 900, need=inside)
    for g in range(GROVES):                                       # groves inside the fence
        for att in range(40):
            ga, gd = rng.uniform(A_L + 800, A_R - 800), rng.uniform(D_B + 800, D_F - 800)
            if not blocked(ga, gd, 900):
                break
        for k in range(rng.randint(4, 9)):
            r = 900 * math.sqrt(rng.random()); ang = rng.uniform(0, 2 * math.pi)
            x, y = F.world(ga + math.cos(ang) * r, gd + math.sin(ang) * r)
            try_tree(x, y, [("tree_a", 0.45), ("tree_b", 0.35), ("tree_dead", 0.12), ("bush", 0.08)], "Grove%d_%d" % (g, k), 480, need=inside)
    nb = 0
    BMIX = [("tree_a", 0.44), ("tree_b", 0.4), ("tree_dead", 0.08), ("bush", 0.08)]
    for k in range(BELT_TREES * 10):                              # dense belt hugging the fence on the outside
        if nb >= BELT_TREES:
            break
        off = BELT[0] + (BELT[1] - BELT[0]) * rng.random() ** 0.8
        x0, x1, y0, y1 = A_L - off, A_R + off, D_B - off, D_F + off
        t = rng.uniform(0, 2 * (x1 - x0) + 2 * (y1 - y0))
        if t < x1 - x0: a, d = x0 + t, y0
        elif t < 2 * (x1 - x0): a, d = x0 + t - (x1 - x0), y1
        elif t < 2 * (x1 - x0) + (y1 - y0): a, d = x0, y0 + t - 2 * (x1 - x0)
        else: a, d = x1, y0 + t - 2 * (x1 - x0) - (y1 - y0)
        a += rng.uniform(-250, 250); d += rng.uniform(-250, 250)
        if not (LA0 + 200 < a < LA1 - 200 and LD0 + 200 < d < LD1 - 200):
            continue
        x, y = F.world(a, d)
        if try_tree(x, y, BMIX, "Belt_%03d" % nb, BELT_GAP):
            nb += 1
    nf = 0
    for k in range(FOREST_MAX * 6):                               # forest belt outside the fence, to the landscape edge
        if nf >= FOREST_MAX:
            break
        a, d = rng.uniform(LA0 + 200, LA1 - 200), rng.uniform(LD0 + 200, LD1 - 200)
        if A_L - 400 < a < A_R + 400 and D_B - 400 < d < D_F + 400:
            continue
        x, y = F.world(a, d)
        if try_tree(x, y, [("tree_a", 0.42), ("tree_b", 0.38), ("tree_dead", 0.12), ("bush", 0.08)], "Forest_%03d" % nf, 850):
            nf += 1
    for k in range(int(W // 700)):                               # row along the far side of the lot
        a = a0 + 250 + k * 700 + rng.uniform(-80, 80)
        if abs(a - drive_a) < T / 2 + 250:
            continue
        x, y = F.world(a, LOT_D + 550 + rng.uniform(-80, 120))
        placed.append((x, y))
        key = rng.choices(["tree_a", "tree_b", "tree_dead"], [0.45, 0.4, 0.15])[0]
        add(key, "Trees", "LotTree_%02d" % k, yaw=rng.uniform(0, 360), scale=rng.uniform(0.9, 1.15), x=x, y=y, ground="terrain")
    for k in range(10):                                          # bushes hugging the walls
        s = rng.choice(["x0", "x1", "y0", "y1"]); off = rng.uniform(250, 420)
        if s in ("x0", "x1"):
            x = (bmin[0] - off) if s == "x0" else (bmax[0] + off); y = rng.uniform(bmin[1], bmax[1])
        else:
            y = (bmin[1] - off) if s == "y0" else (bmax[1] + off); x = rng.uniform(bmin[0], bmax[0])
        a, d = frame_of(x, y)
        if not (a0 - 350 < a < a0 + W + 350 and -300 < d < LOT_D + 300):
            add("bush", "Trees", "Bush_%02d" % k, yaw=rng.uniform(0, 360), scale=rng.uniform(0.8, 1.3), x=x, y=y, ground="terrain")
    # ---- grass over the whole map (denser inside the fence)
    g_rng = random.Random(rng.random())
    ng = 0
    for k in range(GRASS_PATCHES * 6):
        if ng >= GRASS_PATCHES:
            break
        if g_rng.random() < 0.55:
            a, d = g_rng.uniform(A_L, A_R), g_rng.uniform(D_B, D_F)
        else:
            a, d = g_rng.uniform(LA0 + 100, LA1 - 100), g_rng.uniform(LD0 + 100, LD1 - 100)
        if blocked(a, d, -250):
            continue
        x, y = F.world(a, d)
        add("grass_a" if g_rng.random() < 0.6 else "grass_b", "Grass", "Grass_%03d" % ng, yaw=g_rng.uniform(0, 360),
            scale=g_rng.uniform(0.8, 1.35), x=x, y=y, ground="terrain")
        ng += 1
    zones = dict(frame=F, a0=a0, W=W, D0=D0, LOT_D=LOT_D, drive_a=drive_a, a_ent=a_ent, a_lo=a_lo, a_hi=a_hi,
                 A_L=A_L, A_R=A_R, D_B=D_B, D_F=D_F, road=road, d_r=d_r, slabs=slabs, ndrive=ndrive)
    return items, zones


# ================================================================= Unreal side
def ensure_assets():
    missing = [kit for kit, keys in KITS.items() if not all(eal.does_asset_exist(M[k]) for k in keys)]
    if not missing:
        return True
    before = {a.get_path_name() for a in eas.get_all_level_actors()}
    for kit in missing:
        script = os.path.join(ROOT, kit, "import_to_unreal.py")
        log("importing missing kit " + kit)
        try:
            runpy.run_path(script, run_name="__main__")
        except Exception as e:
            warn("could not import %s: %s" % (kit, e))
    extra = [a for a in eas.get_all_level_actors() if a.get_path_name() not in before]
    for a in extra:                                               # kit scripts drop a sample in front of the camera - not wanted here
        eas.destroy_actor(a)
    ok = True
    for kit, keys in KITS.items():
        for k in keys:
            if not eal.does_asset_exist(M[k]):
                warn("missing asset " + M[k]); ok = False
    return ok


def mesh_path(actor):
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp is None:
        return ""
    sm = comp.get_editor_property("static_mesh")
    return sm.get_path_name().split(".")[0] if sm else ""


def has_tag(actor, tag):
    return any(str(t) == tag for t in actor.get_editor_property("tags"))


def building_bounds(actors):
    boxes = []
    for a in actors:
        p = mesh_path(a)
        if p.startswith("/Game/Office_Pack_Vol_1/") and any(s in p for s in SHELL):
            o, e = a.get_actor_bounds(False)
            boxes.append((o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z, o.x, o.y))
    if not boxes:
        return None
    mx = sorted(b[6] for b in boxes)[len(boxes) // 2]; my = sorted(b[7] for b in boxes)[len(boxes) // 2]
    boxes = [b for b in boxes if abs(b[6] - mx) < 15000 and abs(b[7] - my) < 15000]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), min(b[2] for b in boxes),
            max(b[3] for b in boxes), max(b[4] for b in boxes), max(b[5] for b in boxes))


def pick_front(actors, bb):
    x0, y0, z0, x1, y1, z1 = bb
    planes = {"+X": (1, x1), "-X": (-1, x0), "+Y": (1, y1), "-Y": (-1, y0)}

    def nearest(px, py):
        best = None
        for s, (sg, v) in planes.items():
            d = abs((px if "X" in s else py) - v)
            if best is None or d < best[1]:
                best = (s, d, py if "X" in s else px)
        return best
    if FRONT in planes:
        return FRONT, ((y0 + y1) / 2 if "X" in FRONT else (x0 + x1) / 2), "set in FRONT"
    if FRONT == "auto":
        hints = []
        for a in actors:
            p = mesh_path(a)
            name = p.rsplit("/", 1)[-1]
            if name == "SM_BarrierPost":
                l = a.get_actor_location(); s, d, e = nearest(l.x, l.y)
                if d < 1200: hints.append((0, d, s, e, "barrier post"))
            elif p.startswith("/Game/Office_Pack_Vol_1/") and ("Door" in name or "door" in name) and "Cabin" not in name:
                l = a.get_actor_location(); s, d, e = nearest(l.x, l.y)
                if d < 250: hints.append((1, d, s, e, name))
        if hints:
            hints.sort()
            _, d, s, e, why = hints[0]
            return s, e, "%s %.0f cm from the %s wall" % (why, d, s)
    cam = ues.get_level_viewport_camera_info()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if cam:
        loc = cam[0]; dx, dy = loc.x - cx, loc.y - cy
        s = ("+X" if dx > 0 else "-X") if abs(dx) / max(1, x1 - x0) > abs(dy) / max(1, y1 - y0) else ("+Y" if dy > 0 else "-Y")
        return s, (cy if "X" in s else cx), "viewport camera side"
    return "-Y", cx, "default"


def car_infos():
    out = []
    for i, p in enumerate(CARS):
        if not eal.does_asset_exist(p):
            continue
        sm = eal.load_asset(p)
        bb = sm.get_bounding_box()
        sx, sy, sz = bb.max.x - bb.min.x, bb.max.y - bb.min.y, bb.max.z - bb.min.z
        L, Wd = max(sx, sy), min(sx, sy)
        if 280 < L < 750 and 100 < sz < 300 and Wd > 120:
            M["car%d" % i] = p
            out.append(dict(key="car%d" % i, length=L, width=Wd, long_x=sx >= sy,
                            cx=(bb.max.x + bb.min.x) / 2, cy=(bb.max.y + bb.min.y) / 2, zmin=bb.min.z))
        else:
            log("skipping %s (%.0f x %.0f x %.0f cm - not car sized)" % (p.rsplit("/", 1)[-1], sx, sy, sz))
    return out


def hit_info(hit):
    if hit is None:
        return None
    try:
        return hit.get_editor_property("impact_point"), hit.get_editor_property("hit_actor")
    except Exception:
        t = hit.to_tuple()
        return t[5], t[9]


def main():
    rng = random.Random(SEED)
    world = ues.get_editor_world()
    if not ensure_assets():
        warn("some assets are missing - check the log above"); return
    try:                                                    # make sure the leaves / grass material compiles (textured trees)
        runpy.run_path(os.path.join(ROOT, "Exterior", "fix_foliage_material.py"), run_name="__main__")
    except Exception as e:
        warn("foliage material repair failed: %s" % e)
    actors = eas.get_all_level_actors()
    with unreal.ScopedEditorTransaction("Abandoned office exterior"):
        removed = 0
        for a in actors:
            p = mesh_path(a)
            if has_tag(a, TAG) or (has_tag(a, "AbandonedOffice") and p in (M["booth"], M["barrier"], M["sign"])):
                eas.destroy_actor(a); removed += 1
        if removed:
            log("removed %d actor(s) from the previous run" % removed)
        actors = eas.get_all_level_actors()
        bb = building_bounds(actors)
        if bb is None:
            warn("no Office Pack walls/floors found on this level - open OfficeMap first"); return
        x0, y0, z0, x1, y1, z1 = bb
        log("building footprint %.0f x %.0f m, floor z %.0f" % ((x1 - x0) / 100, (y1 - y0) / 100, z0))
        side, ent, why = pick_front(actors, bb)
        log("entrance side %s (%s)" % (side, why))
        cars = car_infos()
        if not cars:
            warn("no car-sized meshes in /Game/RustyCarsFree - parking stays empty")
        land = None
        lps = [a for a in actors if isinstance(a, unreal.LandscapeProxy)]
        if lps:
            bx = []
            for la in lps:
                o, e = la.get_actor_bounds(False)
                bx.append((o.x - e.x, o.y - e.y, o.x + e.x, o.y + e.y))
            land = (min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx))
            log("landscape %.0f x %.0f m" % ((land[2] - land[0]) / 100, (land[3] - land[1]) / 100))
        else:
            warn("no landscape on this level - trees and grass need one to stand on")
        items, Z = layout((x0, y0), (x1, y1), side, ent, rng, cars, land)
        F = Z["frame"]
        log("compound %.0f x %.0f m, gate %.0f m from the entrance, road: %s"
            % ((Z["A_R"] - Z["A_L"]) / 100, (Z["D_F"] - Z["D_B"]) / 100, Z["D_F"] / 100, "yes" if Z["road"] else "no room"))
        ignore = []

        def trace(x, y):
            h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z1 + 20000), unreal.Vector(x, y, z0 - 20000),
                                                       unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                       unreal.DrawDebugTrace.NONE, True)
            r = hit_info(h)
            if r is None:
                return None, False
            pt, act = r
            return pt.z, isinstance(act, unreal.LandscapeProxy)
        # lot height: highest terrain under the lot (+2 cm) so the slab never sinks below the ground
        zs = []
        for i in range(9):
            for j in range(5):
                x, y = F.world(Z["a0"] + Z["W"] * i / 8, Z["D0"] + (Z["LOT_D"] - Z["D0"]) * j / 4)
                z, isl = trace(x, y)
                if z is not None and isl: zs.append(z)
        z_lot = (max(zs) if zs else z0) + 2.0
        if zs and max(zs) - min(zs) > 30:
            warn("terrain under the lot varies by %.0f cm - flatten it a bit with the Landscape tool for a clean edge" % (max(zs) - min(zs)))
        log("parking lot at z %.0f" % z_lot)
        slab_z = {}

        def slab_height(sid):
            if sid not in slab_z:
                sa, sd = Z["slabs"][sid]; cs = []
                for da in (-380, 380):
                    for dd in (-380, 380):
                        zz, isl = trace(*F.world(sa + da, sd + dd))
                        if zz is not None and isl: cs.append(zz)
                slab_z[sid] = max(cs) + 2 if cs else z_lot
            return slab_z[sid]
        # phase 1: ground heights (traces against the clean level - nothing of ours is in the way yet)
        plan = []
        for it in items:
            x, y = F.world(it["a"], it["d"]) if "a" in it else (it["x"], it["y"])
            g = it["ground"]
            if g == "lot":
                z = z_lot
            elif g.startswith("slab:"):
                z = slab_height(g[5:])
            else:
                z, isl = trace(x, y)
                if z is None or not isl:
                    continue                                      # not on the landscape (or over the building) - skip
                if it["key"].startswith("tree") or it["key"] == "bush":
                    z -= 5
            plan.append((it, x, y, z))
        log("planned %d actors - spawning..." % len(plan))
        spawned = []
        meshes = {}

        def spawn(it, x, y, z):
            key = it["key"]
            if key not in meshes:
                meshes[key] = eal.load_asset(M[key])
            yaw = it["yaw"]
            loc = unreal.Vector(x, y, z)
            if key.startswith("car"):                             # foreign pivots: centre the footprint, sit on the ground
                c = next(c for c in cars if c["key"] == key)
                yaw += 0 if c["long_x"] else -90
                r = math.radians(yaw)
                ox, oy = c["cx"] * math.cos(r) - c["cy"] * math.sin(r), c["cx"] * math.sin(r) + c["cy"] * math.cos(r)
                loc = unreal.Vector(x - ox, y - oy, z - c["zmin"])
            if key == "cone" and it["roll"]:
                loc = unreal.Vector(loc.x, loc.y, loc.z + 18)     # knocked-over cone lies on its side
            a = eas.spawn_actor_from_object(meshes[key], loc, unreal.Rotator(it["roll"], 0, yaw))
            if a is None:
                return None
            if it["scale"] != 1.0:
                a.set_actor_scale3d(unreal.Vector(it["scale"], it["scale"], it["scale"]))
            if key.startswith(("tree", "bush", "grass", "weed")):        # Lumen would treat the crowns as solid blobs -> black trees
                comp = a.get_component_by_class(unreal.StaticMeshComponent)
                comp.set_editor_property("affect_distance_field_lighting", False)
                if key.startswith(("grass", "weed")):
                    comp.set_editor_property("cast_shadow", False)
            a.set_actor_label(it["label"])
            a.set_folder_path("AbandonedOffice/Exterior/" + it["group"])
            a.set_editor_property("tags", [TAG])
            spawned.append(a)
            return a
        counts = {}
        with unreal.ScopedSlowTask(len(plan), "Placing the office grounds") as task:
            task.make_dialog(True)
            for it, x, y, z in plan:
                if task.should_cancel():
                    warn("cancelled - %d actors placed" % len(spawned)); break
                task.enter_progress_frame(1)
                if spawn(it, x, y, z) is not None:
                    counts[it["group"]] = counts.get(it["group"], 0) + 1
        ignore.extend(spawned)
        # landscape material: dry grass with bare dirt patches
        if GROUND_MATERIAL:
            gm = eal.load_asset(M["ground"])
            for la in [a for a in eas.get_all_level_actors() if isinstance(a, unreal.LandscapeProxy)]:
                old = la.get_editor_property("landscape_material")
                if old != gm:
                    log("landscape %s: material %s -> M_AbandonedGround (set GROUND_MATERIAL = False to keep yours)"
                        % (la.get_actor_label(), old.get_path_name() if old else "none"))
                    la.set_editor_property("landscape_material", gm)
        # ivy on the walls (RustyCarsFree), away from the entrance
        if USE_IVY:
            ivy = [p for p in IVY if eal.does_asset_exist(p)]
            n_ivy = 0
            for k in range(8 if ivy else 0):
                p = rng.choice(ivy); sm = eal.load_asset(p); b = sm.get_bounding_box()
                ext = (b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z)
                thin = min(range(3), key=lambda i: ext[i])
                if thin == 2 or max(ext) > 2500:
                    continue                                       # lying flat or huge - not a wall piece
                s = rng.choice(["+X", "-X", "+Y", "-Y"])
                if s == side:
                    continue
                if "X" in s:
                    wx = x1 if s == "+X" else x0; wy = rng.uniform(y0 + 200, y1 - 200)
                    out = unreal.Vector(1 if s == "+X" else -1, 0, 0)
                else:
                    wy = y1 if s == "+Y" else y0; wx = rng.uniform(x0 + 200, x1 - 200)
                    out = unreal.Vector(0, 1 if s == "+Y" else -1, 0)
                # rotate so the thin axis points out of the wall
                face_yaw = math.degrees(math.atan2(out.y, out.x)) - (0 if thin == 0 else 90)
                gz, _ = trace(wx + out.x * 150, wy + out.y * 150)
                gz = z0 if gz is None else gz
                r = math.radians(face_yaw)
                cx_, cy_ = (b.max.x + b.min.x) / 2, (b.max.y + b.min.y) / 2
                ox, oy = cx_ * math.cos(r) - cy_ * math.sin(r), cx_ * math.sin(r) + cy_ * math.cos(r)
                half = ext[thin] / 2
                loc = unreal.Vector(wx + out.x * (half + 3) - ox, wy + out.y * (half + 3) - oy, gz - b.min.z - 10)
                a = eas.spawn_actor_from_object(sm, loc, unreal.Rotator(0, 0, face_yaw))
                if a:
                    a.set_actor_label("Ivy_%02d" % k); a.set_folder_path("AbandonedOffice/Exterior/Ivy")
                    a.set_editor_property("tags", [TAG]); n_ivy += 1
            counts["Ivy"] = n_ivy
        # ---- distance haze: the forest fades out instead of ending in a hard horizon line
        if FOG and not any(a.get_class().get_name() == "ExponentialHeightFog" and not has_tag(a, TAG)
                           for a in eas.get_all_level_actors()):
            fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
            if fog:
                fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
                for k, v in (("fog_density", 0.03), ("fog_height_falloff", 0.12), ("start_distance", 3000.0),
                             ("fog_max_opacity", 0.92),
                             ("fog_inscattering_luminance", unreal.LinearColor(0.42, 0.45, 0.48, 1.0))):
                    try:
                        fc.set_editor_property(k, v)
                    except Exception as e:
                        warn("fog: %s not set (%s)" % (k, e))
                fog.set_actor_label("AbandonedHaze"); fog.set_folder_path("AbandonedOffice/Exterior")
                fog.set_editor_property("tags", [TAG]); counts["Fog"] = 1
    log("placed: " + ", ".join("%s %d" % kv for kv in sorted(counts.items())))
    log("done. Re-run with another SEED / FRONT to rearrange; everything is in the outliner folder AbandonedOffice/Exterior")


if __name__ == "__main__":
    main()
