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
assert bpy.ops.setup_wizard.apply_vmd(filepath=str(ROOT/'Motion & Facials.vmd')) == {'FINISHED'}
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

# Reject incompatible skeletons before changing their current animation.
bpy.ops.object.armature_add()
unsupported = bpy.context.object
previous = bpy.data.actions.new('Unsupported rig animation')
unsupported.animation_data_create().action = previous
try:
    apply_vmd(bpy.context, unsupported, str(ROOT/'Motion & Facials.vmd'))
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
counts = apply_vmd(bpy.context, rig, str(ROOT/'Motion & Facials.vmd'))
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
        apply_vmd(bpy.context, rig, str(ROOT/'Motion & Facials.vmd'))
        raise AssertionError('Blender 4 must be rejected')
    except RuntimeError as exc:
        assert '5.0' in str(exc)
