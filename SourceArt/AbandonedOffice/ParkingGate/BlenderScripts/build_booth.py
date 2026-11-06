"""Abandoned guard booth: sandwich-panel kiosk, front window smashed, side window cracked, door ajar, interior.
python3.11 build_booth.py -> out/stage_booth.blend      (pivot: ground, booth centre; front window faces -Y; metres)
Glass faces carry 'GlassUV' (atlas: front | side | door) and use M_Glass; everything else gets baked.
Collision boxes UCX_SM_GuardBooth_NN are built here (walls, roof, slab, door leaf).
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(12)
X0, X1, Y0, Y1 = -1.0, 1.0, -0.8, 0.8
T = 0.06
ZF, ZW = 0.12, 2.52            # floor level, top of walls
ROOF = 0.12
SEAM = 0.4

# ----------------------------------------------------------------- materials
def panel_material():
    m, nt, b = mat_new("M_Booth_Panel"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    def seam(coord):
        f = g.math('FRACT', g.math('DIVIDE', g.math('ADD', coord, 0.1), SEAM))
        return g.rng(f, 0.03, 0.0)
    sx, sy = seam(sp.outputs[0]), seam(sp.outputs[1])
    seams = g.math('MAXIMUM', g.math('MULTIPLY', sx, g.math('ABSOLUTE', sn.outputs[1])),
                   g.math('MULTIPLY', sy, g.math('ABSOLUTE', sn.outputs[0])))
    c = g.mixc(g.noise(obj, 2, 4), (0.40, 0.41, 0.39, 1), (0.31, 0.32, 0.30, 1))
    grime = g.rng(g.noise(obj, 3, 6, 0.65), 0.35, 0.75)
    c = g.mixc(g.math('MULTIPLY', grime, 0.6), c, (0.14, 0.13, 0.11, 1))
    c = g.mixc(g.math('MULTIPLY', seams, 0.7), c, (0.12, 0.11, 0.1, 1))
    streak = g.math('MULTIPLY', g.rng(g.noise(obj, 4, 5, 0.6, mapping_scale=(5, 5, 0.5)), 0.5, 0.66),
                    g.math('ADD', g.rng(sp.outputs[2], 2.5, 1.4), g.math('MULTIPLY', seams, 0.8)), True)
    c = g.mixc(g.math('MULTIPLY', streak, 0.85), c, (0.22, 0.13, 0.06, 1))           # rust running from roof and seams
    low = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.9, 0.15), g.rng(g.noise(obj, 6, 6), 0.3, 0.65), True)
    c = g.mixc(g.math('MULTIPLY', low, 0.9), c, (0.11, 0.095, 0.08, 1))             # splashed dirt
    pt = g.rng(geo.outputs["Pointiness"], 0.5, 0.58)
    chip = g.rng(g.noise(obj, 25, 8, 0.7), 0.72, 0.76)                  # (no pointiness: big flat panels have no inner verts)
    c = g.mixc(chip, c, (0.33, 0.32, 0.3, 1))
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(160, 160, 14)), 0.765, 0.785)
    c = g.mixc(g.math('MULTIPLY', scr, 0.5), c, (0.6, 0.6, 0.58, 1))
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(streak, 0.5, 0.8); r = g.mixf(low, r, 0.9); g.L(r, b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.4, Distance=0.002)
    g.L(g.math('SUBTRACT', g.math('MULTIPLY', g.noise(obj, 200, 3), 0.1), seams), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def floor_material():
    m, nt, b = mat_new("M_Booth_Floor"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 10, 6), (0.07, 0.075, 0.07, 1), (0.13, 0.13, 0.12, 1))
    wear = g.rng(g.noise(obj, 3, 4), 0.55, 0.75)
    c = g.mixc(g.math('MULTIPLY', wear, 0.6), c, (0.22, 0.2, 0.17, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6
    return m

def glass_material():
    m, nt, b = mat_new("M_Glass"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="GlassUV")
    img = g.n("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(HERE, "tex", "booth_glass.png"))
    g.L(uvn.outputs[0], img.inputs[0])
    g.L(img.outputs[0], b.inputs["Base Color"]); g.L(img.outputs[1], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.12
    m.blend_method = 'BLEND' if hasattr(m, "blend_method") else None
    return m

M_PANEL = panel_material()
M_ALU = C.plain("M_Booth_Alu", (0.42, 0.43, 0.43, 1), 0.45, 0.9, 0.45)
M_FLOOR = floor_material()
M_CON = C.concrete()
M_GLASS = glass_material()
M_SIGN = C.image_material("M_Booth_Sign", os.path.join(HERE, "tex", "booth_sign.png"), "SignUV", 0.5)
M_LAM = C.plain("M_Laminate", (0.30, 0.29, 0.27, 1), 0.5, 0.0, 0.4)
M_BEIGE = C.plain("M_OldPlastic", (0.52, 0.48, 0.40, 1), 0.55, 0.0, 0.4)
M_DARK = C.plain("M_DarkPlastic", (0.03, 0.03, 0.032, 1), 0.35, 0.0, 0.2)
M_PAPER = C.plain("M_Paper", (0.62, 0.60, 0.53, 1), 0.85, 0.0, 0.3)
M_FABRIC = C.plain("M_ChairFabric", (0.06, 0.07, 0.09, 1), 0.9, 0.0, 0.3)

ucx = []
def UCX(x0, x1, y0, y1, z0, z1):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    me = bpy.data.meshes.new("ucx"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(f"UCX_SM_GuardBooth_{len(ucx):02d}", me); bpy.context.scene.collection.objects.link(o)
    o.display_type = 'WIRE'; o.hide_render = True; ucx.append(o); return o

def glass_pane(name, corners, region):
    """corners: 4 world points (bl, br, tr, tl); region 0 front | 1 side | 2 door"""
    bm = bmesh.new(); vs = [bm.verts.new(c) for c in corners]
    f = bm.faces.new(vs); uv = bm.loops.layers.uv.new("GlassUV")
    for l, (u, v) in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        l[uv].uv = ((region + u) / 3.0, v)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return C.link(name, me, M_GLASS)

# ----------------------------------------------------------------- slab, floor, walls
C.box("Slab", X0 - 0.15, X1 + 0.15, Y0 - 0.15, Y1 + 0.15, -0.02, ZF, M_CON, bevel=0.01, cuts=4)
UCX(X0 - 0.15, X1 + 0.15, Y0 - 0.15, Y1 + 0.15, -0.02, ZF)
C.box("Floor", X0 + T, X1 - T, Y0 + T, Y1 - T, ZF, ZF + 0.02, M_FLOOR)
WZ0, WZ1 = 1.05, 2.15                          # window sill / head
# front (-Y) with the big window
C.box("FrontLow", X0, X1, Y0, Y0 + T, ZF, WZ0, M_PANEL, bevel=0.004)
C.box("FrontHigh", X0, X1, Y0, Y0 + T, WZ1, ZW, M_PANEL, bevel=0.004)
C.box("FrontL", X0, X0 + 0.15, Y0, Y0 + T, WZ0, WZ1, M_PANEL, bevel=0.004)
C.box("FrontR", X1 - 0.15, X1, Y0, Y0 + T, WZ0, WZ1, M_PANEL, bevel=0.004)
UCX(X0, X1, Y0, Y0 + T, ZF, ZW)
# back
C.box("Back", X0, X1, Y1 - T, Y1, ZF, ZW, M_PANEL, bevel=0.004)
UCX(X0, X1, Y1 - T, Y1, ZF, ZW)
# left (-X) with a side window
C.box("LeftLow", X0, X0 + T, Y0 + T, Y1 - T, ZF, WZ0, M_PANEL, bevel=0.004)
C.box("LeftHigh", X0, X0 + T, Y0 + T, Y1 - T, WZ1, ZW, M_PANEL, bevel=0.004)
C.box("LeftF", X0, X0 + T, Y0 + T, -0.5, WZ0, WZ1, M_PANEL, bevel=0.004)
C.box("LeftB", X0, X0 + T, 0.5, Y1 - T, WZ0, WZ1, M_PANEL, bevel=0.004)
UCX(X0, X0 + T, Y0 + T, Y1 - T, ZF, ZW)
# right (+X) with the door opening
DY0, DY1, DZ1 = -0.55, 0.25, 2.2
C.box("RightF", X1 - T, X1, Y0 + T, DY0, ZF, ZW, M_PANEL, bevel=0.004)
C.box("RightB", X1 - T, X1, DY1, Y1 - T, ZF, ZW, M_PANEL, bevel=0.004)
C.box("RightTop", X1 - T, X1, DY0, DY1, DZ1, ZW, M_PANEL, bevel=0.004)
UCX(X1 - T, X1, Y0 + T, DY0, ZF, ZW); UCX(X1 - T, X1, DY1, Y1 - T, ZF, ZW); UCX(X1 - T, X1, DY0, DY1, DZ1, ZW)
# roof with overhang + fascia, gutter lip
C.box("Roof", X0 - 0.12, X1 + 0.12, Y0 - 0.12, Y1 + 0.12, ZW, ZW + ROOF, M_PANEL, bevel=0.006, cuts=3)
C.box("RoofLip", X0 - 0.13, X1 + 0.13, Y0 - 0.13, Y0 - 0.11, ZW + ROOF, ZW + ROOF + 0.03, M_ALU)
UCX(X0 - 0.12, X1 + 0.12, Y0 - 0.12, Y1 + 0.12, ZW, ZW + ROOF)
# sign on the front fascia
sign_w, sign_h = 1.1, 0.27
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("SignUV")
sy = Y0 - 0.003
SZ = WZ1 + 0.06
vs = [bm.verts.new((x, sy, z)) for x, z in ((-sign_w / 2, SZ), (sign_w / 2, SZ), (sign_w / 2, SZ + sign_h), (-sign_w / 2, SZ + sign_h))]
f = bm.faces.new(vs)
for l, q in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]): l[uvl].uv = q
me = bpy.data.meshes.new("Sign"); bm.to_mesh(me); bm.free()
signob = C.link("Sign", me, M_SIGN)
if signob.data.polygons[0].normal.y > 0: signob.data.polygons[0].flip()
rot = Matrix.Rotation(math.radians(-3), 3, 'Y')                   # one screw gone -> slightly tilted
for v in signob.data.vertices:
    v.co = rot @ (v.co - Vector((-sign_w / 2, sy, SZ + sign_h))) + Vector((-sign_w / 2, sy, SZ + sign_h))

# ----------------------------------------------------------------- window frames + glass
def frame(name, axis, a0, a1, z0, z1, plane, depth=0.05, w=0.04):
    """aluminium frame in an opening; axis 'x' -> opening spans x, wall plane at y=plane"""
    pieces = [(a0, a1, z0, z0 + w), (a0, a1, z1 - w, z1), (a0, a0 + w, z0, z1), (a1 - w, a1, z0, z1)]
    for k, (b0, b1, c0, c1) in enumerate(pieces):
        if axis == 'x': C.box(f"{name}{k}", b0, b1, plane - depth / 2, plane + depth / 2, c0, c1, M_ALU, bevel=0.003)
        else:           C.box(f"{name}{k}", plane - depth / 2, plane + depth / 2, b0, b1, c0, c1, M_ALU, bevel=0.003)
fy = Y0 + T / 2
frame("FrameFront", 'x', X0 + 0.15, X1 - 0.15, WZ0, WZ1, fy)
C.box("Mullion", -0.02, 0.02, fy - 0.025, fy + 0.025, WZ0, WZ1, M_ALU, bevel=0.003)
glass_pane("GlassFrontL", [Vector((X0 + 0.19, fy, WZ0 + 0.04)), Vector((-0.02, fy, WZ0 + 0.04)), Vector((-0.02, fy, WZ1 - 0.04)), Vector((X0 + 0.19, fy, WZ1 - 0.04))], 0)
glass_pane("GlassFrontR", [Vector((0.02, fy, WZ0 + 0.04)), Vector((X1 - 0.19, fy, WZ0 + 0.04)), Vector((X1 - 0.19, fy, WZ1 - 0.04)), Vector((0.02, fy, WZ1 - 0.04))], 2)
fx = X0 + T / 2
frame("FrameSide", 'y', -0.5, 0.5, WZ0, WZ1, fx)
glass_pane("GlassSide", [Vector((fx, 0.46, WZ0 + 0.04)), Vector((fx, -0.46, WZ0 + 0.04)), Vector((fx, -0.46, WZ1 - 0.04)), Vector((fx, 0.46, WZ1 - 0.04))], 1)
frame("FrameDoor", 'y', DY0, DY1, ZF, DZ1, X1 - T / 2, w=0.035)

# ----------------------------------------------------------------- door leaf, ajar (hinge on the front edge, opens outward)
door_parts = []
DW = DY1 - DY0 - 0.07
hinge = Vector((X1 - 0.005, DY0 + 0.035, 0))
def dbox(name, y0, y1, z0, z1, mat, bev=0.003):
    o = C.box(name, -0.022, 0.022, y0, y1, z0, z1, mat, bevel=bev); door_parts.append(o); return o
LZ0, LZ1 = ZF + 0.03, DZ1 - 0.035
dbox("DoorLow", 0, DW, LZ0, 1.15, M_PANEL); dbox("DoorTop", 0, DW, 1.9, LZ1, M_PANEL)
dbox("DoorSideA", 0, 0.12, 1.15, 1.9, M_PANEL); dbox("DoorSideB", DW - 0.12, DW, 1.15, 1.9, M_PANEL)
dg = glass_pane("GlassDoor", [Vector((0, 0.12, 1.15)), Vector((0, DW - 0.12, 1.15)), Vector((0, DW - 0.12, 1.9)), Vector((0, 0.12, 1.9))], 2)
door_parts.append(dg)
h1 = C.box("Handle", 0.022, 0.06, DW - 0.1, DW - 0.08, 1.02, 1.04, M_ALU, bevel=0.004); door_parts.append(h1)
h2 = C.box("HandleBar", 0.045, 0.06, DW - 0.2, DW - 0.08, 1.02, 1.04, M_ALU, bevel=0.004); door_parts.append(h2)
ang = math.radians(-38)
R = Matrix.Rotation(ang, 4, 'Z')
for o in door_parts:
    for v in o.data.vertices:
        v.co = (R @ v.co.to_4d()).to_3d() + hinge
# door collision (rotated box approximated by its hull)
dco = [v.co.copy() for o in door_parts for v in o.data.vertices]
bm = bmesh.new()
for p in dco: bm.verts.new(p)
bmesh.ops.convex_hull(bm, input=bm.verts[:])
me = bpy.data.meshes.new("ucxd"); bm.to_mesh(me); bm.free()
o = bpy.data.objects.new(f"UCX_SM_GuardBooth_{len(ucx):02d}", me); bpy.context.scene.collection.objects.link(o)
o.display_type = 'WIRE'; o.hide_render = True; ucx.append(o)

# ----------------------------------------------------------------- interior
CZ = 0.88
C.box("Counter", X0 + T, X1 - T, Y0 + T, Y0 + 0.55, CZ - 0.03, CZ, M_LAM, bevel=0.004)
C.box("CounterFront", X0 + T, X1 - T, Y0 + 0.53, Y0 + 0.55, ZF, CZ - 0.03, M_LAM)
C.box("CRT", -0.55, -0.17, Y0 + 0.16, Y0 + 0.52, CZ, CZ + 0.36, M_BEIGE, bevel=0.02)
C.box("CRTscreen", -0.52, -0.20, Y0 + 0.14, Y0 + 0.165, CZ + 0.05, CZ + 0.31, M_DARK, bevel=0.01)
C.box("Keyboard", -0.6, -0.15, Y0 + 0.52, Y0 + 0.36, CZ, CZ + 0.02, M_BEIGE) if False else None
C.box("Keyboard", -0.62, -0.18, Y0 + 0.3, Y0 + 0.45, CZ, CZ + 0.025, M_BEIGE, bevel=0.003, rot=Matrix.Rotation(0.15, 3, 'Z'), pivot=(-0.4, Y0 + 0.37, CZ))
C.cyl("Mug", (0.35, Y0 + 0.35, CZ + 0.05), 0.04, 0.1, M_BEIGE, segs=16)
for k in range(7):                                             # papers on the counter and floor
    zz = CZ + 0.001 + 0.0015 * k if k < 4 else ZF + 0.021
    cx = rnd.uniform(-0.1, 0.7) if k < 4 else rnd.uniform(-0.7, 0.6)
    cy = rnd.uniform(Y0 + 0.2, Y0 + 0.45) if k < 4 else rnd.uniform(-0.1, 0.6)
    C.box(f"Paper{k}", cx - 0.105, cx + 0.105, cy - 0.148, cy + 0.148, zz, zz + 0.001, M_PAPER,
          rot=Matrix.Rotation(rnd.uniform(0, 3.14), 3, 'Z'), pivot=(cx, cy, zz))
# office chair pushed back and turned
chx, chy = 0.15, 0.15
C.cyl("ChairSeat", (chx, chy, 0.52), 0.23, 0.07, M_FABRIC, segs=20)
C.box("ChairBack", chx - 0.2, chx + 0.2, chy + 0.2, chy + 0.24, 0.6, 1.0, M_FABRIC, bevel=0.03,
      rot=Matrix.Rotation(0.6, 3, 'Z') @ Matrix.Rotation(-0.15, 3, 'X'), pivot=(chx, chy, 0.52))
C.cyl("ChairPole", (chx, chy, 0.33), 0.022, 0.32, M_DARK, segs=12)
for k in range(5):
    a = k * 2 * math.pi / 5 + 0.3
    C.box(f"ChairLeg{k}", 0, 0.3, -0.02, 0.02, ZF + 0.04, ZF + 0.07, M_DARK, rot=Matrix.Rotation(a, 3, 'Z'), pivot=(0, 0, 0))
    C.PARTS[-1].location = (0, 0, 0)
    for v in C.PARTS[-1].data.vertices: v.co += Vector((chx, chy, 0))
# ceiling light fixture (diffuser cracked) and a wall clock
C.box("Light", -0.5, 0.5, -0.1, 0.1, ZW - 0.06, ZW - 0.01, M_BEIGE, bevel=0.01)
C.cyl("Clock", (0.4, Y1 - T - 0.015, 2.0), 0.13, 0.03, M_BEIGE, axis='Y', segs=24)
C.cyl("ClockFace", (0.4, Y1 - T - 0.031, 2.0), 0.11, 0.002, M_PAPER, axis='Y', segs=24)

# ----------------------------------------------------------------- broken glass shards: on the ground in front and on the counter
for k in range(16):
    if k < 11:
        cx, cy, cz = rnd.uniform(-0.8, 0.8), rnd.uniform(Y0 - 0.5, Y0 - 0.15), ZF + 0.002 if rnd.random() < 0.5 else 0.002
        cz = ZF + 0.002 if cy > Y0 - 0.15 - 0.0 else ZF + 0.002
        if cy < Y0 - 0.15: cz = 0.002
    else:
        cx, cy, cz = rnd.uniform(-0.1, 0.8), rnd.uniform(Y0 + 0.08, Y0 + 0.45), CZ + 0.002
    s = rnd.uniform(0.03, 0.09)
    pts = [Vector((cx + s * math.cos(a), cy + s * math.sin(a) * rnd.uniform(0.4, 1), cz)) for a in (rnd.uniform(0, 2), rnd.uniform(2, 4), rnd.uniform(4, 6.2))]
    glass_pane(f"Shard{k}", [pts[0], pts[1], pts[2], pts[2] + (pts[0] - pts[2]) * 0.02], 2)
# make sure the slab sits on the ground beyond the booth: shards outside at z=0.002 need ground -> keep them on the slab
for o in C.PARTS:
    if o.name.startswith("Shard"):
        for v in o.data.vertices:
            if Y0 - 0.15 <= v.co.y: v.co.z = max(v.co.z, ZF + 0.002) if v.co.z < CZ else v.co.z

C.finalize(["GlassUV", "SignUV"])
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in C.PARTS)
print("booth parts", len(C.PARTS), "tris", tris, "ucx", len(ucx))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage_booth.blend"))
