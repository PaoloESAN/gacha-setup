# Author: michael-gh1

import bpy
from bpy.types import Panel, UILayout

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import GenshinImpactUIRenderChecker

class UI_Properties:
    @staticmethod
    def create_custom_ui_properties():
        bpy.types.WindowManager.setup_wizard_full_run_rigging_enabled = bpy.props.BoolProperty(
            name = "Rigging Enabled",
            default = True
        )

        bpy.types.WindowManager.cache_enabled = bpy.props.BoolProperty(
            name = "Cache Enabled",
            default = True
        )



        bpy.types.WindowManager.post_processing_setup_enabled = bpy.props.BoolProperty(
            name = "Post-Processing Setup Enabled",
            description = "Enables Post-Processing Compositing Setup",
            default = True
        )

        bpy.types.WindowManager.enable_viewport_outlines = bpy.props.BoolProperty(
            name = "Enable Viewport Outlines",
            description = "Enables Viewport Outlines on Setup",
            default = True
        )

        bpy.types.Scene.zzz_shader_type = bpy.props.EnumProperty(
            items=[
                ("KYTHERA", "Kythera's Shader", "Use Kythera's ZZZ Shader (Face Shader + General Shader)"),
                ("LEGACY", "Legacy Shader", "Use Legacy ZZZ Setup File V2.0 Shader"),
            ],
            name="Shader",
            description="Select shader setup for Zenless Zone Zero",
            default="KYTHERA",
        )

        bpy.types.Scene.enable_hair_clothes_physics = bpy.props.BoolProperty(
            name="Hair & Clothes Physics",
            description="Apply Damped Track physics to Hair and Clothes bone chains",
            default=False,
        )

        bpy.types.Scene.hair_physics_influence = bpy.props.FloatProperty(
            name="Hair Influence",
            description="Damped Track influence for hair bone chains",
            min=0.0,
            max=1.0,
            default=0.7,
            step=10,
            precision=2,
        )

        bpy.types.Scene.clothes_physics_influence = bpy.props.FloatProperty(
            name="Clothes Influence",
            description="Damped Track influence for clothes bone chains",
            min=0.0,
            max=1.0,
            default=0.4,
            step=10,
            precision=2,
        )


class GI_PT_Setup_Wizard_UI_Layout(Panel, GenshinImpactUIRenderChecker):
    bl_label = "Genshin Impact Setup Wizard"
    bl_idname = "GI_PT_Setup_Wizard_UI_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"

    @classmethod
    def poll(cls, context):
        return False

    def draw(self, context):
        layout = self.layout
        window_manager = context.window_manager

        sub_layout = layout.box()
        run_entire_setup_column = sub_layout.column()
        OperatorFactory.create(
            run_entire_setup_column,
            'genshin.setup_wizard_ui',
            'Run Entire Setup',
            'PLAY',
            game_type=GameType.GENSHIN_IMPACT.name
        )
        from setup_wizard.services.isolation import isolation_service
        isolation_service.draw_setup_status_box(sub_layout, context, run_entire_setup_column)

        settings_box = layout.box()
        settings_header = settings_box.row()
        settings_header.label(text="Setup Settings", icon="PREFERENCES")

        settings_col = settings_box.column()
        props = context.scene.character_rigger_props
        enable_physics = getattr(props, "enable_hair_clothes_physics", getattr(props, "enable_hair_dress_physics", False))
        settings_col.prop(props, "enable_hair_clothes_physics", text="Hair & Clothes Physics")
        if enable_physics:
            sliders_col = settings_col.column()
            sliders_col.prop(props, "hair_physics_influence", text="Hair", slider=True)
            sliders_col.prop(props, "clothes_physics_influence", text="Clothes", slider=True)
        settings_col.prop(props, "disable_rigging", text="Disable Rigging")


