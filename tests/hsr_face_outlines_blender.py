"""Camera-free HSR shell and rendered view-mask regression.

blender -b --factory-startup --python-exit-code 1 --python
tests/hsr_face_outlines_blender.py -- character.blend
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/hsr-face-outline' / bpy.app.version_string.split()[0]
RUNTIME.mkdir(parents=True, exist_ok=True)
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = RUNTIME / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.utils.hsr_face_outlines import configure_face_outlines
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
path = Path(args[0]) if args else ROOT / 'output/Stelle - Elation.blend'
bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
face = bpy.data.objects['Face']
modifier = next(m for m in face.modifiers if m.type == 'NODES' and m.node_group
                and m.node_group.get('gacha_hsr_face_outlines') == 3)
group = modifier.node_group
assert group.get('camera_free') == 1
assert not any(o.type == 'CAMERA' for o in bpy.context.scene.objects)
assert not any(s.item_type == 'SOCKET' and s.socket_type == 'NodeSocketObject' for s in group.interface.items_tree)
assert not any(n.bl_idname == 'GeometryNodeObjectInfo' for n in group.nodes)
assert get_modifier_property(modifier, 'Input_8') == 0
assert get_modifier_property(modifier, group['dynamic_socket']) == 1
assert get_modifier_property(modifier, 'Input_3_use_attribute')
assert get_modifier_property(modifier, 'Input_3_attribute_name') == 'Col'
world_scale = sum(abs(v) for v in face.matrix_world.to_scale()) / 3
assert abs(get_modifier_property(modifier, 'Input_7') * world_scale - .25) < 1e-5
counts = len(bpy.data.node_groups), len(bpy.data.objects), len(bpy.data.cameras)
materials = [get_modifier_property(modifier, key) for key in ('Input_5', 'Input_9', 'Input_15', 'Input_19', 'Input_25')]
node_counts = {m: len(m.node_tree.nodes) for m in materials if m}
configure_face_outlines(bpy.context, face, modifier)
configure_face_outlines(bpy.context, face, modifier)
assert counts == (len(bpy.data.node_groups), len(bpy.data.objects), len(bpy.data.cameras))
assert all(len(m.node_tree.nodes) == count for m, count in node_counts.items())
view_mask = next(g for g in bpy.data.node_groups if g.get('gacha_hsr_face_view_mask') == 2)
assert any(m and any(n.type == 'GROUP' and n.node_tree == view_mask for n in m.node_tree.nodes) for m in materials)
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or obj == face:
        continue
    assert not any(m.type == 'NODES' and m.node_group and m.node_group.get('gacha_hsr_face_outlines') for m in obj.modifiers)
    for slot in obj.material_slots:
        if slot.material and slot.material.use_nodes:
            assert not any(n.type == 'GROUP' and n.node_tree == view_mask for n in slot.material.node_tree.nodes)
realize_tree = bpy.data.node_groups.new('Test Realize Face', 'GeometryNodeTree')
realize_tree.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
realize_tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
ni = realize_tree.nodes.new('NodeGroupInput')
no = realize_tree.nodes.new('NodeGroupOutput')
nr = realize_tree.nodes.new('GeometryNodeRealizeInstances')
realize_tree.links.new(ni.outputs[0], nr.inputs[0])
realize_tree.links.new(nr.outputs[0], no.inputs[0])
realize = face.modifiers.new('Test Realize Face', 'NODES')
realize.node_group = realize_tree
bpy.context.view_layer.update()
evaluated = face.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = evaluated.to_mesh()
for name in ('headForward', 'headUp'):
    assert mesh.attributes.get(name) and mesh.attributes[name].data[0].vector.length > .001, name
assert mesh.attributes['gacha_hsr_face_view_mask'].data[0].value == 1
evaluated.to_mesh_clear()

# Realized outline-only geometry must exclude the blue-marked internal folds.
# The original mesh, lip texture and exterior outline remain available.
original_geometry = len(face.data.vertices), len(face.data.polygons)
base_setting = get_modifier_property(modifier, 'Input_12')
set_modifier_property(modifier, 'Input_12', False)
shell_counts = []
for clean in (False, True):
    set_modifier_property(modifier, group['interior_mask_socket'], clean)
    face.update_tag()
    bpy.context.view_layer.update()
    evaluated = face.evaluated_get(bpy.context.evaluated_depsgraph_get())
    shell = evaluated.to_mesh()
    shell_counts.append(len(shell.polygons))
    if clean:
        colors = shell.color_attributes['Col']
        for polygon in shell.polygons:
            blue = sum(colors.data[i if colors.domain == 'CORNER' else shell.loops[i].vertex_index].color[2]
                       for i in polygon.loop_indices) / polygon.loop_total
            assert blue <= .0011, (polygon.index, blue)
    evaluated.to_mesh_clear()
assert 0 < shell_counts[1] < shell_counts[0], shell_counts
assert original_geometry == (len(face.data.vertices), len(face.data.polygons))
set_modifier_property(modifier, 'Input_12', base_setting)
set_modifier_property(modifier, group['interior_mask_socket'], True)
print('HSR_INTERIOR_FACE_HULL_PASS', shell_counts, flush=True)
face.modifiers.remove(realize)
bpy.data.node_groups.remove(realize_tree)

# Render the baked shader's visibility using real rays and world-space head
# attributes. The render camera is test equipment and is never saved.
scene = bpy.data.scenes.new('View Mask Regression')
scene.render.engine = 'CYCLES'
scene.cycles.samples = 1
scene.render.resolution_x = scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.world = bpy.data.worlds.new('Black Test World')
scene.world.color = (0, 0, 0)
mesh = bpy.data.meshes.new('Face Region Swatch')
mesh.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new('Face Region Swatch', mesh)
scene.collection.objects.link(plane)
colors = mesh.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='POINT')
for item in colors.data:
    # Half-intensity BYTE_COLOR markers evaluate near 0.216, not 0.5.
    item.color = (0, .215861, .215861, 1)
for name in ('headForward', 'headUp'):
    mesh.attributes.new(name=name, type='FLOAT_VECTOR', domain='POINT')
mesh.attributes.new(name='gacha_hsr_face_view_mask', type='FLOAT', domain='POINT')
material = bpy.data.materials.new('Visibility Swatch')
material.use_nodes = True
material.node_tree.nodes.clear()
mask = material.node_tree.nodes.new('ShaderNodeGroup')
mask.node_tree = view_mask
emission = material.node_tree.nodes.new('ShaderNodeEmission')
output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
material.node_tree.links.new(mask.outputs['Visibility'], emission.inputs['Color'])
material.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
mesh.materials.append(material)
camera = bpy.data.objects.new('Test Render View', bpy.data.cameras.new('Test Render View'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .5


def direction(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))


report = []
for name, yaw, pitch, head_yaw, strength, visible in (
        ('front', 0, 0, 0, 1, True),
        ('profile', 80, 0, 0, 1, False),
        ('above', 0, 60, 0, 1, False),
        ('below', 0, -60, 0, 1, False),
        ('head_turn', 80, 0, 80, 1, True),
        ('disabled', 80, 0, 0, 0, True)):
    ray = direction(yaw, pitch)
    camera.location = ray * 2
    camera.rotation_euler = (-ray).to_track_quat('-Z', 'Y').to_euler()
    plane.rotation_euler = ray.to_track_quat('Z', 'Y').to_euler()
    for item in mesh.attributes['headForward'].data:
        item.vector = direction(head_yaw, 0)
    for item in mesh.attributes['headUp'].data:
        item.vector = (0, 0, 1)
    for item in mesh.attributes['gacha_hsr_face_view_mask'].data:
        item.value = strength
    mesh.update()
    mesh.update_tag()
    filename = RUNTIME / (name + '.png')
    scene.render.filepath = str(filename)
    bpy.ops.render.render(scene=scene.name, write_still=True)
    rendered = bpy.data.images.load(str(filename), check_existing=False)
    center = (16 * 32 + 16) * 4
    value = rendered.pixels[center]
    bpy.data.images.remove(rendered)
    assert (value > .98 if visible else value < .02), (name, value)
    report.append({'case': name, 'visibility': value})
    print('HSR_FACE_VIEW_CASE_PASS', name, value, flush=True)
(RUNTIME / 'regression.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HSR_CAMERA_FREE_FACE_OUTLINES_PASS', len(report), flush=True)
