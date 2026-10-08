import bpy


def is_blender_version_lower_than_4_5() -> bool:
    """
    Returns True if the running Blender version is lower than 4.5.
    In Blender < 4.5, the fast C++ FBX importer is not natively available.
    """
    return bpy.app.version < (4, 5, 0)


def is_better_fbx_installed() -> bool:
    """
    Checks if the Better FBX addon is installed and available in Blender.
    If it is installed in the Blender addons folder but disabled, attempts to enable it.
    """
    if hasattr(bpy.types, "BETTER_IMPORT_OT_fbx"):
        return True
    try:
        import addon_utils
        for mod in addon_utils.modules():
            if mod.__name__ == "better_fbx":
                loaded, enabled = addon_utils.check("better_fbx")
                if not enabled:
                    addon_utils.enable("better_fbx", default_set=False)
                return hasattr(bpy.types, "BETTER_IMPORT_OT_fbx")
    except Exception:
        pass
    return False


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
