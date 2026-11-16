"""
Security guard, step 0: export the soldiers' mannequin (mesh + skeleton) to FBX, so the guard's uniform is modelled in
Blender exactly on this body and skinned to the same skeleton (then every soldier animation works on it).

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/SecurityGuard/export_mannequin.py"

Writes SourceArt/AbandonedOffice/SecurityGuard/Mannequin/SK_Mannequin_Enemy.fbx (nothing in the project is changed).
"""
import os
import unreal

MESH = "/Game/_Game/Enemies/SK_Mannequin_Enemy"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Mannequin", "SK_Mannequin_Enemy.fbx")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
mesh = unreal.EditorAssetLibrary.load_asset(MESH)
if mesh is None:
    raise RuntimeError("not found: " + MESH)

opt = unreal.FbxExportOption()
opt.set_editor_property("ascii", False)
opt.set_editor_property("force_front_x_axis", False)
opt.set_editor_property("level_of_detail", False)
opt.set_editor_property("collision", False)
opt.set_editor_property("export_morph_targets", False)

task = unreal.AssetExportTask()
task.set_editor_property("object", mesh)
task.set_editor_property("filename", OUT)
task.set_editor_property("automated", True)
task.set_editor_property("prompt", False)
task.set_editor_property("replace_identical", True)
task.set_editor_property("options", opt)
ok = unreal.Exporter.run_asset_export_task(task)
unreal.log("[SecurityGuard] mannequin export %s -> %s" % ("OK" if ok else "FAILED", OUT))
