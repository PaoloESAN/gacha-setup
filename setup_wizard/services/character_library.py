"""Catalog saved setup characters and append just one character's dependencies."""

import hashlib
import json
import os
from pathlib import Path

import bpy
from bpy.app.handlers import persistent

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.character_settings_utils import (
    detect_armature_game, invalidate_caches, resolve_character_name,
)


def catalog_path():
    return Path(bpy.utils.user_resource('CONFIG', path='gacha_setup', create=True)) / 'characters.json'


def read_catalog():
    path = catalog_path()
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(entries, list):
        raise ValueError('Invalid character catalog')
    return entries


def _dependencies(roots, dependencies):
    found = set(roots)
    pending = list(roots)
    while pending:
        for dependency in dependencies.get(pending.pop(), ()):
            if dependency not in found:
                found.add(dependency)
                pending.append(dependency)
    return found


def _characters(scene, include_linked=False):
    candidates = [obj for obj in scene.objects
                  if obj.type == 'ARMATURE' and (include_linked or not obj.library)
                  and not any(word in obj.name.lower() for word in
                              ('metarig', 'eyerig', 'facerig', 'lighting', 'wgt'))
                  and detect_armature_game(obj) in GameType.__members__]
    roots = [obj for obj in candidates
             if not any(parent in candidates for parent in _parents(obj))]
    # Mesh-only setups can carry the same game tag as an armature.
    roots.extend(obj for obj in scene.objects
                 if obj.type == 'MESH' and (include_linked or not obj.library) and obj.get('gacha_game')
                 and not obj.find_armature() and not any(_parents(obj)))
    return roots


def _parents(obj):
    parent = obj.parent
    while parent:
        yield parent
        parent = parent.parent


def _is_widget_helper(obj):
    name = obj.name.casefold().replace('_', ' ').replace('-', ' ')
    if obj.type == 'EMPTY':
        return any(marker in name for marker in
                   ('head direction', 'head origin', 'head driver', 'head controller',
                    'head forward', 'head up', 'face light direction', 'head pole'))
    return obj.type == 'MESH' and name.startswith(('wgt', 'widget', 'head control shape'))


def _exclude_widgets(scene, collection):
    collection.hide_viewport = True
    collection.hide_render = True
    collection.hide_select = True

    def exclude(layer):
        if layer.collection == collection:
            layer.exclude = True
        for child in layer.children:
            exclude(child)

    for view_layer in scene.view_layers:
        exclude(view_layer.layer_collection)


def write_catalog(entries):
    path = catalog_path()
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def _file_entries(filepath, scenes, include_linked=False):
    normalized = os.path.normcase(filepath)
    entries = []
    # user_map points from dependencies to users. Reverse it once for the file.
    dependencies = {}
    for dependency, users in bpy.data.user_map().items():
        for user in users:
            dependencies.setdefault(user, set()).add(dependency)
    seen = set()
    for scene in scenes:
        for rig in _characters(scene, include_linked):
            if rig in seen:
                continue
            seen.add(rig)
            roots = {rig, *rig.children_recursive}
            roots.update(obj for obj in scene.objects
                         if obj.type == 'MESH' and obj.find_armature() == rig)
            ids = _dependencies(roots, dependencies)
            objects = sorted((item for item in ids if isinstance(item, bpy.types.Object)),
                             key=lambda obj: obj.name)
            texts = {item.name for item in ids if isinstance(item, bpy.types.Text)}
            rig_id = rig.data.get('rig_id') if rig.data else None
            if rig_id:
                from setup_wizard.services.isolation.rig_ui_manager import _find_rig_ui_text
                text = _find_rig_ui_text(rig, rig_id, tuple(bpy.data.texts))
                if text:
                    texts.add(text.name)
            key = hashlib.sha256((normalized + '\0' + rig.name).encode('utf-8')).hexdigest()
            entries.append({
                'key': key, 'name': resolve_character_name(rig, rig.name),
                'game': detect_armature_game(rig), 'filepath': filepath, 'rig': rig.name,
                'objects': [obj.name for obj in objects], 'texts': sorted(texts),
                'widgets': [obj.name for obj in objects if _is_widget_helper(obj)
                            or any(coll.name.casefold().startswith(('wgt', 'widget'))
                                   for coll in obj.users_collection)],
                'hidden': [obj.name for obj in objects if obj.hide_get(view_layer=scene.view_layers[0])],
                'blender': list(bpy.app.version),
            })
    return entries


def _scene_state(scene):
    """Compare only the object list, regardless of poses, geometry or settings."""
    objects = sorted((obj.name, obj.type) for obj in scene.objects)
    return hashlib.sha256(json.dumps(objects).encode()).hexdigest()


