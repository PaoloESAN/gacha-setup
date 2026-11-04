"""Presentation of WuWa head controls and internal facial helpers."""

import bpy
from math import pi
from pathlib import Path


def setup_wuwa_head_widget(rig):
    """Use PGR's canonical head ring, independently of bone display length."""
    head = rig.pose.bones.get('head')
    if head is None:
        return
    name = 'WGT-WuWa-Head-PGR'
    widget = bpy.data.objects.get(name)
    if widget is None:
        with bpy.data.libraries.load(str(Path(__file__).with_name('RootShape.blend')), link=False) as (_, loaded):
            loaded.objects = ['neck']
        widget = loaded.objects[0]
        widget.name = name
        previous = head.custom_shape
        collection = previous.users_collection[0] if previous and previous.users_collection else rig.users_collection[0]
        collection.objects.link(widget)
        widget.hide_render = True
    head.custom_shape = widget
    head.use_custom_shape_bone_size = False
    head.custom_shape_scale_xyz = (1.25, 1.25, 1.25)
    head.custom_shape_translation = (0, .225, 0)
    head.custom_shape_rotation_euler = (pi / 2, 0, 0)
    head.custom_shape_transform = None


def outline_word_widget(rig):
    control = rig.pose.bones.get('fp.outline')
    if not control or not control.custom_shape:
        return
    name = 'WGT-WuWaV3-Outline-OL'
    widget = bpy.data.objects.get(name)
    if widget is None:
        # Stroke letters remain readable as a wire widget in Pose Mode.
        strokes = [
            [(-1.1, -.7), (-1.1, .7), (-.2, .7), (-.2, -.7), (-1.1, -.7)],
            [(.2, .7), (.2, -.7), (1.1, -.7)],
        ]
        vertices, edges = [], []
        for stroke in strokes:
            start = len(vertices)
            vertices.extend((x, y, 0) for x, y in stroke)
            edges.extend((start + i, start + i + 1) for i in range(len(stroke) - 1))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, edges, [])
        widget = bpy.data.objects.new(name, mesh)
        collection = control.custom_shape.users_collection[0]
        collection.objects.link(widget)
        widget.hide_render = True
    control.custom_shape = widget
    control.use_custom_shape_bone_size = False
    unit = rig.get('ww_face_control_unit', 1.)
    control.custom_shape_scale_xyz = (.01 * unit,) * 3


def arrange_wuwa_visual_controls(rig):
    outline_word_widget(rig)
    helpers = [rig.data.bones.get(name) for name in ('FacePanelRoot', 'FacePanel')]
    helpers = [bone for bone in helpers if bone]
    if helpers:
        others = rig.data.collections.get('Others') or rig.data.collections.new('Others')
        others.is_visible = False
        name = 'WGT-WuWaV3-Internal-Hidden'
        invisible = bpy.data.objects.get(name)
        if invisible is None:
            invisible = bpy.data.objects.new(name, bpy.data.meshes.new(name))
            head_widget = rig.pose.bones.get('EyeTracker')
            if head_widget and head_widget.custom_shape:
                head_widget.custom_shape.users_collection[0].objects.link(invisible)
            invisible.hide_render = True
        for bone in helpers:
            for collection in list(bone.collections):
                collection.unassign(bone)
            others.assign(bone)
            bone.hide = True
            bone.hide_select = True
            # Also suppress stick/envelope fallback if another visibility
            # operation unhides these internal transform bones later.
            rig.pose.bones[bone.name].custom_shape = invisible
