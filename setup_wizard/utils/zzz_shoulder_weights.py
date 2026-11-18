"""Local shoulder-transition skin-weight smoothing for ZZZ characters."""
import bpy
import numpy as np
from mathutils.kdtree import KDTree


def _find_combined_seam_groups(meshes, mesh_ids, local_indices, positions, strength, totals, weights, target_names):
    """Find split skin vertices across meshes that should share deformation."""
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

    group_names_by_mesh = [{g.index: g.name for g in m.vertex_groups} for m in meshes]
    external = {}
    for i in active:
        m_idx = int(mesh_ids[i])
        v_idx = int(local_indices[i])
        gmap = group_names_by_mesh[m_idx]
        external[int(i)] = {
            gmap[g.group]: g.weight
            for g in meshes[m_idx].data.vertices[v_idx].groups
            if g.group in gmap and gmap[g.group] not in target_names and g.weight > 1e-7
        }

    for index in active:
        i_idx = int(index)
        a = external[i_idx]
        for _, other, _ in tree.find_range(positions[i_idx], tolerance):
            if other <= i_idx:
                continue
            b = external[other]
            if any(abs(a.get(g, 0) - b.get(g, 0)) > 1e-5 for g in a.keys() | b.keys()):
                continue
            if abs(totals[i_idx] - totals[other]) > 1e-5:
                continue
            # Across separate mesh objects, only stitch genuine split-surface
            # seams that already share the same initial skinning at the seam.
            if mesh_ids[i_idx] != mesh_ids[other] and np.any(np.abs(weights[i_idx] - weights[other]) > 1e-3):
                continue
            parents[root(other)] = root(i_idx)

    groups = {}
    for index in active:
        groups.setdefault(root(int(index)), []).append(int(index))
    return [indices for indices in groups.values() if len(indices) > 1]


