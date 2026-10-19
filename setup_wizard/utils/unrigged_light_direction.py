"""Keep the shader's direction control usable without generating a rig."""
import bpy
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property


LIGHT_DIRECTION_GAMES = {
    'GENSHIN_IMPACT', 'HONKAI_STAR_RAIL', 'ZENLESS_ZONE_ZERO',
    'WUTHERING_WAVES', 'PUNISHING_GRAY_RAVEN', 'HONKAI_IMPACT_3RD',
}
# NTE deliberately removes this control; Endfield uses Sun, and HNA's
# outline-only geometry setup does not expose a Light Vectors direction input.


def setup_unrigged_light_direction(context, game_type, target_object=None):
    from setup_wizard.genshin_import_character_model import is_rigging_disabled

    if game_type not in LIGHT_DIRECTION_GAMES or not is_rigging_disabled(context):
        return None
    active = context.view_layer.objects.active
    selected = [obj for obj in context.selected_objects if obj.type in {'ARMATURE', 'MESH'}]
    target = target_object or (active if active in selected else next(iter(selected), None))
    if target is None and active and active.get('_setup_wizard_model_id'):
        target = active
    if target is None:
        return None
    model_id = target.get('_setup_wizard_model_id')
    armature = target if target.type == 'ARMATURE' else target.find_armature()
    owner = armature or target
    model_id = model_id or owner.get('_setup_wizard_model_id')
    meshes = [obj for obj in context.scene.objects if obj.type == 'MESH' and (
        obj == target or (armature and obj.find_armature() == armature)
        or (model_id and obj.get('_setup_wizard_model_id') == model_id))]
    sockets = []
    for mesh in meshes:
        for modifier in mesh.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            if not any(word in modifier.node_group.name.lower() for word in ('light vectors', 'light vector', '灯光矢量')):
                continue
            for item in modifier.node_group.interface.items_tree:
                if (item.item_type == 'SOCKET' and item.in_out == 'INPUT'
                        and item.socket_type == 'NodeSocketObject'
                        and (item.name.lower() in {'light direction', 'main light direction', '光照方向'}
                             or item.identifier == 'Input_3')):
                    sockets.append((modifier, item.identifier))
    if not sockets:
        return None

    light = next((get_modifier_property(modifier, key) for modifier, key in sockets
                  if isinstance(get_modifier_property(modifier, key), bpy.types.Object)), None)
    light = light or bpy.data.objects.get(f'Light Direction_{owner.name}') or bpy.data.objects.get('Light Direction')
    # A previous character may still use the unsuffixed template object.
    # Give this character its own control before changing visibility or links.
    if light and any(
        obj not in meshes and obj.type == 'MESH' and any(
            mod.type == 'NODES' and mod.node_group and any(
                item.item_type == 'SOCKET' and item.in_out == 'INPUT'
                and item.socket_type == 'NodeSocketObject'
                and get_modifier_property(mod, item.identifier) == light
                for item in mod.node_group.interface.items_tree)
            for mod in obj.modifiers)
        for obj in context.scene.objects
    ):
        light = light.copy()
        light.animation_data_clear()
    if light is None:
        light = bpy.data.objects.new('Light Direction', None)
        light.location = (0.0, -2.0, 1.5)
    light.name = f'Light Direction_{owner.name}'
    if light.parent:
        matrix = light.matrix_world.copy()
        light.parent = None
        light.matrix_world = matrix
    light.empty_display_type = 'SINGLE_ARROW'
    light.empty_display_size = 0.5
    destination = next((coll for coll in owner.users_collection
                        if not any(word in coll.name.lower() for word in ('wgt', 'widget'))), context.scene.collection)
    if light.name not in destination.objects:
        destination.objects.link(light)
    for coll in list(light.users_collection):
        if coll != destination:
            coll.objects.unlink(light)
    light.hide_viewport = False
    light.hide_select = False
    light.hide_render = True
    light.hide_set(False)
    for modifier, key in sockets:
        set_modifier_property(modifier, key, light)
        modifier.id_data.update_tag()
    return light
