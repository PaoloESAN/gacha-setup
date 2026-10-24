"""Smoke-test bundled dependencies and the version-specific conversion API."""
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
expected = 'retarget' if bpy.app.version >= (5, 0, 0) else 'expy'
assert any(expected in key.lower() for key in bpy.context.preferences.addons.keys())
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.object.armature_basic_human_metarig_add()
source = bpy.context.object
bpy.ops.object.mode_set(mode='POSE')
assert safe_expykit_convert_bone_names() == {'FINISHED'}
assert 'DEF-spine' in source.data.bones
assert safe_expykit_extract_metarig(assign_metarig=True) == {'FINISHED'}
metarig = bpy.context.object
assert metarig != source
assert metarig.data.rigify_target_rig == source
bpy.ops.pose.rigify_generate()
assert source.data.get('rig_id')
assert 'hand_ik.L' in source.pose.bones and 'foot_ik.R' in source.pose.bones
print('RIG_CONVERSION_PASS', bpy.app.version_string, expected)
