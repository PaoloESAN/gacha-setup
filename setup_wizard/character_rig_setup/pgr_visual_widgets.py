"""PGR widget alignment: display properties only, never rig transforms."""
from mathutils import Matrix

HAND_WIDGET_LIFT = .02


def align_hand_ik_widgets(rig):
    for side in ('L', 'R'):
        control = rig.pose.bones.get(f'hand_ik.{side}')
        index = rig.data.bones.get(f'DEF-f_index.01.{side}')
        pinky = rig.data.bones.get(f'DEF-f_pinky.01.{side}')
        middle = rig.data.bones.get(f'DEF-f_middle.03.{side}')
        if not all((control, index, pinky, middle)) or not control.custom_shape:
            continue
        transform = control.custom_shape_transform or control
        wrist = transform.bone.head_local
        forward = middle.tail_local - wrist
        width = pinky.head_local - index.head_local
        if forward.length < 1e-6 or width.length < 1e-6:
            continue
        forward.normalize()
        width -= forward * width.dot(forward)
        if width.length < 1e-6:
            continue
        width.normalize()
        if side == 'R':
            width.negate()
        normal = forward.cross(width).normalized()
        # The bundled "hand" shape lies in Y/Z: Y along fingers, Z across palm.
        palm_frame = Matrix((normal, forward, width)).transposed()
        inverse = transform.bone.matrix_local.to_3x3().normalized().inverted()
        local_frame = inverse @ palm_frame
        control.custom_shape_rotation_euler = local_frame.to_euler('XYZ')
        control.custom_shape_translation = inverse @ (normal * HAND_WIDGET_LIFT)


def align_head_controller_widget(rig):
    control = rig.pose.bones.get('head-controller')
    eyes = rig.pose.bones.get('Eye-Track-Master')
    if not control or not eyes or not control.custom_shape or not eyes.custom_shape:
        return
    transform = control.custom_shape_transform or control
    # Bone.y_axis is relative to the parent; use the armature-space matrix.
    up = eyes.bone.matrix_local.to_3x3().col[1].normalized()
    top = max(v.co.y for v in eyes.custom_shape.data.vertices) * eyes.custom_shape_scale_xyz.y
    target = eyes.bone.head_local + up * (top + eyes.bone.length * 2)
    inverse = transform.bone.matrix_local.to_3x3().normalized().inverted()
    control.custom_shape_translation = inverse @ (target - transform.bone.head_local)
