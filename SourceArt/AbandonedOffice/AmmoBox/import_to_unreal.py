"""
Open ammo crate for the +ammo pickup -> UniversityGame.

Run in Unreal Editor (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/AmmoBox/import_to_unreal.py"

  SM_AmmoBox_Open   olive wooden military crate 62 x 40 x 33 cm, lid swung open, ~200 cartridges inside,
                    nothing outside the crate. Pivot: bottom centre, stencilled front faces +Y.

The script also makes BP_AmmoItem use it:
  * StaticMesh -> SM_AmmoBox_Open (scale 1, sitting on the pickup's origin, no collision of its own - so the player
    walks into the pickup sphere instead of bumping into the crate)
  * pickup sphere radius 30 -> 50 cm, so it covers the bigger crate
  * every BP_AmmoItem already placed in the open level is updated too
Save the level afterwards (Ctrl+S).
"""
import os
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Environment/AbandonedOffice/AmmoBox"
DEST_TEX = DEST + "/Textures"
DEST_MAT = "/Game/_Game/Environment/AbandonedOffice/Materials"
MASTER = "M_AbandonedProp"
BP = "/Game/_Game/Stuff/BonusItems/BP_AmmoItem"
MESH_OFFSET = unreal.Vector(0, 0, 2)      # crate bottom 2 cm above the pickup origin
SPHERE_RADIUS = 50.0

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg):
    unreal.log("[AbandonedOffice] " + msg)


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
    sm.set_editor_property("auto_generate_collision", False)  # UCX hull is in the FBX
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("remove_degenerates", True)
    sm.set_editor_property("build_nanite", False)
    return import_file(os.path.join(SRC, fname), DEST, ui)


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
    return mat


def make_instance(name, master, bc, orm, nrm):
    path = DEST_MAT + "/" + name
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        name, DEST_MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    mel.set_material_instance_texture_parameter_value(mi, "BaseColor", bc)
    mel.set_material_instance_texture_parameter_value(mi, "ORM", orm)
    mel.set_material_instance_texture_parameter_value(mi, "Normal", nrm)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def setup_components(mesh_comp, sphere_comp, mesh):
    mesh_comp.set_editor_property("static_mesh", mesh)
    mesh_comp.set_editor_property("relative_location", MESH_OFFSET)
    mesh_comp.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 0))
    mesh_comp.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
    try:                                                   # as a property, so the blueprint template keeps it
        bi = mesh_comp.get_editor_property("body_instance")
        bi.set_editor_property("collision_profile_name", "NoCollision")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
        mesh_comp.set_editor_property("body_instance", bi)
    except Exception as e:
        log("collision via body_instance failed (%s)" % e)
    mesh_comp.set_collision_profile_name("NoCollision")
    if sphere_comp is not None:
        sphere_comp.set_editor_property("sphere_radius", SPHERE_RADIUS)


def templates_of(bp):
    """component templates of a blueprint, including the ones declared in C++ (AAmmoItem)"""
    found = {}
    try:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for h in sds.k2_gather_subobject_data_for_blueprint(bp):
            data = sds.k2_find_subobject_data_from_handle(h)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data) if data else None
            if isinstance(obj, unreal.StaticMeshComponent) and "mesh" not in found:
                found["mesh"] = obj
            elif isinstance(obj, unreal.SphereComponent) and "sphere" not in found:
                found["sphere"] = obj
    except Exception as e:
        log("subobject lookup failed (%s) - using the class default object" % e)
    if "mesh" not in found:
        cdo = unreal.get_default_object(bp.generated_class())
        found["mesh"] = cdo.get_component_by_class(unreal.StaticMeshComponent)
        found["sphere"] = cdo.get_component_by_class(unreal.SphereComponent)
    return found.get("mesh"), found.get("sphere")


def update_pickup(mesh):
    bp = eal.load_asset(BP)
    if bp is None:
        log("BP_AmmoItem not found at " + BP + " - assign SM_AmmoBox_Open by hand"); return
    mc, sc = templates_of(bp)
    if mc is None:
        log("no StaticMeshComponent in BP_AmmoItem - assign SM_AmmoBox_Open by hand"); return
    setup_components(mc, sc, mesh)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    eal.save_loaded_asset(bp)
    log("BP_AmmoItem now uses SM_AmmoBox_Open (pickup radius %.0f cm)" % SPHERE_RADIUS)
    n = 0
    for a in eas.get_all_level_actors():
        if a.get_class().get_name() == "BP_AmmoItem_C":
            setup_components(a.get_component_by_class(unreal.StaticMeshComponent),
                             a.get_component_by_class(unreal.SphereComponent), mesh)
            n += 1
    log("updated %d BP_AmmoItem actor(s) in the level - save it with Ctrl+S" % n)


def main():
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        bc = import_texture("T_AmmoBox_BC.png", "color")
        orm = import_texture("T_AmmoBox_ORM.png", "masks")
        nrm = import_texture("T_AmmoBox_N.png", "normal")
        master = get_or_create_master(bc, orm, nrm)
        mi = make_instance("MI_AmmoBox", master, bc, orm, nrm)
        mesh = import_mesh("SM_AmmoBox_Open.fbx")
        for i in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(i, mi)
        eal.save_loaded_asset(mesh)
        log("imported " + mesh.get_path_name())
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    update_pickup(mesh)
    eal.sync_browser_to_objects([mesh.get_path_name()])


main()
