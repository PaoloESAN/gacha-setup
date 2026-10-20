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
    _ensure_weapon_output(node)

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

    if material.get('_genshin_weapon_elements'):
        apply_weapon_element_colors(material, node, colors, floats)


def apply_weapon_element_colors(material, shader, colors, floats):
    """Tint the diffuse by material ID when the weapons shader lacks Color 1..5."""
    if shader.inputs.get('Color') is not None:
        return  # Shader versions exposing these colors use the mapping above.
    diffuse = shader.inputs.get('Diffuse Color')
    alpha = shader.inputs.get('Lightmap Alpha')
    if diffuse is None or alpha is None:
        return
    tree = material.node_tree
    ids = tree.nodes.get('Weapon Element Colors')
    if ids is None:
        template = next((n.node_tree for n in shader.node_tree.nodes
                         if n.type == 'GROUP' and n.node_tree
                         and 'Use Color 5' in n.inputs and 'Color 1' in n.inputs
                         and 'Lightmap Alpha' in n.inputs and 'Color' in n.outputs), None)
        if template is None:
            raise RuntimeError('The weapon shader has no material ID color selector')
        ids = tree.nodes.new('ShaderNodeGroup')
        ids.name = 'Weapon Element Colors'
        ids.label = 'Weapon Element Colors'
        ids.node_tree = template
        ids.location = (shader.location.x - 500, shader.location.y - 300)
    tint = tree.nodes.get('Weapon Element Tint')
    if tint is None:
        tint = tree.nodes.new('ShaderNodeMixRGB')
        tint.name = 'Weapon Element Tint'
        tint.label = 'Weapon Element Tint'
        tint.blend_type = 'MULTIPLY'
        tint.inputs[0].default_value = 1.0
        tint.location = (shader.location.x - 220, shader.location.y)
        if diffuse.is_linked:
            tree.links.new(diffuse.links[0].from_socket, tint.inputs[1])
        else:
            tint.inputs[1].default_value = diffuse.default_value
        tree.links.new(ids.outputs['Color'], tint.inputs[2])
        tree.links.new(tint.outputs['Color'], diffuse)

    for i in range(1, 6):
        ids.inputs['Color ' + str(i)].default_value = colors.get(
            '_Color' + (str(i) if i > 1 else ''), (1.0, 1.0, 1.0, 1.0))
        if i == 1:
            continue
        source = shader.inputs.get('Use Material ' + str(i))
        target = ids.inputs['Use Color ' + str(i)]
        if source and source.is_linked:
            tree.links.new(source.links[0].from_socket, target)
        elif source:
            target.default_value = source.default_value
    if alpha.is_linked:
        tree.links.new(alpha.links[0].from_socket, ids.inputs['Lightmap Alpha'])
    else:
        ids.inputs['Lightmap Alpha'].default_value = alpha.default_value

    color_output = ids.outputs['Color']
    if floats.get('_UseMaterialMasksTex'):
        image = _weapon_material_mask(material)
        if image is None:
            raise RuntimeError('Missing material mask for the weapon element colors')
        mask = tree.nodes.get('Weapon Element Mask')
        if mask is None:
            mask = tree.nodes.new('ShaderNodeTexImage')
            mask.name = 'Weapon Element Mask'
            mask['_genshin_texture_property'] = '_MaterialMasksTex'
            mask.location = (shader.location.x - 1100, shader.location.y - 600)
        mask.image = image
        separate = tree.nodes.get('Weapon Element Mask RGB')
        if separate is None:
            separate = tree.nodes.new('ShaderNodeSeparateColor')
            separate.name = 'Weapon Element Mask RGB'
            separate.location = (shader.location.x - 850, shader.location.y - 600)
        tree.links.new(mask.outputs['Color'], separate.inputs[0])
        # This Unity shader uses RGB masks for _Color3, _Color4 and _Color5.
        # Successive blends preserve the authored overlaps (yellow/magenta edges).
        for channel, index in enumerate((3, 4, 5)):
            name = 'Weapon Element Mask Color ' + str(index)
            mix = tree.nodes.get(name)
            if mix is None:
                mix = tree.nodes.new('ShaderNodeMixRGB')
                mix.name = name
                mix.blend_type = 'MIX'
                mix.location = (shader.location.x - 650 + channel * 180,
                                shader.location.y - 600)
            tree.links.new(separate.outputs[channel], mix.inputs[0])
            tree.links.new(color_output, mix.inputs[1])
            mix.inputs[2].default_value = colors.get('_Color' + str(index), (1, 1, 1, 1))
            color_output = mix.outputs['Color']
        # Add emission only on the authored colored regions, before final Sheathe.
        mask_max = tree.nodes.get('Weapon Element Emission Mask')
        if mask_max is None:
            mask_max = tree.nodes.new('ShaderNodeMath')
            mask_max.name = 'Weapon Element Emission Mask'
            mask_max.operation = 'MAXIMUM'
        mask_union = tree.nodes.get('Weapon Element Emission Mask RGB')
        if mask_union is None:
            mask_union = tree.nodes.new('ShaderNodeMath')
            mask_union.name = 'Weapon Element Emission Mask RGB'
            mask_union.operation = 'MAXIMUM'
        tree.links.new(separate.outputs[0], mask_max.inputs[0])
        tree.links.new(separate.outputs[1], mask_max.inputs[1])
        tree.links.new(mask_max.outputs[0], mask_union.inputs[0])
        tree.links.new(separate.outputs[2], mask_union.inputs[1])
        tree.links.new(mask_union.outputs[0], shader.inputs['Element Emission Mask'])
        tree.links.new(tint.outputs['Color'], shader.inputs['Element Emission Color'])
        shader.inputs['Element Emission Strength'].default_value = floats.get('_EmissionScaler', 0.0)
    tree.links.new(color_output, tint.inputs[2])


