"""Join the guard parts into one skinned mesh, bake the procedural materials into one 2048 atlas, export the FBX.
blender -b -P bake_guard.py -> ../SK_SecurityGuard.fbx, ../Textures/T_SecurityGuard_{BC,N,ORM}.png, ../SecurityGuard.blend
"""
import bpy, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE); TEX = os.path.join(OUT, "Textures")           # results go to SecurityGuard/; os.makedirs(TEX, exist_ok=True)
RES = 2048; BASE = "T_SecurityGuard"
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "_work", "stage.blend"))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.render.bake.margin = 8; sc.render.bake.use_clear = True
if sc.world is None: sc.world = bpy.data.worlds.new("BakeWorld")
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
parts = [o for o in bpy.data.objects if o.type == 'MESH']

def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]

skin = next(o for o in parts if o.name == "Skin")
select_only(parts, skin); bpy.ops.object.join()
ob = bpy.context.active_object; ob.name = ob.data.name = "SK_SecurityGuard"; me = ob.data
for l in [l.name for l in me.uv_layers]: me.uv_layers.remove(me.uv_layers[l])
lay = me.uv_layers.new(name="UVMap"); me.uv_layers.active = lay; lay.active_render = True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.003, area_weight=0.0)
# more texels for the SECURITY prints and the face, so the letters / glasses / moustache stay crisp
import bmesh
BOOST = {"M_VestText": 5.0, "M_Glasses": 2.0, "M_Hair": 2.0, "M_Badge": 2.0, "M_Skin": 1.5}
bm = bmesh.from_edit_mesh(me); uvl = bm.loops.layers.uv.active
for f in bm.faces:
    k = BOOST.get(me.materials[f.material_index].name, 1.0)
    for l in f.loops:
        l[uvl].uv *= k                                   # pack_islands moves islands, only the size matters
        l[uvl].select = True; l[uvl].select_edge = True
bmesh.update_edit_mesh(me)
bpy.ops.uv.pack_islands(margin=0.003, rotate=True, scale=True)
bpy.ops.object.mode_set(mode='OBJECT')
uvs = [d.uv[:] for d in me.uv_layers.active.data]
print("uv range", min(min(u) for u in uvs), max(max(u) for u in uvs), flush=True)
assert max(max(u) for u in uvs) <= 1.0001, "UV pack failed"
print("joined", len(me.polygons), "faces,", len(me.materials), "materials", flush=True)

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
save_rgb(bc[..., :3] * (0.72 + 0.28 * ao[..., :1]), os.path.join(TEX, BASE + "_BC.png"), True)
save_rgb(np.concatenate([ao[..., :1], r[..., :1], mm[..., :1]], 2), os.path.join(TEX, BASE + "_ORM.png"), False)
nd = n[..., :3].copy(); nd[..., 1] = 1 - nd[..., 1]; save_rgb(nd, os.path.join(TEX, BASE + "_N.png"), False)
print("baked", flush=True)
for i in list(bpy.data.images):
    if i.name in ("bc", "r", "m", "n", "ao") or i.name.startswith(BASE): bpy.data.images.remove(i)
for i in bpy.data.images:
    if i.filepath and not i.packed_file: i.pack()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "SecurityGuard.blend"), compress=True)

# one material slot for Unreal
mat = bpy.data.materials.new("M_SecurityGuard")
for p in me.polygons: p.material_index = 0
me.materials.clear(); me.materials.append(mat)
select_only([arm, ob], arm)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SK_SecurityGuard.fbx"), use_selection=True,
    object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, use_armature_deform_only=False,
    primary_bone_axis='Y', secondary_bone_axis='X', bake_anim=False, path_mode='STRIP', use_tspace=True)
print("exported", len(me.polygons), "faces", flush=True)
