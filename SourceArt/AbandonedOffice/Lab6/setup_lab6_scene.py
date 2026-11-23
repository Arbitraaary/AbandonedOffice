"""
Lab 6, task 3 (animated scene objects). Build the C++ first (AHangingLamp, AFlickeringLights, ASlidingGlassDoor),
then in Unreal (Output Log -> Cmd):

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Lab6/setup_lab6_scene.py"

  * imports SK_FluorescentLamp from SK_HangingLamp.fbx (made and animated in Blender: skeletal mesh + A_FluorescentLamp_Swing) with MI_HangingLamp,
    makes M_LampTube (emissive, scalar parameter "Glow" for the flicker)
  * hangs the lamp from the lobby ceiling (Lobby_HangingLamp)
  * Lobby_FlickeringLights: a few existing ceiling lamps / movable lights flicker
  * Lobby_AutoDoor: automatic sliding glass door in the lobby entrance frame; the two old swing leaves
    (SM_Door_1_A3, SM_Door_1_A4) are only hidden in game and lose their collision (nothing is deleted)
Running it again rebuilds the Lab 6 actors (tag Lab6). Save the level afterwards (Ctrl+S).
"""
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "HangingLamp")
DEST = "/Game/_Game/Environment/AbandonedOffice/Animated/HangingLamp"
DEST_TEX = DEST + "/Textures"
MESH_NAME = "SK_FluorescentLamp"           # fresh names: the first import (SK_HangingLamp) came in with a 100x too small rig
ANIM_NAME = "A_FluorescentLamp_Swing"
OLD_ASSETS = ["A_HangingLamp_Swing", "SK_HangingLamp", "SK_HangingLamp_Skeleton", "SK_HangingLamp_PhysicsAsset"]
MASTER = "/Game/_Game/Environment/AbandonedOffice/Materials/M_AbandonedProp"
TAG = "Lab6"
FOLDER = "AbandonedOffice/Lab6"
# where the lamp may hang (lobby, west to east); the first spot with nothing in the way of the lamp is used
LAMP_SPOTS = [(-1600.0, 1050.0), (-1450.0, 1050.0), (-1750.0, 1000.0), (-1600.0, 900.0), (-1400.0, 900.0),
              (-1900.0, 1000.0), (-950.0, 1000.0), (-800.0, 1150.0), (-2100.0, 1150.0)]
LAMP_DROP = 225.0          # the lamp + the dangling cable reach this far below the ceiling (cm)
LAMP_SWING = 45.0          # half-size of the free space it needs round it while swinging (cm)
FLICKER_TARGETS = ["BP_Light_1", "BP_Light_2", "BP_Light_3", "RectLight", "RectLight2", "BP_Light_14", "BP_Light_15", "RectLight4"]
FRAME_LABEL = "SM_Door_Frame_2"
OLD_LEAVES = ["SM_Door_1_A3", "SM_Door_1_A4"]
GLASS_LABEL = "SM_glass_1"

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def log(m):
    unreal.log("[Lab6] " + m)


def warn(m):
    unreal.log_warning("[Lab6] " + m)


def need_class(path):
    cls = unreal.load_class(None, path)
    if cls is None:
        raise RuntimeError("C++ class %s not found - build the project first" % path)
    return cls


def import_task(path, dest, options=None):
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
    return [eal.load_asset(p) for p in paths]


def import_texture(fname, kind):
    tex = import_task(os.path.join(SRC, "Textures", fname), DEST_TEX)[0]
    if kind == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
    elif kind == "masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
    eal.save_asset(tex.get_path_name(), only_if_is_dirty=False)
    return tex


