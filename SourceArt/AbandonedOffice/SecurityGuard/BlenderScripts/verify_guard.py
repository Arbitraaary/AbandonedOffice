"""Re-import out/SK_SecurityGuard.fbx with the baked textures and render front/back (checks the export)."""
import bpy, os, math
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.dirname(HERE); TEX = os.path.join(OUT, "Textures")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, "SK_SecurityGuard.fbx"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); ob = next(o for o in bpy.data.objects if o.type == 'MESH')
print("bones", len(arm.data.bones), "groups", len(ob.vertex_groups), "faces", len(ob.data.polygons),
      "ngons", sum(len(p.vertices) > 4 for p in ob.data.polygons), "dims", tuple(round(d, 2) for d in ob.dimensions))
m = ob.data.materials[0]; m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
def tex(n, nc):
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(TEX, "T_SecurityGuard_%s.png" % n))
    if nc: t.image.colorspace_settings.name = 'Non-Color'
    return t
nt.links.new(tex("BC", 0).outputs[0], b.inputs["Base Color"])
orm = tex("ORM", 1); sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(orm.outputs[0], sep.inputs[0])
nt.links.new(sep.outputs[1], b.inputs["Roughness"]); nt.links.new(sep.outputs[2], b.inputs["Metallic"])
# pose test: rotate an arm so we see skinning works
pb = arm.pose.bones.get("upperarm_l")
if pb: pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, math.radians(-35))
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE_NEXT'; sc.render.resolution_x = 1400; sc.render.resolution_y = 1000
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.52, 0.55, 1)
for loc, e in (((2, -3, 3), 3), ((-3, 3, 2.5), 2)):
    L = bpy.data.lights.new("L", 'SUN'); L.energy = e; lo = bpy.data.objects.new("L", L); sc.collection.objects.link(lo)
    lo.rotation_euler = (Vector((0, 0, 1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
c = bpy.data.cameras.new("C"); c.type = 'ORTHO'; c.ortho_scale = 2.9; co = bpy.data.objects.new("C", c); sc.collection.objects.link(co); sc.camera = co
import os as _o
Z = float(_o.environ.get("VZ", 0.95)); c.ortho_scale = float(_o.environ.get("VS", c.ortho_scale)); PFX = _o.environ.get("VP", "v")
for name, y in ((PFX + "front", -4), (PFX + "back", 4)):
    co.location = (0, y, Z); co.rotation_euler = (Vector((0, 0, Z)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, "_work", name + ".png"); bpy.ops.render.render(write_still=True)
