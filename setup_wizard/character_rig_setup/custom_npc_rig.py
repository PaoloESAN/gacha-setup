# Custom Rigify rigging for non-Bip001 NPC armatures (e.g. Kukulkan Bone_* skeletons).

import bpy
from mathutils import Vector

from setup_wizard.geometry_nodes_setup.lighting_panel_names import LightingPanelNames
from setup_wizard.character_rig_setup.pole_targets import setup_pole_targets
from setup_wizard.character_rig_setup.rig_ui_utils import (
    modify_and_run_rig_ui_script,
    resolve_rig_character_name,
    setup_standard_bone_collections,
)
from setup_wizard.character_rig_setup.wgts_isolation import (
    get_or_create_char_wgts,
    isolate_wgts_for_character,
)


def _snapshot_source_bones(armature):
    """Return rest-pose descriptors and pose rotation modes for all bones in armature."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    snap = {}
    order = []
    for eb in armature.data.edit_bones:
        order.append(eb.name)
        snap[eb.name] = {
            'head': eb.head.copy(),
            'tail': eb.tail.copy(),
            'roll': eb.roll,
            'parent': eb.parent.name if eb.parent else None,
            'use_connect': eb.use_connect,
            'inherit_scale': eb.inherit_scale,
        }
    bpy.ops.object.mode_set(mode='OBJECT')
    for bname, info in snap.items():
        pb = armature.pose.bones.get(bname)
        info['rotation_mode'] = pb.rotation_mode if pb else 'QUATERNION'
    return order, snap


def _align_finger_chain_rolls(meta_data, chain_names):
    """Align finger chain rolls to the bend plane so curling bends inward."""
    bones = [meta_data.edit_bones.get(n) for n in chain_names if meta_data.edit_bones.get(n)]
    if len(bones) < 2:
        return
    d0 = (bones[0].tail - bones[0].head).normalized()
    d1 = (bones[1].tail - bones[1].head).normalized()
    plane_n = d0.cross(d1)
    if plane_n.length < 1e-4:
        return
    plane_n.normalize()
    for b in bones:
        dir_b = (b.tail - b.head).normalized()
        z_target = plane_n.cross(dir_b)
        if z_target.length > 1e-4:
            b.align_roll(z_target)


def _build_kukulkan_metarig(snap):
    """Create a Rigify metarig aligned to the Bone_* hierarchy and return (meta_obj, bone_map)."""
    bpy.ops.object.armature_basic_human_metarig_add()
    meta_obj = bpy.context.active_object
    meta_obj.name = 'metarig'
    meta_data = meta_obj.data

    bpy.ops.object.mode_set(mode='EDIT')
    for b in list(meta_data.edit_bones):
        meta_data.edit_bones.remove(b)

    def add_bone(name, head, tail, parent=None, connect=False, coll='Spine'):
        b = meta_data.edit_bones.new(name)
        b.head = head
        b.tail = tail
        if parent and parent in meta_data.edit_bones:
            b.parent = meta_data.edit_bones[parent]
            b.use_connect = connect
        c = meta_data.collections.get(coll) or meta_data.collections[0]
        c.assign(b)
        return b

    bone_map = {}

    # Spine: Bone_Pelvis01_M -> Bone_Spine01_M -> Bone_Spine02_M
    pelvis = snap.get('Bone_Pelvis01_M')
    spine1 = snap.get('Bone_Spine01_M')
    spine2 = snap.get('Bone_Spine02_M')
    neck = snap.get('Bone_Neck01_M')
    head = snap.get('Bone_Head01_M')

    top_spine = None
    if pelvis and spine1 and spine2:
        top_tail = neck['head'] if neck else spine2['tail']
        add_bone('spine', pelvis['head'], spine1['head'], coll='Spine')
        add_bone('spine.001', spine1['head'], spine2['head'], 'spine', True, coll='Spine')
        add_bone('spine.002', spine2['head'], top_tail, 'spine.001', True, coll='Spine')
        top_spine = 'spine.002'
        bone_map['Bone_Pelvis01_M'] = 'DEF-spine'
        bone_map['Bone_Spine01_M'] = 'DEF-spine.001'
        bone_map['Bone_Spine02_M'] = 'DEF-spine.002'

    # Neck & Head (disconnected at edit_bones so super_head owns spine.004/006)
    if neck and head:
        add_bone('spine.004', neck['head'], head['head'], top_spine, False, coll='Spine')
        add_bone('spine.006', head['head'], head['head'] + Vector((0, 0, 0.28)), 'spine.004', True, coll='Spine')
        bone_map['Bone_Neck01_M'] = 'DEF-spine.004'
        bone_map['Bone_Head01_M'] = 'DEF-spine.006'
    elif head:
        add_bone('spine.006', head['head'], head['head'] + Vector((0, 0, 0.28)), top_spine, False, coll='Spine')
        bone_map['Bone_Head01_M'] = 'DEF-spine.006'

    # Arms & Fingers
    for side in ('L', 'R'):
        clav = snap.get(f'Bone_Clavicle01_{side}')
        uarm = snap.get(f'Bone_UpperArm01_{side}')
        larm = snap.get(f'Bone_LowerArm01_{side}')
        hand = snap.get(f'Bone_Hand01_{side}')
        coll_arm = f'Arm.{side} (IK)'

        sh_name = None
        if clav:
            sh_name = f'shoulder.{side}'
            add_bone(sh_name, clav['head'], clav['tail'], top_spine, False, coll=coll_arm)
            bone_map[f'Bone_Clavicle01_{side}'] = f'DEF-shoulder.{side}'

        if uarm and larm and hand:
            add_bone(f'upper_arm.{side}', uarm['head'], larm['head'], sh_name or top_spine, False, coll=coll_arm)
            add_bone(f'forearm.{side}', larm['head'], hand['head'], f'upper_arm.{side}', True, coll=coll_arm)
            add_bone(f'hand.{side}', hand['head'], hand['tail'], f'forearm.{side}', True, coll=coll_arm)
            bone_map[f'Bone_UpperArm01_{side}'] = f'DEF-upper_arm.{side}'
            bone_map[f'Bone_LowerArm01_{side}'] = f'DEF-forearm.{side}'
            bone_map[f'Bone_Hand01_{side}'] = f'DEF-hand.{side}'

            finger_specs = [
                ('Thumb', 'thumb'),
                ('Index', 'f_index'),
                ('Mid', 'f_middle'),
                ('Ring', 'f_ring'),
                ('Pinky', 'f_pinky'),
            ]
            for src_prefix, rig_prefix in finger_specs:
                b1 = snap.get(f'Bone_{src_prefix}01_{side}')
                b2 = snap.get(f'Bone_{src_prefix}02_{side}')
                b3 = snap.get(f'Bone_{src_prefix}03_{side}')
                if not (b1 and b2 and b3):
                    continue
                n1, n2, n3 = f'{rig_prefix}.01.{side}', f'{rig_prefix}.02.{side}', f'{rig_prefix}.03.{side}'
                add_bone(n1, b1['head'], b2['head'], f'hand.{side}', False, coll='Fingers')
                add_bone(n2, b2['head'], b3['head'], n1, True, coll='Fingers')
                add_bone(n3, b3['head'], b3['tail'], n2, True, coll='Fingers')
                _align_finger_chain_rolls(meta_data, [n1, n2, n3])
                bone_map[f'Bone_{src_prefix}01_{side}'] = f'DEF-{n1}'
                bone_map[f'Bone_{src_prefix}02_{side}'] = f'DEF-{n2}'
                bone_map[f'Bone_{src_prefix}03_{side}'] = f'DEF-{n3}'

    # Lower Tail chain: Bone_TailLower01_M .. 05_M
    tail_src = [f'Bone_TailLower0{i}_M' for i in range(1, 6) if f'Bone_TailLower0{i}_M' in snap]
    if len(tail_src) >= 2:
        tail_parent = 'spine' if 'spine' in meta_data.edit_bones else None
        for idx, bname in enumerate(tail_src):
            cur = snap[bname]
            nxt_head = snap[tail_src[idx + 1]]['head'] if idx + 1 < len(tail_src) else cur['tail']
            m_name = 'tail' if idx == 0 else f'tail.{idx:03d}'
            p_name = tail_parent if idx == 0 else ('tail' if idx == 1 else f'tail.{idx - 1:03d}')
            add_bone(m_name, cur['head'], nxt_head, p_name, idx > 0, coll='Spine')
            bone_map[bname] = f'DEF-{m_name}'

    # Configure Rigify types in Pose Mode
    bpy.ops.object.mode_set(mode='POSE')
    pb = meta_obj.pose.bones
    if 'spine' in pb:
        pb['spine'].rigify_type = 'spines.basic_spine'
    if 'spine.004' in pb:
        pb['spine.004'].rigify_type = 'spines.super_head'
        pb['spine.004'].rigify_parameters.connect_chain = bool(top_spine)
    if 'tail' in pb:
        pb['tail'].rigify_type = 'spines.basic_tail'
    for side in ('L', 'R'):
        if f'shoulder.{side}' in pb:
            pb[f'shoulder.{side}'].rigify_type = 'basic.super_copy'
            pb[f'shoulder.{side}'].rigify_parameters.super_copy_widget_type = 'shoulder'
        if f'upper_arm.{side}' in pb:
            pb[f'upper_arm.{side}'].rigify_type = 'limbs.arm'
            pb[f'upper_arm.{side}'].rigify_parameters.rotation_axis = 'automatic'
        for rig_prefix in ('thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky'):
            fn = f'{rig_prefix}.01.{side}'
            if fn in pb:
                pb[fn].rigify_type = 'limbs.super_finger'
                pb[fn].rigify_parameters.make_extra_ik_control = True
                pb[fn].rigify_parameters.primary_rotation_axis = 'X'

    bpy.ops.object.mode_set(mode='OBJECT')
    return meta_obj, bone_map


def _move_object_to_collection(obj, target_coll):
    """Link obj into target_coll and unlink from all other collections."""
    if not obj or not target_coll:
        return
    for coll in list(obj.users_collection):
        if coll != target_coll:
            try:
                coll.objects.unlink(obj)
            except Exception:
                pass
    if obj.name not in target_coll.objects:
        target_coll.objects.link(obj)


def _setup_lighting_panel_and_empties(rig_obj, char_name, char_coll, wgt_coll):
    """Integrate Lighting Panel armature, color wheels, and Light Vectors empties into rig_obj."""
    lp_obj = bpy.data.objects.get(LightingPanelNames.Objects.LIGHTING_PANEL)
    if lp_obj:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        with bpy.context.temp_override(
            active_object=rig_obj,
            selected_editable_objects=[rig_obj, lp_obj],
        ):
            bpy.ops.object.join()

        bpy.context.view_layer.objects.active = rig_obj
        bpy.ops.object.mode_set(mode='EDIT')
        lp_bone = rig_obj.data.edit_bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
        parent_bone = rig_obj.data.edit_bones.get('head') or rig_obj.data.edit_bones.get('torso')
        if lp_bone and parent_bone:
            lp_bone.parent = parent_bone
        bpy.ops.object.mode_set(mode='OBJECT')

        for coll_name in (
            LightingPanelNames.Collections.WIDGET_COLLECTION,
            LightingPanelNames.Collections.PICKER,
        ):
            c = bpy.data.collections.get(coll_name)
            if c:
                for o in list(c.objects):
                    _move_object_to_collection(o, wgt_coll)
                    o.hide_viewport = True
                    o.hide_render = True
                if len(c.objects) == 0:
                    bpy.data.collections.remove(c, do_unlink=True)

        wheel_coll = bpy.data.collections.get(LightingPanelNames.Collections.WHEEL)
        if wheel_coll:
            for o in list(wheel_coll.objects):
                _move_object_to_collection(o, char_coll)
                try:
                    o.hide_render = True
                except Exception:
                    pass
                try:
                    drv = o.driver_add('hide_viewport').driver
                    drv.type = 'SCRIPTED'
                    drv.expression = 'not is_visible'
                    var = drv.variables.new()
                    var.name = 'is_visible'
                    var.type = 'SINGLE_PROP'
                    var.targets[0].id_type = 'ARMATURE'
                    var.targets[0].id = rig_obj.data
                    var.targets[0].data_path = 'collections["Lighting"].is_visible'
                except Exception:
                    pass
            if len(wheel_coll.objects) == 0:
                bpy.data.collections.remove(wheel_coll, do_unlink=True)

        lp_coll = bpy.data.collections.get(LightingPanelNames.Collections.LIGHTING_PANEL)
        if lp_coll and len(lp_coll.objects) == 0:
            bpy.data.collections.remove(lp_coll, do_unlink=True)

    for empty_name, dest_coll in (
        ('Face Light Direction', wgt_coll),
        ('Head Driver', wgt_coll),
        ('Head Origin', wgt_coll),
        ('Head Forward', wgt_coll),
        ('Head Up', wgt_coll),
        ('Main Light Direction', char_coll),
        ('Light Direction', char_coll),
    ):
        empty_obj = bpy.data.objects.get(empty_name)
        if empty_obj:
            empty_obj.name = f'{empty_name}_{char_name}'
            _move_object_to_collection(empty_obj, dest_coll)


def _organize_bone_collections(rig_obj, bone_map, orig_order):
    """Place Rigify controls and original Bone_* extras into standard bone collections."""
    setup_standard_bone_collections(rig_obj, is_version_4=True)
    colls = rig_obj.data.collections
    tail_coll = colls.get('Tail') or colls.new('Tail')
    tail_coll.is_visible = True

    def assign_only(bone_name, coll_name):
        b = rig_obj.data.bones.get(bone_name)
        c = colls.get(coll_name)
        if not b or not c:
            return
        for existing in list(b.collections):
            if existing != c:
                try:
                    existing.unassign(b)
                except Exception:
                    pass
        c.assign(b)

    for b in rig_obj.data.bones:
        assign_only(b.name, 'Other')

    for b in rig_obj.data.bones:
        bn = b.name
        if bn.startswith(('DEF-', 'ORG-', 'MCH-')):
            continue
        if 'tweak' in bn:
            assign_only(bn, 'Tweaks')
        elif bn in ('root',):
            assign_only(bn, 'Root')
        elif bn in ('torso', 'hips', 'chest', 'neck', 'head'):
            assign_only(bn, 'Torso (IK)')
        elif bn.startswith('spine_fk'):
            assign_only(bn, 'Torso (FK)')
        elif bn.startswith(('thumb', 'f_')) and (bn.endswith('_master.L') or bn.endswith('_master.R') or bn.endswith('_ik.L') or bn.endswith('_ik.R')):
            assign_only(bn, 'Fingers')
        elif bn.startswith(('thumb.', 'f_index.', 'f_middle.', 'f_ring.', 'f_pinky.')):
            assign_only(bn, 'Fingers (Detail)')
        elif bn in ('upper_arm_parent.L', 'upper_arm_ik_target.L', 'hand_ik.L', 'shoulder.L', 'upper_arm_ik.L'):
            assign_only(bn, 'Arm.L (IK)')
        elif bn in ('upper_arm_parent.R', 'upper_arm_ik_target.R', 'hand_ik.R', 'shoulder.R', 'upper_arm_ik.R'):
            assign_only(bn, 'Arm.R (IK)')
        elif bn in ('upper_arm_fk.L', 'forearm_fk.L', 'hand_fk.L'):
            assign_only(bn, 'Arm.L (FK)')
        elif bn in ('upper_arm_fk.R', 'forearm_fk.R', 'hand_fk.R'):
            assign_only(bn, 'Arm.R (FK)')
        elif bn in ('tail', 'tail.001', 'tail.002', 'tail.003', 'tail.004', 'tail_master'):
            assign_only(bn, 'Tail')
        elif bn.startswith('LimitDistance-'):
            assign_only(bn, 'Other')
            b.hide = True
        elif bn in (
            LightingPanelNames.Bones.LIGHTING_PANEL,
            'Fresnel', 'Ambient', 'SoftLit', 'Lit', 'SoftShadow', 'Shadow',
            'RimShadow', 'Rim Lit', 'RimX', 'RimY',
            'RimLitPin', 'ShadowPin', 'LitPin', 'AmbientPin',
            'RimShadowPin', 'SoftShadowPin', 'SoftLitPin', 'FresnelPin',
            'ShadowOffset', 'FresnelSize', 'FresnelToggle',
        ):
            assign_only(bn, 'Lighting')

    # Organize original Bone_* bones: mapped deformers go to Other (hidden),
    # unmapped poseable extras go to Face / Tail / Clothes.
    face_kw = ('jaw', 'tongue', 'eyelid', 'earfur', 'eye', 'mouth')
    for bn in orig_order:
        if bn in bone_map or bn == 'Bone_Root':
            assign_only(bn, 'Other')
            continue
        low = bn.lower()
        if any(k in low for k in face_kw):
            assign_only(bn, 'Face')
        elif 'tail' in low:
            assign_only(bn, 'Tail')
        else:
            assign_only(bn, 'Clothes')

    for coll_name in ('Leg.L (IK)', 'Leg.R (IK)', 'Leg.L (FK)', 'Leg.R (FK)'):
        c = colls.get(coll_name)
        if c:
            c.is_visible = False
    for coll_name in ('Face', 'Clothes', 'Tail'):
        c = colls.get(coll_name)
        if c and len(c.bones) > 0:
            c.is_visible = True


def rig_custom_npc(
    armature,
    disallow_arm_ik_stretch=True,
    use_arm_ik_poles=False,
):
    """Build a Rigify rig in-place on a non-Bip001 NPC armature, driving original deform bones."""
    original_name = armature.name
    char_name = resolve_rig_character_name(original_name, arm_obj=armature)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    orig_order, snap = _snapshot_source_bones(armature)
    meta_obj, bone_map = _build_kukulkan_metarig(snap)

    # Generate Rigify rig directly onto the existing armature object so all mesh modifiers stay valid.
    meta_obj.data.rigify_target_rig = armature
    bpy.context.view_layer.objects.active = meta_obj
    bpy.ops.object.select_all(action='DESELECT')
    meta_obj.select_set(True)
    bpy.ops.pose.rigify_generate()

    # Reconstruct original Bone_* bones on the generated rig and attach mapped ones to Rigify DEF-* bones.
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    edit_bones = armature.data.edit_bones
    for bname in orig_order:
        if bname in edit_bones:
            continue
        info = snap[bname]
        eb = edit_bones.new(bname)
        eb.head = info['head']
        eb.tail = info['tail']
        eb.roll = info['roll']
        eb.use_deform = True
        eb.inherit_scale = info['inherit_scale']

    for bname in orig_order:
        eb = edit_bones[bname]
        if bname in bone_map and bone_map[bname] in edit_bones:
            def_bone = edit_bones[bone_map[bname]]
            def_bone.use_deform = False
            eb.parent = def_bone
            eb.use_connect = False
        elif bname == 'Bone_Root':
            eb.parent = edit_bones.get('torso') or edit_bones.get('root')
            eb.use_connect = False
        else:
            orig_parent = snap[bname]['parent']
            if orig_parent and orig_parent in edit_bones:
                eb.parent = edit_bones[orig_parent]
                eb.use_connect = snap[bname]['use_connect'] if orig_parent not in bone_map else False

    bpy.ops.object.mode_set(mode='OBJECT')
    for bname in orig_order:
        pb = armature.pose.bones.get(bname)
        if pb:
            pb.rotation_mode = snap[bname]['rotation_mode']

    # Remove metarig
    bpy.data.objects.remove(meta_obj, do_unlink=True)

    # Configure pose options on generated Rigify rig
    if armature.pose:
        for side in ('.L', '.R'):
            up = armature.pose.bones.get(f'upper_arm_parent{side}')
            if up:
                if disallow_arm_ik_stretch:
                    up['IK_Stretch'] = 0.0
                if use_arm_ik_poles:
                    up['pole_vector'] = 1
        torso = armature.pose.bones.get('torso')
        if torso:
            torso['neck_follow'] = 1.0
            torso['head_follow'] = 1.0

    # Rename armature & package into character collection
    armature.name = char_name
    if armature.data:
        armature.data.name = char_name
        armature.data.display_type = 'STICK'
        armature.data.property_overridable_library_set('["rig_id"]', True)
    armature.show_in_front = True

    char_coll = bpy.data.collections.get(char_name)
    if not char_coll:
        char_coll = bpy.data.collections.new(char_name)
    if char_coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(char_coll)

    _move_object_to_collection(armature, char_coll)
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH' and (
            obj.parent == armature
            or any(m.type == 'ARMATURE' and m.object == armature for m in obj.modifiers)
        ):
            _move_object_to_collection(obj, char_coll)

    wgt_coll = get_or_create_char_wgts(char_coll, char_name)
    for coll in list(bpy.data.collections):
        if coll.name.startswith('WGTS') and coll != wgt_coll:
            for o in list(coll.objects):
                _move_object_to_collection(o, wgt_coll)
                o.hide_viewport = True
                o.hide_render = True
            if len(coll.objects) == 0 and len(coll.children) == 0:
                try:
                    bpy.data.collections.remove(coll, do_unlink=True)
                except Exception:
                    pass

    _setup_lighting_panel_and_empties(armature, char_name, char_coll, wgt_coll)
    _organize_bone_collections(armature, bone_map, orig_order)

    wgt_coll.hide_select = True
    wgt_coll.hide_viewport = True
    wgt_coll.hide_render = True

    isolate_wgts_for_character(armature, char_name, char_coll=char_coll)
    if use_arm_ik_poles:
        setup_pole_targets(armature, use_arm_ik_poles=True, use_leg_ik_poles=False)

    modify_and_run_rig_ui_script(armature, original_name, char_name=char_name)

    default_coll = bpy.data.collections.get('Collection')
    if default_coll and len(default_coll.objects) == 0 and len(default_coll.children) == 0:
        try:
            bpy.data.collections.remove(default_coll, do_unlink=True)
        except Exception:
            pass
