"""Two dead office plants.
python3.11 build_plants.py large   -> out/stage_large.blend   (floor pot, dried dracaena, ~1.4 m)
python3.11 build_plants.py small   -> out/stage_small.blend   (desk pot, dried trailing pothos)
"""
import bpy, math, random, os, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import plantlib as P

which = sys.argv[-1]
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
M_LEAF, M_SOIL = P.leaf_material(), P.soil_material()
parts = []

def sph(elev, azim):
    return Vector((math.cos(elev) * math.cos(azim), math.cos(elev) * math.sin(azim), math.sin(elev)))

if which == "large":
    rnd = random.Random(11)
    M_POT, M_CANE = P.granite_material(), P.bark_material()
    prof = [(0.0005, 0.0), (0.124, 0.0), (0.13, 0.008), (0.188, 0.425), (0.196, 0.437), (0.198, 0.452),
            (0.192, 0.461), (0.182, 0.458), (0.177, 0.43), (0.174, 0.39), (0.168, 0.36)]
    def chip(i, th, r, z):                       # small chip knocked out of the rim
        dth = math.atan2(math.sin(th - 2.4), math.cos(th - 2.4))
        if z > 0.43: z -= 0.008 * math.exp(-(dth / 0.08) ** 2)
        return r, z
    parts.append(P.revolve("Pot", prof, M_POT, 64, chip))
    SOIL_Z = 0.405
    parts.append(P.soil_disc("Soil", 0.177, SOIL_Z, M_SOIL, seed=3))
    canes = [((-0.03, 0.02), 0.58, 0.021, (0.05, -0.02)), ((0.035, 0.015), 0.82, 0.018, (-0.04, 0.05)),
             ((0.0, -0.035), 1.02, 0.016, (0.06, 0.04))]
    for ci, ((x, y), h, r, (bx, by)) in enumerate(canes):
        pts = []
        for k in range(9):
            t = k / 8
            pts.append(Vector((x + bx * t * t, y + by * t * t, SOIL_Z - 0.04 + (h + 0.04) * t)))
        parts.append(P.tube(f"Cane{ci}", pts, r, M_CANE, 12))
        top = pts[-1]
        n_leaves = 11 + ci * 2
        for k in range(n_leaves):
            az = k * 2.4 + rnd.uniform(-0.3, 0.3)
            elev = rnd.uniform(0.35, 1.1)
            root = top + Vector((math.cos(az), math.sin(az), 0)) * r * 0.7 - Vector((0, 0, rnd.uniform(0.0, 0.07)))
            broken = rnd.uniform(0.2, 0.5) if rnd.random() < 0.35 else None
            parts.append(P.leaf(f"L{ci}_{k}", root, sph(elev, az), rnd.uniform(0.28, 0.42), rnd.uniform(0.026, 0.034),
                                M_LEAF, 100 * ci + k, droop=rnd.uniform(2.3, 3.4), curl=rnd.uniform(0.7, 1.3),
                                twist=1.0, shape="strap", broken_at=broken, thickness=0.0005))
        for k in range(5):                       # old dead leaves hanging lower down the cane
            az = rnd.uniform(0, 6.28); zz = SOIL_Z + h * rnd.uniform(0.45, 0.85)
            root = Vector((x + bx * 0.4, y + by * 0.4, zz)) + Vector((math.cos(az), math.sin(az), 0)) * r
            parts.append(P.leaf(f"Old{ci}_{k}", root, sph(-0.2, az), rnd.uniform(0.2, 0.3), 0.025, M_LEAF,
                                500 + 10 * ci + k, droop=2.0, curl=1.2, twist=1.4, thickness=0.0005))
    for k in range(6):                           # fallen leaves lying on the soil
        az = rnd.uniform(0, 6.28); rr = rnd.uniform(0.03, 0.07)
        root = Vector((rr * math.cos(az), rr * math.sin(az), SOIL_Z + 0.006))
        parts.append(P.leaf(f"Fallen{k}", root, sph(0.02, az + rnd.uniform(-1.2, 1.2)), rnd.uniform(0.09, 0.15), 0.028, M_LEAF,
                            900 + k, droop=0.05, curl=1.3, twist=0.6, thickness=0.0005))
