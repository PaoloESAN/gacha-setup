import bpy
import os

from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, ShaderIdentifierServiceFactory
from setup_wizard.geometry_nodes_setup.lighting_panel_names import LightingPanelNames
from setup_wizard.utils.modifier_utils import has_modifier_property, get_modifier_property, set_modifier_property



class LightingPanelFileNames:
    LIGHTING_PANEL_FILENAME = 'LightingPanel.blend'
    LIGHTING_PANEL_V3_4_FILENAME = 'LightingPanel_Shader_v3_4.blend'
    ROOT_SHAPE_FILENAME = 'RootShape.blend'
    ROOT_SHAPE_V3_4_FILENAME = 'RootShape_Shader_v3_4.blend'

    def __init__(self, lighting_panel_filepath, root_shape_filepath):
        self.VERSION = 3 if self.LIGHTING_PANEL_V3_4_FILENAME in lighting_panel_filepath else 4
        self.LIGHTING_PANEL_FILEPATH = lighting_panel_filepath
        self.ROOT_SHAPE_FILEPATH = root_shape_filepath


class LightingPanelFileNamesFactory:
    @staticmethod
    def create(shader: GenshinImpactShaders):
        if shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER or shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
            lighting_panel_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), LightingPanelFileNames.LIGHTING_PANEL_V3_4_FILENAME)
            root_shape_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), LightingPanelFileNames.ROOT_SHAPE_V3_4_FILENAME)
        else:
            lighting_panel_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), LightingPanelFileNames.LIGHTING_PANEL_FILENAME)
            root_shape_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), LightingPanelFileNames.ROOT_SHAPE_FILENAME)

        return LightingPanelFileNames(lighting_panel_filepath, root_shape_filepath)


# Genshin Shader >= v3.4
class LightingPanel:
    def __init__(self, lighting_panel_filepath):
        self.lighting_panel_filepath = lighting_panel_filepath

    def set_up_lighting_panel(self, light_vectors_modifier):
        lighting_panel_attributes_exist = has_modifier_property(light_vectors_modifier, LightingPanelNames.LIGHT_VECTORS_MODIFIER_INPUT_NAME_TO_OBJECT_NAME[0][0])
        if lighting_panel_attributes_exist:
            if not bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL):
                self.import_lighting_panel()
                lighting_panel = bpy.data.objects.get(LightingPanelNames.Bones.LIGHTING_PANEL)
                self.prevent_lighting_issues_when_scaling_character(lighting_panel)
            self.connect_lighting_panel_nodes_to_global_material_properties()

            for modifier_input_name, object_name in LightingPanelNames.LIGHT_VECTORS_MODIFIER_INPUT_NAME_TO_OBJECT_NAME:
                try:
                    val = get_modifier_property(light_vectors_modifier, modifier_input_name) or bpy.data.objects.get(object_name)
                    set_modifier_property(light_vectors_modifier, modifier_input_name, val)
                except KeyError:
                    pass  # Skip if modifier input name does not exist, must do try-except because it may not have a value yet

    def import_lighting_panel(self):
        inner_path = 'Collection'
        bpy.ops.wm.append(
            filepath=os.path.join(self.lighting_panel_filepath, inner_path, LightingPanelNames.Collections.LIGHTING_PANEL),
            directory=os.path.join(self.lighting_panel_filepath, inner_path),
            files=[
                {'name': LightingPanelNames.Collections.LIGHTING_PANEL},
            ],
        )
        for obj in bpy.data.objects:
            if "colorwheel" in obj.name.lower():
                try:
                    obj.hide_render = True
                except Exception:
                    pass

    def prevent_lighting_issues_when_scaling_character(self, lighting_panel_armature):
        if not lighting_panel_armature:
            return

        lighting_panel_pose_bone = lighting_panel_armature.pose.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
        lighting_panel_bone_data = lighting_panel_armature.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)

        if lighting_panel_pose_bone:
            lighting_panel_pose_bone.lock_scale = (True, True, True)
        if lighting_panel_bone_data:
            lighting_panel_bone_data.inherit_scale = 'NONE'

def find_lighting_node(tree, name_or_label):
    if not tree or not hasattr(tree, "nodes"):
        return None
    if name_or_label in tree.nodes:
        return tree.nodes[name_or_label]
    for n in tree.nodes:
        if getattr(n, "label", None) == name_or_label:
            return n
    target_clean = name_or_label.lower().replace(" ", "").replace("_", "")
    for n in tree.nodes:
        nl_clean = getattr(n, "label", "").lower().replace(" ", "").replace("_", "")
        nn_clean = n.name.lower().replace(" ", "").replace("_", "")
        if nl_clean == target_clean or nn_clean == target_clean:
            return n
    return None


