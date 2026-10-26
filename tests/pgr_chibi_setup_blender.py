"""PGR chibi atlas and rig regression on QR3LaiyaMd010011. Run in Blender 5.2."""
import json, os, sys, zipfile
from pathlib import Path
import bpy, addon_utils
from mathutils import Matrix, Vector
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'tests/.runtime/pgr-chibi-regression'
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
args = [str(ROOT / 'chars/pgr/Animator/QR3LaiyaMd010011/QR3LaiyaMd010011.fbx')]
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


rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name in baseline)
mat = body.material_slots[0].material
from setup_wizard.utils.pgr_chibi_face import ATLAS_NODE, OVERLAY_NODE, FACE_UV, configure_chibi_face
atlas = mat.node_tree.nodes[ATLAS_NODE]
assert Path(atlas.image.filepath).stem == 'Base'
assert atlas.image.colorspace_settings.name == 'sRGB'
assert atlas.extension == 'CLIP'
assert mat.node_tree.nodes[OVERLAY_NODE].inputs[0].links[0].from_socket == atlas.outputs['Alpha']
assert body.data.uv_layers['UV0'].active_render
assert body.get('pgr_chibi_face_loops', 0) > 100
face = [l.vertex_index for l in body.data.loops if body.data.uv_layers[FACE_UV].data[l.index].uv.x >= 0]
assert face
weights = {v.index: sum(g.weight for g in v.groups if body.vertex_groups[g.group].name == 'DEF-spine.006') for v in body.data.vertices}
assert all(weights[i] > .99 for i in face)
for curve in body.animation_data.drivers if body.animation_data else []:
    if curve.data_path.endswith('show_viewport'):
        curve.mute = True
saved_mods = [(m, m.show_viewport) for m in body.modifiers]
for mod, _ in saved_mods:
    mod.show_viewport = mod.type == 'ARMATURE'
def points():
    rig.update_tag(); body.update_tag(); bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [body.matrix_world @ v.co for v in ev.data.vertices]
neutral = points()
assert len(neutral) == len(baseline[body.name])
neutral_error = max((a-b).length for a,b in zip(neutral, baseline[body.name]))
assert neutral_error < 1e-4, ('neutral bind changed', neutral_error)
head = rig.pose.bones['head']; rest_basis = head.matrix_basis.copy()
rest_head = (rig.matrix_world @ rig.pose.bones['DEF-spine.006'].matrix).copy()
head.rotation_mode = 'XYZ'; head.rotation_euler.y += .5
moved = points()
transform = rig.matrix_world @ rig.pose.bones['DEF-spine.006'].matrix @ rest_head.inverted()
error = max((moved[i] - transform @ neutral[i]).length for i in face)
assert error < 1e-4, ('face does not follow head', error)
assert max((moved[i]-neutral[i]).length for i in face) > .02
head.matrix_basis = rest_basis
assert max((a-b).length for a,b in zip(points(), neutral)) < 1e-4
for side in ('L', 'R'):
    foot = rig.pose.bones['DEF-foot.' + side]
    parent = rig.pose.bones['thigh_parent.' + side]
    old_switch = parent['IK_FK']
    group = body.vertex_groups['DEF-foot.' + side]
    indices = [v.index for v in body.data.vertices if any(g.group == group.index and g.weight > .99 for g in v.groups)]
    assert indices
    for mode in ('FK', 'IK'):
        parent['IK_FK'] = 1.0 if mode == 'FK' else 0.0
        initial = points()
        rest = (rig.matrix_world @ foot.matrix).copy()
        control = rig.pose.bones[('foot_fk.' if mode == 'FK' else 'foot_ik.') + side]
        old_basis = control.matrix_basis.copy()
        if mode == 'FK':
            control.matrix_basis = old_basis @ Matrix.Rotation(.25, 4, 'X')
        else:
            matrix = control.matrix.copy(); matrix.translation += Vector((0, -.02, .03)); control.matrix = matrix
        changed = points()
        transform = rig.matrix_world @ foot.matrix @ rest.inverted()
        assert max((changed[i] - transform @ initial[i]).length for i in indices) < 1e-4, (side, mode, 'foot deformation')
        assert max((changed[i] - initial[i]).length for i in indices) > .003, (side, mode, 'foot does not move')
        control.matrix_basis = old_basis
        points()
    parent['IK_FK'] = old_switch
    points()
checks = assert_rig('pgr', str(model.parent))
failures = [check for check in checks if not check['passed']]
print('CHIBI_RIG_CHECKS', len(checks), 'FAILURES', failures, flush=True)
assert not failures, failures
for mod, visible in saved_mods:
    mod.show_viewport = visible
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
# Re-importing the facial atlas must not grow UV layers or insert another mix.
data = json.loads((model.parent / 'Materials' / (model.stem + '.json')).read_text(encoding='utf-8-sig'))
diffuse = mat.node_tree.nodes['Body_Diffuse_UV0']
counts = (len(body.data.vertices), len(body.data.uv_layers), len(mat.node_tree.nodes), len(mat.node_tree.links))
for _ in range(2):
    assert configure_chibi_face(mat, data, {'base': str(model.parent/'Base.png')}, diffuse) == 1
assert counts == (len(body.data.vertices), len(body.data.uv_layers), len(mat.node_tree.nodes), len(mat.node_tree.links))
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'QR3LaiyaMd010011_fixed.blend'))
print('PGR_CHIBI_FACE_AND_RIG_PASS', 'vertices', len(neutral), 'face_loops', len(face), 'bind_error', neutral_error, 'rig_checks', len(checks), flush=True)
