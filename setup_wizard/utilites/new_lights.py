"""Blender 5.3 light shaders scoped to the selected character."""
import json
from pathlib import Path

import bpy
from bpy.props import EnumProperty
from bpy.types import Operator, Panel

from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property

TAG = '_gacha_lights_plus'
MODE = '_gacha_lights_plus_mode'
VERSION = '_gacha_lights_plus_version'
COLOR_VERSION = '_gacha_lights_plus_color_version'
CURRENT_COLOR_VERSION = 4


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


def is_color_wheel(value):
    names = [value.name, str(value.get('_original_material_name', ''))]
    tree = getattr(value, 'node_tree', None)
    if tree:
        names.extend(n.node_tree.name for n in tree.nodes if n.type == 'GROUP' and n.node_tree)
    return any('colorwheel' in ''.join(c for c in name.lower() if c.isalnum()) for name in names)


def is_eye_specular(material):
    names = [material.name, str(material.get('_original_material_name', ''))]
    if material.node_tree:
        names.extend(n.node_tree.name for n in material.node_tree.nodes
                     if n.type == 'GROUP' and n.node_tree)
    compact = ''.join(c for c in ' '.join(names).lower() if c.isalnum())
    return 'eyespecular' in compact


def excluded_materials(objects, owner):
    materials = {m for obj in objects for m in object_materials(obj)}
    wheels = {m for obj in objects if is_color_wheel(obj) for m in object_materials(obj)}
    return wheels | {
        m for m in materials
        if is_color_wheel(m) or is_genshin_highlight(m, owner) or is_eye_specular(m)
    }


def is_light_node(node):
    if node.type != 'GROUP' or node.node_tree is None:
        return False
    return bool(node.get(TAG) or node.node_tree.get(VERSION) or (
        node.node_tree.name.startswith('New Light Type')
        and node.inputs.get('Index') is not None and node.inputs.get('Shader') is not None
        and node.outputs.get('Shader') is not None))


_HAS_SETUP_CACHE = {}
_NEEDS_SETUP_CACHE = {}


def _lights_cache_key(owner):
    return (
        owner.as_pointer(),
        len(bpy.data.objects),
        len(bpy.data.materials),
        bool(owner.get(TAG)),
    )


def _clear_lights_cache():
    _HAS_SETUP_CACHE.clear()
    _NEEDS_SETUP_CACHE.clear()


def has_setup(owner):
    key = _lights_cache_key(owner)
    if key in _HAS_SETUP_CACHE:
        return _HAS_SETUP_CACHE[key]
    res = bool(owner.get(TAG) or any(
        material.node_tree and any(is_light_node(n) for n in material.node_tree.nodes)
        for obj in character_objects(owner) for material in object_materials(obj)))
    if len(_HAS_SETUP_CACHE) > 64:
        _HAS_SETUP_CACHE.clear()
    _HAS_SETUP_CACHE[key] = res
    return res