def get_lighting_panel_source_socket(tree, socket_name):
    """
    Given an input socket name on Global Properties (Group Output),
    finds the corresponding output socket from the internal Lighting Panel nodes.
    Matches the exact layout used in Hutao (and modern PrimoToon v4.0).
    """
    s_low = socket_name.lower()

    # Ambient
    if "ambient" in s_low:
        n = find_lighting_node(tree, "Ambient")
        if n:
            return n.outputs.get("Output") or n.outputs.get("Color") or (n.outputs[0] if n.outputs else None)

    # Sharp Lit
    if "sharp" in s_low and "lit" in s_low:
        n = find_lighting_node(tree, "SharpLit")
        if n:
            return n.outputs.get("Output") or n.outputs.get("Color") or (n.outputs[0] if n.outputs else None)

    # Sharp Shadow
    if "sharp" in s_low and "shadow" in s_low:
        n = find_lighting_node(tree, "SharpShadow")
        if n:
            return n.outputs.get("Output") or n.outputs.get("Color") or (n.outputs[0] if n.outputs else None)

    # Soft Lit
    if "soft" in s_low and "lit" in s_low:
        n = find_lighting_node(tree, "SoftLit")
        if n:
            return n.outputs.get("Output") or n.outputs.get("Color") or (n.outputs[0] if n.outputs else None)

    # Soft Shadow (ensure face softness is excluded)
    if "soft" in s_low and "shadow" in s_low and "face" not in s_low:
        n = find_lighting_node(tree, "SoftShadow")
        if n:
            return n.outputs.get("Output") or n.outputs.get("Color") or (n.outputs[0] if n.outputs else None)

    # Fresnel Color
    if "fresnel" in s_low and "color" in s_low:
        n = find_lighting_node(tree, "Fresnel Color")
        if n:
            return n.outputs.get("Color") or (n.outputs[0] if n.outputs else None)

    # Fresnel Scaler
    if "fresnel" in s_low and ("scaler" in s_low or "multiplier" in s_low):
        n = find_lighting_node(tree, "Value = Fresnel Scaler")
        if n:
            return n.outputs.get("Blue") or n.outputs.get("Value") or (n.outputs[0] if n.outputs else None)

    # Toggle Fresnel
    if "toggle" in s_low and "fresnel" in s_low:
        n = find_lighting_node(tree, "ToggleFresnel") or find_lighting_node(tree, "Toggle Fresnel")
        if n:
            return n.outputs.get("Value") or (n.outputs[0] if n.outputs else None)

    # Fresnel Power
    if "fresnel" in s_low and ("power" in s_low or "size" in s_low):
        n = find_lighting_node(tree, "FresnelPower") or find_lighting_node(tree, "Fresnel Power")
        if n:
            return n.outputs.get("Color") or n.outputs.get("Value") or (n.outputs[0] if n.outputs else None)

    # Shadow Position Offset / Shadow Position
    if "shadow" in s_low and "pos" in s_low:
        n = find_lighting_node(tree, "ShadowPos") or find_lighting_node(tree, "Shadow Position")
        if n:
            return n.outputs.get("Value") or (n.outputs[0] if n.outputs else None)

    # Rim Lit
    if "rim" in s_low and "lit" in s_low and "scale" not in s_low:
        n_rim = find_lighting_node(tree, "RimLit")
        if n_rim:
            out_sock = n_rim.outputs.get("Output") or n_rim.outputs.get("Color") or (n_rim.outputs[0] if n_rim.outputs else None)
            if out_sock:
                for l in out_sock.links:
                    if l.to_node.type == 'MIX':
                        res = l.to_node.outputs.get("Result") or l.to_node.outputs.get("Color")
                        if res:
                            return res
        n_mult = find_lighting_node(tree, "RimLitMult")
        if n_mult:
            res = n_mult.outputs.get("Result") or n_mult.outputs.get("Color")
            if res:
                return res
        if n_rim:
            return n_rim.outputs.get("Output") or n_rim.outputs.get("Color") or (n_rim.outputs[0] if n_rim.outputs else None)

    # Rim Shadow
    if "rim" in s_low and "shadow" in s_low and "scale" not in s_low:
        n_rim = find_lighting_node(tree, "RimShadow")
        if n_rim:
            out_sock = n_rim.outputs.get("Output") or n_rim.outputs.get("Color") or (n_rim.outputs[0] if n_rim.outputs else None)
            if out_sock:
                for l in out_sock.links:
                    if l.to_node.type == 'MIX':
                        res = l.to_node.outputs.get("Result") or l.to_node.outputs.get("Color")
                        if res:
                            return res
        n_mult = find_lighting_node(tree, "RimShadowMult")
        if n_mult:
            res = n_mult.outputs.get("Result") or n_mult.outputs.get("Color")
            if res:
                return res
        if n_rim:
            return n_rim.outputs.get("Output") or n_rim.outputs.get("Color") or (n_rim.outputs[0] if n_rim.outputs else None)

    # Rim Scale
    if "rim" in s_low and "scale" in s_low:
        n_scale_001 = tree.nodes.get("Rim Scale.001")
        if n_scale_001:
            res = n_scale_001.outputs.get("Vector")
            if res:
                return res
        n_scale = find_lighting_node(tree, "Rim Scale")
        if n_scale:
            out_sock = n_scale.outputs.get("Vector")
            if out_sock:
                for l in out_sock.links:
                    if l.to_node.type == 'VECT_MATH':
                        res = l.to_node.outputs.get("Vector")
                        if res:
                            return res
            return out_sock
        n_size = find_lighting_node(tree, "RimSize")
        if n_size:
            return n_size.outputs.get("Output") or n_size.outputs.get("Vector")

    return None


