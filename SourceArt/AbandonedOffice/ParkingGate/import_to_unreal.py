"""
Guard booth + broken boom barrier for the parking lot -> UniversityGame.

Run in Unreal Editor (Output Log -> Cmd), level open:
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/ParkingGate/import_to_unreal.py"

Imports into /Game/_Game/Environment/AbandonedOffice/Parking:
  SM_GuardBooth          MI_GuardBooth + MI_GuardBooth_Glass (translucent, cracks/hole in the alpha)
  SM_BoomBarrierBroken   MI_BoomBarrierBroken
A translucent master M_AbandonedGlass is created once (two-sided, per-pixel lit).
If they are not in the level yet: the booth goes ~8 m in front of the viewport camera facing it,
the barrier to its right with the arm across the road. Ctrl+Z undoes it; save with Ctrl+S.
"""
import os
import math
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Environment/AbandonedOffice/Parking"
DEST_TEX = DEST + "/Textures"
DEST_MAT = "/Game/_Game/Environment/AbandonedOffice/Materials"
MASTER = "M_AbandonedProp"
GLASS_MASTER = "M_AbandonedGlass"

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


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
    sm.set_editor_property("auto_generate_collision", True)   # only used if there is no UCX_
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("remove_degenerates", True)
    sm.set_editor_property("build_nanite", False)   # booth has translucent glass (no Nanite)
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


def floor_point(world, p, fallback_z):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(p.x, p.y, p.z + 150), unreal.Vector(p.x, p.y, p.z - 3000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        return unreal.Vector(p.x, p.y, fallback_z), False
    try:
        return hit.get_editor_property("impact_point"), True
    except Exception:
        return hit.to_tuple()[5], True



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


def mesh_of(actor):
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp is None:
        return ""
    sm = comp.get_editor_property("static_mesh")
    return sm.get_path_name() if sm else ""


def build(name, glass=False):
    bc = import_texture("T_%s_BC.png" % name, "color")
    orm = import_texture("T_%s_ORM.png" % name, "masks")
    nrm = import_texture("T_%s_N.png" % name, "normal")
    master = get_or_create_master(bc, orm, nrm)
    mi = make_instance("MI_" + name, master, bc, orm, nrm)
    mi_glass = None
    if glass:
        gt = import_texture("T_%s_Glass.png" % name, "color")
        gm = get_or_create_glass_master(gt)
        path = DEST_MAT + "/MI_%s_Glass" % name
        mi_glass = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
            "MI_%s_Glass" % name, DEST_MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi_glass, gm)
        mel.set_material_instance_texture_parameter_value(mi_glass, "Glass", gt)
        mel.update_material_instance(mi_glass)
        eal.save_loaded_asset(mi_glass)
    mesh = import_mesh("SM_%s.fbx" % name)
    for i, s in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(s.get_editor_property("material_slot_name"))
        mesh.set_material(i, mi_glass if (mi_glass and "Glass" in slot) else mi)
    eal.save_loaded_asset(mesh)
    log("imported " + mesh.get_path_name())
    return mesh


def place(booth, barrier):
    placed = {mesh_of(a) for a in eas.get_all_level_actors()}
    world = ues.get_editor_world()
    cam = ues.get_level_viewport_camera_info()
    cam_loc, cam_rot = cam if cam else (unreal.Vector(0, 0, 150), unreal.Rotator(0, 0, 0))
    fwd = cam_rot.get_forward_vector()
    fwd = unreal.Vector(fwd.x, fwd.y, 0)
    fwd = fwd.normal() if fwd.length() > 0.01 else unreal.Vector(1, 0, 0)
    right = unreal.Vector(-fwd.y, fwd.x, 0)
    face_cam = math.degrees(math.atan2(-fwd.y, -fwd.x)) - 90.0      # booth window (+Y in Unreal) towards the camera
    arm_right = math.degrees(math.atan2(right.y, right.x))          # barrier arm (+X) across the road
    jobs = [(booth, cam_loc + fwd * 800.0, face_cam, "GuardBooth"),
            (barrier, cam_loc + fwd * 650.0 + right * 160.0, arm_right, "BoomBarrierBroken")]
    new = []
    with unreal.ScopedEditorTransaction("Place parking gate"):
        for mesh, spot, yaw, label in jobs:
            if mesh.get_path_name() in placed:
                log(label + " already in the level - updated in place")
                continue
            loc, ok = floor_point(world, spot, cam_loc.z - 170)
            a = eas.spawn_actor_from_object(mesh, loc, unreal.Rotator(0, 0, yaw))
            a.set_actor_label(label)
            a.set_folder_path("AbandonedOffice/Parking")
            a.set_editor_property("tags", ["AbandonedOffice"])
            new.append(a)
        if new:
            eas.set_selected_level_actors(new)
    log("placed %d actor(s)" % len(new))


def main():
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        booth = build("GuardBooth", glass=True)
        barrier = build("BoomBarrierBroken")
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    place(booth, barrier)
    log("done - save the level with Ctrl+S")


main()
