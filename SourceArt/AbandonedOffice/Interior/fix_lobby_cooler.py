"""
Put the lobby water cooler back against the nearest wall (it stands in the passage).

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Interior/fix_lobby_cooler.py"

The cooler is moved to the closest tall wall around it (desks and counters are skipped), its back 2 cm from the wall,
the tap facing the room. Save the level afterwards (Ctrl+S). Ctrl+Z undoes it.
"""
import math
import unreal

LABEL = "Lobby_WaterCooler"
HALF_DEPTH = 17.0            # SM_WaterCooler is 31 x 32 cm; its front (tap) looks along local +Y
SEARCH = 450.0               # look for a wall this far around the cooler (cm)
MIN_WALL_HEIGHT = 200.0      # anything lower is furniture, not a wall

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def log(m):
    unreal.log("[Cooler] " + m)


def trace(a, b, ignore):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                               unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    t = h.to_tuple()
    # FHitResult tuple: blocking_hit, initial_overlap, time, distance, location, impact_point, normal, impact_normal,
    #                   phys_mat, hit_actor, hit_component, ...
    return dict(distance=t[3], point=t[5], normal=t[7], actor=t[9], comp=t[10])


cooler = next((a for a in eas.get_all_level_actors() if a.get_actor_label() == LABEL), None)
if cooler is None:
    raise RuntimeError(LABEL + " not found")
p = cooler.get_actor_location()
log("%s now at (%.0f, %.0f, %.0f)" % (LABEL, p.x, p.y, p.z))

best = None
for k in range(16):                                       # 16 directions around the cooler
    ang = 2 * math.pi * k / 16
    d = unreal.Vector(math.cos(ang), math.sin(ang), 0)
    a = unreal.Vector(p.x, p.y, p.z + 60)
    h = trace(a, a + d * SEARCH, [cooler])
    if h is None:
        continue
    n = h["normal"]
    if abs(n.z) > 0.3:
        continue                                          # not a vertical surface
    # tall enough to be a wall? (a ray 2 m up must hit the same kind of surface)
    hi = trace(unreal.Vector(p.x, p.y, p.z + MIN_WALL_HEIGHT), unreal.Vector(p.x, p.y, p.z + MIN_WALL_HEIGHT) + d * SEARCH, [cooler])
    if hi is None or abs(hi["distance"] - h["distance"]) > 30:
        continue
    if best is None or h["distance"] < best[0]["distance"]:
        best = (h, d)

if best is None:
    unreal.log_warning("[Cooler] no wall within %.1f m - move it by hand" % (SEARCH / 100))
else:
    h, d = best
    n = unreal.Vector(h["normal"].x, h["normal"].y, 0)
    ln = math.hypot(n.x, n.y) or 1.0
    n = unreal.Vector(n.x / ln, n.y / ln, 0)
    loc = unreal.Vector(h["point"].x + n.x * (HALF_DEPTH + 2), h["point"].y + n.y * (HALF_DEPTH + 2), p.z)
    yaw = math.degrees(math.atan2(n.y, n.x)) - 90.0       # local +Y (tap) looks away from the wall
    cooler.set_actor_location_and_rotation(loc, unreal.Rotator(0, 0, yaw), False, True)
    log("moved %.1f m to the wall of %s: (%.0f, %.0f), yaw %.0f - save the level (Ctrl+S)" % (
        h["distance"] / 100, h["actor"].get_actor_label() if h["actor"] else "?", loc.x, loc.y, yaw))
