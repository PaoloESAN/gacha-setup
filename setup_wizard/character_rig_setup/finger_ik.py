"""Enable Rigify fingertip targets without changing each game's finger axes."""


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
