"""Recover unweighted arm control roots from imported skin bind joints."""
import bpy


def align_genshin_arm_roots(rig):
    """The C++ importer preserves weighted twist joints; fit controls to them.

    Some Genshin FBXs store a different pose for unweighted Bip001 UpperArm
    nodes. Their A01/B01 skin joints describe the actual shoulder position.
    Never move a skinned bone or any of the twist joints themselves.
    """
    if rig.type != 'ARMATURE':
        return []
    weighted = set()
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.find_armature() != rig:
            continue
        groups = {g.index: g.name for g in obj.vertex_groups}
        for vertex in obj.data.vertices:
            weighted.update(groups[w.group] for w in vertex.groups
                            if w.weight > 1e-6 and w.group in groups)
    roots = {}
    for side in ('L', 'R'):
        name = f'Bip001 {side} UpperArm'
        root = rig.data.bones.get(name)
        if root is None or name in weighted:
            continue
        anchors = [b for b in root.children if b.name in
                   {f'+UpperArmTwist {side} A01', f'+UpperArmTwist {side} B01'}
                   and b.name in weighted]
        if not anchors:
            continue
        point = anchors[0].head_local.copy()
        if any((b.head_local - point).length > 1e-4 for b in anchors):
            continue
        if (root.head_local - point).length > 1e-4:
            roots[name] = point
    if not roots:
        return []
    context = bpy.context
    previous = context.view_layer.objects.active
    mode = context.object.mode if context.object else 'OBJECT'
    was_selected = rig.select_get()
    try:
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for name, point in roots.items():
            bone = rig.data.edit_bones[name]
            bone.use_connect = False
            bone.head = point
    finally:
        if rig.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = previous
        if previous and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        if previous != rig and not was_selected:
            rig.select_set(False)
    return list(roots)
