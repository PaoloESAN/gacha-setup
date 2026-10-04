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
    _get_low_material,
    register as register_animate_mode,
    ANIMATE_MODE_SCENE_KEY,
)
from setup_wizard.ui.character_settings_utils import GACHA_GAME_KEY


def run_tests():
    print("=== Running Genshin Animate Mode Legacy Fallback Tests ===")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        register_animate_mode()
    except Exception:
        pass

    # 1. Setup Character 1
    arm1_data = bpy.data.armatures.new("Char1_ArmatureData")
    arm1 = bpy.data.objects.new("Char1_Rig", arm1_data)
    arm1[GACHA_GAME_KEY] = "GENSHIN_IMPACT"
    bpy.context.scene.collection.objects.link(arm1)

    mesh1_data = bpy.data.meshes.new("Char1_MeshData")
    mesh1 = bpy.data.objects.new("Char1_Body", mesh1_data)
    mesh1.parent = arm1
    bpy.context.scene.collection.objects.link(mesh1)

    mat1 = bpy.data.materials.new("Char1_Body_Mat")
    mesh1.data.materials.append(mat1)
    ng1 = bpy.data.node_groups.new("GI_Outlines_1", 'GeometryNodeTree')
    mod1 = mesh1.modifiers.new("Outlines", 'NODES')
    mod1.node_group = ng1
    mod1.show_viewport = True

    # 2. Setup Character 2
    arm2_data = bpy.data.armatures.new("Char2_ArmatureData")
    arm2 = bpy.data.objects.new("Char2_Rig", arm2_data)
    arm2[GACHA_GAME_KEY] = "GENSHIN_IMPACT"
    bpy.context.scene.collection.objects.link(arm2)

    mesh2_data = bpy.data.meshes.new("Char2_MeshData")
    mesh2 = bpy.data.objects.new("Char2_Body", mesh2_data)
    mesh2.parent = arm2
    bpy.context.scene.collection.objects.link(mesh2)

    mat2 = bpy.data.materials.new("Char2_Body_Mat")
    mesh2.data.materials.append(mat2)
    ng2 = bpy.data.node_groups.new("GI_Outlines_2", 'GeometryNodeTree')
    mod2 = mesh2.modifiers.new("Outlines", 'NODES')
    mod2.node_group = ng2
    mod2.show_viewport = True

    # 3. Setup a non-character prop (e.g. sword / table) with NO armature
    prop_data = bpy.data.meshes.new("Prop_MeshData")
    prop = bpy.data.objects.new("Prop_Sword", prop_data)
    bpy.context.scene.collection.objects.link(prop)

    mat_prop = bpy.data.materials.new("Prop_Sword_Mat")
    prop.data.materials.append(mat_prop)
    ng_prop = bpy.data.node_groups.new("GI_Outlines_Prop", 'GeometryNodeTree')
    mod_prop = prop.modifiers.new("Outlines", 'NODES')
    mod_prop.node_group = ng_prop
    mod_prop.show_viewport = True

    # --- Simulate Legacy State (from version prior to fix where animated mode was global) ---
    # In the old version:
    # 1. scene["gi_animate_mode"] = True
    # 2. All meshes in the scene were converted to _Low materials
    # 3. All outline modifiers were hidden
    # 4. Neither arm1 nor arm2 had "gi_animate_mode" set
    bpy.context.scene[ANIMATE_MODE_SCENE_KEY] = True

    low1 = _get_low_material(mat1)
    mesh1.material_slots[0].material = low1
    mod1.show_viewport = False

    low2 = _get_low_material(mat2)
    mesh2.material_slots[0].material = low2
    mod2.show_viewport = False

    low_prop = _get_low_material(mat_prop)
    prop.material_slots[0].material = low_prop
    mod_prop.show_viewport = False

    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat_Low"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat_Low"
    assert prop.material_slots[0].material.name == "Prop_Sword_Mat_Low"
    assert ANIMATE_MODE_SCENE_KEY not in arm1
    assert ANIMATE_MODE_SCENE_KEY not in arm2

    # --- Test A: Disabling animate mode on arm1 automatically performs fallback cleanup of all legacy objects ---
    bpy.context.view_layer.objects.active = arm1
    arm1.select_set(True)
    arm2.select_set(False)

    # Toggling arm1 restores Char1 AND automatically cleans up Char2 and Prop from legacy state
    res = bpy.ops.genshin.toggle_animate_mode()
    assert res == {'FINISHED'}

    assert not is_genshin_animate_mode(arm1), "Char1 animate mode should be False"
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat", "Char1 material should be restored"
    assert mod1.show_viewport is True, "Char1 outline should be restored"

    # Fallback verification: Char2 and Prop MUST also be restored because they were legacy unowned _Low!
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat", f"Char2 material remained in _Low: {mesh2.material_slots[0].material.name}"
    assert mod2.show_viewport is True, "Char2 outline should be restored by fallback"
    assert prop.material_slots[0].material.name == "Prop_Sword_Mat", f"Prop remained in _Low: {prop.material_slots[0].material.name}"
    assert mod_prop.show_viewport is True, "Prop outline should be restored by fallback"
    print("PASS Test A: Disabling Animate Mode on arm1 automatically cleaned up all legacy _Low objects")

    # --- Test B: Verify modern per-character isolation is still preserved! ---
    # In the modern workflow:
    # 1. Enable arm1
    set_genshin_animate_mode(True, arm=arm1)
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat_Low"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat"
    assert prop.material_slots[0].material.name == "Prop_Sword_Mat"

    # 2. Enable arm2 explicitly (modern per-character)
    set_genshin_animate_mode(True, arm=arm2)
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat_Low"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat_Low"

    # 3. Disable arm1: arm2 MUST NOT be affected because arm2 explicitly has arm2["gi_animate_mode"] = True!
    set_genshin_animate_mode(False, arm=arm1)
    assert mesh1.material_slots[0].material.name == "Char1_Body_Mat", "Char1 should be restored"
    assert mesh2.material_slots[0].material.name == "Char2_Body_Mat_Low", "Char2 MUST remain in Animate Mode"
    assert mod2.show_viewport is False, "Char2 outline must remain hidden"
    print("PASS Test B: Modern per-character animate mode isolation remains 100% intact")

    print("\nALL LEGACY FALLBACK TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
