"""Required conversion failures must stop Genshin rigging at their source."""
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.genshin_setup_wizard import on_register
from setup_wizard.genshin_import_character_model import _execute_fbx_import, reorient_armature_bones
from setup_wizard.character_rig_setup import rig_script

on_register()
model = ROOT / 'chars/genshin/Amber/Default/Avatar_Girl_Bow_Ambor.fbx'
runtime = ROOT / 'tests/.runtime/genshin-metarig'
runtime.mkdir(parents=True, exist_ok=True)

def import_model():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    _execute_fbx_import(str(model))
    source = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    reorient_armature_bones(source)
    bpy.ops.object.select_all(action='DESELECT')
    source.select_set(True)
    bpy.context.view_layer.objects.active = source

for operation, outcome, expected in (
    ('convert_bone_names', RuntimeError('retarget operator missing'), 'retarget operator missing'),
    ('convert_bone_names', {'CANCELLED'}, 'Bone name conversion did not finish'),
    ('extract_metarig', RuntimeError('metarig operator missing'), 'metarig operator missing'),
    ('extract_metarig', {'CANCELLED'}, 'Metarig extraction did not finish'),
    ('extract_metarig', {'FINISHED'}, 'Metarig extraction did not create'),
):
    import_model()
    kwargs = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
    with patch.object(rig_script, 'safe_expykit_' + operation, **kwargs):
        try:
            rig_script.rig_character('', 0, True, True, True, True, False, False)
        except RuntimeError as error:
            assert expected in str(error), str(error)
        else:
            raise AssertionError(f'{operation}: rigging continued after failure')
    assert not any(o.type == 'ARMATURE' and o.data.get('rig_id') for o in bpy.data.objects)
    print('EXPECTED_CONVERSION_FAILURE', operation, expected, flush=True)

# Run the real isolated pipeline with ExpyKit initially disabled, matching
# the worker in the supplied log. The worker clears all previous test objects.
job = {
    'game_type': 'GENSHIN_IMPACT', 'disable_rigging': False,
    'character_directory': str(model.parent), 'selected_model_file': str(model),
    'gacha_module': 'setup_wizard', 'gacha_addon_parent': str(ROOT),
    'status_path': str(runtime / 'status.json'),
    'result_path': str(runtime / 'Amber.blend'),
}
job_path = runtime / 'job.json'
job_path.write_text(json.dumps(job), encoding='utf-8')
sys.argv = [sys.argv[0], '--', str(job_path)]
try:
    runpy.run_path(str(ROOT / 'setup_wizard/services/isolation/isolated_runner.py'), run_name='__main__')
except SystemExit as error:
    if error.code not in (None, 0):
        raise
status = json.loads((runtime / 'status.json').read_text(encoding='utf-8'))
assert status['state'] == 'SUCCESS', status
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
for side in ('L', 'R'):
    assert f'hand_ik.{side}' in rig.pose.bones
    assert f'foot_ik.{side}' in rig.pose.bones
print('GENSHIN_METARIG_REGRESSION_PASS', bpy.app.version_string, flush=True)