def localize_materials(objects, owner=None, force=False):
    """Copy shared materials and only the geometry groups that reference them."""
    materials = {m for obj in objects for m in object_materials(obj)}
    external = {m for obj in bpy.data.objects if obj not in objects for m in object_materials(obj)}
    excluded = excluded_materials(objects, owner)
    replacements = {m: m.copy() for m in materials & external
                    if force or m not in excluded
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
    if group and group.get(COLOR_VERSION) == CURRENT_COLOR_VERSION:
        return group
    path = Path(__file__).with_name('NewLights.blend')
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.node_groups = ['New Light Type']
    updated = target.node_groups[0]
    if group:
        name = group.name
        group.user_remap(updated)
        bpy.data.node_groups.remove(group)
        updated.name = name
    return updated


def _is_expression_selector(node):
    if node.type != 'GROUP' or node.node_tree is None:
        return False
    original = node.inputs.get('Original Skin')
    shader_out = node.outputs.get('Shader')
    return (
        original is not None and original.type == 'SHADER'
        and shader_out is not None and shader_out.type == 'SHADER'
        and ('expression' in node.name.lower() or 'expression' in node.node_tree.name.lower())
    )


def _target_shader_input(output):
    """Return the shader input socket where Lights+ should be inserted.

    For facial expression overlay materials, insert before the expression
    selector (into 'Original Skin') so the overlay's transparency mask stays
    intact across all lighting modes.
    """
    surface = output.inputs.get('Surface')
    if not surface or not surface.is_linked:
        return None
    src_node = surface.links[0].from_node
    if _is_expression_selector(src_node):
        original = src_node.inputs.get('Original Skin')
        if original and original.is_linked:
            return original
    return surface


def _unwrap_goo_links(tree, removed_names):
    """Collapse any gacha_goo_links entries routed through removed Lights+ nodes."""
    raw = tree.get('gacha_goo_links')
    if not raw or not removed_names:
        return
    try:
        variants = json.loads(raw)
    except (TypeError, ValueError):
        return
    changed = False
    for mode, links in variants.items():
        new_links = list(links)
        for name in removed_names:
            incoming = [l for l in new_links if l[2] == name]
            outgoing = [l for l in new_links if l[0] == name]
            if not incoming and not outgoing:
                continue
            changed = True
            new_links = [l for l in new_links if l[0] != name and l[2] != name]
            if incoming and outgoing:
                src_node, src_sock = incoming[0][0], incoming[0][1]
                for out_l in outgoing:
                    new_links.append([src_node, src_sock, out_l[2], out_l[3]])
        variants[mode] = new_links
    if changed:
        tree['gacha_goo_links'] = json.dumps(variants)


def _wrap_goo_links(tree, source_socket, light_node, target_socket):
    """Keep gacha_goo_links portable paths routed through the installed Lights+ node."""
    raw = tree.get('gacha_goo_links')
    if not raw:
        return
    try:
        variants = json.loads(raw)
    except (TypeError, ValueError):
        return
    src_sig = (source_socket.node.name, source_socket.identifier)
    dst_sig = (target_socket.node.name, target_socket.identifier)
    in_sig = (light_node.name, light_node.inputs['Shader'].identifier)
    out_sig = (light_node.name, light_node.outputs['Shader'].identifier)
    changed = False
    for mode, links in variants.items():
        updated = []
        for l in links:
            if (l[0], l[1]) == src_sig and (l[2], l[3]) == dst_sig:
                updated.append([src_sig[0], src_sig[1], in_sig[0], in_sig[1]])
                updated.append([out_sig[0], out_sig[1], dst_sig[0], dst_sig[1]])
                changed = True
            else:
                updated.append(l)
        variants[mode] = updated
    if changed:
        tree['gacha_goo_links'] = json.dumps(variants)


def setup_material(material, owner, group, exclusions=None):
    if material.is_grease_pencil:
        return 0
    excluded = material in (exclusions if exclusions is not None
                            else excluded_materials(character_objects(owner), owner))
    if not excluded:
        material.use_nodes = True
    tree = material.node_tree
    if tree is None:
        return 0
    # Bypass the previous Lights+ nodes first, so repeated setup stays at the
    # very end even if the user has added another effect after the previous one.
    removed_names = []
    for node in list(tree.nodes):
        if not is_light_node(node):
            continue
        removed_names.append(node.name)
        shader = node.inputs.get('Shader')
        source = shader.links[0].from_socket if shader and shader.is_linked else None
        if source:
            for output in node.outputs:
                for link in list(output.links):
                    tree.links.new(source, link.to_socket)
        tree.nodes.remove(node)
    if removed_names:
        _unwrap_goo_links(tree, removed_names)
    if excluded:
        tree.update_tag()
        material.update_tag()
        return 0
    count = 0
    for output in list(tree.nodes):
        if output.type != 'OUTPUT_MATERIAL':
            continue
        target_socket = _target_shader_input(output)
        if not target_socket or not target_socket.is_linked:
            continue
        source = target_socket.links[0].from_socket
        node = tree.nodes.new('ShaderNodeGroup')
        node.node_tree = group
        node[TAG] = True
        anchor = target_socket.node
        node.location = (anchor.location.x - 220, anchor.location.y)
        node.width = 200
        tree.links.new(source, node.inputs['Shader'])
        tree.links.new(node.outputs['Shader'], target_socket)
        _wrap_goo_links(tree, source, node, target_socket)
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
    if has_setup(self):
        # Store the selected mode in the materials too: it survives saving and
        # Append without depending on evaluation of unused GN material drivers.
        objects = character_objects(self)
        materials = localize_materials(objects, self)
        excluded = excluded_materials(objects, self)
        for material in materials:
            if not material.node_tree or material in excluded:
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
        # A wheel can share a generic material with a character mesh. Isolate
        # its copy first so restoring the wheel cannot strip the body's effect.
        wheels = {obj for obj in objects if is_color_wheel(obj)}
        if wheels:
            localize_materials(wheels, owner, force=True)
        materials = localize_materials(objects, owner)
        excluded = excluded_materials(objects, owner)
        count = sum(bool(setup_material(m, owner, group, excluded)) for m in materials)
        owner[TAG] = True
        _clear_lights_cache()
        self.report({'INFO'}, f'Lights+ configured on {count} character materials')
        return {'FINISHED'}


def needs_setup(owner):
    """Inspect the current outputs, including newly added modifier materials."""
    key = _lights_cache_key(owner)
    if key in _NEEDS_SETUP_CACHE:
        return _NEEDS_SETUP_CACHE[key]
    res = _needs_setup_uncached(owner)
    if len(_NEEDS_SETUP_CACHE) > 64:
        _NEEDS_SETUP_CACHE.clear()
    _NEEDS_SETUP_CACHE[key] = res
    return res


def _needs_setup_uncached(owner):
    """Inspect the current outputs, including newly added modifier materials."""
    objects = character_objects(owner)
    materials = {m for obj in objects for m in object_materials(obj)}
    excluded = excluded_materials(objects, owner)
    for material in materials:
        if material.is_grease_pencil:
            continue
        if material in excluded:
            if material.node_tree and any(is_light_node(n) for n in material.node_tree.nodes):
                return True  # Offer setup once to remove the previous wrapper.
            continue
        if not material.node_tree:
            return True
        for output in material.node_tree.nodes:
            if output.type != 'OUTPUT_MATERIAL':
                continue
            target_socket = _target_shader_input(output)
            if not target_socket or not target_socket.is_linked:
                continue
            node = target_socket.links[0].from_node
            if not (node.type == 'GROUP' and node.node_tree and is_light_node(node)
                    and node.node_tree.get(COLOR_VERSION) == CURRENT_COLOR_VERSION
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
    installed = has_setup(owner)
    if needs_setup(owner):
        text = 'Update Lights+' if installed else 'Setup New Lights'
        box.operator('gacha.setup_new_lights', text=text, icon='LIGHT_SUN')
    if installed:
        box.prop(owner, 'gacha_lights_plus_mode', text='Mode')


def register():
    bpy.types.Object.gacha_lights_plus_mode = EnumProperty(
        name='Mode', items=[('DEFAULT', 'Default', '', 0),
                                 ('LIGHT_COLOR', 'Light Color', '', 1),
                                 ('DIFFUSE', 'Diffuse', '', 2)],
        get=get_mode, set=set_mode,
    )
    bpy.utils.register_class(GACHA_OT_SetupNewLights)


def unregister():
    bpy.utils.unregister_class(GACHA_OT_SetupNewLights)
    del bpy.types.Object.gacha_lights_plus_mode
