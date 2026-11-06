import bpy, sys, os
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0])
for o in bpy.data.objects: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=args[1], use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False,
    bake_anim=False, path_mode='STRIP', use_tspace=True)
