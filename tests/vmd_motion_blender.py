"""Run in Blender with MMD Tools installed; exercises the real VMD on an FBX."""
import math
import os
from pathlib import Path
import sys
import zipfile

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.environ.get('GACHA_TEST_MMD_DIR'):
    mmd = Path(os.environ['GACHA_TEST_MMD_DIR'])
    sys.path.insert(0, str(mmd.parent))
    wheels = ROOT/'tests/.runtime/wheels'
    for wheel in (mmd/'wheels').glob('*.whl'):
        zipfile.ZipFile(wheel).extractall(wheels)
    sys.path.insert(0, str(wheels))
    addon_utils.enable('mmd_tools', default_set=True)
os.environ['GACHA_SETUP_ISOLATED_WORKER'] = '1'
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.utilites.vmd_motion import apply_vmd
from setup_wizard.utils.optional_addons import find_addon


def motion_fixture():
    """Use the user's motion when present, otherwise write a small reproducible VMD."""
    for path in (ROOT/'chars/vmdmotion/Motion & Facials.vmd', ROOT/'Motion & Facials.vmd'):
        if path.is_file():
            print('VMD_MOTION_FIXTURE', path)
            return path
    import struct
    path = ROOT/'tests/.runtime/facial-regression.vmd'
    path.parent.mkdir(parents=True, exist_ok=True)
    names = ['全ての親', 'センター', '下半身', '上半身', '上半身2', '首', '頭']
    names += [side+name for side in ('左', '右')
              for name in ('肩', '腕', 'ひじ', '手首', '足', 'ひざ', '足首', 'つま先')]
    with path.open('wb') as out:
        out.write(struct.pack('<30s20sI', b'Vocaloid Motion Data 0002', b'Regression', len(names)*2))
        for name in names:
            for number in (0, 10):
                angle = .1 if number else 0
                out.write(struct.pack('<15sI3f4f64B', name.encode('cp932'), number,
                                      0, .1 if number else 0, 0,
                                      math.sin(angle), 0, 0, math.cos(angle),
                                      *([20, 20, 0, 0, 107, 107, 0, 0]*8)))
        out.write(struct.pack('<I', 4))
        for name in ('あ', 'まばたき'):
            for number, weight in ((0, 0), (10, 1)):
                out.write(struct.pack('<15sIf', name.encode('cp932'), number, weight))
        out.write(struct.pack('<4I', 0, 0, 0, 0))
    print('VMD_SYNTHETIC_FIXTURE', path)
    return path


MOTION = motion_fixture()


def fcurves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