class GI_PT_Basic_Setup_Wizard_UI_Layout(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Basic Setup'
    bl_idname = 'GI_PT_UI_Basic_Setup_Layout'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Gacha Setup"
    bl_order = 2
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        OperatorFactory.create(
            sub_layout,
            'genshin.set_up_character',
            'Set Up Character',
            icon='OUTLINER_OB_ARMATURE',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.set_up_materials',
            'Set Up Materials',
            icon='MATERIAL',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        if bpy.app.version >= (3,3,0):
            OperatorFactory.create(
                sub_layout,
                'genshin.set_up_outlines',
                'Set Up Outlines',
                icon='GEOMETRY_NODES',
                game_type=GameType.GENSHIN_IMPACT.name,
            )
        else:
            layout.label(text='(Outlines Disabled < v3.3.0)')
        OperatorFactory.create(
            sub_layout,
            'genshin.fix_transformations',
            'Fix Transformations',
            'OBJECT_DATA'
        )

        OperatorFactory.create_rig_character_ui(sub_layout)

        OperatorFactory.create(
            sub_layout,
            'genshin.finish_setup',
            'Finish Setup',
            icon='CHECKMARK',
            game_type=GameType.GENSHIN_IMPACT.name,
        )


class GI_PT_Advanced_Setup_Wizard_UI_Layout(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Advanced Setup'
    bl_idname = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Gacha Setup"
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout


class GI_PT_UI_Character_Model_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Set Up Character Menu'
    bl_idname = 'GI_PT_UI_Character_Model_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            'genshin.import_model',
            'Import Character Model',
            'OUTLINER_OB_ARMATURE',
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.delete_empties',
            'Delete Empties',
            'TRASH'
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.clear_pose',
            'Clear Pose',
            'POSE_HLT',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.reorient_bones',
            'Fix Orientation',
            'BONE_DATA'
        )


class GI_PT_UI_Materials_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Set Up Materials Menu'
    bl_idname = 'GI_PT_UI_Materials_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            'genshin.import_materials',
            'Import Genshin Materials',
            'MATERIAL',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.replace_default_materials',
            'Replace Default Materials',
            'ARROW_LEFTRIGHT',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.import_textures',
            'Import Character Textures',
            'TEXTURE',
            game_type=GameType.GENSHIN_IMPACT.name,
        )


class GI_PT_UI_Outlines_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Set Up Outlines Menu'
    bl_idname = 'GI_PT_UI_Outlines_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()
        scene = context.scene

        if bpy.app.version >= (3,3,0):
            OperatorFactory.create(
                sub_layout,
                'genshin.import_outlines',
                'Import Outlines',
                'FILE_FOLDER',
                game_type=GameType.GENSHIN_IMPACT.name,
            )
            OperatorFactory.create(
                sub_layout,
                'genshin.setup_geometry_nodes',
                'Set Up Geometry Nodes',
                'GEOMETRY_NODES',
                game_type=GameType.GENSHIN_IMPACT.name,
            )
            OperatorFactory.create(
                sub_layout,
                'genshin.import_outline_lightmaps',
                'Import Outline Lightmaps',
                'FILE_FOLDER',
                game_type=GameType.GENSHIN_IMPACT.name,
            )

            sub_layout = layout.box()
            sub_layout.prop_search(scene, 'setup_wizard_material_for_material_data_import', bpy.data, 'materials')
            sub_layout.prop_search(scene, 'setup_wizard_outlines_material_for_material_data_import', bpy.data, 'materials')
            OperatorFactory.create(
                sub_layout,
                'genshin.import_material_data',
                'Import Material Data',
                'FILE',
                game_type=GameType.GENSHIN_IMPACT.name,
                setup_mode='ADVANCED',
            )
        else:
            layout.label(text='(Outlines Disabled < v3.3.0)')


class GI_PT_UI_Finish_Setup_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Finish Setup Menu'
    bl_idname = 'GI_PT_UI_Misc_Setup_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            'genshin.setup_head_driver',
            'Set Up Head Driver',
            'CONSTRAINT',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.set_color_management_to_standard',
            'Set Color Mgmt to Standard',
            'SCENE'
        )
        OperatorFactory.create(
            sub_layout,
            'genshin.delete_specific_objects',
            'Clean Up Extra Meshes',
            'TRASH'
        )
        OperatorFactory.create(
            sub_layout,
            'hoyoverse.rename_shader_materials',
            'Rename Shader Materials',
            'GREASEPENCIL',
            game_type=GameType.GENSHIN_IMPACT.name,
        )


class GI_PT_UI_Character_Rig_Setup_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Character Rig Menu'
    bl_idname = 'GI_PT_Rigify_Setup_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()
        box = sub_layout.box()

        character_rigger_props = context.scene.character_rigger_props

        OperatorFactory.create_rig_character_ui(box)
        OperatorFactory.create(
            box,
            'hoyoverse.apply_hair_clothes_physics',
            'Apply Hair & Clothes Physics',
            'PHYSICS',
        )

        box = sub_layout.box()        
        box.label(text='Settings')

        col = box.column()
        OperatorFactory.create(
            col,
            'hoyoverse.rootshape_filepath_setter',
            'Override RootShape Filepath',
            'FILE_FOLDER',
            game_type=GameType.GENSHIN_IMPACT.name,
            operator_context='INVOKE_DEFAULT'
        )
        col = box.column()
        col.prop(character_rigger_props, 'allow_arm_ik_stretch')
        col.prop(character_rigger_props, 'allow_leg_ik_stretch')
        col.prop(character_rigger_props, 'use_arm_ik_poles')
        col.prop(character_rigger_props, 'use_leg_ik_poles')
        col.prop(character_rigger_props, 'add_children_of_constraints')
        col.prop(character_rigger_props, 'use_head_tracker')
        enable_physics = getattr(character_rigger_props, "enable_hair_clothes_physics", getattr(character_rigger_props, "enable_hair_dress_physics", False))
        col.prop(character_rigger_props, 'enable_hair_clothes_physics', text="Hair & Clothes Physics")
        if enable_physics:
            sliders_col = col.column()
            sliders_col.prop(character_rigger_props, 'hair_physics_influence', text='Hair', slider=True)
            sliders_col.prop(character_rigger_props, 'clothes_physics_influence', text='Clothes', slider=True)


class GI_PT_UI_Post_Processing_Setup_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = 'Post Processing Menu'
    bl_idname = 'GI_PT_UI_Post_Processing_Setup_Menu'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'GI_PT_UI_Advanced_Setup_Layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        OperatorFactory.create(
            sub_layout,
            'hoyoverse.custom_composite_node_setup',
            'Set Up Compositing Nodes',
            'NODE_COMPOSITING'
        )
        OperatorFactory.create(
            sub_layout,
            'hoyoverse.post_processing_default_settings',
            'Set HYV-PP Defaults',
            'FILE_REFRESH'
        )


