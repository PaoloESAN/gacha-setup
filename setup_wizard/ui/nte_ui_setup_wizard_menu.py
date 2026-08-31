# Author: Gacha Setup (NTE Integration)

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


class NTE_PT_Basic_Setup_Wizard_UI_Layout(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "NTE_PT_UI_Basic_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        # Step 1: Set Up Character button
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
            operator_context="INVOKE_DEFAULT",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )

        # Step 2: Set Up Materials button
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
            operator_context="INVOKE_DEFAULT",
        )


        # Step 3: Setup Outlines button
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_outlines",
            "Setup Outlines",
            icon="GEOMETRY_NODES",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )

        # Step 4: Rig Character button
        OperatorFactory.create_rig_character_ui(sub_layout)

        # Step 5: Finish Setup button
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.finish_setup",
            "Finish Setup",
            icon="CHECKMARK",
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
        sub_layout.label(text="File > Import > Unreal Model (.uemodel)", icon="INFO")


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


class NTE_PT_UI_Outlines_Menu(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "3. Outlines"
    bl_parent_id = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.set_up_outlines",
            "Setup Outlines",
            "GEOMETRY_NODES",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )


class NTE_PT_UI_Rig_Character_Menu(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "4. Rig Character"
    bl_parent_id = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create_rig_character_ui(sub_layout)
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.apply_hair_clothes_physics",
            "Apply Hair & Clothes Physics",
            "PHYSICS",
        )


class NTE_PT_UI_Finish_Setup_Menu(Panel, NevernessToEvernessUIRenderChecker):
    bl_label = "5. Finish Setup"
    bl_parent_id = "NTE_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "genshin.setup_head_driver",
            "Set Up Head Driver",
            "CONSTRAINT",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_color_management_to_standard",
            "Set Color Mgmt to Standard",
            "COLOR",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.set_up_screen_space_reflections",
            "Enable Raytracing & SSR",
            "SCENE",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )
        OperatorFactory.create(
            sub_layout,
            "neverness_to_everness.setup_compositor_nodes",
            "Setup Compositor Nodes",
            "NODE_COMPOSITING",
            game_type=GameType.NEVERNESS_TO_EVERNESS.name,
        )


classes = (
    NTE_PT_Setup_Wizard_UI_Layout,
    NTE_PT_Basic_Setup_Wizard_UI_Layout,
    NTE_PT_Advanced_Setup_Wizard_UI_Layout,
    NTE_PT_UI_Character_Model_Menu,
    NTE_PT_UI_Materials_Menu,
    NTE_PT_UI_Outlines_Menu,
    NTE_PT_UI_Rig_Character_Menu,
    NTE_PT_UI_Finish_Setup_Menu,
)




def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
