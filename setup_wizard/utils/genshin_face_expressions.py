"""Use authored, closed face overlays for Genshin's expression atlas."""

from pathlib import Path
import json

import bpy
import bmesh


SELECTOR = 'Genshin Face Expressions'
GROUP = 'Genshin - Face Expressions'
UV = 'Expressions_Front'
LEFT = 'gacha_expression_eye_left'
RIGHT = 'gacha_expression_eye_right'
REPLACED_COVER = 'gacha_expression_replaced_cover'
NO_OUTLINE = 'gacha_expression_no_outline'
COVER_LEFT = 'gacha_expression_native_cover_left'
COVER_RIGHT = 'gacha_expression_native_cover_right'
MODIFIER = 'Facial Expressions - Clean Eyes'


def expression_nodes(arm):
    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
    seen = set()
    for obj in _iter_rig_meshes(arm):
        for mat in obj.data.materials:
            if not mat or mat in seen or not mat.node_tree:
                continue
            seen.add(mat)
            node = mat.node_tree.nodes.get(SELECTOR)
            if node:
                yield node


def _components(mesh):
    neighbors = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    remaining = set(range(len(mesh.vertices)))
    components, membership = [], {}
    while remaining:
        seed = remaining.pop()
        vertices, pending = {seed}, [seed]
        while pending:
            for index in neighbors[pending.pop()]:
                if index in remaining:
                    remaining.remove(index)
                    vertices.add(index)
                    pending.append(index)
        number = len(components)
        membership.update((index, number) for index in vertices)
        components.append((vertices, []))
    for poly in mesh.polygons:
        components[membership[poly.vertices[0]]][1].append(poly.index)
    return components


def _bounds(points):
    return tuple((min(p[i] for p in points), max(p[i] for p in points))
                 for i in range(3))


def _find_overlay(obj, components):
    """Require two large, overlapping face shells; ordinary faces are untouched."""
    mesh = obj.data
    candidates = []
    for vertices, polygons in components:
        if len(vertices) < 150 or len(polygons) < 250:
            continue
        materials = {mesh.polygons[i].material_index for i in polygons}
        if len(materials) != 1:
            continue
        index = next(iter(materials))
        mat = mesh.materials[index] if index < len(mesh.materials) else None
        if not mat or not mat.node_tree or 'face' not in mat.name.lower():
            continue
        if any(word in mat.name.lower() for word in ('outline', 'brow', 'eye')):
            continue
        bounds = _bounds([mesh.vertices[i].co for i in vertices])
        candidates.append((vertices, polygons, index, bounds))
    for outer in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
        for inner in candidates:
            if outer is inner or len(outer[1]) < len(inner[1]) * 1.15:
                continue
            scale = max(high - low for low, high in outer[3])
            delta = max(abs(a - b) for pair_a, pair_b in zip(outer[3], inner[3])
                        for a, b in zip(pair_a, pair_b))
            if scale > 0 and delta < scale * .005:
                return outer[:3]
    return None


def _load_selector():
    group = bpy.data.node_groups.get(GROUP)
    if group:
        return group
    asset = Path(__file__).resolve(
    ).parents[1] / 'shaders/gi/Face Expressions.blend'
    with bpy.data.libraries.load(str(asset), link=False) as (source, target):
        target.node_groups = [GROUP]
    group = target.node_groups[0]
    return group


def _eye_fit(meshes):
    """Fit the atlas windows to this character's neutral pupil geometry."""
    points = []
    for obj in meshes:
        name = obj.name.lower()
        if 'pupil' not in name and not any(
                mat and any(word in mat.name.lower()
                            for word in ('pupil', 'iris'))
                for mat in obj.data.materials):
            continue
        points.extend(obj.matrix_world @
                      vertex.co for vertex in obj.data.vertices)
    if not points:
        return None
    center = sum(p.x for p in points) / len(points)
    sides = [[p for p in points if (p.x > center) == left]
             for left in (True, False)]
    if any(len(side) < 8 for side in sides):
        return None
    boxes = [_bounds(side) for side in sides]
    spacing = abs(sum(boxes[0][0]) / 2 - sum(boxes[1][0]) / 2)
    height = sum(sum(box[2]) / 2 for box in boxes) / 2
    width = max(box[0][1] - box[0][0] for box in boxes) * 1.6
    window_height = max(box[2][1] - box[2][0] for box in boxes) * 1.8
    if min(spacing, width, window_height) <= 0:
        return None
    return center, spacing, height, width, window_height