class LightingPanel:
    def __init__(self, lighting_panel_filepath):
        self.lighting_panel_filepath = lighting_panel_filepath

    def set_up_lighting_panel(self, light_vectors_modifier):
        lighting_panel_attributes_exist = has_modifier_property(light_vectors_modifier, LightingPanelNames.LIGHT_VECTORS_MODIFIER_INPUT_NAME_TO_OBJECT_NAME[0][0])
        if lighting_panel_attributes_exist:
            if not bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL):
                self.import_lighting_panel()
                lighting_panel = bpy.data.objects.get(LightingPanelNames.Bones.LIGHTING_PANEL)
                self.prevent_lighting_issues_when_scaling_character(lighting_panel)
            self.connect_lighting_panel_nodes_to_global_material_properties()

            for modifier_input_name, object_name in LightingPanelNames.LIGHT_VECTORS_MODIFIER_INPUT_NAME_TO_OBJECT_NAME:
                try:
                    val = get_modifier_property(light_vectors_modifier, modifier_input_name) or bpy.data.objects.get(object_name)
                    set_modifier_property(light_vectors_modifier, modifier_input_name, val)
                except KeyError:
                    pass

    def import_lighting_panel(self):
        inner_path = 'Collection'
        bpy.ops.wm.append(
            filepath=os.path.join(self.lighting_panel_filepath, inner_path, LightingPanelNames.Collections.LIGHTING_PANEL),
            directory=os.path.join(self.lighting_panel_filepath, inner_path),
            files=[
                {'name': LightingPanelNames.Collections.LIGHTING_PANEL},
            ],
        )
        for obj in bpy.data.objects:
            if "colorwheel" in obj.name.lower():
                try:
                    obj.hide_render = True
                except Exception:
                    pass

    def prevent_lighting_issues_when_scaling_character(self, lighting_panel_armature):
        if not lighting_panel_armature:
            return

        lighting_panel_pose_bone = lighting_panel_armature.pose.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
        lighting_panel_bone_data = lighting_panel_armature.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)

        if lighting_panel_pose_bone:
            lighting_panel_pose_bone.lock_scale = (True, True, True)
        if lighting_panel_bone_data:
            lighting_panel_bone_data.inherit_scale = 'NONE'

    def connect_lighting_panel_nodes_to_global_material_properties(self, target_materials=None):
        target_trees = set()
        mats = target_materials if target_materials else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
        for mat in mats:
            if getattr(mat, "use_nodes", False) and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree:
                        if "global material properties" in node.node_tree.name.lower() or node.name == 'Global Properties':
                            target_trees.add(node.node_tree)

        if not target_trees:
            for ng in bpy.data.node_groups:
                if "global material properties" in ng.name.lower():
                    target_trees.add(ng)

        for tree in target_trees:
            out_node = tree.nodes.get('Global Properties') or tree.nodes.get('Group Output')
            if not out_node:
                continue

            for inp in out_node.inputs:
                if not inp.name or inp.name.startswith("---") or "face" in inp.name.lower():
                    continue
                source_sock = get_lighting_panel_source_socket(tree, inp.name)
                if source_sock:
                    for l in list(inp.links):
                        tree.links.remove(l)
                    tree.links.new(source_sock, inp)


