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
    register as register_animate_mode,
)
from setup_wizard.wuwa_operations import (
    set_animate_mode as set_wuwa_animate_mode,
)
from setup_wizard.ui.character_settings_utils import GACHA_GAME_KEY


def run_tests():
    print("=== Running Genshin & WuWa Animate Mode Fake User Tests ===")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        register_animate_mode()
    except Exception:
        pass

    # 1. Setup Genshin character
    arm_data = bpy.data.armatures.new("GI_Char_ArmData")
    arm = bpy.data.objects.new("GI_Char_Rig", arm_data)
    arm[GACHA_GAME_KEY] = "GENSHIN_IMPACT"
    bpy.context.scene.collection.objects.link(arm)

    mesh_data = bpy.data.meshes.new("GI_Char_MeshData")
    mesh = bpy.data.objects.new("GI_Char_Body", mesh_data)
    mesh.parent = arm
    bpy.context.scene.collection.objects.link(mesh)

    orig_mat = bpy.data.materials.new("GI_Char_Body_Mat")
    orig_mat.use_fake_user = False
    mesh.data.materials.append(orig_mat)

    # Initial state
    assert orig_mat.use_fake_user is False
    assert mesh.material_slots[0].material == orig_mat

    # --- Test 1: Enable Animate Mode sets fake user on original material ---
    set_genshin_animate_mode(True, arm=arm)

    low_mat = mesh.material_slots[0].material
    assert low_mat.name == "GI_Char_Body_Mat_Low"
    assert orig_mat.use_fake_user is True, "Original material MUST have fake user while in Animate Mode!"
    assert low_mat.use_fake_user is False, "Low material should NOT have fake user!"
    print("PASS: Original material has use_fake_user=True upon entering Animate Mode")

    # --- Test 2: Disable Animate Mode restores original material and clears fake user on low material ---
    set_genshin_animate_mode(False, arm=arm)
    assert mesh.material_slots[0].material == orig_mat
    assert low_mat.use_fake_user is False, "Low material must not have fake user after disabling"
    print("PASS: Disabling Animate Mode restored original material and cleared fake user on low material")

    # --- Test 3: WuWa Animate Mode also sets fake user on original material ---
    ww_mesh_data = bpy.data.meshes.new("WW_MeshData")
    ww_mesh = bpy.data.objects.new("WW_Body", ww_mesh_data)
    bpy.context.scene.collection.objects.link(ww_mesh)

    ww_orig_mat = bpy.data.materials.new("WW_Body_Mat")
    ww_orig_mat.use_fake_user = False
    ww_mesh.data.materials.append(ww_orig_mat)

    set_wuwa_animate_mode(True)
    ww_low_mat = ww_mesh.material_slots[0].material
    assert ww_low_mat.name == "WW_Body_Mat_Low"
    assert ww_orig_mat.use_fake_user is True, "Original WuWa material MUST have fake user while in Animate Mode!"
    assert ww_low_mat.use_fake_user is False, "Low material should NOT have fake user!"
    print("PASS: WuWa original material has use_fake_user=True upon entering Animate Mode")

    set_wuwa_animate_mode(False)
    assert ww_mesh.material_slots[0].material == ww_orig_mat
    assert ww_low_mat.use_fake_user is False, "WuWa low material must not have fake user after disabling"
    print("PASS: Disabling WuWa Animate Mode restored original material and cleared fake user on low material")

    print("\nALL ANIMATE MODE FAKE USER TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
