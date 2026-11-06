"""Procedural trees / bushes / weeds for the office grounds.
python3.11 build_trees.py -> out/trees/*.fbx + Trees.blend
Two material slots per mesh: M_Bark (tiling T_Bark, UV = 0.5 m around x 1 m along) and M_Foliage (T_Foliage atlas, masked).
Pivot at the ground under the trunk; roots go ~30 cm below 0 so the tree sits on uneven ground.
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "trees"); os.makedirs(OUT, exist_ok=True)
REG = {}
for line in open(os.path.join(HERE, "tex", "foliage_regions.txt")):
    k, *v = line.split(); REG[k] = tuple(float(x) for x in v)

bpy.ops.wm.read_factory_settings(use_empty=True)
def preview_mats():
    mb = bpy.data.materials.new("M_Bark"); mb.use_nodes = True; nt = mb.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(HERE, "tex", "T_Bark_BC.png"))
    nt.links.new(t.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    mf = bpy.data.materials.new("M_Foliage"); mf.use_nodes = True; nt = mf.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(HERE, "tex", "T_Foliage.png"))
    nt.links.new(t.outputs[0], b.inputs["Base Color"]); nt.links.new(t.outputs[1], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.7
    try: mf.blend_method = 'CLIP'
    except Exception: pass
    return mb, mf
M_BARK, M_FOL = preview_mats()

class Builder:
    def __init__(s, seed):
        s.rnd = random.Random(seed); s.bm = bmesh.new(); s.uv = s.bm.loops.layers.uv.new("UVMap")
        s.leaf_faces = []; s.trunk_pts = []
    # ------------------------------------------------------------ branches
    def tube(s, pts, radii, segs):
        rings = []; prev = None; vlen = 0.0
        circ = 2 * math.pi * max(radii[0], 0.01); utile = max(1, round(circ / 0.5))
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            a = t.cross(Vector((0, 0, 1))) if prev is None else prev - t * prev.dot(t)
            if a.length < 1e-4: a = t.cross(Vector((1, 0, 0)))
            a.normalize(); prev = a; b2 = t.cross(a)
            if k: vlen += (pts[k] - pts[k - 1]).length
            ring = []
            for j in range(segs + 1):                          # duplicate seam column for clean UVs
                ang = 2 * math.pi * j / segs
                ring.append((s.bm.verts.new(p + (a * math.cos(ang) + b2 * math.sin(ang)) * radii[k]), (utile * j / segs, vlen)))
            rings.append(ring)
        for k in range(len(rings) - 1):
            for j in range(segs):
                q = [rings[k][j], rings[k][j + 1], rings[k + 1][j + 1], rings[k + 1][j]]
                f = s.bm.faces.new([x[0] for x in q]); f.smooth = True; f.material_index = 0
                for l, (_, uvv) in zip(f.loops, q): l[s.uv].uv = uvv
        return rings
    def branch(s, start, d, length, r0, depth, P, parent_t=0.0):
        n = max(3, int(length / P["step"]))
        pts = [start]; radii = []; dirc = d.normalized()
        for k in range(1, n + 1):
            t = k / n
            dirc = (dirc + Vector((noise.noise(pts[-1] * 0.9 + Vector((depth * 3.1, 0, 0))),
                                   noise.noise(pts[-1] * 0.9 + Vector((0, depth * 2.3, 0))),
                                   noise.noise(pts[-1] * 0.9 + Vector((0, 0, depth * 1.7))))) * P["wobble"]
                    + Vector((0, 0, P["up"][depth])) ).normalized()
            pts.append(pts[-1] + dirc * length / n)
        for k in range(n + 1):
            t = k / n
            r = r0 * (1 - t * P["taper"]) + 0.003
            if depth == 0 and not P.get("no_root") and t < 0.05: r *= 1 + ((0.05 - t) / 0.05) ** 2 * 0.45   # root flare
            radii.append(r)
        if depth == 0 and not P.get("no_root"):
            pts.insert(0, start - Vector((0, 0, 0.35))); radii.insert(0, radii[0] * 1.5)
            s.trunk_pts = pts[:max(2, len(pts) // 3)]
        s.tube(pts, radii, P["segs"][depth])
        if P.get("broken") and depth == 1 and s.rnd.random() < 0.3:          # snapped branch: no children
            return
        if depth >= P["depth"]:
            s.leaves_on(pts, P); return
        nk = P["kids"][depth]
        for c in range(nk):
            t = P["kid_from"][depth] + (1 - P["kid_from"][depth]) * (c + s.rnd.random() * 0.6) / nk
            i = min(len(pts) - 2, int(t * (len(pts) - 1)))
            base = pts[i]; pd = (pts[i + 1] - pts[i]).normalized()
            az = c * 2.4 + s.rnd.uniform(-0.4, 0.4)
            side = pd.cross(Vector((0, 0, 1))) if abs(pd.z) < 0.95 else pd.cross(Vector((1, 0, 0)))
            side.normalize(); side = Quaternion(pd, az) @ side
            ang = math.radians(s.rnd.uniform(*P["angle"][depth]))
            cd = (pd * math.cos(ang) + side * math.sin(ang)).normalized()
            cl = length * P["ratio"][depth] * (1.0 - 0.45 * t) * s.rnd.uniform(0.8, 1.15)
            cr = radii[i] * P["rratio"][depth]
            s.branch(base - pd * cr, cd, cl, cr, depth + 1, P, t)
        if depth == P["depth"] - 1 and P.get("leaves"):
            s.leaves_on(pts[len(pts) // 2:], P, sparse=True)
    # ------------------------------------------------------------ leaf cards
    def card(s, pos, normal, up, w, h, reg):
        u0, v0, u1, v1 = REG[reg]
        side = up.cross(normal).normalized(); up = normal.cross(side).normalized()
        cs = [pos - side * w / 2, pos + side * w / 2, pos + side * w / 2 + up * h, pos - side * w / 2 + up * h]
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        vs = [s.bm.verts.new(c) for c in cs]
        f = s.bm.faces.new(vs); f.material_index = 1; f.smooth = True
        for l, uv in zip(f.loops, uvs): l[s.uv].uv = uv
    def leaves_on(s, pts, P, sparse=False):
        if not P.get("leaves"): return
        cnt = P["cards"] // (2 if sparse else 1)
        for k in range(cnt):
            if s.rnd.random() > P["density"]: continue
            p = pts[s.rnd.randint(len(pts) // 3, len(pts) - 1)]
            out = (p - Vector((0, 0, P["crown_c"]))); out.z *= 0.5
            out = (out.normalized() + Vector((s.rnd.uniform(-1, 1), s.rnd.uniform(-1, 1), s.rnd.uniform(-0.3, 1))) * 0.8).normalized()
            nrm = Vector((s.rnd.uniform(-1, 1), s.rnd.uniform(-1, 1), s.rnd.uniform(-0.5, 0.5))).normalized()
            if abs(nrm.dot(out)) > 0.95: nrm = out.cross(Vector((0, 0, 1))).normalized()
            sz = P["card"] * s.rnd.uniform(0.75, 1.25)
            s.card(p - out * sz * 0.15, nrm, out, sz, sz, s.rnd.choice(P["regs"]))
    def finish(s, name):
        me = bpy.data.meshes.new(name); s.bm.to_mesh(me); s.bm.free()
        me.materials.append(M_BARK); me.materials.append(M_FOL)
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        # foliage normals point away from the crown centre -> soft, volumetric lighting instead of flat cards
        lv = [me.vertices[i].co for p in me.polygons if p.material_index == 1 for i in p.vertices]
        if lv:
            c = sum(lv, Vector()) / len(lv); c.z -= 0.15 * (max(v.z for v in lv) - min(v.z for v in lv))
            cn = [Vector(n.vector) for n in me.corner_normals]
            for p in me.polygons:
                if p.material_index == 1:
                    for li in p.loop_indices:
                        d = me.vertices[me.loops[li].vertex_index].co - c
                        cn[li] = (d.normalized() * 0.8 + Vector(p.normal) * 0.2).normalized() if d.length > 1e-4 else Vector((0, 0, 1))
            me.normals_split_custom_set(cn)
        return ob

def ucx_trunk(name, pts, r, top=3.0):
    bm = bmesh.new()
    for p in pts:
        if p.z > top: break
        for j in range(8):
            a = 2 * math.pi * j / 8; bm.verts.new(p + Vector((math.cos(a) * r, math.sin(a) * r, 0)))
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    m = bpy.data.meshes.new("ucx"); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(f"UCX_{name}_00", m); bpy.context.scene.collection.objects.link(o); o.hide_render = True; o.display_type = 'WIRE'
    return o

BASE = dict(step=0.35, wobble=0.25, taper=0.85, depth=3, segs=[12, 8, 6, 4], kids=[7, 5, 3], kid_from=[0.35, 0.25, 0.3],
            angle=[(35, 60), (30, 55), (25, 50)], ratio=[0.55, 0.55, 0.55], rratio=[0.55, 0.6, 0.6], up=[0.12, 0.06, 0.02, 0.0],
            leaves=True, cards=6, density=0.8, card=0.9, crown_c=6.0, regs=["leaf0", "leaf1", "leaf2"])
SPECS = {
    # broad, full crown (~9.5 m)
    "SM_Tree_Broadleaf_A": dict(BASE, seed=1, h=6.8, r=0.26, kids=[9, 5, 3], kid_from=[0.3, 0.25, 0.3], ratio=[0.62, 0.55, 0.55], angle=[(40, 70), (30, 55), (25, 50)]),
    # slender, thinning crown, forked trunk (~8 m)
    "SM_Tree_Broadleaf_B": dict(BASE, seed=2, h=6.5, r=0.18, kids=[6, 4, 3], ratio=[0.5, 0.5, 0.5], density=0.55,
                                angle=[(20, 40), (30, 50), (25, 50)], crown_c=5.5, regs=["leaf1", "leaf2", "leaf2"], fork=True),
    # dead: no leaves, broken branches, snapped top (~6.5 m)
    "SM_Tree_Dead": dict(BASE, seed=3, h=6.0, r=0.21, leaves=False, broken=True, wobble=0.4, kids=[6, 4, 2], up=[0.06, 0.02, -0.02, -0.04]),
}
objs = []
for name, P in SPECS.items():
    B = Builder(P["seed"]); noise_seed = P["seed"]
    if P.get("fork"):
        B.branch(Vector((0, 0, 0)), Vector((0.02, 0, 1)), 1.4, P["r"], 0, dict(P, kids=[0, 4, 3]))
        tp = B.trunk_pts
        for k, d in enumerate([Vector((0.35, 0.1, 1)), Vector((-0.3, -0.15, 1))]):
            B.branch(Vector((0.02, 0, 1.25)), d, P["h"] * (0.95 - 0.12 * k), P["r"] * 0.75, 0, dict(P, step=0.4, no_root=True))
        B.trunk_pts = tp
    elif P.get("broken"):
        B.branch(Vector((0, 0, 0)), Vector((0, 0.05, 1)), P["h"], P["r"], 0, P)
    else:
        B.branch(Vector((0, 0, 0)), Vector((0, 0, 1)), P["h"], P["r"], 0, P)
    ob = B.finish(name); objs.append((ob, B.trunk_pts, P["r"]))

# bush: many thin stems from the ground, dense cards
B = Builder(7)
P = dict(BASE, step=0.15, depth=2, segs=[5, 4, 3], kids=[4, 3], kid_from=[0.3, 0.3], ratio=[0.5, 0.5], rratio=[0.6, 0.6],
         angle=[(30, 55), (30, 50)], up=[0.1, 0.05, 0.0], cards=5, card=0.45, crown_c=0.5, density=0.85)
for k in range(9):
    a = k * 2.4; d = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 1))
    B.branch(Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, -0.05)), d, B.rnd.uniform(0.55, 0.8), 0.015, 0, dict(P, no_root=True))
bush = B.finish("SM_Bush")
# weeds: crossed cards
def weeds(name, reg, h, w, n, seed):
    B = Builder(seed)
    for k in range(n):
        a = math.pi * k / n + B.rnd.uniform(-0.2, 0.2); off = Vector((B.rnd.uniform(-0.08, 0.08), B.rnd.uniform(-0.08, 0.08), -0.02))
        nrm = Vector((math.cos(a), math.sin(a), 0)); up = Vector((B.rnd.uniform(-0.15, 0.15), B.rnd.uniform(-0.15, 0.15), 1)).normalized()
        B.card(off, nrm, up, w * B.rnd.uniform(0.85, 1.1), h * B.rnd.uniform(0.85, 1.15), reg)
    return B.finish(name)
wg = weeds("SM_Weeds_Grass", "grass", 0.45, 0.9, 4, 11)
wt = weeds("SM_Weeds_Tall", "weed", 0.75, 1.1, 3, 12)
# grass patches: ~2.5-3 m wide clusters of crossed grass cards (one actor covers a patch of ground)
def patch(name, radius, n, tall_share, seed):
    B = Builder(seed)
    for k in range(n):
        r = radius * math.sqrt(B.rnd.random()); a = B.rnd.uniform(0, 2 * math.pi)
        c = Vector((math.cos(a) * r, math.sin(a) * r, -0.03))
        edge = 1 - 0.5 * (r / radius)                             # shorter towards the rim
        tall = B.rnd.random() < tall_share
        reg = "weed" if tall else "grass"
        h = (0.7 if tall else 0.42) * B.rnd.uniform(0.75, 1.2) * edge; w = (0.9 if tall else 0.75) * B.rnd.uniform(0.8, 1.1) * edge
        a0 = B.rnd.uniform(0, math.pi)
        for j in range(2):
            ang = a0 + j * math.pi / 2
            up = Vector((B.rnd.uniform(-0.12, 0.12), B.rnd.uniform(-0.12, 0.12), 1)).normalized()
            B.card(c, Vector((math.cos(ang), math.sin(ang), 0)), up, w, h, reg)
    return B.finish(name)
pa = patch("SM_GrassPatch_A", 1.3, 75, 0.08, 21)
pb = patch("SM_GrassPatch_B", 1.6, 70, 0.25, 22)

# ------------------------------------------------------------------ export + preview layout
for ob, tp, r in objs:
    u = ucx_trunk(ob.name, tp, r * 1.2); u.parent = ob
layout = {"SM_GrassPatch_A": (-3, -6), "SM_GrassPatch_B": (-6, -5), "SM_Tree_Broadleaf_A": (0, 0), "SM_Tree_Broadleaf_B": (9, 1), "SM_Tree_Dead": (-8, 2), "SM_Bush": (4, -4),
          "SM_Weeds_Grass": (2, -5), "SM_Weeds_Tall": (5.5, -6)}
EXP_MATS = {}
def export_mat(m):
    # plain stand-in with the same slot name, no image nodes -> no texture references inside the FBX
    if m not in EXP_MATS:
        n = m.name; m.name = n + "_preview"
        EXP_MATS[m] = bpy.data.materials.new(n)                  # same name as the slot in Unreal
    return EXP_MATS[m]
def export(ob):
    keep_mats = list(ob.data.materials)
    for i, m in enumerate(keep_mats):
        e = export_mat(m); ob.data.materials[i] = e
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True)
    for c in ob.children: c.select_set(True)
    loc = ob.location.copy(); ob.location = (0, 0, 0)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, ob.name + ".fbx"), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE',
        add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_tspace=True)
    ob.location = loc
    for i, m in enumerate(keep_mats): ob.data.materials[i] = m
    me = ob.data
    print("exported", ob.name, "tris", sum(len(p.vertices) - 2 for p in me.polygons), "dims", tuple(round(d, 2) for d in ob.dimensions))
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("UCX")]:
    export(ob)
    ob.location = (*layout[ob.name], 0)
for i in bpy.data.images: i.pack()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Trees.blend"), compress=True)
