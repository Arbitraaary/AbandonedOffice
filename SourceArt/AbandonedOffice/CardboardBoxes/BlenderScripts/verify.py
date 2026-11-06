import bpy, os, sys
D = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
m = bpy.data.materials.new("v"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
def tex(s, nc):
    n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(D, "Textures", f"T_CardboardBoxes_{s}.png"))
    if nc: n.image.colorspace_settings.name = 'Non-Color'
    return n
bc, orm, nm = tex("BC", 0), tex("ORM", 1), tex("N", 1)
nt.links.new(bc.outputs[0], b.inputs["Base Color"])
sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(orm.outputs[0], sp.inputs[0])
nt.links.new(sp.outputs[1], b.inputs["Roughness"]); nt.links.new(sp.outputs[2], b.inputs["Metallic"])
sn = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(nm.outputs[0], sn.inputs[0])
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; nt.links.new(sn.outputs[1], inv.inputs[1])
cc = nt.nodes.new("ShaderNodeCombineColor"); nt.links.new(sn.outputs[0], cc.inputs[0]); nt.links.new(inv.outputs[0], cc.inputs[1]); nt.links.new(sn.outputs[2], cc.inputs[2])
nmp = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(cc.outputs[0], nmp.inputs["Color"]); nt.links.new(nmp.outputs[0], b.inputs["Normal"])
layout = {"SM_Box_Closed": (0.0, 0.0, 0.0), "SM_Box_Open": (0.75, 0.05, 0.0), "SM_Box_Crushed": (-0.8, 0.0, 0.0)}
for name, loc in layout.items():
    bpy.ops.import_scene.fbx(filepath=os.path.join(D, name + ".fbx"))
    for o in bpy.context.selected_objects:
        print(o.name, tuple(round(d, 3) for d in o.dimensions), [x.name for x in o.data.materials])
        if o.name.startswith("UCX"): o.hide_render = True
        else:
            o.data.materials.clear(); o.data.materials.append(m)
        if o.parent is None: o.location = loc
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/boxes/out/verify.blend")
