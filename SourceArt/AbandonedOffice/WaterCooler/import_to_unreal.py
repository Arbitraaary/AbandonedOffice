"""
Abandoned water cooler -> UniversityGame.

Run in Unreal Editor (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/WaterCooler/import_to_unreal.py"

Imports into /Game/_Game/Environment/AbandonedOffice/WaterCooler:
  SM_WaterCooler   floor-standing cooler (31x32x98 cm, 1.55 m with the bottle): empty cracked 19 L bottle,
                   dirty tap alcove, paper cup on the drip tray, 'OUT OF ORDER' note, unplugged cord + plug on the floor
  Slot 0 -> MI_WaterCooler (baked), slot 1 -> MI_WaterCooler_Glass (translucent bottle, uses M_AbandonedGlass).
Pivot: floor under the body centre, the taps face +Y in Unreal; the cord runs out of the back (-Y),
so leave ~45 cm behind it. Collision: body box + bottle hull. Nanite off (translucent slot).
Nothing is placed in the level - drag it from the Content Browser.
"""
import os
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Environment/AbandonedOffice/WaterCooler"
DEST_TEX = DEST + "/Textures"
DEST_MAT = "/Game/_Game/Environment/AbandonedOffice/Materials"
MASTER = "M_AbandonedProp"
GLASS_MASTER = "M_AbandonedGlass"
NAMES = ["SM_WaterCooler"]

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
    sm.set_editor_property("auto_generate_collision", False)  # UCX hulls are in the FBX
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("remove_degenerates", True)
    sm.set_editor_property("build_nanite", False)
    return import_file(os.path.join(SRC, fname), DEST, ui)


# ---------------------------------------------------------------- materials
def get_or_create_glass_master(tex):
    path = DEST_MAT + "/" + GLASS_MASTER
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    mat = tools.create_asset(GLASS_MASTER, DEST_MAT, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    mat.set_editor_property("two_sided", True)
    s = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
    s.set_editor_property("parameter_name", "Glass")
    s.set_editor_property("texture", tex)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -300, 250)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.12)
    mel.connect_material_property(s, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(s, "A", unreal.MaterialProperty.MP_OPACITY)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    log("created translucent master " + path)
    return mat


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
        bc = import_texture("T_WaterCooler_BC.png", "color")
        orm = import_texture("T_WaterCooler_ORM.png", "masks")
        nrm = import_texture("T_WaterCooler_N.png", "normal")
        master = get_or_create_master(bc, orm, nrm)
        mi = make_instance("MI_WaterCooler", master, bc, orm, nrm)
        gt = import_texture("T_WaterCooler_Glass.png", "color")
        gm = get_or_create_glass_master(gt)
        gpath = DEST_MAT + "/MI_WaterCooler_Glass"
        mi_glass = eal.load_asset(gpath) if eal.does_asset_exist(gpath) else tools.create_asset(
            "MI_WaterCooler_Glass", DEST_MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi_glass, gm)
        mel.set_material_instance_texture_parameter_value(mi_glass, "Glass", gt)
        mel.set_material_instance_scalar_parameter_value(mi_glass, "Roughness", 0.2)
        mel.update_material_instance(mi_glass)
        eal.save_loaded_asset(mi_glass)
        meshes = []
        for n in NAMES:
            mesh = import_mesh(n + ".fbx")
            for i, slot in enumerate(mesh.get_editor_property("static_materials")):
                name = str(slot.get_editor_property("material_slot_name"))
                mesh.set_material(i, mi_glass if "Glass" in name else mi)
            eal.save_loaded_asset(mesh)
            meshes.append(mesh.get_path_name())
            log("imported " + mesh.get_path_name())
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    eal.sync_browser_to_objects(meshes)
    log("done - drag SM_WaterCooler from the Content Browser into the office")


main()
