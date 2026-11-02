"""Real FBX fallback regression. Run with Blender --background --factory-startup
--python-exit-code 1 --python tests/fbx_python_fallback_blender.py.
"""
from pathlib import Path
import sys
from unittest.mock import patch

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / 'tests/.runtime/fbx-python-fallback'
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'SCRIPTS', 'CONFIG'}:
        target = OUTPUT / kind / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard import genshin_import_character_model as importer

assert bpy.app.version >= (4, 5, 0)
sentinel = bpy.data.objects.get('Cube')
assert sentinel
enabled_before = set(bpy.context.preferences.addons.keys())
loaded_before = addon_utils.check('io_scene_fbx')[1]

models = sorted((ROOT / 'chars/ake/Zhuang Fangyi').glob('*.fbx'))
assert len(models) == 2, 'Both Zhuang Fangyi FBX fixtures are required'
for model in models:
    before = set(bpy.data.objects)
    assert importer._execute_fbx_import(str(model)) == {'FINISHED'}
    imported = set(bpy.data.objects) - before
    assert any(o.type == 'MESH' and len(o.data.vertices) for o in imported), model
    assert any(o.type == 'ARMATURE' and len(o.data.bones) for o in imported), model
    assert sentinel in bpy.context.scene.objects[:]
    assert set(bpy.context.preferences.addons.keys()) == enabled_before
    assert addon_utils.check('io_scene_fbx')[1] == loaded_before
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    print('FBX_PYTHON_FALLBACK_PASS', model.name, flush=True)

# A supported FBX must still use the native importer.
model = next((ROOT / 'chars/ake/Perlica').glob('*.fbx'))
with patch.object(importer, 'temporary_addon', side_effect=AssertionError('Unexpected fallback')):
    assert importer._execute_fbx_import(str(model)) == {'FINISHED'}

# Both importers failing must preserve the existing scene and dependency state.
before = set(bpy.data.objects)
try:
    importer._execute_fbx_import(str(OUTPUT / 'missing.fbx'))
except RuntimeError as error:
    assert 'Python FBX fallback failed' in str(error), error
else:
    raise AssertionError('Missing FBX was accepted')
assert set(bpy.data.objects) == before
assert set(bpy.context.preferences.addons.keys()) == enabled_before
assert addon_utils.check('io_scene_fbx')[1] == loaded_before
print('FBX_PYTHON_FALLBACK_REGRESSION_PASS', flush=True)
