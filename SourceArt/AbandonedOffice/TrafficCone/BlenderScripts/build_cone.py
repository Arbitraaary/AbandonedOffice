"""Damaged orange/white traffic cone (70 cm) for the abandoned office. Blender 4.2 / bpy.
python3.11 build_cone.py  ->  out/stage.blend      (pivot: floor centre, metres)
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, noise, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
BASE_W, BASE_H = 0.36, 0.032
Z0, ZT = BASE_H, 0.70
R0, RT = 0.128, 0.024
WALL = 0.0045
BANDS = [(0.50, 0.625), (0.33, 0.42)]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ----------------------------------------------------------------- materials
DUST = (0.30, 0.28, 0.25, 1)
def cone_material():
    m, nt, b = mat_new("M_Cone_Plastic"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); geo = g.n("ShaderNodeNewGeometry")
    obj = tc.outputs["Object"]
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    z = sp.outputs[2]
    # orange PVC, sun-faded unevenly
    fade = g.noise(obj, 2.5, 4)
    orange = g.mixc(fade, (0.90, 0.20, 0.012, 1), (0.80, 0.22, 0.03, 1))
    # reflective bands with ragged, peeling edges
    edge_n = g.math('MULTIPLY', g.math('SUBTRACT', g.noise(obj, 35, 6, 0.7), 0.5), 0.018)
    zz = g.math('ADD', z, edge_n)
    band = None
    for lo, hi in BANDS:
        bm_ = g.math('MULTIPLY', g.math('GREATER_THAN', zz, lo), g.math('LESS_THAN', zz, hi))
        band = bm_ if band is None else g.math('MAXIMUM', band, bm_)
    peel = g.rng(g.noise(obj, 9, 8, 0.7), 0.64, 0.66)               # patches of sheeting torn off
    band = g.math('MULTIPLY', band, g.math('SUBTRACT', 1.0, peel), True)
    resid = g.math('MULTIPLY', peel, g.math('GREATER_THAN', g.math('ADD', z, edge_n), 0.33))
    white = g.mixc(g.noise(obj, 18, 5), (0.80, 0.80, 0.78, 1), (0.68, 0.68, 0.66, 1))
    c = g.mixc(band, orange, white)
    # scratches (light), tyre mark (dark smear on one side), dirt rising from the floor
    scr = g.rng(g.noise(obj, 5, 3, 0.5, mapping_scale=(260, 260, 8)), 0.74, 0.77)
    c = g.mixc(g.math('MULTIPLY', scr, 0.5), c, (0.75, 0.55, 0.45, 1))
    side = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); g.L(obj, side.inputs[0])
    side.inputs[1].default_value = (-0.6, -0.8, 0.0)
    tyre = g.math('MULTIPLY', g.rng(side.outputs["Value"], 0.03, 0.1),
                  g.rng(g.noise(obj, 4, 6, 0.6, mapping_scale=(3, 3, 0.8)), 0.42, 0.62), True)
    tyre = g.math('MULTIPLY', tyre, g.rng(z, 0.55, 0.15), True)
    low = g.math('MULTIPLY', g.rng(z, 0.22, 0.03), g.rng(g.noise(obj, 12, 8), 0.3, 0.7), True)
    c = g.mixc(g.math('MULTIPLY', low, 0.45), c, (0.22, 0.17, 0.12, 1))
    pt = g.rng(geo.outputs["Pointiness"], 0.52, 0.6)                # grime in cracks/creases
    c = g.mixc(g.math('MULTIPLY', pt, 0.5), c, (0.10, 0.08, 0.06, 1))
    up = g.rng(sn.outputs[2], 0.3, 0.8)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 20, 6), 0.35, 0.65), True)
    c = g.mixc(g.math('ADD', g.math('MULTIPLY', dust, 0.8), 0.05, True), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(band, 0.55, 0.38)
    r = g.mixf(resid, r, 0.8)
    r = g.mixf(low, r, 0.9); r = g.mixf(dust, r, 0.95)
    g.L(r, b.inputs["Roughness"]); b.inputs["Metallic"].default_value = 0.0
    h = g.math('ADD', g.math('MULTIPLY', band, 0.4), g.math('MULTIPLY', g.noise(obj, 600, 2), 0.1))
    h = g.math('SUBTRACT', h, g.math('MULTIPLY', scr, 0.3))
    bump = g.n("ShaderNodeBump", Strength=0.25, Distance=0.0006); g.L(h, bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def rubber_material():
    m, nt, b = mat_new("M_Cone_Rubber"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    geo = g.n("ShaderNodeNewGeometry"); sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    c = g.mixc(g.noise(obj, 60, 6), (0.014, 0.014, 0.014, 1), (0.03, 0.029, 0.028, 1))
    grit = g.rng(g.noise(obj, 220, 3), 0.66, 0.72)                  # recycled rubber specks
    c = g.mixc(g.math('MULTIPLY', grit, 0.5), c, (0.18, 0.17, 0.16, 1))
    pt = g.rng(geo.outputs["Pointiness"], 0.5, 0.6)                # scuffed, greyed edges
    c = g.mixc(g.math('MULTIPLY', pt, 0.35), c, (0.12, 0.115, 0.11, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 15, 6), 0.3, 0.7), True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.25), c, DUST)
    g.L(c, b.inputs["Base Color"])
    g.L(g.mixf(dust, g.mixf(pt, 0.75, 0.9), 0.95), b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.3, Distance=0.001); g.L(g.noise(obj, 300, 4), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

M_CONE, M_RUB = cone_material(), rubber_material()

# ----------------------------------------------------------------- cone shell
SEG, NZ = 72, 48
def cone_r(z):
    return R0 + (RT - R0) * (z - Z0) / (ZT - Z0)
DENT = (-0.45, 0.34, 0.0, 0.06)            # theta, z, depth, sigma
TEAR_T = 4.2
bm = bmesh.new()
grid = {}
for j in range(SEG):
    th = 2 * math.pi * j / SEG
    chew = 0.0
    for i in range(NZ + 1):
        t = i / NZ
        ztop = ZT - chew
        z = Z0 + 0.012 + (ztop - Z0 - 0.012) * t
        r = cone_r(z)
        if i == 0: r += 0.008                       # flared skirt into the base collar
        dth = math.atan2(math.sin(th - DENT[0]), math.cos(th - DENT[0]))
        r -= DENT[2] * math.exp(-((dth * r) ** 2 + (z - DENT[1]) ** 2) / (2 * DENT[3] ** 2))
        lean = 0.0
        grid[j, i] = bm.verts.new((r * math.cos(th) + lean, r * math.sin(th) + lean * 0.3, z))
faces = {}
for j in range(SEG):
    for i in range(NZ):
        a, b_ = grid[j, i], grid[(j + 1) % SEG, i]
        faces[j, i] = bm.faces.new((a, b_, grid[(j + 1) % SEG, i + 1], grid[j, i + 1]))
# tear: a jagged split running up from the skirt
kill = []
for (j, i), f in faces.items():
    c = f.calc_center_median()
    th = math.atan2(c.y, c.x)
    dth = math.atan2(math.sin(th - TEAR_T), math.cos(th - TEAR_T))
    zr = (c.z - Z0) / 0.2
    if 0 <= zr <= 1:
        w = 0.30 * (1 - zr) ** 1.3 + 0.03
        if abs(dth - 0.04 * noise.noise(c * 45)) < w * (0.75 + 0.5 * abs(noise.noise(c * 120))):
            kill.append(f)
# (no hole any more - the split stays closed, only the flap bulges out below)
me = bpy.data.meshes.new("Cone"); bm.to_mesh(me); bm.free()
cone = bpy.data.objects.new("Cone", me); sc.collection.objects.link(cone)
for p in me.polygons: p.use_smooth = True
s = cone.modifiers.new("solid", 'SOLIDIFY'); s.thickness = WALL; s.offset = -1.0; s.use_even_offset = True
with bpy.context.temp_override(object=cone, active_object=cone):
    bpy.ops.object.modifier_apply(modifier="solid")
me.materials.append(M_CONE)
# the torn flap is pushed outward a bit
for v in me.vertices:
    th = math.atan2(v.co.y, v.co.x)
    dth = math.atan2(math.sin(th - TEAR_T), math.cos(th - TEAR_T))
    if 0 < dth < 0.35 and v.co.z < Z0 + 0.2:
        k = (1 - (v.co.z - Z0) / 0.2) * (1 - dth / 0.35)
        v.co += Vector((math.cos(th), math.sin(th), 0)) * 0.007 * k

# collar ring where the cone meets the base
def ring(name, r_in, r_out, z0, z1, segs=56, mat=M_CONE):
    bm = bmesh.new()
    prof = [(r_in, z0), (r_out, z0), (r_out, z1 - 0.003), (r_out - 0.003, z1), (r_in, z1)]
    rings = []
    for j in range(segs):
        th = 2 * math.pi * j / segs
        rings.append([bm.verts.new((r * math.cos(th), r * math.sin(th), z)) for r, z in prof])
    for j in range(segs):
        A, B = rings[j], rings[(j + 1) % segs]
        for i in range(len(prof)):
            k = (i + 1) % len(prof)
            bm.faces.new((A[i], B[i], B[k], A[k]))
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); sc.collection.objects.link(o); m.materials.append(mat)
    for p in m.polygons: p.use_smooth = True
    return o
collar = ring("Collar", R0 - 0.004, R0 + 0.016, Z0 - 0.002, Z0 + 0.016)

# ----------------------------------------------------------------- base (black rubber, one corner broken off)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((v.co.x * BASE_W, v.co.y * BASE_W, (v.co.z + 0.5) * BASE_H))
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
me = bpy.data.meshes.new("Base"); bm.to_mesh(me); bm.free()
base = bpy.data.objects.new("Base", me); sc.collection.objects.link(base)
bev = base.modifiers.new("bev", 'BEVEL'); bev.width = 0.025; bev.segments = 4; bev.limit_method = 'ANGLE'
bev.affect = 'EDGES'
with bpy.context.temp_override(object=base, active_object=base):
    bpy.ops.object.modifier_apply(modifier="bev")
# broken corner: cut with a plane, then roughen the fracture
bm = bmesh.new(); bm.from_mesh(me)
pn = Vector((1, -1, 0.15)).normalized(); pc = Vector((0.115, -0.115, 0))
res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5, plane_co=pc, plane_no=pn, clear_outer=True)
cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
new_faces = [f for f in bm.faces if abs(f.normal.dot(pn)) > 0.9]
bmesh.ops.triangulate(bm, faces=new_faces)
for v in bm.verts:
    if abs((v.co - pc).dot(pn)) < 0.002:
        v.co += pn * (-0.0015 * (noise.noise(v.co * 60) + 0.6))
bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = False
me.materials.append(M_RUB)
# small dent/gouge on the top of the base
for v in me.vertices:
    d = (Vector((v.co.x, v.co.y)) - Vector((-0.12, 0.1))).length
    if v.co.z > BASE_H - 0.002: v.co.z -= 0.006 * math.exp(-(d / 0.025) ** 2)

parts = [cone, collar, base]
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
print("tris", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage.blend"))
