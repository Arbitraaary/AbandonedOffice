import bpy, sys
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0])
m = bpy.data.materials.get("M_ChainLink")
m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "ChainUV"
t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load("/home/claude/exterior/tex/T_ChainLink.png")
nt.links.new(uv.outputs[0], t.inputs[0]); nt.links.new(t.outputs[0], b.inputs["Base Color"]); nt.links.new(t.outputs[1], b.inputs["Alpha"])
b.inputs["Metallic"].default_value = 0.6; b.inputs["Roughness"].default_value = 0.5
t.image.pack()
bpy.ops.wm.save_as_mainfile(filepath=args[1])
