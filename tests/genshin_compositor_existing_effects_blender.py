"""Preserve See Through, Hair Shadows, AOVs and grading on compositor reruns.

blender -b --factory-startup --python-exit-code 1 --python
tests/genshin_compositor_existing_effects_blender.py
"""
from pathlib import Path
import sys

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = ROOT / 'tests/.runtime/compositor-existing-effects' / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard.genshin_compositing_node_setup import get_node_tree, get_output_node_type
from setup_wizard.services.compositor_alpha_over import ensure_hoyoverse_alpha_over
from setup_wizard.utilites.compositor_effects import eye_group
from setup_wizard.utilites.hair_shadows import _group as hair_group

scene = bpy.context.scene
for name in ('Eye color', 'Eye mask'):
    aov = scene.view_layers[0].aovs.add()
    aov.name = name
    aov.type = 'COLOR'
tree = get_node_tree(scene)
tree.nodes.clear()
rl = tree.nodes.new('CompositorNodeRLayers')
eye = tree.nodes.new('CompositorNodeGroup')
eye.node_tree = eye_group()
eye.name = 'Eye See Through'
eye['csw_effect'] = 'eye'
eye.inputs['Opacity'].default_value = .37
hair = tree.nodes.new('CompositorNodeGroup')
hair.node_tree = hair_group('regression', scene)
hair.name = 'Hair Shadows'
hair['csw_effect'] = 'hair'
grade = tree.nodes.new('CompositorNodeExposure')
grade.inputs['Exposure'].default_value = .42
out = tree.nodes.new(get_output_node_type())
viewer = tree.nodes.new('CompositorNodeViewer')
tree.links.new(rl.outputs['Image'], eye.inputs['Image'])
tree.links.new(rl.outputs['Eye color'], eye.inputs['Eye Color'])
tree.links.new(rl.outputs['Eye mask'], eye.inputs['Eye Mask'])
tree.links.new(eye.outputs['Image'], hair.inputs['Image'])
tree.links.new(hair.outputs['Image'], grade.inputs['Image'])
tree.links.new(grade.outputs['Image'], out.inputs['Image'])
tree.links.new(grade.outputs['Image'], viewer.inputs['Image'])


def run(shader):
    scene.gi_shader_type = shader
    assert bpy.ops.hoyoverse.custom_composite_node_setup('EXEC_DEFAULT', game_type='GENSHIN_IMPACT') == {'FINISHED'}
    assert eye.inputs['Image'].links[0].from_node == rl
    assert hair.inputs['Image'].links[0].from_node == eye
    assert eye.inputs['Eye Color'].links[0].from_socket == rl.outputs['Eye color']
    assert eye.inputs['Eye Mask'].links[0].from_socket == rl.outputs['Eye mask']
    assert abs(eye.inputs['Opacity'].default_value - .37) < 1e-6
    assert abs(grade.inputs['Exposure'].default_value - .42) < 1e-6
    return tree.nodes['HoYoverse Post Processing']


post = run('OLD')
assert post.inputs['Image'].links[0].from_node == grade
assert grade.inputs['Image'].links[0].from_node == hair
assert out.inputs['Image'].links[0].from_node == post

# Move user grading downstream, then change shaders and rerun repeatedly.
tree.links.new(hair.outputs['Image'], post.inputs['Image'])
tree.links.new(post.outputs[0], grade.inputs['Image'])
tree.links.new(grade.outputs['Image'], out.inputs['Image'])
tree.links.new(grade.outputs['Image'], viewer.inputs['Image'])
counts = len(tree.nodes), len(tree.links)
for shader in ('OLD', 'NEW', 'NEW', 'OLD'):
    post = run(shader)
    assert counts == (len(tree.nodes), len(tree.links))
    assert post.inputs['Image'].links[0].from_node == hair
    assert grade.inputs['Image'].links[0].from_node == post
    assert out.inputs['Image'].links[0].from_node == grade
    assert viewer.inputs['Image'].links[0].from_node == grade
    group = post.node_tree
    assert len([n for n in group.nodes if n.bl_idname == 'CompositorNodeAlphaOver']) == 1
    print('GENSHIN_EXISTING_EFFECTS_PASS', shader, flush=True)

# A separate viewer branch must keep its own source.
tree.links.new(eye.outputs['Image'], viewer.inputs['Image'])
run('NEW')
assert viewer.inputs['Image'].links[0].from_node == eye

# Preserve effects added inside the post-processing group as well.
group = post.node_tree
alpha = next(n for n in group.nodes if n.bl_idname == 'CompositorNodeAlphaOver')
background = alpha.inputs.get('Background') or alpha.inputs[1]
foreground = alpha.inputs.get('Foreground') or alpha.inputs[2]
tone = background.links[0].from_socket
inner_grade = group.nodes.new('CompositorNodeExposure')
group.links.new(tone, inner_grade.inputs['Image'])
group.links.new(inner_grade.outputs['Image'], background)
inner_eye = group.nodes.new('CompositorNodeGroup')
inner_eye.node_tree = eye_group()
raw = next(n for n in group.nodes if n.type == 'GROUP_INPUT').outputs['Image']
bloom = next(n for n in group.nodes if n.type == 'GROUP' and n.node_tree.name.startswith('Genshin Bloom'))
group.links.new(raw, inner_eye.inputs['Image'])
group.links.new(inner_eye.outputs['Image'], bloom.inputs['Image'])
inner_output = next(n for n in group.nodes if n.type == 'GROUP_OUTPUT' and n.is_active_output)
after = group.nodes.new('CompositorNodeExposure')
group.links.new(alpha.outputs['Image'], after.inputs['Image'])
group.links.new(after.outputs['Image'], inner_output.inputs['Image'])
counts = len(group.nodes), len(group.links)
for repeat in range(2):
    assert ensure_hoyoverse_alpha_over(group)
    assert background.links[0].from_node == inner_grade
    assert foreground.links[0].from_node == inner_eye
    assert inner_output.inputs['Image'].links[0].from_node == after
    assert counts == (len(group.nodes), len(group.links))
print('GENSHIN_INTERNAL_EFFECTS_PASS', flush=True)
