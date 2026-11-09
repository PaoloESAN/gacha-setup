"""Recover ZZZ skeletons whose skin link matrices disagree with BindPose."""
import re

import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix

from setup_wizard.utils.optional_addons import temporary_addon


def _child(element, name):
    return next((item for item in element.elems if item.id == name), None) if element else None


def _matrix(values):
    return Matrix(tuple(tuple(values[column * 4 + row] for column in range(4)) for row in range(4)))


def restore_zzz_bind_pose(filepath, armature):
    """Repair only demonstrably displaced hand chains, using the FBX BindPose.

    Normal exports and deliberately different mesh bind offsets are left alone.
    The repair runs before chain orientation or pose clearing can lose the
    importer's bone-axis correction. Skin group names are reconciled with
    their actual bind joints; mesh coordinates and morphs stay intact.
    """
    if armature.get('_gacha_zzz_bind_pose_v1'):
        return 0
    with temporary_addon('io_scene_fbx'):
        from io_scene_fbx import parse_fbx
        from io_scene_fbx.fbx_utils import RIGHT_HAND_AXES
        try:
            root, _ = parse_fbx.parse(filepath)
        except (OSError, ValueError):
            # The binary parser cannot inspect ASCII exports accepted by FBX
            # importers. No readable pose is evidence for changing their rig.
            return 0
    objects, connections = _child(root, b'Objects'), _child(root, b'Connections')
    if objects is None or connections is None:
        return 0
    by_id = {item.props[0]: item for item in objects.elems}
    names = {identifier: item.props[1].split(b'\x00')[0].decode('utf-8')
             for identifier, item in by_id.items() if item.id == b'Model'}
    poses = {}
    for item in objects.elems:
        if item.id != b'Pose' or item.props[-1] not in {b'BindPose', b'RestPose'}:
            continue
        for entry in item.elems:
            if entry.id == b'PoseNode':
                node, matrix = _child(entry, b'Node'), _child(entry, b'Matrix')
                if node and matrix and node.props[0] in names:
                    poses[names[node.props[0]]] = _matrix(matrix.props[0])
    settings = _child(_child(root, b'GlobalSettings'), b'Properties70')
    props = {p.props[0]: p.props[4] for p in settings.elems if len(p.props) > 4} if settings else {}
    axes = tuple((props.get(axis, default), props.get(axis + b'Sign', 1))
                 for axis, default in ((b'UpAxis', 2), (b'FrontAxis', 1), (b'CoordAxis', 0)))
    orientation = {value: key for key, value in RIGHT_HAND_AXES.items()}.get(axes)
    if orientation is None:
        return 0
    up, forward = orientation
    unit = props.get(b'UnitScaleFactor', 1.0) * .01 / bpy.context.scene.unit_settings.scale_length
    conversion = (armature.matrix_world.inverted_safe() @ Matrix.Scale(unit, 4)
                  @ axis_conversion(from_forward=forward, from_up=up).to_4x4())
    targets = {name: conversion @ matrix for name, matrix in poses.items()
               if name in armature.data.bones}

    # A whole hand translated by an intentional bind offset is not a broken
    # chain. Require large relative joint errors in both hands instead.
    for side in ('L', 'R'):
        hand = f'Bip001 {side} Hand'
        fingers = [name for name in targets if re.fullmatch(rf'Bip001 {side} Finger[0-4][0-2]?', name)]
        if hand not in targets or len(fingers) < 6:
            return 0
        span = max((targets[name].translation - targets[hand].translation).length for name in fingers)
        if span < 1e-6:
            return 0
        errors = [(armature.data.bones[name].head_local - armature.data.bones[hand].head_local
                   - (targets[name].translation - targets[hand].translation)).length for name in fingers]
        if sum(error > span * 2 for error in errors) < 2:
            return 0

    links, children = {}, {}
    for connection in connections.elems:
        if len(connection.props) < 3 or connection.props[0] != b'OO':
            continue
        bone_id, cluster_id = connection.props[1:3]
        children.setdefault(cluster_id, []).append(bone_id)
        cluster = by_id.get(cluster_id)
        if bone_id in names and cluster is not None and cluster.id == b'Deformer':
            matrix = _child(cluster, b'TransformLink')
            if matrix is not None:
                links.setdefault(names[bone_id], []).append(conversion @ _matrix(matrix.props[0]))
    # The broken export connects skin clusters to the wrong Model IDs too.
    # Their matrices still identify the actual rest joints. Repair the group
    # association alongside the skeleton, or curling a finger moves the torso.
    def skin_joint(name, matrix):
        matches = [candidate for candidate, target in targets.items()
                   if max(abs(matrix[row][column] - target[row][column])
                          for row in range(4) for column in range(4)) < 1e-4]
        if not matches:
            return None
        if name in matches:
            return name
        # Coincident helper/twist joints can have identical rest matrices.
        # Prefer their standard deform joint when the source cannot
        # distinguish them, retaining all contributing skin weights.
        return min(matches, key=lambda item: (not item.startswith('Bip001 '), len(item), item))

    mesh_weights = {}
    for model_id, model in by_id.items():
        if model.id != b'Model' or model.props[-1] != b'Mesh':
            continue
        weight_names = {}
        for geometry_id in children.get(model_id, []):
            geometry = by_id.get(geometry_id)
            if geometry is None or geometry.id != b'Geometry':
                continue
            for skin_id in children.get(geometry_id, []):
                skin = by_id.get(skin_id)
                if skin is None or skin.id != b'Deformer' or skin.props[-1] != b'Skin':
                    continue
                for cluster_id in children.get(skin_id, []):
                    cluster = by_id.get(cluster_id)
                    matrix = _child(cluster, b'TransformLink')
                    if matrix is None:
                        continue
                    for bone_id in children.get(cluster_id, []):
                        if bone_id not in names:
                            continue
                        name = names[bone_id]
                        target_name = skin_joint(name, conversion @ _matrix(matrix.props[0]))
                        if target_name is None:
                            # An intentional per-mesh bind offset is not a
                            # shuffled joint. Never partially remap a model.
                            return 0
                        weight_names[name] = target_name
        mesh_weights[names[model_id]] = weight_names
    rest = {}
    for name, target in targets.items():
        bone = armature.data.bones[name]
        if (bone.head_local - target.translation).length < 1e-5:
            continue
        if name in links:
            # Retain Blender's FBX bone-axis correction, replacing only the
            # erroneous source bind transform (including its rotation).
            source = min(links[name], key=lambda matrix: (matrix.translation - bone.head_local).length)
            rest[name] = target @ source.inverted_safe() @ bone.matrix_local
        else:
            matrix = bone.matrix_local.copy()
            matrix.translation = target.translation
            rest[name] = matrix
    if not rest:
        return 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not any(mod.type == 'ARMATURE' and mod.object == armature
                                        for mod in obj.modifiers):
            continue
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        weight_names = mesh_weights.get(obj.name, mesh_weights.get(re.sub(r'\.\d{3}$', '', obj.name), {}))
        changed = {group.index: (group, weight_names[group.name]) for group in obj.vertex_groups
                   if group.name in weight_names and weight_names[group.name] != group.name}
        target_names = {name for _, name in changed.values()}
        retained = {group.index: group.name for group in obj.vertex_groups
                    if group.index not in changed and group.name in target_names}
        contributions = {}
        for vertex in obj.data.vertices:
            for group in vertex.groups:
                if group.group in changed:
                    target_name = changed[group.group][1]
                elif group.group in retained:
                    target_name = retained[group.group]
                else:
                    continue
                weights = contributions.setdefault(target_name, {})
                weights[vertex.index] = weights.get(vertex.index, 0.0) + group.weight
        # Rename first to handle permutations without name collisions.
        for index, (group, _) in changed.items():
            group.name = f'__gacha_zzz_bind_{index}'
        for name, weights in contributions.items():
            target_group = obj.vertex_groups.get(name)
            if target_group is None:
                target_group = obj.vertex_groups.new(name=name)
            for index, weight in weights.items():
                target_group.add([index], min(weight, 1.0), 'REPLACE')
        for group, _ in changed.values():
            obj.vertex_groups.remove(group)
    attachments = {obj: obj.matrix_world.copy() for obj in bpy.context.scene.objects
                   if obj.parent == armature and obj.parent_type == 'BONE'}
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name, matrix in rest.items():
        armature.data.edit_bones[name].matrix = matrix
    bpy.ops.object.mode_set(mode='OBJECT')
    for name in rest:
        armature.pose.bones[name].matrix_basis.identity()
    bpy.context.view_layer.update()
    for obj, world in attachments.items():
        obj.matrix_world = world
    armature['_gacha_zzz_bind_pose_v1'] = True
    print(f'[ZZZ IMPORT] Restored {len(rest)} displaced joints from FBX BindPose')
    return len(rest)
