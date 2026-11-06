"""
Exterior kit for the abandoned office -> UniversityGame (parking lot pieces, trees, bushes, weeds).

Run in Unreal Editor (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Exterior/import_to_unreal.py"
(place_exterior.py runs this automatically when the meshes are missing.)

Imports into /Game/_Game/Environment/AbandonedOffice/Exterior:
  SM_AsphaltTile_8m      8x8 m cracked asphalt slab, tiling texture (MI_Asphalt)
  SM_ParkingLine         5 m worn paint stripe (no collision)          \
  SM_Curb                2 m concrete curb                              > MI_ParkingKit
  SM_WheelStop(_Broken)  concrete parking blocks                       /
  SM_Tree_Broadleaf_A/B, SM_Tree_Dead, SM_Bush, SM_Weeds_Grass, SM_Weeds_Tall, SM_GrassPatch_A/B
  SM_Fence_Panel(_Damaged), SM_Fence_Post, SM_FenceGate_8m, SM_StreetLamp(_Broken), SM_JerseyBarrier,
  SM_Dumpster, SM_Container20       slot M_GroundsKit -> MI_GroundsKit, slot M_ChainLink -> MI_ChainLink (masked)
                         slot M_Bark -> MI_Bark (tiling bark), slot M_Foliage -> MI_Foliage
A masked two-sided-foliage master M_AbandonedFoliage (with light wind) is created once, plus
M_AbandonedGround - world-aligned dry grass / bare dirt material for the landscape (place_exterior.py assigns it).
"""
import os
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Environment/AbandonedOffice/Exterior"
DEST_TEX = DEST + "/Textures"
DEST_MAT = "/Game/_Game/Environment/AbandonedOffice/Materials"
MASTER = "M_AbandonedProp"
FOLIAGE_MASTER = "M_AbandonedFoliage"
PARKING = ["SM_ParkingLine", "SM_Curb", "SM_WheelStop", "SM_WheelStop_Broken"]
TREES = ["SM_Tree_Broadleaf_A", "SM_Tree_Broadleaf_B", "SM_Tree_Dead", "SM_Bush", "SM_Weeds_Grass", "SM_Weeds_Tall",
         "SM_GrassPatch_A", "SM_GrassPatch_B"]
GROUND = "M_AbandonedGround"
MASKED_MASTER = "M_AbandonedMasked"
GROUNDS = ["SM_Fence_Panel", "SM_Fence_PanelDamaged", "SM_Fence_Post", "SM_FenceGate_8m", "SM_StreetLamp", "SM_StreetLamp_Broken",
           "SM_JerseyBarrier", "SM_Dumpster", "SM_Container20"]
WIND_FUNCS = ["/Engine/Functions/Engine_MaterialFunctions01/WorldPositionOffset/SimpleGrassWind",
              "/Engine/Engine_MaterialFunctions01/WorldPositionOffset/SimpleGrassWind"]

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
    sm.set_editor_property("auto_generate_collision", False)  # UCX hulls come with the FBX
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("remove_degenerates", True)
    sm.set_editor_property("build_nanite", False)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)   # keep the soft foliage normals
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

