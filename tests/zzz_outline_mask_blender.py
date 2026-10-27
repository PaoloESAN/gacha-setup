"""Blender --background --factory-startup --python-exit-code 1 --python tests/zzz_outline_mask_blender.py"""
import os
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYTEST_VERSION'] = 'outline-regression'
from setup_wizard.services.zzz_outline_mask_service import create_face_outline_mask
from setup_wizard.utils.modifier_utils import get_modifier_property

bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(ROOT/'setup_wizard/shaders/zzz/ZZZ Setup v7.blend')) as (source, target):
    target.node_groups = ['face_outlines', 'ZZZ Outlines']
general = bpy.data.node_groups['ZZZ Outlines']
general_links = [(l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name) for l in general.links]
model = next((ROOT/'chars/zzz/roxy-default').glob('*.fbx'))
bpy.ops.import_scene.fbx(filepath=str(model))
face = next(o for o in bpy.data.objects if o.type == 'MESH' and 'face' in o.name.lower())
mesh = face.data
topology = (len(mesh.vertices), len(mesh.edges), len(mesh.polygons), len(mesh.loops))
coordinates = [v.co.copy() for v in mesh.vertices]
original_colors = [tuple(d.color) for d in mesh.color_attributes['Attribute'].data]
# Reproduce old scenes with the colliding group and color-mask names.
face.vertex_groups.new(name='outline_mask').add([0], 0, 'REPLACE')
assert create_face_outline_mask(face)
assert face.vertex_groups.get('outline_mask') is None
assert face.vertex_groups.get('outline_mask_weights') is not None
mask = mesh.color_attributes['outline_mask']
assert mask.data[0].color[0] == 1 and mask.data[36].color[0] == 1, 'Both skin halves must receive outlines'
white = [v for v in mesh.vertices if mask.data[v.index].color[0] > .5]
left = sum(v.co.x < -1e-5 for v in white)
right = sum(v.co.x > 1e-5 for v in white)
assert left > 400 and right > 400 and abs(left-right) / max(left, right) < .05, (left, right)
for polygon in mesh.polygons:
    if polygon.material_index in (1, 2):
        assert all(mask.data[v].color[0] == 0 for v in polygon.vertices), 'Eyes/brows must be excluded'
assert topology == (len(mesh.vertices), len(mesh.edges), len(mesh.polygons), len(mesh.loops))
assert coordinates == [v.co for v in mesh.vertices]
assert original_colors == [tuple(d.color) for d in mesh.color_attributes['Attribute'].data]
modifier = face.modifiers['Outlines']
assert get_modifier_property(modifier, 'Input_13')
assert get_modifier_property(modifier, 'Input_3_use_attribute') == 1
assert get_modifier_property(modifier, 'Input_3_attribute_name') == 'outline_mask'
group = modifier.node_group
assert group.nodes['Reroute.024'].inputs[0].links[0].from_socket.name == 'Red'
assert group.nodes['Merge by Distance'].inputs['Geometry'].links[0].from_node.name == 'ZZZ_Delete_Masked_Outlines'
assert group.nodes['ZZZ_Delete_Masked_Outlines'].inputs['Geometry'].links[0].from_node.name != 'Merge by Distance'
counts = (len(group.nodes), len(group.links))
assert create_face_outline_mask(face)
assert counts == (len(group.nodes), len(group.links)), 'Patch must be idempotent'
assert general_links == [(l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name) for l in general.links]

def make_hull_wrapper(group):
    """Realize only the outline stream so tests inspect generated geometry."""
    wrapper = bpy.data.node_groups.new('Outline regression wrapper', 'GeometryNodeTree')
    wrapper.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    wrapper.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    inp = wrapper.nodes.new('NodeGroupInput')
    out = wrapper.nodes.new('NodeGroupOutput')
    hull = wrapper.nodes.new('GeometryNodeGroup'); hull.node_tree = group
    attribute = wrapper.nodes.new('GeometryNodeInputNamedAttribute'); attribute.data_type = 'FLOAT_COLOR'
    attribute.inputs['Name'].default_value = 'outline_mask'
    realize = wrapper.nodes.new('GeometryNodeRealizeInstances')
    wrapper.links.new(inp.outputs['Geometry'], hull.inputs['Geometry'])
    wrapper.links.new(attribute.outputs['Attribute'], hull.inputs['Vertex Colors'])
    wrapper.links.new(hull.outputs['Geometry'], realize.inputs['Geometry'])
    wrapper.links.new(realize.outputs['Geometry'], out.inputs['Geometry'])
    hull.inputs['Base Geometry'].default_value = False
    hull.inputs['Use Vertex Colors?'].default_value = True
    return wrapper

