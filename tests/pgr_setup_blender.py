"""PGR regressions on real assets, including all Bianca/Animator outfits.

blender --background --factory-startup --python-exit-code 1 --python tests/pgr_setup_blender.py
Optional: -- path/to/model.fbx [--save-blend]
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import addon_utils
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / 'tests/.runtime/pgr'
OUTPUT.mkdir(parents=True, exist_ok=True)
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not args:
    models = sorted((ROOT / 'chars/pgr').rglob('*.fbx'))
    assert len(models) >= 17, 'PGR character fixtures missing'
    for model in models:
        extra = [] if model.stem.startswith(('R5Bianka', 'R3Nietiya', 'R3Laiya', 'R3Kurumi')) else ['--materials-only']
        with (OUTPUT / (model.stem + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run([bpy.app.binary_path, '--background', '--factory-startup',
                            '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
                            '--', str(model), *extra], stdout=log, stderr=subprocess.STDOUT, check=True)
        print('PGR PASS', model.stem, flush=True)
    print('PGR_SUITE_PASS', len(models))
    raise SystemExit(0)

model = Path(args[0]).resolve()
materials_only = '--materials-only' in args
os.environ['GACHA_SETUP_ISOLATED_WORKER'] = '1'
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'SCRIPTS', 'CONFIG'}:
        target = OUTPUT / 'resources' / kind / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
dependencies = OUTPUT / 'dependencies'
with zipfile.ZipFile(ROOT / 'setup_wizard/dependencies/retarget.zip') as archive:
    archive.extractall(dependencies)
sys.path.insert(0, str(dependencies))
sys.path.insert(0, str(OUTPUT / 'resources/SCRIPTS/addons'))
import retarget  # Make the isolated dependency discoverable to optional_addons.
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard.genshin_setup_wizard import on_register
from setup_wizard.character_rig_setup.rig_ui_utils import get_view3d_override
from setup_wizard.services.isolation.workflow import checked_workflow
from setup_wizard import import_order
from tests.rig.rig_assertions import assert_rig
on_register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

steps = json.loads((ROOT / 'setup_wizard/config_ui.json').read_text())['ui_order']['PUNISHING_GRAY_RAVEN_OT_setup_wizard_ui']
if materials_only:
    steps = steps[:6]
completed = set()
baseline = {}
factory = import_order.ComponentFunctionFactory
descriptor = factory.__dict__['create_component_function']
original = factory.create_component_function


def observe(component):
    operation = original(component)

    def run(*a, **kw):
        completed.add(component)
        if component == 'rig_character' or (materials_only and component not in steps):
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH':
                    baseline[obj.name] = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if materials_only and component not in steps:
            return {'FINISHED'}
        return operation(*a, **kw)
    return run


factory.create_component_function = staticmethod(observe)
try:
    with bpy.context.temp_override(**get_view3d_override()):
        with checked_workflow(import_order, steps):
            result = bpy.ops.genshin.import_model('EXEC_DEFAULT', filepath=str(model), file_directory=str(model.parent),
                next_step_idx=1, invoker_type='invoke_next_step_ui',
                high_level_step_name='punishing_gray_raven.setup_wizard_ui', game_type='PUNISHING_GRAY_RAVEN')
    assert result == {'FINISHED'} and set(steps[2:]) <= completed
finally:
    factory.create_component_function = descriptor

rig = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id')), None)
assert materials_only or rig, 'Generated rig missing'
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
def show_collections(layer):
    layer.exclude = False
    layer.hide_viewport = False
    layer.collection.hide_viewport = False
    for child in layer.children:
        show_collections(child)
show_collections(bpy.context.view_layer.layer_collection)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and (materials_only or o.find_armature() == rig)]
assert meshes
assert materials_only or all(n in rig.pose.bones for n in ('hand_ik.L', 'hand_ik.R', 'Eye-Track-Master', 'head'))
repaired = [o.name for o in meshes if o.get('setup_wizard_pgr_bind_pose')]
bound_faces = [o.name for o in meshes if o.get('setup_wizard_pgr_rigid_face')]
bound_bands = [o.name for o in meshes if o.get('setup_wizard_pgr_rigid_bands')]
if model.stem.startswith('R5Bianka'):
    assert len(bound_faces) >= 4, ('Bianca static face parts remain unbound', bound_faces)
    assert bound_bands, 'Bianca bracelets remain unbound'
if model.stem.startswith('R3Nietiya'):
    assert len(repaired) >= 3, 'Nirvatia skins were not rebased'
    body = next(o for o in meshes if o.name.endswith('Body'))
    # The broken model's unrebased feet were below zero and its hands below
    # the wrists. The body must now span the same space as the skeleton.
    assert min(v.co.z for v in body.data.vertices) > -.1
    for side in ('L', 'R'):
        hand = rig.data.bones['DEF-hand.' + side]
        group = body.vertex_groups.get(hand.name)
        points = [v.co for v in body.data.vertices if any(g.group == group.index and g.weight > .5 for g in v.groups)]
        assert points and (sum(points, Vector()) / len(points) - hand.head_local).length < .08

materials = {s.material for o in bpy.context.scene.objects if o.type == 'MESH' and o.name in baseline
             for s in o.material_slots if s.material}
definitions = {p.stem: json.loads(p.read_text(encoding='utf-8-sig')) for p in model.parent.rglob('*.json')}
verified = []
for mat in materials:
    source = mat.get('pgr_source_material')
    env = definitions.get(source, {}).get('m_SavedProperties', {}).get('m_TexEnvs', {})
    expected = env.get('_MainTex', {}).get('m_Texture', {}).get('Name')
    if not expected or not any(p.stem == expected for p in model.parent.glob('*') if p.is_file()):
        continue
    nodes = mat.node_tree.nodes
    diffuse = nodes.get('Face_Diffuse') or nodes.get('Body_Diffuse_UV0') or nodes.get('Image Texture')
    assert diffuse and diffuse.image and Path(diffuse.image.filepath).stem == expected, (mat.name, expected)
    assert diffuse.image.colorspace_settings.name == 'sRGB', mat.name
    assert diffuse.image.size[0] > 0
    verified.append((mat.name, expected))
assert verified, 'No material color atlases verified'
if materials_only:
    summary = {'model': str(model), 'materials': verified}
    (OUTPUT / (model.stem + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('PGR_MATERIALS_PASS', summary)
    raise SystemExit(0)
assert any(name.endswith(' Eye') for name, _ in verified), 'Eye atlas not verified'

head = rig.pose.bones['head']
head.rotation_mode = 'XYZ'
original_rotation = head.rotation_euler.copy()

# Neutral generated rig must preserve mesh geometry, including extra finger
# segments. Disable outlines only while comparing vertex counts/positions.
for obj in meshes:
    obj.hide_set(False)
    obj.hide_viewport = False
    drivers = [(curve, curve.mute) for curve in obj.animation_data.drivers] if obj.animation_data else []
    for curve, _ in drivers:
        if curve.data_path.endswith('show_viewport'):
            curve.mute = True
    mods = [(m, m.show_viewport) for m in obj.modifiers]
    for modifier, _ in mods:
        modifier.show_viewport = modifier.type == 'ARMATURE'
    bpy.context.view_layer.update()
    obj.update_tag()
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    points = baseline[obj.name]
    assert len(evaluated.vertices) == len(points), (obj.name, len(evaluated.vertices), len(points), len(obj.data.vertices), obj.visible_get(), [(m.name, m.type, m.show_viewport) for m in obj.modifiers])
    delta = max(((obj.matrix_world @ v.co - points[v.index]).length for v in evaluated.vertices), default=0)
    assert delta < 1e-4, (obj.name, 'neutral rig changed geometry', delta)
    if obj.get('setup_wizard_pgr_rigid_face'):
        head_rest = (rig.matrix_world @ rig.pose.bones['DEF-spine.006'].matrix).copy()
        head.rotation_euler.y += .6
        rig.update_tag()
        bpy.context.view_layer.update()
        head_pose = rig.matrix_world @ rig.pose.bones['DEF-spine.006'].matrix
        transform = head_pose @ head_rest.inverted()
        moved = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        delta = max(((obj.matrix_world @ v.co - transform @ points[v.index]).length for v in moved.vertices), default=0)
        assert delta < 1e-4, (obj.name, 'face detached during head turn', delta)
        assert max(((transform @ p - p).length for p in points), default=0) > .005, 'Head turn had no effect'
        head.rotation_euler = original_rotation
        rig.update_tag()
        bpy.context.view_layer.update()
    if obj.get('setup_wizard_pgr_rigid_bands'):
        assignments = []
        for vertex in obj.data.vertices:
            assert len(vertex.groups) == 1 and abs(vertex.groups[0].weight - 1) < 1e-6
            name = obj.vertex_groups[vertex.groups[0].group].name
            assert name in {'DEF-hand.L', 'DEF-hand.R'}, name
            assignments.append(name)
        assert set(assignments) == {'DEF-hand.L', 'DEF-hand.R'}
        for side in ('L', 'R'):
            parent = rig.pose.bones['upper_arm_parent.' + side]
            old_switch = parent['IK_FK']
            for mode in ('FK', 'IK'):
                parent['IK_FK'] = 1.0 if mode == 'FK' else 0.0
                rig.update_tag()
                bpy.context.view_layer.update()
                control = rig.pose.bones[('hand_fk.' if mode == 'FK' else 'hand_ik.') + side]
                basis = control.matrix_basis.copy()
                rest_bones = {n: (rig.matrix_world @ rig.pose.bones[n].matrix).copy() for n in set(assignments)}
                initial = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
                rest_points = [obj.matrix_world @ v.co for v in initial.vertices]
                if mode == 'FK':
                    control.matrix_basis = basis @ Matrix.Rotation(.5, 4, 'Z')
                else:
                    matrix = control.matrix.copy()
                    matrix.translation += Vector((0, -.08, .03))
                    control.matrix = matrix
                rig.update_tag()
                bpy.context.view_layer.update()
                transforms = {n: rig.matrix_world @ rig.pose.bones[n].matrix @ rest_bones[n].inverted() for n in rest_bones}
                moved = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
                error = max(((obj.matrix_world @ v.co - transforms[assignments[v.index]] @ rest_points[v.index]).length
                             for v in moved.vertices), default=0)
                assert error < 1e-4, (obj.name, side, mode, 'bracelet deformation', error)
                for name in rest_bones:
                    movement = max(((transforms[name] @ p - p).length for p, group in zip(rest_points, assignments) if group == name), default=0)
                    assert movement > .005 if name.endswith(side) else movement < 1e-4, (side, mode, name, movement)
                control.matrix_basis = basis
                rig.update_tag()
                bpy.context.view_layer.update()
            parent['IK_FK'] = old_switch
            rig.update_tag()
            bpy.context.view_layer.update()
    for modifier, visible in mods:
        modifier.show_viewport = visible
    for curve, muted in drivers:
        curve.mute = muted

facial_checks = 0
if model.stem.startswith('R5Bianka'):
    face = next(o for o in meshes if o.name.endswith('Face'))
    overlay = next(o for o in meshes if o.name.endswith('FaceEX'))
    cases = [
        ('m.A', 0, .02, 'mouth01'), ('m.AA', 0, .02, 'mouth05'),
        ('m.E', 0, .02, 'mouth03'), ('m.I', 0, .02, 'mouth07'),
        ('m.O', 0, .02, 'mouth02'), ('m.U', 0, .02, 'mouth04'),
        ('x1', 0, .02, 'mouth07'), ('x2', 0, .02, 'mouth08'),
        ('x3', 0, .02, 'mouth06'), ('x4', 0, .02, 'mouth21'),
        ('x5', 0, .02, 'mouth22'), ('x6', 0, .02, 'mouth04'),
        ('doubt.1', 0, .02, 'eyebrow03'), ('doubt.2', 0, .02, 'eyebrow04'),
        ('b.happy', 0, .02, 'eyebrow05'), ('b.flat', 0, .02, 'eyebrow09'),
        ('b.close', 0, .02, 'eyebrow01'), ('e.ji', 0, .02, 'eye08'),
        ('e.lowlid', 0, .02, 'eye09'), ('e.focus', 0, .02, 'eye10'),
        ('e.wide', 0, .02, 'eye04'), ('e.wink.up.l', 0, .02, 'eye02'),
        ('e.wink.up.r', 0, .02, 'eye03'),
        ('fp.brow.sel', 0, -.02, 'eyebrow01'), ('eye.pos', 1, -.02, 'eye01'),
        ('fp.m.pos.sel', 1, -.02, 'mouth01'), ('fp.m.pos.sel', 1, .02, 'mouth17'),
        ('fp.m.pos.sel', 0, .02, 'mouth19'), ('fp.m.pos.sel', 0, -.02, 'mouth20'),
        ('lip.cor.pos.sel.r', 1, .02, 'mouth11'), ('lip.cor.pos.sel.l', 1, .02, 'mouth12'),
    ]
    saved_mods = [(m, m.show_viewport) for m in face.modifiers]
    saved_drivers = [(f, f.mute) for f in face.animation_data.drivers] if face.animation_data else []
    for f, _ in saved_drivers:
        if f.data_path.endswith('show_viewport'):
            f.mute = True
    for m, _ in saved_mods:
        m.show_viewport = m.type == 'ARMATURE'
    def face_points():
        face.update_tag(); rig.update_tag(); bpy.context.view_layer.update()
        return [v.co.copy() for v in face.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
    neutral = face_points()
    for bone, axis, value, morph in cases:
        control = rig.pose.bones[bone]
        original_location = control.location.copy()
        control.location[axis] += value
        deformed = face_points()
        key = face.data.shape_keys.key_blocks[morph]
        assert key.value > .1, (bone, morph, 'panel does not drive morph', key.value)
        assert abs(key.value - overlay.data.shape_keys.key_blocks[morph].value) < 1e-5, (bone, 'FaceEX out of sync')
        assert max(((p-q).length for p,q in zip(deformed,neutral)), default=0) > 1e-5, (bone, 'panel does not deform face')
        control.location = original_location
        reset = face_points()
        assert max(((p-q).length for p,q in zip(reset,neutral)), default=0) < 1e-5, (bone, 'expression sticks after reset')
        facial_checks += 1
    for m, value in saved_mods:
        m.show_viewport = value
    for f, value in saved_drivers:
        f.mute = value
checks = assert_rig('pgr', str(model.parent))
failures = [check for check in checks if not check['passed']]
assert not failures, failures
if '--save-blend' in args:
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / (model.stem + '.blend')))
summary = {'model': str(model), 'repaired': repaired, 'bound_faces': bound_faces, 'bound_bands': bound_bands,
           'materials': verified, 'rig_checks': len(checks), 'facial_checks': facial_checks}
(OUTPUT / (model.stem + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
print('PGR_SETUP_PASS', summary)
