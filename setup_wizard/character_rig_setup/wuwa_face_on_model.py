"""On-face WuWa controls adapted from the supplied WuWaRigify V3.0a script.

Only facial controls are rebuilt. Body Rigify controls, pupil calibration and
the shader's independent eye-highlight controls remain on the character rig.
"""
import math
import re

import bpy
from mathutils import Vector


FANS = ('Insipid', 'Focus', 'Sad', 'Anger', 'Smile')
BROWS = ('B_Anger', 'B_Happy', 'B_Cheerful', 'B_Sad', 'B_Flat', 'B_Inside_Add')
MOUTHS = ('Aa', 'M_OpenSmall', 'M_Laugh', 'M_Scared', 'M_ScaredTooth',
          'M_Anger', 'M_Trapezoid', 'M_Nutcracker', 'M_O', 'M_A')
HELPERS = {'FacePanelRoot', 'FacePanel', 'MouthPanel'}
HIDDEN_HELPERS = {'FacePanelRoot', 'FacePanel'}
CONTROLS = {'Eyebrows', 'Mouth', 'Mouth.L', 'Mouth.R', 'EyeScale', 'fp.outline',
            *BROWS, *MOUTHS, *(f'{n}.{s}' for n in FANS for s in ('L', 'R'))}
GAZE = {'EyeTracker', 'Eye.L', 'Eye.R'}
HIGHLIGHTS = {'CTRL-Eye_Highlight', 'CTRL-Highlight_Top', 'CTRL-Highlight_Bottom'}