def _ensure_weapon_output(shader):
    """Apply Sheathe after all shading/emission, keeping the original dissolve."""
    if 'Sheathe' not in shader.inputs or shader.node_tree.get('_gi_weapon_output_version') == 4:
        return
    original = shader.node_tree
    sheathe = next((n for n in original.nodes if n.type == 'GROUP' and n.node_tree
                    and 'Sheathe Fac' in n.inputs and 'Shader' in n.outputs), None)
    if sheathe is None:
        return
    if original.get('_gi_weapon_output_version') in (1, 2, 3):
        if original.get('_gi_weapon_output_version') < 3:
            _configure_weapon_visibility(original, sheathe)
        _configure_weapon_emission(original)
        original['_gi_weapon_output_version'] = 4
        return
    tree = original.copy()
    shader.node_tree = tree
    sheathe = tree.nodes[sheathe.name]
    sheathe.node_tree = sheathe.node_tree.copy()
    sub = sheathe.node_tree
    sub.interface.new_socket(name='Visibility', in_out='OUTPUT', socket_type='NodeSocketFloat')
    _configure_weapon_visibility(tree, sheathe)
    for name, socket_type in [('Element Emission Color', 'NodeSocketColor'),
                              ('Element Emission Mask', 'NodeSocketFloat'),
                              ('Element Emission Strength', 'NodeSocketFloat')]:
        socket = tree.interface.new_socket(name=name, in_out='INPUT', socket_type=socket_type)
        socket.default_value = (1, 1, 1, 1) if socket_type == 'NodeSocketColor' else 0.0
    inputs = tree.nodes.new('NodeGroupInput')
    inputs.name = 'Weapon Finish Inputs'
    gate = tree.nodes.new('ShaderNodeMath')
    gate.name = 'Weapon Sheathe Enabled'
    gate.operation = 'GREATER_THAN'
    gate.inputs[1].default_value = 0.0
    tree.links.new(inputs.outputs['Sheathe'], gate.inputs[0])
    visible = tree.nodes.new('ShaderNodeMath')
    visible.name = 'Weapon Final Visibility'
    visible.operation = 'MULTIPLY'
    tree.links.new(gate.outputs[0], visible.inputs[0])
    tree.links.new(sheathe.outputs['Visibility'], visible.inputs[1])
    strength = tree.nodes.new('ShaderNodeMath')
    strength.name = 'Weapon Masked Emission Strength'
    strength.operation = 'MULTIPLY'
    tree.links.new(inputs.outputs['Element Emission Mask'], strength.inputs[0])
    tree.links.new(inputs.outputs['Element Emission Strength'], strength.inputs[1])
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.name = 'Weapon Element Emission'
    tree.links.new(inputs.outputs['Element Emission Color'], emission.inputs['Color'])
    tree.links.new(strength.outputs[0], emission.inputs['Strength'])
    transparent = tree.nodes.new('ShaderNodeBsdfTransparent')
    transparent.name = 'Weapon Hidden'
    output = next(n for n in tree.nodes if n.type == 'GROUP_OUTPUT' and n.is_active_output)
    for socket in output.inputs:
        if socket.type != 'SHADER' or not socket.is_linked:
            continue
        source = socket.links[0].from_socket
        add = tree.nodes.new('ShaderNodeAddShader')
        add.name = 'Weapon Emission ' + socket.name
        tree.links.new(source, add.inputs[0])
        tree.links.new(emission.outputs[0], add.inputs[1])
        finish = tree.nodes.new('ShaderNodeMixShader')
        finish.name = 'Weapon Sheathe ' + socket.name
        tree.links.new(visible.outputs[0], finish.inputs[0])
        tree.links.new(transparent.outputs[0], finish.inputs[1])
        tree.links.new(add.outputs[0], finish.inputs[2])
        tree.links.new(finish.outputs[0], socket)
    _configure_weapon_emission(tree)
    tree['_gi_weapon_output_version'] = 4


