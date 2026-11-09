"""Read texture declarations from Unity dumps and compact ZZZ exports."""
from pathlib import PurePosixPath


def texture_environments(data):
    """Return Unity-style texture slots, or None for an unknown schema."""
    saved = data.get('m_SavedProperties')
    raw = saved.get('m_TexEnvs') if isinstance(saved, dict) else None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {entry.get('Key', entry.get('first')): entry.get('Value', entry.get('second'))
                for entry in raw if isinstance(entry, dict)
                and entry.get('Key', entry.get('first'))}
    if not isinstance(data.get('textures'), list):
        return None
    slots = {}
    for entry in data['textures']:
        if not isinstance(entry, dict) or not entry.get('slot'):
            continue
        filename = entry.get('file') or entry.get('name') or ''
        if not isinstance(filename, str):
            filename = ''
        name = PurePosixPath(filename.replace('\\', '/')).stem
        empty = entry.get('empty', not bool(filename))
        slots[entry['slot']] = {'m_Texture': {'IsNull': bool(empty), 'Name': name}}
    return slots


def is_untextured(data):
    slots = texture_environments(data)
    if slots is None:
        # Missing support for a schema must not suppress shader assignment.
        return False
    for value in slots.values():
        ref = value.get('m_Texture') if isinstance(value, dict) else None
        if not isinstance(ref, dict) or ref.get('IsNull') is True:
            continue
        if ref.get('IsNull') is False or ref.get('Name') or ref.get('m_PathID'):
            return False
    return True
