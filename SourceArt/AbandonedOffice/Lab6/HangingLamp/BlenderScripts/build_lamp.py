"""Lab 6: hanging fluorescent office lamp. One of its two suspension cables snapped, so the fixture hangs on the other
one and swings; the broken cable dangles from the lower end, one tube is broken.
Skeletal mesh (root - cable_01..03 - lamp - dangle_01..02, light) + 4 s looping swing animation.
python3.11 build_lamp.py -> out/SK_HangingLamp.fbx, out/Textures/T_HangingLamp_{BC,ORM,N}.png, out/HangingLamp.blend"""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); TEX = os.path.join(OUT, "Textures")
random.seed(3)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------------- palette atlas
PAL = [("white", (0.70, 0.69, 0.64), 0.55, 0.0), ("dirty", (0.47, 0.45, 0.39), 0.75, 0.0),
       ("alu", (0.62, 0.63, 0.64), 0.35, 1.0), ("black", (0.035, 0.035, 0.04), 0.55, 0.0),
       ("copper", (0.80, 0.42, 0.22), 0.3, 1.0), ("burnt", (0.06, 0.05, 0.045), 0.85, 0.0),
       ("rust", (0.36, 0.20, 0.10), 0.8, 0.2), ("glass", (0.92, 0.94, 0.95), 0.15, 0.0)]
N = len(PAL); W, H = 256, 32
bc = np.zeros((H, W, 3)); orm = np.zeros((H, W, 3))
for i, (_, col, r, m) in enumerate(PAL):
    x0, x1 = i * W // N, (i + 1) * W // N
    noise = 1.0 + 0.10 * (np.random.RandomState(i).rand(H, x1 - x0, 1) - 0.5)
    bc[:, x0:x1] = np.array(col) * noise
    orm[:, x0:x1] = (1.0, r, m)
