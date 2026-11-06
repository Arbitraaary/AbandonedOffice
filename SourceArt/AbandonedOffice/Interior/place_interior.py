"""
Furnish the abandoned office inside (OfficeMap):
  * floor 1 and floor 2 get new props (desk clutter on the existing workstations - their layout is unchanged, the two empty
    core rooms on floor 2 become a storage room and a staff lounge, the empty east room on floor 1 becomes a
    storeroom, ceiling collapses with cones / tape post, boxes, filing cabinets, dead plants, papers, clocks...)
  * floor 2 (walls, doors, furniture, ceiling lamps / lights, the new props) is then copied 1:1 to floors 3 and 4
    (floor and ceiling slabs are already the same on every storey; pieces that already exist there are skipped)
  * a stray, half-finished copy of floor 2 that floats 1.6 m above floor 5 (and a bench floating on floor 4)
    is removed (REMOVE_STRAYS)

Run in Unreal Editor with OfficeMap open (Output Log -> Cmd):
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Interior/place_interior.py"
Safe to re-run: everything it placed / copied before (tag AO_Interior) is removed first. One Ctrl+Z undoes a run.
Enemies, targets, triggers and the player start are never copied.
"""
import math
import os
import random
import runpy
import unreal

SEED = 11
COPY_TO = (3, 4)            # storeys that get a copy of floor 2
REMOVE_STRAYS = True
FLOOR_H = 400.0             # storey height (cm); floor 1 at z=0, floor 2 at z=400 ...
TAG = "AO_Interior"
REPLACED = "AO_ReplacedOriginal"   # office pack pieces hidden by this script (shown again on every re-run)
PHYSICS_PROPS = True        # floor papers -> LoosePaper (blown along by walking), boxes / bins / cones -> GrabbableProp
                            # (pushed by walking into them, E = pick up / put down, fire = throw); needs the C++ classes built
REPLACE_POTS = True         # swap the green SM_flower_pot_1 plants for dead ones
ROOT = "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice"
AO = "/Game/_Game/Environment/AbandonedOffice"
OP = "/Game/Office_Pack_Vol_1/Models"
M = {
    "keyboard": AO + "/Workstation/SM_Keyboard", "mouse": AO + "/Workstation/SM_Mouse", "pc": AO + "/Workstation/SM_PCTower",
    "phone": AO + "/Workstation/SM_DeskPhone", "phone_hang": AO + "/Workstation/SM_DeskPhone_Hanging",
    "box_closed": AO + "/Boxes/SM_Box_Closed", "box_open": AO + "/Boxes/SM_Box_Open", "box_crushed": AO + "/Boxes/SM_Box_Crushed",
    "hole": AO + "/Ceiling/SM_CeilingHole_Hanging", "hole_cables": AO + "/Ceiling/SM_CeilingHole_Cables", "tiles": AO + "/Ceiling/SM_CeilingTiles_Fallen",
    "cooler": AO + "/WaterCooler/SM_WaterCooler", "board": AO + "/Wall/SM_CorkBoard", "clock": AO + "/Wall/SM_WallClock",
    "plant": AO + "/Plants/SM_DeadPlant_Large", "plant_desk": AO + "/Plants/SM_DeadPlant_Desk",
    "cabinet": AO + "/FilingCabinet/SM_FilingCabinet", "paper": AO + "/Paper/SM_PaperA4", "bin": AO + "/TrashBin/SM_AbandonedTrashBin",
    "post": AO + "/BarrierPost/SM_BarrierPost", "cone": AO + "/TrafficCone/SM_TrafficCone",
    "desk": OP + "/SM_Table_2", "chair": OP + "/SM_Chair_1", "monitor": OP + "/SM_Monitor_1", "sofa": OP + "/SM_Sofa_2", "coffee": OP + "/SM_Table_1",
}
KITS = {"WorkstationKit": ["keyboard", "mouse", "pc", "phone", "phone_hang"], "CardboardBoxes": ["box_closed", "box_open", "box_crushed"],
        "CeilingDamage": ["hole", "hole_cables", "tiles"], "WaterCooler": ["cooler"], "CorkBoardClock": ["board", "clock"],
        "DeadPlants": ["plant", "plant_desk"], "FilingCabinet": ["cabinet"], "PaperA4": ["paper"], "TrashBin": ["bin"],
        "BarrierPost": ["post"], "TrafficCone": ["cone"]}
