"""Genshin weapon template texture isolation and Unity property mapping."""


def localize_weapon_texture_groups(material):
    # Copies must own image-bearing groups so another weapon cannot replace
    # this weapon's matcap or specular ramp. Lighting groups remain shared.
    memo = {}

    def clone(tree):
        if tree in memo:
            return memo[tree]
        memo[tree] = tree
        replacements = {}
        has_images = any(node.type == 'TEX_IMAGE' for node in tree.nodes)
        for node in tree.nodes:
            if node.type == 'GROUP' and node.node_tree:
                local = clone(node.node_tree)
                if local != node.node_tree:
                    replacements[node.name] = local
        if has_images or replacements:
            local = tree.copy()
            for name, child in replacements.items():
                local.nodes[name].node_tree = child
            memo[tree] = local
        return memo[tree]

    for node in material.node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            node.node_tree = clone(node.node_tree)


def iter_shader_image_nodes(tree, seen=None):
    seen = set() if seen is None else seen
    if tree in seen:
        return
    seen.add(tree)
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE':
            yield node
        elif node.type == 'GROUP' and node.node_tree:
            yield from iter_shader_image_nodes(node.node_tree, seen)


def apply_weapon_properties(material, node, colors, floats):
    from setup_wizard.material_data_import_setup.material_data_applier import V3_MaterialDataApplier

    def set_value(name, value):
        socket = node.inputs.get(name)
        if socket is not None and not socket.is_linked:
            socket.default_value = value

    # Use the existing Genshin JSON-to-socket mapping for this V3 weapon group.
    mapping = {**V3_MaterialDataApplier.local_material_mapping,
               **V3_MaterialDataApplier.additional_local_material_mapping}
    for key, name in mapping.items():
        value = colors.get(key) if key in colors else floats.get(key)
        if value is not None:
            set_value(name, value)
    set_value('Enable Metallics?', floats.get('_MetalMaterial', 0.0))

    original = material.get('_original_material_name', material.name).lower()
    transparent = '_trans' in original or floats.get('_SrcBlendMode') == 5
    alpha_test = any(floats.get(key, 0) == 1 for key in
                     ('_UseAlphaTest', '_UseAlphaClip', '_EnableAlphaTest', '_AlphaClip'))
    alpha_mode = int(floats.get('_MainTexAlphaUse', 0))
    opaque = (floats.get('_Mode') == 0
              or (floats.get('_SrcBlend') == 1 and floats.get('_DstBlend') == 0))
    emission = alpha_mode == 2 or floats.get('_UseMainTexAlphaEmission') == 1
    alpha = transparent or alpha_test or (alpha_mode == 1 and not opaque) or emission
    set_value('Use Alpha', float(alpha))
    set_value('0 = Emission, 1 = Transparency', 0.0 if emission else 1.0)
    set_value('Transparency Cutoff', floats.get('_MainTexAlphaCutoff', floats.get('_Cutoff', .5)))
    if not emission:
        set_value('Emission Strength', 0.0)
    if hasattr(material, 'surface_render_method'):
        material.surface_render_method = 'BLENDED' if transparent else 'DITHERED'
    elif hasattr(material, 'blend_method'):
        material.blend_method = 'BLEND' if transparent else 'HASHED'


def import_weapon_textures(material, directory):
    import json
    from pathlib import Path
    import bpy

    root = Path(directory)
    if root.name.lower() in {'textures', 'texture', 'texture2d'}:
        root = root.parent
    source = material.get('_original_material_name')
    json_path = root / 'Materials' / (source + '.json')
    if not json_path.is_file():
        return
    saved = json.loads(json_path.read_text(encoding='utf-8')).get('m_SavedProperties', {})
    environments = saved.get('m_TexEnvs') or {}
    files = {path.stem.lower(): path for path in root.rglob('*')
             if path.suffix.lower() in {'.png', '.dds', '.tga', '.jpg', '.jpeg'}
             and not path.name.startswith('._')}
    for node in iter_shader_image_nodes(material.node_tree):
        key = node.get('_genshin_texture_property')
        if not key:
            continue
        name = environments.get(key, {}).get('m_Texture', {}).get('Name')
        if not name:
            node.image = None
            continue
        path = files.get(Path(name).stem.lower())
        if path is None:
            raise RuntimeError('Missing Genshin weapon texture: ' + name)
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = 'sRGB' if key in {'_MainTex', '_MTMap'} else 'Non-Color'
        image.alpha_mode = 'CHANNEL_PACKED'
        node.image = image
    shader = material.node_tree.nodes.get('Body Shader')
    if shader and 'Use Specular Ramp' in shader.inputs:
        shader.inputs['Use Specular Ramp'].default_value = float(any(
            node.get('_genshin_texture_property') == '_MTSpecularRamp' and node.image is not None
            for node in iter_shader_image_nodes(material.node_tree)))
