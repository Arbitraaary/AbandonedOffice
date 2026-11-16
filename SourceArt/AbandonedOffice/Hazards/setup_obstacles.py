"""
Lab 5, step 5: obstacles for the security guard (and the lobby water cooler back against a wall).
Build the C++ first (ASmokeZone, ASparkingCables), then in Unreal with OfficeMap open (Output Log -> Cmd):

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Hazards/setup_obstacles.py"

  * imports SM_SparkingCables (+ MI_SparkingCables) and makes M_Spark (glowing spark material)
    into /Game/_Game/Environment/AbandonedOffice/Hazards
  * "Lobby_SparkingCables": live cables hanging from the lobby ceiling hole down to the floor, sparking;
    a guard who walks into them is shocked (damage, freezes and shakes, "SHOCKED!")
  * "Lobby_SmokeZone": a cloud of smoke on the guard's patrol area; the player inside it is invisible to the guard,
    a guard inside it is blind and slow ("BLINDED")
  * the lobby water cooler is moved back against the nearest wall
Save the level afterwards (Ctrl+S). Running it again is safe: the obstacles are replaced, not duplicated.
"""
import math
import os
import unreal

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = "/Game/_Game/Environment/AbandonedOffice/Hazards"
DEST_TEX = DEST + "/Textures"
MASTER = "/Game/_Game/Environment/AbandonedOffice/Materials/M_AbandonedProp"
TAG = "Lab5Obstacle"
HOLE_LABEL = "Lobby_CeilingHole"           # the cables hang from this ceiling hole
GUARD_LABEL = "SecurityGuard_1"            # the smoke goes on his patrol area
COOLER_LABEL = "Lobby_WaterCooler"
SMOKE_EXTENT = (190.0, 190.0, 140.0)

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def log(m):
    unreal.log("[Lab5] " + m)


def warn(m):
    unreal.log_warning("[Lab5] " + m)


def need_class(path):
    cls = unreal.load_class(None, path)
    if cls is None:
        raise RuntimeError("C++ class %s not found - build the project first" % path)
    return cls


# ------------------------------------------------------------------ assets
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
    elif kind == "masks":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    tex.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)     # flat colour patches - keep them crisp
    eal.save_asset(tex.get_path_name(), only_if_is_dirty=False)
    return tex


def import_cables():
    bc = import_texture("T_SparkingCables_BC.png", "color")
    orm = import_texture("T_SparkingCables_ORM.png", "masks")
    nrm = import_texture("T_SparkingCables_N.png", "normal")
    path = DEST + "/MI_SparkingCables"
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        "MI_SparkingCables", DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, eal.load_asset(MASTER))
    mel.set_material_instance_texture_parameter_value(mi, "BaseColor", bc)
    mel.set_material_instance_texture_parameter_value(mi, "ORM", orm)
    mel.set_material_instance_texture_parameter_value(mi, "Normal", nrm)
    mel.update_material_instance(mi)
    eal.save_asset(mi.get_path_name(), only_if_is_dirty=False)

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("build_nanite", False)
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        mesh = import_file(os.path.join(SRC, "SM_SparkingCables.fbx"), DEST, ui)
    finally:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 1")
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, mi)
    eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    try:
        n = len(mesh.get_editor_property("sockets") or [])
    except Exception:
        n = -1
    log("SM_SparkingCables imported, spark sockets: %s" % (n if n >= 0 else "?"))
    return mesh


