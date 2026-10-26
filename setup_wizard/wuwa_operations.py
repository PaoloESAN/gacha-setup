# Based on Blender-WuWa-Character-Setup by @fnoji (https://github.com/fnoji/Blender-WuWa-Character-Setup)
# Gustling Waters integration by @nytsjared (https://github.com/nytsjared)
# Adapted for Gacha Setup by PaoloESAN
# Licensed under GPL-3.0-or-later

import bpy
import os
import re
from bpy.types import Operator, Panel
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)


def _settings_target(context):
    if _is_updating_ww_light_props:
        return None, []
    from setup_wizard.ui.character_settings_utils import get_character_settings_materials
    return get_character_settings_materials(context, 'WUTHERING_WAVES')


def _property_nodes(materials):
    for mat in materials:
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree and 'global material properties' in node.node_tree.name.lower():
                    yield node


def get_global_material_properties_group(context=None):
    _, mats = _settings_target(context)
    return next((n.node_tree for n in _property_nodes(mats)), None)


def update_material_property(node_group_name, input_name, value, context=None):
    _, mats = _settings_target(context)
    for node in _property_nodes(mats):
        if node_group_name.lower() not in node.node_tree.name.lower():
            continue
        def assign(socket):
            socket.default_value = bool(value) if socket.type == 'BOOLEAN' else value
        if input_name in node.inputs:
            assign(node.inputs[input_name])
        group = node.node_tree
        for n in group.nodes:
            sockets = n.inputs if n.type == 'GROUP_OUTPUT' else n.outputs if n.type == 'GROUP_INPUT' else ()
            if input_name in sockets:
                assign(sockets[input_name])
        for item in group.interface.items_tree:
            if item.item_type == 'SOCKET' and item.name == input_name and hasattr(item, 'default_value'):
                item.default_value = bool(value) if item.socket_type == 'NodeSocketBool' else value
    # Current shaders expose some controls directly instead of through GMP.
    aliases = {'Face Shadow Softness': ('Face Shadow Softness', 'Face Shadows Softness')}
    for mat in mats:
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'GROUP':
                continue
            for name in aliases.get(input_name, (input_name,)):
                if name in node.inputs:
                    socket = node.inputs[name]
                    socket.default_value = bool(value) if socket.type == 'BOOLEAN' else value


def _set_global_property(context, name, value):
    update_material_property('Global Material Properties', name, value, context=context)


