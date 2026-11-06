"""Abandoned floor-standing water cooler with an empty, cracked 19 L bottle; unplugged, 'OUT OF ORDER' note.
python3.11 build_cooler.py -> out/stage.blend   (pivot: floor under the body centre, front = -Y, metres)
Bottle uses M_Glass + GlassUV (kept as a separate translucent slot); everything else is baked.
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(8)
DUST = C.DUST

# ================================================================= materials
def plastic(name, col, rough=0.45, wear=0.5, yellow=0.0, streaks=0.0):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 12, 4), col, tuple(v * 0.92 for v in col[:3]) + (1,))
    if yellow:
        c = g.mixc(g.math('MULTIPLY', g.rng(g.noise(obj, 3, 3), 0.35, 0.7), yellow), c, (0.55, 0.50, 0.38, 1))
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.62), wear)
    c = g.mixc(edge, c, (0.30, 0.29, 0.27, 1))
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(250, 250, 25)), 0.765, 0.785)
    c = g.mixc(g.math('MULTIPLY', scr, 0.4), c, (0.25, 0.24, 0.22, 1))
    grime = g.rng(g.noise(obj, 22, 6), 0.52, 0.78)
    c = g.mixc(g.math('MULTIPLY', grime, 0.45), c, (0.20, 0.18, 0.14, 1))
    if streaks:                                               # drips running down from the taps / top
        st = g.math('MULTIPLY', g.rng(g.noise(obj, 4, 5, 0.6, mapping_scale=(40, 40, 1.5)), 0.6, 0.75), streaks, True)
        c = g.mixc(st, c, (0.30, 0.25, 0.17, 1))
    low = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.12, 0.0), 0.6)            # scuffed by mops and shoes
    c = g.mixc(low, c, (0.18, 0.16, 0.13, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 14, 6, 0.65), 0.35, 0.7), True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.7), c, DUST)
    g.L(c, b.inputs["Base Color"])
    g.L(g.mixf(dust, g.mixf(grime, rough, 0.7), 0.95), b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.15, Distance=0.0004)
    g.L(g.math('ADD', g.noise(obj, 500, 2), g.math('MULTIPLY', dust, 0.5)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def glass_material():
    m, nt, b = mat_new("M_Glass"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="GlassUV")
    img = g.n("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(HERE, "tex", "bottle.png"))
    g.L(uvn.outputs[0], img.inputs[0])
    g.L(img.outputs[0], b.inputs["Base Color"]); g.L(img.outputs[1], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.2
    try: m.blend_method = 'BLEND'
    except Exception: pass
    return m

def note_material():
    m, nt, b = mat_new("M_Note"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    uvn = g.n("ShaderNodeUVMap", uv_map="NoteUV")
    im = g.n("ShaderNodeTexImage"); im.image = bpy.data.images.load(os.path.join(HERE, "tex", "note.png")); im.extension = 'EXTEND'
    im.image.colorspace_settings.name = 'Non-Color'; g.L(uvn.outputs[0], im.inputs[0])
    paper = g.mixc(g.noise(obj, 15, 4), (0.62, 0.60, 0.53, 1), (0.68, 0.66, 0.58, 1))
    ink = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, im.outputs[0]), g.rng(g.noise(obj, 80, 3), 0.25, 0.5), True)
    c = g.mixc(g.math('MULTIPLY', ink, 0.9), paper, (0.03, 0.03, 0.04, 1))
    yel = g.rng(g.noise(obj, 8, 4), 0.4, 0.75)
    c = g.mixc(g.math('MULTIPLY', yel, 0.5), c, (0.52, 0.44, 0.27, 1))
    dirt = g.rng(g.noise(obj, 30, 5), 0.55, 0.8)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.4), c, (0.25, 0.22, 0.18, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
    return m

M_BODY = plastic("M_CoolerBody", (0.60, 0.59, 0.55, 1), wear=0.35, yellow=0.9, streaks=0.45)
M_GREY = plastic("M_CoolerGrey", (0.16, 0.165, 0.17, 1), wear=0.5)
M_DARK = plastic("M_CoolerRecess", (0.05, 0.05, 0.055, 1), wear=0.2, streaks=0.6)
M_RED = plastic("M_TapRed", (0.42, 0.04, 0.03, 1), wear=0.5)
M_BLUE = plastic("M_TapBlue", (0.03, 0.09, 0.32, 1), wear=0.5)
M_CUP = plastic("M_PaperCup", (0.62, 0.60, 0.55, 1), rough=0.75, wear=0.3)
M_COIL = C.painted("M_CondenserBlack", (0.03, 0.03, 0.03, 1), primer=(0.25, 0.25, 0.25, 1), chip_amt=0.05, rust=0.5)
M_CORD = plastic("M_PowerCord", (0.02, 0.02, 0.02, 1), rough=0.6, wear=0.0)
M_PIN = C.plain("M_PlugPins", (0.55, 0.55, 0.52, 1), 0.3, 1.0, 0.3)
M_TAPE = plastic("M_Tape", (0.58, 0.56, 0.48, 1), rough=0.4, wear=0.0)
M_LED = C.plain("M_DeadLED", (0.08, 0.02, 0.02, 1), 0.2, 0.0, 0.2)
M_GLASS = glass_material(); M_NOTE = note_material()

P = []
def keep(o): P.append(o); return o
def B(*a, **k): return keep(C.box(*a, **k))
def CY(*a, **k): return keep(C.cyl(*a, **k))

def tube(name, pts, r, mat, segs=8):
    bm = bmesh.new(); rings = []; prev = None
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        a = (t.cross(Vector((0, 0, 1))) if prev is None else prev - t * prev.dot(t))
        if a.length < 1e-4: a = t.cross(Vector((1, 0, 0)))
        a.normalize(); prev = a; b2 = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b2 * math.sin(2 * math.pi * j / segs)) * r) for j in range(segs)])
    for k in range(len(pts) - 1):
        for j in range(segs):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % segs], rings[k + 1][(j + 1) % segs], rings[k + 1][j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = C.link(name, me, mat)
    for p in me.polygons: p.use_smooth = True
    return keep(ob)

def spline(ctrl, n=10):
    Pp = [ctrl[0]] + ctrl + [ctrl[-1]]; out = []
    for i in range(1, len(Pp) - 2):
        p0, p1, p2, p3 = Pp[i - 1], Pp[i], Pp[i + 1], Pp[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1]); return out

# ================================================================= body 0.31 x 0.32 x 0.98
W, D, H = 0.31, 0.32, 0.98
X0, X1, Y0, Y1 = -W / 2, W / 2, -D / 2, D / 2
RZ0, RZ1, RX = 0.55, 0.90, 0.11              # tap alcove
B("Plinth", X0 + 0.01, X1 - 0.01, Y0 + 0.01, Y1 - 0.01, 0.0, 0.035, M_GREY, bevel=0.004)
B("BodyLow", X0, X1, Y0, Y1, 0.035, RZ0, M_BODY, bevel=0.012, seg=3, cuts=3)
B("BodyTop", X0, X1, Y0, Y1, RZ1, H, M_BODY, bevel=0.012, seg=3, cuts=2)
B("PillarL", X0, -RX, Y0, Y1, RZ0 - 0.005, RZ1 + 0.005, M_BODY, bevel=0.006, cuts=2)
B("PillarR", RX, X1, Y0, Y1, RZ0 - 0.005, RZ1 + 0.005, M_BODY, bevel=0.006, cuts=2)
B("BodyMidBack", -RX, RX, Y0 + 0.065, Y1, RZ0 - 0.005, RZ1 + 0.005, M_BODY, bevel=0.004)
B("RecessBack", -RX, RX, Y0 + 0.06, Y0 + 0.066, RZ0, RZ1, M_DARK, cuts=3)
B("RecessTop", -RX, RX, Y0 + 0.002, Y0 + 0.066, RZ1 - 0.01, RZ1, M_DARK)
B("RecessFloor", -RX, RX, Y0 + 0.002, Y0 + 0.066, RZ0, RZ0 + 0.008, M_DARK)
# cabinet door seam + dead power LEDs on the lower front
B("DoorSeamL", X0 + 0.02, X0 + 0.023, Y0 - 0.0008, Y0 + 0.002, 0.08, 0.5, M_DARK)
B("DoorSeamR", X1 - 0.023, X1 - 0.02, Y0 - 0.0008, Y0 + 0.002, 0.08, 0.5, M_DARK)
B("DoorSeamT", X0 + 0.02, X1 - 0.02, Y0 - 0.0008, Y0 + 0.002, 0.497, 0.5, M_DARK)
B("DoorSeamB", X0 + 0.02, X1 - 0.02, Y0 - 0.0008, Y0 + 0.002, 0.08, 0.083, M_DARK)
B("DoorPull", -0.04, 0.04, Y0 - 0.012, Y0 + 0.001, 0.46, 0.475, M_GREY, bevel=0.003)
for k, col in enumerate([M_LED, M_LED]):
    CY(f"LED{k}", (-0.02 + 0.04 * k, Y0 - 0.001, RZ1 + 0.04), 0.004, 0.004, col, axis='Y', segs=10)
# drip tray with grille, slight crack in the front lip
B("Tray", -RX + 0.008, RX - 0.008, Y0 - 0.03, Y0 + 0.06, RZ0 + 0.008, RZ0 + 0.03, M_GREY, bevel=0.003)
for k in range(9):
    x = -RX + 0.02 + k * (2 * RX - 0.04) / 8
    B(f"Grille{k}", x - 0.0035, x + 0.0035, Y0 - 0.026, Y0 + 0.055, RZ0 + 0.03, RZ0 + 0.034, M_DARK)
# taps: hot (red) left, cold (blue) right
for sx, mat in ((-1, M_RED), (1, M_BLUE)):
    x = sx * 0.045
    CY(f"TapBody{sx}", (x, Y0 + 0.035, RZ1 - 0.06), 0.014, 0.055, M_GREY, axis='Y', segs=16)
    CY(f"TapNozzle{sx}", (x, Y0 + 0.016, RZ1 - 0.08), 0.006, 0.03, M_GREY, segs=12)
    B(f"TapPaddle{sx}", x - 0.016, x + 0.016, Y0 + 0.0, Y0 + 0.022, RZ1 - 0.052, RZ1 - 0.035, mat, bevel=0.003)
# crumpled paper cup left on the tray
cup = CY("Cup", (0.03, Y0 + 0.025, RZ0 + 0.072), 0.032, 0.075, M_CUP, r2=0.024, segs=18, cap=True)
for v in cup.data.vertices:
    v.co -= Vector((0.03, Y0 + 0.025, RZ0 + 0.072))
    v.co.x *= 1.0 + 0.18 * noise.noise(v.co * 40); v.co.y *= 0.82 + 0.15 * noise.noise(v.co * 35 + Vector((2, 0, 0)))
    v.co = Matrix.Rotation(math.radians(80), 3, 'Y') @ v.co
    v.co += Vector((0.035, Y0 + 0.02, RZ0 + 0.034 + 0.025))
cup.data.polygons.foreach_set("use_smooth", [True] * len(cup.data.polygons))
# bottle seat on top
CY("Collar", (0, 0, H + 0.012), 0.11, 0.024, M_GREY, segs=36)
CY("CollarLip", (0, 0, H + 0.026), 0.06, 0.006, M_DARK, segs=24)
# back: condenser coil grid
for k in range(7):
    z = 0.18 + k * 0.1
    tube(f"Coil{k}", [Vector((-0.11, Y1 + 0.022, z)), Vector((0.11, Y1 + 0.022, z))], 0.0045, M_COIL, 8)
for k in range(12):
    x = -0.1 + k * 0.2 / 11
    B(f"CoilWire{k}", x - 0.0012, x + 0.0012, Y1 + 0.014, Y1 + 0.017, 0.16, 0.82, M_COIL)
for sx in (-1, 1):
    B(f"CoilBracket{sx}", sx * 0.12 - 0.008, sx * 0.12 + 0.008, Y1, Y1 + 0.026, 0.15, 0.83, M_COIL)
# power cord: out of the back, down, across the floor, plug lying loose (unplugged)
cord = spline([Vector((0.08, Y1 + 0.005, 0.12)), Vector((0.09, Y1 + 0.05, 0.06)), Vector((0.1, Y1 + 0.1, 0.006)),
               Vector((0.22, Y1 + 0.2, 0.004)), Vector((0.18, Y1 + 0.36, 0.004)), Vector((0.32, Y1 + 0.44, 0.005))], 8)
tube("Cord", cord, 0.0035, M_CORD, 8)
pe = cord[-1]; pd = (cord[-1] - cord[-2]).normalized(); yaw = math.atan2(pd.y, pd.x)
plug = [B("Plug", 0.0, 0.045, -0.018, 0.018, 0.0, 0.024, M_CORD, bevel=0.005, seg=2)]
for s in (-1, 1):
    plug.append(CY(f"Pin{s}", (0.06, s * 0.0095, 0.012), 0.002, 0.03, M_PIN, axis='X', segs=8))
for o in plug:
    for v in o.data.vertices: v.co = Matrix.Rotation(yaw, 3, 'Z') @ v.co + Vector((pe.x, pe.y, 0.0))
# OUT OF ORDER note taped on the lower front, two strips of tape
NW, NH = 0.15, 0.10
bm = bmesh.new(); vs = []
nu, nv = 6, 4
for j in range(nv + 1):
    for i in range(nu + 1):
        vs.append(bm.verts.new(((i / nu - 0.5) * NW, 0, (j / nv - 0.5) * NH)))
for j in range(nv):
    for i in range(nu):
        a = j * (nu + 1) + i
        bm.faces.new((vs[a], vs[a + 1], vs[a + nu + 2], vs[a + nu + 1]))
me = bpy.data.meshes.new("Note"); bm.to_mesh(me); bm.free()
lay = me.uv_layers.new(name="NoteUV")
for p in me.polygons:
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        lay.data[li].uv = (co.x / NW + 0.5, co.z / NH + 0.5)
rot = Matrix.Rotation(math.radians(-4), 3, 'Y')
for v in me.vertices:
    co = rot @ v.co
    curl = 0.012 * max(0.0, (co.z + NH / 2 - 0.07)) / 0.03 if co.z > 0.02 else 0.0        # top corner peeling off
    co.y -= 0.0012 + curl * max(0.0, co.x / (NW / 2))
    v.co = co + Vector((0.0, Y0, 0.32))
note = keep(C.link("Note", me, M_NOTE))
for s in (-1, 1):
    tp = B(f"NoteTape{s}", -0.012, 0.012, Y0 - 0.0022, Y0 - 0.0016, -0.03, 0.03, M_TAPE)
    for v in tp.data.vertices: v.co = Matrix.Rotation(math.radians(-4 + s * 30), 3, 'Y') @ v.co + Vector((s * 0.07, 0, 0.32 + 0.045 * (1 if s < 0 else -1)))

# ================================================================= the bottle (upside down, empty, a bit askew)
prof = [(0.0265, H + 0.006), (0.0265, H + 0.055), (0.033, H + 0.06), (0.033, H + 0.072), (0.03, H + 0.078),
        (0.05, H + 0.10), (0.09, H + 0.13), (0.125, H + 0.165), (0.135, H + 0.2)]
z = H + 0.2
for k in range(5):                               # ribbed body
    prof += [(0.135, z + 0.03), (0.131, z + 0.038), (0.131, z + 0.046), (0.135, z + 0.054)]; z += 0.06
prof += [(0.135, z + 0.035), (0.128, z + 0.055), (0.11, z + 0.064), (0.06, z + 0.066), (0.0, z + 0.062)]
SEG = 40
bm = bmesh.new(); rings = []
for (r, zz) in prof:
    rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / SEG), r * math.sin(2 * math.pi * j / SEG), zz)) for j in range(SEG)])
for a, b2 in zip(rings, rings[1:]):
    for j in range(SEG):
        bm.faces.new((a[j], a[(j + 1) % SEG], b2[(j + 1) % SEG], b2[j]))
me = bpy.data.meshes.new("Bottle"); bm.to_mesh(me); bm.free()
zmin, zmax = prof[0][1], prof[-1][1]
lay = me.uv_layers.new(name="GlassUV")
for p in me.polygons:
    us = []
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        us.append(((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, (co.z - zmin) / (zmax - zmin)))
    umax = max(u for u, _ in us)
    for li, (u, vv) in zip(p.loop_indices, us):
        if umax - u > 0.5: u += 1.0                       # seam fix
        lay.data[li].uv = (u, vv)
tilt = Matrix.Rotation(math.radians(2.5), 3, 'X') @ Matrix.Rotation(math.radians(1.5), 3, 'Y')
piv = Vector((0, 0, H + 0.03))
for v in me.vertices:
    co = v.co.copy()
    if co.z > H + 0.2:                                    # thin polycarbonate: a soft dent on one side
        d = (Vector((co.x, co.y, co.z)) - Vector((0.12, -0.06, H + 0.33))).length
        if d < 0.08: co -= Vector((co.x, co.y, 0)).normalized() * 0.014 * (1 - d / 0.08) ** 2
    v.co = tilt @ (co - piv) + piv
bottle = keep(C.link("Bottle", me, M_GLASS))
for p in me.polygons: p.use_smooth = True

# ================================================================= collision (stage UCX objects, picked up by bake_prop booth mode)
def ucx_box(name, x0, x1, y0, y1, z0, z1):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o); o.display_type = 'WIRE'; o.hide_render = True
ucx_box("UCX_SM_WaterCooler_00", X0, X1, Y0 - 0.03, Y1 + 0.03, 0.0, H + 0.03)
bm = bmesh.new()
for v in list(me.vertices)[::3]: bm.verts.new(v.co)
bmesh.ops.convex_hull(bm, input=bm.verts[:])
m = bpy.data.meshes.new("ucxb"); bm.to_mesh(m); bm.free()
o = bpy.data.objects.new("UCX_SM_WaterCooler_01", m); bpy.context.scene.collection.objects.link(o); o.display_type = 'WIRE'; o.hide_render = True

C.finalize(["NoteUV", "GlassUV"])
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in C.PARTS)
print("cooler parts", len(C.PARTS), "tris", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage.blend"))
