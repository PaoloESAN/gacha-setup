import bpy
import sys
from pathlib import Path

# Add workspace to path
WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from setup_wizard.ui.character_settings_utils import GACHA_GAME_KEY
from setup_wizard.ui.gi_ui_setup_wizard_menu import (
    GI_LIGHT_PRESETS,
    detect_character_light_mode,
    update_gi_light_mode,
    update_gi_lighting,
    pull_gi_panel_values,
    register_gi_properties,
    unregister_gi_properties,
)


def create_genshin_test_character(name, preset_key="0"):
    # Create armature
    arm_data = bpy.data.armatures.new(f"{name}_ArmData")
    arm = bpy.data.objects.new(f"{name}_Rig", arm_data)
    arm[GACHA_GAME_KEY] = "GENSHIN_IMPACT"
    bpy.context.scene.collection.objects.link(arm)

    # Create mesh
    mesh_data = bpy.data.meshes.new(f"{name}_MeshData")
    mesh = bpy.data.objects.new(f"{name}_Body", mesh_data)
    mesh.parent = arm
    bpy.context.scene.collection.objects.link(mesh)

    # Create material
    mat = bpy.data.materials.new(f"{name}_Mat")
    mat.use_nodes = True
    mesh.data.materials.append(mat)

    # Create Global Material Properties node group with interface sockets
    ng = bpy.data.node_groups.new(f"Global Material Properties_{name}", 'ShaderNodeTree')
    out_node = ng.nodes.new('NodeGroupOutput')
    out_node.name = "Global Properties"

    # Add interface sockets (compatible with Blender 4.0+)
    for prop in [
        "Ambient Colour", "Sharp Lit Colour", "Soft Lit Colour",
        "Sharp Shadow Colour", "Soft Shadow Colour", "Rim Lit", "Rim Shadow"
    ]:
        if hasattr(ng, "interface"):
            sock = ng.interface.new_socket(prop, in_out='OUTPUT', socket_type='NodeSocketColor')
        else:
            sock = ng.outputs.new('NodeSocketColor', prop)

    for prop in [
        "Shadow Position", "Day/Night", "Toggle Fresnel", "Fresnel Power",
        "Fresnel Scaler", "Toggle Catch Shadows"
    ]:
        if hasattr(ng, "interface"):
            sock = ng.interface.new_socket(prop, in_out='OUTPUT', socket_type='NodeSocketFloat')
        else:
            sock = ng.outputs.new('NodeSocketFloat', prop)

    # Set initial values according to preset_key
    preset = GI_LIGHT_PRESETS.get(preset_key, GI_LIGHT_PRESETS["0"])
    if "Ambient Colour" in out_node.inputs:
        out_node.inputs["Ambient Colour"].default_value = list(preset["ambient"]) + [1.0]
    if "Sharp Lit Colour" in out_node.inputs:
        out_node.inputs["Sharp Lit Colour"].default_value = list(preset["sharp_lit"]) + [1.0]
    if "Soft Lit Colour" in out_node.inputs:
        out_node.inputs["Soft Lit Colour"].default_value = list(preset["soft_lit"]) + [1.0]
    if "Sharp Shadow Colour" in out_node.inputs:
        out_node.inputs["Sharp Shadow Colour"].default_value = list(preset["sharp_shadow"]) + [1.0]
    if "Soft Shadow Colour" in out_node.inputs:
        out_node.inputs["Soft Shadow Colour"].default_value = list(preset["soft_shadow"]) + [1.0]
    if "Shadow Position" in out_node.inputs:
        out_node.inputs["Shadow Position"].default_value = preset.get("shadow_position", 0.55)
    if "Day/Night" in out_node.inputs:
        out_node.inputs["Day/Night"].default_value = preset.get("day_night", 0.0)
    if "Rim Lit" in out_node.inputs:
        out_node.inputs["Rim Lit"].default_value = list(preset["rim_lit"]) + [1.0]
    if "Rim Shadow" in out_node.inputs:
        out_node.inputs["Rim Shadow"].default_value = list(preset["rim_shadow"]) + [1.0]

    # Add group node to material
    g_node = mat.node_tree.nodes.new('ShaderNodeGroup')
    g_node.node_tree = ng

    return arm, mesh, mat, ng


