"""Worn 5-drawer metal filing cabinet for the abandoned office (Blender 4.2 / bpy).
python3.11 build_cabinet.py  ->  out/stage.blend
Front faces -Y. Pivot: floor, centre. Units: metres.
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
random.seed(5)

W, D, H = 0.46, 0.62, 1.63
PLINTH = 0.06
LID = 0.012
STILE = 0.018
FRONT = -D / 2
GAP = 0.004
Z0, Z1 = PLINTH + 0.015, H - LID - 0.022           # drawer zone
HD = (Z1 - Z0 - 6 * GAP) / 5                        # drawer height
DW = W - 2 * STILE - 2 * 0.003                      # drawer width
OPEN = {1: 0.075}                                   # drawer index (0 = top) -> pulled out (m)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'

# ----------------------------------------------------------------- materials (procedural)
def mat_new(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); o.location = (1200, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (900, 0)
    nt.links.new(b.outputs[0], o.inputs[0])
    return m, nt, b

class G:
    """tiny node-graph helper"""
    def __init__(s, nt): s.nt = nt; s.x = -1600; s.y = 0
    def n(s, t, **kw):
        nd = s.nt.nodes.new(t); nd.location = (s.x, s.y); s.y -= 180
        if s.y < -2400: s.y = 0; s.x += 220
        for k, v in kw.items():
            if k in nd.inputs: nd.inputs[k].default_value = v
            else: setattr(nd, k, v)
        return nd
    def L(s, a, b): s.nt.links.new(a, b)
    def val(s, x, sock):
        if isinstance(x, bpy.types.NodeSocket): s.L(x, sock)
        else: sock.default_value = x
    def math(s, op, a, b=0.0, clamp=False):
        m = s.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        s.val(a, m.inputs[0]); s.val(b, m.inputs[1]); return m.outputs[0]
    def rng(s, src, a, b):
        r = s.n("ShaderNodeMapRange"); r.inputs[1].default_value = a; r.inputs[2].default_value = b
        s.L(src, r.inputs[0]); return r.outputs[0]
    def mixc(s, fac, a, b, blend='MIX'):
        m = s.n("ShaderNodeMix", data_type='RGBA', blend_type=blend)
        s.val(fac, m.inputs[0]); s.val(a, m.inputs[6]); s.val(b, m.inputs[7]); return m.outputs[2]
    def mixf(s, fac, a, b):
        m = s.n("ShaderNodeMix", data_type='FLOAT')
        s.val(fac, m.inputs[0]); s.val(a, m.inputs[2]); s.val(b, m.inputs[3]); return m.outputs[0]
    def noise(s, vec, scale, detail=6.0, rough=0.6, mapping_scale=None):
        if mapping_scale:
            mp = s.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = mapping_scale
            s.L(vec, mp.inputs[0]); vec = mp.outputs[0]
        nz = s.n("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough)
        s.L(vec, nz.inputs[0]); return nz.outputs[0]

DUST = (0.33, 0.31, 0.28, 1)

def common(g):
    tc = g.n("ShaderNodeTexCoord"); geo = g.n("ShaderNodeNewGeometry")
    sep_n = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sep_n.inputs[0])
    sep_p = g.n("ShaderNodeSeparateXYZ"); g.L(tc.outputs["Object"], sep_p.inputs[0])
    up = g.rng(sep_n.outputs[2], 0.6, 0.95)
    dust = g.math('MULTIPLY', up, g.rng(g.noise(tc.outputs["Object"], 14, 8), 0.3, 0.65), True)
    return tc, geo, sep_n, sep_p, dust

def paint_material(name="M_Cab_Paint", pw=1.0):
    m, nt, b = mat_new(name); g = G(nt)
    tc, geo, sn, sp, dust = common(g)
    obj = tc.outputs["Object"]
    # base putty-grey paint with large blotchy fading
    base = g.mixc(g.noise(obj, 3, 4), (0.26, 0.255, 0.24, 1), (0.31, 0.30, 0.28, 1))
    # chips: edges (pointiness) + noise
    chip = g.rng(g.math('ADD', g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.58), pw), g.noise(obj, 30, 10, 0.75)), 1.0, 1.04)
    chip_core = g.rng(g.math('ADD', g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.58), pw), g.noise(obj, 30, 10, 0.75)), 1.08, 1.14)
    # horizontal scratches (stretched noise)
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(6, 6, 240)), 0.73, 0.76)
    scr = g.math('MULTIPLY', scr, g.rng(g.noise(obj, 4, 2), 0.45, 0.6), True)
    # rust: bottom band + random spots, follows chips
    low = g.rng(sp.outputs[2], 0.12, 0.0)
    rust_n = g.noise(obj, 12, 8, 0.7)
    rust = g.rng(g.math('MULTIPLY', g.math('ADD', low, g.math('MULTIPLY', chip, 0.6)), rust_n), 0.4, 0.55)
    # hand grime around handles: front faces, band around each handle height
    front = g.rng(sn.outputs[1], -0.6, -0.95)
    pitch = HD + GAP
    rel = g.math('DIVIDE', g.math('SUBTRACT', sp.outputs[2], Z0 + HD * 0.62), pitch)
    band = g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', rel), 0.5))
    band = g.rng(band, 0.5, 0.36)                                   # 1 near handle height
    xcen = g.rng(g.math('ABSOLUTE', sp.outputs[0]), 0.13, 0.03)
    grime = g.math('MULTIPLY', g.math('MULTIPLY', band, xcen), g.math('MULTIPLY', front, g.rng(g.noise(obj, 22, 6), 0.4, 0.7)), True)
    c = g.mixc(chip, base, (0.07, 0.07, 0.075, 1))                 # dark primer
    c = g.mixc(chip_core, c, (0.40, 0.40, 0.40, 1))                # bare steel
    c = g.mixc(g.math('MULTIPLY', scr, 0.7), c, (0.42, 0.42, 0.41, 1))
    rc = g.mixc(g.noise(obj, 50, 5), (0.14, 0.05, 0.02, 1), (0.28, 0.12, 0.05, 1))
    c = g.mixc(rust, c, rc)
    c = g.mixc(g.math('MULTIPLY', grime, 0.75), c, (0.09, 0.08, 0.07, 1))
    c = g.mixc(g.math('ADD', g.math('MULTIPLY', dust, 0.9), 0.06, True), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(chip, 0.52, 0.6); r = g.mixf(chip_core, r, 0.35); r = g.mixf(scr, r, 0.35)
    r = g.mixf(rust, r, 0.85); r = g.mixf(grime, r, 0.38); r = g.mixf(dust, r, 0.95)
    g.L(r, b.inputs["Roughness"])
    met = g.math('MAXIMUM', chip_core, g.math('MULTIPLY', scr, 0.8))
    met = g.mixf(rust, met, 0.0); met = g.mixf(dust, met, 0.0)
    g.L(met, b.inputs["Metallic"])
    h = g.math('ADD', g.math('MULTIPLY', chip, -1.0), g.math('MULTIPLY', g.noise(obj, 400, 2), 0.15))
    h = g.math('ADD', h, g.math('MULTIPLY', rust, 0.5))
    bump = g.n("ShaderNodeBump", Strength=0.3, Distance=0.0006); g.L(h, bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def simple_material(name, col, rough, metal, rust=0.0, dust_amt=0.8, col2=None):
    m, nt, b = mat_new(name); g = G(nt)
    tc, geo, sn, sp, dust = common(g)
    obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 25, 4), col, col2 or col)
    r = rough
    if rust:
        rm = g.rng(g.noise(obj, 40, 8, 0.7), 0.62 - rust * 0.1, 0.66 - rust * 0.1)
        c = g.mixc(rm, c, (0.2, 0.08, 0.03, 1)); r = g.mixf(rm, rough, 0.85)
        mm = g.mixf(rm, metal, 0.0); g.L(mm, b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = metal
    dirt = g.rng(g.noise(obj, 60, 6), 0.45, 0.8)
    c = g.mixc(g.math('MULTIPLY', dirt, 0.35), c, (0.15, 0.14, 0.12, 1))
    r = g.mixf(g.math('MULTIPLY', dirt, 0.5), r, 0.6)
    c = g.mixc(g.math('MULTIPLY', dust, dust_amt), c, DUST)
    r = g.mixf(dust, r, 0.95)
    g.L(c, b.inputs["Base Color"]); g.L(r, b.inputs["Roughness"])
    return m

def label_material():
    m, nt, b = mat_new("M_Cab_Label"); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map="LabelUV")
    img = g.n("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(HERE, "labels", "labels.png"))
    g.L(uvn.outputs[0], img.inputs[0])
    g.L(img.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    return m

M = {"paint": paint_material(), "trim": paint_material("M_Cab_PaintTrim", 0.35),
     "interior": simple_material("M_Cab_Interior", (0.035, 0.035, 0.037, 1), 0.7, 0.2),
     "kick": simple_material("M_Cab_Kick", (0.02, 0.02, 0.02, 1), 0.6, 0.0, dust_amt=1.0),
     "chrome": simple_material("M_Cab_Chrome", (0.55, 0.55, 0.55, 1), 0.32, 1.0, rust=-0.6),
     "label": label_material(),
     "manila": simple_material("M_Cab_Folder", (0.42, 0.33, 0.18, 1), 0.9, 0.0, col2=(0.5, 0.4, 0.24, 1)),
     "green": simple_material("M_Cab_FolderGreen", (0.10, 0.17, 0.12, 1), 0.88, 0.0, col2=(0.14, 0.2, 0.15, 1))}

# ----------------------------------------------------------------- geometry helpers
parts = []
def box(name, x0, x1, y0, y1, z0, z1, mat, cuts=0, bevel=0.0, seg=2, face_mat=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    me.materials.append(M[mat])
    if face_mat:
        for fm_name, test in face_mat:
            me.materials.append(M[fm_name])
            idx = len(me.materials) - 1
            for p in me.polygons:
                if test(p.normal): p.material_index = idx
    if bevel:
        mod = ob.modifiers.new("bev", 'BEVEL'); mod.width = bevel; mod.segments = seg
        mod.limit_method = 'ANGLE'; mod.harden_normals = False
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier="bev")
    for p in me.polygons: p.use_smooth = False
    parts.append(ob)
    return ob

def dent(ob, center, normal, depth, sigma):
    c = Vector(center); n = Vector(normal).normalized()
    for v in ob.data.vertices:
        if v.normal.dot(n) > 0.5 or abs((v.co - c).dot(n)) < 0.02:
            d2 = ((v.co - c) - n * (v.co - c).dot(n)).length_squared
            v.co -= n * depth * math.exp(-d2 / (2 * sigma * sigma))

def cylinder(name, center, r, depth, axis_y=True, mat="chrome", segs=20):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=depth)
    if axis_y:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); me.materials.append(M[mat])
    for p in me.polygons: p.use_smooth = True
    parts.append(ob); return ob

# ----------------------------------------------------------------- carcass
core = box("Carcass", -W / 2, W / 2, FRONT + 0.012, D / 2, PLINTH, H - LID, "paint", cuts=14, bevel=0.004,
           face_mat=[("interior", lambda n: n.y < -0.9)])
dent(core, (W / 2, 0.08, 0.62), (1, 0, 0), 0.011, 0.07)          # kicked side
dent(core, (-W / 2, -0.15, 1.25), (-1, 0, 0), 0.005, 0.04)
lid = box("Lid", -W / 2 - 0.003, W / 2 + 0.003, FRONT - 0.003, D / 2 + 0.003, H - LID, H, "paint", cuts=10, bevel=0.004)
dent(lid, (0.12, -0.05, H), (0, 0, 1), 0.004, 0.05)
box("StileL", -W / 2, -W / 2 + STILE, FRONT, FRONT + 0.013, PLINTH, H - LID, "trim", bevel=0.002)
box("StileR", W / 2 - STILE, W / 2, FRONT, FRONT + 0.013, PLINTH, H - LID, "trim", bevel=0.002)
box("RailTop", -W / 2 + STILE, W / 2 - STILE, FRONT, FRONT + 0.013, Z1 + GAP, H - LID, "trim", bevel=0.002)
box("RailBot", -W / 2 + STILE, W / 2 - STILE, FRONT, FRONT + 0.013, PLINTH, Z0 - GAP, "trim", bevel=0.002)
box("Kick", -W / 2 + 0.02, W / 2 - 0.02, FRONT + 0.03, D / 2 - 0.02, 0.0, PLINTH, "kick", bevel=0.002)
for sx in (-1, 1):                                               # little feet
    for sy in (-1, 1):
        cylinder(f"Foot{sx}{sy}", (sx * (W / 2 - 0.04), sy * (D / 2 - 0.05), 0.004), 0.015, 0.008, axis_y=False, mat="kick", segs=12)

# ----------------------------------------------------------------- drawers
label_cards = []
for k in range(5):
    zt = Z1 - k * (HD + GAP)
    zb = zt - HD
    zc = (zt + zb) / 2
    oy = -OPEN.get(k, 0.0)
    f0, f1 = FRONT - 0.006 + oy, FRONT + 0.014 + oy                # front panel y-range
    fr = box(f"Drawer{k}", -DW / 2, DW / 2, f0, f1, zb, zt, "paint", cuts=6, bevel=0.003)
    if k == 3:
        dent(fr, (-0.11, f0, zb + 0.08), (0, -1, 0), 0.006, 0.035)
    # handle: rounded bar on two posts
    hz = zb + HD * 0.42
    box(f"HandleBar{k}", -0.075, 0.075, f0 - 0.032, f0 - 0.014, hz - 0.011, hz + 0.011, "chrome", bevel=0.0085, seg=4)
    for sx in (-1, 1):
        box(f"HandlePost{k}{sx}", sx * 0.062 - 0.006, sx * 0.062 + 0.006, f0 - 0.02, f0, hz - 0.008, hz + 0.008, "chrome", bevel=0.002)
    # label holder frame + card
    lz = zb + HD * 0.72
    lw, lh, bw = 0.085, 0.05, 0.005
    for nm, (x0, x1, z0, z1) in {"T": (-lw / 2, lw / 2, lz + lh / 2 - bw, lz + lh / 2),
                                 "B": (-lw / 2, lw / 2, lz - lh / 2, lz - lh / 2 + bw),
                                 "L": (-lw / 2, -lw / 2 + bw, lz - lh / 2, lz + lh / 2),
                                 "R": (lw / 2 - bw, lw / 2, lz - lh / 2, lz + lh / 2)}.items():
        box(f"LabelFrame{k}{nm}", x0, x1, f0 - 0.003, f0, z0, z1, "chrome", bevel=0.0008, seg=1)
    card = box(f"Card{k}", -lw / 2 + bw * 0.6, lw / 2 - bw * 0.6, f0 - 0.0012, f0 - 0.0002,
               lz - lh / 2 + bw * 0.6, lz + lh / 2 - bw * 0.6, "label")
    label_cards.append((card, k))
    if k == 0:                                                     # cylinder lock, top right
        cylinder("Lock", (DW / 2 - 0.045, f0 - 0.004, zt - 0.04), 0.011, 0.01)
        box("LockSlot", DW / 2 - 0.0465, DW / 2 - 0.0435, f0 - 0.0095, f0 - 0.008, zt - 0.047, zt - 0.033, "interior")
    if k in OPEN:                                                  # visible drawer box + hanging folders
        depth = 0.48
        box(f"DrawerSideL{k}", -DW / 2 + 0.01, -DW / 2 + 0.018, f1, f1 + depth, zb + 0.02, zt - 0.03, "interior")
        box(f"DrawerSideR{k}", DW / 2 - 0.018, DW / 2 - 0.01, f1, f1 + depth, zb + 0.02, zt - 0.03, "interior")
        box(f"DrawerBottom{k}", -DW / 2 + 0.01, DW / 2 - 0.01, f1, f1 + depth, zb + 0.02, zb + 0.026, "interior")
        for sx in (-1, 1):
            box(f"Rail{k}{sx}", sx * (DW / 2 - 0.03) - 0.003, sx * (DW / 2 - 0.03) + 0.003, f1, f1 + depth,
                zt - 0.045, zt - 0.039, "chrome")
        y = f1 + 0.02
        rnd = random.Random(9)
        while y < f1 + depth - 0.03:
            th = 0.0012
            tilt = rnd.uniform(-0.05, 0.05)
            fh = HD - 0.08
            mat = rnd.choice(["manila", "manila", "green"])
            fo = box(f"Folder{k}_{y:.3f}", -DW / 2 + 0.035, DW / 2 - 0.035, y, y + th, zt - 0.04 - fh, zt - 0.04, mat)
            fo.rotation_euler = (tilt, 0, rnd.uniform(-0.02, 0.02))
            tx = rnd.uniform(-0.12, 0.08)
            box(f"Tab{k}_{y:.3f}", tx, tx + 0.06, y, y + th, zt - 0.04, zt - 0.025, mat).rotation_euler = (tilt, 0, 0)
            # paper peeking out of some folders
            if rnd.random() < 0.5:
                box(f"Sheet{k}_{y:.3f}", -DW / 2 + 0.05, DW / 2 - 0.06, y + 0.003, y + 0.0035,
                    zt - 0.04 - fh + 0.02, zt - 0.04 + rnd.uniform(0.005, 0.02), "label").rotation_euler = (tilt, 0, 0)
            y += rnd.uniform(0.025, 0.05)

# label UVs (cards map to their slice of labels.png); sheets inside folders reuse the blank card
for ob in parts:
    me = ob.data
    lay = me.uv_layers.new(name="LabelUV")
    card_k = None
    if ob.name.startswith("Card"): card_k = int(ob.name[4])
    elif ob.name.startswith("Sheet"): card_k = 4
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            if card_k is None:
                lay.data[li].uv = (0, 0)
            else:
                u = (v.x - x0) / (x1 - x0 + 1e-9)
                t = (v.z - z0) / (z1 - z0 + 1e-9)
                lay.data[li].uv = (u, (4 - card_k + t) / 5.0)

for ob in parts:                    # apply transforms (folders are tilted)
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
print("parts", len(parts), "tris", tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage.blend"))
