"""Shared Character / Bone Layers navigation for every game panel."""

import ast
from functools import lru_cache
from types import SimpleNamespace
import bpy


SUPPORTED_GAMES = {
    'GENSHIN_IMPACT', 'HONKAI_STAR_RAIL', 'ZENLESS_ZONE_ZERO',
    'PUNISHING_GRAY_RAVEN', 'HONKAI_IMPACT_3RD', 'HONKAI_NEXUS_ANIMA',
    'NEVERNESS_TO_EVERNESS', 'WUTHERING_WAVES', 'ARKNIGHTS_ENDFIELD',
}

def has_character_settings(context):
    from setup_wizard.ui.character_settings_utils import (
        resolve_settings_armature, detect_armature_game,
    )
    arm = resolve_settings_armature(context)
    return bool(arm and detect_armature_game(arm) in SUPPORTED_GAMES)


def draw_character_settings_tabs(layout, context):
    """Return True when the Bone Layers tab has consumed this draw call."""
    from setup_wizard.ui.character_settings_utils import (
        resolve_settings_armature, resolve_character_name,
    )
    arm = resolve_settings_armature(context)
    if arm is None:
        return False
    card = layout.box()
    heading = card.row()
    heading.alignment = 'CENTER'
    heading.label(text=resolve_character_name(arm, 'Character'))
    card.row(align=True).prop(arm, 'gacha_settings_tab', expand=True)
    if arm.gacha_settings_tab == 'BONE_LAYERS':
        draw_bone_layers(layout, arm)
        return True
    layout.separator()
    return False


@lru_cache(maxsize=1)
def _original_bone_layers_draw():
    """Reuse the original rig layout, including paired buttons and solo stars."""
    from setup_wizard import bl_info
    from setup_wizard.character_rig_setup.rig_ui_utils import build_rig_layers_ui_code
    version = '.'.join(map(str, bl_info['version']))
    body = build_rig_layers_ui_code('', version)
    namespace = {'bpy': bpy, 'rig_id': ''}
    exec(compile('def draw(self, context):' + body + '\n',
                 '<character-settings-bone-layers>', 'exec'), namespace)
    return namespace['draw']


def draw_bone_layers(layout, arm):
    if getattr(arm, 'type', None) != 'ARMATURE':
        layout.label(text='This character has no armature', icon='INFO')
        return
    # The original Blender 3.x draw uses active_object directly. Resolving the
    # character first also keeps that layout working when a mesh is selected.
    _original_bone_layers_draw()(
        SimpleNamespace(layout=layout), SimpleNamespace(active_object=arm),
    )


def patch_standalone_layers(source):
    """Keep embedded rig scripts compatible while hiding the duplicate panel."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    insertions = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name != 'RigLayers' and 'rig_layers' not in node.name.lower():
            continue
        for method in node.body:
            if not isinstance(method, ast.FunctionDef) or method.name != 'poll':
                continue
            if 'has_character_settings' in ast.get_source_segment(source, method):
                continue
            first = method.body[0]
            indent = ' ' * first.col_offset
            guard = (f'{indent}from setup_wizard.ui.character_settings_tabs import has_character_settings\n'
                     f'{indent}if has_character_settings(context):\n'
                     f'{indent}    return False\n')
            insertions.append((first.lineno - 1, guard))
    for index, guard in sorted(insertions, reverse=True):
        lines.insert(index, guard)
    return ''.join(lines)


_old_polls = {}


def _replace_panel_poll(cls, replacement):
    """Refresh RNA's callback cache whenever a panel's poll method changes."""
    registered = cls.is_registered
    original = cls.__dict__.get('poll')
    if registered:
        bpy.utils.unregister_class(cls)

    def assign(value):
        if value is None:
            if 'poll' in cls.__dict__:
                delattr(cls, 'poll')
        else:
            cls.poll = value

    try:
        assign(replacement)
        if registered:
            bpy.utils.register_class(cls)
    except Exception:
        assign(original)
        if registered:
            bpy.utils.register_class(cls)
        raise


def _layers_poll(original):
    # RNA registers a two-argument class callback. Keep captured state in the
    # closure rather than adding an extra default argument to its signature.
    def poll(cls, context):
        return not has_character_settings(context) and original(context)
    return classmethod(poll)


def hide_registered_rig_layers():
    """Also cover rig scripts already executed by Blender on file load."""
    for cls in bpy.types.Panel.__subclasses__():
        name = cls.__name__.lower()
        if name != 'riglayers' and 'rig_layers' not in name and name != 'dynamicriglayers':
            continue
        if not cls.is_registered or cls in _old_polls or not hasattr(cls, 'poll'):
            continue
        original = cls.__dict__.get('poll')
        _replace_panel_poll(cls, _layers_poll(cls.poll))
        _old_polls[cls] = original


def register():
    bpy.types.Object.gacha_settings_tab = bpy.props.EnumProperty(
        name='Character Settings',
        items=(('CHARACTER', 'Character', 'Character settings'),
               ('BONE_LAYERS', 'Bone Layers', 'Show or hide groups of bones')),
        default='CHARACTER',
    )


def unregister():
    for cls, poll in _old_polls.items():
        _replace_panel_poll(cls, poll)
    _old_polls.clear()
    if hasattr(bpy.types.Object, 'gacha_settings_tab'):
        del bpy.types.Object.gacha_settings_tab
