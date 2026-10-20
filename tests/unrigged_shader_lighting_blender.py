"""Run with Blender --background --factory-startup --python-exit-code 1
--python tests/unrigged_shader_lighting_blender.py.
"""
import sys
from pathlib import Path
import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard.character_rig_setup.lighting_panel_setup import (
    LightingPanel, get_lighting_panel_source_socket, setup_unrigged_genshin_lighting,
)
from setup_wizard.utils.modifier_utils import set_modifier_property

with bpy.data.libraries.load(str(ROOT / 'setup_wizard/shaders/gi/HoYoverse - PrimoToon v4.0.blend'), link=False) as (src, dst):
    dst.materials = ['HoYoverse - Genshin Body']
template = dst.materials[0]
first, second, guard_material = template.copy(), template.copy(), template.copy()
for mat, source in ((first, 'Equip_Test_Mat'), (guard_material, 'Equip_Test_Mat_SwordGuard'),
                    (second, 'Equip_Other_Mat')):
    mat['_genshin_equipment'] = True
    mat['_original_material_name'] = source

def property_node(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'GROUP' and n.node_tree and 'global material properties' in n.node_tree.name.lower())

shared = property_node(first).node_tree
assert property_node(second).node_tree == shared
LightingPanel('').connect_lighting_panel_nodes_to_global_material_properties([first])
output = shared.nodes.get('Global Properties') or next(n for n in shared.nodes if n.type == 'GROUP_OUTPUT')
panel_inputs = [s.name for s in output.inputs if s.is_linked and get_lighting_panel_source_socket(shared, s.name) == s.links[0].from_socket]
assert len(panel_inputs) == 13, panel_inputs
before = len(shared.links)

# A mesh-only weapon must still receive lighting setup before Head Driver skips.
mesh = bpy.data.meshes.new('Weapon mesh')
weapon = bpy.data.objects.new('Equip_Test', mesh)
bpy.context.scene.collection.objects.link(weapon)
mesh.materials.append(first)
guard = bpy.data.objects.new('SwordGuard', bpy.data.meshes.new('Detached guard mesh'))
bpy.context.scene.collection.objects.link(guard)
guard.data.materials.append(guard_material)
other = bpy.data.objects.new('Other weapon', bpy.data.meshes.new('Other weapon mesh'))
bpy.context.scene.collection.objects.link(other)
other.data.materials.append(second)
bpy.ops.object.select_all(action='DESELECT')
weapon.select_set(True)
bpy.context.view_layer.objects.active = weapon
bpy.context.scene['setup_wizard_imported_fbx_path'] = 'Equip_Test.fbx'
props = bpy.context.scene.character_rigger_props
kwargs = dict(game_type='GENSHIN_IMPACT', next_step_idx=-1, invoker_type='', high_level_step_name='')

props.disable_rigging = True
assert len(shared.links) == before
assert bpy.ops.hoyoverse.rig_character(**kwargs) == {'FINISHED'}
assert len(shared.links) == before
print('PASS: preference and skipped rigging do not disconnect shader lighting')

assert bpy.ops.genshin.setup_head_driver(**kwargs) == {'FINISHED'}
tree = property_node(first).node_tree
assert tree != shared and property_node(second).node_tree == shared
guard_tree = property_node(guard_material).node_tree
assert all(not guard_tree.nodes['Global Properties'].inputs[name].is_linked for name in panel_inputs), (
    guard_tree.name, tree.name, dict(first.items()), dict(guard_material.items()))
new_output = tree.nodes.get('Global Properties') or next(n for n in tree.nodes if n.type == 'GROUP_OUTPUT')
assert all(not new_output.inputs[name].is_linked for name in panel_inputs)
for name in ('Ambient Colour', 'Sharp Lit Colour', 'Soft Lit Colour', 'Sharp Shadow Colour', 'Soft Shadow Colour'):
    assert all(value > 0.9 for value in new_output.inputs[name].default_value[:3]), name
assert len(shared.links) == before
print('PASS: lighting step disconnects all 13 panel links for the weapon; static colors are white; other material unchanged')
print('PASS: older imports include detached SwordGuard by equipment source, excluding other weapons')

# New imports group all their pieces even when an effect has no equipment name
# or Armature modifier. The detached effect must still get static lighting.
weapon['_setup_wizard_model_id'] = 'current-model'
guard['_setup_wizard_model_id'] = 'current-model'
other['_setup_wizard_model_id'] = 'other-model'
del guard_material['_genshin_equipment']
del guard_material['_original_material_name']
LightingPanel('').connect_lighting_panel_nodes_to_global_material_properties([first, guard_material])
assert bpy.ops.genshin.setup_head_driver(**kwargs) == {'FINISHED'}
assert all(not property_node(guard_material).node_tree.nodes['Global Properties'].inputs[name].is_linked
           for name in panel_inputs)
assert len(shared.links) == before
print('PASS: model ID includes detached effects without equipment names or armature links')

# A rigging preference alone cannot supply the shader's panel attributes.
LightingPanel('').connect_lighting_panel_nodes_to_global_material_properties([first, guard_material])
props.disable_rigging = False
assert bpy.ops.genshin.setup_head_driver(**kwargs) == {'FINISHED'}
assert all(not new_output.inputs[name].is_linked for name in panel_inputs)
assert len(shared.links) == before
print('PASS: rigging enabled without a configured panel still uses static lighting')

# A configured panel on this model must retain its controls.
group = bpy.data.node_groups.new('Test Light Vectors', 'GeometryNodeTree')
for name in ('Wheel', 'Picker'):
    group.interface.new_socket(name=name, in_out='INPUT', socket_type='NodeSocketObject')
modifier = weapon.modifiers.new('Light Vectors Weapon', 'NODES')
modifier.node_group = group
set_modifier_property(modifier, 'Socket_0', weapon)
set_modifier_property(modifier, 'Socket_1', guard)
LightingPanel('').connect_lighting_panel_nodes_to_global_material_properties([first, guard_material])
assert bpy.ops.genshin.setup_head_driver(**kwargs) == {'FINISHED'}
assert all(new_output.inputs[name].is_linked for name in panel_inputs)
print('PASS: lighting step preserves a configured panel when rigging is enabled')

bpy.ops.object.select_all(action='DESELECT')
setup_unrigged_genshin_lighting(bpy.context)
assert all(new_output.inputs[name].is_linked for name in panel_inputs)
print('PASS: no selected setup model means no lighting changes')

# The pipeline can keep the last import active while deselecting it.
assert bpy.context.view_layer.objects.active == weapon
props.disable_rigging = True
assert bpy.ops.genshin.setup_head_driver(**kwargs) == {'FINISHED'}
assert all(not new_output.inputs[name].is_linked for name in panel_inputs)
assert len(shared.links) == before
print('PASS: lighting step finishes a stamped active import after deselection')
