"""
Abandoned office trash bin — procedural build for Blender 4.2+.
Run:  blender -b -P build_trashbin.py   (or python3.11 with the bpy module)
Builds: SM_AbandonedTrashBin (dented metal bin + torn liner + paper trash)
        SM_TrashSpill        (crumpled paper + crushed cup on the floor)
Units: metres (Blender default) -> Unreal reads them as centimetres x100.
"""
import bpy, bmesh, math, random
from mathutils import Vector, noise, Matrix

random.seed(7)
OUT = __import__("os").environ.get("TB_OUT", "/home/claude/trashbin/out")

# ----------------------------------------------------------------- helpers
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'
    s.unit_settings.scale_length = 1.0

def new_obj(name, me, coll=None):
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob

def revolve(name, profile_fn, n_prof, segs, close_bottom=True):
    """profile_fn(i, theta) -> (r, z) ; builds a ring-grid mesh."""
    bm = bmesh.new()
    rings = []
    for j in range(segs):
        th = 2 * math.pi * j / segs
        col = []
        for i in range(n_prof):
            r, z = profile_fn(i, th)
            col.append(bm.verts.new((r * math.cos(th), r * math.sin(th), z)))
        rings.append(col)
    for j in range(segs):
        a, b = rings[j], rings[(j + 1) % segs]
        for i in range(n_prof - 1):
            bm.faces.new((a[i], b[i], b[i + 1], a[i + 1]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return me

def smooth(me, on=True):
    for p in me.polygons:
        p.use_smooth = on

def add_mod_apply(ob, mtype, **kw):
    m = ob.modifiers.new(mtype.lower(), mtype)
    for k, v in kw.items():
        setattr(m, k, v)
    bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=m.name)

def merge_close(ob, d=1e-5):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=d)
    bm.to_mesh(ob.data); bm.free()

# ----------------------------------------------------------------- bin body
H = 0.38          # height
RB, RT = 0.118, 0.142   # bottom / top outer radius
T = 0.0025        # wall thickness
DENTS = [  # (theta, z, depth, sigma)
    (0.6, 0.22, 0.016, 0.045),
    (0.95, 0.31, 0.008, 0.03),
    (3.7, 0.12, 0.010, 0.05),
    (4.6, 0.33, 0.006, 0.025),
]

def wall_offset(th, z):
    """Radial deformation shared by every surface hugging the wall."""
    r_here = RB + (RT - RB) * max(0.0, min(1.0, z / H))
    d = 0.0
    for t0, z0, dep, sg in DENTS:
        dth = math.atan2(math.sin(th - t0), math.cos(th - t0))
        dd = (dth * r_here) ** 2 + (z - z0) ** 2
        d -= dep * math.exp(-dd / (2 * sg * sg))
    d += 0.004 * math.cos(2 * th + 0.4) * (z / H)          # slightly oval mouth
    for zb in (0.035, H - 0.035):                           # stamped stiffening beads
        d += 0.003 * math.exp(-((z - zb) ** 2) / (2 * 0.0035 ** 2))
    d += 0.0008 * noise.noise(Vector((math.cos(th) * 3, math.sin(th) * 3, z * 6)))
    return d

def rim_drop(th):
    dth = math.atan2(math.sin(th - 0.75), math.cos(th - 0.75))
    return -0.006 * math.exp(-dth * dth / 0.18)              # rim bent where kicked

def body_profile():
    pts = []  # (r, z, follows_wall)
    pts.append((0.0005, 0.0, False))
    for k in range(1, 6):
        pts.append((RB * 0.95 * k / 5, 0.0, False))
    pts.append((RB - 0.002, 0.0, False))
    pts.append((RB, 0.003, True))
    N = 34
    for k in range(1, N + 1):
        z = 0.003 + (H - 0.003) * k / N
        pts.append((RB + (RT - RB) * z / H, z, True))
    # rolled rim (circle r=4.5mm around the lip)
    cr = 0.0038
    cx, cz = RT - T / 2 + 0.0022, H + 0.0015
    for k in range(0, 13):                      # -60deg (outside) over the top to 240deg (inside)
        a = math.radians(-60 + 300 * k / 12)
        pts.append((cx + cr * math.cos(a), cz + cr * math.sin(a), True))
    # inner wall going down
    for k in range(N, 0, -1):
        z = 0.003 + (H - 0.003) * k / N
        pts.append((RB + (RT - RB) * z / H - T, z, True))
    pts.append((RB - T, 0.003 + T, True))
    for k in range(5, 0, -1):
        pts.append((RB * 0.95 * k / 5 - T, T, False))
    pts.append((0.0005, T, False))
    return pts

