"""Re-export SM_FilingCabinet.fbx from FilingCabinet.blend (fixes UCX_01 to the open drawer only)."""
import bpy, sys, os
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0]); OUT = args[1]
ob = bpy.data.objects["SM_FilingCabinet"]; me = ob.data
pts = [v.co for v in me.vertices if v.co.y < -0.36]          # open drawer front + its handle
x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
y0 = min(p.y for p in pts); z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
u1 = bpy.data.objects["UCX_SM_FilingCabinet_01"]
import bmesh
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((x0 if v.co.x < 0 else x1, y0 if v.co.y < 0 else -0.316, z0 if v.co.z < 0 else z1))
bm.to_mesh(u1.data); bm.free()
print("UCX_01", round(x1 - x0, 3), round(-0.316 - y0, 3), round(z1 - z0, 3))
bpy.ops.wm.save_as_mainfile(filepath=args[0], compress=True)
mat = bpy.data.materials.new("M_FilingCabinet")
for p in me.polygons: p.material_index = 0
me.materials[0] = mat
while len(me.materials) > 1: me.materials.pop(index=len(me.materials) - 1)
me.uv_layers.remove(me.uv_layers["LabelUV"])
for o in bpy.context.view_layer.objects: o.select_set(False)
ob.select_set(True); bpy.context.view_layer.objects.active = ob
for o in bpy.data.objects:
    if o.name.startswith("UCX_"): o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_FilingCabinet.fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
    mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_tspace=True)
print("exported")
