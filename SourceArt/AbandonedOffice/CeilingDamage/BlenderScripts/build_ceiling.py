"""Ceiling damage kit for the abandoned office (suspended 600x600 mineral-fibre ceiling).
python3.11 build_ceiling.py -> out/stage.blend
Every part carries 'asset' (final mesh name), 'ofs' (stage offset) and optionally 'hull' (collision group).
  SM_CeilingHole_Hanging  pivot = ceiling surface, cell centre; everything hangs below z=0
  SM_CeilingHole_Cables   same, half the tile still in place, lots of cables + a flexible conduit
  SM_CeilingTiles_Fallen  pivot = floor; a sagged whole tile, a tile broken in 3, crumbs
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, noise
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nodes import mat_new, G
import common as C

bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = random.Random(52)
DUST = C.DUST
S = 0.2975                     # half size of a tile (595 mm)
CELL = 0.30                    # half grid pitch (600 mm)
FL_Z0, FL_Z1 = -0.006, -0.0045 # T-bar flange (visible face flush with the ceiling)
TILE_T = 0.015

# ================================================================= materials
def stains(g, obj, c, scale, tint_in, tint_ring):
    s = g.noise(obj, scale, 2, 0.5)
    inside = g.rng(s, 0.56, 0.66)
    ring = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', s, 0.57)), 0.022, 0.0),
                  g.rng(g.noise(obj, 9, 3), 0.35, 0.6), True)
    c = g.mixc(g.math('MULTIPLY', inside, 0.5), c, tint_in)
    c = g.mixc(g.math('MULTIPLY', ring, 0.45), c, tint_ring)
    return c, inside

def tile_face():
    m, nt, b = mat_new("M_CeilTile_Face"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 6, 4), (0.56, 0.545, 0.50, 1), (0.64, 0.625, 0.58, 1))
    fn = g.noise(obj, 42, 3, 0.5)                                            # worm-like fissures
    fiss = g.math('MULTIPLY', g.rng(g.math('ABSOLUTE', g.math('SUBTRACT', fn, 0.5)), 0.011, 0.0),
                  g.rng(g.noise(obj, 22, 2), 0.42, 0.58), True)
    vor = g.n("ShaderNodeTexVoronoi", Scale=170.0); g.L(obj, vor.inputs[0])  # pinholes
    holes = g.math('MULTIPLY', g.rng(vor.outputs["Distance"], 0.16, 0.07), 0.8)
    pits = g.math('MAXIMUM', fiss, holes)
    c = g.mixc(g.math('MULTIPLY', pits, 0.9), c, (0.22, 0.21, 0.19, 1))
    c, wet = stains(g, obj, c, 2.2, (0.52, 0.42, 0.27, 1), (0.36, 0.25, 0.12, 1))
    grime = g.rng(g.noise(obj, 14, 6), 0.5, 0.78)
    c = g.mixc(g.math('MULTIPLY', grime, 0.45), c, (0.30, 0.27, 0.22, 1))
    g.L(c, b.inputs["Base Color"]); g.L(g.mixf(wet, 0.9, 0.82), b.inputs["Roughness"])
    bump = g.n("ShaderNodeBump", Strength=0.45, Distance=0.0015)
    g.L(g.math('ADD', g.math('MULTIPLY', pits, -1.0), g.math('MULTIPLY', g.noise(obj, 260, 3), 0.3)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def tile_back():
    m, nt, b = mat_new("M_CeilTile_Back"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 90, 7, 0.7), (0.22, 0.18, 0.13, 1), (0.36, 0.30, 0.22, 1))
    c, wet = stains(g, obj, c, 2.6, (0.30, 0.22, 0.13, 1), (0.22, 0.15, 0.08, 1))
    dust = g.rng(g.noise(obj, 9, 5), 0.35, 0.7)
    c = g.mixc(g.math('MULTIPLY', dust, 0.35), c, DUST)
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump = g.n("ShaderNodeBump", Strength=0.5, Distance=0.002)
    g.L(g.noise(obj, 220, 6, 0.7), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def tile_core():
    m, nt, b = mat_new("M_CeilTile_Core"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 140, 6, 0.7), (0.50, 0.47, 0.42, 1), (0.68, 0.65, 0.59, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.97
    bump = g.n("ShaderNodeBump", Strength=0.8, Distance=0.003)
    g.L(g.noise(obj, 160, 6, 0.75), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def void_mat():
    m, nt, b = mat_new("M_CeilVoid"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 4, 4), (0.008, 0.008, 0.007, 1), (0.035, 0.032, 0.028, 1))
    duct = g.rng(g.noise(obj, 3, 2, 0.4, mapping_scale=(1, 8, 1)), 0.55, 0.6)   # faint shapes up in the dark
    c = g.mixc(g.math('MULTIPLY', duct, 0.5), c, (0.05, 0.05, 0.048, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    return m

M_FACE, M_BACK, M_CORE = tile_face(), tile_back(), tile_core()
TILE_MATS = [M_FACE, M_BACK, M_CORE]
M_VOID = void_mat()
M_TBAR = C.painted("M_TBar", (0.62, 0.62, 0.60, 1), primer=(0.45, 0.46, 0.47, 1), chip_amt=0.05, rough=0.4, rust=0.25)
M_WEB = C.plain("M_TBarWeb", (0.48, 0.49, 0.5, 1), 0.45, 0.9, 0.5)
M_WIRE = C.plain("M_HangerWire", (0.42, 0.42, 0.42, 1), 0.5, 1.0, 0.5)
M_CU = C.plain("M_Copper", (0.62, 0.30, 0.14, 1), 0.35, 1.0, 0.4)
SHEATH = {"grey": C.plain("M_Cable_Grey", (0.30, 0.30, 0.30, 1), 0.55, 0.0, 0.4),
          "white": C.plain("M_Cable_White", (0.55, 0.55, 0.53, 1), 0.5, 0.0, 0.5),
          "black": C.plain("M_Cable_Black", (0.02, 0.02, 0.02, 1), 0.6, 0.0, 0.4),
          "blue": C.plain("M_Cable_Blue", (0.03, 0.10, 0.32, 1), 0.5, 0.0, 0.4)}
CORES = [C.plain("M_Core_Brown", (0.16, 0.07, 0.03, 1), 0.4, 0.0, 0.2),
         C.plain("M_Core_Blue", (0.03, 0.08, 0.30, 1), 0.4, 0.0, 0.2),
         C.plain("M_Core_YG", (0.32, 0.36, 0.03, 1), 0.4, 0.0, 0.2)]
M_CONDUIT = C.plain("M_Conduit", (0.13, 0.13, 0.125, 1), 0.6, 0.0, 0.5)

# ================================================================= helpers
ASSETS = {}
def part(asset, ob, hull=None):
    ob["asset"] = asset
    if hull: ob["hull"] = hull
    ASSETS.setdefault(asset, []).append(ob)
    return ob
def B(asset, *a, hull=None, **k): return part(asset, C.box(*a, **k), hull)

def tile_slots(ob):
    """face (-Z) = 0, back (+Z) = 1, broken/cut edges = 2, judged before any deformation"""
    for p in ob.data.polygons:
        p.material_index = 0 if p.normal.z < -0.7 else (1 if p.normal.z > 0.7 else 2)

def jag_outline(corners, broken, step=0.011, amp=0.006):
    """corners CCW; broken[i] -> edge corners[i]->corners[i+1] is a torn edge"""
    out = []
    for i, a in enumerate(corners):
        b2 = corners[(i + 1) % len(corners)]
        a, b2 = Vector(a), Vector(b2)
        out.append(a)
        if broken[i]:
            d = b2 - a; L = d.length; n = Vector((d.y, -d.x)).normalized()
            k = max(1, int(L / step))
            for j in range(1, k):
                t = j / k
                off = amp * (noise.noise(Vector((t * L * 40, i * 3.3, rnd.random() * 0.3))) * 1.6 + rnd.uniform(-0.6, 0.6))
                out.append(a + d * t + n * off)
    return out

def slab(asset, name, outline, thick, z0=0.0, hull=None):
    """flat piece of tile from a 2D outline: bottom (face) at z0, top (back) at z0+thick, edges = core"""
    pts = [Vector(p) for p in outline]
    area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))
    if area < 0: pts.reverse()
    tb = bmesh.new(); vs = [tb.verts.new((p.x, p.y, 0)) for p in pts]
    es = [tb.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    bmesh.ops.triangle_fill(tb, use_beauty=True, use_dissolve=False, edges=es)
    tb.verts.index_update()
    tris = [[v.index for v in f.verts] for f in tb.faces]; tb.free()
    bm = bmesh.new(); n = len(pts)
    bot = [bm.verts.new((p.x, p.y, z0)) for p in pts]; top = [bm.verts.new((p.x, p.y, z0 + thick)) for p in pts]
    for t in tris:
        a, b2, c = t
        e1 = pts[b2] - pts[a]; e2 = pts[c] - pts[a]
        if e1.x * e2.y - e1.y * e2.x > 0: a, c = c, a          # bottom must face -Z
        bm.faces.new((bot[a], bot[b2], bot[c])); bm.faces.new((top[c], top[b2], top[a]))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = C.link(name, me, TILE_MATS); tile_slots(ob)
    for p in me.polygons: p.use_smooth = False
    return part(asset, ob, hull)

def grid_tile(asset, name, cuts=10, hull=None):
    ob = B(asset, name, -S, S, -S, S, 0.0, TILE_T, TILE_MATS, cuts=cuts, hull=hull)
    tile_slots(ob); return ob

def tube(asset, name, pts, r, mat, segs=8, cap_end=True, rfun=None):
    bm = bmesh.new(); rings = []; prev_a = None
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        if prev_a is None:
            a = t.cross(Vector((0, 0, 1)))
            if a.length < 1e-3: a = t.cross(Vector((1, 0, 0)))
        else:
            a = prev_a - t * prev_a.dot(t)                       # parallel transport -> no twisting
        a.normalize(); prev_a = a; b2 = t.cross(a)
        rr = r * (rfun(k) if rfun else 1.0)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b2 * math.sin(2 * math.pi * j / segs)) * rr) for j in range(segs)])
    for k in range(len(pts) - 1):
        for j in range(segs):
            bm.faces.new((rings[k][j], rings[k][(j + 1) % segs], rings[k + 1][(j + 1) % segs], rings[k + 1][j]))
    if cap_end: bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = C.link(name, me, mat)
    for p in me.polygons: p.use_smooth = True
    return part(asset, ob)

def spline(ctrl, n=10):
    P = [ctrl[0]] + ctrl + [ctrl[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1]); return out

def cable(asset, name, ctrl, r, colour, stripped=True):
    pts = spline([Vector(c) for c in ctrl], 6)
    tube(asset, name, pts, r, SHEATH[colour], 8, cap_end=True)
    if not stripped: return
    end = pts[-1]; t = (pts[-1] - pts[-2]).normalized()
    a = t.cross(Vector((0, 0, 1)))
    if a.length < 1e-3: a = t.cross(Vector((1, 0, 0)))
    a.normalize(); b2 = t.cross(a)
    for k, cm in enumerate(CORES):                              # three insulated cores, splayed, copper ends
        ang = 2 * math.pi * k / 3 + rnd.uniform(-0.3, 0.3)
        side = (a * math.cos(ang) + b2 * math.sin(ang))
        L = rnd.uniform(0.03, 0.055)
        p0 = end - t * 0.004 + side * r * 0.45
        p1 = p0 + t * L * 0.5 + side * 0.004
        p2 = p0 + t * L + side * rnd.uniform(0.006, 0.014)
        cp = spline([p0, p1, p2], 4)
        tube(asset, f"{name}_Core{k}", cp, r * 0.36, cm, 6)
        d = (p2 - p1).normalized()
        cu = [p2 - d * 0.001, p2 + d * 0.006 + side * 0.002, p2 + d * 0.012 + side * rnd.uniform(0.002, 0.006)]
        tube(asset, f"{name}_Cu{k}", cu, r * 0.2, M_CU, 5)

def hang_ctrl(start, drop, out_dir, spill=0.12, amp=0.05):
    """cable spilling out of the plenum: short horizontal arc, then hanging with lazy S-curves and a curled tip"""
    sx, sy = start; ox, oy = out_dir; ph = rnd.uniform(0, 6.28)
    pts = [(sx, sy, 0.02), (sx, sy, -0.01), (sx + ox * spill * 0.6, sy + oy * spill * 0.6, -0.05),
           (sx + ox * spill, sy + oy * spill, -0.13)]
    n = 5
    for i in range(1, n + 1):
        t = i / n
        z = -0.13 - (drop - 0.13) * t
        lat = amp * math.sin(ph + t * 4.0) * (0.4 + 0.6 * t)
        pts.append((sx + ox * spill * (1 + 0.25 * t) - oy * lat, sy + oy * spill * (1 + 0.25 * t) + ox * lat, z))
    lx, ly, lz = pts[-1]; cu = rnd.uniform(0.04, 0.08); a = rnd.uniform(0, 6.28)
    pts.append((lx + math.cos(a) * cu, ly + math.sin(a) * cu, lz - 0.03))       # curled tip
    return pts

def tbar(asset, name, x0, x1, y, along='X', mat_f=M_TBAR):
    """main tee: flange 24 mm, web 4 mm going up (hidden unless the bar drops)"""
    if along == 'X':
        f = B(asset, name + "_F", x0, x1, y - 0.012, y + 0.012, FL_Z0, FL_Z1, mat_f)
        w = B(asset, name + "_W", x0, x1, y - 0.002, y + 0.002, FL_Z1, 0.03, M_WEB)
    else:
        f = B(asset, name + "_F", y - 0.012, y + 0.012, x0, x1, FL_Z0, FL_Z1, mat_f)
        w = B(asset, name + "_W", y - 0.002, y + 0.002, x0, x1, FL_Z1, 0.03, M_WEB)
    return [f, w]

def rotate_parts(parts, axis_pt, mat):
    for o in parts:
        for v in o.data.vertices: v.co = mat @ (v.co - axis_pt) + axis_pt

def void_and_frame(asset, broken_bar):
    B(asset, f"{asset}_Void", -CELL, CELL, -CELL, CELL, -0.0022, -0.0008, M_VOID)
    E = CELL + 0.012
    tbar(asset, f"{asset}_TeeS", -E, E, -CELL)
    tbar(asset, f"{asset}_TeeW", -E, E, -CELL, along='Y')
    tbar(asset, f"{asset}_TeeE", -E, E, CELL, along='Y')
    if broken_bar:
        # north tee snapped at x = 0.04: west half sags a little, east half hangs from the cross tee
        wpart = tbar(asset, f"{asset}_TeeN_A", -E, 0.04, CELL)
        rotate_parts(wpart, Vector((-E, CELL, FL_Z0)), Matrix.Rotation(math.radians(3.5), 3, 'Y'))
        epart = tbar(asset, f"{asset}_TeeN_B", 0.055, E, CELL)
        for o in epart:                                         # jagged torn end
            for v in o.data.vertices:
                if v.co.x < 0.06: v.co.x += rnd.uniform(-0.006, 0.006)
        rotate_parts(epart, Vector((E, CELL, FL_Z0)), Matrix.Rotation(math.radians(-48), 3, 'Y') @ Matrix.Rotation(math.radians(6), 3, 'X'))
        free_end = Matrix.Rotation(math.radians(-48), 3, 'Y') @ (Vector((0.055, CELL, FL_Z0)) - Vector((E, CELL, FL_Z0))) + Vector((E, CELL, FL_Z0))
        mid = (free_end + Vector((E, CELL, 0))) * 0.5 + Vector((0, 0, -0.01))
        # bent hanger wire still hooked through the tee
        tube(asset, f"{asset}_Hanger", spline([Vector((0.16, CELL - 0.004, 0.01)), Vector((0.165, CELL - 0.002, -0.03)),
                                                  mid + Vector((0.0, 0.0, 0.02)), mid + Vector((0.004, 0.0, -0.004))], 8), 0.0011, M_WIRE, 5)
    else:
        tn = tbar(asset, f"{asset}_TeeN", -E, E, CELL)
        rotate_parts(tn, Vector((-E, CELL, FL_Z0)), Matrix.Rotation(math.radians(1.2), 3, 'Y'))

def remnant(asset, name, corners, broken, hull=None):
    """piece of tile still lying on the flanges: face at z = flange top"""
    return slab(asset, name, jag_outline(corners, broken), TILE_T, FL_Z1, hull)

# ================================================================= SM_CeilingHole_Hanging
A = "SM_CeilingHole_Hanging"
void_and_frame(A, broken_bar=True)
remnant(A, "H_RemS", [(-0.2, -S), (0.22, -S), (0.18, -S + 0.035), (0.02, -S + 0.06), (-0.12, -S + 0.03)], [0, 1, 1, 1, 1])
remnant(A, "H_RemSE", [(0.13, -S), (S, -S), (S, -0.08), (S - 0.05, -0.15), (0.2, -S + 0.07)], [0, 0, 1, 1, 1])
remnant(A, "H_RemNW", [(-S, 0.2), (-0.17, 0.27), (-0.08, S), (-S, S)], [1, 1, 0, 0])
# the tile that came loose on its east side and swung down on the west edge
ht = grid_tile(A, "H_Tile", cuts=20, hull="Tile")
bite_c = Vector((S, -S))
la, lb = Vector((S - 0.2, -S)), Vector((S, -S + 0.12))                # crack line cutting the corner off
ld = (lb - la).normalized(); ln = Vector((ld.y, -ld.x))                 # ln points into the lost corner
for v in ht.data.vertices:                                     # broken south-east corner
    p2 = Vector((v.co.x, v.co.y)); t = (p2 - la).dot(ld)
    jag = 0.012 * noise.noise(Vector((t * 30, 0.3, 0.7))) + 0.005 * math.sin(t * 160) - 0.01
    if (p2 - la).dot(ln) > jag:
        q = la + ld * t + ln * jag
        v.co.x, v.co.y = q.x, q.y
for p in ht.data.polygons:                                     # the squeezed corner faces become torn edge
    if all((Vector((ht.data.vertices[i].co.x, ht.data.vertices[i].co.y)) - la).dot(ln) > -0.03 for i in p.vertices) and abs(p.normal.z) < 0.7:
        p.material_index = 2
hinge_x = -CELL + 0.016
for v in ht.data.vertices:
    u = v.co.x + S                                             # 0 .. 0.595 from the hinge
    w = (v.co.y + S) / (2 * S)                                 # 0 .. 1 along the hinge
    sag = -0.035 * math.sin(math.pi * w) * math.sin(math.pi * min(1.0, u / (2 * S)) * 0.9) - 0.012 * (u / (2 * S)) ** 2
    co = Vector((u, v.co.y, v.co.z + sag))
    ang = math.radians(66 - 9 * w)                             # twisted: one end hangs lower
    co = Matrix.Rotation(ang, 3, 'Y') @ co
    v.co = co + Vector((hinge_x, 0, FL_Z1 - 0.002))
for k, (col, r, start, sway, drop) in enumerate([
        ("grey", 0.0055, (0.12, 0.05), (0.05, -0.03), 1.25),
        ("black", 0.0045, (0.16, 0.09), (-0.03, 0.04), 0.95),
        ("blue", 0.004, (0.08, 0.12), (0.06, 0.05), 1.1),
        ("white", 0.005, (0.2, -0.02), (0.02, -0.06), 0.75)]):
    d = Vector(sway).normalized()
    ctrl = hang_ctrl(start, drop, (d.x, d.y), spill=rnd.uniform(0.06, 0.14))
    cable(A, f"H_Cable{k}", ctrl, r, col, stripped=(k != 2))
# loop of cable sagging out of the ceiling
cable(A, "H_CableLoop", [(0.24, -0.12, 0.02), (0.24, -0.12, -0.04), (0.17, -0.06, -0.33), (0.06, 0.0, -0.38),
                         (-0.01, 0.06, -0.2), (-0.03, 0.1, -0.03), (-0.03, 0.1, 0.02)], 0.005, "grey", stripped=False)

# ================================================================= SM_CeilingHole_Cables
Bn = "SM_CeilingHole_Cables"
void_and_frame(Bn, broken_bar=False)
# north half of the tile still in place, broken across the middle
remnant(Bn, "C_RemN", [(-S, 0.03), (-0.15, -0.02), (0.02, 0.06), (0.14, -0.04), (S, 0.0), (S, S), (-S, S)], [1, 1, 1, 1, 0, 0, 0])
remnant(Bn, "C_RemSW", [(-S, -S), (-0.12, -S), (-0.2, -S + 0.05), (-S + 0.04, -0.17)], [0, 1, 1, 0])
remnant(Bn, "C_RemE", [(S - 0.04, -0.2), (S, -0.24), (S, -0.04), (S - 0.03, -0.09)], [1, 0, 1, 1])
cab = [("grey", 0.006, (-0.1, -0.12), (-0.04, -0.05), 1.4),
       ("black", 0.0045, (-0.05, -0.15), (0.06, -0.02), 1.05),
       ("white", 0.005, (0.05, -0.1), (0.08, 0.04), 0.85),
       ("blue", 0.004, (0.0, -0.2), (-0.02, -0.07), 1.2),
       ("blue", 0.004, (0.02, -0.21), (0.05, -0.08), 1.15),
       ("grey", 0.0045, (0.15, -0.18), (0.03, 0.02), 0.6)]
for k, (col, r, start, sway, drop) in enumerate(cab):
    d = Vector(sway).normalized()
    ctrl = hang_ctrl(start, drop, (d.x, d.y), spill=rnd.uniform(0.06, 0.16))
    cable(Bn, f"C_Cable{k}", ctrl, r, col, stripped=(k not in (3, 4)))
cable(Bn, "C_CableLoop", [(-0.22, -0.22, 0.02), (-0.22, -0.22, -0.04), (-0.15, -0.14, -0.45), (-0.02, -0.06, -0.5),
                          (0.12, -0.1, -0.3), (0.2, -0.2, -0.04), (0.2, -0.2, 0.02)], 0.0055, "black", stripped=False)
# corrugated flexible conduit drooping out in an arc, torn open at the end
cp = spline([Vector((0.22, -0.05, 0.02)), Vector((0.22, -0.05, -0.04)), Vector((0.24, -0.12, -0.3)),
             Vector((0.18, -0.22, -0.55)), Vector((0.1, -0.24, -0.66))], 30)
dense = []
for i in range(len(cp) - 1):                                   # resample ~2.5 mm for the ribs
    a, b2 = cp[i], cp[i + 1]; k = max(1, int((b2 - a).length / 0.0025))
    dense += [a + (b2 - a) * (j / k) for j in range(k)]
dense.append(cp[-1])
tube(Bn, "C_Conduit", dense, 0.011, M_CONDUIT, 10, cap_end=False, rfun=lambda k: 1.0 + 0.13 * (0.5 + 0.5 * math.sin(k * 2 * math.pi / 3)))
cend = dense[-1]; cdir = (dense[-1] - dense[-2]).normalized()
for k, cm in enumerate(CORES):                                 # single cores poking out of the conduit
    side = Vector((math.cos(k * 2.1), math.sin(k * 2.1), 0)) * 0.004
    p0 = cend - cdir * 0.02 + side
    cp2 = spline([p0, p0 + cdir * 0.05 + side * 1.5, p0 + cdir * 0.09 + side * 3 + Vector((0, 0, -0.02))], 5)
    tube(Bn, f"C_ConduitCore{k}", cp2, 0.0016, cm, 6)
    tube(Bn, f"C_ConduitCu{k}", [cp2[-1], cp2[-1] + (cp2[-1] - cp2[-2]).normalized() * 0.01], 0.0009, M_CU, 5)
# dark inner face of the conduit end
CY = C.cyl(f"C_ConduitIn", tuple(cend - cdir * 0.002), 0.0105, 0.001, M_VOID, segs=10)
rot = cdir.to_track_quat('Z', 'Y').to_matrix()
for v in CY.data.vertices: v.co = rot @ (v.co - (cend - cdir * 0.002)) + (cend - cdir * 0.002)
part(Bn, CY)

# ================================================================= SM_CeilingTiles_Fallen
F = "SM_CeilingTiles_Fallen"
def place(objs, yaw, pos, tilt=(0.0, 0.0), flip=False):
    m = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(tilt[0]), 3, 'X') @ Matrix.Rotation(math.radians(tilt[1]), 3, 'Y')
    if flip: m = m @ Matrix.Rotation(math.pi, 3, 'X')
    for o in objs:
        for v in o.data.vertices: v.co = m @ v.co
    zmin = min(v.co.z for o in objs for v in o.data.vertices)
    for o in objs:
        for v in o.data.vertices: v.co += Vector((pos[0], pos[1], -zmin + pos[2]))
# whole tile, sagged from water: lies face up, middle touching the floor, edges lifted
wt = grid_tile(F, "F_TileWhole", cuts=12, hull="Whole")
for v in wt.data.vertices:
    r2 = (v.co.x ** 2 + v.co.y ** 2) / (2 * S * S)
    v.co.z -= 0.03 * r2 + 0.006 * noise.noise(Vector((v.co.x * 6, v.co.y * 6, 1.3)))
place([wt], 14, (-0.16, 0.08, 0.0), flip=True)
# tile broken in three
c0 = Vector((0.05, -0.03)); e1 = (-0.1, -S); e2 = (S, 0.15); e3 = (-S, 0.2)
pieces = [([e1, (S, -S), e2, tuple(c0)], [0, 0, 1, 1]),
          ([e2, (S, S), (-S, S), e3, tuple(c0)], [0, 0, 0, 1, 1]),
          ([e3, (-S, -S), e1, tuple(c0)], [0, 0, 1, 1])]
spots = [(41, (0.42, -0.36, 0.0), (0, 0), False), (-23, (0.52, 0.47, 0.0), (0, 4), True), (73, (-0.52, -0.42, 0.0), (2, 0), False)]
for k, ((corners, br), (yaw, pos, tilt, flip)) in enumerate(zip(pieces, spots)):
    ctr = sum((Vector(c) for c in corners), Vector((0.0, 0.0))) / len(corners)
    ob = slab(F, f"F_Piece{k}", [Vector(p) - ctr for p in jag_outline(corners, br, amp=0.008)], TILE_T, 0.0, hull=f"Piece{k}")
    place([ob], yaw, pos, tilt, flip)
# crumbs, denser close to the middle
for k in range(18):
    rr = rnd.uniform(0.012, 0.045) if k < 10 else rnd.uniform(0.008, 0.02)
    n = rnd.randint(5, 7)
    outline = [(math.cos(2 * math.pi * j / n + rnd.uniform(-0.3, 0.3)) * rr * rnd.uniform(0.6, 1.2),
                math.sin(2 * math.pi * j / n + rnd.uniform(-0.3, 0.3)) * rr * rnd.uniform(0.6, 1.2)) for j in range(n)]
    ob = slab(F, f"F_Crumb{k}", outline, rnd.uniform(0.006, TILE_T), 0.0)
    while True:                                                # keep crumbs off the whole tile
        d = rnd.uniform(0.25, 0.85) ** 1.3; a = rnd.uniform(0, 2 * math.pi)
        px_, py_ = 0.05 + math.cos(a) * d * 0.8, 0.02 + math.sin(a) * d * 0.7
        if max(abs(px_ + 0.16), abs(py_ - 0.08)) > 0.38: break
    place([ob], rnd.uniform(0, 360), (px_, py_, 0.0),
          (rnd.uniform(-8, 8), rnd.uniform(-8, 8)), flip=rnd.random() < 0.4)

# ================================================================= stage layout
layout = {A: (0.0, 0.0, 2.8), Bn: (1.8, 0.0, 2.8), F: (0.2, 0.1, 0.0)}
for name, objs in ASSETS.items():
    for o in objs:
        o.location = layout[name]; o["ofs"] = layout[name]
for o in C.PARTS:
    if o.data.materials[0] in TILE_MATS or o.data.materials[0] in (M_TBAR, M_WEB, M_VOID):
        for p in o.data.polygons: p.use_smooth = False
for name, objs in ASSETS.items():
    print(name, len(objs), "parts", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), "tris")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "stage.blend"))
