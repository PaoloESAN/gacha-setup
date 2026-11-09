"""Sandrone integration and render checks; run with Blender --background --factory-startup --python-exit-code 1 --python FILE."""
import bpy
import os
import sys
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYTEST_VERSION'] = 'expression test'
from setup_wizard.utils.genshin_face_expressions import setup_face_expressions, expression_nodes, MODIFIER, LEFT, RIGHT
from setup_wizard.utils.genshin_face_expressions import _find_overlay, _components
from setup_wizard.ui.character_settings_utils import invalidate_caches
from setup_wizard.utils.genshin_engine_nodes import configure_genshin_engine_nodes
from setup_wizard.utils.genshin_face_expressions import _brow_polygons
source = (Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else
          ROOT / 'output/sandrone-clockwork-expressions/Sandrone - Clockwork Maidens Waltz.blend')
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
invalidate_caches()
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
before_shapes = [
    key.name for key in bpy.data.objects['Face'].data.shape_keys.key_blocks]
uv_names = [uv.name for uv in bpy.data.objects['Face'].data.uv_layers]
setup_face_expressions(arm)
assert list(expression_nodes(arm))
assert [uv.name for uv in bpy.data.objects['Face'].data.uv_layers] == uv_names
assert [key.name for key in bpy.data.objects['Face'].data.shape_keys.key_blocks] == before_shapes
assert not bpy.data.objects['Body'].modifiers.get(MODIFIER)
assert not bpy.data.objects['Bang'].modifiers.get(MODIFIER)
assert not setup_face_expressions(arm)
selector = next(expression_nodes(arm))
face_brows = _brow_polygons(bpy.data.objects['Face'])
assert face_brows, 'Fixture has no recognized brows'
for attribute in (LEFT, RIGHT):
    mask = bpy.data.objects['Face'].data.attributes[attribute]
    assert not any(mask.data[i].value for i in face_brows), 'Expression mask hides brows'
print('EXPRESSION_SETUP', [(s.name, s.default_value)
      for s in selector.inputs if s.name != 'Original Skin'], flush=True)
for o in bpy.context.scene.objects:
    if o.type == 'MESH' and o.modifiers.get(MODIFIER):
        print('EYE_MASK', o.name, [(name, sum(
            x.value for x in o.data.attributes[name].data)) for name in (LEFT, RIGHT)], flush=True)
configure_genshin_engine_nodes()
from setup_wizard.utils.genshin_engine_nodes import is_goo_engine
material = next(mat for mat in bpy.data.materials if mat.node_tree == selector.id_data)
output = next(node for node in material.node_tree.nodes
              if node.type == 'OUTPUT_MATERIAL' and node.is_active_output)
if is_goo_engine():
    visibility = output.inputs['Surface'].links[0].from_node
    assert visibility.type == 'MIX_SHADER'
    assert visibility.inputs[0].links[0].from_socket == selector.outputs['Visibility']
    assert visibility.inputs[1].links[0].from_node.type == 'BSDF_TRANSPARENT'
    depth = visibility.inputs[2].links[0].from_node
    assert depth.type == 'GROUP' and depth.node_tree
    assert any(node.bl_idname == 'ShaderNodeSetDepth' for node in depth.node_tree.nodes)
    assert depth.inputs['Shader'].links[0].from_node == selector
    assert selector.inputs['Original Skin'].links[0].from_node != depth
else:
    assert output.inputs['Surface'].links[0].from_node == selector
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 32
scene.render.use_compositing = False
face = bpy.data.objects['Face']
pts = [face.matrix_world @ v.co for v in face.data.vertices]
center = Vector((0, -.08, (min(p.z for p in pts) + max(p.z for p in pts)) / 2))
cam = bpy.data.objects.new(
    'Expression Preview', bpy.data.cameras.new('Expression Preview'))
