"""Element presets authored in Genshin equipment material JSONs."""

import json
from functools import lru_cache
from pathlib import Path

import bpy

PRESETS_KEY = '_genshin_weapon_elements'
SELECTION_KEY = '_genshin_weapon_element'
ELEMENTS = (
    ('Wind', 'Anemo'), ('Rock', 'Geo'), ('Electric', 'Electro'),
    ('Grass', 'Dendro'), ('Water', 'Hydro'), ('Fire', 'Pyro'), ('Ice', 'Cryo'),
)
_ITEMS = tuple((key, label, 'Apply the authored ' + label + ' materials', i)
               for i, (key, label) in enumerate(ELEMENTS, 1))
_ITEM_SETS = {}


@lru_cache(maxsize=64)
def _decode(serialized):
    return json.loads(serialized)


def capture_element_presets(material, directory):
    """Embed matching families and texture IDs so switching needs no source files."""
    source = material.get('_original_material_name', '')
    family, _, current = source.rpartition('_')
    if not material.get('_genshin_equipment') or current not in dict(ELEMENTS):
        return
    root = Path(directory)
    if root.name.lower() in {'textures', 'texture', 'texture2d', 'materials'}:
        root = root.parent
    paths = {key: root / 'Materials' / (family + '_' + key + '.json') for key, _ in ELEMENTS}
    paths = {key: path for key, path in paths.items() if path.is_file()}
    if len(paths) < 2:
        return
    files = {p.stem.lower(): p for p in root.rglob('*')
             if p.suffix.lower() in {'.png', '.dds', '.tga', '.jpg', '.jpeg', '.hdr', '.exr'}
             and not p.name.startswith('._')}
    from setup_wizard.utils.genshin_weapon_material_utils import iter_shader_image_nodes
    used_textures = {n.get('_genshin_texture_property')
                     for n in iter_shader_image_nodes(material.node_tree)}
    used_textures.add('_MaterialMasksTex')
    presets = {}
    for element, path in paths.items():
        saved = json.loads(path.read_text(encoding='utf-8-sig'))['m_SavedProperties']
        textures = {}
        for key, env in saved.get('m_TexEnvs', {}).items():
            if key not in used_textures:
                continue
            name = env.get('m_Texture', {}).get('Name')
            if not name:
                textures[key] = None
                continue
            image_path = files.get(Path(name).stem.lower())
            if image_path is None:
                raise RuntimeError('Missing Genshin weapon element texture: ' + name)
            image = bpy.data.images.load(str(image_path), check_existing=True)
            image.colorspace_settings.name = 'sRGB' if key in {'_MainTex', '_MTMap'} else 'Non-Color'
            image.alpha_mode = 'CHANNEL_PACKED'
            # ID pointers survive renames, save/reopen and Append with name collisions.
            image_key = '_gi_element_image_' + element + key
            material[image_key] = image
            textures[key] = image_key
        presets[element] = {'saved': saved, 'textures': textures}
    material[PRESETS_KEY] = json.dumps(presets, separators=(',', ':'))
    material[SELECTION_KEY] = current


def weapon_meshes(owner):
    objects = [owner, *owner.children_recursive] if owner else []
    # A detached duplicate may still carry the original Armature modifier.
    # Prefer the real hierarchy so it cannot become another weapon's master.
    has_equipment = any(o.type == 'MESH' and any(
        s.material and s.material.get('_genshin_equipment') for s in o.material_slots)
        for o in objects)
    if owner and owner.type == 'ARMATURE' and not has_equipment:
        objects.extend(o for o in bpy.context.scene.objects
                       if o.type == 'MESH' and o.find_armature() == owner)
    return set(o for o in objects if o.type == 'MESH')


def weapon_materials(owner):
    return {s.material for o in weapon_meshes(owner) for s in o.material_slots
            if s.material and s.material.get(PRESETS_KEY)}


def find_weapon_outline(material, meshes=None):
    """Resolve the material actually used by Geometry Nodes, including long names."""
    from setup_wizard.utils.modifier_utils import get_modifier_property
    for mesh in meshes if meshes is not None else bpy.data.objects:
        if mesh.type != 'MESH':
            continue
        for modifier in mesh.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            sockets = {s.name: s for s in modifier.node_group.interface.items_tree
                       if s.item_type == 'SOCKET' and s.in_out == 'INPUT'
                       and s.socket_type == 'NodeSocketMaterial'}
            for name, socket in sockets.items():
                if get_modifier_property(modifier, socket.identifier) != material:
                    continue
                pair = sockets.get(name + ' Outline') or sockets.get(name + ' Outlines')
                if pair:
                    return get_modifier_property(modifier, pair.identifier)
    return None


def settings_target(context):
    obj = context.active_object or context.object
    if obj is None:
        return None

    def equipment_only(owner):
        return all(not slot.material or slot.material.get('_genshin_equipment')
                   for mesh in weapon_meshes(owner) for slot in mesh.material_slots)

    # Prefer the selected weapon over an unrelated character elsewhere in the scene.
    if obj.type == 'MESH' and weapon_materials(obj):
        arm = obj.find_armature()
        return arm if arm and obj in weapon_meshes(arm) and equipment_only(arm) else obj
    return obj if weapon_materials(obj) and equipment_only(obj) else None


def element_items(self, context):
    materials = weapon_materials(self)
    keys = tuple(item[0] for item in _ITEMS if materials and all(
        item[0] in _decode(m[PRESETS_KEY]) for m in materials))
    # Blender retains references to dynamic enum strings.
    if keys not in _ITEM_SETS:
        _ITEM_SETS[keys] = tuple(item for item in _ITEMS if item[0] in keys)
    return _ITEM_SETS[keys]


