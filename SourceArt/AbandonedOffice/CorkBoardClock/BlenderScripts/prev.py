import bpy, sys, math, os
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0])
sc = bpy.context.scene
bpy.ops.mesh.primitive_plane_add(size=8); fl = bpy.context.active_object
fm = bpy.data.materials.new("fl"); fm.use_nodes = True; fn = fm.node_tree
nz = fn.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 200
cr = fn.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.10, 0.10, 0.10, 1); cr.color_ramp.elements[1].color = (0.2, 0.2, 0.19, 1)
fn.links.new(nz.outputs[0], cr.inputs[0]); fn.links.new(cr.outputs[0], fn.nodes["Principled BSDF"].inputs["Base Color"])
fl.data.materials.append(fm)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, float(os.environ.get("WALLY", 0.33)), 4), rotation=(math.pi / 2, 0, 0)); wl = bpy.context.active_object
wm = bpy.data.materials.new("wall"); wm.use_nodes = True
wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35, 0.35, 0.34, 1); wl.data.materials.append(wm)
bpy.ops.object.light_add(type='AREA', location=(1.2, -1.8, 2.6)); l = bpy.context.active_object
l.data.energy = 90; l.data.size = 2.0; l.rotation_euler = (math.radians(40), 0, math.radians(30))
bpy.ops.object.light_add(type='AREA', location=(-1.8, -1.0, 1.5)); l2 = bpy.context.active_object
l2.data.energy = 20; l2.data.size = 2.0; l2.rotation_euler = (math.radians(60), 0, math.radians(-60))
cl = tuple(float(v) for v in args[2].split(","))
bpy.ops.object.camera_add(location=cl); cam = bpy.context.active_object; sc.camera = cam; cam.data.lens = float(os.environ.get("LENS", 40))
tz = float(os.environ.get("TGTZ", 0.85))
cam.rotation_euler = (Vector((float(os.environ.get("TGTX", 0)), -0.1, tz)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.17, 0.18, 1)
for o in bpy.data.objects:
    if o.name.startswith("UCX"): o.hide_render = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("SAMPLES", 32)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", 900)), int(os.environ.get("RY", 1200))
sc.view_settings.view_transform = 'AgX'
sc.render.filepath = args[1]
bpy.ops.render.render(write_still=True)
