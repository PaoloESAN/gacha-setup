"""Load compositor assets by source file, independently of colliding group names."""
import bpy

from setup_wizard.genshin_compositing_node_setup import get_node_tree, get_output_node_type


def load_group(filepath, name):
    for group in bpy.data.node_groups:
        if group.get('_gacha_compositor_source') == filepath and group.get('_gacha_compositor_group') == name:
            return group
    with bpy.data.libraries.load(filepath, link=False) as (source, target):
        if name not in source.node_groups:
            raise RuntimeError(f'Compositor group {name} missing from {filepath}')
        target.node_groups = [name]
    group = target.node_groups[0]
    group['_gacha_compositor_source'] = filepath
    group['_gacha_compositor_group'] = name
    return group


def copy_scene_compositor(filepath, scene):
    """Older AKE shaders store their compositor on a scene, not in a group."""
    objects_before = set(bpy.data.objects)
    with bpy.data.libraries.load(filepath, link=False) as (source, target):
        target.scenes = list(source.scenes[:1])
    temporary = [s for s in target.scenes if s]
    try:
        source_tree = next((getattr(s, 'compositing_node_group', None) or s.node_tree
                            for s in temporary if getattr(s, 'compositing_node_group', None) or s.node_tree), None)
        if source_tree is None:
            raise RuntimeError(f'No compositor found in {filepath}')
        tree = get_node_tree(scene)
        tree.nodes.clear()
        mapping = {}
        for node in source_tree.nodes:
            kind = get_output_node_type() if node.type in {'COMPOSITE', 'GROUP_OUTPUT'} else node.bl_idname
            if kind == 'NodeGroupOutput' and not any(
                s.item_type == 'SOCKET' and s.in_out == 'OUTPUT' and s.socket_type == 'NodeSocketColor'
                for s in tree.interface.items_tree
            ):
                tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
            new = tree.nodes.new(kind)
            mapping[node] = new
            for prop in node.bl_rna.properties:
                if prop.is_readonly or prop.identifier in {'rna_type', 'parent'} or prop.type == 'COLLECTION':
                    continue
                if prop.type == 'POINTER' and prop.identifier != 'node_tree':
                    continue
                try:
                    value = getattr(node, prop.identifier)
                    if prop.is_array:
                        value = value[:]
                    setattr(new, prop.identifier, value)
                except (AttributeError, TypeError, ValueError):
                    pass
            if new.bl_idname == 'CompositorNodeRLayers':
                new.scene = scene
                new.layer = scene.view_layers[0].name
            for old_input, new_input in zip(node.inputs, new.inputs):
                if hasattr(old_input, 'default_value') and hasattr(new_input, 'default_value'):
                    new_input.default_value = old_input.default_value
        for node, new in mapping.items():
            if node.parent in mapping:
                new.parent = mapping[node.parent]
        for link in source_tree.links:
            start, end = mapping[link.from_node], mapping[link.to_node]
            start_index = list(link.from_node.outputs).index(link.from_socket)
            end_index = list(link.to_node.inputs).index(link.to_socket)
            tree.links.new(start.outputs[start_index], end.inputs[end_index])
        return tree
    finally:
        imported_objects = {o for s in temporary for o in s.objects} - objects_before
        for s in temporary:
            bpy.data.scenes.remove(s, do_unlink=True)
        for obj in imported_objects:
            if not any(obj.name in s.objects for s in bpy.data.scenes):
                bpy.data.objects.remove(obj, do_unlink=True)
