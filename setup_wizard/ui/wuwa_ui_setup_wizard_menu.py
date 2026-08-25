# Based on Blender-WuWa-Character-Setup by @fnoji and @nytsjared
# Adapted for Gacha Setup by PaoloESAN
# Licensed under GPL-3.0-or-later

import bpy
from bpy.types import Panel, UILayout

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import WutheringWavesUIRenderChecker
from setup_wizard.ui.gi_ui_setup_wizard_menu import OperatorFactory


class WW_PT_Setup_Wizard_UI_Layout(Panel, WutheringWavesUIRenderChecker):
    bl_label = "Wuthering Waves Setup Wizard"
    bl_idname = "WW_PT_Setup_Wizard_UI_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    def draw(self, context):
        layout = self.layout

        sub_layout = layout.box()
        run_entire_setup_column = sub_layout.column()
        OperatorFactory.create(
            run_entire_setup_column,
            "wuthering_waves.setup_wizard_ui",
            "Run Entire Setup",
            "PLAY",
            game_type=GameType.WUTHERING_WAVES.name,
            operator_context="INVOKE_DEFAULT",
        )

        rigify_installed = bpy.context.preferences.addons.get('rigify')
        if not rigify_installed:
            sub_layout.label(text='Rigify Disabled / Missing', icon='ERROR')

        # Fast Animate Mode Switch
        anim_box = layout.box()
        anim_row = anim_box.row(align=True)
        is_anim = context.scene.get("ww_animate_mode", False)
        anim_row.operator(
            "wuthering_waves.toggle_animate_mode",
            text="Disable Animate Mode" if is_anim else "Enable Animate Mode",
            icon="SHADING_TEXTURE" if is_anim else "RESTRICT_RENDER_OFF"
        )


class WW_PT_Basic_Setup_Wizard_UI_Layout(Panel, WutheringWavesUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "WW_PT_UI_Basic_Setup_Layout"
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
            "wuthering_waves.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
            operator_context="INVOKE_DEFAULT",
            game_type=GameType.WUTHERING_WAVES.name,
        )

        # Step 2: Set Up Materials
        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.WUTHERING_WAVES.name,
            operator_context="INVOKE_DEFAULT",
        )

        # Step 3: Setup Outlines
        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.set_up_outlines",
            "Setup Outlines",
            icon="GEOMETRY_NODES",
            game_type=GameType.WUTHERING_WAVES.name,
        )

        # Step 4: Rig Character
        OperatorFactory.create_rig_character_ui(sub_layout, game_type=GameType.WUTHERING_WAVES.name)

        # Step 5: Finish Setup
        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.finish_setup",
            "Finish Setup",
            icon="CHECKMARK",
            game_type=GameType.WUTHERING_WAVES.name,
        )


class WW_PT_Advanced_Setup_Wizard_UI_Layout(Panel, WutheringWavesUIRenderChecker):
    bl_label = "Advanced Setup"
    bl_idname = "WW_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        pass


class WW_PT_UI_Character_Model_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "1. Character Model"
    bl_parent_id = "WW_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)
        sub_layout.label(text="Import .uemodel (UEFormat) or .fbx", icon="INFO")
        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.set_up_character",
            "Import Character Model",
            "IMPORT",
            game_type=GameType.WUTHERING_WAVES.name,
            operator_context="INVOKE_DEFAULT",
        )


class WW_PT_UI_Materials_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "2. Materials"
    bl_parent_id = "WW_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "genshin.import_materials",
            "Import Gustling Waters Shader",
            "IMPORT",
            game_type=GameType.WUTHERING_WAVES.name,
            setup_mode="ADVANCED",
            operator_context="INVOKE_DEFAULT",
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.replace_default_materials",
            "Replace Default Materials",
            "MATERIAL",
            game_type=GameType.WUTHERING_WAVES.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.import_textures",
            "Import Character Textures",
            "TEXTURE",
            game_type=GameType.WUTHERING_WAVES.name,
            operator_context="INVOKE_DEFAULT",
        )


class WW_PT_UI_Outlines_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "3. Outlines"
    bl_parent_id = "WW_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.set_up_outlines",
            "Setup Outlines",
            "GEOMETRY_NODES",
            game_type=GameType.WUTHERING_WAVES.name,
        )


class WW_PT_UI_Rig_Character_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "4. Rig Character"
    bl_parent_id = "WW_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create_rig_character_ui(sub_layout, game_type=GameType.WUTHERING_WAVES.name)
        sub_layout.separator()
        sub_layout.operator("wuthering_waves.create_face_panel", text="Create Face Rig Panel", icon="FACE_MAPS")