def build_body():
    prof = body_profile()
    segs = 112
    def fn(i, th):
        r, z, follow = prof[i]
        if follow:
            r += wall_offset(th, min(z, H))
            if z > H - 0.03:
                z += rim_drop(th) * (z - (H - 0.03)) / 0.03
        return r, z
    me = revolve("Body", fn, len(prof), segs)
    ob = new_obj("Bin_Body", me)
    merge_close(ob, 0.0008)
    smooth(me)
    return ob

# ----------------------------------------------------------------- liner bag
def build_liner():
    segs, N = 112, 46
    def hang(th):
        n = noise.noise(Vector((math.cos(th) * 1.7, math.sin(th) * 1.7, 0.3)))
        h = 0.055 + 0.03 * n
        # one long torn strip
        dth = math.atan2(math.sin(th - 2.2), math.cos(th - 2.2))
        h += 0.06 * math.exp(-dth * dth / 0.02)
        return max(0.035, h)
    def fn(i, th):
        t = i / (N - 1)
        zr = H + rim_drop(th)
        if t < 0.55:                          # inside, from bottom up
            u = t / 0.55
            z = 0.03 + (zr - 0.035) * u
            r = RB + (RT - RB) * z / H - T - 0.0025 + wall_offset(th, z)
            r -= 0.012 * (1 - u) ** 3           # bag sags inward near bottom
            wr = 0.0035 * noise.noise(Vector((math.cos(th) * 9, math.sin(th) * 9, z * 25))) + 0.0015 * noise.noise(Vector((math.cos(th) * 30, math.sin(th) * 30, z * 60)))
            return r + wr, z
        elif t < 0.66:                        # fold over the rim
            u = (t - 0.55) / 0.11
            a = math.pi * u
            cx = RT + 0.002 + wall_offset(th, H)
            return cx - 0.0085 * math.cos(a), zr + 0.002 + 0.0075 * math.sin(a)
        else:                                 # hanging outside
            u = (t - 0.66) / 0.34
            z = zr - hang(th) * u
            r = RB + (RT - RB) * z / H + 0.0065 + wall_offset(th, z)
            wr = 0.006 * u * noise.noise(Vector((math.cos(th) * 7, math.sin(th) * 7, z * 18 + 3))) + 0.003 * u * noise.noise(Vector((math.cos(th) * 28, math.sin(th) * 28, z * 50)))
            wr += 0.004 * u * u                   # flares outwards a bit
            return r + abs(wr), z
    me = revolve("Liner", fn, N, segs)
    ob = new_obj("Bin_Liner", me)
    # tear holes / ragged edge in the hanging part
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z < H - 0.025:
            r = math.hypot(c.x, c.y)
            if r > RB + (RT - RB) * c.z / H:     # outside part only
                n = noise.noise(c * 22.0)
                if n > 0.42:
                    kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me); bm.free()
    smooth(me)
    add_mod_apply(ob, 'SOLIDIFY', thickness=0.0006, offset=0.0)
    return ob

# ----------------------------------------------------------------- paper trash
def crumpled_ball(name, radius, seed):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=radius)
    off = Vector((rnd.random() * 50, rnd.random() * 50, rnd.random() * 50))
    planes = [Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() for _ in range(9)]
    for v in bm.verts:
        p = v.co.normalized()
        k = 1.0 + 0.22 * noise.noise(p * 2.2 + off) + 0.10 * noise.noise(p * 5.0 + off)
        for pl in planes:                      # sharp fold creases
            k -= 0.045 * abs(p.dot(pl)) ** 0.5 - 0.03
        k += rnd.uniform(-0.035, 0.035)
        v.co = p * radius * k
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    smooth(me, False)                          # faceted = crumpled
    ob = new_obj(name, me)
    ob.scale = (1.0, rnd.uniform(0.8, 1.0), rnd.uniform(0.75, 0.95))
    return ob

