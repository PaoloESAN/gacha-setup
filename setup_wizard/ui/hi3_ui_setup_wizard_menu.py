# Author: Gacha Setup (HI3 Integration)
# Honkai Impact 3rd Setup Wizard Menu for Old Setup & Sub-panels

import bpy
from bpy.types import Panel, UILayout

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import HonkaiImpact3rdUIRenderChecker


class HI3_PT_Setup_Wizard_UI_Layout(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Honkai Impact 3rd Setup Wizard"
    bl_idname = "HI3_PT_Setup_Wizard_UI_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"

    @classmethod
    def poll(cls, context):
        return False

    def draw(self, context):
        pass


class HI3_PT_Basic_Setup_Wizard_UI_Layout(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "HI3_PT_UI_Basic_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"
    bl_parent_id = "CSW_PT_Old_Setup_UI_Layout"
    bl_order = 1
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        OperatorFactory.create(
            sub_layout,
            "honkai_impact_3rd.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        OperatorFactory.create(
            sub_layout,
            "honkai_impact_3rd.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        if bpy.app.version >= (3, 3, 0):
            OperatorFactory.create(
                sub_layout,
                "honkai_impact_3rd.set_up_outlines",
                "Set Up Outlines",
                icon="GEOMETRY_NODES",
                game_type=GameType.HONKAI_IMPACT_3RD.name,
            )
        else:
            layout.label(text="(Outlines Disabled < v3.3.0)")
        OperatorFactory.create(
            sub_layout,
            "genshin.fix_transformations",
            "Fix Transformations",
            "OBJECT_DATA",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        OperatorFactory.create_rig_character_ui(sub_layout)
        OperatorFactory.create(
            sub_layout,
            "honkai_impact_3rd.finish_setup",
            "Finish Setup",
            icon="CHECKMARK",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )


class HI3_PT_Advanced_Setup_Wizard_UI_Layout(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Advanced Setup"
    bl_idname = "HI3_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"
    bl_parent_id = "CSW_PT_Old_Setup_UI_Layout"
    bl_order = 2
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        pass


class HI3_PT_UI_Character_Model_Menu(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Set Up Character Menu"
    bl_idname = "HI3_PT_UI_Character_Model_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HI3_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            "genshin.import_model",
            "Import Character Model",
            "OUTLINER_OB_ARMATURE",
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.delete_empties",
            "Delete Empties",
            "TRASH",
        )


class HI3_PT_UI_Materials_Menu(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Set Up Materials Menu"
    bl_idname = "HI3_PT_UI_Materials_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HI3_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            "genshin.import_materials",
            "Import HI3 Materials",
            "MATERIAL",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.replace_default_materials",
            "Replace Default Materials",
            "ARROW_LEFTRIGHT",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.import_textures",
            "Import Character Textures",
            "TEXTURE",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )


class HI3_PT_UI_Outlines_Menu(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Set Up Outlines Menu"
    bl_idname = "HI3_PT_UI_Outlines_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HI3_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        if bpy.app.version >= (3, 3, 0):
            OperatorFactory.create(
                sub_layout,
                "genshin.import_outlines",
                "Import Outlines",
                "FILE_FOLDER",
                game_type=GameType.HONKAI_IMPACT_3RD.name,
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.setup_geometry_nodes",
                "Set Up Geometry Nodes",
                "GEOMETRY_NODES",
                game_type=GameType.HONKAI_IMPACT_3RD.name,
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.import_outline_lightmaps",
                "Import Outline Lightmaps",
                "FILE_FOLDER",
                game_type=GameType.HONKAI_IMPACT_3RD.name,
            )
        else:
            layout.label(text="(Outlines Disabled < v3.3.0)")


class HI3_PT_UI_Character_Rig_Setup_Menu(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Character Rig Menu"
    bl_idname = "HI3_PT_Rigify_Setup_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HI3_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()
        box = sub_layout.box()

        character_rigger_props = context.scene.character_rigger_props

        OperatorFactory.create_rig_character_ui(box)
        OperatorFactory.create(
            box,
            "honkai_impact_3rd.setup_face_rig",
            "Set Up Face Rig",
            "FACE_MAPS",
        )
        OperatorFactory.create(
            box,
            "hoyoverse.apply_hair_clothes_physics",
            "Apply Hair & Clothes Physics",
            "PHYSICS",
        )

        box = sub_layout.box()
        box.label(text="Settings")

        col = box.column()
        OperatorFactory.create(
            col,
            "hoyoverse.rootshape_filepath_setter",
            "Override RootShape Filepath",
            "FILE_FOLDER",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
            operator_context="INVOKE_DEFAULT",
        )
        col = box.column()
        col.prop(character_rigger_props, "allow_arm_ik_stretch")
        col.prop(character_rigger_props, "allow_leg_ik_stretch")
        col.prop(character_rigger_props, "use_arm_ik_poles")
        col.prop(character_rigger_props, "use_leg_ik_poles")
        col.prop(character_rigger_props, "add_children_of_constraints")
        col.prop(character_rigger_props, "use_head_tracker")
        enable_physics = getattr(
            character_rigger_props,
            "enable_hair_clothes_physics",
            getattr(character_rigger_props, "enable_hair_dress_physics", False),
        )
        col.prop(character_rigger_props, "enable_hair_clothes_physics", text="Hair & Clothes Physics")
        if enable_physics:
            sliders_col = col.column()
            sliders_col.prop(character_rigger_props, "hair_physics_influence", text="Hair", slider=True)
            sliders_col.prop(character_rigger_props, "clothes_physics_influence", text="Clothes", slider=True)


class HI3_PT_UI_Finish_Setup_Menu(Panel, HonkaiImpact3rdUIRenderChecker):
    bl_label = "Finish Setup Menu"
    bl_idname = "HI3_PT_UI_Misc_Setup_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HI3_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            "genshin.setup_head_driver",
            "Set Up Head Driver",
            "CONSTRAINT",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_color_management_to_standard",
            "Set Color Mgmt to Standard",
            "SCENE",
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.delete_specific_objects",
            "Clean Up Extra Meshes",
            "TRASH",
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.rename_shader_materials",
            "Rename Shader Materials",
            "GREASEPENCIL",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_up_armtwist_bone_constraints",
            "Set Up ArmTwist Bone Constraints",
            "CONSTRAINT_BONE",
        )


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
    def create_rig_character_ui(ui_object: UILayout):
        expy_kit_installed = any("expy" in k.lower() for k in bpy.context.preferences.addons.keys())
        rigify_installed = any("rigify" in k.lower() for k in bpy.context.preferences.addons.keys())

        column = ui_object.column()
        column.enabled = True if expy_kit_installed and rigify_installed else False
        OperatorFactory.create(
            column,
            "hoyoverse.set_up_character_rig",
            "Rig Character",
            "OUTLINER_OB_ARMATURE",
            game_type=GameType.HONKAI_IMPACT_3RD.name,
        )
        if not column.enabled:
            column = ui_object.column()
            if not expy_kit_installed:
                column.label(text="ExpyKit required", icon="ERROR")
            if not rigify_installed:
                column.label(text="Rigify required", icon="ERROR")


classes = (
    HI3_PT_Setup_Wizard_UI_Layout,
    HI3_PT_Basic_Setup_Wizard_UI_Layout,
    HI3_PT_Advanced_Setup_Wizard_UI_Layout,
    HI3_PT_UI_Character_Model_Menu,
    HI3_PT_UI_Materials_Menu,
    HI3_PT_UI_Outlines_Menu,
    HI3_PT_UI_Character_Rig_Setup_Menu,
    HI3_PT_UI_Finish_Setup_Menu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