class WW_PT_UI_Finish_Setup_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "5. Finish Setup"
    bl_parent_id = "WW_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column(align=True)

        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.setup_head_driver",
            "Set Up Head Driver & Light Direction",
            "CONSTRAINT",
            game_type=GameType.WUTHERING_WAVES.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_color_management_to_standard",
            "Set Color Mgmt to Standard",
            "COLOR",
            game_type=GameType.WUTHERING_WAVES.name,
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.set_up_screen_space_reflections",
            "Enable SSR & Shadows",
            "SCENE",
            game_type=GameType.WUTHERING_WAVES.name,
        )
        OperatorFactory.create(
            sub_layout,
            "wuthering_waves.setup_compositor_nodes",
            "Set Up Compositing Nodes",
            "NODE_COMPOSITING",
            game_type=GameType.WUTHERING_WAVES.name,
        )


class WW_PT_UI_Appearance_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "Appearance Settings"
    bl_idname = "WW_PT_UI_Appearance_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Shading controls
        box = layout.box()
        box.label(text="Shading Adjustments", icon="SHADING_RENDERED")
        col = box.column(align=True)
        col.prop(scene, "ww_metallic_value", text="Metallics", slider=True)
        col.prop(scene, "ww_specular_value", text="Specular", slider=True)
        col.prop(scene, "ww_blush_value", text="Blush", slider=True)
        col.prop(scene, "ww_disgust_value", text="Disgust Shadow", slider=True)

        # Texture & Visual options
        box_tex = layout.box()
        box_tex.label(text="Texture & Effects", icon="TEXTURE")
        col_tex = box_tex.column(align=True)
        col_tex.prop(scene, "ww_tex_mode", text="Mode")
        col_tex.operator("wuthering_waves.fix_eye_uv", text="Fix Eye UV (UV2)", icon="UV")
        col_tex.separator()
        col_tex.operator("wuthering_waves.toggle_outlines", text="Toggle Outlines", icon="MOD_EDGESPLIT")
        col_tex.operator("wuthering_waves.toggle_hair_transparency", text="Toggle Hair Transparency", icon="GHOST_ENABLED")
        col_tex.operator("wuthering_waves.toggle_star_motion", text="Toggle Resonator Star", icon="LIGHT_SUN")


class WW_PT_UI_Lighting_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "Lighting & Colors"
    bl_idname = "WW_PT_UI_Lighting_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Lighting Preset", icon="LIGHT")
        col = box.column(align=True)
        col.prop(scene, "ww_light_mode", text="Mode")
        col.prop(scene, "ww_catch_shadows", text="Catch Shadows")
        col.prop(scene, "ww_shadow_transition_range_value", text="Shadow Range", slider=True)
        col.prop(scene, "ww_face_shadow_softness_value", text="Face Softness", slider=True)

        if scene.ww_light_mode == "6":
            box_col = layout.box()
            box_col.label(text="Custom Colors", icon="COLOR")
            col_colors = box_col.column(align=True)
            col_colors.prop(scene, "ww_amb_color", text="Ambient")
            col_colors.prop(scene, "ww_light_color", text="Light")
            col_colors.prop(scene, "ww_shadow_color", text="Shadow")
            col_colors.prop(scene, "ww_rim_color", text="Rim")


class WW_PT_UI_Tools_Menu(Panel, WutheringWavesUIRenderChecker):
    bl_label = "Tools & Optimization"
    bl_idname = "WW_PT_UI_Tools_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        box_vp = layout.box()
        box_vp.label(text="Viewport Presets", icon="RESTRICT_VIEW_OFF")
        row = box_vp.row(align=True)
        row.operator("wuthering_waves.set_performance_mode", text="Performance", icon="PREVIEW_RANGE")
        row.operator("wuthering_waves.set_quality_mode", text="Quality", icon="SCENE")

        box_mesh = layout.box()
        box_mesh.label(text="Mesh Tools", icon="MESH_DATA")
        box_mesh.operator("wuthering_waves.separate_mesh", text="Separate Mesh Parts", icon="SELECT_SUBTRACT")


classes = (
    WW_PT_Setup_Wizard_UI_Layout,
    WW_PT_Basic_Setup_Wizard_UI_Layout,
    WW_PT_Advanced_Setup_Wizard_UI_Layout,
    WW_PT_UI_Character_Model_Menu,
    WW_PT_UI_Materials_Menu,
    WW_PT_UI_Outlines_Menu,
    WW_PT_UI_Rig_Character_Menu,
    WW_PT_UI_Finish_Setup_Menu,
    WW_PT_UI_Appearance_Menu,
    WW_PT_UI_Lighting_Menu,
    WW_PT_UI_Tools_Menu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