def crumpled_sheet(name, seed, crumple=0.02, w=0.21, h=0.297):
    rnd = random.Random(seed)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=22, y_subdivisions=30, size=1)
    ob = bpy.context.active_object; ob.name = name; ob.data.name = name
    off = Vector((rnd.random() * 40, rnd.random() * 40, 0))
    for v in ob.data.vertices:
        x, y = v.co.x * w, v.co.y * h
        z = crumple * noise.noise(Vector((x * 9, y * 9, 0)) + off)
        z += crumple * 0.6 * abs(noise.noise(Vector((x * 23, y * 23, 1)) + off))
        z += 0.03 * max(0.0, x / w + 0.3) ** 2 * (rnd.random() * 0.2 + 1)   # curled edge
        v.co = (x, y, z)
    smooth(ob.data, False)
    add_mod_apply(ob, 'SOLIDIFY', thickness=0.0005, offset=-1.0)
    return ob

def paper_cup(name, crushed=0.25):
    rt, rb, h = 0.041, 0.028, 0.095
    def fn(i, th):
        prof = [(0.0005, 0.0), (rb * 0.5, 0.0), (rb - 0.001, 0.0), (rb, 0.002)]
        for k in range(1, 15):
            z = 0.002 + (h - 0.002) * k / 14
            prof.append((rb + (rt - rb) * z / h, z))
        prof += [(rt + 0.0015, h + 0.0015), (rt + 0.002, h - 0.001)]
        r, z = prof[i]
        sq = 1 - crushed * 0.35 * (math.cos(2 * th) * 0.5 + 0.5) * (z / h)   # squeezed
        dth = math.atan2(math.sin(th - 1.0), math.cos(th - 1.0))
        r -= crushed * 0.012 * math.exp(-dth * dth / 0.15) * math.sin(math.pi * min(1, z / h))
        return r * sq, z
    me = revolve(name, fn, 20, 64)
    ob = new_obj(name, me)
    merge_close(ob, 0.0005)
    smooth(me)
    add_mod_apply(ob, 'SOLIDIFY', thickness=0.0006, offset=-1.0)
    return ob

