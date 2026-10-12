"""Geometry-based identification of floating ZZZ eye-shadow overlays."""
import re
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def classify_zzz_eyeshadow_faces(face_object):
    """Return overlay polygon indices, protecting all eye-skinned geometry.

    Eye weights provide the reference surface and left/right axis. Head/neck
    joint positions supply up; bone tails are deliberately ignored because FBX
    importers and rig generation reorient them. Only floating layers in front
    of the upper eye qualify.
    """
    mesh = face_object.data
    armature = face_object.find_armature()
    if not armature:
        return set()
    head = next((armature.data.bones.get(name) for name in
                 ('Bip001 Head', 'Bip001_Head', 'Head', 'Head_M', 'head')
                 if armature.data.bones.get(name)), None)
    if head is None:
        head = next((bone for bone in armature.data.bones
                     if re.search(r'(?:^|[_.\s])head$', bone.name.lower())), None)
    if head is None:
        return set()

    eye_groups = {}
    for group in face_object.vertex_groups:
        low = group.name.lower()
        if not any(word in low for word in ('eye', 'pupil', 'iris', 'highlight')):
            continue
        if any(word in low for word in ('brow', 'lid', 'lash', 'shadow', 'track', 'ctrl', 'mch', 'org')):
            continue
        side = next((side for side in ('l', 'r') if re.search(r'(?:^|[_.\s])' + side + r'(?:$|[_.\s])', low)), None)
        if side:
            eye_groups[group.index] = side
    weighted = {'l': set(), 'r': set()}
    for vertex in mesh.vertices:
        for assignment in vertex.groups:
            if assignment.group in eye_groups and assignment.weight > 0.1:
                weighted[eye_groups[assignment.group]].add(vertex.index)
    if not weighted['l'] or not weighted['r']:
        return set()
    coordinates = [face_object.matrix_world @ vertex.co for vertex in mesh.vertices]
    centers = {side: sum((coordinates[i] for i in indices), Vector()) / len(indices)
               for side, indices in weighted.items()}
    right = centers['l'] - centers['r']
    neck = next((armature.data.bones.get(name) for name in
                 ('Bip001 Neck', 'Bip001_Neck', 'Neck', 'Neck_M', 'neck', 'DEF-neck')
                 if armature.data.bones.get(name)), head.parent)
    if head.parent and 'neck' in head.parent.name.lower():
        neck = head.parent
    if neck is None:
        return set()
    up = armature.matrix_world.to_3x3() @ (head.head_local - neck.head_local)
    if right.length < 1e-8 or up.length < 1e-8:
        return set()
    right.normalize()
    up -= right * up.dot(right)
    if up.length < 1e-8:
        return set()
    up.normalize()
    forward = right.cross(up).normalized()
    head_position = armature.matrix_world @ head.head_local
    eye_center = (centers['l'] + centers['r']) * 0.5
    if (eye_center - head_position).dot(forward) < 0:
        forward.negate()
    protected = weighted['l'] | weighted['r']
    eye_polygons = [list(p.vertices) for p in mesh.polygons if all(i in protected for i in p.vertices)]
    if not eye_polygons:
        return set()
    # Refine forward from the eye surface itself: the neck can lean while the
    # eyeballs stay upright. Sign-align triangle normals to prevent mirrored
    # winding or back faces from cancelling the reference direction.
    eye_normal = Vector()
    for vertices in eye_polygons:
        origin = coordinates[vertices[0]]
        for i in range(1, len(vertices) - 1):
            normal = (coordinates[vertices[i]] - origin).cross(coordinates[vertices[i + 1]] - origin)
            projection = normal.dot(forward)
            if normal.length > 1e-12 and abs(projection) > normal.length * 0.5:
                eye_normal += normal if projection > 0 else -normal
    eye_normal -= right * eye_normal.dot(right)
    if eye_normal.length > 1e-12:
        forward = eye_normal.normalized()
        refined_up = forward.cross(right).normalized()
        if refined_up.dot(up) < 0:
            refined_up.negate()
        up = refined_up
    eye_surface = BVHTree.FromPolygons(coordinates, eye_polygons)
    heights = [coordinates[i].dot(up) for i in protected]
    eye_height = max(heights) - min(heights)
    if eye_height < 1e-8:
        return set()
    epsilon = eye_height * 0.001

    adjacent = [[] for _ in mesh.vertices]
    for polygon in mesh.polygons:
        for index in polygon.vertices:
            adjacent[index].append(polygon.index)
    visited = set()
    islands = []
    for polygon in mesh.polygons:
        if polygon.index in visited:
            continue
        pending = [polygon.index]
        visited.add(polygon.index)
        island = []
        while pending:
            index = pending.pop()
            island.append(index)
            for vertex in mesh.polygons[index].vertices:
                for neighbor in adjacent[vertex]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        pending.append(neighbor)
        if 4 <= len(island) <= 150 and not any(vertex in protected for index in island for vertex in mesh.polygons[index].vertices):
            islands.append(island)
    if not islands:
        return set()
    candidate_polygons = [list(mesh.polygons[index].vertices) for island in islands for index in island]
    front_surface = BVHTree.FromPolygons(coordinates, candidate_polygons)
    polygon_islands = [number for number, island in enumerate(islands) for _ in island]
    supported_islands = {}
    # A shadow covers the central upper eye surface. Eyelashes and rim strips
    # can sit in front too, but only overlap its perimeter and must stay opaque.
    for side, center in centers.items():
        horizontal = [coordinates[i].dot(right) for i in weighted[side]]
        eye_width = max(horizontal) - min(horizontal)
        for x in (-0.2, 0.0, 0.2):
            for z in (0.0, 0.1, 0.2):
                probe = center + right * (x * eye_width) + up * (z * eye_height)
                origin = probe + forward * eye_height * 4
                eye_hit, _, _, _ = eye_surface.ray_cast(origin, -forward, eye_height * 8)
                hit, _, polygon_index, _ = front_surface.ray_cast(origin, -forward, eye_height * 8)
                if hit is not None and eye_hit is not None and epsilon < (hit - eye_hit).dot(forward) < eye_height * 0.3:
                    number = polygon_islands[polygon_index]
                    supported_islands[number] = supported_islands.get(number, 0) + 1
    selected = set()
    for number, island in enumerate(islands):
        if supported_islands.get(number, 0) < 2:
            continue
        qualifying = 0
        overlapping = 0
        for index in island:
            polygon = mesh.polygons[index]
            center = sum((coordinates[i] for i in polygon.vertices), Vector()) / len(polygon.vertices)
            side = min(centers, key=lambda s: abs((center - centers[s]).dot(right)))
            if (center - centers[side]).dot(up) < -eye_height * 0.08:
                continue
            origin = center + forward * eye_height * 4
            eye_hit, _, _, _ = eye_surface.ray_cast(origin, -forward, eye_height * 8)
            if eye_hit is None:
                continue
            overlapping += 1
            offset = (center - eye_hit).dot(forward)
            if not epsilon < offset < eye_height * 0.3:
                continue
            front_hit, _, _, _ = front_surface.ray_cast(origin, -forward, eye_height * 8)
            if front_hit is not None and (front_hit - center).dot(forward) > epsilon:
                continue
            qualifying += 1
        if qualifying >= 2 and qualifying >= overlapping * 0.5 and qualifying >= len(island) * 0.1:
            selected.update(island)
    return selected