mmd_module = find_addon('mmd_tools')
addon_utils.disable(mmd_module, default_set=True)
assert not addon_utils.check(mmd_module)[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
fbx = ROOT/'chars/genshin/columbina-moonweave-gossamer/Avatar_Girl_Catalyst_Columbina.fbx'
bpy.ops.import_scene.fbx(filepath=str(fbx))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
print('FBX_BONES', list(rig.pose.bones.keys())[:40])
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
old = bpy.data.actions.new('Existing animation to preserve')
rig.animation_data_create().action = old
assert bpy.ops.setup_wizard.apply_vmd(filepath=str(MOTION)) == {'FINISHED'}
assert not addon_utils.check(mmd_module)[1]
assert mmd_module not in bpy.context.preferences.addons
action = rig.animation_data.action
assert action and action != old and old.use_fake_user
assert bpy.context.scene.frame_end > 1
assert len(fcurves(action)) > 20
paths = {f.data_path for f in fcurves(action)}
assert any('UpperArm' in p for p in paths), paths
snapshots = []
for frame in (1, bpy.context.scene.frame_end//2, bpy.context.scene.frame_end):
    bpy.context.scene.frame_set(frame)
    snapshots.append(tuple(v for pb in rig.pose.bones for row in pb.matrix for v in row))
    assert all(math.isfinite(v) for v in snapshots[-1])
assert snapshots[0] != snapshots[1], 'The imported action must move the rig'
print('VMD_FBX_PASS', len(fcurves(action)), bpy.context.scene.frame_end)
assert any(o.data.shape_keys and o.data.shape_keys.animation_data
           and o.data.shape_keys.animation_data.action
           for o in bpy.context.scene.objects if o.type == 'MESH' and o.find_armature() == rig)

# A real FBX face driven by a custom rig property must retain its driver while
# the generated facial control keys coexist with imported body motion.
face = next(o for o in bpy.context.scene.objects
            if o.type == 'MESH' and o.find_armature() == rig and o.data.shape_keys
            and 'Mouth_A01' in o.data.shape_keys.key_blocks)
rig['regression_face_weight'] = 0.0
driver = face.data.shape_keys.key_blocks['Mouth_A01'].driver_add('value').driver
driver.type = 'SCRIPTED'
variable = driver.variables.new()
variable.name = 'weight'
variable.type = 'SINGLE_PROP'
variable.targets[0].id = rig
variable.targets[0].data_path = '["regression_face_weight"]'
driver.expression = 'weight'
counts = apply_vmd(bpy.context, rig, str(MOTION))
assert counts[1] >= 1
assert any('regression_face_weight' in f.data_path for f in fcurves(rig.animation_data.action))
assert any('UpperArm' in f.data_path for f in fcurves(rig.animation_data.action))
assert face.data.shape_keys.animation_data.drivers

# A facial-only file does not require a compatible skeleton or change Rigify
# FK/IK settings. Existing body animation remains in the copied rig action.
import struct
face_only = ROOT/'tests/.runtime/face-only-regression.vmd'
with face_only.open('wb') as out:
    out.write(struct.pack('<30s20sII', b'Vocaloid Motion Data 0002', b'Face Only', 0, 2))
    for number, weight in ((0, 0), (4, .8)):
        out.write(struct.pack('<15sIf', 'あ'.encode('cp932'), number, weight))
    out.write(struct.pack('<4I', 0, 0, 0, 0))
body_action = rig.animation_data.action
scene_range = bpy.context.scene.frame_start, bpy.context.scene.frame_end
counts = apply_vmd(bpy.context, rig, str(face_only), start=20)
assert counts == (0, 1, 0), counts
assert rig.animation_data.action != body_action and body_action.use_fake_user
assert any('UpperArm' in f.data_path for f in fcurves(rig.animation_data.action))
assert bpy.context.scene.frame_start == min(scene_range[0], 20)
assert bpy.context.scene.frame_end == max(scene_range[1], 24)
bpy.context.scene.frame_set(24)
assert abs(rig['regression_face_weight']-.8) < 1e-4
assert abs(face.data.shape_keys.key_blocks['Mouth_A01'].value-.8) < 1e-4
assert not addon_utils.check(mmd_module)[1]
print('VMD_DRIVEN_AND_FACE_ONLY_PASS', counts)

# Explicit facial mode must also exclude body tracks from a combined VMD.
body_before = {(f.data_path, f.array_index): [tuple(p.co) for p in f.keyframe_points]
               for f in fcurves(rig.animation_data.action) if 'regression_face_weight' not in f.data_path}
bpy.context.scene.render.fps = 24
counts = apply_vmd(bpy.context, rig, str(MOTION), facial=False, face_only=True)
body_after = {(f.data_path, f.array_index): [tuple(p.co) for p in f.keyframe_points]
              for f in fcurves(rig.animation_data.action) if 'regression_face_weight' not in f.data_path}
assert counts[0] == 0 and counts[1] > 0 and counts[2] == 0, counts
assert body_after == body_before
assert bpy.context.scene.render.fps == 24
print('VMD_EXPLICIT_FACE_ONLY_PASS', counts)

# Reject incompatible skeletons before changing their current animation.
bpy.ops.object.armature_add()
unsupported = bpy.context.object
previous = bpy.data.actions.new('Unsupported rig animation')
unsupported.animation_data_create().action = previous
try:
    apply_vmd(bpy.context, unsupported, str(MOTION))
    raise AssertionError('An incompatible rig must be rejected')
except RuntimeError as exc:
    assert 'No compatible' in str(exc), exc
assert unsupported.animation_data.action == previous
assert not addon_utils.check(mmd_module)[1]

# Also exercise the exact same importer against generated Rigify controls.
addon_utils.enable('rigify', default_set=True)
bpy.ops.object.armature_basic_human_metarig_add()
bpy.ops.pose.rigify_generate()
rig = bpy.context.object
counts = apply_vmd(bpy.context, rig, str(MOTION))
assert counts[0] > 15, counts
assert rig.animation_data.action
assert rig.pose.bones['upper_arm_parent.L']['IK_FK'] == 1
assert any('upper_arm_fk.L' in f.data_path for f in fcurves(rig.animation_data.action))
print('VMD_RIGIFY_PASS', counts)
assert not addon_utils.check(mmd_module)[1]
# Pre-5.0 access must fail both through poll and the Python entry point.
from unittest.mock import patch
from types import SimpleNamespace
from setup_wizard.utilites.vmd_motion import CSW_OT_ApplyVMD
with patch('setup_wizard.utilites.vmd_motion.bpy', SimpleNamespace(app=SimpleNamespace(version=(4, 5, 0)))):
    assert not CSW_OT_ApplyVMD.poll(bpy.context)
    try:
        apply_vmd(bpy.context, rig, str(MOTION))
        raise AssertionError('Blender 4 must be rejected')
    except RuntimeError as exc:
        assert '5.0' in str(exc)
