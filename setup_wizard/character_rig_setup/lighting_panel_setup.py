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


_FRESNEL_SWITCH_NODE = 'Blender_Fresnel_Toggle_Threshold'


def _fresnel_switch_socket(tree, source):
    """Suppress slider roundoff before Blender converts the float to a bool."""
    if bpy.app.version < (5, 3, 0) or source.type != 'VALUE':
        return source
    if source.node.name == _FRESNEL_SWITCH_NODE:
        return source
    switch = tree.nodes.get(_FRESNEL_SWITCH_NODE)
    if switch is None:
        switch = tree.nodes.new('ShaderNodeMath')
        switch.name = _FRESNEL_SWITCH_NODE
        switch.label = 'Fresnel Toggle Threshold'
        switch.location = (source.node.location.x + 180, source.node.location.y - 100)
    switch.operation = 'GREATER_THAN'
    switch.inputs[1].default_value = 0.5
    if not switch.inputs[0].is_linked or switch.inputs[0].links[0].from_socket != source:
        tree.links.new(source, switch.inputs[0])
    return switch.outputs[0]


def patch_fresnel_toggle_links(target_materials=None):
    """Give imported 5.3 lighting panels an exact 0/1 Fresnel toggle."""
    if bpy.app.version < (5, 3, 0):
        return False
    if target_materials is None:
        trees = {t for t in bpy.data.node_groups if 'global material properties' in t.name.lower()}
    else:
        trees = {n.node_tree for m in target_materials if m.node_tree
                 for n in m.node_tree.nodes if n.type == 'GROUP' and n.node_tree
                 and 'global material properties' in n.node_tree.name.lower()}
    changed = False
    for tree in trees:
        for node in list(tree.nodes):
            if node.type != 'GROUP_OUTPUT':
                continue
            toggle = node.inputs.get('Toggle Fresnel')
            if toggle is None or toggle.type != 'BOOLEAN' or not toggle.is_linked:
                continue
            source = toggle.links[0].from_socket
            switched = _fresnel_switch_socket(tree, source)
            if switched != source:
                tree.links.new(switched, toggle)
                changed = True
    return changed


@bpy.app.handlers.persistent
def repair_fresnel_after_import(_context):
    # Append does not emit load_post and may leave no active object.
    patch_fresnel_toggle_links()


def register_fresnel_repair():
    for name in ('blend_import_post', 'load_post'):
        handlers = getattr(bpy.app.handlers, name, None)
        if handlers is not None and repair_fresnel_after_import not in handlers:
            handlers.append(repair_fresnel_after_import)


def unregister_fresnel_repair():
    for name in ('blend_import_post', 'load_post'):
        handlers = getattr(bpy.app.handlers, name, None)
        if handlers is not None and repair_fresnel_after_import in handlers:
            handlers.remove(repair_fresnel_after_import)


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
            source = n.outputs.get("Value") or (n.outputs[0] if n.outputs else None)
            boolean_output = any(node.type == 'GROUP_OUTPUT'
                                 and (socket := node.inputs.get(socket_name)) is not None
                                 and socket.type == 'BOOLEAN' for node in tree.nodes)
            if source is not None and boolean_output:
                return _fresnel_switch_socket(tree, source)
            return source

    # Fresnel Power
    if "fresnel" in s_low and ("power" in s_low or "size" in s_low):
        n = find_lighting_node(tree, "FresnelPower") or find_lighting_node(tree, "Fresnel Power")
        if n:
            return n.outputs.get("Color") or n.outputs.get("Value") or (n.outputs[0] if n.outputs else None)

    # The panel controls the relative offset, not material shadow thresholds.
    if "shadow" in s_low and "pos" in s_low and "offset" in s_low:
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


def sync_legacy_shadow_position(tree):
    """Keep the legacy threshold adapter inside Global Properties in both modes."""
    add = tree.nodes.get('Legacy Shadow Position')
    output = tree.nodes.get('Global Properties')
    if add is None or output is None or add.type != 'MATH':
        return
    offset = output.inputs.get('Shadow Position Offset')
    if offset is None:
        return
    target = add.inputs[0]
    source = offset.links[0].from_socket if offset.is_linked else None
    if source is not None:
        if not any(link.from_socket == source for link in target.links):
            tree.links.new(source, target)
    else:
        for link in list(target.links):
            tree.links.remove(link)
        target.default_value = offset.default_value


def repair_genshin_shadow_offset_links(materials):
    """Route the global offset to every shader, preserving material thresholds.

    Some PrimoToon templates connect Face Shadow Softness to the body offset.
    Repair material instances as well as new imports, without editing shaders.
    """
    for material in materials:
        tree = material.node_tree
        if tree is None:
            continue
        properties = next((node for node in tree.nodes if node.type == 'GROUP'
                           and node.node_tree and (
                               'global material properties' in node.node_tree.name.lower()
                               or node.name == 'Global Properties')
                           and node.outputs.get('Shadow Position Offset') is not None), None)
        if properties is None:
            continue
        source = properties.outputs['Shadow Position Offset']
        changed = False
        for node in tree.nodes:
            if node.type != 'GROUP' or node == properties:
                continue
            target = node.inputs.get('Shadow Position Offset')
            if target is not None and not any(link.from_socket == source for link in target.links):
                tree.links.new(source, target)
                changed = True
        if changed:
            tree.update_tag()
            material.update_tag()


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
        if target_materials is None:
            # Setup can append the outline shader separately from the body.
            # Consolidate those copies before wiring the lighting panel.
            from setup_wizard.ui.character_settings_utils import get_character_materials, ensure_character_node_trees_isolated
            for arm in list(bpy.data.objects):
                if arm.type == 'ARMATURE':
                    _, materials = get_character_materials(arm=arm)
                    ensure_character_node_trees_isolated(arm, materials)
        target_trees = set()
        mats = target_materials if target_materials is not None else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
        repair_genshin_shadow_offset_links(mats)
        for mat in mats:
            if getattr(mat, "use_nodes", False) and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree:
                        if "global material properties" in node.node_tree.name.lower() or node.name == 'Global Properties':
                            target_trees.add(node.node_tree)

        if not target_trees and target_materials is None:
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
            sync_legacy_shadow_position(tree)


