"""Visibility rules for auxiliary HI3 meshes."""

def hide_hi3_body_shadow_meshes(objects):
    hidden = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        name = ''.join(c for c in obj.name.lower() if c.isalnum())
        if not name.startswith('bodyshadow'):
            continue
        obj.hide_render = True
        obj.hide_viewport = True
        obj.hide_set(True)
        hidden.append(obj.name)
    return hidden
