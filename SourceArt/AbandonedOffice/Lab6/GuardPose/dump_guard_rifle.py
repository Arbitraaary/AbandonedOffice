"""
Lab 6: data for building the guard's "rifle lowered in one hand" pose in Blender.
Writes guard_rifle_data.json and AR4.fbx next to this file. Changes nothing in the project.
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Lab6/GuardPose/dump_guard_rifle.py"
"""
import json
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
eal = unreal.EditorAssetLibrary
out = {}


def tr(t):
    q = t.rotation
    return {"loc": [t.translation.x, t.translation.y, t.translation.z],
            "quat": [q.x, q.y, q.z, q.w],
            "scale": [t.scale3d.x, t.scale3d.y, t.scale3d.z]}


guard = eal.load_asset("/Game/_Game/Enemies/SecurityGuard/Meshes/SK_SecurityGuard")
for name in ("hand_r_val_socket", "hand_r_venra_socket"):
    s = guard.find_socket(name) if guard else None
    if s:
        out[name] = {"bone": str(s.get_editor_property("bone_name")),
                     "loc": [s.relative_location.x, s.relative_location.y, s.relative_location.z],
                     "rot": [s.relative_rotation.roll, s.relative_rotation.pitch, s.relative_rotation.yaw],
                     "scale": [s.relative_scale.x, s.relative_scale.y, s.relative_scale.z]}

# the rifle blueprint: mesh component placement inside the weapon actor
bp = eal.load_asset("/Game/_Game/Weapons/BP_GuardRifle")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = sds.k2_find_subobject_data_from_handle(h)
    o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d) if d else None
    if isinstance(o, unreal.SkeletalMeshComponent):
        m = o.get_skeletal_mesh_asset()
        out["rifle_component"] = {"mesh": m.get_path_name() if m else None,
                                  "loc": list(o.get_editor_property("relative_location").to_tuple()),
                                  "rot": [o.get_editor_property("relative_rotation").roll,
                                          o.get_editor_property("relative_rotation").pitch,
                                          o.get_editor_property("relative_rotation").yaw],
                                  "scale": list(o.get_editor_property("relative_scale3d").to_tuple())}

# rifle-at-the-hip pose (frame 0) of the bones the new pose changes, local space
idle = eal.load_asset("/Game/AnimStarterPack/Idle_Rifle_Hip")
bones = ["root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head",
         "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r"]
for side in ("l", "r"):
    for f in ("thumb", "index", "middle", "ring", "pinky"):
        for i in (1, 2, 3):
            bones.append("%s_%02d_%s" % (f, i, side))
out["idle_rifle_hip"] = {}
for b in bones:
    try:
        out["idle_rifle_hip"][b] = tr(unreal.AnimationLibrary.get_bone_pose_for_frame(idle, b, 0, False))
    except Exception as e:
        unreal.log_warning("[Lab6] %s: %s" % (b, e))

with open(os.path.join(HERE, "guard_rifle_data.json"), "w") as f:
    json.dump(out, f, indent=1)

# the rifle model, for the preview render in Blender
rifle_mesh = out.get("rifle_component", {}).get("mesh")
if rifle_mesh:
    task = unreal.AssetExportTask()
    task.object = eal.load_asset(rifle_mesh)
    task.filename = os.path.join(HERE, "AR4.fbx")
    task.automated = True
    task.replace_identical = True
    task.prompt = False
    task.exporter = unreal.SkeletalMeshExporterFBX()
    unreal.Exporter.run_asset_export_task(task)
unreal.log("[Lab6] written: %s (sockets: %s, rifle: %s, pose bones: %d)" % (
    HERE, [k for k in out if k.endswith("socket")], rifle_mesh, len(out["idle_rifle_hip"])))
