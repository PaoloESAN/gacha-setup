"""Blender --background --factory-startup --python-exit-code 1 --python this_file."""
import sys
from pathlib import Path
from unittest.mock import patch
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
original_resource = bpy.utils.user_resource
def isolated_resource(kind, path='', create=False):
    if kind in {'SCRIPTS', 'CONFIG'}:
        target = ROOT / '.tmp/unrigged-direction-test' / kind.lower() / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = isolated_resource
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard.utils.unrigged_light_direction import setup_unrigged_light_direction, LIGHT_DIRECTION_GAMES
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property
from setup_wizard.import_order import get_shader_file_path


def make_mesh(name, armature, group, collection):
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    collection.objects.link(obj)
    arm = obj.modifiers.new('Armature', 'ARMATURE')
    arm.object = armature
    mod = obj.modifiers.new('Light Vectors', 'NODES')
    mod.node_group = group
    return obj, mod


for game in sorted(LIGHT_DIRECTION_GAMES):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for tree in list(bpy.data.node_groups):
        bpy.data.node_groups.remove(tree)
    bpy.context.scene.character_rigger_props.disable_rigging = True
    coll = bpy.data.collections.new('Character')
    bpy.context.scene.collection.children.link(coll)
    widgets = bpy.data.collections.new('WGTS_Character')
    coll.children.link(widgets)
    widgets.hide_viewport = True
    widgets.hide_select = True
    armature = bpy.data.objects.new('Original Skeleton', bpy.data.armatures.new('Original Skeleton'))
    coll.objects.link(armature)
    shader_path = get_shader_file_path(game, 'outlines') or get_shader_file_path(game, 'main')
    with bpy.data.libraries.load(shader_path, link=False) as (source, result):
        assert 'Light Vectors' in source.node_groups, game
        result.node_groups = ['Light Vectors']
    group = result.node_groups[0]
    direction = next(s for s in group.interface.items_tree if s.item_type == 'SOCKET'
                     and s.in_out == 'INPUT' and s.name == 'Light Direction')
    head = next(s for s in group.interface.items_tree if s.item_type == 'SOCKET'
                and s.in_out == 'INPUT' and s.name == 'Head Origin')
    mesh, mod = make_mesh('Face', armature, group, coll)
    head_obj = bpy.data.objects.new('Head Origin', None)
    widgets.objects.link(head_obj)
    set_modifier_property(mod, head.identifier, head_obj)
    light = bpy.data.objects.new('Light Direction', None)
    widgets.objects.link(light)
    light.hide_viewport = True
    light.hide_select = True
    light.rotation_euler = (.3, .4, .5)
    set_modifier_property(mod, direction.identifier, light)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.context.view_layer.update()
    rotation = tuple(light.rotation_euler)
    before = set(bpy.data.objects)
    result = setup_unrigged_light_direction(bpy.context, game)
    assert result == light
    assert set(bpy.data.objects) == before, 'Setup created a rig or extra controls'
    assert list(light.users_collection) == [coll]
    assert not light.hide_viewport and not light.hide_get() and not light.hide_select
    assert light.empty_display_type == 'SINGLE_ARROW'
    assert tuple(light.rotation_euler) == rotation
    assert get_modifier_property(mod, direction.identifier) == light
    assert get_modifier_property(mod, head.identifier) == head_obj
    assert list(head_obj.users_collection) == [widgets] and widgets.hide_viewport
    assert setup_unrigged_light_direction(bpy.context, game) == light
    assert set(bpy.data.objects) == before

    # Shared template references must not move or modify the older character.
    other_coll = bpy.data.collections.new('Previous Character')
    bpy.context.scene.collection.children.link(other_coll)
    other_arm = bpy.data.objects.new('Previous Skeleton', bpy.data.armatures.new('Previous Skeleton'))
    other_coll.objects.link(other_arm)
    other_mesh, other_mod = make_mesh('Previous Face', other_arm, group, other_coll)
    set_modifier_property(other_mod, direction.identifier, light)
    saved_collections = list(light.users_collection)
    independent = setup_unrigged_light_direction(bpy.context, game)
    assert independent != light
    assert list(light.users_collection) == saved_collections
    assert get_modifier_property(other_mod, direction.identifier) == light
    assert get_modifier_property(mod, direction.identifier) == independent
    assert len(bpy.data.objects) == len(before) + 3

    # A deselected but stamped import still needs its control connected.
    armature['_setup_wizard_model_id'] = 'current'
    armature.select_set(False)
    assert setup_unrigged_light_direction(bpy.context, game) == independent
    bpy.context.scene.character_rigger_props.disable_rigging = False
    independent.hide_select = True
    assert setup_unrigged_light_direction(bpy.context, game) is None
    assert independent.hide_select
    bpy.context.scene.character_rigger_props.disable_rigging = True
    for unsupported in ('NEVERNESS_TO_EVERNESS', 'ARKNIGHTS_ENDFIELD', 'HONKAI_NEXUS_ANIMA'):
        assert setup_unrigged_light_direction(bpy.context, unsupported) is None
    print('PASS:', game, 'direction visible and connected; head controls, skeleton and previous character preserved', flush=True)

# Exercise the geometry operator hook, including a setup changing active object.
bpy.context.view_layer.objects.active = armature
armature.select_set(True)
def geometry_setup():
    bpy.context.view_layer.objects.active = head_obj
with patch('setup_wizard.genshin_set_up_geometry_nodes.GameGeometryNodesSetupFactory.create') as factory, patch('setup_wizard.genshin_set_up_geometry_nodes.NextStepInvoker'):
    factory.return_value.setup_geometry_nodes.side_effect = geometry_setup
    assert bpy.ops.genshin.setup_geometry_nodes(game_type='ZENLESS_ZONE_ZERO', next_step_idx=-1) == {'FINISHED'}
assert get_modifier_property(mod, direction.identifier) == independent and not independent.hide_select
print('PASS: geometry operator configures original target even if setup changes active object', flush=True)

# Missing control is created without adding a rig or any other controls.
bpy.context.view_layer.objects.active = armature
set_modifier_property(mod, direction.identifier, None)
bpy.data.objects.remove(independent, do_unlink=True)
# The old light has a suffix belonging to its existing model, so cannot be reused.
light.name = 'Light Direction_Previous'
before = set(bpy.data.objects)
created = setup_unrigged_light_direction(bpy.context, 'ZENLESS_ZONE_ZERO')
assert set(bpy.data.objects) - before == {created}
assert get_modifier_property(mod, direction.identifier) == created
print('PASS: missing Light Direction creates only one arrow control', flush=True)

