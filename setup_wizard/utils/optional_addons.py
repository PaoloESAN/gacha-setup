"""Use installed dependencies without changing the user's enabled add-ons."""
from contextlib import contextmanager
from functools import wraps
import sys
from types import ModuleType

import addon_utils
import bpy


def find_addon(search_key):
    key = search_key.lower()
    modules = list(addon_utils.modules(refresh=False))
    # Also include dependencies loaded from custom script paths (e.g. workers).
    known = {mod.__name__ for mod in modules}
    modules.extend(mod for name, mod in list(sys.modules.items())
                   if isinstance(mod, ModuleType) and name not in known
                   and (isinstance(vars(mod).get('bl_info'), dict)
                        or isinstance(vars(mod).get('manifest'), dict))
                   and callable(vars(mod).get('register'))
                   and callable(vars(mod).get('unregister')))
    for module in modules:
        name = module.__name__
        title = vars(module).get('bl_info', vars(module).get('manifest', {})).get('name', '')
        if key in name.lower() or key in title.lower():
            return name
    return None


def addon_installed(search_key):
    return find_addon(search_key) is not None


@contextmanager
def temporary_addon(search_key):
    """Nested uses share registration; only undo registration owned by this call."""
    module = find_addon(search_key)
    if not module:
        raise RuntimeError(f'{search_key} is required. Install the add-on first; it can remain disabled.')
    was_loaded = addon_utils.check(module)[1]
    was_enabled = module in bpy.context.preferences.addons
    try:
        if not was_loaded:
            # Retarget's register() reads its preferences entry. Add it for the
            # operation, then remove only the entry this scope created.
            addon_utils.enable(module, default_set=True, persistent=False)
            if not addon_utils.check(module)[1]:
                raise RuntimeError(f'Could not activate installed dependency: {module}')
        yield module
    finally:
        if not was_loaded and addon_utils.check(module)[1]:
            addon_utils.disable(module, default_set=not was_enabled)
        elif not was_enabled and module in bpy.context.preferences.addons:
            entry = bpy.context.preferences.addons.get(module)
            bpy.context.preferences.addons.remove(entry)


def uses_addon(search_key):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with temporary_addon(search_key):
                return function(*args, **kwargs)
        return wrapped
    return decorate
