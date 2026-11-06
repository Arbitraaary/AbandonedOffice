"""Workstation kit for the abandoned office: keyboard, mouse, PC tower (side panel gone), desk phone x2.
python3.11 build_desk.py -> out/stage.blend
Every part has a custom property 'asset' (final mesh name) and the stage offset 'ofs' of that asset;
the bake script joins everything for one shared atlas and splits it back per asset.
Pivots: bottom centre of each item; front faces -Y. Phone 'Hanging': pivot on the desk top, desk edge at y = -0.16.
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(31)
DUST = C.DUST

# ----------------------------------------------------------------- materials
def plastic(name, col, rough=0.45, wear=0.6, dust_amt=0.9):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    c = g.mixc(g.noise(obj, 30, 4), col, tuple(min(1, v * 1.4) for v in col[:3]) + (1,))
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.62), wear)          # rubbed, greyed edges
    c = g.mixc(edge, c, (0.16, 0.16, 0.16, 1))
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(300, 300, 30)), 0.765, 0.785)
    c = g.mixc(g.math('MULTIPLY', scr, 0.5), c, (0.2, 0.2, 0.2, 1))
    grime = g.rng(g.noise(obj, 40, 6), 0.55, 0.75)
    c = g.mixc(g.math('MULTIPLY', grime, 0.3), c, (0.09, 0.08, 0.06, 1))
    up = g.rng(sn.outputs[2], 0.4, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 18, 6, 0.65), 0.5, 0.75), True)
    c = g.mixc(g.math('MULTIPLY', dust, dust_amt * 0.45), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(edge, rough, 0.3); r = g.mixf(dust, r, 0.95); g.L(r, b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.15, Distance=0.0003)
    g.L(g.math('ADD', g.noise(obj, 800, 2), g.math('MULTIPLY', dust, 0.5)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def pcb_material():
    m, nt, b = mat_new("M_PCB"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 40, 3), (0.012, 0.05, 0.025, 1), (0.02, 0.07, 0.035, 1))
    tr = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Y', Scale=180.0, Distortion=1.5); g.L(obj, tr.inputs[0])
    trace = g.math('MULTIPLY', g.rng(tr.outputs["Fac"], 0.93, 0.97), g.rng(g.noise(obj, 30, 2), 0.4, 0.55), True)
    c = g.mixc(trace, c, (0.35, 0.28, 0.08, 1))
    dust = g.rng(g.noise(obj, 50, 6), 0.4, 0.75)
    c = g.mixc(g.math('MULTIPLY', dust, 0.3), c, DUST)
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(trace, 0.5, 0.3), b.inputs["Roughness"])
    g.L(g.mixf(trace, 0.0, 0.8), b.inputs["Metallic"])
    return m

def lcd_material():
    m, nt, b = mat_new("M_LCD"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 20, 4), (0.05, 0.065, 0.055, 1), (0.08, 0.09, 0.075, 1))
    dust = g.rng(g.noise(obj, 50, 6), 0.45, 0.8)
    c = g.mixc(g.math('MULTIPLY', dust, 0.4), c, DUST)
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.2
    return m

def sticker_material():
    m, nt, b = mat_new("M_AssetTag"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    wv = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='X', Scale=260.0, Distortion=0.0); g.L(obj, wv.inputs[0])
    bars = g.math('MULTIPLY', g.rng(wv.outputs["Fac"], 0.55, 0.6), g.rng(g.noise(obj, 400, 1), 0.3, 0.7), True)
    c = g.mixc(bars, (0.62, 0.6, 0.52, 1), (0.05, 0.05, 0.05, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6
    return m

M_BLK = plastic("M_Plastic_Black", (0.018, 0.018, 0.02, 1))
M_KEY = plastic("M_Keycap", (0.03, 0.03, 0.033, 1), rough=0.35, wear=0.35, dust_amt=0.6)
M_GREY = plastic("M_Plastic_Grey", (0.12, 0.12, 0.125, 1), wear=0.4)
M_RUB = plastic("M_Cable", (0.012, 0.012, 0.012, 1), rough=0.7, wear=0.0, dust_amt=0.6)
M_STEEL = C.plain("M_CaseSteel", (0.35, 0.36, 0.36, 1), 0.45, 0.9, 0.5)
M_ALU = C.plain("M_HeatsinkAlu", (0.55, 0.56, 0.57, 1), 0.35, 1.0, 0.6)
M_PCB = pcb_material(); M_LCD = lcd_material(); M_TAG = sticker_material()

ASSETS = {}
def part(asset, ob):
    ob["asset"] = asset
    ASSETS.setdefault(asset, []).append(ob)
    return ob
def B(asset, *a, **k): return part(asset, C.box(*a, **k))
def CY(asset, *a, **k): return part(asset, C.cyl(*a, **k))

def tube(asset, name, pts, r, mat, segs=8):
    bm = bmesh.new(); rings = []
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        a = t.cross(Vector((0, 0, 1)));
        if a.length < 1e-3: a = t.cross(Vector((1, 0, 0)))
        a.normalize(); b2 = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b2 * math.sin(2 * math.pi * j / segs)) * r) for j in range(segs)])
    for k in range(len(pts) - 1):
        for j in range(segs):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % segs], rings[k + 1][(j + 1) % segs], rings[k + 1][j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = C.link(name, me, mat)
    for p in me.polygons: p.use_smooth = True
    return part(asset, ob)

def spline(ctrl, n=10):
    P = [ctrl[0]] + ctrl + [ctrl[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1]); return out

def coil(path, radius=0.0055, pitch=0.007):
    """helical phone cord around a centre-line path"""
    out = []; s = 0.0
    for i in range(len(path) - 1):
        a, b2 = path[i], path[i + 1]
        seg = (b2 - a); L = seg.length; t = seg.normalized()
        n1 = t.cross(Vector((0, 0, 1)));
        if n1.length < 1e-3: n1 = t.cross(Vector((1, 0, 0)))
        n1.normalize(); n2 = t.cross(n1)
        steps = max(1, int(L / (pitch / 6)))
        for k in range(steps):
            p = a + seg * (k / steps); ang = 2 * math.pi * (s + L * k / steps) / pitch
            out.append(p + (n1 * math.cos(ang) + n2 * math.sin(ang)) * radius)
        s += L
    return out

# ================================================================= KEYBOARD (0.44 x 0.14)
K = "SM_Keyboard"
kb_rot = Matrix.Rotation(math.radians(4), 3, 'X')               # slight typing angle
B(K, "KB_Body", -0.22, 0.22, -0.07, 0.07, 0.0, 0.022, M_BLK, bevel=0.006, seg=3)
B(K, "KB_Feet", -0.2, 0.2, 0.055, 0.068, -0.0, 0.006, M_BLK)
bm = bmesh.new(); missing = {(1, 4), (3, 9), (2, 13)}
def keycap(x, y, w, h=0.0165):
    vs = []
    for (dx, dy, dz, s) in [(-1, -1, 0, 1), (1, -1, 0, 1), (1, 1, 0, 1), (-1, 1, 0, 1),
                            (-1, -1, 1, 0.82), (1, -1, 1, 0.82), (1, 1, 1, 0.82), (-1, 1, 1, 0.82)]:
        vs.append(bm.verts.new((x + dx * w / 2 * (s if dz else 1) - (0 if not dz else 0), y + dy * h / 2 * s, 0.022 + dz * 0.008)))
    for f in [(0, 1, 2, 3)[::-1], (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([vs[i] for i in f])
U = 0.019
for row in range(5):
    y = 0.045 - row * U
    x = -0.205
    col = 0
    while x < 0.09:
        w = U * (1.5 if (col == 0 and row in (1, 3)) else 1.0)
        if row == 4 and col == 3: w = U * 6.2                    # space bar
        if (row, col) not in missing:
            keycap(x + w / 2, y, w - 0.0025)
        x += w; col += 1
for row in range(5):                                              # numpad
    for colm in range(4):
        if (row, colm) == (4, 1): continue
        w = U * (2 if (row, colm) == (4, 0) else 1)
        keycap(0.115 + colm * U + w / 2 - U / 2, 0.045 - row * U, w - 0.0025)
for colm in range(12):                                            # function row
    keycap(-0.195 + colm * U * 1.1, 0.064, U - 0.004, 0.011)
me = bpy.data.meshes.new("KB_Keys"); bm.to_mesh(me); bm.free()
part(K, C.link("KB_Keys", me, M_KEY))
tube(K, "KB_Cable", spline([Vector((0.0, 0.07, 0.012)), Vector((0.01, 0.12, 0.004)), Vector((-0.03, 0.2, 0.003)), Vector((0.02, 0.27, 0.003))]), 0.0022, M_RUB)
for o in ASSETS[K]:
    for v in o.data.vertices: v.co = kb_rot @ v.co
    zmin = 0.0

# ================================================================= MOUSE
Mo = "SM_Mouse"
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1.0)
for v in bm.verts:
    x, y, z = v.co
    z = max(z, -0.05)
    y2 = y * 0.058
    v.co = Vector((x * 0.031 * (1 - 0.15 * y), y2, (z + 0.05) * 0.019 * (1 + 0.25 * (-y)) ))
me = bpy.data.meshes.new("Mouse"); bm.to_mesh(me); bm.free()
mo = part(Mo, C.link("Mouse", me, M_BLK))
for p in me.polygons: p.use_smooth = True
B(Mo, "MouseSplit", -0.0006, 0.0006, -0.058, -0.012, 0.018, 0.036, M_RUB)
CY(Mo, "Wheel", (0, -0.035, 0.034), 0.0055, 0.006, M_GREY, axis='X', segs=14)
tube(Mo, "MouseCable", spline([Vector((0, -0.057, 0.008)), Vector((0.004, -0.09, 0.003)), Vector((-0.02, -0.14, 0.003)), Vector((0.01, -0.2, 0.003))]), 0.0016, M_RUB, 6)

# ================================================================= PC TOWER (0.19 x 0.43 x 0.42), right side panel missing
P_ = "SM_PCTower"
W, D, H = 0.19, 0.43, 0.42; t = 0.006
B(P_, "Case_Left", -W / 2, -W / 2 + t, -D / 2, D / 2, 0.012, H, M_BLK, bevel=0.002)
B(P_, "Case_Top", -W / 2, W / 2, -D / 2, D / 2, H - t, H, M_BLK, bevel=0.002)
B(P_, "Case_Bottom", -W / 2, W / 2, -D / 2, D / 2, 0.012, 0.012 + t, M_BLK, bevel=0.002)
B(P_, "Case_Back", -W / 2, W / 2, D / 2 - t, D / 2, 0.012, H, M_STEEL, bevel=0.002)
B(P_, "Case_Front", -W / 2 - 0.004, W / 2 + 0.004, -D / 2 - 0.012, -D / 2, 0.006, H + 0.004, M_BLK, bevel=0.004, seg=3)
for sx in (-1, 1):
    for sy in (-1, 1):
        B(P_, f"Foot{sx}{sy}", sx * 0.07 - 0.012, sx * 0.07 + 0.012, sy * 0.18 - 0.02, sy * 0.18 + 0.02, 0.0, 0.012, M_RUB)
B(P_, "DriveBay", -0.075, 0.075, -D / 2 - 0.0135, -D / 2 - 0.01, H - 0.07, H - 0.03, M_GREY, bevel=0.001)
CY(P_, "PowerBtn", (0, -D / 2 - 0.013, H - 0.11), 0.011, 0.004, M_GREY, axis='Y', segs=18)
for k in range(2):
    B(P_, f"USB{k}", -0.03 + k * 0.035, -0.015 + k * 0.035, -D / 2 - 0.0125, -D / 2 - 0.0115, H - 0.15, H - 0.143, M_RUB)
for k in range(8):                                                # front vent slots
    B(P_, f"Vent{k}", -0.06, 0.06, -D / 2 - 0.0123, -D / 2 - 0.0118, 0.05 + k * 0.016, 0.058 + k * 0.016, M_RUB)
tag = B(P_, "AssetTag", -0.05, 0.03, -D / 2 - 0.0128, -D / 2 - 0.0124, H - 0.22, H - 0.19, M_TAG)
# interior
B(P_, "Mobo", -W / 2 + t, -W / 2 + t + 0.003, -D / 2 + 0.03, D / 2 - 0.02, 0.05, H - 0.06, M_PCB)
B(P_, "PSU", -W / 2 + t, W / 2 - 0.01, D / 2 - 0.16, D / 2 - t, H - 0.095, H - t, M_STEEL, bevel=0.002)
B(P_, "Cooler", -W / 2 + 0.01, -W / 2 + 0.07, -0.02, 0.07, H - 0.2, H - 0.11, M_ALU, bevel=0.002)
CY(P_, "Fan", (-W / 2 + 0.072, 0.025, H - 0.155), 0.04, 0.004, M_BLK, axis='X', segs=24)
for k in range(2):
    B(P_, f"RAM{k}", -W / 2 + 0.009, -W / 2 + 0.04, 0.09 + k * 0.012, 0.095 + k * 0.012, H - 0.2, H - 0.07, M_PCB)
B(P_, "EmptySlotPlate", -W / 2 + 0.009, -W / 2 + 0.03, -0.1, 0.17, 0.16, 0.168, M_STEEL)      # graphics card was pulled
for k in range(3):                                                # loose cables hanging out of the open side
    a = Vector((-0.02 + k * 0.02, D / 2 - 0.12, H - 0.1))
    tube(P_, f"Cable{k}", spline([a, a + Vector((0.03, -0.05, -0.08)), a + Vector((0.09 + k * 0.02, -0.1, -0.22)),
                                  Vector((W / 2 + 0.03 + k * 0.02, -0.05 - k * 0.04, 0.015))]), 0.0035, M_RUB, 6)

# ================================================================= DESK PHONE (two variants)
def phone(asset, hanging):
    pb = B(asset, f"{asset}_Base", -0.1, 0.1, -0.09, 0.09, 0.0, 0.05, M_BLK, bevel=0.008, seg=3)
    for v in pb.data.vertices:                                    # sloped top
        if v.co.z > 0.025: v.co.z -= (v.co.y + 0.09) / 0.18 * 0.0 + (0.09 - v.co.y) * 0.18
    surf = lambda y: 0.05 - (0.09 - y) * 0.18                  # sloped top surface of the base
    def onto(ob, h):
        z0 = min(v.co.z for v in ob.data.vertices); z1 = max(v.co.z for v in ob.data.vertices)
        for v in ob.data.vertices:
            v.co.z = surf(v.co.y) - 0.002 + (h + 0.002) * (v.co.z - z0) / (z1 - z0 + 1e-9)
    onto(B(asset, f"{asset}_Cradle", -0.1, -0.035, -0.08, 0.085, 0.0, 0.01, M_BLK, bevel=0.006), 0.014)
    onto(B(asset, f"{asset}_Hook", -0.075, -0.06, -0.06, -0.045, 0.0, 0.01, M_GREY, bevel=0.002), 0.02)
    onto(B(asset, f"{asset}_LCD", -0.02, 0.085, 0.035, 0.075, 0.0, 0.01, M_LCD), 0.0015)
    for r in range(4):
        for c in range(3):
            kx, ky = 0.0 + c * 0.024, 0.01 - r * 0.02
            onto(B(asset, f"{asset}_Key{r}{c}", kx - 0.008, kx + 0.008, ky - 0.006, ky + 0.006, 0.0, 0.005, M_GREY, bevel=0.0015), 0.005)
    # handset
    def handset(origin, rot):
        parts = []
        hb = C.box(f"{asset}_Handset", -0.022, 0.022, -0.1, 0.1, 0.0, 0.03, M_BLK, bevel=0.01, seg=3); parts.append(hb)
        e1 = C.box(f"{asset}_Ear", -0.026, 0.026, 0.065, 0.11, -0.012, 0.032, M_BLK, bevel=0.012, seg=3); parts.append(e1)
        e2 = C.box(f"{asset}_Mouth", -0.026, 0.026, -0.11, -0.065, -0.012, 0.032, M_BLK, bevel=0.012, seg=3); parts.append(e2)
        for o in parts:
            for v in o.data.vertices: v.co = rot @ v.co + origin
            part(asset, o)
        return rot @ Vector((0, -0.11, 0.0)) + origin             # cord attaches at the mouth end
    jack = Vector((-0.1, 0.0, 0.015))
    if hanging:
        # desk edge at y = -0.16; handset dangling ~0.35 m below the desk top
        rot = Matrix.Rotation(math.radians(8), 3, 'Z') @ Matrix.Rotation(math.radians(-82), 3, 'X')
        end = handset(Vector((-0.07, -0.19, -0.33)), rot)
        path = spline([jack, Vector((-0.13, -0.04, 0.006)), Vector((-0.11, -0.12, 0.005)), Vector((-0.09, -0.163, 0.0)),
                       Vector((-0.085, -0.175, -0.06)), Vector((-0.08, -0.185, -0.15)), end], 8)
    else:
        rot = Matrix.Rotation(math.radians(70), 3, 'Z') @ Matrix.Rotation(math.radians(85), 3, 'Y')
        end = handset(Vector((-0.24, -0.06, 0.026)), rot)
        path = spline([jack, Vector((-0.14, 0.03, 0.006)), Vector((-0.18, 0.06, 0.006)), Vector((-0.24, 0.03, 0.006)), end], 8)
    tube(asset, f"{asset}_Cord", coil(path), 0.0013, M_RUB, 5)
phone("SM_DeskPhone_Hanging", True)
phone("SM_DeskPhone", False)

# ----------------------------------------------------------------- lay the assets out on the stage (apart -> clean AO)
layout = {"SM_Keyboard": (0.0, 0.0), "SM_Mouse": (0.35, -0.05), "SM_PCTower": (-0.55, 0.15),
          "SM_DeskPhone": (0.0, -0.45), "SM_DeskPhone_Hanging": (0.6, -0.45)}
for name, objs in ASSETS.items():
    ox, oy = layout[name]
    zmin = min(v.co.z for o in objs for v in o.data.vertices) if name != "SM_DeskPhone_Hanging" else 0.0
    for o in objs:
        for v in o.data.vertices: v.co += Vector((0, 0, -zmin)) if name != "SM_DeskPhone_Hanging" else Vector()
        o.location = (ox, oy, 0.4 if name == "SM_DeskPhone_Hanging" else 0.0)
        o["ofs"] = (ox, oy, 0.4 if name == "SM_DeskPhone_Hanging" else 0.0)
for name, objs in ASSETS.items():
    print(name, len(objs), "parts", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "tris")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage.blend"))
