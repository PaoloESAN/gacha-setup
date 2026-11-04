"""Calibrate legacy Genshin eye pivots from the separate sclera geometry."""
import bpy
import numpy as np
from mathutils import Vector


def needs_eye_pivot_calibration(armature):
    """Only the validated legacy exports opt into sclera fitting.

    A nearby face island is not necessarily an eyeball. In particular Kinich's
    authored pivots must survive: the same fit also accepts his eyelid patches.
    Keep unknown characters unchanged until their eye layout is validated.
    """
    identity = ' '.join((armature.name, armature.data.name,
                         str(armature.get('gacha_character', '')))).casefold()
    names = ('neuvillette', 'alhaitham', 'alhatham')
    if any(name in identity for name in names):
        return True
    # BetterFBX can name Alhaitham's main armature Collider. Identify that
    # export through its own bound materials, never another scene character.
    return any(any(name in material.name.casefold() for name in names)
               for obj in bpy.context.scene.objects
               if obj.type == 'MESH' and obj.find_armature() == armature
               for material in obj.data.materials if material)


def calibrate_eye_pivots(armature):
    """Run in Edit mode; preserve the skin and pupil rest positions.

    Some exports place A01 well behind the eyeball. Rotating that long lever
    moves the iris through the eyelids. Fit the nearby sclera island instead;
    reject flat/ambiguous surfaces rather than guessing a character-specific
    offset. The same routine can repair an already generated rig.
    """
    if not needs_eye_pivot_calibration(armature):
        return {}
    bones = armature.data.edit_bones
    inverse = armature.matrix_world.inverted()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH'
              and o.find_armature() == armature]
    head = next((bones.get(n) for n in ('Bip001 Head', 'head', 'Head_M') if bones.get(n)), None)
    if head is None:
        return {}
    # Exported head bones can point forward rather than up. In raw FBX space
    # this confused depth with height and selected an eyelid as the eyeball.
    vertical = np.array((inverse.to_3x3() @ Vector((0, 0, 1))).normalized())
    pupils = {}
    for side in ('L', 'R'):
        names = (f'+EyeBone {side} A02', f'+EyeBoneA02.{side}')
        points = []
        for obj in meshes:
            if 'star' in obj.name.casefold():
                continue
            group = next((obj.vertex_groups.get(n) for n in names if obj.vertex_groups.get(n)), None)
            if group is None:
                continue
            transform = inverse @ obj.matrix_world
            points.extend(tuple(transform @ v.co) for v in obj.data.vertices
                          if any(g.group == group.index and g.weight > .5 for g in v.groups))
        if len(points) >= 8:
            pupils[side] = np.array(points, dtype=float)
    if len(pupils) != 2:
        return {}
    lateral = pupils['L'].mean(axis=0) - pupils['R'].mean(axis=0)
    lateral -= vertical * np.dot(lateral, vertical)
    lateral /= np.linalg.norm(lateral)
    # Unmerged exports retain the sclera as Face_Eye. Prefer that explicit
    # surface over eyelashes and eyelids from the main face mesh.
    sclera_meshes = [o for o in meshes if 'face_eye' in o.name.casefold()]
    islands = []
    for obj in sclera_meshes or meshes:
        name = obj.name.casefold()
        if not any(k in name for k in ('face', 'eye')) or any(k in name for k in ('star', 'pupil', 'brow')):
            continue
        adjacency = [[] for _ in obj.data.vertices]
        for edge in obj.data.edges:
            a, b = edge.vertices
            adjacency[a].append(b)
            adjacency[b].append(a)
        seen = set()
        transform = inverse @ obj.matrix_world
        for start in range(len(adjacency)):
            if start in seen:
                continue
            stack, indices = [start], []
            seen.add(start)
            while stack:
                index = stack.pop()
                indices.append(index)
                for neighbor in adjacency[index]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            if len(indices) >= 12:
                islands.append(np.array([tuple(transform @ obj.data.vertices[i].co) for i in indices]))
    fitted = {}
    for side, pupil in pupils.items():
        a01 = bones.get(f'+EyeBone {side} A01') or bones.get(f'+EyeBoneA01.{side}')
        a02 = bones.get(f'+EyeBone {side} A02') or bones.get(f'+EyeBoneA02.{side}')
        if a01 is None or a02 is None:
            continue
        pupil_center = pupil.mean(axis=0)
        width = np.ptp(pupil @ lateral)
        height = np.ptp(pupil @ vertical)
        candidates = []
        for points in islands:
            mean = points.mean(axis=0)
            distance = np.linalg.norm(mean - pupil_center)
            if distance > width * .75:
                continue
            if np.ptp(points @ lateral) < width * .8 or np.ptp(points @ vertical) < height * .8:
                continue
            local = points - mean
            coefficient, _, rank, _ = np.linalg.lstsq(
                np.column_stack((2 * local, np.ones(len(points)))), (local * local).sum(axis=1), rcond=None)
            if rank < 4:
                continue
            center = coefficient[:3] + mean
            radius = np.sqrt(max(0., coefficient[3] + np.dot(coefficient[:3], coefficient[:3])))
            if not width * .5 < radius < width * 2:
                continue
            error = np.std(np.linalg.norm(points - center, axis=1))
            # A curved eyelid can fit a sphere better than the sclera. Its
            # center can lie well below the iris, producing a tilted orbit
            # and burying the pupil when viewed or tracked from the side.
            if abs(np.dot(center - pupil_center, vertical)) > height * .25:
                continue
            if error > radius * .18 or np.dot(center - pupil_center, np.array(a01.head) - pupil_center) <= 0:
                continue
            candidates.append((error / radius, distance, center, radius))
        if not candidates:
            continue
        _, _, center, radius = min(candidates, key=lambda item: item[:2])
        fitted[side] = (center, radius, a01, a02)
    # Do not repair just one eye or accept two different facial surfaces.
    if len(fitted) != 2:
        return {}
    left, right = fitted['L'], fitted['R']
    height = max(np.ptp(pupils[s] @ vertical) for s in pupils)
    if (abs(np.dot(left[0] - right[0], vertical)) > height * .25
            or max(left[1], right[1]) > min(left[1], right[1]) * 1.25):
        return {}
    changed = {}
    for side, (center, radius, a01, a02) in fitted.items():
        pupil_center = pupils[side].mean(axis=0)
        if (Vector(center) - a01.head).length < 1e-6:
            continue
        pivot = Vector(center)
        target = bones.get(f'eyetrack_{side}')
        if target:
            offset = pivot - target.head
            # Preserve the target's forward distance and the user's local
            # gaze pose, but place its neutral X/height over the new pivot.
            forward = np.cross(lateral, vertical)
            forward /= np.linalg.norm(forward)
            delta = offset - Vector(forward) * offset.dot(Vector(forward))
            target.head += delta
            target.tail += delta
        for name in (a01.name, f'ORG-eye.{side}', f'eye.{side}', f'+EyeBone {side} A01.001'):
            bone = bones.get(name)
            if bone is None:
                continue
            bone.use_connect = False
            bone.head = pivot
            bone.tail = a02.head
            if name.endswith('A01.001'):
                # The tracking helper points straight forward; its local
                # rotation is transferred to the oblique deformation bone.
                forward = np.array(target.head - pivot) if target else np.cross(lateral, vertical)
                if np.dot(forward, pupil_center - center) < 0:
                    forward = -forward
                bone.tail = pivot + Vector(forward).normalized() * radius
        changed[side] = tuple(pivot)
    if changed and bones.get('eyetrack'):
        tracker = bones['eyetrack']
        targets = [bones.get(f'eyetrack_{side}') for side in ('L', 'R')]
        if all(targets):
            delta = (targets[0].head + targets[1].head) * .5 - tracker.head
            tracker.head += delta
            tracker.tail += delta
    return changed
