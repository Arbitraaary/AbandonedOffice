"""
Security guard (Lab 5): weapon, bullet, BP_SecurityGuard, and one guard on the map.
Build the C++ first (ASecurityGuard, UGuardHealthBarWidget), then in Unreal (Output Log -> Cmd):

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/SecurityGuard/setup_blueprints.py"

Content layout (assets from the first attempt are moved here automatically):
  /Game/_Game/Enemies/SecurityGuard/
      BP_SecurityGuard              ASecurityGuard: guard mesh + the soldiers' animation blueprint + BP_GuardRifle
      Meshes/SK_SecurityGuard, SK_SecurityGuard_PhysicsAsset
      Materials/MI_SecurityGuard
      Textures/T_SecurityGuard_BC, _N, _ORM
      AI/BB_SecurityGuard           blackboard (6 keys), AI/BT_SecurityGuard - the tree is assembled by hand (instruction)
  /Game/_Game/Weapons/              (next to BP_ValWeapon, BP_VenraWeapon, BP_Bullet)
      BP_GuardRifle                 ABaseWeapon with the AR4 carbine (separate asset, attached to the hand socket at runtime)
      BP_GuardBullet                child of BP_Bullet, Damage 4 (the guard only does minor damage)
Places BP_SecurityGuard "SecurityGuard_1" in the lobby and "SecurityGuard_Gate" outside next to the guard booth. Save the level afterwards (Ctrl+S).
Running it again is safe: nothing is duplicated.
"""
import math
import unreal

GUARD = "/Game/_Game/Enemies/SecurityGuard"
WEAPONS = "/Game/_Game/Weapons"
BULLET_BP = WEAPONS + "/BP_Bullet"
SOLDIER_BP = "/Game/_Game/Enemies/BP_EnemySoldier"
RIFLE_MESH = "/Game/FPS_Weapon_Bundle/Weapons/Meshes/AR4/SK_AR4_X"
BAR_SIZE = unreal.Vector2D(150, 34)            # 10 px bar at the bottom, room for "DODGE xx%" above it
TAG = "Lab5Guard"
SCALE = 0.85                     # chosen in the editor (soldiers are 0.75); used for the blueprint and every placed guard
GUARD_SCALE = [SCALE]
SPOTS = [(-1500, 1000, 0, 180, "SecurityGuard_1")]           # x, y, floor z, yaw, label: one guard in the lobby
GATE_LABEL = "SecurityGuard_Gate"                             # outside, next to the guard booth at the parking gate
AWAY_FROM_SOLDIERS = set()                                    # labels placed as far as possible from the soldiers
# guards placed by this script but no longer in SPOTS are removed from the level

# first attempt -> tidy layout
MOVES = [
    (GUARD + "/SK_SecurityGuard", GUARD + "/Meshes/SK_SecurityGuard"),
    (GUARD + "/SK_SecurityGuard_PhysicsAsset", GUARD + "/Meshes/SK_SecurityGuard_PhysicsAsset"),
    (GUARD + "/MI_SecurityGuard", GUARD + "/Materials/MI_SecurityGuard"),
    (GUARD + "/BP_GuardBullet", WEAPONS + "/BP_GuardBullet"),
    (GUARD + "/BP_GuardSMG", WEAPONS + "/BP_GuardRifle"),
]

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
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


def templates(bp):
    """component templates of a blueprint, including the ones declared in C++"""
    out = []
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = sds.k2_find_subobject_data_from_handle(h)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data) if data else None
        if obj is not None:
            out.append(obj)
    return out


def first(objs, cls):
    return next((o for o in objs if isinstance(o, cls)), None)


def get_bp(path, parent_class):
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    return unreal.BlueprintEditorLibrary.create_blueprint_asset_with_parent(path, parent_class)


def set_props(obj, **kw):
    for k, v in kw.items():
        try:
            obj.set_editor_property(k, v)
        except Exception as e:
            warn("%s.%s not set (%s)" % (obj.get_name(), k, e))


def finish(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    eal.save_asset(bp.get_path_name(), only_if_is_dirty=False)


def hit_z(x, y, z_from, z_to, ignore):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z_from), unreal.Vector(x, y, z_to),
                                               unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    try:
        return h.get_editor_property("impact_point").z
    except Exception:
        return h.to_tuple()[5].z


