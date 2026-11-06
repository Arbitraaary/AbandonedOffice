"""Bake + export for trash bin v2.
python3.11 bake_v2.py -- <stage_v2_parts.blend> <out_dir> [res]
Produces: SM_AbandonedTrashBin.fbx (2 material slots: M_TrashBin_Metal / M_TrashBin_Paper),
          Textures/T_AbandonedTrashBin_{BC,ORM,N}.png, Textures/T_AbandonedTrashBin_Paper_{BC,ORM,N}.png,
          AbandonedTrashBin.blend (procedural materials, for editing in Blender)
"""
import bpy, sys, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_trashbin as B

args = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT = args[0], args[1]
RES = int(args[2]) if len(args) > 2 else 2048
TEX = os.path.join(OUT, "Textures"); os.makedirs(TEX, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.render.bake.margin = 12; sc.render.bake.use_clear = True

def select_only(objs):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

def join(objs, name):
    select_only(objs)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    ob = bpy.context.active_object; ob.name = name; ob.data.name = name
    return ob

# AO only from nearby geometry (paper deep in the bin must not go black)
if sc.world is None:
    sc.world = bpy.data.worlds.new("BakeWorld")
sc.world.light_settings.distance = 0.04

shell = join([bpy.data.objects["Bin_Body"], bpy.data.objects["Bin_Liner"]], "BinShell")
papers = [o for o in bpy.data.objects if o.type == 'MESH' and o.name != "BinShell"]

# drop paper that can never be seen through the opening (saves texture space + triangles)
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import random as _r
rnd = _r.Random(3)
def bvh(ob):
    me = ob.data.copy(); me.transform(ob.matrix_world)
    import bmesh as _b
    bm = _b.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    t = BVHTree.FromBMesh(bm); bm.free(); return t
trees = {o.name: bvh(o) for o in papers + [shell]}
hits = {o.name: 0 for o in papers}
for _ in range(24000):
    a = rnd.uniform(0, 6.283); rr = 1.4 * math.sqrt(rnd.random())
    eye = Vector((rr * math.cos(a), rr * math.sin(a), rnd.uniform(0.55, 1.8)))
    b = rnd.uniform(0, 6.283); rt = 0.135 * math.sqrt(rnd.random())
    tgt = Vector((rt * math.cos(b), rt * math.sin(b), 0.36))
    d = (tgt - eye).normalized()
    best, who = 1e9, None
    for n, t in trees.items():
        h = t.ray_cast(eye, d)
        if h[0] is not None and h[3] < best:
            best, who = h[3], n
    if who in hits: hits[who] += 1
hidden = [o for o in papers if hits[o.name] == 0]
print("visibility:", {k: v for k, v in sorted(hits.items())})
for o in hidden:
    bpy.data.objects.remove(o)
papers = [o for o in papers if o not in hidden]
print("removed hidden:", len(hidden))

def bake_uv(ob, angle=50, pack=True):
    me = ob.data
    lay = me.uv_layers.get("BakeUV") or me.uv_layers.new(name="BakeUV")
    me.uv_layers.active = lay
    lay.active_render = True
    select_only([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    if angle:
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.003, area_weight=0.0)
    if pack:
        bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
for o in papers:                       # big islands per piece, packed together after the join
    bake_uv(o, angle=80, pack=False)
fill = join(papers, "PaperFill")
fill.data.uv_layers.active = fill.data.uv_layers["BakeUV"]
fill.data.uv_layers["BakeUV"].active_render = True
bake_uv(fill, angle=None, pack=True)
bake_uv(shell)
islands = None

def bsdf_of(mat): return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
def out_of(mat): return next(n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')

def bake(ob, kind, img, channel=None, samples=1):
    sc.cycles.samples = samples
    temp = []
    for mat in ob.data.materials:
        nt = mat.node_tree
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img
        nt.nodes.active = tn; temp.append((mat, tn))
        if kind == 'EMIT':
            b, o = bsdf_of(mat), out_of(mat)
            em = nt.nodes.new("ShaderNodeEmission")
            sock = b.inputs[channel]
            if sock.is_linked:
                nt.links.new(sock.links[0].from_socket, em.inputs[0])
            else:
                v = sock.default_value
                em.inputs[0].default_value = tuple(v) if channel == "Base Color" else (v, v, v, 1)
            nt.links.new(em.outputs[0], o.inputs[0])
            temp.append((mat, em))
    select_only([ob])
    if kind == 'NORMAL':
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
    else:
        bpy.ops.object.bake(type=kind)
    for mat, n in temp:
        mat.node_tree.nodes.remove(n)
    for mat in ob.data.materials:
        mat.node_tree.links.new(bsdf_of(mat).outputs[0], out_of(mat).inputs[0])

def new_img(name, noncolor):
    img = bpy.data.images.new(name, RES, RES, alpha=False)
    img.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return img
def px(img): return np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)
def save_rgb(arr, path, srgb):
    img = bpy.data.images.new(os.path.basename(path), RES, RES, alpha=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    rgba = np.ones((RES, RES, 4), np.float32); rgba[..., :3] = np.clip(arr, 0, 1)
    img.pixels[:] = rgba.ravel(); img.filepath_raw = path; img.file_format = 'PNG'; img.save()

def process(ob, base, ao_mix):
    i_bc = new_img(base + "_bc", False); bake(ob, 'EMIT', i_bc, "Base Color")
    i_r = new_img(base + "_r", True); bake(ob, 'EMIT', i_r, "Roughness")
    i_m = new_img(base + "_m", True); bake(ob, 'EMIT', i_m, "Metallic")
    i_n = new_img(base + "_n", True); bake(ob, 'NORMAL', i_n, samples=4)
    i_ao = new_img(base + "_ao", True); bake(ob, 'AO', i_ao, samples=32)
    bc, r, m, n, ao = (px(i) for i in (i_bc, i_r, i_m, i_n, i_ao))
    aoc = ao[..., :1]
    save_rgb(bc[..., :3] * ((1 - ao_mix) + ao_mix * aoc), os.path.join(TEX, base + "_BC.png"), True)
    save_rgb(np.concatenate([ao[..., :1], r[..., :1], m[..., :1]], 2), os.path.join(TEX, base + "_ORM.png"), False)
    nd = n[..., :3].copy(); nd[..., 1] = 1.0 - nd[..., 1]           # DirectX normal for Unreal
    save_rgb(nd, os.path.join(TEX, base + "_N.png"), False)
    print("baked", base, flush=True)

process(shell, "T_AbandonedTrashBin", 0.35)
process(fill, "T_AbandonedTrashBin_Paper", 0.5)   # paper deep in the bin gets darker

# ------------------------------------------------ editable .blend (procedural materials)
for img in list(bpy.data.images):
    if img.name.startswith("T_"): bpy.data.images.remove(img)
bin_ob = join([shell, fill], "SM_AbandonedTrashBin")
ucx = B.add_collision(bin_ob)
ucx.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "AbandonedTrashBin.blend"))

# ------------------------------------------------ FBX for Unreal
me = bin_ob.data
m_metal = bpy.data.materials.new("M_TrashBin_Metal")
m_paper = bpy.data.materials.new("M_TrashBin_Paper")
paper_idx = {i for i, m in enumerate(me.materials) if m and m.name.startswith("M_Paper")}
for p in me.polygons:
    p.material_index = 1 if p.material_index in paper_idx else 0
me.materials.clear(); me.materials.append(m_metal); me.materials.append(m_paper)
me.uv_layers.remove(me.uv_layers["PaperUV"])          # BakeUV becomes UV channel 0
select_only([bin_ob]); ucx.select_set(True)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, "SM_AbandonedTrashBin.fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
    mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
    path_mode='STRIP', use_tspace=True)
print("exported", len(me.vertices), "verts", sum(len(p.vertices) - 2 for p in me.polygons), "tris")
