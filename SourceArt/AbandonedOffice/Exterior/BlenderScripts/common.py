"""Shared helpers for the parking props (Blender 4.2 / bpy)."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, noise
from nodes import mat_new, G

DUST = (0.30, 0.28, 0.25, 1)
PARTS = []

def link(name, me, mat):
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if isinstance(mat, (list, tuple)):
        for m in mat: me.materials.append(m)
    else:
        me.materials.append(mat)
    PARTS.append(ob); return ob

def box(name, x0, x1, y0, y1, z0, z1, mat, bevel=0.0, seg=2, cuts=0, rot=None, pivot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    if cuts: bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    if rot is not None:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=Vector(pivot), matrix=rot)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(name, me, mat)
    if bevel:
        md = ob.modifiers.new("b", 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
        with bpy.context.temp_override(object=ob, active_object=ob): bpy.ops.object.modifier_apply(modifier="b")
    for p in me.polygons: p.use_smooth = False
    return ob

def cyl(name, center, r, depth, mat, axis='Z', segs=24, r2=None, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    if axis == 'X': bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    if axis == 'Y': bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(name, me, mat)
    for p in me.polygons: p.use_smooth = True
    return ob

def dome(name, center, r, mat, segs=20, rings=6):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings * 2, radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context='VERTS')
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(name, me, mat)
    for p in me.polygons: p.use_smooth = True
    return ob

# ----------------------------------------------------------------- materials
def painted(name, col, primer=(0.07, 0.07, 0.07, 1), chip_amt=0.8, rough=0.5, rust=0.6, streak_from=None):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    sn = g.n("ShaderNodeSeparateXYZ"); g.L(geo.outputs["Normal"], sn.inputs[0])
    sp = g.n("ShaderNodeSeparateXYZ"); g.L(obj, sp.inputs[0])
    c = g.mixc(g.noise(obj, 3, 4), col, tuple(v * 0.8 for v in col[:3]) + (1,))
    chip = g.rng(g.math('ADD', g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.6), chip_amt),
                       g.noise(obj, 30, 10, 0.75)), 0.82, 0.86)
    core = g.rng(g.math('ADD', g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.6), chip_amt),
                       g.noise(obj, 30, 10, 0.75)), 0.9, 0.94)
    scr = g.rng(g.noise(obj, 6, 3, 0.5, mapping_scale=(200, 200, 12)), 0.765, 0.785)
    low = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.35, 0.0), g.rng(g.noise(obj, 14, 6), 0.4, 0.7), True)
    rr = g.math('MULTIPLY', g.math('ADD', g.math('MULTIPLY', core, 1.0), low), rust)
    if streak_from is not None:
        st = g.math('MULTIPLY', g.rng(g.noise(obj, 4, 5, 0.6, mapping_scale=(30, 30, 1.2)), 0.62, 0.75),
                    g.rng(sp.outputs[2], streak_from, streak_from - 0.8), True)
        rr = g.math('MAXIMUM', rr, g.math('MULTIPLY', st, rust))
    rr = g.math('MINIMUM', rr, 1.0)
    c = g.mixc(chip, c, primer)
    c = g.mixc(g.math('MULTIPLY', scr, 0.7), c, (0.4, 0.4, 0.4, 1))
    rc = g.mixc(g.noise(obj, 50, 5), (0.15, 0.06, 0.02, 1), (0.30, 0.13, 0.05, 1))
    c = g.mixc(rr, c, rc)
    up = g.rng(sn.outputs[2], 0.5, 0.95)
    dust = g.math('ADD', g.math('MULTIPLY', up, g.rng(g.noise(obj, 16, 6), 0.3, 0.65)), 0.05, True)
    dirt = g.math('MULTIPLY', g.rng(sp.outputs[2], 0.4, 0.0), 0.5)
    c = g.mixc(dirt, c, (0.12, 0.1, 0.08, 1))
    c = g.mixc(g.math('MULTIPLY', dust, 0.8), c, DUST)
    g.L(c, b.inputs["Base Color"])
    r = g.mixf(chip, rough, 0.6); r = g.mixf(scr, r, 0.35); r = g.mixf(rr, r, 0.85); r = g.mixf(dust, r, 0.95)
    g.L(r, b.inputs["Roughness"])
    met = g.math('MAXIMUM', g.math('SUBTRACT', core, rr), g.math('MULTIPLY', scr, 0.8))
    g.L(g.mixf(dust, met, 0.0), b.inputs["Metallic"])
    bump = g.n("ShaderNodeBump", Strength=0.25, Distance=0.0006)
    g.L(g.math('ADD', g.math('MULTIPLY', chip, -1), g.math('MULTIPLY', rr, 0.5)), bump.inputs["Height"])
    g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def concrete():
    m, nt, b = mat_new("M_Concrete"); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]; geo = g.n("ShaderNodeNewGeometry")
    c = g.mixc(g.noise(obj, 12, 8, 0.65), (0.20, 0.195, 0.185, 1), (0.33, 0.32, 0.30, 1))
    vor = g.n("ShaderNodeTexVoronoi", Scale=6.0, feature='DISTANCE_TO_EDGE'); g.L(obj, vor.inputs[0])
    crack = g.math('MULTIPLY', g.rng(vor.outputs["Distance"], 0.01, 0.0), g.rng(g.noise(obj, 5, 3), 0.45, 0.6), True)
    c = g.mixc(crack, c, (0.04, 0.04, 0.035, 1))
    c = g.mixc(g.math('MULTIPLY', g.rng(geo.outputs["Pointiness"], 0.5, 0.6), 0.5), c, (0.4, 0.39, 0.37, 1))
    c = g.mixc(g.math('MULTIPLY', g.rng(g.noise(obj, 20, 6), 0.62, 0.72), 0.6), c, (0.07, 0.09, 0.04, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump = g.n("ShaderNodeBump", Strength=0.5, Distance=0.002)
    g.L(g.math('SUBTRACT', g.noise(obj, 120, 5), crack), bump.inputs["Height"]); g.L(bump.outputs[0], b.inputs["Normal"])
    return m

def plain(name, col, rough, metal, dirt_amt=0.35):
    m, nt, b = mat_new(name); g = G(nt)
    tc = g.n("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    c = g.mixc(g.noise(obj, 20, 5), col, tuple(v * 0.8 for v in col[:3]) + (1,))
    dirt = g.rng(g.noise(obj, 30, 5), 0.5, 0.8)
    c = g.mixc(g.math('MULTIPLY', dirt, dirt_amt), c, (0.12, 0.11, 0.09, 1))
    g.L(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

def image_material(name, path, uv="SignUV", rough=0.5):
    m, nt, b = mat_new(name); g = G(nt)
    uvn = g.n("ShaderNodeUVMap", uv_map=uv)
    img = g.n("ShaderNodeTexImage"); img.image = bpy.data.images.load(path); img.extension = 'EXTEND'
    g.L(uvn.outputs[0], img.inputs[0]); g.L(img.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m

def set_uv(ob, layer, fn):
    """fn(world_co, polygon) -> (u, v) for every loop"""
    me = ob.data
    lay = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    for p in me.polygons:
        for li in p.loop_indices:
            lay.data[li].uv = fn(me.vertices[me.loops[li].vertex_index].co, p)

def finalize(layers):
    for ob in PARTS:
        for l in layers:
            if l not in ob.data.uv_layers: ob.data.uv_layers.new(name=l)
