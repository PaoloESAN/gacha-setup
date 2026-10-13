"""Run with Blender --background --factory-startup --python-exit-code 1
--python tests/disable_rigging_lighting_blender.py.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
addon_utils.enable('setup_wizard', default_set=False)

from setup_wizard.character_rig_setup.rigify_character_service import RigifyCharacterService
import setup_wizard

assert Path(setup_wizard.__file__).resolve().parent == ROOT / 'setup_wizard', (
    'Use --factory-startup to test the workspace addon instead of an installed copy')

# Two already configured characters with independent lighting groups. The output
# socket defaults are black, as in the shaders affected by the disconnection bug.
groups = []
for name, color in [('Character A', (0.8, 0.6, 0.4, 1.0)), ('Character B', (0.3, 0.5, 0.9, 1.0))]:
    group = bpy.data.node_groups.new(f'Global Material Properties {name}', 'ShaderNodeTree')
    group.interface.new_socket(name='Ambient Colour', in_out='OUTPUT', socket_type='NodeSocketColor')
    output = group.nodes.new('NodeGroupOutput')
    output.name = 'Global Properties'
    output.inputs['Ambient Colour'].default_value = (0, 0, 0, 1)
    source = group.nodes.new('ShaderNodeRGB')
    source.name = 'Lighting color'
    source.outputs[0].default_value = color
    group.links.new(source.outputs[0], output.inputs['Ambient Colour'])
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    node = material.node_tree.nodes.new('ShaderNodeGroup')
    node.node_tree = group
    groups.append(group)

armature = bpy.data.armatures.new('Existing rig')
rig = bpy.data.objects.new('Existing rig', armature)
bpy.context.scene.collection.objects.link(rig)
rig['gacha_game_type'] = 'HONKAI_STAR_RAIL'

def snapshot():
    return (
        tuple((g.name, tuple((l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name) for l in g.links),
               tuple(g.nodes['Lighting color'].outputs[0].default_value)) for g in groups),
        tuple(sorted(rig.items())),
        tuple(o.name for o in bpy.context.scene.objects),
    )

before = snapshot()
props = bpy.context.scene.character_rigger_props
for value in (True, False, True):
    props.disable_rigging = value
    bpy.context.view_layer.update()
    assert snapshot() == before, 'Toggling Disable Rigging changed existing character lighting or objects'
print('PASS: toggling Disable Rigging preserves lighting for both existing characters')

service = RigifyCharacterService.__new__(RigifyCharacterService)
service.context = bpy.context
service.blender_operator = SimpleNamespace(game_type='GENSHIN_IMPACT', report=Mock())
service.character_rigger = SimpleNamespace(rig_character=Mock())
service.rig_character()
service.character_rigger.rig_character.assert_not_called()
assert snapshot() == before, 'Skipping rigging through the service changed the scene'
print('PASS: service skips rig generation without changing the scene')

result = bpy.ops.hoyoverse.rig_character(
    game_type='GENSHIN_IMPACT', next_step_idx=-1, invoker_type='', high_level_step_name='')
assert result == {'FINISHED'}, result
assert snapshot() == before, 'Skipping rigging through the operator changed the scene'
print('PASS: rigging operator skips without altering materials or existing rig metadata')

props.disable_rigging = False
service.rig_character()
service.character_rigger.rig_character.assert_called_once()
assert snapshot() == before
print('PASS: rig generation remains enabled when Disable Rigging is off')
