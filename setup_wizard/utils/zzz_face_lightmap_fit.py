"""Compare bundled face-map landmarks with the character's actual UV layout."""
import re
import numpy as np
from mathutils import Vector


def nose_uv(face):
    """Locate the protruding nose on the main skin island, excluding eye atlases."""
    mesh = face.data
    uv_layer = mesh.uv_layers.active
    armature = face.find_armature()
    if not uv_layer or not armature:
        return None
    eyes = {'l': [], 'r': []}
    for group in face.vertex_groups:
        low = group.name.lower()
        if 'eye' not in low or any(s in low for s in ('brow', 'lid', 'lash', 'highlight', 'light', 'shadow', 'ctrl')):
            continue
        side = next((s for s in eyes if re.search(r'(?:^|[_.\s])' + s + r'(?:$|[_.\s])', low)), None)
        if side:
            eyes[side].extend(face.matrix_world @ v.co for v in mesh.vertices
                              if any(g.group == group.index and g.weight > .1 for g in v.groups))
    if not all(eyes.values()):
        return None
    centers = {s: sum(points, Vector()) / len(points) for s, points in eyes.items()}
    right = centers['l'] - centers['r']
    spacing = right.length
    if spacing < 1e-8:
        return None
    right.normalize()
    head = next((b for b in armature.data.bones if re.search(r'(?:^|[_.\s])head$', b.name.lower())), None)
    if head is None or head.parent is None:
        return None
    up = armature.matrix_world.to_3x3() @ (head.head_local - head.parent.head_local)
    up -= right * up.dot(right)
    if up.length < 1e-8:
        return None
    up.normalize()
    forward = right.cross(up).normalized()
    center = (centers['l'] + centers['r']) * .5
    if forward.dot(center - armature.matrix_world @ head.head_local) < 0:
        forward.negate()

    adjacent = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacent[a].append(b)
        adjacent[b].append(a)
    visited = set()
    skin = []
    for vertex in mesh.vertices:
        if vertex.index in visited:
            continue
        pending = [vertex.index]
        visited.add(vertex.index)
        island = []
        while pending:
            index = pending.pop()
            island.append(index)
            for neighbor in adjacent[index]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        if len(island) > len(skin):
            skin = island
    candidates = []
    for index in skin:
        offset = face.matrix_world @ mesh.vertices[index].co - center
        if abs(offset.dot(right)) < spacing * .2 and -spacing * .8 < offset.dot(up) < spacing * .1:
            candidates.append((offset.dot(forward), index))
    if not candidates:
        return None
    index = max(candidates)[1]
    uvs = [uv_layer.data[loop.index].uv.copy() for loop in mesh.loops if loop.vertex_index == index]
    if not uvs or any((uv - uvs[0]).length > .01 for uv in uvs):
        return None
    return tuple(uvs[0])


def select_face_lightmap(images, faces):
    """Rank maps with an identifiable nose mask; abstain without usable evidence."""
    landmarks = [uv for face in faces if (uv := nose_uv(face)) is not None]
    if not landmarks:
        return None
    ranked = []
    for image in images:
        width, height = image.size
        if not width or not height or image.channels != 4:
            continue
        pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(height, width, 4)
        # ZZZ stores the small nose specular mask in blue. A distinct local
        # patch supplies evidence; flat channels and broad furry markings do not.
        blue = pixels[:, :, 2]
        mask = (blue > .2) & (blue - pixels[:, :, 0] > .08) & (blue - pixels[:, :, 1] > .08)
        mask[:, :int(width * .4)] = False
        mask[:, int(width * .6):] = False
        mask[:int(height * .2)] = False
        mask[int(height * .8):] = False
        rows, columns = np.nonzero(mask)
        if not 2 <= len(rows) <= width * height * .005:
            continue
        weights = blue[mask]
        uv = (np.average(columns + .5, weights=weights) / width,
              np.average(rows + .5, weights=weights) / height)
        score = sum((uv[0] - u) ** 2 + (uv[1] - v) ** 2 for u, v in landmarks) / len(landmarks)
        ranked.append((score, image.name, image))
    if not ranked:
        return None
    score, _, image = min(ranked, key=lambda item: item[:2])
    return image if score < .1 ** 2 else None
