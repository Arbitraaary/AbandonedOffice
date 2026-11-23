"""
Lab 6, task 4 (natural phenomena). Build the C++ first (ADayNightCycle, ARainWeather), then in Unreal (Output Log -> Cmd):

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Lab6/setup_lab6_weather.py"

  * M_RainDrop: translucent bluish streak for the rain drops
  * BP_Sky_Sphere: follows the sun (Directional light actor = Light Source, colours from the sun's height -> stars at night)
  * M_SunDisc / M_MoonDisc: the round sun and moon in the sky
  * Weather_DayNight: day/night cycle (sun, sky, fog, exposure, moon light, street lamps on at night, broken ones flicker)
  * Weather_Rain: random rain with lightning
Running it again replaces the two weather actors (tag Lab6Weather). Save the level afterwards (Ctrl+S).
"""
import unreal

DEST = "/Game/_Game/Environment/AbandonedOffice/Weather"
TAG = "Lab6Weather"
FOLDER = "AbandonedOffice/Lab6"

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(m):
    unreal.log("[Lab6] " + m)


def warn(m):
    unreal.log_warning("[Lab6] " + m)


def need_class(path):
    cls = unreal.load_class(None, path)
    if cls is None:
        raise RuntimeError("C++ class %s not found - build the project first" % path)
    return cls


def drop_material():
    path = DEST + "/M_RainDrop"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    eal.make_directory(DEST)
    mat = tools.create_asset("M_RainDrop", DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    col.set_editor_property("constant", unreal.LinearColor(0.70, 0.76, 0.85, 1.0))
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 150)
    op.set_editor_property("r", 0.28)
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def disc_material(name, colour, strength, craters=False):
    """unlit glowing disc for the sun / the moon (the moon gets soft darker patches)"""
    path = DEST + "/" + name
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    eal.make_directory(DEST)
    mat = tools.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -600, 0)
    col.set_editor_property("constant", unreal.LinearColor(colour[0], colour[1], colour[2], 1.0))
    k = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -600, 150)
    k.set_editor_property("r", strength)
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -380, 60)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(k, "", mul, "B")
    out = mul
    if craters:
        pos = mel.create_material_expression(mat, unreal.MaterialExpressionLocalPosition, -900, 300)
        noise = mel.create_material_expression(mat, unreal.MaterialExpressionNoise, -700, 300)
        noise.set_editor_property("scale", 0.035)
        noise.set_editor_property("output_min", 0.72)
        noise.set_editor_property("output_max", 1.0)
        mel.connect_material_expressions(pos, "", noise, "Position")
        m2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 120)
        mel.connect_material_expressions(mul, "", m2, "A")
        mel.connect_material_expressions(noise, "", m2, "B")
        out = m2
    mel.connect_material_property(out, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def main():
    day_cls = need_class("/Script/UniversityGame.DayNightCycle")
    rain_cls = need_class("/Script/UniversityGame.RainWeather")
    mat = drop_material()
    sun_mat = disc_material("M_SunDisc", (1.0, 0.93, 0.78), 40.0)
    moon_mat = disc_material("M_MoonDisc", (0.82, 0.86, 0.95), 3.0, craters=True)
    actors = eas.get_all_level_actors()
    for a in actors:
        if TAG in [str(t) for t in a.tags]:
            eas.destroy_actor(a)
    actors = eas.get_all_level_actors()

    sun = next((a for a in actors if isinstance(a, unreal.DirectionalLight)), None)
    sky = next((a for a in actors if "Sky_Sphere" in a.get_class().get_name()), None)
    if sky and sun:
        for prop, val in (("directional_light_actor", sun), ("colors_determined_by_sun_position", True)):
            try:
                sky.set_editor_property(prop, val)
            except Exception as e:
                warn("sky sphere %s not set (%s)" % (prop, e))
        log("BP_Sky_Sphere follows %s" % sun.get_actor_label())
    else:
        warn("sun or sky sphere not found (sun %s, sky %s)" % (sun, sky))

    # the old atmospheric fog draws a second (not quite round) sun: switch its disc off
    for a in actors:
        if a.get_class().get_name() == "AtmosphericFog":
            for c in a.get_components_by_class(unreal.ActorComponent):
                try:
                    c.set_editor_property("disable_sun_disk", True)
                    log("AtmosphericFog: sun disk off")
                except Exception:
                    pass

    lamps, broken = [], []
    for a in actors:
        if isinstance(a, unreal.StaticMeshActor):
            sm = a.static_mesh_component.static_mesh
            if sm and sm.get_name() == "SM_StreetLamp":
                lamps.append(a)
            elif sm and sm.get_name() == "SM_StreetLamp_Broken":
                broken.append(a)

    def spawn(cls, label, loc):
        x = eas.spawn_actor_from_class(cls, loc, unreal.Rotator(0, 0, 0))
        x.set_actor_label(label)
        x.set_folder_path(FOLDER)
        x.set_editor_property("tags", [TAG])
        return x

    rain = spawn(rain_cls, "Weather_Rain", unreal.Vector(0, 4000, 1500))
    rain.set_editor_property("drop_material", mat)
    day = spawn(day_cls, "Weather_DayNight", unreal.Vector(0, 4000, 1600))
    if sun:
        day.set_editor_property("sun", sun)
        day.set_editor_property("sun_yaw", sun.get_actor_rotation().yaw)
    if sky:
        day.set_editor_property("sky_sphere", sky)
    day.set_editor_property("sun_material", sun_mat)
    day.set_editor_property("moon_material", moon_mat)
    day.set_editor_property("street_lamps", lamps)
    day.set_editor_property("broken_street_lamps", broken)
    log("Weather_DayNight: %d street lamps, %d broken; Weather_Rain placed" % (len(lamps), len(broken)))
    log("done - save the level (Ctrl+S), then Play")


main()
