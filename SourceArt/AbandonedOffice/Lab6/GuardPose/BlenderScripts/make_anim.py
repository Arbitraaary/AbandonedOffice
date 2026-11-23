import sys, json, math; sys.path.insert(0, "/home/claude/pose")
from gp import *
P = {"hand_r": (-7, 10, -51), "barrel": (0.15, 0.4, -1), "pole_r": (-0.6, -1, 0), "hand_l": (4, 3, -55), "pole_l": (0.4, -1, 0)}
arm, body, gun = setup()
body.color = (0.7, 0.7, 0.75, 1); gun.color = (0.9, 0.3, 0.1, 1)
R = rest_ue(arm)
FING = [b for b in D["idle_rifle_hip"] if b.endswith("_r") and b.split("_")[0] in ("thumb", "index", "middle", "ring", "pinky")]
Ls = ue_tr(D["hand_r_val_socket"]["loc"], ue_rotator_quat(*D["hand_r_val_socket"]["rot"]))


def pose(breath):
    """breath 0..1: chest rises a little, shoulders follow"""
    up = ["spine_01", "spine_02", "spine_03", "neck_01", "head", "clavicle_l", "clavicle_r"]
    rot = {n: R[n].to_3x3() for n in up}
    tilt = Matrix.Rotation(math.radians(-1.6 * breath), 3, Vector((1, 0, 0)))
    for n in ("spine_03", "neck_01", "head", "clavicle_l", "clavicle_r"):
        rot[n] = tilt @ rot[n]
    comp = build_comp(arm, rot, keep_idle=FING)
    S = comp["upperarm_r"].translation.copy(); H = S + Vector(P["hand_r"])
    bar = Vector(P["barrel"]).normalized(); top = Vector((0, 1, 0)); top = (top - bar * top.dot(bar)).normalized()
    G = Matrix((bar, top.cross(bar), top)).transposed()
    E = two_bone(S, H, 30.34, 26.975, Vector(P["pole_r"]))
    SL = comp["upperarm_l"].translation.copy(); HL = SL + Vector(P["hand_l"])
    EL = two_bone(SL, HL, 30.34, 26.975, Vector(P["pole_l"]))
    rot.update({"upperarm_r": swing(R["upperarm_r"].to_3x3(), -R["upperarm_r"].col[0].xyz, E - S),
                "lowerarm_r": swing(R["lowerarm_r"].to_3x3(), -R["lowerarm_r"].col[0].xyz, H - E),
                "hand_r": G @ Ls.to_3x3().inverted(),
                "upperarm_l": swing(R["upperarm_l"].to_3x3(), R["upperarm_l"].col[0].xyz, EL - SL),
                "lowerarm_l": swing(R["lowerarm_l"].to_3x3(), R["lowerarm_l"].col[0].xyz, HL - EL),
                "hand_l": swing(R["hand_l"].to_3x3(), R["lowerarm_l"].col[0].xyz, HL - EL)})
    return build_comp(arm, rot, keep_idle=FING)


sc = bpy.context.scene
sc.render.fps = 30; sc.frame_start = 0; sc.frame_end = 60
arm.animation_data_create()
act = bpy.data.actions.new("A_Guard_RifleLowered"); arm.animation_data.action = act
for f in range(0, 61, 5):
    b = 0.5 - 0.5 * math.cos(2 * math.pi * f / 60.0)
    set_comp(arm, pose(b))
    for pb in arm.pose.bones:
        pb.keyframe_insert("location", frame=f); pb.keyframe_insert("rotation_quaternion", frame=f); pb.keyframe_insert("scale", frame=f)
# preview at frame 0 with the rifle
sc.frame_set(0)
comp0 = pose(0.0); set_comp(arm, comp0); place_gun(arm, gun, comp0)
print(render("/home/claude/pose/final", ("front", "side", "back3q")))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/pose/GuardRifleLowered.blend")
# export: armature + body mesh, animation only this action
for o in bpy.data.objects: o.select_set(False)
arm.select_set(True); body.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath="/home/claude/pose/A_Guard_RifleLowered.fbx", use_selection=True,
    object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z', axis_up='Y', add_leaf_bones=False, use_armature_deform_only=False,
    primary_bone_axis='X', secondary_bone_axis='Y', bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, path_mode='STRIP')
json.dump({k: [list(r) for r in v] for k, v in comp0.items()}, open("/home/claude/pose/final_comp.json", "w"))
print("exported")
