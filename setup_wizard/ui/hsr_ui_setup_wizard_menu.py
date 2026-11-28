from setup_wizard.character_rig_setup.rig_ui_utils import rig_conversion_available
from setup_wizard.utilites.new_lights import draw_lights_plus
# Author: michael-gh1

import bpy
from bpy.types import Panel, UILayout

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.ui_render_checker import HonkaiStarRailUIRenderChecker


class HSR_PT_Setup_Wizard_UI_Layout(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Honkai Star Rail Setup Wizard"
    bl_idname = "HSR_PT_Setup_Wizard_UI_Layout"
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
            "honkai_star_rail.setup_wizard_ui",
            "Setup Character",
            "PLAY",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        from setup_wizard.services.isolation import isolation_service
        isolation_service.draw_setup_status_box(sub_layout, context, run_entire_setup_column)

        settings_box = layout.box()
        settings_header = settings_box.row()
        settings_header.label(text="Setup Settings", icon="PREFERENCES")

        settings_col = settings_box.column()
        props = context.scene.character_rigger_props
        settings_col.prop(props, "disable_rigging", text="Disable Rigging")


class HSR_PT_Basic_Setup_Wizard_UI_Layout(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "HSR_PT_UI_Basic_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"
    bl_parent_id = 'CSW_PT_Old_Setup_UI_Layout'
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        set_up_character_column = sub_layout.column()
        OperatorFactory.create(
            set_up_character_column,
            "honkai_star_rail.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )

        OperatorFactory.create(
            sub_layout,
            "honkai_star_rail.set_up_materials",
            "Set Up Materials",
            icon="MATERIAL",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        if bpy.app.version >= (3, 3, 0):
            OperatorFactory.create(
                sub_layout,
                "honkai_star_rail.set_up_outlines",
                "Set Up Outlines",
                icon="GEOMETRY_NODES",
                game_type=GameType.HONKAI_STAR_RAIL.name,
            )
        else:
            layout.label(text="(Outlines Disabled < v3.3.0)")
        OperatorFactory.create(
            sub_layout,
            "genshin.fix_transformations",
            "Fix Transformations",
            "OBJECT_DATA",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )

        OperatorFactory.create_rig_character_ui(sub_layout)

        sub_layout.operator(
            "honkai_star_rail.create_shapekey_panel",
            text="Create Shapekey Panel",
            icon="FACE_MAPS",
        )

        OperatorFactory.create(
            sub_layout,
            "honkai_star_rail.finish_setup",
            "Finish Setup",
            icon="CHECKMARK",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )


class HSR_PT_Advanced_Setup_Wizard_UI_Layout(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Advanced Setup"
    bl_idname = "HSR_PT_UI_Advanced_Setup_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"
    bl_parent_id = 'CSW_PT_Old_Setup_UI_Layout'
    bl_order = 2
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout


class HSR_PT_UI_Character_Model_Menu(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Set Up Character Menu"
    bl_idname = "HSR_PT_UI_Character_Model_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HSR_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.box()

        import_character_model_column = sub_layout.column()
        OperatorFactory.create(
            import_character_model_column,
            "genshin.import_model",
            "Import Character Model",
            "OUTLINER_OB_ARMATURE",
        )

        OperatorFactory.create(
            sub_layout, "genshin.delete_empties", "Delete Empties", "TRASH"
        )
        OperatorFactory.create(
            sub_layout, "genshin.reorient_bones", "Fix Orientation", "BONE_DATA"
        )


class HSR_PT_UI_Materials_Menu(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Set Up Materials Menu"
    bl_idname = "HSR_PT_UI_Materials_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HSR_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout,
            "genshin.import_materials",
            "Import HSR Materials",
            "MATERIAL",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.replace_default_materials",
            "Replace Default Materials",
            "ARROW_LEFTRIGHT",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.import_textures",
            "Import Character Textures",
            "TEXTURE",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )


class HSR_PT_UI_Outlines_Menu(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Set Up Outlines Menu"
    bl_idname = "HSR_PT_UI_Outlines_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HSR_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()
        scene = context.scene

        if bpy.app.version >= (3, 3, 0):
            OperatorFactory.create(
                sub_layout,
                "genshin.import_outlines",
                "Import Outlines",
                "FILE_FOLDER",
                game_type=GameType.HONKAI_STAR_RAIL.name,
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.setup_geometry_nodes",
                "Set Up Geometry Nodes",
                "GEOMETRY_NODES",
                game_type=GameType.HONKAI_STAR_RAIL.name,
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.import_outline_lightmaps",
                "Import Outline Lightmaps",
                "FILE_FOLDER",
                game_type=GameType.HONKAI_STAR_RAIL.name,
            )

            sub_layout = layout.box()
            sub_layout.prop_search(
                scene,
                "setup_wizard_material_for_material_data_import",
                bpy.data,
                "materials",
            )
            sub_layout.prop_search(
                scene,
                "setup_wizard_outlines_material_for_material_data_import",
                bpy.data,
                "materials",
            )
            OperatorFactory.create(
                sub_layout,
                "genshin.import_material_data",
                "Import Material Data",
                "FILE",
                game_type=GameType.HONKAI_STAR_RAIL.name,
                setup_mode="ADVANCED",
            )
        else:
            layout.label(text="(Outlines Disabled < v3.3.0)")


class HSR_PT_UI_Finish_Setup_Menu(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Finish Setup Menu"
    bl_idname = "HSR_PT_UI_Misc_Setup_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HSR_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()

        OperatorFactory.create(
            sub_layout, "genshin.setup_head_driver", "Set Up Head Driver", "CONSTRAINT"
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_color_management_to_standard",
            "Set Color Mgmt to Standard",
            "SCENE",
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.set_up_screen_space_reflections",
            "Enable SSR",
            "SCENE",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.vertex_paint_face_see_through_effect",
            "Vertex Paint Face",
            "VPAINT_HLT",
            game_type=GameType.HONKAI_STAR_RAIL.name,
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
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        OperatorFactory.create(
            sub_layout,
            "genshin.set_up_armtwist_bone_constraints",
            "Set Up ArmTwist Bone Constraints",
            "CONSTRAINT_BONE",
        )


class HSR_PT_UI_Character_Rig_Setup_Menu(Panel, HonkaiStarRailUIRenderChecker):
    bl_label = "Character Rig Menu"
    bl_idname = "HSR_PT_Rigify_Setup_Menu"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "HSR_PT_UI_Advanced_Setup_Layout"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sub_layout = layout.column()
        box = sub_layout.box()

        character_rigger_props = context.scene.character_rigger_props

        OperatorFactory.create_rig_character_ui(box)
        OperatorFactory.create(
            box,
            "hoyoverse.fix_light_direction",
            "Fix Light Direction",
            "LIGHT_SUN",
            game_type=GameType.HONKAI_STAR_RAIL.name,
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
            game_type=GameType.HONKAI_STAR_RAIL.name,
            operator_context="INVOKE_DEFAULT",
        )
        col = box.column()
        col.prop(character_rigger_props, "allow_arm_ik_stretch")
        col.prop(character_rigger_props, "allow_leg_ik_stretch")
        col.prop(character_rigger_props, "use_arm_ik_poles")
        col.prop(character_rigger_props, "use_leg_ik_poles")
        col.prop(character_rigger_props, "add_children_of_constraints")
        col.prop(character_rigger_props, "use_head_tracker")
        enable_physics = getattr(character_rigger_props, "enable_hair_clothes_physics", getattr(character_rigger_props, "enable_hair_dress_physics", False))
        col.prop(character_rigger_props, "enable_hair_clothes_physics", text="Hair & Clothes Physics")
        if enable_physics:
            sliders_col = col.column()
            sliders_col.prop(character_rigger_props, "hair_physics_influence", text="Hair", slider=True)
            sliders_col.prop(character_rigger_props, "clothes_physics_influence", text="Clothes", slider=True)


# class HSR_PT_UI_Compositing_Panel_Post_Processing_UI_Layout(Panel, HonkaiStarRailUIRenderChecker):
#     bl_label = "Compositing Setup Wizard"
#     bl_idname = "HSR_PT_Custom_Compositing_Node_UI_Layout"
#     bl_space_type = "NODE_EDITOR"
#     bl_region_type = "UI"
#     bl_category = "HSR - Setup Wizard"

#     def draw(self, context):
#         layout = self.layout
#         row = layout.row()
#         sub_layout = layout.box()
#         window_manager = context.window_manager

#         row.prop(window_manager, 'cache_enabled')
#         OperatorFactory.create(
#             row,
#             'genshin.clear_cache_operator',
#             'Clear Cache',
#             'TRASH',
#             game_type=GameType.HONKAI_STAR_RAIL.name,
#         )
#         OperatorFactory.create(
#             sub_layout,
#             'genshin.change_bpy_context',
#             'Enable Use Nodes',
#             'CHECKMARK',
#             bpy_context_attr='scene.use_nodes',
#             bpy_context_value_bool=True
#         )
#         OperatorFactory.create(
#             sub_layout,
#             'hoyoverse.custom_composite_node_setup',
#             'Set Up Compositing Node',
#             'PLAY'
#         )


"""
    This factory is intended to help create a UI element's operator (or the action it takes) when pressed.
    While it currently doesn't do anything too grand, it may provide future flexibility.
"""


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
        expy_kit_installed = rig_conversion_available()
        rigify_installed = any('rigify' in k.lower() for k in bpy.context.preferences.addons.keys())

        column = ui_object.column()
        column.enabled = True if expy_kit_installed and rigify_installed else False
        OperatorFactory.create(
            column,
            "hoyoverse.set_up_character_rig",
            "Rig Character",
            "OUTLINER_OB_ARMATURE",
            game_type=GameType.HONKAI_STAR_RAIL.name,
        )
        if not column.enabled:
            column = ui_object.column()
            if not expy_kit_installed:
                column.label(text="Rig conversion add-on required", icon="ERROR")
            if not rigify_installed:
                column.label(text="Rigify required", icon="ERROR")


HSR_LIGHT_PRESETS = {
    "0": { # Default
        "ambient": (1.0, 1.0, 1.0),
        "lit": (1.0, 1.0, 1.0),
        "shadow": (1.0, 1.0, 1.0),
        "sharp_lit": (1.0, 1.0, 1.0),
        "sharp_shadow": (1.0, 1.0, 1.0),
    },
    "1": { # Sunrise
        "ambient": (0.95, 0.85, 0.8),
        "lit": (1.0, 0.88, 0.75),
        "shadow": (0.65, 0.65, 0.85),
        "sharp_lit": (1.0, 0.9, 0.8),
        "sharp_shadow": (0.6, 0.6, 0.8),
    },
    "2": { # Day
        "ambient": (1.0, 1.0, 1.0),
        "lit": (1.0, 1.0, 1.0),
        "shadow": (1.0, 1.0, 1.0),
        "sharp_lit": (1.0, 1.0, 1.0),
        "sharp_shadow": (1.0, 1.0, 1.0),
    },
    "3": { # Sunset
        "ambient": (0.9, 0.75, 0.7),
        "lit": (1.0, 0.65, 0.45),
        "shadow": (0.5, 0.45, 0.7),
        "sharp_lit": (1.0, 0.7, 0.5),
        "sharp_shadow": (0.45, 0.4, 0.65),
    },
    "4": { # Night
        "ambient": (0.4, 0.45, 0.6),
        "lit": (0.6, 0.7, 0.9),
        "shadow": (0.25, 0.3, 0.5),
        "sharp_lit": (0.65, 0.75, 0.95),
        "sharp_shadow": (0.2, 0.25, 0.45),
    },
    "5": { # Rainy
        "ambient": (0.6, 0.65, 0.7),
        "lit": (0.75, 0.8, 0.85),
        "shadow": (0.45, 0.5, 0.6),
        "sharp_lit": (0.8, 0.85, 0.9),
        "sharp_shadow": (0.4, 0.45, 0.55),
    },
}

_is_updating_hsr_props = False

def update_hsr_light_mode(self, context=None):
    global _is_updating_hsr_props
    if _is_updating_hsr_props:
        return
    mode = getattr(self, "hsr_light_mode", "0")
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        arm = resolve_settings_armature(context)
        if arm:
            arm["hsr_light_mode"] = str(mode)
    except Exception:
        pass

    if mode in HSR_LIGHT_PRESETS:
        preset = HSR_LIGHT_PRESETS[mode]
        _is_updating_hsr_props = True
        try:
            self.hsr_amb_color = preset["ambient"]
            self.hsr_lit_color = preset["lit"]
            self.hsr_shadow_color = preset["shadow"]
            self.hsr_sharp_lit_color = preset["sharp_lit"]
            self.hsr_sharp_shadow_color = preset["sharp_shadow"]
        finally:
            _is_updating_hsr_props = False
    update_hsr_stellartoon_props(self, context)


def update_hsr_stellartoon_props(self, context=None):
    global _is_updating_hsr_props
    if _is_updating_hsr_props:
        return
    scene = bpy.context.scene if context is None else getattr(context, "scene", bpy.context.scene)
    if not scene:
        return

    _is_updating_hsr_props = True
    try:
        # Snap float sliders to 1 decimal place (steps of 0.1) and clamp near-zero
        raw_cheek = getattr(scene, "hsr_exp_cheek", 0.0)
        raw_shy = getattr(scene, "hsr_exp_shy", 0.0)
        raw_shadow = getattr(scene, "hsr_exp_shadow", 0.0)

        exp_cheek = 0.0 if raw_cheek < 0.05 else round(raw_cheek, 1)
        exp_shy = 0.0 if raw_shy < 0.05 else round(raw_shy, 1)
        exp_shadow = 0.0 if raw_shadow < 0.05 else round(raw_shadow, 1)
        
        if scene.hsr_exp_cheek != exp_cheek:
            scene.hsr_exp_cheek = exp_cheek
        if scene.hsr_exp_shy != exp_shy:
            scene.hsr_exp_shy = exp_shy
        if scene.hsr_exp_shadow != exp_shadow:
            scene.hsr_exp_shadow = exp_shadow
    finally:
        _is_updating_hsr_props = False

    eye_cant_tint = 1.0 if getattr(scene, "hsr_eye_cant_be_tinted", False) else 0.0

    amb_color = list(getattr(scene, "hsr_amb_color", (1.0, 1.0, 1.0)))
    if len(amb_color) == 3: amb_color.append(1.0)
    
    lit_color = list(getattr(scene, "hsr_lit_color", (1.0, 1.0, 1.0)))
    if len(lit_color) == 3: lit_color.append(1.0)
    
    shadow_color = list(getattr(scene, "hsr_shadow_color", (1.0, 1.0, 1.0)))
    if len(shadow_color) == 3: shadow_color.append(1.0)
    
    sharp_lit = list(getattr(scene, "hsr_sharp_lit_color", (1.0, 1.0, 1.0)))
    if len(sharp_lit) == 3: sharp_lit.append(1.0)
    
    sharp_shadow = list(getattr(scene, "hsr_sharp_shadow_color", (1.0, 1.0, 1.0)))
    if len(sharp_shadow) == 3: sharp_shadow.append(1.0)

    # 1. Resolve character armature & materials and isolate GlobalProperties
    arm = None
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

    is_lp_active = False
    try:
        from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
        if arm and armature_has_lighting_panel(arm):
            ctrl_type = arm.get("hsr_lighting_control_type")
            if ctrl_type not in ("PANEL", "THIS_PANEL"):
                ctrl_type = getattr(scene, "hsr_lighting_control_type", "PANEL")
            is_lp_active = (ctrl_type == "PANEL")
    except Exception:
        is_lp_active = False

    prop_map = {
        "Expression Cheek Intensity": exp_cheek,
        "Expression Shy Intensity": exp_shy,
        "Expression Shadow Intensity": exp_shadow,
        "Eye Can't Be Tinted?": eye_cant_tint,
    }
    if not is_lp_active:
        rim_x = max(0.0, min(20.0, float(getattr(scene, "hsr_rim_x", 0.0))))
        rim_y = max(0.0, min(20.0, float(getattr(scene, "hsr_rim_y", 0.0))))

        rim_lit = list(getattr(scene, "hsr_rim_lit_color", (1.0, 1.0, 1.0)))
        if len(rim_lit) == 3:
            rim_lit.append(1.0)

        rim_shadow = list(getattr(scene, "hsr_rim_shadow_color", (0.0, 0.0, 0.0)))
        if len(rim_shadow) == 3:
            rim_shadow.append(1.0)

        prop_map.update({
            "Custom Ambient Color": amb_color,
            "Custom Lit Color": lit_color,
            "Custom Shadow Color": shadow_color,
            "Custom Sharp Lit Color": sharp_lit,
            "Custom Sharp Shadow Color": sharp_shadow,
            "Scale": (rim_x, rim_y, 0.0),
            "Tint Lit": rim_lit,
            "Tint Shadow": rim_shadow,
        })

    # 2. Find target GlobalProperties node group(s)
    target_trees = set()
    mats_to_update = target_materials if target_materials else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "globalproperties" in node.node_tree.name.lower():
                        target_trees.add(node.node_tree)

    if not target_trees:
        for ng in bpy.data.node_groups:
            if "globalproperties" in ng.name.lower():
                target_trees.add(ng)

    # 3. Update inside each target GlobalProperties node group
    for tree in target_trees:
        out_node = tree.nodes.get("Group Output") or tree.nodes.get("Global Properties")
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

    # 4. Also update direct group node inputs on character materials if any exist
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    for inp_name, val in prop_map.items():
                        if inp_name in node.inputs:
                            try:
                                node.inputs[inp_name].default_value = val
                            except Exception:
                                pass

    # 5. Tag 3D areas for redraw
    if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
        for win in getattr(bpy.context, 'window_manager', 'windows', []) if False else getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()


def _redraw_view3d():
    wm = getattr(bpy.context, 'window_manager', None)
    if not wm:
        return
    for win in getattr(wm, 'windows', []):
        screen = getattr(win, 'screen', None)
        if screen:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def _iter_hsr_outline_nodes(materials):
    for mat in materials:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree and "outlines" in node.node_tree.name.lower():
                    yield mat, node


def _outline_thickness_socket_id(mod):
    ng = getattr(mod, "node_group", None)
    if ng and hasattr(ng, "interface") and hasattr(ng.interface, "items_tree"):
        for item in ng.interface.items_tree:
            if getattr(item, "item_type", None) == 'SOCKET' and item.in_out == 'INPUT' and item.name == "Outline Thickness":
                return item.identifier
    return "Input_7"


def _get_outline_thickness(mod):
    from setup_wizard.utils.modifier_utils import get_modifier_property
    ident = _outline_thickness_socket_id(mod)
    val = get_modifier_property(mod, ident)
    if val is None and ident != "Outline Thickness":
        val = get_modifier_property(mod, "Outline Thickness")
    return val


def _set_outline_thickness(mod, val):
    from setup_wizard.utils.modifier_utils import set_modifier_property
    ident = _outline_thickness_socket_id(mod)
    if not set_modifier_property(mod, ident, val) and ident != "Outline Thickness":
        return set_modifier_property(mod, "Outline Thickness", val)
    return True


def _ensure_hsr_outline_override_group():
    ng_name = "HSR Outline Color Override"
    ng = bpy.data.node_groups.get(ng_name)
    if ng and ng.get("_hsr_outline_override_v1"):
        return ng
    if ng:
        ng.nodes.clear()
    else:
        ng = bpy.data.node_groups.new(ng_name, "ShaderNodeTree")

    if hasattr(ng, "interface"):
        ng.interface.clear()
        s_mix = ng.interface.new_socket(name="Mix", in_out="INPUT", socket_type="NodeSocketFloat")
        s_mix.min_value = 0.0
        s_mix.max_value = 1.0
        s_mix.default_value = 0.0
        s_ovr = ng.interface.new_socket(name="Override Color", in_out="INPUT", socket_type="NodeSocketColor")
        s_ovr.default_value = (0.0, 0.0, 0.0, 1.0)
        for i in range(1, 9):
            s_orig = ng.interface.new_socket(name=f"Original {i}", in_out="INPUT", socket_type="NodeSocketColor")
            s_orig.default_value = (0.0, 0.0, 0.0, 1.0)
            ng.interface.new_socket(name=f"Color {i}", in_out="OUTPUT", socket_type="NodeSocketColor")
    else:
        ng.inputs.clear()
        ng.outputs.clear()
        s_mix = ng.inputs.new("NodeSocketFloat", "Mix")
        s_mix.min_value = 0.0
        s_mix.max_value = 1.0
        s_mix.default_value = 0.0
        s_ovr = ng.inputs.new("NodeSocketColor", "Override Color")
        s_ovr.default_value = (0.0, 0.0, 0.0, 1.0)
        for i in range(1, 9):
            s_orig = ng.inputs.new("NodeSocketColor", f"Original {i}")
            s_orig.default_value = (0.0, 0.0, 0.0, 1.0)
            ng.outputs.new("NodeSocketColor", f"Color {i}")

    n_in = ng.nodes.new("NodeGroupInput")
    n_in.location = (-400, 0)
    n_out = ng.nodes.new("NodeGroupOutput")
    n_out.location = (400, 0)

    for i in range(1, 9):
        m = ng.nodes.new("ShaderNodeMix")
        m.data_type = 'RGBA'
        m.blend_type = 'MIX'
        m.clamp_factor = True
        m.location = (0, (4 - i) * 160)
        ng.links.new(n_in.outputs["Mix"], m.inputs["Factor"])
        ng.links.new(n_in.outputs[f"Original {i}"], m.inputs[6])
        ng.links.new(n_in.outputs["Override Color"], m.inputs[7])
        ng.links.new(m.outputs[2], n_out.inputs[f"Color {i}"])

    ng["_hsr_outline_override_v1"] = True
    return ng


def _ensure_outline_override_nodes(materials):
    ng = _ensure_hsr_outline_override_group()
    nodes = []
    for mat, ol_node in _iter_hsr_outline_nodes(materials):
        nt = mat.node_tree
        ovr = nt.nodes.get("HSR_Outline_Color_Override")
        if not ovr or ovr.type != 'GROUP':
            ovr = nt.nodes.new("ShaderNodeGroup")
            ovr.name = "HSR_Outline_Color_Override"
            ovr.label = "Outline Color Override"
            ovr.location = (ol_node.location.x - 260, ol_node.location.y)
        if ovr.node_tree != ng:
            ovr.node_tree = ng
        for i in range(1, 9):
            target_sock = ol_node.inputs.get(f"Outline Color {i}")
            orig_sock = ovr.inputs.get(f"Original {i}")
            out_sock = ovr.outputs.get(f"Color {i}")
            if not target_sock or not orig_sock or not out_sock:
                continue
            if not any(l.from_node == ovr for l in target_sock.links):
                if target_sock.is_linked:
                    src = target_sock.links[0].from_socket
                    nt.links.new(src, orig_sock)
                else:
                    orig_sock.default_value = tuple(target_sock.default_value)
                nt.links.new(out_sock, target_sock)
        nodes.append(ovr)
    return nodes


def update_hsr_outline_color(self, context):
    global _is_updating_hsr_props
    if _is_updating_hsr_props:
        return
    try:
        from setup_wizard.ui.character_settings_utils import (
            get_character_materials,
            ensure_character_node_trees_isolated,
        )
        arm, mats = get_character_materials(context)
        if arm and mats:
            ensure_character_node_trees_isolated(arm, mats)
    except Exception:
        arm, mats = None, []
    if arm:
        arm["hsr_outline_color"] = list(self.hsr_outline_color)
        arm["hsr_outline_color_mix"] = float(self.hsr_outline_color_mix)
    color = tuple(self.hsr_outline_color) + (1.0,)
    mix_val = float(self.hsr_outline_color_mix)
    mats_to_update = mats if mats else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    for ovr in _ensure_outline_override_nodes(mats_to_update):
        if "Override Color" in ovr.inputs:
            ovr.inputs["Override Color"].default_value = color
        if "Mix" in ovr.inputs:
            ovr.inputs["Mix"].default_value = mix_val
    _redraw_view3d()


def update_hsr_outline_thickness(self, context):
    global _is_updating_hsr_props
    if _is_updating_hsr_props:
        return
    try:
        from setup_wizard.ui.character_settings_utils import (
            resolve_settings_armature,
            _iter_rig_meshes,
        )
        arm = resolve_settings_armature(context)
        meshes = list(_iter_rig_meshes(arm)) if arm else []
    except Exception:
        arm, meshes = None, []
    if arm:
        arm["hsr_outline_thickness"] = float(self.hsr_outline_thickness)
    if not meshes:
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    val = float(self.hsr_outline_thickness)
    for obj in meshes:
        for mod in obj.modifiers:
            if mod.type == 'NODES' and (
                "outline" in mod.name.lower()
                or (mod.node_group and "outline" in mod.node_group.name.lower())
            ):
                if _set_outline_thickness(mod, val):
                    obj.update_tag()
    _redraw_view3d()


def update_hsr_lighting_control_type(self, context=None):
    global _is_updating_hsr_props
    if _is_updating_hsr_props:
        return
    ctrl_type = getattr(self, "hsr_lighting_control_type", "PANEL")
    arm = None
    mats = []
    try:
        from setup_wizard.ui.character_settings_utils import (
            resolve_settings_armature,
            get_character_materials,
            ensure_character_node_trees_isolated,
        )
        arm = resolve_settings_armature(context)
        if arm:
            arm["hsr_lighting_control_type"] = str(ctrl_type)
            _, mats = get_character_materials(context, arm)
            if mats:
                ensure_character_node_trees_isolated(arm, mats)
    except Exception:
        arm = None
        mats = []

    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        connect_hsr_lighting_panel,
        disconnect_hsr_lighting_panel,
        set_lighting_panel_visibility,
    )

    if ctrl_type == "PANEL":
        connect_hsr_lighting_panel(target_materials=mats or None)
        if arm:
            set_lighting_panel_visibility(arm, True)
    else:
        if arm:
            set_lighting_panel_visibility(arm, False)
        disconnect_hsr_lighting_panel(target_materials=mats or None)

        current_mode = arm.get("hsr_light_mode", "0") if arm else getattr(self, "hsr_light_mode", "0")
        if str(current_mode) not in HSR_LIGHT_PRESETS and str(current_mode) != "6":
            current_mode = "0"
            if arm:
                arm["hsr_light_mode"] = "0"
            _is_updating_hsr_props = True
            try:
                self.hsr_light_mode = "0"
            finally:
                _is_updating_hsr_props = False

        if str(current_mode) in HSR_LIGHT_PRESETS:
            preset = HSR_LIGHT_PRESETS[str(current_mode)]
            _is_updating_hsr_props = True
            try:
                self.hsr_amb_color = preset["ambient"]
                self.hsr_lit_color = preset["lit"]
                self.hsr_shadow_color = preset["shadow"]
                self.hsr_sharp_lit_color = preset["sharp_lit"]
                self.hsr_sharp_shadow_color = preset["sharp_shadow"]
            finally:
                _is_updating_hsr_props = False

        update_hsr_stellartoon_props(self, context)

    _redraw_view3d()


def pull_hsr_panel_values(scene, context, force=False):
    """Synchronizes UI sliders and lighting mode with the selected character's materials and rig."""
    global _is_updating_hsr_props
    if _is_updating_hsr_props or not scene:
        return
    try:
        from setup_wizard.ui.character_settings_utils import (
            get_character_materials,
            has_active_character_changed,
            ensure_character_node_trees_isolated,
        )
        if not force and not has_active_character_changed(context):
            return
        arm, mats = get_character_materials(context)
    except Exception:
        return
    if not arm or not mats:
        return

    ensure_character_node_trees_isolated(arm, mats)

    # Ensure color wheels are never visible in render
    for o in bpy.data.objects:
        if "colorwheel" in o.name.lower() and not getattr(o, "hide_render", False):
            try:
                o.hide_render = True
            except Exception:
                pass

    # 0. Pull lighting control type (Light Panel vs This Panel)
    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        is_hsr_lighting_panel_connected,
        armature_has_lighting_panel,
    )
    has_lp = armature_has_lighting_panel(arm)
    if has_lp:
        ctrl_type = arm.get("hsr_lighting_control_type")
        if ctrl_type not in ("PANEL", "THIS_PANEL"):
            lp_connected = is_hsr_lighting_panel_connected(target_materials=mats)
            ctrl_type = "PANEL" if lp_connected else "THIS_PANEL"
        if getattr(scene, "hsr_lighting_control_type", "") != ctrl_type:
            _is_updating_hsr_props = True
            try:
                scene.hsr_lighting_control_type = ctrl_type
                arm["hsr_lighting_control_type"] = ctrl_type
            finally:
                _is_updating_hsr_props = False

    # 1. Pull lighting mode saved on this armature
    saved_mode = arm.get("hsr_light_mode", "0")
    if getattr(scene, "hsr_light_mode", "") != str(saved_mode):
        _is_updating_hsr_props = True
        try:
            scene.hsr_light_mode = str(saved_mode)
        finally:
            _is_updating_hsr_props = False

    # 2. Find target GlobalProperties node group for this character
    target_tree = None
    target_node = None
    for m in mats:
        if getattr(m, "node_tree", None):
            for node in m.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_name = node.node_tree.name.lower()
                    if "globalproperties" in nt_name:
                        target_tree = node.node_tree
                        target_node = node
                        break
        if target_tree:
            break

    if not target_tree and not target_node:
        return

    out_node = None
    if target_tree:
        out_node = target_tree.nodes.get("Group Output") or target_tree.nodes.get("Global Properties")

    inputs = out_node.inputs if out_node else (target_node.inputs if target_node else None)
    if not inputs:
        return

    _is_updating_hsr_props = True
    try:
        if "Expression Cheek Intensity" in inputs:
            scene.hsr_exp_cheek = float(inputs["Expression Cheek Intensity"].default_value)
        if "Expression Shy Intensity" in inputs:
            scene.hsr_exp_shy = float(inputs["Expression Shy Intensity"].default_value)
        if "Expression Shadow Intensity" in inputs:
            scene.hsr_exp_shadow = float(inputs["Expression Shadow Intensity"].default_value)
        if "Eye Can't Be Tinted?" in inputs:
            scene.hsr_eye_cant_be_tinted = bool(inputs["Eye Can't Be Tinted?"].default_value > 0.5)
        if "Custom Ambient Color" in inputs:
            scene.hsr_amb_color = tuple(inputs["Custom Ambient Color"].default_value)[:3]
        if "Custom Lit Color" in inputs:
            scene.hsr_lit_color = tuple(inputs["Custom Lit Color"].default_value)[:3]
        if "Custom Shadow Color" in inputs:
            scene.hsr_shadow_color = tuple(inputs["Custom Shadow Color"].default_value)[:3]
        if "Custom Sharp Lit Color" in inputs:
            scene.hsr_sharp_lit_color = tuple(inputs["Custom Sharp Lit Color"].default_value)[:3]
        if "Custom Sharp Shadow Color" in inputs:
            scene.hsr_sharp_shadow_color = tuple(inputs["Custom Sharp Shadow Color"].default_value)[:3]
        if "Scale" in inputs:
            sc = tuple(inputs["Scale"].default_value)
            if len(sc) >= 2:
                scene.hsr_rim_x = max(0.0, min(20.0, float(sc[0])))
                scene.hsr_rim_y = max(0.0, min(20.0, float(sc[1])))
        if "Tint Lit" in inputs:
            scene.hsr_rim_lit_color = tuple(inputs["Tint Lit"].default_value)[:3]
        if "Tint Shadow" in inputs:
            scene.hsr_rim_shadow_color = tuple(inputs["Tint Shadow"].default_value)[:3]

        saved_ol_color = arm.get("hsr_outline_color")
        if saved_ol_color is not None and len(saved_ol_color) >= 3:
            scene.hsr_outline_color = tuple(saved_ol_color)[:3]
        else:
            ovr = next((m.node_tree.nodes.get("HSR_Outline_Color_Override") for m in mats if m.node_tree and m.node_tree.nodes.get("HSR_Outline_Color_Override")), None)
            if ovr and "Override Color" in ovr.inputs:
                scene.hsr_outline_color = tuple(ovr.inputs["Override Color"].default_value)[:3]
            else:
                scene.hsr_outline_color = (0.0, 0.0, 0.0)

        saved_ol_mix = arm.get("hsr_outline_color_mix")
        if saved_ol_mix is not None:
            scene.hsr_outline_color_mix = float(saved_ol_mix)
        else:
            ovr = next((m.node_tree.nodes.get("HSR_Outline_Color_Override") for m in mats if m.node_tree and m.node_tree.nodes.get("HSR_Outline_Color_Override")), None)
            if ovr and "Mix" in ovr.inputs:
                scene.hsr_outline_color_mix = float(ovr.inputs["Mix"].default_value)
            else:
                scene.hsr_outline_color_mix = 0.0

        saved_ol_thick = arm.get("hsr_outline_thickness")
        if saved_ol_thick is not None:
            scene.hsr_outline_thickness = float(saved_ol_thick)
        else:
            from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
            for obj in _iter_rig_meshes(arm):
                found_thick = False
                for mod in obj.modifiers:
                    if mod.type == 'NODES' and (
                        "outline" in mod.name.lower()
                        or (mod.node_group and "outline" in mod.node_group.name.lower())
                    ):
                        val = _get_outline_thickness(mod)
                        if val is not None:
                            scene.hsr_outline_thickness = float(val)
                            found_thick = True
                            break
                if found_thick:
                    break
    except Exception:
        pass
    finally:
        _is_updating_hsr_props = False


class HSR_OT_SelectLightingPanel(bpy.types.Operator):
    bl_idname = "honkai_star_rail.select_lighting_panel"
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
        for pin in ("Ambient", "Lit", "Shadow", "Rim Lit", "RimShadow", "Rim.L", "Rim.R", "RimX", "RimY"):
            b = arm.data.bones.get(pin)
            if b:
                b.select = True
        return {'FINISHED'}


class HSR_OT_ToggleLightingPanelVisibility(bpy.types.Operator):
    bl_idname = "honkai_star_rail.toggle_lighting_panel_visibility"
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
        _redraw_view3d()
        return {'FINISHED'}


def _draw_hsr_this_panel_controls(layout, context, scene):
    """Draw This Panel lighting presets and custom color controls for HSR."""
    col_light = layout.column(align=True)
    col_light.label(text="Lighting Mode:")
    col_light.prop(scene, "hsr_light_mode", text="")

    if getattr(scene, "hsr_light_mode", "0") == "6":
        box_col = col_light.box()
        box_col.label(text="Custom Colors", icon="COLOR")
        col_colors = box_col.column(align=True)
        col_colors.prop(scene, "hsr_amb_color", text="Ambient")
        col_colors.prop(scene, "hsr_lit_color", text="Lit")
        col_colors.prop(scene, "hsr_shadow_color", text="Shadow")
        col_colors.prop(scene, "hsr_sharp_lit_color", text="Sharp Lit")
        col_colors.prop(scene, "hsr_sharp_shadow_color", text="Sharp Shadow")

    draw_lights_plus(layout, context)

    box_rim = layout.box()
    box_rim.label(text="Rim Light", icon="LIGHT_SUN")
    col_rim = box_rim.column(align=True)
    col_rim.prop(scene, "hsr_rim_x", text="Rim Light X", slider=True)
    col_rim.prop(scene, "hsr_rim_y", text="Rim Light Y", slider=True)
    col_rim.prop(scene, "hsr_rim_lit_color", text="Rim Lit")
    col_rim.prop(scene, "hsr_rim_shadow_color", text="Rim Shadow")


class HSR_PT_Rig_Character_Settings(Panel):
    bl_label = "Character Settings"
    bl_idname = "HSR_PT_Rig_Character_Settings_Main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.ui.character_settings_utils import is_game_armature
            return is_game_armature(context, "HONKAI_STAR_RAIL")
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
        from setup_wizard.ui.character_settings_tabs import draw_character_settings_tabs
        if draw_character_settings_tabs(self.layout, context):
            return
        layout = self.layout
        scene = context.scene

        try:
            pull_hsr_panel_values(scene, context)
        except Exception:
            pass

        arm = None
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
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

        # 1. Lighting Type (Light Panel vs This Panel) & Lighting Mode / Presets
        from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
        has_lp = armature_has_lighting_panel(arm)

        if has_lp:
            col_type = layout.column(align=False)
            col_type.label(text="Lighting Type:")
            row_btn = col_type.row(align=True)
            row_btn.prop(scene, "hsr_lighting_control_type", expand=True)

            is_lp_mode = (getattr(scene, "hsr_lighting_control_type", "PANEL") == "PANEL")
            if not is_lp_mode:
                _draw_hsr_this_panel_controls(layout, context, scene)
            else:
                draw_lights_plus(layout, context)
        else:
            _draw_hsr_this_panel_controls(layout, context, scene)

        # 3. Expressions (3 sliders)
        box_exp = layout.box()
        box_exp.label(text="Expressions", icon="COMMUNITY")
        col_exp = box_exp.column(align=True)
        col_exp.prop(scene, "hsr_exp_cheek", text="Cheek", slider=True)
        col_exp.prop(scene, "hsr_exp_shy", text="Shy", slider=True)
        col_exp.prop(scene, "hsr_exp_shadow", text="Shadow", slider=True)

        # 4. Eye Can't Be Tinted?
        layout.prop(scene, "hsr_eye_cant_be_tinted", text="Eye Can't Be Tinted?")

        # 5. Outlines
        box_outlines = layout.box()
        box_outlines.label(text="Outlines", icon="STROKE")
        col_outlines = box_outlines.column(align=True)
        col_outlines.prop(scene, "hsr_outline_color", text="Outline Color")
        col_outlines.prop(scene, "hsr_outline_color_mix", text="Mix (0 = Original)", slider=True)
        col_outlines.prop(scene, "hsr_outline_thickness", text="Outline Thickness", slider=True)

        # 6. Hair & Clothes Physics
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
            box_physics.column(align=True).operator("hoyoverse.remove_hair_clothes_physics", text="Remove Physics", icon="PANEL_CLOSE")
        else:
            col_physics.operator("hoyoverse.apply_hair_clothes_physics", text="Apply Physics", icon="FILE_REFRESH")


def register_hsr_properties():
    from bpy.props import EnumProperty, FloatProperty, FloatVectorProperty, BoolProperty

    try:
        bpy.utils.register_class(HSR_OT_SelectLightingPanel)
    except Exception:
        pass
    try:
        bpy.utils.register_class(HSR_OT_ToggleLightingPanelVisibility)
    except Exception:
        pass

    bpy.types.Scene.hsr_lighting_control_type = EnumProperty(
        name="Lighting Control",
        description="Choose how lighting colors and tints are controlled for HSR",
        items=[
            ("PANEL", "Light Panel", "Use 3D Lighting Panel in viewport"),
            ("THIS_PANEL", "This Panel", "Use Character Settings panel controls"),
        ],
        default="PANEL",
        update=update_hsr_lighting_control_type,
    )

    bpy.types.Scene.hsr_light_mode = EnumProperty(
        name="Light Mode",
        description="Lighting preset mode for Honkai Star Rail StellarToon shader",
        items=[
            ("0", "Default", "Default Game Lighting"),
            ("1", "Sunrise", "Sunrise Tone"),
            ("2", "Day", "Bright Daylight"),
            ("3", "Sunset", "Warm Sunset"),
            ("4", "Night", "Cool Night"),
            ("5", "Rainy", "Overcast / Rainy"),
            ("6", "Custom", "Custom User Colors"),
        ],
        default="0",
        update=update_hsr_light_mode,
    )

    bpy.types.Scene.hsr_exp_cheek = FloatProperty(
        name="Expression Cheek Intensity",
        description="Expression cheek intensity",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=1,
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_exp_shy = FloatProperty(
        name="Expression Shy Intensity",
        description="Expression shy intensity",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=1,
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_exp_shadow = FloatProperty(
        name="Expression Shadow Intensity",
        description="Expression shadow intensity",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=1,
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_eye_cant_be_tinted = BoolProperty(
        name="Eye Can't Be Tinted?",
        description="Prevent eyes from being affected by lighting tints",
        default=False,
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_amb_color = FloatVectorProperty(
        name="Custom Ambient Color",
        description="Custom ambient color for StellarToon shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_lit_color = FloatVectorProperty(
        name="Custom Lit Color",
        description="Custom lit color for StellarToon shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_shadow_color = FloatVectorProperty(
        name="Custom Shadow Color",
        description="Custom shadow color for StellarToon shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_sharp_lit_color = FloatVectorProperty(
        name="Custom Sharp Lit Color",
        description="Custom sharp lit color for StellarToon shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_sharp_shadow_color = FloatVectorProperty(
        name="Custom Sharp Shadow Color",
        description="Custom sharp shadow color for StellarToon shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_rim_x = FloatProperty(
        name="Rim Light X",
        description="HSR Rim Light X scale",
        min=0.0,
        max=20.0,
        default=0.0,
        step=10,
        precision=2,
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_rim_y = FloatProperty(
        name="Rim Light Y",
        description="HSR Rim Light Y scale",
        min=0.0,
        max=20.0,
        default=0.0,
        step=10,
        precision=2,
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_rim_lit_color = FloatVectorProperty(
        name="Rim Lit",
        description="HSR Rim Lit tint color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_rim_shadow_color = FloatVectorProperty(
        name="Rim Shadow",
        description="HSR Rim Shadow tint color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
        update=update_hsr_stellartoon_props,
    )

    bpy.types.Scene.hsr_outline_color = FloatVectorProperty(
        name="Outline Color",
        description="Override outline color for Honkai Star Rail outlines",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
        update=update_hsr_outline_color,
    )

    bpy.types.Scene.hsr_outline_color_mix = FloatProperty(
        name="Outline Color Mix",
        description="Blend between original per-part outline colors (0) and Outline Color (1)",
        min=0.0,
        max=1.0,
        default=0.0,
        step=5,
        precision=2,
        update=update_hsr_outline_color,
    )

    bpy.types.Scene.hsr_outline_thickness = FloatProperty(
        name="Outline Thickness",
        description="Outline thickness from the Geometry Nodes Outlines modifier",
        min=0.0,
        max=5.0,
        default=0.375,
        step=5,
        precision=3,
        update=update_hsr_outline_thickness,
    )


def unregister_hsr_properties():
    try:
        bpy.utils.unregister_class(HSR_OT_SelectLightingPanel)
    except Exception:
        pass
    try:
        bpy.utils.unregister_class(HSR_OT_ToggleLightingPanelVisibility)
    except Exception:
        pass

    props = [
        "hsr_lighting_control_type",
        "hsr_light_mode",
        "hsr_exp_cheek",
        "hsr_exp_shy",
        "hsr_exp_shadow",
        "hsr_eye_cant_be_tinted",
        "hsr_amb_color",
        "hsr_lit_color",
        "hsr_shadow_color",
        "hsr_sharp_lit_color",
        "hsr_sharp_shadow_color",
        "hsr_rim_x",
        "hsr_rim_y",
        "hsr_rim_lit_color",
        "hsr_rim_shadow_color",
        "hsr_outline_color",
        "hsr_outline_color_mix",
        "hsr_outline_thickness",
    ]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)

