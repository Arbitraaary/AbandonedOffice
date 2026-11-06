"""Cardboard boxes for the abandoned office (left behind half-packed).
python3.11 build_boxes.py -> out/stage.blend
Parts carry 'asset', 'ofs' and optionally 'hull' (collision group). Pivots: bottom centre, front = -Y.
  SM_Box_Closed   taped moving box, slightly dented, marker scribble, shipping label
  SM_Box_Open     archive box, flaps open (one torn), lever-arch files and paper inside
  SM_Box_Crushed  box with the top caved in, sides bulging, tape split
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(61)
DUST = C.DUST
TEX = os.path.join(HERE, "tex")
T = 0.004                                  # cardboard thickness

# ================================================================= materials
def cardboard_graph(g, b, ink_img=None, ink_col=(0.025, 0.022, 0.025, 1), ink_strength=0.92):
    edge_w = 0.0 if ink_img else 0.6                           # decal planes: pointiness would outline them
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 7, 5), (0.36, 0.24, 0.13, 1), (0.45, 0.31, 0.17, 1))
    flute = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z', Scale=55.0, Distortion=0.4); g.L(obj, flute.inputs[0])
    c = g.mixc(g.math('MULTIPLY', g.rng(flute.outputs["Fac"], 0.3, 0.7), 0.06), c, (0.30, 0.20, 0.10, 1))   # faint flute shading
    if ink_img:
        uvn = g.n("ShaderNodeUVMap", uv_map="LabelUV")
        im = g.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(ink_img); im.extension = 'EXTEND'
        im.image.colorspace_settings.name = 'Non-Color'
        g.L(uvn.outputs[0], im.inputs[0])
        ink = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, im.outputs[0]), g.rng(g.noise(obj, 60, 4), 0.2, 0.55), True)
        c = g.mixc(g.math('MULTIPLY', ink, ink_strength), c, ink_col)
    scuff = g.math('MULTIPLY', g.rng(g.noise(obj, 22, 6, 0.7), 0.66, 0.74), 0.7)     # torn top paper -> lighter fibres
    c = g.mixc(scuff, c, (0.55, 0.45, 0.32, 1))
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.6), edge_w)
    c = g.mixc(edge, c, (0.56, 0.46, 0.33, 1))
    wet = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.09, 0.01), g.rng(g.noise(obj, 6, 3), 0.35, 0.6), True)  # damp floor
    tide = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', wet, 0.5)), 0.1, 0.0), 0.3)
    c = g.mixc(g.math('MULTIPLY', wet, 0.55), c, (0.22, 0.14, 0.07, 1))
    c = g.mixc(tide, c, (0.17, 0.10, 0.05, 1))
    grime = g.rng(g.noise(obj, 16, 6), 0.55, 0.78)
    c = g.mixc(g.math('MULTIPLY', grime, 0.5), c, (0.17, 0.12, 0.08, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 12, 6, 0.65), 0.35, 0.7), True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.6), c, DUST)
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(dust, 0.82, 0.95), b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.25, Distance=0.001)
    g.L(g.math('ADD', g.noise(obj, 300, 4), g.math('MULTIPLY', scuff, 0.6)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])

def cardboard(name, ink=None, ink_col=(0.025, 0.022, 0.025, 1)):
    m, nt, b = mat_new(name); g = G(nt)
    cardboard_graph(g, b, os.path.join(TEX, ink) if ink else None, ink_col); return m

def tape_mat():
    m, nt, b = mat_new("M_PackTape"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 25, 4), (0.42, 0.27, 0.10, 1), (0.52, 0.35, 0.14, 1))
    dirt = g.rng(g.noise(obj, 30, 6), 0.5, 0.75)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.45), c, (0.2, 0.15, 0.1, 1))
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(dirt, 0.3, 0.7), b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.4, Distance=0.0008)
    g.L(g.noise(obj, 6, 3, 0.5, mapping_scale=(40, 3, 40)), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def label_mat():
    m, nt, b = mat_new("M_ShipLabel"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    uvn = g.n("ShaderNodeUVMap", uv_map="LabelUV")
    im = g.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(os.path.join(TEX, "label.png")); im.extension = 'EXTEND'
    im.image.colorspace_settings.name = 'Non-Color'; g.L(uvn.outputs[0], im.inputs[0])
    paper = g.mixc(g.noise(obj, 20, 4), (0.62, 0.60, 0.52, 1), (0.68, 0.66, 0.58, 1))
    c = g.mixc(g.math('SUBTRACT', 1.0, im.outputs[0]), paper, (0.06, 0.06, 0.07, 1))
    yel = g.rng(g.noise(obj, 9, 4), 0.45, 0.75)
    c = g.mixc(g.math('MULTIPLY', yel, 0.45), c, (0.5, 0.42, 0.25, 1))
    dirt = g.rng(g.noise(obj, 40, 5), 0.55, 0.8)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.4), c, (0.25, 0.22, 0.18, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6
    return m

def plastic(name, col, rough=0.45, wear=0.5):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    c = g.mixc(g.noise(obj, 20, 4), col, tuple(min(1, v * 1.3) for v in col[:3]) + (1,))
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.62), wear)
    c = g.mixc(edge, c, (0.45, 0.45, 0.45, 1))
    grime = g.rng(g.noise(obj, 35, 6), 0.55, 0.75)
    c = g.mixc(g.math('MULTIPLY', grime, 0.35), c, (0.08, 0.07, 0.06, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 15, 6, 0.65), 0.4, 0.7), True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.5), c, DUST)
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(dust, rough, 0.95), b.inputs["Roughness"])
    return m

def paper_mat():
    m, nt, b = mat_new("M_PaperStack"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    c = g.mixc(g.noise(obj, 10, 4), (0.58, 0.56, 0.50, 1), (0.66, 0.64, 0.57, 1))
    side = g.rng(g.math('ABSOLUTE', sn.outputs[2]), 0.6, 0.3)                    # stacked edges: fine grey lines
    lines = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z', Scale=900.0, Distortion=2.0); g.L(obj, lines.inputs[0])
    c = g.mixc(g.math('MULTIPLY', side, g.math('MULTIPLY', lines.outputs["Fac"], 0.35)), c, (0.3, 0.29, 0.26, 1))
    txt = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Y', Scale=160.0, Distortion=0.0); g.L(obj, txt.inputs[0])
    t2 = g.math('MULTIPLY', g.math('MULTIPLY', g.rng(txt.outputs["Fac"], 0.75, 0.9), g.rng(g.noise(obj, 120, 2), 0.3, 0.6)),
                g.rng(sn.outputs[2], 0.7, 0.9), True)
    c = g.mixc(g.math('MULTIPLY', t2, 0.4), c, (0.2, 0.2, 0.22, 1))
    yel = g.rng(g.noise(obj, 7, 4), 0.45, 0.75)
    c = g.mixc(g.math('MULTIPLY', yel, 0.35), c, (0.52, 0.45, 0.30, 1))
    dust = g.math('MULTIPLY', g.rng(sn.outputs[2], 0.5, 0.95), g.rng(g.noise(obj, 15, 6), 0.35, 0.7), True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.5), c, DUST)
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    return m

M_CB = cardboard("M_Cardboard")
M_CB_CF = cardboard("M_Cardboard_ClosedFront", "face_closed_front.png")
M_CB_OF = cardboard("M_Cardboard_OpenFront", "face_open_front.png")
M_CB_KF = cardboard("M_Cardboard_CrushedFront", "face_crushed_front.png")
M_CB_KS = cardboard("M_Cardboard_CrushedSide", "face_crushed_side.png", (0.10, 0.05, 0.03, 1))
M_TAPE = tape_mat(); M_LABEL = label_mat(); M_PAPER = paper_mat()
M_HOLE = C.plain("M_HandHole", (0.012, 0.01, 0.008, 1), 0.95, 0.0, 0.2)
M_RIM = C.plain("M_CardboardCut", (0.50, 0.40, 0.27, 1), 0.95, 0.0, 0.5)
M_BIND_B = plastic("M_Binder_Blue", (0.035, 0.075, 0.19, 1))
M_BIND_G = plastic("M_Binder_Grey", (0.16, 0.16, 0.165, 1))
M_RING = C.plain("M_BinderRing", (0.5, 0.5, 0.5, 1), 0.35, 1.0, 0.4)
M_SPINE = C.plain("M_SpineLabel", (0.62, 0.6, 0.52, 1), 0.7, 0.0, 0.5)

# ================================================================= helpers
ASSETS = {}
def part(asset, ob, hull=None):
    ob["asset"] = asset
    if hull: ob["hull"] = hull
    ASSETS.setdefault(asset, []).append(ob)
    return ob
def B(asset, *a, hull=None, **k): return part(asset, C.box(*a, **k), hull)

def decal(asset, name, center, axis, w, h, mat, off=0.0006, cuts=6, rot=0.0):
    """grid quad on a box face; axis = '-Y', '+X', '+Z' ...; LabelUV 0..1"""
    bm = bmesh.new(); vs = []
    nu, nv = cuts + 1, max(2, cuts // 2 + 1)
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            vs.append(bm.verts.new(((u - 0.5) * w, (v - 0.5) * h, 0.0)))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nu + 2], vs[a + nu + 1]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    lay = me.uv_layers.new(name="LabelUV")
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = (co.x / w + 0.5, co.y / h + 0.5)
    r = Matrix.Rotation(rot, 3, 'Z')
    basis = {'-Y': Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0))).transposed(),
             '+Y': Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))).transposed(),
             '+X': Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).transposed(),
             '-X': Matrix(((0, -1, 0), (0, 0, 1), (-1, 0, 0))).transposed(),
             '+Z': Matrix(((1, 0, 0), (0, 1, 0), (0, 0, 1))).transposed()}[axis]
    nrm = basis @ Vector((0, 0, 1))
    for v in me.vertices: v.co = basis @ (r @ v.co) + Vector(center) + nrm * off
    ob = C.link(name, me, mat)
    for p in me.polygons: p.use_smooth = False
    return part(asset, ob)

def oval(asset, name, center, axis, w, h, mat, off=0.0008, segs=20):
    bm = bmesh.new()
    vs = [bm.verts.new((math.cos(2 * math.pi * k / segs) * w / 2 * (1 if abs(math.cos(2 * math.pi * k / segs)) > 0.5 else 1),
                        math.sin(2 * math.pi * k / segs) * h / 2, 0)) for k in range(segs)]
    for v in vs:                                               # stadium shape
        v.co.x = max(-w / 2, min(w / 2, v.co.x * 1.25))
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    basis = {'+X': Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).transposed(),
             '-X': Matrix(((0, -1, 0), (0, 0, 1), (-1, 0, 0))).transposed()}[axis]
    nrm = basis @ Vector((0, 0, 1))
    for v in me.vertices: v.co = basis @ v.co + Vector(center) + nrm * off
    ob = part(asset, C.link(name, me, mat))
    if mat is M_HOLE:                                          # torn cut edge around the hole
        rim = oval(asset, name + "_Rim", center, axis, w + 0.008, h + 0.007, M_RIM, off * 0.5, segs)
    return ob

def ink_face(ob, mat, axis, L, W, H):
    """give the wall facing `axis` its own ink material + LabelUV covering the whole wall"""
    me = ob.data; me.materials.append(mat); idx = len(me.materials) - 1
    lay = me.uv_layers.get("LabelUV") or me.uv_layers.new(name="LabelUV")
    ax = Vector({'-Y': (0, -1, 0), '+X': (1, 0, 0)}[axis])
    for p in me.polygons:
        if p.normal.dot(ax) > 0.9:
            p.material_index = idx
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                lay.data[li].uv = ((co.x + L / 2) / L, co.z / H) if axis == '-Y' else ((co.y + W / 2) / W, co.z / H)

def deform(asset, fn):
    for o in ASSETS[asset]:
        for v in o.data.vertices: v.co = fn(v.co)

def tape_strip(asset, name, pts_path, width, mat=M_TAPE, thick=0.0004):
    """tape following a polyline on the box surface; pts_path = [(point, normal)]"""
    bm = bmesh.new(); rows = []
    for k, (p, n) in enumerate(pts_path):
        p, n = Vector(p), Vector(n)
        t = (Vector(pts_path[min(k + 1, len(pts_path) - 1)][0]) - Vector(pts_path[max(k - 1, 0)][0])).normalized()
        s = n.cross(t).normalized()
        rows.append([bm.verts.new(p + n * thick + s * (j / 2 - 0.5) * width) for j in range(3)])
    for a, b2 in zip(rows, rows[1:]):
        for j in range(2):
            bm.faces.new((a[j], a[j + 1], b2[j + 1], b2[j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = C.link(name, me, mat)
    for p in me.polygons: p.use_smooth = False
    return part(asset, ob)

def wrap_x(L, W, H, y, down, n=8):
    """path for tape along X over the top, running `down` metres down both short sides (at height H)"""
    pts = []
    for k in range(n + 1):
        pts.append(((-L / 2, y, H - down + down * k / n), (-1, 0, 0)))
    for k in range(1, 4 * n):
        pts.append(((-L / 2 + L * k / (4 * n), y, H), (0, 0, 1)))
    for k in range(n + 1):
        pts.append(((L / 2, y, H - down * k / n), (1, 0, 0)))
    pts[n] = ((-L / 2, y, H), (-0.7, 0, 0.7)); pts[-n - 1] = ((L / 2, y, H), (0.7, 0, 0.7))
    return pts

# ================================================================= SM_Box_Closed  (0.50 x 0.36 x 0.34)
A = "SM_Box_Closed"
L, W, H = 0.50, 0.36, 0.34
ink_face(B(A, "A_Body", -L / 2, L / 2, -W / 2, W / 2, 0.0, H, [M_CB], bevel=0.004, seg=2, cuts=10, hull="Body"), M_CB_CF, '-Y', L, W, H)
B(A, "A_SeamL", -L / 2 + 0.002, L / 2 - 0.002, -0.0012, 0.0012, H - 0.0006, H + 0.0002, M_HOLE)     # gap between the top flaps
tape_strip(A, "A_Tape", wrap_x(L, W, H, 0.0, 0.07), 0.05)
tape_strip(A, "A_Tape2", [((0.08, -0.12 + 0.03 * k / 6, H), (0, 0, 1)) for k in range(7)] +
           [((0.09 + 0.006 * k, -0.09 + 0.001 * k, H + 0.004 * k * k), (0, 0, 1)) for k in range(1, 4)], 0.05)  # peeled scrap
decal(A, "A_Label", (-0.13, 0.08, H), '+Z', 0.12, 0.09, M_LABEL, off=0.0008, rot=math.radians(5))
for sx in (-1, 1):
    oval(A, f"A_Hole{sx}", (sx * L / 2, 0, H - 0.07), '+X' if sx > 0 else '-X', 0.11, 0.035, M_HOLE)
def closed_def(co):
    x, y, z = co
    bul = 0.007 * math.sin(math.pi * min(1, max(0, (y + W / 2) / W))) * math.sin(math.pi * min(1, max(0, z / H)))
    out = Vector((x + math.copysign(bul, x) * (abs(x) > L / 2 - 0.01),
                  y + math.copysign(bul * 1.3, y) * (abs(y) > W / 2 - 0.01), z))
    if z > H - 0.02 and abs(y) < W / 2 - 0.01 and abs(x) < L / 2 - 0.01:       # top sags a little
        out.z -= 0.008 * math.cos(math.pi * x / L) * math.cos(math.pi * y / W)
    d = (Vector((x, y, z)) - Vector((L / 2, -W / 2, H))).length                    # dented corner
    if d < 0.09: out += Vector((-0.4, 0.5, -1)).normalized() * 0.028 * (1 - d / 0.09) ** 2
    out += Vector((noise.noise(Vector((x * 9, y * 9, z * 9))), noise.noise(Vector((x * 9 + 5, y * 9, z * 9))),
                   noise.noise(Vector((x * 9, y * 9 + 5, z * 9))))) * 0.0018
    return out
deform(A, closed_def)

# ================================================================= SM_Box_Open  archive box (0.45 x 0.33 x 0.30)
Bn = "SM_Box_Open"
L, W, H = 0.45, 0.33, 0.30
B(Bn, "B_Bottom", -L / 2, L / 2, -W / 2, W / 2, 0.0, T, M_CB, hull="Body")
ink_face(B(Bn, "B_WallS", -L / 2, L / 2, -W / 2, -W / 2 + T, 0.0, H, [M_CB], cuts=4, hull="Body"), M_CB_OF, '-Y', L, W, H)
B(Bn, "B_WallN", -L / 2, L / 2, W / 2 - T, W / 2, 0.0, H, M_CB, cuts=4, hull="Body")
B(Bn, "B_WallW", -L / 2, -L / 2 + T, -W / 2 + T, W / 2 - T, 0.0, H, M_CB, cuts=4, hull="Body")
B(Bn, "B_WallE", L / 2 - T, L / 2, -W / 2 + T, W / 2 - T, 0.0, H, M_CB, cuts=4, hull="Body")
for sx in (-1, 1):
    ax = '+X' if sx > 0 else '-X'; ax_in = '-X' if sx > 0 else '+X'
    oval(Bn, f"B_Hole{sx}", (sx * L / 2, 0, H - 0.06), ax, 0.1, 0.032, M_HOLE)
    oval(Bn, f"B_HoleIn{sx}", (sx * (L / 2 - T), 0, H - 0.06), ax_in, 0.1, 0.032, M_HOLE)
decal(Bn, "B_Label", (0.13, -W / 2, 0.075), '-Y', 0.1, 0.075, M_LABEL, off=0.0008, rot=math.radians(-4))
def flap(name, edge, depth, length, ang, torn=False):
    """flap hinged on the top edge of a wall, built standing up, bent outward by `ang` degrees"""
    if edge in ('N', 'S'):
        sgn = 1 if edge == 'N' else -1; y0 = sgn * W / 2
        o = B(Bn, name, -length / 2, length / 2, y0 - (T if sgn > 0 else 0), y0 + (0 if sgn > 0 else T), H, H + depth, M_CB, cuts=5)
        piv = Vector((0, y0, H)); rot = Matrix.Rotation(math.radians(-ang * sgn), 3, 'X')
    else:
        sgn = 1 if edge == 'E' else -1; x0 = sgn * L / 2
        o = B(Bn, name, x0 - (T if sgn > 0 else 0), x0 + (0 if sgn > 0 else T), -length / 2, length / 2, H, H + depth, M_CB, cuts=5)
        piv = Vector((x0, 0, H)); rot = Matrix.Rotation(math.radians(ang * sgn), 3, 'Y')
    for v in o.data.vertices:
        h = v.co.z - H
        if torn and h > depth * 0.45:                       # ragged tear across the flap
            lat = v.co.x if edge in ('N', 'S') else v.co.y
            v.co.z = H + depth * 0.45 + 0.02 * noise.noise(Vector((lat * 30, 1.1, 0.2))) + 0.03 * (lat / length)
            h = v.co.z - H
        bend = 0.02 * (h / depth) ** 2                       # flaps curl, they never stay flat
        if edge in ('N', 'S'): v.co.y += sgn * bend
        else: v.co.x += sgn * bend
        v.co = rot @ (v.co - piv) + piv
    return o
flap("B_FlapN", 'N', W / 2 - 0.01, L - 0.004, 118)
flap("B_FlapS", 'S', W / 2 - 0.01, L - 0.004, 72)
flap("B_FlapE", 'E', W / 2 - 0.02, W - 0.012, 165)
flap("B_FlapW", 'W', W / 2 - 0.02, W - 0.012, 58, torn=True)
# contents: lever-arch files standing (tilted), paper stack, a few sheets
def binder(name, mat, x, tilt, h=0.32, th=0.075, d=0.285):
    ct = 0.003
    parts = [B(Bn, name + "_CoverL", -th / 2, -th / 2 + ct, -d / 2, d / 2, 0.0, h, mat, bevel=0.001),
             B(Bn, name + "_CoverR", th / 2 - ct, th / 2, -d / 2, d / 2, 0.0, h, mat, bevel=0.001),
             B(Bn, name, -th / 2, th / 2, -d / 2, -d / 2 + 0.004, 0.0, h, mat, bevel=0.0015),
             B(Bn, name + "_Pages", -th / 2 + ct + 0.003, th / 2 - ct - 0.008, -d / 2 + 0.02, d / 2 - 0.006, 0.006, h - 0.006, M_PAPER)]
    parts.append(decal(Bn, name + "_Lbl", (0, -d / 2, h * 0.62), '-Y', th * 0.7, 0.12, M_SPINE, off=0.0006, cuts=2))
    ring = C.cyl(name + "_Ring", (0, -d / 2 - 0.0012, h * 0.3), 0.012, 0.002, M_HOLE, axis='Y', segs=16); parts.append(part(Bn, ring))
    rot = Matrix.Rotation(math.radians(tilt), 3, 'Y')
    for o in parts:
        for v in o.data.vertices: v.co = rot @ v.co + Vector((x, 0.005, T))
    return parts
binder("B_FileA", M_BIND_B, -0.17, 4)
binder("B_FileB", M_BIND_B, -0.09, 9)
binder("B_FileC", M_BIND_G, -0.005, 16)
st = B(Bn, "B_Paper", -0.025, 0.025, -0.1485, 0.1485, 0.0, 0.21, M_PAPER, cuts=3)
for v in st.data.vertices:                                     # sheets slid a little against each other
    k = (v.co.x + 0.025) / 0.05
    v.co.z += 0.004 * math.sin(k * 11); v.co.y += 0.003 * math.cos(k * 7)
r = Matrix.Rotation(math.radians(-12), 3, 'Y')
for v in st.data.vertices: v.co = r @ v.co + Vector((0.185, 0.0, T))
for k, (yy, hh, curl) in enumerate([(-0.07, 0.297, 0.05), (0.06, 0.29, 0.035)]):   # loose sheets curling over the rim
    sh = B(Bn, f"B_Sheet{k}", -0.0003, 0.0003, yy - 0.105, yy + 0.105, 0.0, hh, M_PAPER, cuts=8)
    for v in sh.data.vertices:
        h = v.co.z / hh
        lean = 0.03 * h
        over = max(0.0, h - 0.82) / 0.18
        v.co.x += -lean * 0.6 - curl * over * over; v.co.z -= 0.02 * over * over
        v.co.y += 0.008 * math.sin(h * 3 + k)
    for v in sh.data.vertices: v.co += Vector((L / 2 - T - 0.003 - 0.004 * k, 0, T))
open_jit = lambda co: co + Vector((noise.noise(co * 11), noise.noise(co * 11 + Vector((3, 0, 0))), noise.noise(co * 11 + Vector((0, 3, 0))))) * 0.0015
for o in ASSETS[Bn]:
    if o.name.startswith(("B_Wall", "B_Flap")):
        for v in o.data.vertices:
            # walls bow outward a bit under the load
            bw = 0.006 * math.sin(math.pi * min(1, max(0, v.co.z / H)))
            if o.name in ("B_WallS", "B_WallN"): v.co.y += math.copysign(bw, v.co.y) * math.cos(math.pi * v.co.x / L)
            if o.name in ("B_WallE", "B_WallW"): v.co.x += math.copysign(bw, v.co.x) * math.cos(math.pi * v.co.y / W)
            v.co = open_jit(v.co)

# ================================================================= SM_Box_Crushed  (0.55 x 0.40, crushed from 0.40 to ~0.29)
Cn = "SM_Box_Crushed"
L, W, H0 = 0.55, 0.40, 0.40
cb = B(Cn, "C_Body", -L / 2, L / 2, -W / 2, W / 2, 0.0, H0, [M_CB], bevel=0.004, seg=2, cuts=14, hull="Body")
ink_face(cb, M_CB_KF, '-Y', L, W, H0); ink_face(cb, M_CB_KS, '+X', L, W, H0)
B(Cn, "C_SeamL", -L / 2 + 0.002, L / 2 - 0.002, -0.0012, 0.0012, H0 - 0.0006, H0 + 0.0002, M_HOLE)
tp = wrap_x(L, W, H0, 0.0, 0.08, n=10)
cut = len(tp) // 2 + 3                                         # tape split where the top caved in
tape_strip(Cn, "C_TapeA", tp[:cut - 2], 0.05)
tape_strip(Cn, "C_TapeB", tp[cut + 1:], 0.05)
def crushed_def(co):
    x, y, z = co
    zn = z / H0
    comp = 0.74                                               # squashed height
    z2 = z * comp
    cave = 0.085 * math.exp(-((x - 0.06) ** 2 / 0.03 + (y + 0.03) ** 2 / 0.02)) * zn ** 3
    z2 -= cave
    bulge = 0.028 * math.sin(math.pi * zn) * (1 - comp) / 0.26
    sx = 1 if abs(x) > L / 2 - 0.01 else 0; sy = 1 if abs(y) > W / 2 - 0.01 else 0
    x2 = x + math.copysign(bulge, x) * sx * math.cos(math.pi * y / W * 0.9)
    y2 = y + math.copysign(bulge * 1.2, y) * sy * math.cos(math.pi * x / L * 0.9)
    wr = noise.noise(Vector((x * 7, y * 7, z * 7)))                            # creases
    crease = 0.012 * (abs(noise.noise(Vector((x * 4 + 2, y * 4, z * 6)))) - 0.2) * math.sin(math.pi * zn)
    x2 += math.copysign(crease, x) * sx; y2 += math.copysign(crease, y) * sy
    z2 += 0.004 * wr * zn
    d = Vector((x + L / 2, y - W / 2, z - H0)).length                          # NW top corner smashed in
    if d < 0.14:
        f = (1 - d / 0.14) ** 2
        x2 += 0.035 * f; y2 -= 0.03 * f; z2 -= 0.05 * f
    return Vector((x2, y2, max(0.0, z2)))
deform(Cn, crushed_def)

# ================================================================= stage layout
for o in C.PARTS:
    o.data.uv_layers.get("LabelUV") or o.data.uv_layers.new(name="LabelUV")
layout = {A: (0.0, 0.0, 0.0), Bn: (0.75, 0.05, 0.0), Cn: (-0.8, 0.0, 0.0)}
for name, objs in ASSETS.items():
    for o in objs:
        o.location = layout[name]; o["ofs"] = layout[name]
    print(name, len(objs), "parts", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "tris")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage.blend"))