def update_alpha_transparency(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    try:
        enabled = bool(getattr(self, "ww_alpha_transparency", True))
    except Exception:
        enabled = True

    for mat in target_materials:
        orig_m = mat.get("ww_original_name", "")
        base_m = mat.get("ww_base_part", "")
        is_alpha = any(
            k in orig_m.lower() or k in base_m.lower() or k in mat.name.lower()
            for k in ["alpha", "touming", "transparency", "fur", "flur"]
        )
        if is_alpha and mat.node_tree:
            for node in mat.node_tree.nodes:
                if (node.type == 'GROUP' and node.node_tree and "alpha transparency" in node.node_tree.name.lower()) or "alpha transparency" in node.name.lower():
                    node.mute = not enabled
            if enabled:
                if hasattr(mat, "surface_render_method"):
                    try:
                        mat.surface_render_method = 'BLENDED'
                    except Exception:
                        pass
                if hasattr(mat, "blend_method"):
                    try:
                        mat.blend_method = 'BLEND'
                    except Exception:
                        pass
                if hasattr(mat, "shadow_method"):
                    try:
                        mat.shadow_method = 'HASHED'
                    except Exception:
                        pass
                if hasattr(mat, "use_transparency_overlap"):
                    try:
                        mat.use_transparency_overlap = False
                    except Exception:
                        pass
            else:
                if hasattr(mat, "surface_render_method"):
                    try:
                        mat.surface_render_method = 'DITHERED'
                    except Exception:
                        pass
                if hasattr(mat, "blend_method"):
                    try:
                        mat.blend_method = 'OPAQUE'
                    except Exception:
                        pass


# Appearance Property Update Callbacks
def update_blush(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    try:
        val = float(getattr(self, "ww_blush_value", 0.0))
    except Exception:
        val = 0.0

    def apply_blush_to_container(container):
        if not container or not hasattr(container, "nodes"):
            return
        for node in container.nodes:
            if hasattr(node, "inputs"):
                for inp in node.inputs:
                    inp_low = inp.name.lower().strip()
                    if inp_low == "blush":
                        try:
                            inp.default_value = True
                        except Exception:
                            try:
                                inp.default_value = 1.0
                            except Exception:
                                pass
                    elif "blush" in inp_low and any(k in inp_low for k in ["intensity", "multiplier", "value", "amount"]):
                        try:
                            inp.default_value = val
                        except Exception:
                            pass

            if node.type == 'GROUP_INPUT' and hasattr(node, "outputs"):
                for out in node.outputs:
                    out_low = out.name.lower().strip()
                    if out_low == "blush":
                        try:
                            out.default_value = True
                        except Exception:
                            try:
                                out.default_value = 1.0
                            except Exception:
                                pass
                    elif "blush" in out_low and any(k in out_low for k in ["intensity", "multiplier", "value", "amount"]):
                        try:
                            out.default_value = val
                        except Exception:
                            pass

    mats_to_update = target_materials
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree and any(k in mat.name.lower() for k in ["face", "head", "skin", "body"]):
            apply_blush_to_container(mat.node_tree)


def update_disgust(self, context=None):
    _set_global_property(context, "Disgust Multiplier", getattr(self, "ww_disgust_value", 0.0))



def update_metallic(self, context=None):
    _set_global_property(context, "Metallic Multiplier", getattr(self, "ww_metallic_value", 1.0))



def update_specular(self, context=None):
    _set_global_property(context, "Specular Multiplier", getattr(self, "ww_specular_value", 1.0))



def update_custom_colors(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    amb = (*getattr(self, "ww_amb_color", (0.5, 0.5, 0.5)), 1.0)
    light = (*getattr(self, "ww_light_color", (1.0, 1.0, 1.0)), 1.0)
    shadow = (*getattr(self, "ww_shadow_color", (0.3, 0.3, 0.4)), 1.0)
    rim = (*getattr(self, "ww_rim_color", (1.0, 1.0, 1.0)), 1.0)

    # 1. Update in Color Palette Node Group definition
    color_pairs = [
        ("Custom Ambient", amb), ("Amb Color", amb), ("Custom Amb", amb),
        ("Custom Light", light), ("Light Color", light),
        ("Custom Shadow", shadow), ("Shadow Color", shadow),
        ("Custom Rim Tint", rim), ("Custom Rim", rim), ("Rim Color", rim), ("Rim Tint", rim),
    ]

    gmp_trees = set()
    palette_nodes = []
    palette_trees = set()

    mats_to_update = target_materials
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_name = node.node_tree.name.lower()
                    if "color palette" in nt_name:
                        palette_nodes.append(node)
                        palette_trees.add(node.node_tree)
                    elif "global material properties" in nt_name:
                        gmp_trees.add(node.node_tree)

    for gmp in gmp_trees:
        if hasattr(gmp, "nodes"):
            for n in gmp.nodes:
                if n.type == 'GROUP' and n.node_tree and "color palette" in n.node_tree.name.lower():
                    palette_nodes.append(n)
                    palette_trees.add(n.node_tree)

    # 1. Update on Color Palette node instances (in GMP or materials)
    for n in palette_nodes:
        for socket_name, col_val in color_pairs:
            if socket_name in n.inputs:
                try:
                    n.inputs[socket_name].default_value = col_val
                except Exception:
                    pass

    # 2. Update on Color Palette trees (GROUP_INPUT outputs and interface defaults)
    for tree in palette_trees:
        if hasattr(tree, "nodes"):
            for node in tree.nodes:
                if node.type == 'GROUP_INPUT':
                    for socket_name, col_val in color_pairs:
                        if socket_name in node.outputs:
                            try:
                                node.outputs[socket_name].default_value = col_val
                            except Exception:
                                pass
        if hasattr(tree, "interface") and hasattr(tree.interface, "items_tree"):
            for item in tree.interface.items_tree:
                for socket_name, col_val in color_pairs:
                    if item.name == socket_name:
                        try:
                            item.default_value = col_val
                        except Exception:
                            pass


def update_shadow_range(self, context=None):
    _set_global_property(context, "Shadow Transition Range", getattr(self, "ww_shadow_transition_range_value", 0.05))



def update_face_shadow_softness(self, context=None):
    _set_global_property(context, "Face Shadow Softness", getattr(self, "ww_face_shadow_softness_value", 0.05))



def update_catch_shadows(self, context=None):
    _set_global_property(context, "Catch Shadows", 1.0 if getattr(self, "ww_catch_shadows", True) else 0.0)



WW_LIGHT_PRESETS = {
    "0": {  # Default (Value = 0)
        "ambient": (1.0, 1.0, 1.0),
        "light": (1.0, 1.0, 1.0),
        "shadow": (0.9, 0.9, 0.9),
        "rim": (0.9, 0.9, 0.9),
    },
    "1": {  # Sunrise (Value = 1)
        "ambient": (1.0, 0.967269, 0.935483),
        "light": (1.0, 0.895639, 0.906351),
        "shadow": (0.76, 0.78477, 0.95),
        "rim": (1.0, 0.823099, 0.657774),
    },
    "2": {  # Day (Value = 2)
        "ambient": (1.0, 1.0, 1.0),
        "light": (1.0, 1.0, 1.0),
        "shadow": (0.81, 0.826437, 0.90),
        "rim": (1.0, 0.923343, 0.923343),
    },
    "3": {  # Sunset (Value = 3)
        "ambient": (1.0, 0.905373, 0.905373),
        "light": (1.0, 0.731331, 0.68462),
        "shadow": (0.778473, 0.758187, 0.90),
        "rim": (1.0, 0.800843, 0.505831),
    },
    "4": {  # Night (Value = 4)
        "ambient": (0.92078, 0.949791, 1.0),
        "light": (0.794931, 0.859457, 1.0),
        "shadow": (0.90, 0.934303, 1.0),
        "rim": (0.492182, 0.678144, 1.0),
    },
    "5": {  # Rainy (Value = 5)
        "ambient": (0.900502, 0.922236, 0.945747),
        "light": (0.445574, 0.445574, 0.445574),
        "shadow": (0.511766, 0.511766, 0.511766),
        "rim": (0.28772, 0.28772, 0.28772),
    },
}

_is_updating_ww_light_props = False

def update_light_mode(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    global _is_updating_ww_light_props
    if _is_updating_ww_light_props:
        return
    mode = str(getattr(self, "ww_light_mode", "0"))
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        arm = resolve_settings_armature(context)
        if arm:
            arm["ww_light_mode"] = str(mode)
    except Exception:
        pass

    if mode in WW_LIGHT_PRESETS:
        preset = WW_LIGHT_PRESETS[mode]
        _is_updating_ww_light_props = True
        try:
            self.ww_amb_color = preset["ambient"]
            self.ww_light_color = preset["light"]
            self.ww_shadow_color = preset["shadow"]
            self.ww_rim_color = preset["rim"]
        except Exception:
            pass
        finally:
            _is_updating_ww_light_props = False

    try:
        mode_val = float(mode)
    except Exception:
        mode_val = 0.0

    try:
        arm["ww_light_mode"] = str(mode)
    except Exception:
        pass

    gmp_trees = set()
    palette_nodes = []
    palette_trees = set()

    mats_to_update = target_materials
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_name = node.node_tree.name.lower()
                    if "color palette" in nt_name:
                        palette_nodes.append(node)
                        palette_trees.add(node.node_tree)
                    elif "global material properties" in nt_name:
                        gmp_trees.add(node.node_tree)

    for gmp in gmp_trees:
        if hasattr(gmp, "nodes"):
            for n in gmp.nodes:
                if n.type == 'GROUP' and n.node_tree and "color palette" in n.node_tree.name.lower():
                    palette_nodes.append(n)
                    palette_trees.add(n.node_tree)

    # 1. Update on Color Palette node instances (in GMP or materials)
    for n in palette_nodes:
        if "Value" in n.inputs:
            try:
                n.inputs["Value"].default_value = mode_val
            except Exception:
                pass
        if "Light Mode" in n.inputs:
            try:
                n.inputs["Light Mode"].default_value = mode_val
            except Exception:
                pass

    # 2. Update on Color Palette trees (GROUP_INPUT outputs and interface defaults)
    for tree in palette_trees:
        if hasattr(tree, "nodes"):
            for node in tree.nodes:
                if node.type == 'GROUP_INPUT':
                    if "Value" in node.outputs:
                        try:
                            node.outputs["Value"].default_value = mode_val
                        except Exception:
                            pass
                    if "Light Mode" in node.outputs:
                        try:
                            node.outputs["Light Mode"].default_value = mode_val
                        except Exception:
                            pass
        if hasattr(tree, "interface") and hasattr(tree.interface, "items_tree"):
            for item in tree.interface.items_tree:
                if item.name in ("Value", "Light Mode"):
                    try:
                        item.default_value = mode_val
                    except Exception:
                        pass

    update_custom_colors(self, context)


def update_fresnel(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    scene = getattr(bpy.context, "scene", None) if not isinstance(self, bpy.types.Scene) else self
    if not scene:
        return
    use_fresnel = bool(getattr(scene, "ww_use_fresnel", False))
    col = getattr(scene, "ww_fresnel_color", (1.0, 1.0, 1.0))
    col_rgba = (*col[:3], 1.0) if len(col) == 3 else col
    scale = float(getattr(scene, "ww_fresnel_scale", 2.0))
    strength = float(getattr(scene, "ww_fresnel_strength", 2.0))

    fresnel_map = {
        "Use Fresnel": use_fresnel,
        "Fresnel Color": col_rgba,
        "Fresnel Scale": scale,
        "Fresnel Strength": strength,
    }

    target_trees = set()
    mats_to_update = target_materials
    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower():
                        target_trees.add(node.node_tree)

    for tree in target_trees:
        out_node = tree.nodes.get("Global Properties") or tree.nodes.get("Group Output")
        if out_node:
            for name, val in fresnel_map.items():
                if name in out_node.inputs:
                    inp = out_node.inputs[name]
                    for l in list(inp.links):
                        tree.links.remove(l)
                    try:
                        inp.default_value = val
                    except Exception:
                        pass
        if hasattr(tree, "interface") and hasattr(tree.interface, "items_tree"):
            for item in tree.interface.items_tree:
                if item.name in fresnel_map:
                    try:
                        item.default_value = fresnel_map[item.name]
                    except Exception:
                        pass

    for mat in mats_to_update:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower():
                        for name, val in fresnel_map.items():
                            if name in node.inputs:
                                try:
                                    node.inputs[name].default_value = val
                                except Exception:
                                    pass

    # Tag 3D viewports for redraw
    if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
        for win in getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()


def pull_wuwa_panel_values(scene, context, force=False):
    """Synchronizes UI sliders and lighting mode with the selected character's materials and rig."""
    global _is_updating_ww_light_props
    if _is_updating_ww_light_props or not scene:
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

    # 1. Find target Global Material Properties and Color Palette node groups
    target_gmp_tree = None
    target_palette_tree = None
    target_palette_node = None
    target_blush = None

    for m in mats:
        if getattr(m, "use_nodes", False) and m.node_tree:
            for node in m.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    tname = node.node_tree.name.lower()
                    if "global material properties" in tname and not target_gmp_tree:
                        target_gmp_tree = node.node_tree
                        for sub in getattr(node.node_tree, "nodes", []) or []:
                            if getattr(sub, "type", None) == 'GROUP' and sub.node_tree and "color palette" in sub.node_tree.name.lower():
                                target_palette_tree = sub.node_tree
                                target_palette_node = sub
                                break
                    if "color palette" in tname and not target_palette_tree:
                        target_palette_tree = node.node_tree
                        target_palette_node = node
                    if any(k in tname for k in ["blush", "face"]) and not target_blush:
                        target_blush = node
        if target_gmp_tree and target_palette_tree and target_blush:
            break

    # 2. Pull lighting mode saved on this armature or read from node
    saved_mode = arm.get("ww_light_mode")
    if saved_mode is None and target_palette_node and "Value" in target_palette_node.inputs:
        try:
            saved_mode = str(int(round(target_palette_node.inputs["Value"].default_value)))
        except Exception:
            saved_mode = "0"
    elif saved_mode is None:
        saved_mode = "0"

    if getattr(scene, "ww_light_mode", "") != str(saved_mode):
        _is_updating_ww_light_props = True
        try:
            scene.ww_light_mode = str(saved_mode)
        finally:
            _is_updating_ww_light_props = False

    _is_updating_ww_light_props = True
    try:
        # Pull Fresnel from GMP out_node
        if target_gmp_tree:
            out_node = target_gmp_tree.nodes.get("Global Properties") or target_gmp_tree.nodes.get("Group Output")
            if out_node:
                inputs = out_node.inputs
                if "Use Fresnel" in inputs:
                    scene.ww_use_fresnel = bool(inputs["Use Fresnel"].default_value > 0.5)
                if "Fresnel Color" in inputs:
                    scene.ww_fresnel_color = tuple(inputs["Fresnel Color"].default_value)[:3]
                if "Fresnel Scale" in inputs:
                    scene.ww_fresnel_scale = float(inputs["Fresnel Scale"].default_value)
                if "Fresnel Strength" in inputs:
                    scene.ww_fresnel_strength = float(inputs["Fresnel Strength"].default_value)
                for name, prop in [
                    ('Catch Shadows', 'ww_catch_shadows'),
                    ('Metallic Multiplier', 'ww_metallic_value'),
                    ('Specular Multiplier', 'ww_specular_value'),
                    ('Disgust Multiplier', 'ww_disgust_value'),
                    ('Shadow Transition Range', 'ww_shadow_transition_range_value'),
                    ('Face Shadow Softness', 'ww_face_shadow_softness_value'),
                ]:
                    if name in inputs:
                        setattr(scene, prop, inputs[name].default_value)

        # Pull Palette colors
        cur_mode = getattr(scene, "ww_light_mode", "0")
        if cur_mode in WW_LIGHT_PRESETS and cur_mode != "6":
            preset = WW_LIGHT_PRESETS[cur_mode]
            scene.ww_amb_color = preset["ambient"]
            scene.ww_light_color = preset["light"]
            scene.ww_shadow_color = preset["shadow"]
            scene.ww_rim_color = preset["rim"]
        elif target_palette_node:
            inputs = target_palette_node.inputs
            if "Custom Ambient" in inputs:
                scene.ww_amb_color = tuple(inputs["Custom Ambient"].default_value)[:3]
            elif "Amb Color" in inputs:
                scene.ww_amb_color = tuple(inputs["Amb Color"].default_value)[:3]
            if "Custom Light" in inputs:
                scene.ww_light_color = tuple(inputs["Custom Light"].default_value)[:3]
            elif "Light Color" in inputs:
                scene.ww_light_color = tuple(inputs["Light Color"].default_value)[:3]
            if "Custom Shadow" in inputs:
                scene.ww_shadow_color = tuple(inputs["Custom Shadow"].default_value)[:3]
            elif "Shadow Color" in inputs:
                scene.ww_shadow_color = tuple(inputs["Shadow Color"].default_value)[:3]
            if "Custom Rim Tint" in inputs:
                scene.ww_rim_color = tuple(inputs["Custom Rim Tint"].default_value)[:3]
            elif "Rim Color" in inputs:
                scene.ww_rim_color = tuple(inputs["Rim Color"].default_value)[:3]

        if target_blush:
            softness = target_blush.inputs.get('Face Shadows Softness')
            if softness is not None:
                scene.ww_face_shadow_softness_value = softness.default_value
            for inp in target_blush.inputs:
                inp_low = inp.name.lower().strip()
                if "blush" in inp_low and any(k in inp_low for k in ["intensity", "multiplier", "value", "amount"]):
                    scene.ww_blush_value = float(inp.default_value)
                    break
        from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
        from setup_wizard.utils.modifier_utils import get_modifier_property
        for mesh in _iter_rig_meshes(arm):
            found_width = False
            for mod in mesh.modifiers:
                if mod.type != 'NODES' or not mod.node_group or 'outline' not in mod.node_group.name.lower():
                    continue
                for item in mod.node_group.interface.items_tree:
                    if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == 'Outline Thickness':
                        scene.ww_outline_thickness = float(get_modifier_property(mod, item.identifier))
                        found_width = True
                        break
                if found_width:
                    break
            if found_width:
                break
    except Exception:
        pass
    finally:
        _is_updating_ww_light_props = False


def update_outline_settings(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    scene = getattr(bpy.context, "scene", None) if not isinstance(self, bpy.types.Scene) else self
    if not scene:
        return

    ol_mode = getattr(scene, "ww_outline_mode", "NORMAL")
    col1 = getattr(scene, "ww_outline_color_1", (0.0, 0.0, 0.0))
    col2 = getattr(scene, "ww_outline_color_2", (0.0, 0.0, 0.0))

    col1_rgba = (*col1[:3], 1.0) if len(col1) == 3 else col1
    col2_rgba = (*col2[:3], 1.0) if len(col2) == 3 else col2
    factor_val = 1.0 if ol_mode == "CUSTOM" else 0.0

    for mat in target_materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        if mat.name != "WW - Outlines" and not mat.name.startswith("WW - Outlines"):
            continue

        nodes = mat.node_tree.nodes

        mix1 = nodes.get("Mix_Outline_Color_1")
        mix2 = nodes.get("Mix_Outline_Color_2")
        outlines_node = nodes.get("Outlines")

        if mix1:
            try:
                mix1.inputs[0].default_value = factor_val
                mix1.inputs[7].default_value = col1_rgba
            except Exception:
                pass

        if mix2:
            try:
                mix2.inputs[0].default_value = factor_val
                mix2.inputs[7].default_value = col2_rgba
            except Exception:
                pass

        if outlines_node and ol_mode == "CUSTOM":
            for inp in outlines_node.inputs:
                name_clean = inp.name.strip().lower()
                if name_clean == "outline color":
                    try:
                        inp.default_value = col1_rgba
                    except Exception:
                        pass
                elif name_clean == "outline color 2":
                    try:
                        inp.default_value = col2_rgba
                    except Exception:
                        pass

    if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
        for win in getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()


def update_outline_thickness(self, context=None):
    arm, target_materials = _settings_target(context)
    if not arm or not target_materials:
        return
    scene = getattr(bpy.context, "scene", None) if not isinstance(self, bpy.types.Scene) else self
    if not scene:
        return
    val = float(getattr(scene, "ww_outline_thickness", 0.2))

    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
    from setup_wizard.utils.modifier_utils import set_modifier_property
    updated_any = False
    for obj in _iter_rig_meshes(arm):
        for mod in obj.modifiers:
            if mod.type != 'NODES' or not mod.node_group or 'outline' not in mod.node_group.name.lower():
                continue
            for item in mod.node_group.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name.strip() == 'Outline Thickness':
                    set_modifier_property(mod, item.identifier, val)
                    obj.update_tag(refresh={'DATA'})
                    updated_any = True
                    break

    if updated_any and hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
        for win in getattr(bpy.context.window_manager, 'windows', []):
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()


def sync_wuwa_shader_properties(scene=None, context=None):
    """Applies scene panel values only to an explicit character target."""
    scene = scene or getattr(bpy.context, "scene", None)
    if not scene:
        return
    update_blush(scene, context)
    update_light_mode(scene, context)
    update_custom_colors(scene, context)
    update_shadow_range(scene, context)
    update_face_shadow_softness(scene, context)
    update_catch_shadows(scene, context)
    update_metallic(scene, context)
    update_specular(scene, context)
    update_disgust(scene, context)
    update_alpha_transparency(scene, context)
    update_fresnel(scene, context)
    update_outline_settings(scene, context)
    update_outline_thickness(scene, context)


# Animate Mode: Swapping materials for low-poly/simplified fast viewport playback
ANIMATE_MODE_SUFFIX = "_Low"

def get_animate_mode_meshes(arm):
    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
    return [obj for obj in _iter_rig_meshes(arm)
            if not obj.name.startswith('WGT-') and not any(
                coll.name.startswith('WGTS') for coll in obj.users_collection)]


def set_animate_mode(enable: bool, context=None, arm=None):
    from setup_wizard.ui.character_settings_utils import resolve_settings_armature
    context = context or bpy.context
    arm = arm or resolve_settings_armature(context)
    if not arm:
        return
    meshes = get_animate_mode_meshes(arm)
    set_animate_mode_outlines(enable, meshes)
    for obj in meshes:
        for slot_index, slot in enumerate(obj.material_slots):
            mat = slot.material
            if not mat:
                continue

            if enable:
                if mat.get('_ww_animate_source'):
                    mat['_ww_animate_source'].use_fake_user = True
                    continue
                mat.use_fake_user = True
                low_name = mat.name[:24] + '_' + arm.name[:24] + ANIMATE_MODE_SUFFIX
                low_mat = next((candidate for candidate in bpy.data.materials
                                if candidate.get('_ww_animate_source') == mat
                                and candidate.get('_ww_animate_rig') == arm), None)
                if not low_mat:
                    low_mat = bpy.data.materials.new(name=low_name)
                    low_mat.use_nodes = True
                    low_mat['_ww_animate_source'] = mat
                    low_mat['_ww_animate_rig'] = arm
                    low_mat.node_tree.nodes.clear()
                    material_output = low_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')

                    # Find diffuse image from original material
                    diff_img = None
                    def _is_bad_tex(name: str) -> bool:
                        if not name:
                            return False
                        n = name.lower()
                        tokens = [
                            'lightmap', 'light_map', '_lm.', '_lm_', '_ld.', '_ld_', '_id.', '_id_',
                            'normal', '_norm.', '_norm_', '_n.', '_n_', 'bump',
                            'ramp', 'shadow', '_mask.', '_mask_', 'mask_',
                            'metal', 'metallic', 'specular', '_spec.', '_spec_',
                            'roughness', 'curvature', 'nyx', 'height', 'depth',
                            'ambient_occlusion', 'ambientocclusion', '_ao.', '_ao_', 'ao_'
                        ]
                        return any(tok in n for tok in tokens)

                    if mat.use_nodes and mat.node_tree:
                        # 1. Tracing from Material Output -> Surface -> Main Shader
                        output = mat.node_tree.nodes.get("Material Output")
                        main_nodes = []
                        if output and "Surface" in output.inputs and output.inputs["Surface"].is_linked:
                            for link in output.inputs["Surface"].links:
                                fn = link.from_node
                                while fn and fn.type == 'REROUTE':
                                    fn = fn.inputs[0].links[0].from_node if (fn.inputs and fn.inputs[0].is_linked) else None
                                if fn:
                                    main_nodes.append(fn)

                        for node in mat.node_tree.nodes:
                            if node.type in ('GROUP', 'BSDF_PRINCIPLED', 'EMISSION') and node not in main_nodes:
                                main_nodes.append(node)

                        for node in main_nodes:
                            for inp_name in ('Diffuse', 'Diffuse (sRGB)', 'Main Diffuse', 'Base Color', 'Color'):
                                inp = node.inputs.get(inp_name)
                                if inp and inp.is_linked:
                                    for link in inp.links:
                                        from_node = link.from_node
                                        while from_node and from_node.type == 'REROUTE':
                                            from_socket = from_node.inputs[0] if from_node.inputs else None
                                            from_node = from_socket.links[0].from_node if (from_socket and from_socket.is_linked) else None
                                        if from_node and from_node.type == 'TEX_IMAGE' and getattr(from_node, "image", None):
                                            if inp_name == 'Color' and _is_bad_tex(from_node.image.name):
                                                continue
                                            if not _is_bad_tex(from_node.image.name):
                                                diff_img = from_node.image
                                                break
                                if diff_img:
                                    break
                            if diff_img:
                                break

                        # 2. Check diffuse keywords excluding bad keywords
                        if not diff_img:
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                                    img_low = node.image.name.lower()
                                    if any(k in img_low for k in ['_d.', '_d_', '_diff', 'diff', 'basecolor', 'base_color', 'albedo']):
                                        if not _is_bad_tex(img_low):
                                            diff_img = node.image
                                            break

                        # 3. Any TEX_IMAGE without bad keywords
                        if not diff_img:
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                                    img_low = node.image.name.lower()
                                    node_low = node.name.lower()
                                    if not _is_bad_tex(img_low) and not _is_bad_tex(node_low):
                                        diff_img = node.image
                                        break

                        # 4. Fallback to any TEX_IMAGE
                        if not diff_img:
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                                    diff_img = node.image
                                    break

                    if diff_img:
                        tex_node = low_mat.node_tree.nodes.new("ShaderNodeTexImage")
                        tex_node.image = diff_img
                        low_mat.node_tree.links.new(tex_node.outputs["Color"], material_output.inputs["Surface"])

                # Object slots keep linked mesh duplicates on other characters intact.
                links_key = '_ww_animate_slot_links'
                links = dict(obj.get(links_key, {}))
                index = str(slot_index)
                links.setdefault(index, slot.link)
                obj[links_key] = links
                slot.link = 'OBJECT'
                slot.material = low_mat
            else:
                if mat.get('_ww_animate_source'):
                    orig_mat = mat['_ww_animate_source']
                    if orig_mat:
                        slot.material = orig_mat
                        links = dict(obj.get('_ww_animate_slot_links', {}))
                        slot.link = links.pop(str(slot_index), slot.link)
                        if links:
                            obj['_ww_animate_slot_links'] = links
                        elif '_ww_animate_slot_links' in obj:
                            del obj['_ww_animate_slot_links']
    arm['ww_animate_mode'] = bool(enable)
    context.view_layer.update()


def set_animate_mode_outlines(enable, meshes):
    """Hide WuWa viewport outlines and restore their state on leaving Animate Mode."""
    key = '_ww_animate_outline_states'
    for obj in meshes:
        states = {name: dict(state) for name, state in obj.get(key, {}).items()}
        for mod in obj.modifiers:
            group = getattr(mod, 'node_group', None)
            if enable:
                if 'ww - outlines' not in mod.name.lower() and not (
                    group and 'ww - outlines' in group.name.lower()
                ):
                    continue
            elif mod.name not in states:
                continue
            path = mod.path_from_id('show_viewport')
            drivers = obj.animation_data.drivers if obj.animation_data else []
            driver = next((d for d in drivers if d.data_path == path), None)
            if enable:
                states.setdefault(mod.name, {
                    'visible': mod.show_viewport,
                    'driver_muted': driver.mute if driver else False,
                })
                if driver:
                    driver.mute = True
                mod.show_viewport = False
            else:
                state = states.pop(mod.name)
                if driver:
                    driver.mute = bool(state['driver_muted'])
                mod.show_viewport = bool(state['visible'])
            obj.update_tag()
        if states:
            obj[key] = states
        elif key in obj:
            del obj[key]


# Operators
class WW_OT_ToggleAnimateMode(Operator):
    bl_idname = "wuthering_waves.toggle_animate_mode"
    bl_label = "Toggle Animate Mode"
    bl_description = "Use lightweight materials and disable viewport outlines for smooth animation playback"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        arm = resolve_settings_armature(context)
        if not arm:
            return {'CANCELLED'}
        current = arm.get("ww_animate_mode", False)
        new_val = not current
        set_animate_mode(new_val, context=context, arm=arm)
        status = "Enabled (Fast Playback)" if new_val else "Disabled (Full Shaders)"
        self.report({'INFO'}, f"Animate Mode {status}")
        return {'FINISHED'}


def get_viewport_outline_modifiers(context):
    """Return outline modifiers belonging to the selected character only."""
    from setup_wizard.ui.character_settings_utils import resolve_settings_armature
    arm = resolve_settings_armature(context)
    if not arm:
        return []
    result = []
    for obj in context.scene.objects:
        if obj.type != 'MESH':
            continue
        if obj.parent != arm and not any(
            mod.type == 'ARMATURE' and mod.object == arm for mod in obj.modifiers
        ):
            continue
        for mod in obj.modifiers:
            group = getattr(mod, 'node_group', None)
            if 'outline' in mod.name.lower() or (group and 'outline' in group.name.lower()):
                result.append((obj, mod))
    return result


class WW_OT_ToggleOutlines(Operator):
    bl_idname = "wuthering_waves.toggle_outlines"
    bl_label = "Toggle Outlines"
    bl_description = "Toggle viewport visibility for Wuthering Waves outline modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        modifiers = get_viewport_outline_modifiers(context)
        if not modifiers:
            self.report({'WARNING'}, "No outline modifiers found on the selected character.")
            return {'CANCELLED'}
        enable = not any(mod.show_viewport for _, mod in modifiers)
        for obj, mod in modifiers:
            # The face panel drives visibility every frame. Pause only the
            # viewport driver while hidden, preserving its previous mute state.
            path = mod.path_from_id('show_viewport')
            drivers = obj.animation_data.drivers if obj.animation_data else []
            driver = next((d for d in drivers if d.data_path == path), None)
            key = '_ww_viewport_outline_driver_states'
            if driver:
                states = dict(obj.get(key, {}))
                if not enable:
                    states.setdefault(mod.name, driver.mute)
                    driver.mute = True
                elif mod.name in states:
                    driver.mute = bool(states.pop(mod.name))
                if states:
                    obj[key] = states
                elif key in obj:
                    del obj[key]
            mod.show_viewport = enable
            obj.update_tag()
        context.view_layer.update()
        self.report({'INFO'}, f"Outlines in Viewport: {'ON' if enable else 'OFF'}")
        return {'FINISHED'}


class WW_OT_ToggleHairTrans(Operator):
    bl_idname = "wuthering_waves.toggle_hair_transparency"
    bl_label = "Toggle Hair Transparency"
    bl_description = "Toggle see-through / transparency effect on hair materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm, materials = _settings_target(context)
        if not arm or not materials:
            return {'CANCELLED'}
        from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
        toggled = False
        for mat in materials:
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree and "see through" in node.node_tree.name.lower():
                        node.mute = not node.mute
                        toggled = True

        for obj in _iter_rig_meshes(arm):
            if "_seethru" in obj.name.lower():
                obj.hide_viewport = not obj.hide_viewport
                toggled = True

        if toggled:
            self.report({'INFO'}, "Toggled Hair Transparency.")
        else:
            self.report({'WARNING'}, "No Hair Transparency / See Through nodes found.")
        return {'FINISHED'}


class WW_OT_ToggleStarMotion(Operator):
    bl_idname = "wuthering_waves.toggle_star_motion"
    bl_label = "Toggle Resonator Star"
    bl_description = "Toggle Resonator Star (Switch to Ult / Animation)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm, materials = _settings_target(context)
        if not arm or not materials:
            return {'CANCELLED'}
        from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
        toggled = 0

        # 1. Determine current state
        current_val = None

        def find_ult_val(container):
            if not container or not hasattr(container, "nodes"):
                return None
            for node in container.nodes:
                if hasattr(node, "inputs"):
                    for inp in node.inputs:
                        inp_low = inp.name.lower().strip()
                        if "switch" in inp_low and "ult" in inp_low:
                            return inp.default_value
                        if inp_low == "moving":
                            return inp.default_value
            return None

        for mat in materials:
            if mat.use_nodes and mat.node_tree:
                val = find_ult_val(mat.node_tree)
                if val is not None:
                    current_val = val
                    break

        if current_val is None:
            current_val = 1.0 if arm.get("ww_star_ult_state", False) else 0.0

        try:
            is_active = bool(float(current_val) > 0.5)
        except Exception:
            is_active = bool(current_val)

        new_bool = not is_active
        new_val = 1.0 if new_bool else 0.0
        arm["ww_star_ult_state"] = new_bool

        # 2. Apply to the selected character's material instances.
        def apply_ult_val(container):
            nonlocal toggled
            if not container or not hasattr(container, "nodes"):
                return
            for node in container.nodes:
                if hasattr(node, "inputs"):
                    for inp in node.inputs:
                        inp_low = inp.name.lower().strip()
                        if ("switch" in inp_low and "ult" in inp_low) or inp_low == "moving" or ("tacet" in inp_low and "ult" in inp_low):
                            try:
                                inp.default_value = new_bool
                                toggled += 1
                            except Exception:
                                try:
                                    inp.default_value = new_val
                                    toggled += 1
                                except Exception:
                                    pass

        for mat in materials:
            if mat.use_nodes and mat.node_tree:
                apply_ult_val(mat.node_tree)

        # 3. Also toggle any star modifiers or objects
        for obj in _iter_rig_meshes(arm):
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    mod_low = mod.name.lower()
                    if "resonatorstar" in mod_low or "star move" in mod_low or "tacet" in mod_low:
                        mod.show_viewport = new_bool
                        toggled += 1

        state_str = "Switch to Ult: ON" if new_bool else "Switch to Ult: OFF"
        if toggled > 0:
            self.report({'INFO'}, f"Resonator Star: {state_str}")
        else:
            self.report({'INFO'}, f"Resonator Star: {state_str}")
        return {'FINISHED'}


class WW_OT_FixEyeUV(Operator):
    bl_idname = "wuthering_waves.fix_eye_uv"
    bl_label = "Fix Eye UV"
    bl_description = "Ensure Eye materials use UV2 / correct UV Map channel"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm, materials = _settings_target(context)
        if not arm or not materials:
            return {'CANCELLED'}
        from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
        count = 0
        for mat in materials:
            if not mat.use_nodes or not mat.node_tree:
                continue
            if "eye" in mat.name.lower() or "ww - eye" in mat.name.lower():
                for node in mat.node_tree.nodes:
                    if node.type == 'UVMAP':
                        node.uv_map = "UV2"
                        count += 1
                    elif node.type == 'GROUP' and node.node_tree and "eye depth" in node.node_tree.name.lower():
                        node.node_tree = node.node_tree.copy()
                        for subnode in node.node_tree.nodes:
                            if subnode.type == 'UVMAP':
                                subnode.uv_map = "UV2"
                                count += 1

        self.report({'INFO'}, f"Fixed Eye UV to UV2 on {count} nodes.")
        return {'FINISHED'}


class WW_OT_SeparateMesh(Operator):
    bl_idname = "wuthering_waves.separate_mesh"
    bl_label = "Separate Mesh by Vertex Groups"
    bl_description = "Separates character mesh into Hair, Cloth (Piao), Skirt, and Body meshes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        mesh_obj = context.active_object
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a Mesh.")
            return {'CANCELLED'}

        # Groups to separate
        group_categories = [
            ("Hair", ["Hair", "hair", "TouFa", "前发", "后发"]),
            ("Cloth", ["Piao", "piao", "Cloth", "cloth", "Sleeve", "Ribbon"]),
            ("Skirt", ["Skirt", "skirt", "Trousers", "trousers", "QunZi"]),
        ]

        bpy.ops.object.mode_set(mode='OBJECT')
        initial_name = mesh_obj.name

        separated_objs = []
        for cat_name, keywords in group_categories:
            matching_groups = [
                g.name for g in mesh_obj.vertex_groups
                if any(kw.lower() in g.name.lower() for kw in keywords)
            ]
            if not matching_groups:
                continue

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            for g_name in matching_groups:
                g = mesh_obj.vertex_groups[g_name]
                for v in mesh_obj.data.vertices:
                    for vg in v.groups:
                        if vg.group == g.index and vg.weight > 0.01:
                            v.select = True

            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                for o in context.selected_objects:
                    if o != mesh_obj and o not in separated_objs:
                        o.name = f"{initial_name}_{cat_name}"
                        separated_objs.append(o)
            except Exception as e:
                bpy.ops.object.mode_set(mode='OBJECT')
                print(f"Notice separating {cat_name}: {e}")

        self.report({'INFO'}, f"Separated mesh into {len(separated_objs) + 1} parts.")
        return {'FINISHED'}


class WW_OT_SetPerformanceMode(Operator):
    bl_idname = "wuthering_waves.set_performance_mode"
    bl_label = "Performance Mode"
    bl_description = "Optimize viewport settings for smooth viewport animation performance"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if hasattr(scene, "eevee"):
            if hasattr(scene.eevee, "taa_samples"):
                scene.eevee.taa_samples = 1
            if hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = 16
            if hasattr(scene.eevee, "use_ssr"):
                scene.eevee.use_ssr = False
            if hasattr(scene.eevee, "use_gtao"):
                scene.eevee.use_gtao = False
            if hasattr(scene.eevee, "use_shadows"):
                scene.eevee.use_shadows = False

        self.report({'INFO'}, "Performance Viewport Mode Enabled.")
        return {'FINISHED'}


class WW_OT_SetQualityMode(Operator):
    bl_idname = "wuthering_waves.set_quality_mode"
    bl_label = "Quality Mode"
    bl_description = "Configure high quality viewport shading and render settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if hasattr(scene, "eevee"):
            if hasattr(scene.eevee, "taa_samples"):
                scene.eevee.taa_samples = 64
            if hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = 128
            if hasattr(scene.eevee, "use_ssr"):
                scene.eevee.use_ssr = True
            if hasattr(scene.eevee, "use_gtao"):
                scene.eevee.use_gtao = True
            if hasattr(scene.eevee, "use_shadows"):
                scene.eevee.use_shadows = True

        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Standard'

        self.report({'INFO'}, "Quality Viewport Mode Enabled.")
        return {'FINISHED'}


def register_wuwa_properties():
    bpy.types.Scene.ww_tex_mode = EnumProperty(
        name="Texture Mode",
        description="Texture assignment mode for Wuthering Waves",
        items=[
            ("Default", "Default", "Default texture matching"),
            ("Version", "Version", "Version-based texture matching"),
        ],
        default="Default",
    )

    bpy.types.Scene.ww_light_mode = EnumProperty(
        name="Light Mode",
        description="Lighting preset mode for Gustling Waters shader",
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
        update=update_light_mode,
    )

    bpy.types.Scene.ww_blush_value = FloatProperty(
        name="Blush",
        description="Face blush intensity",
        min=0.0,
        max=2.0,
        default=0.0,
        step=10,
        precision=1,
        update=update_blush,
    )

    bpy.types.Scene.ww_disgust_value = FloatProperty(
        name="Disgust",
        description="Face disgust shadow intensity",
        min=0.0,
        max=2.0,
        default=0.0,
        step=10,
        precision=1,
        update=update_disgust,
    )

    bpy.types.Scene.ww_metallic_value = FloatProperty(
        name="Metallic Multiplier",
        description="Metallic reflections intensity",
        min=0.0,
        max=2.0,
        default=1.0,
        step=10,
        precision=1,
        update=update_metallic,
    )

    bpy.types.Scene.ww_specular_value = FloatProperty(
        name="Specular Multiplier",
        description="Specular highlight multiplier",
        min=0.0,
        max=2.0,
        default=1.0,
        step=10,
        precision=1,
        update=update_specular,
    )

    bpy.types.Scene.ww_amb_color = FloatVectorProperty(
        name="Ambient Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.5, 0.5, 0.5),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_light_color = FloatVectorProperty(
        name="Light Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_shadow_color = FloatVectorProperty(
        name="Shadow Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.3, 0.3, 0.4),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_rim_color = FloatVectorProperty(
        name="Rim Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_shadow_transition_range_value = FloatProperty(
        name="Shadow Transition Range",
        description="Softness range of shadow transitions",
        min=0.0,
        max=1.0,
        default=0.05,
        step=10,
        precision=2,
        update=update_shadow_range,
    )

    bpy.types.Scene.ww_face_shadow_softness_value = FloatProperty(
        name="Face Shadow Softness",
        description="Face shadow boundary softness",
        min=0.0,
        max=1.0,
        default=0.05,
        step=10,
        precision=2,
        update=update_face_shadow_softness,
    )

    bpy.types.Scene.ww_catch_shadows = BoolProperty(
        name="Catch Shadows",
        description="Enable shadow receiving on character",
        default=True,
        update=update_catch_shadows,
    )

    bpy.types.Scene.ww_alpha_transparency = BoolProperty(
        name="Alpha Transparency",
        description="Toggle Alpha Transparency on Alpha materials",
        default=True,
        update=update_alpha_transparency,
    )

    bpy.types.Scene.ww_use_fresnel = BoolProperty(
        name="Use Fresnel",
        description="Enable Fresnel rim lighting",
        default=False,
        update=update_fresnel,
    )

    bpy.types.Scene.ww_fresnel_color = FloatVectorProperty(
        name="Fresnel Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_fresnel,
    )

    bpy.types.Scene.ww_fresnel_scale = FloatProperty(
        name="Fresnel Scale",
        description="Fresnel scale",
        min=0.0,
        max=20.0,
        default=2.0,
        step=10,
        precision=2,
        update=update_fresnel,
    )

    bpy.types.Scene.ww_fresnel_strength = FloatProperty(
        name="Fresnel Strength",
        description="Fresnel strength",
        min=0.0,
        max=20.0,
        default=2.0,
        step=10,
        precision=2,
        update=update_fresnel,
    )

    bpy.types.Scene.ww_outline_mode = EnumProperty(
        name="Outline Mode",
        description="Outline color mode for Wuthering Waves characters",
        items=[
            ("DEFAULT", "Default", "Use default / LD texture outline colors"),
            ("CUSTOM", "Custom", "Use custom outline colors"),
        ],
        default="DEFAULT",
        update=update_outline_settings,
    )

    bpy.types.Scene.ww_outline_color_1 = FloatVectorProperty(
        name="Outline Color 1",
        description="First custom outline color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
        update=update_outline_settings,
    )

    bpy.types.Scene.ww_outline_color_2 = FloatVectorProperty(
        name="Outline Color 2",
        description="Second custom outline color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0),
        update=update_outline_settings,
    )

    bpy.types.Scene.ww_outline_thickness = FloatProperty(
        name="Outline Thickness",
        description="Outline thickness modifier setting",
        min=0.0,
        max=2.0,
        default=0.2,
        step=1,
        precision=3,
        update=update_outline_thickness,
    )


class WW_OT_ToggleAlphaTransparency(Operator):
    bl_idname = "wuthering_waves.toggle_alpha_transparency"
    bl_label = "Toggle Alpha Transparency"
    bl_description = "Mute or unmute Alpha Transparency on Alpha materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene
        curr = getattr(sc, "ww_alpha_transparency", True)
        sc.ww_alpha_transparency = not curr
        update_alpha_transparency(sc, context)
        state_str = "ON" if sc.ww_alpha_transparency else "OFF"
        self.report({'INFO'}, f"Alpha Transparency: {state_str}")
        return {'FINISHED'}


classes = (
    WW_OT_ToggleAnimateMode,
    WW_OT_ToggleOutlines,
    WW_OT_ToggleHairTrans,
    WW_OT_ToggleStarMotion,
    WW_OT_ToggleAlphaTransparency,
    WW_OT_FixEyeUV,
    WW_OT_SeparateMesh,
    WW_OT_SetPerformanceMode,
    WW_OT_SetQualityMode,
)


@bpy.app.handlers.persistent
def wuwa_frame_change_handler(scene, depsgraph=None):
    """Legacy hook: material values/animation are authoritative during render."""
    return


def register():
    register_wuwa_properties()
    for cls in classes:
        bpy.utils.register_class(cls)
    if wuwa_frame_change_handler in bpy.app.handlers.render_init:
        bpy.app.handlers.render_init.remove(wuwa_frame_change_handler)


def unregister():
    if wuwa_frame_change_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(wuwa_frame_change_handler)
    if wuwa_frame_change_handler in bpy.app.handlers.render_init:
        bpy.app.handlers.render_init.remove(wuwa_frame_change_handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
