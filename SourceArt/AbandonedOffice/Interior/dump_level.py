"""
1) Fixes the dark trees / grass placed by place_exterior.py (Lumen treats each crown as a solid blob through
   mesh distance fields -> black crowns; grass patches also shadowed each other into black).
2) Writes a full description of the open level (every actor: mesh / class, position, rotation, scale, bounds,
   folder) + lighting settings to Saved/AbandonedOffice/level_dump.json so the interior can be planned from it.

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Interior/dump_level.py"
"""
import json
import os
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OUT = os.path.join(unreal.Paths.project_saved_dir(), "AbandonedOffice")
os.makedirs(OUT, exist_ok=True)
FOLIAGE = ("SM_Tree_", "SM_Bush", "SM_GrassPatch", "SM_Weeds")
NO_SHADOW = ("SM_GrassPatch", "SM_Weeds")


def log(m):
    unreal.log("[AbandonedOffice] " + m)


def mesh_of(a):
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c is None:
        return None, ""
    sm = c.get_editor_property("static_mesh")
    return c, (sm.get_path_name().split(".")[0] if sm else "")


def v3(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


fixed = 0
actors = eas.get_all_level_actors()
with unreal.ScopedEditorTransaction("Fix foliage lighting"):
    for a in actors:
        comp, mp = mesh_of(a)
        name = mp.rsplit("/", 1)[-1]
        if comp is not None and name.startswith(FOLIAGE):
            comp.set_editor_property("affect_distance_field_lighting", False)
            if name.startswith(NO_SHADOW):
                comp.set_editor_property("cast_shadow", False)
            fixed += 1
log("foliage lighting fixed on %d actors" % fixed)

data = {"actors": [], "lights": []}
for a in actors:
    comp, mp = mesh_of(a)
    o, e = a.get_actor_bounds(False)
    r = a.get_actor_rotation(); s = a.get_actor_scale3d()
    entry = {"label": a.get_actor_label(), "class": a.get_class().get_name(), "mesh": mp,
             "loc": v3(a.get_actor_location()), "rot": [round(r.roll, 1), round(r.pitch, 1), round(r.yaw, 1)],
             "scale": [round(s.x, 3), round(s.y, 3), round(s.z, 3)], "bounds_o": v3(o), "bounds_e": v3(e),
             "folder": str(a.get_folder_path()), "tags": [str(t) for t in a.get_editor_property("tags")]}
    if comp is not None:
        try:
            entry["materials"] = [m.get_path_name().split(".")[0] if m else "" for m in comp.get_materials()]
        except Exception:
            pass
    data["actors"].append(entry)
    cls = entry["class"]
    if cls in ("DirectionalLight", "SkyLight", "PostProcessVolume", "ExponentialHeightFog", "SkyAtmosphere"):
        info = {"class": cls, "label": entry["label"]}
        try:
            lc = a.get_component_by_class(unreal.LightComponentBase)
            if lc:
                info["intensity"] = lc.get_editor_property("intensity")
                info["mobility"] = str(lc.get_editor_property("mobility"))
        except Exception:
            pass
        if cls == "PostProcessVolume":
            try:
                st = a.get_editor_property("settings")
                info["exposure_bias"] = st.get_editor_property("auto_exposure_bias")
                info["override_bias"] = st.get_editor_property("override_auto_exposure_bias")
                info["unbound"] = a.get_editor_property("unbound")
            except Exception:
                pass
        data["lights"].append(info)
path = os.path.join(OUT, "level_dump.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
log("level description written to " + path + " (%d actors)" % len(data["actors"]))
