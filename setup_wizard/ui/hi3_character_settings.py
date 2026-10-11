"""Per-character controls for the bundled HI3 ImpactToon shader."""
import bpy
from bpy.props import EnumProperty
from bpy.types import Operator, Panel

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.character_settings_utils import (
    ensure_character_node_trees_isolated, get_character_materials,
    is_game_armature,
)

LIGHTING_SOCKETS = (
    ('Ambient Colour', 'ambient'), ('Sharp Lit Colour', 'sharp_lit'),
    ('Soft Lit Colour', 'soft_lit'), ('Sharp Shadow Colour', 'sharp_shadow'),
    ('Soft Shadow Colour', 'soft_shadow'), ('Shadow Position', 'shadow_position'),
)
OUTLINE_SOCKETS = ('Outline Tint', 'Outline Saturation', 'Outline Intensity')
PRESET_ITEMS = tuple((str(i), name, '') for i, name in enumerate(
    ('Default', 'Sunrise', 'Day', 'Sunset', 'Night', 'Rainy', 'Custom')))
_pending = False


def _global_nodes(materials):
    return [node for mat in materials if mat.node_tree
            for node in mat.node_tree.nodes
            if node.type == 'GROUP' and node.node_tree
            and 'global material properties' in node.node_tree.name.lower()
            and node.node_tree.nodes.get('Global Properties')]


def _interface_socket(tree, name, direction):
    if hasattr(tree, 'interface'):
        return next((item for item in tree.interface.items_tree
                     if item.item_type == 'SOCKET' and item.in_out == direction
                     and item.name == name), None)
    return (tree.inputs if direction == 'INPUT' else tree.outputs).get(name)


def configure_hi3_materials(materials):
    """Set HI3 defaults once and widen the actual shader socket ranges."""
    trees = {node.node_tree for node in _global_nodes(materials)}
    for tree in trees:
        output = tree.nodes.get('Global Properties')
        if not tree.get('_hi3_settings_defaults_v2'):
            if 'Outline Saturation' in output.inputs:
                output.inputs['Outline Saturation'].default_value = 1.0
            tree['_hi3_settings_defaults_v2'] = True
        intensity = _interface_socket(tree, 'Outline Intensity', 'OUTPUT')
        if intensity:
            intensity.min_value = 0.0
            intensity.max_value = 50.0
    for mat in materials:
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'GROUP' or not node.node_tree:
                continue
            if 'impacttoon - outlines' in node.node_tree.name.lower():
                intensity = _interface_socket(node.node_tree, 'Outline Intensity', 'INPUT')
                if intensity:
                    intensity.min_value = 0.0
                    intensity.max_value = 50.0
                saturation = node.inputs.get('Outline Saturation')
                if saturation and not saturation.is_linked and not mat.get('_hi3_outline_defaults_v2'):
                    saturation.default_value = 1.0
                    mat['_hi3_outline_defaults_v2'] = True


def prepare_character_settings(arm, materials):
    ensure_character_node_trees_isolated(arm, materials)
    nodes = _global_nodes(materials)
    if not nodes:
        return None
    # Body, face, hair and outlines use a single property tree owned by this rig.
    tree = nodes[0].node_tree
    for node in nodes:
        node.node_tree = tree
    configure_hi3_materials(materials)
    output = tree.nodes['Global Properties']
    face_nodes = [node for mat in materials if mat.node_tree
                  for node in mat.node_tree.nodes
                  if node.type == 'GROUP' and node.node_tree
                  and 'impacttoon - face' in node.node_tree.name.lower()
                  and '_ExpBlushIntensity' in node.inputs]
    if face_nodes:
        blush = _interface_socket(tree, 'Exp Blush Intensity', 'OUTPUT')
        if not blush:
            value = face_nodes[0].inputs['_ExpBlushIntensity'].default_value
            if hasattr(tree, 'interface'):
                blush = tree.interface.new_socket(name='Exp Blush Intensity',
                    in_out='OUTPUT', socket_type='NodeSocketFloat')
            else:
                blush = tree.outputs.new('NodeSocketFloat', 'Exp Blush Intensity')
            blush.min_value, blush.max_value = 0.0, 1.0
            blush.default_value = value
            output.inputs['Exp Blush Intensity'].default_value = value
        for mat in materials:
            if not mat.node_tree:
                continue
            global_node = next((n for n in mat.node_tree.nodes
                                if n.type == 'GROUP' and n.node_tree == tree), None)
            if not global_node:
                continue
            for face in face_nodes:
                if face.id_data != mat.node_tree:
                    continue
                target = face.inputs['_ExpBlushIntensity']
                source = global_node.outputs['Exp Blush Intensity']
                if not any(link.from_socket == source for link in target.links):
                    mat.node_tree.links.new(source, target)
    tree['_hi3_character_settings_ready'] = True
    return output


def _ready_output(arm, materials):
    nodes = _global_nodes(materials)
    if not nodes or any(n.node_tree.get('_owner_armature') != arm.name
                        or not n.node_tree.get('_hi3_character_settings_ready')
                        or not n.node_tree.get('_hi3_settings_defaults_v2') for n in nodes):
        return None
    return nodes[0].node_tree.nodes['Global Properties']