def _brow_polygons(obj):
    """Recognize brows even after they have been joined into the face mesh."""
    def is_brow(name):
        return any(token in name.casefold() for token in ('brow', 'ceja', '眉'))

    if is_brow(obj.name):
        return set(range(len(obj.data.polygons)))
    materials = {i for i, mat in enumerate(obj.data.materials) if mat and is_brow(mat.name)}
    protected = {poly.index for poly in obj.data.polygons if poly.material_index in materials}
    if protected:
        return protected
    # Some shader replacements merge the brow material into the face. Its
    # authored brow morphs still identify the eyebrow vertices.
    keys = obj.data.shape_keys
    if keys is None:
        return protected
    vertices = set()
    for key in keys.key_blocks:
        if not is_brow(key.name) or key == key.relative_key:
            continue
        vertices.update(i for i, (point, neutral) in enumerate(zip(key.data, key.relative_key.data))
                        if (point.co - neutral.co).length_squared > 1e-12)
    protected.update(poly.index for poly in obj.data.polygons
                     if all(index in vertices for index in poly.vertices))
    return protected


def _eye_masks(obj, components, overlay, fit):
    center, spacing, height, width, window_height = fit
    left, right = set(), set()
    for vertices, polygons in components:
        if overlay and vertices == overlay[0]:
            continue
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in vertices]
        bounds = _bounds(points)
        # Skin, mouth and central face shells must survive the expression.
        midpoint = sum(bounds[0]) / 2 - center
        if abs(midpoint) < spacing * .18:
            continue
        eye_x = center + (spacing / 2 if midpoint > 0 else -spacing / 2)
        inside = sum(abs(p.x - eye_x) < width * .85
                     and abs(p.z - height) < window_height * .9 for p in points)
        if inside >= len(points) * .9:
            (left if midpoint > 0 else right).update(polygons)
    protected = _brow_polygons(obj)
    left.difference_update(protected)
    right.difference_update(protected)
    return left, right


def _eye_hole_edges(obj, polygons, fit):
    """Find only the two eye openings; never fill the outer face boundary."""
    from collections import Counter
    center, spacing, height, width, window_height = fit
    mesh = obj.data
    counts = Counter(tuple(sorted(edge)) for index in polygons
                     for edge in mesh.polygons[index].edge_keys)
    boundary = [edge for edge, count in counts.items() if count == 1]
    neighbors = {}
    for a, b in boundary:
        neighbors.setdefault(a, set()).add(b)
        neighbors.setdefault(b, set()).add(a)
    remaining = set(neighbors)
    holes = []
    while remaining:
        pending = [remaining.pop()]
        vertices = set(pending)
        while pending:
            for index in neighbors[pending.pop()]:
                if index in remaining:
                    remaining.remove(index)
                    vertices.add(index)
                    pending.append(index)
        points = [obj.matrix_world @ mesh.vertices[i].co for i in vertices]
        midpoint = sum(point.x for point in points) / len(points) - center
        if abs(midpoint) < spacing * .18:
            continue
        eye_x = center + (spacing / 2 if midpoint > 0 else -spacing / 2)
        inside = sum(abs(p.x - eye_x) < width and
                     abs(p.z - height) < window_height for p in points)
        if inside >= len(points) * .9:
            holes.extend(edge for edge in boundary if edge[0] in vertices)
    return holes


