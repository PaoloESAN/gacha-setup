"""Blender 5.2: character isolation, effect migration, chains and actual pixels."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.common.blender_executor import enable_addons, clear_scene
enable_addons()
from setup_wizard.utilites.hair_shadows import execute_hair_shadows
from setup_wizard.utilites.eye_through_hair import ensure_aov_passes, setup_compositor_nodes, get_or_create_compositor_tree
from setup_wizard.utilites.compositor_effects import render_layer, ensure_output


def material(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    tree = m.node_tree
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = color
    output = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
    tree.links.new(emission.outputs[0], output.inputs['Surface'])
    return m


def plane(name, mat, rig, z, size):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    o.parent = rig
    return o


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def effects(tree, kind):
    return [n for n in tree.nodes if n.get('csw_effect') == kind]


clear_scene()
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 96
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'OPEN_EXR'
scene.view_settings.view_transform = 'Standard'
scene.world.color = (0, 0, 0)
face_mat = material('Test Face', (1, 1, 1, 1))
hair_mat = material('Test Hair', (.2, .2, .2, 1))
rigs = []
for name in ('Character A', 'Character B'):
    rig = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    scene.collection.objects.link(rig)
    face = plane(name + ' Face', face_mat, rig, 0, 2)
    hair = plane(name + ' Bangs', hair_mat, rig, .1, .8)
    eye = plane(name + ' EyeStar', face_mat, rig, .01, .15)
    rigs.append((rig, face, hair, eye))
rigs[1][0].location.x = 10
activate(rigs[0][2])  # A mesh selection must find all meshes of its rig.
assert bpy.ops.setup_wizard.hair_shadows() == {'FINISHED'}
tree = get_or_create_compositor_tree(scene)
hair = effects(tree, 'hair')[0]
assert hair.node_tree.name.startswith('Hair Shadows')
controls = [s.name for s in hair.inputs if not s.hide and not s.is_linked]
assert controls == ['Offset X', 'Offset Y', 'Strength', 'Shadow Tint'], controls
assert len(bpy.context.view_layer.aovs) == 3
assert rigs[0][1].active_material != rigs[1][1].active_material, 'Shared material was not isolated'
assert not any(n.type == 'OUTPUT_AOV' for n in rigs[1][1].active_material.node_tree.nodes)
face_attr = next(a for a in rigs[0][1].data.attributes if a.name.startswith('csw_hs_') and a.name.endswith('_face'))
eye_attr = rigs[0][3].data.attributes[face_attr.name]
assert all(v.value == 1 for v in face_attr.data)
assert all(v.value == 0 for v in eye_attr.data), ('Eye geometry received facial shadow', rigs[0][3].name, eye_attr.name, [v.value for v in eye_attr.data])
hair.inputs['Strength'].default_value = .3
hair.inputs['Offset Y'].default_value = .7
counts = (len(tree.nodes), len(bpy.data.materials), len(bpy.data.node_groups))
assert execute_hair_shadows(bpy.context)[0]
assert counts == (len(tree.nodes), len(bpy.data.materials), len(bpy.data.node_groups))
assert abs(hair.inputs['Strength'].default_value - .3) < 1e-6
assert abs(hair.inputs['Offset Y'].default_value - .7) < 1e-6

# Eye utility wraps old math/mix nodes, retaining opacity and grading consumers.
ensure_aov_passes(bpy.context.view_layer)
rl = render_layer(tree, scene)
legacy_math = tree.nodes.new('ShaderNodeMath')
legacy_math.name = 'Math (Eye Through Hair Multiply)'
legacy_math.operation = 'MULTIPLY'
legacy_math.inputs[1].default_value = .27
legacy_mix = tree.nodes.new('ShaderNodeMix')
legacy_mix.name = 'Mix (Eye Through Hair)'
legacy_mix.data_type = 'RGBA'
tree.links.new(rl.outputs['Image'], legacy_mix.inputs[6])
tree.links.new(legacy_math.outputs[0], legacy_mix.inputs[0])
tree.links.new(legacy_mix.outputs[2], hair.inputs['Image'])
assert setup_compositor_nodes(scene)
eye = effects(tree, 'eye')[0]
assert abs(eye.inputs['Opacity'].default_value - .27) < 1e-6
assert hair.inputs['Image'].links[0].from_node == eye
assert [s.name for s in eye.inputs if not s.is_linked] == ['Opacity']
assert 'Math (Eye Through Hair Multiply)' not in tree.nodes and 'Mix (Eye Through Hair)' not in tree.nodes
assert setup_compositor_nodes(scene)
assert execute_hair_shadows(bpy.context)[0]
assert len(effects(tree, 'eye')) == len(effects(tree, 'hair')) == 1
assert hair.inputs['Image'].links[0].from_node == eye

# A second character gets its own passes and controls without changing A.
rigs[1][0]['csw_hair_shadow_id'] = rigs[0][0]['csw_hair_shadow_id']  # Copied rig properties.
activate(rigs[1][0])
assert execute_hair_shadows(bpy.context)[0]
assert rigs[1][0]['csw_hair_shadow_id'] != rigs[0][0]['csw_hair_shadow_id']
assert len(effects(tree, 'hair')) == 2
assert len(bpy.context.view_layer.aovs) == 8
assert abs(hair.inputs['Strength'].default_value - .3) < 1e-6

# Render the first character to verify the compositor actually produces shadow.
activate(rigs[0][0])
bpy.ops.object.camera_add(location=(0, 0, .5))
camera = bpy.context.object
camera.data.type, camera.data.ortho_scale = 'ORTHO', 2.4
scene.camera = camera
hair.inputs['Shadow Tint'].default_value = (.1, .1, .1, 1)
hair.inputs['Offset Y'].default_value = -math.pi / 2
output_dir = ROOT / '.tmp' / 'hair-effects-check'
output_dir.mkdir(parents=True, exist_ok=True)


def render(opacity, direction):
    hair.inputs['Strength'].default_value = opacity
    hair.inputs['Offset Y'].default_value = math.sin(direction) * 16.6
    scene.render.filepath = str(output_dir / 'check.exr')
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath, check_existing=False)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    return pixels


off = render(0, -math.pi / 2)
on = render(1, -math.pi / 2)
opposite = render(1, math.pi / 2)
print('PIXELS:', min(off), max(off), min(on), max(on), 'delta', max(a - b for a, b in zip(off, on)), flush=True)
assert max(a - b for a, b in zip(off, on)) > .05, 'No visible hair shadow'
assert max(abs(a - b) for a, b in zip(on, opposite)) > .05, 'Direction does not change shadow'
assert all(math.isfinite(v) for v in on), 'Invalid rendered pixels'
assert bpy.ops.setup_wizard.create_camera_pro() == {'FINISHED'}
assert bpy.context.scene.camera is not None
assert hasattr(bpy.types, 'CSW_PT_Utilities_UI_Layout')
print('PASS: character-scoped masks/materials/AOVs; migration; repeat setup; combined effects; opacity and direction change rendered pixels')
