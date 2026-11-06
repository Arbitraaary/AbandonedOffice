"""Export SM_AbandonedTrashBin.fbx from AbandonedTrashBin.blend (2 slots: Metal / Paper)."""
import bpy, sys, os
args = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT = args
bpy.ops.wm.open_mainfile(filepath=BLEND)
ob = bpy.data.objects["SM_AbandonedTrashBin"]; me = ob.data
ucx = next(o for o in bpy.data.objects if o.name.startswith("UCX_"))
m_metal = bpy.data.materials.new("M_TrashBin_Metal"); m_paper = bpy.data.materials.new("M_TrashBin_Paper")
paper = [bool(m and m.name.startswith("M_Paper")) for m in me.materials]
n_before = sum(paper[p.material_index] for p in me.polygons)
for p in me.polygons:
    p.material_index = 1 if paper[p.material_index] else 0
me.materials[0] = m_metal; me.materials[1] = m_paper
while len(me.materials) > 2:
    me.materials.pop(index=len(me.materials) - 1)
n_after = sum(p.material_index == 1 for p in me.polygons)
print("paper faces", n_before, "->", n_after, "slots", [m.name for m in me.materials])
assert n_before == n_after > 0
me.uv_layers.remove(me.uv_layers["PaperUV"])
for o in bpy.context.view_layer.objects: o.select_set(False)
ob.select_set(True); ucx.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, "SM_AbandonedTrashBin.fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
    mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
    path_mode='STRIP', use_tspace=True)
print("exported")