def disconnect_lighting_panel_nodes_from_global_material_properties(target_materials=None):
    """Disconnect only lighting-panel links in explicitly supplied materials.

    Missing or empty targets are a no-op. Shared property groups are copied so
    switching one character's lighting mode cannot disconnect another's panel.
    """
    if target_materials is None:
        return
    grouped_nodes = {}
    for mat in set(target_materials):
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower() or "global properties" in node.node_tree.name.lower() or node.name == 'Global Properties':
                        grouped_nodes.setdefault(node.node_tree, []).append(node)

    for tree, group_nodes in grouped_nodes.items():
        if tree.users - int(tree.use_fake_user) > len(group_nodes):
            tree = tree.copy()
            for node in group_nodes:
                node.node_tree = tree
        nodes_to_disconnect = [
            n for n in tree.nodes
            if n.name == 'Global Properties' or getattr(n, 'label', '') == 'Global Properties' or n.type == 'GROUP_OUTPUT'
        ]
        for out_node in nodes_to_disconnect:
            for inp in out_node.inputs:
                if "face" in inp.name.lower():
                    continue
                source_socket = get_lighting_panel_source_socket(tree, inp.name)
                if source_socket is None:
                    continue
                panel_sources = {source_socket}
                if source_socket.node.name == _FRESNEL_SWITCH_NODE:
                    panel_sources.update(link.from_socket for link in source_socket.node.inputs[0].links)
                for l in list(inp.links):
                    if l.from_socket in panel_sources:
                        tree.links.remove(l)
        sync_legacy_shadow_position(tree)


def setup_unrigged_genshin_lighting(context, only_if_panel_missing=False, target_object=None):
    """Use static lighting for the selected model when no panel supplies it."""
    from setup_wizard.ui.character_settings_utils import get_character_materials

    selected = [obj for obj in context.selected_objects if obj.type in {'ARMATURE', 'MESH'}]
    active = context.view_layer.objects.active
    target = target_object or (active if active in selected else next(iter(selected), None))
    if target is None:
        return
    model_id = target.get('_setup_wizard_model_id')
    if target.type == 'MESH':
        target = target.find_armature() or target
    model_id = model_id or target.get('_setup_wizard_model_id')
    if only_if_panel_missing:
        # Enabling rigging does not guarantee a panel was installed: rigging
        # can be skipped for missing dependencies, or the panel can be disabled.
        # Unbound lightPanel attributes evaluate to black in classic EEVEE.
        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue
            if not (obj == target or obj.find_armature() == target
                    or (model_id and obj.get('_setup_wizard_model_id') == model_id)):
                continue
            for modifier in obj.modifiers:
                if modifier.type != 'NODES' or 'Light Vectors' not in modifier.name:
                    continue
                if all(get_modifier_property(modifier, key) is not None for key in (
                    LightingPanelNames.GeometryNodeInputs.AMBIENT_COLOR_WHEEL,
                    LightingPanelNames.GeometryNodeInputs.AMBIENT_COLOR_PICKER,
                )):
                    return
    _, materials = get_character_materials(context, arm=target)
    materials = set(materials)
    if model_id:
        # Effects and detached mesh parts need not be skinned to the armature.
        for obj in context.scene.objects:
            if obj.type == 'MESH' and obj.get('_setup_wizard_model_id') == model_id:
                materials.update(slot.material for slot in obj.material_slots if slot.material)
    else:
        # Older imports have no model ID. Equipment materials retain the Unity
        # source name, including the model prefix before _Mat and effect suffixes.
        def equipment_source(mat):
            source = mat.get('_original_material_name', '')
            if mat.get('_genshin_equipment') and source.startswith(('Equip_', 'EquipSkin_')):
                return source.partition('_Mat')[0]
            return None

        sources = {equipment_source(mat) for mat in materials} - {None}
        if sources:
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    materials.update(slot.material for slot in obj.material_slots
                                     if slot.material and equipment_source(slot.material) in sources)
    from setup_wizard.ui.character_settings_utils import ensure_character_node_trees_isolated
    ensure_character_node_trees_isolated(target, materials)
    disconnect_lighting_panel_nodes_from_global_material_properties(target_materials=materials)


def is_lighting_panel_connected(target_materials=None) -> bool:
    """Checks whether the character's Global Properties node group has incoming links from the Lighting Panel."""
    target_trees = set()
    mats = target_materials if target_materials is not None else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    for mat in mats:
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower() or node.name == 'Global Properties':
                        target_trees.add(node.node_tree)

    if not target_trees and target_materials is None:
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
                # Bangboo uses the attached panel's controls; the standalone
                # color wheel spheres otherwise float above its small body.
                hide_helper = not visible
                obj.hide_viewport = hide_helper
                obj.hide_set(hide_helper)
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


