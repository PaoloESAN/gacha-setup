"""Blender 5.3 light shaders scoped to the selected character."""
from pathlib import Path

import bpy
from bpy.props import EnumProperty
from bpy.types import Operator, Panel

from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property

TAG = '_gacha_lights_plus'
MODE = '_gacha_lights_plus_mode'
VERSION = '_gacha_lights_plus_version'


def supported():
    return bpy.app.version[:2] == (5, 3)


def selected_owner(context):
    obj = context.active_object
    if obj is None or obj.type in {'LIGHT', 'CAMERA'}:
        return None
    if obj.type == 'ARMATURE':
        return obj
    arm = obj.find_armature() if hasattr(obj, 'find_armature') else None
    if arm:
        return arm
    parent = obj.parent
    while parent:
        if parent.type == 'ARMATURE':
            return parent
        parent = parent.parent
    return obj if hasattr(obj, 'material_slots') else None


def character_objects(owner):
    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes_uncached
    return set(_iter_rig_meshes_uncached(owner)) | {
        obj for obj in (owner, *owner.children_recursive) if hasattr(obj, 'material_slots')
    }


def group_materials(tree, visited=None):
    visited = visited if visited is not None else set()
    if tree in visited:
        return set()
    visited.add(tree)
    materials = set()
    for item in tree.interface.items_tree:
        value = getattr(item, 'default_value', None)
        if isinstance(value, bpy.types.Material):
            materials.add(value)
    for node in tree.nodes:
        value = getattr(node, 'material', None)
        if isinstance(value, bpy.types.Material):
            materials.add(value)
        for socket in node.inputs:
            value = getattr(socket, 'default_value', None)
            if isinstance(value, bpy.types.Material):
                materials.add(value)
        if node.type == 'GROUP' and node.node_tree:
            materials.update(group_materials(node.node_tree, visited))
    return materials


def object_materials(obj):
    materials = {s.material for s in getattr(obj, 'material_slots', ()) if s.material}
    for modifier in obj.modifiers:
        if modifier.type != 'NODES' or not modifier.node_group:
            continue
        materials.update(group_materials(modifier.node_group))
        for item in modifier.node_group.interface.items_tree:
            if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.socket_type == 'NodeSocketMaterial':
                value = get_modifier_property(modifier, item.identifier)
                if isinstance(value, bpy.types.Material):
                    materials.add(value)
    return materials


def is_genshin_highlight(material, owner=None):
    names = [material.name, str(material.get('_original_material_name', ''))]
    if material.node_tree:
        names.extend(n.node_tree.name for n in material.node_tree.nodes
                     if n.type == 'GROUP' and n.node_tree)
    names = ' '.join(names).lower()
    if 'highlight' not in names:
        return False
    if 'genshin' in names or 'primotoon' in names:
        return True
    if owner is not None:
        from setup_wizard.ui.character_settings_utils import detect_armature_game
        game = detect_armature_game(owner)
        if game is not None:
            return game == 'GENSHIN_IMPACT'
    return material.name.lower().startswith(('hoyoverse - ', 'mihoyo - '))


def is_light_node(node):
    return bool(node.get(TAG) or (node.type == 'GROUP' and node.node_tree
                                and node.node_tree.get(VERSION) == 1))


def localize_materials(objects, owner=None):
    """Copy shared materials and only the geometry groups that reference them."""
    materials = {m for obj in objects for m in object_materials(obj)}
    external = {m for obj in bpy.data.objects if obj not in objects for m in object_materials(obj)}
    replacements = {m: m.copy() for m in materials & external
                    if not is_genshin_highlight(m, owner)
                    or (m.node_tree and any(is_light_node(n) for n in m.node_tree.nodes))}
    if not replacements:
        return materials
    memo = {}

    def remap(tree):
        if tree in memo:
            return memo[tree]
        memo[tree] = tree
        children = {n.name: remap(n.node_tree) for n in tree.nodes if n.type == 'GROUP' and n.node_tree}
        if not (group_materials(tree) & replacements.keys()):
            return tree
        local = tree.copy()
        memo[tree] = local
        for item in local.interface.items_tree:
            value = getattr(item, 'default_value', None)
            if isinstance(value, bpy.types.Material) and value in replacements:
                item.default_value = replacements[value]
        for node in local.nodes:
            if node.name in children:
                node.node_tree = children[node.name]
            value = getattr(node, 'material', None)
            if isinstance(value, bpy.types.Material) and value in replacements:
                node.material = replacements[value]
            for socket in node.inputs:
                value = getattr(socket, 'default_value', None)
                if isinstance(value, bpy.types.Material) and value in replacements:
                    socket.default_value = replacements[value]
        return local

    for obj in objects:
        for slot in obj.material_slots:
            if slot.material in replacements:
                value = replacements[slot.material]
                slot.link = 'OBJECT'
                slot.material = value
        for modifier in obj.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            values = {}
            for item in modifier.node_group.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.socket_type == 'NodeSocketMaterial':
                    value = get_modifier_property(modifier, item.identifier)
                    if isinstance(value, bpy.types.Material) and value in replacements:
                        values[item.identifier] = replacements[value]
            modifier.node_group = remap(modifier.node_group)
            for identifier, value in values.items():
                set_modifier_property(modifier, identifier, value)
    return {replacements.get(m, m) for m in materials}


def light_group():
    group = next((g for g in bpy.data.node_groups if g.get(VERSION) == 1), None)
    if group:
        return group
    path = Path(__file__).with_name('NewLights.blend')
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.node_groups = ['New Light Type']
    return target.node_groups[0]