def mark_setup_complete(scene=None):
    scene = scene or bpy.context.scene
    scene['gacha_library_setup_state'] = _scene_state(scene)


def index_current_file():
    """Only catalog completed setups that retain the same object list."""
    if os.environ.get('GACHA_SETUP_ISOLATED_WORKER') == '1' or not bpy.data.filepath:
        return
    filepath = str(Path(bpy.data.filepath).resolve())
    if not Path(filepath).is_file():
        return
    scenes = list(bpy.data.scenes)
    if not scenes or any(scene.get('gacha_library_setup_state') != _scene_state(scene)
                         for scene in scenes):
        return
    fresh = _file_entries(filepath, scenes)
    allowed = {name for entry in fresh for name in entry['objects']}
    if not fresh or any(obj.name not in allowed and obj.type not in {'CAMERA', 'LIGHT'}
                        for scene in scenes for obj in scene.objects):
        return
    _merge_file_entries(filepath, fresh)


def _merge_file_entries(filepath, fresh):
    entries = read_catalog()
    previous = {entry['key']: entry for entry in entries}
    for entry in fresh:
        if entry['key'] in previous and 'label' in previous[entry['key']]:
            entry['label'] = previous[entry['key']]['label']
        if ('library_game' not in entry and entry['key'] in previous
                and 'library_game' in previous[entry['key']]):
            entry['library_game'] = previous[entry['key']]['library_game']
    # A removed file stays removed on future saves until explicitly added again.
    removed = catalog_path().with_name('removed_characters.json')
    excluded = json.loads(removed.read_text(encoding='utf-8')) if removed.exists() else []
    if os.path.normcase(filepath) in excluded:
        return
    write_catalog([entry for entry in entries
                   if os.path.normcase(entry['filepath']) != os.path.normcase(filepath)] + fresh)


def add_blend(filepath, game=None):
    """Inspect linked scenes without opening or modifying the current project."""
    if game is not None and game not in GameType.__members__:
        raise ValueError('Select a valid game')
    filepath = str(Path(filepath).resolve())
    if not Path(filepath).is_file() or Path(filepath).suffix.lower() != '.blend':
        raise ValueError('Choose an existing .blend file')
    if bpy.data.filepath and os.path.normcase(filepath) == os.path.normcase(str(Path(bpy.data.filepath).resolve())):
        fresh = _file_entries(filepath, bpy.data.scenes)
    else:
        before = set(bpy.data.user_map())
        try:
            with bpy.data.libraries.load(filepath, link=True) as (source, target):
                target.scenes = source.scenes
                target.texts = source.texts
            fresh = _file_entries(filepath, target.scenes, include_linked=True)
        finally:
            bpy.data.batch_remove(ids=set(bpy.data.user_map()) - before)
    if not fresh:
        raise ValueError('No setup characters found in this .blend file')
    if game is not None:
        for entry in fresh:
            entry['library_game'] = game
    removed = catalog_path().with_name('removed_characters.json')
    if removed.exists():
        excluded = json.loads(removed.read_text(encoding='utf-8'))
        removed.write_text(json.dumps([path for path in excluded if path != os.path.normcase(filepath)]), encoding='utf-8')
    _merge_file_entries(filepath, fresh)
    return len(fresh)


def rename_blend(filepath, label):
    label = label.strip()
    if not label:
        raise ValueError('Enter a name')
    entries = read_catalog()
    for entry in entries:
        if entry['filepath'] == filepath:
            entry['label'] = label
    write_catalog(entries)


def remove_blend(filepath):
    removed = catalog_path().with_name('removed_characters.json')
    excluded = json.loads(removed.read_text(encoding='utf-8')) if removed.exists() else []
    normalized = os.path.normcase(filepath)
    removed.write_text(json.dumps(sorted(set(excluded) | {normalized})), encoding='utf-8')
    write_catalog([entry for entry in read_catalog() if entry['filepath'] != filepath])


@persistent
def saved_characters_post(_unused):
    try:
        index_current_file()
    except Exception as exc:
        print(f'[GACHA SETUP] Could not update character catalog: {exc}')


def _setup_character_compositor(entry):
    game = entry.get('library_game', entry['game'])
    result = bpy.ops.gacha.run_compositing('EXEC_DEFAULT', step='ALL', game_type=game)
    if 'FINISHED' not in result:
        raise RuntimeError('Character added, but its compositor setup failed')


