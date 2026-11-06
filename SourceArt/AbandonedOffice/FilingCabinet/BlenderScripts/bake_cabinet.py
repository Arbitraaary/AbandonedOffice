"""Bake + export the filing cabinet.
python3.11 bake_cabinet.py -- <stage.blend> <out_dir> [res]
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT = args[0], args[1]
RES = int(args[2]) if len(args) > 2 else 2048
TEX = os.path.join(OUT, "Textures"); os.makedirs(TEX, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.render.bake.margin = 8; sc.render.bake.use_clear = True
if sc.world is None: sc.world = bpy.data.worlds.new("BakeWorld")
sc.world.light_settings.distance = 0.15

def select_only(objs):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

parts = [o for o in bpy.data.objects if o.type == 'MESH']
select_only(parts); bpy.ops.object.join()
ob = bpy.context.active_object; ob.name = ob.data.name = "SM_FilingCabinet"
me = ob.data
lay = me.uv_layers.new(name="BakeUV"); me.uv_layers.active = lay; lay.active_render = True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0)
bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
bpy.ops.object.mode_set(mode='OBJECT')

def bsdf_of(m): return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
def out_of(m): return next(n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
def bake(kind, img, channel=None, samples=1):
    sc.cycles.samples = samples
    temp = []
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

base = "T_FilingCabinet"
i_bc = new_img("bc", False); bake('EMIT', i_bc, "Base Color")
i_r = new_img("r", True); bake('EMIT', i_r, "Roughness")
i_m = new_img("m", True); bake('EMIT', i_m, "Metallic")
i_n = new_img("n", True); bake('NORMAL', i_n, samples=4)
i_ao = new_img("ao", True); bake('AO', i_ao, samples=32)
bc, r, mm, n, ao = (px(i) for i in (i_bc, i_r, i_m, i_n, i_ao))
save_rgb(bc[..., :3] * (0.7 + 0.3 * ao[..., :1]), os.path.join(TEX, base + "_BC.png"), True)
save_rgb(np.concatenate([ao[..., :1], r[..., :1], mm[..., :1]], 2), os.path.join(TEX, base + "_ORM.png"), False)
nd = n[..., :3].copy(); nd[..., 1] = 1 - nd[..., 1]; save_rgb(nd, os.path.join(TEX, base + "_N.png"), False)
print("baked", flush=True)
for i in list(bpy.data.images):
    if i.name in ("bc", "r", "m", "n", "ao") or i.name.startswith(base): bpy.data.images.remove(i)

# collision: cabinet body + the pulled-out drawer front
def ucx(name, x0, x1, y0, y1, z0, z1):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); sc.collection.objects.link(o)
    o.display_type = 'WIRE'; o.hide_render = True; o.parent = ob; return o
xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
u0 = ucx("UCX_SM_FilingCabinet_00", min(xs), max(xs), -0.31 - 0.006, max(ys), 0.0, max(zs))
dz = [v.co.z for v in me.vertices if v.co.y < -0.33]
u1 = ucx("UCX_SM_FilingCabinet_01", -0.21, 0.21, min(ys), -0.316, min(dz), max(dz))
for i in bpy.data.images:
    if i.filepath and not i.packed_file: i.pack()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "FilingCabinet.blend"), compress=True)

# FBX: single material slot, BakeUV only
mat = bpy.data.materials.new("M_FilingCabinet")
for p in me.polygons: p.material_index = 0
me.materials[0] = mat
while len(me.materials) > 1: me.materials.pop(index=len(me.materials) - 1)
me.uv_layers.remove(me.uv_layers["LabelUV"])
select_only([ob]); u0.select_set(True); u1.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_FilingCabinet.fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
    mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_tspace=True)
print("exported tris", sum(len(p.vertices) - 2 for p in me.polygons), "dims", tuple(round(d, 3) for d in ob.dimensions))
