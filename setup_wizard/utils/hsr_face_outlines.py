"""Bronya's camera-dependent face outline mask for StellarToon HSR.

The reference keeps depth offset at zero and suppresses the blue/green
vertex-color regions at steep vertical/profile angles. Body/hair outlines
must continue using the original node group.
"""
import bpy
from mathutils import Vector

from .modifier_utils import get_modifier_property, set_modifier_property

GROUP_NAME = 'StellarToon - Outlines FACE'
VERSION = 1


def configure_face_outlines(context, mesh, modifier):
    if not any(m and 'face' in m.name.lower() and 'mask' not in m.name.lower()
               and 'outline' not in m.name.lower() for m in mesh.data.materials):
        return False
    base = modifier.node_group
    if not base or not (base.name.startswith('StellarToon - Outlines GN') or base.get('gacha_hsr_face_outlines')):
        return False
    # The complete node graph is authored in StellarToonV1.1.blend.
    group = next((g for g in bpy.data.node_groups
                  if g.name.startswith(GROUP_NAME) and g.get('gacha_hsr_face_outlines') == VERSION), None)
    if group is None:
        raise RuntimeError('Reimport HSR outlines: the StellarToon face template is missing.')
    modifier.node_group = group
    set_modifier_property(modifier, group['dynamic_socket'], 1.)
    set_modifier_property(modifier, 'Input_8', 0.)
    light_vectors = next((m for m in mesh.modifiers if m.type == 'NODES' and m.node_group
                          and m.node_group.name.startswith('Light Vectors')), None)
    head = get_modifier_property(light_vectors, 'Input_4') if light_vectors else None
    set_modifier_property(modifier, group['head_socket'], head)
    camera = context.scene.camera or next((o for o in context.scene.objects if o.type == 'CAMERA'), None)
    if camera is None:
        camera = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
        context.scene.collection.objects.link(camera)
        center = mesh.matrix_world @ (sum((Vector(c) for c in mesh.bound_box), Vector()) / 8)
        camera.location = center + Vector((0, -1.5, 0))
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    if context.scene.camera is None:
        context.scene.camera = camera
    set_modifier_property(modifier, 'Input_4', camera)
    return True
