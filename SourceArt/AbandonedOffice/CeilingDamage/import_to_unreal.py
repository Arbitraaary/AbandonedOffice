"""
Ceiling damage kit for the abandoned office -> UniversityGame.

Run in Unreal Editor (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/CeilingDamage/import_to_unreal.py"

Imports into /Game/_Game/Environment/AbandonedOffice/Ceiling (all share MI_CeilingDamage):
  SM_CeilingHole_Hanging   missing 60x60 tile: dark hole, torn tile edges, snapped T-bar hanging down,
                           a tile swung down on one edge, 4 cables with stripped copper ends + a sagging loop
  SM_CeilingHole_Cables    half a tile broken out, 6 cables, a cable loop, corrugated conduit with loose wires
  SM_CeilingTiles_Fallen   on the floor: a sagged whole tile, a tile broken in 3, crumbs

How to place the hole pieces:
  pivot = the ceiling surface at the centre of one 60x60 cell, everything hangs below it.
  Put the actor exactly at the height of the ceiling (Z of the SM_roof underside), Rotation 0,
  then snap X/Y so the frame lines up with the tile grid painted on the ceiling (grid step 60).
  Drop SM_CeilingTiles_Fallen on the floor right below.
Collision: hanging tile and fallen pieces have convex hulls; cables, wires and the frame have none,
so the player walks through the cables. Nothing is placed in the level automatically.
"""
import os
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Environment/AbandonedOffice/Ceiling"
DEST_TEX = DEST + "/Textures"
DEST_MAT = "/Game/_Game/Environment/AbandonedOffice/Materials"
MASTER = "M_AbandonedProp"
NAMES = ["SM_CeilingHole_Hanging", "SM_CeilingHole_Cables", "SM_CeilingTiles_Fallen"]

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg):
    unreal.log("[AbandonedOffice] " + msg)


# ---------------------------------------------------------------- import helpers
def import_file(path, dest, options=None):
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = dest
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    tools.import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    if not paths:
        raise RuntimeError("Import failed: " + path)
    return eal.load_asset(paths[0])


def import_texture(fname, kind):
    tex = import_file(os.path.join(SRC, "Textures", fname), DEST_TEX)
    if kind == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", False)  # already DirectX
    elif kind == "masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    eal.save_loaded_asset(tex)
    return tex


def import_mesh(fname):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)  # never wrap the cables in a box
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("remove_degenerates", True)
    sm.set_editor_property("build_nanite", False)
    return import_file(os.path.join(SRC, fname), DEST, ui)


# ---------------------------------------------------------------- materials
def get_or_create_master(bc, orm, nrm):
    path = DEST_MAT + "/" + MASTER
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    mat = tools.create_asset(MASTER, DEST_MAT, unreal.Material, unreal.MaterialFactoryNew())

    def sampler(name, tex, stype, y):
        e = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, y)
        e.set_editor_property("parameter_name", name)
        e.set_editor_property("texture", tex)
        e.set_editor_property("sampler_type", stype)
        return e

    e_bc = sampler("BaseColor", bc, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -300)
    e_orm = sampler("ORM", orm, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 0)
    e_n = sampler("Normal", nrm, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 300)
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -500, -500)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, -350)
    mel.connect_material_expressions(e_bc, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(e_orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    mel.connect_material_property(e_orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(e_orm, "B", unreal.MaterialProperty.MP_METALLIC)
    mel.connect_material_property(e_n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    log("created master material " + path)
    return mat


def make_instance(name, master, bc, orm, nrm):
    path = DEST_MAT + "/" + name
    if eal.does_asset_exist(path):
        mi = eal.load_asset(path)
    else:
        mi = tools.create_asset(name, DEST_MAT, unreal.MaterialInstanceConstant,
                                unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    mel.set_material_instance_texture_parameter_value(mi, "BaseColor", bc)
    mel.set_material_instance_texture_parameter_value(mi, "ORM", orm)
    mel.set_material_instance_texture_parameter_value(mi, "Normal", nrm)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def main():
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        bc = import_texture("T_CeilingDamage_BC.png", "color")
        orm = import_texture("T_CeilingDamage_ORM.png", "masks")
        nrm = import_texture("T_CeilingDamage_N.png", "normal")
        master = get_or_create_master(bc, orm, nrm)
        mi = make_instance("MI_CeilingDamage", master, bc, orm, nrm)
        meshes = []
        for n in NAMES:
            mesh = import_mesh(n + ".fbx")
            for i in range(len(mesh.get_editor_property("static_materials"))):
                mesh.set_material(i, mi)
            eal.save_loaded_asset(mesh)
            meshes.append(mesh.get_path_name())
            log("imported " + mesh.get_path_name())
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    eal.sync_browser_to_objects(meshes)
    log("done - place the hole pieces at ceiling height on the 60 cm grid, debris on the floor below")


main()
