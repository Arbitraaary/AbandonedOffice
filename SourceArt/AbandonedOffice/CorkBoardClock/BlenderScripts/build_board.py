"""Cork notice board + stopped wall clock for the abandoned office.
python3.11 build_board.py -> out/stage.blend
Parts carry 'asset', 'ofs', 'hull'. Pivots: centre of the back face (put it on the wall), front = -Y.
  SM_CorkBoard  90 x 60 cm aluminium frame, yellowed papers, photos, stickies, push pins, ghost marks
  SM_WallClock  32 cm clock stopped at 4:47, glass gone, second hand dropped, hanging crooked
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(23)
DUST = C.DUST
REG = {}
for line in open(os.path.join(HERE, "tex", "regions.txt")):
    k, *v = line.split(); REG[k] = tuple(float(x) for x in v)

# ================================================================= materials
def cork(name, unfaded=False):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    lo, hi = ((0.29, 0.19, 0.10, 1), (0.40, 0.27, 0.15, 1)) if unfaded else ((0.33, 0.22, 0.12, 1), (0.45, 0.32, 0.19, 1))
    vor = g.n("ShaderNodeTexVoronoi", Scale=260.0); g.L(obj, vor.inputs[0])
    c = g.mixc(vor.outputs["Color"], lo, hi)                                   # granules
    c = g.mixc(g.math('MULTIPLY', g.noise(obj, 600, 3), 0.5), c, (0.18, 0.11, 0.05, 1))
    vh = g.n("ShaderNodeTexVoronoi", Scale=45.0); g.L(obj, vh.inputs[0])
    holes = g.rng(vh.outputs["Distance"], 0.03, 0.015)
    hm = g.math('MULTIPLY', holes, g.rng(g.noise(obj, 9, 2), 0.55, 0.6), True)   # old pin holes, in patches
    c = g.mixc(hm, c, (0.05, 0.03, 0.02, 1))
    if not unfaded:
        c = g.mixc(g.math('MULTIPLY', g.rng(g.noise(obj, 3, 3), 0.4, 0.7), 0.35), c, (0.52, 0.42, 0.30, 1))   # sun-faded
    grime = g.rng(g.noise(obj, 12, 5), 0.55, 0.8)
    c = g.mixc(g.math('MULTIPLY', grime, 0.35), c, (0.14, 0.10, 0.07, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump = g.n("ShaderNodeBump", Strength=0.6, Distance=0.001)
    g.L(g.math('ADD', vor.outputs["Distance"], g.math('MULTIPLY', hm, -1.0)), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def paper(name, rough=0.8):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    uvn = g.n("ShaderNodeUVMap", uv_map="PaperUV")
    im = g.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(os.path.join(HERE, "tex", "papers.png")); im.extension = 'EXTEND'
    g.L(uvn.outputs[0], im.inputs[0])
    c = g.mixc(g.math('MULTIPLY', g.rng(g.noise(obj, 6, 4), 0.45, 0.75), 0.4), im.outputs[0], (0.55, 0.45, 0.28, 1), 'MULTIPLY')
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.56), 0.5)
    c = g.mixc(edge, c, (0.42, 0.36, 0.25, 1))
    fox = g.math('MULTIPLY', g.rng(g.noise(obj, 40, 4), 0.68, 0.74), 0.6)     # foxing spots
    c = g.mixc(fox, c, (0.45, 0.32, 0.16, 1))
    grime = g.rng(g.noise(obj, 20, 5), 0.55, 0.8)
    c = g.mixc(g.math('MULTIPLY', grime, 0.35), c, (0.25, 0.22, 0.17, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bump = g.n("ShaderNodeBump", Strength=0.2, Distance=0.0005)
    g.L(g.noise(obj, 120, 4), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def plastic(name, col, rough=0.45, wear=0.4):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    c = g.mixc(g.noise(obj, 20, 4), col, tuple(min(1, v * 1.3) for v in col[:3]) + (1,))
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.62), wear)
    c = g.mixc(edge, c, (0.4, 0.4, 0.4, 1))
    grime = g.rng(g.noise(obj, 30, 6), 0.55, 0.78)
    c = g.mixc(g.math('MULTIPLY', grime, 0.35), c, (0.1, 0.09, 0.07, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 15, 6, 0.65), 0.3, 0.65), True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.8), c, DUST)
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(dust, rough, 0.95), b.inputs["Roughness"])
    return m

M_CORK, M_CORK_UN = cork("M_Cork"), cork("M_Cork_Unfaded", True)
M_PAPER, M_PHOTO = paper("M_Papers"), paper("M_Photos", 0.4)
M_ALU = C.painted("M_FrameAlu", (0.50, 0.51, 0.52, 1), primer=(0.3, 0.3, 0.3, 1), chip_amt=0.05, rough=0.35, rust=0.0)
M_CAP = plastic("M_FrameCorner", (0.14, 0.14, 0.15, 1))
M_BACK = C.plain("M_Hardboard", (0.25, 0.2, 0.15, 1), 0.9, 0.0, 0.4)
PINS = [plastic(f"M_Pin{k}", c, 0.3, 0.2) for k, c in enumerate([(0.45, 0.04, 0.03, 1), (0.04, 0.1, 0.38, 1), (0.55, 0.45, 0.05, 1),
                                                                  (0.06, 0.3, 0.08, 1), (0.6, 0.6, 0.58, 1)])]
M_RIM = plastic("M_ClockRim", (0.025, 0.025, 0.028, 1), 0.4, 0.08)
M_HAND = C.plain("M_ClockHand", (0.02, 0.02, 0.02, 1), 0.4, 0.3, 0.2)
M_SEC = C.plain("M_ClockSecond", (0.45, 0.05, 0.03, 1), 0.4, 0.0, 0.2)
M_SHARD = C.plain("M_GlassShard", (0.22, 0.27, 0.26, 1), 0.05, 0.0, 0.3)

ASSETS = {}
def part(asset, ob, hull=None):
    ob["asset"] = asset
    if hull: ob["hull"] = hull
    ASSETS.setdefault(asset, []).append(ob); return ob
def B(asset, *a, hull=None, **k): return part(asset, C.box(*a, **k), hull)
def CY(asset, *a, **k): return part(asset, C.cyl(*a, **k))

# ================================================================= CORK BOARD (frame 0.90 x 0.60)
A = "SM_CorkBoard"
BW, BH = 0.90, 0.60; FW = 0.022; FD = 0.022
CORK_Y = -0.012                       # cork front surface
B(A, "Back", -BW / 2 + 0.005, BW / 2 - 0.005, -0.004, 0.0, -BH / 2 + 0.005, BH / 2 - 0.005, M_BACK, hull="Board")
B(A, "Cork", -BW / 2 + FW - 0.003, BW / 2 - FW + 0.003, CORK_Y, -0.004, -BH / 2 + FW - 0.003, BH / 2 - FW + 0.003, M_CORK, cuts=6, hull="Board")
B(A, "FrameT", -BW / 2, BW / 2, -FD, 0.0, BH / 2 - FW, BH / 2, M_ALU, bevel=0.003, hull="Board")
B(A, "FrameB", -BW / 2, BW / 2, -FD, 0.0, -BH / 2, -BH / 2 + FW, M_ALU, bevel=0.003, hull="Board")
B(A, "FrameL", -BW / 2, -BW / 2 + FW, -FD, 0.0, -BH / 2 + FW, BH / 2 - FW, M_ALU, bevel=0.003)
B(A, "FrameR", BW / 2 - FW, BW / 2, -FD, 0.0, -BH / 2 + FW, BH / 2 - FW, M_ALU, bevel=0.003)
for sx in (-1, 1):
    for sz in (-1, 1):
        xa, xb = sorted((sx * (BW / 2 + 0.002), sx * (BW / 2 - 0.034)))
        za, zb = sorted((sz * (BH / 2 + 0.002), sz * (BH / 2 - 0.034)))
        B(A, f"Corner{sx}{sz}", xa, xb, -FD - 0.003, 0.0, za, zb, M_CAP, bevel=0.004)
layer = [0]
def sheet(name, reg, w, h, cx, cz, rot, pins, mat=M_PAPER, curl=(), hang=None, nu=8, nv=10, drop=()):
    """paper on the cork. pins: local (u,v) 0..1 positions. curl: [(u, v, radius, lift)] lifted corners.
    hang: (pin_u, pin_v, extra_deg) - only that pin holds it, rotated about it"""
    layer[0] += 1; y0 = CORK_Y - 0.0004 * layer[0]
    bm = bmesh.new(); vs = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            vs.append(bm.verts.new((i / nu, 0, j / nv)))
    for j in range(nv):
        for i in range(nu):
            if (i, j) in drop: continue                          # torn-off pieces
            a = j * (nu + 1) + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nu + 2], vs[a + nu + 1]))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    u0, v0, u1, v1 = REG[reg]
    lay = me.uv_layers.new(name="PaperUV")
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = (u0 + (u1 - u0) * co.x, v0 + (v1 - v0) * co.z)
    r = Matrix.Rotation(math.radians(rot), 3, 'Y')
    for v in me.vertices:
        u, vv = v.co.x, v.co.z
        lift = 0.0
        for (cu, cv, rad, amt) in curl:
            d = math.hypot((u - cu) * w, (vv - cv) * h)
            if d < rad: lift += amt * (1 - d / rad) ** 2
        lift += 0.0015 * noise.noise(Vector((u * 3, vv * 3, layer[0])))           # paper never lies flat
        p = Vector(((u - 0.5) * w, 0, (vv - 0.5) * h))
        v.co = r @ p + Vector((cx, y0 - abs(lift), cz))
    pin_pts = [r @ Vector(((pu - 0.5) * w, 0, (pv - 0.5) * h)) + Vector((cx, y0, cz)) for pu, pv in pins]
    if hang:
        piv = r @ Vector(((hang[0] - 0.5) * w, 0, (hang[1] - 0.5) * h)) + Vector((cx, y0, cz))
        rr = Matrix.Rotation(math.radians(hang[2]), 3, 'Y')
        for v in me.vertices: v.co = rr @ (v.co - piv) + piv
    ob = part(A, C.link(name, me, mat))
    for p in me.polygons: p.use_smooth = True
    for k, pp in enumerate(pin_pts): pushpin(f"{name}_Pin{k}", pp)
    return ob

def pushpin(name, p):
    mat = rnd.choice(PINS); y = p.y - 0.0004
    tilt = Matrix.Rotation(math.radians(rnd.uniform(-8, 8)), 3, 'X') @ Matrix.Rotation(math.radians(rnd.uniform(-8, 8)), 3, 'Z')
    objs = [CY(A, name + "_Neck", (0, -0.004, 0), 0.0032, 0.008, mat, axis='Y', segs=10),
            CY(A, name + "_Head", (0, -0.0105, 0), 0.0058, 0.005, mat, axis='Y', segs=14)]
    for o in objs:
        for v in o.data.vertices: v.co = tilt @ v.co + Vector((p.x, y, p.z))

# ghost marks: unfaded cork where papers hung for years (+ their pin holes)
for k, (cx, cz, w, h, rot) in enumerate([(0.06, 0.17, 0.15, 0.10, 2), (-0.29, -0.2, 0.2, 0.08, -1)]):
    g = B(A, f"Ghost{k}", -w / 2, w / 2, CORK_Y - 0.0002, CORK_Y + 0.001, -h / 2, h / 2, M_CORK_UN)
    for v in g.data.vertices: v.co = Matrix.Rotation(math.radians(rot), 3, 'Y') @ v.co + Vector((cx, 0, cz))
pushpin("LonePin", Vector((0.05, CORK_Y, 0.215)))
sheet("Calendar", "calendar", 0.21, 0.297, -0.29, 0.08, -1.5, [(0.5, 0.97)], curl=[(0.0, 0.0, 0.07, 0.012), (1.0, 0.0, 0.05, 0.006)], nv=12)
sheet("Memo", "memo", 0.21, 0.297, -0.05, -0.05, 2.5, [(0.12, 0.96), (0.88, 0.96)], curl=[(1.0, 0.0, 0.09, 0.02)], nv=12)
sheet("Flyer", "flyer", 0.148, 0.21, 0.15, -0.15, -3, [(0.5, 0.95)], curl=[(0.0, 0.0, 0.05, 0.008)], nu=7, nv=9,
      drop={(c, r) for c in (1, 2, 4) for r in (0, 1)} | {(6, 0)})
sheet("Photo1", "photo1", 0.15, 0.104, 0.27, 0.16, -6, [(0.5, 0.92)], mat=M_PHOTO, curl=[(1, 0, 0.05, 0.006)], nu=6, nv=5)
sheet("Photo2", "photo2", 0.15, 0.104, 0.33, -0.02, 7, [(0.15, 0.9)], mat=M_PHOTO, nu=6, nv=5, hang=(0.15, 0.9, -14))
for k, (cx, cz, rot, hang) in enumerate([(0.12, 0.08, 4, None), (0.36, -0.19, -3, (0.5, 0.92, 38)), (-0.15, 0.19, -6, None), (0.04, -0.22, 9, None)]):
    sheet(f"Sticky{k}", f"sticky{k}", 0.076, 0.076, cx, cz, rot, [(0.5, 0.88)], curl=[(0.5, 0.0, 0.05, 0.01)], nu=4, nv=4, hang=hang)

# ================================================================= WALL CLOCK  (r 0.16, stopped 4:47)
K = "SM_WallClock"
prof = [(0.0, 0.0), (0.150, 0.0), (0.160, -0.006), (0.163, -0.030), (0.158, -0.042), (0.148, -0.046), (0.141, -0.041), (0.140, -0.014), (0.0, -0.014)]
SEG = 64
bm = bmesh.new(); rings = []
for (r, y) in prof:
    rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / SEG), y, r * math.sin(2 * math.pi * j / SEG))) for j in range(SEG)])
for a, b2 in zip(rings[:-2], rings[1:-1]):
    for j in range(SEG):
        bm.faces.new((a[j], a[(j + 1) % SEG], b2[(j + 1) % SEG], b2[j]))
me = bpy.data.meshes.new("ClockRim"); bm.to_mesh(me); bm.free()
part(K, C.link("ClockRim", me, M_RIM), hull="Clock")
for p in me.polygons: p.use_smooth = True
# face disk with the dial image
bm = bmesh.new(); vs = [bm.verts.new((0.1405 * math.cos(2 * math.pi * j / SEG), -0.0141, 0.1405 * math.sin(2 * math.pi * j / SEG))) for j in range(SEG)]
f = bm.faces.new(vs)
me = bpy.data.meshes.new("Dial"); bm.to_mesh(me); bm.free()
u0, v0, u1, v1 = REG["clockface"]
lay = me.uv_layers.new(name="PaperUV")
for p in me.polygons:
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        lay.data[li].uv = (u0 + (u1 - u0) * (co.x / 0.29 + 0.5), v0 + (v1 - v0) * (co.z / 0.29 + 0.5))
part(K, C.link("Dial", me, M_PAPER))
def hand(name, ang, length, tail, wid, y, mat, tip=0.6):
    bm = bmesh.new()
    pts = [(-wid * 0.6, -tail), (wid * 0.6, -tail), (wid / 2, length * tip), (0.0, length), (-wid / 2, length * tip)]
    top = [bm.verts.new((x, y, z)) for x, z in pts]; bot = [bm.verts.new((x, y + 0.0008, z)) for x, z in pts]
    bm.faces.new(top); bm.faces.new(bot[::-1])
    for i in range(len(pts)):
        j = (i + 1) % len(pts); bm.faces.new((top[j], top[i], bot[i], bot[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    r = Matrix.Rotation(math.radians(ang), 3, 'Y')
    for v in me.vertices: v.co = r @ v.co
    return part(K, C.link(name, me, mat))
hand("HourHand", (4 + 47 / 60) * 30, 0.075, 0.015, 0.009, -0.0175, M_HAND)
hand("MinuteHand", 47 * 6, 0.112, 0.018, 0.006, -0.0195, M_HAND)
sh = hand("SecondHand", 180 - 4, 0.118, 0.025, 0.0022, -0.0215, M_SEC, tip=0.9)           # came loose, hangs down
for v in sh.data.vertices: v.co.y -= 0.004 * max(0.0, -v.co.z) / 0.12                        # sagging away from the dial
CY(K, "CenterCap", (0, -0.022, 0), 0.0055, 0.006, M_HAND, axis='Y', segs=14)
# glass gone, a few shards still stuck in the rim groove
for k, a0 in enumerate([25, 32, 200, 300]):
    a = math.radians(a0); da = math.radians(rnd.uniform(5, 11)); ins = rnd.uniform(0.02, 0.045)
    pts = [Vector((0.142 * math.cos(a), -0.041, 0.142 * math.sin(a))), Vector((0.142 * math.cos(a + da), -0.041, 0.142 * math.sin(a + da))),
           Vector(((0.142 - ins) * math.cos(a + da * 0.4), -0.040, (0.142 - ins) * math.sin(a + da * 0.4)))]
    bm = bmesh.new(); t = [bm.verts.new(p) for p in pts]; bt = [bm.verts.new(p + Vector((0, 0.002, 0))) for p in pts]
    bm.faces.new(t); bm.faces.new(bt[::-1])
    for i in range(3): bm.faces.new((t[(i + 1) % 3], t[i], bt[i], bt[(i + 1) % 3]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"Shard{k}"); bm.to_mesh(me); bm.free(); part(K, C.link(f"Shard{k}", me, M_SHARD))
crook = Matrix.Rotation(math.radians(-7), 3, 'Y')
for o in ASSETS[K]:
    for v in o.data.vertices: v.co = crook @ v.co

# ================================================================= stage layout
for o in C.PARTS:
    for p in o.data.polygons:
        if o.data.materials[0] in (M_ALU, M_CAP, M_BACK, M_CORK, M_CORK_UN): p.use_smooth = False
C.finalize(["PaperUV"])
layout = {A: (0.0, 0.0, 1.3), K: (0.85, 0.0, 1.45)}
for name, objs in ASSETS.items():
    for o in objs:
        o.location = layout[name]; o["ofs"] = layout[name]
    print(name, len(objs), "parts", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "tris")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage.blend"))
