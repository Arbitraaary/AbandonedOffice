"""Realistic crumpled paper for Blender 4.2 (bpy).

Crumpled paper is (almost) piecewise flat: facets meet in sharp creases.
Here the surface height is the MIN / MAX of a few random planes around each
point, which gives continuous geometry with crisp creases. Each facet gets its
own patch of the page texture (random rotation/offset, true 1:1 paper scale),
with the texture seam lying exactly on the crease - like a real folded sheet.
"""
import bpy, bmesh, math, random, os
import numpy as np
from mathutils import Vector, noise

PAGES = os.environ.get("TB_PAGES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages"))

def _fib_sphere(n, rnd):
    pts = []
    for i in range(n):
        z = 1 - 2 * (i + rnd.random()) / n
        r = math.sqrt(max(0, 1 - z * z))
        a = i * 2.399963 + rnd.uniform(-0.4, 0.4)
        pts.append((r * math.cos(a), r * math.sin(a), z))
    return np.array(pts)

def _tangent_basis(n):
    a = np.array([0, 0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
    t = np.cross(n, a); t /= np.linalg.norm(t)
    return t, np.cross(n, t)

def crumpled_ball(name, radius, seed, page_w=0.21, page_h=0.297, n_big=26, n_small=90,
                  depth=0.22, flat=(1.0, 1.0, 1.0)):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)
    V = np.array([v.co[:] for v in bm.verts])
    D = V / np.linalg.norm(V, axis=1)[:, None]

    def planes(n, amp, tilt):
        C = _fib_sphere(n, rnd)
        A = np.array([rnd.uniform(-amp, amp) for _ in range(n)])
        T = []
        for c in C:
            t, b = _tangent_basis(c)
            ang = rnd.uniform(0, 2 * math.pi); mag = rnd.uniform(0.2, 1.0) * tilt
            T.append((t * math.cos(ang) + b * math.sin(ang)) * mag)
        return C, A, np.array(T)

    Cb, Ab, Tb = planes(n_big, depth * 0.6, depth * 1.6)
    Cs, As, Ts = planes(n_small, depth * 0.18, depth * 0.7)

    def evaluate(C, A, T, k, use_min):
        dots = D @ C.T                              # cosine to each centre
        idx = np.argsort(-dots, axis=1)[:, :k]      # k nearest centres
        vals = np.empty(idx.shape)
        for j in range(k):
            c = C[idx[:, j]]
            vals[:, j] = A[idx[:, j]] + np.einsum('ij,ij->i', D - c, T[idx[:, j]])
        win = np.argmin(vals, axis=1) if use_min else np.argmax(vals, axis=1)
        h = vals[np.arange(len(D)), win]
        return h, idx[np.arange(len(D)), win]

    hb, cell = evaluate(Cb, Ab, Tb, 6, True)      # big facets, valley creases
    hs, _ = evaluate(Cs, As, Ts, 5, False)        # small facets, ridge creases
    lump = np.array([noise.noise(Vector(d) * 1.3 + Vector((seed, seed * 2, 0))) for d in D])
    r = radius * (1.0 + hb + 0.5 * hs + 0.12 * lump)
    P = D * r[:, None] * np.array(flat)
    for v, p in zip(bm.verts, P):
        v.co = p

    # per-facet page patches
    uv = bm.loops.layers.uv.new("PaperUV")
    bm.verts.index_update()
    patch = {}
    for f in bm.faces:
        cid = int(np.bincount([cell[v.index] for v in f.verts]).argmax())
        if cid not in patch:
            n = Cb[cid]; t, b = _tangent_basis(n)
            a = rnd.uniform(0, 2 * math.pi)
            t2, b2 = t * math.cos(a) + b * math.sin(a), -t * math.sin(a) + b * math.cos(a)
            patch[cid] = (t2, b2, rnd.uniform(0.15, 0.85), rnd.uniform(0.12, 0.88))
        t2, b2, ou, ov = patch[cid]
        for l in f.loops:
            p = np.array(l.vert.co[:])
            l[uv].uv = (ou + p @ t2 / page_w, ov + p @ b2 / page_h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def crumpled_sheet(name, w, h, seed, res=0.004, crumple=0.6, curl=0.0, folds=()):
    """Loosely crumpled / folded flat sheet. folds: list of (axis 'x'|'y', position 0..1, angle deg)."""
    rnd = random.Random(seed)
    nx, ny = max(6, int(w / res)), max(6, int(h / res))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5)
    uv = bm.loops.layers.uv.new("PaperUV")
    for v in bm.verts:
        v.co.x *= w; v.co.y *= h
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / w + 0.5, l.vert.co.y / h + 0.5)
    P = np.array([v.co[:] for v in bm.verts])
    ext = max(w, h)
    # 2D min/max-of-planes crinkle
    def field(n, amp, tilt, use_min):
        C = np.array([(rnd.uniform(-w, w) * 0.6, rnd.uniform(-h, h) * 0.6) for _ in range(n)])
        A = np.array([rnd.uniform(-amp, amp) for _ in range(n)])
        T = np.array([(rnd.gauss(0, tilt), rnd.gauss(0, tilt)) for _ in range(n)])
        d2 = ((P[:, None, :2] - C[None]) ** 2).sum(-1)
        idx = np.argsort(d2, axis=1)[:, :5]
        vals = np.stack([A[idx[:, j]] + np.einsum('ij,ij->i', P[:, :2] - C[idx[:, j]], T[idx[:, j]])
                         for j in range(5)], 1)
        return vals.min(1) if use_min else vals.max(1)
    z = crumple * (field(40, 0.006, 0.12, True) + 0.6 * field(120, 0.002, 0.07, False))
    P[:, 2] = z - z.mean()
    for axis, pos, ang in folds:                      # real folds (letters folded in three, etc.)
        i = 0 if axis == 'x' else 1
        L = w if axis == 'x' else h
        c = (pos - 0.5) * L
        side = P[:, i] > c
        a = math.radians(ang)
        q = P[side].copy()
        dx, dz = q[:, i] - c, q[:, 2]
        q[:, i] = c + dx * math.cos(a) - dz * math.sin(a)
        q[:, 2] = dx * math.sin(a) + dz * math.cos(a)
        P[side] = q
    if curl:
        P[:, 2] += curl * (P[:, 0] / ext) ** 2
    for v, p in zip(bm.verts, P):
        v.co = p
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    m = ob.modifiers.new("solid", 'SOLIDIFY'); m.thickness = 0.0002; m.offset = 0.0
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier="solid")
    return ob

