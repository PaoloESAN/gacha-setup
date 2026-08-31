# Author: michael-gh1


from pathlib import Path, Path

from setup_wizard.domain.character_types import CharacterType


def get_monster_body_part_name(name):
    if not name:
        return 'Body'
    if '_Mat_' in name:
        return name.split('_Mat_')[-1]
    if name.endswith('_Mat') or '_Mat_' in name:
        clean = name[:-4] if name.endswith('_Mat') else name
        return clean.split('_')[-1]
    if '_' in name:
        return name.split('_')[-1]
    return name


def get_npc_mesh_body_part_name(material_name):
    if not material_name:
        return 'Body'
    if 'Hair' in material_name:
        return 'Hair'
    elif 'Face' in material_name:
        return 'Face'
    elif 'Item' in material_name:
        return material_name.replace('NPC_', '').replace('_Mat', '')
    elif 'Screw' in material_name:
        return 'Screw'
    elif 'Hat' in material_name:
        return 'Hat'
    elif 'Others' in material_name:
        return 'Others'
    elif 'Cloak' in material_name:
        return 'Cloak'
    if '_Mat_' in material_name:
        return material_name.split('_Mat_')[-1]
    if material_name.endswith('_Mat'):
        return material_name[:-4].split('_')[-1]
    if '_' in material_name:
        return material_name.split('_')[-1]
    return material_name


def get_body_part(file):
    if 'Monster' in file.name:
        expected_body_part_name = Path(file.name).stem.split('_')[-2]
        body_part = get_monster_body_part_name(Path(file.name).stem.split('_')[-2]) if expected_body_part_name != 'Mat' else get_monster_body_part_name(Path(file.name).stem.split('_')[-1])
    elif 'NPC' in file.name:
        body_part = get_npc_mesh_body_part_name(Path(file.name).stem)
    elif 'Equip' in file.name:
        body_part = 'Body'
    else:
        body_part = Path(file.name).stem.split('_')[-1]
    return body_part


def get_character_type(file):
    if 'Monster' in file.name:
        return CharacterType.MONSTER
    elif 'NPC' in file.name:
        return CharacterType.NPC
    elif 'Equip' in file.name:
        return CharacterType.GI_EQUIPMENT
    else:
        return CharacterType.UNKNOWN  # catch-all, tries default material applying behavior
