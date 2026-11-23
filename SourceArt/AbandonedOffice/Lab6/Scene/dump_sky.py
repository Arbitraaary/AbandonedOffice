"""
Lab 6: what makes the sky and the outdoor light on OfficeMap (for the day/night cycle and the rain).
Writes sky_dump.json next to this file. Changes nothing.
    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Lab6/Scene/dump_sky.py"
"""
import json
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {"actors": [], "streetlamps": []}
WORDS = ("Sky", "Fog", "Cloud", "Atmosphere", "PostProcess", "Directional", "Exponential", "Volume", "Weather", "Rain", "Sun")
for a in eas.get_all_level_actors():
    cls = a.get_class().get_name()
    label = a.get_actor_label()
    if isinstance(a, unreal.StaticMeshActor):
        sm = a.static_mesh_component.static_mesh
        if sm and "StreetLamp" in sm.get_name():
            o, e = a.get_actor_bounds(False)
            out["streetlamps"].append({"label": label, "mesh": sm.get_name(), "loc": [round(v) for v in a.get_actor_location().to_tuple()],
                                       "yaw": round(a.get_actor_rotation().yaw), "top": round(o.z + e.z),
                                       "bmin": [round(o.x - e.x), round(o.y - e.y)], "bmax": [round(o.x + e.x), round(o.y + e.y)]})
        continue
    if not any(w in cls or w in label for w in WORDS):
        continue
    e = {"label": label, "class": cls, "path": a.get_class().get_path_name(), "loc": [round(v) for v in a.get_actor_location().to_tuple()],
         "rot": [round(v, 1) for v in (a.get_actor_rotation().roll, a.get_actor_rotation().pitch, a.get_actor_rotation().yaw)]}
    for c in a.get_components_by_class(unreal.ActorComponent):
        cd = {"comp": c.get_class().get_name()}
        for prop in ("intensity", "light_color", "mobility", "atmosphere_sun_light", "real_time_capture", "source_type",
                     "cubemap", "fog_density", "fog_height_falloff", "volumetric_fog", "cast_shadows", "use_temperature",
                     "temperature", "static_mesh"):
            try:
                v = c.get_editor_property(prop)
                cd[prop] = v.get_path_name() if hasattr(v, "get_path_name") else str(v)
            except Exception:
                pass
        e.setdefault("components", []).append(cd)
    out["actors"].append(e)
with open(os.path.join(HERE, "sky_dump.json"), "w") as f:
    json.dump(out, f, indent=1)
unreal.log("[Lab6] sky_dump.json: %d sky/light actors, %d street lamps" % (len(out["actors"]), len(out["streetlamps"])))
