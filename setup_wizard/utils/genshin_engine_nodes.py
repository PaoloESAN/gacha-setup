"""Activate the bundled Starriia extensions only when native Goo nodes exist."""
import json

import bpy
from bpy.app.handlers import persistent


def is_goo_engine():
    # Check the registered native node class rather than the executable's name
    # or version: Goo forks retain Blender's version numbers.
    return getattr(bpy.types, 'ShaderNodeSetDepth', None) is not None


def _socket(sockets, identifier):
    return next((socket for socket in sockets if socket.identifier == identifier), None)


def configure_genshin_engine_nodes(materials=None):
    """Restore native or portable links on marked trees, including nested copies.

    The bundle stays portable on disk. Per-tree socket identifiers survive
    character isolation, unlike datablock names with generated suffixes.
    """
    native = is_goo_engine()
    roots = [m.node_tree for m in (materials if materials is not None else bpy.data.materials)
             if m.node_tree]
    if materials is None:
        roots.extend(bpy.data.node_groups)
    visited = set()
    changed = 0
    while roots:
        tree = roots.pop()
        if tree in visited:
            continue
        visited.add(tree)
        roots.extend(n.node_tree for n in tree.nodes if n.type == 'GROUP' and n.node_tree)
        data = tree.get('gacha_goo_links')
        if not data:
            continue
        variants = json.loads(data)
        desired = variants['native' if native else 'portable']
        # Resolve first so a damaged graph cannot be left half-rewired.
        resolved = []
        for source, output, target, input_id in desired:
            source_node, target_node = tree.nodes.get(source), tree.nodes.get(target)
            if source_node is None or target_node is None:
                break
            output_socket = _socket(source_node.outputs, output)
            input_socket = _socket(target_node.inputs, input_id)
            if output_socket is None or input_socket is None:
                break
            resolved.append((output_socket, input_socket))
        else:
            wanted = set(map(tuple, desired))
            optional = set(map(tuple, variants['native'] + variants['portable']))
            for link in list(tree.links):
                signature = (link.from_node.name, link.from_socket.identifier,
                             link.to_node.name, link.to_socket.identifier)
                if signature in optional and signature not in wanted:
                    tree.links.remove(link)
                    changed += 1
            for output_socket, input_socket in resolved:
                if not any(link.from_socket == output_socket for link in input_socket.links):
                    tree.links.new(output_socket, input_socket)
                    changed += 1
    return changed


@persistent
def repair_genshin_engine_nodes(_context):
    configure_genshin_engine_nodes()


def _repair_after_register():
    configure_genshin_engine_nodes()


def register():
    for name in ('load_post', 'blend_import_post'):
        handlers = getattr(bpy.app.handlers, name, None)
        if handlers is not None and repair_genshin_engine_nodes not in handlers:
            handlers.append(repair_genshin_engine_nodes)
    # Addon registration runs with restricted bpy.data. Repair the open scene
    # on the next event loop, after Blender releases that restriction.
    if not bpy.app.timers.is_registered(_repair_after_register):
        bpy.app.timers.register(_repair_after_register, first_interval=0.0)


def unregister():
    if bpy.app.timers.is_registered(_repair_after_register):
        bpy.app.timers.unregister(_repair_after_register)
    for name in ('load_post', 'blend_import_post'):
        handlers = getattr(bpy.app.handlers, name, None)
        if handlers is not None and repair_genshin_engine_nodes in handlers:
            handlers.remove(repair_genshin_engine_nodes)