NO_COPY = ("BP_EnemySoldier", "Target", "BP_TeleportTrigger", "PlayerStart", "DirectionalLight", "PostProcessVolume", "SkyLight",
           "SphereReflectionCapture", "LightmassImportanceVolume", "LightmassPortal", "Landscape", "NavMeshBoundsVolume",
           "RecastNavMesh", "BP_Sky_Sphere", "AtmosphericFog", "ExponentialHeightFog", "BP_HealthItem", "BP_AmmoItem", "BP_ArmorItem")

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(m):
    unreal.log("[AbandonedOffice/Interior] " + m)


def warn(m):
    unreal.log_warning("[AbandonedOffice/Interior] " + m)


# ================================================================= the plan (pure python, checked offline on a floor plan)
F1, F2 = 0.0, 400.0
DESK_TOP = 90.0                    # SM_Table_2 top above its floor
TABLE3_TOP = 98.0                  # meeting table top above floor 2


def plan(rng):
    items = []

    def add(key, x, y, z, yaw=0.0, label="", group="Props", roll=0.0, pitch=0.0, centre=None):
        items.append(dict(key=key, x=x, y=y, z=z, yaw=yaw, roll=roll, pitch=pitch, label=label or key, group=group,
                          centre=centre))

    def face(direction_deg):                   # our props face local +Y
        return direction_deg - 90.0

    def papers(n, x0, x1, y0, y1, z, label, group):
        for k in range(n):
            add("paper", rng.uniform(x0, x1), rng.uniform(y0, y1), z + 0.2 * k * (z not in (F1, F2)), rng.uniform(0, 360), "%s_Paper%d" % (label, k), group)

    def box_stack(x, y, z, label, group, n=2):
        add("box_closed", x, y, z, rng.uniform(-12, 12), label + "_Box0", group)
        if n > 1:
            add("box_closed" if rng.random() < 0.6 else "box_crushed", x + rng.uniform(-4, 4), y + rng.uniform(-4, 4), z + 37.3,
                rng.uniform(-15, 15), label + "_Box1", group)

    def desk_clutter(px, py, zf, south, label, group, keep=1.0):
        """props on an SM_Table_2 workstation whose pivot is (px, py); north row yaw 90, south row (rotated 180) yaw -90"""
        s = -1 if south else 1
        P = lambda dx, dy: (px + s * dx, py + s * dy)
        zt = zf + DESK_TOP
        c = P(45, 170)                          # middle of the desk top - things that hang over the edge slide towards it
        r = rng.random()
        if r < 0.85 * keep:
            x, y = P(13, 115); add("keyboard", x, y, zt, (90 if not south else -90) + rng.uniform(-6, 6), label + "_Keyboard", group, centre=c)
        if r < 0.7 * keep:
            x, y = P(14, 68); add("mouse", x, y, zt, (270 if not south else 90) + rng.uniform(-20, 20), label + "_Mouse", group, centre=c)
        if rng.random() < 0.6 * keep:
            x, y = P(35, 250); add("phone", x, y, zt, (90 if not south else -90) + rng.uniform(-20, 20), label + "_Phone", group, centre=c)
        x, y = P(50, 300); add("plant_desk", x, y, zt, rng.uniform(0, 360), label + "_DeskPlant", group, centre=c)
        if rng.random() < 0.8 * keep:
            x, y = P(45, 30); add("pc", x, y, zf, (90 if not south else -90) + rng.uniform(-8, 8), label + "_PC", group)
        for k in range(rng.randint(1, 4)):
            x, y = P(rng.uniform(10, 40), rng.uniform(190, 300)); add("paper", x, y, zt + 0.3 * k, rng.uniform(0, 360), "%s_Paper%d" % (label, k), group, centre=c)
        if rng.random() < 0.35:
            x, y = P(rng.uniform(-150, -100), rng.uniform(40, 300)); add("paper", x, y, zf, rng.uniform(0, 360), label + "_FloorPaper", group)
        if rng.random() < 0.3:
            x, y = P(-110, 320); add("bin", x, y, zf, rng.uniform(0, 360), label + "_Bin", group)

    # ---------------------------------------------------------------- FLOOR 1
    g = "Floor1"
    # lobby: tape post pushed aside inside the entrance, collapsed ceiling cordoned off with cones
    add("post", -870, 1555, F1, 205, "Lobby_TapePost", g)
    add("hole", -1150, 1250, F1 + 390, 0, "Lobby_CeilingHole", g)
    add("tiles", -1140, 1240, F1, rng.uniform(0, 360), "Lobby_FallenTiles", g)
    for k, (dx, dy) in enumerate(((-140, -90), (130, -100), (150, 95), (-120, 110))):
        add("cone", -1150 + dx, 1250 + dy, F1, rng.uniform(0, 360), "Lobby_Cone%d" % k, g)
    add("cooler", -640, 820, F1, face(90), "Lobby_WaterCooler", g)
    add("clock", -1450, 741, F1 + 300, face(90) + 8, "Lobby_Clock", g)
    add("board", -820, 741, F1 + 165, face(90), "Lobby_CorkBoard", g)
    add("plant", -2620, 610, F1, rng.uniform(0, 360), "Lobby_DeadPlantW", g)
    add("plant", 320, 610, F1, rng.uniform(0, 360), "Lobby_DeadPlantE", g)
    add("bin", -1735, 1475, F1, rng.uniform(0, 360), "Lobby_BinW", g)
    add("bin", -585, 1330, F1, rng.uniform(0, 360), "Lobby_BinE", g)
    box_stack(-1650, 1600, F1, "Lobby_BoxesDoor", g)
    add("box_open", -1560, 1640, F1, rng.uniform(-20, 20), "Lobby_BoxOpen", g)
    papers(5, -1350, -950, 1450, 1620, F1, "Lobby", g)
    papers(3, -2000, -1700, 1150, 1300, F1, "LobbyW", g)
    # south corridor: ceiling cables hanging, boxes and cabinets left against the core wall
    add("hole_cables", -800, -1150, F1 + 390, 0, "South_CeilingCables", g)
    add("tiles", -770, -1115, F1, rng.uniform(0, 360), "South_FallenTiles", g)
    add("cone", -930, -1040, F1, rng.uniform(0, 360), "South_Cone0", g)
    add("cone", -640, -1230, F1, rng.uniform(0, 360), "South_Cone1", g, roll=90)
    add("cabinet", -1620, -987, F1, face(-90), "South_Cabinet0", g)
    add("cabinet", -1572, -987, F1, face(-90) + 3, "South_Cabinet1", g)
    box_stack(-2100, -1200, F1, "South_BoxesW", g)
    add("box_crushed", -2020, -1120, F1, rng.uniform(0, 360), "South_BoxCrushed", g)
    add("box_open", -400, -1180, F1, rng.uniform(-20, 20), "South_BoxOpen", g)
    papers(5, -2100, -400, -1300, -1000, F1, "South", g)
    # east room (was empty) -> storeroom: cabinets on the east wall, boxes, dumped PC towers
    for k, y in enumerate((385, 337, 289, -560, -608)):
        add("cabinet", 262, y, F1, face(180) + rng.uniform(-2, 2), "Store_Cabinet%d" % k, g)
    box_stack(150, -100, F1, "Store_StackA", g)
    box_stack(160, -40, F1, "Store_StackB", g, 1)
    add("box_open", 80, 40, F1, rng.uniform(0, 360), "Store_BoxOpen", g)
    add("box_crushed", 200, 130, F1, rng.uniform(0, 360), "Store_BoxCrushed", g)
    box_stack(100, -760, F1, "Store_StackC", g)
    add("box_closed", 190, -800, F1, rng.uniform(-10, 10), "Store_BoxC2", g)
    for k, (x, y) in enumerate(((40, -300), (105, -345), (10, -250), (160, -265))):
        add("pc", x, y, F1, rng.uniform(0, 360), "Store_PC%d" % k, g)
    add("bin", 255, -880, F1, rng.uniform(0, 360), "Store_Bin", g)
    papers(8, 0, 250, -900, 400, F1, "Store", g)

    papers(26, -2400, 150, 800, 1180, F1, "LobbyWalk", "Floor1")
    papers(14, -2300, -500, -1300, -1010, F1, "SouthWalk", "Floor1")
    papers(10, -440, -180, -900, 650, F1, "EastWalk", "Floor1")
    papers(8, -2650, -1900, -900, 650, F1, "WestWalk", "Floor1")

    # ---------------------------------------------------------------- FLOOR 2
    g = "Floor2"
    papers(30, -2400, 150, 770, 1200, F2, "OpenWalk", g)
    papers(12, -2350, -2000, -900, 600, F2, "WestWalk", g)
    papers(10, -440, -240, -900, 650, F2, "EastWalk", g)
    papers(10, -2000, -500, -1300, -1010, F2, "SouthWalk", g)
    # clutter on the existing north row of workstations
    for k, px in enumerate((-2050, -1545, -1050, -545, -50)):
        desk_clutter(px, 1310, F2, False, "NorthDesk%d" % k, g)
    # south windows: the walkway stays free - only a few boxes tucked into the corners by the archive racks
    box_stack(-2240, -1240, F2, "SouthW_Stack", g)
    add("box_crushed", -2160, -1270, F2, rng.uniform(0, 360), "SouthW_BoxCrushed", g)
    add("box_open", -300, -1250, F2, rng.uniform(-20, 20), "SouthE_BoxOpen", g)
    papers(4, -2000, -500, -1290, -1000, F2, "South", g)
    # core room west (was empty) -> archive / storage
    for k, y in enumerate((-880, -832, -784)):
        add("cabinet", -1331, y, F2, face(180) + rng.uniform(-2, 2), "Archive_Cabinet%d" % k, g)
    add("box_open", -1770, -330, F2, rng.uniform(-20, 20), "Archive_BoxOpen", g)
    box_stack(-1450, -325, F2, "Archive_Stack", g)
    add("box_crushed", -1700, -880, F2, rng.uniform(0, 360), "Archive_BoxCrushed", g)
    add("box_closed", -1600, -895, F2, rng.uniform(-10, 10), "Archive_BoxClosed", g)
    papers(6, -1780, -1360, -900, -320, F2, "Archive", g)
    # core room east (was empty) -> staff lounge
    add("sofa", -880, -700, F2, 180, "Lounge_Sofa", g)
    add("coffee", -820, -655, F2, 90, "Lounge_Table", g)
    add("cooler", -540, -875, F2, face(90), "Lounge_WaterCooler", g)
    add("board", -700, -272, F2 + 160, face(-90), "Lounge_CorkBoard", g)
    add("clock", -760, -938, F2 + 250, face(90) - 6, "Lounge_Clock", g)
    add("plant", -955, -885, F2, rng.uniform(0, 360), "Lounge_DeadPlant", g)
    add("bin", -950, -330, F2, rng.uniform(0, 360), "Lounge_Bin", g)
    add("box_crushed", -600, -330, F2, rng.uniform(0, 360), "Lounge_Box", g)
    papers(3, -820, -730, -650, -510, F2 + 60, "Lounge", g)
    # open area north of the core: collapsed ceiling, taped off
    add("hole", -1300, 950, F2 + 390, 0, "Open_CeilingHole", g)
    add("tiles", -1270, 925, F2, rng.uniform(0, 360), "Open_FallenTiles", g)
    for k, (dx, dy) in enumerate(((-150, -110), (140, -120), (160, 110), (-140, 120))):
        add("cone", -1300 + dx, 950 + dy, F2, rng.uniform(0, 360), "Open_Cone%d" % k, g, roll=90 if k == 3 else 0)
    add("post", -1520, 1060, F2, 30, "Open_TapePost", g)
    box_stack(-2050, 1000, F2, "Open_Boxes", g)
    add("box_open", -1980, 1070, F2, rng.uniform(-20, 20), "Open_BoxOpen", g)
    add("cabinet", -600, 1080, F2, face(-90), "Open_Cabinet0", g)
    add("cabinet", -553, 1080, F2, face(-90) + 4, "Open_Cabinet1", g)
    add("board", -1350, 741, F2 + 160, face(90), "Open_CorkBoard", g)
    add("clock", -900, 741, F2 + 300, face(90), "Open_Clock", g)
    papers(5, -1700, -700, 750, 1150, F2, "Open", g)
    # west strip between the archive racks and the core
    add("cabinet", -2337, -250, F2, face(0), "West_Cabinet", g)
    box_stack(-2150, 200, F2, "West_Stack", g)
    add("box_crushed", -2120, 130, F2, rng.uniform(0, 360), "West_BoxCrushed", g)
    add("box_open", -2100, -650, F2, rng.uniform(-20, 20), "West_BoxOpen", g)
    papers(4, -2250, -1980, -900, 500, F2, "West", g)
    # east corner + meeting room
    add("plant", 300, 1150, F2, rng.uniform(0, 360), "East_DeadPlant", g)
    box_stack(250, 700, F2, "East_Stack", g)
    add("bin", 330, 1000, F2, rng.uniform(0, 360), "East_Bin", g)
    papers(4, -60, 140, -380, 60, F2 + TABLE3_TOP, "Meeting", g)
    add("phone", 110, 10, F2 + TABLE3_TOP, -90 + rng.uniform(-15, 15), "Meeting_Phone", g)
    add("bin", -170, -480, F2, rng.uniform(0, 360), "Meeting_Bin", g)
    add("plant", 220, -495, F2, rng.uniform(0, 360), "Meeting_DeadPlant", g)
    add("clock", -213, 250, F2 + 240, face(0), "Meeting_Clock", g)
    add("board", -213, -350, F2 + 160, face(0), "Meeting_CorkBoard", g)
    return items


