"""Security guard for lab 5 - built on the UE4 mannequin (same skeleton -> all soldier animations work).
blender -b -P build_guard.py -> ../_work/stage.blend   (then bake_guard.py, then verify_guard.py)
The mannequin body is kept only where skin shows (head, neck, hands); everything else is replaced by clothing shells made
from the body surface itself (offset outwards, thickened) - they carry the body's skin weights, so they bend exactly like it
and nothing pokes through. Rigid gear (cap, glasses, nose, moustache, holster, radio, buckle) is bound 100 % to one bone.
Front = -Y (Unreal +Y). Body mesh units are cm (object scale 0.01) like the FBX.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)                          # SourceArt/AbandonedOffice/SecurityGuard
WORK = os.path.join(ROOT, "_work")                     # intermediate files (stage.blend, check renders)
from nodes import mat_new, G

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "Mannequin", "SK_Mannequin_Enemy.fbx"), automatic_bone_orientation=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = next(o for o in bpy.data.objects if o.type == 'MESH')
empty = arm.parent
if empty is not None:                                  # drop the FBX null above the armature (it would become a bone)
    mw = arm.matrix_world.copy(); arm.parent = None; arm.matrix_world = mw
    bpy.data.objects.remove(empty)
W2L = body.matrix_world.inverted()                       # world (m) -> body local (cm)
GI = {g.index: g.name for g in body.vertex_groups}
TEX = os.path.join(HERE, "tex")

# ---------------------------------------------------------------- materials (procedural, baked later)
def simple(name, col, rough, metal=0.0, noise=0.08, scale=60.0, bump=0.15):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    c = g.mixc(g.noise(tc.outputs["Object"], scale * 0.01, 4), col,
               tuple(max(0, x * (1 - noise * 2)) for x in col[:3]) + (1,))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if bump:
        bn = g.n("ShaderNodeBump", Strength=bump, Distance=0.002)
        g.L(g.noise(tc.outputs["Object"], scale * 0.06, 6), bn.inputs["Height"]); g.L(bn.outputs[0], b.inputs["Normal"])
    return m


def fabric(name, col, rough=0.85, weave=0.25):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 0.5, 4), col, tuple(x * 0.8 for x in col[:3]) + (1,))
    dirt = g.rng(g.noise(obj, 0.08, 3), 0.55, 0.75)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.35), c, (0.12, 0.11, 0.09, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    wv = g.n("ShaderNodeTexWave", wave_type='BANDS', Scale=2.2, Distortion=1.0)
    g.L(obj, wv.inputs[0])
    bn = g.n("ShaderNodeBump", Strength=weave, Distance=0.002)
    g.L(g.math('ADD', wv.outputs["Fac"], g.noise(obj, 3.0, 4)), bn.inputs["Height"]); g.L(bn.outputs[0], b.inputs["Normal"])
    return m


def with_text(m, img_path, boxes, ink):
    """stamp text (white-on-black image) inside axis boxes in metres: (x0, x1, z0, z1, side) side = +1 back, -1 front"""
    nt = m.node_tree; g = G(nt); b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    base = b.inputs["Base Color"].links[0].from_socket
    tc = g.n("ShaderNodeTexCoord"); sep = g.n("ShaderNodeSeparateXYZ"); g.L(tc.outputs["Object"], sep.inputs[0])
    x = g.math('MULTIPLY', sep.outputs[0], 0.01); y = g.math('MULTIPLY', sep.outputs[1], 0.01); z = g.math('MULTIPLY', sep.outputs[2], 0.01)
    im_src = bpy.data.images.load(img_path); im_src.colorspace_settings.name = 'Non-Color'
    for (x0, x1, z0, z1, side) in boxes:
        u = g.math('DIVIDE', g.math('SUBTRACT', x, x0), x1 - x0)
        if side > 0:                                     # seen from behind, x runs right-to-left
            u = g.math('SUBTRACT', 1.0, u)
        v = g.math('DIVIDE', g.math('SUBTRACT', z, z0), z1 - z0)
        cmb = g.n("ShaderNodeCombineXYZ"); g.L(u, cmb.inputs[0]); g.L(v, cmb.inputs[1])
        it = g.n("ShaderNodeTexImage"); it.image = im_src; it.extension = 'CLIP'; g.L(cmb.outputs[0], it.inputs[0])
        side_ok = g.math('GREATER_THAN', g.math('MULTIPLY', y, side), 0.03)
        mask = g.math('MULTIPLY', it.outputs[0], side_ok)
        base = g.mixc(mask, base, ink)
    g.L(base, b.inputs["Base Color"])
    return m


M = {
    "skin": simple("M_Skin", (0.62, 0.43, 0.33, 1), 0.55, noise=0.06, scale=40, bump=0.05),
    "shirt": fabric("M_Shirt", (0.42, 0.52, 0.66, 1), 0.8, 0.15),
    "trousers": fabric("M_Trousers", (0.035, 0.045, 0.085, 1), 0.85, 0.2),
    "vest": fabric("M_Vest", (0.018, 0.02, 0.024, 1), 0.7, 0.35),
    "boots": simple("M_Boots", (0.02, 0.018, 0.016, 1), 0.35, noise=0.1, scale=80, bump=0.1),
    "leather": simple("M_Belt", (0.025, 0.022, 0.02, 1), 0.45, noise=0.1),
    "cap": fabric("M_Cap", (0.03, 0.035, 0.07, 1), 0.75, 0.2),
    "metal": simple("M_Metal", (0.75, 0.72, 0.62, 1), 0.3, 1.0, noise=0.04, bump=0.0),
    "gold": simple("M_Badge", (0.85, 0.62, 0.22, 1), 0.3, 1.0, noise=0.05, bump=0.0),
    "glass": simple("M_Glasses", (0.01, 0.012, 0.015, 1), 0.08, 0.6, noise=0.02, bump=0.0),
    "plastic": simple("M_Plastic", (0.035, 0.035, 0.035, 1), 0.5, noise=0.05),
    "hair": simple("M_Hair", (0.05, 0.035, 0.025, 1), 0.7, noise=0.15, scale=300, bump=0.3),
    "reflect": simple("M_Reflective", (0.62, 0.64, 0.6, 1), 0.3, 0.3, noise=0.05, bump=0.0),
}
with_text(M["vest"], os.path.join(TEX, "text_security.png"),
          [(-0.15, 0.15, 1.235, 1.330, +1), (0.035, 0.150, 1.355, 1.390, -1)], (0.92, 0.92, 0.88, 1))


# ---------------------------------------------------------------- body regions from skin weights
def wsum(v, names):
    return sum(g.weight for g in v.groups if GI[g.group] in names)

ARMS = {"clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r", "upperarm_twist_01_l", "upperarm_twist_01_r",
        "lowerarm_l", "lowerarm_r", "lowerarm_twist_01_l", "lowerarm_twist_01_r"}
SPINE = {"spine_01", "spine_02", "spine_03"}
HANDS = {n for n in GI.values() if any(k in n for k in ("hand", "index", "middle", "ring", "pinky", "thumb"))}
LEGS = {"pelvis", "thigh_l", "thigh_r", "thigh_twist_01_l", "thigh_twist_01_r", "calf_l", "calf_r", "calf_twist_01_l", "calf_twist_01_r"}
FEET = {"foot_l", "foot_r", "ball_l", "ball_r"}


def wz(v):
    return (body.matrix_world @ v.co).z


def region_of(v):
    if wsum(v, HANDS) > 0.35: return "hand"
    if wsum(v, {"head"}) > 0.5 or (wsum(v, {"neck_01"}) > 0.4 and wz(v) > 1.585): return "head"
    if wsum(v, FEET) > 0.4 or wz(v) < 0.20: return "boot"
    if wsum(v, LEGS) > 0.5 and wz(v) < 1.0: return "legs"
    if wz(v) < 0.985 and wsum(v, ARMS) < 0.3: return "legs"
    return "shirt"


REG = [region_of(v) for v in body.data.vertices]


def shell(name, keep, offset_cm, thick_cm, mat, decimate=1.0, smooth=0, zcut=None, edge_smooth=0, extra_cm=0.0, crop=None, rect=None):
    """copy of the body faces whose verts all satisfy keep(index), pushed out along the normal and thickened"""
    me = body.data.copy(); ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    ob.parent = arm; ob.matrix_world = body.matrix_world.copy()
    for vg in body.vertex_groups:
        ob.vertex_groups.new(name=vg.name)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if not all(keep(v.index) for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.02)      # weld UV-seam splits, else the offset tears them
    if zcut:                                                         # straight hem: cut by horizontal planes (weights interpolate)
        no = (W2L.to_3x3() @ Vector((0, 0, 1))).normalized()
        for z, outer in ((zcut[0], True), (zcut[1], False)):
            r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-4,
                                       plane_co=W2L @ Vector((0, 0, z)), plane_no=no, clear_inner=outer, clear_outer=not outer)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.normal_update()
    if smooth:                                                       # cloth hides the muscles: relax the surface,
        for v in bm.verts:                                           # but keep the open edges (wrist, waist...) in place
            v.co += v.normal * offset_cm * 0.6
        inner = [v for v in bm.verts if not v.is_boundary]
        for _ in range(smooth):
            bmesh.ops.smooth_vert(bm, verts=inner, factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.normal_update()
        offset_cm *= 0.4
    for v in bm.verts:
        v.co += v.normal * offset_cm
    for _ in range(edge_smooth):                                     # even out the stair-stepped open edges (armholes, neck)
        bnd = [v for v in bm.verts if v.is_boundary]
        new = {}
        for v in bnd:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2: new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items(): v.co = c
    if extra_cm:                                                     # e.g. a print sitting on top of the vest surface
        bm.normal_update()
        for v in bm.verts: v.co += v.normal * extra_cm
    if crop:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not crop(body.matrix_world @ f.calc_center_median())], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    if rect:                                                         # clean rectangular label: cut by 4 world planes
        x0, x1, z0, z1 = rect
        for co, n, keep_pos in (((x0, 0, 0), (1, 0, 0), True), ((x1, 0, 0), (1, 0, 0), False),
                                ((0, 0, z0), (0, 0, 1), True), ((0, 0, z1), (0, 0, 1), False)):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-4, plane_co=W2L @ Vector(co),
                                   plane_no=(W2L.to_3x3() @ Vector(n)).normalized(), clear_inner=keep_pos, clear_outer=not keep_pos)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free()
    me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.material_index = 0; p.use_smooth = True
    if decimate < 1.0:
        d = ob.modifiers.new("dec", 'DECIMATE'); d.ratio = decimate
    if thick_cm > 0:
        s = ob.modifiers.new("sol", 'SOLIDIFY'); s.thickness = thick_cm; s.offset = 1.0; s.use_rim = True
        s.use_even_offset = False; s.use_quality_normals = True
    bpy.context.view_layer.objects.active = ob
    for mname in [m.name for m in ob.modifiers]:
        bpy.ops.object.modifier_apply(modifier=mname)
    am = ob.modifiers.new("Armature", 'ARMATURE'); am.object = arm
    return ob


def zrange(z0, z1):
    return lambda i: z0 <= wz(body.data.vertices[i]) <= z1


PARTS = []
# shirt: torso + arms down to the wrist, collar up to the neck
NECK = {"neck_01", "head"}
PARTS.append(shell("Shirt", lambda i: (REG[i] == "shirt" or (REG[i] == "legs" and wz(body.data.vertices[i]) > 0.95))
                   and wsum(body.data.vertices[i], NECK) < 0.25,          # neckline at the base of the neck, no collar
                   0.9, 0.35, M["shirt"], smooth=12, edge_smooth=6))
# trousers: hips to the boot tops
PARTS.append(shell("Trousers", lambda i: REG[i] == "legs" or (REG[i] == "boot" and wz(body.data.vertices[i]) > 0.17),
                   1.4, 0.35, M["trousers"], smooth=18))
# boots: feet + ankles, chunky
PARTS.append(shell("Boots", lambda i: REG[i] == "boot", 1.3, 0.8, M["boots"], decimate=0.7))
# vest: torso only (no arms), waist to chest
PARTS.append(shell("Vest", lambda i: (REG[i] in ("shirt", "legs") and wsum(body.data.vertices[i], ARMS) < 0.25
                                      and 0.95 <= wz(body.data.vertices[i]) <= 1.50), 2.2, 1.2, M["vest"], smooth=8,
                   zcut=(0.985, 1.47), edge_smooth=10))
# SECURITY prints: thin patches just on top of the vest, each gets its own big clean UV island when baked (bake_guard.py)
VEST_KEEP = PARTS[-1]
M["vest_text"] = M["vest"].copy(); M["vest_text"].name = "M_VestText"
for nm, (x0, x1, z0, z1, side) in (("VestTextBack", (-0.15, 0.15, 1.235, 1.330, +1)), ("VestTextFront", (0.035, 0.150, 1.355, 1.390, -1))):
    PARTS.append(shell(nm, lambda i: (REG[i] in ("shirt", "legs") and wsum(body.data.vertices[i], ARMS) < 0.25
                                      and 0.95 <= wz(body.data.vertices[i]) <= 1.50), 2.2, 0.0, M["vest_text"], smooth=8,
                       zcut=(0.985, 1.47), extra_cm=1.3, rect=(x0 - 0.012, x1 + 0.012, z0 - 0.008, z1 + 0.008),
                       crop=lambda p, x0=x0, x1=x1, z0=z0, z1=z1, side=side: (x0 - 0.02 <= p.x <= x1 + 0.02 and z0 - 0.02 <= p.z <= z1 + 0.02
                                                                                and p.y * side > 0.03)))
# belt
PARTS.append(shell("Belt", lambda i: 0.93 <= wz(body.data.vertices[i]) <= 1.03 and REG[i] in ("legs", "shirt")
                   and wsum(body.data.vertices[i], ARMS) < 0.2, 2.7, 1.0, M["leather"], zcut=(0.952, 1.0)))

# body: keep only skin (head, neck, hands) - everything else is under clothes
bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(REG[v.index] not in ("head", "hand")
                                                      and wsum(body.data.vertices[v.index], NECK) < 0.12 for v in f.verts)], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(body.data); bm.free()
body.data.materials.clear(); body.data.materials.append(M["skin"])
for p in body.data.polygons: p.material_index = 0
body.name = "Skin"; PARTS.append(body)


# ---------------------------------------------------------------- rigid gear (one bone each), built in metres then -> cm
def rigid(name, bm_build, bone, mat, smooth=True):
    bm = bmesh.new(); bm_build(bm)
    for v in bm.verts:
        v.co = W2L @ v.co
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    ob.parent = arm; ob.matrix_world = body.matrix_world.copy()
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    am = ob.modifiers.new("Armature", 'ARMATURE'); am.object = arm
    PARTS.append(ob); return ob


def box(bm, c, size, rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M_ = Matrix.Translation(c) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((size[0], size[1], size[2], 1))
    bmesh.ops.transform(bm, matrix=M_, verts=r["verts"])
    return r


def sphere(bm, c, radii, segs=16, rings=10, zcut=None):
    r = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1)), verts=r["verts"])
    if zcut is not None:
        bmesh.ops.delete(bm, geom=[v for v in r["verts"] if v.co.z < zcut - 1e-4], context='VERTS')
    return r


def cyl(bm, c, rad, depth, axis='Z', segs=14, rad2=None):
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=rad, radius2=rad if rad2 is None else rad2, depth=depth)
    rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ rot, verts=r["verts"])
    return r


# cap: crown + band + peak + badge
HC = Vector((0.0, 0.016, 1.745))


def cap_crown(bm):
    sphere(bm, HC + Vector((0, 0, -0.005)), (0.100, 0.122, 0.092), segs=24, rings=14, zcut=HC.z - 0.012)
    cyl(bm, HC + Vector((0, 0, -0.022)), 0.1, 0.03, segs=24)
    for v in bm.verts:                                     # band follows the head's oval
        v.co.y = HC.y + (v.co.y - HC.y) * (1.21 if abs(v.co.z - (HC.z - 0.022)) < 0.02 else 1.0)


def cap_peak(bm):
    r = bmesh.ops.create_circle(bm, cap_ends=True, segments=28, radius=1.0)
    for v in r["verts"]:
        if v.co.y > 0.25: v.co.y = 0.25
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((0.095, 0.09, 1, 1)), verts=r["verts"])
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    bmesh.ops.translate(bm, vec=(0, 0, -0.007), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    for v in bm.verts:                                           # slight downward curve of the bill
        v.co.z -= 0.02 * (v.co.x / 0.095) ** 2
    tilt = Matrix.Rotation(math.radians(3), 4, 'X')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, HC.y - 0.128, HC.z - 0.019)) @ tilt, verts=bm.verts[:])


rigid("CapCrown", cap_crown, "head", M["cap"])
rigid("CapPeak", cap_peak, "head", M["cap"])
rigid("CapBadge", lambda bm: box(bm, Vector((0, HC.y - 0.117, HC.z + 0.008)), (0.026, 0.006, 0.03)), "head", M["gold"])


# sunglasses (aviators), nose, ears
HEADV = [p for p in (body.matrix_world @ v.co for v in body.data.vertices) if p.z > 1.55 and abs(p.x) < 0.12]


def face_y(x, z, r=0.012):
    """front surface of the face (the character looks to -Y) near (x, z)"""
    ys = [p.y for p in HEADV if abs(p.x - x) < r and abs(p.z - z) < r]
    return min(ys) if ys else -0.09


EYE_Z, NOSE_Z, MOU_Z = 1.693, 1.660, 1.632
print("face y: eyes %.3f nose %.3f mouth %.3f" % (face_y(0.034, EYE_Z), face_y(0, NOSE_Z), face_y(0, MOU_Z)))


def glasses(bm):
    for sx in (-1, 1):
        sphere(bm, Vector((sx * 0.036, face_y(sx * 0.036, EYE_Z) - 0.009, EYE_Z)), (0.031, 0.007, 0.021), segs=16, rings=8)
    box(bm, Vector((0, face_y(0, EYE_Z + 0.008) - 0.012, EYE_Z + 0.009)), (0.024, 0.004, 0.005))
    for sx in (-1, 1):
        box(bm, Vector((sx * 0.086, -0.045, EYE_Z + 0.006)), (0.005, 0.11, 0.005))


def nose(bm):
    y = face_y(0, NOSE_Z + 0.012)
    r = sphere(bm, Vector((0, y - 0.006, NOSE_Z + 0.006)), (0.016, 0.02, 0.03), segs=12, rings=10)
    for v in r["verts"]:                                      # wedge: narrow bridge, wider tip at the bottom
        k = (NOSE_Z + 0.006 - v.co.z) / 0.03
        v.co.x *= 0.75 + 0.35 * max(k, 0)
        v.co.y -= 0.008 * max(k, 0)


def moustache(bm):
    y = face_y(0, MOU_Z + 0.004)
    r = sphere(bm, Vector((0, y - 0.006, MOU_Z + 0.004)), (0.042, 0.012, 0.011), segs=16, rings=8)
    for v in r["verts"]:                                      # ends droop and wrap round the mouth
        t = v.co.x / 0.042
        v.co.z -= 0.010 * t * t
        v.co.y += 0.014 * t * t


rigid("Glasses", glasses, "head", M["glass"])
rigid("Moustache", moustache, "head", M["hair"])
rigid("Nose", nose, "head", M["skin"])
for sx, nm in ((1, "EarL"), (-1, "EarR")):
    rigid(nm, lambda bm, sx=sx: sphere(bm, Vector((sx * 0.089, 0.012, 1.70)), (0.009, 0.018, 0.028), segs=10, rings=8), "head", M["skin"])

# gear on the belt: holster + pistol grip (right hip), radio (left hip), pouches, buckle
rigid("Holster", lambda bm: (box(bm, Vector((-0.178, 0.0, 0.915)), (0.035, 0.07, 0.13)),
                             box(bm, Vector((-0.178, -0.008, 1.0)), (0.03, 0.035, 0.06))), "pelvis", M["leather"])
rigid("Radio", lambda bm: (box(bm, Vector((0.165, -0.06, 0.94)), (0.03, 0.055, 0.1)),
                           cyl(bm, Vector((0.165, -0.075, 1.02)), 0.005, 0.07)), "pelvis", M["plastic"])
rigid("Pouches", lambda bm: [box(bm, Vector((x, -0.15, 0.975)), (0.05, 0.03, 0.055)) for x in (-0.085, 0.085)], "pelvis", M["leather"])
rigid("Buckle", lambda bm: box(bm, Vector((0, -0.15, 0.98)), (0.06, 0.012, 0.04)), "pelvis", M["metal"])
# epaulettes, shoulder radio mic
rigid("Mic", lambda bm: (box(bm, Vector((0.095, -0.155, 1.43)), (0.035, 0.02, 0.05)),), "spine_03", M["plastic"])

for o in PARTS:
    for p in o.data.polygons:
        p.use_smooth = True
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in PARTS)
print("parts", len(PARTS), "tris", tris)
os.makedirs(WORK, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "stage.blend"))
