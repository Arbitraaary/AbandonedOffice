# Guard rifle pose builder: UE local bone transforms <-> Blender pose, rifle on hand_r_val_socket, preview renders.
import bpy, json, math, sys
from mathutils import Matrix, Quaternion, Vector

D = json.load(open("/home/claude/pose/guard_rifle_data.json"))
F4 = Matrix.Diagonal((1, -1, 1, 1))
K = Matrix(((0, -1, 0), (1, 0, 0), (0, 0, -1)))          # UE bone-local -> Blender bone-local
K4 = K.to_4x4(); K4T = K.transposed().to_4x4()


def ue_quat_matrix(q):           # q = [x,y,z,w]
    return Quaternion((q[3], q[0], q[1], q[2])).to_matrix().to_4x4()


def ue_tr(loc, quat):
    m = ue_quat_matrix(quat); m.translation = Vector(loc); return m


def ue_rotator_quat(roll, pitch, yaw):
    d = math.pi / 360.0
    sp, cp = math.sin(pitch * d), math.cos(pitch * d)
    sy, cy = math.sin(yaw * d), math.cos(yaw * d)
    sr, cr = math.sin(roll * d), math.cos(roll * d)
    return [cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy]


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath="/home/claude/guard/in/SK_Mannequin_Enemy.fbx", automatic_bone_orientation=False,
                             primary_bone_axis='X', secondary_bone_axis='Y', ignore_leaf_bones=False)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    body = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    # rifle
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath="/home/claude/pose/AR4.fbx", automatic_bone_orientation=False,
                             primary_bone_axis='X', secondary_bone_axis='Y', ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before]
    gun = [o for o in new if o.type == 'MESH'][0]
    bpy.context.view_layer.update()
    gun_ue = F4 @ Matrix.Scale(100, 4) @ gun.matrix_world        # gun vertices -> UE mesh space (cm)
    gun.data.transform(gun_ue)
    gun.parent = None
    gun.matrix_world = Matrix.Identity(4)
    for o in new:
        if o is not gun:
            bpy.data.objects.remove(o, do_unlink=True)
    return arm, body, gun


def rest_ue(arm):
    """UE component-space rest matrices from the Blender rest pose"""
    return {b.name: F4 @ b.matrix_local @ K4 for b in arm.data.bones}


def apply_pose(arm, local_ue):
    """local_ue: bone -> UE local 4x4 (bones missing use the rest local). Returns UE component-space matrices."""
    R = rest_ue(arm)
    comp = {}
    for b in arm.data.bones:                       # parents come first
        if b.name in local_ue:
            L = local_ue[b.name]
        else:
            L = (R[b.parent.name].inverted() @ R[b.name]) if b.parent else R[b.name]
        comp[b.name] = (comp[b.parent.name] @ L) if b.parent else L
    for b in arm.data.bones:
        pb = arm.pose.bones[b.name]
        Pb = F4 @ comp[b.name] @ K4T
        if b.parent:
            Ppb = F4 @ comp[b.parent.name] @ K4T
            rest_rel = b.parent.matrix_local.inverted() @ b.matrix_local
            pb.matrix_basis = rest_rel.inverted() @ (Ppb.inverted() @ Pb)
        else:
            pb.matrix_basis = b.matrix_local.inverted() @ Pb
    bpy.context.view_layer.update()
    return comp


def place_gun(arm, gun, comp, socket="hand_r_val_socket"):
    s = D[socket]
    Ls = ue_tr(s["loc"], ue_rotator_quat(*s["rot"]))
    M = comp[s["bone"]] @ Ls
    gun.matrix_world = arm.matrix_world @ F4 @ M @ F4     # gun mesh is in UE space -> back to Blender
    return M


def idle_locals():
    return {b: ue_tr(v["loc"], v["quat"]) for b, v in D["idle_rifle_hip"].items() if b != "root"}


def render(path, views=("front", "side", "back3q"), res=(520, 700)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'OBJECT'
    sc.render.resolution_x, sc.render.resolution_y = res
    if "Cam" not in bpy.data.objects:
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam = bpy.data.objects["Cam"]
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.1
    import os
    outs = []
    pos = {"front": (Vector((0, -4, 0.95)), (90, 0, 0)), "side": (Vector((-4, 0, 0.95)), (90, 0, -90)),
           "back3q": (Vector((3, 3, 1.3)), (78, 0, 135)), "right": (Vector((4, 0, 0.95)), (90, 0, 90)),
           "top": (Vector((0, 0, 5)), (0, 0, 0))}
    for v in views:
        loc, rot = pos[v]
        cam.location = loc; cam.rotation_euler = [math.radians(a) for a in rot]
        sc.render.filepath = "%s_%s.png" % (path, v)
        bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
    return outs


def build_comp(arm, rot_targets, keep_idle=(), full_targets=None):
    """UE component-space pose: legs/pelvis from Idle_Rifle_Hip, bones in rot_targets get that component rotation,
    bones in keep_idle keep their idle local transform, all others their rest local transform."""
    R = rest_ue(arm)
    idle = idle_locals()
    full_targets = full_targets or {}
    comp = {}
    for b in arm.data.bones:
        n = b.name
        parent = comp[b.parent.name] if b.parent else Matrix.Identity(4)
        if n in ("pelvis",) or n.startswith(("thigh", "calf", "foot", "ball")) or n in keep_idle:
            L = idle.get(n) or ((R[b.parent.name].inverted() @ R[n]) if b.parent else R[n])
            M = parent @ L
        else:
            L = (R[b.parent.name].inverted() @ R[n]) if b.parent else R[n]
            M = parent @ L
        if n in rot_targets:
            M = rot_targets[n].to_4x4(); M.translation = (parent @ L).translation
        if n in full_targets:
            M = full_targets[n].copy()
        comp[n] = M
    return comp


def set_comp(arm, comp):
    for b in arm.data.bones:
        pb = arm.pose.bones[b.name]
        Pb = F4 @ comp[b.name] @ K4T
        if b.parent:
            Ppb = F4 @ comp[b.parent.name] @ K4T
            rest_rel = b.parent.matrix_local.inverted() @ b.matrix_local
            pb.matrix_basis = rest_rel.inverted() @ (Ppb.inverted() @ Pb)
        else:
            pb.matrix_basis = b.matrix_local.inverted() @ Pb
    bpy.context.view_layer.update()


def swing(rest_rot, dir_rest, dir_new):
    q = Vector(dir_rest).normalized().rotation_difference(Vector(dir_new).normalized())
    return q.to_matrix() @ rest_rot


def two_bone(S, H, a, b, pole):
    u = (H - S); d = min(u.length, a + b - 0.01); u.normalize()
    ca = (a * a + d * d - b * b) / (2 * a * d); sa = math.sqrt(max(0.0, 1 - ca * ca))
    w = (pole - u * pole.dot(u)).normalized()
    return S + a * (ca * u + sa * w)