def run_tests():
    print("=== Running Genshin Lighting Mode Detection Tests ===")

    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    register_gi_properties()

    # Setup Character 1 with Default lighting ("0")
    arm1, mesh1, mat1, ng1 = create_genshin_test_character("Char1", preset_key="0")

    # Setup Character 2 with Sunset lighting ("3")
    arm2, mesh2, mat2, ng2 = create_genshin_test_character("Char2", preset_key="3")

    # --- Test 1: Detection directly from character shaders ---
    mode1 = detect_character_light_mode(arm1)
    mode2 = detect_character_light_mode(arm2)
    assert mode1 == "0", f"Expected Char1 to be detected as Default ('0'), got '{mode1}'"
    assert mode2 == "3", f"Expected Char2 to be detected as Sunset ('3'), got '{mode2}'"
    print("PASS: Both characters' distinct presets detected from shader values independently")

    # --- Test 2: Switching selection in UI updates scene.gi_light_mode to match character ---
    # Select Char1
    bpy.context.view_layer.objects.active = arm1
    arm1.select_set(True)
    arm2.select_set(False)

    pull_gi_panel_values(bpy.context.scene, bpy.context, force=True)
    assert bpy.context.scene.gi_light_mode == "0", f"Expected scene.gi_light_mode to be '0', got '{bpy.context.scene.gi_light_mode}'"

    # Select Char2
    bpy.context.view_layer.objects.active = arm2
    arm1.select_set(False)
    arm2.select_set(True)

    pull_gi_panel_values(bpy.context.scene, bpy.context, force=True)
    assert bpy.context.scene.gi_light_mode == "3", f"Expected scene.gi_light_mode to switch to '3' for Char2, got '{bpy.context.scene.gi_light_mode}'"
    print("PASS: Selection switch properly updates scene.gi_light_mode per character")

    # --- Test 3: Changing preset on Char1 does not affect Char2 ---
    bpy.context.view_layer.objects.active = arm1
    arm1.select_set(True)
    arm2.select_set(False)

    # Change Char1 to Night ("4")
    bpy.context.scene.gi_light_mode = "4"
    update_gi_light_mode(bpy.context.scene, bpy.context)

    # Verify Char1 is now Night
    assert detect_character_light_mode(arm1) == "4", "Char1 should now be detected as Night ('4')"
    assert arm1.get("gi_light_mode") == "4"

    # Verify Char2 is completely untouched and still Sunset!
    assert detect_character_light_mode(arm2) == "3", f"Char2 was unexpectedly modified! Detected: {detect_character_light_mode(arm2)}"
    print("PASS: Changing Char1 to Night did not leak into Char2 (Char2 is still Sunset)")

    # --- Test 4: Switching back to Char2 updates UI back to Sunset ---
    bpy.context.view_layer.objects.active = arm2
    arm1.select_set(False)
    arm2.select_set(True)

    pull_gi_panel_values(bpy.context.scene, bpy.context, force=True)
    assert bpy.context.scene.gi_light_mode == "3", f"Expected scene.gi_light_mode to be '3' for Char2, got '{bpy.context.scene.gi_light_mode}'"

    # --- Test 5: Custom colors detection ("6") ---
    # Edit ambient color on Char2 to custom green
    bpy.context.scene.gi_amb_color = (0.2, 0.9, 0.3)
    update_gi_lighting(bpy.context.scene, bpy.context)

    assert detect_character_light_mode(arm2) == "6", f"Expected Char2 to be detected as Custom ('6'), got '{detect_character_light_mode(arm2)}'"
    assert bpy.context.scene.gi_light_mode == "6"

    # Char1 must still be Night ("4")
    assert detect_character_light_mode(arm1) == "4"

    # Switching to Char1 restores Night ("4")
    bpy.context.view_layer.objects.active = arm1
    arm1.select_set(True)
    arm2.select_set(False)
    pull_gi_panel_values(bpy.context.scene, bpy.context, force=True)
    assert bpy.context.scene.gi_light_mode == "4"
    print("PASS: Custom colors correctly detected as '6' without affecting other characters")

    print("\nALL GENSHIN LIGHTING MODE DETECTION TESTS PASSED!")


if __name__ == "__main__":
    run_tests()
