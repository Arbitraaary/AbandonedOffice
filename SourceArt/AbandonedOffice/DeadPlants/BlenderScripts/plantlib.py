"""Shared pieces for the dead office plants (Blender 4.2 / bpy): pots, cracked soil, dead leaves, materials."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
from nodes import mat_new, G

DUST = (0.30, 0.28, 0.25, 1)
sc = lambda: bpy.context.scene

def link(name, me, mat=None):
    ob = bpy.data.objects.new(name, me); sc().collection.objects.link(ob)
    if mat: me.materials.append(mat)
    return ob

def set_attr(me, name, value_fn):
    a = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
    for i, v in enumerate(me.vertices):
        a.data[i].value = value_fn(v)

# ----------------------------------------------------------------- materials
def granite_material():
    m, nt, b = mat_new("M_Pot_Granite"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    vor = g.n("ShaderNodeTexVoronoi", Scale=180.0); g.L(obj, vor.inputs[0])
    specks = g.rng(vor.outputs["Distance"], 0.08, 0.02)
    grey = g.rng(g.noise(obj, 90, 4), 0.55, 0.62)
    c = g.mixc(g.noise(obj, 30, 6), (0.025, 0.025, 0.027, 1), (0.05, 0.05, 0.052, 1))
    c = g.mixc(g.math('MULTIPLY', grey, 0.6), c, (0.16, 0.16, 0.16, 1))
    c = g.mixc(g.math('MULTIPLY', specks, 0.8), c, (0.55, 0.55, 0.53, 1))
    lime = g.math('MULTIPLY', g.rng(g.noise(obj, 4, 5, 0.6, mapping_scale=(14, 14, 1.2)), 0.55, 0.7),
                  g.rng(sp.outputs[2], 0.15, 0.42), True)                    # dried water run-off streaks
    c = g.mixc(g.math('MULTIPLY', lime, 0.45), c, (0.55, 0.53, 0.48, 1))
    chip = g.rng(g.math('ADD', g.rng(geo.outputs["Pointiness"], 0.5, 0.6), g.noise(obj, 40, 8)), 1.02, 1.06)
    c = g.mixc(chip, c, (0.32, 0.31, 0.3, 1))
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('ADD', g.math('MULTIPLY', up, g.rng(g.noise(obj, 16, 6), 0.3, 0.65)), 0.1, True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.8), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(lime, 0.3, 0.8); r = g.mixf(chip, r, 0.7); r = g.mixf(dust, r, 0.95)
    g.L(r, b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.15, Distance=0.0004); g.L(g.math('SUBTRACT', lime, chip), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def ceramic_material():
    m, nt, b = mat_new("M_Pot_Ceramic"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 8, 4), (0.36, 0.36, 0.355, 1), (0.42, 0.42, 0.41, 1))  # matte office grey
    drip = g.math('MULTIPLY', g.rng(g.noise(obj, 5, 5, 0.6, mapping_scale=(30, 30, 2)), 0.55, 0.7),
                  g.rng(sp.outputs[2], 0.03, 0.1), True)
    c = g.mixc(g.math('MULTIPLY', drip, 0.55), c, (0.30, 0.24, 0.17, 1))          # brown water drips
    ring = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', sp.outputs[2], 0.018)), 0.006, 0.0),
                  g.rng(g.noise(obj, 40, 4), 0.3, 0.6), True)
    c = g.mixc(g.math('MULTIPLY', ring, 0.7), c, (0.78, 0.76, 0.70, 1))           # lime ring on the saucer
    chip = g.rng(g.math('ADD', g.rng(geo.outputs["Pointiness"], 0.5, 0.6), g.noise(obj, 50, 8)), 1.12, 1.16)
    c = g.mixc(chip, c, (0.40, 0.33, 0.27, 1))                                    # chipped glaze -> terracotta
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('ADD', g.math('MULTIPLY', up, g.rng(g.noise(obj, 25, 6), 0.3, 0.65)), 0.08, True)
    c = g.mixc(g.math('MULTIPLY', dust, 0.8), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(drip, 0.45, 0.75); r = g.mixf(chip, r, 0.9); r = g.mixf(dust, r, 0.95)
    g.L(r, b.inputs["Roughness"])
    return m

def soil_material():
    m, nt, b = mat_new("M_Soil"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    vor = g.n("ShaderNodeTexVoronoi", Scale=38.0, feature='DISTANCE_TO_EDGE'); g.L(obj, vor.inputs[0])
    crack = g.rng(vor.outputs["Distance"], 0.03, 0.0)
    c = g.mixc(g.noise(obj, 25, 8, 0.7), (0.018, 0.016, 0.014, 1), (0.05, 0.04, 0.03, 1))
    dry = g.rng(g.noise(obj, 12, 6), 0.55, 0.7)                                   # dried, greyish crust
    c = g.mixc(g.math('MULTIPLY', dry, 0.6), c, (0.12, 0.11, 0.10, 1))
    c = g.mixc(crack, c, (0.004, 0.004, 0.004, 1))
    vp = g.n("ShaderNodeTexVoronoi", Scale=260.0); g.L(obj, vp.inputs[0])
    perl = g.math('MULTIPLY', g.rng(vp.outputs["Distance"], 0.06, 0.02), g.rng(g.noise(obj, 30, 3), 0.55, 0.6), True)
    c = g.mixc(perl, c, (0.55, 0.54, 0.5, 1))                                     # a few perlite grains
    g.L(c, b.inputs["Base Color"])
    g.L(g.mixf(perl, 0.95, 0.7), b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.6, Distance=0.002)
    g.L(g.math('SUBTRACT', g.noise(obj, 120, 6), g.math('MULTIPLY', crack, 1.5)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def leaf_material():
    """dead leaves: per-leaf 'rnd' attribute, LeafUV (u along leaf, v across)"""
    m, nt, b = mat_new("M_DeadLeaf"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="LeafUV")
    sep = g.n("ShaderNodeSeparateXYZ"); g.L(uvn.outputs[0], sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]
    rnd = g.n("ShaderNodeAttribute", attribute_name="rnd").outputs["Fac"]
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    # natural, desaturated dead-leaf palette: grey-brown / straw / dark umber, mottled
    mott = g.noise(obj, 35, 6, 0.65)
    dark = (0.038, 0.025, 0.014, 1); greyb = (0.13, 0.092, 0.058, 1); straw = (0.26, 0.19, 0.105, 1)
    base = g.mixc(g.rng(rnd, 0.0, 0.55), dark, greyb)
    base = g.mixc(g.rng(rnd, 0.55, 1.0), base, straw)
    base = g.mixc(g.math('MULTIPLY', g.rng(mott, 0.35, 0.75), 0.6), base, greyb)        # blotchy drying
    olive = g.math('MULTIPLY', g.rng(rnd, 0.85, 1.0), g.rng(u, 0.35, 0.05), True)
    c = g.mixc(g.math('MULTIPLY', olive, 0.6), base, (0.16, 0.15, 0.08, 1))            # last trace of green
    tip = g.math('MULTIPLY', g.rng(u, 0.75, 1.0), g.rng(g.noise(obj, 25, 4), 0.3, 0.7), True)
    edge = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', v, 0.5)), 0.38, 0.5), 0.5)
    c = g.mixc(g.math('MAXIMUM', tip, edge), c, (0.06, 0.045, 0.03, 1))                # dried, darker margins/tip
    vein = g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', v, 0.5)), 0.025, 0.0)
    c = g.mixc(g.math('MULTIPLY', vein, 0.2), c, (0.30, 0.25, 0.18, 1))
    spots = g.rng(g.noise(obj, 70, 5), 0.64, 0.7)
    c = g.mixc(g.math('MULTIPLY', spots, 0.4), c, (0.05, 0.04, 0.03, 1))
    dust = g.rng(g.noise(obj, 20, 5), 0.45, 0.8)
    c = g.mixc(g.math('MULTIPLY', dust, 0.15), c, DUST)
    g.L(c, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.68
    bump = g.n("ShaderNodeBump", Strength=0.35, Distance=0.0006)
    g.L(g.math('ADD', g.noise(obj, 260, 6), g.math('MULTIPLY', vein, 0.3)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def bark_material(name="M_DeadCane", dark=1.0):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    wave = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z', Scale=22.0, Distortion=3.0)
    g.L(obj, wave.inputs[0])
    rings = g.rng(wave.outputs["Fac"], 0.92, 1.0)
    c = g.mixc(g.noise(obj, 40, 6), (0.16 * dark, 0.13 * dark, 0.10 * dark, 1), (0.24 * dark, 0.20 * dark, 0.15 * dark, 1))
    c = g.mixc(g.math('MULTIPLY', rings, 0.7), c, (0.07, 0.055, 0.04, 1))
    stripes = g.rng(g.noise(obj, 6, 4, 0.5, mapping_scale=(80, 80, 3)), 0.55, 0.7)
    c = g.mixc(g.math('MULTIPLY', stripes, 0.4), c, (0.33 * dark, 0.29 * dark, 0.23 * dark, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump = g.n("ShaderNodeBump", Strength=0.5, Distance=0.001)
    g.L(g.math('ADD', rings, g.math('MULTIPLY', stripes, 0.5)), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

# ----------------------------------------------------------------- geometry
def revolve(name, prof, mat, segs=48, deform=None, smooth=True):
    bm = bmesh.new(); rings = []
    for j in range(segs):
        th = 2 * math.pi * j / segs
        col = []
        for i, (r, z) in enumerate(prof):
            if deform: r, z = deform(i, th, r, z)
            col.append(bm.verts.new((r * math.cos(th), r * math.sin(th), z)))
        rings.append(col)
    for j in range(segs):
        A, B = rings[j], rings[(j + 1) % segs]
        for i in range(len(prof) - 1):
            bm.faces.new((A[i], B[i], B[i + 1], A[i + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    return link(name, me, mat)

def soil_disc(name, radius, z, mat, rings=14, segs=56, gap=0.004, seed=1):
    """dry soil: shrunk away from the pot wall, cracked, slightly uneven"""
    bm = bmesh.new()
    centre = bm.verts.new((0, 0, z))
    grid = []
    for i in range(1, rings + 1):
        rr = (radius - gap) * i / rings
        row = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            p = Vector((rr * math.cos(th), rr * math.sin(th), 0))
            h = 0.006 * noise.noise(p * 18 + Vector((seed, 0, 0))) + 0.003 * noise.noise(p * 50)
            h -= 0.008 * (i / rings) ** 6                                     # sinks at the edge
            row.append(bm.verts.new((p.x, p.y, z + h)))
        grid.append(row)
    for j in range(segs):
        bm.faces.new((centre, grid[0][j], grid[0][(j + 1) % segs]))
    for i in range(rings - 1):
        for j in range(segs):
            a, b2 = grid[i][j], grid[i][(j + 1) % segs]
            bm.faces.new((a, grid[i + 1][j], grid[i + 1][(j + 1) % segs], b2))
    # outer lip turning down into the gap
    lip = [bm.verts.new((v.co.x * 1.0, v.co.y * 1.0, v.co.z - 0.03)) for v in grid[-1]]
    for j in range(segs):
        bm.faces.new((grid[-1][j], lip[j], lip[(j + 1) % segs], grid[-1][(j + 1) % segs]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return link(name, me, mat)

def leaf(name, root, direction, length, width, mat, seed, droop=1.4, curl=0.6, twist=0.8,
         shape="strap", seg_u=12, broken_at=None, petiole=0.0, thickness=0.0005):
    """Builds one dead leaf as a bent strip.  direction: initial unit vector.  droop: radians of
    downward bending accumulated along the leaf.  curl: cross-section fold.  shape: 'strap' | 'ellipse'."""
    rnd = random.Random(seed)
    d = Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-3: side = Vector((1, 0, 0))
    side.normalize()
    pts, sides, ups = [], [], []
    p = Vector(root); cur = d.copy()
    n_seg = seg_u
    ds = length / n_seg
    tw_total = rnd.uniform(-twist, twist)
    for k in range(n_seg + 1):
        s = k / n_seg
        pts.append(p.copy())
        # width direction rotates (twist) around the current direction
        sd = (side - cur * side.dot(cur)).normalized()
        q = Matrix.Rotation(tw_total * s, 3, cur)
        sd = (q @ sd).normalized()
        sides.append(sd); ups.append(cur.cross(sd).normalized())
        if broken_at is not None and s > broken_at:
            cur = (cur * 0.3 + Vector((0, 0, -1)) * 0.7).normalized()      # snapped: hangs straight down
        else:
            ax = cur.cross(Vector((0, 0, 1)))
            if ax.length > 1e-4:
                cur = (Matrix.Rotation(-droop / n_seg * (0.4 + 1.2 * s), 3, ax.normalized()) @ cur).normalized()
        p = p + cur * ds
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("LeafUV")
    rows = []
    across = [-1.0, -0.5, 0.0, 0.5, 1.0]
    for k, (pt, sd, up) in enumerate(zip(pts, sides, ups)):
        s = k / n_seg
        if petiole and s < petiole:
            w = width * 0.06
        else:
            ss = (s - petiole) / (1 - petiole) if petiole else s
            if shape == "strap":
                w = width * (min(1.0, ss * 6) ** 0.5) * (1 - ss ** 3) + width * 0.03
            elif shape == "heart":
                w = width * (math.sin(math.pi * min(1.0, ss)) ** 0.45) * (1.25 - 0.75 * ss) + width * 0.02
            else:
                w = width * math.sin(math.pi * min(1.0, ss)) ** 0.7 + width * 0.02
        crisp = 1.0 + 0.25 * noise.noise(Vector((s * 9, seed, 0)))          # ragged, shrivelled edges
        row = []
        for a in across:
            fold = curl * w * 0.6 * abs(a) ** 1.5                            # edges curl upward/inward
            off = sd * (a * w * 0.5 * crisp) + up * fold
            row.append(bm.verts.new(pt + off))
        rows.append(row)
    for k in range(n_seg):
        for i in range(len(across) - 1):
            f = bm.faces.new((rows[k][i], rows[k + 1][i], rows[k + 1][i + 1], rows[k][i + 1]))
            for l in f.loops:
                kk = k + (1 if l.vert in rows[k + 1] else 0)
                ii = i + (1 if l.vert in (rows[k][i + 1], rows[k + 1][i + 1]) else 0)
                l[uvl].uv = (kk / n_seg, (across[ii] + 1) / 2)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = link(name, me, mat)
    if thickness:
        md = ob.modifiers.new("s", 'SOLIDIFY'); md.thickness = thickness; md.offset = 0.0
        with bpy.context.temp_override(object=ob, active_object=ob): bpy.ops.object.modifier_apply(modifier="s")
    val = rnd.random()
    set_attr(ob.data, "rnd", lambda v: val)
    return ob

def tube(name, pts, radius, mat, segs=10, taper=0.15):
    """simple swept tube along points (canes, stems)"""
    bm = bmesh.new(); rings = []
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        a = t.cross(Vector((1, 0, 0)));
        if a.length < 1e-3: a = t.cross(Vector((0, 1, 0)))
        a.normalize(); b2 = t.cross(a)
        r = radius * (1 - taper * k / (len(pts) - 1))
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b2 * math.sin(2 * math.pi * j / segs)) * r)
                      for j in range(segs)])
    for k in range(len(pts) - 1):
        for j in range(segs):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % segs], rings[k + 1][(j + 1) % segs], rings[k + 1][j]))
    bm.faces.new(rings[-1][::-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = link(name, me, mat)
    lay = me.uv_layers.new(name="LeafUV")
    set_attr(me, "rnd", lambda v: 0.5)
    return ob

def finalize(parts):
    for ob in parts:
        if "LeafUV" not in ob.data.uv_layers: ob.data.uv_layers.new(name="LeafUV")
        if "rnd" not in ob.data.attributes: set_attr(ob.data, "rnd", lambda v: 0.0)

def keep_outside_pot(ob, wall_r, rim_r, rim_z, soil_r, soil_z, margin=0.003):
    """Pushes leaf vertices out of the pot: over the rim, outside the tapered wall, above the soil."""
    for v in ob.data.vertices:
        x, y, z = v.co
        r = math.hypot(x, y) + 1e-9
        if z < rim_z + margin and r < rim_r + margin and r > soil_r - 0.012:
            if z > rim_z - 0.02:                     # lying across the rim -> lift onto it
                v.co.z = rim_z + margin
            else:                                     # beside the wall -> push out
                k = (max(rim_r, wall_r(z)) + margin) / r
                v.co.x, v.co.y = x * k, y * k
        elif r <= soil_r - 0.012 and z < soil_z + 0.002:
            v.co.z = soil_z + 0.002 + 0.002 * (soil_z - z > 0)
        elif r > rim_r and z < rim_z:
            wr = wall_r(z) + margin
            if r < wr:
                k = wr / r; v.co.x, v.co.y = x * k, y * k