def tube_material():
    """the fluorescent tubes: emissive, brightness = Glow (the flicker drives it)"""
    path = DEST + "/M_LampTube"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    mat = tools.create_asset("M_LampTube", DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -600, 0)
    col.set_editor_property("constant", unreal.LinearColor(0.85, 0.93, 1.0, 1.0))
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -600, 150)
    glow.set_editor_property("parameter_name", "Glow")
    glow.set_editor_property("default_value", 1.0)
    k = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -600, 260)
    k.set_editor_property("r", 25.0)
    m1 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 100)
    m2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -220, 50)
    mel.connect_material_expressions(glow, "", m1, "A")
    mel.connect_material_expressions(k, "", m1, "B")
    mel.connect_material_expressions(col, "", m2, "A")
    mel.connect_material_expressions(m1, "", m2, "B")
    mel.connect_material_property(m2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    base = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, -150)
    base.set_editor_property("constant", unreal.LinearColor(0.9, 0.92, 0.95, 1.0))
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, -260)
    rough.set_editor_property("r", 0.2)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def fix_anim_name(mesh):
    """an animation import into a new name also makes a stray copy of the mesh under that name and calls the
    animation <name>_Anim: delete the copy, give the animation its proper name"""
    path = DEST + "/" + ANIM_NAME
    a = eal.load_asset(path) if eal.does_asset_exist(path) else None
    if isinstance(a, unreal.AnimSequence):
        return a
    anim_path = path + "_Anim"
    if not eal.does_asset_exist(anim_path):
        return None
    anim = eal.load_asset(anim_path)
    try:
        anim.set_preview_skeletal_mesh(mesh)
    except Exception:
        pass
    eal.save_asset(anim_path, only_if_is_dirty=False)
    for junk in (path, path + "_PhysicsAsset"):
        if eal.does_asset_exist(junk):
            if eal.delete_asset(junk):
                log("deleted the stray copy " + junk.split("/")[-1])
            else:
                warn("could not delete " + junk + " - delete it by hand")
    if eal.does_asset_exist(path):
        return anim
    eal.rename_asset(anim_path, path)
    return eal.load_asset(path)


def import_lamp():
    bc = import_texture("T_HangingLamp_BC.png", "color")
    orm = import_texture("T_HangingLamp_ORM.png", "masks")
    nrm = import_texture("T_HangingLamp_N.png", "normal")
    path = DEST + "/MI_HangingLamp"
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        "MI_HangingLamp", DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, eal.load_asset(MASTER))
    mel.set_material_instance_texture_parameter_value(mi, "BaseColor", bc)
    mel.set_material_instance_texture_parameter_value(mi, "ORM", orm)
    mel.set_material_instance_texture_parameter_value(mi, "Normal", nrm)
    mel.update_material_instance(mi)
    eal.save_asset(mi.get_path_name(), only_if_is_dirty=False)
    tube = tube_material()

    fbx = os.path.join(SRC, "SK_HangingLamp.fbx")
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", False)
    skel_path = DEST + "/" + MESH_NAME + "_Skeleton"
    if eal.does_asset_exist(skel_path):                      # re-import onto its own skeleton
        ui.set_editor_property("skeleton", eal.load_asset(skel_path))
    sk = ui.get_editor_property("skeletal_mesh_import_data")
    sk.set_editor_property("import_morph_targets", False)
    sk.set_editor_property("update_skeleton_reference_pose", True)
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        mt = unreal.AssetImportTask()
        mt.filename = fbx
        mt.destination_path = DEST
        mt.destination_name = MESH_NAME
        mt.automated = True
        mt.replace_existing = True
        mt.save = True
        mt.options = ui
        tools.import_asset_tasks([mt])
        mesh = eal.load_asset(DEST + "/" + MESH_NAME)
        # the swing: imported on its own, always into ANIM_NAME
        ua = unreal.FbxImportUI()
        ua.set_editor_property("import_mesh", False)
        ua.set_editor_property("import_as_skeletal", True)
        ua.set_editor_property("import_animations", True)
        ua.set_editor_property("import_materials", False)
        ua.set_editor_property("import_textures", False)
        ua.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
        ua.set_editor_property("skeleton", mesh.get_editor_property("skeleton"))
        ad = ua.get_editor_property("anim_sequence_import_data")
        ad.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task = unreal.AssetImportTask()
        task.filename = fbx
        task.destination_path = DEST
        task.destination_name = ANIM_NAME
        task.automated = True
        task.replace_existing = True
        task.save = True
        task.options = ua
        tools.import_asset_tasks([task])
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    swing = fix_anim_name(mesh)
    if mesh is None or swing is None:
        raise RuntimeError("lamp import failed (mesh %s, animation %s)" % (mesh, swing))
    mesh.modify()
    mats = mesh.get_editor_property("materials")
    for i in range(len(mats)):
        m = mats[i]
        slot = str(m.get_editor_property("material_slot_name")).lower()
        m.set_editor_property("material_interface", tube if "tube" in slot else mi)
        mats[i] = m
    mesh.set_editor_property("materials", mats)
    eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    eal.save_asset(swing.get_path_name(), only_if_is_dirty=False)
    log(MESH_NAME + " imported (%d material slots), animation %s %.1f s" % (len(mats), swing.get_name(), swing.get_play_length()))
    return mesh, swing


