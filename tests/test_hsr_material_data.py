"""Unit test for HSR Material Data JSON import and outline colors.

Verifies:
1. Body part deduction handles all HSR naming conventions (Firefly, Stelle, Cerydra, Ashveil, etc.).
2. Body outline materials (e.g. Body_D Outlines, Body_S Outlines, Body_Trans Outlines)
   correctly receive colors from JSON instead of remaining default black (0, 0, 0, 1).
3. Outline socket indexing (1-based vs 0-based) resolves properly.
"""

import os
import sys
import unittest
import bpy
from pathlib import PurePosixPath

from setup_wizard.import_order import set_active_character_directory
from setup_wizard.material_data_import_setup.game_material_data_importers import HonkaiStarRailMaterialDataImporter


class TestHSRMaterialDataImport(unittest.TestCase):
    def test_deduce_hsr_body_part(self):
        cases = {
            "Cerydra_00_Mat_Body_D.json": "Body_D",
            "Cerydra_00_Mat_Body_S.json": "Body_S",
            "Cerydra_00_Mat_Crystal.json": "Crystal",
            "Cerydra_00_Mat_Face.json": "Face",
            "Cerydra_00_Mat_Hair.json": "Hair",
            "Cerydra_00_Mat_Weapon.json": "Weapon",
            "Cerydra_00_Mat_Weapon_Crystal.json": "Weapon_Crystal",
            "Mat_EyeShadow_00.json": "EyeShadow",
            "Mat_FaceMask.json": "FaceMask",
            "Ashveil_00_Mat_Body_D.json": "Body_D",
            "Ashveil_00_Mat_Body_S.json": "Body_S",
            "Ashveil_00_Mat_Body_Trans.json": "Body_Trans",
            "Avatar_PlayerGirl_Body_034_000_000_Mat_D.json": "Body_D",
            "Avatar_PlayerGirl_Body_034_000_000_Mat_S.json": "Body_S",
            "Avatar_PlayerGirl_Body_034_000_000_Mat_Trans.json": "Body_Trans",
            "Avatar_PlayerGirl_Face_034_000_000_Mat.json": "Face",
            "Avatar_PlayerGirl_Hair_034_000_000_Mat.json": "Hair",
            "Avatar_PlayerGirl_Weapon40_042_000_000_Mat.json": "Weapon",
            "Feixiao_00_Mat_Coat.json": "Coat",
            "Sampo_00_Mat_Handbag.json": "Handbag",
            "Sparkle_00_Mat_Kendama.json": "Kendama",
            "Avatar_DanHeng_00_Mat_Body1.json": "Body1",
            "Avatar_DanHeng_00_Mat_Body2.json": "Body2",
            "Avatar_DanHeng_00_Mat_Body2_Trans.json": "Body2_Trans",
            "Avatar_DanHeng_00_Mat_Body3.json": "Body3",
        }

        for filename, expected in cases.items():
            result = HonkaiStarRailMaterialDataImporter.deduce_hsr_body_part(filename)
            self.assertEqual(result, expected, f"Failed for {filename}: expected {expected}, got {result}")
        print("✔ HSR body part deduction verified for all test cases!")

    def test_end_to_end_ashveil_outline_colors(self):
        char_dir = os.path.abspath('chars/hsr/ashveil-hunt')
        if not os.path.isdir(char_dir):
            self.skipTest(f"Character directory not found: {char_dir}")

        set_active_character_directory(char_dir)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.genshin.import_materials(game_type='HONKAI_STAR_RAIL')
        fbx = [f for f in os.listdir(char_dir) if f.endswith('.fbx')][0]
        bpy.ops.import_scene.fbx(filepath=os.path.join(char_dir, fbx))
        bpy.ops.genshin.replace_default_materials(game_type='HONKAI_STAR_RAIL')
        bpy.ops.genshin.import_outlines(game_type='HONKAI_STAR_RAIL')
        bpy.ops.genshin.setup_geometry_nodes(game_type='HONKAI_STAR_RAIL')
        bpy.ops.genshin.import_material_data(game_type='HONKAI_STAR_RAIL')

        black = (0.0, 0.0, 0.0, 1.0)

        # Check Body_D Outlines
        mat_d = bpy.data.materials.get('StellarToon - Body_D Outlines')
        self.assertIsNotNone(mat_d, "StellarToon - Body_D Outlines should exist")
        node_d = mat_d.node_tree.nodes.get('Group.006')
        col1_d = tuple(round(v, 4) for v in node_d.inputs['Outline Color 1'].default_value[:])
        self.assertNotEqual(col1_d, black, "Body_D Outline Color 1 should NOT be black")
        print(f"✔ Ashveil Body_D Outline Color 1 verified non-black: {col1_d}")

        # Check Body_S Outlines
        mat_s = bpy.data.materials.get('StellarToon - Body_S Outlines')
        self.assertIsNotNone(mat_s, "StellarToon - Body_S Outlines should exist")
        node_s = mat_s.node_tree.nodes.get('Group.006')
        col1_s = tuple(round(v, 4) for v in node_s.inputs['Outline Color 1'].default_value[:])
        self.assertNotEqual(col1_s, black, "Body_S Outline Color 1 should NOT be black")
        print(f"✔ Ashveil Body_S Outline Color 1 verified non-black: {col1_s}")

        # Check Face Outlines
        mat_face = bpy.data.materials.get('StellarToon - Face Outlines')
        self.assertIsNotNone(mat_face, "StellarToon - Face Outlines should exist")
        node_face = mat_face.node_tree.nodes.get('Group.006')
        col1_face = tuple(round(v, 4) for v in node_face.inputs['Outline Color 1'].default_value[:])
        self.assertNotEqual(col1_face, black, "Face Outline Color 1 should NOT be black")
        print(f"✔ Ashveil Face Outline Color 1 verified non-black: {col1_face}")

        # Check Hair Outlines
        mat_hair = bpy.data.materials.get('StellarToon - Hair Outlines')
        self.assertIsNotNone(mat_hair, "StellarToon - Hair Outlines should exist")
        node_hair = mat_hair.node_tree.nodes.get('Group.006')
        col1_hair = tuple(round(v, 4) for v in node_hair.inputs['Outline Color 1'].default_value[:])
        self.assertNotEqual(col1_hair, black, "Hair Outline Color 1 should NOT be black")
        print(f"✔ Ashveil Hair Outline Color 1 verified non-black: {col1_hair}")

    def test_end_to_end_cerydra_outline_colors(self):
        char_dir = os.path.abspath('chars/hsr/Art_Cerydra_00')
        if not os.path.isdir(char_dir):
            self.skipTest(f"Character directory not found: {char_dir}")

        set_active_character_directory(char_dir)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.genshin.import_materials(game_type='HONKAI_STAR_RAIL')
        fbx = [f for f in os.listdir(char_dir) if f.endswith('.fbx')][0]
        bpy.ops.import_scene.fbx(filepath=os.path.join(char_dir, fbx))
        bpy.ops.genshin.replace_default_materials(game_type='HONKAI_STAR_RAIL')
        bpy.ops.genshin.import_outlines(game_type='HONKAI_STAR_RAIL')
        bpy.ops.genshin.setup_geometry_nodes(game_type='HONKAI_STAR_RAIL')
        bpy.ops.genshin.import_material_data(game_type='HONKAI_STAR_RAIL')

        black = (0.0, 0.0, 0.0, 1.0)

        # Check Body_D Outlines
        mat_d = bpy.data.materials.get('StellarToon - Body_D Outlines')
        self.assertIsNotNone(mat_d, "StellarToon - Body_D Outlines should exist")
        node_d = mat_d.node_tree.nodes.get('Group.006')
        col1_d = tuple(round(v, 4) for v in node_d.inputs['Outline Color 1'].default_value[:])
        self.assertNotEqual(col1_d, black, "Cerydra Body_D Outline Color 1 should NOT be black")
        print(f"✔ Cerydra Body_D Outline Color 1 verified non-black: {col1_d}")

        # Check Body_S Outlines
        mat_s = bpy.data.materials.get('StellarToon - Body_S Outlines')
        self.assertIsNotNone(mat_s, "StellarToon - Body_S Outlines should exist")
        node_s = mat_s.node_tree.nodes.get('Group.006')
        col1_s = tuple(round(v, 4) for v in node_s.inputs['Outline Color 1'].default_value[:])
        self.assertNotEqual(col1_s, black, "Cerydra Body_S Outline Color 1 should NOT be black")
        print(f"✔ Cerydra Body_S Outline Color 1 verified non-black: {col1_s}")


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