def _get_mix_socket(node, name, socket_type):
    """Return the input socket matching both name and Blender socket type (for ShaderNodeMix)."""
    for sock in node.inputs:
        if sock.name == name and sock.type == socket_type:
            return sock
    return None


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
                    for stype in ("VECTOR", "RGBA"):
                        sock_b = _get_mix_socket(mix_node, "B", stype)
                        sock_a = _get_mix_socket(mix_node, "A", stype)
                        if sock_b and "Lit" in lp_node.outputs:
                            for l in list(sock_b.links):
                                ng.links.remove(l)
                            ng.links.new(lp_node.outputs["Lit"], sock_b)
                        if sock_a and "Shad" in lp_node.outputs:
                            for l in list(sock_a.links):
                                ng.links.remove(l)
                            ng.links.new(lp_node.outputs["Shad"], sock_a)
                if vm_node and len(vm_node.inputs) > 1 and "Ambient" in lp_node.outputs:
                    sock_amb = vm_node.inputs[1]
                    for l in list(sock_amb.links): ng.links.remove(l)
                    ng.links.new(lp_node.outputs["Ambient"], sock_amb)
            else:
                amb_node = ng.nodes.get("Ambient")
                mix_node = ng.nodes.get("Mix")
                rim_node = ng.nodes.get("Group.001")
                mix_rim = ng.nodes.get("Mix.002")
                if amb_node:
                    sock_b = _get_mix_socket(amb_node, "B", "RGBA") or (amb_node.inputs[7] if len(amb_node.inputs) > 7 else None)
                    if sock_b and "Ambient" in lp_node.outputs:
                        for l in list(sock_b.links): ng.links.remove(l)
                        ng.links.new(lp_node.outputs["Ambient"], sock_b)
                if mix_node:
                    sock_b = _get_mix_socket(mix_node, "B", "RGBA") or (mix_node.inputs[7] if len(mix_node.inputs) > 7 else None)
                    sock_a = _get_mix_socket(mix_node, "A", "RGBA") or (mix_node.inputs[6] if len(mix_node.inputs) > 6 else None)
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
                if mix_rim and rim_node:
                    sock_fac = _get_mix_socket(mix_rim, "Factor", "VALUE") or (mix_rim.inputs[0] if mix_rim.inputs else None)
                    out_fac = rim_node.outputs.get("Factor")
                    if sock_fac and out_fac:
                        if getattr(bpy.context.scene, "zzz_legacy_enable_rim_light", True):
                            if not sock_fac.links:
                                ng.links.new(out_fac, sock_fac)
                        else:
                            for l in list(sock_fac.links):
                                ng.links.remove(l)
                            sock_fac.default_value = 0.0


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


HSR_LIGHT_PANEL_GN_NAME = "HSR Light Panel"
HSR_LIGHT_PANEL_MODIFIER_NAME = "Lighting Panel"
HSR_LIGHT_PANEL_ATTR_NAME = "ZZZLightPanelAttr"

HSR_LIGHT_PANEL_SOCKET_LINKS = (
    ("Ambient", "Custom Ambient Color"),
    ("Lit", "Custom Lit Color"),
    ("Lit", "Custom Sharp Lit Color"),
    ("Shad", "Custom Shadow Color"),
    ("Shad", "Custom Sharp Shadow Color"),
    ("RimLit", "Tint Lit"),
    ("RimShad", "Tint Shadow"),
)


def _get_zzz_setup_blend_path():
    from setup_wizard.import_order import get_shader_file_path
    from setup_wizard.domain.game_types import GameType

    setup_blend = get_shader_file_path(GameType.ZENLESS_ZONE_ZERO.name, file_type='outlines')
    if setup_blend and os.path.isfile(setup_blend):
        return setup_blend
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for filename in ("ZZZ Setup v7.blend", "ZZZ Setup File V2.0.blend"):
        cand = os.path.join(addon_dir, "shaders", "zzz", filename)
        if os.path.isfile(cand):
            return cand
    return None


def _ensure_zzz_light_panel_attr_group():
    lp_attr_group = bpy.data.node_groups.get(HSR_LIGHT_PANEL_ATTR_NAME)
    if lp_attr_group:
        return lp_attr_group
    setup_blend = _get_zzz_setup_blend_path()
    if setup_blend and os.path.isfile(setup_blend):
        try:
            bpy.ops.wm.append(
                filepath=os.path.join(setup_blend, "NodeTree", HSR_LIGHT_PANEL_ATTR_NAME),
                directory=os.path.join(setup_blend, "NodeTree"),
                filename=HSR_LIGHT_PANEL_ATTR_NAME,
            )
            lp_attr_group = bpy.data.node_groups.get(HSR_LIGHT_PANEL_ATTR_NAME)
        except Exception as e:
            print(f"[HSR Lighting Panel] Failed to append {HSR_LIGHT_PANEL_ATTR_NAME}: {e}")
    return lp_attr_group


def import_hsr_lighting_panel():
    """Import ZZZ's 3D Lighting Panel, ZZZLightPanelAttr, and attribute-only Light Vectors GN for HSR."""
    setup_blend = _get_zzz_setup_blend_path()
    if not setup_blend or not os.path.isfile(setup_blend):
        print("[HSR Lighting Panel] ZZZ setup blend not found; skipping Lighting Panel import.")
        return False

    _ensure_zzz_light_panel_attr_group()

    # Load ZZZ's Light Vectors node group under a dedicated name so HSR's Light Vectors stays intact.
    if not bpy.data.node_groups.get(HSR_LIGHT_PANEL_GN_NAME):
        try:
            with bpy.data.libraries.load(setup_blend, link=False) as (data_from, data_to):
                if "Light Vectors" in data_from.node_groups:
                    data_to.node_groups = ["Light Vectors"]
            if data_to.node_groups and data_to.node_groups[0]:
                data_to.node_groups[0].name = HSR_LIGHT_PANEL_GN_NAME
        except Exception as e:
            print(f"[HSR Lighting Panel] Failed to load {HSR_LIGHT_PANEL_GN_NAME} GN: {e}")

    try:
        lighting_panel_keywords = (
            "colorwheel", "colorpicker", "slider-rim", "origin-rim",
            "lightpanelwgtplane", "lightpanelselectorwgt", "lighting panel",
        )
        excluded_kw = ("face", "phoneme", "mouth", "eyebrow", "expression", "facerig", "facrig")

        with bpy.data.libraries.load(setup_blend, link=False) as (data_from, data_to):
            target_objs = [
                o for o in data_from.objects
                if not any(kw in o.lower() for kw in excluded_kw)
                and any(kw in o.lower() for kw in lighting_panel_keywords)
                and o not in bpy.data.objects
            ]
            data_to.objects = target_objs

        target_wgt_coll = next((c for c in bpy.data.collections if c.name.startswith("WGTS_")), None)
        if not target_wgt_coll:
            target_wgt_coll = bpy.data.collections.get("wgt") or bpy.data.collections.get("WGTS")
        if not target_wgt_coll:
            target_wgt_coll = bpy.data.collections.new("wgt")
            if target_wgt_coll.name not in [c.name for c in bpy.context.scene.collection.children]:
                bpy.context.scene.collection.children.link(target_wgt_coll)

        for obj in data_to.objects:
            if not obj:
                continue
            o_low = obj.name.lower()
            is_widget = any(k in o_low for k in ("colorpicker", "slider-rim", "origin-rim", "lightpanelwgt", "lightpanelselector"))
            dest_coll = target_wgt_coll if is_widget else bpy.context.scene.collection
            if obj.name not in dest_coll.objects:
                dest_coll.objects.link(obj)
            if "colorwheel" in o_low:
                obj.hide_viewport = False
                obj.hide_render = True
            elif is_widget:
                obj.hide_render = True

        wgt_plane = bpy.data.objects.get("LightPanelWGTPlane")
        wgt_selector = bpy.data.objects.get("LightPanelSelectorWGT")
        if wgt_plane:
            wgt_plane.hide_viewport = False
            wgt_plane.hide_render = True
        if wgt_selector:
            wgt_selector.hide_viewport = False
            wgt_selector.hide_render = True

        lp_arm = bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL)
        if lp_arm and lp_arm.type == 'ARMATURE':
            for pb in lp_arm.pose.bones:
                if pb.name == "Lighting Panel" and wgt_plane:
                    pb.custom_shape = wgt_plane
                    pb.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
                    pb.use_custom_shape_bone_size = True
                    pb.bone.hide = False
                elif pb.name in ("Rim Lit", "Shadow", "Lit", "Ambient", "RimShadow", "Rim.R", "Rim.L", "RimX", "RimY") and wgt_selector:
                    pb.custom_shape = wgt_selector
                    pb.custom_shape_scale_xyz = (0.15, 0.15, 0.15)
                    pb.use_custom_shape_bone_size = True
                    pb.bone.hide = False
            from setup_wizard.utils.zzz_lighting_panel import bake_zzz_rim_slider_defaults
            bake_zzz_rim_slider_defaults(lp_arm, force=True)
    except Exception as e:
        print(f"[HSR Lighting Panel] Failed to import Lighting Panel objects from {setup_blend}: {e}")
        return False
    return True


