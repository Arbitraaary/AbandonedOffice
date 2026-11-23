"""
Lab 6: lists what is on OfficeMap (lights, doors/glass, ceilings, guard/obstacles) so the animated objects can be placed.
Writes scene_dump.json next to this file. Changes nothing.
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Lab6/Scene/dump_scene.py"
"""
import json
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = []
for a in eas.get_all_level_actors():
    cls = a.get_class().get_name()
    label = a.get_actor_label()
    mesh = ""
    if isinstance(a, unreal.StaticMeshActor):
        sm = a.static_mesh_component.static_mesh
        mesh = sm.get_path_name() if sm else ""
    keep = (isinstance(a, unreal.Light) or "Light" in cls or "Lamp" in label or "lamp" in mesh.lower()
            or "light" in mesh.lower() or "door" in label.lower() or "door" in mesh.lower()
            or "glass" in label.lower() or "glass" in mesh.lower() or "entr" in label.lower()
            or "ceiling" in label.lower() or "ceiling" in mesh.lower() or "Lab5" in str(a.get_folder_path())
            or "Lobby" in label or "PlayerStart" in cls or "window" in mesh.lower())
    if not keep:
        continue
    o, ext = a.get_actor_bounds(False)
    l = a.get_actor_location()
    r = a.get_actor_rotation()
    e = {"label": label, "class": cls, "mesh": mesh, "folder": str(a.get_folder_path()),
         "loc": [round(l.x), round(l.y), round(l.z)], "yaw": round(r.yaw, 1),
         "bmin": [round(o.x - ext.x), round(o.y - ext.y), round(o.z - ext.z)],
         "bmax": [round(o.x + ext.x), round(o.y + ext.y), round(o.z + ext.z)]}
    if isinstance(a, unreal.Light):
        lc = a.get_component_by_class(unreal.LightComponent)
        if lc:
            e["intensity"] = lc.get_editor_property("intensity")
            e["mobility"] = str(lc.get_editor_property("mobility"))
    out.append(e)
with open(os.path.join(HERE, "scene_dump.json"), "w") as f:
    json.dump(out, f, indent=0)
unreal.log("[Lab6] scene_dump.json: %d actors" % len(out))