# ================================================================= Unreal side

WALL_MOUNTED = ("clock", "board")
FLOOR_STANDING = ("cabinet", "cooler", "plant", "box_closed", "box_open", "box_crushed", "bin", "post", "cone", "sofa", "coffee", "tiles")


def _trace(world, a, b, ignore):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                               unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    try:
        return h.get_editor_property("distance"), h.get_editor_property("impact_point")
    except Exception:
        t = h.to_tuple()
        return t[3], t[5]


def keep_clear(world, a, spawned):
    """rays from the prop's centre out to its bounds (+X/-X/+Y/-Y, two heights); anything closer than the bounds
    is a wall or furniture inside the prop -> push the prop away, give up after 4 tries"""
    moved = False
    for attempt in range(4):
        o, e = a.get_actor_bounds(False)
        push = unreal.Vector(0, 0, 0); hit_any = False
        for hz in (o.z - e.z * 0.5, o.z + e.z * 0.4):
            for dx, dy, ext in ((1, 0, e.x), (-1, 0, e.x), (0, 1, e.y), (0, -1, e.y)):
                start = unreal.Vector(o.x, o.y, hz)
                r = _trace(world, start, unreal.Vector(o.x + dx * (ext + 2), o.y + dy * (ext + 2), hz), spawned)
                if r is not None:
                    pen = ext + 2 - r[0]
                    if pen > 0.5:
                        hit_any = True
                        if dx: push.x = -dx * max(abs(push.x), pen)
                        if dy: push.y = -dy * max(abs(push.y), pen)
        if not hit_any:
            return "moved" if moved else True
        if abs(push.x) > 120 or abs(push.y) > 120:
            return None
        l = a.get_actor_location()
        a.set_actor_location(unreal.Vector(l.x + push.x, l.y + push.y, l.z), False, True)
        moved = True
    return None


