"""Grounds kit for the office compound (Blender 4.2). python3.11 build_grounds.py -> out/stage_grounds.blend
Parts carry 'asset', 'ofs', 'hull'. Chain-link quads use material M_ChainLink + 'ChainUV' (1 m tiling, masked in Unreal);
everything else is baked into T_GroundsKit.
Fence pieces: run along +X from the pivot (post at x=0), OUTSIDE is Blender +Y (= Unreal -Y), barbed-wire arms lean outside.
  SM_Fence_Panel          3 m section, 2.0 m mesh + 3 strands of barbed wire
  SM_Fence_PanelDamaged   3 m section: torn hole, mesh bulged, top rail bent
  SM_Fence_Post           single post (corners / ends)
  SM_FenceGate_8m         two posts 8 m apart, left leaf swung in 75 deg, right leaf sagging half open (inside = Blender -Y)
  SM_StreetLamp           7 m steel lamp post with cobra head
  SM_StreetLamp_Broken    pole bent over, head hanging on its cable
  SM_JerseyBarrier        2 m concrete road barrier with faded red/white stripes
  SM_Dumpster             green 1100 l waste container, one lid open
  SM_Container20          20 ft shipping container, faded blue, rust
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(77)

# ================================================================= materials
M_GALV = C.painted("M_Galvanised", (0.36, 0.37, 0.36, 1), primer=(0.25, 0.25, 0.24, 1), chip_amt=0.05, rough=0.5, rust=0.75)
M_POLE = C.painted("M_LampPole", (0.40, 0.42, 0.41, 1), primer=(0.25, 0.25, 0.25, 1), chip_amt=0.08, rough=0.5, rust=0.6, streak_from=6.0)
M_DARKM = C.plain("M_LampHead", (0.12, 0.12, 0.12, 1), 0.5, 0.3, 0.5)
M_LENS = C.plain("M_LampLensBroken", (0.03, 0.035, 0.035, 1), 0.15, 0.0, 0.3)
M_CON = C.concrete()
M_GREEN = C.painted("M_DumpsterGreen", (0.07, 0.20, 0.11, 1), primer=(0.08, 0.08, 0.08, 1), chip_amt=0.08, rough=0.55, rust=0.8, streak_from=1.2)
M_LID = C.plain("M_DumpsterLid", (0.025, 0.025, 0.025, 1), 0.6, 0.0, 0.4)
M_RUB = C.plain("M_Rubber", (0.02, 0.02, 0.02, 1), 0.8, 0.0, 0.3)
M_BLUE = C.painted("M_ContainerBlue", (0.07, 0.17, 0.30, 1), primer=(0.18, 0.08, 0.04, 1), chip_amt=0.1, rough=0.55, rust=1.0, streak_from=2.6)
M_CHAIN = bpy.data.materials.new("M_ChainLink")                  # not baked; tiling masked material in Unreal

def jersey_mat():
    m, nt, b = mat_new("M_JerseyConcrete"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 10, 7, 0.65), (0.36, 0.35, 0.33, 1), (0.50, 0.49, 0.46, 1))
    band = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.5, 0.52), g.rng(sp.outputs[2], 0.72, 0.70), True)   # stripe band height
    stripes = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='X', Scale=2.0, Distortion=0.0); g.L(obj, stripes.inputs[0])
    red = g.rng(stripes.outputs["Fac"], 0.48, 0.52)
    paint = g.mixc(red, (0.62, 0.60, 0.55, 1), (0.42, 0.07, 0.05, 1))
    worn = g.rng(g.noise(obj, 6, 5), 0.42, 0.55)
    c = g.mixc(g.math('MULTIPLY', band, worn), c, paint)
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.6), 0.6)
    c = g.mixc(edge, c, (0.55, 0.54, 0.5, 1))
    low = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.15, 0.0), 0.7)
    c = g.mixc(low, c, (0.15, 0.14, 0.11, 1))
    moss = g.math('MULTIPLY', g.rng(g.noise(obj, 7, 5), 0.62, 0.72), 0.6)
    c = g.mixc(moss, c, (0.14, 0.18, 0.08, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    bump = g.n("ShaderNodeBump", Strength=0.5, Distance=0.002)
    g.L(g.noise(obj, 90, 5), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m
M_JER = jersey_mat()

ASSETS = {}
def part(asset, ob, hull=None):
    ob["asset"] = asset
    if hull: ob["hull"] = hull
    ASSETS.setdefault(asset, []).append(ob); return ob
def B(asset, *a, hull=None, **k): return part(asset, C.box(*a, **k), hull)
def CY(asset, *a, hull=None, **k): return part(asset, C.cyl(*a, **k), hull)

def tube(asset, name, pts, r, mat, segs=8, hull=None):
    bm = bmesh.new(); rings = []; prev = None
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        a = t.cross(Vector((0, 0, 1))) if prev is None else prev - t * prev.dot(t)
        if a.length < 1e-4: a = t.cross(Vector((1, 0, 0)))
        a.normalize(); prev = a; b2 = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b2 * math.sin(2 * math.pi * j / segs)) * r) for j in range(segs)])
    for k in range(len(pts) - 1):
        for j in range(segs):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % segs], rings[k + 1][(j + 1) % segs], rings[k + 1][j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = C.link(name, me, mat)
    for p in me.polygons: p.use_smooth = True
    return part(asset, ob, hull)

def chain_quad(asset, name, x0, x1, z0, z1, nx=12, nz=8, hole=None, bulge=None, xform=None):
    """chain-link sheet in the XZ plane; hole=(cx, cz, rx, rz) removes faces; bulge(x,z)->dy; xform(Vector)->Vector"""
    bm = bmesh.new(); vs = {}
    for j in range(nz + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx; z = z0 + (z1 - z0) * j / nz
            y = bulge(x, z) if bulge else 0.0
            vs[i, j] = bm.verts.new((x, y, z))
    uvl = bm.loops.layers.uv.new("ChainUV")
    for j in range(nz):
        for i in range(nx):
            cx = x0 + (x1 - x0) * (i + 0.5) / nx; cz = z0 + (z1 - z0) * (j + 0.5) / nz
            if hole and ((cx - hole[0]) / hole[2]) ** 2 + ((cz - hole[1]) / hole[3]) ** 2 + 0.25 * noise.noise(Vector((cx * 3, cz * 3, 0))) < 1:
                continue
            q = [vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]]
            f = bm.faces.new(q)
            for l in f.loops: l[uvl].uv = (l.vert.co.x, l.vert.co.z)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    if xform:
        for v in bm.verts: v.co = xform(v.co)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return part(asset, C.link(name, me, M_CHAIN))

def fence_post(asset, name, x, h=2.0, r=0.03, lean=None):
    pts = [Vector((x, 0, -0.3)), Vector((x, 0, h))]
    arm = [Vector((x, 0, h)), Vector((x, 0.30, h + 0.32))]          # barbed-wire arm, leaning outside (+Y)
    T = (lambda p: p) if lean is None else lean
    tube(asset, name, [T(p) for p in pts], r, M_GALV, 8, hull="Fence")
    tube(asset, name + "_Arm", [T(p) for p in arm], 0.012, M_GALV, 6)
    CY(asset, name + "_Cap", tuple(T(Vector((x, 0, h + 0.01)))), r * 1.15, 0.03, M_GALV, segs=8)

def barbed(asset, name, x0, x1, T=lambda p: p, sag=0.04):
    for k in range(3):
        t = (k + 1) / 3
        y, z = 0.30 * t, 2.0 + 0.32 * t
        pts = [Vector((x0 + (x1 - x0) * i / 10, y, z - sag * math.sin(math.pi * i / 10))) for i in range(11)]
        tube(asset, f"{name}_Wire{k}", [T(p) for p in pts], 0.0025, M_GALV, 4)

# ================================================================= fence panel (intact)
A = "SM_Fence_Panel"
fence_post(A, "P_Post", 0.0)
tube(A, "P_TopRail", [Vector((0, 0.0, 1.98)), Vector((3.0, 0.0, 1.98))], 0.02, M_GALV, 8)
tube(A, "P_BotWire", [Vector((0, 0.0, 0.08 + 0.03 * math.sin(math.pi * i / 6))) + Vector((3.0 * i / 6, 0, 0)) for i in range(7)], 0.004, M_GALV, 4)
chain_quad(A, "P_Mesh", 0.03, 2.97, 0.06, 1.97, bulge=lambda x, z: 0.04 * math.sin(math.pi * x / 3) * math.sin(math.pi * z / 2))["hull"] = "Fence"
barbed(A, "P_Barb", 0.0, 3.0)

# ================================================================= fence panel (damaged)
A = "SM_Fence_PanelDamaged"
fence_post(A, "D_Post", 0.0)
bend = lambda x: -0.35 * math.exp(-((x - 1.7) / 0.6) ** 2)
tube(A, "D_TopRail", [Vector((3.0 * i / 12, 0.08 * math.exp(-((3.0 * i / 12 - 1.7) / 0.6) ** 2), 1.98 + bend(3.0 * i / 12))) for i in range(13)], 0.02, M_GALV, 8)
chain_quad(A, "D_Mesh", 0.03, 2.97, 0.06, 1.97, nx=18, nz=12, hole=(1.5, 0.75, 0.55, 0.6),
           bulge=lambda x, z: -0.22 * math.exp(-(((x - 1.5) / 0.9) ** 2 + ((z - 0.8) / 0.7) ** 2)) + 0.03 * math.sin(math.pi * x / 3))["hull"] = "Fence"
# torn mesh flap peeled back from the hole
chain_quad(A, "D_Flap", 1.2, 1.75, 0.3, 0.75, nx=4, nz=4,
           xform=lambda p: Matrix.Rotation(math.radians(-60), 3, 'Z') @ (p - Vector((1.2, 0, 0))) + Vector((1.2, -0.05, 0)) + Vector((0, 0, -0.1 * (p.x - 1.2))))
barbed(A, "D_Barb", 0.0, 1.2, sag=0.02)
for k in range(2):                                              # snapped wires hanging down
    pts = [Vector((1.2, 0.1 + 0.1 * k, 2.1 + 0.1 * k)), Vector((1.35, 0.15 + 0.1 * k, 1.8)), Vector((1.4, 0.2, 1.5 - 0.2 * k))]
    tube(A, f"D_Hang{k}", pts, 0.0025, M_GALV, 4)

# ================================================================= single post
A = "SM_Fence_Post"
fence_post(A, "S_Post", 0.0, r=0.04)

# ================================================================= gate 8 m (inside = -Y)
A = "SM_FenceGate_8m"
for x in (0.0, 8.0):
    tube(A, f"G_Post{x:.0f}", [Vector((x, 0, -0.4)), Vector((x, 0, 2.4))], 0.055, M_GALV, 10, hull="Post%d" % x)
    CY(A, f"G_Cap{x:.0f}", (x, 0, 2.41), 0.065, 0.04, M_GALV, segs=10)
def leaf(name, hinge_x, width, sign, ang, sag=0.0, hull=None):
    """leaf frame + mesh, hinged at hinge_x, extending sign*X; ang = swing inward (deg)"""
    rot = Matrix.Rotation(math.radians(-ang * sign), 3, 'Z')     # inward = -Y
    def T(p):
        q = Vector((p.x - hinge_x, p.y, p.z))
        q.z -= sag * (abs(q.x) / width) ** 1.5
        return rot @ q + Vector((hinge_x, 0, 0))
    x_far = hinge_x + sign * width
    fr = [Vector((hinge_x + sign * 0.08, 0, 0.12)), Vector((x_far, 0, 0.12)), Vector((x_far, 0, 2.0)), Vector((hinge_x + sign * 0.08, 0, 2.0)), Vector((hinge_x + sign * 0.08, 0, 0.12))]
    for k in range(4):
        tube(A, f"{name}_Frame{k}", [T(fr[k]), T(fr[k + 1])], 0.025, M_GALV, 8, hull=hull if k == 0 else None)
    tube(A, f"{name}_Brace", [T(fr[0]), T(fr[2])], 0.018, M_GALV, 6)
    lo, hi = sorted((hinge_x + sign * 0.1, x_far - sign * 0.02))
    cq = chain_quad(A, f"{name}_Mesh", lo, hi, 0.14, 1.98, nx=10, nz=8, xform=T)
    if hull: cq["hull"] = hull
    barbed(A, f"{name}_Barb", lo, hi, T=T, sag=0.02)
    return T
leaf("G_L", 0.0, 3.95, 1, 75, hull="LeafL")
leaf("G_R", 8.0, 3.95, -1, 25, sag=0.12, hull="LeafR")
CY(A, "G_Lock", (4.0, -0.2, 1.0), 0.03, 0.12, M_GALV, axis='X', segs=8)

# ================================================================= street lamps
def lamp(asset, broken=False):
    H = 7.0
    bendm = (lambda p: p) if not broken else \
        (lambda p: Matrix.Rotation(math.radians(-16), 3, 'X') @ (p - Vector((0, 0, 0.6))) + Vector((0, 0, 0.6)) if p.z > 0.6 else p)
    pole = [Vector((0, 0, -0.5 + 0.5 * i)) for i in range(16)]
    radii = [0.11 - 0.06 * max(0, p.z) / H for p in pole]
    bm = bmesh.new(); rings = []
    for p, r in zip(pole, radii):
        q = bendm(p)
        rings.append([bm.verts.new(q + Vector((math.cos(2 * math.pi * j / 12) * r, math.sin(2 * math.pi * j / 12) * r, 0))) for j in range(12)])
    for a, b2 in zip(rings, rings[1:]):
        for j in range(12): bm.faces.new((a[j], a[(j + 1) % 12], b2[(j + 1) % 12], b2[j]))
    me = bpy.data.meshes.new(asset + "_Pole"); bm.to_mesh(me); bm.free()
    o = part(asset, C.link(asset + "_Pole", me, M_POLE), hull="Pole")
    for p in o.data.polygons: p.use_smooth = True
    B(asset, asset + "_Base", -0.16, 0.16, -0.16, 0.16, 0.0, 0.04, M_POLE, bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1): CY(asset, f"{asset}_Bolt{sx}{sy}", (sx * 0.12, sy * 0.12, 0.05), 0.012, 0.03, M_DARKM, segs=6)
    arm = [Vector((0, 0, H - 0.4)), Vector((0, 0.15, H + 0.05)), Vector((0, 0.6, H + 0.25)), Vector((0, 1.5, H + 0.3))]
    tube(asset, asset + "_Arm", [bendm(p) for p in arm], 0.045, M_POLE, 8)
    end = bendm(arm[-1])
    head = [B(asset, asset + "_Head", -0.16, 0.16, 0.0, 0.62, -0.12, 0.0, M_DARKM, bevel=0.04, seg=3),
            B(asset, asset + "_Lens", -0.12, 0.12, 0.08, 0.5, -0.125, -0.11, M_LENS)]
    if broken:                                                     # head torn off, dangling on its cable
        hang = end + Vector((0, 0.05, -1.4))
        rot = Matrix.Rotation(math.radians(80), 3, 'X') @ Matrix.Rotation(math.radians(20), 3, 'Z')
        for o in head:
            for v in o.data.vertices: v.co = rot @ v.co + hang
        tube(asset, asset + "_Cable", [end, end + Vector((0.02, 0.03, -0.5)), end + Vector((0.0, 0.05, -1.0)), hang + Vector((0, 0, 0.0))], 0.008, M_RUB, 5)
    else:
        for o in head:
            for v in o.data.vertices: v.co = v.co + end - Vector((0, 0.05, 0))
    CY(asset, asset + "_Door", tuple(bendm(Vector((0, -0.105, 0.9)))), 0.05, 0.004, M_DARKM, axis='Y', segs=8)
lamp("SM_StreetLamp"); lamp("SM_StreetLamp_Broken", True)

# ================================================================= jersey barrier
A = "SM_JerseyBarrier"
prof = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.12, 0.33), (0.075, 0.8), (-0.075, 0.8), (-0.12, 0.33), (-0.3, 0.08)]
bm = bmesh.new(); rings = []
for k in range(9):
    x = -1.0 + 2.0 * k / 8
    rings.append([bm.verts.new((x, y, z)) for y, z in prof])
for a, b2 in zip(rings, rings[1:]):
    for j in range(len(prof)): bm.faces.new((a[j], a[(j + 1) % len(prof)], b2[(j + 1) % len(prof)], b2[j]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1]); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("Jersey"); bm.to_mesh(me); bm.free()
j = part(A, C.link("Jersey", me, M_JER), hull="J")
for v in j.data.vertices:
    if v.co.z > 0.02: v.co += Vector((noise.noise(v.co * 8), noise.noise(v.co * 8 + Vector((3, 0, 0))), noise.noise(v.co * 8 + Vector((0, 3, 0))))) * 0.008
    d = (v.co - Vector((0.95, 0.07, 0.8))).length
    if d < 0.2: v.co += Vector((-0.5, -0.3, -1)).normalized() * 0.07 * (1 - d / 0.2)   # chipped corner
for sx in (-1, 1):
    B(A, f"J_Lift{sx}", sx * 0.55 - 0.06, sx * 0.55 + 0.06, -0.08, 0.08, 0.795, 0.805, M_DARKM)

# ================================================================= dumpster
A = "SM_Dumpster"
body = B(A, "Dm_Body", -0.68, 0.68, -0.5, 0.5, 0.18, 1.25, M_GREEN, bevel=0.02, cuts=2, hull="Body")
for v in body.data.vertices:                                    # tapered towards the bottom
    k = (1.25 - v.co.z) / 1.07
    v.co.x *= 1 - 0.08 * k; v.co.y *= 1 - 0.12 * k
B(A, "Dm_Rim", -0.72, 0.72, -0.55, 0.55, 1.22, 1.27, M_GREEN, bevel=0.01)
for sx in (-1, 1):
    B(A, f"Dm_Pocket{sx}", sx * 0.69 - 0.03, sx * 0.69 + 0.03, -0.35, 0.35, 0.75, 0.9, M_GREEN, bevel=0.005)
    for sy in (-1, 1):
        CY(A, f"Dm_Wheel{sx}{sy}", (sx * 0.5, sy * 0.33, 0.09), 0.085, 0.05, M_RUB, axis='X', segs=12)
        B(A, f"Dm_Fork{sx}{sy}", sx * 0.5 - 0.04, sx * 0.5 + 0.04, sy * 0.33 - 0.04, sy * 0.33 + 0.04, 0.12, 0.2, M_DARKM)
lid1 = B(A, "Dm_LidA", -0.71, 0.0, -0.56, 0.56, 1.27, 1.31, M_LID, bevel=0.01)
lid2 = B(A, "Dm_LidB", 0.0, 0.71, -0.56, 0.56, 1.27, 1.31, M_LID, bevel=0.01)
for v in lid2.data.vertices:                                     # thrown open, resting against the back
    v.co = Matrix.Rotation(math.radians(-110), 3, 'X') @ (v.co - Vector((0, 0.56, 1.27))) + Vector((0, 0.56, 1.27))
# rubbish bags poking out
for k in range(3):
    o = C.dome(f"Dm_Bag{k}", (0.1 + 0.18 * k, -0.1 + 0.1 * k, 1.16), 0.2, M_RUB, segs=10, rings=4); part(A, o)
    for v in o.data.vertices: v.co.z = 1.16 + (v.co.z - 1.16) * 0.8 + 0.02 * noise.noise(v.co * 10)

# ================================================================= 20 ft container (6.06 x 2.44 x 2.59)
A = "SM_Container20"
L, W, H = 6.06, 2.44, 2.59
B(A, "Ct_Floor", -L / 2, L / 2, -W / 2, W / 2, 0.0, 0.16, M_BLUE, hull="Box")
B(A, "Ct_Roof", -L / 2, L / 2, -W / 2, W / 2, H - 0.06, H, M_BLUE, bevel=0.005)
for k in range(40):                                              # corrugated long walls
    x0 = -L / 2 + 0.12 + k * (L - 0.24) / 40; x1 = x0 + (L - 0.24) / 40
    out = 0.03 if k % 2 == 0 else 0.0
    for sy in (-1, 1):
        B(A, f"Ct_Rib{sy}_{k}", x0, x1, sy * (W / 2 - 0.035 + out) - 0.0125, sy * (W / 2 - 0.035 + out) + 0.0125, 0.16, H - 0.06, M_BLUE)
for sx in (-1, 1):
    for sy in (-1, 1):
        B(A, f"Ct_Post{sx}{sy}", sx * L / 2 - (0.12 if sx > 0 else 0), sx * L / 2 + (0.0 if sx > 0 else 0.12),
          sy * W / 2 - (0.12 if sy > 0 else 0), sy * W / 2 + (0 if sy > 0 else 0.12), 0.0, H, M_BLUE)
        for z in (0.0, H - 0.12):
            B(A, f"Ct_Corner{sx}{sy}{z:.0f}", sx * L / 2 - (0.17 if sx > 0 else -0.01), sx * L / 2 + (0.01 if sx > 0 else 0.17),
              sy * W / 2 - (0.16 if sy > 0 else -0.01), sy * W / 2 + (0.01 if sy > 0 else 0.16), z, z + 0.12, M_DARKM)
B(A, "Ct_Front", -L / 2 + 0.02, -L / 2 + 0.06, -W / 2 + 0.1, W / 2 - 0.1, 0.16, H - 0.06, M_BLUE, cuts=3)
B(A, "Ct_Doors", L / 2 - 0.06, L / 2 - 0.02, -W / 2 + 0.1, W / 2 - 0.1, 0.16, H - 0.06, M_BLUE, cuts=3)
for k, y in enumerate((-0.85, -0.4, 0.4, 0.85)):                 # door lock bars
    tube(A, f"Ct_Bar{k}", [Vector((L / 2 + 0.01, y, 0.25)), Vector((L / 2 + 0.01, y, H - 0.12))], 0.017, M_GALV, 6)
    B(A, f"Ct_Handle{k}", L / 2 - 0.0, L / 2 + 0.06, y - 0.02, y + 0.12, 1.0, 1.05, M_GALV)
B(A, "Ct_DoorGap", L / 2 - 0.019, L / 2 - 0.015, -0.006, 0.006, 0.16, H - 0.06, M_DARKM)

# ================================================================= stage
for o in C.PARTS:
    if not o.data.polygons[0].use_smooth or o.data.materials[0] in (M_CHAIN,):
        pass
C.finalize(["ChainUV"])
layout = {"SM_Fence_Panel": (0, 0, 0), "SM_Fence_PanelDamaged": (0, 3, 0), "SM_Fence_Post": (4, 0, 0), "SM_FenceGate_8m": (0, 7, 0),
          "SM_StreetLamp": (-4, 0, 0), "SM_StreetLamp_Broken": (-4, 4, 0), "SM_JerseyBarrier": (6, 3, 0), "SM_Dumpster": (6, 0, 0),
          "SM_Container20": (14, 3, 0)}
for name, objs in ASSETS.items():
    for o in objs: o.location = layout[name]; o["ofs"] = layout[name]
    print(name, len(objs), "parts", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "tris")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage_grounds.blend"))