class GI_PT_UI_Post_Processing_Node_Editor_Setup_Menu(Panel, GenshinImpactUIRenderChecker):
    bl_label = "Compositing Setup Wizard"
    bl_idname = "GI_PT_Custom_Compositing_Node_UI_Layout"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Genshin - Setup Wizard"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        sub_layout = layout.box()
        window_manager = context.window_manager

        row.prop(window_manager, 'cache_enabled')
        OperatorFactory.create(
            row,
            'genshin.clear_cache_operator',
            'Clear Cache',
            'TRASH',
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        OperatorFactory.create(
            sub_layout,
            'hoyoverse.custom_composite_node_setup',
            'Set Up Compositing Nodes',
            'NODE_COMPOSITING'
        )
        OperatorFactory.create(
            sub_layout,
            'hoyoverse.post_processing_default_settings',
            'Set HYV-PP Defaults',
            'FILE_REFRESH'
        )


'''
    This factory is intended to help create a UI element's operator (or the action it takes) when pressed.
    While it currently doesn't do anything too grand, it may provide future flexibility.
'''
class OperatorFactory:
    @staticmethod
    def create(
        ui_object: UILayout,
        operator: str,
        text: str,
        icon: str,
        operator_context='EXEC_DEFAULT',
        **kwargs
    ):
        ui_object.operator_context = operator_context
        op_item = ui_object.operator(
            operator=operator,
            text=text,
            icon=icon,
        )

        if op_item is not None:
            for key, value in kwargs.items():
                setattr(op_item, key, value)

    @staticmethod
    def create_rig_character_ui(
        ui_object: UILayout,
        game_type: str = GameType.GENSHIN_IMPACT.name,
    ):
        expy_kit_installed = any('expy' in k.lower() for k in bpy.context.preferences.addons.keys())
        rigify_installed = any('rigify' in k.lower() for k in bpy.context.preferences.addons.keys())

        column = ui_object.column()
        column.enabled = True if expy_kit_installed and rigify_installed else False
        OperatorFactory.create(
            column,
            'hoyoverse.set_up_character_rig',
            'Rig Character',
            'OUTLINER_OB_ARMATURE',
            game_type=game_type,
        )
        if not column.enabled:
            column = ui_object.column()
            if not expy_kit_installed:
                column.label(text='ExpyKit required', icon='ERROR')
            if not rigify_installed:
                column.label(text='Rigify required', icon='ERROR')


GI_LIGHT_PRESETS = {
    "0": {  # Default
        "ambient": (1.0, 1.0, 1.0),
        "sharp_lit": (1.0, 1.0, 1.0),
        "soft_lit": (1.0, 1.0, 1.0),
        "sharp_shadow": (1.0, 1.0, 1.0),
        "soft_shadow": (1.0, 1.0, 1.0),
        "shadow_position": 0.55,
        "day_night": 0.0,
        "rim_lit": (1.0, 1.0, 1.0),
        "rim_shadow": (1.0, 1.0, 1.0),
    },
    "1": {  # Sunrise
        "ambient": (0.95, 0.85, 0.8),
        "sharp_lit": (1.0, 0.9, 0.8),
        "soft_lit": (1.0, 0.88, 0.75),
        "sharp_shadow": (0.6, 0.6, 0.8),
        "soft_shadow": (0.65, 0.65, 0.85),
        "shadow_position": 0.55,
        "day_night": 0.0,
        "rim_lit": (1.0, 0.82, 0.66),
        "rim_shadow": (0.6, 0.5, 0.7),
    },
    "2": {  # Day
        "ambient": (1.0, 1.0, 1.0),
        "sharp_lit": (1.0, 1.0, 1.0),
        "soft_lit": (1.0, 1.0, 1.0),
        "sharp_shadow": (0.75, 0.75, 0.85),
        "soft_shadow": (0.8, 0.8, 0.9),
        "shadow_position": 0.55,
        "day_night": 0.0,
        "rim_lit": (1.0, 1.0, 1.0),
        "rim_shadow": (0.6, 0.6, 0.7),
    },
    "3": {  # Sunset
        "ambient": (0.9, 0.75, 0.7),
        "sharp_lit": (1.0, 0.7, 0.5),
        "soft_lit": (1.0, 0.65, 0.45),
        "sharp_shadow": (0.45, 0.4, 0.65),
        "soft_shadow": (0.5, 0.45, 0.7),
        "shadow_position": 0.55,
        "day_night": 0.0,
        "rim_lit": (1.0, 0.8, 0.5),
        "rim_shadow": (0.5, 0.35, 0.6),
    },
    "4": {  # Night
        "ambient": (0.4, 0.45, 0.6),
        "sharp_lit": (0.65, 0.75, 0.95),
        "soft_lit": (0.6, 0.7, 0.9),
        "sharp_shadow": (0.2, 0.25, 0.45),
        "soft_shadow": (0.25, 0.3, 0.5),
        "shadow_position": 0.55,
        "day_night": 1.0,
        "rim_lit": (0.5, 0.7, 1.0),
        "rim_shadow": (0.2, 0.3, 0.5),
    },
    "5": {  # Rainy
        "ambient": (0.6, 0.65, 0.7),
        "sharp_lit": (0.8, 0.85, 0.9),
        "soft_lit": (0.75, 0.8, 0.85),
        "sharp_shadow": (0.4, 0.45, 0.55),
        "soft_shadow": (0.45, 0.5, 0.6),
        "shadow_position": 0.55,
        "day_night": 0.3,
        "rim_lit": (0.6, 0.7, 0.8),
        "rim_shadow": (0.3, 0.35, 0.45),
    },
}

_is_updating_gi_props = False


def update_gi_light_mode(self, context=None):
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    mode = getattr(self, "gi_light_mode", "0")
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        arm = resolve_settings_armature(context)
        if arm:
            arm["gi_light_mode"] = str(mode)
    except Exception:
        pass

    if mode in GI_LIGHT_PRESETS:
        preset = GI_LIGHT_PRESETS[mode]
        _is_updating_gi_props = True
        try:
            self.gi_amb_color = preset["ambient"]
            self.gi_sharp_lit_color = preset["sharp_lit"]
            self.gi_soft_lit_color = preset["soft_lit"]
            self.gi_sharp_shadow_color = preset["sharp_shadow"]
            self.gi_soft_shadow_color = preset["soft_shadow"]
            if "shadow_position" in preset:
                self.gi_shadow_position = preset["shadow_position"]
            if "day_night" in preset:
                self.gi_day_night = preset["day_night"]
            if "rim_lit" in preset:
                self.gi_rim_lit_color = preset["rim_lit"]
            if "rim_shadow" in preset:
                self.gi_rim_shadow_color = preset["rim_shadow"]
        finally:
            _is_updating_gi_props = False
    sync_genshin_shader_properties(getattr(context, "scene", getattr(bpy.context, "scene", None)), context=context)


def update_gi_lighting(self, context=None):
    sync_genshin_shader_properties(getattr(context, "scene", getattr(bpy.context, "scene", None)), context=context)


def update_gi_fresnel(self, context=None):
    sync_genshin_shader_properties(getattr(context, "scene", getattr(bpy.context, "scene", None)), context=context)


def sync_genshin_shader_properties(scene=None, context=None):
    scene = scene or getattr(bpy.context, "scene", None)
    if not scene:
        return

    use_fresnel = 1.0 if getattr(scene, "gi_use_fresnel", False) else 0.0
    fresnel_col = list(getattr(scene, "gi_fresnel_color", (1.0, 1.0, 1.0)))
    if len(fresnel_col) == 3:
        fresnel_col.append(1.0)
    fresnel_power = float(getattr(scene, "gi_fresnel_power", 2.0))
    fresnel_scaler = float(getattr(scene, "gi_fresnel_scaler", 2.0))

    amb_col = list(getattr(scene, "gi_amb_color", (1.0, 1.0, 1.0)))
    if len(amb_col) == 3:
        amb_col.append(1.0)

    sharp_lit_col = list(getattr(scene, "gi_sharp_lit_color", (1.0, 1.0, 1.0)))
    if len(sharp_lit_col) == 3:
        sharp_lit_col.append(1.0)

    soft_lit_col = list(getattr(scene, "gi_soft_lit_color", (1.0, 1.0, 1.0)))
    if len(soft_lit_col) == 3:
        soft_lit_col.append(1.0)

    sharp_shadow_col = list(getattr(scene, "gi_sharp_shadow_color", (1.0, 1.0, 1.0)))
    if len(sharp_shadow_col) == 3:
        sharp_shadow_col.append(1.0)

    soft_shadow_col = list(getattr(scene, "gi_soft_shadow_color", (1.0, 1.0, 1.0)))
    if len(soft_shadow_col) == 3:
        soft_shadow_col.append(1.0)

    shadow_pos = float(getattr(scene, "gi_shadow_position", 0.55))
    catch_shadows = 1.0 if getattr(scene, "gi_catch_shadows", False) else 0.0
    day_night = float(getattr(scene, "gi_day_night", 0.0))

    rim_lit_col = list(getattr(scene, "gi_rim_lit_color", (1.0, 1.0, 1.0)))
    if len(rim_lit_col) == 3:
        rim_lit_col.append(1.0)

    rim_shadow_col = list(getattr(scene, "gi_rim_shadow_color", (1.0, 1.0, 1.0)))
    if len(rim_shadow_col) == 3:
        rim_shadow_col.append(1.0)

    prop_map = {
        "Use Fresnel": use_fresnel,
        "Fresnel Color": fresnel_col,
        "Fresnel Power": fresnel_power,
        "Fresnel Scaler": fresnel_scaler,
        "Ambient Colour": amb_col,
        "Sharp Lit Colour": sharp_lit_col,
        "Soft Lit Colour": soft_lit_col,
        "Sharp Shadow Colour": sharp_shadow_col,
        "Soft Shadow Colour": soft_shadow_col,
        "Shadow Position": shadow_pos,
        "Catch Shadows": catch_shadows,
        "Day/Night": day_night,
        "Rim Lit": rim_lit_col,
        "Rim Shadow": rim_shadow_col,
    }

    # 1. Resolve character materials to keep settings strictly per-character
    try:
        from setup_wizard.ui.character_settings_utils import (
            get_character_materials,
            ensure_character_node_trees_isolated,
        )
        arm, target_materials = get_character_materials(context)
        if arm and target_materials:
            ensure_character_node_trees_isolated(arm, target_materials)
    except Exception:
        target_materials = []

    # 2. Find target Global Material Properties node group(s)
    target_trees = set()
    mats_to_update = target_materials if target_materials else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower():
                        target_trees.add(node.node_tree)

    if not target_trees:
        for ng in bpy.data.node_groups:
            if "global material properties" in ng.name.lower():
                target_trees.add(ng)

    # 3. Update inside each target Global Material Properties node group
    for tree in target_trees:
        out_node = tree.nodes.get("Global Properties") or tree.nodes.get("Group Output")
        if out_node:
            for inp in out_node.inputs:
                if inp.name in prop_map:
                    for l in list(inp.links):
                        tree.links.remove(l)
                    try:
                        inp.default_value = prop_map[inp.name]
                    except Exception:
                        pass

        if hasattr(tree, "interface") and hasattr(tree.interface, "items_tree"):
            for item in tree.interface.items_tree:
                if item.name in prop_map:
                    try:
                        item.default_value = prop_map[item.name]
                    except Exception:
                        pass

    # 4. Also update direct group node inputs on character materials if any exist (e.g. PrimoToon v4.0)
    prop_aliases = {
        "Use Fresnel": ["Toggle Fresnel", "Use Fresnel"],
        "Fresnel Color": ["Fresnel Color"],
        "Fresnel Power": ["Fresnel Power"],
        "Fresnel Scaler": ["Fresnel Scaler"],
        "Ambient Colour": ["Ambient Colour", "Ambient Color"],
        "Sharp Lit Colour": ["Sharp Lit Colour", "Sharp Lit Color"],
        "Soft Lit Colour": ["Soft Lit Colour", "Soft Lit Color"],
        "Sharp Shadow Colour": ["Sharp Shadow Colour", "Sharp Shadow Color"],
        "Soft Shadow Colour": ["Soft Shadow Colour", "Soft Shadow Color"],
        "Shadow Position": ["Shadow Position", "Shadow Position Offset"],
        "Catch Shadows": ["Toggle Catch Shadows", "Catch Shadows"],
        "Day/Night": ["Warm / Cold Ramps", "Day/Night"],
        "Rim Lit": ["Rim Lit"],
        "Rim Shadow": ["Rim Shadow"],
    }

    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    for canonical_name, val in prop_map.items():
                        aliases = prop_aliases.get(canonical_name, [canonical_name])
                        for alias in aliases:
                            if alias in node.inputs:
                                inp = node.inputs[alias]
                                try:
                                    if type(inp) is bpy.types.NodeSocketBool:
                                        inp.default_value = bool(val > 0.5 if isinstance(val, (int, float)) else val)
                                    else:
                                        inp.default_value = val
                                except Exception:
                                    pass

    # 5. Tag 3D areas for redraw
    if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
        for win in getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()


def pull_gi_panel_values(scene, context, force=False):
    """Synchronizes UI sliders and lighting mode with the selected character's materials and rig."""
    global _is_updating_gi_props
    if _is_updating_gi_props or not scene:
        return
    try:
        from setup_wizard.ui.character_settings_utils import (
            get_character_materials,
            has_active_character_changed,
            ensure_character_node_trees_isolated,
            _iter_rig_meshes,
        )
        from setup_wizard.utils.modifier_utils import get_modifier_property
        if not force and not has_active_character_changed(context):
            return
        arm, mats = get_character_materials(context)
        if not arm:
            return

        _is_updating_gi_props = True
        try:
            # 1. Pull Outlines & Night Soul states from character meshes
            for mesh in _iter_rig_meshes(arm):
                for mod in getattr(mesh, "modifiers", []):
                    if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                        v24 = get_modifier_property(mod, "Socket_24")
                        if v24 is None:
                            v24 = get_modifier_property(mod, "Toggle Outlines")
                        if v24 is not None:
                            scene.gi_enable_outlines = bool(v24)
                        else:
                            scene.gi_enable_outlines = bool(mod.show_viewport)

                        v23 = get_modifier_property(mod, "Socket_23")
                        if v23 is None:
                            v23 = get_modifier_property(mod, "Toggle Night Soul State")
                        if v23 is not None:
                            scene.gi_enable_night_soul = bool(v23)
                        break
                break

            # 2. Pull lighting mode saved on this armature
            saved_mode = arm.get("gi_light_mode", "0")
            if getattr(scene, "gi_light_mode", "") != str(saved_mode):
                scene.gi_light_mode = str(saved_mode)

            if mats:
                ensure_character_node_trees_isolated(arm, mats)

                # 3. Find target Global Material Properties node group for this character
                target_tree = None
                for m in mats:
                    if getattr(m, "node_tree", None):
                        for node in m.node_tree.nodes:
                            if node.type == 'GROUP' and node.node_tree:
                                if "global material properties" in node.node_tree.name.lower():
                                    target_tree = node.node_tree
                                    break
                    if target_tree:
                        break

                if not target_tree:
                    for m in mats:
                        if getattr(m, "node_tree", None):
                            primo_node = m.node_tree.nodes.get("PrimoToon")
                            if primo_node:
                                inputs = primo_node.inputs
                                if "Toggle Fresnel" in inputs:
                                    scene.gi_use_fresnel = bool(inputs["Toggle Fresnel"].default_value)
                                elif "Use Fresnel" in inputs:
                                    scene.gi_use_fresnel = bool(inputs["Use Fresnel"].default_value > 0.5)
                                if "Fresnel Color" in inputs:
                                    scene.gi_fresnel_color = tuple(inputs["Fresnel Color"].default_value)[:3]
                                if "Fresnel Power" in inputs:
                                    scene.gi_fresnel_power = float(inputs["Fresnel Power"].default_value)
                                if "Fresnel Scaler" in inputs:
                                    scene.gi_fresnel_scaler = float(inputs["Fresnel Scaler"].default_value)
                                if "Ambient Colour" in inputs:
                                    scene.gi_amb_color = tuple(inputs["Ambient Colour"].default_value)[:3]
                                if "Sharp Lit Colour" in inputs:
                                    scene.gi_sharp_lit_color = tuple(inputs["Sharp Lit Colour"].default_value)[:3]
                                if "Soft Lit Colour" in inputs:
                                    scene.gi_soft_lit_color = tuple(inputs["Soft Lit Colour"].default_value)[:3]
                                sharp_shadow = inputs.get("Sharp Shadow Colour") or inputs.get("Sharp Shadow Color")
                                if sharp_shadow:
                                    scene.gi_sharp_shadow_color = tuple(sharp_shadow.default_value)[:3]
                                soft_shadow = inputs.get("Soft Shadow Colour") or inputs.get("Soft Shadow Color")
                                if soft_shadow:
                                    scene.gi_soft_shadow_color = tuple(soft_shadow.default_value)[:3]
                                shadow_pos_inp = inputs.get("Shadow Position Offset") or inputs.get("Shadow Position")
                                if shadow_pos_inp:
                                    scene.gi_shadow_position = float(shadow_pos_inp.default_value)
                                catch_shadow_inp = inputs.get("Toggle Catch Shadows") or inputs.get("Catch Shadows")
                                if catch_shadow_inp:
                                    scene.gi_catch_shadows = bool(catch_shadow_inp.default_value)
                                day_night_inp = inputs.get("Warm / Cold Ramps") or inputs.get("Day/Night")
                                if day_night_inp:
                                    scene.gi_day_night = 1.0 if day_night_inp.default_value else 0.0
                                break
                else:
                    out_node = target_tree.nodes.get("Global Properties") or target_tree.nodes.get("Group Output")
                    if out_node:
                        inputs = out_node.inputs
                        if "Use Fresnel" in inputs:
                            scene.gi_use_fresnel = bool(inputs["Use Fresnel"].default_value > 0.5)
                        if "Fresnel Color" in inputs:
                            scene.gi_fresnel_color = tuple(inputs["Fresnel Color"].default_value)[:3]
                        if "Fresnel Power" in inputs:
                            scene.gi_fresnel_power = float(inputs["Fresnel Power"].default_value)
                        if "Fresnel Scaler" in inputs:
                            scene.gi_fresnel_scaler = float(inputs["Fresnel Scaler"].default_value)
                        if "Ambient Colour" in inputs:
                            scene.gi_amb_color = tuple(inputs["Ambient Colour"].default_value)[:3]
                        if "Sharp Lit Colour" in inputs:
                            scene.gi_sharp_lit_color = tuple(inputs["Sharp Lit Colour"].default_value)[:3]
                        if "Soft Lit Colour" in inputs:
                            scene.gi_soft_lit_color = tuple(inputs["Soft Lit Colour"].default_value)[:3]
                        if "Sharp Shadow Colour" in inputs:
                            scene.gi_sharp_shadow_color = tuple(inputs["Sharp Shadow Colour"].default_value)[:3]
                        if "Soft Shadow Colour" in inputs:
                            scene.gi_soft_shadow_color = tuple(inputs["Soft Shadow Colour"].default_value)[:3]
                        if "Shadow Position" in inputs:
                            scene.gi_shadow_position = float(inputs["Shadow Position"].default_value)
                        if "Catch Shadows" in inputs:
                            scene.gi_catch_shadows = bool(inputs["Catch Shadows"].default_value > 0.5)
                        if "Day/Night" in inputs:
                            scene.gi_day_night = float(inputs["Day/Night"].default_value)
                        if "Rim Lit" in inputs:
                            scene.gi_rim_lit_color = tuple(inputs["Rim Lit"].default_value)[:3]
                        if "Rim Shadow" in inputs:
                            scene.gi_rim_shadow_color = tuple(inputs["Rim Shadow"].default_value)[:3]
        finally:
            _is_updating_gi_props = False
    except Exception:
        pass


def _apply_outlines_and_night_soul(context, outlines_on, ns_on):
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, _iter_rig_meshes
        from setup_wizard.utils.modifier_utils import set_modifier_property
        arm = resolve_settings_armature(context)
        meshes = list(_iter_rig_meshes(arm)) if arm else [obj for obj in bpy.data.objects if obj.type == 'MESH']
        should_show = bool(outlines_on or ns_on)

        for mesh in meshes:
            has_mod = False
            for mod in getattr(mesh, "modifiers", []):
                if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                    has_mod = True
                    set_modifier_property(mod, "Socket_24", outlines_on)
                    set_modifier_property(mod, "Toggle Outlines", outlines_on)
                    set_modifier_property(mod, "Socket_23", ns_on)
                    set_modifier_property(mod, "Toggle Night Soul State", ns_on)

                    try:
                        mod["Socket_24"] = outlines_on
                    except Exception:
                        pass
                    try:
                        mod["Toggle Outlines"] = outlines_on
                    except Exception:
                        pass
                    try:
                        mod["Socket_23"] = ns_on
                    except Exception:
                        pass
                    try:
                        mod["Toggle Night Soul State"] = ns_on
                    except Exception:
                        pass

                    # Solo si ambos están desactivados, quitar show_viewport y show_render
                    mod.show_viewport = should_show
                    mod.show_render = should_show

            if has_mod:
                try:
                    mesh.update_tag()
                except Exception:
                    pass

        try:
            if context and getattr(context, "view_layer", None):
                context.view_layer.update()
        except Exception:
            pass

        for win in getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
    except Exception:
        pass


def update_gi_outlines(self, context):
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    outlines_on = getattr(self, "gi_enable_outlines", True)
    ns_on = getattr(self, "gi_enable_night_soul", False)
    _apply_outlines_and_night_soul(context, outlines_on, ns_on)


def update_gi_night_soul(self, context):
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    outlines_on = getattr(self, "gi_enable_outlines", True)
    ns_on = getattr(self, "gi_enable_night_soul", False)
    _apply_outlines_and_night_soul(context, outlines_on, ns_on)


def character_has_night_soul(context):
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, _iter_rig_meshes, get_character_materials
        from setup_wizard.utils.modifier_utils import get_modifier_property
        arm = resolve_settings_armature(context)
        if arm:
            for mesh in _iter_rig_meshes(arm):
                for mod in getattr(mesh, "modifiers", []):
                    if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                        ns_mat = get_modifier_property(mod, "Socket_10")
                        if not ns_mat:
                            ns_mat = get_modifier_property(mod, "Night Soul Outline")
                        if ns_mat:
                            return True
            _, mats = get_character_materials(context, arm)
            for mat in mats:
                if not getattr(mat, "node_tree", None):
                    continue
                for n_name in ['Main_NYXmask', 'Face_NYXmask']:
                    n = mat.node_tree.nodes.get(n_name)
                    if n and getattr(n, 'image', None):
                        return True
    except Exception:
        pass

    for mat in bpy.data.materials:
        if not getattr(mat, "node_tree", None):
            continue
        if "night soul" in mat.name.lower() and getattr(mat, "users", 0) > 0:
            return True
        for n_name in ['Main_NYXmask', 'Face_NYXmask']:
            n = mat.node_tree.nodes.get(n_name)
            if n and getattr(n, 'image', None):
                return True

    st = bpy.data.node_groups.get("Shader Textures")
    if st:
        nr = st.nodes.get("NYX_Color_Ramp")
        if nr and getattr(nr, 'image', None):
            return True

    return False


def update_gi_hair_physics(self, context):
    val = getattr(self, "gi_hair_physics_influence", 0.7)
    try:
        from setup_wizard.character_rig_setup.rig_ui_utils import update_hair_physics_influence
        update_hair_physics_influence(val, context)
    except Exception:
        pass


def update_gi_clothes_physics(self, context):
    val = getattr(self, "gi_clothes_physics_influence", 0.4)
    try:
        from setup_wizard.character_rig_setup.rig_ui_utils import update_clothes_physics_influence
        update_clothes_physics_influence(val, context)
    except Exception:
        pass


class GI_PT_Rig_Character_Settings(Panel):
    bl_label = "Character Settings"
    bl_idname = "GI_PT_Rig_Character_Settings_Main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.ui.character_settings_utils import is_game_armature
            return is_game_armature(context, "GENSHIN_IMPACT")
        except Exception:
            pass
        obj = context.active_object or context.object
        if not obj:
            return False
        is_rig = (obj.type == 'ARMATURE') or (obj.type == 'MESH' and obj.parent and obj.parent.type == 'ARMATURE')
        if not is_rig:
            return False
        return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        try:
            pull_gi_panel_values(scene, context)
        except Exception:
            pass

        # 1. Lighting Mode
        col_light = layout.column(align=True)
        col_light.label(text="Lighting Mode:")
        col_light.prop(scene, "gi_light_mode", text="")

        # 2. Custom Colors (Shown ONLY when in Custom mode "6")
        if getattr(scene, "gi_light_mode", "0") == "6":
            box_col = col_light.box()
            box_col.label(text="Custom Colors", icon="COLOR")
            col_colors = box_col.column(align=True)
            col_colors.prop(scene, "gi_amb_color", text="Ambient")
            col_colors.prop(scene, "gi_sharp_lit_color", text="Sharp Lit")
            col_colors.prop(scene, "gi_soft_lit_color", text="Soft Lit")
            col_colors.prop(scene, "gi_sharp_shadow_color", text="Sharp Shadow")
            col_colors.prop(scene, "gi_soft_shadow_color", text="Soft Shadow")
            col_colors.prop(scene, "gi_rim_lit_color", text="Rim Lit")
            col_colors.prop(scene, "gi_rim_shadow_color", text="Rim Shadow")

        # 3. Fresnel
        col_fresnel = layout.column(align=True)
        col_fresnel.prop(scene, "gi_use_fresnel", text="Use Fresnel")
        if getattr(scene, "gi_use_fresnel", False):
            box_fr = col_fresnel.box()
            box_fr.label(text="Fresnel Options", icon="SHADING_RENDERED")
            col_fr_props = box_fr.column(align=True)
            col_fr_props.prop(scene, "gi_fresnel_color", text="Fresnel Color")
            col_fr_props.prop(scene, "gi_fresnel_power", text="Fresnel Power")
            col_fr_props.prop(scene, "gi_fresnel_scaler", text="Fresnel Scaler")

        # 4. Outlines Settings
        box_outlines = layout.box()
        box_outlines.label(text="Outlines", icon="STROKE")
        col_outlines = box_outlines.column(align=True)
        col_outlines.prop(scene, "gi_enable_outlines", text="Enable Outlines")
        if character_has_night_soul(context):
            col_outlines.prop(scene, "gi_enable_night_soul", text="Enable Night Soul (Natlan Characters Only)")

        # 5. Shadows & Scene Settings (At the bottom)
        box_shadow = layout.box()
        box_shadow.label(text="Shadow & Scene Settings", icon="SHADING_SOLID")
        col_shadow = box_shadow.column(align=True)
        col_shadow.prop(scene, "gi_shadow_position", text="Shadow Position", slider=True)
        col_shadow.prop(scene, "gi_catch_shadows", text="Catch Shadows")
        col_shadow.prop(scene, "gi_day_night", text="Day / Night", slider=True)

        # 5. Hair & Clothes Physics (Below Shadow & Scene Settings)
        box_physics = layout.box()
        box_physics.label(text="Hair & Clothes Physics", icon="PHYSICS")
        col_physics = box_physics.column(align=True)
        try:
            from setup_wizard.character_rig_setup.rig_ui_utils import has_hair_clothes_physics
            physics_present = has_hair_clothes_physics(context)
        except Exception:
            physics_present = False

        if physics_present:
            col_physics.prop(scene, "gi_hair_physics_influence", text="Hair Physics", slider=True)
            col_physics.prop(scene, "gi_clothes_physics_influence", text="Clothes Physics", slider=True)
        else:
            col_physics.operator("hoyoverse.apply_hair_clothes_physics", text="Apply Physics", icon="FILE_REFRESH")


def register_gi_properties():
    for cls_name in dir(bpy.types):
        if cls_name.startswith("VIEW3D_PT_"):
            cls_prop = getattr(bpy.types, cls_name, None)
            if cls_prop and getattr(cls_prop, "bl_category", "") == "Item" and getattr(cls_prop, "bl_label", "") in ["Properties", "Context Properties"]:
                try:
                    bpy.utils.unregister_class(cls_prop)
                    cls_prop.bl_order = 4
                    cls_prop.bl_options = {'DEFAULT_CLOSED'}
                    bpy.utils.register_class(cls_prop)
                except Exception:
                    pass

    bpy.types.Scene.gi_light_mode = bpy.props.EnumProperty(
        items=[
            ("0", "Default", "Default Genshin lighting"),
            ("1", "Sunrise", "Sunrise lighting"),
            ("2", "Day", "Bright daytime lighting"),
            ("3", "Sunset", "Sunset lighting"),
            ("4", "Night", "Night lighting"),
            ("5", "Rainy", "Rainy / overcast lighting"),
            ("6", "Custom", "Custom user-defined lighting"),
        ],
        name="Lighting Mode",
        description="Select lighting mode / preset",
        default="0",
        update=update_gi_light_mode,
    )

    bpy.types.Scene.gi_use_fresnel = bpy.props.BoolProperty(
        name="Use Fresnel",
        description="Toggle Fresnel rim lighting",
        default=False,
        update=update_gi_fresnel,
    )
    bpy.types.Scene.gi_fresnel_color = bpy.props.FloatVectorProperty(
        name="Fresnel Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_fresnel,
    )
    bpy.types.Scene.gi_fresnel_power = bpy.props.FloatProperty(
        name="Fresnel Power",
        description="Fresnel exponent power",
        min=0.0,
        max=10.0,
        default=2.0,
        step=10,
        precision=2,
        update=update_gi_fresnel,
    )
    bpy.types.Scene.gi_fresnel_scaler = bpy.props.FloatProperty(
        name="Fresnel Scaler",
        description="Fresnel scale multiplier",
        min=0.0,
        max=20.0,
        default=2.0,
        step=10,
        precision=2,
        update=update_gi_fresnel,
    )

    bpy.types.Scene.gi_amb_color = bpy.props.FloatVectorProperty(
        name="Ambient Colour",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_sharp_lit_color = bpy.props.FloatVectorProperty(
        name="Sharp Lit Colour",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_soft_lit_color = bpy.props.FloatVectorProperty(
        name="Soft Lit Colour",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_sharp_shadow_color = bpy.props.FloatVectorProperty(
        name="Sharp Shadow Colour",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_soft_shadow_color = bpy.props.FloatVectorProperty(
        name="Soft Shadow Colour",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_shadow_position = bpy.props.FloatProperty(
        name="Shadow Position",
        description="Shadow Position",
        min=0.0,
        max=1.0,
        default=0.55,
        step=1,
        precision=3,
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_catch_shadows = bpy.props.BoolProperty(
        name="Catch Shadows",
        description="Enable scene shadows",
        default=False,
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_day_night = bpy.props.FloatProperty(
        name="Day / Night",
        description="Day/Night lighting transition",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=2,
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_rim_lit_color = bpy.props.FloatVectorProperty(
        name="Rim Lit",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_rim_shadow_color = bpy.props.FloatVectorProperty(
        name="Rim Shadow",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_gi_lighting,
    )
    bpy.types.Scene.gi_hair_physics_influence = bpy.props.FloatProperty(
        name="Hair Physics",
        description="Damped Track constraint influence for hair bone chains",
        min=0.0,
        max=1.0,
        default=0.7,
        step=5,
        precision=2,
        update=update_gi_hair_physics,
    )
    bpy.types.Scene.gi_clothes_physics_influence = bpy.props.FloatProperty(
        name="Clothes Physics",
        description="Damped Track constraint influence for clothes/dress bone chains",
        min=0.0,
        max=1.0,
        default=0.4,
        step=5,
        precision=2,
        update=update_gi_clothes_physics,
    )
    bpy.types.Scene.gi_enable_outlines = bpy.props.BoolProperty(
        name="Enable Outlines",
        description="Enable or disable character outlines (Toggle Outlines)",
        default=True,
        update=update_gi_outlines,
    )
    bpy.types.Scene.gi_enable_night_soul = bpy.props.BoolProperty(
        name="Enable Night Soul (Natlan Characters Only)",
        description="Enable or disable Night Soul state on outlines for Natlan characters (Toggle Night Soul State)",
        default=False,
        update=update_gi_night_soul,
    )


def unregister_gi_properties():
    for prop in [
        "gi_light_mode", "gi_use_fresnel", "gi_fresnel_color", "gi_fresnel_power", "gi_fresnel_scaler",
        "gi_amb_color", "gi_sharp_lit_color", "gi_soft_lit_color",
        "gi_sharp_shadow_color", "gi_soft_shadow_color", "gi_shadow_position",
        "gi_catch_shadows", "gi_day_night", "gi_rim_lit_color", "gi_rim_shadow_color",
        "gi_hair_physics_influence", "gi_clothes_physics_influence",
        "gi_enable_outlines", "gi_enable_night_soul"
    ]:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


@bpy.app.handlers.persistent
def gi_frame_change_handler(scene, depsgraph=None):
    try:
        sync_genshin_shader_properties(scene)
    except Exception:
        pass
