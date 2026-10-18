"""Preserve Endfield facial skinning when joining separate face submeshes."""


def ensure_head_fallback_weights(mesh, armature, head_name='Bip001_Head'):
    """Bind only unskinned vertices; facial joints already inherit the head."""
    deform_groups = {group.index for group in mesh.vertex_groups
                     if (bone := armature.data.bones.get(group.name)) and bone.use_deform}
    unweighted = [vertex.index for vertex in mesh.data.vertices
                  if not any(weight.group in deform_groups and weight.weight > 0
                             for weight in vertex.groups)]
    if unweighted:
        group = mesh.vertex_groups.get(head_name) or mesh.vertex_groups.new(name=head_name)
        group.add(unweighted, 1.0, 'REPLACE')
    return len(unweighted)


def repair_duplicated_face_head_weights(armature, objects):
    """Repair the old importer's extra head=1 on fully skinned facial vertices.

    Keep genuine blended head weights and restrict the repair to meshes bound
    to this rig and vertices whose facial influences already sum to one.
    """
    repaired = 0
    facial_prefixes = ('eyeLf', 'eyeRt', 'browLf', 'browRt', 'browLineLf', 'browLineRt')
    head_names = ('Bip001_Head', 'DEF-spine.006', 'head')
    for mesh in objects:
        if mesh.type != 'MESH' or not any(
            modifier.type == 'ARMATURE' and modifier.object == armature for modifier in mesh.modifiers
        ):
            continue
        facial_groups = {group.index for group in mesh.vertex_groups
                         if group.name.startswith(facial_prefixes) and group.name in armature.data.bones}
        if not facial_groups:
            continue
        for name in head_names:
            head = mesh.vertex_groups.get(name)
            if head is None:
                continue
            indices = []
            for vertex in mesh.data.vertices:
                head_weight = sum(weight.weight for weight in vertex.groups if weight.group == head.index)
                face_weight = sum(weight.weight for weight in vertex.groups if weight.group in facial_groups)
                if abs(head_weight - 1.0) < 1e-5 and abs(face_weight - 1.0) < 1e-4:
                    indices.append(vertex.index)
            if indices:
                head.remove(indices)
                repaired += len(indices)
    return repaired
