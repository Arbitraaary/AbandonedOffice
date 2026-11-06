"""
Gameplay pass for OfficeMap (run AFTER place_exterior.py and place_interior.py):

  * one more +health, +ammo and +armour pickup on clearly visible, free spots
    (lobby on floor 1, open office on floor 2, next to the guard booth at the gate);
    the pickups that were already in the level are checked too and moved off cars / furniture if they ended up inside
  * the old cars get simple box collision (if they had none) - then the nav mesh goes AROUND them and soldiers
    stop running into them
  * every soldier's patrol points: moved onto the nav mesh, away from cars / furniture / walls,
    kept apart from other soldiers' points and checked that the next point can actually be reached
  * soldiers get RVO avoidance, so two of them meeting in a corridor step around each other

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Gameplay/place_gameplay.py"

Safe to re-run: pickups it added (tag AO_Gameplay) are removed first. Ctrl+Z undoes a run. Save with Ctrl+S.
"""
import math
import unreal

TAG = "AO_Gameplay"
ITEMS = "/Game/_Game/Stuff/BonusItems/"
NEW_PICKUPS = [            # blueprint, wanted spot (x, y, floor z), where
    ("BP_HealthItem", (-850, 1000, 0), "lobby, floor 1"),
    ("BP_AmmoItem", (-1750, 990, 400), "open office, floor 2"),
    ("BP_ArmorItem", "booth", "next to the guard booth at the gate"),
]
CARS = ["/Game/RustyCarsFree/Geometries/SM_asset_%02d" % i for i in range(5)]
POINT_CLEAR = 85.0          # free radius around a patrol point (soldier capsule ~35 cm + margin)
ITEM_CLEAR = 55.0
POINT_APART = 300.0         # patrol points of different soldiers at least this far apart

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
NAV = unreal.NavigationSystemV1
OBJ = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2,
       unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY4]          # WorldStatic, WorldDynamic, PhysicsBody


def log(m):
    unreal.log("[AbandonedOffice/Gameplay] " + m)


def warn(m):
    unreal.log_warning("[AbandonedOffice/Gameplay] " + m)


def has_tag(a, t):
    return any(str(x) == t for x in a.get_editor_property("tags"))


def mesh_name(a):
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    sm = c.get_editor_property("static_mesh") if c else None
    return sm.get_name() if sm else ""


IGNORE_WORDS = ("Grass", "Weeds", "Landscape", "Trigger", "Volume", "Paper", "Item", "TargetPoint", "Decal", "Light", "Fog",
                "Sky", "PlayerStart", "Ivy", "Plane")


def blocking(actors):
    out = []
    for a in actors or []:
        n = a.get_class().get_name() + " " + mesh_name(a) + " " + a.get_actor_label()
        if not any(w in n for w in IGNORE_WORDS) and not isinstance(a, unreal.Character):
            out.append(a)
    return out


def floor_at(x, y, z):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z + 150), unreal.Vector(x, y, z - 250),
                                               unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    try:
        return h.get_editor_property("impact_point").z
    except Exception:
        return h.to_tuple()[5].z


def on_nav(p):
    try:
        q = NAV.project_point_to_navigation(world, p, None, None, unreal.Vector(40, 40, 150))
    except Exception:
        return None
    if q is None or (q.x == 0 and q.y == 0 and q.z == 0) or math.hypot(q.x - p.x, q.y - p.y) > 30:
        return None
    return q


def is_clear(p, radius, ignore):
    c = unreal.Vector(p.x, p.y, p.z + radius + 25)                 # sphere sits just above the floor
    hits = unreal.SystemLibrary.sphere_overlap_actors(world, c, radius, OBJ, None, ignore)
    return not blocking(hits)


def reachable(a, b):
    try:
        path = NAV.find_path_to_location_synchronously(world, a, b)
    except Exception:
        return True                                             # can't tell - don't block on it
    return path is not None and len(path.get_editor_property("path_points")) > 1 and not path.is_partial()


def find_spot(x, y, z, radius, ignore, need_nav=True, max_r=900, ok=None):
    """nearest free spot to (x, y) on the floor at about height z"""
    for r in [0] + list(range(60, int(max_r) + 1, 60)):
        n = 1 if r == 0 else max(8, int(2 * math.pi * r / 70))
        for k in range(n):
            ang = 2 * math.pi * k / n
            cx, cy = x + r * math.cos(ang), y + r * math.sin(ang)
            fz = floor_at(cx, cy, z)
            if fz is None or abs(fz - z) > 60:
                continue
            p = unreal.Vector(cx, cy, fz)
            if need_nav:
                q = on_nav(p)
                if q is None:
                    continue
                p = unreal.Vector(q.x, q.y, fz)
            if is_clear(p, radius, ignore) and (ok is None or ok(p)):
                return p
    return None


def fix_car_collision():
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    fixed = 0
    for path in CARS:
        if not eal.does_asset_exist(path):
            continue
        sm = eal.load_asset(path)
        if sub.get_simple_collision_count(sm) == 0:
            sub.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
            eal.save_loaded_asset(sm); fixed += 1
    log("cars: simple box collision added to %d mesh(es) (nav mesh now goes around them)" % fixed)