Image.fromarray((np.clip(bc, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, "T_HangingLamp_BC.png"))
Image.fromarray((np.clip(orm, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, "T_HangingLamp_ORM.png"))
Image.fromarray(np.full((8, 8, 3), (128, 128, 255), np.uint8)).save(os.path.join(TEX, "T_HangingLamp_N.png"))
PIDX = {p[0]: i for i, p in enumerate(PAL)}


def make_mat(name, emissive=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    if emissive:
        b.inputs["Base Color"].default_value = (0.95, 0.97, 1.0, 1)
        b.inputs["Emission Color"].default_value = (0.85, 0.92, 1.0, 1); b.inputs["Emission Strength"].default_value = 6.0
    else:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(TEX, "T_HangingLamp_BC.png"))
        t.interpolation = 'Closest'; nt.links.new(t.outputs[0], b.inputs["Base Color"])
        to = nt.nodes.new("ShaderNodeTexImage"); to.image = bpy.data.images.load(os.path.join(TEX, "T_HangingLamp_ORM.png"))
        to.image.colorspace_settings.name = 'Non-Color'; to.interpolation = 'Closest'
        sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(to.outputs[0], sp.inputs[0])
        nt.links.new(sp.outputs[1], b.inputs["Roughness"]); nt.links.new(sp.outputs[2], b.inputs["Metallic"])
    return m


MAT = make_mat("M_HangingLamp"); MAT_TUBE = make_mat("M_HangingLamp_Tube", True)
parts = []   # (object, bone or weight function)


def new_obj(name, bm, mat):
    me = bpy.data.meshes.new(name); bm.normal_update(); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); me.materials.append(mat)
    return ob


def patch_uv(bm, colour):
    """non-degenerate UVs inside the colour's palette patch (planar from the vertex position)"""
    uvl = bm.loops.layers.uv.verify(); c = PIDX[colour]
    for f in bm.faces:
        n = f.normal
        ax = (1, 2) if abs(n.x) > max(abs(n.y), abs(n.z)) else ((0, 2) if abs(n.y) > abs(n.z) else (0, 1))
        for l in f.loops:
            co = l.vert.co
            l[uvl].uv = ((c + 0.15 + 0.7 * ((co[ax[0]] * 3.1) % 1.0)) / N, (co[ax[1]] * 3.1) % 1.0)


def box(name, center, size, colour, bone, mat=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    bm.normal_update(); patch_uv(bm, colour)
    ob = new_obj(name, bm, mat or MAT); parts.append((ob, bone)); return ob


def tube(name, path, r, colour, bone, segs=8, mat=None, burnt_tail=0.0, caps=True):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); rings = []; prev = None; along = 0.0
    total = sum((path[i + 1] - path[i]).length for i in range(len(path) - 1))
    for i, p in enumerate(path):
        d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        nrm = (prev - d * prev.dot(d)).normalized() if prev else d.orthogonal().normalized(); prev = nrm
        b = d.cross(nrm)
        if i: along += (path[i] - path[i - 1]).length
        rings.append(([bm.verts.new(p + (nrm * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r)
                       for k in range(segs)], along))
    for (ra, la), (rb, lb) in zip(rings, rings[1:]):
        c = PIDX["burnt"] if burnt_tail and total - la < burnt_tail else PIDX[colour]
        for k in range(segs):
            f = bm.faces.new((ra[k], ra[(k + 1) % segs], rb[(k + 1) % segs], rb[k]))
            u0 = (c + 0.15 + 0.7 * k / segs) / N; u1 = (c + 0.15 + 0.7 * (k + 1) / segs) / N
            for l, (u, v) in zip(f.loops, ((u0, la), (u1, la), (u1, lb), (u0, lb))):
                l[uvl].uv = (u, v * 4.0)
    if caps:
        for ring, _ in (rings[0], rings[-1]):
            f = bm.faces.new(ring)
            for k, l in enumerate(f.loops):
                a = 2 * math.pi * k / len(ring); l[uvl].uv = ((PIDX[colour] + 0.5 + 0.3 * math.cos(a)) / N, 0.5 + 0.3 * math.sin(a))
    ob = new_obj(name, bm, mat or MAT); parts.append((ob, bone)); return ob


def cyl_path(a, b, n=2):
    return [a.lerp(b, k / (n - 1)) for k in range(n)]


# ---------------- geometry (metres; origin = the anchor in the ceiling, the ceiling is z = 0)
TOP, LEN = -0.45, 1.0                        # the fixture hangs from z = TOP, 1 m long, straight down
BOT = TOP - LEN
# ceiling canopies: the one it still hangs from, and the other one with the snapped cable stub
tube("CanopyA", [Vector((0, 0, 0.0)), Vector((0, 0, -0.025))], 0.045, "white", "root", segs=16)
tube("CanopyB", [Vector((0.0, -1.0, 0.0)), Vector((0.0, -1.0, -0.025))], 0.045, "white", "root", segs=16)
stub = [Vector((0.0, -1.0, -0.02)), Vector((0.01, -1.0, -0.10)), Vector((0.03, -0.985, -0.17)), Vector((0.05, -0.97, -0.20))]
tube("StubB", stub, 0.004, "black", "root", segs=6, burnt_tail=0.04)
# the cable it hangs on (3 bones)
cable = [Vector((0, 0, -0.02 - k * (abs(TOP) - 0.02) / 12)) for k in range(13)]
tube("CableA", cable, 0.0045, "black", "cable", segs=8)
# hook on top of the fixture
tube("Hook", [Vector((0, 0, TOP + 0.005)), Vector((0, 0, TOP - 0.03))], 0.009, "alu", "lamp", segs=8)
# housing: back plate, side walls, end caps; the open side (diffuser) faces +y
mid = (TOP + BOT) / 2
box("Back", (0, -0.035, mid), (0.20, 0.010, LEN), "white", "lamp")
box("SideL", (-0.10, 0.0, mid), (0.010, 0.075, LEN), "dirty", "lamp")
box("SideR", (0.10, 0.0, mid), (0.010, 0.075, LEN), "white", "lamp")
box("CapT", (0, 0.0, TOP - 0.005), (0.21, 0.075, 0.012), "white", "lamp")
box("CapB", (0, 0.0, BOT + 0.005), (0.21, 0.075, 0.012), "dirty", "lamp")
box("Reflector", (0, -0.026, mid), (0.17, 0.006, LEN - 0.03), "alu", "lamp")
for k in range(9):                           # louvre slats across the open side, one hangs loose
    z = TOP - 0.06 - k * (LEN - 0.12) / 8
    if k == 6:
        box("SlatLoose", (0.05, 0.05, z - 0.03), (0.012, 0.030, 0.18), "alu", "lamp")
        continue
    box("Slat%d" % k, (0, 0.03, z), (0.19, 0.030, 0.004), "alu", "lamp")
box("RailL", (-0.07, 0.03, mid), (0.004, 0.03, LEN - 0.04), "alu", "lamp")
box("RailR", (0.07, 0.03, mid), (0.004, 0.03, LEN - 0.04), "alu", "lamp")
# the tubes: one whole, one broken off half way (emissive material)
tube("Tube1", cyl_path(Vector((-0.045, 0.0, TOP - 0.025)), Vector((-0.045, 0.0, BOT + 0.025))), 0.013, "glass", "lamp", segs=12, mat=MAT_TUBE)
broken = [Vector((0.045, 0.0, TOP - 0.025)), Vector((0.045, 0.0, TOP - 0.48)), Vector((0.047, 0.004, TOP - 0.53))]
tube("Tube2", broken, 0.013, "glass", "lamp", segs=12, mat=MAT_TUBE)
tube("Tube2End", cyl_path(Vector((0.045, 0.0, BOT + 0.025)), Vector((0.045, 0.0, BOT + 0.09))), 0.013, "glass", "lamp", segs=12, mat=MAT_TUBE)
for x in (-0.045, 0.045):
    for z in (TOP - 0.018, BOT + 0.018):
        box("Pin%.2f%.2f" % (x, z), (x, 0.0, z), (0.034, 0.034, 0.014), "alu", "lamp")
# the snapped cable dangling from the lower end (2 bones), burnt frayed tip
dang = [Vector((0.08, 0.0, BOT - 0.005)), Vector((0.085, 0.004, BOT - 0.10)), Vector((0.075, 0.012, BOT - 0.20)), Vector((0.06, 0.02, BOT - 0.29))]
dpath = [dang[0]] + [dang[i].lerp(dang[i + 1], s / 4) for i in range(3) for s in range(1, 5)]
tube("Dangle", dpath, 0.004, "black", "dangle", segs=6, burnt_tail=0.05)
tip = dpath[-1]
for s in range(6):
    a = 2 * math.pi * s / 6
    sp = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, -1)).normalized()
    tube("Strand%d" % s, [tip, tip + sp * 0.02, tip + sp * 0.035 + Vector((0, 0, -0.005))], 0.0009, "copper", "dangle", segs=4)