CAPSULE = {"r": 40.0, "hh": 96.0}             # scaled guard capsule, filled in main()


def free_floor_spot(x, y, floor_z, ignore, keep_out=None):
    """the nearest point around (x, y) where the floor itself is hit (not a desk or a counter) and a standing guard
    fits without touching anything"""
    import math
    blockers = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2]
    rings = [(0, 0)] + [(r, k) for r in range(60, 481, 60) for k in range(16)]
    samples = []
    for r, k in rings:
        a = 2 * math.pi * k / 16
        px, py = x + r * math.cos(a), y + r * math.sin(a)
        if keep_out and abs(px - keep_out[0].x) < keep_out[1].x + 45 and abs(py - keep_out[0].y) < keep_out[1].y + 45:
            continue                                       # inside / against the box we stand next to
        z = hit_z(px, py, floor_z + 250, floor_z - 60, ignore)
        if z is not None:
            samples.append((px, py, z))
    if samples:
        ground = min(z for _, _, z in samples)            # the floor is the lowest surface around; desks are higher
        for px, py, z in samples:                          # samples are ordered from the centre outwards
            if z - ground > 15:
                continue
            centre = unreal.Vector(px, py, z + CAPSULE["hh"] + 3)
            hits = unreal.SystemLibrary.capsule_overlap_actors(world, centre, CAPSULE["r"] + 10, CAPSULE["hh"],
                                                               blockers, None, ignore)
            if not hits:
                return centre
    warn("no free floor spot near (%.0f, %.0f) - move the guard by hand (select him, press End to drop him)" % (x, y))
    return unreal.Vector(x, y, floor_z + CAPSULE["hh"] + 3)


def ensure_material():
    mesh = eal.load_asset(GUARD + "/Meshes/SK_SecurityGuard")
    mi = eal.load_asset(GUARD + "/Materials/MI_SecurityGuard")
    mats = mesh.get_editor_property("materials")
    if any(mats[i].get_editor_property("material_interface") != mi for i in range(len(mats))):
        mesh.modify()
        for i in range(len(mats)):                       # items are copies: change one, then write it back
            m = mats[i]
            m.set_editor_property("material_interface", mi)
            mats[i] = m
        mesh.set_editor_property("materials", mats)
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    pa = eal.load_asset(GUARD + "/Meshes/SK_SecurityGuard_PhysicsAsset")
    if pa is not None and mesh.get_editor_property("physics_asset") != pa:
        mesh.modify()
        mesh.set_editor_property("physics_asset", pa)
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
        log("SK_SecurityGuard physics asset relinked")
    slot = mesh.get_editor_property("materials")[0].get_editor_property("material_interface")
    log("SK_SecurityGuard material: %s" % (slot.get_path_name() if slot else "NONE"))
    return mesh


def soldier_spots():
    """where the soldiers stand and patrol (their TargetPoints)"""
    pts = []
    for a in eas.get_all_level_actors():
        if "EnemySoldier" in a.get_class().get_name():
            pts.append(a.get_actor_location())
            try:
                pts += [t.get_actor_location() for t in (a.get_editor_property("target_points") or []) if t]
            except Exception:
                pass
    return pts


def on_navmesh(p):
    try:
        r = unreal.NavigationSystemV1.k2_project_point_to_navigation(world, p, None, None, unreal.Vector(60, 60, 150))
        if isinstance(r, tuple):                           # (success, projected point)
            return r[1] if r[0] else None
        return r                                           # projected point, or None when not on the navmesh
    except Exception:
        return p                                           # no nav query from Python - trust the floor trace


