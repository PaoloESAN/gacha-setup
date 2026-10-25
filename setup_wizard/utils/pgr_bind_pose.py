"""Rebase PGR skins with per-mesh bind poses onto the FBX skeleton pose.

Unity exports can bind the same bone at different positions for each mesh.
Blender has one rest matrix per bone, so those differences must be baked into
the mesh (including every morph) before clearing the imported pose or rigging.
"""
import re

import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix, Vector
from io_scene_fbx import parse_fbx
from io_scene_fbx.fbx_utils import RIGHT_HAND_AXES


def _child(element, identifier):
    return next((e for e in element.elems if e.id == identifier), None) if element else None


def _matrix(values):
    return Matrix(tuple(tuple(values[j * 4 + i] for j in range(4)) for i in range(4)))


def bind_unskinned_pgr_faces(imported_objects):
    """Attach facial parts exported as static meshes to this model's head."""
    armatures = [o for o in imported_objects if o.type == 'ARMATURE']
    if len(armatures) != 1:
        return []
    armature = armatures[0]
    head = next((b for b in armature.data.bones
                 if re.sub(r'[^a-z0-9]', '', b.name.lower()) in
                 {'bip001head', 'headm', 'head', 'defspine006'}), None)
    if head is None:
        return []
    bound = []
    for mesh in imported_objects:
        if (mesh.type != 'MESH' or mesh.vertex_groups or mesh.parent_type == 'BONE'
                or any(m.type == 'ARMATURE' for m in mesh.modifiers)
                or not re.search(r'(?:face(?:ex\d*)?|eyes?\d*|shade|eyeshadow|mouth)(?:\.\d{3})?$', mesh.name, re.I)):
            continue
        world = mesh.matrix_world.copy()
        group = mesh.vertex_groups.new(name=head.name)
        group.add(list(range(len(mesh.data.vertices))), 1.0, 'REPLACE')
        modifier = mesh.modifiers.new('PGR Rigid Face', 'ARMATURE')
        modifier.object = armature
        mesh.parent = armature
        mesh.matrix_world = world
        mesh['setup_wizard_pgr_rigid_face'] = True
        bound.append(mesh.name)
    return bound


def bind_unskinned_bianca_bands(imported_objects):
    """Weight each rigid bracelet island to its corresponding hand."""
    armatures = [o for o in imported_objects if o.type == 'ARMATURE']
    if len(armatures) != 1:
        return []
    armature = armatures[0]
    hands = {}
    for bone in armature.data.bones:
        name = re.sub(r'[^a-z0-9]', '', bone.name.lower())
        for side in ('l', 'r'):
            if name in {f'bip001{side}hand', f'wrist{side}', f'defhand{side}'}:
                hands[side] = bone
    if len(hands) != 2:
        return []
    bound = []
    for mesh in imported_objects:
        if (mesh.type != 'MESH' or mesh.vertex_groups
                or any(m.type == 'ARMATURE' for m in mesh.modifiers)
                or not re.search(r'bianka.*band(?:\.\d{3})?$', mesh.name, re.I)):
            continue
        # Both bracelets can be stored in one object. Keep every connected
        # piece rigid, including the separate decorative rings and spikes.
        neighbors = [[] for _ in mesh.data.vertices]
        for edge in mesh.data.edges:
            a, b = edge.vertices
            neighbors[a].append(b)
            neighbors[b].append(a)
        pending = set(range(len(neighbors)))
        groups = {side: mesh.vertex_groups.new(name=bone.name) for side, bone in hands.items()}
        hand_positions = {side: armature.matrix_world @ bone.head_local for side, bone in hands.items()}
        while pending:
            stack = [pending.pop()]
            island = []
            while stack:
                index = stack.pop()
                island.append(index)
                for neighbor in neighbors[index]:
                    if neighbor in pending:
                        pending.remove(neighbor)
                        stack.append(neighbor)
            center = mesh.matrix_world @ (sum((mesh.data.vertices[i].co for i in island), Vector()) / len(island))
            side = min(hands, key=lambda side: (center - hand_positions[side]).length_squared)
            groups[side].add(island, 1.0, 'REPLACE')
        world = mesh.matrix_world.copy()
        modifier = mesh.modifiers.new('PGR Rigid Bands', 'ARMATURE')
        modifier.object = armature
        mesh.parent = armature
        mesh.matrix_world = world
        mesh['setup_wizard_pgr_rigid_bands'] = True
        bound.append(mesh.name)
    return bound


