import bpy
import os
from contextlib import nullcontext

from setup_wizard.utils.optional_addons import find_addon, temporary_addon


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
        result = operator('EXEC_DEFAULT', **options)
        if result != {'FINISHED'}:
            raise RuntimeError(f'BetterFBX import failed: {result}')
        if not any(o.type == 'MESH' for o in set(bpy.context.scene.objects) - before):
            raise RuntimeError('BetterFBX finished without importing any mesh objects.')
        print('[FBX IMPORT] Imported with BetterFBX (better_import.fbx)')
        return result


def should_show_better_fbx_warning(game_type: str = None) -> bool:
    """
    Determines if the BetterFBX recommendation warning should be displayed below 'Run Entire Setup'.
    Conditions:
    - Blender version must be < 4.5.
    - For game_type: applies when None or 'GENSHIN_IMPACT'.
    - BetterFBX is NOT installed/available.
    """
    if not is_blender_version_lower_than_4_5():
        return False
    if game_type and game_type != "GENSHIN_IMPACT":
        return False
    return not is_better_fbx_installed()
