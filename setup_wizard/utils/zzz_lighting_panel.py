"""Keep the ZZZ lighting panel's authored defaults when clearing its pose."""
import bpy
from mathutils import Matrix


def bake_zzz_rim_slider_defaults(armature, *, force=False):
    """Rebase only the two rim sliders, never the character's deform bones.

    The asset puts Rim.L at -0.0075 in pose space to switch the rim off.
    Clearing that translation turns it on. Incorporate the configured slider
    translations into their rest bones and shift the local limits by the same
    amounts, keeping their evaluated positions and full travel unchanged.
    """
    if armature is None or armature.type != 'ARMATURE':
        return 0
    tag = 'zzz_rim_slider_rest_v1'
    plans = []
    for name in ('Rim.L', 'Rim.R'):
        pose = armature.pose.bones.get(name)
        if pose is None or (pose.bone.get(tag) and not force):
            continue
        offset = pose.location.copy()
        if offset.length < 1e-9:
            pose.bone[tag] = True
            continue
        plans.append((name, offset, pose.bone.matrix_local @ Matrix.Translation(offset)))
    if not plans:
        return 0
    active = bpy.context.view_layer.objects.active
    mode = active.mode if active else 'OBJECT'
    selected = list(bpy.context.selected_objects)
    hidden = armature.hide_get()
    try:
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        armature.hide_set(False)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        for name, _, matrix in plans:
            bone = armature.data.edit_bones[name]
            length = bone.length
            bone.matrix = matrix
            bone.length = length
        bpy.ops.object.mode_set(mode='OBJECT')
        for name, offset, _ in plans:
            pose = armature.pose.bones[name]
            pose.location = (0, 0, 0)
            for constraint in pose.constraints:
                if constraint.type == 'LIMIT_LOCATION' and constraint.owner_space == 'LOCAL':
                    for axis, value in zip(('x', 'y', 'z'), offset):
                        setattr(constraint, 'min_' + axis, getattr(constraint, 'min_' + axis) - value)
                        setattr(constraint, 'max_' + axis, getattr(constraint, 'max_' + axis) - value)
            pose.bone[tag] = True
        armature.update_tag()
        bpy.context.view_layer.update()
    finally:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            obj.select_set(True)
        armature.hide_set(hidden)
        bpy.context.view_layer.objects.active = active
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
    return len(plans)
