"""Smoke-test bundled dependencies and ExpyKit conversion on Blender 4 and 5."""
from pathlib import Path
import sys
import addon_utils
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.genshin_setup_wizard import on_register
from setup_wizard.character_rig_setup.rig_ui_utils import (
    rig_conversion_available, safe_expykit_convert_bone_names,
    safe_expykit_extract_metarig,
)

on_register()
assert rig_conversion_available()
expected = 'expy'
from setup_wizard.utils.optional_addons import find_addon, temporary_addon
module = find_addon(expected)
optional_keys = [expected, 'ueformat']
if bpy.app.version >= (5, 0, 0):
    optional_keys.append('retarget')
for key in optional_keys:
    dependency = find_addon(key)
    assert dependency
    assert not addon_utils.check(dependency)[1]
    assert dependency not in bpy.context.preferences.addons
addon_utils.disable(module, default_set=True)
assert not addon_utils.check(module)[1]
# Registration also leaves optional dependencies disabled.
on_register()
assert not addon_utils.check(module)[1]
assert rig_conversion_available()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.object.armature_basic_human_metarig_add()
source = bpy.context.object
bpy.ops.object.mode_set(mode='POSE')
assert safe_expykit_convert_bone_names() == {'FINISHED'}
assert not addon_utils.check(module)[1]
assert 'DEF-spine' in source.data.bones
assert safe_expykit_extract_metarig(assign_metarig=True) == {'FINISHED'}
assert not addon_utils.check(module)[1]
if bpy.app.version >= (5, 0, 0):
    assert not addon_utils.check(find_addon('retarget'))[1]
metarig = bpy.context.object
assert metarig != source
assert metarig.data.rigify_target_rig == source
bpy.ops.pose.rigify_generate()
assert source.data.get('rig_id')
assert 'hand_ik.L' in source.pose.bones and 'foot_ik.R' in source.pose.bones
# Nested scopes and failures must restore registration without losing user choices.
try:
    with temporary_addon(expected):
        with temporary_addon(expected):
            assert addon_utils.check(module)[1]
        assert addon_utils.check(module)[1]
        raise ValueError('cleanup check')
except ValueError:
    pass
assert not addon_utils.check(module)[1]
addon_utils.enable(module, default_set=True)
with temporary_addon(expected):
    assert addon_utils.check(module)[1]
assert addon_utils.check(module)[1] and module in bpy.context.preferences.addons
print('RIG_CONVERSION_PASS', bpy.app.version_string, expected)