def main():
    with unreal.ScopedEditorTransaction("Abandoned office gameplay"):
        old = [a for a in eas.get_all_level_actors() if has_tag(a, TAG)]
        for a in old:
            eas.destroy_actor(a)
        fix_car_collision()
        actors = eas.get_all_level_actors()

        # ---------------------------------------------------------------- pickups
        existing = [a for a in actors if a.get_class().get_name() in ("BP_HealthItem_C", "BP_AmmoItem_C", "BP_ArmorItem_C")]
        for a in existing:                                       # the ones already in the level: still on a free spot?
            l = a.get_actor_location()
            fz = floor_at(l.x, l.y, l.z) or l.z
            if not is_clear(unreal.Vector(l.x, l.y, fz), ITEM_CLEAR, [a]):
                p = find_spot(l.x, l.y, fz, ITEM_CLEAR, [a], need_nav=False)
                if p:
                    a.set_actor_location(unreal.Vector(p.x, p.y, p.z + (l.z - fz)), False, True)
                    log("moved %s off an obstacle to (%.0f, %.0f)" % (a.get_actor_label(), p.x, p.y))
        booth = next((a for a in actors if mesh_name(a) == "SM_GuardBooth"), None)
        for bp, where, desc in NEW_PICKUPS:
            cls = eal.load_blueprint_class(ITEMS + bp)
            if cls is None:
                warn("missing " + ITEMS + bp); continue
            if where == "booth":
                if booth is None:
                    warn("no guard booth in the level - %s goes to the lobby instead" % bp); where = (-1350, 950, 0)
                else:
                    b = booth.get_actor_location(); where = (b.x, b.y, b.z)
            x, y, z = where
            spot = find_spot(x, y, z, ITEM_CLEAR, [booth] if booth else [], need_nav=False,
                             ok=(lambda p: math.hypot(p.x - x, p.y - y) > 250) if desc.startswith("next") else None)
            if spot is None:
                warn("no free spot for %s near %s" % (bp, desc)); continue
            a = eas.spawn_actor_from_class(cls, unreal.Vector(spot.x, spot.y, spot.z + 5), unreal.Rotator(0, 0, 0))
            if a:
                a.set_actor_label(bp.replace("BP_", "Extra_")); a.set_folder_path("AbandonedOffice/Gameplay")
                a.set_editor_property("tags", [TAG])
                log("placed %s - %s (%.0f, %.0f, %.0f)" % (bp, desc, spot.x, spot.y, spot.z))

        # ---------------------------------------------------------------- soldiers: avoidance + patrol points
        soldiers = [a for a in actors if a.get_class().get_name().startswith("BP_EnemySoldier")]
        done_pts = []                                           # (owner, Vector)
        moved = bad_path = 0
        for s in soldiers:
            cm = s.get_component_by_class(unreal.CharacterMovementComponent)
            if cm:
                for k, v in (("use_rvo_avoidance", True), ("avoidance_consideration_radius", 350.0), ("avoidance_weight", 0.5)):
                    try:
                        cm.set_editor_property(k, v)
                    except Exception as e:
                        warn("%s: %s not set (%s)" % (s.get_actor_label(), k, e))
            try:
                pts = list(s.get_editor_property("target_points") or [])
            except Exception:
                pts = []
            prev = s.get_actor_location()
            ignore = [s] + [p for p in pts if p]
            for tp in pts:
                if tp is None:
                    continue
                l = tp.get_actor_location()
                fz = floor_at(l.x, l.y, l.z) or l.z
                here = unreal.Vector(l.x, l.y, fz)
                far_from_others = lambda p: all(o is s or math.hypot(p.x - q.x, p.y - q.y) > POINT_APART or abs(p.z - q.z) > 200
                                                for o, q in done_pts)
                good = on_nav(here) is not None and is_clear(here, POINT_CLEAR, ignore) and far_from_others(here) \
                    and reachable(prev, here)
                if not good:
                    p = find_spot(l.x, l.y, fz, POINT_CLEAR, ignore, need_nav=True, max_r=900,
                                  ok=lambda p: far_from_others(p) and reachable(prev, p))
                    if p is None:
                        p = find_spot(l.x, l.y, fz, POINT_CLEAR, ignore, need_nav=True, max_r=900)
                        bad_path += 1
                    if p is not None:
                        tp.set_actor_location(unreal.Vector(p.x, p.y, p.z + (l.z - fz)), False, True)
                        here = p; moved += 1
                    else:
                        warn("%s: no free nav-mesh spot near %s" % (s.get_actor_label(), tp.get_actor_label()))
                done_pts.append((s, here))
                prev = here
        log("soldiers: %d, avoidance on; patrol points moved: %d%s" % (len(soldiers), moved,
            (" (%d still have no clean path to the next point - check the nav mesh, P in the viewport)" % bad_path) if bad_path else ""))
    log("done - save the level (Ctrl+S)")


main()