def _collect_hsr_global_property_trees(target_materials=None):
    """Return dict[NodeTree, list[Node]] for HSR GlobalProperties groups used by target_materials."""
    grouped_nodes = {}
    mats = (
        list(target_materials)
        if target_materials is not None
        else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    )
    for mat in set(mats):
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "globalproperties" in node.node_tree.name.lower():
                        grouped_nodes.setdefault(node.node_tree, []).append(node)

    if not grouped_nodes and target_materials is None:
        for ng in bpy.data.node_groups:
            if "globalproperties" in ng.name.lower():
                grouped_nodes.setdefault(ng, [])

    return grouped_nodes


def _find_hsr_lp_attr_node(tree):
    return next(
        (
            n for n in tree.nodes
            if n.type == 'GROUP' and n.node_tree
            and "zzzlightpanelattr" in n.node_tree.name.lower()
        ),
        None,
    )


def connect_hsr_lighting_panel(target_materials=None):
    """Connect ZZZLightPanelAttr colors and RimScale (X, Y, Z=1.0) to HSR GlobalProperties."""
    lp_attr_group = _ensure_zzz_light_panel_attr_group()
    if not lp_attr_group:
        return False

    grouped_nodes = _collect_hsr_global_property_trees(target_materials)
    connected_any = False

    for tree, group_nodes in grouped_nodes.items():
        if group_nodes and tree.users - int(tree.use_fake_user) > len(group_nodes):
            tree = tree.copy()
            for node in group_nodes:
                node.node_tree = tree

        out_node = tree.nodes.get("Group Output") or tree.nodes.get("Global Properties")
        if not out_node:
            continue

        lp_node = _find_hsr_lp_attr_node(tree)
        if not lp_node:
            lp_node = tree.nodes.new("ShaderNodeGroup")
            lp_node.name = HSR_LIGHT_PANEL_ATTR_NAME
            lp_node.label = HSR_LIGHT_PANEL_ATTR_NAME
            lp_node.location = (out_node.location.x - 420, out_node.location.y - 180)
        if lp_node.node_tree != lp_attr_group:
            lp_node.node_tree = lp_attr_group

        for out_name, inp_name in HSR_LIGHT_PANEL_SOCKET_LINKS:
            if out_name in lp_node.outputs and inp_name in out_node.inputs:
                target_sock = out_node.inputs[inp_name]
                for l in list(target_sock.links):
                    tree.links.remove(l)
                tree.links.new(lp_node.outputs[out_name], target_sock)
                connected_any = True

        # Connect RimScale.X and RimScale.Y (scaled x2 -> 0..20) to Scale, keeping Z = 0.0
        scale_sock = out_node.inputs.get("Scale")
        if scale_sock and "RimScale" in lp_node.outputs:
            scale_2x = tree.nodes.get("HSR_Rim_Scale2x")
            if not scale_2x or scale_2x.type != 'VECT_MATH':
                scale_2x = tree.nodes.new("ShaderNodeVectorMath")
                scale_2x.name = "HSR_Rim_Scale2x"
                scale_2x.location = (lp_node.location.x + 150, lp_node.location.y - 140)
            scale_2x.operation = 'SCALE'
            scale_2x.inputs["Scale"].default_value = 2.0

            sep = tree.nodes.get("HSR_Rim_SepXYZ")
            if not sep or sep.type != 'SEPXYZ':
                sep = tree.nodes.new("ShaderNodeSeparateXYZ")
                sep.name = "HSR_Rim_SepXYZ"
                sep.location = (scale_2x.location.x + 160, scale_2x.location.y)
            comb = tree.nodes.get("HSR_Rim_CombXYZ")
            if not comb or comb.type != 'COMBXYZ':
                comb = tree.nodes.new("ShaderNodeCombineXYZ")
                comb.name = "HSR_Rim_CombXYZ"
                comb.location = (sep.location.x + 160, sep.location.y)

            for l in list(scale_2x.inputs[0].links):
                tree.links.remove(l)
            tree.links.new(lp_node.outputs["RimScale"], scale_2x.inputs[0])

            for l in list(sep.inputs["Vector"].links):
                tree.links.remove(l)
            tree.links.new(scale_2x.outputs["Vector"], sep.inputs["Vector"])

            for axis in ("X", "Y"):
                for l in list(comb.inputs[axis].links):
                    tree.links.remove(l)
                tree.links.new(sep.outputs[axis], comb.inputs[axis])
            for l in list(comb.inputs["Z"].links):
                tree.links.remove(l)
            comb.inputs["Z"].default_value = 0.0

            for l in list(scale_sock.links):
                tree.links.remove(l)
            tree.links.new(comb.outputs["Vector"], scale_sock)
            connected_any = True

        tree.update_tag()

    return connected_any


