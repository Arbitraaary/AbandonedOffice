"""Bent parking sign: galvanised pole kinked halfway, upper part + sign leaning 25 deg back. Blender 4.2 / bpy.
python3.11 build_sign.py -> out/stage.blend   (pivot: ground, pole centre; sign faces -Y; metres)
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
POLE_R = 0.030
COLLAR_H = 0.08
BEND_Z = 1.25                 # kink in the middle of the visible pole
LEAN = math.radians(25)       # upper part leans back (+Y)
BEND_R = 0.09
UPPER = 1.38
SIGN = 0.60
SIGN_AT = 0.98                # sign centre, metres along the upper part from the kink
DUST = (0.30, 0.28, 0.25, 1)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ----------------------------------------------------------------- materials
def galv_material():
    m, nt, b = mat_new("M_Pole_Galv"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    vor = g.n("ShaderNodeTexVoronoi", Scale=90.0); g.L(obj, vor.inputs[0])
    spangle = vor.outputs["Color"]
    sep = g.n("ShaderNodeSeparateColor"); g.L(spangle, sep.inputs[0])
    c = g.mixc(sep.outputs[0], (0.36, 0.37, 0.37, 1), (0.48, 0.49, 0.49, 1))       # zinc spangle
    oxide = g.rng(g.noise(obj, 8, 6), 0.55, 0.7)
    c = g.mixc(g.math('MULTIPLY', oxide, 0.7), c, (0.62, 0.62, 0.60, 1))          # white zinc oxide
    bend = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', sp.outputs[2], BEND_Z + 0.03)), 0.18, 0.02),
                  g.rng(g.noise(obj, 30, 8, 0.7), 0.35, 0.6), True)                 # cracked coating at the kink
    low = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.35, 0.05), g.rng(g.noise(obj, 20, 6), 0.4, 0.7), True)
    streak = g.math('MULTIPLY', g.rng(g.noise(obj, 4, 5, 0.6, mapping_scale=(40, 40, 1.5)), 0.6, 0.72),
                    g.rng(sp.outputs[2], BEND_Z + 0.05, BEND_Z - 0.5), True)          # rust running down from the kink
    rust = g.math('MAXIMUM', g.math('MAXIMUM', bend, g.math('MULTIPLY', low, 0.6)), streak)
    rc = g.mixc(g.noise(obj, 60, 5), (0.16, 0.06, 0.02, 1), (0.32, 0.14, 0.05, 1))
    c = g.mixc(rust, c, rc)
    dirt = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.5, 0.0), 0.6)
    c = g.mixc(dirt, c, (0.12, 0.10, 0.08, 1))
    g.L(c, b.inputs["Base Color"])
    g.L(g.mixf(rust, g.mixf(oxide, 0.4, 0.75), 0.85), b.inputs["Roughness"])
    g.L(g.mixf(rust, g.mixf(dirt, 0.9, 0.2), 0.0), b.inputs["Metallic"])
    bump = g.n("ShaderNodeBump", Strength=0.3, Distance=0.0006)
    g.L(g.math('ADD', g.math('MULTIPLY', rust, 0.6), g.math('MULTIPLY', g.noise(obj, 400, 3), 0.2)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def face_material():
    m, nt, b = mat_new("M_Sign_Face"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="SignUV")
    img = g.n("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(HERE, "tex", "sign_face.png"))
    img.extension = 'EXTEND'
    g.L(uvn.outputs[0], img.inputs[0])
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    dust = g.rng(g.noise(obj, 12, 6), 0.5, 0.8)
    c = g.mixc(g.math('MULTIPLY', dust, 0.25), img.outputs[0], DUST)
    g.L(c, b.inputs["Base Color"])
    sepc = g.n("ShaderNodeSeparateColor"); g.L(img.outputs[0], sepc.inputs[0])
    bare = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', sepc.outputs[0], sepc.outputs[2])), 0.05, 0.0),
                  g.rng(sepc.outputs[1], 0.5, 0.6), True)                          # grey = bare aluminium
    g.L(g.mixf(bare, 0.42, 0.35), b.inputs["Roughness"])
    g.L(g.mixf(bare, 0.0, 0.8), b.inputs["Metallic"])
    return m

def plain(name, col, rough, metal, rust=0.0):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 20, 5), col, tuple(v * 0.8 for v in col[:3]) + (1,))
    r = rough
    if rust:
        rm = g.rng(g.noise(obj, 25, 8, 0.7), 0.62 - rust * 0.1, 0.68 - rust * 0.1)
        c = g.mixc(rm, c, (0.25, 0.1, 0.035, 1)); r = g.mixf(rm, rough, 0.85)
        g.L(g.mixf(rm, metal, 0.0), b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = metal
    dirt = g.rng(g.noise(obj, 40, 5), 0.5, 0.8)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.35), c, (0.12, 0.11, 0.09, 1))
    g.L(c, b.inputs["Base Color"]); g.L(r, b.inputs["Roughness"])
    return m

def concrete_material():
    m, nt, b = mat_new("M_Concrete"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    c = g.mixc(g.noise(obj, 15, 8, 0.65), (0.20, 0.195, 0.185, 1), (0.33, 0.32, 0.30, 1))
    vor = g.n("ShaderNodeTexVoronoi", Scale=14.0, feature='DISTANCE_TO_EDGE'); g.L(obj, vor.inputs[0])
    crack = g.math('MULTIPLY', g.rng(vor.outputs["Distance"], 0.012, 0.0), g.rng(g.noise(obj, 6, 3), 0.45, 0.6), True)
    c = g.mixc(crack, c, (0.04, 0.04, 0.035, 1))
    pt = g.rng(geo.outputs["Pointiness"], 0.5, 0.6)
    c = g.mixc(g.math('MULTIPLY', pt, 0.5), c, (0.40, 0.39, 0.37, 1))
    moss = g.math('MULTIPLY', g.rng(g.noise(obj, 30, 6), 0.62, 0.72), 0.6)
    c = g.mixc(moss, c, (0.07, 0.09, 0.04, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump = g.n("ShaderNodeBump", Strength=0.5, Distance=0.002)
    g.L(g.math('SUBTRACT', g.noise(obj, 150, 5), crack), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

M = {"galv": galv_material(), "face": face_material(), "back": plain("M_Sign_Back", (0.42, 0.43, 0.43, 1), 0.45, 0.85, rust=0.6),
     "clamp": plain("M_Clamp", (0.38, 0.38, 0.38, 1), 0.4, 1.0, rust=1.0), "concrete": concrete_material()}
parts = []
def link(name, me, mat):
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); me.materials.append(M[mat])
    parts.append(ob); return ob

# ----------------------------------------------------------------- pole path
lean_dir = Vector((0, math.sin(LEAN), math.cos(LEAN)))
path, tangents = [], []
z = 0.0
while z < BEND_Z:                                                  # lower straight part
    path.append(Vector((0, 0, z))); tangents.append(Vector((0, 0, 1))); z += 0.08
centre = Vector((0, BEND_R, BEND_Z))                               # bend arc about the X axis
for k in range(13):
    a = LEAN * k / 12
    path.append(centre + Vector((0, -BEND_R * math.cos(a), BEND_R * math.sin(a))))
    tangents.append(Vector((0, math.sin(a), math.cos(a))))
kink_end = path[-1].copy()
s = 0.08
while s <= UPPER + 1e-6:                                           # upper straight part
    path.append(kink_end + lean_dir * s); tangents.append(lean_dir.copy()); s += 0.08
top = path[-1]

# ----------------------------------------------------------------- crumpled tube
SEG = 24
bm = bmesh.new(); rings = []
kink_mid = centre + Vector((0, -BEND_R * math.cos(LEAN / 2), BEND_R * math.sin(LEAN / 2)))
for p, t in zip(path, tangents):
    side = Vector((1, 0, 0)); up = t.cross(side).normalized()      # 'up' points to the inner (+Y) side of the bend
    dist = (p - kink_mid).length
    k = math.exp(-(dist / 0.07) ** 2)
    ring = []
    for j in range(SEG):
        th = 2 * math.pi * j / SEG
        cx, cy = math.cos(th), math.sin(th)
        r = POLE_R
        # flattened cross-section + buckled wrinkles on the compressed (inner) side
        sx = 1.0 + 0.10 * k
        sy = 1.0 - 0.22 * k
        inner = max(0.0, cy)                                       # compressed side of the bend
        r *= 1.0 + k * inner * 0.28 * math.sin(dist * 170 + th * 3) - 0.08 * k * inner
        ring.append(bm.verts.new(p + side * (cx * r * sx) + up * (cy * r * sy)))
    rings.append(ring)
for a, b2 in zip(rings, rings[1:]):
    for j in range(SEG):
        bm.faces.new((a[j], a[(j + 1) % SEG], b2[(j + 1) % SEG], b2[j]))
bm.faces.new(rings[0][::-1])
# domed top cap
capc = bm.verts.new(top + lean_dir * 0.012)
for j in range(SEG):
    bm.faces.new((rings[-1][j], rings[-1][(j + 1) % SEG], capc))
me = bpy.data.meshes.new("Pole"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
pole = link("Pole", me, "galv")

# ----------------------------------------------------------------- sign plate (in the upper part's frame)
frame_rot = Matrix.Rotation(-LEAN, 4, 'X')                        # local Z -> lean_dir, local -Y -> sign normal
sign_c = kink_end + lean_dir * SIGN_AT
plate_off = POLE_R + 0.018
def to_world(v):
    return sign_c + (frame_rot @ Vector(v).to_4d()).to_3d() - (frame_rot @ Vector((0, 0, 0, 1))).to_3d()
bm = bmesh.new(); uv = bm.loops.layers.uv.new("SignUV")
h = SIGN / 2; t = 0.002; rim = 0.015
fy, by_ = -plate_off - t, -plate_off                             # front / back face planes (local y)
F = [bm.verts.new(to_world((x, fy, zz))) for x, zz in ((-h, -h), (h, -h), (h, h), (-h, h))]
B = [bm.verts.new(to_world((x, by_, zz))) for x, zz in ((-h, -h), (h, -h), (h, h), (-h, h))]
ff = bm.faces.new((F[0], F[1], F[2], F[3]))                      # facing -Y
for l in ff.loops:
    lv = (frame_rot.inverted() @ (l.vert.co - sign_c).to_4d()).to_3d() if False else None
uvmap = {F[0]: (0, 0), F[1]: (1, 0), F[2]: (1, 1), F[3]: (0, 1)}
for l in ff.loops: l[uv].uv = uvmap[l.vert]
bm.faces.new((B[0], B[3], B[2], B[1]))
for i in range(4):
    a, c2 = i, (i + 1) % 4
    bm.faces.new((F[a], F[c2], B[c2], B[a]))
# folded stiffening rim on the back
Ri = [bm.verts.new(to_world((x * (h - 0.004) / h, by_ + rim, zz * (h - 0.004) / h))) for x, zz in ((-h, -h), (h, -h), (h, h), (-h, h))]
for i in range(4):
    a, c2 = i, (i + 1) % 4
    bm.faces.new((B[a], B[c2], Ri[c2], Ri[a]))
me = bpy.data.meshes.new("Plate"); bm.to_mesh(me); bm.free()
plate = link("Plate", me, "back")
me.materials.append(M["face"])
nrm_front = (frame_rot @ Vector((0, -1, 0, 0))).to_3d()
big = [p for p in me.polygons if p.area > 0.3]
front = min(big, key=lambda p: (p.center - sign_c).dot(-nrm_front) * -1 if False else -(p.center - sign_c).dot(nrm_front))
front.material_index = 1
if front.normal.dot(nrm_front) < 0: front.flip()
# face UVs straight from the plate's local coordinates
inv = frame_rot.inverted()
lay = me.uv_layers.get("SignUV") or me.uv_layers.new(name="SignUV")
for p in me.polygons:
    for li in p.loop_indices:
        if p.material_index == 1:
            lv = (inv @ (me.vertices[me.loops[li].vertex_index].co - sign_c).to_4d()).to_3d()
            lay.data[li].uv = (lv.x / SIGN + 0.5, lv.z / SIGN + 0.5)
        else:
            lay.data[li].uv = (0.0, 0.0)
# clamps + bolts at the two holes (12 % and 88 % of the sign height)
for frac in (0.12, 0.88):
    zl = -h + frac * SIGN
    cpos = kink_end + lean_dir * (SIGN_AT + zl)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=POLE_R + 0.004, radius2=POLE_R + 0.004, depth=0.03)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=frame_rot.to_3x3())
    bmesh.ops.translate(bm, verts=bm.verts, vec=cpos)
    me = bpy.data.meshes.new("Clamp"); bm.to_mesh(me); bm.free()
    o = link(f"Clamp{frac}", me, "clamp")
    md = o.modifiers.new("s", 'SOLIDIFY'); md.thickness = 0.003
    with bpy.context.temp_override(object=o, active_object=o): bpy.ops.object.modifier_apply(modifier="s")
    bm = bmesh.new()                                               # bracket from clamp to plate
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 0.04, v.co.y * (plate_off - POLE_R), v.co.z * 0.03))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((0, -(POLE_R + plate_off) / 2, 0)))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=frame_rot.to_3x3())
    bmesh.ops.translate(bm, verts=bm.verts, vec=cpos)
    me = bpy.data.meshes.new("Bracket"); bm.to_mesh(me); bm.free()
    link(f"Bracket{frac}", me, "clamp")
    bm = bmesh.new()                                               # bolt head on the face
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.011, radius2=0.011, depth=0.006)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((0, fy - 0.003, zl)))
    for v in bm.verts: v.co = to_world(v.co)
    me = bpy.data.meshes.new("Bolt"); bm.to_mesh(me); bm.free()
    link(f"Bolt{frac}", me, "clamp")

# ----------------------------------------------------------------- concrete footing, cracked, chunk missing
bm = bmesh.new(); prof = [(POLE_R + 0.002, COLLAR_H), (0.13, COLLAR_H), (0.15, COLLAR_H - 0.02), (0.155, -0.02),
                          (POLE_R + 0.002, -0.02)]
SEGC = 32; rr = []
for j in range(SEGC):
    th = 2 * math.pi * j / SEGC
    row = []
    for r, zz in prof:
        n = noise.noise(Vector((math.cos(th) * 3, math.sin(th) * 3, zz * 10)))
        rj = r + (0.008 * n if r > 0.1 else 0)
        zj = zz + (0.006 * n if zz > 0.03 else 0)
        dth = math.atan2(math.sin(th - 2.2), math.cos(th - 2.2))
        if r > 0.1 and zz > 0.03: zj -= 0.035 * math.exp(-(dth / 0.35) ** 2)   # broken-off chunk
        row.append(bm.verts.new((rj * math.cos(th), rj * math.sin(th), zj)))
    rr.append(row)
for j in range(SEGC):
    A, Bc = rr[j], rr[(j + 1) % SEGC]
    for i in range(len(prof) - 1):
        bm.faces.new((A[i], Bc[i], Bc[i + 1], A[i + 1]))
    bm.faces.new((A[-1], Bc[-1], Bc[0], A[0]))
me = bpy.data.meshes.new("Footing"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = False
link("Footing", me, "concrete")

for ob in parts:
    if "SignUV" not in ob.data.uv_layers: ob.data.uv_layers.new(name="SignUV")
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
print("parts", len(parts), "tris", tris, "top", tuple(round(c, 3) for c in top))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage.blend"))