def setup_material(material, owner, group):
    excluded = is_genshin_highlight(material, owner)
    if not excluded:
        material.use_nodes = True
    tree = material.node_tree
    if tree is None:
        return 0
    # Bypass the previous Lights+ nodes first, so repeated setup stays at the
    # very end even if the user has added another effect after the previous one.
    for node in list(tree.nodes):
        if not is_light_node(node):
            continue
        shader = node.inputs.get('Shader')
        source = shader.links[0].from_socket if shader and shader.is_linked else None
        if source:
            for output in node.outputs:
                for link in list(output.links):
                    tree.links.new(source, link.to_socket)
        tree.nodes.remove(node)
    if excluded:
        tree.update_tag()
        material.update_tag()
        return 0
    count = 0
    for output in list(tree.nodes):
        if output.type != 'OUTPUT_MATERIAL':
            continue
        surface = output.inputs.get('Surface')
        if not surface or not surface.is_linked:
            continue
        source = surface.links[0].from_socket
        node = tree.nodes.new('ShaderNodeGroup')
        node.node_tree = group
        node.name = node.label = 'Lights+'
        node[TAG] = True
        node.location = (output.location.x - 220, output.location.y)
        node.width = 200
        tree.links.new(source, node.inputs['Shader'])
        tree.links.new(node.outputs['Shader'], surface)
        for socket in node.inputs:
            if socket.name != 'Shader':
                socket.hide = True
        node.inputs['Index'].default_value = int(owner.get(MODE, 0))
        count += 1
    tree.update_tag()
    material.update_tag()
    return count


def get_mode(self):
    return int(self.get(MODE, 0))


def set_mode(self, value):
    self[MODE] = int(value)
    if self.get(TAG):
        # Store the selected mode in the materials too: it survives saving and
        # Append without depending on evaluation of unused GN material drivers.
        for material in localize_materials(character_objects(self), self):
            if not material.node_tree or is_genshin_highlight(material, self):
                continue
            for node in material.node_tree.nodes:
                if node.get(TAG):
                    node.inputs['Index'].default_value = int(value)
            material.node_tree.update_tag()
    self.update_tag()


class GACHA_OT_SetupNewLights(Operator):
    """Add Lights+ after the final shader of every material used by the selected character"""
    bl_idname = 'gacha.setup_new_lights'
    bl_label = 'Setup New Lights'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return supported() and selected_owner(context) is not None

    def execute(self, context):
        owner = selected_owner(context)
        objects = character_objects(owner)
        if not any(object_materials(obj) for obj in objects):
            self.report({'ERROR'}, 'Selected character has no materials')
            return {'CANCELLED'}
        group = light_group()
        if MODE not in owner:
            owner[MODE] = 0
        materials = localize_materials(objects, owner)
        count = sum(bool(setup_material(m, owner, group)) for m in materials)
        owner[TAG] = True
        self.report({'INFO'}, f'Lights+ configured on {count} character materials')
        return {'FINISHED'}


def needs_setup(owner):
    """Inspect the current outputs, including newly added modifier materials."""
    materials = {m for obj in character_objects(owner) for m in object_materials(obj)}
    for material in materials:
        if is_genshin_highlight(material, owner):
            if material.node_tree and any(is_light_node(n) for n in material.node_tree.nodes):
                return True  # Offer setup once to remove the previous wrapper.
            continue
        if not material.node_tree:
            return True
        for output in material.node_tree.nodes:
            if output.type != 'OUTPUT_MATERIAL':
                continue
            surface = output.inputs.get('Surface')
            if not surface or not surface.is_linked:
                continue
            node = surface.links[0].from_node
            if not (node.type == 'GROUP' and node.node_tree
                    and node.node_tree.get(VERSION) == 1
                    and node.inputs.get('Index') and node.inputs.get('Shader')
                    and node.inputs['Shader'].is_linked):
                return True
    return False


def draw_lights_plus(layout, context):
    if not supported():
        return
    owner = selected_owner(context)
    if owner is None:
        return
    box = layout.box()
    box.label(text='Lights+', icon='LIGHT')
    if needs_setup(owner):
        box.operator('gacha.setup_new_lights', text='Setup New Lights', icon='LIGHT_SUN')
    if owner.get(TAG):
        box.prop(owner, 'gacha_lights_plus_mode', text='Mode')


class GACHA_PT_NTELightsCharacterSettings(Panel):
    """NTE has no separate Character Settings panel yet."""
    bl_label = 'Character Settings'
    bl_idname = 'GACHA_PT_NTELightsCharacterSettings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_order = 1

    @classmethod
    def poll(cls, context):
        if not supported():
            return False
        from setup_wizard.ui.character_settings_utils import is_game_armature
        return is_game_armature(context, 'NEVERNESS_TO_EVERNESS')

    def draw(self, context):
        draw_lights_plus(self.layout, context)


def register():
    bpy.types.Object.gacha_lights_plus_mode = EnumProperty(
        name='Mode', items=[('DEFAULT', 'Default', '', 0),
                                 ('LIGHT_COLOR', 'Light Color', '', 1),
                                 ('DIFFUSE', 'Diffuse', '', 2)],
        get=get_mode, set=set_mode,
    )
    bpy.utils.register_class(GACHA_OT_SetupNewLights)
    bpy.utils.register_class(GACHA_PT_NTELightsCharacterSettings)


def unregister():
    bpy.utils.unregister_class(GACHA_PT_NTELightsCharacterSettings)
    bpy.utils.unregister_class(GACHA_OT_SetupNewLights)
    del bpy.types.Object.gacha_lights_plus_mode