# ---------------- armature
arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data); sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
def bone(name, head, tail, parent=None, connect=False):
    b = eb.new(name); b.head = Vector(head); b.tail = Vector(tail)
    if parent: b.parent = eb[parent]; b.use_connect = connect
    return b
CZ = [-0.02, -0.02 + (TOP + 0.02) / 3, -0.02 + 2 * (TOP + 0.02) / 3, TOP]
bone("root", (0, 0, 0), (0, 0, -0.02))
bone("cable_01", (0, 0, CZ[0]), (0, 0, CZ[1]), "root")
bone("cable_02", (0, 0, CZ[1]), (0, 0, CZ[2]), "cable_01", True)
bone("cable_03", (0, 0, CZ[2]), (0, 0, CZ[3]), "cable_02", True)
bone("lamp", (0, 0, TOP), (0, 0, BOT), "cable_03", True)
bone("dangle_01", dang[0], dang[0] + (dang[2] - dang[0]) * 0.5, "lamp")
bone("dangle_02", eb["dangle_01"].tail.copy(), dang[3], "dangle_01", True)
bone("light", (0, 0.05, mid), (0, 0.15, mid), "lamp")           # points out of the open side: light direction
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------- skinning
for ob, b in parts:
    me = ob.data
    groups = {n: ob.vertex_groups.new(name=n) for n in ("root", "cable_01", "cable_02", "cable_03", "lamp", "dangle_01", "dangle_02")}
    for v in me.vertices:
        z = v.co.z
        if b == "cable":                                     # smooth weights along the cable
            w = {}
            for i in range(3):
                c = (CZ[i] + CZ[i + 1]) / 2; seg = (CZ[i] - CZ[i + 1])
                w["cable_%02d" % (i + 1)] = max(0.0, 1 - abs(z - c) / seg)
            if z > CZ[0] - 0.01: w = {"root": 1.0}
            s = sum(w.values()) or 1
            for n, x in w.items():
                if x > 0: groups[n].add([v.index], x / s, 'REPLACE')
        elif b == "dangle":
            t = min(1.0, max(0.0, (BOT - z) / 0.29))
            if t < 0.05: groups["lamp"].add([v.index], 1.0, 'REPLACE')
            else:
                groups["dangle_01"].add([v.index], max(0.0, 1 - t), 'REPLACE'); groups["dangle_02"].add([v.index], t, 'REPLACE')
        else:
            groups[b].add([v.index], 1.0, 'REPLACE')

