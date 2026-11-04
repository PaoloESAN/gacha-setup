"""Restore the original render over Genshin bloom/tonemapping."""


def ensure_hoyoverse_alpha_over(group):
    if not group or group.bl_idname != 'CompositorNodeTree':
        return False
    tonemapper = next((node for node in group.nodes
                       if node.type == 'GROUP' and node.node_tree
                       and node.node_tree.name.startswith('Genshin Tonemapper')), None)
    source = next((node for node in group.nodes if node.type == 'GROUP_INPUT'), None)
    output = next((node for node in group.nodes if node.type == 'GROUP_OUTPUT' and node.is_active_output), None)
    if not tonemapper or not source or not output:
        return False
    image_out = output.inputs.get('Image')
    if image_out is None:
        return False
    processed = image_out.links[0].from_socket if image_out.is_linked else tonemapper.outputs['Image']
    alpha = None
    for candidate in group.nodes:
        if candidate.bl_idname != 'CompositorNodeAlphaOver':
            continue
        old_background = candidate.inputs.get('Background') or candidate.inputs[1]
        old_foreground = candidate.inputs.get('Foreground') or candidate.inputs[2]
        if candidate.get('_gacha_source_alpha_over') or (
                old_background.is_linked and old_background.links[0].from_node == tonemapper
                and old_foreground.is_linked and old_foreground.links[0].from_node == source):
            alpha = candidate
            break
    reuse = alpha is not None
    if not reuse:
        alpha = group.nodes.new('CompositorNodeAlphaOver')
        alpha.name = 'Alpha Over'
        alpha.location = (tonemapper.location.x + tonemapper.width + 120, tonemapper.location.y)
        output.location = (alpha.location.x + alpha.width + 120, alpha.location.y)
    alpha['_gacha_source_alpha_over'] = True
    # Blender 5.2 exposes these settings as sockets; older files use RNA flags.
    if alpha.inputs.get('Background') is not None:
        background = alpha.inputs['Background']
        foreground = alpha.inputs['Foreground']
        alpha.inputs['Factor'].default_value = 1.
        alpha.inputs['Type'].default_value = 'Over'
        alpha.inputs['Straight Alpha'].default_value = True
    else:
        background, foreground = alpha.inputs[1], alpha.inputs[2]
        alpha.inputs[0].default_value = 1.
        alpha.use_premultiply = True
        alpha.premul = 0.
    if not reuse:
        group.links.new(processed, background)
    elif not background.is_linked:
        group.links.new(tonemapper.outputs['Image'], background)
    if not foreground.is_linked or foreground.links[0].from_socket == source.outputs['Image']:
        bloom = next((n for n in group.nodes if n.type == 'GROUP' and n.node_tree
                      and n.node_tree.name.startswith('Genshin Bloom')), None)
        image = bloom.inputs.get('Image') if bloom else None
        source_image = image.links[0].from_socket if image is not None and image.is_linked else source.outputs['Image']
        group.links.new(source_image, foreground)
    if not reuse or not image_out.is_linked:
        group.links.new(alpha.outputs['Image'], image_out)
    return True