def _make_closed_cover(face, vertices, material, fit):
    """Keep the real eyelid skin, and create a separate, closed expression cover."""
    cover = face.copy()
    cover.data = face.data.copy()
    cover.name = face.name + ' Expressions'
    cover.data.name = cover.name
    face.users_collection[0].objects.link(cover)
    for modifier in list(cover.modifiers):
        if modifier.name == MODIFIER or 'outline' in modifier.name.lower():
            cover.modifiers.remove(modifier)
    mesh = cover.data
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in vertices], context='VERTS')
        bm.to_mesh(mesh)
    finally:
        bm.free()
    holes = set(_eye_hole_edges(cover, range(len(mesh.polygons)), fit))
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        edges = [edge for edge in bm.edges if tuple(sorted(v.index for v in edge.verts)) in holes]
        result = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        if result['faces']:
            bmesh.ops.triangulate(bm, faces=result['faces'])
        bm.normal_update()
        offset = max(high - low for low, high in _bounds([v.co for v in bm.verts])) * .0005
        shape_layers = list(bm.verts.layers.shape.values())
        for vertex in bm.verts:
            delta = vertex.normal * offset
            vertex.co += delta
            for layer in shape_layers:
                vertex[layer] += delta
        for poly in bm.faces:
            poly.material_index = 0
            poly.smooth = True
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.materials.clear()
    mesh.materials.append(material)
    mesh.update()
    cover['gacha_expression_cover'] = True
    return cover


