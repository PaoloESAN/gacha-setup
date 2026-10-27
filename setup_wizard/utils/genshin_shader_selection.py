"""Genshin setup shader selection shared by the UI and isolated workers."""
import bpy


def default_genshin_shader(version=None):
    version = bpy.app.version if version is None else version
    return 'NEW' if tuple(version) >= (5, 0, 0) else 'OLD'


def get_genshin_shader_selection(scene=None):
    scene = scene if scene is not None else getattr(bpy.context, 'scene', None)
    selected = getattr(scene, 'gi_shader_type', default_genshin_shader())
    return selected if selected in {'NEW', 'OLD'} else default_genshin_shader()