PHYS_CLASS = {"paper": "/Script/UniversityGame.LoosePaper"}
PHYS_CLASS.update({k: "/Script/UniversityGame.GrabbableProp" for k in ("box_closed", "box_open", "box_crushed", "bin", "cone")})
_class_cache = {}


def phys_class(key, it):
    if not PHYSICS_PROPS or key not in PHYS_CLASS:
        return None
    if key == "paper" and min(abs(it["z"] - f) for f in (F1, F2)) > 2.0:
        return None                                              # papers on desks / tables stay static
    path = PHYS_CLASS[key]
    if path not in _class_cache:
        try:
            _class_cache[path] = unreal.load_class(None, path)
        except Exception:
            _class_cache[path] = None
        if _class_cache[path] is None:
            warn("C++ class %s not found - build the project in your IDE first; placing plain static props instead" % path)
    return _class_cache[path]


def spawn_prop(key, mesh, it):
    loc = unreal.Vector(it["x"], it["y"], it["z"])
    rot = unreal.Rotator(it["roll"], it["pitch"], it["yaw"])
    cls = phys_class(key, it)
    if cls is None:
        return eas.spawn_actor_from_object(mesh, loc, rot)
    if key == "paper":
        loc.z += 0.45                                            # LoosePaper's 0.8 cm thick body rests on the floor
    a = eas.spawn_actor_from_class(cls, loc, rot)
    if a is not None:
        a.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(mesh)
    return a


