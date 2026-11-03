"""Compare generated face outlines with Bronya.blend across camera/head angles.

Run after a full Blade setup:
blender -b --factory-startup --python-exit-code 1 --python
tests/hsr_face_outlines_blender.py -- output/Blade.blend Bronya.blend
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/hsr-face-outline'
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
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property
from setup_wizard.utils.hsr_face_outlines import configure_face_outlines

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
path = Path(args[0]) if args else ROOT / 'output/Blade.blend'
reference_path = Path(args[1]) if len(args) > 1 else ROOT / 'Bronya.blend'
bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
face = bpy.data.objects['Face']
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
modifier = next(m for m in face.modifiers if m.type == 'NODES' and m.node_group
                and m.node_group.get('gacha_hsr_face_outlines'))
group = modifier.node_group
assert get_modifier_property(modifier, 'Input_8') == 0
assert get_modifier_property(modifier, group['dynamic_socket']) == 1
head_origin = get_modifier_property(modifier, group['head_socket'])
camera = get_modifier_property(modifier, 'Input_4')
assert head_origin and camera
assert head_origin.name in bpy.context.scene.objects
assert camera == bpy.context.scene.camera
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH' and obj != face:
        assert not any(m.type == 'NODES' and m.node_group and m.node_group.get('gacha_hsr_face_outlines') for m in obj.modifiers), obj.name

counts = len(bpy.data.node_groups), len(group.nodes), len(group.links), len(bpy.data.objects)
configure_face_outlines(bpy.context, face, modifier)
assert modifier.node_group == group
assert counts == (len(bpy.data.node_groups), len(group.nodes), len(group.links), len(bpy.data.objects))
saved_values = {s.identifier: get_modifier_property(modifier, s.identifier)
                for s in group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT'}
with bpy.data.libraries.load(str(reference_path.resolve()), link=False) as (source, target):
    target.node_groups = ['StellarToon - Outlines FACE']
reference = target.node_groups[0]
assert reference and reference != group
# An appended Bronya group must not cause repeated copies of the generated one.
group.name = 'StellarToon - Outlines FACE.generated'
reference.name = 'StellarToon - Outlines FACE'
counts = len(bpy.data.node_groups), len(bpy.data.objects)
configure_face_outlines(bpy.context, face, modifier)
assert modifier.node_group == group
assert counts == (len(bpy.data.node_groups), len(bpy.data.objects))
for node in reference.nodes:
    if node.type == 'GROUP' and node.node_tree and node.node_tree.name.startswith('Light Vectors'):
        node.inputs['Input_4'].default_value = head_origin

# Realize the outline instances to compare all emitted vertices, including the
# shell; evaluated_get().data alone only contains the original face mesh.
realize_group = bpy.data.node_groups.new('Test Realize Outlines', 'GeometryNodeTree')
realize_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
realize_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
ni = realize_group.nodes.new('NodeGroupInput')
no = realize_group.nodes.new('NodeGroupOutput')
nr = realize_group.nodes.new('GeometryNodeRealizeInstances')
realize_group.links.new(ni.outputs[0], nr.inputs[0])
realize_group.links.new(nr.outputs[0], no.inputs[0])
realize = face.modifiers.new('Test Realize', 'NODES')
realize.node_group = realize_group

def select_group(selected, dynamic=True):
    modifier.node_group = selected
    for identifier, value in saved_values.items():
        if value is not None and identifier not in (group['dynamic_socket'], group['head_socket']):
            set_modifier_property(modifier, identifier, value)
    if selected == reference:
        set_modifier_property(modifier, 'Input_31', float(dynamic))
    else:
        set_modifier_property(modifier, group['dynamic_socket'], float(dynamic))
        set_modifier_property(modifier, group['head_socket'], head_origin)

def positions():
    rig.update_tag()
    face.update_tag()
    bpy.context.view_layer.update()
    evaluated = face.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = [v.co.copy() for v in mesh.vertices]
    evaluated.to_mesh_clear()
    assert all(math.isfinite(c) for v in result for c in v)
    return result

center = face.matrix_world @ (sum((Vector(c) for c in face.bound_box), Vector()) / 8)
worst = 0
changed = 0
cases = []
head = rig.pose.bones['head']
head.rotation_mode = 'XYZ'
for head_angle in (0, 35):
    head.rotation_euler.z = math.radians(head_angle)
    for yaw, pitch in [(0, 0), (45, 0), (-45, 0), (75, 0), (-75, 0), (90, 0), (0, 60), (0, -60), (65, 50)]:
        y, p = math.radians(yaw), math.radians(pitch)
        camera.location = center + Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * 1.5
        camera.update_tag()
        select_group(reference)
        expected = positions()
        select_group(group)
        actual = positions()
        assert len(expected) == len(actual) > len(face.data.vertices)
        error = max((a-b).length for a,b in zip(actual, expected))
        worst = max(worst, error)
        assert error < 2e-6, (head_angle, yaw, pitch, error)
        select_group(group, dynamic=False)
        static = positions()
        delta = max((a-b).length for a,b in zip(actual, static))
        changed += delta > 1e-6
        cases.append({'head': head_angle, 'yaw': yaw, 'pitch': pitch, 'reference_error': error, 'dynamic_delta': delta})
assert changed >= 4, 'Dynamic mask had no effect at grazing camera angles'
report = {'cases': cases, 'max_reference_error': worst, 'angles_with_suppressed_outlines': changed,
          'idempotent': True, 'face_only': True, 'zero_depth_offset': True}
(RUNTIME / 'regression.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HSR_FACE_OUTLINES_PASS', worst, changed, len(cases), flush=True)
