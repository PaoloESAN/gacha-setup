import bpy
import sys
from pathlib import Path

# Add workspace to path
WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from setup_wizard.genshin_animate_mode import (
    set_genshin_animate_mode,
    is_genshin_animate_mode,
    GI_OT_ToggleAnimateMode,
    register as register_animate_mode,
)
from setup_wizard.ui.character_settings_utils import GACHA_GAME_KEY


def run_tests():
    print("=== Running Genshin Animate Mode Per-Character Tests ===")

    # Clear existing objects and materials
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        register_animate_mode()
    except Exception:
        pass

    # 1. Setup Character 1 (Genshin)
    arm1_data = bpy.data.armatures.new("Char1_ArmatureData")
    arm1 = bpy.data.objects.new("Char1_Rig", arm1_data)
    arm1[GACHA_GAME_KEY] = "GENSHIN_IMPACT"
    bpy.context.scene.collection.objects.link(arm1)

    mesh1_data = bpy.data.meshes.new("Char1_Mesh1Data")
    mesh1 = bpy.data.objects.new("Char1_Body", mesh1_data)
    mesh1.parent = arm1
    bpy.context.scene.collection.objects.link(mesh1)

    mat1 = bpy.data.materials.new("Char1_Body_Mat")
    mat1.use_nodes = True
    mesh1.data.materials.append(mat1)

    # Add outline GN modifier to mesh1
    ng1 = bpy.data.node_groups.new("GI_Outlines", 'GeometryNodeTree')
    mod1 = mesh1.modifiers.new("Outlines", 'NODES')
    mod1.node_group = ng1
    mod1.show_viewport = True

    # 2. Setup Character 2 (Genshin)
    arm2_data = bpy.data.armatures.new("Char2_ArmatureData")
    arm2 = bpy.data.objects.new("Char2_Rig", arm2_data)
    arm2[GACHA_GAME_KEY] = "GENSHIN_IMPACT"
    bpy.context.scene.collection.objects.link(arm2)

    mesh2_data = bpy.data.meshes.new("Char2_Mesh1Data")
    mesh2 = bpy.data.objects.new("Char2_Body", mesh2_data)
    mesh2.parent = arm2
    bpy.context.scene.collection.objects.link(mesh2)

    mat2 = bpy.data.materials.new("Char2_Body_Mat")
    mat2.use_nodes = True
    mesh2.data.materials.append(mat2)

    # Add outline GN modifier to mesh2
    ng2 = bpy.data.node_groups.new("GI_Outlines_2", 'GeometryNodeTree')
    mod2 = mesh2.modifiers.new("Outlines", 'NODES')
    mod2.node_group = ng2
    mod2.show_viewport = True

    # --- Test 1: Initial State ---
    assert not is_genshin_animate_mode(arm1), "Char1 should not be in animate mode initially"
    assert not is_genshin_animate_mode(arm2), "Char2 should not be in animate mode initially"
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat"
    assert mod1.show_viewport is True
    assert mod2.show_viewport is True
    print("PASS: Initial state verified")

    # --- Test 2: Enable Animate Mode on Character 1 ---
    bpy.context.view_layer.objects.active = arm1
    arm1.select_set(True)
    arm2.select_set(False)

    success = set_genshin_animate_mode(True, arm=arm1, context=bpy.context)
    assert success is True, "set_genshin_animate_mode should return True"
    assert is_genshin_animate_mode(arm1), "Char1 should be in animate mode"
    assert not is_genshin_animate_mode(arm2), "Char2 should NOT be in animate mode"

    # Verify Char1 meshes have low materials and outline modifier hidden
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat_Low", f"Expected Char1_Body_Mat_Low, got {mesh1.material_slots[0].material.name}"
    assert mod1.show_viewport is False, "Char1 outline modifier should be hidden"

    # Verify Char2 is completely untouched!
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat", f"Char2 material was modified to {mesh2.material_slots[0].material.name}!"
    assert mod2.show_viewport is True, "Char2 outline modifier was unexpectedly hidden!"
    print("PASS: Animate mode strictly applied to Char1, Char2 remained untouched")

    # --- Test 3: Toggle Animate Mode on Character 2 via Operator ---
    bpy.context.view_layer.objects.active = arm2
    arm1.select_set(False)
    arm2.select_set(True)

    res = bpy.ops.genshin.toggle_animate_mode()
    assert res == {'FINISHED'}, f"Operator failed with {res}"

    assert is_genshin_animate_mode(arm1), "Char1 should still be in animate mode"
    assert is_genshin_animate_mode(arm2), "Char2 should now be in animate mode"
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat_Low"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat_Low"
    assert mod1.show_viewport is False
    assert mod2.show_viewport is False
    print("PASS: Char2 toggled via operator independently while Char1 remained in animate mode")

    # --- Test 4: Disable Animate Mode on Character 1 via Operator ---
    bpy.context.view_layer.objects.active = arm1
    arm1.select_set(True)
    arm2.select_set(False)

    res = bpy.ops.genshin.toggle_animate_mode()
    assert res == {'FINISHED'}, f"Operator failed with {res}"

    assert not is_genshin_animate_mode(arm1), "Char1 should now be disabled from animate mode"
    assert is_genshin_animate_mode(arm2), "Char2 should still be in animate mode"
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat", f"Expected Char1_Body_Mat, got {mesh1.material_slots[0].material.name}"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat_Low"
    assert mod1.show_viewport is True, "Char1 outline modifier should be visible again"
    assert mod2.show_viewport is False, "Char2 outline modifier should remain hidden"
    print("PASS: Char1 disabled back to full shaders while Char2 stayed in animate mode")

    # --- Test 5: Selecting a character mesh instead of armature ---
    bpy.context.view_layer.objects.active = mesh1
    mesh1.select_set(True)
    arm1.select_set(False)

    # Toggling with mesh1 active should target Char1
    res = bpy.ops.genshin.toggle_animate_mode()
    assert res == {'FINISHED'}
    assert is_genshin_animate_mode(arm1), "Char1 should be in animate mode when toggling via mesh selection"
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat_Low"
    print("PASS: Mesh selection correctly resolves character armature")

    print("\nALL GENSHIN ANIMATE MODE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
