"""Shared arrow poles and joint-following visualizers for every game."""
import bpy
from mathutils import Vector


def _widget_collection(rig):
    """Reuse this character's widget collection, including pre-isolation rigs."""
    from setup_wizard.character_rig_setup.wgts_isolation import (
        get_char_collection, get_or_create_char_wgts,
    )
    from setup_wizard.ui.character_settings_utils import resolve_character_name

    name = resolve_character_name(rig, rig.name.removesuffix('Rig'))
    owner = get_char_collection(rig, name)
    collections = [coll for coll in owner.children
                   if coll.name.lower().startswith('wgts') and '_poles' not in coll.name.lower()]
    canonical = next((coll for coll in collections if coll.name == f'WGTS_{name}'), None)
    if canonical:
        return canonical
    # Rigify may not have moved its shapes under the character yet.
    referenced = {}
    for bone in rig.pose.bones:
        if bone.custom_shape:
            for coll in bone.custom_shape.users_collection:
                if (coll.name.lower().startswith(('wgt', 'widget'))
                        and '_poles' not in coll.name.lower()):
                    referenced[coll] = referenced.get(coll, 0) + 1
    if referenced:
        owned = {coll: count for coll, count in referenced.items() if coll in collections}
        return max(owned or referenced, key=(owned or referenced).get)
    if len(collections) == 1 and owner != bpy.context.scene.collection:
        return collections[0]
    return get_or_create_char_wgts(owner, name)


def create_pole_arrow_widget(name, radius=.70125, length=.935, collection=None):
    """Create a 4-sided wireframe pyramid arrowhead widget matching Miyabi IK pole widget."""
    obj = bpy.data.objects.get(name)
    mesh = bpy.data.meshes.get(name)
    if not mesh:
        mesh = bpy.data.meshes.new(name)
    else:
        mesh.clear_geometry()

    verts = [
        (0.0, length, 0.0),       # 0: reference vert (matching Miyabi)
        (0.0, 0.0, -radius),      # 1: base -Z
        (radius, 0.0, 0.0),       # 2: base +X
        (0.0, 0.0, radius),       # 3: base +Z
        (-radius, 0.0, 0.0),      # 4: base -X
        (0.0, -length, 0.0),      # 5: apex tip (pointing outward away from joint)
    ]
    edges = [
        (1, 2), (2, 3), (3, 4), (1, 4),  # base diamond
        (1, 5), (2, 5), (3, 5), (4, 5),  # pyramid sides to apex
    ]
    mesh.from_pydata(verts, edges, [])
    mesh.update()

    if not obj:
        obj = bpy.data.objects.new(name, mesh)
        (collection or bpy.context.scene.collection).objects.link(obj)
        obj.hide_render = True
    else:
        obj.data = mesh
    if obj.name in bpy.context.view_layer.objects:
        try:
            obj.hide_set(True)
        except RuntimeError:
            # Reused WGTS can be excluded from the current view layer.
            pass
    return obj


def create_pole_line_widget(name, collection=None):
    """Create a 1-segment line widget from (0,0,0) to (0,1,0) for VIS stretch bones."""
    obj = bpy.data.objects.get(name)
    mesh = bpy.data.meshes.get(name)
    if not mesh:
        mesh = bpy.data.meshes.new(name)
    else:
        mesh.clear_geometry()

    verts = [
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    ]
    edges = [
        (0, 1),
    ]
    mesh.from_pydata(verts, edges, [])
    mesh.update()

    if not obj:
        obj = bpy.data.objects.new(name, mesh)
        (collection or bpy.context.scene.collection).objects.link(obj)
        obj.hide_render = True
    else:
        obj.data = mesh
    if obj.name in bpy.context.view_layer.objects:
        try:
            obj.hide_set(True)
        except RuntimeError:
            pass
    return obj


