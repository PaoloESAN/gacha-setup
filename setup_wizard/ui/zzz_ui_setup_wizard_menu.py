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
    bl_category = "Gacha Setup"

    @classmethod
    def poll(cls, context):
        return False

    bpy.types.Scene.zzz_shader_type = bpy.props.EnumProperty(
        items=[
            ("KYTHERA", "Kythera's Shader", "Use Kythera's ZZZ Shader (Face Shader + General Shader)"),
            ("LEGACY", "Legacy Shader", "Use Legacy ZZZ Setup v7 Shader"),
        ],
        name="Shader",
        description="Select shader setup for Zenless Zone Zero",
        default="KYTHERA",
    )

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
        from setup_wizard.services.isolation import isolation_service
        isolation_service.draw_setup_status_box(sub_layout, context, run_entire_setup_column)

        settings_box = layout.box()
        settings_header = settings_box.row()
        settings_header.label(text="Setup Settings", icon="PREFERENCES")

        settings_col = settings_box.column()
        settings_col.prop(context.scene, "zzz_shader_type", text="Shader")
        props = context.scene.character_rigger_props
        enable_physics = getattr(props, "enable_hair_clothes_physics", getattr(props, "enable_hair_dress_physics", False))
        settings_col.prop(props, "enable_hair_clothes_physics", text="Hair & Clothes Physics")
        if enable_physics:
            sliders_col = settings_col.column()
            sliders_col.prop(props, "hair_physics_influence", text="Hair", slider=True)
            sliders_col.prop(props, "clothes_physics_influence", text="Clothes", slider=True)
        settings_col.prop(props, "disable_rigging", text="Disable Rigging")