def get_element(self):
    materials = weapon_materials(self)
    current = self.get(SELECTION_KEY)
    if current is None and materials:
        current = next(iter(materials)).get(SELECTION_KEY)
    return next((item[3] for item in _ITEMS if item[0] == current), 1)


def _localize_shared_materials(owner):
    from setup_wizard.utils.genshin_weapon_material_utils import localize_weapon_texture_groups
    from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property
    meshes = weapon_meshes(owner)
    replacements = {}
    for material in weapon_materials(owner):
        if not any(o.type == 'MESH' and o not in meshes and any(
                s.material == material for s in o.material_slots) for o in bpy.data.objects):
            continue
        local = material.copy()
        localize_weapon_texture_groups(local)
        replacements[material] = local
        outline = local.get('_gi_element_outline')
        if outline:
            if outline not in replacements:
                replacements[outline] = outline.copy()
            local_outline = replacements[outline]
            local['_gi_element_outline'] = local_outline
        for obj in meshes:
            for slot in obj.material_slots:
                if slot.material == material:
                    # Object links keep linked mesh duplicates independent.
                    slot.link = 'OBJECT'
                    slot.material = local
    if not replacements:
        return

    memo = {}

    def remap_group(tree):
        if tree in memo:
            return memo[tree]
        memo[tree] = tree
        children = {n.name: remap_group(n.node_tree) for n in tree.nodes
                    if n.type == 'GROUP' and n.node_tree}
        changes = [(n.name, i, replacements[s.default_value])
                   for n in tree.nodes for i, s in enumerate(n.inputs)
                   if not s.is_linked and s.type == 'MATERIAL'
                   and s.default_value in replacements]
        if changes or any(tree.nodes[k].node_tree != v for k, v in children.items()):
            local = tree.copy()
            for name, child in children.items():
                local.nodes[name].node_tree = child
            for name, index, material in changes:
                local.nodes[name].inputs[index].default_value = material
            memo[tree] = local
        return memo[tree]

    for obj in meshes:
        for slot in obj.material_slots:
            if slot.material in replacements:
                replacement = replacements[slot.material]
                slot.link = 'OBJECT'
                slot.material = replacement
        for modifier in obj.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            for item in modifier.node_group.interface.items_tree:
                if item.item_type != 'SOCKET' or item.in_out != 'INPUT' or item.socket_type != 'NodeSocketMaterial':
                    continue
                value = get_modifier_property(modifier, item.identifier)
                if isinstance(value, bpy.types.Material) and value in replacements:
                    set_modifier_property(modifier, item.identifier, replacements[value])
            modifier.node_group = remap_group(modifier.node_group)


def set_element(self, value):
    from setup_wizard.domain.outline_material_data import OutlineMaterialGroup
    from setup_wizard.parsers.material_data_json_parsers import HoyoStudioMaterialDataJsonParser
    from setup_wizard.material_data_import_setup.material_data_applier import GenshinWeaponMaterialDataApplier
    from setup_wizard.utils.genshin_weapon_material_utils import apply_weapon_properties, iter_shader_image_nodes

    element = next(item[0] for item in _ITEMS if item[3] == value)
    materials = weapon_materials(self)
    if not materials or any(element not in _decode(m[PRESETS_KEY]) for m in materials):
        raise ValueError('Element is not available for every material of this weapon')
    meshes = weapon_meshes(self)
    for material in materials:
        outline = find_weapon_outline(material, meshes)
        if outline:
            material['_gi_element_outline'] = outline
        elif '_gi_element_outline' in material:
            del material['_gi_element_outline']
    _localize_shared_materials(self)
    for material in weapon_materials(self):
        preset = _decode(material[PRESETS_KEY])[element]
        material[SELECTION_KEY] = element
        parser = HoyoStudioMaterialDataJsonParser({'m_SavedProperties': preset['saved']})
        parser.parse()
        outline = material.get('_gi_element_outline')
        applier = GenshinWeaponMaterialDataApplier(parser, OutlineMaterialGroup(material, outline))
        shader = material.node_tree.nodes.get('Body Shader')
        if shader:
            # Do not rewrite shared Global Properties or the user's lighting mode.
            applier.set_up_mesh_material_data_with_tooltips(shader, shader)
            apply_weapon_properties(material, shader, vars(parser.m_colors), vars(parser.m_floats))
        if outline and outline.node_tree:
            node = outline.node_tree.nodes.get(applier.outlines_node_tree_node_name)
            if node:
                if applier._has_json_outline_colors():
                    applier._clear_diffuse_outline_color_fallback(node)
                applier.set_up_mesh_material_data_with_tooltips(node, node, is_outlines=True)
        for node in iter_shader_image_nodes(material.node_tree):
            key = node.get('_genshin_texture_property')
            if key in preset['textures']:
                image_key = preset['textures'][key]
                node.image = material.get(image_key) if image_key else None
        material[SELECTION_KEY] = element
    self[SELECTION_KEY] = element
    sync_weapon_sheathe(self)


def sync_weapon_sheathe(owner):
    """One Sheathe control hides the body, transparent parts and real outlines."""
    from setup_wizard.utils.genshin_weapon_material_utils import link_weapon_sheathe
    materials = weapon_materials(owner)
    master = next((m for m in materials if '_trans' not in m.get('_original_material_name', '').lower()),
                  next(iter(materials), None))
    if master:
        link_weapon_sheathe(master, materials)


def register():
    bpy.types.Object.gi_weapon_element = bpy.props.EnumProperty(
        name='Element', description='Element variants supplied by the weapon materials',
        items=element_items, get=get_element, set=set_element,
    )


def unregister():
    if hasattr(bpy.types.Object, 'gi_weapon_element'):
        del bpy.types.Object.gi_weapon_element
