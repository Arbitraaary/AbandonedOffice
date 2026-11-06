"""outdoor preview: sun + sky + big ground. args: <blend> <out.png> <cam x,y,z> <tgt x,y,z>"""
import bpy, sys, math, os
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0])
sc = bpy.context.scene
if os.environ.get("GROUND", "1") == "1":
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.01)); g = bpy.context.active_object
    m = bpy.data.materials.new("ground"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.3
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.10, 0.09, 0.06, 1); cr.color_ramp.elements[1].color = (0.16, 0.15, 0.09, 1)
    nt.links.new(nz.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    g.data.materials.append(m)
bpy.ops.object.light_add(type='SUN'); s = bpy.context.active_object; s.data.energy = 3.5; s.data.angle = math.radians(3)
s.rotation_euler = (math.radians(50), math.radians(10), math.radians(float(os.environ.get("SUNAZ", 35))))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.47, 0.55, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
cl = Vector(tuple(float(v) for v in args[2].split(","))); tg = Vector(tuple(float(v) for v in args[3].split(",")))
bpy.ops.object.camera_add(location=cl); cam = bpy.context.active_object; sc.camera = cam; cam.data.lens = float(os.environ.get("LENS", 30))
cam.data.clip_end = 1000
cam.rotation_euler = (tg - cl).to_track_quat('-Z', 'Y').to_euler()
for o in bpy.data.objects:
    if o.name.startswith("UCX"): o.hide_render = True
for m in bpy.data.materials:
    if m.name.startswith("M_Foliage"):
        try: m.blend_method = 'CLIP'
        except Exception: pass
sc.cycles.transparent_max_bounces = 128; sc.cycles.max_bounces = 16
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("SAMPLES", 32)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", 1400)), int(os.environ.get("RY", 800))
sc.view_settings.view_transform = 'AgX'
sc.render.filepath = args[1]
bpy.ops.render.render(write_still=True)