class ZZZ_PT_Basic_Setup_Wizard_UI_Layout(Panel, ZenlessZoneZeroUIRenderChecker):
    bl_label = "Basic Setup"
    bl_idname = "ZZZ_PT_UI_Basic_Setup_Layout"
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
            "zenless_zone_zero.set_up_character",
            "Set Up Character",
            icon="OUTLINER_OB_ARMATURE",
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
    bl_category = "Gacha Setup"
    bl_parent_id = 'CSW_PT_Old_Setup_UI_Layout'
    bl_order = 2
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
        OperatorFactory.create(
            sub_layout,
            "genshin.reorient_bones",
            "Fix Orientation",
            "BONE_DATA",
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
            "zenless_zone_zero.setup_head_driver",
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
            "hoyoverse.rename_shader_materials",
            "Rename Shader Materials",
            "FONT_DATA",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "zenless_zone_zero.rename_collection_and_rig",
            "Rename Collection & Rig",
            "OUTLINER_COLLECTION",
            game_type=GameType.ZENLESS_ZONE_ZERO.name,
        )
        OperatorFactory.create(
            sub_layout,
            "zenless_zone_zero.move_lighting_panel_to_char_collection",
            "Move Lighting Panel to Collection",
            "LIGHT",
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
        OperatorFactory.create(
            sub_layout,
            "hoyoverse.apply_hair_clothes_physics",
            "Apply Hair & Clothes Physics",
            "PHYSICS",
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
        btn = ui_object.operator(
            operator=operator,
            text=text,
            icon=icon,
        )

        if btn:
            for key, value in kwargs.items():
                setattr(btn, key, value)

    @staticmethod
    def create_rig_character_ui(
        ui_object: UILayout,
    ):
        expy_kit_installed = any('expy' in k.lower() for k in bpy.context.preferences.addons.keys())
        rigify_installed = any('rigify' in k.lower() for k in bpy.context.preferences.addons.keys())

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


ZZZ_LIGHT_PRESETS = {
    "0": { # Default
        "ambient": (1.0, 1.0, 1.0),
        "lit_tint": (1.0, 1.0, 1.0),
        "lit_brightness": 0.0,
        "shadow_tint": (0.65, 0.65, 0.85),
        "shadow_intensity": 1.0,
        "fake_sss_intensity": 1.0,
        "enable_rim": True,
        "rim_color": (1.0, 1.0, 1.0),
        "coverage": 1.0,
        "brightness": 1.0,
        "left_right": 0.5,
        "up_down": 0.1,
    },
    "1": { # Sunrise
        "ambient": (0.95, 0.85, 0.8),
        "lit_tint": (1.0, 0.88, 0.75),
        "lit_brightness": 0.1,
        "shadow_tint": (0.65, 0.65, 0.85),
        "shadow_intensity": 1.0,
        "fake_sss_intensity": 1.0,
        "enable_rim": True,
        "rim_color": (1.0, 0.85, 0.6),
        "coverage": 1.0,
        "brightness": 1.0,
        "left_right": 0.6,
        "up_down": 0.05,
    },
    "2": { # Day
        "ambient": (1.0, 1.0, 1.0),
        "lit_tint": (1.0, 1.0, 1.0),
        "lit_brightness": 0.2,
        "shadow_tint": (0.75, 0.75, 0.85),
        "shadow_intensity": 1.0,
        "fake_sss_intensity": 1.0,
        "enable_rim": True,
        "rim_color": (1.0, 1.0, 1.0),
        "coverage": 1.0,
        "brightness": 1.0,
        "left_right": 0.5,
        "up_down": 0.3,
    },
    "3": { # Sunset
        "ambient": (0.9, 0.75, 0.7),
        "lit_tint": (1.0, 0.65, 0.45),
        "lit_brightness": 0.1,
        "shadow_tint": (0.5, 0.45, 0.7),
        "shadow_intensity": 1.0,
        "fake_sss_intensity": 1.0,
        "enable_rim": True,
        "rim_color": (1.0, 0.6, 0.3),
        "coverage": 1.0,
        "brightness": 1.0,
        "left_right": 0.7,
        "up_down": 0.0,
    },
    "4": { # Night
        "ambient": (0.4, 0.45, 0.6),
        "lit_tint": (0.6, 0.7, 0.9),
        "lit_brightness": 0.0,
        "shadow_tint": (0.25, 0.3, 0.5),
        "shadow_intensity": 1.0,
        "fake_sss_intensity": 0.5,
        "enable_rim": True,
        "rim_color": (0.5, 0.7, 1.0),
        "coverage": 1.0,
        "brightness": 0.8,
        "left_right": 0.4,
        "up_down": 0.1,
    },
    "5": { # Rainy
        "ambient": (0.6, 0.65, 0.7),
        "lit_tint": (0.75, 0.8, 0.85),
        "lit_brightness": 0.0,
        "shadow_tint": (0.45, 0.5, 0.6),
        "shadow_intensity": 0.8,
        "fake_sss_intensity": 0.5,
        "enable_rim": True,
        "rim_color": (0.7, 0.8, 0.9),
        "coverage": 1.0,
        "brightness": 0.7,
        "left_right": 0.5,
        "up_down": 0.4,
    },
}

_is_updating_zzz_props = False

def update_zzz_light_mode(self, context=None):
    global _is_updating_zzz_props
    if _is_updating_zzz_props:
        return
    mode = getattr(self, "zzz_light_mode", "0")
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        arm = resolve_settings_armature(context)
        if arm:
            arm["zzz_light_mode"] = str(mode)
    except Exception:
        pass

    if mode in ZZZ_LIGHT_PRESETS:
        preset = ZZZ_LIGHT_PRESETS[mode]
        _is_updating_zzz_props = True
        try:
            self.zzz_ambient_tint = preset["ambient"]
            self.zzz_lit_tint = preset["lit_tint"]
            self.zzz_lit_brightness = preset["lit_brightness"]
            self.zzz_shadow_tint = preset["shadow_tint"]
            self.zzz_shadow_intensity = preset.get("shadow_intensity", 1.0)
            self.zzz_fake_sss_intensity = preset.get("fake_sss_intensity", 1.0)
            self.zzz_enable_rim_light = preset["enable_rim"]
            self.zzz_rim_light_color = preset["rim_color"]
            self.zzz_rim_coverage = preset["coverage"]
            self.zzz_rim_brightness = preset["brightness"]
            self.zzz_rim_left_right = preset["left_right"]
            self.zzz_rim_up_down = preset["up_down"]
        finally:
            _is_updating_zzz_props = False
    update_zzz_kythera_props(self, context)


def update_zzz_kythera_props(self, context=None):
    global _is_updating_zzz_props
    if _is_updating_zzz_props:
        return
    scene = bpy.context.scene if context is None else getattr(context, "scene", bpy.context.scene)
    if not scene:
        return

    _is_updating_zzz_props = True
    try:
        # Snap float sliders to 1 decimal place (steps of 0.1) and clamp near-zero
        raw_lb = getattr(scene, "zzz_lit_brightness", 0.0)
        raw_si = getattr(scene, "zzz_shadow_intensity", 1.0)
        raw_sss = getattr(scene, "zzz_fake_sss_intensity", 1.0)
        raw_rc = getattr(scene, "zzz_rim_coverage", 1.0)
        raw_rb = getattr(scene, "zzz_rim_brightness", 1.0)
        raw_lr = getattr(scene, "zzz_rim_left_right", 0.5)
        raw_ud = getattr(scene, "zzz_rim_up_down", 0.1)

        lit_brightness = 0.0 if raw_lb < 0.05 else round(raw_lb, 1)
        shadow_intensity = 0.0 if raw_si < 0.05 else round(raw_si, 1)
        fake_sss_intensity = 0.0 if raw_sss < 0.05 else round(raw_sss, 1)
        rim_coverage = 0.0 if raw_rc < 0.05 else round(raw_rc, 1)
        rim_brightness = 0.0 if raw_rb < 0.05 else round(raw_rb, 1)
        rim_left_right = 0.0 if raw_lr < 0.05 else round(raw_lr, 1)
        rim_up_down = 0.0 if raw_ud < 0.05 else round(raw_ud, 1)

        if scene.zzz_lit_brightness != lit_brightness:
            scene.zzz_lit_brightness = lit_brightness
        if scene.zzz_shadow_intensity != shadow_intensity:
            scene.zzz_shadow_intensity = shadow_intensity
        if scene.zzz_fake_sss_intensity != fake_sss_intensity:
            scene.zzz_fake_sss_intensity = fake_sss_intensity
        if scene.zzz_rim_coverage != rim_coverage:
            scene.zzz_rim_coverage = rim_coverage
        if scene.zzz_rim_brightness != rim_brightness:
            scene.zzz_rim_brightness = rim_brightness
        if scene.zzz_rim_left_right != rim_left_right:
            scene.zzz_rim_left_right = rim_left_right
        if scene.zzz_rim_up_down != rim_up_down:
            scene.zzz_rim_up_down = rim_up_down
    finally:
        _is_updating_zzz_props = False

    ambient_tint = list(getattr(scene, "zzz_ambient_tint", (1.0, 1.0, 1.0)))
    if len(ambient_tint) == 3: ambient_tint.append(1.0)
    
    lit_tint = list(getattr(scene, "zzz_lit_tint", (1.0, 1.0, 1.0)))
    if len(lit_tint) == 3: lit_tint.append(1.0)
    
    shadow_tint = list(getattr(scene, "zzz_shadow_tint", (1.0, 1.0, 1.0)))
    if len(shadow_tint) == 3: shadow_tint.append(1.0)
    
    enable_rim = getattr(scene, "zzz_enable_rim_light", True)
    
    rim_color = list(getattr(scene, "zzz_rim_light_color", (1.0, 1.0, 1.0)))
    if len(rim_color) == 3: rim_color.append(1.0)

    prop_map = {
        "Ambient Tint": ambient_tint,
        "Overall Tint": ambient_tint,
        "Lit Tint": lit_tint,
        "Lit Brightness": lit_brightness,
        "Shadow Tint": shadow_tint,
        "Shadow Intensity": shadow_intensity,
        "Fake SSS Intensity": fake_sss_intensity,
        "Enable Rim Light": enable_rim,
        "Rim Light Color": rim_color,
        "Coverage": rim_coverage,
        "Brightness": rim_brightness,
        "Left/Right": rim_left_right,
        "Up/Down": rim_up_down,
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

    # 2. Update in node groups definitions ONLY if no character is selected
    if not target_materials:
        for ng in bpy.data.node_groups:
            ng_low = ng.name.lower()
            if "kythera" in ng_low or "rim light" in ng_low or "lit/shadow" in ng_low or "face shader" in ng_low:
                if hasattr(ng, "interface"):
                    for item in ng.interface.items_tree:
                        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name in prop_map:
                            try:
                                item.default_value = prop_map[item.name]
                            except Exception:
                                pass
                elif hasattr(ng, "inputs"):
                    for inp in ng.inputs:
                        if inp.name in prop_map:
                            try:
                                inp.default_value = prop_map[inp.name]
                            except Exception:
                                pass

    # 3. Update targeted materials (scoped to this character only!)
    mats_to_update = target_materials if target_materials else bpy.data.materials
    for m in mats_to_update:
        if getattr(m, "node_tree", None):
            is_mask = "mask" in m.name.lower() or m.get("_is_mask", False)
            for node in m.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_low = node.node_tree.name.lower()
                    if "kythera" in nt_low or "rim light" in nt_low or "lit/shadow" in nt_low or "face shader" in nt_low:
                        for inp_name, val in prop_map.items():
                            if is_mask and inp_name in ("Enable Rim Light", "Rim Light Color", "Brightness", "Coverage", "Left/Right", "Up/Down"):
                                continue
                            if inp_name in node.inputs:
                                try:
                                    node.inputs[inp_name].default_value = val
                                except Exception:
                                    pass

    def _safe_sock_assign(sock, val):
        if not sock:
            return
        try:
            dv = getattr(sock, "default_value", None)
            if hasattr(dv, "__len__"):
                if len(dv) == 3:
                    sock.default_value = (val[0], val[1], val[2])
                elif len(dv) == 4:
                    sock.default_value = (val[0], val[1], val[2], val[3] if len(val) > 3 else 1.0)
            elif isinstance(dv, (int, float)):
                sock.default_value = float(val) if not isinstance(val, (tuple, list)) else float(val[0])
            else:
                sock.default_value = val
        except Exception:
            pass

    # 4. Also update Legacy shader node groups if present (when in THIS_PANEL mode)
    for ng in bpy.data.node_groups:
        ng_low = ng.name.lower()
        if "global material properties" in ng_low:
            if "face" in ng_low:
                mix_node = ng.nodes.get("Mix")
                vm_node = ng.nodes.get("Vector Math.001")
                if mix_node:
                    sock_b = mix_node.inputs.get("B") or (mix_node.inputs[7] if len(mix_node.inputs) > 7 else None)
                    sock_a = mix_node.inputs.get("A") or (mix_node.inputs[6] if len(mix_node.inputs) > 6 else None)
                    _safe_sock_assign(sock_b, lit_tint)
                    _safe_sock_assign(sock_a, shadow_tint)
                if vm_node and len(vm_node.inputs) > 1:
                    _safe_sock_assign(vm_node.inputs[1], ambient_tint)
            else:
                amb_node = ng.nodes.get("Ambient")
                mix_node = ng.nodes.get("Mix")
                rim_node = ng.nodes.get("Group.001")
                if amb_node:
                    sock_b = amb_node.inputs.get("B") or (amb_node.inputs[7] if len(amb_node.inputs) > 7 else None)
                    _safe_sock_assign(sock_b, ambient_tint)
                if mix_node:
                    sock_b = mix_node.inputs.get("B") or (mix_node.inputs[7] if len(mix_node.inputs) > 7 else None)
                    sock_a = mix_node.inputs.get("A") or (mix_node.inputs[6] if len(mix_node.inputs) > 6 else None)
                    _safe_sock_assign(sock_b, lit_tint)
                    _safe_sock_assign(sock_a, shadow_tint)
                if rim_node:
                    if "Rim Lit" in rim_node.inputs:
                        _safe_sock_assign(rim_node.inputs["Rim Lit"], rim_color)
                    if "Rim Shadow" in rim_node.inputs:
                        _safe_sock_assign(rim_node.inputs["Rim Shadow"], shadow_tint)

                # Handle Enable Rim Light in Legacy shader (Mix.002 blends between Color and Rims)
                mix_rim = ng.nodes.get("Mix.002")
                if mix_rim:
                    sock_fac = mix_rim.inputs.get("Factor") or (mix_rim.inputs[0] if mix_rim.inputs else None)
                    if sock_fac:
                        if enable_rim:
                            if not sock_fac.links and rim_node:
                                out_fac = rim_node.outputs.get("Factor")
                                if out_fac:
                                    ng.links.new(out_fac, sock_fac)
                        else:
                            for l in list(sock_fac.links):
                                ng.links.remove(l)
                            sock_fac.default_value = 0.0

    try:
        from setup_wizard.optimization.blender_rimlight_patch import patch_all_rimlight_groups_for_blender
        patch_all_rimlight_groups_for_blender()
    except Exception:
        pass


def update_zzz_lighting_control_type(self, context=None):
    global _is_updating_zzz_props
    if _is_updating_zzz_props:
        return
    ctrl_type = getattr(self, "zzz_lighting_control_type", "PANEL")
    arm = None
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, get_character_materials
        arm = resolve_settings_armature(context)
        if arm:
            arm["zzz_lighting_control_type"] = str(ctrl_type)
    except Exception:
        arm = None

    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        connect_zzz_lighting_panel,
        disconnect_zzz_lighting_panel,
        set_lighting_panel_visibility,
    )

    try:
        from setup_wizard.ui.character_settings_utils import get_character_materials
        _, mats = get_character_materials(context, arm)
    except Exception:
        mats = []

    if ctrl_type == "PANEL":
        connect_zzz_lighting_panel(target_materials=mats)
        if arm:
            set_lighting_panel_visibility(arm, True)
    else:
        if arm:
            set_lighting_panel_visibility(arm, False)
        disconnect_zzz_lighting_panel(target_materials=mats)

        current_mode = arm.get("zzz_light_mode", "0") if arm else getattr(self, "zzz_light_mode", "0")
        if str(current_mode) not in ZZZ_LIGHT_PRESETS and str(current_mode) != "6":
            current_mode = "0"
            if arm:
                arm["zzz_light_mode"] = "0"
            _is_updating_zzz_props = True
            try:
                self.zzz_light_mode = "0"
            finally:
                _is_updating_zzz_props = False

        if str(current_mode) in ZZZ_LIGHT_PRESETS:
            preset = ZZZ_LIGHT_PRESETS[str(current_mode)]
            _is_updating_zzz_props = True
            try:
                self.zzz_ambient_tint = preset["ambient"]
                self.zzz_lit_tint = preset["lit_tint"]
                self.zzz_lit_brightness = preset["lit_brightness"]
                self.zzz_shadow_tint = preset["shadow_tint"]
                self.zzz_shadow_intensity = preset.get("shadow_intensity", 1.0)
                self.zzz_fake_sss_intensity = preset.get("fake_sss_intensity", 1.0)
                self.zzz_enable_rim_light = preset["enable_rim"]
                self.zzz_rim_light_color = preset["rim_color"]
                self.zzz_rim_coverage = preset["coverage"]
                self.zzz_rim_brightness = preset["brightness"]
                self.zzz_rim_left_right = preset["left_right"]
                self.zzz_rim_up_down = preset["up_down"]
            finally:
                _is_updating_zzz_props = False

        update_zzz_kythera_props(self, context)


def pull_zzz_panel_values(scene, context, force=False):
    """Synchronizes UI sliders and lighting mode with the selected character's materials and rig."""
    global _is_updating_zzz_props
    if _is_updating_zzz_props or not scene:
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

    # 1. Pull lighting control type (Light Panel vs This Panel)
    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        is_zzz_lighting_panel_connected,
        armature_has_lighting_panel,
    )
    has_lp = armature_has_lighting_panel(arm)
    if has_lp:
        ctrl_type = arm.get("zzz_lighting_control_type")
        if ctrl_type not in ("PANEL", "THIS_PANEL"):
            lp_connected = is_zzz_lighting_panel_connected(target_materials=mats)
            ctrl_type = "PANEL" if lp_connected else "THIS_PANEL"
        if getattr(scene, "zzz_lighting_control_type", "") != ctrl_type:
            _is_updating_zzz_props = True
            try:
                scene.zzz_lighting_control_type = ctrl_type
                arm["zzz_lighting_control_type"] = ctrl_type
            finally:
                _is_updating_zzz_props = False

    # 2. Pull lighting mode saved on this armature
    saved_mode = arm.get("zzz_light_mode", "0")
    if getattr(scene, "zzz_light_mode", "") != str(saved_mode):
        _is_updating_zzz_props = True
        try:
            scene.zzz_light_mode = str(saved_mode)
        finally:
            _is_updating_zzz_props = False

    # 3. Pull shader node group values
    target_node = None
    for m in mats:
        if getattr(m, "node_tree", None):
            for node in m.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_low = node.node_tree.name.lower()
                    if "kythera" in nt_low or "face shader" in nt_low or "lit/shadow" in nt_low:
                        target_node = node
                        break
        if target_node:
            break

    if not target_node:
        return

    _is_updating_zzz_props = True
    try:
        inputs = target_node.inputs
        if "Lit Brightness" in inputs:
            scene.zzz_lit_brightness = float(inputs["Lit Brightness"].default_value)
        if "Shadow Intensity" in inputs:
            scene.zzz_shadow_intensity = float(inputs["Shadow Intensity"].default_value)
        if "Fake SSS Intensity" in inputs:
            scene.zzz_fake_sss_intensity = float(inputs["Fake SSS Intensity"].default_value)
        if "Ambient Tint" in inputs:
            scene.zzz_ambient_tint = tuple(inputs["Ambient Tint"].default_value)[:3]
        elif "Overall Tint" in inputs:
            scene.zzz_ambient_tint = tuple(inputs["Overall Tint"].default_value)[:3]
        if "Lit Tint" in inputs:
            scene.zzz_lit_tint = tuple(inputs["Lit Tint"].default_value)[:3]
        if "Shadow Tint" in inputs:
            scene.zzz_shadow_tint = tuple(inputs["Shadow Tint"].default_value)[:3]
        if "Enable Rim Light" in inputs:
            scene.zzz_enable_rim_light = bool(inputs["Enable Rim Light"].default_value > 0.5)
        if "Rim Light Color" in inputs:
            scene.zzz_rim_light_color = tuple(inputs["Rim Light Color"].default_value)[:3]
        if "Coverage" in inputs:
            scene.zzz_rim_coverage = float(inputs["Coverage"].default_value)
        if "Brightness" in inputs:
            scene.zzz_rim_brightness = float(inputs["Brightness"].default_value)
        if "Left/Right" in inputs:
            scene.zzz_rim_left_right = float(inputs["Left/Right"].default_value)
        if "Up/Down" in inputs:
            scene.zzz_rim_up_down = float(inputs["Up/Down"].default_value)
    except Exception:
        pass
    finally:
        _is_updating_zzz_props = False


class ZZZ_OT_SelectLightingPanel(bpy.types.Operator):
    bl_idname = "zenless_zone_zero.select_lighting_panel"
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
        for pin in ["Ambient", "Lit", "Shadow", "Rim Lit", "RimShadow", "Rim.L", "Rim.R", "RimX", "RimY"]:
            b = arm.data.bones.get(pin)
            if b:
                b.select = True
        return {'FINISHED'}


class ZZZ_OT_ToggleLightingPanelVisibility(bpy.types.Operator):
    bl_idname = "zenless_zone_zero.toggle_lighting_panel_visibility"
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


class ZZZ_PT_Rig_Character_Settings(Panel):
    bl_label = "Character Settings"
    bl_idname = "ZZZ_PT_Rig_Character_Settings_Main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.ui.character_settings_utils import is_game_armature
            return is_game_armature(context, "ZENLESS_ZONE_ZERO")
        except Exception:
            pass
        return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        try:
            pull_zzz_panel_values(scene, context)
        except Exception:
            pass

        arm = None
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
        except Exception:
            pass

        from setup_wizard.character_rig_setup.lighting_panel_setup import (
            armature_has_lighting_panel,
        )
        has_lp = armature_has_lighting_panel(arm)

        is_legacy = (getattr(scene, "zzz_shader_type", "KYTHERA") == "LEGACY")
        if not is_legacy:
            has_legacy = any("global material properties" in ng.name.lower() for ng in bpy.data.node_groups)
            has_kythera = any("kythera" in ng.name.lower() for ng in bpy.data.node_groups) or any("face shader" in ng.name.lower() for ng in bpy.data.node_groups)
            if has_legacy and not has_kythera:
                is_legacy = True

        if has_lp:
            col_type = layout.column(align=False)
            col_type.label(text="Lighting Type:")
            row_btn = col_type.row(align=True)
            row_btn.prop(scene, "zzz_lighting_control_type", expand=True)

            is_lp_mode = (getattr(scene, "zzz_lighting_control_type", "PANEL") == "PANEL")

            if not is_lp_mode:
                col_light = layout.column(align=True)
                col_light.label(text="Lighting Mode:")
                col_light.prop(scene, "zzz_light_mode", text="")

                if getattr(scene, "zzz_light_mode", "0") == "6":
                    box_shading = layout.box()
                    box_shading.label(text="Shading & Tints", icon="COLOR")
                    col_shading = box_shading.column(align=True)
                    col_shading.prop(scene, "zzz_ambient_tint", text="Ambient")
                    col_shading.prop(scene, "zzz_lit_tint", text="Lit Tint")
                    col_shading.prop(scene, "zzz_lit_brightness", text="Lit Brightness", slider=True)
                    col_shading.prop(scene, "zzz_shadow_tint", text="Shadow Tint")
                    col_shading.prop(scene, "zzz_shadow_intensity", text="Shadow Intensity", slider=True)
                    col_shading.prop(scene, "zzz_fake_sss_intensity", text="Fake SSS Intensity", slider=True)

                box_rim = layout.box()
                box_rim.label(text="Rim Light", icon="LIGHT_SUN")
                box_rim.prop(scene, "zzz_enable_rim_light", text="Enable Rim Light")

                if not is_legacy:
                    col_rim = box_rim.column(align=True)
                    col_rim.active = scene.zzz_enable_rim_light
                    col_rim.prop(scene, "zzz_rim_brightness", text="Brightness", slider=True)
                    col_rim.prop(scene, "zzz_rim_left_right", text="Left / Right", slider=True)
                    col_rim.prop(scene, "zzz_rim_up_down", text="Up / Down", slider=True)
                    if getattr(scene, "zzz_light_mode", "0") == "6":
                        col_rim.prop(scene, "zzz_rim_light_color", text="Color")
                else:
                    if getattr(scene, "zzz_light_mode", "0") == "6":
                        col_rim = box_rim.column(align=True)
                        col_rim.active = scene.zzz_enable_rim_light
                        col_rim.prop(scene, "zzz_rim_light_color", text="Color")
            else:
                box_rim = layout.box()
                box_rim.label(text="Rim Light", icon="LIGHT_SUN")
                box_rim.prop(scene, "zzz_enable_rim_light", text="Enable Rim Light")
        else:
            col_light = layout.column(align=True)
            col_light.label(text="Lighting Mode:")
            col_light.prop(scene, "zzz_light_mode", text="")

            if getattr(scene, "zzz_light_mode", "0") == "6":
                box_shading = layout.box()
                box_shading.label(text="Shading & Tints", icon="COLOR")
                col_shading = box_shading.column(align=True)
                col_shading.prop(scene, "zzz_ambient_tint", text="Ambient")
                col_shading.prop(scene, "zzz_lit_tint", text="Lit Tint")
                col_shading.prop(scene, "zzz_lit_brightness", text="Lit Brightness", slider=True)
                col_shading.prop(scene, "zzz_shadow_tint", text="Shadow Tint")
                col_shading.prop(scene, "zzz_shadow_intensity", text="Shadow Intensity", slider=True)
                col_shading.prop(scene, "zzz_fake_sss_intensity", text="Fake SSS Intensity", slider=True)

            box_rim = layout.box()
            box_rim.label(text="Rim Light", icon="LIGHT_SUN")
            box_rim.prop(scene, "zzz_enable_rim_light", text="Enable Rim Light")

            if not is_legacy:
                col_rim = box_rim.column(align=True)
                col_rim.active = scene.zzz_enable_rim_light
                col_rim.prop(scene, "zzz_rim_brightness", text="Brightness", slider=True)
                col_rim.prop(scene, "zzz_rim_left_right", text="Left / Right", slider=True)
                col_rim.prop(scene, "zzz_rim_up_down", text="Up / Down", slider=True)
                if getattr(scene, "zzz_light_mode", "0") == "6":
                    col_rim.prop(scene, "zzz_rim_light_color", text="Color")
            else:
                if getattr(scene, "zzz_light_mode", "0") == "6":
                    col_rim = box_rim.column(align=True)
                    col_rim.active = scene.zzz_enable_rim_light
                    col_rim.prop(scene, "zzz_rim_light_color", text="Color")

        # Hair & Clothes Physics
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




def register_zzz_properties():
    from bpy.props import EnumProperty, FloatProperty, FloatVectorProperty, BoolProperty

    try:
        bpy.utils.register_class(ZZZ_OT_SelectLightingPanel)
    except Exception:
        pass
    try:
        bpy.utils.register_class(ZZZ_OT_ToggleLightingPanelVisibility)
    except Exception:
        pass

    bpy.types.Scene.zzz_lighting_control_type = EnumProperty(
        name="Lighting Control",
        description="Choose how lighting colors and tints are controlled for ZZZ",
        items=[
            ("PANEL", "Light Panel", "Use 3D Lighting Panel in viewport"),
            ("THIS_PANEL", "This Panel", "Use Character Settings panel controls"),
        ],
        default="PANEL",
        update=update_zzz_lighting_control_type,
    )

    bpy.types.Scene.zzz_light_mode = EnumProperty(
        name="Light Mode",
        description="Lighting preset mode for Kythera ZZZ shader",
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
        update=update_zzz_light_mode,
    )

    bpy.types.Scene.zzz_ambient_tint = FloatVectorProperty(
        name="Ambient Tint",
        description="Ambient color tint for Kythera ZZZ shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_lit_tint = FloatVectorProperty(
        name="Lit Tint",
        description="Lit color tint for Kythera ZZZ shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_lit_brightness = FloatProperty(
        name="Lit Brightness",
        description="Lit brightness offset for Kythera ZZZ shader",
        min=0.0,
        max=1.0,
        default=0.0,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_shadow_tint = FloatVectorProperty(
        name="Shadow Tint",
        description="Shadow color tint for Kythera ZZZ shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.65, 0.65, 0.85),
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_shadow_intensity = FloatProperty(
        name="Shadow Intensity",
        description="Shadow intensity for Kythera ZZZ shader",
        min=0.0,
        max=1.0,
        default=1.0,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_fake_sss_intensity = FloatProperty(
        name="Fake SSS Intensity",
        description="Fake SSS intensity for Kythera ZZZ shader",
        min=0.0,
        max=1.0,
        default=1.0,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_enable_rim_light = BoolProperty(
        name="Enable Rim Light",
        description="Enable or disable rim light on Kythera ZZZ shader",
        default=True,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_rim_light_color = FloatVectorProperty(
        name="Rim Light Color",
        description="Rim light color tint for Kythera ZZZ shader",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_rim_coverage = FloatProperty(
        name="Coverage",
        description="Rim light coverage for Kythera ZZZ shader",
        min=0.0,
        max=1.0,
        default=1.0,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_rim_brightness = FloatProperty(
        name="Brightness",
        description="Rim light brightness for Kythera ZZZ shader",
        min=0.0,
        max=1.0,
        default=1.0,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_rim_left_right = FloatProperty(
        name="Left / Right",
        description="Rim light horizontal direction offset",
        min=0.0,
        max=1.0,
        default=0.5,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )

    bpy.types.Scene.zzz_rim_up_down = FloatProperty(
        name="Up / Down",
        description="Rim light vertical direction offset",
        min=0.0,
        max=1.0,
        default=0.1,
        step=10,
        precision=1,
        update=update_zzz_kythera_props,
    )


def unregister_zzz_properties():
    try:
        bpy.utils.unregister_class(ZZZ_OT_SelectLightingPanel)
    except Exception:
        pass
    try:
        bpy.utils.unregister_class(ZZZ_OT_ToggleLightingPanelVisibility)
    except Exception:
        pass

    props = [
        "zzz_lighting_control_type",
        "zzz_light_mode",
        "zzz_ambient_tint",
        "zzz_lit_tint",
        "zzz_lit_brightness",
        "zzz_shadow_tint",
        "zzz_shadow_intensity",
        "zzz_fake_sss_intensity",
        "zzz_enable_rim_light",
        "zzz_rim_light_color",
        "zzz_rim_coverage",
        "zzz_rim_brightness",
        "zzz_rim_left_right",
        "zzz_rim_up_down",
    ]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)

