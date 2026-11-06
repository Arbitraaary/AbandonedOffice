"""Parking kit for the office exterior.
python3.11 build_parking.py -> out/stage_parking.blend (baked kit) and out/stage_asphalt.blend (tiling slab)
  SM_ParkingLine       5.0 x 0.12 m worn paint stripe (4 mm), no collision
  SM_Curb              2.0 m concrete curb, 15 cm above ground (pivot: ground level, centre)
  SM_WheelStop         1.8 m concrete parking block
  SM_WheelStop_Broken  same, cracked in two, one half shoved aside
  SM_AsphaltTile_8m    8 x 8 m slab, top at z=0, 35 cm thick, tiling UV (4 m texture repeat) -> MI_Asphalt
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(14)

def paint():
    m, nt, b = mat_new("M_LinePaint"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    keep = g.rng(g.math('ADD', g.noise(obj, 3, 4), g.math('MULTIPLY', g.noise(obj, 40, 5), 0.35)), 0.52, 0.6)   # worn-off patches
    paintc = g.mixc(g.noise(obj, 20, 3), (0.60, 0.58, 0.50, 1), (0.68, 0.66, 0.58, 1))
    asph = g.mixc(g.noise(obj, 60, 4), (0.20, 0.20, 0.19, 1), (0.30, 0.295, 0.28, 1))
    c = g.mixc(keep, asph, paintc)
    dirt = g.rng(g.noise(obj, 9, 5), 0.5, 0.8)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.45), c, (0.22, 0.2, 0.16, 1))
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(keep, 0.9, 0.6), b.inputs["Roughness"])
    return m

def concrete(name):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 10, 7, 0.65), (0.33, 0.32, 0.30, 1), (0.47, 0.46, 0.43, 1))
    pores = g.rng(g.noise(obj, 220, 2), 0.66, 0.72)
    c = g.mixc(g.math('MULTIPLY', pores, 0.6), c, (0.16, 0.15, 0.14, 1))
    edge = g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.52, 0.6), 0.6)
    c = g.mixc(edge, c, (0.55, 0.54, 0.5, 1))
    low = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.06, -0.05), g.rng(g.noise(obj, 6, 4), 0.35, 0.65), True)   # damp/dirty foot
    c = g.mixc(g.math('MULTIPLY', low, 0.7), c, (0.15, 0.14, 0.11, 1))
    moss = g.math('MULTIPLY', g.rng(g.noise(obj, 7, 5), 0.6, 0.72), 0.7)
    c = g.mixc(moss, c, (0.14, 0.18, 0.08, 1))
    tyre = g.math('MULTIPLY', g.rng(g.noise(obj, 4, 3, 0.5, mapping_scale=(1, 12, 1)), 0.62, 0.7), 0.5)   # rubber marks
    c = g.mixc(tyre, c, (0.06, 0.06, 0.06, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump = g.n("ShaderNodeBump", Strength=0.5, Distance=0.002)
    g.L(g.math('SUBTRACT', g.noise(obj, 90, 5), pores), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

M_PAINT = paint(); M_CON = concrete("M_CurbConcrete"); M_STOP = concrete("M_WheelStopConcrete")
M_REBAR = C.plain("M_Rebar", (0.25, 0.12, 0.05, 1), 0.7, 0.6, 0.4)
M_YEL = C.plain("M_StopPaint", (0.55, 0.42, 0.06, 1), 0.7, 0.0, 0.5)

ASSETS = {}
def part(asset, ob, hull=None):
    ob["asset"] = asset
    if hull: ob["hull"] = hull
    ASSETS.setdefault(asset, []).append(ob); return ob
def chip(ob, amt, freq=14.0, seed=0.0, zmin=-1.0):
    for v in ob.data.vertices:
        if v.co.z > zmin:
            n = noise.noise(v.co * freq + Vector((seed, 0, 0)))
            v.co += Vector((noise.noise(v.co * freq + Vector((seed + 3, 0, 0))), noise.noise(v.co * freq + Vector((seed + 7, 0, 0))), n)) * amt

# ---- line
L1 = part("SM_ParkingLine", C.box("Line", -2.5, 2.5, -0.06, 0.06, 0.0, 0.004, M_PAINT, cuts=0))
bm = bmesh.new(); bm.from_mesh(L1.data)
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 1], cuts=24)
bm.to_mesh(L1.data); bm.free()
for v in L1.data.vertices:                                     # ragged sprayed edges
    if abs(v.co.y) > 0.05: v.co.y += 0.006 * noise.noise(Vector((v.co.x * 9, v.co.y * 20, 0)))
# ---- curb: chamfered profile, extruded 2 m, chipped
prof = [(-0.075, -0.15), (0.075, -0.15), (0.075, 0.12), (0.05, 0.15), (-0.05, 0.15), (-0.075, 0.12)]
bm = bmesh.new(); rings = []
for k in range(9):
    x = -1.0 + 2.0 * k / 8
    rings.append([bm.verts.new((x, y, z)) for y, z in prof])
for a, b2 in zip(rings, rings[1:]):
    for j in range(len(prof)):
        bm.faces.new((a[j], a[(j + 1) % len(prof)], b2[(j + 1) % len(prof)], b2[j]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("Curb"); bm.to_mesh(me); bm.free()
cu = part("SM_Curb", C.link("Curb", me, M_CON), hull="Curb")
for v in cu.data.vertices:
    v.co.x = max(-0.998, min(0.998, v.co.x))                   # 4 mm joint gap
chip(cu, 0.006, 9, 1.0, zmin=0.0)
for v in cu.data.vertices:                                     # one corner broken off
    d = (v.co - Vector((0.95, -0.075, 0.15))).length
    if d < 0.12: v.co += Vector((-0.4, 0.6, -1)).normalized() * 0.05 * (1 - d / 0.12)
# ---- wheel stop: trapezoid block with two pin holes
def stop_block(asset, name, x0, x1, crack_end=None):
    prof = [(-0.1, 0.0), (0.1, 0.0), (0.1, 0.03), (0.06, 0.12), (-0.06, 0.12), (-0.1, 0.03)]
    bm = bmesh.new(); rings = []
    n = 10
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        rings.append([bm.verts.new((x, y, z)) for y, z in prof])
    for a, b2 in zip(rings, rings[1:]):
        for j in range(len(prof)):
            bm.faces.new((a[j], a[(j + 1) % len(prof)], b2[(j + 1) % len(prof)], b2[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = part(asset, C.link(name, me, M_STOP), hull=name)
    chip(ob, 0.005, 10, rnd.random() * 9, zmin=0.01)
    if crack_end is not None:                                  # jagged broken face
        for v in ob.data.vertices:
            if abs(v.co.x - crack_end) < 1e-4: v.co.x += 0.03 * noise.noise(Vector((v.co.y * 20, v.co.z * 20, 0.5)))
    return ob
for asset in ("SM_WheelStop",):
    stop_block(asset, "Stop", -0.9, 0.9)
    for sx in (-1, 1):
        part(asset, C.cyl(f"Hole{sx}", (sx * 0.55, 0, 0.1205), 0.016, 0.001, M_REBAR, segs=10))
    part(asset, C.box("StopStripe", -0.3, 0.3, -0.061, -0.06, 0.04, 0.1, M_YEL))
A2 = "SM_WheelStop_Broken"
a = stop_block(A2, "StopA", -0.9, 0.05, crack_end=0.05)
b = stop_block(A2, "StopB", 0.05, 0.9, crack_end=0.05)
for v in b.data.vertices:
    v.co = Matrix.Rotation(math.radians(14), 3, 'Z') @ (v.co - Vector((0.05, 0, 0))) + Vector((0.12, 0.09, 0))
for k in range(3):                                             # rebar sticking out of the break
    p0 = Vector((0.04, -0.03 + 0.03 * k, 0.05)); p1 = p0 + Vector((0.09, 0.02 * (k - 1), 0.01 * k))
    part(A2, C.cyl(f"Bar{k}", tuple((p0 + p1) / 2), 0.004, (p1 - p0).length, M_REBAR, axis='X', segs=6))
part(A2, C.cyl("HoleA", (-0.55, 0, 0.1205), 0.016, 0.001, M_REBAR, segs=10))

for o in C.PARTS:
    for p in o.data.polygons: p.use_smooth = False
layout = {"SM_ParkingLine": (0, 0, 0), "SM_Curb": (0, 1.0, 0), "SM_WheelStop": (0, 2.0, 0), "SM_WheelStop_Broken": (0, 3.0, 0)}
for name, objs in ASSETS.items():
    for o in objs: o.location = layout[name]; o["ofs"] = layout[name]
    print(name, sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "tris")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage_parking.blend"))

# ================================================================= asphalt slab (separate file, tiling material, no bake)
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts: v.co = Vector((v.co.x * 8, v.co.y * 8, (v.co.z - 0.5) * 0.35))
me = bpy.data.meshes.new("SM_AsphaltTile_8m"); bm.to_mesh(me); bm.free()
uv = me.uv_layers.new(name="BakeUV")
for p in me.polygons:
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        if abs(p.normal.z) > 0.5: uv.data[li].uv = (co.x / 4 + 1, co.y / 4 + 1)
        elif abs(p.normal.x) > 0.5: uv.data[li].uv = (co.y / 4 + 1, co.z / 4)
        else: uv.data[li].uv = (co.x / 4 + 1, co.z / 4)
me.materials.append(bpy.data.materials.new("M_Asphalt"))
ob = bpy.data.objects.new("SM_AsphaltTile_8m", me); bpy.context.scene.collection.objects.link(ob)
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts: v.co = Vector((v.co.x * 8, v.co.y * 8, (v.co.z - 0.5) * 0.35))
um = bpy.data.meshes.new("ucx"); bm.to_mesh(um); bm.free()
u = bpy.data.objects.new("UCX_SM_AsphaltTile_8m_00", um); bpy.context.scene.collection.objects.link(u)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage_asphalt.blend"))
