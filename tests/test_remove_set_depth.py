import sys
import os
import bpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from setup_wizard.replace_default_materials_setup.game_default_material_replacers import (
    remove_set_depth_nodes_from_highlight_material
)

mat = bpy.data.materials.new(name="HoYoverse - Genshin Highlight Test")
mat.use_nodes = True
tree = mat.node_tree
tree.nodes.clear()

out_node = tree.nodes.new("ShaderNodeOutputMaterial")
mix_node = tree.nodes.new("ShaderNodeMixShader")
emiss_node = tree.nodes.new("ShaderNodeEmission")

ng_depth = bpy.data.node_groups.new(name="Set Depth.001", type="ShaderNodeTree")
if hasattr(ng_depth, "interface"):
    ng_depth.interface.new_socket(name="Shader", in_out="INPUT", socket_type="NodeSocketShader")
else:
    ng_depth.inputs.new("NodeSocketShader", "Shader")

depth_node = tree.nodes.new("ShaderNodeGroup")
depth_node.name = "Group.002"
depth_node.node_tree = ng_depth

if depth_node.inputs:
    tree.links.new(emiss_node.outputs["Emission"], depth_node.inputs[0])
tree.links.new(emiss_node.outputs["Emission"], mix_node.inputs[2])
tree.links.new(mix_node.outputs["Shader"], out_node.inputs["Surface"])

assert any("set depth" in n.name.lower() or (n.type == "GROUP" and n.node_tree and "set depth" in n.node_tree.name.lower()) for n in tree.nodes)

remove_set_depth_nodes_from_highlight_material(mat)

has_set_depth = any(
    "set depth" in n.name.lower() or (n.type == "GROUP" and n.node_tree and "set depth" in n.node_tree.name.lower())
    for n in tree.nodes
)
assert not has_set_depth, "Set Depth node should have been removed!"

assert out_node.name in tree.nodes
assert mix_node.name in tree.nodes
assert emiss_node.name in tree.nodes
assert out_node.inputs["Surface"].is_linked

print("TEST PASSED: Set Depth node removed correctly from highlight material!")