else:
    rnd = random.Random(23)
    M_POT = P.ceramic_material()
    parts.append(P.revolve("Saucer", [(0.0005, 0.0), (0.078, 0.0), (0.084, 0.003), (0.088, 0.015), (0.085, 0.017),
                                      (0.081, 0.006), (0.0005, 0.006)], M_POT, 56))
    prof = [(0.0005, 0.007), (0.05, 0.007), (0.054, 0.011), (0.064, 0.112), (0.069, 0.116), (0.0695, 0.124),
            (0.066, 0.127), (0.061, 0.125), (0.059, 0.11), (0.057, 0.09)]
    parts.append(P.revolve("Pot", prof, M_POT, 56))
    SOIL_Z = 0.106
    parts.append(P.soil_disc("Soil", 0.059, SOIL_Z, M_SOIL, rings=10, segs=48, gap=0.003, seed=7))
    M_STEM = P.bark_material("M_DeadVine", 0.45)
    WALL = lambda z: 0.054 + (0.064 - 0.054) * max(0.0, z - 0.011) / 0.101
    RIM_R, RIM_Z = 0.0695, 0.127
    vines = [(0.4, True, 0.10), (1.6, False, 0.0), (2.9, True, 0.06), (4.1, False, 0.0), (5.2, True, 0.13)]
    leaf_id = 0
    for vi, (az, long_, desk) in enumerate(vines):
        d = Vector((math.cos(az), math.sin(az), 0)); s_ = Vector((-d.y, d.x, 0))
        r0 = rnd.uniform(0.005, 0.02)
        pts = [Vector((0, 0, SOIL_Z - 0.01)) + d * r0,
               Vector((0, 0, SOIL_Z + 0.03)) + d * (r0 + 0.015) + s_ * rnd.uniform(-0.01, 0.01),
               Vector((0, 0, RIM_Z + 0.012)) + d * (RIM_R - 0.004),
               Vector((0, 0, RIM_Z + 0.004)) + d * (RIM_R + 0.008)]
        zz = RIM_Z - 0.01
        z_end = 0.03 if long_ else rnd.uniform(0.06, 0.09)
        while zz > z_end:                                             # hanging down the outside of the pot
            pts.append(Vector((0, 0, zz)) + d * (WALL(zz) + 0.006) + s_ * 0.01 * math.sin(zz * 60 + vi))
            zz -= 0.018
        if long_:                                                     # trailing across the saucer onto the desk
            pts.append(Vector((0, 0, 0.022)) + d * 0.092 + s_ * 0.01)
            r = 0.092
            while r < 0.092 + desk:
                r += 0.025
                pts.append(Vector((0, 0, 0.0025)) + d * r + s_ * 0.03 * math.sin(r * 25 + vi))
        # smooth the path a little
        sm = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        parts.append(P.tube(f"Vine{vi}", sm, 0.0017, M_STEM, segs=6, taper=0.3))
        # shrivelled heart-shaped leaves along the vine; some nodes are bare
        acc = 0.0
        for i in range(1, len(sm)):
            acc += (sm[i] - sm[i - 1]).length
            if acc < 0.026: continue
            acc = 0.0
            if rnd.random() < 0.25: continue
            t = (sm[min(i + 1, len(sm) - 1)] - sm[i - 1]).normalized()
            side = t.cross(Vector((0, 0, 1)));
            if side.length < 1e-3: side = d.copy()
            side.normalize()
            sgn = 1 if leaf_id % 2 else -1
            out = (side * sgn * 0.8 + d * 0.5 + Vector((0, 0, 0.25))).normalized()
            on_desk = sm[i].z < 0.01
            parts.append(P.leaf(f"Pothos{leaf_id}", sm[i] + out * 0.004, out, rnd.uniform(0.045, 0.065),
                                rnd.uniform(0.034, 0.046), M_LEAF, 400 + leaf_id,
                                droop=0.15 if on_desk else rnd.uniform(1.0, 2.0), curl=rnd.uniform(0.45, 0.9),
                                twist=0.7, shape="heart", petiole=0.18, seg_u=8, thickness=0.0004))
            leaf_id += 1
    for k in range(4):                           # dropped leaves on the soil and the saucer
        az = rnd.uniform(0, 6.28)
        rr, zz = (0.03, SOIL_Z + 0.004) if k < 2 else (0.078, 0.0085)
        root = Vector((rr * math.cos(az), rr * math.sin(az), zz))
        parts.append(P.leaf(f"Drop{k}", root, sph(0.0, az + 1.5), 0.045, 0.036, M_LEAF, 700 + k, droop=0.05,
                            curl=0.9, twist=0.6, shape="heart", thickness=0.0004))

if which == "large":
    wall = lambda z: 0.13 + (0.188 - 0.13) * max(0.0, z - 0.008) / 0.417
    rim = (0.198, 0.461, 0.177, SOIL_Z)
else:
    wall = lambda z: 0.054 + (0.064 - 0.054) * max(0.0, z - 0.011) / 0.101
    rim = (0.0695, 0.127, 0.059, SOIL_Z)
for o in parts:
    if o.name.startswith(("L", "Old", "Fallen", "Drop", "Pothos")):
        P.keep_outside_pot(o, wall, *rim)
P.finalize(parts)
# leaves must not poke through the pot wall: push any vertex inside the pot wall back out over it
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
print(which, "parts", len(parts), "tris", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"stage_{which}.blend"))
