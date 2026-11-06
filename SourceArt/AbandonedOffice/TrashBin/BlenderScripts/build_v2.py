"""Abandoned office trash bin v2: bin only, filled about halfway with crumpled paper.
python3.11 build_v2.py   ->  out/stage_v2.blend
"""
import bpy, math, random, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_trashbin as B
import paper as P

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
random.seed(21)

B.clean_scene()
sc = bpy.context.scene
M_metal, M_liner = B.mat_metal(), B.mat_liner()
body = B.build_body(); body.data.materials.append(M_metal)
liner = B.build_liner(); liner.data.materials.append(M_liner)

# ---------------- paper items (bottom ones first: they end up hidden, so keep them light)
pages = ["page_print_a", "page_print_b", "page_table", "page_ruled"]
items = []
def add(ob, page, age):
    ob.data.materials.append(P.paper_material(page, age=age))
    items.append(ob)
seed = 100
for k in range(18):
    seed += 1
    r = random.uniform(0.034, 0.046)
    ob = P.crumpled_ball(f"ball{k}", r, seed, flat=(1, random.uniform(0.8, 1), random.uniform(0.75, 0.95)))
    add(ob, random.choice(pages), random.uniform(0.35, 0.8))
add(P.crumpled_ball("sticky", 0.02, 7, page_w=0.076, page_h=0.076), "sticky", 0.3)
add(P.crumpled_sheet("letter", 0.21, 0.297, 9, res=0.006, crumple=0.5,
                     folds=[('y', 0.333, 168), ('y', 0.666, -140)]), "page_print_a", 0.5)
for ob in items:                      # pivot to geometry centre
    c = sum((v.co for v in ob.data.vertices), Vector()) / len(ob.data.vertices)
    for v in ob.data.vertices: v.co -= c

# ---------------- drop them into the bin with rigid-body physics
def run_sim(frames):
    for f in range(1, frames + 1):
        sc.frame_set(f)

def setup_world(frames):
    bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = 30; rw.solver_iterations = 25
    rw.point_cache.frame_start = 1; rw.point_cache.frame_end = frames
    sc.frame_start, sc.frame_end = 1, frames

def rb(ob, kind, shape, mass=0.004):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.rigidbody.object_add(type=kind)
    ob.rigid_body.collision_shape = shape
    ob.rigid_body.collision_margin = 0.0008
    ob.rigid_body.friction = 0.9
    ob.rigid_body.restitution = 0.0
    if kind == 'ACTIVE':
        ob.rigid_body.mass = mass
        ob.rigid_body.linear_damping = 0.6; ob.rigid_body.angular_damping = 0.7

def bake_down(objs, colliders):
    for o in bpy.context.selected_objects: o.select_set(False)
    for ob in objs: ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.visual_transform_apply()
    for ob in objs + colliders:
        if ob.rigid_body:
            with bpy.context.temp_override(object=ob, active_object=ob):
                bpy.ops.rigidbody.object_remove()
    bpy.ops.rigidbody.world_remove()
    sc.frame_set(1)

def cup_profile(i, th):
    if i == 0:
        return 0.0005, 0.032
    z = 0.032 if i == 1 else 0.032 + (B.H + 0.25 - 0.032) * (i - 1) / 8
    zw = min(z, B.H)
    r = B.RB + (B.RT - B.RB) * zw / B.H - B.T - 0.004 + B.wall_offset(th, zw)
    if i == 1:
        r -= 0.012
    return r, z
cup = B.new_obj("Collider", B.revolve("Collider", cup_profile, 10, 32))
B.add_mod_apply(cup, 'SOLIDIFY', thickness=0.02, offset=1.0)   # tall walls: nothing can escape

balls = [o for o in items if o.name != "letter"]
sheets = [o for o in items if o.name == "letter"]

