import bpy, os, sys
D = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name, glass=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    def tex(s, nc):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(D, "Textures", f"T_WaterCooler_{s}.png"))
        if nc: n.image.colorspace_settings.name = 'Non-Color'
        return n
    if glass:
        g = tex("Glass", 0); nt.links.new(g.outputs[0], b.inputs["Base Color"]); nt.links.new(g.outputs[1], b.inputs["Alpha"])
        b.inputs["Roughness"].default_value = 0.2; return m
    bc, orm, nm = tex("BC", 0), tex("ORM", 1), tex("N", 1)
    nt.links.new(bc.outputs[0], b.inputs["Base Color"])
    sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(orm.outputs[0], sp.inputs[0])
    nt.links.new(sp.outputs[1], b.inputs["Roughness"]); nt.links.new(sp.outputs[2], b.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(nm.outputs[0], sn.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; nt.links.new(sn.outputs[1], inv.inputs[1])
    cc = nt.nodes.new("ShaderNodeCombineColor"); nt.links.new(sn.outputs[0], cc.inputs[0]); nt.links.new(inv.outputs[0], cc.inputs[1]); nt.links.new(sn.outputs[2], cc.inputs[2])
    nmp = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(cc.outputs[0], nmp.inputs["Color"]); nt.links.new(nmp.outputs[0], b.inputs["Normal"])
    return m
mb, mg = mat("baked"), mat("glass", True)
bpy.ops.import_scene.fbx(filepath=os.path.join(D, "SM_WaterCooler.fbx"))
for o in bpy.context.selected_objects:
    print(o.name, tuple(round(d, 3) for d in o.dimensions), [x.name for x in o.data.materials])
    if o.name.startswith("UCX"): o.hide_render = True; continue
    for i, s in enumerate(o.data.materials):
        o.data.materials[i] = mg if "Glass" in s.name else mb
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/cooler/out/verify.blend")
