"""Run with Blender --background --factory-startup --python-exit-code 1
--python tests/lighting_panel_disconnect_blender.py.
"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from setup_wizard.character_rig_setup.lighting_panel_setup import (
    LightingPanel,
    disconnect_lighting_panel_nodes_from_global_material_properties as disconnect,
    is_lighting_panel_connected,
)

bpy.ops.wm.read_factory_settings(use_empty=True)
tree = bpy.data.node_groups.new('Global Material Properties Shared', 'ShaderNodeTree')
for name, socket_type in [('Ambient Colour', 'NodeSocketColor'), ('Face Softness', 'NodeSocketFloat'),
                          ('Custom Shader Input', 'NodeSocketFloat')]:
    tree.interface.new_socket(name=name, in_out='OUTPUT', socket_type=socket_type)
output = tree.nodes.new('NodeGroupOutput')
output.name = 'Global Properties'
ambient = tree.nodes.new('ShaderNodeRGB')
ambient.name = 'Ambient'
ambient.outputs[0].default_value = (0.8, 0.6, 0.4, 1)
tree.links.new(ambient.outputs[0], output.inputs['Ambient Colour'])
custom = tree.nodes.new('ShaderNodeValue')
tree.links.new(custom.outputs[0], output.inputs['Face Softness'])
tree.links.new(custom.outputs[0], output.inputs['Custom Shader Input'])

materials, nodes = [], []
for name in ('Character A', 'Character B'):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    group = mat.node_tree.nodes.new('ShaderNodeGroup')
    group.node_tree = tree
    materials.append(mat)
    nodes.append(group)

disconnect()
disconnect([])
assert len(tree.links) == 3
assert not is_lighting_panel_connected([])
LightingPanel('').connect_lighting_panel_nodes_to_global_material_properties([])
assert len(tree.links) == 3
print('PASS: missing or empty disconnection targets do not affect any material')

disconnect([materials[0]])
isolated = nodes[0].node_tree
assert isolated != tree and nodes[1].node_tree == tree
assert not isolated.nodes['Global Properties'].inputs['Ambient Colour'].is_linked
assert isolated.nodes['Global Properties'].inputs['Face Softness'].is_linked
assert isolated.nodes['Global Properties'].inputs['Custom Shader Input'].is_linked
assert len(tree.links) == 3
assert is_lighting_panel_connected([materials[1]])
print('PASS: only the target character loses its panel link, even with a shared group')

LightingPanel('').connect_lighting_panel_nodes_to_global_material_properties([materials[0]])
assert is_lighting_panel_connected([materials[0]])
assert len(tree.links) == 3
user = isolated.nodes.new('ShaderNodeRGB')
user.name = 'User Lighting'
isolated.links.new(user.outputs[0], isolated.nodes['Global Properties'].inputs['Ambient Colour'])
disconnect([materials[0]])
link = isolated.nodes['Global Properties'].inputs['Ambient Colour'].links[0]
assert link.from_node == user
assert len(tree.links) == 3
print('PASS: reconnect works and disconnection preserves custom user links and face settings')
