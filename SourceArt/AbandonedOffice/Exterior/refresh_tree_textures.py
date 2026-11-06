"""
Re-import the brighter tree textures over the existing ones (T_Foliage, T_Bark_*). Materials pick them up
automatically - no need to re-run place_exterior.py.

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Exterior/refresh_tree_textures.py"
"""
import os
import unreal

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Textures")
DEST = "/Game/_Game/Environment/AbandonedOffice/Exterior/Textures"
FILES = [("T_Foliage.png", "color"), ("T_Bark_BC.png", "color"), ("T_Bark_N.png", "normal"), ("T_Bark_ORM.png", "masks")]
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
done = []
for fname, kind in FILES:
    task = unreal.AssetImportTask()
    task.filename = os.path.join(SRC, fname)
    task.destination_path = DEST
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    if not paths:
        unreal.log_warning("[AbandonedOffice] could not import " + fname); continue
    tex = eal.load_asset(paths[0])
    if kind == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", False)
    elif kind == "masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    eal.save_loaded_asset(tex)
    done.append(fname)
unreal.log("[AbandonedOffice] refreshed " + ", ".join(done))
