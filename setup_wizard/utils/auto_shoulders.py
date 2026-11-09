"""Genshin-style automatic shoulder tracking for humanoid Rigify rigs."""
import bpy
from mathutils import Vector


def has_auto_shoulders(rig):
    if rig is None or rig.type != 'ARMATURE' or rig.pose is None:
        return False
    plate = rig.pose.bones.get('plate-settings')
    if plate is None or 'Toggle Shoulder Constraints' not in plate:
        return False
    for side in ('L', 'R'):
        shoulder = rig.pose.bones.get('shoulder.' + side)
        follow = rig.pose.bones.get('MCH-shoulder_follow.' + side)
        driver = rig.pose.bones.get('shoulder_driver.' + side)
        if not shoulder or not follow or not driver or shoulder.parent != follow:
            return False
        if not any(c.type == 'DAMPED_TRACK' and c.target == rig and c.subtarget == driver.name
                   for c in follow.constraints):
            return False
        if not any(c.type == 'COPY_LOCATION' and c.target == rig and c.subtarget in {
                'hand-ik-' + side, 'hand_ik.' + side, 'MCH-shoulder_hand.' + side}
                   for c in driver.constraints):
            return False
    return True


def auto_shoulders_ui_splice():
    return {
        'divider': 'num_rig_separators[0] += 1',
        'text': '\n        if is_selected({"plate-settings"}):\n            layout.prop(pose_bones["plate-settings"], \'["Toggle Shoulder Constraints"]\', text="Auto Shoulder Constraints", slider=True)',
    }


def setup_auto_shoulders(rig):
    if rig is None or rig.type != 'ARMATURE' or rig.pose is None:
        return False
    # Keep working Genshin/NPC and previously generated rigs intact.
    if has_auto_shoulders(rig):
        return True
    plate = rig.pose.bones.get('plate-settings')
    if plate is None:
        return False
    required = ['shoulder.' + side for side in ('L', 'R')]
    hands = {side: next((name for name in ('hand-ik-' + side, 'hand_ik.' + side)
                         if name in rig.data.bones), None) for side in ('L', 'R')}
    chest = next((name for name in ('ORG-spine.003', 'chest', 'spine_fk.003', 'ORG-Spine2', 'DEF-spine.003')
                  if name in rig.data.bones), None)
    if chest is None or not all(hands.values()) or not all(name in rig.data.bones for name in required):
        return False
    previous_active = bpy.context.view_layer.objects.active
    previous_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
    previous_selected = list(bpy.context.selected_objects)
    previous_hidden = rig.hide_get()
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bones = rig.data.edit_bones
    for side in ('L', 'R'):
        shoulder = bones['shoulder.' + side]
        hand = bones[hands[side]]
        # Preserve each game's rest hierarchy (WuWa uses ORG-Spine2).
        parent = shoulder.parent
        if parent and parent.name == 'MCH-shoulder_follow.' + side:
            parent = parent.parent
        parent = parent or bones[chest]
        direction = shoulder.tail - shoulder.head
        if abs(direction.x) > 1e-6:
            position = shoulder.head + direction * ((hand.head.x - shoulder.head.x) / direction.x)
        else:
            position = shoulder.head + direction.normalized() * max((hand.head - shoulder.head).length, shoulder.length)
        driver_name, follow_name = 'shoulder_driver.' + side, 'MCH-shoulder_follow.' + side
        driver = bones.get(driver_name) or bones.new(driver_name)
        driver.head, driver.tail = position, position + Vector((0, .1, 0))
        driver.parent = parent
        driver.use_connect = driver.use_deform = False
        motion_name = 'MCH-shoulder_hand.' + side
        motion = bones.get(motion_name) or bones.new(motion_name)
        motion.head, motion.tail, motion.roll = driver.head.copy(), driver.tail.copy(), driver.roll
        motion.parent = parent
        motion.use_connect = motion.use_deform = False
        follow = bones.get(follow_name) or bones.new(follow_name)
        follow.head, follow.tail, follow.roll = shoulder.head.copy(), shoulder.tail.copy(), shoulder.roll
        follow.parent = parent
        follow.use_connect = follow.use_deform = False
        shoulder.use_connect = False
        shoulder.parent = follow
    bpy.ops.object.mode_set(mode='OBJECT')
    if 'Toggle Shoulder Constraints' not in plate:
        plate['Toggle Shoulder Constraints'] = 1.0
    plate.id_properties_ui('Toggle Shoulder Constraints').update(
        min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, default=1.0,
        description='Automatic shoulder follow, matching the Genshin rig')
    for side in ('L', 'R'):
        follow = rig.pose.bones['MCH-shoulder_follow.' + side]
        driver = rig.pose.bones['shoulder_driver.' + side]
        motion = rig.pose.bones['MCH-shoulder_hand.' + side]
        # Rigify's hand-parent switch references the shoulder even when that
        # parent is not selected. Reading the evaluated hand with a constraint
        # would therefore create a cycle. Read only its authored translation
        # channels, rotating them into the independent mechanism's rest axes.
        axes = motion.bone.matrix_local.to_3x3().inverted() @ rig.data.bones[hands[side]].matrix_local.to_3x3()
        for axis in range(3):
            translation = motion.driver_add('location', axis).driver
            translation.type = 'SCRIPTED'
            for variable in list(translation.variables):
                translation.variables.remove(variable)
            for component, name in enumerate(('x', 'y', 'z')):
                variable = translation.variables.new()
                variable.name, variable.type = name, 'SINGLE_PROP'
                variable.targets[0].id = rig
                variable.targets[0].data_path = f'pose.bones["{hands[side]}"].location[{component}]'
            translation.expression = ' + '.join(f'{axes[axis][component]:.9g} * {name}'
                                                for component, name in enumerate(('x', 'y', 'z')))
        track = follow.constraints.get('Auto Shoulder') or follow.constraints.new('DAMPED_TRACK')
        track.name = 'Auto Shoulder'
        track.target, track.subtarget = rig, driver.name
        track.track_axis = 'TRACK_Y'
        location = driver.constraints.get('Auto Shoulder Hand') or driver.constraints.new('COPY_LOCATION')
        location.name = 'Auto Shoulder Hand'
        location.target, location.subtarget = rig, motion.name
        location.target_space, location.owner_space = 'LOCAL_OWNER_ORIENT', 'LOCAL'
        influence = track.driver_add('influence').driver
        influence.type = 'SCRIPTED'
        for variable in list(influence.variables):
            influence.variables.remove(variable)
        variable = influence.variables.new()
        variable.name, variable.type = 'bone', 'SINGLE_PROP'
        variable.targets[0].id = rig
        variable.targets[0].data_path = 'pose.bones["plate-settings"]["Toggle Shoulder Constraints"]'
        influence.expression = 'bone * 0.4'
        follow.bone.hide = driver.bone.hide = motion.bone.hide = True
    rig.update_tag()
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in previous_selected:
        obj.select_set(True)
    rig.hide_set(previous_hidden)
    bpy.context.view_layer.objects.active = previous_active
    if previous_active and previous_mode in {'POSE', 'EDIT'}:
        bpy.ops.object.mode_set(mode=previous_mode)
    return True