def disconnect_lighting_panel_nodes_from_global_material_properties(target_materials=None):
    """Disconnects incoming links from internal lighting panel nodes to Global Properties inputs."""
    target_trees = set()
    for ng in bpy.data.node_groups:
        ng_low = ng.name.lower()
        if "global material properties" in ng_low or "global properties" in ng_low:
            target_trees.add(ng)

    mats = target_materials if target_materials else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    for mat in mats:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower() or "global properties" in node.node_tree.name.lower() or node.name == 'Global Properties':
                        target_trees.add(node.node_tree)
                if node.name == 'Global Properties' or getattr(node, 'label', '') == 'Global Properties':
                    for inp in node.inputs:
                        for l in list(inp.links):
                            mat.node_tree.links.remove(l)

    for tree in target_trees:
        nodes_to_disconnect = [
            n for n in tree.nodes
            if n.name == 'Global Properties' or getattr(n, 'label', '') == 'Global Properties' or n.type == 'GROUP_OUTPUT'
        ]
        for out_node in nodes_to_disconnect:
            for inp in out_node.inputs:
                for l in list(inp.links):
                    tree.links.remove(l)


def is_lighting_panel_connected(target_materials=None) -> bool:
    """Checks whether the character's Global Properties node group has incoming links from the Lighting Panel."""
    target_trees = set()
    mats = target_materials if target_materials else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    for mat in mats:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower() or node.name == 'Global Properties':
                        target_trees.add(node.node_tree)

    if not target_trees:
        for ng in bpy.data.node_groups:
            if "global material properties" in ng.name.lower():
                target_trees.add(ng)

    for tree in target_trees:
        out_node = tree.nodes.get('Global Properties') or tree.nodes.get('Group Output')
        if out_node:
            for inp_name in ["Ambient Colour", "Ambient Color", "Sharp Lit Colour", "Sharp Lit Color", "Toggle Fresnel"]:
                sock = out_node.inputs.get(inp_name)
                if sock and sock.links:
                    return True
    return False


def armature_has_lighting_panel(arm) -> bool:
    """Returns True if the armature object contains the 'Lighting Panel' bone."""
    if not arm or arm.type != 'ARMATURE' or not arm.data:
        return False
    return bool(arm.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL))


def character_supports_lighting_panel(arm=None, context=None, target_materials=None) -> bool:
    """Returns True if the character rig has the 3D lighting panel bone."""
    if arm is None and context is not None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
        except Exception:
            pass
    return bool(arm and armature_has_lighting_panel(arm))


def is_lighting_panel_visible(arm) -> bool:
    """Returns True if the Lighting Panel controls are currently visible."""
    if not arm or arm.type != 'ARMATURE' or not arm.data:
        return False
    # Blender 4.0+ bone collections
    if hasattr(arm.data, "collections"):
        coll = arm.data.collections.get("Light Panel") or arm.data.collections.get("Lighting")
        if coll:
            return bool(coll.is_visible)
    b = arm.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
    if b:
        return not b.hide
    return True


def set_lighting_panel_visibility(arm, visible: bool = True):
    """Sets visibility of Lighting Panel bone collection, bones, and helper objects."""
    if arm and arm.type == 'ARMATURE' and arm.data:
        if hasattr(arm.data, "collections"):
            for c_name in ["Light Panel", "Lighting"]:
                coll = arm.data.collections.get(c_name)
                if coll:
                    coll.is_visible = visible
            coll_extras = arm.data.collections.get("Light Panel Extras")
            if coll_extras and not visible:
                coll_extras.is_visible = False
        b = arm.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
        if b:
            b.hide = not visible

    for obj in bpy.data.objects:
        o_low = obj.name.lower()
        if any(k in o_low for k in ["lighting panel", "lightingpanel", "colorwheel", "colorpicker", "slider-", "origin-"]):
            try:
                obj.hide_viewport = not visible
                obj.hide_set(not visible)
                obj.hide_render = True
            except Exception:
                pass

    for coll in bpy.data.collections:
        c_low = coll.name.lower()
        if "lighting panel" in c_low or "lightingpanel" in c_low:
            try:
                coll.hide_viewport = not visible
            except Exception:
                pass

    try:
        wm = getattr(bpy.context, "window_manager", None)
        if wm:
            for win in getattr(wm, 'windows', []) or []:
                screen = getattr(win, 'screen', None)
                if screen:
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
    except Exception:
        pass


def move_into_collection(obj_or_name, collection_name, include_children=True):
    """Moves an object into the specified collection, creating it if needed."""
    obj = bpy.data.objects.get(obj_or_name) if isinstance(obj_or_name, str) else obj_or_name
    if not obj:
        return
    if any(c.name == "lights" for c in obj.users_collection):
        return

    coll = bpy.data.collections.get(collection_name)
    if not coll:
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)

    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)

    if include_children:
        for child in obj.children:
            move_into_collection(child, collection_name, include_children=True)


