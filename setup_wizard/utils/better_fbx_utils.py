import bpy
import os
from contextlib import nullcontext

from setup_wizard.utils.optional_addons import find_addon, temporary_addon


def _fbx_contains_skin(filepath):
    """Distinguish a lost skin from an intentionally unskinned FBX scene."""
    if os.path.splitext(filepath)[1].lower() != '.fbx':
        return False
    try:
        with temporary_addon('io_scene_fbx'):
            from io_scene_fbx import parse_fbx
            root, _version = parse_fbx.parse(filepath)
    except (OSError, ValueError):
        # BetterFBX also supports ASCII FBX; Blender's binary parser does not.
        # An unreadable skin declaration is not evidence of a missing skin.
        return False
    return any(
        element.id == b'Deformer' and b'Skin' in element.props
        for section in root.elems if section.id == b'Objects'
        for element in section.elems
    )


def _has_skin(objects):
    return any(
        obj.type == 'MESH' and obj.vertex_groups
        and any(mod.type == 'ARMATURE' and mod.object is not None
                for mod in obj.modifiers)
        and any(vertex.groups for vertex in obj.data.vertices)
        for obj in objects
    )


def _recover_missing_skin(filepath, imported, previous_data):
    """Retry incompatible FBXs without retaining BetterFBX's static meshes."""
    if (not any(obj.type == 'ARMATURE' for obj in imported)
            or _has_skin(imported) or not _fbx_contains_skin(filepath)):
        return
    # BetterFBX can report FINISHED while dropping every Skin deformer (e.g.
    # The Dahlia). Rigify can still generate a rig, masking the failed import.
    # Replace the incomplete import before any mesh/rig setup takes place.
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    # Release the failed armature's datablock name too: the HSR rigger uses
    # matching object/data names when joining the generated rig. Keep all IDs
    # that existed before import, including the user's unused materials.
    for name, previous in previous_data.items():
        blocks = getattr(bpy.data, name)
        for block in set(blocks) - previous:
            if block.users == 0:
                blocks.remove(block)
    before = set(bpy.data.objects)
    try:
        with temporary_addon('io_scene_fbx'):
            result = bpy.ops.import_scene.fbx(
                'EXEC_DEFAULT', filepath=filepath, global_scale=1.0,
                use_custom_normals=True, use_custom_props=True,
                use_custom_props_enum_as_string=True, use_subsurf=False,
                ignore_leaf_bones=False, use_anim=True, anim_offset=1.0,
            )
        if result != {'FINISHED'} or not _has_skin(set(bpy.data.objects) - before):
            raise RuntimeError('Python FBX fallback did not recover the mesh skin.')
    except Exception:
        for obj in set(bpy.data.objects) - before:
            bpy.data.objects.remove(obj, do_unlink=True)
        raise
    print('[FBX IMPORT] BetterFBX omitted FBX skin; recovered with Python FBX fallback')


def operator_is_registered(operator) -> bool:
    # bpy.ops creates proxy attributes even for operators that do not exist;
    # hasattr(bpy.ops.wm, 'fbx_import') therefore also returns True on Goo 4.3.
    try:
        operator.get_rna_type()
        return True
    except (AttributeError, KeyError, RuntimeError):
        return False


def find_better_fbx_module():
    return find_addon('better_fbx') or find_addon('better fbx')


def is_blender_version_lower_than_4_5() -> bool:
    """
    Returns True if the running Blender version is lower than 4.5.
    In Blender < 4.5, the fast C++ FBX importer is not natively available.
    """
    return bpy.app.version < (4, 5, 0)


def is_better_fbx_installed() -> bool:
    """Check availability without enabling add-ons while drawing the UI."""
    return operator_is_registered(bpy.ops.better_import.fbx) or bool(find_better_fbx_module())


def import_with_better_fbx(filepath):
    """Use the installed BetterFBX operator, including inside factory workers."""
    operator = bpy.ops.better_import.fbx
    registered = operator_is_registered(operator)
    module = None if registered else find_better_fbx_module()
    if not registered and not module:
        raise RuntimeError(
            f'BetterFBX is required for {bpy.app.version_string}: '
            'Blender versions below 4.5 always use BetterFBX, and newer builds need it '
            'when the native FBX importer is unavailable. Install Better FBX Importer & Exporter.'
        )
    with nullcontext() if registered else temporary_addon(module):
        if not operator_is_registered(operator):
            raise RuntimeError('BetterFBX did not register its better_import.fbx operator.')
        supported = operator.get_rna_type().properties
        options = {
            'filepath': filepath,
            # BetterFBX 6.x only executes its import loop when this collection
            # is populated. filepath alone falls through execute() with None.
            'files': [{'name': os.path.basename(filepath)}],
            'directory': os.path.dirname(filepath),
            'my_scale': 1.0,
            'use_auto_bone_orientation': False,
            'use_fix_bone_poses': False,
            'use_animation': True,
            'use_import_materials': True,
            'my_import_normal': 'Import',
        }
        # BetterFBX releases expose different option sets. Send only properties
        # supported by the installed version rather than native importer flags.
        options = {name: value for name, value in options.items() if name in supported}
        before = set(bpy.context.scene.objects)
        previous_data = {name: set(getattr(bpy.data, name)) for name in
                         ('meshes', 'armatures', 'materials', 'images', 'actions', 'collections')}
        result = operator('EXEC_DEFAULT', **options)
        if result != {'FINISHED'}:
            raise RuntimeError(f'BetterFBX import failed: {result}')
        if not any(o.type == 'MESH' for o in set(bpy.context.scene.objects) - before):
            raise RuntimeError('BetterFBX finished without importing any mesh objects.')
        print('[FBX IMPORT] Imported with BetterFBX (better_import.fbx)')
        _recover_missing_skin(filepath, set(bpy.context.scene.objects) - before, previous_data)
        return result


def should_show_better_fbx_warning(game_type: str = None) -> bool:
    """
    Determines if the BetterFBX recommendation warning should be displayed below 'Run Entire Setup'.
    Conditions:
    - Blender version must be < 4.5.
    - The game uses the FBX setup workflow (excluding WuWa's UEMODEL workflow).
    - BetterFBX is NOT installed/available.
    """
    if not is_blender_version_lower_than_4_5():
        return False
    fbx_games = {
        'GENSHIN_IMPACT', 'HONKAI_STAR_RAIL', 'PUNISHING_GRAY_RAVEN',
        'ZENLESS_ZONE_ZERO', 'ARKNIGHTS_ENDFIELD', 'HONKAI_IMPACT_3RD',
        'HONKAI_NEXUS_ANIMA',
    }
    if game_type and game_type not in fbx_games:
        return False
    return not is_better_fbx_installed()
