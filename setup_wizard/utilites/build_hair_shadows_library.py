"""Rebuild from scratch with Blender 4.5 --factory-startup --background --python.

No newer .blend is loaded. Legacy compositor nodes reproduce Sandrone/Danica
and are converted by Blender itself when appended into newer versions.
"""
from pathlib import Path

import bpy


def build():
    if bpy.app.version[:2] != (4, 5):
        raise RuntimeError('Build this library with Blender 4.5.')
    group = bpy.data.node_groups.new('Sandrone Hair Shadow - Danica', 'CompositorNodeTree')
    group['csw_hair_shadow_template'] = True
    group['csw_library_version'] = 1
    group['csw_library_blender'] = bpy.app.version_string
    inputs = (
        ('Image', 'NodeSocketColor', (0, 0, 0, 1)),
        ('Depth', 'NodeSocketFloat', 0),
        ('face_mask', 'NodeSocketFloat', 0),
        ('hair_mask', 'NodeSocketFloat', 0),
        ('Offset X', 'NodeSocketFloat', 1.5),
        ('Offset Y', 'NodeSocketFloat', -16.6),
        ('Threshold', 'NodeSocketFloat', .006),
        ('Fadeout', 'NodeSocketFloat', .2),
        ('Strength', 'NodeSocketFloat', 1),
        ('Shadow Tint', 'NodeSocketColor', (.64, .57, .66, 1)),
        ('Camera Distance', 'NodeSocketFloat', 0),
        ('Distance Fade Start', 'NodeSocketFloat', .7),
        ('Distance Fade End', 'NodeSocketFloat', 1),
    )
    for name, kind, default in inputs:
        item = group.interface.new_socket(name=name, in_out='INPUT', socket_type=kind)
        item.default_value = default
    for name, kind in (('Image', 'NodeSocketColor'), ('Shadow Mask', 'NodeSocketFloat')):
        group.interface.new_socket(name=name, in_out='OUTPUT', socket_type=kind)

    def node(kind, name):
        n = group.nodes.new(kind)
        n.name = n.label = name
        return n

    def link(source, dest):
        group.links.new(source, dest)

    def math(name, operation, a, b):
        n = node('CompositorNodeMath', name)
        n.operation = operation
        for index, value in enumerate((a, b)):
            if isinstance(value, (float, int)):
                n.inputs[index].default_value = value
            else:
                link(value, n.inputs[index])
        return n.outputs[0]

    controls = node('NodeGroupInput', 'Controls')
    output = node('NodeGroupOutput', 'Output')
    c = controls.outputs
    render_scale = node('CompositorNodeValue', 'Render Scale')
    render_scale.outputs[0].default_value = 1
    driver = render_scale.outputs[0].driver_add('default_value').driver
    driver.expression = 'percentage / 100'
    variable = driver.variables.new()
    variable.name, variable.type = 'percentage', 'SINGLE_PROP'
    variable.targets[0].id_type = 'SCENE'
    variable.targets[0].data_path = 'render.resolution_percentage'
    # Intentionally unbound in the library; Append binds the destination scene.
    x = math('Scale Offset X', 'MULTIPLY', c['Offset X'], render_scale.outputs[0])
    y = math('Scale Offset Y', 'MULTIPLY', c['Offset Y'], render_scale.outputs[0])
    samples = []
    for name, source in (('Sample Depth', c['Depth']), ('Sample Hair', c['hair_mask'])):
        n = node('CompositorNodeTranslate', name)
        n.use_relative = False
        n.interpolation = 'BILINEAR'
        link(source, n.inputs['Image'])
        link(x, n.inputs['X'])
        link(y, n.inputs['Y'])
        samples.append(n.outputs[0])
    biased = math('View Depth minus Threshold', 'SUBTRACT', c['Depth'], c['Threshold'])
    difference = math('Sample minus Biased Depth', 'SUBTRACT', samples[0], biased)
    multiplied = math('Danica Multiply 50', 'MULTIPLY', difference, 50)
    divided = math('Danica Divide Fadeout', 'DIVIDE', multiplied, c['Fadeout'])
    clamp = node('CompositorNodeMapRange', 'Danica Clamp Visibility')
    clamp.use_clamp = True
    for index, value in enumerate((0, 0, 1, 0, 1)):
        clamp.inputs[index].default_value = value
    link(divided, clamp.inputs[0])
    inverted = math('Invert Visibility', 'SUBTRACT', 1, clamp.outputs[0])
    coverage = math('Hair Coverage', 'MULTIPLY', samples[1], c['face_mask'])
    mask = math('Hair on Face', 'MULTIPLY', inverted, coverage)
    strength = math('Shadow Strength', 'MULTIPLY', mask, c['Strength'])
    fade = node('CompositorNodeMapRange', 'Camera Distance Fade')
    fade.use_clamp = True
    link(c['Camera Distance'], fade.inputs[0])
    link(c['Distance Fade Start'], fade.inputs[1])
    link(c['Distance Fade End'], fade.inputs[2])
    fade.inputs[3].default_value = 1
    fade.inputs[4].default_value = 0
    mask = math('Apply Distance Fade', 'MULTIPLY', strength, fade.outputs[0])
    mix = node('CompositorNodeMixRGB', 'Apply Hair Shadow')
    mix.blend_type = 'MULTIPLY'
    mix.use_clamp = False
    mix.use_alpha = False
    link(mask, mix.inputs[0])
    link(c['Image'], mix.inputs[1])
    link(c['Shadow Tint'], mix.inputs[2])
    link(mix.outputs[0], output.inputs['Image'])
    link(mask, output.inputs['Shadow Mask'])
    controls.location, output.location = (-950, 0), (1000, 0)
    for index, n in enumerate(n for n in group.nodes if n not in (controls, output)):
        n.location = (-700 + index // 5 * 270, 400 - index % 5 * 210)
    destination = Path(__file__).with_name('hair_shadows.blend')
    bpy.data.libraries.write(str(destination), {group}, fake_user=True, compress=True)
    print(f'BUILT FROM SCRATCH: {destination} using Blender {bpy.app.version_string}')
    return group


if __name__ == '__main__':
    build()
