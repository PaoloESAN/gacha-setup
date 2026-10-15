"""Connect optional Genshin wrist deformation bones to the final hand pose."""


def setup_wrist_twist(rig):
    """Copy local Y from the original hand, following the Genshin wrist setup."""
    if rig is None or rig.type != 'ARMATURE':
        return

    for side in ('L', 'R'):
        hand = rig.pose.bones.get(f'ORG-hand.{side}')
        if hand is None:
            continue
        # Original FBX name and Blender's side-suffix spelling.
        for name in (f'Bone_ForearmTwist01_{side}', f'Bone_ForearmTwist01.{side}'):
            twist = rig.pose.bones.get(name)
            if twist is None:
                continue
            constraint = twist.constraints.get('Genshin Wrist Twist')
            if constraint is None:
                constraint = twist.constraints.new('COPY_ROTATION')
                constraint.name = 'Genshin Wrist Twist'
            constraint.target = rig
            constraint.subtarget = hand.name
            constraint.owner_space = 'LOCAL'
            constraint.target_space = 'LOCAL'
            constraint.euler_order = 'AUTO'
            constraint.use_x = False
            constraint.use_y = True
            constraint.use_z = False
            constraint.invert_x = False
            constraint.invert_y = False
            constraint.invert_z = False
            constraint.mix_mode = 'REPLACE'
            constraint.influence = 1.0
