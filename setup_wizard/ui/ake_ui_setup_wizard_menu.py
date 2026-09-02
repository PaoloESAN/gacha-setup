# Arknights: Endfield UI Setup Wizard Menu
# Adapted for Gacha Setup Wizard

import bpy
from bpy.types import Panel

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import ArknightsEndfieldUIRenderChecker
from setup_wizard.ui.gi_ui_setup_wizard_menu import OperatorFactory


class AKE_PT_Setup_Wizard_UI_Layout(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "Arknights: Endfield Setup Wizard"
    bl_idname = "AKE_PT_Setup_Wizard_UI_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    def draw(self, context):
        layout = self.layout

        sub_layout = layout.box()
        run_entire_setup_column = sub_layout.column()
        OperatorFactory.create(
            run_entire_setup_column,
            "arknights_endfield.setup_wizard_ui",
            "Run Entire Setup",
            "PLAY",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
            operator_context="INVOKE_DEFAULT",
        )

        settings_box = layout.box()
        settings_header = settings_box.row()
        settings_header.label(text="Setup Settings", icon="PREFERENCES")

        settings_col = settings_box.column()
        props = context.scene.character_rigger_props
        enable_physics = getattr(props, "enable_hair_clothes_physics", getattr(props, "enable_hair_dress_physics", False))
        settings_col.prop(props, "enable_hair_clothes_physics", text="Hair & Clothes Physics")
        sliders_col = settings_col.column()
        sliders_col.active = enable_physics
        sliders_col.prop(props, "hair_physics_influence", text="Hair", slider=True)
        sliders_col.prop(props, "clothes_physics_influence", text="Clothes", slider=True)
        settings_col.prop(props, "disable_rigging", text="Disable Rigging")


class AKE_PT_Basic_Setup_Wizard_UI_Layout(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "AKE_PT_UI_Basic_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        # Step 1: Set Up Character
        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
            operator_context="INVOKE_DEFAULT",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )

        # Step 2: Set Up Materials
        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
            operator_context="INVOKE_DEFAULT",
        )

        # Step 3: Setup Outlines
        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.set_up_outlines",
            "Setup Outlines",
            icon="GEOMETRY_NODES",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )

        # Step 4: Rig Character
        OperatorFactory.create_rig_character_ui(sub_layout, game_type=GameType.ARKNIGHTS_ENDFIELD.name)

        # Step 5: Finish Setup
        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.finish_setup",
            "Finish Setup",
            icon="CHECKMARK",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )


class AKE_PT_Advanced_Setup_Wizard_UI_Layout(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "Advanced Setup"
    bl_idname = "AKE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        pass


class AKE_PT_UI_Character_Model_Menu(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "1. Character Model"
    bl_parent_id = "AKE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)
        sub_layout.label(text="Import FBX model & Smooth Normals", icon="INFO")
        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.set_up_character",
            "Import Character Model",
            "IMPORT",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
            operator_context="INVOKE_DEFAULT",
        )


class AKE_PT_UI_Materials_Menu(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "2. Materials"
    bl_parent_id = "AKE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "genshin.import_materials",
            "Import Shader Materials",
            "IMPORT",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )

        OperatorFactory.create(
            sub_layout,
            "genshin.replace_default_materials",
            "Replace Default Materials",
            "MATERIAL",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )

        OperatorFactory.create(
            sub_layout,
            "genshin.import_textures",
            "Import Character Textures",
            "TEXTURE",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
            operator_context="INVOKE_DEFAULT",
        )


class AKE_PT_UI_Outlines_Menu(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "3. Outlines"
    bl_parent_id = "AKE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)
        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.set_up_outlines",
            "Setup Outlines",
            "GEOMETRY_NODES",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )


class AKE_PT_UI_Rig_Character_Menu(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "4. Rig Character"
    bl_parent_id = "AKE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)
        OperatorFactory.create_rig_character_ui(sub_layout, game_type=GameType.ARKNIGHTS_ENDFIELD.name)


class AKE_PT_UI_Finish_Setup_Menu(Panel, ArknightsEndfieldUIRenderChecker):
    bl_label = "5. Finish Setup"
    bl_parent_id = "AKE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.setup_compositor_nodes",
            "Setup Compositor Nodes",
            "NODE_COMPOSITING",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )

        OperatorFactory.create(
            sub_layout,
            "arknights_endfield.finish_setup",
            "Finish Setup",
            "CHECKMARK",
            game_type=GameType.ARKNIGHTS_ENDFIELD.name,
        )