# ----------------------------------------------------------------- materials
_mat_cache = {}
def paper_material(page, age=0.5, tint=(1, 1, 1, 1)):
    key = (page, age, tuple(tint))
    if key in _mat_cache:
        return _mat_cache[key]
    m = bpy.data.materials.new("M_Paper_" + page)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    def N(t, loc, **kw):
        n = nt.nodes.new(t); n.location = loc
        for k, v in kw.items():
            if k in n.inputs: n.inputs[k].default_value = v
            else: setattr(n, k, v)
        return n
    L = nt.links.new
    def mix(loc, fac, a, b, blend='MIX'):
        mm = N("ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
        for sock, val in ((mm.inputs[0], fac), (mm.inputs[6], a), (mm.inputs[7], b)):
            if isinstance(val, bpy.types.NodeSocket): L(val, sock)
            else: sock.default_value = val
        return mm.outputs[2]
    def rng(loc, src, a, b):
        r = N("ShaderNodeMapRange", loc); r.inputs[1].default_value = a; r.inputs[2].default_value = b
        L(src, r.inputs[0]); return r.outputs[0]
    def mul(loc, a, k):
        x = N("ShaderNodeMath", loc, operation='MULTIPLY'); L(a, x.inputs[0]); x.inputs[1].default_value = k
        return x.outputs[0]

    out = N("ShaderNodeOutputMaterial", (1100, 0))
    b = N("ShaderNodeBsdfPrincipled", (800, 0)); L(b.outputs[0], out.inputs[0])
    uvn = N("ShaderNodeUVMap", (-1300, 0), uv_map="PaperUV")
    img = N("ShaderNodeTexImage", (-1050, 0)); img.extension = 'EXTEND'
    img.image = bpy.data.images.load(os.path.join(PAGES, page + ".png"), check_existing=True)
    L(uvn.outputs[0], img.inputs[0])
    tc = N("ShaderNodeTexCoord", (-1300, -500))
    y = N("ShaderNodeTexNoise", (-1050, -300), Scale=5.0, Detail=6.0, Roughness=0.6)
    L(uvn.outputs[0], y.inputs[0])
    c1 = mix((-600, 100), rng((-850, -300), y.outputs[0], 0.3, 0.8), img.outputs[0],
             (0.90, 0.82, 0.62, 1), 'MULTIPLY')
    c1b = mix((-450, 100), age, img.outputs[0], c1)                     # age = overall yellowing
    st = N("ShaderNodeTexNoise", (-1050, -600), Scale=4.0, Detail=8.0, Roughness=0.7)
    L(tc.outputs["Object"], st.inputs[0])
    c2 = mix((-300, 100), mul((-700, -600), rng((-850, -600), st.outputs[0], 0.62, 0.68), 0.6 * age),
             c1b, (0.75, 0.58, 0.38, 1), 'MULTIPLY')                    # water / coffee blotches
    geo = N("ShaderNodeNewGeometry", (-1050, -900))
    c3 = mix((-150, 100), mul((-700, -900), rng((-850, -900), geo.outputs["Pointiness"], 0.5, 0.42), 0.4),
             c2, (0.5, 0.47, 0.42, 1), 'MULTIPLY')                      # grime in the creases
    sep = N("ShaderNodeSeparateXYZ", (-850, -1150)); L(geo.outputs["Normal"], sep.inputs[0])
    c4 = mix((0, 100), mul((-550, -1150), rng((-700, -1150), sep.outputs[2], 0.55, 1.0), 0.3),
             c3, (0.40, 0.38, 0.34, 1))                                 # dust on top
    c5 = mix((200, 100), 1.0, c4, tint, 'MULTIPLY')
    L(c5, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    fib = N("ShaderNodeTexNoise", (300, -400), Scale=1200.0, Detail=2.0)
    L(tc.outputs["Object"], fib.inputs[0])
    bump = N("ShaderNodeBump", (550, -400), Strength=0.05, Distance=0.0002)
    L(fib.outputs[0], bump.inputs["Height"]); L(bump.outputs[0], b.inputs["Normal"])
    _mat_cache[key] = m
    return m