for o in bpy.context.view_layer.objects: o.select_set(False)
for ob, _ in parts: ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0][0]
bpy.ops.object.join()
mesh = bpy.context.active_object; mesh.name = mesh.data.name = "SK_HangingLamp"
bm = bmesh.new(); bm.from_mesh(mesh.data); bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
bm.to_mesh(mesh.data); bm.free()
bpy.ops.object.shade_smooth()
mesh.parent = arm; md = mesh.modifiers.new("Armature", 'ARMATURE'); md.object = arm
print("tris", sum(len(p.vertices) - 2 for p in mesh.data.polygons))

# ---------------- animation: 4 s loop, a slow pendulum swing, the fixture turns a little, the broken cable lags behind
FPS, FR = 30, 120
sc.render.fps = FPS; sc.frame_start = 0; sc.frame_end = FR
arm.animation_data_create(); act = bpy.data.actions.new("A_HangingLamp_Swing"); arm.animation_data.action = act
w = 2 * math.pi / FR
SW = {  # bone: [(axis, degrees, harmonic, phase)]
    "cable_01": [("X", 7.0, 1, 0.0), ("Z", 3.5, 1, 1.4)],
    "cable_02": [("X", 2.0, 1, -0.5), ("Z", 1.2, 1, 0.9)],
    "cable_03": [("X", 1.5, 1, -0.9), ("Z", 0.8, 1, 0.4)],
    "lamp": [("X", 2.0, 1, -1.2), ("Y", 9.0, 1, 0.6), ("Z", 1.0, 2, 0.3)],
    "dangle_01": [("X", 13.0, 1, -1.7), ("Z", 7.0, 1, -0.6)],
    "dangle_02": [("X", 11.0, 1, -2.3), ("Z", 6.0, 1, -1.2)],
}
for pb in arm.pose.bones: pb.rotation_mode = 'XYZ'
for f in range(0, FR + 1, 3):
    for name, terms in SW.items():
        e = [0.0, 0.0, 0.0]
        for ax, deg, h, ph in terms:
            e["XYZ".index(ax)] += math.radians(deg) * math.sin(h * w * f + ph)
        pb = arm.pose.bones[name]; pb.rotation_euler = e; pb.keyframe_insert("rotation_euler", frame=f)
for fc in act.fcurves:
    for k in fc.keyframe_points: k.interpolation = 'BEZIER'

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "HangingLamp.blend"))
for o in bpy.context.view_layer.objects: o.select_set(o in (arm, mesh))
bpy.context.view_layer.objects.active = arm
# Unreal wants centimetres like the other FBX files of the project (unit scale 1 cm, no scale on the Armature node -
# Unreal drops that node together with its scale, so a metre rig with a x100 Armature came in 100 times too small)
sc.unit_settings.scale_length = 0.01
for o in bpy.context.view_layer.objects: o.select_set(o in (arm, mesh))
bpy.context.view_layer.objects.active = arm
arm.scale = (100.0, 100.0, 100.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SK_HangingLamp.fbx"), use_selection=True,
    object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, use_armature_deform_only=False,
    primary_bone_axis='X', secondary_bone_axis='Y', bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
    path_mode='STRIP', use_tspace=True)
print("exported")
