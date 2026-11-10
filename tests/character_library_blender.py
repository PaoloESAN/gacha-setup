"""Blender background integration test: save, catalog, append one of two rigs."""

import os
import shutil
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / 'tests/.runtime/character-library'
RUNTIME.mkdir(parents=True, exist_ok=True)

import setup_wizard
from setup_wizard.services import character_library as library
from setup_wizard.ui.character_library import refresh_characters
from setup_wizard.ui.character_settings_utils import stamp_rig_game

# Keep the test's catalog inside the workspace, separate from user preferences.
library.catalog_path = lambda: RUNTIME / 'characters.json'
library.catalog_path().write_text('[]', encoding='utf-8')
library.catalog_path().with_name('removed_characters.json').write_text('[]', encoding='utf-8')
setup_wizard.register()


def make_character(name, game):
    rig = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    bpy.context.collection.objects.link(rig)
    stamp_rig_game(rig, game, name)
    mesh = bpy.data.objects.new(name + ' Body', bpy.data.meshes.new(name + ' Mesh'))
    bpy.context.collection.objects.link(mesh)
    mesh.parent = rig
    mesh.modifiers.new('Armature', 'ARMATURE').object = rig
    # This helper is not parented: the dependency walk must still include it.
    helper = bpy.data.objects.new(name + ' Target', None)
    bpy.context.collection.objects.link(helper)
    constraint = rig.constraints.new('COPY_LOCATION')
    constraint.target = helper
    head = bpy.data.objects.new('Head Direction_' + name, None)
    bpy.context.collection.objects.link(head)
    head.parent = rig
    widget = bpy.data.objects.new('WGT-' + name, bpy.data.meshes.new('Widget'))
    bpy.context.collection.objects.link(widget)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bone = rig.data.edit_bones.new('Control')
    bone.tail = (0, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.pose.bones['Control'].custom_shape = widget
    rig.select_set(False)
    return rig, mesh, helper, head, widget


bpy.data.objects.remove(bpy.data.objects['Cube'], do_unlink=True)
first = make_character('Sandrone', 'GENSHIN_IMPACT')
second = make_character('Trailblazer', 'HONKAI_STAR_RAIL')
first[2].hide_set(True)
first[1]['test_value'] = 13
first[0]['nested_settings'] = {'values': [1.0, 2.0], 'enabled': True}
library.mark_setup_complete()
bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'characters.blend'))
entries = library.read_catalog()
assert len(entries) == 2, entries
sandrone = next(entry for entry in entries if entry['name'] == 'Sandrone')
assert set(sandrone['objects']) == {obj.name for obj in first}, sandrone
assert sandrone['hidden'] == [first[2].name]
# Saving again replaces entries rather than duplicating them.
bpy.ops.wm.save_mainfile()
assert len(library.read_catalog()) == 2
# The object list baseline must survive reopening.
saved_state = bpy.context.scene['gacha_library_setup_state']
bpy.ops.wm.open_mainfile(filepath=str(RUNTIME / 'characters.blend'))
assert library._scene_state(bpy.context.scene) == saved_state
first_rig = bpy.data.objects['Sandrone']
# Removing a file affects only the picker and survives another pristine save.
source_path = str(RUNTIME / 'characters.blend')
assert bpy.ops.gacha.remove_library_blend(filepath=source_path) == {'FINISHED'}
bpy.ops.wm.save_mainfile()
assert library.read_catalog() == []
assert Path(source_path).is_file()
assert bpy.ops.gacha.add_library_blend(filepath=source_path) == {'FINISHED'}
bpy.context.scene.game_type_dropdown = 'GENSHIN_IMPACT'
refresh_characters(bpy.context)
assert bpy.ops.gacha.rename_library_blend(filepath=source_path, label='My Characters.blend') == {'FINISHED'}
bpy.ops.wm.save_mainfile()
assert all(entry['label'] == 'My Characters.blend' for entry in library.read_catalog())
# Extra objects must not register working copies.
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.object
bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'working-cube.blend'))
assert len(library.read_catalog()) == 2
bpy.data.objects.remove(cube, do_unlink=True)
first_rig.location.x = 2
first_rig.pose.bones['Control'].rotation_euler.z = 0.5
first_rig['nested_settings']['enabled'] = False
body = bpy.data.objects['Sandrone Body']
body['test_value'] = 42
assert library._scene_state(bpy.context.scene) == saved_state
bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'working-pose.blend'))
assert len(library.read_catalog()) == 4
library.remove_blend(str(RUNTIME / 'working-pose.blend'))
assert len(library.read_catalog()) == 2
first_rig.location.x = 0
# Even objects present when setup finishes must belong to a character.
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.object
library.mark_setup_complete()
bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'setup-with-cube.blend'))
assert len(library.read_catalog()) == 2
bpy.data.objects.remove(cube, do_unlink=True)
library.mark_setup_complete()
# Worker outputs must never enter the permanent picker.
os.environ['GACHA_SETUP_ISOLATED_WORKER'] = '1'
bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'worker.blend'))
assert all(Path(entry['filepath']).name == 'characters.blend' for entry in library.read_catalog())
del os.environ['GACHA_SETUP_ISOLATED_WORKER']

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.view_layers.new('Secondary')
# Manual add inspects another file without leaving objects/scenes behind.
original_objects, original_scenes = set(bpy.data.objects), set(bpy.data.scenes)
source_path = str(RUNTIME / 'characters.blend')
library.rename_blend(source_path, 'My Characters.blend')
assert all(entry['label'] == 'My Characters.blend' for entry in library.read_catalog())
library.remove_blend(source_path)
assert library.read_catalog() == []
assert Path(source_path).is_file()
assert library.add_blend(source_path) == 2
assert set(bpy.data.objects) == original_objects
assert set(bpy.data.scenes) == original_scenes
assert {entry['rig'] for entry in library.read_catalog()} == {'Sandrone', 'Trailblazer'}
# Record the game passed to the actual compositor steps, while running them normally.
from setup_wizard.ui import compositor_setup
compositor_games = []
original_setup_color = compositor_setup.setup_color
def record_color(context, game):
    compositor_games.append(game)
    return original_setup_color(context, game)
