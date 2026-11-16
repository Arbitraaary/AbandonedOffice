"""Sparking cables for Lab 5: five cables torn out of the lobby ceiling hole, hanging down to the floor,
frayed copper ends lying on the floor. Pivot = ceiling surface (z = 0), the floor is CEILING_H below.
Flat-colour palette texture (no bake): every cable / the copper gets its own patch of a small atlas.
Sockets SOCKET_Spark_N mark where sparks fly from (the bare copper ends).
blender -b -P build_cables.py -> ../SM_SparkingCables.fbx, ../Textures/T_SparkingCables_*.png, ../SparkingCables.blend
"""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE); TEX = os.path.join(OUT, "Textures"); os.makedirs(TEX, exist_ok=True)   # -> SourceArt/AbandonedOffice/Hazards
CEILING_H = 3.90                     # lobby ceiling hole is 390 cm above the floor
FLOOR = -CEILING_H
random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------------- palette atlas: 8 patches in a row (u = (i + 0.5) / 8)
PAL = [  # name, base colour (sRGB 0..1), roughness, metallic
    ("black", (0.035, 0.035, 0.04), 0.55, 0.0),
    ("grey", (0.42, 0.42, 0.40), 0.6, 0.0),
    ("red", (0.55, 0.06, 0.05), 0.5, 0.0),
    ("blue", (0.07, 0.17, 0.45), 0.5, 0.0),
    ("white", (0.78, 0.76, 0.70), 0.6, 0.0),
    ("copper", (0.80, 0.42, 0.22), 0.3, 1.0),
    ("burnt", (0.06, 0.05, 0.045), 0.8, 0.0),   # scorched insulation near the ends
    ("tape", (0.10, 0.10, 0.10), 0.35, 0.0),
]
N = len(PAL)
W, H = 256, 32
bc = np.zeros((H, W, 3)); orm = np.zeros((H, W, 3))
for i, (_, col, r, m) in enumerate(PAL):
    x0, x1 = i * W // N, (i + 1) * W // N
    noise = 1.0 + 0.06 * (np.random.RandomState(i).rand(H, x1 - x0, 1) - 0.5)
    bc[:, x0:x1] = np.array(col) * noise
    orm[:, x0:x1] = (1.0, r, m)
from PIL import Image
Image.fromarray((np.clip(bc, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, "T_SparkingCables_BC.png"))
Image.fromarray((np.clip(orm, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, "T_SparkingCables_ORM.png"))
Image.fromarray(np.full((8, 8, 3), (128, 128, 255), np.uint8)).save(os.path.join(TEX, "T_SparkingCables_N.png"))
PIDX = {p[0]: i for i, p in enumerate(PAL)}

mat = bpy.data.materials.new("M_SparkingCables"); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(TEX, "T_SparkingCables_BC.png"))
t.interpolation = 'Closest'; nt.links.new(t.outputs[0], bsdf.inputs["Base Color"])
to = nt.nodes.new("ShaderNodeTexImage"); to.image = bpy.data.images.load(os.path.join(TEX, "T_SparkingCables_ORM.png"))
to.image.colorspace_settings.name = 'Non-Color'; to.interpolation = 'Closest'
sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(to.outputs[0], sep.inputs[0])
nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"]); nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def catmull(pts, n=8):
    """smooth poly-line through pts (centripetal-ish Catmull-Rom)"""
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            s = k / n
            s2, s3 = s * s, s * s * s
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s2 + (-p0 + 3 * p1 - 3 * p2 + p3) * s3))
    out.append(pts[-1])
    return out


def tube(name, path, r, colour, segs=8, burnt_tail=0.0):
    """mesh tube along path; UVs collapsed onto the palette patch (last burnt_tail metres scorched)"""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    total = sum((path[i + 1] - path[i]).length for i in range(len(path) - 1))
    along = 0.0
    prev_n = None
    for i, p in enumerate(path):
        tdir = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        nrm = (prev_n - tdir * prev_n.dot(tdir)).normalized() if prev_n else (tdir.orthogonal()).normalized()
        prev_n = nrm
        b = tdir.cross(nrm)
        if i > 0: along += (path[i] - path[i - 1]).length
        ring = [bm.verts.new(p + (nrm * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r) for k in range(segs)]
        rings.append((ring, along))
    for (ra, la), (rb, lb) in zip(rings, rings[1:]):
        c = PIDX["burnt"] if burnt_tail and total - la < burnt_tail else PIDX[colour]
        for k in range(segs):
            f = bm.faces.new((ra[k], ra[(k + 1) % segs], rb[(k + 1) % segs], rb[k]))
            # real (non-degenerate) UVs inside the colour patch: u round the cable, v along it
            u0 = (c + 0.15 + 0.7 * k / segs) / N
            u1 = (c + 0.15 + 0.7 * (k + 1) / segs) / N
            for l, (u, v) in zip(f.loops, ((u0, la), (u1, la), (u1, lb), (u0, lb))):
                l[uvl].uv = (u, v * 4.0)
    for ring, _ in (rings[0], rings[-1]):          # caps
        f = bm.faces.new(ring)
        for k, l in enumerate(f.loops):
            ang = 2 * math.pi * k / len(ring)
            l[uvl].uv = ((PIDX["copper"] + 0.5 + 0.3 * math.cos(ang)) / N, 0.5 + 0.3 * math.sin(ang))
    me = bpy.data.meshes.new(name); bm.normal_update(); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); me.materials.append(mat)
    return ob


