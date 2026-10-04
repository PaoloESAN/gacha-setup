# Author: michael-gh1

import bpy
from bpy.types import Panel, UILayout, Operator

from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.shader_material_names import DURIN_NORMAL_EYE_MATERIAL_NAME
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
    bl_parent_id = 'CSW_PT_Old_Setup_UI_Layout'
    bl_order = 1
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
    bl_parent_id = 'CSW_PT_Old_Setup_UI_Layout'
    bl_order = 2
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
        col.prop(character_rigger_props, 'set_up_lighting_panel')
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


def _is_preset_matching(values, preset, tol_col=0.04, tol_val=0.06):
    def col_close(c1, c2):
        if not c1 or not c2:
            return True
        return all(abs(float(a) - float(b)) <= tol_col for a, b in zip(c1[:3], c2[:3]))

    def val_close(v1, v2):
        if v1 is None or v2 is None:
            return True
        return abs(float(v1) - float(v2)) <= tol_val

    if "ambient" in values and not col_close(values["ambient"], preset["ambient"]):
        return False
    if "sharp_lit" in values and not col_close(values["sharp_lit"], preset["sharp_lit"]):
        return False
    if "sharp_shadow" in values and not col_close(values["sharp_shadow"], preset["sharp_shadow"]):
        return False
    if "soft_lit" in values and not col_close(values["soft_lit"], preset["soft_lit"]):
        return False
    if "soft_shadow" in values and not col_close(values["soft_shadow"], preset["soft_shadow"]):
        return False
    if "rim_lit" in values and not col_close(values["rim_lit"], preset["rim_lit"]):
        return False
    if "rim_shadow" in values and not col_close(values["rim_shadow"], preset["rim_shadow"]):
        return False
    return True


def match_lighting_preset(values):
    if not values:
        return "0"
    for key in ["0", "1", "2", "3", "4", "5"]:
        if _is_preset_matching(values, GI_LIGHT_PRESETS[key]):
            return key
    return "6"  # Custom


def extract_character_lighting_inputs(arm=None, mats=None, context=None):
    if arm is None and context is not None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
        except Exception:
            pass
    if arm is None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(getattr(bpy, "context", None))
        except Exception:
            pass

    if mats is None and arm is not None:
        try:
            from setup_wizard.ui.character_settings_utils import get_character_materials
            _, mats = get_character_materials(context, arm)
        except Exception:
            mats = []

    if not mats:
        return {}

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

    values = {}
    if target_tree:
        out_node = target_tree.nodes.get("Global Properties") or target_tree.nodes.get("Group Output")
        inputs = out_node.inputs if out_node else {}
        for inp_name, target_key in [
            ("Ambient Colour", "ambient"), ("Ambient Color", "ambient"),
            ("Sharp Lit Colour", "sharp_lit"), ("Sharp Lit Color", "sharp_lit"),
            ("Soft Lit Colour", "soft_lit"), ("Soft Lit Color", "soft_lit"),
            ("Sharp Shadow Colour", "sharp_shadow"), ("Sharp Shadow Color", "sharp_shadow"),
            ("Soft Shadow Colour", "soft_shadow"), ("Soft Shadow Color", "soft_shadow"),
            ("Shadow Position", "shadow_position"), ("Shadow Position Offset", "shadow_position"),
            ("Day/Night", "day_night"), ("Warm / Cold Ramps", "day_night"),
            ("Rim Lit", "rim_lit"),
            ("Rim Shadow", "rim_shadow"),
        ]:
            if inp_name in inputs and target_key not in values:
                val = inputs[inp_name].default_value
                if hasattr(val, "__len__"):
                    values[target_key] = tuple(val)[:3]
                else:
                    values[target_key] = float(val)

    if not values:
        for m in mats:
            if getattr(m, "node_tree", None):
                for node in m.node_tree.nodes:
                    if node.type == 'GROUP' and any(k in (node.name.lower() + " " + getattr(node.node_tree, "name", "").lower()) for k in ["hoyotoon", "primotoon", "body shader"]):
                        inputs = node.inputs
                        for inp_name, target_key in [
                            ("Ambient Colour", "ambient"), ("Ambient Color", "ambient"),
                            ("Sharp Lit Colour", "sharp_lit"), ("Sharp Lit Color", "sharp_lit"),
                            ("Soft Lit Colour", "soft_lit"), ("Soft Lit Color", "soft_lit"),
                            ("Sharp Shadow Colour", "sharp_shadow"), ("Sharp Shadow Color", "sharp_shadow"),
                            ("Soft Shadow Colour", "soft_shadow"), ("Soft Shadow Color", "soft_shadow"),
                            ("Shadow Position", "shadow_position"), ("Shadow Position Offset", "shadow_position"),
                            ("Day/Night", "day_night"), ("Warm / Cold Ramps", "day_night"),
                            ("Rim Lit", "rim_lit"),
                            ("Rim Shadow", "rim_shadow"),
                        ]:
                            if inp_name in inputs and target_key not in values:
                                val = inputs[inp_name].default_value
                                if hasattr(val, "__len__"):
                                    values[target_key] = tuple(val)[:3]
                                else:
                                    values[target_key] = float(val)
                        if values:
                            break
            if values:
                break

    return values


def detect_character_light_mode(arm=None, mats=None, context=None) -> str:
    """Detects the lighting mode preset for the character based on shader node values and saved properties."""
    if arm is None and context is not None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
        except Exception:
            pass
    if arm is None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(getattr(bpy, "context", None))
        except Exception:
            pass

    values = extract_character_lighting_inputs(arm=arm, mats=mats, context=context)
    if not values:
        if arm is not None:
            saved = str(arm.get("gi_light_mode", "0"))
            return "0" if saved == "7" else saved
        scene = getattr(bpy.context, "scene", None) if hasattr(bpy, "context") else None
        saved = str(getattr(scene, "gi_light_mode", "0")) if scene else "0"
        return "0" if saved == "7" else saved

    matched = match_lighting_preset(values)
    saved_mode = str(arm.get("gi_light_mode")) if (arm is not None and arm.get("gi_light_mode") is not None) else None
    if saved_mode is not None:
        if saved_mode == "6":
            if matched == "6":
                return "6"
        elif saved_mode in GI_LIGHT_PRESETS:
            if _is_preset_matching(values, GI_LIGHT_PRESETS[saved_mode]):
                return saved_mode

    return matched


