"""Repair unskinned hair vertices in ZZZ FBX exports."""


def bind_unweighted_hair(armature, objects):
    """Attach missing hair skin to the head without changing existing weights."""
    head = armature.data.bones.get('Bip001 Head')
    if head is None or not head.use_deform:
        return 0
    repaired = 0
    for mesh in objects:
        if mesh.type != 'MESH' or 'hair' not in mesh.name.lower():
            continue
        if not any(mod.type == 'ARMATURE' and mod.object == armature
                   for mod in mesh.modifiers):
            continue
        deform_groups = {group.index for group in mesh.vertex_groups
                         if (bone := armature.data.bones.get(group.name))
                         and bone.use_deform}
        missing = [vertex.index for vertex in mesh.data.vertices
                   if not any(weight.group in deform_groups and weight.weight > 0
                              for weight in vertex.groups)]
        if missing:
            group = mesh.vertex_groups.get(head.name) or mesh.vertex_groups.new(name=head.name)
            group.add(missing, 1.0, 'REPLACE')
            repaired += len(missing)
            print(f'[ZZZ RIG] Bound {len(missing)} unweighted hair vertices on {mesh.name} to {head.name}.')
    return repaired