def settle_on_desk(world, a, it, spawned):
    """desk clutter: every corner of the prop must stand on the desk top - otherwise slide it towards the middle of
    the desk in 3 cm steps (max 45 cm); traces ignore our props, so they only see the desk / monitor feet"""
    cx, cy = it["centre"]
    l0 = a.get_actor_location()
    dx, dy = cx - l0.x, cy - l0.y
    dl = math.hypot(dx, dy) or 1.0
    dx, dy = dx / dl, dy / dl
    for step in range(16):
        o, e = a.get_actor_bounds(False)
        zt = it["z"]
        ok = True
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            px, py = o.x + sx * e.x * 0.9, o.y + sy * e.y * 0.9
            r = _trace(world, unreal.Vector(px, py, zt + 6), unreal.Vector(px, py, zt - 4), spawned)
            if r is None or r[1].z < zt - 2.5:
                ok = False; break
        if ok:
            return "moved" if step else True
        if step * 3 >= 45:
            break
        l = a.get_actor_location()
        a.set_actor_location(unreal.Vector(l.x + dx * 3, l.y + dy * 3, l.z), False, True)
    a.set_actor_location(l0, False, True)                        # nothing better found - keep the planned spot
    return True


def snap_to_wall(world, a, it, spawned):
    """clock / cork board: find the real wall surface behind the pivot and hang the back on it"""
    yaw = math.radians(it["yaw"])
    fx, fy = -math.sin(yaw), math.cos(yaw)                      # local +Y = front
    sx, sy = fy, -fx                                             # along the wall
    l = a.get_actor_location()
    # the planned spot first, then slide along the wall / a bit lower (doorways, glass, window gaps)
    for s, dz in ((0, 0), (60, 0), (-60, 0), (120, 0), (-120, 0), (0, -40), (180, 0), (-180, 0), (60, -40), (-60, -40)):
        cx, cy, cz = l.x + sx * s, l.y + sy * s, l.z + dz
        r = _trace(world, unreal.Vector(cx + fx * 60, cy + fy * 60, cz), unreal.Vector(cx - fx * 60, cy - fy * 60, cz), spawned)
        if r is None:
            continue
        p = r[1]
        a.set_actor_location(unreal.Vector(p.x + fx * 0.5, p.y + fy * 0.5, cz), False, True)
        if keep_clear_wall(world, a, spawned, fx, fy):
            return "moved" if (s or dz or abs(r[0] - 60) > 1) else True
    return None                                                  # no wall anywhere near


