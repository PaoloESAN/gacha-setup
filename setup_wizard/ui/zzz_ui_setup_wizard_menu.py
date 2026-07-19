# Author: michael-gh1 (adapted for ZZZ)

import bpy
from bpy.types import Panel, UILayout

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import ZenlessZoneZeroUIRenderChecker


class ZZZ_PT_Setup_Wizard_UI_Layout(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "Zenless Zone Zero Setup Wizard"
    bl_idname = "ZZZ_PT_Setup_Wizard_UI_Layout"
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
            "zenless_zone_zero.setup_wizard_ui",
            "Run Entire Setup",
            "PLAY",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        expy_kit_installed = bpy.context.preferences.addons.get("Expy-Kit-main")
        rigify_installed = bpy.context.preferences.addons.get("rigify")

        if not expy_kit_installed or not rigify_installed:
            sub_layout.label(text="Rigging Disabled", icon="ERROR")

        settings_box = layout.box()
        settings_box.label(text="Global Settings", icon="WORLD")

        row = settings_box.row()
        row.prop(window_manager, "cache_enabled")
        OperatorFactory.create(
            row,
            "genshin.clear_cache_operator",
            "Clear Cache",
            "TRASH",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )


class ZZZ_PT_Basic_Setup_Wizard_UI_Layout(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "ZZZ_PT_UI_Basic_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        set_up_character_column = sub_layout.column()
        OperatorFactory.create(
            set_up_character_column,
            "zenless_zone_zero.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )

        OperatorFactory.create(
            sub_layout,
            "genshin.delete_empties",
            "Delete Empties",
            icon="TRASH",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )

        OperatorFactory.create(
            sub_layout,
            "zenless_zone_zero.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        if bpy.app.version >= (3, 3, 0):
            OperatorFactory.create(
                sub_layout,
                "zenless_zone_zero.set_up_outlines",
                "Set Up Outlines",
                icon="GEOMETRY_NODES",
                game_type=GameType.ZENLESS_ZONE_ZERO.name,
            )
        else:
            layout.label(text="(Outlines Disabled < v3.3.0)")

        OperatorFactory.create(
            sub_layout,
            "genshin.fix_transformations",
            "Fix Transformations",
            "OBJECT_DATA",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )

        OperatorFactory.create_rig_character_ui(sub_layout)

        OperatorFactory.create(
            sub_layout,
            "zenless_zone_zero.finish_setup",
            "Finish Setup",
            icon="CHECKMARK",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )


class ZZZ_PT_Advanced_Setup_Wizard_UI_Layout(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "Advanced Setup"
    bl_idname = "ZZZ_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout


class ZZZ_PT_UI_Character_Model_Menu(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "1. Character Model"
    bl_parent_id = "ZZZ_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "genshin.import_model",
            "Import Character Model",
            "IMPORT",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
            setup_mode="ADVANCED",
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.delete_empties",
            "Delete Empties",
            "TRASH",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )


class ZZZ_PT_UI_Materials_Menu(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "2. Materials"
    bl_parent_id = "ZZZ_PT_UI_Advanced_Setup_Layout"
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
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
            setup_mode="ADVANCED",
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.replace_default_materials",
            "Replace Default Materials",
            "MATERIAL",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.import_textures",
            "Import Character Textures",
            "TEXTURE",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )


class ZZZ_PT_UI_Outlines_Menu(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "3. Outlines"
    bl_parent_id = "ZZZ_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        if bpy.app.version >= (3, 3, 0):
            OperatorFactory.create(
                sub_layout,
                "genshin.import_outlines",
                "Import Outlines Node Group",
                "IMPORT",
                game_type=GameType.ZENLESS_ZONE_ZERO.name,
                setup_mode="ADVANCED",
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.setup_geometry_nodes",
                "Set Up Geometry Nodes",
                "GEOMETRY_NODES",
                game_type=GameType.ZENLESS_ZONE_ZERO.name,
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.import_outline_lightmaps",
                "Import Outline Lightmaps",
                "IMAGE_DATA",
                game_type=GameType.ZENLESS_ZONE_ZERO.name,
                setup_mode="ADVANCED",
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.import_material_data",
                "Import Outline Material Data",
                "ASSET_MANAGER",
                game_type=GameType.ZENLESS_ZONE_ZERO.name,
                setup_mode="ADVANCED",
            )
        else:
            layout.label(text="Outlines Disabled (< v3.3.0)")


class ZZZ_PT_UI_Finish_Setup_Menu(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "5. Finish Setup"
    bl_parent_id = "ZZZ_PT_UI_Advanced_Setup_Layout"
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
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_color_management_to_standard",
            "Set Color Management",
            "COLOR",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.delete_specific_objects",
            "Delete Helper Empties & Meshes",
            "TRASH",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.rename_shader_materials",
            "Rename Shader Materials",
            "FONT_DATA",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.join_meshes_on_armature",
            "Join Meshes on Armature",
            "LINKED",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )


class ZZZ_PT_UI_Character_Rig_Setup_Menu(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "4. Rigging"
    bl_parent_id = "ZZZ_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)
        OperatorFactory.create(
            sub_layout,
            "genshin.fix_transformations",
            "Fix Transformations",
            "OBJECT_DATA",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create_rig_character_ui(sub_layout)


class OperatorFactory:
    @staticmethod
    def create(
        ui_object: UILayout,
        operator: str,
        text: str,
        icon: str,
        operator_context="EXEC_DEFAULT",
        **kwargs,
    ):
        ui_object.operator_context = operator_context
        ui_object = ui_object.operator(
            operator=operator,
            text=text,
            icon=icon,
        )

        for key, value in kwargs.items():
            setattr(ui_object, key, value)

    @staticmethod
    def create_rig_character_ui(
        ui_object: UILayout,
    ):
        expy_kit_installed = bpy.context.preferences.addons.get("Expy-Kit-main")
        rigify_installed = bpy.context.preferences.addons.get("rigify")

        column = ui_object.column()
        column.enabled = True if expy_kit_installed and rigify_installed else False
        OperatorFactory.create(
            column,
            "hoyoverse.set_up_character_rig",
            "Rig Character",
            "OUTLINER_OB_ARMATURE",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        if not column.enabled:
            column = ui_object.column()
            if not expy_kit_installed:
                column.label(text="ExpyKit required", icon="ERROR")
            if not rigify_installed:
                column.label(text="Rigify required", icon="ERROR")