def update_gi_lighting_control_type(self, context=None):
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    ctrl_type = getattr(self, "gi_lighting_control_type", "PANEL")
    arm = None
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, get_character_materials
        arm = resolve_settings_armature(context)
        if arm:
            arm["gi_lighting_control_type"] = str(ctrl_type)
    except Exception:
        arm = None

    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        LightingPanel,
        disconnect_lighting_panel_nodes_from_global_material_properties,
        set_lighting_panel_visibility,
    )

    try:
        _, mats = get_character_materials(context, arm)
    except Exception:
        mats = []

    if ctrl_type == "PANEL":
        # Lighting Panel mode: connect nodes inside Global Material Properties and show in 3D
        lp = LightingPanel("")
        lp.connect_lighting_panel_nodes_to_global_material_properties(target_materials=mats)
        if arm:
            set_lighting_panel_visibility(arm, True)
    else:
        # This Panel mode: hide lighting panel in 3D and disconnect incoming links
        if arm:
            set_lighting_panel_visibility(arm, False)
        disconnect_lighting_panel_nodes_from_global_material_properties(target_materials=mats)

        # Restore / apply preset from This Panel
        current_mode = arm.get("gi_light_mode", "0") if arm else getattr(self, "gi_light_mode", "0")
        if str(current_mode) == "7" or (str(current_mode) not in GI_LIGHT_PRESETS and str(current_mode) != "6"):
            current_mode = "0"
            if arm:
                arm["gi_light_mode"] = "0"
            _is_updating_gi_props = True
            try:
                self.gi_light_mode = "0"
            finally:
                _is_updating_gi_props = False

        if str(current_mode) in GI_LIGHT_PRESETS:
            preset = GI_LIGHT_PRESETS[str(current_mode)]
            _is_updating_gi_props = True
            try:
                if "ambient" in preset:
                    self.gi_amb_color = preset["ambient"]
                if "sharp_lit" in preset:
                    self.gi_sharp_lit_color = preset["sharp_lit"]
                if "soft_lit" in preset:
                    self.gi_soft_lit_color = preset["soft_lit"]
                if "sharp_shadow" in preset:
                    self.gi_sharp_shadow_color = preset["sharp_shadow"]
                if "soft_shadow" in preset:
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


def update_gi_light_mode(self, context=None):
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    mode = getattr(self, "gi_light_mode", "0")
    arm = None
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, get_character_materials
        arm = resolve_settings_armature(context)
        if arm:
            arm["gi_light_mode"] = str(mode)
    except Exception:
        arm = None

    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        disconnect_lighting_panel_nodes_from_global_material_properties,
    )

    try:
        _, mats = get_character_materials(context, arm)
    except Exception:
        mats = []

    # Normal preset or custom mode: disconnect incoming links from lighting panel
    disconnect_lighting_panel_nodes_from_global_material_properties(target_materials=mats)

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
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        arm = resolve_settings_armature(context)
        if arm:
            arm["gi_light_mode"] = "6"
        _is_updating_gi_props = True
        try:
            self.gi_light_mode = "6"
        finally:
            _is_updating_gi_props = False
    except Exception:
        pass
    sync_genshin_shader_properties(getattr(context, "scene", getattr(bpy.context, "scene", None)), context=context)


def update_gi_fresnel(self, context=None):
    if _is_updating_gi_props:
        return
    sync_genshin_shader_properties(getattr(context, "scene", getattr(bpy.context, "scene", None)), context=context)


def update_gi_scene_settings(self, context=None):
    if _is_updating_gi_props:
        return
    sync_genshin_shader_properties(getattr(context, "scene", getattr(bpy.context, "scene", None)), context=context)


