"""Activate the bundled Starriia extensions only when native Goo nodes exist."""
import json
import re

import bpy
from bpy.app.handlers import persistent


def is_goo_engine():
    # Check the registered native node class rather than the executable's name
    # or version: Goo forks retain Blender's version numbers.
    return getattr(bpy.types, 'ShaderNodeSetDepth', None) is not None


def _socket(sockets, identifier):
    return next((socket for socket in sockets if socket.identifier == identifier), None)


def _isolate_legacy_eye_materials():
    """Older Genshin irises share their body material after mesh joining."""
    created = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or 'eyestar' in obj.name.lower().replace('_', ''):
            continue
        groups = {group.index for group in obj.vertex_groups if re.fullmatch(
            r'(?:def)?eye[lr]|eyebone(?:[lr])?a?0[12](?:[lr])?',
            re.sub(r'[^a-z0-9]', '', group.name.lower()))}
        if not groups:
            continue
        eye_vertices = {vertex.index for vertex in obj.data.vertices
                        if sum(g.weight for g in vertex.groups if g.group in groups) > .5}
        for polygon in obj.data.polygons:
            if not all(index in eye_vertices for index in polygon.vertices):
                continue
            source = obj.material_slots[polygon.material_index].material
            if (source is None or not source.node_tree
                    or not source.name.lower().startswith('hoyoverse - ')
                    or any(part in source.name.lower() for part in ('pupil', 'highlight', 'outline'))
                    or not any(node.type == 'GROUP' and node.node_tree
                               and node.node_tree.name.lower().startswith('hoyoverse - gi body')
                               for node in source.node_tree.nodes)):
                continue
            material = created.get(source)
            if material is None:
                material = source.copy()
                material.name = source.name + ' Eye Pupil'
                material['_gacha_legacy_eye_source'] = source.name
                created[source] = material
            slot = next((index for index, existing in enumerate(obj.data.materials)
                         if existing == material), None)
            if slot is None:
                slot = len(obj.data.materials)
                obj.data.materials.append(material)
            polygon.material_index = slot
    return list(created.values())


def _configure_eye_depth(materials):
    """Keep the split pupil/highlight materials on the bundled Goo depth path."""
    if not is_goo_engine():
        return
    depth_tree = next((tree for tree in bpy.data.node_groups
                       if tree.name == 'Set Depth' and any(
                           node.bl_idname == 'ShaderNodeSetDepth' for node in tree.nodes)), None)
    if depth_tree is None:
        return
    eye_depth_tree = None

    def eye_depth():
        nonlocal eye_depth_tree
        if eye_depth_tree is None:
            eye_depth_tree = next((tree for tree in bpy.data.node_groups
                                   if tree.get('_gacha_goo_eye_depth_v1')), None)
        if eye_depth_tree is None:
            eye_depth_tree = depth_tree.copy()
            eye_depth_tree.name = 'Goo Eye Depth'
            eye_depth_tree['_gacha_goo_eye_depth_v1'] = True
        if not eye_depth_tree.get('_gacha_goo_eye_intensity_v2'):
            # Keep occlusion detection, but use the eye's Intensity directly.
            # The face-shadow texture can override it to 1 and erase the iris.
            # Bypassing the blend entirely instead made Intensity ineffective.
            native_depth = next(node for node in eye_depth_tree.nodes
                                if node.bl_idname == 'ShaderNodeSetDepth')
            group_input = eye_depth_tree.nodes['Group Input']
            mix = eye_depth_tree.nodes['Mix']
            strength = eye_depth_tree.nodes['Math.001']
            eye_depth_tree.links.new(group_input.outputs['Intensity'], strength.inputs[1])
            eye_depth_tree.links.new(_socket(mix.outputs, 'Result_Color'), native_depth.inputs['Shader'])
            eye_depth_tree['_gacha_goo_eye_intensity_v2'] = True
        return eye_depth_tree

    for material in materials:
        name = material.name.lower()
        if (not name.startswith('hoyoverse - ') or 'outline' in name
                or not any(part in name for part in ('pupil', 'highlight'))
                or not material.node_tree):
            continue
        tree = material.node_tree
        existing_depth = [node for node in tree.nodes if node.type == 'GROUP'
                          and node.node_tree and any(child.bl_idname == 'ShaderNodeSetDepth'
                                                    for child in node.node_tree.nodes)]
        for node in existing_depth:
            node.node_tree = eye_depth()
        if tree.get('gacha_goo_links') or any(
                any(socket.is_linked for socket in node.outputs) for node in existing_depth):
            continue
        output = next((node for node in tree.nodes if node.type == 'OUTPUT_MATERIAL'
                       and node.is_active_output), None)
        if output is None or not output.inputs['Surface'].is_linked:
            continue
        if 'highlight' in name:
            # Apply depth to the lit highlights, before their alpha mix. The
            # transparent branch must remain transparent, as in Starriia's eye.
            source = next((node for node in tree.nodes if node.type == 'EMISSION'), None)
            links = [link for link in tree.links if source and link.from_node == source
                     and link.to_node.type == 'MIX_SHADER']
            if not links:
                continue
            link = links[0]
        else:
            link = output.inputs['Surface'].links[0]
        source_socket, target_socket = link.from_socket, link.to_socket
        depth = tree.nodes.new('ShaderNodeGroup')
        depth.node_tree = eye_depth()
        depth.name = 'Goo Eye Set Depth'
        depth.label = 'Goo Eye See Through'
        depth.location = (link.to_node.location.x - 220, link.to_node.location.y - 180)
        depth.inputs['Depth'].default_value = -.075
        depth.inputs['Intensity'].default_value = .5
        def signature(source, target):
            return [source.node.name, source.identifier, target.node.name, target.identifier]
        tree['gacha_goo_links'] = json.dumps({
            'native': [signature(source_socket, depth.inputs['Shader']),
                       signature(depth.outputs['Shader'], target_socket)],
            'portable': [signature(source_socket, target_socket)],
        })