def _prepare_selected():
    global _pending
    _pending = False
    context = bpy.context
    if is_game_armature(context, GameType.HONKAI_IMPACT_3RD.name):
        arm, materials = get_character_materials(context)
        if arm and materials:
            prepare_character_settings(arm, materials)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return None


def _queue_prepare():
    global _pending
    if not _pending:
        _pending = True
        bpy.app.timers.register(_prepare_selected, first_interval=0.0)


def _get_light_mode(tree):
    from setup_wizard.ui.gi_ui_setup_wizard_menu import GI_LIGHT_PRESETS
    saved = tree.get('_hi3_light_mode')
    if saved == '6':
        return 6
    output = tree.nodes.get('Global Properties')
    if not output:
        return 0
    candidates = [saved] if saved in GI_LIGHT_PRESETS else list(GI_LIGHT_PRESETS)
    for key in candidates:
        preset = GI_LIGHT_PRESETS[key]
        if all(all(abs(float(a) - float(b)) < 1e-4
                   for a, b in zip(output.inputs[name].default_value[:3], preset[field]))
               for name, field in LIGHTING_SOCKETS if field != 'shadow_position'
               and name in output.inputs):
            return int(key)
    return 6


def _set_light_mode(tree, mode):
    tree['_hi3_light_mode'] = str(mode)
    if mode == 6:
        return
    from setup_wizard.ui.gi_ui_setup_wizard_menu import GI_LIGHT_PRESETS
    values = GI_LIGHT_PRESETS[str(mode)]
    output = tree.nodes.get('Global Properties')
    if not output:
        return
    for name, key in LIGHTING_SOCKETS:
        socket = output.inputs.get(name)
        if socket:
            value = values[key]
            socket.default_value = ((*value, 1.0) if isinstance(value, tuple)
                                    else (0.51 if mode == 0 else value))


def register_hi3_properties():
    bpy.types.ShaderNodeTree.hi3_light_mode = EnumProperty(
        name='Lighting Preset', items=PRESET_ITEMS,
        get=_get_light_mode, set=_set_light_mode,
    )


def unregister_hi3_properties():
    unregister_pending()
    if hasattr(bpy.types.ShaderNodeTree, 'hi3_light_mode'):
        del bpy.types.ShaderNodeTree.hi3_light_mode


class HI3_OT_CharacterLightingPreset(Operator):
    bl_idname = 'hi3.character_lighting_preset'
    bl_label = 'Lighting Preset'
    bl_options = {'REGISTER', 'UNDO'}
    preset: EnumProperty(name='Lighting Preset', items=PRESET_ITEMS, default='0')

    @classmethod
    def poll(cls, context):
        return is_game_armature(context, GameType.HONKAI_IMPACT_3RD.name)

    def execute(self, context):
        arm, materials = get_character_materials(context)
        output = prepare_character_settings(arm, materials)
        if not output:
            return {'CANCELLED'}
        _set_light_mode(output.id_data, int(self.preset))
        return {'FINISHED'}


class HI3_PT_CharacterSettings(Panel):
    bl_label = 'Character Settings'
    bl_idname = 'HI3_PT_CharacterSettings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return is_game_armature(context, GameType.HONKAI_IMPACT_3RD.name)

    def draw(self, context):
        arm, materials = get_character_materials(context)
        output = _ready_output(arm, materials)
        layout = self.layout
        if not output:
            if _global_nodes(materials):
                _queue_prepare()
                layout.label(text='Loading character settings…')
            else:
                layout.label(text='Set up HI3 materials first', icon='INFO')
            return
        mode = output.id_data.hi3_light_mode
        lighting = layout.column(align=True)
        lighting.label(text='Lighting Mode:', icon='LIGHT')
        lighting.prop(output.id_data, 'hi3_light_mode', text='')
        if mode == '6':
            custom = lighting.box()
            custom.label(text='Custom Colors', icon='COLOR')
            colors = custom.column(align=True)
            for name, key in LIGHTING_SOCKETS:
                if key == 'shadow_position':
                    continue
                socket = output.inputs.get(name)
                if socket:
                    colors.prop(socket, 'default_value', text=name.replace(' Colour', ''))
        outlines = layout.box()
        outlines.label(text='Outlines', icon='STROKE')
        outline_controls = outlines.column(align=True)
        for name in OUTLINE_SOCKETS:
            socket = output.inputs.get(name)
            if socket:
                outline_controls.prop(socket, 'default_value', text=name, slider=socket.type == 'VALUE')
        shadow = layout.box()
        shadow.label(text='Shadow Settings', icon='SHADING_SOLID')
        shadow_position = output.inputs.get('Shadow Position')
        if shadow_position:
            shadow.column(align=True).prop(shadow_position, 'default_value', text='Shadow Position', slider=True)
        blush = output.inputs.get('Exp Blush Intensity')
        if blush:
            face = layout.box()
            face.label(text='Face', icon='USER')
            face.column(align=True).prop(blush, 'default_value', text='Exp Blush Intensity', slider=True)


def unregister_pending():
    global _pending
    if bpy.app.timers.is_registered(_prepare_selected):
        bpy.app.timers.unregister(_prepare_selected)
    _pending = False
