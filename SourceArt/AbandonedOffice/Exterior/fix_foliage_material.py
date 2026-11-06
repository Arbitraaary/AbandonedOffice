"""
Repairs M_AbandonedFoliage (leaves / grass showed a grey checkerboard: the wind function was missing its
required inputs, so the material failed to compile and Unreal fell back to the default material).
The wind is now built from plain nodes, so nothing can be left unconnected.
Rebuilds the graph from scratch: masked, two-sided foliage, T_Foliage colour + alpha, gentle wind.

    py "D:/UE_Projects/UniversityGame/SourceArt/AbandonedOffice/Exterior/fix_foliage_material.py"
"""
import unreal

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
PATH = "/Game/_Game/Environment/AbandonedOffice/Materials/M_AbandonedFoliage"
TEX = "/Game/_Game/Environment/AbandonedOffice/Exterior/Textures/T_Foliage"

mat = eal.load_asset(PATH)
tex = eal.load_asset(TEX)
mel.delete_all_material_expressions(mat)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
mat.set_editor_property("two_sided", True)
mat.set_editor_property("opacity_mask_clip_value", 0.4)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)
s = E(unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
s.set_editor_property("parameter_name", "Foliage"); s.set_editor_property("texture", tex)
tint = E(unreal.MaterialExpressionVectorParameter, -700, -250)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
mul = E(unreal.MaterialExpressionMultiply, -400, -150)
mel.connect_material_expressions(s, "RGB", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(s, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
sss = E(unreal.MaterialExpressionMultiply, -400, 100)
mel.connect_material_expressions(mul, "", sss, "A"); sss.set_editor_property("const_b", 0.6)
mel.connect_material_property(sss, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
rough = E(unreal.MaterialExpressionScalarParameter, -400, 250)
rough.set_editor_property("parameter_name", "Roughness"); rough.set_editor_property("default_value", 0.75)
mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
# gentle sway built from plain nodes (no SimpleGrassWind: its required inputs broke the compile)
#   WPO = (1, 0.6, 0.15) * Amp * sin(Time * Speed + dot(WorldPos, (0.004, 0.003, 0.002)))
t = E(unreal.MaterialExpressionTime, -1100, 450)
spd = E(unreal.MaterialExpressionScalarParameter, -1100, 520)
spd.set_editor_property("parameter_name", "WindSpeed"); spd.set_editor_property("default_value", 1.4)
ts = E(unreal.MaterialExpressionMultiply, -900, 470)
mel.connect_material_expressions(t, "", ts, "A"); mel.connect_material_expressions(spd, "", ts, "B")
wp = E(unreal.MaterialExpressionWorldPosition, -1100, 620)
k = E(unreal.MaterialExpressionConstant3Vector, -1100, 700)
k.set_editor_property("constant", unreal.LinearColor(0.004, 0.003, 0.002, 0))
dp = E(unreal.MaterialExpressionDotProduct, -900, 640)
mel.connect_material_expressions(wp, "", dp, "A"); mel.connect_material_expressions(k, "", dp, "B")
ph = E(unreal.MaterialExpressionAdd, -750, 520)
mel.connect_material_expressions(ts, "", ph, "A"); mel.connect_material_expressions(dp, "", ph, "B")
sn = E(unreal.MaterialExpressionSine, -620, 520)
sn.set_editor_property("period", 6.283185)
mel.connect_material_expressions(ph, "", sn, "")
amp = E(unreal.MaterialExpressionScalarParameter, -620, 620)
amp.set_editor_property("parameter_name", "WindAmplitude"); amp.set_editor_property("default_value", 2.5)
m1 = E(unreal.MaterialExpressionMultiply, -480, 560)
mel.connect_material_expressions(sn, "", m1, "A"); mel.connect_material_expressions(amp, "", m1, "B")
dirv = E(unreal.MaterialExpressionConstant3Vector, -480, 680)
dirv.set_editor_property("constant", unreal.LinearColor(1.0, 0.6, 0.15, 0))
m2 = E(unreal.MaterialExpressionMultiply, -330, 600)
mel.connect_material_expressions(m1, "", m2, "A"); mel.connect_material_expressions(dirv, "", m2, "B")
mel.connect_material_property(m2, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
mel.recompile_material(mat)
eal.save_loaded_asset(mat)
mi = eal.load_asset("/Game/_Game/Environment/AbandonedOffice/Materials/MI_Foliage")
if mi:
    mel.set_material_instance_texture_parameter_value(mi, "Foliage", tex)
    mel.update_material_instance(mi); eal.save_loaded_asset(mi)
unreal.log("[AbandonedOffice] M_AbandonedFoliage rebuilt (plain-node wind, no engine function) - leaves should be textured now")
