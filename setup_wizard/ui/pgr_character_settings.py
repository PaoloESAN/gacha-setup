from setup_wizard.utilites.new_lights import draw_lights_plus
"""Character-local controls for PGR's WuWa-based shader."""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator, Panel

from setup_wizard.ui.character_settings_utils import (
    ensure_character_node_trees_isolated, get_character_materials, is_game_armature,
    _iter_rig_meshes,
)

PRESETS = ('Default', 'Sunrise', 'Day', 'Sunset', 'Night', 'Rainy', 'Custom')
_pending = False


def _global_nodes(materials):
    return [n for m in materials if m.node_tree for n in m.node_tree.nodes
            if n.type == 'GROUP' and n.node_tree
            and 'global material properties' in n.node_tree.name.lower()]


def _palette(tree):
    return next((n for n in tree.nodes if n.type == 'GROUP' and n.node_tree
                 and 'color palette' in n.node_tree.name.lower()), None)


def prepare_character_settings(arm, materials):
    ensure_character_node_trees_isolated(arm, materials)
    nodes = _global_nodes(materials)
    for tree in {n.node_tree for n in nodes}:
        if tree.get('_pgr_settings_owner') != arm.name:
            # The global tree may be isolated while its nested palette is shared.
            palette = _palette(tree)
            if palette:
                palette.node_tree = palette.node_tree.copy()
            tree['_pgr_settings_owner'] = arm.name
        if not tree.get('_pgr_fresnel_power_default_v1'):
            _set_power(tree, 5.0)
            tree['_pgr_fresnel_power_default_v1'] = True
        if not tree.get('_pgr_rim_scale_default_v1'):
            _set_rim_scale(tree, 0.0)
            tree['_pgr_rim_scale_default_v1'] = True
    return nodes[0].node_tree if nodes else None


def _prepare_selected():
    global _pending
    _pending = False
    if is_game_armature(bpy.context, 'PUNISHING_GRAY_RAVEN'):
        arm, materials = get_character_materials(bpy.context)
        if arm and materials:
            prepare_character_settings(arm, materials)
            from setup_wizard.character_rig_setup.pgr_visual_widgets import hide_unused_prop_controls
            hide_unused_prop_controls(arm)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def unregister_pending():
    global _pending
    if bpy.app.timers.is_registered(_prepare_selected):
        bpy.app.timers.unregister(_prepare_selected)
    _pending = False


def _get_fresnel(tree):
    output = tree.nodes.get('Global Properties')
    socket = output.inputs.get('Use Fresnel') if output else None
    return bool(socket and socket.default_value > .5)


def _set_fresnel(tree, enabled):
    output = tree.nodes.get('Global Properties')
    socket = output.inputs.get('Use Fresnel') if output else None
    if socket:
        socket.default_value = 1.0 if enabled else 0.0


def _fresnel_socket(tree, name):
    output = tree.nodes.get('Global Properties')
    return output.inputs.get(name) if output else None


def _get_power(tree):
    socket = _fresnel_socket(tree, 'Fresnel Power')
    return max(0.0, min(20.0, 30.0 - socket.default_value)) if socket else 0.0


def _set_power(tree, value):
    socket = _fresnel_socket(tree, 'Fresnel Power')
    if socket:
        socket.default_value = 30.0 - value


def _get_scaler(tree):
    socket = _fresnel_socket(tree, 'Fresnel Scaler')
    return max(0.0, min(10.0, socket.default_value)) if socket else 0.0


def _set_scaler(tree, value):
    socket = _fresnel_socket(tree, 'Fresnel Scaler')
    if socket:
        socket.default_value = value


def _set_rim_scale(tree, value):
    socket = _fresnel_socket(tree, 'Rim Scale')
    if socket:
        socket.default_value = (value, value, value)


def _outline_inputs(arm):
    for mesh in _iter_rig_meshes(arm):
        for modifier in mesh.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            for socket in modifier.node_group.interface.items_tree:
                if (socket.item_type == 'SOCKET' and socket.in_out == 'INPUT'
                        and socket.name == 'Outline Thickness'):
                    yield mesh, modifier, socket


def _get_outline_thickness(arm):
    from setup_wizard.utils.modifier_utils import get_modifier_property
    for _, modifier, socket in _outline_inputs(arm):
        value = get_modifier_property(modifier, socket.identifier)
        return float(value) if value is not None else socket.default_value
    return 0.1


def _set_outline_thickness(arm, value):
    from setup_wizard.utils.modifier_utils import set_modifier_property
    for mesh, modifier, socket in _outline_inputs(arm):
        set_modifier_property(modifier, socket.identifier, value)
        mesh.update_tag()


def register_pgr_properties():
    bpy.types.Object.pgr_outline_thickness = FloatProperty(
        name='Outline Thickness', min=0.0, soft_max=1.0, precision=3,
        get=_get_outline_thickness, set=_set_outline_thickness)
    bpy.types.ShaderNodeTree.pgr_use_fresnel = BoolProperty(
        name='Use Fresnel', get=_get_fresnel, set=_set_fresnel)
    bpy.types.ShaderNodeTree.pgr_fresnel_power = FloatProperty(
        name='Fresnel Power', min=0.0, max=20.0, get=_get_power, set=_set_power)
    bpy.types.ShaderNodeTree.pgr_fresnel_scaler = FloatProperty(
        name='Fresnel Scaler', min=0.0, max=10.0, get=_get_scaler, set=_set_scaler)