def add_wind(mat):
    """plain-node sway -> World Position Offset"""
    E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)
    # gentle sway built from plain nodes (no SimpleGrassWind: its required inputs broke the compile)
    #   WPO = (1, 0.6, 0.15) * Amp * sin(Time * Speed + dot(WorldPos, (0.004, 0.003, 0.002)))
    t = E(unreal.MaterialExpressionTime, -1100, 450)
    spd = E(unreal.MaterialExpressionScalarParameter, -1100, 520)
    spd.set_editor_property("parameter_name", "WindSpeed"); spd.set_editor_property("default_value", 1.4)
    ts = E(unreal.MaterialExpressionMultiply, -900, 470)
    mel.connect_material_expressions(t, "", ts, "A"); mel.connect_material_expressions(spd, "", ts, "B")
    wp = E(unreal.MaterialExpressionWorldPosition, -1100, 620)
    k = E(unreal.MaterialExpressionConstant3Vector, -1100, 700)
    k.set_editor_property("constant", unreal.LinearColor(0.004, 0.003, 0.002, 0))
    dp = E(unreal.MaterialExpressionDotProduct, -900, 640)
    mel.connect_material_expressions(wp, "", dp, "A"); mel.connect_material_expressions(k, "", dp, "B")
    ph = E(unreal.MaterialExpressionAdd, -750, 520)
    mel.connect_material_expressions(ts, "", ph, "A"); mel.connect_material_expressions(dp, "", ph, "B")
    sn = E(unreal.MaterialExpressionSine, -620, 520)
    sn.set_editor_property("period", 6.283185)
    mel.connect_material_expressions(ph, "", sn, "")
    amp = E(unreal.MaterialExpressionScalarParameter, -620, 620)
    amp.set_editor_property("parameter_name", "WindAmplitude"); amp.set_editor_property("default_value", 2.5)
    m1 = E(unreal.MaterialExpressionMultiply, -480, 560)
    mel.connect_material_expressions(sn, "", m1, "A"); mel.connect_material_expressions(amp, "", m1, "B")
    dirv = E(unreal.MaterialExpressionConstant3Vector, -480, 680)
    dirv.set_editor_property("constant", unreal.LinearColor(1.0, 0.6, 0.15, 0))
    m2 = E(unreal.MaterialExpressionMultiply, -330, 600)
    mel.connect_material_expressions(m1, "", m2, "A"); mel.connect_material_expressions(dirv, "", m2, "B")
    mel.connect_material_property(m2, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    return True


def get_or_create_foliage_master(tex):
    path = DEST_MAT + "/" + FOLIAGE_MASTER
    if eal.does_asset_exist(path):
        mat = eal.load_asset(path)
        if mel.get_material_property_input_node(mat, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) is None and add_wind(mat):
            mel.recompile_material(mat); eal.save_loaded_asset(mat); log("added wind to " + path)
        return mat
    mat = tools.create_asset(FOLIAGE_MASTER, DEST_MAT, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("opacity_mask_clip_value", 0.4)
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    except Exception as e:
        log("two-sided foliage shading not set (%s) - using default lit" % e)
    s = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
    s.set_editor_property("parameter_name", "Foliage")
    s.set_editor_property("texture", tex)
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, -250)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, -150)
    mel.connect_material_expressions(s, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(s, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    sss = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 100)
    mel.connect_material_expressions(mul, "", sss, "A")
    sss.set_editor_property("const_b", 0.6)
    mel.connect_material_property(sss, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -400, 250)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.75)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    add_wind(mat)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    log("created foliage master " + path)
    return mat


