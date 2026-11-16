"""
Lab 5, step 1b: import the security guard skeletal mesh into UniversityGame.

Run in Unreal Editor (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/SecurityGuard/import_to_unreal.py"

  SK_SecurityGuard   security guard on the soldiers' skeleton (UE4_Mannequin_Skeleton):
                     light-blue shirt, navy trousers, black vest with SECURITY, cap with a badge,
                     sunglasses, belt with holster + radio, boots. Every soldier animation works on it.
Creates /Game/_Game/Enemies/SecurityGuard/{Meshes/SK_SecurityGuard (+ physics asset), Materials/MI_SecurityGuard, Textures/*}.
Nothing else in the project is changed.
"""
import os
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Enemies/SecurityGuard"
DEST_TEX = DEST + "/Textures"
DEST_MESH = DEST + "/Meshes"
DEST_MAT = DEST + "/Materials"
SKELETON = "/Game/AnimStarterPack/UE4_Mannequin/Mesh/UE4_Mannequin_Skeleton"
SOLDIER = "/Game/_Game/Enemies/SK_Mannequin_Enemy"      # sockets are copied from it
MASTER = "/Game/_Game/Environment/AbandonedOffice/Materials/M_AbandonedProp"

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg):
    unreal.log("[Lab5] " + msg)


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
    for p in paths:                                   # skeletal import also returns physics asset etc.
        a = eal.load_asset(p)
        if isinstance(a, (unreal.SkeletalMesh, unreal.Texture2D)):
            return a
    return eal.load_asset(paths[0])


def import_texture(fname, kind):
    tex = import_file(os.path.join(SRC, "Textures", fname), DEST_TEX)
    if kind == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", False)   # already DirectX
    elif kind == "masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    eal.save_loaded_asset(tex)
    return tex


def import_mesh():
    skel = eal.load_asset(SKELETON)
    if skel is None:
        raise RuntimeError("skeleton not found: " + SKELETON)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("skeleton", skel)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", True)
    sk = ui.get_editor_property("skeletal_mesh_import_data")
    sk.set_editor_property("import_morph_targets", False)
    sk.set_editor_property("update_skeleton_reference_pose", False)
    sk.set_editor_property("use_t0_as_ref_pose", False)
    sk.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    return import_file(os.path.join(SRC, "SK_SecurityGuard.fbx"), DEST_MESH, ui)


def make_instance(master, bc, orm, nrm):
    path = DEST_MAT + "/MI_SecurityGuard"
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        "MI_SecurityGuard", DEST_MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, master)
    mel.set_material_instance_texture_parameter_value(mi, "BaseColor", bc)
    mel.set_material_instance_texture_parameter_value(mi, "ORM", orm)
    mel.set_material_instance_texture_parameter_value(mi, "Normal", nrm)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def main():
    master = eal.load_asset(MASTER)
    if master is None:
        raise RuntimeError("master material not found: " + MASTER)
    master_mat = master if isinstance(master, unreal.Material) else master.get_base_material()
    # the ammo-crate master material must also be allowed on skeletal meshes
    if not master_mat.get_editor_property("used_with_skeletal_mesh"):
        master_mat.set_editor_property("used_with_skeletal_mesh", True)
        mel.recompile_material(master_mat)
        eal.save_loaded_asset(master_mat)
        log("M_AbandonedProp: Used with Skeletal Mesh = on")

    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        bc = import_texture("T_SecurityGuard_BC.png", "color")
        orm = import_texture("T_SecurityGuard_ORM.png", "masks")
        nrm = import_texture("T_SecurityGuard_N.png", "normal")
        mi = make_instance(master, bc, orm, nrm)
        mesh = import_mesh()
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")

    mesh.modify()
    mats = mesh.get_editor_property("materials")
    for i in range(len(mats)):                   # items are copies: change one, then write it back
        m = mats[i]
        m.set_editor_property("material_interface", mi)
        mats[i] = m
    mesh.set_editor_property("materials", mats)

    # weapon sockets like on the soldier mesh (weapon is attached in C++ by socket name).
    # Sockets saved on the shared skeleton are found automatically, only mesh-only ones are copied.
    copied = copy_sockets(eal.load_asset(SOLDIER), mesh)
    eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    pa = mesh.get_editor_property("physics_asset")
    if pa is not None:
        eal.save_asset(pa.get_path_name(), only_if_is_dirty=False)
    log("imported %s, skeleton %s, sockets copied: %s" % (
        mesh.get_path_name(), mesh.get_editor_property("skeleton").get_name(), ", ".join(copied) or "-"))
    eal.sync_browser_to_objects([mesh.get_path_name()])


def copy_sockets(src, dst):
    """'sockets' is protected in Python, so go through num_sockets / get_socket_by_index / find_socket / add_socket"""
    copied = []
    if src is None:
        log("soldier mesh not found: " + SOLDIER)
        return copied
    for i in range(src.num_sockets()):
        s = src.get_socket_by_index(i)
        name = s.get_editor_property("socket_name")
        if dst.find_socket(name) is not None:
            log("socket %s: already available on the guard" % name)
            continue
        ns = unreal.SkeletalMeshSocket(outer=dst)
        for prop in ("socket_name", "bone_name", "relative_location", "relative_rotation", "relative_scale"):
            ns.set_editor_property(prop, s.get_editor_property(prop))
        dst.add_socket(ns, False)
        copied.append(str(name))
    return copied


if __name__ == "__main__":
    main()
