"""Low-poly A4 sheet for Unreal (Blender 4.2).
python3.11 build_sheet.py -- <tex_dir> <out_dir>
"""
import bpy, bmesh, math, os, sys
args = sys.argv[sys.argv.index("--") + 1:]
TEX, OUT = [os.path.abspath(a) for a in args[:2]]
os.makedirs(OUT, exist_ok=True)
W, H, T = 0.210, 0.297, 0.0003
NX, NY = 8, 11
A = 1024.0

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def height(x, y):
    u, v = x / W + 0.5, y / H + 0.5
    z = 0.0025 * math.sin(u * 2.6 + 0.4) * math.sin(v * 2.1)          # gentle wave
    z += 0.004 * (1 - abs(v - 0.5) * 2)                                  # old fold, reopened
    c = max(0.0, (u + v) - 1.45)                                          # curled corner
    z += 0.09 * c * c
    return z

bm = bmesh.new()
uv = bm.loops.layers.uv.new("UVMap")
top, bot = {}, {}
for j in range(NY + 1):
    for i in range(NX + 1):
        x, y = (i / NX - 0.5) * W, (j / NY - 0.5) * H
        z = height(x, y)
        top[i, j] = bm.verts.new((x, y, z + T))
        bot[i, j] = bm.verts.new((x, y, z))

def fuv(x, y):            # front page region
    return ((x / W + 0.5) * 724 / A, y / H + 0.5)
def buv(x, y):            # back side region (mirrored)
    return ((730 + (0.5 - x / W) * 290) / A, 1 - 410 / A + (y / H + 0.5) * 410 / A)
EDGE = (875 / A, 1 - 430 / A)

def face(vs, uvs):
    f = bm.faces.new(vs)
    for l, t in zip(f.loops, uvs):
        l[uv].uv = t
for j in range(NY):
    for i in range(NX):
        q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        face([top[k] for k in q], [fuv(top[k].co.x, top[k].co.y) for k in q])
        r = q[::-1]
        face([bot[k] for k in r], [buv(bot[k].co.x, bot[k].co.y) for k in r])
ring = [(i, 0) for i in range(NX)] + [(NX, j) for j in range(NY)] + \
       [(i, NY) for i in range(NX, 0, -1)] + [(0, j) for j in range(NY, 0, -1)]
for k in range(len(ring)):
    a, b = ring[k], ring[(k + 1) % len(ring)]
    face([bot[a], bot[b], top[b], top[a]], [EDGE] * 4)
zmin = min(v.co.z for v in bm.verts)
for v in bm.verts: v.co.z -= zmin
me = bpy.data.meshes.new("SM_PaperA4"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new("SM_PaperA4", me); sc.collection.objects.link(ob)

# collision: thin box
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co.x *= W; v.co.y *= H; v.co.z = (v.co.z + 0.5) * 0.003
cm = bpy.data.meshes.new("UCX"); bm.to_mesh(cm); bm.free()
ucx = bpy.data.objects.new("UCX_SM_PaperA4_00", cm); sc.collection.objects.link(ucx)
ucx.display_type = 'WIRE'; ucx.hide_render = True; ucx.parent = ob

# material for Blender (variant A); Unreal gets A/B/C instances from the import script
m = bpy.data.materials.new("M_PaperA4"); m.use_nodes = True
nt = m.node_tree; b = nt.nodes["Principled BSDF"]
def tex(name, nc):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(os.path.join(TEX, name)); n.image.pack()
    if nc: n.image.colorspace_settings.name = 'Non-Color'
    return n
bc = tex("T_PaperA4_A_BC.png", False); orm = tex("T_PaperA4_ORM.png", True); nm = tex("T_PaperA4_N.png", True)
nt.links.new(bc.outputs[0], b.inputs["Base Color"])
sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(orm.outputs[0], sp.inputs[0])
nt.links.new(sp.outputs[1], b.inputs["Roughness"])
sn = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(nm.outputs[0], sn.inputs[0])
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
nt.links.new(sn.outputs[1], inv.inputs[1])                # DirectX -> OpenGL for Blender
cc = nt.nodes.new("ShaderNodeCombineColor")
nt.links.new(sn.outputs[0], cc.inputs[0]); nt.links.new(inv.outputs[0], cc.inputs[1]); nt.links.new(sn.outputs[2], cc.inputs[2])
nmap = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(cc.outputs[0], nmap.inputs["Color"])
nt.links.new(nmap.outputs[0], b.inputs["Normal"])
me.materials.append(m)
print("tris", sum(len(p.vertices) - 2 for p in me.polygons), "dims", tuple(round(d, 4) for d in ob.dimensions))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "PaperA4.blend"), compress=True)
for o in bpy.context.view_layer.objects: o.select_set(False)
ob.select_set(True); ucx.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, "SM_PaperA4.fbx"), use_selection=True, object_types={'MESH'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
    mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', use_tspace=True)
print("exported")