def foliage_instance(master, tex):
    path = DEST_MAT + "/MI_Foliage"
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        "MI_Foliage", DEST_MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    mel.set_material_instance_texture_parameter_value(mi, "Foliage", tex)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def create_ground_material():
    """world-aligned (no UVs needed - works on any landscape): grass 4 m, dirt 2.5 m, dirt patches + macro variation from a 50 m mask"""
    path = DEST_MAT + "/" + GROUND
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    gbc, gn = import_texture("T_GroundGrass_BC.png", "color"), import_texture("T_GroundGrass_N.png", "normal")
    dbc, dn = import_texture("T_GroundDirt_BC.png", "color"), import_texture("T_GroundDirt_N.png", "normal")
    mk = import_texture("T_GroundMask.png", "masks")
    mat = tools.create_asset(GROUND, DEST_MAT, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)
    wp = E(unreal.MaterialExpressionWorldPosition, -1600, 0)
    rg = E(unreal.MaterialExpressionComponentMask, -1400, 0)
    rg.set_editor_property("r", True); rg.set_editor_property("g", True)
    rg.set_editor_property("b", False); rg.set_editor_property("a", False)
    mel.connect_material_expressions(wp, "", rg, "")

    def uv(scale, y):
        dv = E(unreal.MaterialExpressionDivide, -1200, y)
        mel.connect_material_expressions(rg, "", dv, "A"); dv.set_editor_property("const_b", scale)
        return dv

    def sample(tex, stype, uvn, y, name=None):
        if name:
            t = E(unreal.MaterialExpressionTextureSampleParameter2D, -900, y); t.set_editor_property("parameter_name", name)
        else:
            t = E(unreal.MaterialExpressionTextureSample, -900, y)
        t.set_editor_property("texture", tex); t.set_editor_property("sampler_type", stype)
        mel.connect_material_expressions(uvn, "", t, "UVs")
        return t
    C, N, MK = unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
    u_g, u_d, u_m = uv(400.0, -300), uv(250.0, 200), uv(5000.0, 600)
    s_gbc, s_gn = sample(gbc, C, u_g, -400, "GrassColor"), sample(gn, N, u_g, -150)
    s_dbc, s_dn = sample(dbc, C, u_d, 150, "DirtColor"), sample(dn, N, u_d, 400)
    s_mk = sample(mk, MK, u_m, 650)
    lc = E(unreal.MaterialExpressionLinearInterpolate, -500, -250)
    mel.connect_material_expressions(s_gbc, "RGB", lc, "A"); mel.connect_material_expressions(s_dbc, "RGB", lc, "B")
    mel.connect_material_expressions(s_mk, "R", lc, "Alpha")
    bright = E(unreal.MaterialExpressionLinearInterpolate, -500, 650)                 # macro brightness 0.8 .. 1.1
    bright.set_editor_property("const_a", 0.8); bright.set_editor_property("const_b", 1.1)
    mel.connect_material_expressions(s_mk, "G", bright, "Alpha")
    mul = E(unreal.MaterialExpressionMultiply, -300, -150)
    mel.connect_material_expressions(lc, "", mul, "A"); mel.connect_material_expressions(bright, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    ln = E(unreal.MaterialExpressionLinearInterpolate, -500, 250)
    mel.connect_material_expressions(s_gn, "RGB", ln, "A"); mel.connect_material_expressions(s_dn, "RGB", ln, "B")
    mel.connect_material_expressions(s_mk, "R", ln, "Alpha")
    mel.connect_material_property(ln, "", unreal.MaterialProperty.MP_NORMAL)
    rough = E(unreal.MaterialExpressionConstant, -300, 450); rough.set_editor_property("r", 0.95)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    log("created landscape material " + path)
    return mat


def masked_instance(name, tex, rough=0.5, metal=0.5):
    path = DEST_MAT + "/" + MASKED_MASTER
    if eal.does_asset_exist(path):
        master = eal.load_asset(path)
    else:
        master = tools.create_asset(MASKED_MASTER, DEST_MAT, unreal.Material, unreal.MaterialFactoryNew())
        master.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        master.set_editor_property("two_sided", True)
        master.set_editor_property("opacity_mask_clip_value", 0.35)
        t = mel.create_material_expression(master, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
        t.set_editor_property("parameter_name", "BaseColor")
        t.set_editor_property("texture", tex)
        mel.connect_material_property(t, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(t, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
        for k, (pn, val, prop) in enumerate((("Roughness", rough, unreal.MaterialProperty.MP_ROUGHNESS),
                                             ("Metallic", metal, unreal.MaterialProperty.MP_METALLIC))):
            sp = mel.create_material_expression(master, unreal.MaterialExpressionScalarParameter, -300, 250 + 100 * k)
            sp.set_editor_property("parameter_name", pn); sp.set_editor_property("default_value", val)
            mel.connect_material_property(sp, "", prop)
        mel.recompile_material(master); eal.save_loaded_asset(master)
        log("created masked master " + path)
    mpath = DEST_MAT + "/" + name
    mi = eal.load_asset(mpath) if eal.does_asset_exist(mpath) else tools.create_asset(
        name, DEST_MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    mel.set_material_instance_texture_parameter_value(mi, "BaseColor", tex)
    mel.update_material_instance(mi); eal.save_loaded_asset(mi)
    return mi


def add_lods(mesh):
    """auto LODs for the trees (hundreds of them on the map)"""
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        opts = unreal.StaticMeshReductionOptions(False, [unreal.StaticMeshReductionSettings(1.0, 1.0),
                                                         unreal.StaticMeshReductionSettings(0.5, 0.35),
                                                         unreal.StaticMeshReductionSettings(0.25, 0.15),
                                                         unreal.StaticMeshReductionSettings(0.12, 0.06)])
        sub.set_lods(mesh, opts)
    except Exception as e:
        log("LODs skipped for %s (%s)" % (mesh.get_name(), e))


def textures(base):
    return (import_texture(base + "_BC.png", "color"), import_texture(base + "_ORM.png", "masks"),
            import_texture(base + "_N.png", "normal"))


def main():
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    meshes = []
    try:
        kit = textures("T_ParkingKit")
        master = get_or_create_master(*kit)
        mi_kit = make_instance("MI_ParkingKit", master, *kit)
        mi_asph = make_instance("MI_Asphalt", master, *textures("T_Asphalt"))
        mi_bark = make_instance("MI_Bark", master, *textures("T_Bark"))
        ft = import_texture("T_Foliage.png", "color")
        mi_fol = foliage_instance(get_or_create_foliage_master(ft), ft)
        create_ground_material()
        mi_grounds = make_instance("MI_GroundsKit", master, *textures("T_GroundsKit"))
        mi_chain = masked_instance("MI_ChainLink", import_texture("T_ChainLink.png", "color"))
        for n in PARKING + ["SM_AsphaltTile_8m"] + TREES + GROUNDS:
            mesh = import_mesh(n + ".fbx")
            for i, slot in enumerate(mesh.get_editor_property("static_materials")):
                sname = str(slot.get_editor_property("material_slot_name"))
                if n in TREES:
                    mi = mi_fol if "Foliage" in sname else mi_bark
                elif n in GROUNDS:
                    mi = mi_chain if "ChainLink" in sname else mi_grounds
                else:
                    mi = mi_asph if n == "SM_AsphaltTile_8m" else mi_kit
                mesh.set_material(i, mi)
            if n.startswith(("SM_Tree", "SM_Bush")):
                add_lods(mesh)
            eal.save_loaded_asset(mesh)
            meshes.append(mesh.get_path_name())
            log("imported " + mesh.get_path_name())
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    eal.sync_browser_to_objects(meshes)
    log("exterior kit imported - run place_exterior.py to lay out the grounds")


main()