def restore_pgr_bind_pose(filepath, imported_objects):
    """Repair only freshly imported meshes; return the number rebased."""
    root, _ = parse_fbx.parse(filepath)
    objects = _child(root, b'Objects')
    connections = _child(root, b'Connections')
    if not objects or not connections:
        return 0
    by_id = {e.props[0]: e for e in objects.elems}
    parents, children = {}, {}
    for connection in connections.elems:
        if len(connection.props) >= 3 and connection.props[0] == b'OO':
            source, target = connection.props[1:3]
            parents.setdefault(source, []).append(target)
            children.setdefault(target, []).append(source)

    poses = {}
    for element in objects.elems:
        if element.id != b'Pose' or element.props[-1] not in {b'BindPose', b'RestPose'}:
            continue
        for node in element.elems:
            if node.id == b'PoseNode':
                identifier, matrix = _child(node, b'Node'), _child(node, b'Matrix')
                if identifier and matrix:
                    poses[identifier.props[0]] = _matrix(matrix.props[0])
    if not poses:
        return 0

    settings = _child(_child(root, b'GlobalSettings'), b'Properties70')
    props = {p.props[0]: p.props[4] for p in settings.elems if len(p.props) > 4} if settings else {}
    axis_key = tuple((props.get(axis, default), props.get(axis + b'Sign', 1))
                     for axis, default in ((b'UpAxis', 2), (b'FrontAxis', 1), (b'CoordAxis', 0)))
    up, forward = {value: key for key, value in RIGHT_HAND_AXES.items()}.get(axis_key, ('Z', 'Y'))
    unit = props.get(b'UnitScaleFactor', 1.0) * .01 / bpy.context.scene.unit_settings.scale_length
    conversion = Matrix.Scale(unit, 4) @ axis_conversion(from_forward=forward, from_up=up).to_4x4()
    imported_meshes = [o for o in imported_objects if o.type == 'MESH']
    repaired = 0
    for geometry in objects.elems:
        if geometry.id != b'Geometry' or geometry.props[-1] != b'Mesh':
            continue
        model_ids = [i for i in parents.get(geometry.props[0], []) if by_id.get(i) and by_id[i].id == b'Model']
        names = {by_id[i].props[1].split(b'\x00')[0].decode('utf-8') for i in model_ids}
        mesh = next((o for o in imported_meshes if o.name in names), None)
        if mesh is None:
            mesh = next((o for o in imported_meshes if re.sub(r'\.\d{3}$', '', o.name) in names), None)
        if mesh is None:
            continue
        if mesh.get('setup_wizard_pgr_bind_pose'):
            continue
        source_vertices = _child(geometry, b'Vertices')
        if source_vertices is None or len(source_vertices.props[0]) != len(mesh.data.vertices) * 3:
            raise RuntimeError(f'PGR bind-pose vertex mapping changed for {mesh.name}')
        matrices = {}
        for skin_id in children.get(geometry.props[0], []):
            skin = by_id.get(skin_id)
            if not skin or skin.id != b'Deformer' or skin.props[-1] != b'Skin':
                continue
            for cluster_id in children.get(skin_id, []):
                cluster = by_id.get(cluster_id)
                if not cluster or cluster.id != b'Deformer' or cluster.props[-1] != b'Cluster':
                    continue
                bone_id = next((i for i in children.get(cluster_id, []) if i in poses), None)
                transform = _child(cluster, b'Transform')
                if bone_id is None or transform is None:
                    continue
                name = by_id[bone_id].props[1].split(b'\x00')[0].decode('utf-8')
                group = mesh.vertex_groups.get(name)
                if group:
                    matrices[group.index] = mesh.matrix_world.inverted_safe() @ conversion @ poses[bone_id] @ _matrix(transform.props[0])
        if not matrices:
            continue
        # Native importer leaves PGR's geometry coordinates unchanged. Avoid
        # touching skins already bound in the canonical model space.
        transforms = []
        for vertex in mesh.data.vertices:
            weights = [(matrices[g.group], g.weight) for g in vertex.groups if g.group in matrices and g.weight > 0]
            total = sum(w for _, w in weights)
            if total:
                matrix = Matrix(tuple(tuple(sum(m[row][col] * w for m, w in weights) / total
                                                  for col in range(4)) for row in range(4)))
            else:
                matrix = Matrix.Identity(4)
            transforms.append(matrix)
        displacement = max(((m @ v.co - v.co).length for m, v in zip(transforms, mesh.data.vertices)), default=0)
        if displacement < 1e-5:
            continue
        blocks = mesh.data.shape_keys.key_blocks if mesh.data.shape_keys else ()
        if blocks:
            for block in blocks:
                for point, matrix in zip(block.data, transforms):
                    point.co = matrix @ point.co
        else:
            for vertex, matrix in zip(mesh.data.vertices, transforms):
                vertex.co = matrix @ vertex.co
        mesh.data.update()
        mesh['setup_wizard_pgr_bind_pose'] = True
        repaired += 1
        print(f'[PGR BIND] Rebased {mesh.name} ({displacement:.6f} m)')
    return repaired