def spark_material():
    """unlit, very bright yellow-white - the sparks glow and bloom"""
    path = DEST + "/M_Spark"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    mat = tools.create_asset("M_Spark", DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    col.set_editor_property("constant", unreal.LinearColor(1.0, 0.72, 0.32, 1.0))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 0)
    k = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 150)
    k.set_editor_property("r", 60.0)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(k, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


# ------------------------------------------------------------------ level helpers
def hit(a, b, ignore=()):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True,
                                               list(ignore), unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    t = h.to_tuple()   # blocking_hit, initial_overlap, time, distance, location, impact_point, normal, impact_normal, phys_mat, actor, component
    return dict(distance=t[3], point=t[5], normal=t[7], actor=t[9])


def floor_z(x, y, z_from, z_to, ignore=()):
    h = hit(unreal.Vector(x, y, z_from), unreal.Vector(x, y, z_to), ignore)
    return h["point"].z if h else None


def by_label(label):
    return next((a for a in eas.get_all_level_actors() if a.get_actor_label() == label), None)


def place(cls, label, loc, rot=unreal.Rotator(0, 0, 0)):
    a = eas.spawn_actor_from_class(cls, loc, rot)
    a.set_actor_label(label)
    a.set_folder_path("AbandonedOffice/Lab5")
    a.set_editor_property("tags", [TAG])
    return a


# ------------------------------------------------------------------ obstacles
def place_cables(cls, mesh, spark_mat):
    hole = by_label(HOLE_LABEL)
    if hole is None:
        warn(HOLE_LABEL + " not found - cables placed at the guard instead")
        g = by_label(GUARD_LABEL)
        base = g.get_actor_location() + unreal.Vector(300, 0, 0) if g else unreal.Vector(-1150, 1250, 0)
        top = unreal.Vector(base.x, base.y, 390)
    else:
        top = hole.get_actor_location()
    fz = floor_z(top.x, top.y, top.z - 30, top.z - 600, [hole] if hole else []) or 0.0
    a = place(cls, "Lobby_SparkingCables", top)
    a.get_editor_property("cables").set_static_mesh(mesh)
    a.set_editor_property("spark_material", spark_mat)
    a.set_editor_property("ceiling_height", top.z - fz)
    log("Lobby_SparkingCables under %s at (%.0f, %.0f), ceiling %.0f cm above the floor" % (
        HOLE_LABEL, top.x, top.y, top.z - fz))
    return unreal.Vector(top.x, top.y, fz)


def place_smoke(cls, avoid):
    """an open bit of floor on the guard's patrol area, 4-9 m from him and away from the cables"""
    g = by_label(GUARD_LABEL)
    home = g.get_actor_location() if g else unreal.Vector(-1546, 1111, 80)
    f0 = floor_z(home.x, home.y, home.z + 50, home.z - 300) or 0.0
    ex, ey, ez = SMOKE_EXTENT
    best, best_score = None, -1e9
    for dx in range(-1000, 1001, 100):
        for dy in range(-1000, 1001, 100):
            d = math.hypot(dx, dy)
            if d < 400 or d > 950:
                continue
            cx, cy = home.x + dx, home.y + dy
            if math.hypot(cx - avoid.x, cy - avoid.y) < 550:
                continue
            ok = True
            for fx in (-0.8, 0, 0.8):                  # the whole square must be bare floor under a ceiling
                for fy in (-0.8, 0, 0.8):
                    px, py = cx + fx * ex, cy + fy * ey
                    z = floor_z(px, py, f0 + 120, f0 - 60)
                    if z is None or abs(z - f0) > 8 or hit(unreal.Vector(px, py, f0 + 150), unreal.Vector(px, py, f0 + 600)) is None:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            score = -abs(d - 650)
            if score > best_score:
                best, best_score = unreal.Vector(cx, cy, f0), score
    if best is None:
        warn("no free 4x4 m floor found near the guard - smoke placed next to him; move it by hand if needed")
        best = unreal.Vector(home.x + 500, home.y, f0)
    a = place(cls, "Lobby_SmokeZone", best)
    a.set_editor_property("zone_extent", unreal.Vector(ex, ey, ez))
    log("Lobby_SmokeZone at (%.0f, %.0f, %.0f), %.1f m from the guard" % (
        best.x, best.y, best.z, math.hypot(best.x - home.x, best.y - home.y) / 100))


def cooler_to_wall():
    """move the lobby cooler against the nearest wall (not a desk or a counter)"""
    c = by_label(COOLER_LABEL)
    if c is None:
        warn(COOLER_LABEL + " not found")
        return
    p = c.get_actor_location()
    best = None
    for k in range(16):
        ang = 2 * math.pi * k / 16
        d = unreal.Vector(math.cos(ang), math.sin(ang), 0)
        side = unreal.Vector(-d.y, d.x, 0)
        a0 = unreal.Vector(p.x, p.y, p.z + 60)
        h = hit(a0, a0 + d * 600, [c])
        if h is None or abs(h["normal"].z) > 0.3:
            continue
        s0 = unreal.Vector(p.x, p.y, p.z + 200)                      # tall = a wall, not a desk or a counter
        h2 = hit(s0, s0 + d * 650, [c])
        good = h2 is not None and abs(h2["distance"] - h["distance"]) <= 30
        if good and (best is None or h["distance"] < best[0]["distance"]):
            best = (h, d)
    if best is None:
        warn("no wall found around the water cooler - move it by hand")
        return
    h, d = best
    n = h["normal"]
    ln = math.hypot(n.x, n.y) or 1.0
    nx, ny = n.x / ln, n.y / ln
    loc = unreal.Vector(h["point"].x + nx * 19, h["point"].y + ny * 19, p.z)
    yaw = math.degrees(math.atan2(ny, nx)) - 90.0          # its tap (local +Y) looks into the room
    c.set_actor_location_and_rotation(loc, unreal.Rotator(0, 0, yaw), False, True)
    log("water cooler moved %.1f m, against the wall at (%.0f, %.0f)" % (h["distance"] / 100, loc.x, loc.y))


def main():
    cables_cls = need_class("/Script/UniversityGame.SparkingCables")
    smoke_cls = need_class("/Script/UniversityGame.SmokeZone")
    eal.make_directory(DEST)
    for a in eas.get_all_level_actors():                   # previous run
        if TAG in [str(t) for t in a.tags]:
            eas.destroy_actor(a)
    mesh = import_cables()
    mat = spark_material()
    cables_floor = place_cables(cables_cls, mesh, mat)
    place_smoke(smoke_cls, cables_floor)
    cooler_to_wall()
    log("obstacles done - save the level (Ctrl+S), then Play")


main()