class GlobalPropertiesNames:
    class LightingPanelNodeNames:
        FRESNEL_COLOR_NODE = 'Fresnel Color'
        FRESNEL_SCALER_NODE = 'Value = Fresnel Scaler'
        AMBIENT_COLOUR_NODE = 'Ambient'
        SHARP_LIT_COLOUR_NODE = 'SharpLit'
        SOFT_LIFT_COLOUR_NODE = 'SoftLit'
        SHARP_SHADOW_COLOUR_NODE = 'SharpShadow'
        SOFT_SHADOW_COLOUR_NODE = 'SoftShadow'
        RIM_LIT_NODE = 'RimLit'
        RIM_SHADOW_NODE = 'RimShadow'
        RIM_LIT_MULT_NODE = 'RimLitMult'  # Backwards compatibility, GI Shader v3.4
        RIM_SHADOW_MULT_NODE = 'RimShadowMult'  # Backwards compatibility, GI Shader v3.4
        RIM_SCALE_NODE = 'Rim Scale'
        TOGGLE_FRESNEL_NODE = 'ToggleFresnel'
        FRESNEL_POWER_NODE = 'FresnelPower'
        SHADOW_POSITION_NODE = 'ShadowPos'

    class Inputs:
        FRESNEL_COLOR = 'Fresnel Color'
        FRESNEL_SCALER = 'Fresnel Scaler'
        AMBIENT_COLOUR = 'Ambient Colour'
        SHARP_LIT_COLOUR = 'Sharp Lit Colour'
        SOFT_LIT_COLOUR = 'Soft Lit Colour'
        SHARP_SHADOW_COLOUR = 'Sharp Shadow Colour'
        SOFT_SHADOW_COLOUR = 'Soft Shadow Colour'
        RIM_LIT = 'Rim Lit'
        RIM_SHADOW = 'Rim Shadow'
        RIM_SCALE = 'Rim Scale'
        TOGGLE_FRESNEL = 'Toggle Fresnel'
        FRESNEL_POWER = 'Fresnel Power'
        SHADOW_POSITION = 'Shadow Position Offset'

    NODES_TO_GLOBAL_PROPERTIES = {
        LightingPanelNodeNames.FRESNEL_COLOR_NODE: {
            'input': Inputs.FRESNEL_COLOR,
            'output': 'Color',
            'valid_output_names': ['Color',],
        },
        LightingPanelNodeNames.FRESNEL_SCALER_NODE: {
            'input': Inputs.FRESNEL_SCALER,
            'output': 'Blue',  # 'Value'
            'valid_output_names': ['Blue',],  # 'Value'
        },
        LightingPanelNodeNames.AMBIENT_COLOUR_NODE: {
            'input': Inputs.AMBIENT_COLOUR,
            'output': 'Output',
            'old_output_name': 'Color',
            'valid_output_names': ['Output', 'Color',],
        },
        LightingPanelNodeNames.SHARP_LIT_COLOUR_NODE: {
            'input': Inputs.SHARP_LIT_COLOUR,
            'output': 'Output',
            'old_output_name': 'Color',
            'valid_output_names': ['Output', 'Color',],
        },
        LightingPanelNodeNames.SOFT_LIFT_COLOUR_NODE: {
            'input': Inputs.SOFT_LIT_COLOUR,
            'output': 'Output',
            'old_output_name': 'Color',
            'valid_output_names': ['Output', 'Color',],
        },
        LightingPanelNodeNames.SHARP_SHADOW_COLOUR_NODE: {
            'input': Inputs.SHARP_SHADOW_COLOUR,
            'output': 'Output',
            'old_output_name': 'Color',
            'valid_output_names': ['Output', 'Color',],
        },
        LightingPanelNodeNames.SOFT_SHADOW_COLOUR_NODE: {
            'input': Inputs.SOFT_SHADOW_COLOUR,
            'output': 'Output',
            'old_output_name': 'Color',
            'valid_output_names': ['Output', 'Color',],
        },
        LightingPanelNodeNames.RIM_LIT_NODE: {
            'input': Inputs.RIM_LIT,
            'output': 'Result',
            'valid_output_names': ['Output',],
        },
        LightingPanelNodeNames.RIM_LIT_MULT_NODE: {  # Backwards compatibility, GI Shader v3.4
            'input': Inputs.RIM_LIT,
            'valid_output_names': ['Result',],
        },
        LightingPanelNodeNames.RIM_SHADOW_NODE: {
            'input': Inputs.RIM_SHADOW,
            'output': 'Result',
            'valid_output_names': ['Output',],
        },
        LightingPanelNodeNames.RIM_SHADOW_MULT_NODE: {  # Backwards compatibility, GI Shader v3.4
            'input': Inputs.RIM_SHADOW,
            'valid_output_names': ['Result',],
        },
        LightingPanelNodeNames.RIM_SCALE_NODE: {
            'input': Inputs.RIM_SCALE,
            'output': 'Vector',
            'valid_output_names': ['Vector',],
        },
        LightingPanelNodeNames.TOGGLE_FRESNEL_NODE: {
            'input': Inputs.TOGGLE_FRESNEL,
            'valid_output_names': ['Value',],
        },
        LightingPanelNodeNames.FRESNEL_POWER_NODE: {
            'input': Inputs.FRESNEL_POWER,
            'valid_output_names': ['Color',],
        },
        LightingPanelNodeNames.SHADOW_POSITION_NODE: {
            'input': Inputs.SHADOW_POSITION,
            'valid_output_names': ['Value',],
        },
    }