def unregister_pgr_properties():
    unregister_pending()
    if hasattr(bpy.types.Object, 'pgr_outline_thickness'):
        del bpy.types.Object.pgr_outline_thickness
    for name in ('pgr_use_fresnel', 'pgr_fresnel_power', 'pgr_fresnel_scaler'):
        if hasattr(bpy.types.ShaderNodeTree, name):
            delattr(bpy.types.ShaderNodeTree, name)


class PGR_OT_CharacterLightingPreset(Operator):
    bl_idname = 'pgr.character_lighting_preset'
    bl_label = 'Lighting Mode'
    bl_options = {'REGISTER', 'UNDO'}
    preset: EnumProperty(items=tuple((str(i), name, '') for i, name in enumerate(PRESETS)))

    @classmethod
    def poll(cls, context):
        return is_game_armature(context, 'PUNISHING_GRAY_RAVEN')

    def execute(self, context):
        arm, materials = get_character_materials(context)
        tree = prepare_character_settings(arm, materials)
        if not tree:
            return {'CANCELLED'}
        for tree in {n.node_tree for n in _global_nodes(materials)}:
            palette = _palette(tree)
            if palette and 'Value' in palette.inputs:
                palette.inputs['Value'].default_value = float(self.preset)
        return {'FINISHED'}


def _draw_sockets(layout, node, names):
    if node:
        for name in names:
            socket = node.inputs.get(name)
            if socket and not socket.is_linked:
                layout.prop(socket, 'default_value', text=name, slider=socket.type == 'VALUE')


class PGR_PT_CharacterSettings(Panel):
    bl_label = 'Character Settings'
    bl_idname = 'PGR_PT_CharacterSettings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return is_game_armature(context, 'PUNISHING_GRAY_RAVEN')

    def draw(self, context):
        from setup_wizard.ui.character_settings_tabs import draw_character_settings_tabs
        if draw_character_settings_tabs(self.layout, context):
            return
        global _pending
        arm, materials = get_character_materials(context)
        nodes = _global_nodes(materials)
        layout = self.layout

        # 0. Animate Mode (fast playback: lightweight materials, no outlines)
        from setup_wizard.genshin_animate_mode import is_genshin_animate_mode
        is_anim = is_genshin_animate_mode(arm, context=context)
        layout.operator(
            "genshin.toggle_animate_mode",
            text="Disable Animate Mode" if is_anim else "Enable Animate Mode",
            icon="SHADING_TEXTURE" if is_anim else "RESTRICT_RENDER_OFF"
        )

        if nodes and any(n.node_tree.get('_pgr_settings_owner') != arm.name
                         or not n.node_tree.get('_pgr_rim_scale_default_v1') for n in nodes):
            if not _pending:
                _pending = True
                bpy.app.timers.register(_prepare_selected, first_interval=0.0)
            layout.label(text='Loading character settings…')
        elif nodes:
            tree = nodes[0].node_tree
            output = tree.nodes.get('Global Properties')
            palette = _palette(tree)
            if palette and 'Value' in palette.inputs:
                mode = max(0, min(6, int(palette.inputs['Value'].default_value)))
                col = layout.column(align=True)
                col.label(text='Lighting Mode:')
                col.operator_menu_enum('pgr.character_lighting_preset', 'preset', text=PRESETS[mode])
                if mode == 6:
                    box = col.box()
                    box.label(text='Custom Colors', icon='COLOR')
                    _draw_sockets(box.column(align=True), palette,
                                  ('Custom Ambient', 'Custom Light', 'Custom Shadow', 'Custom Rim Tint'))
            draw_lights_plus(layout, context)
            _draw_sockets(layout.column(align=True), output, ('Shadow Position',))
            fresnel = layout.box()
            fresnel.label(text='Fresnel', icon='SHADING_RENDERED')
            fresnel.prop(tree, 'pgr_use_fresnel', text='Use Fresnel')
            if tree.pgr_use_fresnel:
                options = fresnel.column(align=True)
                _draw_sockets(options, output, ('Fresnel Color',))
                options.prop(tree, 'pgr_fresnel_power', text='Fresnel Power', slider=True)
                options.prop(tree, 'pgr_fresnel_scaler', text='Fresnel Scaler', slider=True)
            outlines = layout.box()
            outlines.label(text='Outlines', icon='STROKE')
            _draw_sockets(outlines.column(align=True), output,
                          ('Outline Tint', 'Outline Saturation', 'Outline Intensity'))
            if next(_outline_inputs(arm), None) is not None:
                outlines.prop(arm, 'pgr_outline_thickness', text='Outline Thickness', slider=True)
        else:
            layout.label(text='Set up PGR materials first', icon='INFO')
        # Reuse the same physics controls as WuWa and HI3.
        from setup_wizard.ui.hi3_character_settings import _draw_physics
        _draw_physics(layout, context)
