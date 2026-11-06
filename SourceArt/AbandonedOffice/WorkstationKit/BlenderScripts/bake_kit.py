"""Bake the workstation kit into ONE shared atlas, then split it back into separate meshes + FBX.
python3.11 bake_kit.py -- <stage.blend> <out_dir> <res>
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT, RES = args[0], args[1], int(args[2])
TEX = os.path.join(OUT, "Textures"); os.makedirs(TEX, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.render.bake.margin = 6; sc.render.bake.use_clear = True
if sc.world is None: sc.world = bpy.data.worlds.new("BakeWorld")
sc.world.light_settings.distance = 0.05
BASE = "T_WorkstationKit"

def select_only(objs):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

parts = [o for o in bpy.data.objects if o.type == 'MESH' and "asset" in o]
names = sorted({o["asset"] for o in parts})
ofs = {o["asset"]: Vector(o["ofs"]) for o in parts}
# collision hulls (in asset space), from the solid parts only
def hull_pts(asset):
    skip = ("Cable", "Cord", "Handset", "Ear", "Mouth") if asset == "SM_DeskPhone_Hanging" else ("Cable", "Cord")
    return [o.matrix_world @ v.co - ofs[asset] for o in parts if o["asset"] == asset and not any(k in o.name for k in skip)
            for v in o.data.vertices]
hulls = {a: hull_pts(a) for a in names}
# tag faces with the asset index, then join
for o in parts:
    idx = names.index(o["asset"])
    a = o.data.attributes.new("asset_id", 'INT', 'FACE')
    for i in range(len(o.data.polygons)): a.data[i].value = idx
select_only(parts); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
ob = bpy.context.active_object; ob.name = ob.data.name = "Kit"; me = ob.data
lay = me.uv_layers.new(name="BakeUV"); me.uv_layers.active = lay; lay.active_render = True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0)
bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
bpy.ops.object.mode_set(mode='OBJECT')

def bsdf_of(m): return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
def out_of(m): return next(n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
def bake(kind, img, channel=None, samples=1):
    sc.cycles.samples = samples; temp = []
    for m in me.materials:
        nt = m.node_tree
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img; nt.nodes.active = tn; temp.append((m, tn))
        if kind == 'EMIT':
            b, o = bsdf_of(m), out_of(m)
            em = nt.nodes.new("ShaderNodeEmission"); sock = b.inputs[channel]
            if sock.is_linked: nt.links.new(sock.links[0].from_socket, em.inputs[0])
            else:
                v = sock.default_value
                em.inputs[0].default_value = tuple(v) if channel == "Base Color" else (v, v, v, 1)
            nt.links.new(em.outputs[0], o.inputs[0]); temp.append((m, em))
    select_only([ob])
    if kind == 'NORMAL': bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
    else: bpy.ops.object.bake(type=kind)
    for m, n in temp: m.node_tree.nodes.remove(n)
    for m in me.materials: m.node_tree.links.new(bsdf_of(m).outputs[0], out_of(m).inputs[0])
def new_img(name, nc):
    i = bpy.data.images.new(name, RES, RES, alpha=False); i.colorspace_settings.name = 'Non-Color' if nc else 'sRGB'; return i
def px(i): return np.array(i.pixels[:], dtype=np.float32).reshape(RES, RES, 4)
def save_rgb(a, path, srgb):
    i = bpy.data.images.new(os.path.basename(path), RES, RES, alpha=False)
    i.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    rgba = np.ones((RES, RES, 4), np.float32); rgba[..., :3] = np.clip(a, 0, 1)
    i.pixels[:] = rgba.ravel(); i.filepath_raw = path; i.file_format = 'PNG'; i.save()
i_bc = new_img("bc", False); bake('EMIT', i_bc, "Base Color")
i_r = new_img("r", True); bake('EMIT', i_r, "Roughness")
i_m = new_img("m", True); bake('EMIT', i_m, "Metallic")
i_n = new_img("n", True); bake('NORMAL', i_n, samples=4)
i_ao = new_img("ao", True); bake('AO', i_ao, samples=32)
bc, r, mm, n, ao = (px(i) for i in (i_bc, i_r, i_m, i_n, i_ao))
save_rgb(bc[..., :3] * (0.7 + 0.3 * ao[..., :1]), os.path.join(TEX, BASE + "_BC.png"), True)
save_rgb(np.concatenate([ao[..., :1], r[..., :1], mm[..., :1]], 2), os.path.join(TEX, BASE + "_ORM.png"), False)
nd = n[..., :3].copy(); nd[..., 1] = 1 - nd[..., 1]; save_rgb(nd, os.path.join(TEX, BASE + "_N.png"), False)
print("baked", flush=True)
for i in list(bpy.data.images):
    if i.name in ("bc", "r", "m", "n", "ao") or i.name.startswith(BASE): bpy.data.images.remove(i)
for i in bpy.data.images:
    if i.filepath and not i.packed_file: i.pack()

# ---- split back into one object per asset (procedural materials kept for the .blend)
objs = {}
for idx, name in enumerate(names):
    dup = ob.copy(); dup.data = ob.data.copy(); sc.collection.objects.link(dup)
    bm = bmesh.new(); bm.from_mesh(dup.data)
    lay_id = bm.faces.layers.int.get("asset_id")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay_id] != idx], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for v in bm.verts: v.co -= ofs[name]
    bm.to_mesh(dup.data); bm.free()
    dup.name = dup.data.name = name
    dup.location = ofs[name]
    hb = bmesh.new()
    for p in hulls[name][::max(1, len(hulls[name]) // 300)]: hb.verts.new(p)
    bmesh.ops.convex_hull(hb, input=hb.verts[:])
    hm = bpy.data.meshes.new("UCX"); hb.to_mesh(hm); hb.free()
    u = bpy.data.objects.new(f"UCX_{name}_00", hm); sc.collection.objects.link(u)
    u.display_type = 'WIRE'; u.hide_render = True; u.parent = dup
    objs[name] = (dup, u)
bpy.data.objects.remove(ob)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "WorkstationKit.blend"), compress=True)

# ---- FBX per asset: one material slot, BakeUV only, at the origin
mat = bpy.data.materials.new("M_WorkstationKit")
for name, (o, u) in objs.items():
    m = o.data
    for p in m.polygons: p.material_index = 0
    m.materials[0] = mat
    while len(m.materials) > 1: m.materials.pop(index=len(m.materials) - 1)
    for l in [l.name for l in m.uv_layers if l.name != "BakeUV"]: m.uv_layers.remove(m.uv_layers[l])
    keep = o.location.copy(); o.location = (0, 0, 0)
    select_only([o]); u.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_tspace=True)
    o.location = keep
    print("exported", name, len(m.polygons), "faces", tuple(round(d, 3) for d in o.dimensions))
