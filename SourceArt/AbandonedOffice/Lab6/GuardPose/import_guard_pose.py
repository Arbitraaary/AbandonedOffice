"""
Lab 6: imports the guard's "rifle lowered in one hand" animation (made in Blender, GuardRifleLowered.blend)
onto the soldiers' skeleton. Run in Unreal (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Lab6/GuardPose/import_guard_pose.py"
Creates /Game/_Game/Enemies/SecurityGuard/Animations/A_Guard_RifleLowered (2 s loop).
"""
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Enemies/SecurityGuard/Animations"
SKELETON = "/Game/AnimStarterPack/UE4_Mannequin/Mesh/UE4_Mannequin_Skeleton"
eal = unreal.EditorAssetLibrary

ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", False)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("import_animations", True)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
ui.set_editor_property("skeleton", eal.load_asset(SKELETON))
anim = ui.get_editor_property("anim_sequence_import_data")
anim.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
anim.set_editor_property("import_bone_tracks", True)
anim.set_editor_property("remove_redundant_keys", False)

task = unreal.AssetImportTask()
task.filename = os.path.join(HERE, "A_Guard_RifleLowered.fbx")
task.destination_path = DEST
task.destination_name = "A_Guard_RifleLowered"
task.automated = True
task.replace_existing = True
task.save = True
task.options = ui
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
try:
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
finally:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")

paths = [p for p in task.imported_object_paths]
seq = None
for p in paths:
    a = eal.load_asset(p)
    if isinstance(a, unreal.AnimSequence):
        seq = a
if seq is None:
    raise RuntimeError("import failed: " + str(paths))
eal.save_asset(seq.get_path_name(), only_if_is_dirty=False)
unreal.log("[Lab6] imported %s, length %.2f s, skeleton %s" % (seq.get_path_name(), seq.get_play_length(),
                                                             seq.get_editor_property("skeleton").get_name()))
eal.sync_browser_to_objects([seq.get_path_name()])
