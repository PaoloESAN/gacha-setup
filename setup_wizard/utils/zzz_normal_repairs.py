"""Repairs for known authored normal data defects in ZZZ assets."""
import re

import bpy


def repair_lindverne_body_normals(objects):
    """Remove Lindverne Body 1's faulty split normals, retaining smooth flags.

    These normals create triangular lighting discontinuities when the shoulder
    deforms. Automatically calculated normals remove the discontinuities with
    the same geometry, skin weights, UVs and normal-map textures. Do not apply
    this to other characters, the face, hair, or the separate Body 2 mesh.
    """
    targets = [obj for obj in objects if obj.type == 'MESH'
               and re.fullmatch(r'lindverne_body_1(?:\.\d{3})?', obj.name, re.I)
               and obj.data.has_custom_normals]
    if not targets:
        return 0
    active = bpy.context.view_layer.objects.active
    mode = active.mode if active else 'OBJECT'
    selected = list(bpy.context.selected_objects)
    try:
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in targets:
            if obj.data.users > 1:
                obj.data = obj.data.copy()
            hidden = obj.hide_get()
            obj.hide_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            obj.data['zzz_lindverne_normals_v1'] = True
            obj.data.update()
            obj.select_set(False)
            obj.hide_set(hidden)
    finally:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
    return len(targets)
