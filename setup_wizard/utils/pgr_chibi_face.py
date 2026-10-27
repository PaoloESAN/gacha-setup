"""Composite PGR chibi expression atlases onto the existing weighted face."""
from pathlib import Path

import bpy


FACE_UV = 'PGR_ChibiFaceUV'
ATLAS_NODE = 'PGR_ChibiFace_Atlas'
OVERLAY_NODE = 'PGR_ChibiFace_Overlay'


def _face_loops(obj, material, diffuse):
    mesh = obj.data
    uv = mesh.uv_layers.get('UV0') or mesh.uv_layers.active
    if uv is None or not obj.vertex_groups:
        return []
    head_groups = {g.index for g in obj.vertex_groups
                   if 'head' in g.name.lower() or g.name == 'DEF-spine.006'}
    if not head_groups:
        return []
    slots = {i for i, slot in enumerate(obj.material_slots) if slot.material == material}
    vertices = {i for poly in mesh.polygons if poly.material_index in slots for i in poly.vertices}
    neighbors = {i: set() for i in vertices}
    for edge in mesh.edges:
        a, b = edge.vertices
        if a in vertices and b in vertices:
            neighbors[a].add(b); neighbors[b].add(a)
    width, height = diffuse.size
    if not width or not height:
        return []
    pixels = list(diffuse.pixels)
    remaining, candidates = set(vertices), []
    while remaining:
        pending = [remaining.pop()]
        component = set(pending)
        while pending:
            for index in neighbors[pending.pop()]:
                if index in remaining:
                    remaining.remove(index); component.add(index); pending.append(index)
        if len(component) < 16:
            continue
        head = sum(sum(g.weight for g in mesh.vertices[i].groups if g.group in head_groups) > .7
                   for i in component)
        if head < len(component) * .8:
            continue
        loops = [loop.index for poly in mesh.polygons if poly.material_index in slots
                 for loop in (mesh.loops[i] for i in poly.loop_indices) if loop.vertex_index in component]
        skin = 0
        for index in loops:
            u, v = uv.data[index].uv
            x, y = min(width - 1, max(0, int(u * width))), min(height - 1, max(0, int(v * height)))
            r, g, b = pixels[(y * width + x) * 4:(y * width + x) * 4 + 3]
            skin += r > .5 and r > g + .035 and r > b + .01
        if loops and skin > len(loops) * .8:
            candidates.append((len(component), loops))
    # The face is the largest skin island rigidly weighted to the head; smaller
    # head skin islands are the neck/ears and must not receive another eye pair.
    return max(candidates, key=lambda c: c[0])[1] if candidates else []


def configure_chibi_face(material, definition, image_paths, diffuse_node):
    props = definition.get('m_SavedProperties', {})
    if float(props.get('m_Floats', {}).get('_FaceMark', 0)) <= 0 or not diffuse_node.image:
        return 0
    face = props.get('m_TexEnvs', {}).get('_FaceMap', {})
    reference = face.get('m_Texture', {})
    path = image_paths.get(str(reference.get('Name', '')).lower())
    if not path or reference.get('IsNull', False):
        return 0
    image = bpy.data.images.load(str(Path(path).resolve()), check_existing=True)
    # These are alpha decals, unlike the opaque face-shadow maps on avatars.
    if image.channels != 4 or not image.size[0] or image.pixels[3] > .05:
        return 0
    configured = 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not any(s.material == material for s in obj.material_slots):
            continue
        loops = _face_loops(obj, material, diffuse_node.image)
        if not loops:
            continue
        mesh = obj.data
        if mesh.users > 1:
            mesh = obj.data = mesh.copy()
        source = mesh.uv_layers.get('UV0') or mesh.uv_layers.active
        active = mesh.uv_layers.active_index
        render = next((uv.name for uv in mesh.uv_layers if uv.active_render), None)
        minimum = [min(source.data[i].uv[a] for i in loops) for a in range(2)]
        span = [max(source.data[i].uv[a] for i in loops) - minimum[a] for a in range(2)]
        if min(span) < 1e-6:
            continue
        scale, offset = face.get('m_Scale', {}), face.get('m_Offset', {})
        coordinates = {i: tuple((source.data[i].uv[a] - minimum[a]) / span[a] * scale.get(axis, 1)
                                + offset.get(axis, 0) for a, axis in enumerate(('X', 'Y'))) for i in loops}
        uv = mesh.uv_layers.get(FACE_UV) or mesh.uv_layers.new(name=FACE_UV)
        for index, corner in enumerate(uv.data):
            corner.uv = coordinates.get(index, (-1, -1))
        mesh.uv_layers.active_index = active
        if render:
            mesh.uv_layers[render].active_render = True
        obj['pgr_chibi_face_loops'] = len(loops)
        configured += 1
    if not configured:
        return 0
    image.alpha_mode = 'CHANNEL_PACKED'
    image.colorspace_settings.name = 'sRGB'
    tree = material.node_tree
    atlas = tree.nodes.get(ATLAS_NODE) or tree.nodes.new('ShaderNodeTexImage')
    atlas.name = ATLAS_NODE; atlas.label = 'Chibi facial expressions (_FaceMap)'
    atlas.image = image; atlas.extension = 'CLIP'
    uv_node = tree.nodes.get(FACE_UV) or tree.nodes.new('ShaderNodeUVMap')
    uv_node.name = FACE_UV; uv_node.uv_map = FACE_UV
    mix = tree.nodes.get(OVERLAY_NODE) or tree.nodes.new('ShaderNodeMixRGB')
    mix.name = OVERLAY_NODE; mix.blend_type = 'MIX'
    destinations = [l.to_socket for l in diffuse_node.outputs['Color'].links if l.to_node != mix]
    tree.links.new(uv_node.outputs['UV'], atlas.inputs['Vector'])
    tree.links.new(diffuse_node.outputs['Color'], mix.inputs[1])
    tree.links.new(atlas.outputs['Color'], mix.inputs[2])
    tree.links.new(atlas.outputs['Alpha'], mix.inputs[0])
    for socket in destinations:
        tree.links.new(mix.outputs['Color'], socket)
    atlas.location = (diffuse_node.location.x, diffuse_node.location.y - 350)
    uv_node.location = (atlas.location.x - 200, atlas.location.y)
    mix.location = (atlas.location.x + 300, diffuse_node.location.y)
    material['pgr_chibi_face_atlas'] = image.name
    return configured