def _configure_weapon_emission(tree):
    """Blend toward self-lit authored RGB instead of adding it until it clips white."""
    inputs = tree.nodes['Weapon Finish Inputs']
    denominator = tree.nodes.get('Weapon Emission Blend Denominator')
    if denominator is None:
        denominator = tree.nodes.new('ShaderNodeMath')
        denominator.name = 'Weapon Emission Blend Denominator'
        denominator.operation = 'ADD'
        denominator.inputs[1].default_value = 1.0
    tree.links.new(inputs.outputs['Element Emission Strength'], denominator.inputs[0])
    blend = tree.nodes.get('Weapon Emission Blend')
    if blend is None:
        blend = tree.nodes.new('ShaderNodeMath')
        blend.name = 'Weapon Emission Blend'
        blend.operation = 'DIVIDE'
        blend.use_clamp = True
    tree.links.new(inputs.outputs['Element Emission Strength'], blend.inputs[0])
    tree.links.new(denominator.outputs[0], blend.inputs[1])
    strength = tree.nodes['Weapon Masked Emission Strength']
    tree.links.new(blend.outputs[0], strength.inputs[1])
    emission = tree.nodes['Weapon Element Emission']
    for link in list(emission.inputs['Strength'].links):
        tree.links.remove(link)
    emission.inputs['Strength'].default_value = 1.0
    for node in list(tree.nodes):
        if not node.name.startswith('Weapon Emission BSDF') or node.type != 'ADD_SHADER':
            continue
        name, location = node.name, node.location.copy()
        shaded = node.inputs[0].links[0].from_socket
        emissive = node.inputs[1].links[0].from_socket
        targets = [link.to_socket for link in node.outputs[0].links]
        tree.nodes.remove(node)
        mix = tree.nodes.new('ShaderNodeMixShader')
        mix.name = name
        mix.location = location
        tree.links.new(strength.outputs[0], mix.inputs[0])
        tree.links.new(shaded, mix.inputs[1])
        tree.links.new(emissive, mix.inputs[2])
        for target in targets:
            tree.links.new(mix.outputs[0], target)


def _configure_weapon_visibility(tree, sheathe):
    # The native mix factor selects transparency, so visibility is its inverse.
    sub = sheathe.node_tree
    mix = next(n for n in sub.nodes if n.type == 'MIX_SHADER')
    factor = mix.inputs[0].links[0].from_socket
    inverse = sub.nodes.get('Weapon Sheathe Opacity')
    if inverse is None:
        inverse = sub.nodes.new('ShaderNodeMath')
        inverse.name = 'Weapon Sheathe Opacity'
        inverse.operation = 'SUBTRACT'
        inverse.inputs[0].default_value = 1.0
    sub.links.new(factor, inverse.inputs[1])
    output = next(n for n in sub.nodes if n.type == 'GROUP_OUTPUT' and n.is_active_output)
    sub.links.new(inverse.outputs[0], output.inputs['Visibility'])
    inputs = next(n for n in tree.nodes if n.type == 'GROUP_INPUT' and 'Sheathe' in n.outputs)
    tree.links.new(inputs.outputs['Sheathe'], sheathe.inputs['Sheathe Fac'])
    old = tree.nodes.get('Weapon Sheathe Progress')
    if old:
        tree.nodes.remove(old)


def _weapon_material_mask(material):
    """Resolve embedded IDs; also upgrade weapons saved before mask support."""
    from pathlib import Path
    import bpy
    from setup_wizard.utils.genshin_weapon_elements import PRESETS_KEY, SELECTION_KEY, _decode

    element = material.get(SELECTION_KEY, material.get('_original_material_name', '').rsplit('_', 1)[-1])
    image_key = '_gi_element_image_' + element + '_MaterialMasksTex'
    if material.get(image_key):
        return material[image_key]
    preset = _decode(material[PRESETS_KEY]).get(element, {})
    env = preset.get('saved', {}).get('m_TexEnvs', {}).get('_MaterialMasksTex', {})
    name = env.get('m_Texture', {}).get('Name')
    if not name:
        return None
    stem = Path(name).stem.lower()
    image = next((i for i in bpy.data.images if Path(i.filepath).stem.lower() == stem), None)
    if image is None:
        for node in iter_shader_image_nodes(material.node_tree):
            if not node.image or not node.image.filepath:
                continue
            folder = Path(bpy.path.abspath(node.image.filepath, library=node.image.library)).parent
            path = next((p for p in folder.glob('*') if p.stem.lower() == stem
                         and p.suffix.lower() in {'.png', '.dds', '.tga', '.jpg', '.jpeg'}), None)
            if path:
                image = bpy.data.images.load(str(path), check_existing=True)
                break
    if image:
        image.colorspace_settings.name = 'Non-Color'
        image.alpha_mode = 'CHANNEL_PACKED'
        material[image_key] = image
    return image