def disconnect_hsr_lighting_panel(target_materials=None):
    """Disconnect ZZZLightPanelAttr from HSR GlobalProperties."""
    grouped_nodes = _collect_hsr_global_property_trees(target_materials)

    for tree, group_nodes in grouped_nodes.items():
        if group_nodes and tree.users - int(tree.use_fake_user) > len(group_nodes):
            tree = tree.copy()
            for node in group_nodes:
                node.node_tree = tree

        out_node = tree.nodes.get("Group Output") or tree.nodes.get("Global Properties")
        lp_node = _find_hsr_lp_attr_node(tree)
        if lp_node:
            for out_sock in lp_node.outputs:
                for l in list(out_sock.links):
                    tree.links.remove(l)

        if out_node:
            scale_sock = out_node.inputs.get("Scale")
            if scale_sock:
                for l in list(scale_sock.links):
                    if l.from_node.name == "HSR_Rim_CombXYZ":
                        tree.links.remove(l)

        tree.update_tag()


def is_hsr_lighting_panel_connected(target_materials=None) -> bool:
    """Return True if HSR GlobalProperties has ZZZLightPanelAttr linked to Group Output."""
    grouped_nodes = _collect_hsr_global_property_trees(target_materials)
    for tree in grouped_nodes:
        out_node = tree.nodes.get("Group Output") or tree.nodes.get("Global Properties")
        if not out_node:
            continue
        lp_node = _find_hsr_lp_attr_node(tree)
        if not lp_node:
            continue
        for out_sock in lp_node.outputs:
            for l in out_sock.links:
                if l.to_node == out_node:
                    return True
        scale_sock = out_node.inputs.get("Scale")
        if scale_sock and any(l.from_node.name == "HSR_Rim_CombXYZ" for l in scale_sock.links):
            return True
    return False


# =============================================================================
# Neverness to Everness (NTE) 3D Lighting Panel (reuses ZZZ's 3D Lighting Panel)
# =============================================================================
NTE_LIGHT_PANEL_GN_NAME = "NTE Light Panel"
NTE_LIGHT_PANEL_MODIFIER_NAME = "Lighting Panel"
NTE_LIGHT_PANEL_SOCKET_LINKS = (
    ("Ambient", "Ambient Colour"),
    ("Lit", "Light Colour"),
    ("Shad", "Shadow Colour"),
    ("RimLit", "Rim Lit"),
    ("RimShad", "Rim Shadow"),
)


def import_nte_lighting_panel():
    """Import ZZZ's 3D Lighting Panel, ZZZLightPanelAttr, and attribute-only GN for NTE (single clean load)."""
    setup_blend = _get_zzz_setup_blend_path()
    if not setup_blend or not os.path.isfile(setup_blend):
        print("[NTE Lighting Panel] ZZZ setup blend not found; skipping Lighting Panel import.")
        return False

    _ensure_zzz_light_panel_attr_group()

    if not bpy.data.node_groups.get(NTE_LIGHT_PANEL_GN_NAME):
        try:
            with bpy.data.libraries.load(setup_blend, link=False) as (data_from, data_to):
                if "Light Vectors" in data_from.node_groups:
                    data_to.node_groups = ["Light Vectors"]
            if data_to.node_groups and data_to.node_groups[0]:
                data_to.node_groups[0].name = NTE_LIGHT_PANEL_GN_NAME
        except Exception as e:
            print(f"[NTE Lighting Panel] Failed to load {NTE_LIGHT_PANEL_GN_NAME} GN: {e}")

    try:
        lighting_panel_keywords = (
            "colorwheel", "colorpicker", "slider-rim", "origin-rim",
            "lightpanelwgtplane", "lightpanelselectorwgt", "lighting panel",
        )
        excluded_kw = ("face", "phoneme", "mouth", "eyebrow", "expression", "facerig", "facrig")

        with bpy.data.libraries.load(setup_blend, link=False) as (data_from, data_to):
            target_objs = [
                o for o in data_from.objects
                if not any(kw in o.lower() for kw in excluded_kw)
                and any(kw in o.lower() for kw in lighting_panel_keywords)
                and o not in bpy.data.objects
            ]
            data_to.objects = target_objs

        target_wgt_coll = next((c for c in bpy.data.collections if c.name.startswith("WGTS_")), None)
        if not target_wgt_coll:
            target_wgt_coll = bpy.data.collections.get("wgt") or bpy.data.collections.get("WGTS")
        if not target_wgt_coll:
            target_wgt_coll = bpy.data.collections.new("wgt")
            if target_wgt_coll.name not in [c.name for c in bpy.context.scene.collection.children]:
                bpy.context.scene.collection.children.link(target_wgt_coll)

        for obj in data_to.objects:
            if not obj:
                continue
            o_low = obj.name.lower()
            is_widget = any(k in o_low for k in ("colorpicker", "slider-rim", "origin-rim", "lightpanelwgt", "lightpanelselector"))
            dest_coll = target_wgt_coll if is_widget else bpy.context.scene.collection
            if obj.name not in dest_coll.objects:
                dest_coll.objects.link(obj)
            if "colorwheel" in o_low:
                obj.hide_viewport = False
                obj.hide_render = True
            elif is_widget:
                obj.hide_render = True

        wgt_plane = bpy.data.objects.get("LightPanelWGTPlane")
        wgt_selector = bpy.data.objects.get("LightPanelSelectorWGT")
        if wgt_plane:
            wgt_plane.hide_viewport = False
            wgt_plane.hide_render = True
        if wgt_selector:
            wgt_selector.hide_viewport = False
            wgt_selector.hide_render = True

        lp_arm = bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL)
        if lp_arm and lp_arm.type == 'ARMATURE':
            for pb in lp_arm.pose.bones:
                if pb.name == "Lighting Panel" and wgt_plane:
                    pb.custom_shape = wgt_plane
                    pb.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
                    pb.use_custom_shape_bone_size = True
                    pb.bone.hide = False
                elif pb.name in ("Rim Lit", "Shadow", "Lit", "Ambient", "RimShadow", "Rim.R", "Rim.L", "RimX", "RimY") and wgt_selector:
                    pb.custom_shape = wgt_selector
                    pb.custom_shape_scale_xyz = (0.15, 0.15, 0.15)
                    pb.use_custom_shape_bone_size = True
                    pb.bone.hide = False
            from setup_wizard.utils.zzz_lighting_panel import bake_zzz_rim_slider_defaults
            bake_zzz_rim_slider_defaults(lp_arm, force=True)
    except Exception as e:
        print(f"[NTE Lighting Panel] Failed to import Lighting Panel objects from {setup_blend}: {e}")
        return False
    return True