def _configure_native_depth_materials(materials):
    """Native depth shaders need the Goo refraction pass, unlike the fallback."""
    uses_depth = False
    for material in materials:
        tree = material.node_tree
        if tree is None or not tree.get('gacha_goo_links'):
            continue
        if not any(node.type == 'GROUP' and node.node_tree
                   and any(child.bl_idname == 'ShaderNodeSetDepth' for child in node.node_tree.nodes)
                   for node in tree.nodes):
            continue
        uses_depth = True
        if material.get('_gacha_goo_depth_defaults_v1'):
            continue
        if 'highlight' not in material.name.lower():
            for attribute in ('use_screen_refraction', 'use_raytrace_refraction'):
                if hasattr(material, attribute):
                    setattr(material, attribute, True)
        if hasattr(material, 'thickness_mode'):
            material.thickness_mode = 'SLAB'
        if hasattr(material, 'blend_method'):
            material.blend_method = 'HASHED'
        if hasattr(material, 'shadow_method'):
            material.shadow_method = 'HASHED'
        material.use_backface_culling = True
        output = next((node for node in tree.nodes if node.type == 'OUTPUT_MATERIAL'
                       and node.is_active_output), None)
        thickness = output.inputs.get('Thickness') if output else None
        if thickness is not None and not thickness.is_linked:
            thickness.default_value = 0.0
        material['_gacha_goo_depth_defaults_v1'] = True
    scene = bpy.context.scene
    if uses_depth and not scene.get('_gacha_goo_depth_scene_v1'):
        eevee = getattr(scene, 'eevee', None)
        for attribute in ('use_ssr', 'use_ssr_refraction'):
            if hasattr(eevee, attribute):
                setattr(eevee, attribute, True)
        scene['_gacha_goo_depth_scene_v1'] = True


def configure_genshin_engine_nodes(materials=None):
    """Restore native or portable links on marked trees, including nested copies.

    The bundle stays portable on disk. Per-tree socket identifiers survive
    character isolation, unlike datablock names with generated suffixes.
    """
    native = is_goo_engine()
    candidates = list(materials if materials is not None else bpy.data.materials)
    if native and materials is None:
        candidates.extend(_isolate_legacy_eye_materials())
    _configure_eye_depth(candidates)
    if native:
        _configure_native_depth_materials(candidates)
    roots = [m.node_tree for m in candidates
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
        if native and any(node.bl_idname == 'ShaderNodeSetDepth' for node in tree.nodes):
            # The bundled color mask is not painted consistently across
            # characters (and exists under different attribute names).
            # Removing this optional mask preserves the authored
            # input defaults, just as deleting the node in the shader editor.
            for node in list(tree.nodes):
                if node.bl_idname == 'ShaderNodeVertexColor':
                    tree.nodes.remove(node)
                    changed += 1
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
