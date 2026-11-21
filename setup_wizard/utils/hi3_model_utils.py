"""Visibility rules for auxiliary HI3 meshes."""


def eye_bone_deforms_mesh(armature, bone_name):
    """An eye joint is useful for tracking only if it skins this character."""
    bone = armature.data.bones.get(bone_name) if bone_name else None
    if bone is None:
        return False
    names = {b.name for b in [bone, *bone.children_recursive] if b.use_deform}
    for obj in armature.users_scene[0].objects if armature.users_scene else []:
        if obj.type != 'MESH' or not any(
            mod.type == 'ARMATURE' and mod.object == armature for mod in obj.modifiers
        ):
            continue
        indices = {vg.index for vg in obj.vertex_groups if vg.name in names}
        if indices and any(g.group in indices and g.weight > 0
                           for vertex in obj.data.vertices for g in vertex.groups):
            return True
    return False

def nudge_hi3_eye_mouth_layers(objects, forward_offset=0.0015):
    """Nudge separate HI3 2D eye/mouth overlay meshes slightly forward (-Y) to avoid face occlusion."""
    import re
    from mathutils import Vector

    moved = []
    target_names = {'eyel', 'eyer', 'mouth'}
    for obj in objects:
        if obj.type != 'MESH' or not obj.data or not obj.data.vertices:
            continue
        base_name = re.sub(r'\.\d+$', '', obj.name)
        clean_name = re.sub(r'[^a-z0-9]', '', base_name.lower())
        if clean_name not in target_names:
            continue
        # Convert world-space -Y offset into mesh local space
        local_delta = obj.matrix_world.to_3x3().inverted_safe() @ Vector((0.0, -forward_offset, 0.0))
        for vertex in obj.data.vertices:
            vertex.co += local_delta
        obj.data.update()
        moved.append(obj.name)
    return moved


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
