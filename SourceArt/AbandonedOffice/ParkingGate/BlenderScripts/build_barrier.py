"""Broken boom barrier: yellow housing on a concrete pad, arm snapped in the middle, the outer half lying on the ground.
python3.11 build_barrier.py -> out/stage_barrier.blend    (pivot: ground under the housing centre, arm along +X; metres)
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(4)

def arm_material():
    m, nt, b = mat_new("M_BarrierArm"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="ArmUV"); sep = g.n("ShaderNodeSeparateXYZ"); g.L(uvn.outputs[0], sep.inputs[0])
    u = sep.outputs[0]
    stripe = g.math('GREATER_THAN', g.math('FRACT', g.math('MULTIPLY', u, 1.0)), 0.5)       # 0.5 m red / white bands
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    red = g.mixc(g.noise(obj, 6, 4), (0.42, 0.04, 0.03, 1), (0.30, 0.05, 0.04, 1))           # faded red film
    white = g.mixc(g.noise(obj, 6, 4), (0.70, 0.70, 0.68, 1), (0.58, 0.58, 0.56, 1))
    c = g.mixc(stripe, white, red)
    peel = g.rng(g.noise(obj, 14, 8, 0.7), 0.66, 0.69)
    c = g.mixc(peel, c, (0.55, 0.56, 0.57, 1))                                               # bare aluminium
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(10, 200, 200)), 0.76, 0.78)
    c = g.mixc(g.math('MULTIPLY', scr, 0.6), c, (0.5, 0.5, 0.5, 1))
    pt = g.rng(geo.outputs["Pointiness"], 0.52, 0.62)                                         # torn metal edge darker
    c = g.mixc(g.math('MULTIPLY', pt, 0.6), c, (0.2, 0.2, 0.2, 1))
    dirt = g.rng(g.noise(obj, 10, 6), 0.45, 0.75)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.35), c, (0.14, 0.12, 0.1, 1))
    g.L(c, b.inputs["Base Color"])
    g.L(g.mixf(peel, g.mixf(dirt, 0.4, 0.75), 0.35), b.inputs["Roughness"])
    g.L(g.mixf(peel, 0.0, 0.85), b.inputs["Metallic"])
    return m

M_Y = C.painted("M_Barrier_Yellow", (0.62, 0.42, 0.02, 1), chip_amt=0.9, rough=0.45, rust=0.7, streak_from=1.0)
M_ARM = arm_material()
M_CON = C.concrete()
M_BLK = C.painted("M_Barrier_Black", (0.025, 0.025, 0.025, 1), primer=(0.3, 0.3, 0.3, 1), chip_amt=0.05, rust=0.35)
M_YT = C.painted("M_Barrier_YellowTrim", (0.62, 0.42, 0.02, 1), chip_amt=0.05, rough=0.45, rust=0.35)
M_LAMP = C.plain("M_Lamp_Amber", (0.55, 0.22, 0.02, 1), 0.3, 0.0, 0.5)
M_MET = C.plain("M_Metal", (0.45, 0.45, 0.45, 1), 0.4, 1.0)

PAD = 0.10
HX, HY, HZ = 0.34, 0.30, 1.0
HUB_Z = PAD + HZ - 0.14
C.box("Pad", -0.32, 0.32, -0.28, 0.28, -0.03, PAD, M_CON, bevel=0.01, cuts=3)
C.box("Housing", -HX / 2, HX / 2, -HY / 2, HY / 2, PAD, PAD + HZ, M_Y, bevel=0.02, seg=3, cuts=4)
C.box("Cap", -HX / 2 - 0.015, HX / 2 + 0.015, -HY / 2 - 0.015, HY / 2 + 0.015, PAD + HZ, PAD + HZ + 0.03, M_YT, bevel=0.008)
C.box("Plinth", -HX / 2 - 0.01, HX / 2 + 0.01, -HY / 2 - 0.01, HY / 2 + 0.01, PAD, PAD + 0.06, M_BLK, bevel=0.005)
# service door on the -Y side with lock + vent slots
C.box("Door", -0.12, 0.12, -HY / 2 - 0.006, -HY / 2 + 0.001, PAD + 0.14, PAD + 0.8, M_YT, bevel=0.004)
C.cyl("Lock", (0.08, -HY / 2 - 0.012, PAD + 0.62), 0.012, 0.012, M_MET, axis='Y', segs=16)
for k in range(6):
    C.box(f"Vent{k}", -0.08, 0.08, -HY / 2 - 0.008, -HY / 2 - 0.004, PAD + 0.2 + k * 0.03, PAD + 0.212 + k * 0.03, M_BLK)
# amber warning lamp, cracked open on one side
C.cyl("LampBase", (0, 0, PAD + HZ + 0.045), 0.06, 0.03, M_BLK, segs=24)
lamp = C.dome("Lamp", (0, 0, PAD + HZ + 0.06), 0.055, M_LAMP)
bm = bmesh.new(); bm.from_mesh(lamp.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().x > 0.02 and f.calc_center_median().z > PAD + HZ + 0.09], context='FACES')
bm.to_mesh(lamp.data); bm.free()
# hub on the +Y side, counterweight arm to -X
C.cyl("Hub", (0, HY / 2 + 0.04, HUB_Z), 0.075, 0.08, M_BLK, axis='Y', segs=28)
C.box("Counter", -0.55, -0.05, HY / 2 + 0.015, HY / 2 + 0.065, HUB_Z - 0.04, HUB_Z + 0.04, M_BLK, bevel=0.006)
C.box("Weight", -0.62, -0.46, HY / 2 + 0.0, HY / 2 + 0.08, HUB_Z - 0.09, HUB_Z + 0.05, M_BLK, bevel=0.01)

# ----------------------------------------------------------------- arm (rectangular profile), snapped
AW, AH = 0.05, 0.09
def arm_segment(name, length, start_jag, end_jag, steps):
    """profile along local +X from 0..length; jagged/torn ends where requested"""
    bm = bmesh.new(); rings = []
    prof = [(-AW / 2, -AH / 2), (AW / 2, -AH / 2), (AW / 2, AH / 2), (-AW / 2, AH / 2)]
    for k in range(steps + 1):
        x = length * k / steps
        ring = []
        for j, (py, pz) in enumerate(prof):
            xx = x
            if k == steps and end_jag:  xx += 0.05 * noise.noise(Vector((j * 1.7, 3.1, 0.0))) + rnd.uniform(-0.03, 0.03)
            if k == 0 and start_jag:    xx += 0.05 * noise.noise(Vector((j * 1.7, 7.3, 0.0))) + rnd.uniform(-0.03, 0.03)
            if (k == steps and end_jag) or (k == 0 and start_jag):   # torn tube pinched shut a bit
                py *= 0.75; pz *= 0.85
            ring.append(bm.verts.new((xx, py, pz)))
        rings.append(ring)
    for a, b2 in zip(rings, rings[1:]):
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b2[(j + 1) % 4], b2[j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me
L1, L2 = 1.95, 2.0
me = arm_segment("ArmStub", L1, False, True, 24)
stub = C.link("ArmStub", me, M_ARM)
C.set_uv(stub, "ArmUV", lambda co, p: (co.x / 1.0, 0.0))
droop = math.radians(4)                                               # the stub sags where it cracked
for v in stub.data.vertices:
    x = v.co.x
    v.co.z -= max(0.0, x - 0.4) * math.tan(droop) * min(1.0, (x - 0.4) / 0.8) if x > 0.4 else 0.0
for v in stub.data.vertices:
    v.co += Vector((0.0, HY / 2 + 0.06, HUB_Z))
piece = C.link("ArmPiece", arm_segment("ArmPiece", L2, True, False, 24), M_ARM)
C.set_uv(piece, "ArmUV", lambda co, p: ((co.x + L1) / 1.0, 0.0))
yaw = math.radians(-11)
for v in piece.data.vertices:                                         # lying on its side on the ground
    co = Matrix.Rotation(math.pi / 2, 3, 'X') @ v.co
    co = Matrix.Rotation(yaw, 3, 'Z') @ co
    v.co = co + Vector((L1 + 0.25, HY / 2 + 0.35, AW / 2))
C.cyl("ArmEndCap", (L1 + 0.25 + L2 * math.cos(yaw) + 0.005, HY / 2 + 0.35 + L2 * math.sin(yaw), AW / 2), 0.03, 0.02, M_BLK, axis='X', segs=12)

for o in C.PARTS:
    for p in o.data.polygons: p.use_smooth = False
C.finalize(["ArmUV"])
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in C.PARTS)
print("barrier parts", len(C.PARTS), "tris", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage_barrier.blend"))