def sync_genshin_shader_properties(scene=None, context=None):
    scene = scene or getattr(bpy.context, "scene", None)
    if not scene:
        return

    # Fresnel = Toggle checkbox + Power slider 0..1 (inverted:
    # 0 -> Power 10, 1 -> Power 0) + Scaler slider 0..1
    # (0 -> Scaler 1, 1 -> Scaler 10).
    use_fresnel = 1.0 if getattr(scene, "gi_use_fresnel", False) else 0.0
    try:
        fresnel_power_slider = max(0.0, min(1.0, float(getattr(scene, "gi_fresnel_power", 0.0))))
    except Exception:
        fresnel_power_slider = 0.0
    try:
        fresnel_scaler_slider = max(0.0, min(1.0, float(getattr(scene, "gi_fresnel_scaler", 0.0))))
    except Exception:
        fresnel_scaler_slider = 0.0
    fresnel_power = 10.0 * (1.0 - fresnel_power_slider)
    fresnel_scaler = 1.0 + 9.0 * fresnel_scaler_slider
    fresnel_col = list(getattr(scene, "gi_fresnel_color", (1.0, 1.0, 1.0)))
    if len(fresnel_col) == 3:
        fresnel_col.append(1.0)

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
    catch_shadows_on = bool(getattr(scene, "gi_catch_shadows", False))
    catch_shadows = 1.0 if catch_shadows_on else 0.0
    day_night = float(getattr(scene, "gi_day_night", 0.0))
    try:
        blush_strength = max(0.0, min(1.0, float(getattr(scene, "gi_blush_strength", 0.0))))
    except Exception:
        blush_strength = 0.0

    rim_lit_col = list(getattr(scene, "gi_rim_lit_color", (1.0, 1.0, 1.0)))
    if len(rim_lit_col) == 3:
        rim_lit_col.append(1.0)

    rim_shadow_col = list(getattr(scene, "gi_rim_shadow_color", (1.0, 1.0, 1.0)))
    if len(rim_shadow_col) == 3:
        rim_shadow_col.append(1.0)

    prop_map = {
        "Toggle Fresnel": use_fresnel,
        "Fresnel Color": fresnel_col,
        "Fresnel Power": fresnel_power,
        "Fresnel Scaler": fresnel_scaler,
        "Ambient Colour": amb_col,
        "Sharp Lit Colour": sharp_lit_col,
        "Soft Lit Colour": soft_lit_col,
        "Sharp Shadow Colour": sharp_shadow_col,
        "Soft Shadow Colour": soft_shadow_col,
        "Shadow Position": shadow_pos,
        # New shader uses boolean "Toggle Catch Shadows"; keep legacy
        # float "Catch Shadows" for older shader versions.
        "Toggle Catch Shadows": catch_shadows_on,
        "Catch Shadows": catch_shadows,
        "Day/Night": day_night,
        "Warm / Cold Ramps": day_night,
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

    if not target_trees and not target_materials:
        for ng in bpy.data.node_groups:
            if "global material properties" in ng.name.lower():
                target_trees.add(ng)

    def _coerce_value(sock_or_item, value):
        # Bool sockets/items (ex. "Toggle Fresnel") reject float with
        # TypeError (expected True/False or 0/1), which used to be swallowed
        # and the toggle silently never applied.
        try:
            if type(sock_or_item) is bpy.types.NodeSocketBool:
                return bool(value > 0.5 if isinstance(value, (int, float)) else value)
        except Exception:
            pass
        try:
            if getattr(sock_or_item, "socket_type", "") == "NodeSocketBool" or \
                    type(sock_or_item).__name__ == "NodeTreeInterfaceSocketBool":
                v = value
                return bool(v > 0.5 if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
        except Exception:
            pass
        return value

    is_lp_mode = (getattr(scene, "gi_lighting_control_type", "PANEL") == "PANEL")
    lp_inputs_to_preserve = {
        "Ambient Colour", "Ambient Color", "Sharp Lit Colour", "Sharp Lit Color",
        "Soft Lit Colour", "Soft Lit Color", "Sharp Shadow Colour", "Sharp Shadow Color",
        "Soft Shadow Colour", "Soft Shadow Color", "Rim Lit", "Rim Shadow",
        "Rim Scale", "Toggle Fresnel", "Fresnel Color", "Fresnel Power", "Fresnel Scaler",
        "Shadow Position Offset", "Shadow Position"
    }

    # 3. Update inside each target Global Material Properties node group
    for tree in target_trees:
        out_node = tree.nodes.get("Global Properties") or tree.nodes.get("Group Output")
        if out_node:
            for inp in out_node.inputs:
                if is_lp_mode and inp.name in lp_inputs_to_preserve:
                    continue
                if inp.name in prop_map:
                    for l in list(inp.links):
                        tree.links.remove(l)
                    try:
                        inp.default_value = _coerce_value(inp, prop_map[inp.name])
                    except Exception:
                        pass

        if hasattr(tree, "interface") and hasattr(tree.interface, "items_tree"):
            for item in tree.interface.items_tree:
                if is_lp_mode and item.name in lp_inputs_to_preserve:
                    continue
                if item.name in prop_map:
                    try:
                        item.default_value = _coerce_value(item, prop_map[item.name])
                    except Exception:
                        pass

    # 4. Also update direct group node inputs on character materials if any exist (e.g. PrimoToon v4.0)
    prop_aliases = {
        "Toggle Fresnel": ["Toggle Fresnel", "Use Fresnel"],
        "Fresnel Color": ["Fresnel Color"],
        "Fresnel Power": ["Fresnel Power", "Fresnel Size"],
        "Fresnel Scaler": ["Fresnel Scaler", "Fresnel Multiplier"],
        "Ambient Colour": ["Ambient Colour", "Ambient Color"],
        "Sharp Lit Colour": ["Sharp Lit Colour", "Sharp Lit Color"],
        "Soft Lit Colour": ["Soft Lit Colour", "Soft Lit Color"],
        "Sharp Shadow Colour": ["Sharp Shadow Colour", "Sharp Shadow Color"],
        "Soft Shadow Colour": ["Soft Shadow Colour", "Soft Shadow Color"],
        "Shadow Position": ["Shadow Position", "Shadow Position Offset"],
        "Toggle Catch Shadows": ["Toggle Catch Shadows", "Catch Shadows"],
        "Catch Shadows": ["Toggle Catch Shadows", "Catch Shadows"],
        "Day/Night": ["Warm / Cold Ramps", "Day/Night"],
        "Warm / Cold Ramps": ["Warm / Cold Ramps", "Day/Night"],
        "Rim Lit": ["Rim Lit"],
        "Rim Shadow": ["Rim Shadow"],
    }

    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    for canonical_name, val in prop_map.items():
                        if is_lp_mode and (canonical_name in lp_inputs_to_preserve or canonical_name in [
                            "Ambient Colour", "Sharp Lit Colour", "Soft Lit Colour",
                            "Sharp Shadow Colour", "Soft Shadow Colour", "Rim Lit", "Rim Shadow",
                            "Rim Scale", "Toggle Fresnel", "Fresnel Color", "Fresnel Power",
                            "Fresnel Scaler", "Shadow Position"
                        ]):
                            continue
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

    # 4b. Blush Strength lives on the face material's shader node
    # (e.g. HoYoToon/PrimoToon "Blush Strength", 0..1), not in Global Properties.
    # Only face shader node groups expose this input, so setting it wherever
    # the socket exists is inherently face-scoped.
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    blush_inp = node.inputs.get("Blush Strength") or node.inputs.get("Face Blush Strength")
                    if blush_inp is not None:
                        try:
                            blush_inp.default_value = float(blush_strength)
                        except Exception:
                            pass

    # 4c. Character-specific shader overrides (e.g. Danica face Cold/Warm Shadow Color 2 & 3 pure white)
    try:
        from setup_wizard.replace_default_materials_setup.game_default_material_replacers import apply_character_shader_overrides
        apply_character_shader_overrides()
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

        if mats:
            ensure_character_node_trees_isolated(arm, mats)

        _is_updating_gi_props = True
        try:
            # 1. Pull Outlines & Night Soul states from character meshes.
            # Scan all rig meshes until the first outline modifier is found
            # (old code broke out after the very first mesh even when it had
            # no outline modifier, leaving the checkbox out of sync).
            found_outlines = False
            for mesh in _iter_rig_meshes(arm):
                for mod in getattr(mesh, "modifiers", []):
                    if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                        v24 = get_modifier_property(mod, "Socket_24")
                        if v24 is None:
                            v24 = get_modifier_property(mod, "Toggle Outlines")
                        if v24 is not None:
                            scene.gi_enable_outlines = bool(v24)
                        elif not arm.get("gi_animate_mode", False):
                            scene.gi_enable_outlines = bool(mod.show_viewport)

                        v23 = get_modifier_property(mod, "Socket_23")
                        if v23 is None:
                            v23 = get_modifier_property(mod, "Toggle Night Soul State")
                        if v23 is not None:
                            scene.gi_enable_night_soul = bool(v23)
                        found_outlines = True
                        break
                if found_outlines:
                    break

            # 2. Detect & pull lighting control type and preset for this character
            from setup_wizard.character_rig_setup.lighting_panel_setup import is_lighting_panel_connected
            lp_connected = is_lighting_panel_connected(target_materials=mats)
            saved_ctrl = arm.get("gi_lighting_control_type")
            if saved_ctrl in ("PANEL", "THIS_PANEL"):
                ctrl_type = saved_ctrl
            else:
                ctrl_type = "PANEL" if lp_connected else "THIS_PANEL"

            scene.gi_lighting_control_type = ctrl_type
            arm["gi_lighting_control_type"] = ctrl_type

            detected_mode = detect_character_light_mode(arm, mats=mats, context=context)
            saved_mode = arm.get("gi_light_mode")
            if saved_mode is not None:
                saved_mode = str(saved_mode)
                if saved_mode == "7" or (saved_mode not in GI_LIGHT_PRESETS and saved_mode != "6"):
                    saved_mode = None

            final_mode = saved_mode if saved_mode is not None else str(detected_mode)
            if final_mode not in GI_LIGHT_PRESETS and final_mode != "6":
                final_mode = "0"

            arm["gi_light_mode"] = final_mode
            if getattr(scene, "gi_light_mode", "") != final_mode:
                scene.gi_light_mode = final_mode

            # Pull animate mode saved on this armature
            from setup_wizard.genshin_animate_mode import is_genshin_animate_mode
            scene["gi_animate_mode"] = bool(is_genshin_animate_mode(arm, context=context))

            if mats:
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
                            primo_node = (
                                m.node_tree.nodes.get("HoYoToon")
                                or m.node_tree.nodes.get("PrimoToon")
                                or m.node_tree.nodes.get("Body Shader")
                            )
                            if primo_node:
                                inputs = primo_node.inputs
                                if "Toggle Fresnel" in inputs:
                                    scene.gi_use_fresnel = bool(inputs["Toggle Fresnel"].default_value)
                                elif "Use Fresnel" in inputs:
                                    scene.gi_use_fresnel = bool(inputs["Use Fresnel"].default_value > 0.5)
                                if "Fresnel Color" in inputs:
                                    scene.gi_fresnel_color = tuple(inputs["Fresnel Color"].default_value)[:3]
                                # Power slider is inverted: 0 -> Power 10, 1 -> Power 0.
                                power_inp = inputs.get("Fresnel Power") or inputs.get("Fresnel Size")
                                if power_inp:
                                    try:
                                        scene.gi_fresnel_power = max(0.0, min(1.0, 1.0 - float(power_inp.default_value) / 10.0))
                                    except Exception:
                                        pass
                                # Scaler slider: 0 -> Scaler 1, 1 -> Scaler 10.
                                scaler_inp = inputs.get("Fresnel Scaler") or inputs.get("Fresnel Multiplier")
                                if scaler_inp:
                                    try:
                                        scene.gi_fresnel_scaler = max(0.0, min(1.0, (float(scaler_inp.default_value) - 1.0) / 9.0))
                                    except Exception:
                                        pass
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
                                    try:
                                        v = catch_shadow_inp.default_value
                                        scene.gi_catch_shadows = bool(v > 0.5 if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                                    except Exception:
                                        scene.gi_catch_shadows = bool(catch_shadow_inp.default_value)
                                day_night_inp = inputs.get("Warm / Cold Ramps") or inputs.get("Day/Night")
                                if day_night_inp:
                                    try:
                                        scene.gi_day_night = max(0.0, min(1.0, float(day_night_inp.default_value)))
                                    except Exception:
                                        pass
                                break
                else:
                    out_node = target_tree.nodes.get("Global Properties") or target_tree.nodes.get("Group Output")
                    if out_node:
                        inputs = out_node.inputs
                        if "Toggle Fresnel" in inputs:
                            scene.gi_use_fresnel = bool(inputs["Toggle Fresnel"].default_value)
                        elif "Use Fresnel" in inputs:
                            scene.gi_use_fresnel = bool(inputs["Use Fresnel"].default_value > 0.5)
                        if "Fresnel Color" in inputs:
                            scene.gi_fresnel_color = tuple(inputs["Fresnel Color"].default_value)[:3]
                        power_inp = inputs.get("Fresnel Power") or inputs.get("Fresnel Size")
                        if power_inp:
                            try:
                                scene.gi_fresnel_power = max(0.0, min(1.0, 1.0 - float(power_inp.default_value) / 10.0))
                            except Exception:
                                pass
                        scaler_inp = inputs.get("Fresnel Scaler") or inputs.get("Fresnel Multiplier")
                        if scaler_inp:
                            try:
                                scene.gi_fresnel_scaler = max(0.0, min(1.0, (float(scaler_inp.default_value) - 1.0) / 9.0))
                            except Exception:
                                pass
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
                        catch_shadow_inp = inputs.get("Toggle Catch Shadows") or inputs.get("Catch Shadows")
                        if catch_shadow_inp:
                            try:
                                v = catch_shadow_inp.default_value
                                scene.gi_catch_shadows = bool(v > 0.5 if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                            except Exception:
                                pass
                        day_night_inp = inputs.get("Warm / Cold Ramps") or inputs.get("Day/Night")
                        if day_night_inp:
                            try:
                                scene.gi_day_night = max(0.0, min(1.0, float(day_night_inp.default_value)))
                            except Exception:
                                pass
                        if "Rim Lit" in inputs:
                            scene.gi_rim_lit_color = tuple(inputs["Rim Lit"].default_value)[:3]
                        if "Rim Shadow" in inputs:
                            scene.gi_rim_shadow_color = tuple(inputs["Rim Shadow"].default_value)[:3]
                # Blush Strength is face-material only: pull from the first
                # shader node exposing it (face materials).
                try:
                    for m in mats:
                        if not getattr(m, "node_tree", None):
                            continue
                        found_blush = False
                        for node in m.node_tree.nodes:
                            if node.type == 'GROUP' and node.node_tree:
                                blush_inp = node.inputs.get("Blush Strength") or node.inputs.get("Face Blush Strength")
                                if blush_inp is not None:
                                    try:
                                        scene.gi_blush_strength = max(0.0, min(1.0, float(blush_inp.default_value)))
                                    except Exception:
                                        pass
                                    found_blush = True
                                    break
                        if found_blush:
                            break
                except Exception:
                    pass

            # 6. Durin Dark Eyes (pulled directly from second slot material Mix Shader)
            try:
                if is_durin(context):
                    d_mesh, d_mat1, d_mat2 = get_durin_pupil_materials(context, arm)
                    target_mat = d_mat2
                    if not target_mat or not getattr(target_mat, 'node_tree', None):
                        if d_mesh and len(d_mesh.material_slots) > 1 and d_mesh.material_slots[1].material:
                            target_mat = d_mesh.material_slots[1].material
                        else:
                            target_mat = bpy.data.materials.get(DURIN_NORMAL_EYE_MATERIAL_NAME)
                            if target_mat is not None and not getattr(target_mat, 'node_tree', None):
                                target_mat = None
                            if target_mat is None:
                                for m in bpy.data.materials:
                                    m_low = m.name.lower()
                                    if ('pupil' in m_low or 'pupila' in m_low) and (m.name.endswith('.001') or 'two' in m_low) and getattr(m, 'node_tree', None):
                                        target_mat = m
                                        break
                    if target_mat and getattr(target_mat, 'node_tree', None):
                        mix_n = target_mat.node_tree.nodes.get('Mix Shader')
                        if not mix_n:
                            for n in target_mat.node_tree.nodes:
                                if n.type == 'MIX_SHADER':
                                    mix_n = n
                                    break
                        if mix_n and len(mix_n.inputs) > 0:
                            scene.gi_dark_eyes = bool(mix_n.inputs[0].default_value > 0.5)
                        else:
                            scene.gi_dark_eyes = False
                    else:
                        scene.gi_dark_eyes = False
            except Exception:
                pass
        finally:
            _is_updating_gi_props = False
    except Exception:
        pass


def _apply_outlines_and_night_soul(context, outlines_on, ns_on, arm=None):
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, _iter_rig_meshes
        from setup_wizard.utils.modifier_utils import set_modifier_property
        if arm is None:
            arm = resolve_settings_armature(context)
        meshes = list(_iter_rig_meshes(arm)) if arm else [obj for obj in bpy.data.objects if obj.type == 'MESH']
        should_show = bool(outlines_on or ns_on)
        dirty_meshes = []

        for mesh in meshes:
            has_mod = False
            for mod in getattr(mesh, "modifiers", []):
                if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                    has_mod = True
                    # Single write per socket via set_modifier_property (it already
                    # handles Blender 5 properties.inputs + legacy fallbacks).
                    # The old code additionally wrote mod["Socket_xx"] directly,
                    # doubling depsgraph updates per modifier.
                    set_modifier_property(mod, "Socket_24", outlines_on)
                    set_modifier_property(mod, "Toggle Outlines", outlines_on)
                    set_modifier_property(mod, "Socket_23", ns_on)
                    set_modifier_property(mod, "Toggle Night Soul State", ns_on)

                    # show_viewport=False skips GN evaluation entirely: this is
                    # the fast path that makes "outlines off" much faster.
                    # Only touch it when it actually changes to avoid a
                    # depsgraph rebuild per modifier.
                    if mod.show_viewport != should_show:
                        mod.show_viewport = should_show
                    try:
                        if mod.show_render != should_show:
                            mod.show_render = should_show
                    except Exception:
                        pass

            if has_mod:
                dirty_meshes.append(mesh)

        # Batch tags: one pass at the end instead of per-mesh update + redraw.
        for mesh in dirty_meshes:
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
    # Fast path: per-armature cache. character_has_night_soul() runs on every
    # Character Settings panel draw, so a global scan of bpy.data.materials
    # on each redraw is wasted work. The Night Soul state of a character never
    # changes after setup, so stamp it once.
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, _iter_rig_meshes, get_character_materials
        from setup_wizard.utils.modifier_utils import get_modifier_property
        arm = resolve_settings_armature(context)
        if arm is not None:
            try:
                cached = arm.get("gacha_has_night_soul")
                if cached is not None:
                    return bool(cached)
            except Exception:
                pass
        if arm:
            for mesh in _iter_rig_meshes(arm):
                for mod in getattr(mesh, "modifiers", []):
                    if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                        ns_mat = get_modifier_property(mod, "Socket_10")
                        if not ns_mat:
                            ns_mat = get_modifier_property(mod, "Night Soul Outline")
                        if ns_mat:
                            # A Night Soul outline material is always bound by
                            # setup (base fallback), so only count it when the
                            # character actually has NYX textures.
                            has_nyx = False
                            try:
                                _, _mats = get_character_materials(context, arm)
                                for mat in _mats:
                                    if not getattr(mat, "node_tree", None):
                                        continue
                                    for n_name in ['Main_NYXmask', 'Face_NYXmask']:
                                        n = mat.node_tree.nodes.get(n_name)
                                        if n and getattr(n, 'image', None):
                                            has_nyx = True
                                            break
                                    if has_nyx:
                                        break
                            except Exception:
                                pass
                            try:
                                arm["gacha_has_night_soul"] = bool(has_nyx)
                            except Exception:
                                pass
                            return bool(has_nyx)
            _, mats = get_character_materials(context, arm)
            for mat in mats:
                if not getattr(mat, "node_tree", None):
                    continue
                for n_name in ['Main_NYXmask', 'Face_NYXmask']:
                    n = mat.node_tree.nodes.get(n_name)
                    if n and getattr(n, 'image', None):
                        try:
                            arm["gacha_has_night_soul"] = True
                        except Exception:
                            pass
                        return True
            try:
                arm["gacha_has_night_soul"] = False
            except Exception:
                pass
            return False
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


def is_durin(context):
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, resolve_character_name, _iter_rig_meshes
        arm = resolve_settings_armature(context)
        if arm is not None:
            cached = arm.get("gacha_is_durin")
            if cached is not None:
                return bool(cached)
            char_name = resolve_character_name(arm, "")
            if char_name and "durin" in str(char_name).lower():
                arm["gacha_is_durin"] = True
                return True
            if "durin" in arm.name.lower():
                arm["gacha_is_durin"] = True
                return True
            for mesh in _iter_rig_meshes(arm):
                if "durin" in mesh.name.lower():
                    arm["gacha_is_durin"] = True
                    return True
                for slot in getattr(mesh, "material_slots", []):
                    if slot.material and "durin" in slot.material.name.lower():
                        arm["gacha_is_durin"] = True
                        return True
            for mesh in _iter_rig_meshes(arm):
                for slot in getattr(mesh, "material_slots", []):
                    if slot.material and "pupil" in slot.material.name.lower():
                        import bpy
                        if any("durin" in m.name.lower() for m in bpy.data.materials) or any("durin" in o.name.lower() for o in bpy.data.objects) or any("durin" in img.name.lower() for img in bpy.data.images):
                            arm["gacha_is_durin"] = True
                            return True
            arm["gacha_is_durin"] = False
            return False
        import bpy
        obj = getattr(context, "active_object", None) or getattr(context, "object", None)
        if obj and "durin" in obj.name.lower():
            return True
        for m in bpy.data.materials:
            if "durin" in m.name.lower():
                return True
    except Exception:
        pass
    return False


def get_durin_pupil_materials(context=None, arm=None):
    from setup_wizard.ui.character_settings_utils import resolve_settings_armature, _iter_rig_meshes
    import bpy
    if arm is None:
        arm = resolve_settings_armature(context)
    if not arm:
        obj = getattr(bpy.context, "active_object", None) or getattr(bpy.context, "object", None)
        if obj and obj.type == 'MESH':
            meshes = [obj]
        else:
            meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    else:
        meshes = list(_iter_rig_meshes(arm))

    pupil_mesh = None
    for mesh in meshes:
        n_low = mesh.name.lower()
        if ('pupil' in n_low or 'pupila' in n_low or any('pupil' in s.name.lower() for s in mesh.material_slots if s.material)) and not any(ex in n_low for ex in ['face', 'eyestar', 'star', 'brow']):
            pupil_mesh = mesh
            break

    if not pupil_mesh:
        for mesh in meshes:
            for s in mesh.material_slots:
                if s.material and ('pupil' in s.material.name.lower() or 'pupila' in s.material.name.lower()) and not any(ex in s.material.name.lower() for ex in ['face', 'eyestar', 'star', 'brow']):
                    pupil_mesh = mesh
                    break
            if pupil_mesh:
                break

    if not pupil_mesh:
        return None, None, None

    mat1 = pupil_mesh.material_slots[0].material if len(pupil_mesh.material_slots) > 0 else None
    mat2 = pupil_mesh.material_slots[1].material if len(pupil_mesh.material_slots) > 1 else None
    return pupil_mesh, mat1, mat2


def apply_durin_dark_eyes(context=None, enabled=False):
    from setup_wizard.ui.character_settings_utils import resolve_settings_armature
    import bpy
    arm = resolve_settings_armature(context)
    mesh, mat1, mat2 = get_durin_pupil_materials(context, arm)

    target_val = 1.0 if enabled else 0.0

    # Ensure slot 1 (mat1) NEVER has transparent Mix Shader (always 0.0)
    if mat1 and getattr(mat1, 'node_tree', None):
        mix_n1 = mat1.node_tree.nodes.get('Mix Shader')
        if not mix_n1:
            for n in mat1.node_tree.nodes:
                if n.type == 'MIX_SHADER':
                    mix_n1 = n
                    break
        if mix_n1 and len(mix_n1.inputs) > 0:
            try:
                mix_n1.inputs[0].driver_remove('default_value')
            except Exception:
                pass
            mix_n1.inputs[0].default_value = 0.0

    # Target ONLY the second slot (mat2)
    target_mat = mat2
    if not target_mat or not getattr(target_mat, 'node_tree', None):
        if mesh and len(mesh.material_slots) > 1 and mesh.material_slots[1].material:
            target_mat = mesh.material_slots[1].material
        else:
            target_mat = bpy.data.materials.get(DURIN_NORMAL_EYE_MATERIAL_NAME)
            if target_mat is not None and not getattr(target_mat, 'node_tree', None):
                target_mat = None
            if target_mat is None:
                for m in bpy.data.materials:
                    m_low = m.name.lower()
                    if ('pupil' in m_low or 'pupila' in m_low) and (m.name.endswith('.001') or 'two' in m_low) and getattr(m, 'node_tree', None):
                        target_mat = m
                        break

    if target_mat and getattr(target_mat, 'node_tree', None):
        nt = target_mat.node_tree
        mix_node = nt.nodes.get('Mix Shader')
        if not mix_node:
            for n in nt.nodes:
                if n.type == 'MIX_SHADER':
                    mix_node = n
                    break
        if mix_node and len(mix_node.inputs) > 0:
            try:
                mix_node.inputs[0].driver_remove('default_value')
            except Exception:
                pass
            mix_node.inputs[0].default_value = target_val
            target_mat.blend_method = 'HASHED'
            if hasattr(target_mat, 'surface_render_method'):
                target_mat.surface_render_method = 'DITHERED'

    # Tag redraw on 3D viewports so the change shows immediately
    if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
        for win in getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()


def update_gi_dark_eyes(self, context):
    global _is_updating_gi_props
    if _is_updating_gi_props:
        return
    enabled = getattr(self, "gi_dark_eyes", False)
    apply_durin_dark_eyes(context, enabled)


class GI_OT_SetupLightingPanel(Operator):
    bl_idname = "genshin.setup_lighting_panel"
    bl_label = "Setup 3D Lighting Panel"
    bl_description = "Imports LightingPanel.blend, attaches it to the character rig and links it to material shaders"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.ui.character_settings_utils import is_game_armature, resolve_settings_armature
            arm = resolve_settings_armature(context)
            return bool(arm and is_game_armature(context, "GENSHIN_IMPACT"))
        except Exception:
            return False

    def execute(self, context):
        import os
        from setup_wizard.ui.character_settings_utils import (
            resolve_settings_armature,
            get_character_materials,
            _iter_rig_meshes,
        )
        from setup_wizard.geometry_nodes_setup.lighting_panel_names import LightingPanelNames
        from setup_wizard.utils.modifier_utils import set_modifier_property
        from setup_wizard.character_rig_setup.lighting_panel_setup import (
            LightingPanelFileNamesFactory,
            LightingPanel,
            move_into_collection,
            armature_has_lighting_panel,
            set_lighting_panel_visibility,
        )
        from setup_wizard.domain.shader_identifier_service import ShaderIdentifierServiceFactory

        arm = resolve_settings_armature(context)
        if not arm:
            self.report({'ERROR'}, "No Genshin character armature found.")
            return {'CANCELLED'}

        arm, mats = get_character_materials(context, arm)

        if armature_has_lighting_panel(arm):
            lp = LightingPanel("")
            lp.connect_lighting_panel_nodes_to_global_material_properties(target_materials=mats)
            set_lighting_panel_visibility(arm, True)
            arm["gi_lighting_control_type"] = "PANEL"
            context.scene.gi_lighting_control_type = "PANEL"
            arm["gi_light_mode"] = "0"
            context.scene.gi_light_mode = "0"
            self.report({'INFO'}, "Lighting Panel already present in rig. Connected to shaders!")
            return {'FINISHED'}

        try:
            from setup_wizard.domain.game_types import GameType
            from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders
            service = ShaderIdentifierServiceFactory.create(GameType.GENSHIN_IMPACT.name)
            shader = service.identify_shader(bpy.data.materials, bpy.data.node_groups) or GenshinImpactShaders.V4_GENSHIN_IMPACT_SHADER
        except Exception:
            from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders
            shader = GenshinImpactShaders.V4_GENSHIN_IMPACT_SHADER

        lp_file_names = LightingPanelFileNamesFactory.create(shader)
        lp_filepath = lp_file_names.LIGHTING_PANEL_FILEPATH

        if not os.path.exists(lp_filepath):
            self.report({'ERROR'}, f"LightingPanel.blend not found at {lp_filepath}")
            return {'CANCELLED'}

        inner_path = 'Collection'
        try:
            bpy.ops.wm.append(
                filepath=os.path.join(lp_filepath, inner_path, LightingPanelNames.Collections.LIGHTING_PANEL),
                directory=os.path.join(lp_filepath, inner_path),
                files=[{'name': LightingPanelNames.Collections.LIGHTING_PANEL}],
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to append Lighting Panel: {e}")
            return {'CANCELLED'}

        lp_rig_obj = bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL)
        if not lp_rig_obj:
            self.report({'ERROR'}, "Lighting Panel object not found after append.")
            return {'CANCELLED'}

        char_name = arm.name.replace("Rig", "").replace("rig", "").strip()

        target_char_coll = None
        for c in arm.users_collection:
            if c.name.lower() not in ["collection", "wgt"]:
                target_char_coll = c.name
                break
        if not target_char_coll:
            target_char_coll = char_name if bpy.data.collections.get(char_name) else "wgt"

        to_del_coll = bpy.data.collections.get(LightingPanelNames.Collections.WIDGET_COLLECTION)
        if to_del_coll:
            for obj in list(to_del_coll.objects):
                move_into_collection(obj.name, "wgt")
        to_del_coll = bpy.data.collections.get(LightingPanelNames.Collections.PICKER)
        if to_del_coll:
            for obj in list(to_del_coll.objects):
                move_into_collection(obj.name, "wgt")
        to_del_coll = bpy.data.collections.get(LightingPanelNames.Collections.WHEEL)
        if to_del_coll:
            for obj in list(to_del_coll.objects):
                move_into_collection(obj.name, target_char_coll)

        move_into_collection(LightingPanelNames.Objects.LIGHTING_PANEL, target_char_coll, include_children=False)
        _lp_coll = bpy.data.collections.get(LightingPanelNames.Collections.LIGHTING_PANEL)
        if _lp_coll:
            try:
                bpy.data.collections.remove(_lp_coll, do_unlink=True)
            except Exception:
                pass

        for mesh in _iter_rig_meshes(arm):
            for mod in getattr(mesh, "modifiers", []):
                if mod.type == 'NODES' and mod.node_group and 'Light Vectors' in mod.node_group.name:
                    for modifier_input_name, object_name in LightingPanelNames.LIGHT_VECTORS_MODIFIER_INPUT_NAME_TO_OBJECT_NAME:
                        try:
                            val = bpy.data.objects.get(f"{object_name}_{char_name}") or bpy.data.objects.get(object_name)
                            if val:
                                set_modifier_property(mod, modifier_input_name, val)
                        except KeyError:
                            pass

        try:
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        bpy.ops.object.select_all(action='DESELECT')
        lp_rig_obj.select_set(True)
        arm.select_set(True)
        context.view_layer.objects.active = arm
        bpy.ops.object.join()

        bpy.ops.object.mode_set(mode='EDIT')
        head_bone = arm.data.edit_bones.get("head") or arm.data.edit_bones.get("Head")
        lp_bone = arm.data.edit_bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
        if lp_bone and head_bone:
            lp_bone.parent = head_bone

        bpy.ops.object.mode_set(mode='OBJECT')

        if arm.pose and arm.pose.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL):
            arm.pose.bones[LightingPanelNames.Bones.LIGHTING_PANEL].lock_scale = (True, True, True)
        if arm.data and arm.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL):
            arm.data.bones[LightingPanelNames.Bones.LIGHTING_PANEL].inherit_scale = 'NONE'

        from setup_wizard.character_rig_setup.rig_ui_utils import setup_standard_bone_collections
        try:
            setup_standard_bone_collections(arm)
        except Exception:
            pass

        lp = LightingPanel("")
        lp.connect_lighting_panel_nodes_to_global_material_properties(target_materials=mats)

        arm["gi_lighting_control_type"] = "PANEL"
        context.scene.gi_lighting_control_type = "PANEL"
        arm["gi_light_mode"] = "0"
        context.scene.gi_light_mode = "0"

        for win in getattr(context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()

        self.report({'INFO'}, "Lighting Panel successfully attached and linked to character settings!")
        return {'FINISHED'}


class GI_OT_SelectLightingPanel(Operator):
    bl_idname = "genshin.select_lighting_panel"
    bl_label = "Select 3D Lighting Panel"
    bl_description = "Selects the Lighting Panel controls in Pose Mode in the 3D viewport"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
            arm = resolve_settings_armature(context)
            return bool(arm and armature_has_lighting_panel(arm))
        except Exception:
            return False

    def execute(self, context):
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        from setup_wizard.geometry_nodes_setup.lighting_panel_names import LightingPanelNames
        arm = resolve_settings_armature(context)
        if not arm:
            return {'CANCELLED'}
        try:
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='POSE')
        for b in arm.data.bones:
            b.select = False
        lp_b = arm.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
        if lp_b:
            lp_b.select = True
            arm.data.bones.active = lp_b
        for pin in ["AmbientPin", "LitPin", "ShadowPin"]:
            b = arm.data.bones.get(pin)
            if b:
                b.select = True
        return {'FINISHED'}


class GI_OT_ToggleLightingPanelVisibility(Operator):
    bl_idname = "genshin.toggle_lighting_panel_visibility"
    bl_label = "Toggle Lighting Panel Visibility"
    bl_description = "Shows or hides the Lighting Panel controls in the viewport"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
            arm = resolve_settings_armature(context)
            return bool(arm and armature_has_lighting_panel(arm))
        except Exception:
            return False

    def execute(self, context):
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        from setup_wizard.character_rig_setup.lighting_panel_setup import is_lighting_panel_visible, set_lighting_panel_visibility
        arm = resolve_settings_armature(context)
        if not arm:
            return {'CANCELLED'}
        vis = is_lighting_panel_visible(arm)
        set_lighting_panel_visibility(arm, not vis)
        for win in getattr(context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        return {'FINISHED'}


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

        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, has_active_character_changed
        arm = resolve_settings_armature(context)

        # Defer property pull to avoid illegal ID write in draw context
        if has_active_character_changed(context):
            def _deferred_pull():
                try:
                    pull_gi_panel_values(bpy.context.scene, bpy.context, force=True)
                    for win in getattr(bpy.context.window_manager, 'windows', []):
                        screen = getattr(win, 'screen', None)
                        if screen:
                            for area in screen.areas:
                                if area.type == 'VIEW_3D':
                                    area.tag_redraw()
                except Exception:
                    pass
                return None
            try:
                bpy.app.timers.register(_deferred_pull, first_interval=0.0)
            except Exception:
                pass

        # 0. Animate Mode (fast playback: lightweight materials, no outlines)
        from setup_wizard.genshin_animate_mode import is_genshin_animate_mode
        is_anim = is_genshin_animate_mode(arm, context=context)
        layout.operator(
            "genshin.toggle_animate_mode",
            text="Disable Animate Mode" if is_anim else "Enable Animate Mode",
            icon="SHADING_TEXTURE" if is_anim else "RESTRICT_RENDER_OFF"
        )

        # 1. Lighting Type
        col_type = layout.column(align=False)
        col_type.label(text="Lighting Type:")
        row_btn = col_type.row(align=True)
        row_btn.prop(scene, "gi_lighting_control_type", expand=True)

        is_lp_mode = (getattr(scene, "gi_lighting_control_type", "PANEL") == "PANEL")

        from setup_wizard.character_rig_setup.lighting_panel_setup import (
            armature_has_lighting_panel,
        )
        has_lp = armature_has_lighting_panel(arm)

        if is_lp_mode:
            # Lighting Panel mode: controls are in 3D viewport, remove 3D active box/select/hide buttons
            if not has_lp:
                col_type.operator("genshin.setup_lighting_panel", text="Add 3D Lighting Panel to Rig", icon="LIGHT")
        else:
            # This Panel mode: show Lighting Mode label and preset dropdown
            col_preset = layout.column(align=True)
            col_preset.label(text="Lighting Mode:")
            col_preset.prop(scene, "gi_light_mode", text="")
            if getattr(scene, "gi_light_mode", "0") == "6":
                box_col = col_preset.box()
                box_col.label(text="Custom Colors", icon="COLOR")
                col_colors = box_col.column(align=True)
                col_colors.prop(scene, "gi_amb_color", text="Ambient")
                col_colors.prop(scene, "gi_sharp_lit_color", text="Sharp Lit")
                col_colors.prop(scene, "gi_soft_lit_color", text="Soft Lit")
                col_colors.prop(scene, "gi_sharp_shadow_color", text="Sharp Shadow")
                col_colors.prop(scene, "gi_soft_shadow_color", text="Soft Shadow")
                col_colors.prop(scene, "gi_rim_lit_color", text="Rim Lit")
                col_colors.prop(scene, "gi_rim_shadow_color", text="Rim Shadow")

        # 3. Fresnel (Toggle checkbox + Power slider + Scaler slider)
        # In Lighting Panel mode, Toggle Fresnel must NOT be visible
        if not is_lp_mode:
            col_fresnel = layout.column(align=True)
            col_fresnel.prop(scene, "gi_use_fresnel", text="Toggle Fresnel")
            if getattr(scene, "gi_use_fresnel", False):
                box_fr = col_fresnel.box()
                box_fr.label(text="Fresnel Options", icon="SHADING_RENDERED")
                col_fr_props = box_fr.column(align=True)
                col_fr_props.prop(scene, "gi_fresnel_color", text="Fresnel Color")
                col_fr_props.prop(scene, "gi_fresnel_power", text="Fresnel Power", slider=True)
                col_fr_props.prop(scene, "gi_fresnel_scaler", text="Fresnel Scaler", slider=True)

        # 4. Outlines Settings
        box_outlines = layout.box()
        box_outlines.label(text="Outlines", icon="STROKE")
        col_outlines = box_outlines.column(align=True)
        col_outlines.prop(scene, "gi_enable_outlines", text="Enable Outlines")
        if character_has_night_soul(context):
            col_outlines.prop(scene, "gi_enable_night_soul", text="Enable Night Soul (Natlan Characters Only)")

        # Dark Eyes (Durin Only)
        if is_durin(context):
            box_durin = layout.box()
            box_durin.label(text="Durin Settings", icon="HIDE_OFF")
            col_durin = box_durin.column(align=True)
            col_durin.prop(scene, "gi_dark_eyes", text="Dark Eyes")

        # 5. Shadows & Scene Settings (At the bottom)
        box_shadow = layout.box()
        box_shadow.label(text="Shadow & Scene Settings", icon="SHADING_SOLID")
        col_shadow = box_shadow.column(align=True)
        # In Lighting Panel mode, Shadow Position and Day / Night must NOT be visible
        if not is_lp_mode:
            col_shadow.prop(scene, "gi_shadow_position", text="Shadow Position", slider=True)
        col_shadow.prop(scene, "gi_catch_shadows", text="Catch Shadows")
        if not is_lp_mode:
            col_shadow.prop(scene, "gi_day_night", text="Day / Night", slider=True)
        col_shadow.prop(scene, "gi_blush_strength", text="Blush Strength", slider=True)

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


_LAST_CHECKED_ACTIVE = None


@bpy.app.handlers.persistent
def _on_character_selection_change(scene, depsgraph=None):
    global _LAST_CHECKED_ACTIVE
    try:
        act = getattr(bpy.context.view_layer.objects, "active", None)
        if act == _LAST_CHECKED_ACTIVE:
            return
        _LAST_CHECKED_ACTIVE = act

        from setup_wizard.ui.character_settings_utils import has_active_character_changed, is_game_armature
        context = bpy.context
        if has_active_character_changed(context):
            if is_game_armature(context, "GENSHIN_IMPACT"):
                pull_gi_panel_values(scene, context, force=True)
    except Exception:
        pass



def register_gi_properties():
    if _on_character_selection_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_character_selection_change)

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

    bpy.types.Scene.gi_lighting_control_type = bpy.props.EnumProperty(
        items=[
            ("PANEL", "Lighting Panel", "Use 3D Lighting Panel rig controls in viewport"),
            ("THIS_PANEL", "This Panel", "Use Character Settings panel controls"),
        ],
        name="Lighting Type",
        description="Choose whether to control lighting via 3D Lighting Panel or This Panel",
        default="PANEL",
        update=update_gi_lighting_control_type,
    )

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
        name="Lighting Preset",
        description="Select lighting mode / preset",
        default="0",
        update=update_gi_light_mode,
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
    bpy.types.Scene.gi_use_fresnel = bpy.props.BoolProperty(
        name="Toggle Fresnel",
        description="Toggle Fresnel rim lighting",
        default=False,
        update=update_gi_fresnel,
    )
    bpy.types.Scene.gi_fresnel_power = bpy.props.FloatProperty(
        name="Fresnel Power",
        description="Fresnel Power slider 0..1 (inverted): 0 sets Power to 10, 1 sets Power to 0",
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_gi_fresnel,
    )
    bpy.types.Scene.gi_fresnel_scaler = bpy.props.FloatProperty(
        name="Fresnel Scaler",
        description="Fresnel Scaler slider 0..1: 0 sets Scaler to 1, 1 sets Scaler to 10",
        min=0.0,
        max=1.0,
        default=0.0,
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
        update=update_gi_scene_settings,
    )
    bpy.types.Scene.gi_catch_shadows = bpy.props.BoolProperty(
        name="Catch Shadows",
        description="Enable scene shadows",
        default=False,
        update=update_gi_scene_settings,
    )
    bpy.types.Scene.gi_day_night = bpy.props.FloatProperty(
        name="Day / Night",
        description="Day/Night lighting transition",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=2,
        update=update_gi_scene_settings,
    )
    bpy.types.Scene.gi_blush_strength = bpy.props.FloatProperty(
        name="Blush Strength",
        description="Blush Strength (face material only)",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=2,
        update=update_gi_scene_settings,
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
    bpy.types.Scene.gi_dark_eyes = bpy.props.BoolProperty(
        name="Dark Eyes",
        description="Toggle Durin's dark eyes. When enabled (1), sets Mix Shader Fac to 1 (transparent BSDF, revealing slot 1 dark eyes). When disabled (0), sets Mix Shader Fac to 0",
        default=False,
        update=update_gi_dark_eyes,
    )


def unregister_gi_properties():
    if _on_character_selection_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_character_selection_change)

    for prop in [
        "gi_lighting_control_type", "gi_light_mode", "gi_use_fresnel", "gi_fresnel_color", "gi_fresnel_size", "gi_fresnel_power", "gi_fresnel_scaler",
        "gi_amb_color", "gi_sharp_lit_color", "gi_soft_lit_color",
        "gi_sharp_shadow_color", "gi_soft_shadow_color", "gi_shadow_position",
        "gi_catch_shadows", "gi_day_night", "gi_blush_strength",
        "gi_rim_lit_color", "gi_rim_shadow_color",
        "gi_hair_physics_influence", "gi_clothes_physics_influence",
        "gi_enable_outlines", "gi_enable_night_soul", "gi_dark_eyes"
    ]:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


@bpy.app.handlers.persistent
def gi_frame_change_handler(scene, depsgraph=None):
    try:
        sync_genshin_shader_properties(scene)
    except Exception:
        pass