def connect_zzz_lighting_panel(target_materials=None):
    """
    Connects ZZZ lighting panel attributes to materials for both Kythera and Legacy shaders.
    """
    mats = target_materials if target_materials else [
        m for m in bpy.data.materials
        if getattr(m, "use_nodes", False) and m.node_tree
        and not m.name.startswith("Kythera's ZZZ")
        and getattr(m, "users", 1) > 0
    ]
    
    # 1. Check for Kythera shader materials
    lp_attr_group = bpy.data.node_groups.get("ZZZLightPanelAttr")
    if not lp_attr_group:
        from setup_wizard.import_order import get_shader_file_path
        from setup_wizard.domain.game_types import GameType
        setup_blend = get_shader_file_path(GameType.ZENLESS_ZONE_ZERO.name, file_type='outlines')
        if setup_blend and os.path.isfile(setup_blend):
            try:
                bpy.ops.wm.append(
                    filepath=os.path.join(setup_blend, "NodeTree", "ZZZLightPanelAttr"),
                    directory=os.path.join(setup_blend, "NodeTree"),
                    filename="ZZZLightPanelAttr"
                )
                lp_attr_group = bpy.data.node_groups.get("ZZZLightPanelAttr")
            except Exception:
                pass

    for mat in mats:
        if not getattr(mat, "use_nodes", False) or not mat.node_tree:
            continue
        if mat.name.startswith("Kythera's ZZZ") or getattr(mat, "users", 1) == 0:
            continue
        
        for node in mat.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree:
                nt_low = node.node_tree.name.lower()
                if "kythera" in nt_low or "face shader" in nt_low or "zzz shader" in nt_low:
                    lp_node = next((n for n in mat.node_tree.nodes if n.type == 'GROUP' and n.node_tree and n.node_tree.name == "ZZZLightPanelAttr"), None)
                    if not lp_node and lp_attr_group:
                        lp_node = mat.node_tree.nodes.new('ShaderNodeGroup')
                        lp_node.node_tree = lp_attr_group
                        lp_node.name = "ZZZLightPanelAttr"
                        lp_node.location = (node.location.x - 300, node.location.y)
                    
                    if lp_node:
                        is_face = "face" in nt_low or "face" in mat.name.lower()
                        amb_input_name = "Overall Tint" if is_face and "Overall Tint" in node.inputs else "Ambient Tint"
                        
                        links_to_make = [
                            ("Ambient", amb_input_name),
                            ("Lit", "Lit Tint"),
                            ("Shad", "Shadow Tint"),
                            ("RimLit", "Rim Light Color"),
                        ]
                        for out_name, inp_name in links_to_make:
                            if out_name in lp_node.outputs and inp_name in node.inputs:
                                target_sock = node.inputs[inp_name]
                                for l in list(target_sock.links):
                                    mat.node_tree.links.remove(l)
                                mat.node_tree.links.new(lp_node.outputs[out_name], target_sock)

                        if ("Left/Right" in node.inputs or "Up/Down" in node.inputs) and "RimScale" in lp_node.outputs:
                            sep_node = next((n for n in mat.node_tree.nodes if n.type == 'SEPXYZ' and n.name == "ZZZ_Rim_SepXYZ"), None)
                            if not sep_node:
                                sep_node = mat.node_tree.nodes.new('ShaderNodeSeparateXYZ')
                                sep_node.name = "ZZZ_Rim_SepXYZ"
                                sep_node.location = (lp_node.location.x + 150, lp_node.location.y - 150)
                            mat.node_tree.links.new(lp_node.outputs["RimScale"], sep_node.inputs["Vector"])

                            map_x = next((n for n in mat.node_tree.nodes if n.type == 'MAP_RANGE' and n.name == "ZZZ_Rim_MapX"), None)
                            if not map_x:
                                map_x = mat.node_tree.nodes.new('ShaderNodeMapRange')
                                map_x.name = "ZZZ_Rim_MapX"
                                map_x.location = (sep_node.location.x + 180, sep_node.location.y + 60)
                            map_x.clamp = True
                            map_x.inputs['From Min'].default_value = 0.0
                            map_x.inputs['From Max'].default_value = 10.0
                            map_x.inputs['To Min'].default_value = 0.0
                            map_x.inputs['To Max'].default_value = 1.0
                            mat.node_tree.links.new(sep_node.outputs["X"], map_x.inputs["Value"])

                            map_y = next((n for n in mat.node_tree.nodes if n.type == 'MAP_RANGE' and n.name == "ZZZ_Rim_MapY"), None)
                            if not map_y:
                                map_y = mat.node_tree.nodes.new('ShaderNodeMapRange')
                                map_y.name = "ZZZ_Rim_MapY"
                                map_y.location = (sep_node.location.x + 180, sep_node.location.y - 60)
                            map_y.clamp = True
                            map_y.inputs['From Min'].default_value = 0.0
                            map_y.inputs['From Max'].default_value = 10.0
                            map_y.inputs['To Min'].default_value = 0.0
                            map_y.inputs['To Max'].default_value = 1.0
                            mat.node_tree.links.new(sep_node.outputs["Y"], map_y.inputs["Value"])

                            if "Left/Right" in node.inputs:
                                for l in list(node.inputs["Left/Right"].links):
                                    mat.node_tree.links.remove(l)
                                mat.node_tree.links.new(map_x.outputs["Result"], node.inputs["Left/Right"])
                            if "Up/Down" in node.inputs:
                                for l in list(node.inputs["Up/Down"].links):
                                    mat.node_tree.links.remove(l)
                                mat.node_tree.links.new(map_y.outputs["Result"], node.inputs["Up/Down"])

    # 2. Check for Legacy shader node groups (Global Material Properties & Global Material Properties FACE)
    for ng in bpy.data.node_groups:
        ng_low = ng.name.lower()
        if "global material properties" in ng_low:
            lp_node = next((n for n in ng.nodes if n.type == 'GROUP' and n.node_tree and "zzzlightpanelattr" in n.node_tree.name.lower()), None)
            if not lp_node:
                continue
            
            if "face" in ng_low:
                mix_node = ng.nodes.get("Mix")
                vm_node = ng.nodes.get("Vector Math.001")
                if mix_node:
                    sock_b = mix_node.inputs.get("B") or (mix_node.inputs[7] if len(mix_node.inputs) > 7 else None)
                    sock_a = mix_node.inputs.get("A") or (mix_node.inputs[6] if len(mix_node.inputs) > 6 else None)
                    if sock_b and "Lit" in lp_node.outputs:
                        for l in list(sock_b.links): ng.links.remove(l)
                        ng.links.new(lp_node.outputs["Lit"], sock_b)
                    if sock_a and "Shad" in lp_node.outputs:
                        for l in list(sock_a.links): ng.links.remove(l)
                        ng.links.new(lp_node.outputs["Shad"], sock_a)
                if vm_node and len(vm_node.inputs) > 1 and "Ambient" in lp_node.outputs:
                    sock_amb = vm_node.inputs[1]
                    for l in list(sock_amb.links): ng.links.remove(l)
                    ng.links.new(lp_node.outputs["Ambient"], sock_amb)
            else:
                amb_node = ng.nodes.get("Ambient")
                mix_node = ng.nodes.get("Mix")
                rim_node = ng.nodes.get("Group.001")
                if amb_node:
                    sock_b = amb_node.inputs.get("B") or (amb_node.inputs[7] if len(amb_node.inputs) > 7 else None)
                    if sock_b and "Ambient" in lp_node.outputs:
                        for l in list(sock_b.links): ng.links.remove(l)
                        ng.links.new(lp_node.outputs["Ambient"], sock_b)
                if mix_node:
                    sock_b = mix_node.inputs.get("B") or (mix_node.inputs[7] if len(mix_node.inputs) > 7 else None)
                    sock_a = mix_node.inputs.get("A") or (mix_node.inputs[6] if len(mix_node.inputs) > 6 else None)
                    if sock_b and "Lit" in lp_node.outputs:
                        for l in list(sock_b.links): ng.links.remove(l)
                        ng.links.new(lp_node.outputs["Lit"], sock_b)
                    if sock_a and "Shad" in lp_node.outputs:
                        for l in list(sock_a.links): ng.links.remove(l)
                        ng.links.new(lp_node.outputs["Shad"], sock_a)
                if rim_node:
                    for out_name, inp_name in [("RimLit", "Rim Lit"), ("RimShad", "Rim Shadow"), ("RimScale", "Scale")]:
                        if out_name in lp_node.outputs and inp_name in rim_node.inputs:
                            sock = rim_node.inputs[inp_name]
                            for l in list(sock.links): ng.links.remove(l)
                            ng.links.new(lp_node.outputs[out_name], sock)


