from setup_wizard.utilites.new_lights import draw_lights_plus
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


def _upgrade_legacy_eye_atlas_nodes(materials):
    """Upgrades any legacy HI3_Atlas_Mapping ShaderNodeMapping on 4x4 eye materials to HI3_Eye_Atlas_Controller."""
    from setup_wizard.material_data_import_setup.game_material_data_importers import HonkaiImpact3rdMaterialDataImporter
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
        nt = mat.node_tree
        if nt.nodes.get("HI3_Eye_Atlas_Controller"):
            continue
        legacy_map = nt.nodes.get("HI3_Atlas_Mapping")
        if not legacy_map or legacy_map.type != 'MAPPING':
            continue
        orig_m = (mat.get("_original_material_name") or mat.name.replace("ImpactToon - ", "").replace(" Outlines", "")).strip().lower()
        if "eye" not in orig_m:
            continue
        sc = legacy_map.inputs["Scale"].default_value
        loc = legacy_map.inputs["Location"].default_value
        if abs(sc[0] - 0.25) <= 1e-3 and abs(sc[1] - 0.25) <= 1e-3:
            HonkaiImpact3rdMaterialDataImporter._apply_uv_scale_offset(
                mat, (float(sc[0]), float(sc[1])), (float(loc[0]), float(loc[1])), orig_low=orig_m
            )


def _eye_controller_nodes(materials):
    """Returns list of (mat, grp_node, side) for HI3_Eye_Atlas_Controller nodes on eye materials."""
    result = []
    for mat in materials:
        if not mat or not mat.node_tree or "outlines" in mat.name.lower():
            continue
        grp = mat.node_tree.nodes.get("HI3_Eye_Atlas_Controller")
        if not grp or grp.type != 'GROUP':
            continue
        orig_low = (mat.get("_original_material_name") or mat.name).lower()
        side = mat.get("_hi3_eye_side")
        if not side:
            is_left = ("lefteye" in orig_low or (
                "Is Left Eye" in grp.inputs and grp.inputs["Is Left Eye"].default_value >= 0.5
            ))
            side = "L" if is_left else "R"
        result.append((mat, grp, side))
    return result


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

    # Wire 4x4 Eye Atlas Controllers (Left Eye Type / Right Eye Type 1..8)
    _upgrade_legacy_eye_atlas_nodes(materials)
    eye_ctrls = _eye_controller_nodes(materials)
    if eye_ctrls:
        for side_code, sock_name in (("L", "Left Eye Type"), ("R", "Right Eye Type")):
            side_nodes = [(m, g) for (m, g, s) in eye_ctrls if s == side_code]
            if not side_nodes:
                continue
            eye_sock = _interface_socket(tree, sock_name, 'OUTPUT')
            init_val = int(side_nodes[0][1].inputs['Eye Type'].default_value) if 'Eye Type' in side_nodes[0][1].inputs else 1
            init_val = max(1, min(8, init_val))
            if not eye_sock:
                if hasattr(tree, 'interface'):
                    eye_sock = tree.interface.new_socket(
                        name=sock_name, in_out='OUTPUT', socket_type='NodeSocketInt'
                    )
                else:
                    eye_sock = tree.outputs.new('NodeSocketInt', sock_name)
                eye_sock.min_value = 1
                eye_sock.max_value = 8
                eye_sock.default_value = init_val
                if sock_name in output.inputs:
                    output.inputs[sock_name].default_value = init_val
            else:
                eye_sock.min_value = 1
                eye_sock.max_value = 8
            for mat, grp_node in side_nodes:
                nt = mat.node_tree
                global_node = next((n for n in nt.nodes if n.type == 'GROUP' and n.node_tree == tree), None)
                if not global_node or sock_name not in global_node.outputs or 'Eye Type' not in grp_node.inputs:
                    continue
                source = global_node.outputs[sock_name]
                target = grp_node.inputs['Eye Type']
                if not any(link.from_socket == source for link in target.links):
                    nt.links.new(source, target)

    tree['_hi3_character_settings_ready'] = True
    tree['_hi3_eye_settings_ready'] = True
    return output


def _ready_output(arm, materials):
    nodes = _global_nodes(materials)
    if not nodes or any(n.node_tree.get('_owner_armature') != arm.name
                        or not n.node_tree.get('_hi3_character_settings_ready')
                        or not n.node_tree.get('_hi3_settings_defaults_v2') for n in nodes):
        return None
    tree = nodes[0].node_tree
    if not tree.get('_hi3_eye_settings_ready'):
        return None
    return tree.nodes['Global Properties']


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


def _draw_physics(layout, context):
    box_physics = layout.box()
    box_physics.label(text='Hair & Clothes Physics', icon='PHYSICS')
    col_physics = box_physics.column(align=True)
    from setup_wizard.character_rig_setup.rig_ui_utils import has_hair_clothes_physics
    if has_hair_clothes_physics(context):
        col_physics.prop(context.scene, 'gi_hair_physics_influence', text='Hair Physics', slider=True)
        col_physics.prop(context.scene, 'gi_clothes_physics_influence', text='Clothes Physics', slider=True)
        box_physics.column(align=True).operator('hoyoverse.remove_hair_clothes_physics', text='Remove Physics', icon='PANEL_CLOSE')
    else:
        col_physics.operator('hoyoverse.apply_hair_clothes_physics', text='Apply Physics', icon='FILE_REFRESH')


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
            _draw_physics(layout, context)
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
        draw_lights_plus(layout, context)

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
        left_eye = output.inputs.get('Left Eye Type')
        right_eye = output.inputs.get('Right Eye Type')
        if blush or left_eye or right_eye:
            face = layout.box()
            face.label(text='Face', icon='USER')
            face_col = face.column(align=True)
            if blush:
                face_col.prop(blush, 'default_value', text='Exp Blush Intensity', slider=True)
            if left_eye:
                face_col.prop(left_eye, 'default_value', text='Left Eye Type', slider=True)
            if right_eye:
                face_col.prop(right_eye, 'default_value', text='Right Eye Type', slider=True)
        _draw_physics(layout, context)


def unregister_pending():
    global _pending
    if bpy.app.timers.is_registered(_prepare_selected):
        bpy.app.timers.unregister(_prepare_selected)
    _pending = False