# phase 1: balls, dropped in small layers from low height
setup_world(140)
rb(cup, 'PASSIVE', 'MESH')
for k, ob in enumerate(balls):
    layer, slot = divmod(k, 4)
    ang = slot * math.pi / 2 + layer * 0.7 + random.uniform(-0.3, 0.3)
    rad = 0.055 if slot < 4 else 0.0
    ob.location = (rad * math.cos(ang), rad * math.sin(ang), 0.09 + layer * 0.095)
    ob.rotation_euler = (random.uniform(0, 6.3), random.uniform(0, 6.3), random.uniform(0, 6.3))
    rb(ob, 'ACTIVE', 'CONVEX_HULL')
run_sim(140)
bake_down(balls, [cup])

# phase 2: sticky note falls on the pile
sticky = next(o for o in balls if o.name == "sticky")
balls_only = [o for o in balls if o is not sticky]
# phase 1 already dropped it - re-drop it on top
setup_world(80)
rb(cup, 'PASSIVE', 'MESH')
for ob in balls_only: rb(ob, 'PASSIVE', 'CONVEX_HULL')
top = max(max((ob.matrix_world @ v.co).z for v in ob.data.vertices) for ob in balls_only)
sticky.location = (0.03, -0.04, top + 0.04)
rb(sticky, 'ACTIVE', 'CONVEX_HULL', 0.001)
run_sim(80)
bake_down([sticky], [cup] + balls_only)

# phase 3: sheets are draped onto the pile (stiff paper resting on lumps)
from mathutils.bvhtree import BVHTree
import bmesh as _bm
def world_bvh(objs):
    bm = _bm.new()
    for ob in objs:
        me = ob.data.copy(); me.transform(ob.matrix_world)
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    t = BVHTree.FromBMesh(bm); bm.free(); return t
def drape(sheet, support, xy, yaw, tilt=0.0, lift=0.004, stiff=0.45):
    me = sheet.data
    sheet.matrix_world = Matrix.Identity(4)
    import numpy as np
    co = np.array([v.co[:] for v in me.vertices])
    c, s_ = math.cos(yaw), math.sin(yaw)
    x = co[:, 0] * c - co[:, 1] * s_ + xy[0]
    y = co[:, 0] * s_ + co[:, 1] * c + xy[1]
    zl = co[:, 2] + tilt * co[:, 0]
    tree = world_bvh(support)
    pile = np.zeros(len(co))
    for i in range(len(co)):
        hit = tree.ray_cast(Vector((x[i], y[i], 1.0)), Vector((0, 0, -1)))
        pile[i] = hit[0].z if hit[0] is not None else 0.03
    floor = pile + lift - zl                       # minimum offset per vertex
    base = np.percentile(floor, 70)                # rests on the highest ~30%
    off = np.maximum(base, floor)
    # relax: stiff paper bridges between lumps but never goes through them
    nbr = [[] for _ in range(len(co))]
    for e in me.edges:
        a, b = e.vertices; nbr[a].append(b); nbr[b].append(a)
    for it in range(40):
        avg = np.array([off[n].mean() if n else off[i] for i, n in enumerate(nbr)])
        off = np.maximum(off * (1 - stiff) + avg * stiff, floor)
    z = zl + off
    # edges that reach the bag wall are pushed in and curl up along it
    for i in range(len(co)):
        r = math.hypot(x[i], y[i])
        rin = B.RB + (B.RT - B.RB) * z[i] / B.H - B.T - 0.008
        if r > rin:
            k = rin / r
            z[i] += (r - rin) * 0.9
            x[i] *= k; y[i] *= k
    for i, v in enumerate(me.vertices):
        v.co = (x[i], y[i], z[i])
    me.update()
support = balls_only + [sticky]
letter = next(o for o in sheets if o.name == "letter")
drape(letter, support, (-0.045, 0.03), 1.25, tilt=0.12)
bpy.data.objects.remove(cup)

# report: fill height and anything that escaped
tops = []
for ob in items:
    ws = [ob.matrix_world @ v.co for v in ob.data.vertices]
    zt = max(w.z for w in ws); rmax = max(math.hypot(w.x, w.y) for w in ws)
    tops.append(zt)
    print(f"{ob.name:8s} top={zt:.3f} rmax={rmax:.3f} zmin={min(w.z for w in ws):.3f}")
print("fill top", round(max(tops), 3), "of", B.H)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage_v2_parts.blend"))