def spot_away_from_soldiers(x, y, floor_z, ignore, avoid):
    """a free indoor spot on this floor, as far as possible from the soldiers and their patrol routes"""
    best, best_score = None, -1.0
    blockers = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2]
    for gx in range(-2500, 2501, 250):
        for gy in range(-2500, 2501, 250):
            px, py = x + gx, y + gy
            z = hit_z(px, py, floor_z + 250, floor_z - 60, ignore)
            if z is None or abs(z - floor_z) > 30:
                continue
            if hit_z(px, py, z + 150, z + 700, ignore) is None:   # no ceiling above - outside the building
                continue
            centre = unreal.Vector(px, py, z + CAPSULE["hh"] + 3)
            if unreal.SystemLibrary.capsule_overlap_actors(world, centre, CAPSULE["r"] + 25, CAPSULE["hh"], blockers, None, ignore):
                continue
            if on_navmesh(unreal.Vector(px, py, z)) is None:
                continue
            score = min([(centre - a).length() for a in avoid] or [99999.0])
            if score > best_score:
                best, best_score = centre, score
    if best is None:
        warn("no free spot found on this floor - the guard stays where he is")
        return free_floor_spot(x, y, floor_z, ignore)
    log("nearest soldier / soldier patrol point is %.1f m away" % (best_score / 100.0))
    return best


def guard_booth():
    """the checkpoint booth at the parking gate (SM_GuardBooth)"""
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.StaticMeshActor):
            sm = a.get_editor_property("static_mesh_component").get_editor_property("static_mesh")
            if sm and "GuardBooth" in sm.get_name():
                return a
    return None


def tidy_up():
    for d in (GUARD + "/Meshes", GUARD + "/Materials", GUARD + "/Textures"):
        eal.make_directory(d)
    moved = []
    for src, dst in MOVES:
        if eal.does_asset_exist(src) and not eal.does_asset_exist(dst):
            if eal.rename_asset(src, dst):
                moved.append(dst.split("/")[-1])
            else:
                warn("could not move %s -> %s" % (src, dst))
    if moved:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
        log("moved: " + ", ".join(moved))
    # replace the redirectors left behind by the moves
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reds = []
    for path in (GUARD, WEAPONS):
        for ad in reg.get_assets_by_path(path, recursive=True):
            if str(ad.asset_class_path.asset_name) == "ObjectRedirector":
                obj = ad.get_asset()
                if obj is not None:
                    reds.append(obj)
    if reds:
        unreal.AssetToolsHelpers.get_asset_tools().fixup_referencers(reds)
        log("fixed %d redirector(s)" % len(reds))


BB_KEYS = [("TargetActor", "Object"), ("CanSeeTarget", "Bool"), ("InAttackRange", "Bool"), ("HasLastKnown", "Bool"),
           ("LastKnownLocation", "Vector"), ("PatrolPoint", "Vector")]


def make_ai_assets():
    """BB_SecurityGuard with its keys and an empty BT_SecurityGuard (nodes can't be added from Python)"""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    ai = GUARD + "/AI"
    eal.make_directory(ai)
    bb_path, bt_path = ai + "/BB_SecurityGuard", ai + "/BT_SecurityGuard"
    bb = eal.load_asset(bb_path) if eal.does_asset_exist(bb_path) else tools.create_asset(
        "BB_SecurityGuard", ai, unreal.BlackboardData, unreal.BlackboardDataFactory())
    try:
        have = {str(e.get_editor_property("entry_name")) for e in bb.get_editor_property("keys")}
    except Exception:
        have = set()
    missing = [(n, t) for n, t in BB_KEYS if n not in have]
    if missing:
        try:
            keys = list(bb.get_editor_property("keys"))
            for name, kind in missing:
                kt = getattr(unreal, "BlackboardKeyType_" + kind)(outer=bb)
                e = unreal.BlackboardEntry()
                e.set_editor_property("entry_name", name)
                e.set_editor_property("key_type", kt)
                keys.append(e)
            bb.set_editor_property("keys", keys)
            log("BB_SecurityGuard keys added: " + ", ".join(n for n, _ in missing))
        except Exception as ex:
            warn("could not add blackboard keys (%s) - add them by hand: %s" % (
                ex, ", ".join("%s (%s)" % k for k in missing)))
    eal.save_asset(bb.get_path_name(), only_if_is_dirty=False)
    bt = eal.load_asset(bt_path) if eal.does_asset_exist(bt_path) else tools.create_asset(
        "BT_SecurityGuard", ai, unreal.BehaviorTree, unreal.BehaviorTreeFactory())
    try:
        bt.set_editor_property("blackboard_asset", bb)
    except Exception:
        pass                                              # set by hand when assembling the tree
    eal.save_asset(bt.get_path_name(), only_if_is_dirty=False)
    return bt