def setup_nte_light_panel_modifier(obj):
    """Attach NTE's attribute-only Lighting Panel GN modifier to a character mesh."""
    from setup_wizard.utils.modifier_utils import set_modifier_property, get_modifier_outputs

    lp_gn = bpy.data.node_groups.get(NTE_LIGHT_PANEL_GN_NAME)
    if not lp_gn or not obj or obj.type != 'MESH':
        return None

    mod = next(
        (
            m for m in obj.modifiers
            if m.type == 'NODES'
            and (m.name == NTE_LIGHT_PANEL_MODIFIER_NAME or (m.node_group and m.node_group.name == lp_gn.name))
        ),
        None,
    )
    if not mod:
        mod = obj.modifiers.new(name=NTE_LIGHT_PANEL_MODIFIER_NAME, type='NODES')
    mod.node_group = lp_gn

    socket_mapping = {
        "Ambient Color Wheel": "ColorWheel-Ambient",
        "Ambient Color Picker": "ColorPicker-Ambient",
        "Lit Color Wheel": "ColorWheel-Lit",
        "Lit Color Picker": "ColorPicker-Lit",
        "Shadow Color Wheel": "ColorWheel-Shadow",
        "Shadow Color Picker": "ColorPicker-Shadow",
        "Rim Lit Color Wheel": "ColorWheel-RimLit",
        "Rim Lit Color Picker": "ColorPicker-RimLit",
        "Rim Shadow Color Wheel": "ColorWheel-RimShadow",
        "Rim Shadow Color Picker": "ColorPicker-RimShadow",
        "Rim X Size Origin": "Origin-RimX",
        "Rim X Size Slider": "Slider-RimX",
        "Rim Y Size Origin": "Origin-RimY",
        "Rim Y Size Slider": "Slider-RimY",
        "Socket_0": "ColorWheel-Ambient",
        "Socket_1": "ColorPicker-Ambient",
        "Socket_2": "ColorWheel-Lit",
        "Socket_3": "ColorPicker-Lit",
        "Socket_4": "ColorWheel-Shadow",
        "Socket_5": "ColorPicker-Shadow",
        "Socket_6": "ColorWheel-RimLit",
        "Socket_7": "ColorPicker-RimLit",
        "Socket_8": "ColorWheel-RimShadow",
        "Socket_9": "ColorPicker-RimShadow",
        "Socket_26": "Origin-RimX",
        "Socket_27": "Slider-RimX",
        "Socket_28": "Origin-RimY",
        "Socket_29": "Slider-RimY",
    }
    for socket_name, target_name in socket_mapping.items():
        target_obj = bpy.data.objects.get(target_name)
        if target_obj:
            set_modifier_property(mod, socket_name, target_obj)

    # Leave lightDir/headForward/headUp empty so NTE's Light Vectors stays authoritative.
    # Map ZZZ Light Vectors socket names to the exact attribute names ZZZLightPanelAttr reads
    # (note: 'RimLit' and 'RimShadow' have NO spaces!).
    from setup_wizard.utils.modifier_utils import set_property_field
    clear_names = {"lightDir", "headForward", "headUp"}
    attr_map = {
        "Ambient": "Ambient",
        "Lit": "Lit",
        "Shadow": "Shadow",
        "Rim Lit": "RimLit",
        "Rim Shadow": "RimShadow",
        "Rim": "Rim",
    }
    outputs = get_modifier_outputs(mod)
    if lp_gn and hasattr(lp_gn, "interface"):
        for item in lp_gn.interface.items_tree:
            if item.item_type == 'SOCKET' and item.in_out == 'OUTPUT' and item.socket_type != 'NodeSocketGeometry':
                ident = item.identifier
                if item.name in clear_names:
                    val = ""
                elif item.name in attr_map:
                    val = attr_map[item.name]
                else:
                    continue
                set_modifier_property(mod, f"{ident}_attribute_name", val)
                if outputs is not None:
                    if hasattr(outputs, "keys") and ident in outputs.keys():
                        set_property_field(outputs[ident], "attribute_name", val)
                    elif hasattr(outputs, ident):
                        set_property_field(getattr(outputs, ident), "attribute_name", val)
    return mod


