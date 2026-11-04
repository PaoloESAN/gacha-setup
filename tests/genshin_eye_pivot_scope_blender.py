"""Real-export coverage for conservative eye fitting and authored pupil pivots."""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/genshin-eye-scope'
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        target = RUNTIME / kind / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.genshin_import_character_model import _execute_fbx_import, align_eye_bones
from setup_wizard.utils.genshin_eye_pivots import calibrate_eye_pivots

cases = [('Kinich/Avatar_Boy_Claymore_Kinich.fbx', False),
         ('Alhatham/NPC_Avatar_Male_Sword_Alhatham.fbx', True),
         ('Neuvillette/Avatar_Male_Catalyst_Neuvillette.fbx', True),
         ('Diluc/Default/Cs_Avatar_Male_Claymore_Diluc.fbx', False)]
for filename, fitted in cases:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    _execute_fbx_import(str(ROOT / 'chars/genshin' / filename))
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    if filename.startswith('Alhatham/'):
        arm.name = 'Collider'
        arm.data.name = 'Collider'
        arm['gacha_character'] = 'Collider'
    pupil_names = [f'+EyeBone {side} A02' for side in ('L', 'R')]
    pupil_before = {n: arm.data.bones[n].head_local.copy() for n in pupil_names}
    align_eye_bones(arm)
    if filename.startswith('Kinich/'):
        assert all((arm.data.bones[n].head_local - p).length < 1e-6 for n, p in pupil_before.items())
    bpy.ops.object.mode_set(mode='EDIT')
    names = [f'+EyeBone {side} A0{i}' for side in ('L', 'R') for i in (1, 2)]
    before = {n: (arm.data.edit_bones[n].head.copy(), arm.data.edit_bones[n].tail.copy()) for n in names}
    changed = calibrate_eye_pivots(arm)
    assert not changed, ('Repeated fitting changed pivots', filename, changed)
    assert all((arm.data.edit_bones[n].head - h).length < 1e-6 and
               (arm.data.edit_bones[n].tail - t).length < 1e-6 for n, (h, t) in before.items())
    # Validated exports must really have moved away from the long source lever.
    if fitted:
        head = arm.data.edit_bones['Bip001 Head']
        up = (arm.matrix_world.inverted().to_3x3() @ Vector((0, 0, 1))).normalized()
        eyes = [arm.data.edit_bones[f'+EyeBone {s} A01'] for s in ('L', 'R')]
        assert abs((eyes[0].head - eyes[1].head).dot(up)) < .001
        assert all((eye.tail - eye.head).length < .05 for eye in eyes)
        for side, eye in zip(('L', 'R'), eyes):
            group_name = f'+EyeBone {side} A02'
            points = []
            for obj in bpy.context.scene.objects:
                if obj.type != 'MESH' or obj.find_armature() != arm or 'star' in obj.name.casefold():
                    continue
                group = obj.vertex_groups.get(group_name)
                if group:
                    transform = arm.matrix_world.inverted() @ obj.matrix_world
                    points.extend(transform @ v.co for v in obj.data.vertices
                                  if any(g.group == group.index and g.weight > .5 for g in v.groups))
            center = sum(points, Vector()) / len(points)
            height = max(p.dot(up) for p in points) - min(p.dot(up) for p in points)
            assert abs((eye.head - center).dot(up)) < height * .25
    bpy.ops.object.mode_set(mode='OBJECT')
    align_eye_bones(arm)
    assert all((arm.data.bones[n].head_local - h).length < 1e-6 for n, (h, _) in before.items())
    print('EYE_SCOPE_PASS', filename, 'calibrated' if fitted else 'authored pivots retained', flush=True)
