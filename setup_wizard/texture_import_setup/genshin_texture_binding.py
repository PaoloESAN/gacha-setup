"""Bind texture roles by meaning and shader connections, never node numbering."""
import re


def texture_role(name):
    name = str(name).casefold()
    compact = re.sub(r'[^a-z0-9]', '', name)
    if 'lightmap' in compact or 'facemap' in compact:
        return 'lightmap'
    if 'normal' in compact or 'bump' in compact:
        return 'normal'
    if 'ramp' in compact:
        return 'ramp'
    if any(word in compact for word in ('mask', 'metalmap', 'matcap', 'specular', 'roughness')):
        return 'mask'
    if any(word in compact for word in ('diffuse', 'basecolor', 'albedo', 'maintex', 'basetex')):
        return 'diffuse'
    return None


def _connected_roles(node):
    roles, visited = set(), set()

    def follow(socket):
        for link in socket.links:
            dest = link.to_node
            key = dest.as_pointer(), link.to_socket.identifier
            if key in visited:
                continue
            visited.add(key)
            if dest.type == 'REROUTE':
                for output in dest.outputs:
                    follow(output)
            elif dest.type in {'NORMAL_MAP', 'BUMP'}:
                roles.add('normal')
            else:
                role = texture_role(link.to_socket.name)
                if role:
                    roles.add(role)
    for socket in node.outputs:
        follow(socket)
    return roles


def find_genshin_texture_nodes(tree, category):
    found, visited = [], set()

    def visit(current):
        if not current or current.as_pointer() in visited:
            return
        visited.add(current.as_pointer())
        for node in current.nodes:
            if node.type == 'TEX_IMAGE':
                # A default Blender name (Image Texture.001, etc.) says nothing
                # about its role. Labels and actual shader sockets do.
                role = texture_role(node.name + ' ' + (node.label or ''))
                if role == category or (role is None and _connected_roles(node) == {category}):
                    found.append(node)
            elif node.type == 'GROUP' and node.node_tree:
                name = node.node_tree.name.casefold()
                if name.startswith('genshin ') or any(part in name for part in (
                    'gi body', 'gi face', 'gi weapons', 'face factor', 'face shader',
                    'eyeshadow', 'primotoon', 'hoyotoon', 'outline', 'shader textures',
                    'global material properties', 'night soul', 'depth-based rim',
                )):
                    continue
                visit(node.node_tree)
    visit(tree)
    return found
