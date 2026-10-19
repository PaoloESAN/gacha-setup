"""Preserve Endfield skinning and bind rigid FBX submeshes."""


def bind_lod_accessories(armature, objects):
    """Bind unskinned LOD children to nearby skin in the normalized rest pose.

    LOD containers do not animate with the character. Give each rigid object
    one attachment bone, keeping its shape and world transform. Larger shells
    are bound first so their glass and VFX layers inherit the same attachment.
    """
    from mathutils.kdtree import KDTree

    meshes = [obj for obj in objects if obj.type == 'MESH']
    deform_names = {bone.name for bone in armature.data.bones if bone.use_deform}

    def weighted_vertices(mesh):
        names = {group.index: group.name for group in mesh.vertex_groups
                 if group.name in deform_names}
        for vertex in mesh.data.vertices:
            weights = {names[w.group]: w.weight for w in vertex.groups
                       if w.group in names and w.weight > 0}
            if weights:
                yield vertex, weights

    targets = [mesh for mesh in meshes
               if mesh.parent == armature and mesh.parent_type == 'BONE'
               and mesh.parent_bone.lower().startswith('lod')
               and not any(weighted_vertices(mesh))]
    if not targets:
        return 0
    samples = []
    for mesh in meshes:
        if not any(mod.type == 'ARMATURE' and mod.object == armature for mod in mesh.modifiers):
            continue
        samples.extend((mesh.matrix_world @ vertex.co, weights)
                       for vertex, weights in weighted_vertices(mesh))
    if not samples:
        return 0
    bound = 0
    for mesh in sorted(targets, key=lambda obj: len(obj.data.vertices), reverse=True):
        if not mesh.data.vertices:
            continue
        tree = KDTree(len(samples))
        for index, (point, _) in enumerate(samples):
            tree.insert(point, index)
        tree.balance()
        world = mesh.matrix_world.copy()
        points = [world @ vertex.co for vertex in mesh.data.vertices]
        scores = {}
        for point in points:
            _, index, distance = tree.find(point)
            for name, weight in samples[index][1].items():
                # Contact with a skinned attachment matters more than a large
                # nearby surface (e.g. a gadget mount next to a skirt).
                scores[name] = scores.get(name, 0.0) + weight / max(distance, 1e-5) ** 2
        bone_name = max(scores, key=scores.get)
        mesh.parent_type = 'OBJECT'
        mesh.parent_bone = ''
        mesh.matrix_parent_inverse = armature.matrix_world.inverted()
        mesh.matrix_world = world
        group = mesh.vertex_groups.get(bone_name) or mesh.vertex_groups.new(name=bone_name)
        group.add(list(range(len(mesh.data.vertices))), 1.0, 'REPLACE')
        modifier = next((mod for mod in mesh.modifiers if mod.type == 'ARMATURE'
                         and mod.object == armature), None)
        if modifier is None:
            modifier = mesh.modifiers.new(name='Armature', type='ARMATURE')
            modifier.object = armature
        samples.extend((point, {bone_name: 1.0}) for point in points)
        bound += 1
        print(f"[AKE SETUP] Bound rigid accessory {mesh.name} to {bone_name}.")
    return bound


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
