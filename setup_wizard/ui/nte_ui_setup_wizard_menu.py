# Author: Gacha Blender Setup (NTE Integration)

import bpy
from bpy.types import Panel, UILayout

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import NevernessToEvernessUIRenderChecker
from setup_wizard.ui.gi_ui_setup_wizard_menu import OperatorFactory


class NTE_PT_Setup_Wizard_UI_Layout(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "Neverness to Everness Setup Wizard"
    bl_idname = "NTE_PT_Setup_Wizard_UI_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    def draw(self, context):
        layout = self.layout
        window_manager = context.window_manager

        sub_layout = layout.box()
        run_entire_setup_column = sub_layout.column()
        OperatorFactory.create(
            run_entire_setup_column,
            "neverness_to_everness.setup_wizard_ui",
            "Run Entire Setup",
            "PLAY",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
            operator_context="INVOKE_DEFAULT",
        )


        settings_box = layout.box()
        settings_box.label(text="Global Settings", icon="WORLD")

        row = settings_box.row()
        row.prop(window_manager, "cache_enabled")
        OperatorFactory.create(
            row,
            "genshin.clear_cache_operator",
            "Clear Cache",
            "TRASH",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )


class NTE_PT_Basic_Setup_Wizard_UI_Layout(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "NTE_PT_UI_Basic_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        # Step 1: Informative note about model import
        info_box = sub_layout.box()
        info_box.label(text="1. Import Model", icon="IMPORT")
        col = info_box.column(align=True)
        col.label(text="Import the model (.uemodel) yourself")
        col.label(text="using the free UE Format addon.")

        # Step 2: Set Up Materials button
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
            operator_context="INVOKE_DEFAULT",
        )


        # Step 3: Set Up Hair Specular button
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_hair_specular",
            "Set Up Hair Specular",
            icon="STRANDS",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )


class NTE_PT_Advanced_Setup_Wizard_UI_Layout(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "Advanced Setup"
    bl_idname = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout


class NTE_PT_UI_Character_Model_Menu(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "1. Character Model"
    bl_parent_id = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)
        sub_layout.label(text="Import the model (.uemodel)", icon="INFO")
        sub_layout.label(text="using the UE Format addon.")


class NTE_PT_UI_Materials_Menu(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "2. Materials"
    bl_parent_id = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "genshin.import_materials",
            "Import Materials",
            "IMPORT",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
            setup_mode="ADVANCED",
            operator_context="INVOKE_DEFAULT",
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.replace_default_materials",
            "Replace Default Materials",
            "MATERIAL",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.import_textures",
            "Import Character Textures",
            "TEXTURE",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
            operator_context="INVOKE_DEFAULT",
        )



class NTE_PT_UI_Hair_Specular_Menu(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "3. Hair Specular"
    bl_parent_id = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_hair_specular",
            "Set Up Hair Specular",
            "STRANDS",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )


classes = (
    NTE_PT_Setup_Wizard_UI_Layout,
    NTE_PT_Basic_Setup_Wizard_UI_Layout,
    NTE_PT_Advanced_Setup_Wizard_UI_Layout,
    NTE_PT_UI_Character_Model_Menu,
    NTE_PT_UI_Materials_Menu,
    NTE_PT_UI_Hair_Specular_Menu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
