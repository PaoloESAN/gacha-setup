"""Exercise the complete FBX-equivalent Genshin pipeline on PMX models.

blender --background --factory-startup --python-exit-code 1 --python
tests/mmd_setup_blender.py -- chars/COLUMBINA [output_directory]
"""
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import zipfile

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.environ.get('GACHA_TEST_MMD_DIR'):
    mmd = Path(os.environ['GACHA_TEST_MMD_DIR'])
    sys.path.insert(0, str(mmd.parent))
    wheels = ROOT / 'tests/.runtime/wheels'
    for wheel in (mmd / 'wheels').glob('*.whl'):
        zipfile.ZipFile(wheel).extractall(wheels)
    sys.path.insert(0, str(wheels))
    addon_utils.enable('mmd_tools', default_set=True)
os.environ['GACHA_SETUP_ISOLATED_WORKER'] = '1'
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.genshin_setup_wizard import on_register
from setup_wizard import import_order
from setup_wizard.character_rig_setup.mmd_rig import find_pmx
from setup_wizard.character_rig_setup.rig_ui_utils import get_view3d_override, rig_conversion_available
from setup_wizard.services.isolation.workflow import checked_workflow
from setup_wizard.texture_import_setup.texture_importer_types import find_all_image_nodes_by_category
from tests.rig.rig_assertions import assert_rig

on_register()
assert rig_conversion_available(), 'Automatic dependency installation failed'
from setup_wizard.utils.optional_addons import find_addon
optional_modules = [find_addon(key) for key in ('mmd_tools', 'retarget', 'ueformat')]
for module in optional_modules:
    if module:
        addon_utils.disable(module, default_set=True)
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
selected = Path(args[0]).resolve() if args else ROOT / 'chars/COLUMBINA'
folder = selected.parent if selected.is_file() else selected
output = Path(args[1]).resolve() if len(args) > 1 else ROOT / 'tests/.runtime/pmx-full-results'
output.mkdir(parents=True, exist_ok=True)
steps = json.loads((ROOT/'setup_wizard/config_ui.json').read_text())['ui_order']['GENSHIN_OT_setup_wizard_ui']


def update():
    for obj in bpy.context.scene.objects:
        obj.update_tag()
    bpy.context.view_layer.update()


def points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


assert find_pmx(str(folder)), 'Folder selection did not resolve a PMX'
models = [selected] if selected.is_file() else sorted(folder.glob('*.pmx'), key=lambda p: len(p.name))
if len(models) > 1:
    # The production isolated setup also starts a fresh Blender process.
    # Appended rig asset collections must not leak from one fixture to another.
    combined = []
    for model in models:
        destination = output / model.stem
        subprocess.run([bpy.app.binary_path, '--background', '--factory-startup',
                        '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
                        '--', str(model), str(destination)], check=True)
        combined.extend(json.loads((destination/'results.json').read_text(encoding='utf-8')))
    (output/'results.json').write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding='utf-8')
    print('MMD_FULL_SETUP_PASS', json.dumps(combined, ensure_ascii=False))
    raise SystemExit(0)
