"""Place ZZZ foot IK widgets beneath the character's actual footwear."""
from mathutils import Vector
import bpy


def align_zzz_foot_widgets(armature):
    if not armature or armature.type != 'ARMATURE':
        return 0
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH'
              and any(mod.type == 'ARMATURE' and mod.object == armature for mod in obj.modifiers)]
    rig_inverse = armature.matrix_world.inverted()
    count = 0
    for side in ('L', 'R'):
        control = armature.pose.bones.get(f'foot_ik.{side}')
        foot = armature.data.bones.get(f'DEF-foot.{side}')
        if not control or not foot or not control.custom_shape or control.custom_shape.type != 'MESH':
            continue
        anchor = control.custom_shape_transform or control
        inverse = anchor.bone.matrix_local.inverted()
        names = {foot.name, *(bone.name for bone in foot.children_recursive), f'DEF-toe.{side}'}
        points = []
        for mesh in meshes:
            indices = {group.index for group in mesh.vertex_groups if group.name in names}
            if not indices:
                continue
            transform = inverse @ rig_inverse @ mesh.matrix_world
            points.extend(transform @ vertex.co for vertex in mesh.data.vertices
                          if sum(group.weight for group in vertex.groups if group.group in indices) > .2)
        vertices = control.custom_shape.data.vertices
        if not points or not vertices:
            continue
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        target = (low + high) * .5
        target.z = low.z - max((high.y - low.y) * .01, 1e-5)

        # The outline's origin is at its heel, not its visual center. Account
        # for both this offset and the mirrored right-foot widget scale.
        rotation = control.custom_shape_rotation_euler.to_matrix()
        scale = control.custom_shape_scale_xyz
        size = anchor.length if control.use_custom_shape_bone_size else 1.0
        displayed = [rotation @ Vector(tuple(vertex.co[axis] * scale[axis] * size for axis in range(3)))
                     for vertex in vertices]
        center = Vector(tuple((min(point[axis] for point in displayed) + max(point[axis] for point in displayed)) * .5
                              for axis in range(3)))
        control.custom_shape_translation = target - center
        count += 1
    return count