def _mask_group():
    name = 'Genshin - Expression Eye Visibility'
    group = bpy.data.node_groups.get(name)
    if group:
        return group
    group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    group.interface.new_socket(
        name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(
        name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    for name in ('Left', 'Right'):
        group.interface.new_socket(
            name=name, in_out='INPUT', socket_type='NodeSocketBool')
    incoming = group.nodes.new('NodeGroupInput')
    outgoing = group.nodes.new('NodeGroupOutput')
    masks = []
    for side, attribute in (('Left', LEFT), ('Right', RIGHT)):
        attr = group.nodes.new('GeometryNodeInputNamedAttribute')
        attr.data_type = 'BOOLEAN'
        attr.inputs['Name'].default_value = attribute
        both = group.nodes.new('FunctionNodeBooleanMath')
        both.operation = 'AND'
        group.links.new(attr.outputs['Attribute'], both.inputs[0])
        group.links.new(incoming.outputs[side], both.inputs[1])
        masks.append(both.outputs[0])
    either = group.nodes.new('FunctionNodeBooleanMath')
    either.operation = 'OR'
    for index, socket in enumerate(masks):
        group.links.new(socket, either.inputs[index])
    delete = group.nodes.new('GeometryNodeDeleteGeometry')
    delete.domain = 'FACE'
    delete.mode = 'ALL'
    group.links.new(incoming.outputs['Geometry'], delete.inputs['Geometry'])
    group.links.new(either.outputs[0], delete.inputs['Selection'])
    group.links.new(delete.outputs['Geometry'], outgoing.inputs['Geometry'])
    previous = delete.inputs['Selection'].links[0].from_socket
    attr = group.nodes.new('GeometryNodeInputNamedAttribute')
    attr.data_type = 'BOOLEAN'
    attr.inputs['Name'].default_value = REPLACED_COVER
    either = group.nodes.new('FunctionNodeBooleanMath')
    either.operation = 'OR'
    group.links.new(previous, either.inputs[0])
    group.links.new(attr.outputs['Attribute'], either.inputs[1])
    group.links.new(either.outputs[0], delete.inputs['Selection'])
    # A transparent Goo depth-writing surface can still stamp a dithered
    # depth pattern. Omit the native cover geometry for each neutral eye.
    for side, name in (('Left', COVER_LEFT), ('Right', COVER_RIGHT)):
        attr = group.nodes.new('GeometryNodeInputNamedAttribute')
        attr.data_type = 'BOOLEAN'
        attr.inputs['Name'].default_value = name
        neutral = group.nodes.new('FunctionNodeBooleanMath')
        neutral.operation = 'NOT'
        group.links.new(incoming.outputs[side], neutral.inputs[0])
        selected = group.nodes.new('FunctionNodeBooleanMath')
        selected.operation = 'AND'
        group.links.new(attr.outputs['Attribute'], selected.inputs[0])
        group.links.new(neutral.outputs[0], selected.inputs[1])
        either = group.nodes.new('FunctionNodeBooleanMath')
        either.operation = 'OR'
        group.links.new(delete.inputs['Selection'].links[0].from_socket, either.inputs[0])
        group.links.new(selected.outputs[0], either.inputs[1])
        group.links.new(either.outputs[0], delete.inputs['Selection'])
    return group


def _install_masks(obj, masks, selector, material):
    from setup_wizard.utils.modifier_utils import get_modifier_inputs, set_modifier_property
    if (not any(masks) and obj.data.attributes.get(REPLACED_COVER) is None
            and obj.data.attributes.get(COVER_LEFT) is None):
        return
    for name, polygons in zip((LEFT, RIGHT), masks):
        attr = obj.data.attributes.get(
            name) or obj.data.attributes.new(name, 'BOOLEAN', 'FACE')
        attr.data.foreach_set(
            'value', [i in polygons for i in range(len(obj.data.polygons))])
    modifier = obj.modifiers.get(
        MODIFIER) or obj.modifiers.new(MODIFIER, 'NODES')
    modifier.node_group = _mask_group()
    # Remove the details before outline extrusion, so their outlines disappear too.
    obj.modifiers.move(list(obj.modifiers).index(modifier), 0)
    for side in ('Left', 'Right'):
        socket = next(item for item in modifier.node_group.interface.items_tree
                      if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == side)
        set_modifier_property(modifier, socket.identifier, False)
        inputs = get_modifier_inputs(modifier)
        if inputs is not None:
            item = getattr(inputs, socket.identifier) if hasattr(
                inputs, socket.identifier) else inputs[socket.identifier]
            curve = item.driver_add('value')
        else:
            curve = modifier.driver_add(f'["{socket.identifier}"]')
        driver = curve.driver
        while driver.variables:
            driver.variables.remove(driver.variables[0])
        for name, input_name in (('shared', 'Expression'), ('eye', f'{side} Eye (-1 = shared)')):
            variable = driver.variables.new()
            variable.name = name
            variable.type = 'SINGLE_PROP'
            # Material node trees are embedded IDs; targeting them directly
            # loses the ID reference after reopening a .blend file.
            variable.targets[0].id_type = 'MATERIAL'
            variable.targets[0].id = material
            variable.targets[0].data_path = 'node_tree.' + \
                selector.inputs[input_name].path_from_id('default_value')
        driver.expression = '(eye if eye >= 0 else shared) != 0'


def _exclude_overlay_from_outlines(face, material):
    """Bypass outline material reassignment for the transparent overlay shell."""
    for modifier in face.modifiers:
        if modifier.type != 'NODES' or not modifier.node_group or 'outline' not in modifier.name.lower():
            continue
        group = modifier.node_group.copy()
        group.name = modifier.node_group.name + ' - Expression Overlay'
        modifier.node_group = group
        incoming = [link for link in group.links
                    if link.from_node.type == 'GROUP_INPUT' and link.from_socket.name == 'Geometry']
        output = next(node for node in group.nodes if node.type ==
                      'GROUP_OUTPUT' and node.is_active_output)
        previous = output.inputs['Geometry'].links[0].from_socket
        selection = group.nodes.new('GeometryNodeMaterialSelection')
        selection.inputs['Material'].default_value = material
        no_outline = group.nodes.new('GeometryNodeInputNamedAttribute')
        no_outline.data_type = 'BOOLEAN'
        no_outline.inputs['Name'].default_value = NO_OUTLINE
        either = group.nodes.new('FunctionNodeBooleanMath')
        either.operation = 'OR'
        group.links.new(selection.outputs['Selection'], either.inputs[0])
        group.links.new(no_outline.outputs['Attribute'], either.inputs[1])
        separate = group.nodes.new('GeometryNodeSeparateGeometry')
        separate.domain = 'FACE'
        group.links.new(
            either.outputs[0], separate.inputs['Selection'])
        group.links.new(incoming[0].from_socket, separate.inputs['Geometry'])
        for link in incoming:
            target = link.to_socket
            group.links.remove(link)
            group.links.new(separate.outputs['Inverted'], target)
        join = group.nodes.new('GeometryNodeJoinGeometry')
        group.links.new(previous, join.inputs['Geometry'])
        group.links.new(separate.outputs['Selection'], join.inputs['Geometry'])
        group.links.new(join.outputs['Geometry'], output.inputs['Geometry'])


def _project_cover(obj, fit):
    projection = obj.data.attributes.get(UV) or obj.data.attributes.new(
        name=UV, type='FLOAT_VECTOR', domain='CORNER')
    for loop in obj.data.loops:
        point = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
        if projection.data_type == 'FLOAT2':
            obj.data.uv_layers[UV].data[loop.index].uv = (point.x - fit[0], point.z)
        else:
            projection.data[loop.index].vector = (point.x - fit[0], point.z, 0)


def _detached_eye_covers(face, components, cover, fit):
    """Find separate skin inserts sharing the alternate face's eye boundaries."""
    from mathutils.kdtree import KDTree
    vertices, polygons = cover[:2]
    mesh = face.data
    bounds = _bounds([mesh.vertices[i].co for i in vertices])
    scale = max(high - low for low, high in bounds)
    rims = [set(), set()]
    for edge in _eye_hole_edges(face, polygons, fit):
        for index in edge:
            point = face.matrix_world @ mesh.vertices[index].co
            rims[0 if point.x > fit[0] else 1].add(index)
    active_masks = set().union(*_eye_masks(face, components, cover, fit))
    detached = set()
    for other_vertices, other_polygons in components:
        # Only remove pieces already hidden for nonzero expressions. This
        # extends that cleanup to zero without changing any active expression.
        if not other_polygons or not set(other_polygons) <= active_masks:
            continue
        tree = KDTree(len(other_vertices))
        for number, index in enumerate(other_vertices):
            tree.insert(mesh.vertices[index].co, number)
        tree.balance()
        for rim in rims:
            if len(rim) < 8:
                continue
            shared = sum(tree.find(mesh.vertices[index].co)[2] < scale * .0001 for index in rim)
            # A cap may be split into several disconnected islands, each
            # sharing only a portion of the cover's eye-opening boundary.
            if shared >= max(3, min(len(rim), len(other_vertices)) * .2):
                detached.update(other_polygons)
                break
    return detached


def _replace_open_cover(face, vertices, polygons, material, fit):
    """Retain the authored neutral eye skin without duplicate skins or seam outlines."""
    bounds = _bounds([face.data.vertices[i].co for i in vertices])
    scale = max(high - low for low, high in bounds)
    cover_bounds = _bounds([face.matrix_world @ face.data.vertices[i].co for i in vertices])
    interior = set(range(len(face.data.polygons)))
    components = _components(face.data)
    for other_vertices, other_polygons in components:
        if other_vertices == vertices or len(other_vertices) < 150:
            continue
        other_bounds = _bounds(
            [face.matrix_world @ face.data.vertices[i].co for i in other_vertices])
        # Only the exterior jaw needs an inverted-hull face outline. Upper
        # skins and eyelid inserts have open borders inside the face; outlining
        # those borders produces black seams and wire-like eye patches.
        if (other_bounds[2][0] < cover_bounds[2][0] - scale * .02
                and other_bounds[0][1] - other_bounds[0][0] > scale * .45):
            interior.difference_update(other_polygons)
    detached = _detached_eye_covers(face, components, (vertices, polygons), fit)
    for name, selected in ((REPLACED_COVER, set(polygons) | detached), (NO_OUTLINE, interior)):
        attr = face.data.attributes.get(name) or face.data.attributes.new(name, 'BOOLEAN', 'FACE')
        attr.data.foreach_set('value', [i in selected for i in range(len(face.data.polygons))])
    _exclude_overlay_from_outlines(face, material)
    _mask_group()


def _expression_engine_links(tree, selector, output):
    """Keep Goo's native depth writer after the complete expression shader."""
    variants = json.loads(tree.get('gacha_goo_links', '{}'))
    for mode, links in variants.items():
        final = next((link for link in links if link[2] == output.name and
                      link[3] == output.inputs['Surface'].identifier), None)
        depth = tree.nodes.get(final[0]) if final else None
        shader_input = depth.inputs.get('Shader') if depth else None
        native_depth = (mode == 'native' and depth is not None and depth.type == 'GROUP'
                        and depth.node_tree is not None and shader_input is not None
                        and shader_input.type == 'SHADER' and
                        any(node.bl_idname == 'ShaderNodeSetDepth'
                            for node in depth.node_tree.nodes))
        upstream = next((link for link in links if native_depth and link[2] == depth.name
                         and link[3] == shader_input.identifier), None)
        if upstream:
            # Mixing an emission expression after Goo 4.1's depth writer
            # produces a white silhouette. Feed the expression into its
            # shader input instead, retaining depth and zero transparency.
            upstream[2:] = [selector.name, selector.inputs['Original Skin'].identifier]
            links.append([selector.name, selector.outputs['Shader'].identifier,
                          depth.name, shader_input.identifier])
            # Set Depth converts a transparent shader to opaque black. Apply
            # the per-eye visibility after depth so zero remains transparent.
            transparent = tree.nodes.new('ShaderNodeBsdfTransparent')
            transparent.name = 'Expression Zero Transparent'
            mix = tree.nodes.new('ShaderNodeMixShader')
            mix.name = 'Expression Visibility'
            mix.location = (output.location.x - 180, output.location.y)
            final[2:] = [mix.name, mix.inputs[2].identifier]
            links.extend([
                [transparent.name, transparent.outputs[0].identifier,
                 mix.name, mix.inputs[1].identifier],
                [selector.name, selector.outputs['Visibility'].identifier,
                 mix.name, mix.inputs[0].identifier],
                [mix.name, mix.outputs[0].identifier,
                 output.name, output.inputs['Surface'].identifier],
            ])
        else:
            if final:
                final[2:] = [selector.name, selector.inputs['Original Skin'].identifier]
            links.append([selector.name, selector.outputs['Shader'].identifier,
                          output.name, output.inputs['Surface'].identifier])
    if variants:
        tree['gacha_goo_links'] = json.dumps(variants)
    return bool(variants)


def _native_cover_visibility(obj, polygons, center):
    selected = set(polygons)
    left, right = set(), set()
    for poly in obj.data.polygons:
        if poly.index not in selected:
            continue
        x = sum((obj.matrix_world @ obj.data.vertices[i].co).x for i in poly.vertices)
        (left if x / len(poly.vertices) > center else right).add(poly.index)
    for name, faces in ((COVER_LEFT, left), (COVER_RIGHT, right)):
        attr = obj.data.attributes.new(name, 'BOOLEAN', 'FACE')
        attr.data.foreach_set('value', [i in faces for i in range(len(obj.data.polygons))])


def setup_face_expressions(arm):
    """Install once per compatible character; do not modify other characters."""
    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
    meshes = [obj for obj in _iter_rig_meshes(arm) if len(obj.data.materials)
              and not obj.name.startswith(('WGT-', 'ColorWheel-'))]
    existing = next(expression_nodes(arm), None)
    if existing:
        return False
    for face in meshes:
        if 'face' not in face.name.lower() or 'star' in face.name.lower():
            continue
        components = _components(face.data)
        overlay = _find_overlay(face, components)
        if overlay is None:
            continue
        fit = _eye_fit(meshes)
        if fit is None:
            continue
        # Preserve a mesh datablock shared by an appended duplicate character.
        for obj in meshes:
            if obj.data.users > 1:
                obj.data = obj.data.copy()
        vertices, polygons, index = overlay
        material = face.data.materials[index].copy()
        material.name = face.data.materials[index].name + ' - Expressions'
        if _eye_hole_edges(face, polygons, fit):
            expression_mesh = _make_closed_cover(face, vertices, material, fit)
            _replace_open_cover(face, vertices, polygons, material, fit)
        else:
            expression_mesh = face
            face.data.materials.append(material)
            expression_index = len(face.data.materials) - 1
            for index in polygons:
                face.data.polygons[index].material_index = expression_index
        # Native FBX imports may already use Blender's eight UV slots. A
        # generic corner vector projects the atlas without discarding any UV.
        center, spacing, height, width, window_height = fit
        _project_cover(expression_mesh, fit)
        tree = material.node_tree
        output = next(node for node in tree.nodes if node.type ==
                      'OUTPUT_MATERIAL' and node.is_active_output)
        original = output.inputs['Surface'].links[0].from_socket
        selector = tree.nodes.new('ShaderNodeGroup')
        selector.node_tree = _load_selector()
        selector.name = SELECTOR
        selector.label = 'Facial Expressions (0 = Original)'
        selector.location = (output.location.x - 240, output.location.y)
        selector.inputs['Expression'].default_value = 0
        selector.inputs['Eye Spacing'].default_value = spacing
        selector.inputs['Eye Height'].default_value = height
        selector.inputs['Width'].default_value = width
        selector.inputs['Height'].default_value = window_height
        tree.links.new(original, selector.inputs['Original Skin'])
        tree.links.new(selector.outputs['Shader'], output.inputs['Surface'])
        # Preserve the selector when native/portable engine links are repaired.
        if _expression_engine_links(tree, selector, output):
            from setup_wizard.utils.genshin_engine_nodes import configure_genshin_engine_nodes
            configure_genshin_engine_nodes([material])
        from setup_wizard.utils.genshin_engine_nodes import is_goo_engine
        if is_goo_engine():
            cover_faces = polygons if expression_mesh == face else range(len(expression_mesh.data.polygons))
            _native_cover_visibility(expression_mesh, cover_faces, center)
            if expression_mesh != face:
                _install_masks(expression_mesh, (set(), set()), selector, material)
        if expression_mesh == face:
            _exclude_overlay_from_outlines(face, material)
        for obj in meshes:
            if obj != face and not any(word in obj.name.lower() for word in
                                       ('eye', 'pupil', 'brow', 'iris', 'highlight', 'lash')):
                continue
            parts = components if obj == face else _components(obj.data)
            masks = _eye_masks(obj, parts, overlay if obj ==
                               face else None, fit)
            _install_masks(obj, masks, selector, material)
        arm['gacha_face_expressions'] = True
        from setup_wizard.ui.character_settings_utils import invalidate_caches
        invalidate_caches()
        return True
    return False


def setup_scene_face_expressions(scene):
    from setup_wizard.ui.character_settings_utils import detect_armature_game
    for arm in scene.objects:
        if arm.type == 'ARMATURE' and detect_armature_game(arm) == 'GENSHIN_IMPACT':
            setup_face_expressions(arm)


def draw_face_expressions(layout, arm):
    selector = next(expression_nodes(arm), None)
    if selector is None:
        return
    box = layout.box()
    box.label(text='Facial Expressions', icon='FACESEL')
    for name in ('Expression', 'Left Eye (-1 = shared)', 'Right Eye (-1 = shared)',
                 'Intensity', 'Scale', 'Rotation'):
        socket = selector.inputs.get(name)
        if socket is not None:
            box.prop(socket, 'default_value', text=name)
