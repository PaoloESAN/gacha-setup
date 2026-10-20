"""Restore a hip/thigh blend for ZZZ FBX pelvis deformation helpers."""
import re
import bpy
import numpy as np
from mathutils.kdtree import KDTree


def hip_seam_groups(mesh, positions, strength, totals, target_groups):
    """Find split skin vertices that should share deformation, without welding UVs."""
    active = np.flatnonzero((strength > 0) & (totals > .1))
    if not len(active):
        return []
    tolerance = max(float(np.ptp(positions, axis=0).max()) * 1e-7, 1e-8)
    tree = KDTree(len(active))
    for index in active:
        tree.insert(positions[index], int(index))
    tree.balance()
    parents = np.arange(len(positions))
    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    external = {int(i): {g.group: g.weight for g in mesh.data.vertices[i].groups
                         if g.group not in target_groups and g.weight > 1e-7} for i in active}
    for index in active:
        for _, other, _ in tree.find_range(positions[index], tolerance):
            if other <= index:
                continue
            # Coincident clothing layers can have intentionally different rigs.
            # Only join skin with equivalent influence outside the hip groups.
            a, b = external[int(index)], external[other]
            if any(abs(a.get(g,0)-b.get(g,0)) > 1e-5 for g in a.keys() | b.keys()):
                continue
            if abs(totals[index]-totals[other]) > 1e-5:
                continue
            parents[root(other)] = root(index)
    groups = {}
    for index in active:
        groups.setdefault(root(index), []).append(int(index))
    return [indices for indices in groups.values() if len(indices) > 1]


def smooth_hip_weights(mesh, armature, plans):
    """Smooth abrupt FBX skin-weight changes locally, retaining total influence."""
    tag = 'zzz_hip_weights_smoothed_v3'
    if mesh.get(tag):
        return
    # The stitched graph has more neighbors than the split FBX islands and
    # needs a gradual transition across the full joint. Apply this graph-based
    # repair once to fresh imports and older repairs alike.
    passes = 72
    names = {g.name for g in mesh.vertex_groups if re.fullmatch(r'Skn_[LR]_(?:Pelvis_0[1-4]|Thigh_Twist(?:02)?|RouTui)', g.name)}
    parents = {parent for _, _, parent, _ in plans}
    names.update(parents)
    groups = [g for g in mesh.vertex_groups if g.name in names]
    if not groups or not mesh.data.edges:
        return
    lookup = {g.index: i for i, g in enumerate(groups)}
    weights = np.zeros((len(mesh.data.vertices), len(groups)), dtype=np.float64)
    for vertex in mesh.data.vertices:
        for assignment in vertex.groups:
            if assignment.group in lookup:
                weights[vertex.index, lookup[assignment.group]] = assignment.weight
    totals = weights.sum(axis=1)
    positions = np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices])
    strength = np.zeros(len(positions))
    for _, thigh_name, _, _ in plans:
        thigh = armature.data.bones[thigh_name]
        hip = armature.matrix_world @ thigh.head_local
        side = 'L' if thigh_name.endswith('.L') or ' L ' in thigh_name else 'R'
        knee = next((armature.data.bones.get(n) for n in (f'DEF-shin.{side}', f'Bip001 {side} Calf', f'shin.{side}') if armature.data.bones.get(n)), None)
        if not knee:
            continue
        length = (armature.matrix_world @ knee.head_local - hip).length
        if length < 1e-6:
            continue
        distance = np.linalg.norm(positions - np.array(hip), axis=1)
        strength = np.maximum(strength, np.clip((length * .55 - distance) / (length * .3), 0, 1) * .5)
    strength[totals < .1] = 0
    seams = hip_seam_groups(mesh, positions, strength, totals, lookup)
    edges = np.array([tuple(e.vertices) for e in mesh.data.edges])
    # Smooth over the stitched skin graph. UV/normal splits must not create
    # separate neighborhoods with independent skin-weight transitions.
    representatives = np.arange(len(positions))
    for seam in seams:
        representatives[seam] = seam[0]
    edges = np.unique(np.sort(representatives[edges], axis=1), axis=0)
    edges = edges[edges[:,0] != edges[:,1]]
    first, second = edges[:, 0], edges[:, 1]
    valid = (totals[first] > .1) & (totals[second] > .1)
    first, second = first[valid], second[valid]
    lengths = np.linalg.norm(positions[first] - positions[second], axis=1)
    edge_weights = 1 / np.maximum(lengths, 1e-5)
    degree = np.zeros(len(positions))
    np.add.at(degree, first, edge_weights)
    np.add.at(degree, second, edge_weights)
    proportions = weights / np.maximum(totals[:, None], 1e-12)
    for seam in seams:
        proportions[seam] = proportions[seam].mean(axis=0)
    for _ in range(passes):
        neighbors = np.zeros_like(weights)
        np.add.at(neighbors, first, proportions[second] * edge_weights[:, None])
        np.add.at(neighbors, second, proportions[first] * edge_weights[:, None])
        average = neighbors / np.maximum(degree[:, None], 1e-12)
        blend = np.where(degree > 0, strength, 0)[:, None]
        proportions = proportions * (1 - blend) + average * blend
        for seam in seams:
            proportions[seam] = proportions[seam[0]]
    result = proportions * totals[:, None]
    for index in np.flatnonzero(strength > 0):
        for column, group in enumerate(groups):
            value = float(result[index, column])
            if value > 1e-8:
                group.add([int(index)], value, 'REPLACE')
            elif weights[index, column] > 0:
                group.remove([int(index)])
    mesh[tag] = True