def attach_nte_lighting_panel_to_rig(context, active_rig):
    """Join the imported ZZZ 3D Lighting Panel armature into the NTE rig and attach modifiers to meshes."""
    if not active_rig or active_rig.type != 'ARMATURE':
        return False

    lp_arms = [
        o for o in list(bpy.data.objects)
        if o != active_rig and o.type == 'ARMATURE' and 'lighting panel' in o.name.lower()
    ]
    lp_arm = bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL)
    if lp_arm not in lp_arms and lp_arms:
        lp_arm = lp_arms[0]

    if lp_arm and lp_arm != active_rig and lp_arm.type == 'ARMATURE' and not active_rig.data.bones.get("Lighting Panel"):
        try:
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            # Ensure lp_arm is linked in the active view layer so bpy.ops.object.join() always succeeds
            if lp_arm.name not in context.scene.collection.objects and not lp_arm.users_collection:
                context.scene.collection.objects.link(lp_arm)
            # Shift Lighting Panel slightly to the left (-X) so it clears NTE face sliders without being too far
            lp_arm.location.x -= 0.35
            context.view_layer.update()
            for o in list(context.selected_objects):
                o.select_set(False)
            lp_arm.hide_viewport = False
            lp_arm.hide_select = False
            lp_arm.hide_set(False)
            active_rig.hide_viewport = False
            active_rig.hide_select = False
            active_rig.hide_set(False)
            lp_arm.select_set(True)
            active_rig.select_set(True)
            context.view_layer.objects.active = active_rig
            bpy.ops.object.join()
        except Exception as e_join:
            print(f"[NTE Lighting Panel] Join notice: {e_join}")

    # Remove any remaining standalone/duplicate Lighting Panel armatures so there is never a duplicate in the scene
    for extra_lp in list(bpy.data.objects):
        if extra_lp != active_rig and extra_lp.type == 'ARMATURE' and 'lighting panel' in extra_lp.name.lower():
            try:
                arm_data = extra_lp.data
                bpy.data.objects.remove(extra_lp, do_unlink=True)
                if arm_data and arm_data.users == 0:
                    bpy.data.armatures.remove(arm_data)
            except Exception:
                pass

    if not active_rig.data.bones.get("Lighting Panel"):
        return False

    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = active_rig
        bpy.ops.object.mode_set(mode='EDIT')
        eb_lp = active_rig.data.edit_bones.get("Lighting Panel")
        if eb_lp:
            eb_lp.parent = None
        bpy.ops.object.mode_set(mode='POSE')
        lp_pb = active_rig.pose.bones.get("Lighting Panel")
        if lp_pb:
            target_lp = next(
                (cand for cand in ("DEF-spine.006", "head", "Head", "root.002", "root.001", "root") if cand in active_rig.pose.bones),
                None,
            )
            if target_lp:
                con_lp = lp_pb.constraints.get("Child Of") or lp_pb.constraints.new('CHILD_OF')
                con_lp.name = "Child Of"
                con_lp.target = active_rig
                con_lp.subtarget = target_lp
                active_rig.data.bones.active = active_rig.data.bones["Lighting Panel"]
                try:
                    bpy.ops.constraint.childof_set_inverse(constraint=con_lp.name, owner='BONE')
                except Exception:
                    r_bone = active_rig.data.bones.get(target_lp)
                    p_bone = active_rig.data.bones.get("Lighting Panel")
                    if r_bone and p_bone:
                        con_lp.inverse_matrix = r_bone.matrix_local.inverted() @ p_bone.matrix_local
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e_con:
        print(f"[NTE Lighting Panel] Child Of notice: {e_con}")

    try:
        wgt_selector = bpy.data.objects.get("LightPanelSelectorWGT")
        wgt_plane = bpy.data.objects.get("LightPanelWGTPlane")

        lighting_coll = None
        if hasattr(active_rig.data, "collections"):
            lighting_coll = active_rig.data.collections.get("Lighting") or active_rig.data.collections.get("Light Panel")
            if not lighting_coll:
                lighting_coll = active_rig.data.collections.new("Lighting")
            lighting_coll.is_visible = True
            lp_extras = active_rig.data.collections.get("Light Panel Extras")
            if lp_extras:
                lp_extras.is_visible = False

        other_coll = active_rig.data.collections.get("Other") if hasattr(active_rig.data, "collections") else None
        panel_bones = ("Lighting Panel", "Rim Lit", "Shadow", "Lit", "Ambient", "RimShadow", "Rim.L", "Rim.R", "RimX", "RimY")
        for pb_name in panel_bones:
            b = active_rig.data.bones.get(pb_name)
            pb = active_rig.pose.bones.get(pb_name)
            if b and pb:
                b.hide = False
                b.hide_select = False
                if lighting_coll:
                    lighting_coll.assign(b)
                    if other_coll:
                        try:
                            other_coll.unassign(b)
                        except Exception:
                            pass
                if pb_name == "Lighting Panel" and wgt_plane:
                    pb.custom_shape = wgt_plane
                    pb.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
                    pb.use_custom_shape_bone_size = True
                elif pb_name != "Lighting Panel" and wgt_selector:
                    pb.custom_shape = wgt_selector
                    pb.custom_shape_scale_xyz = (0.15, 0.15, 0.15)
                    pb.use_custom_shape_bone_size = True

        from setup_wizard.utils.zzz_lighting_panel import bake_zzz_rim_slider_defaults
        bake_zzz_rim_slider_defaults(active_rig, force=True)

        char_coll = next((c for c in active_rig.users_collection if not c.name.startswith("WGTS") and c.name.lower() != "wgt"), None)
        for obj in bpy.data.objects:
            if "colorwheel" in obj.name.lower():
                obj.hide_render = True
                if char_coll and obj.name not in char_coll.objects:
                    for c in list(obj.users_collection):
                        try:
                            c.objects.unlink(obj)
                        except Exception:
                            pass
                    char_coll.objects.link(obj)
    except Exception as e_bones:
        print(f"[NTE Lighting Panel] Bones config notice: {e_bones}")

    # Attach attribute-only Lighting Panel modifier to all character meshes
    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
    for mesh_obj in _iter_rig_meshes(active_rig):
        o_low = mesh_obj.name.lower()
        if any(k in o_low for k in ("colorwheel", "colorpicker", "slider", "origin-rim", "lightpanel", "wgt")):
            continue
        setup_nte_light_panel_modifier(mesh_obj)

    return True