def keep_clear_wall(world, a, spawned, fx, fy):
    """a hung prop must not stick into a side wall / window frame: check left and right edges"""
    o, e = a.get_actor_bounds(False)
    for d in (1, -1):
        sx, sy = fy * d, -fx * d
        ext = abs(sx) * e.x + abs(sy) * e.y
        c = unreal.Vector(o.x + fx * 3, o.y + fy * 3, o.z)
        r = _trace(world, c, unreal.Vector(c.x + sx * (ext + 1), c.y + sy * (ext + 1), c.z), spawned)
        if r is not None and r[0] < ext:
            return False
    return True

def ensure_assets():
    missing = [kit for kit, keys in KITS.items() if not all(eal.does_asset_exist(M[k]) for k in keys)]
    if missing:
        before = {a.get_path_name() for a in eas.get_all_level_actors()}
        for kit in missing:
            log("importing missing kit " + kit)
            try:
                runpy.run_path(os.path.join(ROOT, kit, "import_to_unreal.py"), run_name="__main__")
            except Exception as e:
                warn("could not import %s: %s" % (kit, e))
        for a in eas.get_all_level_actors():                    # kit scripts drop samples in front of the camera
            if a.get_path_name() not in before:
                eas.destroy_actor(a)
    ok = True
    for k, p in M.items():
        if not eal.does_asset_exist(p):
            warn("missing asset " + p); ok = False
    return ok