compositor_setup.setup_color = record_color
rig = library.append_character(sandrone, bpy.context)
assert bpy.context.view_layer.objects.active == rig
assert {obj.name for obj in bpy.context.scene.objects} == set(sandrone['objects'])
mesh = bpy.data.objects['Sandrone Body']
assert mesh.parent == rig and mesh.modifiers[0].object == rig
assert mesh['test_value'] == 13
assert rig.constraints[0].target == bpy.data.objects['Sandrone Target']
assert bpy.data.objects['Sandrone Target'].hide_get()
assert rig['gacha_game'] == 'GENSHIN_IMPACT'
def assert_widgets(rig):
    main_collection = rig.users_collection[0]
    widgets = next(coll for coll in main_collection.children if coll.name.startswith('WGTS_'))
    assert widgets.hide_viewport and widgets.hide_render and widgets.hide_select
    head = next(obj for obj in rig.children if obj.type == 'EMPTY' and obj.name.startswith('Head Direction'))
    shape = rig.pose.bones['Control'].custom_shape
    assert set(head.users_collection) == {widgets}
    assert set(shape.users_collection) == {widgets}
    for layer in bpy.context.scene.view_layers:
        assert layer.layer_collection.children[main_collection.name].children[widgets.name].exclude
    return widgets
first_widgets = assert_widgets(rig)
assert compositor_games == ['GENSHIN_IMPACT']
from setup_wizard.genshin_compositing_node_setup import get_node_tree, get_output_node_type
tree = get_node_tree(bpy.context.scene)
assert any(node.bl_idname == get_output_node_type() and any(socket.is_linked for socket in node.inputs)
           for node in tree.nodes)
