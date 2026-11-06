"""preview: room with a ceiling at 2.8 m. args: <blend> <out.png> <camx,camy,camz> <tgtx,tgty,tgtz>"""
import bpy, sys, math, os
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0])
sc = bpy.context.scene
def plane(size, loc, rot, col, name):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc, rotation=rot); p = bpy.context.active_object; p.name = name
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = col; b.inputs["Roughness"].default_value = 0.9
    p.data.materials.append(m); return p, nt, b
fl, fnt, fb = plane(10, (0, 0, 0), (0, 0, 0), (0.12, 0.12, 0.115, 1), "floor")
cz = float(os.environ.get("CEILZ", 2.8))
ce, cnt, cb = plane(10, (0, 0, cz), (math.pi, 0, 0), (0.58, 0.57, 0.54, 1), "ceil")
# ceiling grid lines every 0.6 m, with holes where the damage pieces are (cells at x=0 and x=1.6 -> use 0.0/1.8 grid)
tc = cnt.nodes.new("ShaderNodeTexCoord"); sep = cnt.nodes.new("ShaderNodeSeparateXYZ"); cnt.links.new(tc.outputs["Object"], sep.inputs[0])
def grid(sock):
    a = cnt.nodes.new("ShaderNodeMath"); a.operation = 'ADD'; a.inputs[1].default_value = 0.3; cnt.links.new(sock, a.inputs[0])
    w = cnt.nodes.new("ShaderNodeMath"); w.operation = 'PINGPONG'; w.inputs[1].default_value = 0.3; cnt.links.new(a.outputs[0], w.inputs[0])
    l = cnt.nodes.new("ShaderNodeMath"); l.operation = 'LESS_THAN'; l.inputs[1].default_value = 0.012; cnt.links.new(w.outputs[0], l.inputs[0])
    return l.outputs[0]
mx = cnt.nodes.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'
cnt.links.new(grid(sep.outputs[0]), mx.inputs[0]); cnt.links.new(grid(sep.outputs[1]), mx.inputs[1])
mix = cnt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; cnt.links.new(mx.outputs[0], mix.inputs[0])
mix.inputs[6].default_value = (0.58, 0.57, 0.54, 1); mix.inputs[7].default_value = (0.62, 0.62, 0.6, 1)
cnt.links.new(mix.outputs[2], cb.inputs["Base Color"])
bpy.ops.object.light_add(type='AREA', location=(-1.5, -2.0, 1.4)); l = bpy.context.active_object
l.data.energy = 160; l.data.size = 2.5; l.rotation_euler = (math.radians(-60), math.radians(30), 0)
bpy.ops.object.light_add(type='AREA', location=(2.5, -1.0, 2.2)); l2 = bpy.context.active_object
l2.data.energy = 70; l2.data.size = 1.5; l2.rotation_euler = (math.radians(70), 0, math.radians(60))
bpy.ops.object.light_add(type='POINT', location=(0.8, -0.8, 0.8)); l3 = bpy.context.active_object; l3.data.energy = 40
cl = Vector(tuple(float(v) for v in args[2].split(","))); tg = Vector(tuple(float(v) for v in args[3].split(",")))
bpy.ops.object.camera_add(location=cl); cam = bpy.context.active_object; sc.camera = cam; cam.data.lens = float(os.environ.get("LENS", 30))
cam.rotation_euler = (tg - cl).to_track_quat('-Z', 'Y').to_euler()
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.1, 0.1, 0.11, 1)
for o in bpy.data.objects:
    if o.name.startswith("UCX"): o.hide_render = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("SAMPLES", 32)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", 1200)), int(os.environ.get("RY", 900))
sc.view_settings.view_transform = 'AgX'
sc.render.filepath = args[1]
bpy.ops.render.render(write_still=True)