def link_weapon_sheathe(master, materials):
    """Bind companion materials to the main Sheathe input without changing its value."""
    shader = master.node_tree.nodes.get('Body Shader')
    if shader is None or 'Sheathe' not in shader.inputs:
        return
    sheathe = shader.inputs['Sheathe']
    if master.get('_gi_sheathe_linked'):
        sheathe.driver_remove('default_value')
        del master['_gi_sheathe_linked']

    def drive(socket):
        driver = socket.driver_add('default_value').driver
        driver.type = 'SCRIPTED'
        for variable in list(driver.variables):
            driver.variables.remove(variable)
        variable = driver.variables.new()
        variable.name = 'sheathe'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id_type = 'NODETREE'
        variable.targets[0].id = master.node_tree
        variable.targets[0].data_path = sheathe.path_from_id('default_value')
        driver.expression = 'sheathe'

    original_sheathe = next((n for n in shader.node_tree.nodes if n.type == 'GROUP'
                             and 'Sheathe Fac' in n.inputs and 'Visibility' in n.outputs), None)
    if original_sheathe is None:
        return
    outlines = set()
    for material in materials:
        if material != master:
            other_shader = material.node_tree.nodes.get('Body Shader')
            if other_shader and 'Sheathe' in other_shader.inputs:
                drive(other_shader.inputs['Sheathe'])
                material['_gi_sheathe_linked'] = True
        outline = material.get('_gi_element_outline')
        if outline:
            outlines.add(outline)
    for outline in outlines:
        tree = outline.node_tree
        control = tree.nodes.get('Weapon Sheathe')
        if control is None:
            control = tree.nodes.new('ShaderNodeValue')
            control.name = 'Weapon Sheathe'
            control.outputs[0].default_value = sheathe.default_value
        drive(control.outputs[0])
        mask = tree.nodes.get('Weapon Sheathe Mask')
        if mask is None:
            mask = tree.nodes.new('ShaderNodeGroup')
            mask.name = 'Weapon Sheathe Mask'
        mask.node_tree = original_sheathe.node_tree
        tree.links.new(control.outputs[0], mask.inputs['Sheathe Fac'])
        enabled = tree.nodes.get('Weapon Sheathe Enabled')
        if enabled is None:
            enabled = tree.nodes.new('ShaderNodeMath')
            enabled.name = 'Weapon Sheathe Enabled'
            enabled.operation = 'GREATER_THAN'
            enabled.inputs[1].default_value = 0.0
        tree.links.new(control.outputs[0], enabled.inputs[0])
        visible = tree.nodes.get('Weapon Sheathe Visibility')
        if visible is None:
            visible = tree.nodes.new('ShaderNodeMath')
            visible.name = 'Weapon Sheathe Visibility'
            visible.operation = 'MULTIPLY'
        tree.links.new(mask.outputs['Visibility'], visible.inputs[0])
        tree.links.new(enabled.outputs[0], visible.inputs[1])
        finish = tree.nodes.get('Weapon Sheathe Surface')
        if finish is None:
            output = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
            source = output.inputs['Surface'].links[0].from_socket
            transparent = tree.nodes.new('ShaderNodeBsdfTransparent')
            transparent.name = 'Weapon Sheathe Hidden'
            finish = tree.nodes.new('ShaderNodeMixShader')
            finish.name = 'Weapon Sheathe Surface'
            tree.links.new(transparent.outputs[0], finish.inputs[1])
            tree.links.new(source, finish.inputs[2])
            tree.links.new(finish.outputs[0], output.inputs['Surface'])
        tree.links.new(visible.outputs[0], finish.inputs[0])
        if hasattr(outline, 'surface_render_method'):
            outline.surface_render_method = 'DITHERED'
        else:
            outline.blend_method = 'HASHED'


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
    from setup_wizard.utils.genshin_weapon_elements import capture_element_presets
    capture_element_presets(material, root)
