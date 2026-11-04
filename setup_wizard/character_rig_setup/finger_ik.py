"""Enable Rigify fingertip targets without changing each game's finger axes."""


def fit_wuwa_fingertips(metarig, meshes):
    """Replace UEFormat's display tails with the skinned fingertip positions.

    Rigify uses the last phalanx tail both to place its IK target and to size
    its sphere (0.7 * phalanx length). UEFormat supplies arbitrary 4 cm tails.
    Keep the native Rigify widget settings used by Genshin/ZZZ and fix the
    input geometry instead. Skin weights and joint heads remain untouched.
    """
    import bpy

    samples = {}
    for mesh in meshes:
        if mesh.type != 'MESH' or not any(
                mod.type == 'ARMATURE' and mod.object == metarig for mod in mesh.modifiers):
            continue
        matrix = metarig.matrix_world.inverted() @ mesh.matrix_world
        groups = {g.index: g.name for g in mesh.vertex_groups}
        for vertex in mesh.data.vertices:
            for weight in vertex.groups:
                name = groups[weight.group]
                if weight.weight > 0.5 and name.endswith(('.03.L', '.03.R')):
                    samples.setdefault(name, []).append(matrix @ vertex.co)

    bpy.ops.object.mode_set(mode='EDIT')
    bones = metarig.data.edit_bones
    fitted = 0
    for side in ('L', 'R'):
        for finger in ('thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky'):
            chain = [bones.get(f'{finger}.{i:02d}.{side}') for i in (1, 2, 3)]
            if not all(chain):
                continue
            first, middle, tip = chain
            direction = tip.head - middle.head
            if direction.length < 1e-6:
                continue
            direction.normalize()
            length = max(((point - tip.head).dot(direction)
                          for point in samples.get(tip.name, [])), default=0.0)
            if length <= 1e-6:
                continue
            # Preserve each joint's roll reference while connecting the chain.
            for bone, end in ((first, middle.head.copy()), (middle, tip.head.copy()),
                              (tip, tip.head + direction * length)):
                roll_axis = bone.z_axis.copy()
                bone.tail = end
                bone.align_roll(roll_axis)
            fitted += 1
    bpy.ops.object.mode_set(mode='POSE')
    return fitted


def enable_finger_ik_controls(metarig):
    """Configure actual super-finger chains, including nonstandard bone names."""
    if metarig is None or metarig.type != 'ARMATURE' or metarig.pose is None:
        return 0
    count = 0
    for bone in metarig.pose.bones:
        if bone.rigify_type != 'limbs.super_finger':
            continue
        bone.rigify_parameters.make_extra_ik_control = True
        count += 1
    return count