parts, sockets = [], []
CABLES = [  # colour, radius m, top (x, y) in the hole, floor direction (deg), hanging drift, lying length, loop
    ("black", 0.0110, (-0.10, 0.06), 20, 0.20, 1.2, False),
    ("grey", 0.0095, (0.05, 0.12), 140, 0.12, 0.9, True),
    ("red", 0.0075, (0.12, -0.05), 255, 0.28, 1.3, False),
    ("blue", 0.0075, (-0.02, -0.12), 320, 0.16, 0.8, False),
    ("white", 0.0085, (0.00, 0.00), 200, 0.30, 1.0, True),
]
BUNDLE_Z = -0.30
for ci, (colour, r, (tx, ty), ang, drift, lie, loop) in enumerate(CABLES):
    a = math.radians(ang)
    d = Vector((math.cos(a), math.sin(a), 0))
    side = Vector((-d.y, d.x, 0))
    floor_z = FLOOR + r
    top = Vector((tx, ty, 0.02))
    bund = Vector((0.012 * math.cos(ci * 1.3), 0.012 * math.sin(ci * 1.3), BUNDLE_Z))   # taped together here
    pts = [top, top * 0.5 + bund * 0.5 + Vector((0, 0, -0.04)), bund]
    # hanging part: slightly swaying, drifting towards its side of the floor
    low = FLOOR + 0.55
    for k in range(1, 6):
        s_ = k / 5.0
        p = bund + d * drift * (s_ ** 1.6) + side * 0.04 * math.sin(s_ * math.pi * (1.2 + 0.3 * ci))
        p.z = BUNDLE_Z + (low - BUNDLE_Z) * s_
        pts.append(p)
    base = pts[-1]
    # a soft bend onto the floor (radius ~25 cm), then lying on the floor
    for ang_b in (25, 50, 72, 88):
        t_ = math.radians(ang_b)
        p = base + d * (0.28 * (1 - math.cos(t_))) * 1.6 + Vector((0, 0, -(0.55 - r) * math.sin(t_)))
        pts.append(p)
    touch = pts[-1].copy(); touch.z = floor_z; pts[-1] = touch
    if loop:                                       # a loose loop lying on the floor
        c = touch + d * 0.35 + side * 0.18
        for k in range(1, 10):
            t_ = -math.pi / 2 + k * (2 * math.pi * 0.85) / 9
            p = c + (side * math.cos(t_) + d * math.sin(t_)) * 0.18 * (1 + 0.15 * k / 9)
            p.z = floor_z + (0.012 if 3 <= k <= 5 else 0.0)        # crosses over itself
            pts.append(p)
        start = pts[-1]
    else:
        start = touch
    for k in range(1, 5):
        s_ = k / 4.0
        p = start + d * lie * s_ * 0.8 + side * 0.15 * math.sin(s_ * math.pi * 1.3 + ci) * s_
        p.z = floor_z
        pts.append(p)
    path = catmull(pts, 6)
    parts.append(tube("Cable_%d" % ci, path, r, colour, burnt_tail=0.15))
    # stripped copper core at the end + splayed strands
    end, back = path[-1], (path[-1] - path[-3]).normalized()
    core = [end + back * (0.012 * k) for k in range(5)]
    for q in core: q.z = max(q.z, FLOOR + r * 0.45)
    parts.append(tube("Core_%d" % ci, core, r * 0.45, "copper", segs=6))
    tip = core[-1]
    for s_ in range(7):
        sa = 2 * math.pi * s_ / 7 + ci
        spread = (back + Vector((math.cos(sa), math.sin(sa), 0)) * 0.7).normalized()
        strand = [tip, tip + spread * 0.025 + Vector((0, 0, 0.004)), tip + spread * 0.055 + Vector((0, 0, random.uniform(0.0, 0.015)))]
        for q in strand: q.z = max(q.z, FLOOR + 0.0015)
        parts.append(tube("Strand_%d_%d" % (ci, s_), strand, 0.0012, "copper", segs=4))
    sockets.append(tip + Vector((0, 0, 0.01)))

# a bit of black tape round the bundle just below the ceiling
tape = [Vector((0.0, 0.0, BUNDLE_Z - 0.04 + k * 0.02)) for k in range(5)]
parts.append(tube("Tape", tape, 0.032, "tape", segs=12))

for o in bpy.context.view_layer.objects: o.select_set(False)
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object; ob.name = ob.data.name = "SM_SparkingCables"
bm = bmesh.new(); bm.from_mesh(ob.data)                       # cable end caps are n-gons -> triangles (clean tangents)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
bm.to_mesh(ob.data); bm.free()
bpy.ops.object.shade_smooth()
print("tris", sum(len(p.vertices) - 2 for p in ob.data.polygons))

# sockets for the sparks (FBX empties named SOCKET_<name> become static mesh sockets in Unreal)
for i, p in enumerate(sockets + [Vector((0, 0, -0.32))]):
    e = bpy.data.objects.new("SOCKET_Spark_%d" % i, None); sc.collection.objects.link(e)
    e.location = p; e.parent = ob; e.empty_display_size = 0.05

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "SparkingCables.blend"))
for o in bpy.context.view_layer.objects: o.select_set(o.name.startswith("SOCKET_") or o == ob)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_SparkingCables.fbx"), use_selection=True,
    object_types={'MESH', 'EMPTY'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False,
    path_mode='STRIP', use_tspace=True)
print("exported")