def disconnect_zzz_lighting_panel(target_materials=None):
    """
    Disconnects ZZZ lighting panel attributes from materials for both Kythera and Legacy shaders.
    """
    mats_set = set(target_materials) if target_materials else set()
    for m in bpy.data.materials:
        if getattr(m, "use_nodes", False) and m.node_tree:
            if not target_materials or m in mats_set or getattr(m, "users", 1) == 0 or m.name.startswith("Kythera's ZZZ"):
                mats_set.add(m)
            else:
                has_lp = any(
                    l.from_node and getattr(l.from_node, "node_tree", None) and "zzzlightpanelattr" in l.from_node.node_tree.name.lower()
                    for n in m.node_tree.nodes if n.type == 'GROUP'
                    for inp in n.inputs
                    for l in inp.links
                )
                if has_lp:
                    mats_set.add(m)
    
    # 1. Kythera materials
    for mat in mats_set:
        if not getattr(mat, "use_nodes", False) or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree:
                nt_low = node.node_tree.name.lower()
                if "kythera" in nt_low or "face shader" in nt_low or "zzz shader" in nt_low:
                    for inp_name in ["Ambient Tint", "Overall Tint", "Lit Tint", "Shadow Tint", "Rim Light Color", "Left/Right", "Up/Down"]:
                        if inp_name in node.inputs:
                            for l in list(node.inputs[inp_name].links):
                                if l.from_node and (
                                    (getattr(l.from_node, "node_tree", None) and "zzzlightpanelattr" in l.from_node.node_tree.name.lower())
                                    or l.from_node.name in ("ZZZ_Rim_SepXYZ", "ZZZ_Rim_MapX", "ZZZ_Rim_MapY")
                                ):
                                    mat.node_tree.links.remove(l)
                    for node_name in ("ZZZ_Rim_SepXYZ", "ZZZ_Rim_MapX", "ZZZ_Rim_MapY"):
                        extra_node = mat.node_tree.nodes.get(node_name)
                        if extra_node:
                            mat.node_tree.nodes.remove(extra_node)

    # 2. Legacy shader node groups
    for ng in bpy.data.node_groups:
        ng_low = ng.name.lower()
        if "global material properties" in ng_low:
            lp_node = next((n for n in ng.nodes if n.type == 'GROUP' and n.node_tree and "zzzlightpanelattr" in n.node_tree.name.lower()), None)
            if lp_node:
                for out_sock in lp_node.outputs:
                    for l in list(out_sock.links):
                        ng.links.remove(l)


