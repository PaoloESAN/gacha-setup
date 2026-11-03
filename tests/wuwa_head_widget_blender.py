"""Check the visible head ring after a complete WuWa setup.

blender -b --factory-startup --python-exit-code 1 --python
tests/wuwa_head_widget_blender.py -- character.blend [other-character.blend]
"""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

paths = sys.argv[sys.argv.index('--') + 1:]
for path in paths:
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
    head = rig.pose.bones['head']
    eyes = [rig.matrix_world @ rig.pose.bones[f'Eye.{s}'].head for s in ('L', 'R')]
    eye_center = (eyes[0] + eyes[1]) * .5
    eye_width = (eyes[0] - eyes[1]).length
    length = head.bone.length if head.use_custom_shape_bone_size else 1.
    basis = rig.matrix_world @ (head.custom_shape_transform or head).matrix
    rotation = head.custom_shape_rotation_euler.to_matrix()
    points = [basis @ (rotation @ Vector(tuple(v.co[i] * head.custom_shape_scale_xyz[i] * length
                                             for i in range(3))) + head.custom_shape_translation * length)
              for v in head.custom_shape.data.vertices]
    center = sum(points, Vector()) / len(points)
    # A horizontal circle above the eyes, close to the skull, not a vertical
    # face overlay, neck ring, or a line floating far above the character.
    assert max(p.z for p in points) - min(p.z for p in points) < 1e-5
    assert eye_width * 1.4 < center.z - eye_center.z < eye_width * 4.5
    radii = [(p - center).length for p in points]
    assert max(radii) - min(radii) < 1e-5
    # RootShape.blend's neck ring radius .07, at PGR's scale 1.25.
    assert abs(min(radii) - .0875) < 1e-5
    assert eye_width < min(radii) < eye_width * 3
    for name in ('FacePanelRoot', 'FacePanel'):
        assert [c.name for c in rig.data.bones[name].collections] == ['Others']
        assert rig.data.bones[name].hide
    print('WUWA_HEAD_RING_PASS', path, 'center', tuple(center), 'radius', min(radii), flush=True)
