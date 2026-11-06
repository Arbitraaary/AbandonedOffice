"""Retractable-belt barrier post, belt pulled out and left lying on the floor (Blender 4.2 / bpy).
python3.11 build_barrier.py -> out/stage.blend   (pivot: floor, post centre; metres)
Belt faces carry 'BeltUV' (tiling: 1 U = 0.40 m of belt) and use M_Belt.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, noise, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
BASE_R, POST_R, HEAD_R = 0.175, 0.031, 0.034
H_TOP = 0.98
SLOT_Z = 0.915
BELT_W, BELT_T, TILE = 0.05, 0.0011, 0.40

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
DUST = (0.30, 0.28, 0.25, 1)

# ----------------------------------------------------------------- materials
def painted(name, col, metal_col=(0.5, 0.5, 0.5, 1), chip_amt=1.0, rough=0.45):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 6, 3), col, tuple(min(1, v * 1.5) for v in col[:3]) + (1,))
    chip = g.rng(g.math('ADD', g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.6), chip_amt), g.noise(obj, 35, 10, 0.75)), 0.78, 0.82)
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(30, 30, 300)), 0.77, 0.785)   # vertical-ish scuffs
    scr2 = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(300, 300, 20)), 0.775, 0.79)
    scr = g.math('MAXIMUM', scr, scr2)
    kick = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.3, 0.05), g.rng(g.noise(obj, 9, 6), 0.45, 0.7), True)  # shoe scuffs low
    c = g.mixc(chip, c, metal_col)
    c = g.mixc(g.math('MULTIPLY', scr, 0.6), c, metal_col)
    c = g.mixc(g.math('MULTIPLY', kick, 0.5), c, (0.18, 0.17, 0.16, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 18, 6), 0.3, 0.65), True)
    c = g.mixc(g.math('ADD', g.math('MULTIPLY', dust, 0.85), 0.04, True), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(chip, rough, 0.35); r = g.mixf(scr, r, 0.3); r = g.mixf(kick, r, 0.7); r = g.mixf(dust, r, 0.95)
    g.L(r, b.inputs["Roughness"])
    met = g.math('MAXIMUM', chip, g.math('MULTIPLY', scr, 0.9)); met = g.mixf(dust, met, 0.0)
    g.L(met, b.inputs["Metallic"])
    bump = g.n("ShaderNodeBump", Strength=0.2, Distance=0.0004)
    g.L(g.math('SUBTRACT', g.math('MULTIPLY', g.noise(obj, 500, 2), 0.2), chip), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def plain(name, col, rough, metal, dust_amt=0.8):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    c = g.mixc(g.rng(g.noise(obj, 60, 6), 0.45, 0.8), col, (0.12, 0.11, 0.1, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(obj, 18, 6), 0.3, 0.65), True)
    c = g.mixc(g.math('MULTIPLY', dust, dust_amt), c, DUST)
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(dust, rough, 0.95), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = metal
    return m

def belt_material():
    m, nt, b = mat_new("M_Belt"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="BeltUV")
    def tex(f, nc):
        t = g.n("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(HERE, "tex", f))
        if nc: t.image.colorspace_settings.name = 'Non-Color'
        g.L(uvn.outputs[0], t.inputs[0]); return t
    bc, orm, nm = tex("T_BarrierBelt_BC.png", 0), tex("T_BarrierBelt_ORM.png", 1), tex("T_BarrierBelt_N.png", 1)
    g.L(bc.outputs[0], b.inputs["Base Color"])
    sp = g.n("ShaderNodeSeparateColor"); g.L(orm.outputs[0], sp.inputs[0]); g.L(sp.outputs[1], b.inputs["Roughness"])
    sn = g.n("ShaderNodeSeparateColor"); g.L(nm.outputs[0], sn.inputs[0])
    inv = g.math('SUBTRACT', 1.0, sn.outputs[1])
    cc = g.n("ShaderNodeCombineColor"); g.L(sn.outputs[0], cc.inputs[0]); g.L(inv, cc.inputs[1]); g.L(sn.outputs[2], cc.inputs[2])
    nmp = g.n("ShaderNodeNormalMap"); g.L(cc.outputs[0], nmp.inputs["Color"]); g.L(nmp.outputs[0], b.inputs["Normal"])
    return m

M = {"post": painted("M_Post_Paint", (0.02, 0.02, 0.022, 1), (0.45, 0.45, 0.46, 1), 0.0, 0.58),
     "base": painted("M_Base_Paint", (0.022, 0.022, 0.024, 1), (0.40, 0.40, 0.41, 1), 0.5, 0.5),
     "head": plain("M_Head_Plastic", (0.03, 0.03, 0.032, 1), 0.5, 0.0),
     "chrome": plain("M_Chrome", (0.6, 0.6, 0.6, 1), 0.3, 1.0, 0.5),
     "rubber": plain("M_Rubber", (0.02, 0.02, 0.02, 1), 0.85, 0.0, 0.2),
     "belt": belt_material()}

parts = []
def revolve(name, prof, mat, segs=48, smooth=True):
    bm = bmesh.new(); rings = []
    for j in range(segs):
        th = 2 * math.pi * j / segs
        rings.append([bm.verts.new((r * math.cos(th), r * math.sin(th), z)) for r, z in prof])
    for j in range(segs):
        A, B = rings[j], rings[(j + 1) % segs]
        for i in range(len(prof) - 1):
            bm.faces.new((A[i], B[i], B[i + 1], A[i + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); me.materials.append(M[mat])
    for p in me.polygons: p.use_smooth = smooth
    parts.append(ob); return ob

def box(name, c, size, mat, bevel=0.0, rot=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if rot: bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(c))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); me.materials.append(M[mat])
    if bevel:
        md = ob.modifiers.new("b", 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'
        with bpy.context.temp_override(object=ob, active_object=ob): bpy.ops.object.modifier_apply(modifier="b")
    parts.append(ob); return ob

# ----------------------------------------------------------------- post
revolve("RubberRing", [(0.0005, 0.0), (BASE_R - 0.012, 0.0), (BASE_R - 0.008, 0.004), (BASE_R - 0.012, 0.006), (0.0005, 0.006)], "rubber", 64)
revolve("Base", [(0.0005, 0.006), (BASE_R - 0.004, 0.006), (BASE_R, 0.009), (BASE_R, 0.016), (BASE_R - 0.006, 0.022),
                 (0.12, 0.030), (0.07, 0.038), (0.045, 0.045), (POST_R + 0.006, 0.050), (POST_R + 0.002, 0.056), (0.0005, 0.056)], "base", 64)
# small chips in the base rim
basep = parts[-1]
for v in basep.data.vertices:
    r = math.hypot(v.co.x, v.co.y)
    if r > BASE_R - 0.007:
        th = math.atan2(v.co.y, v.co.x)
        n = noise.noise(Vector((math.cos(th) * 9, math.sin(th) * 9, 0.3)))
        if n > 0.35: v.co.z -= 0.003 * (n - 0.35) / 0.65
revolve("Post", [(POST_R, 0.054), (POST_R, 0.86), (0.0005, 0.86)], "post", 40)
revolve("Head", [(0.0005, 0.86), (HEAD_R, 0.86), (HEAD_R + 0.001, 0.865), (HEAD_R + 0.001, 0.955), (HEAD_R, 0.96), (0.0005, 0.96)], "head", 40)
revolve("Cap", [(0.0005, 0.958), (HEAD_R - 0.002, 0.958), (HEAD_R - 0.004, 0.968), (HEAD_R - 0.012, 0.976), (0.0005, H_TOP)], "chrome", 40)
# belt exit slot (front, +X) and three receiver slots for other belts
box("SlotFrame", (HEAD_R + 0.002, 0, SLOT_Z), (0.006, 0.010, 0.062), "chrome", 0.0015)
box("SlotDark", (HEAD_R + 0.0052, 0, SLOT_Z), (0.002, 0.004, 0.054), "rubber")
for a in (math.pi / 2, math.pi, 3 * math.pi / 2):
    rot = Matrix.Rotation(a, 3, 'Z')
    box(f"Receiver{a:.1f}", rot @ Vector((HEAD_R + 0.001, 0, SLOT_Z)), (0.004, 0.016, 0.07), "chrome", 0.001, rot)
    box(f"ReceiverHole{a:.1f}", rot @ Vector((HEAD_R + 0.0032, 0, SLOT_Z)), (0.001, 0.009, 0.05), "rubber", 0, rot)
# small dent in the post where it was knocked
postob = next(o for o in parts if o.name == "Post")
for v in postob.data.vertices:
    d = (Vector((v.co.x, v.co.y, v.co.z)) - Vector((-0.6 * POST_R, -0.8 * POST_R, 0.42))).length
    v.co.x += 0.0035 * math.exp(-(d / 0.02) ** 2) * 0.6
    v.co.y += 0.0035 * math.exp(-(d / 0.02) ** 2) * 0.8

# ----------------------------------------------------------------- belt path (centre line) and twist
def catmull(pts, n_per):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n_per):
            t = k / n_per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1]); return out
fz = BELT_T / 2 + 0.0004
ctrl = [Vector(p) for p in [
    (HEAD_R + 0.004, 0.0, SLOT_Z), (0.07, -0.004, SLOT_Z - 0.005), (0.13, -0.02, SLOT_Z - 0.07),
    (0.17, -0.04, 0.62), (0.19, -0.06, 0.30), (0.21, -0.08, 0.06), (0.25, -0.10, fz + 0.004),
    (0.34, -0.14, fz), (0.48, -0.15, fz), (0.62, -0.10, fz), (0.74, -0.02, fz), (0.86, 0.02, fz), (0.97, -0.01, fz)]]
path = catmull(ctrl, 14)
# keep everything above the floor and the base
for p in path:
    p.z = max(p.z, fz)
lengths = [0.0]
for a, b in zip(path, path[1:]): lengths.append(lengths[-1] + (b - a).length)
L = lengths[-1]
up = Vector((0, 0, 1))
ground_s = next(s for p, s in zip(path, lengths) if p.z <= fz + 1e-4)
top, bot = [], []
bm = bmesh.new(); uv = bm.loops.layers.uv.new("BeltUV")
frames = []
tangents = []
for i in range(len(path)):
    tangents.append((path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized())
w = Vector((0, 0, 1)); w = (w - tangents[0] * w.dot(tangents[0])).normalized()     # leaves the slot edge-on
blend_from = ground_s - 0.35
for i, (p, s_) in enumerate(zip(path, lengths)):
    t = tangents[i]
    if i:                                                          # parallel transport (no flips)
        q = tangents[i - 1].rotation_difference(t)
        w = (q @ w); w = (w - t * w.dot(t)).normalized()
    wf = up.cross(t)
    if wf.length > 1e-4 and s_ > blend_from:                       # ease into lying flat on the floor
        wf.normalize()
        if wf.dot(w) < 0: wf = -wf
        k = min(1.0, (s_ - blend_from) / (ground_s - blend_from + 1e-6))
        k = k * k * (3 - 2 * k)
        w = (w * (1 - k) + wf * k); w = (w - t * w.dot(t)).normalized()
    n = t.cross(w).normalized()
    if s_ >= ground_s and n.z < 0:                                 # printed side up on the floor
        n = -n
    frames.append((p, w, n, s_))
for p, w, n, s in frames:
    hw = BELT_W / 2
    if s > ground_s:                                                # small ripples where it lies on the floor
        p = p + Vector((0, 0, 0.0025 * max(0.0, noise.noise(Vector((s * 6, 0, 0))))))
    top.append((bm.verts.new(p - w * hw + n * BELT_T / 2), bm.verts.new(p + w * hw + n * BELT_T / 2)))
    bot.append((bm.verts.new(p - w * hw - n * BELT_T / 2), bm.verts.new(p + w * hw - n * BELT_T / 2)))
def quad(vs, uvs):
    try:
        f = bm.faces.new(vs)
    except ValueError:
        return
    for l, q in zip(f.loops, uvs): l[uv].uv = q
for i in range(len(frames) - 1):
    u0, u1 = frames[i][3] / TILE, frames[i + 1][3] / TILE
    a0, b0 = top[i]; a1, b1 = top[i + 1]
    quad([a0, a1, b1, b0], [(u0, 0), (u1, 0), (u1, 1), (u0, 1)])
    c0, d0 = bot[i]; c1, d1 = bot[i + 1]
    quad([c0, d0, d1, c1], [(-u0, 0), (-u0, 1), (-u1, 1), (-u1, 0)])       # back side reads correctly
    quad([c0, c1, a1, a0], [(u0, 0.0), (u1, 0.0), (u1, 0.03), (u0, 0.03)])
    quad([b0, b1, d1, d0], [(u0, 0.97), (u1, 0.97), (u1, 1.0), (u0, 1.0)])
me = bpy.data.meshes.new("Belt"); bm.to_mesh(me); bm.free()
belt = bpy.data.objects.new("Belt", me); sc.collection.objects.link(belt); me.materials.append(M["belt"])
for p in me.polygons: p.use_smooth = True
parts.append(belt)
# metal end clip lying flat at the end of the belt
pe, we, ne, _ = frames[-1]
te = (frames[-1][0] - frames[-2][0]).normalized()
rot = Matrix((te, we, ne)).transposed()
box("ClipPlate", pe + te * 0.022 + ne * 0.0035, (0.04, 0.056, 0.006), "chrome", 0.0015, rot)
box("ClipHook", pe + te * 0.048 + ne * 0.0035, (0.014, 0.03, 0.006), "chrome", 0.002, rot)
print("belt length", round(L, 3), "ground at", round(ground_s, 3))

for ob in parts:
    lay = ob.data.uv_layers.get("BeltUV") or ob.data.uv_layers.new(name="BeltUV")
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
print("parts", len(parts), "tris", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage.blend"))
