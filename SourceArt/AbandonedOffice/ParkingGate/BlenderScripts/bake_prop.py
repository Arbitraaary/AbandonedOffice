"""Bake + export a parking prop.
python3.11 bake_prop.py -- <stage.blend> <out_dir> <res> <SM_Name> <barrier|booth>
barrier: one material slot; collision hulls built from part groups.
booth:   slot 0 baked, slot 1 = glass (keeps its GlassUV atlas); collision from the UCX_ objects in the stage.
"""
import bpy, bmesh, sys, os, math
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT, RES, NAME, MODE = args[0], args[1], int(args[2]), args[3], args[4]
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

def hull(name, pts):
    bm = bmesh.new()
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); sc.collection.objects.link(o); o.display_type = 'WIRE'; o.hide_render = True
    return o

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
ucx = [o for o in meshes if o.name.startswith("UCX_")]
glass = [o for o in meshes if not o.name.startswith("UCX_") and o.data.materials and o.data.materials[0].name == "M_Glass"]
solid = [o for o in meshes if o not in ucx and o not in glass]

if MODE == "barrier":
    def pts(prefixes):
        return [o.matrix_world @ v.co for o in solid if o.name.startswith(prefixes) for v in o.data.vertices]
    housing = pts(("Pad", "Housing", "Cap", "Plinth", "Door", "Lock", "Vent", "LampBase", "Lamp", "Hub", "Counter", "Weight"))
    ucx = [hull(f"UCX_{NAME}_00", housing[::max(1, len(housing) // 300)]),
           hull(f"UCX_{NAME}_01", pts(("ArmStub",))),
           hull(f"UCX_{NAME}_02", pts(("ArmPiece", "ArmEndCap")))]

select_only(solid); bpy.ops.object.join()
ob = bpy.context.active_object; ob.name = ob.data.name = NAME; me = ob.data
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
    for g in glass: g.hide_render = True              # glass must not occlude the AO bake
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

for o in ucx: o.hide_render = True
base = NAME.replace("SM_", "T_")
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
for g in glass: g.hide_render = False
for o in ucx: o.parent = ob
for i in bpy.data.images:
    if i.filepath and not i.packed_file: i.pack()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME.replace("SM_", "") + ".blend"), compress=True)

# FBX: slot 0 baked, slot 1 glass (booth); single UV channel
m_main = bpy.data.materials.new("M_" + NAME[3:])
for p in me.polygons: p.material_index = 0
me.materials[0] = m_main
while len(me.materials) > 1: me.materials.pop(index=len(me.materials) - 1)
export_objs = [ob]
if glass:
    m_glass = bpy.data.materials.new("M_" + NAME[3:] + "_Glass")
    for g in glass:
        gm = g.data
        gm.materials[0] = m_glass
        bl = gm.uv_layers.get("BakeUV") or gm.uv_layers.new(name="BakeUV")
        src = gm.uv_layers["GlassUV"]
        for i in range(len(gm.loops)): bl.data[i].uv = src.data[i].uv
    select_only([ob] + glass); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()
    me = ob.data
for l in [l.name for l in me.uv_layers if l.name != "BakeUV"]: me.uv_layers.remove(me.uv_layers[l])
select_only([ob])
for o in ucx: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, NAME + ".fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
    mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_tspace=True)
print("exported tris", sum(len(p.vertices) - 2 for p in me.polygons), "dims", tuple(round(d, 3) for d in ob.dimensions),
      "slots", [m.name for m in me.materials], "ucx", len(ucx))