# ------------------------------------------------------------------ level
def by_label(label):
    return next((a for a in eas.get_all_level_actors() if a.get_actor_label() == label), None)


def ceiling_above(x, y, z0=150.0):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z0), unreal.Vector(x, y, z0 + 600),
                                               unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                               unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return 390.0
    t = h.to_tuple()
    if t[1]:                             # started inside something (a pillar): no ceiling to hang from here
        return 390.0
    return t[5].z


def lamp_space_free(x, y, ceiling):
    """a box the size of the swinging lamp, swept from just under the ceiling down to its lowest point"""
    h = unreal.SystemLibrary.box_trace_single(
        world, unreal.Vector(x, y, ceiling - 8.0), unreal.Vector(x, y, ceiling - LAMP_DROP),
        unreal.Vector(LAMP_SWING, LAMP_SWING, 1.0), unreal.Rotator(0, 0, 0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return True
    t = h.to_tuple()
    return not (t[0] or t[1])            # blocking hit or starts inside something


def spawn(cls, label, loc, rot=unreal.Rotator(0, 0, 0)):
    a = eas.spawn_actor_from_class(cls, loc, rot)
    a.set_actor_label(label)
    a.set_folder_path(FOLDER)
    a.set_editor_property("tags", [TAG])
    return a


def trace_hit(a, b, ignore=()):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True,
                                               list(ignore), unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    t = h.to_tuple()
    return t[5] if t[0] else None


def measure_opening(frame):
    """the real clear opening of the door frame, measured with traces from its middle: left / right / top edges.
    The leaves are made 2 cm wider on each side and 1 cm higher, so they tuck behind the frame - no gap."""
    o, ext = frame.get_actor_bounds(False)
    floor = o.z - ext.z
    yaw = frame.get_actor_rotation().yaw
    side = unreal.Vector(1, 0, 0) if ext.x >= ext.y else unreal.Vector(0, 1, 0)
    half = max(ext.x, ext.y) + 30.0
    lefts, rights = [], []
    for z in (60.0, 120.0, 180.0):
        c = unreal.Vector(o.x, o.y, floor + z)
        l = trace_hit(c, c - side * half)
        r = trace_hit(c, c + side * half)
        if l: lefts.append(l)
        if r: rights.append(r)
    top = trace_hit(unreal.Vector(o.x, o.y, floor + 100.0), unreal.Vector(o.x, o.y, floor + ext.z * 2 + 50.0))
    if not lefts or not rights or not top:
        warn("door opening could not be measured - frame bounds used")
        return unreal.Vector(o.x, o.y, floor), max(ext.x, ext.y) * 2 - 4.0, ext.z * 2 - 2.0
    def along(v):
        return v.x if side.x else v.y
    left = max(along(v) for v in lefts)            # innermost edge on each side
    right = min(along(v) for v in rights)
    mid = (left + right) * 0.5
    centre = unreal.Vector(mid, o.y, floor) if side.x else unreal.Vector(o.x, mid, floor)
    width = (right - left) + 4.0
    height = (top.z - floor) + 1.0
    log("door opening measured: %.0f x %.0f cm, centre shifted %.1f cm from the frame bounds" %
        (right - left, top.z - floor, mid - (o.x if side.x else o.y)))
    return centre, width, height


def first_material(actor):
    c = actor.get_component_by_class(unreal.StaticMeshComponent) if actor else None
    return c.get_material(0) if c else None


def main():
    lamp_cls = need_class("/Script/UniversityGame.HangingLamp")
    flicker_cls = need_class("/Script/UniversityGame.FlickeringLights")
    door_cls = need_class("/Script/UniversityGame.SlidingGlassDoor")
    mesh, swing = import_lamp()

    for a in eas.get_all_level_actors():                 # rebuild our own actors (nothing else is touched)
        if TAG in [str(t) for t in a.tags]:
            eas.destroy_actor(a)

    # ---- hanging lamp: the first spot where nothing (pillar, beam, furniture) is in the way of the swinging lamp
    x, y, cz = None, None, None
    for sx, sy in LAMP_SPOTS:
        c = ceiling_above(sx, sy)
        if lamp_space_free(sx, sy, c):
            x, y, cz = sx, sy, c
            break
        log("lamp spot (%.0f, %.0f) is blocked" % (sx, sy))
    if x is None:
        x, y = LAMP_SPOTS[0]
        cz = ceiling_above(x, y)
        warn("no free spot found - the lamp is at (%.0f, %.0f), move it by hand" % (x, y))
    lamp = spawn(lamp_cls, "Lobby_HangingLamp", unreal.Vector(x, y, cz - 0.5), unreal.Rotator(0, 0, 25))
    comp = lamp.get_component_by_class(unreal.SkeletalMeshComponent)
    comp.modify()
    comp.set_skeletal_mesh_asset(mesh)
    lamp.set_editor_property("swing_animation", swing)
    b = mesh.get_bounds()
    log("%s bounds: origin %s, extent %s (should be about 10 x 55 x 88 cm)" % (MESH_NAME, b.origin, b.box_extent))
    log("Lobby_HangingLamp under the ceiling at (%.0f, %.0f, %.0f)" % (x, y, cz))

    # ---- flickering ceiling lamps
    targets = [by_label(l) for l in FLICKER_TARGETS]
    found = [t for t in targets if t is not None]
    fl = spawn(flicker_cls, "Lobby_FlickeringLights", unreal.Vector(-1150, 1000, 300))
    fl.set_editor_property("targets", found)
    log("Lobby_FlickeringLights: %s" % ", ".join(t.get_actor_label() for t in found))
    if len(found) < len(FLICKER_TARGETS):
        warn("not found: %s" % [l for l, t in zip(FLICKER_TARGETS, targets) if t is None])

    # ---- automatic glass door in the lobby entrance
    frame = by_label(FRAME_LABEL)
    if frame is None:
        warn(FRAME_LABEL + " not found - the door is not placed")
    else:
        for label in OLD_LEAVES:                       # the old leaves must not get in the way of the measuring
            leaf = by_label(label)
            if leaf:
                leaf.set_actor_enable_collision(False)
        loc, width, height = measure_opening(frame)
        door = spawn(door_cls, "Lobby_AutoDoor", loc, frame.get_actor_rotation())
        door.set_editor_property("door_width", width)
        door.set_editor_property("door_height", height)
        door.set_editor_property("glass_material", first_material(by_label(GLASS_LABEL)))
        door.set_editor_property("frame_material", first_material(frame))
        door.set_actor_location(loc, False, False)          # re-runs the construction (leaf sizes)
        for label in OLD_LEAVES:
            leaf = by_label(label)
            if leaf:
                leaf.set_actor_hidden_in_game(True)
                leaf.set_actor_enable_collision(False)
                leaf.set_folder_path(FOLDER + "/HiddenOldDoorLeaves")
        log("Lobby_AutoDoor %.0f x %.0f cm in %s; old swing leaves hidden in game" % (width, height, FRAME_LABEL))

    # the first, too small import is not used any more
    for name in OLD_ASSETS:
        path = DEST + "/" + name
        if eal.does_asset_exist(path):
            try:
                ok = eal.delete_asset(path)
            except Exception:
                ok = False
            log("old asset %s %s" % (name, "deleted" if ok else "still in use - delete it later by hand"))
    eal.sync_browser_to_objects([mesh.get_path_name()])
    log("done - save the level (Ctrl+S), then Play")


main()