def main():
    guard_cls = need_class("/Script/UniversityGame.SecurityGuard")
    weapon_cls = need_class("/Script/UniversityGame.BaseWeapon")
    tidy_up()

    # ---- bullet with minor damage
    bullet_parent = eal.load_blueprint_class(BULLET_BP)
    if bullet_parent is None:
        raise RuntimeError("BP_Bullet not found at " + BULLET_BP)
    bp_bullet = get_bp(WEAPONS + "/BP_GuardBullet", bullet_parent)
    finish(bp_bullet)
    set_props(unreal.get_default_object(bp_bullet.generated_class()), damage=4.0)
    finish(bp_bullet)

    # ---- the rifle: AR4 carbine, long enough for the soldiers' two-handed rifle pose
    bp_rifle = get_bp(WEAPONS + "/BP_GuardRifle", weapon_cls)
    finish(bp_rifle)
    skc = first(templates(bp_rifle), unreal.SkeletalMeshComponent)
    if skc is not None:
        skc.set_skeletal_mesh_asset(eal.load_asset(RIFLE_MESH))
        # collision exactly like the player's / soldiers' weapons (object type "Pickable", so E picks it up;
        # AEnemy::DropWeapon also sets it when the weapon is dropped)
        val = eal.load_asset(WEAPONS + "/BP_ValWeapon")
        val_skc = first(templates(val), unreal.SkeletalMeshComponent) if val else None
        if val_skc is not None:
            skc.set_editor_property("body_instance", val_skc.get_editor_property("body_instance"))
            log("rifle collision copied from BP_ValWeapon")
        else:
            warn("BP_ValWeapon not found - rifle collision left as it is")
        try:
            pa = eal.load_asset(RIFLE_MESH).get_editor_property("physics_asset")
            log("rifle physics asset: %s" % (pa.get_name() if pa else "NONE - the dropped rifle cannot fall"))
        except Exception as e:
            warn("rifle physics asset unknown (%s)" % e)
    else:
        warn("BP_GuardRifle: no SkeletalMeshComponent found - set its mesh to SK_AR4_X by hand")
    set_props(unreal.get_default_object(bp_rifle.generated_class()), bullet_class=bp_bullet.generated_class(),
              socket="hand_r_val_socket", fire_rate=0.15, magazine_ammo_capacity=30, magazine_ammo_count=30,
              muzzle_socket_name="Muzzle")       # bullets leave from the end of the barrel, outside the guard's capsule
    finish(bp_rifle)
    log("BP_GuardBullet (damage 4), BP_GuardRifle (SK_AR4_X)")

    # ---- the guard
    bp_g = get_bp(GUARD + "/BP_SecurityGuard", guard_cls)
    finish(bp_g)
    comps = templates(bp_g)
    g_mesh = first(comps, unreal.SkeletalMeshComponent)
    soldier = eal.load_asset(SOLDIER_BP)
    s_mesh = first(templates(soldier), unreal.SkeletalMeshComponent) if soldier else None
    if g_mesh is None:
        raise RuntimeError("BP_SecurityGuard has no mesh component")
    if s_mesh is not None:
        for k in ("anim_class", "animation_mode", "relative_location", "relative_rotation", "relative_scale3d"):
            try:
                g_mesh.set_editor_property(k, s_mesh.get_editor_property(k))
            except Exception as e:
                warn("mesh %s not copied from BP_EnemySoldier (%s)" % (k, e))
    else:
        warn("BP_EnemySoldier not found - set Anim Class = ABP_EnemySoldier on BP_SecurityGuard's mesh by hand")
    g_mesh.set_skeletal_mesh_asset(ensure_material())
    s_bar = first(templates(soldier), unreal.WidgetComponent) if soldier else None
    if s_bar is not None:
        ds = s_bar.get_editor_property("draw_size"); rl = s_bar.get_editor_property("relative_location")
        wc = s_bar.get_editor_property("widget_class")
        log("soldier bar: %s, draw size %dx%d, space %s, at z %.0f, draw at desired size %s" % (
            wc.get_name() if wc else "?", ds.x, ds.y, s_bar.get_editor_property("space"), rl.z,
            s_bar.get_editor_property("draw_at_desired_size")))
    # ---- same size as the soldiers: their capsule, and the scale they are placed with in the level
    # (BP_EnemySoldier's root capsule is scaled; placed soldiers simply inherit that scale)
    k = 1.0
    s_cap = first(templates(soldier), unreal.CapsuleComponent) if soldier else None
    g_cap = first(comps, unreal.CapsuleComponent)
    if s_cap is not None and g_cap is not None:
        hh, r = s_cap.get_editor_property("capsule_half_height"), s_cap.get_editor_property("capsule_radius")
        k = SCALE
        set_props(g_cap, capsule_half_height=hh, capsule_radius=r, relative_scale3d=unreal.Vector(k, k, k))
        CAPSULE["hh"], CAPSULE["r"] = hh * k, r * k
        log("capsule %.0f x %.0f like the soldier's, scale %.2f" % (r, hh, k))
    else:
        k = SCALE
        warn("soldier capsule not found - capsule size not copied")
    for nm, m in (("soldier", s_mesh.get_editor_property("skeletal_mesh_asset") if s_mesh else None),
                  ("guard", eal.load_asset(GUARD + "/Meshes/SK_SecurityGuard"))):
        if m is not None:
            b = m.get_bounds()
            log("%s mesh height %.0f cm" % (nm, b.box_extent.z * 2))
    log("guard scale %.2f" % k)
    bar = first(comps, unreal.WidgetComponent)
    if bar is not None:
        set_props(bar, draw_size=unreal.IntPoint(int(BAR_SIZE.x), int(BAR_SIZE.y)))
    bt = make_ai_assets()
    set_props(unreal.get_default_object(bp_g.generated_class()), weapon_class=bp_rifle.generated_class(), behavior_tree=bt)
    finish(bp_g)
    log("BP_SecurityGuard: SK_SecurityGuard, anim %s, weapon BP_GuardRifle, tree BT_SecurityGuard" % (
        g_mesh.get_editor_property("anim_class").get_name() if g_mesh.get_editor_property("anim_class") else "?"))

    # ---- one guard in the lobby (moved back there if he already exists)
    scale = unreal.Vector(GUARD_SCALE[0], GUARD_SCALE[0], GUARD_SCALE[0])
    placed = {a.get_actor_label(): a for a in eas.get_all_level_actors() if TAG in [str(t) for t in a.tags]}
    spots = [(x, y, z, yaw, label, None) for x, y, z, yaw, label in SPOTS]
    booth = guard_booth()
    if booth is not None:
        o, ext = booth.get_actor_bounds(False)
        spots.append((o.x, o.y, booth.get_actor_location().z, 0.0, GATE_LABEL, (o, ext)))
        log("guard booth found: %s at (%.0f, %.0f)" % (booth.get_actor_label(), o.x, o.y))
    else:
        warn("SM_GuardBooth not found in the level - no guard at the gate")
    for x, y, z, yaw, label, keep_out in spots:
        a = placed.pop(label, None)
        ign = [a] if a is not None else []
        if label in AWAY_FROM_SOLDIERS:
            loc = spot_away_from_soldiers(x, y, z, ign, soldier_spots())
        else:
            loc = free_floor_spot(x, y, z, ign + ([booth] if keep_out else []), keep_out)
        if keep_out:                                       # stand next to the booth, facing away from it
            yaw = math.degrees(math.atan2(loc.y - y, loc.x - x))
        if a is None or a.get_class() != bp_g.generated_class():
            if a is not None:
                eas.destroy_actor(a)
            a = eas.spawn_actor_from_class(bp_g.generated_class(), loc, unreal.Rotator(0, 0, yaw))
            a.set_actor_label(label)
            a.set_folder_path("AbandonedOffice/Lab5")
            a.set_editor_property("tags", [TAG])
        else:
            a.set_actor_location_and_rotation(loc, unreal.Rotator(0, 0, yaw), False, True)
        a.set_actor_scale3d(scale)
        log("%s at (%.0f, %.0f, %.0f)" % (label, loc.x, loc.y, loc.z))
    for a in placed.values():
        eas.destroy_actor(a)
    eal.sync_browser_to_objects([bp_g.get_path_name()])
    log("done - save the level (Ctrl+S), then Play")


main()