def build_wuwa_face_on_model(context, rig, primary, head_name):
    from . import wuwa_face_panel as shared
    meshes = shared._collect_character_face_meshes(primary, rig)
    meshes = [m for m in meshes if any(mod.type == 'ARMATURE' and mod.object == rig for mod in m.modifiers)]
    if not meshes:
        return False
    # Prefer the character's actual facial expressions over a hair/eyebrow mesh.
    face = max(meshes, key=lambda m: sum(k in m.data.shape_keys.key_blocks
               for k in ('E_Close', 'M_OpenSmall', 'Pupil_Up', 'B_Anger', 'Aa')))
    if context.object and context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for mesh in meshes:
        shared.split_shape_keys(mesh)

    def centroid(keys, side=None):
        for mesh in [face] + [m for m in meshes if m != face]:
            point = shared.feature_centroid(mesh, keys, side=side)
            if point is not None:
                return point
        return None

    fallback = rig.matrix_world @ rig.data.bones[head_name].head_local
    eyes = {}
    for side, sign in [('L', 1), ('R', -1)]:
        point = centroid([f'E_Close.{side}', f'E_Smile_{side}', f'Pupil_Up.{side}'], side)
        if point is None:
            point = fallback + Vector((sign * .03, -.06, .03))
        eyes[side] = point
    eye_center = (eyes['L'] + eyes['R']) * .5
    unit = max(.5, min(2., (eyes['L'] - eyes['R']).length / .06))
    mouth = centroid(['M_OpenSmall', 'Aa', 'A', 'M_A'])
    if mouth is None:
        mouth = eye_center - Vector((0, 0, .055 * unit))
    brow = centroid(list(BROWS))
    if brow is None:
        brow = eye_center + Vector((0, 0, .04 * unit))
    depth = min(eye_center.y, mouth.y, brow.y) - .02 * unit
    # Keep the source's brow-row clearance above the gaze capsule. A brow
    # morph centroid is too close to the eyelids and overlaps that capsule.
    brow = eye_center + Vector((0, 0, .06 * unit))

    def front(point):
        point = point.copy()
        point.y = depth
        return point

    eye_center, mouth, brow = map(front, (eye_center, mouth, brow))
    eyes = {side: front(point) for side, point in eyes.items()}
    inv = rig.matrix_world.inverted()
    inv3 = inv.to_3x3()
    legacy = set(shared.WUWA_FACE_PANEL_BONE_NAMES) - GAZE - HIGHLIGHTS
    remove = {b.name for b in rig.data.bones if b.name in legacy
              or b.name.startswith(('fp.key.', 'fp.label.'))}
    # Remove obsolete panel drivers before deleting their target bones.
    for mesh in meshes:
        keys = mesh.data.shape_keys
        if not keys.animation_data:
            continue
        for curve in list(keys.animation_data.drivers):
            obsolete = False
            for var in curve.driver.variables:
                for target in var.targets:
                    if target.id != rig:
                        continue
                    match = re.search(r'pose\.bones\["([^"]+)"\]', target.data_path)
                    name = target.bone_target if var.type == 'TRANSFORMS' else match[1] if match else ''
                    obsolete |= name in remove or name in CONTROLS
            if obsolete:
                keys.driver_remove(curve.data_path)
    context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    for name in remove - {'fp.outline'}:
        if name in eb:
            eb.remove(eb[name])
    created = []

    def bone(name, point, parent, direction=Vector((0, 0, 1))):
        b = eb.get(name) or eb.new(name)
        b.head = inv @ point
        length = .03 if name in GAZE else .01 if name in HELPERS | {'EyeScale', 'Eyebrows'} else .02
        b.tail = b.head + inv3 @ (direction.normalized() * length * unit)
        b.align_roll(inv3 @ Vector((0, -1, 0)))
        b.use_deform = False
        b.use_connect = False
        b.parent = eb.get(parent)
        created.append(name)
        return b

    bone('FacePanelRoot', eye_center, head_name)
    bone('FacePanel', eye_center, 'FacePanelRoot')
    bone('EyeTracker', eye_center, 'FacePanelRoot')
    for side in ('L', 'R'):
        bone(f'Eye.{side}', eyes[side], 'EyeTracker')
    bone('EyeScale', eye_center - Vector((0, 0, .01 * unit)), 'FacePanel')
    bone('Eyebrows', brow, 'FacePanel')
    for i, name in enumerate(BROWS):
        bone(name, brow + Vector(((i-2.5) * .015 * unit, 0, .01 * unit)), 'Eyebrows')
    bone('MouthPanel', mouth, 'FacePanel')
    bone('Mouth', mouth, 'MouthPanel')
    for side, sign in [('L', 1), ('R', -1)]:
        # Smile morphs move much of the mouth; their centroid is not a lip
        # corner. Keep the controls just outside the mouth capsule.
        corner = mouth + Vector((sign * .025 * unit, 0, 0))
        bone(f'Mouth.{side}', front(corner), 'MouthPanel')
        for i, name in enumerate(FANS):
            angle = math.radians(-60 + 30 * i)
            direction = Vector((sign * math.cos(angle), 0, math.sin(angle)))
            bone(f'{name}.{side}', eyes[side] + direction * .035 * unit, 'FacePanel', direction)
    for i, name in enumerate(MOUTHS):
        bone(name, mouth + Vector(((i-4.5) * .01 * unit, 0, -.035 * unit)), 'MouthPanel', Vector((0, 0, -1)))
    bone('fp.outline', brow + Vector((.09 * unit, 0, .018 * unit)), 'FacePanel')
    bpy.ops.object.mode_set(mode='OBJECT')
    coll = rig.data.collections.get('Face') or rig.data.collections.new('Face')
    coll.is_visible = True
    widgets = shared.get_widget_collection()

    def widget(kind):
        # Separate names prevent reusing the earlier approximate shapes or
        # a Rigify/body widget with a coincidentally matching name.
        name = f'WGT-WuWaV3-Reference-{kind}'
        existing = bpy.data.objects.get(name)
        if existing:
            return existing
        if kind == 'triangle':
            verts, edges = [(0, 1, 0), (-1, -1, 0), (1, -1, 0)], [(0, 1), (1, 2), (2, 0)]
        elif kind == 'diamond':
            verts, edges = [(0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)], [(0, 1), (1, 2), (2, 3), (3, 0)]
        elif kind == 'square':
            verts, edges = [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [(0, 1), (1, 2), (2, 3), (3, 0)]
        elif kind == 'cross':
            verts, edges = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0)], [(0, 1), (2, 3)]
        elif kind == 'capsule':
            # Exact double-capsule mesh from WuWaRigifyV3.0a.py.
            verts, edges = [], []
            for radius in (.14, .17):
                start = len(verts)
                for center, angle_start in [(-.3, math.pi / 2), (.3, -math.pi / 2)]:
                    for i in range(17):
                        angle = angle_start + math.pi * i / 16
                        verts.append((center + math.cos(angle) * radius, math.sin(angle) * radius, 0))
                edges.extend((start+i, start+(i+1) % 34) for i in range(34))
        else:
            verts = [(.1*math.cos(i*math.tau/32), .1*math.sin(i*math.tau/32), 0) for i in range(32)]
            edges = [(i, (i+1) % 32) for i in range(32)]
        data = bpy.data.meshes.new(name)
        data.from_pydata(verts, edges, [])
        obj = bpy.data.objects.new(name, data)
        widgets.objects.link(obj)
        obj.hide_render = True
        return obj

    for name in created:
        pb = rig.pose.bones[name]
        for old in list(pb.bone.collections):
            old.unassign(pb.bone)
        coll.assign(pb.bone)
        pb.bone.hide = name in HIDDEN_HELPERS
        pb.bone.hide_select = name in HELPERS
        pb.location = (0, 0, 0)
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
        for con in list(pb.constraints):
            if con.type in {'LIMIT_LOCATION', 'LIMIT_ROTATION', 'LIMIT_SCALE'} or con.name == 'FollowEyeTracker':
                pb.constraints.remove(con)
        pb.lock_location = (True, False, True)
        pb.lock_rotation = (True, True, True)
        pb.lock_scale = (True, True, True)
        if name in HELPERS:
            pb.lock_location = (True, True, True)
            if name in HIDDEN_HELPERS:
                pb.custom_shape = None
                continue
            kind, size, color = 'cross', .04 * unit, 'THEME01'
        elif name in GAZE:
            kind, size, color = 'capsule' if name == 'EyeTracker' else 'circle', .12 * unit, 'THEME01' if name == 'EyeTracker' else 'THEME09'
            pb.lock_location = (False, False, True)
            pb.lock_scale = (False, False, True)
        elif name == 'Mouth':
            kind, size, color = 'capsule', .04 * unit, 'THEME01'
            pb.lock_location = (False, False, True)
            pb.lock_scale = (False, False, False)
        elif name.startswith('Mouth.'):
            kind, size, color = 'diamond', .003 * unit, 'THEME03'
            pb.lock_location = (False, False, True)
        elif name in {'Eyebrows', 'EyeScale'}:
            kind, size, color = 'square', (.045 if name == 'Eyebrows' else .01) * unit, 'THEME01' if name == 'Eyebrows' else 'THEME09'
            if name == 'EyeScale':
                pb.lock_scale = (False, True, True)
            else:
                pb.lock_rotation = (True, True, False)
        elif name == 'fp.outline':
            kind, size, color = 'square', .004 * unit, 'THEME01'
            pb.lock_location = (False, True, True)
        else:
            kind, size, color = 'triangle', .004 * unit, 'THEME03' if name in MOUTHS else 'THEME01' if name in BROWS else 'THEME09'
        pb.custom_shape = widget(kind)
        pb.use_custom_shape_bone_size = False
        pb.custom_shape_scale_xyz = (size, size, size)
        pb.custom_shape_rotation_euler = (0, 0, 0)
        pb.custom_shape_translation = (0, 0, 0)
        pb.custom_shape_transform = None
        pb.color.palette = color
        # Bake the source's bone-length-based dimensions into meter scales.
        # This keeps the same outlines on Blender 4.x and 5.x, independently
        # of how each character's bone lengths were normalized.
        if name == 'Eyebrows':
            pb.custom_shape_scale_xyz = (.045 * unit, .002 * unit, .01 * unit)
        elif name == 'EyeScale':
            pb.custom_shape_scale_xyz = (.01 * unit, .001 * unit, .01 * unit)
        elif name == 'MouthPanel':
            pb.custom_shape_scale_xyz = (.023 * unit, .014375 * unit, .01 * unit)
        limit = pb.constraints.new('LIMIT_LOCATION')
        limit.owner_space = 'LOCAL'
        limit.use_transform_limit = True
        for axis in 'xyz':
            setattr(limit, 'use_min_'+axis, True)
            setattr(limit, 'use_max_'+axis, True)
        limit.min_x = limit.max_x = limit.min_y = limit.max_y = limit.min_z = limit.max_z = 0
        if name in GAZE:
            limit.min_x = limit.min_y = -.1 * unit
            limit.max_x = limit.max_y = .1 * unit
        elif name == 'fp.outline':
            limit.max_x = .02 * unit
        elif name == 'Mouth':
            limit.min_x = limit.min_y = -.02 * unit
            limit.max_x = limit.max_y = .02 * unit
        elif name.startswith('Mouth.') or name == 'Eyebrows':
            limit.min_x = -.01 * unit if name.startswith('Mouth.') else 0
            limit.max_x = .01 * unit if name.startswith('Mouth.') else 0
            limit.min_y, limit.max_y = -.01 * unit, .01 * unit
        else:
            limit.max_y = (.01 if name == 'EyeScale' else .02) * unit
        if not all(pb.lock_scale):
            scale = pb.constraints.new('LIMIT_SCALE')
            scale.owner_space = 'LOCAL'
            scale.use_transform_limit = True
            axis = 'x' if name == 'EyeScale' else 'y'
            if name == 'Mouth':
                for axis in 'xyz':
                    setattr(scale, 'use_min_'+axis, True)
                    setattr(scale, 'use_max_'+axis, True)
                    setattr(scale, 'min_'+axis, 1.)
                    setattr(scale, 'max_'+axis, 1.5)
            else:
                setattr(scale, 'use_min_'+axis, True)
                setattr(scale, 'use_max_'+axis, True)
                setattr(scale, 'min_'+axis, .5)
                setattr(scale, 'max_'+axis, 1.5 if name == 'EyeTracker' else 1.)
                if name in GAZE:
                    scale.use_min_x = scale.use_max_x = True
                    scale.min_x, scale.max_x = .5, 1.5
        if name == 'Eyebrows':
            rotation = pb.constraints.new('LIMIT_ROTATION')
            rotation.owner_space = 'LOCAL'
            rotation.use_limit_z = True
            rotation.min_z, rotation.max_z = -math.radians(10), math.radians(10)
            rotation.use_transform_limit = True

    # The source keeps the expression controls attached to the eye tracker.
    follow = rig.pose.bones['FacePanel'].constraints.new('COPY_LOCATION')
    follow.name = 'FollowEyeTracker'
    follow.target = rig
    follow.subtarget = 'EyeTracker'

    # Match the reference driver's response, using local channels so moving
    # the head and parent controls never adds an unintended expression.
    linked = 0
    for mesh in meshes:
        keys = mesh.data.shape_keys
        def drive(key, expression, channels):
            nonlocal linked
            if key not in keys.key_blocks:
                return
            sk = keys.key_blocks[key]
            sk.driver_remove('value')
            driver = sk.driver_add('value').driver
            driver.type = 'SCRIPTED'
            for variable, bone_name, channel in channels:
                var = driver.variables.new()
                var.name = variable
                var.type = 'SINGLE_PROP'
                var.targets[0].id = rig
                var.targets[0].data_path = f'pose.bones["{bone_name}"].{channel}'
            driver.expression = expression
            linked += 1

        def linear(key, bone, channel='location.y', distance=.02, sign=1):
            drive(key, f'max(0,min(1,{sign}*v/{distance*unit!r}))', [('v', bone, channel)])

        for name in (*BROWS, *MOUTHS):
            linear(name, name)
        for side in ('L', 'R'):
            for name in FANS:
                key = f'E_Smile_{side}' if name == 'Smile' else f'E_{name}.{side}'
                linear(key, f'{name}.{side}')
            for key, sign in [(f'M_Smile_{side}', 1), (f'M_Ennui_{side}', -1)]:
                linear(key, f'Mouth.{side}', sign=sign)
            drive(f'E_Close.{side}', 'max(0,min(1,(1-v)*2))', [('v', f'Eye.{side}', 'scale.y')])
        drive('E_Close', 'max(0,min(1,(1-v)*2))', [('v', 'EyeTracker', 'scale.y')])
        drive('E_Stare', 'max(0,min(1,(v-1)*2))', [('v', 'EyeTracker', 'scale.y')])
        linear('E_Blephar', 'EyeScale')
        # Rebind gaze too: an existing scene may still target the old panel.
        # Use either split morphs or their global source, never both together.
        def reset_global(key):
            if key in keys.key_blocks:
                keys.key_blocks[key].driver_remove('value')
                keys.key_blocks[key].value = 0

        for key, axis, sign in [('Pupil_L', 'x', 1), ('Pupil_R', 'x', -1),
                                ('Pupil_Up', 'y', 1), ('Pupil_Down', 'y', -1)]:
            if all(f'{key}.{s}' in keys.key_blocks for s in ('L', 'R')):
                reset_global(key)
                for side in ('L', 'R'):
                    drive(f'{key}.{side}', f'max(0,min(1,{sign}*(m+i)*10))',
                          [('m', 'EyeTracker', f'location.{axis}'), ('i', f'Eye.{side}', f'location.{axis}')])
            else:
                linear(key, 'EyeTracker', f'location.{axis}', .1 / unit, sign)
        if all(f'Pupil_Scale.{s}' in keys.key_blocks for s in ('L', 'R')):
            reset_global('Pupil_Scale')
            for side in ('L', 'R'):
                keys.key_blocks[f'Pupil_Scale.{side}'].slider_min = -1
                drive(f'Pupil_Scale.{side}', 'max(-1,min(1,(1-m*i)*2+max(0,min(1,(1-s)*2))))',
                      [('m', 'EyeTracker', 'scale.x'), ('i', f'Eye.{side}', 'scale.x'), ('s', 'EyeScale', 'scale.x')])
        else:
            drive('Pupil_Scale', 'max(-1,min(1,(1-m*(l+r)/2)*2+max(0,min(1,(1-s)*2))))',
                  [('m', 'EyeTracker', 'scale.x'), ('l', 'Eye.L', 'scale.x'),
                   ('r', 'Eye.R', 'scale.x'), ('s', 'EyeScale', 'scale.x')])
        linear('B_Up_Add', 'Eyebrows', distance=.01)
        linear('B_Down_Add', 'Eyebrows', distance=.01, sign=-1)
        for side, sign in [('L', -1), ('R', 1)]:
            drive(f'B_AH_{side}', f'max(0,min(1,{sign}*v/{math.radians(10)!r}))', [('v', 'Eyebrows', 'rotation_euler.z')])
        for key, bone, sign in [('P_M_Scale_Add.L', 'Mouth.L', -1), ('P_M_L_Add', 'Mouth.L', 1),
                                ('P_M_R_Add', 'Mouth.R', -1), ('P_M_Scale_Add.R', 'Mouth.R', 1)]:
            linear(key, bone, 'location.x', .01, sign)
        drive('O', 'max(0,min(1,((sx+sy+sz)/3-1)*2))', [(f's{a}', 'Mouth', f'scale.{a}') for a in 'xyz'])
        for key, axis, sign in [('E', 'x', -1), ('I', 'x', 1), ('A', 'y', 1), ('U', 'y', -1)]:
            channels = [('v', 'Mouth', f'location.{axis}'), ('y', 'Mouth', 'location.y')]
            expression = f'max(0,min(1,{sign}*v/{.02*unit!r}))'
            if axis == 'x':
                expression += f'*(1-min(abs(y)/{.02*unit!r},1))'
            channels += [(f's{a}', 'Mouth', f'scale.{a}') for a in 'xyz']
            expression += '*(1-.6*max(0,min(1,((sx+sy+sz)/3-1)*2)))'
            drive(key, expression, channels)
        mesh['ww_face_panel_armature'] = rig.name
        mesh['ww_face_panel_assigned'] = True
    if not HIGHLIGHTS.intersection(rig.pose.bones.keys()):
        shared.merge_eye_highlight_into_armature(context, rig, head_name)
    shared.setup_outline_drivers_from_face_panel(rig, context)
    shared.finalize_widget_collection(widgets)
    rig['ww_face_panel_armature'] = rig.name
    rig['ww_face_rig_version'] = 'WuWaRigify V3 on-face'
    rig['ww_face_widget_version'] = 2
    rig['ww_face_control_unit'] = unit
    from .wuwa_visual_controls import arrange_wuwa_visual_controls
    arrange_wuwa_visual_controls(rig)
    rig.show_in_front = True
    context.view_layer.objects.active = rig
    context.view_layer.update()
    print(f'[WUWA V3 FACE] {len(created)} on-face controls, {linked} expression drivers; highlights preserved.')
    return True
