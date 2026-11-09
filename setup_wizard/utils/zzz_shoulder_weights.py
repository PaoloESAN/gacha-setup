"""Local shoulder-transition skin-weight smoothing for ZZZ characters."""
import bpy
import numpy as np

from setup_wizard.utils.zzz_hip_follow import hip_seam_groups


def smooth_zzz_shoulder_weights(rig):
    """Smooth only the arm/clavicle/chest blend around the shoulder sockets.

    Retain every vertex position, morph, unrelated influence and per-vertex
    weight total. Stitch equivalent UV-split vertices in the smoothing graph
    without merging geometry or intentionally separate clothing layers.
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
    repaired = 0
    tag = 'zzz_shoulder_weights_v1'
    for mesh in bpy.context.scene.objects:
        if (mesh.type != 'MESH' or not mesh.data.vertices
                or mesh.find_armature() != rig or mesh.get(tag)
                or mesh.get('zzz_lindverne_shoulder_weights_v1')):
            continue
        if mesh.data.users > 1:
            mesh.data = mesh.data.copy()
        positions = np.array([mesh.matrix_world @ vertex.co for vertex in mesh.data.vertices])
        changed = False
        for side, center, length in joints:
            arm_names = {group.name for group in mesh.vertex_groups if group.name in {
                'DEF-shoulder.' + side, 'DEF-upper_arm.' + side, 'DEF-upper_arm.' + side + '.001'}
                or (f'_{side}_' in group.name and any(part in group.name for part in ('Clavicle', 'UpArm_Twist')))}
            groups = [group for group in mesh.vertex_groups if group.name in arm_names
                      or group.name in {'DEF-spine.003', 'DEF-spine.004'}]
            if not arm_names:
                continue
            lookup = {group.index: column for column, group in enumerate(groups)}
            weights = np.zeros((len(positions), len(groups)))
            for vertex in mesh.data.vertices:
                for assignment in vertex.groups:
                    if assignment.group in lookup:
                        weights[vertex.index, lookup[assignment.group]] = assignment.weight
            totals = weights.sum(axis=1)
            arm = weights[:, [i for i, group in enumerate(groups) if group.name in arm_names]].sum(axis=1)
            distance = np.linalg.norm(positions - center, axis=1)
            strength = np.clip((length * .65 - distance) / (length * .35), 0, 1) * .5
            strength[(arm < .01) | (totals < .1)] = 0
            if not np.any(strength):
                continue
            seams = hip_seam_groups(mesh, positions, strength, totals, lookup)
            representatives = np.arange(len(positions))
            for seam in seams:
                representatives[seam] = seam[0]
            edges = np.array([tuple(edge.vertices) for edge in mesh.data.edges])
            if not edges.size:
                continue
            edges = np.unique(np.sort(representatives[edges], axis=1), axis=0)
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
            for index in np.flatnonzero(strength > 0):
                for column, group in enumerate(groups):
                    value = float(result[index, column])
                    if value > 1e-8:
                        group.add([int(index)], value, 'REPLACE')
                    elif weights[index, column] > 0:
                        group.remove([int(index)])
            changed = True
        if changed:
            mesh[tag] = True
            mesh.update_tag()
            repaired += 1
    if repaired:
        rig.update_tag()
        bpy.context.view_layer.update()
    return repaired