# Repeated append produces independent data and remapped dependencies.
copy = library.append_character(sandrone, bpy.context)
assert copy != rig and copy.data != rig.data
assert copy.constraints[0].target != rig.constraints[0].target
copy_mesh = next(obj for obj in copy.children if obj.type == 'MESH')
assert copy_mesh.modifiers[0].object == copy
assert len(bpy.context.scene.objects) == 2 * len(sandrone['objects'])
assert assert_widgets(copy) != first_widgets
assert assert_widgets(rig) == first_widgets
assert compositor_games == ['GENSHIN_IMPACT', 'GENSHIN_IMPACT']
copy_mesh['test_value'] = 42
assert mesh['test_value'] == 13
# Reject changed/missing files before creating any scene objects.
for invalid in (dict(sandrone, filepath=str(RUNTIME / 'missing.blend')),
                dict(sandrone, objects=['missing-rig']),
                dict(sandrone, blender=[99, 0, 0])):
    try:
        library.append_character(invalid, bpy.context)
    except (FileNotFoundError, ValueError):
        pass
    else:
        raise AssertionError('Invalid catalog entry accepted')
    assert len(bpy.context.scene.objects) == 2 * len(sandrone['objects'])

# The picker uses the main panel's game and has no second game selector.
assert not hasattr(bpy.types.WindowManager, 'gacha_library_game')
bpy.context.scene.game_type_dropdown = 'GENSHIN_IMPACT'
refresh_characters(bpy.context)
assert [item.name for item in bpy.context.window_manager.gacha_saved_characters] == ['Sandrone']
bpy.context.scene.game_type_dropdown = 'HONKAI_STAR_RAIL'
refresh_characters(bpy.context)
assert [item.name for item in bpy.context.window_manager.gacha_saved_characters] == ['Trailblazer']
existing_tree = tree
existing_nodes = set(tree.nodes)
existing_links = {(edge.from_node.name, edge.to_node.name) for edge in tree.links}
assert bpy.ops.gacha.select_character('EXEC_DEFAULT') == {'FINISHED'}
assert compositor_games[-1] == 'HONKAI_STAR_RAIL'
assert get_node_tree(bpy.context.scene) == existing_tree
assert set(tree.nodes) == existing_nodes
assert {(edge.from_node.name, edge.to_node.name) for edge in tree.links} == existing_links
assert_widgets(bpy.context.view_layer.objects.active)
bpy.context.scene.game_type_dropdown = 'PUNISHING_GRAY_RAVEN'
assert bpy.ops.gacha.run_compositing('EXEC_DEFAULT', step='ALL') == {'FINISHED'}
assert compositor_games[-1] == 'PUNISHING_GRAY_RAVEN'
# Manual additions belong to the selected game, regardless of the source tags.
assert bpy.ops.gacha.add_library_blend(filepath=source_path) == {'FINISHED'}
assert [item.name for item in bpy.context.window_manager.gacha_saved_characters] == ['Sandrone', 'Trailblazer']
assert {entry['library_game'] for entry in library.read_catalog()} == {'PUNISHING_GRAY_RAVEN'}
assert {entry['game'] for entry in library.read_catalog()} == {'GENSHIN_IMPACT', 'HONKAI_STAR_RAIL'}
# Refreshing the file must retain its manually chosen category.
assert library.add_blend(source_path) == 2
assert {entry['library_game'] for entry in library.read_catalog()} == {'PUNISHING_GRAY_RAVEN'}
bpy.context.scene.game_type_dropdown = 'GENSHIN_IMPACT'
refresh_characters(bpy.context)
assert not bpy.context.window_manager.gacha_saved_characters
bpy.context.scene.game_type_dropdown = 'PUNISHING_GRAY_RAVEN'
refresh_characters(bpy.context)
assert len(bpy.context.window_manager.gacha_saved_characters) == 2
# Multi-selection adds each valid file, even when another selection fails.
copy_path = RUNTIME / 'characters-copy.blend'
shutil.copyfile(source_path, copy_path)
objects_before_batch = set(bpy.data.objects)
scenes_before_batch = set(bpy.data.scenes)
assert bpy.ops.gacha.add_library_blend(
    directory=str(RUNTIME), files=[{'name': 'characters.blend'}, {'name': 'missing.blend'},
                                  {'name': copy_path.name}, {'name': 'characters.blend'}],
) == {'FINISHED'}
assert len(library.read_catalog()) == 4
assert {entry['library_game'] for entry in library.read_catalog()} == {'PUNISHING_GRAY_RAVEN'}
assert set(bpy.data.objects) == objects_before_batch
assert set(bpy.data.scenes) == scenes_before_batch
library.remove_blend(str(copy_path))
refresh_characters(bpy.context)
assert len(bpy.context.window_manager.gacha_saved_characters) == 2
# Link creates independent instances of the same linked source dependencies.
assert bpy.ops.gacha.select_character.get_rna_type().properties['import_mode'].default == 'APPEND'
assert bpy.ops.gacha.select_character('EXEC_DEFAULT', import_mode='LINK') == {'FINISHED'}
instance = bpy.context.view_layer.objects.active
assert instance.type == 'EMPTY' and instance.instance_type == 'COLLECTION'
linked_rig = next(obj for obj in instance.instance_collection.all_objects if obj.name == 'Sandrone')
assert linked_rig.library and linked_rig.data.library
linked_mesh = next(obj for obj in instance.instance_collection.all_objects if obj.name == 'Sandrone Body')
assert linked_mesh.library and linked_mesh.data.library
assert linked_mesh.parent == linked_rig and linked_mesh.modifiers[0].object == linked_rig
assert compositor_games[-1] == 'PUNISHING_GRAY_RAVEN'
linked_widgets = next(coll for coll in instance.instance_collection.children if coll.name.startswith('WGTS_'))
assert linked_widgets.hide_viewport and linked_widgets.hide_render
assert linked_rig.pose.bones['Control'].custom_shape in set(linked_widgets.objects)
assert bpy.ops.gacha.select_character('EXEC_DEFAULT', import_mode='LINK') == {'FINISHED'}
second_instance = bpy.context.view_layer.objects.active
assert second_instance != instance
assert linked_rig in set(second_instance.instance_collection.all_objects)
assert set(tree.nodes) == existing_nodes
linked_instance_name = second_instance.name
bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'linked-instances.blend'))
bpy.ops.wm.open_mainfile(filepath=str(RUNTIME / 'linked-instances.blend'))
reopened = bpy.context.scene.objects[linked_instance_name]
assert reopened.instance_type == 'COLLECTION'
assert all(obj.library for obj in reopened.instance_collection.all_objects)
compositor_setup.setup_color = original_setup_color