results = []
for model in models:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.materials, bpy.data.node_groups, bpy.data.meshes, bpy.data.armatures):
        for item in list(datablocks):
            datablocks.remove(item, do_unlink=True)
    completed = set()
    factory = import_order.ComponentFunctionFactory
    descriptor = factory.__dict__['create_component_function']
    original = factory.create_component_function

    def observe(component):
        operation = original(component)

        def execute(*args, **kwargs):
            result = operation(*args, **kwargs)
            assert result == {'FINISHED'}, (component, result)
            completed.add(component)
            return result
        return execute

    factory.create_component_function = staticmethod(observe)
    try:
        with bpy.context.temp_override(**get_view3d_override()):
            with checked_workflow(import_order, steps):
                result = bpy.ops.genshin.import_model(
                    'EXEC_DEFAULT', filepath=str(model), file_directory=str(folder),
                    next_step_idx=1, invoker_type='invoke_next_step_ui',
                    high_level_step_name='genshin.setup_wizard_ui', game_type='GENSHIN_IMPACT')
        assert result == {'FINISHED'}
        assert set(steps[2:]) <= completed, f'Skipped stages: {set(steps[2:])-completed}'
        assert all(not addon_utils.check(module)[1] for module in optional_modules if module)
    finally:
        factory.create_component_function = descriptor
    rig = next(obj for obj in bpy.context.scene.objects
               if obj.type == 'ARMATURE' and obj.data.get('rig_id'))
    assert rig.get('setup_wizard_pmx_normalized')
    for name in ('root', 'root.001', 'root.002', 'plate-settings', 'Mouth-Control',
                 'Eye-Ha-Control', 'eyetrack', 'Lighting Panel', 'hand_ik.L', 'foot_ik.R'):
        assert name in rig.pose.bones, f'Missing FBX rig control: {name}'
    meshes = [obj for obj in bpy.context.scene.objects
              if obj.type == 'MESH' and obj.find_armature() == rig]
    assert {'Body', 'Face', 'Hair', 'Pupil'} <= {obj.name for obj in meshes}
    records = json.loads(bpy.context.scene['setup_wizard_pmx_materials'])
    verified_parts = set()
    for obj in meshes:
        assert {'UV0', 'UV1'} <= set(obj.data.uv_layers.keys()), obj.name
        for slot in obj.material_slots:
            mat = slot.material
            assert mat and mat.name.startswith('HoYoverse - '), f'MMD material remains on {obj.name}'
            part = mat.get('setup_wizard_pmx_part')
            if part in records and 'Outlines' not in mat.name:
                nodes = find_all_image_nodes_by_category(mat.node_tree, 'diffuse')
                assert nodes and all(n.image and n.image.name == records[part]['image'] for n in nodes), (obj.name, part)
                assert all(n.image.size[0] > 0 for n in nodes), 'Missing PMX image data'
                verified_parts.add(part)
        if obj.name != 'EyeStar':
            assert any(m.type == 'NODES' and 'Light Vectors' in m.name for m in obj.modifiers), obj.name
            additive = any(records.get(s.material.get('setup_wizard_pmx_part'), {}).get('additive')
                           for s in obj.material_slots if s.material)
            if obj.name != 'Pupil' and not additive:
                assert any(m.type == 'NODES' and 'Outlines' in m.name for m in obj.modifiers), obj.name
        assert all(math.isfinite(c) for p in points(obj) for c in p), 'Non-finite deformation'
    assert set(records) - {'Brow'} <= verified_parts, f'Missing shader parts: {set(records)-verified_parts}'
    head = rig.matrix_world @ rig.pose.bones['head'].head
    hip = rig.matrix_world @ rig.pose.bones['DEF-spine'].head
    assert head.z > hip.z + 0.2, 'PMX lost Z-up orientation'
    face = bpy.data.objects['Face']
    keys = face.data.shape_keys.key_blocks
    for key, control in (('Mouth_A01', 'Mouth-Control'), ('Eye_Ha', 'Eye-Ha-Control')):
        assert key in keys, f'Expression missing: {key}'
        pb = rig.pose.bones[control]
        old = pb.location.y
        pb.location.y = -0.2
        update()
        assert keys[key].value > 0.2, f'Face control does not drive expression: {key}'
        pb.location.y = old
        update()
    pose = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
    checks = assert_rig('genshin', str(folder))
    assert all(check['passed'] for check in checks), [c for c in checks if not c['passed']]
    for pb in rig.pose.bones:
        pb.matrix_basis = pose[pb.name]
    update()
    blend = output/(model.stem + '-FullSetup.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    results.append(dict(model=str(model), status='PASS', completed=sorted(completed),
                        shader_parts=sorted(verified_parts), rig_checks=checks, blend=str(blend)))
(output/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('MMD_FULL_SETUP_PASS', json.dumps(results, ensure_ascii=False))
