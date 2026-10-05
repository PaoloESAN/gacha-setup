"""
Test verification that Lighting Panel links are cleanly and completely connected
matching Hutao's Global Material Properties layout.
"""
import sys
import os
import bpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from setup_wizard.character_rig_setup.lighting_panel_setup import (
    LightingPanel,
    disconnect_lighting_panel_nodes_from_global_material_properties,
    is_lighting_panel_connected
)

hutao_path = r"D:\arreglos\Hutao\Hutao - Goo TO DISTRIBUTE.blend"
if not os.path.exists(hutao_path):
    print("Hutao blend not found, skipping test")
    sys.exit(0)

bpy.ops.wm.open_mainfile(filepath=hutao_path)

ng = bpy.data.node_groups.get("Global Material Properties+")
out_node = ng.nodes.get("Global Properties") or ng.nodes.get("Group Output")

# 1. Disconnect test
disconnect_lighting_panel_nodes_from_global_material_properties()
connected_count_after_disconnect = sum(
    1 for inp in out_node.inputs
    if inp.links and not inp.name.startswith("---") and "face" not in inp.name.lower()
)
assert connected_count_after_disconnect == 0, f"Expected 0 connections after disconnect, got {connected_count_after_disconnect}"

# 2. Re-connect test
lp = LightingPanel("")
lp.connect_lighting_panel_nodes_to_global_material_properties()

expected_connections = {
    "Toggle Fresnel": "Math",
    "Fresnel Color": "Fresnel Color",
    "Fresnel Power": "Invert Color",
    "Fresnel Scaler": "Value = Fresnel Scaler",
    "Ambient Colour": "Ambient",
    "Sharp Lit Colour": "SharpLit",
    "Sharp Shadow Colour": "SharpShadow",
    "Soft Lit Colour": "SoftLit",
    "Soft Shadow Colour": "SoftShadow",
    "Shadow Position Offset": "Math.003",
    "Rim Lit": "Mix",
    "Rim Shadow": "Mix.001",
    "Rim Scale": "Rim Scale.001"
}

for sock_name, expected_node in expected_connections.items():
    inp = out_node.inputs.get(sock_name)
    assert inp is not None, f"Socket '{sock_name}' missing from Global Properties"
    assert inp.links, f"Socket '{sock_name}' has no incoming link!"
    from_node = inp.links[0].from_node.name
    assert from_node == expected_node, f"Socket '{sock_name}' connected to '{from_node}', expected '{expected_node}'"

print("ALL 13 LIGHTING PANEL CONNECTIONS VERIFIED SUCCESSFULLY ON HUTAO!")