def smooth_zzz_shoulder_weights(rig):
    """Smooth only the arm/clavicle/chest blend around the shoulder sockets.

    Retain every vertex position, morph, unrelated influence and per-vertex
    weight total. Stitch equivalent UV-split vertices in the smoothing graph
    (including split body patches across separate mesh objects) without merging
    geometry or intentionally separate clothing layers.
    """
    if rig is None or rig.type != 'ARMATURE':
        return 0
    joints = []
    for side in ('L', 'R'):
        upper = rig.data.bones.get('DEF-upper_arm.' + side)
        forearm = rig.data.bones.get('DEF-forearm.' + side)
        if not upper or not forearm:
            return 0
        center = rig.matrix_world @ upper.head_local
        length = (rig.matrix_world @ forearm.head_local - center).length
        if length < 1e-6:
            return 0
        joints.append((side, np.array(center), length))

    tag = 'zzz_shoulder_weights_v1'
    meshes = [
        mesh for mesh in bpy.context.scene.objects
        if mesh.type == 'MESH' and mesh.data.vertices
        and mesh.find_armature() == rig
        and not mesh.get(tag)
        and not mesh.get('zzz_lindverne_shoulder_weights_v1')
    ]
    if not meshes:
        return 0

    for mesh in meshes:
        if mesh.data.users > 1:
            mesh.data = mesh.data.copy()

    pos_parts = []
    mesh_id_parts = []
    local_idx_parts = []
    edge_parts = []
    slices = []
    offset = 0
    for m_idx, mesh in enumerate(meshes):
        n_verts = len(mesh.data.vertices)
        pos_parts.append(np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices]))
        mesh_id_parts.append(np.full(n_verts, m_idx, dtype=np.int32))
        local_idx_parts.append(np.arange(n_verts, dtype=np.int32))
        if mesh.data.edges:
            edge_parts.append(np.array([tuple(e.vertices) for e in mesh.data.edges], dtype=np.int32) + offset)
        slices.append((offset, offset + n_verts))
        offset += n_verts

    positions = np.concatenate(pos_parts, axis=0)
    mesh_ids = np.concatenate(mesh_id_parts, axis=0)
    local_indices = np.concatenate(local_idx_parts, axis=0)
    all_edges = np.concatenate(edge_parts, axis=0) if edge_parts else np.empty((0, 2), dtype=np.int32)
    if not all_edges.size:
        return 0

    all_vg_names = {g.name for mesh in meshes for g in mesh.vertex_groups}
    changed_meshes = set()

    for side, center, length in joints:
        arm_names = {
            name for name in all_vg_names
            if name in {'DEF-shoulder.' + side, 'DEF-upper_arm.' + side, 'DEF-upper_arm.' + side + '.001'}
            or (f'_{side}_' in name and any(part in name for part in ('Clavicle', 'UpArm_Twist')))
        }
        if not arm_names:
            continue
        group_names = sorted(arm_names | {'DEF-spine.003', 'DEF-spine.004'})
        target_names = set(group_names)
        name_to_col = {name: col for col, name in enumerate(group_names)}
        arm_cols = [name_to_col[n] for n in arm_names if n in name_to_col]

        weights = np.zeros((len(positions), len(group_names)))
        for m_idx, mesh in enumerate(meshes):
            start, _ = slices[m_idx]
            local_lookup = {g.index: name_to_col[g.name] for g in mesh.vertex_groups if g.name in name_to_col}
            if not local_lookup:
                continue
            for vertex in mesh.data.vertices:
                for assignment in vertex.groups:
                    col = local_lookup.get(assignment.group)
                    if col is not None:
                        weights[start + vertex.index, col] = assignment.weight

        totals = weights.sum(axis=1)
        arm = weights[:, arm_cols].sum(axis=1)
        distance = np.linalg.norm(positions - center, axis=1)
        strength = np.clip((length * .65 - distance) / (length * .35), 0, 1) * .5
        strength[(arm < .01) | (totals < .1)] = 0
        if not np.any(strength):
            continue

        seams = _find_combined_seam_groups(
            meshes, mesh_ids, local_indices, positions, strength, totals, weights, target_names
        )
        representatives = np.arange(len(positions))
        for seam in seams:
            representatives[seam] = seam[0]
        edges = np.unique(np.sort(representatives[all_edges], axis=1), axis=0)
        edges = edges[edges[:, 0] != edges[:, 1]]
        first, second = edges.T
        valid = (totals[first] > .1) & (totals[second] > .1)
        first, second = first[valid], second[valid]
        edge_weights = 1 / np.maximum(np.linalg.norm(positions[first] - positions[second], axis=1), 1e-5)
        degree = np.zeros(len(positions))
        np.add.at(degree, first, edge_weights)
        np.add.at(degree, second, edge_weights)
        proportions = weights / np.maximum(totals[:, None], 1e-12)
        for seam in seams:
            proportions[seam] = proportions[seam].mean(axis=0)
        blend = np.where(degree > 0, strength, 0)[:, None]
        for _ in range(24):
            neighbors = np.zeros_like(weights)
            np.add.at(neighbors, first, proportions[second] * edge_weights[:, None])
            np.add.at(neighbors, second, proportions[first] * edge_weights[:, None])
            average = neighbors / np.maximum(degree[:, None], 1e-12)
            proportions = proportions * (1 - blend) + average * blend
            for seam in seams:
                proportions[seam] = proportions[seam[0]]
        result = proportions * totals[:, None]

        for m_idx, mesh in enumerate(meshes):
            start, end = slices[m_idx]
            local_strength = strength[start:end]
            active_local = np.flatnonzero(local_strength > 0)
            if not len(active_local):
                continue
            mesh_groups = {g.name: g for g in mesh.vertex_groups}
            for col, gname in enumerate(group_names):
                grp = mesh_groups.get(gname)
                for local_idx in active_local:
                    g_idx = start + int(local_idx)
                    value = float(result[g_idx, col])
                    if value > 1e-8:
                        if grp is None:
                            grp = mesh.vertex_groups.new(name=gname)
                            mesh_groups[gname] = grp
                        grp.add([int(local_idx)], value, 'REPLACE')
                    elif grp is not None and weights[g_idx, col] > 0:
                        grp.remove([int(local_idx)])
            changed_meshes.add(mesh)

    repaired = 0
    for mesh in changed_meshes:
        mesh[tag] = True
        mesh.update_tag()
        repaired += 1
    if repaired:
        rig.update_tag()
        bpy.context.view_layer.update()
    return repaired