def is_zzz_lighting_panel_connected(target_materials=None) -> bool:
    """
    Checks if ZZZ lighting panel attributes are connected to materials/node groups.
    """
    if target_materials:
        mats = target_materials
    else:
        mats = [
            m for m in bpy.data.materials
            if getattr(m, "use_nodes", False) and m.node_tree
            and not m.name.startswith("Kythera's ZZZ")
            and getattr(m, "users", 1) > 0
        ]
    
    # Check Kythera materials
    for mat in mats:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            if mat.name.startswith("Kythera's ZZZ") or getattr(mat, "users", 1) == 0:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_low = node.node_tree.name.lower()
                    if "kythera" in nt_low or "face shader" in nt_low or "zzz shader" in nt_low:
                        for inp_name in ["Lit Tint", "Shadow Tint", "Ambient Tint", "Overall Tint"]:
                            if inp_name in node.inputs:
                                for l in node.inputs[inp_name].links:
                                    if l.from_node and getattr(l.from_node, "node_tree", None) and "zzzlightpanelattr" in l.from_node.node_tree.name.lower():
                                        return True

    # Check Legacy groups
    for ng in bpy.data.node_groups:
        ng_low = ng.name.lower()
        if "global material properties" in ng_low:
            lp_node = next((n for n in ng.nodes if n.type == 'GROUP' and n.node_tree and "zzzlightpanelattr" in n.node_tree.name.lower()), None)
            if lp_node:
                for out_sock in lp_node.outputs:
                    if out_sock.links:
                        return True
    return False