# Evaluate a realized hull to catch node cycles and actual channel behavior.
wrapper = make_hull_wrapper(group)
modifier.node_group = wrapper
def evaluated_count():
    mesh.update(); mesh.update_tag(); face.update_tag(refresh={'DATA'}); bpy.context.view_layer.update()
    evaluated = face.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result = evaluated.to_mesh()
    count = len(result.polygons)
    evaluated.to_mesh_clear()
    return count
count = evaluated_count()
assert count > 1500, count
for d in mask.data:
    d.color = (0, 0, 0, .4)
black_count = evaluated_count()
print('COUNTS', count, black_count)
assert black_count == 0, 'Black RGB must mask out even fractional alpha'
for d in mask.data:
    d.color = (1, 1, 1, 0)
assert evaluated_count() > count, 'White RGB must work with alpha zero'

# Existing CORNER masks are supported and source topology stays intact.
modifier.node_group = group
mesh.color_attributes.remove(mask)
mesh.color_attributes.new(name='outline_mask', type='BYTE_COLOR', domain='CORNER')
assert create_face_outline_mask(face)
assert any(d.color[0] == 1 for d in mesh.color_attributes['outline_mask'].data)
assert any(d.color[0] == 0 for d in mesh.color_attributes['outline_mask'].data)
solidify = face.modifiers.new('Solidify', 'SOLIDIFY')
assert create_face_outline_mask(face)
assert solidify.vertex_group == 'outline_mask_weights'
assert solidify.thickness_vertex_group == 0 and not solidify.invert_vertex_group
widget = bpy.data.objects.new('WGT-face', mesh.copy())
bpy.context.collection.objects.link(widget)
widget.modifiers.new('Preserve', 'SOLIDIFY')
assert not create_face_outline_mask(widget)
assert widget.modifiers.get('Preserve') is not None
print('PASS: Roxy seam symmetry, exclusions, RNA binding, evaluated hull, channels, CORNER and idempotence')

# Five characters total, including Roxy; evaluate each actual outline stream.
for folder in ('miyabi-dignified-blossom', 'jane-doe-hidden-nightfade',
               'remielle-feathered-murmurs', 'wise-default'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT/'setup_wizard/shaders/zzz/ZZZ Setup v7.blend')) as (source, target):
        target.node_groups = ['face_outlines']
    bpy.ops.import_scene.fbx(filepath=str(next((ROOT/'chars/zzz'/folder).rglob('*.fbx'))))
    face = next(o for o in bpy.data.objects if o.type == 'MESH' and 'face' in o.name.lower())
    mesh = face.data
    coordinates = [v.co.copy() for v in mesh.vertices]
    topology = (len(mesh.vertices), len(mesh.edges), len(mesh.polygons), len(mesh.loops))
    assert create_face_outline_mask(face)
    mask = mesh.color_attributes['outline_mask']
    skin = [v for v in mesh.vertices if mask.data[v.index].color[0] > .5]
    left = sum(v.co.x < -1e-5 for v in skin)
    right = sum(v.co.x > 1e-5 for v in skin)
    assert min(left, right) > 100 and abs(left-right) / max(left, right) < .15, (folder, left, right)
    for polygon in mesh.polygons:
        material = mesh.materials[polygon.material_index]
        if material and any(word in material.name.lower() for word in ('eye', 'brow', 'shadow', 'teeth', 'tongue')):
            assert all(mask.data[v].color[0] == 0 for v in polygon.vertices), (folder, 'detail outlined')
    assert coordinates == [v.co for v in mesh.vertices]
    assert topology == (len(mesh.vertices), len(mesh.edges), len(mesh.polygons), len(mesh.loops))
    modifier = face.modifiers['Outlines']
    assert get_modifier_property(modifier, 'Input_3_use_attribute') == 1
    assert get_modifier_property(modifier, 'Input_3_attribute_name') == 'outline_mask'
    assert face.vertex_groups.get('outline_mask') is None
    group = modifier.node_group
    original_mask = [tuple(d.color) for d in mask.data]
    assert create_face_outline_mask(face)
    assert original_mask == [tuple(d.color) for d in mask.data], (folder, 'non-repeatable mask')
    modifier.node_group = make_hull_wrapper(group)
    count = evaluated_count()
    assert count > 500, (folder, count)
    for d in mask.data:
        d.color = (0, 0, 0, .4)
    assert evaluated_count() == 0, (folder, 'black mask ignored')
    for d in mask.data:
        d.color = (1, 1, 1, 0)
    assert evaluated_count() > count, (folder, 'white mask ignored')
    print('PASS: bilateral skin, detail exclusion, RNA, topology, repeatability and evaluated hull', folder, left, right, count)