def _link_character(entry, context):
    """Instance a local wrapper of linked dependencies without editing library data."""
    object_names = list(entry['objects'])
    with bpy.data.libraries.load(entry['filepath'], link=True) as (source, target):
        if set(object_names) - set(source.objects):
            raise ValueError('Character changed in the saved file. Add the .blend again to refresh it')
        target.objects = object_names
        target.texts = [name for name in entry['texts'] if name in source.texts]
    loaded = dict(zip(object_names, target.objects))
    collection = bpy.data.collections.new(entry['name'])
    widgets = {bone.custom_shape for obj in target.objects if obj.type == 'ARMATURE'
               for bone in obj.pose.bones if bone.custom_shape}
    widgets.update(loaded[name] for name in entry.get('widgets', ()) if name in loaded)
    widgets.update(obj for obj in target.objects if _is_widget_helper(obj))
    widget_collection = bpy.data.collections.new('WGTS_' + entry['name'])
    widget_collection.hide_viewport = True
    widget_collection.hide_render = True
    collection.children.link(widget_collection)
    hidden_collection = bpy.data.collections.new('Hidden_' + entry['name'])
    hidden_collection.hide_viewport = True
    collection.children.link(hidden_collection)
    hidden = set(entry.get('hidden', ()))
    for name, obj in loaded.items():
        destination = widget_collection if obj in widgets else hidden_collection if name in hidden else collection
        destination.objects.link(obj)
    instance = bpy.data.objects.new(entry['name'], None)
    instance.instance_type = 'COLLECTION'
    instance.instance_collection = collection
    context.scene.collection.objects.link(instance)
    from setup_wizard.services.isolation.rig_ui_manager import initialize_rig_uis
    initialize_rig_uis(target.objects, texts=[text for text in target.texts if text])
    invalidate_caches()
    from setup_wizard.ui.character_settings_tabs import hide_registered_rig_layers
    hide_registered_rig_layers()
    for obj in context.selected_objects:
        obj.select_set(False)
    instance.select_set(True)
    context.view_layer.objects.active = instance
    _setup_character_compositor(entry)
    return instance


def append_character(entry, context, *, link=False):
    path = entry['filepath']
    if not Path(path).is_file():
        raise FileNotFoundError(f'Saved file moved or deleted: {path}')
    if tuple(entry.get('blender', (0, 0))[:2]) > bpy.app.version[:2]:
        raise ValueError('Open this character with the Blender version used to save it or newer')
    if link:
        return _link_character(entry, context)
    before = set(bpy.data.objects)
    images_before = set(bpy.data.images)
    object_names = list(entry['objects'])
    with bpy.data.libraries.load(path, link=False) as (source, target):
        missing = set(object_names) - set(source.objects)
        if missing:
            raise ValueError('Character changed in the saved file. Open it and save again to refresh the catalog')
        target.objects = list(object_names)
        target.texts = [name for name in entry['texts'] if name in source.texts]
    imported = set(bpy.data.objects) - before
    loaded = dict(zip(object_names, target.objects))
    collection = bpy.data.collections.new(entry['name'])
    context.scene.collection.children.link(collection)
    widgets = {bone.custom_shape for obj in imported if obj.type == 'ARMATURE'
               for bone in obj.pose.bones if bone.custom_shape}
    widgets.update(loaded[name] for name in entry.get('widgets', ()) if name in loaded)
    widgets.update(obj for obj in imported if _is_widget_helper(obj))
    widget_collection = None
    if widgets:
        widget_collection = bpy.data.collections.new('WGTS_' + entry['name'])
        collection.children.link(widget_collection)
        widget_collection.hide_render = True
    for obj in imported:
        destination = widget_collection if obj in widgets else collection
        destination.objects.link(obj)
    context.view_layer.update()
    for name in entry.get('hidden', ()):
        obj = loaded.get(name)
        if obj:
            obj.hide_set(True)
    for obj in widgets:
        obj.hide_set(True)
    from setup_wizard.utils.texture_utils import prepare_image_paths
    prepare_image_paths('', images=[img for img in bpy.data.images if img not in images_before],
                        source_blend=path)
    from setup_wizard.services.isolation.rig_ui_manager import initialize_rig_uis
    initialize_rig_uis(imported, texts=[text for text in target.texts if text])
    invalidate_caches()
    from setup_wizard.ui.character_settings_tabs import hide_registered_rig_layers
    hide_registered_rig_layers()
    for obj in context.selected_objects:
        obj.select_set(False)
    rig = loaded[entry['rig']]
    rig.hide_set(False)
    rig.select_set(True)
    context.view_layer.objects.active = rig
    if widget_collection:
        _exclude_widgets(context.scene, widget_collection)
    _setup_character_compositor(entry)
    return rig


def register():
    if saved_characters_post not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(saved_characters_post)


def unregister():
    if saved_characters_post in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(saved_characters_post)
