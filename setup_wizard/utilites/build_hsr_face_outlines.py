"""Bake camera-free face outlines using Blender 4.5 (run as --python).

The geometry shell preserves authored vertex alpha. View-dependent visibility
lives in the material, where Blender supplies the current viewport/render ray.
"""
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'setup_wizard/shaders/hsr/StellarToonV1.1.blend'
MASK_NAME = 'StellarToon - Face View Mask'
STRENGTH = 'gacha_hsr_face_view_mask'


def build_view_mask():
    group = bpy.data.node_groups.new(MASK_NAME, 'ShaderNodeTree')
    group.use_fake_user = True
    group['gacha_hsr_face_view_mask'] = 1
    group.interface.new_socket(name='Outline', in_out='INPUT', socket_type='NodeSocketShader')
    group.interface.new_socket(name='Outline', in_out='OUTPUT', socket_type='NodeSocketShader')
    group.interface.new_socket(name='Visibility', in_out='OUTPUT', socket_type='NodeSocketFloat')
    nodes, links = group.nodes, group.links

    def node(kind, name, x, y):
        result = nodes.new(kind)
        result.name = result.label = name
        result.location = (x, y)
        return result

    def math(name, operation, a, b, x, y):
        result = node('ShaderNodeMath', name, x, y)
        result.operation = operation
        for index, value in enumerate((a, b)):
            if isinstance(value, (float, int)):
                result.inputs[index].default_value = value
            elif value is not None:
                links.new(value, result.inputs[index])
        return result.outputs[0]

    def vector(name, operation, a, b, x, y):
        result = node('ShaderNodeVectorMath', name, x, y)
        result.operation = operation
        links.new(a, result.inputs[0])
        if b is not None:
            links.new(b, result.inputs[1])
        return result.outputs['Value' if operation == 'DOT_PRODUCT' else 'Vector']

    incoming = node('ShaderNodeNewGeometry', 'Current View Direction', -1100, 400)
    up = node('ShaderNodeAttribute', 'Animated Head Up', -1100, 100)
    up.attribute_name = 'headUp'
    forward = node('ShaderNodeAttribute', 'Animated Head Forward', -1100, -150)
    forward.attribute_name = 'headForward'
    up_vector = vector('Normalize Head Up', 'NORMALIZE', up.outputs['Vector'], None, -850, 100)
    forward_vector = vector('Normalize Head Forward', 'NORMALIZE', forward.outputs['Vector'], None, -850, -150)
    right = vector('Head Right', 'CROSS_PRODUCT', forward_vector, up_vector, -600, -150)
    right = vector('Normalize Head Right', 'NORMALIZE', right, None, -400, -150)
    vertical = vector('Vertical View', 'DOT_PRODUCT', incoming.outputs['Incoming'], up_vector, -600, 400)
    profile = vector('Profile View', 'DOT_PRODUCT', incoming.outputs['Incoming'], right, -180, -150)
    vertical = math('Vertical Magnitude', 'ABSOLUTE', vertical, None, -400, 400)
    vertical = math('Vertical Falloff', 'POWER', vertical, 7.39, -180, 400)
    vertical = math('Vertical Suppression', 'MULTIPLY', vertical, 420., 40, 400)
    vertical.node.use_clamp = True
    profile = math('Profile Magnitude', 'ABSOLUTE', profile, None, 40, -150)
    profile = math('Profile Bias', 'ADD', profile, .04, 260, -150)
    profile = math('Profile Falloff', 'POWER', profile, 6.3, 480, -150)
    ramp = node('ShaderNodeValToRGB', 'Profile Transition', 700, -150)
    ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements[0].position = .54090905
    ramp.color_ramp.elements[1].position = 1.
    links.new(profile, ramp.inputs[0])
    colors = node('ShaderNodeVertexColor', 'Authored Face Regions', 40, -500)
    colors.layer_name = 'Col'
    separate = node('ShaderNodeSeparateRGB', 'Region Channels', 260, -500)
    links.new(colors.outputs['Color'], separate.inputs[0])
    blue = math('Blue Region', 'GREATER_THAN', separate.outputs['B'], .5, 480, -450)
    green = math('Green Region', 'GREATER_THAN', separate.outputs['G'], .5, 480, -650)
    vertical = math('Vertical Region Mask', 'MULTIPLY', vertical, blue, 1020, 400)
    profile = math('Profile Region Mask', 'MULTIPLY', ramp.outputs['Color'], green, 1020, -150)
    vertical = math('Vertical Visibility', 'SUBTRACT', 1., vertical, 1240, 400)
    profile = math('Profile Visibility', 'SUBTRACT', 1., profile, 1240, -150)
    visibility = math('Combined Visibility', 'MULTIPLY', vertical, profile, 1460, 250)
    hidden = math('Hidden Regions', 'SUBTRACT', 1., visibility, 1680, 250)
    strength = node('ShaderNodeAttribute', 'Modifier View Mask', 1460, -350)
    strength.attribute_name = STRENGTH
    hidden = math('Modifier Mask Strength', 'MULTIPLY', hidden, strength.outputs['Fac'], 1900, 250)
    visibility = math('Final Visibility', 'SUBTRACT', 1., hidden, 2120, 250)
    visibility.node.use_clamp = True
    source = node('NodeGroupInput', 'Original Outline', 1900, -200)
    transparent = node('ShaderNodeBsdfTransparent', 'Hidden Outline', 2120, -400)
    mix = node('ShaderNodeMixShader', 'View-aware Outline', 2360, 100)
    links.new(visibility, mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(source.outputs['Outline'], mix.inputs[2])
    output = node('NodeGroupOutput', 'Outline Output', 2580, 100)
    links.new(mix.outputs[0], output.inputs['Outline'])
    links.new(visibility, output.inputs['Visibility'])
    return group


def build_geometry():
    group = bpy.data.node_groups['StellarToon - Outlines FACE']
    nodes, links = group.nodes, group.links
    dynamic = group['dynamic_socket']
    # Restore the shell width path, independent of scene view transforms.
    links.new(nodes['Reroute.018'].outputs[0], nodes['Math.001'].inputs[0])
    for node_name, index, value in (
            ('Vector Math.007', 1, (1., 1., 1.)),
            ('Vector Math.011', 1, (0., 0., 0.))):
        socket = nodes[node_name].inputs[index]
        for link in list(socket.links):
            links.remove(link)
        socket.default_value = value
    # Remove dead camera, distance and old dynamic-mask branches.
    live = set()
    def visit(node):
        if node in live:
            return
        live.add(node)
        for socket in node.inputs:
            for link in socket.links:
                visit(link.from_node)
    for node in nodes:
        if node.type == 'GROUP_OUTPUT':
            visit(node)
    for node in list(nodes):
        if node not in live:
            nodes.remove(node)
    for socket in list(group.interface.items_tree):
        if socket.item_type != 'SOCKET' or socket.in_out != 'INPUT':
            continue
        if socket.identifier == dynamic:
            socket.name = 'View-aware Face Outlines'
            socket.default_value = 1.
            socket.description = 'Filter face regions using the current viewport or render view; no camera object required'
        elif socket.name in ('Camera', 'Screen Space Switch', 'Head Origin') or 'Distance Mult' in socket.name or 'Depth Offset Multiplier' in socket.name:
            group.interface.remove(socket)
        elif socket.identifier == 'Input_8':
            socket.default_value = 0.
            socket.hide_in_modifier = True
    source = next(node for node in nodes if node.type == 'GROUP_INPUT')
    strength = nodes.new('ShaderNodeMath')
    strength.name = strength.label = 'View Mask Strength'
    strength.operation = 'MULTIPLY'
    strength.location = (-650, 800)
    links.new(source.outputs[dynamic], strength.inputs[0])
    links.new(source.outputs['Input_13'], strength.inputs[1])
    store = nodes.new('GeometryNodeStoreNamedAttribute')
    store.name = store.label = 'Face Material View Mask'
    store.data_type = 'FLOAT'
    store.domain = 'POINT'
    store.inputs['Name'].default_value = STRENGTH
    store.location = (-400, 800)
    links.new(source.outputs['Input_0'], store.inputs['Geometry'])
    links.new(strength.outputs[0], store.inputs['Value'])
    links.new(store.outputs['Geometry'], nodes['Reroute.003'].inputs[0])
    group['gacha_hsr_face_outlines'] = 2
    group['camera_free'] = 1
    if 'head_socket' in group:
        del group['head_socket']
    group.use_fake_user = True
    return group


def wrap_material(material, group):
    tree = material.node_tree
    for output in [n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL']:
        surface = output.inputs['Surface']
        if not surface.is_linked:
            continue
        source = surface.links[0].from_socket
        wrapper = tree.nodes.new('ShaderNodeGroup')
        wrapper.node_tree = group
        wrapper.name = wrapper.label = 'HSR Face View Mask'
        wrapper.location = (output.location.x - 220, output.location.y)
        tree.links.new(source, wrapper.inputs['Outline'])
        tree.links.new(wrapper.outputs['Outline'], surface)


def clean_interior_contours(group, view_mask):
    """Remove blue-marked inner folds only from the inverted outline shell."""
    if 'interior_mask_socket' not in group:
        control = group.interface.new_socket(name='Clean Mouth and Nose Contours', in_out='INPUT', socket_type='NodeSocketBool')
        control.default_value = True
        control.description = 'Prevent stray outline strokes across the lips and chin; preserve the original face'
        group['interior_mask_socket'] = control.identifier
        nodes, links = group.nodes, group.links
        source = next(n for n in nodes if n.type == 'GROUP_INPUT')
        region = nodes.new('ShaderNodeMath')
        region.name = region.label = 'Interior Face Region'
        region.operation = 'GREATER_THAN'
        region.inputs[1].default_value = .001
        region.location = (-650, 450)
        links.new(nodes['Separate RGB'].outputs['Blue'], region.inputs[0])
        enabled = nodes.new('FunctionNodeBooleanMath')
        enabled.name = enabled.label = 'Use Authored Face Regions'
        enabled.operation = 'AND'
        enabled.location = (-650, 200)
        links.new(source.outputs[control.identifier], enabled.inputs[0])
        links.new(source.outputs['Input_13'], enabled.inputs[1])
        selection = nodes.new('FunctionNodeBooleanMath')
        selection.name = selection.label = 'Clean Interior Selection'
        selection.operation = 'AND'
        selection.location = (-400, 450)
        links.new(enabled.outputs[0], selection.inputs[0])
        links.new(region.outputs[0], selection.inputs[1])
        delete = nodes.new('GeometryNodeDeleteGeometry')
        delete.name = delete.label = 'Exclude Interior Face Hull'
        delete.domain = 'FACE'
        delete.mode = 'ALL'
        delete.location = (-150, 450)
        links.new(nodes['Merge by Distance'].outputs['Geometry'], delete.inputs['Geometry'])
        links.new(selection.outputs[0], delete.inputs['Selection'])
        links.new(delete.outputs['Geometry'], nodes['Set Position'].inputs['Geometry'])
    # BYTE_COLOR face markers at 0.5 sRGB evaluate near 0.216 in linear space.
    # Detect painted regions, rather than testing for a linear value above 0.5.
    for name in ('Blue Region', 'Green Region'):
        view_mask.nodes[name].inputs[1].default_value = .001
    view_mask['gacha_hsr_face_view_mask'] = 2
    group['gacha_hsr_face_outlines'] = 3


if __name__ == '__main__':
    assert bpy.app.version[:2] == (4, 5), bpy.app.version
    bpy.ops.wm.open_mainfile(filepath=str(PATH))
    assert bpy.data.version[:2] == (4, 5), bpy.data.version
    geometry = bpy.data.node_groups['StellarToon - Outlines FACE']
    if geometry.get('gacha_hsr_face_outlines') == 3:
        print('HSR_CAMERA_FREE_SHADER_ALREADY_BAKED', flush=True)
        raise SystemExit(0)
    if geometry.get('camera_free'):
        shader = bpy.data.node_groups[MASK_NAME]
    else:
        shader = build_view_mask()
        geometry = build_geometry()
        wrap_material(bpy.data.materials['StellarToon - Face Outlines'], shader)
    clean_interior_contours(geometry, shader)
    preview = bpy.data.objects['Face Preview']
    modifier = next(m for m in preview.modifiers if m.type == 'NODES' and m.node_group == geometry)
    modifier[geometry['dynamic_socket']] = 1.
    modifier['Input_8'] = 0.
    modifier['Input_3_attribute_name'] = 'Col'
    modifier['Input_3_use_attribute'] = True
    modifier[geometry['interior_mask_socket']] = True
    # The preview relies on the same world-space head basis as characters.
    light_vectors = next(m for m in preview.modifiers if m.type == 'NODES' and m.node_group.name.startswith('Light Vectors'))
    light_vectors['Output_8_attribute_name'] = 'headForward'
    light_vectors['Output_9_attribute_name'] = 'headUp'
    camera = bpy.data.objects.get('Face Preview Camera')
    if camera:
        data = camera.data
        bpy.data.objects.remove(camera, do_unlink=True)
        if data.users == 0:
            bpy.data.cameras.remove(data)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(PATH), compress=True)
    print('HSR_CAMERA_FREE_SHADER_BAKED', bpy.app.version, len(geometry.nodes), len(shader.nodes), flush=True)