# Operators and handler survive an addon disable/enable cycle without duplicates.
setup_wizard.unregister()
assert library.saved_characters_post not in bpy.app.handlers.save_post
setup_wizard.register()
assert bpy.app.handlers.save_post.count(library.saved_characters_post) == 1
setup_wizard.unregister()
print('PASS: saved character catalog, isolated dependencies, repeated append and lifecycle')

if '--' in sys.argv:
    fixture = Path(sys.argv[sys.argv.index('--') + 1])
    setup_wizard.register()
    bpy.ops.wm.open_mainfile(filepath=str(fixture))
    library.mark_setup_complete()
    bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'real-character.blend'))
    entry = next(entry for entry in library.read_catalog()
                 if Path(entry['filepath']).name == 'real-character.blend')
    expected_name = entry['name']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = library.append_character(entry, bpy.context)
    assert rig['gacha_game'] == entry['game']
    assert len(bpy.context.scene.objects) >= len(entry['objects'])
    character_collection = rig.users_collection[0]
    widgets = next(coll for coll in character_collection.children if coll.name.startswith('WGTS_'))
    for obj in character_collection.all_objects:
        if library._is_widget_helper(obj):
            assert set(obj.users_collection) == {widgets}, obj.name
    for layer in bpy.context.scene.view_layers:
        assert layer.layer_collection.children[character_collection.name].children[widgets.name].exclude
    if rig.data.get('rig_id'):
        from setup_wizard.services.isolation.rig_ui_manager import _registered_ui_class
        assert _registered_ui_class('VIEW3D_PT_rig_layers_' + rig.data['rig_id'])
    bpy.ops.wm.save_as_mainfile(filepath=str(RUNTIME / 'real-appended.blend'))
    rig_name = rig.name
    bpy.ops.wm.open_mainfile(filepath=str(RUNTIME / 'real-appended.blend'))
    assert rig_name in bpy.context.scene.objects
    setup_wizard.unregister()
    print(f'PASS: real character {expected_name}, rig UI, save and reopen')
