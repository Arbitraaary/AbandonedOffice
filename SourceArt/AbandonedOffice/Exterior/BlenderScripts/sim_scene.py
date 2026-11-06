"""Build the place_exterior layout in Blender (UE cm -> Blender m, UE y = -Blender y) with the real FBX meshes."""
import bpy, sys, types, math, random, os, runpy
args = sys.argv[sys.argv.index("--") + 1:]
u = types.ModuleType("unreal")
class _Any:
    def __getattr__(self, k): return _Any()
    def __call__(self, *a, **k): return _Any()
u.EditorAssetLibrary = _Any(); u.get_editor_subsystem = lambda *a: _Any(); u.EditorActorSubsystem = None; u.UnrealEditorSubsystem = None
u.log = print; u.log_warning = print; sys.modules["unreal"] = u
mod = runpy.run_path("/home/claude/exterior/place_exterior.py", run_name="test")
bpy.ops.wm.read_factory_settings(use_empty=True)
FBX = {"tile": "out/parking/SM_AsphaltTile_8m.fbx", "line": "out/parking/SM_ParkingLine.fbx", "curb": "out/parking/SM_Curb.fbx",
       "stop": "out/parking/SM_WheelStop.fbx", "stop_broken": "out/parking/SM_WheelStop_Broken.fbx",
       "tree_a": "out/trees/SM_Tree_Broadleaf_A.fbx", "tree_b": "out/trees/SM_Tree_Broadleaf_B.fbx", "tree_dead": "out/trees/SM_Tree_Dead.fbx",
       "bush": "out/trees/SM_Bush.fbx", "weed_grass": "out/trees/SM_Weeds_Grass.fbx", "weed_tall": "out/trees/SM_Weeds_Tall.fbx",
       "booth": "/home/claude/parking/out/booth/SM_GuardBooth.fbx", "barrier": "/home/claude/parking/out/barrier/SM_BoomBarrierBroken.fbx",
       "sign": "/home/claude/psign/out/final/SM_ParkingSignBent.fbx", "cone": "/home/claude/cone/out/final/SM_TrafficCone.fbx",
       "grass_a": "out/trees/SM_GrassPatch_A.fbx", "grass_b": "out/trees/SM_GrassPatch_B.fbx"}
for k, n in (("fence", "SM_Fence_Panel"), ("fence_dmg", "SM_Fence_PanelDamaged"), ("post", "SM_Fence_Post"), ("gate", "SM_FenceGate_8m"),
             ("lamp", "SM_StreetLamp"), ("lamp_broken", "SM_StreetLamp_Broken"), ("jersey", "SM_JerseyBarrier"),
             ("dumpster", "SM_Dumpster"), ("container", "SM_Container20")):
    FBX[k] = "out/grounds/%s.fbx" % n
def tex_mat(name, folder, base, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(folder, base))
    nt.links.new(t.outputs[0], b.inputs["Base Color"])
    if alpha: nt.links.new(t.outputs[1], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.85
    return m
MATS = {"M_Asphalt": tex_mat("asph", "tex", "T_Asphalt_BC.png"), "M_ParkingKit": tex_mat("kit", "out/parking/Textures", "T_ParkingKit_BC.png"),
        "M_Bark": tex_mat("bark", "tex", "T_Bark_BC.png"), "M_Foliage": tex_mat("fol", "tex", "T_Foliage.png", True),
        "M_GroundsKit": tex_mat("gk", "out/grounds/Textures", "T_GroundsKit_BC.png"), "M_ChainLink": tex_mat("cl", "tex", "T_ChainLink.png", True)}
def flat(col):
    m = bpy.data.materials.new("c"); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col; return m
src = {}
for k, p in FBX.items():
    bpy.ops.import_scene.fbx(filepath=p)
    ob = [o for o in bpy.context.selected_objects if not o.name.startswith("UCX")][0]
    for o in bpy.context.selected_objects:
        if o.name.startswith("UCX"): bpy.data.objects.remove(o)
    for i, s in enumerate(ob.data.materials):
        for mk, mv in MATS.items():
            if s and s.name.startswith(mk): ob.data.materials[i] = mv
        if s and s.name.startswith(("M_GuardBooth", "M_BoomBarrier", "M_ParkingSign", "M_TrafficCone")):
            ob.data.materials[i] = flat({"M_Gu": (0.5, 0.5, 0.55, 1), "M_Bo": (0.6, 0.45, 0.05, 1), "M_Pa": (0.1, 0.3, 0.7, 1), "M_Tr": (0.9, 0.35, 0.05, 1)}[s.name[:4]])
    ob.location = (0, 0, -500); src[k] = ob
bmin, bmax = (-1500, -1000), (1500, 1000)
land = tuple(float(v) for v in args[3].split(","))
side, ent = args[0], float(args[1])
cars = [dict(key="car%d" % i, length=450, width=180) for i in range(5)]
items, Z = mod["layout"](bmin, bmax, side, ent, random.Random(int(args[2])), cars, land)
F = Z["frame"]; zl = 0.02
bpy.ops.mesh.primitive_cube_add(size=1); b = bpy.context.active_object
b.scale = ((bmax[0] - bmin[0]) / 100, (bmax[1] - bmin[1]) / 100, 6); b.location = ((bmin[0] + bmax[0]) / 200, -(bmin[1] + bmax[1]) / 200, 3)
b.data.materials.append(flat((0.45, 0.45, 0.47, 1)))
carm = [flat(c) for c in [(0.35, 0.12, 0.06, 1), (0.2, 0.25, 0.3, 1), (0.4, 0.38, 0.3, 1)]]
for it in items:
    x, y = F.world(it["a"], it["d"]) if "a" in it else (it["x"], it["y"])
    z = zl if (it["ground"] == "lot" or it["ground"].startswith("slab")) else 0.0
    k = it["key"]
    if k.startswith("car"):
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.active_object; o.scale = (4.5, 1.8, 1.35)
        o.data.materials.append(carm[int(k[3:]) % 3]); z += 0.7
    else:
        o = src[k].copy(); bpy.context.scene.collection.objects.link(o); o.scale = (it["scale"],) * 3
    o.location = (x / 100, -y / 100, z + (0.17 if it["roll"] and k == "cone" else 0))
    o.rotation_euler = (math.radians(-it["roll"]), 0, math.radians(-it["yaw"]))
for im in bpy.data.images:
    try: im.pack()
    except Exception: pass
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/exterior/out/sim.blend")
print("sim ok", len(items))