def setup_zzz_hip_follow(armature, influence=0.5):
    """Give weighted pelvis helpers a half-angle hip pivot, preserving bind pose.

    The FBX leaves these weighted helpers fixed under the pelvis.
    A separate pivot blends thigh rotation relative to the pelvis; copying
    rotation directly onto each helper would rotate around the wrong joint.
    """
    if not armature or armature.type != 'ARMATURE':
        return 0
    meshes = [o for o in bpy.data.objects if o.type == 'MESH'
              and any(m.type == 'ARMATURE' and m.object == armature for m in o.modifiers)]
    weighted = set()
    for mesh in meshes:
        indices = {g.index: g.name for g in mesh.vertex_groups
                   if re.fullmatch(r'Skn_[LR]_Pelvis_0[1-4]', g.name)}
        for vertex in mesh.data.vertices:
            weighted.update(indices[g.group] for g in vertex.groups
                            if g.group in indices and g.weight > 0.0001)
    plans = []
    for side in ('L', 'R'):
        thigh = next((armature.data.bones.get(name) for name in
                      (f'DEF-thigh.{side}', f'Bip001 {side} Thigh', f'thigh.{side}')
                      if armature.data.bones.get(name)), None)
        helpers = [b for b in armature.data.bones if b.name in weighted and b.name.startswith(f'Skn_{side}_')]
        if not thigh or not helpers:
            continue
        name = f'MCH-ZZZ-HipFollow.{side}'
        parents = {b.parent.name for b in helpers if b.parent and b.parent.name != name}
        existing = armature.data.bones.get(name)
        if not parents and existing and existing.parent:
            parents = {existing.parent.name}
        if len(parents) != 1:
            continue
        parent = next(iter(parents))
        # Do not replace a character's authored corrective behavior.
        if any(armature.pose.bones[b.name].constraints for b in helpers):
            continue
        plans.append((name, thigh.name, parent, [b.name for b in helpers]))
    if not plans:
        return 0

    for mesh in meshes:
        smooth_hip_weights(mesh, armature, plans)

    # A repeated call on an animated rig must not enter Edit Mode: rebuilding
    # mechanism rest transforms while posed can change the evaluated pose.
    if all(armature.data.bones.get(name)
           and armature.data.bones[name].parent
           and armature.data.bones[name].parent.name == parent
           and all(armature.data.bones[h].parent == armature.data.bones[name] for h in helpers)
           and (constraint := armature.pose.bones[name].constraints.get('ZZZ Hip Follow'))
           and constraint.type == 'COPY_ROTATION'
           and constraint.target == armature and constraint.subtarget == thigh
           for name, thigh, parent, helpers in plans):
        for name, _, _, _ in plans:
            armature.pose.bones[name].constraints['ZZZ Hip Follow'].influence = influence
        armature.update_tag()
        bpy.context.view_layer.update()
        return sum(len(helpers) for _, _, _, helpers in plans)

    active = bpy.context.view_layer.objects.active
    mode = active.mode if active else 'OBJECT'
    selected = list(bpy.context.selected_objects)
    try:
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        bones = armature.data.edit_bones
        for name, thigh_name, parent_name, helpers in plans:
            thigh = bones[thigh_name]
            pivot = bones.get(name) or bones.new(name)
            pivot.matrix = thigh.matrix.copy()
            pivot.length = thigh.length
            pivot.parent = bones[parent_name]
            pivot.use_connect = False
            pivot.use_deform = False
            for helper in helpers:
                bones[helper].use_connect = False
                bones[helper].parent = pivot
        bpy.ops.object.mode_set(mode='OBJECT')
        for name, thigh_name, _, _ in plans:
            pivot = armature.pose.bones[name]
            constraint = pivot.constraints.get('ZZZ Hip Follow') or pivot.constraints.new('COPY_ROTATION')
            constraint.name = 'ZZZ Hip Follow'
            constraint.target = armature
            constraint.subtarget = thigh_name
            constraint.target_space = 'LOCAL_WITH_PARENT'
            constraint.owner_space = 'LOCAL_WITH_PARENT'
            constraint.mix_mode = 'REPLACE'
            constraint.influence = influence
            pivot.bone.hide = True
        armature.update_tag()
        bpy.context.view_layer.update()
    finally:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
    return sum(len(helpers) for _, _, _, helpers in plans)

