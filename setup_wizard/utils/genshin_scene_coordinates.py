"""Bring characters exported in cutscene world coordinates into rig space."""
import math
import bpy
from mathutils import Matrix, Vector


def normalize_cutscene_coordinates(armature, objects):
    """Only rebase far-away imports; preserve mesh/bone alignment and morphs."""
    meshes = [o for o in objects if o.type == 'MESH' and o.find_armature() == armature]
    if not meshes:
        return False
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    size = (high - low).length
    center = (high + low) * .5
    if center.length < max(10., size * 10.):
        return False
    # Cutscene exports usually share the actor origin across every mesh.
    # Keep its intended ground height, rather than grounding a floating pose.
    origins = [o.matrix_world.translation for o in meshes]
    anchor = origins[0].copy()
    if anchor.length < 10. or any((p - anchor).length > max(size, .01) for p in origins):
        anchor = Vector((center.x, center.y, low.z))
    yaw = 0.
    left = armature.data.bones.get('Bip001 L Hand')
    right = armature.data.bones.get('Bip001 R Hand')
    if left and right:
        across = armature.matrix_world.to_3x3() @ (left.head_local - right.head_local)
        if Vector((across.x, across.y)).length > .01:
            yaw = math.atan2(across.y, across.x)
    correction = Matrix.Rotation(-yaw, 4, 'Z') @ Matrix.Translation(-anchor)
    targets = [armature, *meshes]
    original = {o: o.matrix_world.copy() for o in targets}
    for obj in targets:
        old = original[obj]
        new = old.copy()
        new.translation = (0, 0, 0)
        transform = new.inverted() @ correction @ old
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        if obj.type == 'MESH':
            obj.data.transform(transform, shape_keys=True)
            obj.data.update()
        else:
            obj.data.transform(transform)
        obj.matrix_world = new
    bpy.context.view_layer.update()
    armature['gacha_cutscene_origin'] = tuple(anchor)
    print(f'[GENSHIN IMPORT] Normalized cutscene coordinates: {tuple(anchor)}, yaw={math.degrees(yaw):.2f}')
    return True
