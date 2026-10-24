"""PMX import and semantic humanoid bone mapping."""

import os
from pathlib import Path

import bpy
from setup_wizard.utils.optional_addons import uses_addon


def is_mmd_armature(obj):
    return bool(obj and obj.type == 'ARMATURE' and (
        obj.get('setup_wizard_pmx') or getattr(obj, 'mmd_type', '') == 'ARMATURE'
    ))


def find_pmx(path):
    path = Path(path)
    if path.is_file():
        return str(path) if path.suffix.lower() == '.pmx' else None
    if not path.is_dir():
        return None
    # Prefer the existing FBX/UE pipeline in mixed asset folders.
    files = [p for p in path.rglob('*') if p.is_file()
             and '__MACOSX' not in p.parts and not p.name.startswith('.')]
    if any(p.suffix.lower() in ('.fbx', '.uemodel') for p in files):
        return None
    models = sorted((p for p in files if p.suffix.lower() == '.pmx'),
                    key=lambda p: (len(p.name), str(p)))
    return str(models[0]) if models else None


@uses_addon('mmd_tools')
def import_pmx(context, filepath):
    from setup_wizard.import_order import (
        CHARACTER_MODEL_FOLDER_FILE_PATH, cache_using_cache_key,
        get_cache, set_active_character_directory,
    )
    before = set(context.scene.objects)
    result = bpy.ops.mmd_tools.import_model(
        'EXEC_DEFAULT', filepath=filepath, scale=0.08, rename_bones=True,
        types={'MESH', 'ARMATURE', 'MORPHS', 'DISPLAY'},
    )
    objects = set(context.scene.objects) - before
    armature = next((obj for obj in objects if obj.type == 'ARMATURE'), None)
    if result != {'FINISHED'} or armature is None or not any(o.type == 'MESH' for o in objects):
        raise RuntimeError(f'MMD Tools did not import a character from {filepath}')
    armature['setup_wizard_pmx'] = filepath
    directory = os.path.dirname(filepath)
    context.scene['setup_wizard_imported_pmx_path'] = filepath
    context.scene['setup_wizard_imported_model_dir'] = directory
    # Clear stale format-specific paths when importing another character.
    for key in ('setup_wizard_imported_fbx_path', 'setup_wizard_imported_uemodel_path'):
        if key in context.scene:
            del context.scene[key]
    set_active_character_directory(directory)
    cache_using_cache_key(get_cache(True), CHARACTER_MODEL_FOLDER_FILE_PATH, directory)
    bpy.ops.object.select_all(action='DESELECT')
    armature.hide_set(False)
    armature.select_set(True)
    context.view_layer.objects.active = armature


def _mapping(armature):
    """Resolve original PMX names even if MMD Tools translated Blender names."""
    names = {pb.name: pb.name for pb in armature.pose.bones}
    names.update({pb.mmd_bone.name_j: pb.name for pb in armature.pose.bones
                  if getattr(pb, 'mmd_bone', None) and pb.mmd_bone.name_j})

    def pick(*choices):
        return next((names[c] for c in choices if c in names), '')

    mapping = {
        'spine': pick('下半身', 'グルーブ'),
        'spine.001': pick('上半身'),
        'spine.002': pick('上半身1'),
        'spine.003': pick('上半身2', '上半身1', '上半身'),
        'spine.004': pick('首'),
        'spine.006': pick('頭'),
    }
    for side, jp in (('L', '左'), ('R', '右')):
        for target, base in (('shoulder', '肩'), ('upper_arm', '腕'),
                             ('forearm', 'ひじ'), ('hand', '手首'),
                             ('thigh', '足'), ('shin', 'ひざ'), ('foot', '足首'),
                             ('toe', 'つま先'), ('eye', '目')):
            mapping[f'{target}.{side}'] = pick(jp+base, f'{base}.{side}')
        for target, jp_finger, digits in (
            ('thumb', '親指', '０１２'), ('f_index', '人指', '１２３'),
            ('f_middle', '中指', '１２３'), ('f_ring', '薬指', '１２３'),
            ('f_pinky', '小指', '１２３'),
        ):
            for i, digit in enumerate(digits, 1):
                mapping[f'{target}.{i:02d}.{side}'] = pick(
                    jp+jp_finger+digit, f'{jp_finger}{digit}.{side}',
                    jp+jp_finger+str('０１２３'.index(digit)),
                )
    required = ['spine', 'spine.001', 'spine.004', 'spine.006'] + [
        f'{part}.{side}' for side in ('L', 'R')
        for part in ('upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot')]
    missing = [name for name in required if not mapping[name]]
    if missing:
        raise RuntimeError('MMD skeleton is missing required humanoid bones: ' + ', '.join(missing))
    return mapping