# ----------------------------------------------------------------- materials
def mat_nodes(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf

def N(nt, t, loc, **kw):
    n = nt.nodes.new(t); n.location = loc
    for k, v in kw.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
        else:
            setattr(n, k, v)
    return n

def L(nt, a, b):
    nt.links.new(a, b)

def mix(nt, loc, fac, a, b, blend='MIX', dtype='RGBA'):
    m = N(nt, "ShaderNodeMix", loc, data_type=dtype, blend_type=blend)
    if dtype == 'RGBA':
        ia, ib, out = m.inputs[6], m.inputs[7], m.outputs[2]
    else:
        ia, ib, out = m.inputs[2], m.inputs[3], m.outputs[0]
    for sock, val in ((ia, a), (ib, b)):
        if isinstance(val, bpy.types.NodeSocket): L(nt, val, sock)
        else: sock.default_value = val
    if isinstance(fac, bpy.types.NodeSocket): L(nt, fac, m.inputs[0])
    else: m.inputs[0].default_value = fac
    return out

def ramp(nt, loc, src, p0, p1):
    r = N(nt, "ShaderNodeMapRange", loc)
    r.inputs[1].default_value, r.inputs[2].default_value = p0, p1
    L(nt, src, r.inputs[0])
    return r.outputs[0]

def dust_mask(nt, x, y, amount=1.0):
    geo = N(nt, "ShaderNodeNewGeometry", (x, y))
    sep = N(nt, "ShaderNodeSeparateXYZ", (x + 180, y)); L(nt, geo.outputs["Normal"], sep.inputs[0])
    up = ramp(nt, (x + 360, y), sep.outputs[2], 0.45, 0.95)
    tc = N(nt, "ShaderNodeTexCoord", (x, y - 200))
    nz = N(nt, "ShaderNodeTexNoise", (x + 180, y - 200), Scale=18.0, Detail=8.0)
    L(nt, tc.outputs["Object"], nz.inputs[0])
    nzr = ramp(nt, (x + 360, y - 200), nz.outputs[0], 0.35, 0.7)
    m = N(nt, "ShaderNodeMath", (x + 540, y), operation='MULTIPLY')
    L(nt, up, m.inputs[0]); L(nt, nzr, m.inputs[1])
    m2 = N(nt, "ShaderNodeMath", (x + 700, y), operation='MULTIPLY', use_clamp=True)
    L(nt, m.outputs[0], m2.inputs[0]); m2.inputs[1].default_value = amount
    return m2.outputs[0]

DUST = (0.36, 0.34, 0.30, 1)

def mat_metal():
    m, nt, b = mat_nodes("M_Bin_Metal")
    tc = N(nt, "ShaderNodeTexCoord", (-1600, 0))
    # paint chips: noise + pointiness (edges / dents wear first)
    geo = N(nt, "ShaderNodeNewGeometry", (-1600, -400))
    nz = N(nt, "ShaderNodeTexNoise", (-1400, -250), Scale=26.0, Detail=12.0, Roughness=0.7)
    L(nt, tc.outputs["Object"], nz.inputs[0])
    pt = ramp(nt, (-1400, -450), geo.outputs["Pointiness"], 0.5, 0.56)
    chip_raw = N(nt, "ShaderNodeMath", (-1200, -300), operation='ADD')
    L(nt, nz.outputs[0], chip_raw.inputs[0]); L(nt, pt, chip_raw.inputs[1])
    chips = ramp(nt, (-1000, -300), chip_raw.outputs[0], 0.86, 0.9)
    # rust streaks: noise stretched vertically, stronger near rim and bottom
    mp = N(nt, "ShaderNodeMapping", (-1400, 250)); mp.inputs["Scale"].default_value = (40, 40, 2.5)
    L(nt, tc.outputs["Object"], mp.inputs[0])
    rn = N(nt, "ShaderNodeTexNoise", (-1200, 250), Scale=3.0, Detail=10.0)
    L(nt, mp.outputs[0], rn.inputs[0])
    sep = N(nt, "ShaderNodeSeparateXYZ", (-1400, 450)); L(nt, tc.outputs["Object"], sep.inputs[0])
    zb = ramp(nt, (-1200, 450), sep.outputs[2], 0.10, 0.0)
    zt = ramp(nt, (-1200, 600), sep.outputs[2], 0.30, 0.385)
    zmask = N(nt, "ShaderNodeMath", (-1000, 500), operation='MAXIMUM')
    L(nt, zb, zmask.inputs[0]); L(nt, zt, zmask.inputs[1])
    patch = N(nt, "ShaderNodeTexNoise", (-1200, 700), Scale=5.0, Detail=4.0)
    L(nt, tc.outputs["Object"], patch.inputs[0])
    pm = ramp(nt, (-1000, 700), patch.outputs[0], 0.5, 0.62)
    zm2 = N(nt, "ShaderNodeMath", (-900, 600), operation='MULTIPLY')
    L(nt, zmask.outputs[0], zm2.inputs[0]); L(nt, pm, zm2.inputs[1])
    rs = N(nt, "ShaderNodeMath", (-850, 300), operation='MULTIPLY')
    L(nt, rn.outputs[0], rs.inputs[0]); L(nt, zm2.outputs[0], rs.inputs[1])
    rust = ramp(nt, (-700, 300), rs.outputs[0], 0.25, 0.45)
    rust_or_chip = N(nt, "ShaderNodeMath", (-550, 0), operation='MAXIMUM')
    L(nt, rust, rust_or_chip.inputs[0])
    chip_rust = N(nt, "ShaderNodeMath", (-700, -150), operation='MULTIPLY')
    L(nt, chips, chip_rust.inputs[0]); chip_rust.inputs[1].default_value = 0.5
    L(nt, chip_rust.outputs[0], rust_or_chip.inputs[1])
    # colours
    pv = N(nt, "ShaderNodeTexNoise", (-1000, 100), Scale=4.0, Detail=3.0)
    L(nt, tc.outputs["Object"], pv.inputs[0])
    paint = mix(nt, (-750, 100), pv.outputs[0], (0.030, 0.032, 0.035, 1), (0.055, 0.057, 0.06, 1))
    c1 = mix(nt, (-400, 100), chips, paint, (0.42, 0.42, 0.40, 1))         # bare steel
    rc = N(nt, "ShaderNodeTexNoise", (-700, 500), Scale=60.0, Detail=6.0)
    L(nt, tc.outputs["Object"], rc.inputs[0])
    rustcol = mix(nt, (-550, 500), rc.outputs[0], (0.16, 0.055, 0.02, 1), (0.30, 0.13, 0.05, 1))
    c2 = mix(nt, (-200, 100), rust, c1, rustcol)
    dm0 = dust_mask(nt, -1100, -800, 0.85)
    film = N(nt, "ShaderNodeMath", (-300, -800), operation='MULTIPLY_ADD', use_clamp=True)
    L(nt, dm0, film.inputs[0]); film.inputs[1].default_value = 0.85; film.inputs[2].default_value = 0.12
    dm = film.outputs[0]
    c3 = mix(nt, (100, 100), dm, c2, DUST)
    L(nt, c3, b.inputs["Base Color"])
    # roughness / metal
    r1 = mix(nt, (-400, -150), chips, 0.5, 0.32, dtype='FLOAT')
    r2 = mix(nt, (-200, -150), rust, r1, 0.88, dtype='FLOAT')
    r3 = mix(nt, (100, -150), dm, r2, 0.95, dtype='FLOAT')
    L(nt, r3, b.inputs["Roughness"])
    met = N(nt, "ShaderNodeMath", (-200, -350), operation='SUBTRACT', use_clamp=True)
    L(nt, chips, met.inputs[0]); L(nt, rust_or_chip.outputs[0], met.inputs[1])
    met2 = N(nt, "ShaderNodeMath", (0, -350), operation='ADD', use_clamp=True)
    L(nt, chips, met2.inputs[0]); met2.inputs[1].default_value = 0.0
    mm = mix(nt, (150, -350), rust, met2.outputs[0], 0.0, dtype='FLOAT')
    mm2 = mix(nt, (300, -350), dm, mm, 0.0, dtype='FLOAT')
    L(nt, mm2, b.inputs["Metallic"])
    # bump: orange peel + chip edges + rust grain
    hb = N(nt, "ShaderNodeMath", (100, -600), operation='ADD')
    L(nt, chips, hb.inputs[0])
    L(nt, rc.outputs[0], hb.inputs[1])
    bump = N(nt, "ShaderNodeBump", (350, -600), Strength=0.25, Distance=0.0008)
    neg = N(nt, "ShaderNodeMath", (200, -600), operation='MULTIPLY')
    L(nt, hb.outputs[0], neg.inputs[0]); neg.inputs[1].default_value = -1.0
    L(nt, neg.outputs[0], bump.inputs["Height"])
    L(nt, bump.outputs[0], b.inputs["Normal"])
    return m

def mat_liner():
    m, nt, b = mat_nodes("M_Bin_Liner")
    tc = N(nt, "ShaderNodeTexCoord", (-900, 0))
    nz = N(nt, "ShaderNodeTexNoise", (-700, 0), Scale=90.0, Detail=4.0)
    L(nt, tc.outputs["Object"], nz.inputs[0])
    base = mix(nt, (-400, 100), nz.outputs[0], (0.006, 0.006, 0.007, 1), (0.016, 0.016, 0.018, 1))
    dm = dust_mask(nt, -1100, -500, 0.6)
    L(nt, mix(nt, (100, 100), dm, base, DUST), b.inputs["Base Color"])
    r = mix(nt, (-400, -150), nz.outputs[0], 0.28, 0.5, dtype='FLOAT')
    L(nt, mix(nt, (100, -150), dm, r, 0.9, dtype='FLOAT'), b.inputs["Roughness"])
    bump = N(nt, "ShaderNodeBump", (300, -400), Strength=0.15, Distance=0.0005)
    L(nt, nz.outputs[0], bump.inputs["Height"]); L(nt, bump.outputs[0], b.inputs["Normal"])
    return m

def mat_paper():
    m, nt, b = mat_nodes("M_Paper_Trash")
    tc = N(nt, "ShaderNodeTexCoord", (-1200, 0))
    st = N(nt, "ShaderNodeTexNoise", (-1000, 200), Scale=7.0, Detail=6.0)
    L(nt, tc.outputs["Object"], st.inputs[0])
    stain = ramp(nt, (-800, 200), st.outputs[0], 0.54, 0.66)
    # faint printed lines (generic, unreadable)
    wv = N(nt, "ShaderNodeTexWave", (-1000, -100), wave_type='BANDS', bands_direction='Y', Scale=55.0, Distortion=0.4)
    L(nt, tc.outputs["Object"], wv.inputs[0])
    lines = ramp(nt, (-800, -100), wv.outputs[1], 0.9, 1.0)
    bk = N(nt, "ShaderNodeTexNoise", (-1000, -300), Scale=120.0)
    L(nt, tc.outputs["Object"], bk.inputs[0])
    lb = N(nt, "ShaderNodeMath", (-650, -150), operation='MULTIPLY')
    L(nt, lines, lb.inputs[0]); L(nt, ramp(nt, (-800, -300), bk.outputs[0], 0.45, 0.6), lb.inputs[1])
    yel = N(nt, "ShaderNodeTexNoise", (-1000, 450), Scale=2.0)
    L(nt, tc.outputs["Object"], yel.inputs[0])
    paper = mix(nt, (-600, 400), yel.outputs[0], (0.70, 0.67, 0.58, 1), (0.58, 0.51, 0.38, 1))
    c1 = mix(nt, (-400, 200), lb.outputs[0], paper, (0.25, 0.25, 0.27, 1))
    c2 = mix(nt, (-200, 200), stain, c1, (0.45, 0.32, 0.18, 1))
    dm = dust_mask(nt, -1300, -700, 0.5)
    L(nt, mix(nt, (100, 200), dm, c2, DUST), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    bump = N(nt, "ShaderNodeBump", (300, -400), Strength=0.08, Distance=0.0003)
    fib = N(nt, "ShaderNodeTexNoise", (0, -400), Scale=300.0, Detail=2.0)
    L(nt, tc.outputs["Object"], fib.inputs[0])
    L(nt, fib.outputs[0], bump.inputs["Height"]); L(nt, bump.outputs[0], b.inputs["Normal"])
    return m

def mat_cup():
    m, nt, b = mat_nodes("M_Paper_Cup")
    tc = N(nt, "ShaderNodeTexCoord", (-1200, 0))
    sep = N(nt, "ShaderNodeSeparateXYZ", (-1000, 0)); L(nt, tc.outputs["Object"], sep.inputs[0])
    band = N(nt, "ShaderNodeMath", (-800, 100), operation='MULTIPLY')
    L(nt, ramp(nt, (-950, 200), sep.outputs[2], 0.045, 0.05), band.inputs[0])
    L(nt, ramp(nt, (-950, 50), sep.outputs[2], 0.075, 0.07), band.inputs[1])
    geo = N(nt, "ShaderNodeNewGeometry", (-1000, -250))
    # backfacing/inside = coffee residue at the bottom
    inside = N(nt, "ShaderNodeMath", (-800, -250), operation='MULTIPLY')
    L(nt, geo.outputs["Backfacing"], inside.inputs[0])
    L(nt, ramp(nt, (-950, -400), sep.outputs[2], 0.035, 0.02), inside.inputs[1])
    nz = N(nt, "ShaderNodeTexNoise", (-1000, 350), Scale=9.0, Detail=5.0)
    L(nt, tc.outputs["Object"], nz.inputs[0])
    white = mix(nt, (-600, 350), nz.outputs[0], (0.72, 0.70, 0.64, 1), (0.52, 0.47, 0.37, 1))
    c1 = mix(nt, (-400, 200), band.outputs[0], white, (0.10, 0.20, 0.33, 1))  # office blue band
    c2 = mix(nt, (-200, 200), inside.outputs[0], c1, (0.12, 0.06, 0.03, 1))
    dm = dust_mask(nt, -1300, -700, 0.5)
    L(nt, mix(nt, (100, 200), dm, c2, DUST), b.inputs["Base Color"])
    L(nt, mix(nt, (100, -100), dm, 0.55, 0.92, dtype='FLOAT'), b.inputs["Roughness"])
    return m

# ----------------------------------------------------------------- assemble
def place(ob, loc, rot=(0, 0, 0)):
    ob.location = loc; ob.rotation_euler = rot

def join(objs, name):
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name; ob.data.name = name
    return ob

def build():
    clean_scene()
    M_metal, M_liner, M_paper, M_cup = mat_metal(), mat_liner(), mat_paper(), mat_cup()

    body = build_body(); body.data.materials.append(M_metal)
    liner = build_liner(); liner.data.materials.append(M_liner)

    trash = []
    spots = [((0.02, 0.01, 0.355), 0.050), ((-0.06, 0.05, 0.345), 0.045), ((0.06, -0.04, 0.35), 0.043),
             ((-0.04, -0.06, 0.34), 0.04), ((0.05, 0.06, 0.34), 0.038), ((-0.01, -0.02, 0.405), 0.044),
             ((-0.07, -0.005, 0.335), 0.036), ((0.04, 0.03, 0.43), 0.036)]
    for k, (p, r) in enumerate(spots):
        b = crumpled_ball(f"ball{k}", r, 100 + k)
        place(b, p, (random.random() * 6, random.random() * 6, random.random() * 6))
        b.data.materials.append(M_paper); trash.append(b)
    sh = crumpled_sheet("sheet_in", 3, 0.025, 0.15, 0.2)
    place(sh, (0.03, -0.035, 0.40), (math.radians(70), math.radians(10), math.radians(25)))
    sh.data.materials.append(M_paper); trash.append(sh)
    cup = paper_cup("cup_in", 0.3)
    place(cup, (-0.035, 0.075, 0.355), (math.radians(35), math.radians(-20), 0.6))
    cup.data.materials.append(M_cup); trash.append(cup)

    bin_ob = join([body, liner] + trash, "SM_AbandonedTrashBin")

    # ---- floor spill (own asset, pivot at its centre on the floor)
    spill = []
    for k, (p, r) in enumerate([((0.0, 0.0), 0.046), ((0.17, 0.09), 0.040), ((-0.14, 0.12), 0.036),
                                ((0.30, -0.06), 0.033)]):
        b = crumpled_ball(f"sball{k}", r, 300 + k)
        place(b, (p[0], p[1], r * 0.72), (random.random() * 6, random.random() * 6, random.random() * 6))
        b.data.materials.append(M_paper); spill.append(b)
    for k, (p, rz, cr) in enumerate([((-0.05, -0.17), 0.4, 0.010), ((0.22, 0.20), -0.9, 0.018)]):
        s = crumpled_sheet(f"ssheet{k}", 20 + k, cr)
        place(s, (p[0], p[1], 0.0015), (0, 0, rz))
        s.data.materials.append(M_paper); spill.append(s)
    c2 = paper_cup("cup_floor", 0.55)
    place(c2, (0.08, -0.07, 0.033), (math.radians(90), 0, math.radians(-30)))
    c2.data.materials.append(M_cup); spill.append(c2)
    spill_ob = join(spill, "SM_TrashSpill")
    # make the spill rest on z=0
    zmin = min(v.co.z for v in spill_ob.data.vertices)
    for v in spill_ob.data.vertices: v.co.z -= zmin
    spill_ob.location = (0.48, -0.12, 0.0)

    for ob in (bin_ob, spill_ob):
        uv_unwrap(ob)
    add_collision(bin_ob)
    return bin_ob, spill_ob

def uv_unwrap(ob):
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')

def add_collision(bin_ob):
    """UCX convex hull, picked up by Unreal's FBX importer."""
    def fn(i, th):
        return [(RB, 0.0), (RT + 0.004, H + 0.006)][i]
    me = revolve("UCX", fn, 2, 12)
    ob = new_obj("UCX_SM_AbandonedTrashBin_00", me)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bm.to_mesh(me); bm.free()
    ob.display_type = 'WIRE'
    ob.parent = bin_ob
    return ob

if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    b, s = build()
    for ob in (b, s):
        print(ob.name, "verts", len(ob.data.vertices), "tris", sum(len(p.vertices) - 2 for p in ob.data.polygons),
              "dims", tuple(round(d, 3) for d in ob.dimensions))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage1.blend"))