scene.collection.objects.link(cam)
cam.data.type = 'ORTHO'
cam.data.ortho_scale = .26
cam.location = center + Vector((0, -1, 0))
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
out = source.parent
character = source.stem.split(' - ')[0]
out.mkdir(parents=True, exist_ok=True)
realize = bpy.data.node_groups.new('Test Realize Face', 'GeometryNodeTree')
realize.interface.new_socket(
    name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
realize.interface.new_socket(
    name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
incoming = realize.nodes.new('NodeGroupInput')
outgoing = realize.nodes.new('NodeGroupOutput')
node = realize.nodes.new('GeometryNodeRealizeInstances')
realize.links.new(incoming.outputs[0], node.inputs[0])
realize.links.new(node.outputs[0], outgoing.inputs[0])
realize_mod = face.modifiers.new('Test Realize', 'NODES')
realize_mod.node_group = realize
counts = {}
for value in (0, 1, 13, 19):
    selector.inputs['Expression'].default_value = value
    selector.id_data.update_tag()
    scene.frame_set(scene.frame_current)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    counts[value] = {o.name: len(o.evaluated_get(dg).data.polygons) for o in (
        bpy.data.objects['Pupil'], bpy.data.objects['EyeStar'])}
    counts[value]['Face'] = len(face.evaluated_get(
        bpy.context.evaluated_depsgraph_get()).data.polygons)
    evaluated_face = face.evaluated_get(dg).data
    if is_goo_engine() and value == 0:
        from setup_wizard.utils.genshin_face_expressions import COVER_LEFT, COVER_RIGHT
        for name in (COVER_LEFT, COVER_RIGHT):
            cover = evaluated_face.attributes.get(name)
            if cover is not None:
                assert not any(item.value for item in cover.data), 'Neutral cover still writes depth'
    visible_brows = sum(poly.material_index < len(evaluated_face.materials) and
                        evaluated_face.materials[poly.material_index] is not None and
                        'brow' in evaluated_face.materials[poly.material_index].name.casefold()
                        for poly in evaluated_face.polygons)
    brow_material_faces = sum('brow' in face.data.materials[poly.material_index].name.casefold()
                              for poly in face.data.polygons
                              if face.data.materials[poly.material_index])
    assert visible_brows >= brow_material_faces, (value, visible_brows, brow_material_faces)
    print('EXPRESSION_COUNTS', value, counts[value], flush=True)
    scene.render.filepath = str(out / f'{character.lower()}-expression-{value}.png')
    bpy.ops.render.render(write_still=True)
# Scale and rotation must be real shader controls, and the panel has no name label.
from setup_wizard.utils.genshin_face_expressions import REPLACED_COVER
static = face.data.attributes.get(REPLACED_COVER)
if static is not None:
    static_values = [item.value for item in static.data]
    neutral_caps = {i for i, value in enumerate(static_values) if value and
                    (face.data.attributes[LEFT].data[i].value or
                     face.data.attributes[RIGHT].data[i].value)}
    if character == 'Vesna':
        # Two disconnected skin pieces per eye (63 + 7 faces), not the
        # surrounding eyelid rings or the actual white eye surfaces.
        assert len(neutral_caps) == 140, len(neutral_caps)

    def face_signature():
        from array import array
        mesh = face.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        coordinates = array('f', [0]) * (3 * len(mesh.vertices))
        mesh.vertices.foreach_get('co', coordinates)
        return len(mesh.polygons), coordinates.tobytes()

    for value in (1, 19):
        selector.inputs['Expression'].default_value = value
        selector.id_data.update_tag()
        scene.frame_set(scene.frame_current)
        bpy.context.view_layer.update()
        cleaned = face_signature()
        static.data.foreach_set('value', [state and i not in neutral_caps
                                          for i, state in enumerate(static_values)])
        face.data.update()
        face.update_tag()
        bpy.context.view_layer.update()
        assert face_signature() == cleaned, 'Neutral cleanup changed an active expression'
        static.data.foreach_set('value', static_values)
        face.data.update()
        face.update_tag()
        bpy.context.view_layer.update()

from setup_wizard.utils.genshin_face_expressions import draw_face_expressions


class RecordingLayout:
    def __init__(self): self.labels = []; self.properties = []
    def box(self): return self
    def label(self, **kwargs): self.labels.append(kwargs['text'])
    def prop(self, target, property, **kwargs): self.properties.append(kwargs['text'])


layout = RecordingLayout()
draw_face_expressions(layout, arm)
assert layout.labels == ['Facial Expressions']
assert 'Scale' in layout.properties and 'Rotation' in layout.properties
assert selector.inputs['Scale'].default_value == 1
selector.inputs['Scale'].default_value = .8
selector.inputs['Rotation'].default_value = .35
selector.id_data.update_tag()
scene.render.filepath = str(out / f'{character.lower()}-scaled-rotated.png')
bpy.ops.render.render(write_still=True)
selector.inputs['Scale'].default_value = 1
selector.inputs['Rotation'].default_value = 0
assert counts[1]['Face'] < counts[0]['Face']
assert counts[1]['Pupil'] == 0 and counts[1]['EyeStar'] == 0
selector.inputs['Expression'].default_value = 0
selector.id_data.update_tag()
scene.frame_set(scene.frame_current)
bpy.context.view_layer.update()
assert len(bpy.data.objects['Pupil'].evaluated_get(
    bpy.context.evaluated_depsgraph_get()).data.polygons) == counts[0]['Pupil']
face.modifiers.remove(realize_mod)
bpy.ops.wm.save_as_mainfile(filepath=str(
    out / f'{character} - Facial Expressions.blend'))
# Independent overrides restore one eye even with a shared expression enabled.
for shared, left, right, expected in ((19, 0, -1, counts[0]['Pupil'] // 2), (0, 1, 0, counts[0]['Pupil'] // 2), (0, 0, 0, counts[0]['Pupil'])):
    selector.inputs['Expression'].default_value = shared
    selector.inputs['Left Eye (-1 = shared)'].default_value = left
    selector.inputs['Right Eye (-1 = shared)'].default_value = right
    selector.id_data.update_tag()
    scene.frame_set(scene.frame_current)
    bpy.context.view_layer.update()
    assert len(bpy.data.objects['Pupil'].evaluated_get(
        bpy.context.evaluated_depsgraph_get()).data.polygons) == expected
# A normal face without the closed cover is not a candidate.
mesh = bpy.data.meshes.new('Ordinary Face')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 0, 1)], [], [(0, 1, 2)])
obj = bpy.data.objects.new('Ordinary Face', mesh)
assert _find_overlay(obj, _components(mesh)) is None
# Drivers and the atlas remain functional after saving and reopening.
bpy.ops.wm.open_mainfile(filepath=str(
    out / f'{character} - Facial Expressions.blend'), load_ui=False, use_scripts=False)
invalidate_caches()
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
selector = next(expression_nodes(arm))
assert selector.inputs['Expression'].default_value == 0
assert selector.inputs['Scale'].default_value == 1
assert selector.inputs['Rotation'].default_value == 0
assert not setup_face_expressions(arm)
assert all(
    n.image.packed_file for n in selector.node_tree.nodes if n.type == 'TEX_IMAGE')
selector.inputs['Expression'].default_value = 19
selector.id_data.update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()
assert len(bpy.data.objects['Pupil'].evaluated_get(
    bpy.context.evaluated_depsgraph_get()).data.polygons) == 0
selector.inputs['Expression'].default_value = 0
selector.id_data.update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
bpy.context.view_layer.update()
assert len(bpy.data.objects['Pupil'].evaluated_get(
    bpy.context.evaluated_depsgraph_get()).data.polygons) == counts[0]['Pupil']
print(character.upper() + '_EXPRESSIONS_PASS: zero restoration, expressions 1/13/19, per-eye overrides, no hair/body changes, shape keys, idempotency, packed atlas, and save/reload', flush=True)