def mesh_path(a):
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c is None:
        return ""
    sm = c.get_editor_property("static_mesh")
    return sm.get_path_name().split(".")[0] if sm else ""


def ident(a):
    p = mesh_path(a)
    return p if p else a.get_class().get_name()


def has_tag(a, t):
    return any(str(x) == t for x in a.get_editor_property("tags"))


def main():
    rng = random.Random(SEED)
    if not ensure_assets():
        warn("some assets are missing - see above"); return
    with unreal.ScopedEditorTransaction("Abandoned office interior"):
        actors = eas.get_all_level_actors()
        old = [a for a in actors if has_tag(a, TAG)]
        for a in old:
            eas.destroy_actor(a)
        if old:
            log("removed %d actor(s) from the previous run" % len(old))
        actors = [a for a in eas.get_all_level_actors() if not has_tag(a, "AO_Exterior")]
        # ---- stray copy of floor 2 floating 160 cm above floor 5 (and a bench on floor 4)
        if REMOVE_STRAYS:
            index = {}
            for a in actors:
                l = a.get_actor_location()
                index.setdefault((ident(a), round(l.x), round(l.y)), []).append((l.z, a))
            strays = []
            for a in actors:
                l = a.get_actor_location()
                if l.z < 1200 or a.get_class().get_name() in NO_COPY:
                    continue
                for z, b in index.get((ident(a), round(l.x), round(l.y)), []):
                    if b is not a and abs((l.z - z) - 1360.0) < 2.0:
                        strays.append(a); break
            for a in strays:
                eas.destroy_actor(a)
            log("removed %d floating stray actor(s) (misplaced copy at +13.6 m)" % len(strays))
        # ---- the office pack's fresh green pot plants -> dead ones (originals hidden, not deleted; restored on re-run)
        for a in actors:
            if has_tag(a, REPLACED):
                a.set_is_temporarily_hidden_in_editor(False); a.set_actor_hidden_in_game(False)
                a.set_actor_enable_collision(True); a.set_editor_property("tags", [])
        pots = 0
        if REPLACE_POTS:
            dead = eal.load_asset(M["plant"])
            for a in actors:
                if "flower_pot" not in ident(a).lower():
                    continue
                l = a.get_actor_location()
                if l.z > F2 + 5:                                  # only floors 1-2; 3-4 get theirs from the copy
                    continue
                n = eas.spawn_actor_from_object(dead, l, unreal.Rotator(0, 0, random.Random(int(l.x * 7 + l.y)).uniform(0, 360)))
                if n is None:
                    continue
                n.set_actor_label("DeadPot_" + a.get_actor_label())
                n.set_folder_path("AbandonedOffice/Interior/DeadPots")
                n.set_editor_property("tags", [TAG])
                a.set_actor_hidden_in_game(True); a.set_is_temporarily_hidden_in_editor(True)
                a.set_actor_enable_collision(False); a.set_editor_property("tags", [REPLACED])
                pots += 1
            log("replaced %d green pot plant(s) with dead ones" % pots)
        # ---- new props on floors 1 and 2 (each one checked against walls / furniture with traces)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        meshes = {}
        spawned = []
        placed = moved = dropped = 0
        for it in plan(rng):
            key = it["key"]
            if key not in meshes:
                meshes[key] = eal.load_asset(M[key])
            a = spawn_prop(key, meshes[key], it)
            if a is None:
                continue
            if key == "cone" and it["roll"]:
                a.set_actor_location(unreal.Vector(it["x"], it["y"], it["z"] + 18), False, True)
            spawned.append(a)
            if it.get("centre"):
                ok = settle_on_desk(world, a, it, spawned)
            elif key in WALL_MOUNTED:
                ok = snap_to_wall(world, a, it, spawned)
            elif key in FLOOR_STANDING:
                ok = keep_clear(world, a, spawned)
            else:
                ok = True
            if ok is None:
                eas.destroy_actor(a); spawned.remove(a); dropped += 1
                warn("%s did not fit (wall or furniture in the way) - left out" % it["label"])
                continue
            moved += 1 if ok == "moved" else 0
            a.set_actor_label(it["label"])
            a.set_folder_path("AbandonedOffice/Interior/" + it["group"])
            a.set_editor_property("tags", [TAG])
            placed += 1
        log("placed %d new props on floors 1-2 (%d nudged off a wall / furniture, %d left out)" % (placed, moved, dropped))
        # ---- copy floor 2 to the storeys in COPY_TO
        actors = [a for a in eas.get_all_level_actors() if not has_tag(a, "AO_Exterior")]
        f2 = [a for a in actors if F2 - 5 <= a.get_actor_location().z < F2 + FLOOR_H - 5 and not has_tag(a, REPLACED)
              and not any(a.get_class().get_name().startswith(c) for c in NO_COPY)]
        present = {}
        for a in actors:
            l = a.get_actor_location()
            present.setdefault(ident(a), []).append((l.x, l.y, l.z))
        for fl in COPY_TO:
            dz = (fl - 2) * FLOOR_H
            n_new = n_skip = 0
            for a in f2:
                l = a.get_actor_location()
                tgt = (l.x, l.y, l.z + dz)
                if any(abs(p[0] - tgt[0]) < 3 and abs(p[1] - tgt[1]) < 3 and abs(p[2] - tgt[2]) < 3 for p in present.get(ident(a), [])):
                    n_skip += 1; continue                         # already there (floor slab, core walls, doors...)
                c = eas.duplicate_actor(a, None, unreal.Vector(0, 0, dz))
                if c is None:
                    continue
                c.set_actor_label("F%d_%s" % (fl, a.get_actor_label()))
                c.set_folder_path("AbandonedOffice/Interior/Floor%d" % fl)
                c.set_editor_property("tags", [TAG])
                n_new += 1
            log("floor %d: copied %d actors from floor 2 (%d already there)" % (fl, n_new, n_skip))
    log("done - save the level (Ctrl+S). Re-run any time; change SEED for different clutter")


if __name__ == "__main__":
    main()