def setup_pole_targets(rig, use_arm_ik_poles=None, use_leg_ik_poles=None):
    """Apply ZZZ's arrow and stretching line to the rig's existing IK poles.

    The helper bones only visualize the joint: IK constraints and pole positions
    remain those generated for the character. Explicit disabled options win.
    """
    if rig is None or rig.type != 'ARMATURE':
        return
    props = getattr(bpy.context.scene, 'character_rigger_props', None)
    if use_arm_ik_poles is None:
        use_arm_ik_poles = getattr(props, 'use_arm_ik_poles', False)
    if use_leg_ik_poles is None:
        use_leg_ik_poles = getattr(props, 'use_leg_ik_poles', False)
    configs = []
    for limb, joint, parent, enabled in (
        ('thigh', 'shin', 'thigh', use_leg_ik_poles),
        ('upper_arm', 'forearm', 'upper_arm', use_arm_ik_poles),
    ):
        for side in ('L', 'R'):
            pole = f'{limb}_ik_target.{side}'
            joint_name = f'MCH-{joint}_ik.{side}'
            if pole in rig.data.bones and joint_name in rig.data.bones:
                configs.append((pole, 'VIS-' + pole, joint_name,
                                f'{parent}_parent.{side}', limb, enabled))
    if not configs:
        return

    context = bpy.context
    active = context.view_layer.objects.active
    mode = active.mode if active else 'OBJECT'
    selected = list(context.selected_objects)
    was_hidden = rig.hide_get()
    try:
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        for pole, vis, joint, parent, limb, enabled in configs:
            pole_bone = rig.data.edit_bones[pole]
            joint_bone = rig.data.edit_bones[joint]
            bone = rig.data.edit_bones.get(vis) or rig.data.edit_bones.new(vis)
            bone.head = pole_bone.head
            bone.tail = joint_bone.head
            if (bone.tail - bone.head).length < 1e-4:
                bone.tail = bone.head + Vector((0, .1, 0))
            bone.parent = pole_bone
            bone.use_connect = False
            bone.use_deform = False
        bpy.ops.object.mode_set(mode='OBJECT')

        collection = _widget_collection(rig)
        legacy_collection = bpy.data.collections.get('WGTS_' + rig.name + '_Poles')
        if legacy_collection and legacy_collection != collection:
            for obj in list(legacy_collection.objects):
                if obj.name not in collection.objects:
                    collection.objects.link(obj)
                legacy_collection.objects.unlink(obj)
            if not legacy_collection.children:
                bpy.data.collections.remove(legacy_collection)
        collection.hide_render = True
        widgets = {}
        for limb in ('thigh', 'upper_arm'):
            # Per-rig objects avoid borrowing widgets from another character.
            prefix = 'WGT-' + rig.name + '-' + limb
            widgets[limb] = (
                create_pole_arrow_widget(prefix + '-Pole', collection=collection),
                create_pole_line_widget(prefix + '-Line', collection),
            )
            for widget in widgets[limb]:
                if widget.name not in collection.objects:
                    collection.objects.link(widget)
                for previous in list(widget.users_collection):
                    if previous != collection:
                        previous.objects.unlink(widget)

        # Match elbow size even when the leg pole bone itself is longer.
        reference = next((rig.data.bones.get(f'upper_arm_ik_target.{side}')
                          for side in ('L', 'R')
                          if rig.data.bones.get(f'upper_arm_ik_target.{side}')), None)
        arrow_size = reference.length if reference else rig.data.bones[configs[0][0]].length
        for pole, vis, joint, parent, limb, enabled in configs:
            pb_pole, pb_vis = rig.pose.bones[pole], rig.pose.bones[vis]
            pb_parent = rig.pose.bones.get(parent)
            if pb_parent and 'pole_vector' in pb_parent:
                pb_parent['pole_vector'] = bool(enabled)
            # Put the visualizer beside its selectable pole, never in Other.
            if hasattr(rig.data, 'collections'):
                for coll in list(pb_vis.bone.collections):
                    coll.unassign(pb_vis.bone)
                for coll in pb_pole.bone.collections:
                    coll.assign(pb_vis.bone)
            else:
                pb_vis.bone.layers = pb_pole.bone.layers[:]
            if hasattr(pb_vis, 'color'):
                pb_vis.color.palette = pb_pole.color.palette
                if pb_pole.color.palette == 'CUSTOM':
                    for state in ('normal', 'select', 'active'):
                        setattr(pb_vis.color.custom, state, getattr(pb_pole.color.custom, state))
            pb_vis.bone.hide_select = True
            pb_vis.custom_shape = widgets[limb][1]
            pb_vis.use_custom_shape_bone_size = True
            pb_vis.custom_shape_scale_xyz = (1, 1, 1)
            pb_vis.custom_shape_translation = (0, 0, 0)
            pb_vis.custom_shape_rotation_euler = (0, 0, 0)
            constraint = pb_vis.constraints.get('Stretch To') or pb_vis.constraints.new('STRETCH_TO')
            constraint.name = 'Stretch To'
            constraint.target = rig
            constraint.subtarget = joint
            constraint.volume = 'NO_VOLUME'
            constraint.keep_axis = 'SWING_Y'
            # Rigify drives PoseBone.hide on Blender 5, and Bone.hide on older
            # versions. Following Bone.hide alone leaves the line visible
            # when Toggle Pole hides the pose control.
            pb_vis.bone.driver_remove('hide')
            pb_vis.bone.hide = False
            hide_owner = pb_vis if hasattr(pb_vis, 'hide') else pb_vis.bone
            hide_owner.driver_remove('hide')
            driver = hide_owner.driver_add('hide').driver
            driver.type = 'SCRIPTED'
            for variable in list(driver.variables):
                driver.variables.remove(variable)
            variable = driver.variables.new()
            variable.name = 'hidden'
            variable.type = 'SINGLE_PROP'
            pole_hide_owner = pb_pole if hasattr(pb_pole, 'hide') else pb_pole.bone
            variable.targets[0].id_type = 'OBJECT' if pole_hide_owner == pb_pole else 'ARMATURE'
            variable.targets[0].id = rig if pole_hide_owner == pb_pole else rig.data
            variable.targets[0].data_path = pole_hide_owner.path_from_id('hide')
            driver.expression = 'hidden'
            if hasattr(pb_pole, 'hide'):
                variable = driver.variables.new()
                variable.name = 'bone_hidden'
                variable.type = 'SINGLE_PROP'
                variable.targets[0].id_type = 'ARMATURE'
                variable.targets[0].id = rig.data
                variable.targets[0].data_path = pb_pole.bone.path_from_id('hide')
                driver.expression += ' or bone_hidden'
            if pb_parent and 'pole_vector' in pb_parent:
                variable = driver.variables.new()
                variable.name = 'pole'
                variable.type = 'SINGLE_PROP'
                variable.targets[0].id = rig
                variable.targets[0].data_path = pb_parent.path_from_id() + '["pole_vector"]'
                driver.expression += ' or not pole'
            pb_pole.custom_shape = widgets[limb][0]
            pb_pole.custom_shape_transform = pb_vis
            pb_pole.use_custom_shape_bone_size = False
            pb_pole.custom_shape_scale_xyz = (
                -arrow_size if pole.endswith('.R') else arrow_size, arrow_size, arrow_size)
            pb_pole.custom_shape_translation = (0, 0, 0)
            pb_pole.custom_shape_rotation_euler = (0, 0, 0)
        rig.update_tag()
        context.view_layer.update()
    finally:
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        rig.hide_set(was_hidden)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            if obj.name in context.view_layer.objects:
                obj.select_set(True)
        context.view_layer.objects.active = active
        if active and mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