def _collect_nte_global_property_trees(target_materials=None):
    """Return dict[NodeTree, list[Node]] for NTE Global Material Properties groups."""
    grouped_nodes = {}
    mats = (
        list(target_materials)
        if target_materials is not None
        else [m for m in bpy.data.materials if getattr(m, "use_nodes", False) and m.node_tree]
    )
    for mat in set(mats):
        if getattr(mat, "use_nodes", False) and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "global material properties" in node.node_tree.name.lower():
                        grouped_nodes.setdefault(node.node_tree, []).append(node)

    if not grouped_nodes and target_materials is None:
        for ng in bpy.data.node_groups:
            if "global material properties" in ng.name.lower():
                grouped_nodes.setdefault(ng, [])

    return grouped_nodes


def connect_nte_lighting_panel(target_materials=None):
    """Connect ZZZLightPanelAttr colors and RimScale to NTE Global Material Properties."""
    lp_attr_group = _ensure_zzz_light_panel_attr_group()
    if not lp_attr_group:
        return False

    grouped_nodes = _collect_nte_global_property_trees(target_materials)
    connected_any = False

    for tree, group_nodes in grouped_nodes.items():
        if group_nodes and tree.users - int(tree.use_fake_user) > len(group_nodes):
            tree = tree.copy()
            for node in group_nodes:
                node.node_tree = tree

        out_node = tree.nodes.get("Global Properties") or tree.nodes.get("Group Output")
        if not out_node:
            continue

        lp_node = _find_hsr_lp_attr_node(tree)
        if not lp_node:
            lp_node = tree.nodes.new("ShaderNodeGroup")
            lp_node.name = HSR_LIGHT_PANEL_ATTR_NAME
            lp_node.label = HSR_LIGHT_PANEL_ATTR_NAME
            lp_node.location = (out_node.location.x - 420, out_node.location.y - 180)
        if lp_node.node_tree != lp_attr_group:
            lp_node.node_tree = lp_attr_group

        for out_name, inp_name in NTE_LIGHT_PANEL_SOCKET_LINKS:
            if out_name in lp_node.outputs and inp_name in out_node.inputs:
                target_sock = out_node.inputs[inp_name]
                for l in list(target_sock.links):
                    tree.links.remove(l)
                tree.links.new(lp_node.outputs[out_name], target_sock)
                connected_any = True

        scale_sock = out_node.inputs.get("Rim Scale")
        if scale_sock and "RimScale" in lp_node.outputs:
            scale_mul = tree.nodes.get("NTE_Rim_Scale")
            if not scale_mul or scale_mul.type != 'VECT_MATH':
                scale_mul = tree.nodes.new("ShaderNodeVectorMath")
                scale_mul.name = "NTE_Rim_Scale"
                scale_mul.location = (lp_node.location.x + 150, lp_node.location.y - 140)
            scale_mul.operation = 'SCALE'
            scale_mul.inputs["Scale"].default_value = 0.25

            sep = tree.nodes.get("NTE_Rim_SepXYZ")
            if not sep or sep.type != 'SEPXYZ':
                sep = tree.nodes.new("ShaderNodeSeparateXYZ")
                sep.name = "NTE_Rim_SepXYZ"
                sep.location = (scale_mul.location.x + 160, scale_mul.location.y)
            comb = tree.nodes.get("NTE_Rim_CombXYZ")
            if not comb or comb.type != 'COMBXYZ':
                comb = tree.nodes.new("ShaderNodeCombineXYZ")
                comb.name = "NTE_Rim_CombXYZ"
                comb.location = (sep.location.x + 160, sep.location.y)

            for l in list(scale_mul.inputs[0].links):
                tree.links.remove(l)
            tree.links.new(lp_node.outputs["RimScale"], scale_mul.inputs[0])

            for l in list(sep.inputs["Vector"].links):
                tree.links.remove(l)
            tree.links.new(scale_mul.outputs["Vector"], sep.inputs["Vector"])

            for axis in ("X", "Y"):
                for l in list(comb.inputs[axis].links):
                    tree.links.remove(l)
                tree.links.new(sep.outputs[axis], comb.inputs[axis])
            for l in list(comb.inputs["Z"].links):
                tree.links.remove(l)
            comb.inputs["Z"].default_value = 0.5

            for l in list(scale_sock.links):
                tree.links.remove(l)
            tree.links.new(comb.outputs["Vector"], scale_sock)
            connected_any = True

        tree.update_tag()

    return connected_any


def disconnect_nte_lighting_panel(target_materials=None):
    """Disconnect ZZZLightPanelAttr from NTE Global Material Properties."""
    grouped_nodes = _collect_nte_global_property_trees(target_materials)

    for tree, group_nodes in grouped_nodes.items():
        if group_nodes and tree.users - int(tree.use_fake_user) > len(group_nodes):
            tree = tree.copy()
            for node in group_nodes:
                node.node_tree = tree

        out_node = tree.nodes.get("Global Properties") or tree.nodes.get("Group Output")
        lp_node = _find_hsr_lp_attr_node(tree)
        if lp_node:
            for out_sock in lp_node.outputs:
                for l in list(out_sock.links):
                    tree.links.remove(l)

        if out_node:
            scale_sock = out_node.inputs.get("Rim Scale")
            if scale_sock:
                for l in list(scale_sock.links):
                    if l.from_node.name == "NTE_Rim_CombXYZ":
                        tree.links.remove(l)

        tree.update_tag()


def is_nte_lighting_panel_connected(target_materials=None) -> bool:
    """Return True if NTE Global Material Properties has ZZZLightPanelAttr linked."""
    grouped_nodes = _collect_nte_global_property_trees(target_materials)
    for tree in grouped_nodes:
        out_node = tree.nodes.get("Global Properties") or tree.nodes.get("Group Output")
        if not out_node:
            continue
        lp_node = _find_hsr_lp_attr_node(tree)
        if not lp_node:
            continue
        for out_sock in lp_node.outputs:
            for l in out_sock.links:
                if l.to_node == out_node:
                    return True
        scale_sock = out_node.inputs.get("Rim Scale")
        if scale_sock and any(l.from_node.name == "NTE_Rim_CombXYZ" for l in scale_sock.links):
            return True
    return False
