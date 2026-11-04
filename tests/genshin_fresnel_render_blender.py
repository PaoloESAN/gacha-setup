"""Render handlers must preserve Genshin colors and their lighting links.

blender -b --factory-startup --python-exit-code 1 --python
tests/genshin_fresnel_render_blender.py
"""
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/fresnel-render-regression' / str(bpy.app.version[:2])
RUNTIME.mkdir(parents=True, exist_ok=True)
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        target = RUNTIME / kind / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.wuwa_operations import update_fresnel, wuwa_frame_change_handler

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def properties(name, color):
    tree = bpy.data.node_groups.new('Global Material Properties ' + name, 'ShaderNodeTree')
    tree.interface.new_socket(name='Fresnel Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    output = tree.nodes.new('NodeGroupOutput')
    output.name = 'Global Properties'
    rgb = tree.nodes.new('ShaderNodeRGB')
    rgb.outputs[0].default_value = (*color, 1)
    tree.links.new(rgb.outputs[0], output.inputs['Fresnel Color'])
    return tree, output, rgb


def character(name, game, color):
    arm = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    arm['gacha_game'] = game
    scene.collection.objects.link(arm)
    bpy.ops.mesh.primitive_plane_add()
    mesh = bpy.context.object
    mesh.parent = arm
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    mesh.data.materials.append(material)
    nodes = material.node_tree.nodes
    nodes.clear()
    surface = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    group = nodes.new('ShaderNodeGroup')
    tree, output, rgb = properties(name, color)
    group.node_tree = tree
    material.node_tree.links.new(group.outputs['Fresnel Color'], emission.inputs['Color'])
    material.node_tree.links.new(emission.outputs[0], surface.inputs['Surface'])
    return arm, mesh, tree, output, rgb


gi, plane, gi_tree, gi_output, gi_color = character('Genshin', 'GENSHIN_IMPACT', (.01, .6, .02))
ww, ww_mesh, ww_tree, ww_output, _ = character('WuWa', 'WUTHERING_WAVES', (.2, .3, .4))
ww_mesh.hide_render = True
orphan, orphan_output, orphan_color = properties('Unused', (.2, .4, .8))
orphan_links = tuple(orphan.links)


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


camera = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
scene.collection.objects.link(camera)
camera.location = (0, 0, 3)
scene.camera = camera
scene.render.engine = 'BLENDER_EEVEE' if bpy.app.version >= (5, 0, 0) else 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.use_compositing = False
bpy.app.handlers.render_init.append(wuwa_frame_change_handler)
bpy.app.handlers.frame_change_post.append(wuwa_frame_change_handler)
activate(gi)
for label, color, channel in [('green', (.01, .6, .02), 1), ('red', (.6, .01, .02), 0)]:
    gi_color.outputs[0].default_value = (*color, 1)
    scene.frame_set(scene.frame_current + 1)
    path = RUNTIME / (label + '.png')
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    link = gi_output.inputs['Fresnel Color'].links[0]
    assert link.from_node == gi_color, 'Render destroyed the Genshin lighting link'
    assert max(abs(a-b) for a, b in zip(gi_color.outputs[0].default_value[:3], color)) < 1e-6
    image = bpy.data.images.load(str(path), check_existing=False)
    index = (16 * 32 + 16) * 4
    pixel = list(image.pixels[index:index + 3])
    assert pixel[channel] > max(pixel[i] for i in range(3) if i != channel) * 2, (label, pixel)

# An explicit WuWa color edit still works and leaves Genshin and unused groups alone.
bpy.types.Scene.ww_fresnel_color = bpy.props.FloatVectorProperty(size=3, subtype='COLOR')
scene.ww_fresnel_color = (.1, .2, .8)
activate(ww)
update_fresnel(scene, bpy.context)
assert not ww_output.inputs['Fresnel Color'].links
assert max(abs(a-b) for a, b in zip(ww_output.inputs['Fresnel Color'].default_value[:3], (.1, .2, .8))) < 1e-6
assert gi_output.inputs['Fresnel Color'].links[0].from_node == gi_color
assert tuple(orphan.links) == orphan_links

# No material target must never fall back to every Global Properties group.
empty = bpy.data.objects.new('Empty WuWa rig', bpy.data.armatures.new('Empty WuWa rig'))
empty['gacha_game'] = 'WUTHERING_WAVES'
scene.collection.objects.link(empty)
activate(empty)
update_fresnel(scene, bpy.context)
assert gi_output.inputs['Fresnel Color'].links[0].from_node == gi_color
assert tuple(orphan.links) == orphan_links
activate(camera)
wuwa_frame_change_handler(scene)
assert gi_output.inputs['Fresnel Color'].links[0].from_node == gi_color
print('GENSHIN_FRESNEL_RENDER_PASS: two renders, frame changes, editable color, linked controls, WuWa isolation', flush=True)
