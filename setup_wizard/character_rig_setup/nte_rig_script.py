import bpy
import mathutils
import os
from setup_wizard.character_rig_setup.rig_ui_utils import (
    extract_clean_character_name,
    setup_standard_bone_collections,
    distribute_standard_rig_bones,
    modify_and_run_rig_ui_script,
)

def _is_already_rigged(arm_obj):
    """Detecta si el armature ya es un rig Rigify generado (evita doble-rig,
    que deja roots/widgets rotos). Solo casos seguros: plate-settings o rig_id
    presentes = rig final. Un run fallido a medias (sin plate) puede reintentarse.
    """
    try:
        if arm_obj is None or arm_obj.type != 'ARMATURE':
            return False
        if arm_obj.pose and "plate-settings" in arm_obj.pose.bones:
            return True
        if arm_obj.data and arm_obj.data.get("rig_id"):
            return True
    except Exception:
        pass
    return False


def rig_character(
    file_path,
    disallow_arm_ik_stretch,
    disallow_leg_ik_stretch,
    use_arm_ik_poles,
    use_leg_ik_poles,
    add_child_of_constraints,
    use_head_tracker,
    meshes_joined=False):

    context = bpy.context
    obj = context.object
    if not obj or obj.type != 'ARMATURE':
        armatures = [o for o in context.scene.objects if o.type == 'ARMATURE']
        if armatures:
            obj = armatures[0]
            context.view_layer.objects.active = obj
        else:
            return

    if _is_already_rigged(obj):
        print(f"[NTE RIG] '{obj.name}' ya es un rig generado (plate-settings/rig_id). "
              f"Rig omitido: borra el rig o parte de un archivo limpio para re-riggear.")
        return

    if obj.name[-4:] == ".001":
        obj.name = obj.name[:-4]
    print("New NTE Rig Run\n\n")

    original_name = obj.name
    meshes = [m for m in context.scene.objects if m.type == 'MESH']

    # Backup original armature object for preserving secondary bones (hair, skirt, sleeves, cloth)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.duplicate(linked=False)
    backup_arm = context.active_object
    backup_arm.name = "NTE_Secondary_Bones_Backup"

    # Re-activate original armature
    context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    # Reset pose transforms
    bpy.ops.object.mode_set(mode='POSE')
    for pb in obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Build comprehensive NTE / Bip001 Bone Mapping to Rigify DEF- Naming
    abadidea = {}
    prefixes = ['Bip001-', 'Bip001 ', 'Bip001_']

    body_base_map = {
        'Pelvis': 'DEF-spine',
        'Spine': 'DEF-spine.001',
        'Spine1': 'DEF-spine.002',
        'Spine2': 'DEF-spine.003',
        'Neck': 'DEF-spine.004',
        'Head': 'DEF-spine.006',

        'L-Thigh': 'DEF-thigh.L', 'L Thigh': 'DEF-thigh.L', 'L_Thigh': 'DEF-thigh.L',
        'L-Calf': 'DEF-shin.L', 'L Calf': 'DEF-shin.L', 'L_Calf': 'DEF-shin.L',
        'L-Foot': 'DEF-foot.L', 'L Foot': 'DEF-foot.L', 'L_Foot': 'DEF-foot.L',
        'L-Toe0': 'DEF-toe.L', 'L Toe0': 'DEF-toe.L', 'L_Toe0': 'DEF-toe.L',

        'R-Thigh': 'DEF-thigh.R', 'R Thigh': 'DEF-thigh.R', 'R_Thigh': 'DEF-thigh.R',
        'R-Calf': 'DEF-shin.R', 'R Calf': 'DEF-shin.R', 'R_Calf': 'DEF-shin.R',
        'R-Foot': 'DEF-foot.R', 'R Foot': 'DEF-foot.R', 'R_Foot': 'DEF-foot.R',
        'R-Toe0': 'DEF-toe.R', 'R Toe0': 'DEF-toe.R', 'R_Toe0': 'DEF-toe.R',

        'L-Clavicle': 'DEF-shoulder.L', 'L Clavicle': 'DEF-shoulder.L', 'L_Clavicle': 'DEF-shoulder.L',
        'L-UpperArm': 'DEF-upper_arm.L', 'L UpperArm': 'DEF-upper_arm.L', 'L_UpperArm': 'DEF-upper_arm.L',
        'L-Forearm': 'DEF-forearm.L', 'L Forearm': 'DEF-forearm.L', 'L_Forearm': 'DEF-forearm.L',
        'L-Hand': 'DEF-hand.L', 'L Hand': 'DEF-hand.L', 'L_Hand': 'DEF-hand.L',

        'R-Clavicle': 'DEF-shoulder.R', 'R Clavicle': 'DEF-shoulder.R', 'R_Clavicle': 'DEF-shoulder.R',
        'R-UpperArm': 'DEF-upper_arm.R', 'R UpperArm': 'DEF-upper_arm.R', 'R_UpperArm': 'DEF-upper_arm.R',
        'R-Forearm': 'DEF-forearm.R', 'R Forearm': 'DEF-forearm.R', 'R_Forearm': 'DEF-forearm.R',
        'R-Hand': 'DEF-hand.R', 'R Hand': 'DEF-hand.R', 'R_Hand': 'DEF-hand.R',
    }

    for pfx in prefixes:
        for k, v in body_base_map.items():
            abadidea[pfx + k] = v

    # Add exact and dynamic matches for eyes & breasts (Bn_l_breast_001, Bn_r_breast_001,
    # Bn_l_breast01 como Nitsa, Bn_l_breast1, etc.)
    abadidea.update({
        'eye_R': 'DEF-eye.R', 'eye_L': 'DEF-eye.L',
        'Bn_l_breast_001': 'DEF-breast.L', 'Bn_r_breast_001': 'DEF-breast.R',
        'Bn_L_breast_001': 'DEF-breast.L', 'Bn_R_breast_001': 'DEF-breast.R',
        'bn_l_breast_001': 'DEF-breast.L', 'bn_r_breast_001': 'DEF-breast.R',
        'Bn_l_breast_01': 'DEF-breast.L', 'Bn_r_breast_01': 'DEF-breast.R',
        'Bn_l_breast01': 'DEF-breast.L', 'Bn_r_breast01': 'DEF-breast.R',
        'Bn_L_breast01': 'DEF-breast.L', 'Bn_R_breast01': 'DEF-breast.R',
        'bn_l_breast01': 'DEF-breast.L', 'bn_r_breast01': 'DEF-breast.R',
        'Bn_l_breast1': 'DEF-breast.L', 'Bn_r_breast1': 'DEF-breast.R',
        'Bn_L_breast1': 'DEF-breast.L', 'Bn_R_breast1': 'DEF-breast.R',
        'bn_l_breast1': 'DEF-breast.L', 'bn_r_breast1': 'DEF-breast.R',
        'breast.L': 'DEF-breast.L', 'breast.R': 'DEF-breast.R',
    })

    # Dynamic breast detection for other naming conventions in NTE.
    # OJO: no usar `v not in abadidea.values()` como guard: las entradas exactas
    # ya pre-llenan esos valores y bloquearian la rama dinamica para siempre
    # (caso Nitsa: Bn_l_breast01 nunca se mapeaba). Se rastrean slots ocupados
    # por matches exactos REALES en este armature + claims dinamicos.
    _existing_names = {pb.name for pb in obj.pose.bones}
    _exact_claimed = {v for k, v in abadidea.items() if k in _existing_names}
    _dynamic_claimed = set()
    for pb in obj.pose.bones:
        pb_low = pb.name.lower()
        if ("breast" in pb_low or "xiong" in pb_low) and not pb.name.startswith(("DEF-", "ORG-", "MCH-")):
            if any(s in pb_low for s in ["_l", ".l", "l_", "left"]) \
                    and "DEF-breast.L" not in _exact_claimed \
                    and "DEF-breast.L" not in _dynamic_claimed:
                abadidea[pb.name] = "DEF-breast.L"
                _dynamic_claimed.add("DEF-breast.L")
            elif any(s in pb_low for s in ["_r", ".r", "r_", "right"]) \
                    and "DEF-breast.R" not in _exact_claimed \
                    and "DEF-breast.R" not in _dynamic_claimed:
                abadidea[pb.name] = "DEF-breast.R"
                _dynamic_claimed.add("DEF-breast.R")

    # Dynamic Finger Mappings for both Left (.L) and Right (.R) hands
    existing_bone_names = {pb.name for pb in obj.pose.bones}
    finger_names_map = [
        ("f_index", 1),
        ("f_middle", 2),
        ("f_ring", 3),
        ("f_pinky", 4),
    ]

    bones_to_remove_from_armature = set()
    vgroups_to_merge_into_hand = []

    for side in ["L", "R"]:
        s_suffix = f".{side}"

        # Detect separator used in armature bone names (e.g. "-", " ", "_")
        sep_found = None
        for test_s in ["-", " ", "_"]:
            for f_idx in [0, 1, 2, 3, 4]:
                if f"Bip001{test_s}{side}{test_s}Finger{f_idx}" in existing_bone_names or f"Bip001{test_s}{side}{test_s}Finger{f_idx}1" in existing_bone_names:
                    sep_found = test_s
                    break
            if sep_found:
                break
        if not sep_found:
            sep_found = "-"

        # 1. Map Thumb (Finger0, Finger01, Finger02 or Finger00, Finger01, Finger02 or Finger01, Finger02, Finger03)
        b0_key = f"Bip001{sep_found}{side}{sep_found}Finger0"
        b00_key = f"Bip001{sep_found}{side}{sep_found}Finger00"
        b01_key = f"Bip001{sep_found}{side}{sep_found}Finger01"
        b02_key = f"Bip001{sep_found}{side}{sep_found}Finger02"
        b03_key = f"Bip001{sep_found}{side}{sep_found}Finger03"

        t1 = b0_key if b0_key in existing_bone_names else (b00_key if b00_key in existing_bone_names else b01_key)
        t2 = b01_key if (t1 != b01_key and b01_key in existing_bone_names) else b02_key
        t3 = b02_key if (t2 != b02_key and b02_key in existing_bone_names) else b03_key

        if t1 in existing_bone_names: abadidea[t1] = f"DEF-thumb.01{s_suffix}"
        if t2 in existing_bone_names: abadidea[t2] = f"DEF-thumb.02{s_suffix}"
        if t3 in existing_bone_names: abadidea[t3] = f"DEF-thumb.03{s_suffix}"

        if b03_key in existing_bone_names and b03_key not in [t1, t2, t3]:
            vgroups_to_merge_into_hand.append((b03_key, f"DEF-thumb.03{s_suffix}"))
            bones_to_remove_from_armature.add(b03_key)

        # 2. Map Index, Middle, Ring, Pinky
        for fname, f_idx in finger_names_map:
            b1_key = f"Bip001{sep_found}{side}{sep_found}Finger{f_idx}"
            b10_key = f"Bip001{sep_found}{side}{sep_found}Finger{f_idx}0"
            b11_key = f"Bip001{sep_found}{side}{sep_found}Finger{f_idx}1"
            b12_key = f"Bip001{sep_found}{side}{sep_found}Finger{f_idx}2"
            b13_key = f"Bip001{sep_found}{side}{sep_found}Finger{f_idx}3"

            if b13_key in existing_bone_names:
                # 4-bone finger chain (e.g. Finger1 = palm, Finger11 = proximal, Finger12 = middle, Finger13 = tip)
                if b11_key in existing_bone_names: abadidea[b11_key] = f"DEF-{fname}.01{s_suffix}"
                if b12_key in existing_bone_names: abadidea[b12_key] = f"DEF-{fname}.02{s_suffix}"
                if b13_key in existing_bone_names: abadidea[b13_key] = f"DEF-{fname}.03{s_suffix}"

                # Metacarpal/palm bone: merge weights into DEF-hand and remove bone from armature
                palm_bone = b1_key if b1_key in existing_bone_names else (b10_key if b10_key in existing_bone_names else None)
                if palm_bone:
                    vgroups_to_merge_into_hand.append((palm_bone, f"DEF-hand{s_suffix}"))
                    bones_to_remove_from_armature.add(palm_bone)
            else:
                # 3-bone finger chain:
                d1 = b1_key if b1_key in existing_bone_names else (b10_key if b10_key in existing_bone_names else b11_key)
                d2 = b11_key if (d1 != b11_key and b11_key in existing_bone_names) else b12_key
                d3 = b12_key if (d2 != b12_key and d2 != b13_key and b12_key in existing_bone_names) else b13_key

                if d1 in existing_bone_names: abadidea[d1] = f"DEF-{fname}.01{s_suffix}"
                if d2 in existing_bone_names: abadidea[d2] = f"DEF-{fname}.02{s_suffix}"
                if d3 in existing_bone_names: abadidea[d3] = f"DEF-{fname}.03{s_suffix}"

    def merge_vgroup(mesh_obj, src_vg_name, dst_vg_name):
        src_vg = mesh_obj.vertex_groups.get(src_vg_name)
        dst_vg = mesh_obj.vertex_groups.get(dst_vg_name)
        if not src_vg or not dst_vg or src_vg == dst_vg:
            return
        for v in mesh_obj.data.vertices:
            try:
                w_src = src_vg.weight(v.index)
            except RuntimeError:
                w_src = 0.0
            if w_src > 0.0:
                try:
                    w_dst = dst_vg.weight(v.index)
                except RuntimeError:
                    w_dst = 0.0
                dst_vg.add([v.index], w_src + w_dst, 'REPLACE')
        mesh_obj.vertex_groups.remove(src_vg)

    # Merge palm/metacarpal vertex groups into DEF-hand (or destination group)
    for m in meshes:
        for src_name, dst_name in vgroups_to_merge_into_hand:
            if dst_name not in m.vertex_groups and dst_name.startswith("DEF-"):
                alt_hand = dst_name[4:]
                if alt_hand in m.vertex_groups:
                    merge_vgroup(m, src_name, alt_hand)
                else:
                    m.vertex_groups.new(name=dst_name)
                    merge_vgroup(m, src_name, dst_name)
            else:
                merge_vgroup(m, src_name, dst_name)

    # Rename bones FIRST so Blender updates linked vertex groups automatically
    for pb in obj.pose.bones:
        if pb.name in abadidea:
            target_name = abadidea[pb.name]
            if target_name != pb.name:
                pb.name = target_name

    # Rename any leftover vertex groups on meshes and merge if target already exists
    for m in meshes:
        for orig_vg_name, target_def in abadidea.items():
            vg = m.vertex_groups.get(orig_vg_name)
            if vg:
                target_vg = m.vertex_groups.get(target_def)
                if target_vg and target_vg != vg:
                    merge_vgroup(m, orig_vg_name, target_def)
                else:
                    vg.name = target_def

        # Cleanup any duplicate .001 vertex groups by merging into base group
        for vg in list(m.vertex_groups):
            if vg.name.endswith(".001"):
                base_name = vg.name[:-4]
                if base_name in m.vertex_groups:
                    merge_vgroup(m, vg.name, base_name)

    # Switch to Edit mode to remove metacarpals and sanitize finger hierarchy, head/tail vectors, and connections
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = obj.data.edit_bones

    for b_del in bones_to_remove_from_armature:
        if b_del in ebs:
            ebs.remove(ebs[b_del])

    for side in [".L", ".R"]:
        hand_eb = ebs.get("DEF-hand" + side) or ebs.get("hand" + side)
        for fname in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
            b1 = ebs.get(f"DEF-{fname}.01{side}") or ebs.get(f"{fname}.01{side}")
            b2 = ebs.get(f"DEF-{fname}.02{side}") or ebs.get(f"{fname}.02{side}")
            b3 = ebs.get(f"DEF-{fname}.03{side}") or ebs.get(f"{fname}.03{side}")

            if b1 and hand_eb:
                b1.parent = hand_eb

            if b1 and b2:
                b2.parent = b1
                # If tail of b1 is misaligned or zero-length, connect to b2 head
                if (b1.tail - b2.head).length > 0.001 or (b1.tail - b1.head).length < 0.0005:
                    b1.tail = b2.head.copy()

            if b2 and b3:
                b3.parent = b2
                # If tail of b2 is misaligned or zero-length, connect to b3 head
                if (b2.tail - b3.head).length > 0.001 or (b2.tail - b2.head).length < 0.0005:
                    b2.tail = b3.head.copy()

            if b3:
                # Ensure b3 has a valid non-zero tail vector extending along the finger
                if (b3.tail - b3.head).length < 0.0005 or b3.tail.length < 0.001:
                    if b2:
                        dir_v = (b3.head - b2.head)
                        if dir_v.length < 0.0001:
                            dir_v = (b2.head - b1.head) if b1 else mathutils.Vector((0, 0.025, 0))
                        flen = b2.length if b2.length > 0.001 else 0.025
                        b3.tail = b3.head + dir_v.normalized() * flen
                    else:
                        b3.tail = b3.head + mathutils.Vector((0, 0.025, 0))

    bpy.ops.object.mode_set(mode='POSE')

    if hasattr(bpy.types, 'Action') and not hasattr(bpy.types.Action, 'fcurves'):
        try:
            bpy.types.Action.fcurves = property(lambda self: getattr(self, 'curves', []))
        except Exception:
            pass

    # Expykit convert bone names & extract metarig
    try:
        bpy.ops.object.expykit_convert_bone_names(src_preset='Rigify_Metarig.py', trg_preset='Rigify_Deform.py')
    except Exception as ex:
        print(f"Notice: Expykit convert_bone_names handled: {ex}")

    try:
        bpy.ops.object.expykit_extract_metarig(rig_preset='Rigify_Metarig.py', assign_metarig=True)
    except Exception as ex:
        print(f"Notice: Expykit extract_metarig handled: {ex}")

    # Generate Rigify with aligned Head bone, Breast bones, Hand alignment, and Finger Roll alignment
    metarig_obj = bpy.data.objects.get("metarig")
    if metarig_obj:
        context.view_layer.objects.active = metarig_obj
        bpy.ops.object.mode_set(mode='EDIT')
        eb_head = metarig_obj.data.edit_bones.get("spine.006") or metarig_obj.data.edit_bones.get("head")
        if eb_head:
            # Set head bone tail pointing straight up (+Z) above crown of head for halo control ring
            eb_head.tail.x = eb_head.head.x
            eb_head.tail.y = eb_head.head.y
            eb_head.tail.z = eb_head.head.z + 0.22
            eb_head.roll = 0.0

        # Align breast bones in metarig to character's actual breast bones (Bn_l_breast_001 / Bn_r_breast_001)
        orig_arm = backup_arm or obj
        boob_b_L = None
        boob_b_R = None
        if orig_arm and orig_arm.data:
            for b_cand in ["Bn_l_breast_001", "Bn_L_breast_001", "Bn_l_breast_01",
                           "Bn_l_breast01", "Bn_L_breast01", "Bn_l_breast1",
                           "DEF-breast.L", "breast.L"]:
                if b_cand in orig_arm.data.bones:
                    boob_b_L = orig_arm.data.bones[b_cand]
                    break
            for b_cand in ["Bn_r_breast_001", "Bn_R_breast_001", "Bn_r_breast_01",
                           "Bn_r_breast01", "Bn_R_breast01", "Bn_r_breast1",
                           "DEF-breast.R", "breast.R"]:
                if b_cand in orig_arm.data.bones:
                    boob_b_R = orig_arm.data.bones[b_cand]
                    break
            if not boob_b_L:
                for b in orig_arm.data.bones:
                    b_l = b.name.lower()
                    if ("breast" in b_l or "xiong" in b_l) and any(s in b_l for s in ["_l", ".l", "l_", "left"]):
                        boob_b_L = b
                        break
            if not boob_b_R:
                for b in orig_arm.data.bones:
                    b_l = b.name.lower()
                    if ("breast" in b_l or "xiong" in b_l) and any(s in b_l for s in ["_r", ".r", "r_", "right"]):
                        boob_b_R = b
                        break

        eb_bl = metarig_obj.data.edit_bones.get("breast.L")
        eb_br = metarig_obj.data.edit_bones.get("breast.R")

        if boob_b_L and eb_bl:
            eb_bl.head = boob_b_L.head_local.copy()
            eb_bl.tail = eb_bl.head + mathutils.Vector((0, -0.06, 0))
            eb_bl.roll = 0.0

            if eb_br:
                if boob_b_R:
                    eb_br.head = boob_b_R.head_local.copy()
                else:
                    eb_br.head = mathutils.Vector((-eb_bl.head.x, eb_bl.head.y, eb_bl.head.z))
                eb_br.tail = eb_br.head + mathutils.Vector((0, -0.06, 0))
                eb_br.roll = 0.0
        elif eb_bl and eb_br:
            chest_eb = metarig_obj.data.edit_bones.get("spine.003") or metarig_obj.data.edit_bones.get("chest")
            if chest_eb:
                cz = chest_eb.head.z + (chest_eb.tail.z - chest_eb.head.z) * 0.25
                cy = chest_eb.head.y - 0.07
                eb_bl.head = mathutils.Vector((0.050, cy, cz))
                eb_bl.tail = mathutils.Vector((0.050, cy - 0.05, cz))
                eb_br.head = mathutils.Vector((-0.050, cy, cz))
                eb_br.tail = mathutils.Vector((-0.050, cy - 0.05, cz))

        # Empujar controles al frente del volumen (como ZZZ): el hueso nace dentro
        # del pecho y el circulo queda enterrado. Push proporcional al halfwidth
        # en -Y (frente NTE), pre-generate para no desplazar el deform.
        for _bb in [b for b in [eb_bl, eb_br] if b is not None]:
            try:
                _push = abs(_bb.head.x) * 2.0
                _dir = _bb.tail - _bb.head
                _bb.head.y -= _push
                _bb.tail = _bb.head + _dir
            except Exception as ex_push:
                print(f"[NTE RIG] breast push notice: {ex_push}")

        # Align shoulder.R metarig bone roll so widget is symmetrical and not flipped
        sh_L = metarig_obj.data.edit_bones.get("shoulder.L")
        sh_R = metarig_obj.data.edit_bones.get("shoulder.R")
        if sh_L and sh_R:
            sh_R.roll = -sh_L.roll

        # Align hand.L and hand.R metarig bones straight along forearm vector so hand_ik widget is centered on wrist
        forearm_R = metarig_obj.data.edit_bones.get("forearm.R")
        hand_R = metarig_obj.data.edit_bones.get("hand.R")
        if forearm_R and hand_R:
            arm_vec_R = (forearm_R.tail - forearm_R.head).normalized()
            hand_R.tail = hand_R.head + arm_vec_R * 0.05
            hand_R.roll = forearm_R.roll

        forearm_L = metarig_obj.data.edit_bones.get("forearm.L")
        hand_L = metarig_obj.data.edit_bones.get("hand.L")
        if forearm_L and hand_L:
            arm_vec_L = (forearm_L.tail - forearm_L.head).normalized()
            hand_L.tail = hand_L.head + arm_vec_L * 0.05
            if hand_R:
                hand_L.roll = -hand_R.roll
            elif forearm_L:
                hand_L.roll = -forearm_L.roll

        # Align metarig finger rolls directly to hand / index finger plane normal
        armature_ebs = obj.data.edit_bones
        metarm_ebs = metarig_obj.data.edit_bones

        for side in [".L", ".R"]:
            hand_mb = metarm_ebs.get("hand" + side)
            hand_ab = armature_ebs.get("hand" + side) or armature_ebs.get("DEF-hand" + side)

            index_chain = []
            for idx in ["01", "02", "03"]:
                b_meta = metarm_ebs.get(f"f_index.{idx}{side}")
                if b_meta:
                    index_chain.append(b_meta)

            index_plane_normal = None
            if len(index_chain) >= 2:
                dir1 = (index_chain[0].tail - index_chain[0].head).normalized()
                dir2 = (index_chain[1].tail - index_chain[1].head).normalized()
                cross_vec = dir1.cross(dir2)
                if cross_vec.length > 0.0001:
                    index_plane_normal = cross_vec.normalized()

            if not index_plane_normal and hand_mb:
                index_plane_normal = hand_mb.matrix.col[2].normalized()
            elif not index_plane_normal and hand_ab:
                index_plane_normal = hand_ab.matrix.col[2].normalized()

            if index_plane_normal:
                for fname in ["f_index", "f_middle", "f_ring", "f_pinky"]:
                    chain = []
                    for idx in ["01", "02", "03"]:
                        b_meta = metarm_ebs.get(f"{fname}.{idx}{side}")
                        if b_meta:
                            chain.append(b_meta)

                    for b_meta in chain:
                        dir_b = (b_meta.tail - b_meta.head).normalized()
                        z_target = index_plane_normal.cross(dir_b)
                        if z_target.length > 0.0001:
                            b_meta.align_roll(z_target)

                        orig_b = (
                            armature_ebs.get(b_meta.name)
                            or armature_ebs.get("DEF-" + b_meta.name)
                        )
                        if orig_b:
                            orig_b.roll = b_meta.roll

        # Thumb alignment using vector from thumb knuckle to index knuckle so flexing points directly into palm
        for side in [".L", ".R"]:
            thumb_01 = metarm_ebs.get(f"thumb.01{side}")
            index_01 = metarm_ebs.get(f"f_index.01{side}")
            if thumb_01 and index_01:
                v_towards_index = (index_01.head - thumb_01.head).normalized()
                for idx in ["01", "02", "03"]:
                    t_meta = metarm_ebs.get(f"thumb.{idx}{side}")
                    if t_meta:
                        dir_t = (t_meta.tail - t_meta.head).normalized()
                        z_target_thumb = v_towards_index.cross(dir_t)
                        if z_target_thumb.length > 0.0001:
                            t_meta.align_roll(z_target_thumb)
                            orig_b = armature_ebs.get(t_meta.name) or armature_ebs.get("DEF-" + t_meta.name)
                            if orig_b:
                                orig_b.roll = t_meta.roll

        # Set primary rotation axis in Pose mode on metarig for fingers and thumb
        bpy.ops.object.mode_set(mode='POSE')
        metapose = metarig_obj.pose
        for fname in ["f_index", "f_middle", "f_ring", "f_pinky", "thumb"]:
            for side in [".L", ".R"]:
                p_b = metapose.bones.get(f"{fname}.01{side}")
                if p_b and hasattr(p_b, 'rigify_parameters'):
                    p_b.rigify_parameters.primary_rotation_axis = "X"

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        metarig_obj.select_set(True)
        context.view_layer.objects.active = metarig_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.rigify_generate()

    # Find generated Rigify rig
    rigifyr = bpy.data.objects.get("rigify") or bpy.data.objects.get("rig")
    if not rigifyr:
        for o in context.scene.objects:
            if o.type == 'ARMATURE' and o.name != "metarig" and o != backup_arm:
                rigifyr = o
                break

    # ZZZ parity: append widget shapes from RootShape.blend.
    # Solo los que ZZZ realmente tiene: head-control-shape viene en append_Root;
    # primo-joint/setting-circle viven en la coleccion suelta 'wgt' que ZZZ nunca
    # añade, asi que NO se traen (quedarian huerfanos en escena y primo-joint
    # ganaria el OR del star dando un shape distinto al de ZZZ).
    if rigifyr and file_path and os.path.isfile(file_path):
        _obj_dir = file_path if "/Object" in file_path else file_path + "/Object"
        for _shape_name in ["root plate.002", "root plate.001", "root plate",
                            "head-control-shape"]:
            if bpy.data.objects.get(_shape_name) is None:
                try:
                    bpy.ops.wm.append(filename=_shape_name, directory=_obj_dir)
                except Exception as ex_app:
                    print(f"[NTE RIG] shape append notice '{_shape_name}': {ex_app}")

    # Adjust master finger controls size in Edit mode and Pose mode
    if rigifyr:
        context.view_layer.objects.active = rigifyr
        bpy.ops.object.mode_set(mode='EDIT')
        
        finger_masters = [
            "thumb.01_master.L", "f_index.01_master.L", "f_middle.01_master.L", "f_ring.01_master.L", "f_pinky.01_master.L",
            "thumb.01_master.R", "f_index.01_master.R", "f_middle.01_master.R", "f_ring.01_master.R", "f_pinky.01_master.R"
        ]
        
        for b_name in finger_masters:
            eb = rigifyr.data.edit_bones.get(b_name)
            if eb:
                # Keep master finger edit bone length proportional so control line extends nicely without being giant
                if eb.length > 0.08:
                    eb.tail = eb.head + (eb.tail - eb.head).normalized() * 0.06

        rig_sh_L = rigifyr.data.edit_bones.get("shoulder.L")
        rig_sh_R = rigifyr.data.edit_bones.get("shoulder.R")
        if rig_sh_L and rig_sh_R:
            rig_sh_R.roll = -rig_sh_L.roll
        org_sh_L = rigifyr.data.edit_bones.get("ORG-shoulder.L")
        org_sh_R = rigifyr.data.edit_bones.get("ORG-shoulder.R")
        if org_sh_L and org_sh_R:
            org_sh_R.roll = -org_sh_L.roll

        bpy.ops.object.mode_set(mode='POSE')
        
        # Scale down custom shape sizes for hand_ik, breast, shoulder, and finger controls
        for b_name in ["shoulder.L", "shoulder.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                pb.custom_shape_scale_xyz = (1.60, 1.60, 1.60)

        for b_name in ["hand_ik.L", "hand_ik.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                pb.custom_shape_scale_xyz = (0.65, 0.65, 0.65)

        # Circulos grandes y deterministas: tamano absoluto (widget unitario r=0.5),
        # sin bone-size (antes 0.70 x hueso 0.06 = diminutos y enterrados).
        for b_name in ["breast.L", "breast.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                try:
                    pb.use_custom_shape_bone_size = False
                except Exception:
                    pass
                pb.custom_shape_scale_xyz = (0.07, 0.07, 0.07)

        for b_name in finger_masters:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                pb.custom_shape_scale_xyz = (1.50, 1.50, 1.50)
                try:
                    pb.lock_scale[0] = False
                except Exception:
                    pass

        # Scale down individual finger tweak/detail control shapes if present
        for fname in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
            for idx in ["01", "02", "03"]:
                for side in [".L", ".R"]:
                    pb = rigifyr.pose.bones.get(f"{fname}.{idx}{side}")
                    if pb and hasattr(pb, 'custom_shape_scale_xyz'):
                        pb.custom_shape_scale_xyz = (0.40, 0.40, 0.40)

        # ZZZ parity: IK defaults (IK_FK=0, IK_Stretch per props, pole_vector per props)
        for b_name in ["thigh_parent.L", "thigh_parent.R", "upper_arm_parent.L", "upper_arm_parent.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                try:
                    pb["IK_FK"] = 0.0
                except Exception:
                    pass
                is_arm = "upper_arm" in b_name
                disallow = disallow_arm_ik_stretch if is_arm else disallow_leg_ik_stretch
                try:
                    pb["IK_Stretch"] = 0.0 if disallow else 1.0
                except Exception:
                    pass
                # Unlock gears so they stay movable (ZZZ convention)
                try:
                    pb.custom_shape_transform = None
                    for i in range(3):
                        pb.lock_location[i] = False
                        pb.lock_rotation[i] = False
                        pb.lock_scale[i] = False
                    pb.lock_rotation_w = False
                except Exception:
                    pass

        if use_arm_ik_poles:
            for b_name in ["upper_arm_parent.L", "upper_arm_parent.R"]:
                pb = rigifyr.pose.bones.get(b_name)
                if pb is not None:
                    try:
                        pb["pole_vector"] = True
                    except Exception:
                        pass
        if use_leg_ik_poles:
            for b_name in ["thigh_parent.L", "thigh_parent.R"]:
                pb = rigifyr.pose.bones.get(b_name)
                if pb is not None:
                    try:
                        pb["pole_vector"] = True
                    except Exception:
                        pass

        # ZZZ parity: IK_parent dropdown (None/Root/Torso/Hips/Chest/Head) default Root=1
        for b_name in ["upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L", "thigh_parent.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb is not None and "IK_parent" in pb:
                try:
                    ui = pb.id_properties_ui("IK_parent")
                    curr = ui.as_dict()
                    curr_items = curr.get("items")
                    items_tuples = [(it[0], it[1], it[2]) for it in curr_items] if curr_items else [
                        ("P0", "None", ""), ("P1", "Root", ""), ("P2", "Torso", ""),
                        ("P3", "Hips", ""), ("P4", "Chest", ""), ("P5", "Head", ""),
                    ]
                    ui.update(items=items_tuples, default=1)
                    pb["IK_parent"] = 1
                except Exception as ex:
                    print(f"[NTE RIG] IK_parent dropdown notice {b_name}: {ex}")

        bpy.ops.object.mode_set(mode='OBJECT')

    # Transfer and parent ALL secondary/dynamic bones from backup_arm into rigifyr
    if rigifyr and backup_arm:
        context.view_layer.objects.active = backup_arm
        bpy.ops.object.mode_set(mode='OBJECT')
        
        sec_bones = []
        for b in backup_arm.data.bones:
            if b.name not in abadidea and b.name not in bones_to_remove_from_armature:
                p_name = b.parent.name if b.parent else None
                sec_bones.append({
                    'name': b.name,
                    'head': b.head_local.copy(),
                    'tail': b.tail_local.copy(),
                    'matrix': b.matrix_local.copy(),
                    'parent': p_name
                })

        context.view_layer.objects.active = rigifyr
        bpy.ops.object.mode_set(mode='EDIT')
        rig_edit_bones = rigifyr.data.edit_bones

        for b_info in sec_bones:
            b_name = b_info['name']
            if b_name not in rig_edit_bones:
                eb = rig_edit_bones.new(b_name)
                eb.head = b_info['head']
                eb.tail = b_info['tail']
                eb.matrix = b_info['matrix']
                eb.use_connect = False

                parent_name = b_info['parent']
                target_p = None

                if parent_name:
                    mapped_p = abadidea.get(parent_name, parent_name)
                    clean_name = mapped_p[4:] if mapped_p.startswith("DEF-") else mapped_p
                    org_p = "ORG-" + clean_name
                    target_p = rig_edit_bones.get(org_p) or rig_edit_bones.get(mapped_p) or rig_edit_bones.get(parent_name)

                if not target_p:
                    nl = b_name.lower()
                    if any(k in nl for k in ["hair", "head", "ear", "horn", "ring", "bone00"]):
                        target_p = rig_edit_bones.get("ORG-spine.006") or rig_edit_bones.get("DEF-spine.006") or rig_edit_bones.get("head")
                    elif any(k in nl for k in ["qun", "skirt", "tail", "pelvis"]):
                        target_p = rig_edit_bones.get("ORG-spine") or rig_edit_bones.get("DEF-spine") or rig_edit_bones.get("hips")
                    elif any(k in nl for k in ["xiu", "sleeve", "arm", "elbow"]):
                        if ".r" in nl or "_r_" in nl or "_r" in nl:
                            target_p = rig_edit_bones.get("ORG-forearm.R") or rig_edit_bones.get("DEF-forearm.R")
                        else:
                            target_p = rig_edit_bones.get("ORG-forearm.L") or rig_edit_bones.get("DEF-forearm.L")
                    elif any(k in nl for k in ["breast", "xiong"]):
                        target_p = rig_edit_bones.get("ORG-breast.R" if any(s in nl for s in [".r", "_r", "r_"]) else "ORG-breast.L") or rig_edit_bones.get("DEF-breast.R" if any(s in nl for s in [".r", "_r", "r_"]) else "DEF-breast.L") or rig_edit_bones.get("chest")
                    elif any(k in nl for k in ["cloth", "sce"]):
                        target_p = rig_edit_bones.get("ORG-spine.003") or rig_edit_bones.get("DEF-spine.003") or rig_edit_bones.get("chest")
                    elif "thigh" in nl:
                        target_p = rig_edit_bones.get("ORG-thigh.R" if ".r" in nl else "ORG-thigh.L") or rig_edit_bones.get("DEF-thigh.R" if ".r" in nl else "DEF-thigh.L")
                    elif "calf" in nl:
                        target_p = rig_edit_bones.get("ORG-shin.R" if ".r" in nl else "ORG-shin.L") or rig_edit_bones.get("DEF-shin.R" if ".r" in nl else "DEF-shin.L")

                if target_p:
                    eb.parent = target_p

        bpy.ops.object.mode_set(mode='OBJECT')

        try:
            bpy.data.objects.remove(backup_arm, do_unlink=True)
        except Exception:
            pass

    # Bind all mesh armature modifiers to rigifyr
    if rigifyr:
        rigifyr.show_in_front = True
        rigifyr.data.display_type = 'STICK'
        for m in meshes:
            for mod in m.modifiers:
                if mod.type == 'ARMATURE':
                    mod.object = rigifyr

    is_version_4 = bpy.app.version[0] >= 4

    char_name = extract_clean_character_name(original_name)
    if rigifyr:
        try:
            if rigifyr.users_collection:
                rigifyr.users_collection[0].name = char_name
        except Exception:
            pass
        rigifyr.name = char_name + "Rig"
    try:
        from setup_wizard.ui.character_settings_utils import stamp_rig_game
        stamp_rig_game(rigifyr, "NEVERNESS_TO_EVERNESS", char_name)
    except Exception:
        pass

    # --- ZZZ parity: varios root (3-tier Genshin convention) + plate/head-controller (EDIT) ---
    if rigifyr:
        context.view_layer.objects.active = rigifyr
        bpy.ops.object.mode_set(mode='EDIT')
        eb = rigifyr.data.edit_bones

        # 3-tier root Genshin/ZZZ: root.002 (rigify interno) -> root.001 (offset) -> root (master)
        try:
            _ensure_root_trio(rigifyr)
        except Exception as ex_root:
            print(f"[NTE RIG] root parenting notice: {ex_root}")

        # inherit_scale ZZZ: padres IK sin escala, torso FULL/AVERAGE
        for _bn, _mode in [("upper_arm_parent.L", "NONE"), ("upper_arm_parent.R", "NONE"),
                           ("thigh_parent.L", "NONE"), ("thigh_parent.R", "NONE")]:
            _e = eb.get(_bn)
            if _e is not None:
                try:
                    _e.inherit_scale = _mode
                except Exception:
                    pass
        for _bn, _mode in [("torso", "FULL"), ("torso-inner", "FULL"), ("torso-outer", "AVERAGE")]:
            _e = eb.get(_bn)
            if _e is not None:
                try:
                    _e.inherit_scale = _mode
                    _e.roll = 0
                except Exception:
                    pass

        # Shoulders limpios a chest como Miyabi (sin damped/follow helpers)
        _spine03 = eb.get("ORG-spine.003") or eb.get("chest") or eb.get("spine_fk.003")
        if _spine03 is not None:
            for _sh in ["shoulder.L", "shoulder.R"]:
                _se = eb.get(_sh)
                if _se is not None:
                    try:
                        _se.parent = _spine03
                    except Exception:
                        pass
        for _sb in ['shoulder_driver.L', 'shoulder_driver.R', 'MCH-shoulder_follow.L', 'MCH-shoulder_follow.R']:
            if _sb in eb:
                try:
                    eb.remove(eb[_sb])
                except Exception:
                    pass

        # plate-settings sobre head (gear de settings) — mínimo: Head/Neck/UseHeadController
        try:
            from mathutils import Vector as _Vec
        except Exception:
            from mathutils import Vector as _Vec
        _head_eb = eb.get("head")
        _head_z = _head_eb.head.z if _head_eb is not None else 1.45
        if 'PROPERTIES' in eb:
            try:
                eb.remove(eb['PROPERTIES'])
            except Exception:
                pass
        _plate = eb.get("plate-settings") or eb.new("plate-settings")
        if _head_eb is not None:
            try:
                _plate.parent = _head_eb
            except Exception:
                pass
        try:
            _plate.head = _Vec((0.0, 0.0, _head_z + 0.35))
            _plate.tail = _Vec((0.0, 0.0, _head_z + 0.45))
            _plate.roll = 0
            _plate.use_deform = False
        except Exception as ex_plate:
            print(f"[NTE RIG] plate-settings edit notice: {ex_plate}")

        # head-controller + MCH parent anti-ciclo (ZZZ)
        _hb = eb.get("head")
        _hp_h2 = _hb.head[2] if _hb is not None else 1.2
        _hp_t2 = _hb.tail[2] if _hb is not None else 1.3
        _hc = eb.get("head-controller") or eb.new("head-controller")
        try:
            _hc.head[0] = 0
            _hc.head[1] = -0.3
            _hc.head[2] = _hp_h2
            _hc.tail[0] = 0
            _hc.tail[1] = -0.3
            _hc.tail[2] = _hp_t2
            _hc.use_deform = False
        except Exception:
            pass
        _mch = eb.get("MCH-head-controller-parent") or eb.new("MCH-head-controller-parent")
        try:
            _mch.head = _hc.head.copy()
            _mch.tail = _hc.head.copy()
            _mch.tail.y += 0.05
            if (_mch.tail - _mch.head).length < 0.01:
                _mch.length = 0.05
            _mch.roll = 0
            _mch.parent = None
            _mch.use_deform = False
            _hc.parent = _mch
        except Exception as ex_mch:
            print(f"[NTE RIG] head-controller edit notice: {ex_mch}")

        bpy.ops.object.mode_set(mode='OBJECT')

    if is_version_4 and rigifyr:
        setup_standard_bone_collections(rigifyr, is_version_4)

        def nte_physics_classifier(armature_obj, b2c_func):
            for bone in armature_obj.data.bones:
                b_name = bone.name
                b_low = b_name.lower()
                # Skip ALL control bones, standard Rigify limbs/fingers, and raw deform/twist/base bones
                if (
                    b_name.startswith("DEF-")
                    or b_name.startswith("ORG-")
                    or b_name.startswith("MCH-")
                    or b_name.startswith("CTRL-")
                    or b_name.startswith("LABEL-")
                    or b_name.startswith("Bon_")
                    or b_name.startswith("BON_")
                    or b_name.startswith("Bone-")
                    or b_name.startswith("Bip")
                    or "tweak" in b_low
                    or "_fk" in b_low
                    or "_ik" in b_low
                    or "master" in b_low
                    or "thumb" in b_low
                    or "f_index" in b_low
                    or "f_middle" in b_low
                    or "f_ring" in b_low
                    or "f_pinky" in b_low
                    or "forearm" in b_low
                    or "upper_arm" in b_low
                    or "thigh" in b_low
                    or "shin" in b_low
                    or "foot" in b_low
                    or "toe" in b_low
                    or "hand" in b_low
                    or "shoulder" in b_low
                    or "spine" in b_low
                    or "torso" in b_low
                    or "head" in b_low
                    or "neck" in b_low
                    or "root" in b_low
                    or "twist" in b_low
                ):
                    continue

                if any(k in b_low for k in ["hair", "headline", "bone00", "ahoge"]):
                    b2c_func(b_name, 20, "Hair")
                elif any(k in b_low for k in ["qun", "skirt", "tail", "xiu", "sleeve", "cloth", "sce", "ribbon", "belt", "strap", "button", "dress"]):
                    b2c_func(b_name, 22, "Clothes")

        distribute_standard_rig_bones(
            rigifyr,
            is_version_4=is_version_4,
            toe_bones_exist=True,
            use_arm_ik_poles=use_arm_ik_poles,
            use_leg_ik_poles=use_leg_ik_poles,
            has_lighting_panel=False,
            physics_bone_callback=nte_physics_classifier,
            detect_prop_keyword=False,
        )

    elif rigifyr:
        for bone in rigifyr.data.bones:
            if bone.name.startswith("DEF-") or bone.name.startswith("ORG-") or bone.name.startswith("MCH-") or "Bn_" in bone.name or "Bone-" in bone.name or "Bip" in bone.name:
                bone.hide = True

    # --- ZZZ parity POSE: plate props + follow drivers + head-controller tracking + childof ---
    if rigifyr:
        context.view_layer.objects.active = rigifyr
        bpy.ops.object.mode_set(mode='POSE')

        def _nte_set_prop(pb_bone, prop_name, default_val, min_val=0.0, max_val=1.0, description=""):
            if not pb_bone:
                return
            if prop_name not in pb_bone:
                pb_bone[prop_name] = default_val
            try:
                pb_bone.id_properties_ui(prop_name).update(
                    default=default_val, min=min_val, max=max_val,
                    soft_min=min_val, soft_max=max_val, description=description)
            except Exception:
                pass

        plate = rigifyr.pose.bones.get("plate-settings")
        if plate is not None:
            gear_obj = None
            for _gb in ["upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L", "thigh_parent.R"]:
                _pg = rigifyr.pose.bones.get(_gb)
                if _pg is not None and getattr(_pg, "custom_shape", None):
                    gear_obj = _pg.custom_shape
                    break
            if gear_obj is None:
                gear_obj = bpy.data.objects.get("setting-circle")
            if gear_obj is not None:
                try:
                    plate.custom_shape = gear_obj
                    plate.use_custom_shape_bone_size = False
                    plate.custom_shape_scale_xyz = (0.05, 0.05, 0.05)
                    plate.custom_shape_rotation_euler = (1.5708, 0.0, 0.0)
                    plate.custom_shape_translation = (0.0, 0.0, 0.0)
                except Exception:
                    pass
            _nte_set_prop(plate, "Head Follow", 1.0, 0.0, 1.0, "Head Follow")
            _nte_set_prop(plate, "Neck Follow", 1.0, 0.0, 1.0, "Neck Follow")
            _nte_set_prop(plate, "Use Head Controller", 1.0 if use_head_tracker else 0.0, 0.0, 1.0, "Use Head Tracker Controller")

        # ZZZ parity (rootrig original): root-outer->"root plate",
        # root-inner->"root plate.001", y el root de Rigify (root.002)->"root plate.002"
        for _rb_name, _shape_name in [("root", "root plate"), ("root.001", "root plate.001"),
                                      ("root.002", "root plate.002")]:
            _pb_r = rigifyr.pose.bones.get(_rb_name)
            _sh_obj = bpy.data.objects.get(_shape_name)
            if _pb_r is not None and _sh_obj is not None:
                try:
                    _pb_r.custom_shape = _sh_obj
                    _pb_r.use_custom_shape_bone_size = False
                except Exception as ex_rsh:
                    print(f"[NTE RIG] root shape notice '{_rb_name}': {ex_rsh}")

        # Created roots copy root.002's color (born after theming with DEFAULT/blue).
        try:
            _r2c = rigifyr.pose.bones.get("root.002")
            if _r2c is not None:
                for _rb_name in ["root", "root.001"]:
                    _pb = rigifyr.pose.bones.get(_rb_name)
                    if _pb is not None and hasattr(_pb, "color"):
                        try:
                            _pb.color.palette = _r2c.color.palette
                            if _r2c.color.palette == 'CUSTOM':
                                _pb.color.custom.normal = tuple(_r2c.color.custom.normal)
                                _pb.color.custom.select = tuple(_r2c.color.custom.select)
                                _pb.color.custom.active = tuple(_r2c.color.custom.active)
                        except Exception:
                            pass
        except Exception as ex_rcol:
            print(f"[NTE RIG] root color notice: {ex_rcol}")

        # torso head_follow/neck_follow -> plate (ZZZ: MCH-ROT retarget a root)
        if rigifyr.animation_data:
            for _fc in list(rigifyr.animation_data.drivers):
                try:
                    for _var in _fc.driver.variables:
                        for _tgt in _var.targets:
                            if _tgt.id == rigifyr and _tgt.data_path:
                                if '["head_follow"]' in _tgt.data_path:
                                    _tgt.data_path = 'pose.bones["plate-settings"]["Head Follow"]'
                                elif '["neck_follow"]' in _tgt.data_path:
                                    _tgt.data_path = 'pose.bones["plate-settings"]["Neck Follow"]'
                except Exception:
                    pass
        _root_bname = "root" if "root" in rigifyr.pose.bones else ("root.002" if "root.002" in rigifyr.pose.bones else "root.001")
        for _rb in ["MCH-ROT-head", "MCH-ROT-neck"]:
            _pb_rot = rigifyr.pose.bones.get(_rb)
            if _pb_rot is not None:
                for _c in _pb_rot.constraints:
                    if _c.type == 'COPY_ROTATION' and _root_bname:
                        try:
                            _c.subtarget = _root_bname
                        except Exception:
                            pass
        for _tn in ["torso", "torso.002"]:
            _pb_t = rigifyr.pose.bones.get(_tn)
            if _pb_t is not None:
                for _prop, _key in [("Head Follow", "head_follow"), ("Neck Follow", "neck_follow")]:
                    try:
                        _d = _pb_t.driver_add(f'["{_key}"]').driver
                        _d.type = 'SCRIPTED'
                        _d.expression = "var"
                        _vh = _d.variables.new()
                        _vh.name = "var"
                        _vh.type = 'SINGLE_PROP'
                        _vh.targets[0].id = rigifyr
                        _vh.targets[0].data_path = f'pose.bones["plate-settings"]["{_prop}"]'
                    except Exception:
                        pass
                try:
                    if "head_follow" in _pb_t:
                        _pb_t["head_follow"] = 1.0
                    if "neck_follow" in _pb_t:
                        _pb_t["neck_follow"] = 1.0
                except Exception:
                    pass

        # head-controller sigue a neck DIRECTO (sin objeto Head_Pole en escena:
        # el empty global se lo robaban entre personajes y quedaba huerfano).
        # Limpieza: se elimina Head_Pole preexistente SOLO si cuelga de este rig
        # (el de ZZZ/otros juegos no se toca).
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            _hp_old = bpy.data.objects.get("Head_Pole")
            if _hp_old is not None and getattr(_hp_old, "parent", None) == rigifyr:
                try:
                    bpy.data.objects.remove(_hp_old, do_unlink=True)
                except Exception:
                    pass
            context.view_layer.objects.active = rigifyr
            bpy.ops.object.mode_set(mode='POSE')
            _head_pb = rigifyr.pose.bones.get("head")
            _hc_pb = rigifyr.pose.bones.get("head-controller")
            if _head_pb is not None and _hc_pb is not None:
                for _c in [c for c in _head_pb.constraints if c.type == 'DAMPED_TRACK']:
                    try:
                        _head_pb.constraints.remove(_c)
                    except Exception:
                        pass
                _dt = _head_pb.constraints.new('DAMPED_TRACK')
                _dt.target = rigifyr
                _dt.subtarget = "head-controller"
                _dt.track_axis = "TRACK_Z"
                try:
                    _drv = _dt.driver_add("influence").driver
                    _drv.type = 'SCRIPTED'
                    _drv.expression = 'bone'
                    _vv = _drv.variables.new()
                    _vv.name = "bone"
                    _vv.type = 'SINGLE_PROP'
                    _vv.targets[0].id = rigifyr
                    _vv.targets[0].data_path = 'pose.bones["plate-settings"]["Use Head Controller"]'
                except Exception:
                    pass
                for _c in [c for c in _hc_pb.constraints if c.type == 'DAMPED_TRACK']:
                    try:
                        _hc_pb.constraints.remove(_c)
                    except Exception:
                        pass
                _dt2 = _hc_pb.constraints.new('DAMPED_TRACK')
                _dt2.target = rigifyr
                _dt2.subtarget = "neck" if "neck" in rigifyr.pose.bones else "head"
                _dt2.head_tail = 0.0
                _dt2.track_axis = "TRACK_NEGATIVE_Z"
                try:
                    _drv2 = _dt2.driver_add("influence").driver
                    _drv2.type = 'SCRIPTED'
                    _drv2.expression = 'bone'
                    _vv2 = _drv2.variables.new()
                    _vv2.name = "bone"
                    _vv2.type = 'SINGLE_PROP'
                    _vv2.targets[0].id = rigifyr
                    _vv2.targets[0].data_path = 'pose.bones["plate-settings"]["Use Head Controller"]'
                except Exception:
                    pass
            # star shape + parent_switch dropdown (ZZZ: head-control-shape manda;
            # primo-joint no existe en escenas ZZZ, queda solo de fallback)
            _star = bpy.data.objects.get("head-control-shape") or bpy.data.objects.get("primo-joint")
            if _hc_pb is not None and _star is not None:
                try:
                    _hc_pb.custom_shape = _star
                    _hc_pb.use_custom_shape_bone_size = False
                    _hc_pb.custom_shape_scale_xyz = (0.035, 0.035, 0.035)
                except Exception:
                    pass
            _switch_items = [("P0", "None", ""), ("P1", "root", ""), ("P2", "root.001", ""),
                             ("P3", "root.002", ""), ("P4", "torso", ""), ("P5", "chest", "")]
            if _hc_pb is not None:
                try:
                    _hc_pb["parent_switch"] = 3
                    _hc_pb.id_properties_ui("parent_switch").update(
                        items=_switch_items, default=3, description="Head Controller Parent")
                except Exception:
                    pass
            _mch_pb = rigifyr.pose.bones.get("MCH-head-controller-parent")
            if _mch_pb is not None and _hc_pb is not None:
                try:
                    _const = _mch_pb.constraints.get("SWITCH PARENT") or _mch_pb.constraints.new('ARMATURE')
                    _const.name = "SWITCH PARENT"
                    while len(_const.targets) < 5:
                        _const.targets.new()
                    # NTE no tiene torso.002 (ese target rompia el grafo con 'Could not
                    #find op_from'); se usa torso. Default P3 = root.002.
                    for _i, _sub in enumerate(["root", "root.001", "root.002", "torso", "chest"]):
                        try:
                            _const.targets[_i].target = rigifyr
                            _const.targets[_i].subtarget = _sub
                        except Exception:
                            pass
                    for _x in range(5):
                        try:
                            _dr = _const.targets[_x].driver_add("weight").driver
                            _vr = _dr.variables.new()
                            _vr.name = "toggle"
                            _vr.type = 'SINGLE_PROP'
                            _vr.targets[0].id = rigifyr
                            _vr.targets[0].data_path = 'pose.bones["head-controller"]["parent_switch"]'
                            _dr.type = 'SCRIPTED'
                            _dr.expression = "toggle == " + str(_x + 1)
                        except Exception:
                            pass
                    _const.enabled = False
                    _const.enabled = True
                except Exception as ex_sw:
                    print(f"[NTE RIG] head parent switch notice: {ex_sw}")
        except Exception as ex_head:
            print(f"[NTE RIG] head-controller pose notice: {ex_head}")
            try:
                context.view_layer.objects.active = rigifyr
                bpy.ops.object.mode_set(mode='POSE')
            except Exception:
                pass

        # ChildOf vacías listas para usar (ZZZ) solo si flag
        if add_child_of_constraints:
            for _cb in ["hand_ik.L", "hand_ik.R", "foot_ik.R", "foot_ik.L", "torso", "root"]:
                _pb_c = rigifyr.pose.bones.get(_cb)
                if _pb_c is not None and not any(c.type == 'CHILD_OF' for c in _pb_c.constraints):
                    try:
                        _pb_c.constraints.new('CHILD_OF')
                    except Exception:
                        pass

        bpy.ops.object.mode_set(mode='OBJECT')

    # Pase final EDIT: re-afirma parenting (head-controller->MCH, plate->head,
    # trio root idempotente). Garantiza el estado final aunque algun paso
    # intermedio haya tocado jerarquias.
    try:
        context.view_layer.objects.active = rigifyr
        bpy.ops.object.mode_set(mode='EDIT')
        _eb2 = rigifyr.data.edit_bones
        _mch2 = _eb2.get("MCH-head-controller-parent")
        _hc2 = _eb2.get("head-controller")
        if _hc2 is not None:
            if _mch2 is None:
                _mch2 = _eb2.new("MCH-head-controller-parent")
                _mch2.head = _hc2.head.copy()
                _mch2.tail = _hc2.head.copy()
                _mch2.tail.y += 0.05
                if (_mch2.tail - _mch2.head).length < 0.01:
                    _mch2.length = 0.05
                _mch2.roll = 0
                _mch2.parent = None
                _mch2.use_deform = False
            if _hc2.parent != _mch2:
                _hc2.parent = _mch2
        _pl2 = _eb2.get("plate-settings")
        _hd2 = _eb2.get("head")
        if _pl2 is not None and _hd2 is not None and _pl2.parent != _hd2:
            _pl2.parent = _hd2
        _ensure_root_trio(rigifyr)
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as ex_par:
        print(f"[NTE RIG] final parenting pass notice: {ex_par}")
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

    # Delete unnecessary utility armatures (metarig) so they don't block Finish Setup
    for extra_arm in ["metarig"]:
        m_obj = bpy.data.objects.get(extra_arm)
        if m_obj:
            try:
                bpy.data.objects.remove(m_obj, do_unlink=True)
            except Exception:
                pass

    # Move widget objects into per-character WGTS_<Char> (Append-safe, no global wgt)
    try:
        from setup_wizard.character_rig_setup.wgts_isolation import isolate_wgts_for_character
        isolate_wgts_for_character(rigifyr, char_name)
    except Exception as e_wgts:
        print(f"[NTE RIG] WGTS isolation notice: {e_wgts}")
        widget_keywords = ["head-control-shape", "root plate", "eye circle", "eye controller", "WGT-"]
        for obj_item in list(bpy.data.objects):
            if any(keyword in obj_item.name for keyword in widget_keywords):
                move_into_collection(obj_item.name, "wgt")
                try:
                    obj_item.hide_viewport = True
                    obj_item.hide_render = True
                except:
                    pass

        wgt_coll = bpy.data.collections.get("wgt")
        if wgt_coll:
            wgt_coll.hide_viewport = True
            wgt_coll.hide_select = True
            wgt_coll.hide_render = True

    # ZZZ parity: root trio + plate en Root, head-controller en Face, visibles
    if rigifyr and hasattr(rigifyr.data, "collections"):
        try:
            _colls = rigifyr.data.collections
            _root_coll = _colls.get("Root") or _colls.new("Root")
            _face_coll = _colls.get("Face") or _colls.new("Face")
            _other_coll = _colls.get("Other")
            for _rn in ["root", "root.001", "root.002", "plate-settings"]:
                _rb = rigifyr.data.bones.get(_rn)
                if _rb is not None:
                    try:
                        _root_coll.assign(_rb)
                    except Exception:
                        pass
                    try:
                        if "Offsets" in _colls:
                            _colls["Offsets"].unassign(_rb)
                        if _other_coll is not None:
                            _other_coll.unassign(_rb)
                        if _rn == "plate-settings" and _face_coll is not None:
                            _face_coll.unassign(_rb)
                    except Exception:
                        pass
            for _fn in ["head-controller", "Face-Root"]:
                _fb = rigifyr.data.bones.get(_fn)
                if _fb is not None and _face_coll is not None:
                    try:
                        _face_coll.assign(_fb)
                    except Exception:
                        pass
            try:
                _root_coll.is_visible = True
                _face_coll.is_visible = True
            except Exception:
                pass
        except Exception as ex_coll:
            print(f"[NTE RIG] root/plate collection notice: {ex_coll}")

    # ZZZ parity: Rigify muestra Neck/Head Follow + Torso Parent al seleccionar
    # neck/head; en ZZZ no aparecen (referencias huerfanas por el rename). Se quitan aqui.
    try:
        _strip_nte_torso_follow_ui(rigifyr, original_name, char_name)
    except Exception as ex_strip:
        print(f"[NTE RIG] torso-follow UI strip notice: {ex_strip}")

    # Update Rigify UI script con sliders plate + head-controller (ZZZ mínimo, sin faldas ni eyetrack)
    _splices = [
        {"divider": "num_rig_separators[0] += 1",
         "text": '\n        if is_selected({"plate-settings"}):\n            layout.prop(pose_bones["plate-settings"], \'["Use Head Controller"]\', text="Use Head Tracker Controller", slider=True)\n            layout.prop(pose_bones["plate-settings"], \'["Head Follow"]\', text="Head Follow", slider=True)\n            layout.prop(pose_bones["plate-settings"], \'["Neck Follow"]\', text="Neck Follow", slider=True)'},
        {"divider": "num_rig_separators[0] += 1",
         "text": '\n        if is_selected({"head-controller"}):\n            layout.prop(pose_bones["plate-settings"], \'["Use Head Controller"]\', text="Use Head Tracker Controller", slider=True)\n        if is_selected({"head"}):\n            layout.prop(pose_bones["plate-settings"], \'["Use Head Controller"]\', text="Use Head Tracker Controller", slider=True)'},
    ]
    try:
        _rig_id_probe = rigifyr.name if rigifyr is not None else original_name
        _hc_probe = rigifyr.pose.bones.get("head-controller") if rigifyr is not None else None
        if _hc_probe is not None:
            try:
                _rid = None
                for _t in bpy.data.texts:
                    try:
                        _s = _t.as_string()
                    except Exception:
                        continue
                    if 'rig_id = "' in _s:
                        _rid = _s.split('rig_id = "')[1].split('"')[0]
                        break
                _rid = _rid or char_name
                _splices.append({"divider": "num_rig_separators[0] += 1",
                    "text": "\n        if is_selected({'head-controller'}):\n            group1 = layout.row(align=True)\n            group2 = group1.split(factor=0.55, align=True)\n            props = group2.operator('pose.rigify_switch_parent_" + _rid + "', text='Parent Switch', icon='DOWNARROW_HLT')\n            props.bone = 'head-controller'\n            props.prop_bone = 'head-controller'\n            props.prop_id='parent_switch'\n            props.parent_names = '[\"None\", \"root\", \"root.001\", \"root.002\", \"torso\", \"chest\"]'\n            props.locks = (False, False, False)\n            group2.prop(pose_bones['head-controller'], '[\"parent_switch\"]', text='')\n            props = group1.operator('pose.rigify_switch_parent_bake_" + _rid + "', text='', icon='ACTION_TWEAK')\n            props.bone = 'head-controller'\n            props.prop_bone='head-controller'\n            props.prop_id='parent_switch'\n            props.parent_names='[\"None\", \"root\", \"root.001\", \"root.002\", \"torso\", \"chest\"]'\n            props.locks = (False, False, False)"})
                # NOTA: parent_names ya usa torso (no torso.002) igual que el constraint.
            except Exception as ex_ps:
                print(f"[NTE RIG] parent-switch splice notice: {ex_ps}")
    except Exception:
        pass
    modify_and_run_rig_ui_script(rigifyr, original_name, char_name=char_name, extra_splices=_splices)


def _ensure_root_trio(rigifyr):
    """Garantiza root/root.001/root.002 con cadena root.002->root.001->root (ZZZ).

    Idempotente: crea el tier que falte (cura rigs parciales/stale) y fuerza
    la jerarquia + props->root.002. Requiere EDIT mode activo en rigifyr.
    """
    if rigifyr is None:
        return
    eb = rigifyr.data.edit_bones
    if "root" in eb and "root.001" not in eb and "root.002" not in eb:
        r0 = eb["root"]
        _h = r0.head.copy()
        _t = r0.tail.copy()
        _rl = r0.roll
        r0.name = "root.002"
        r002 = eb["root.002"]
        e001 = eb.new("root.001")
        e001.head = _h.copy()
        e001.tail = _t.copy()
        e001.roll = _rl
        e001.parent = None
        e000 = eb.new("root")
        e000.head = _h.copy()
        e000.tail = _t.copy()
        e000.roll = _rl
        e000.parent = None
    for _n in ["root.002", "root.001", "root"]:
        if _n not in eb:
            _ref = eb.get("root.002") or eb.get("root.001") or eb.get("root")
            _nb = eb.new(_n)
            if _ref is not None:
                _nb.head = _ref.head.copy()
                _nb.tail = _ref.tail.copy()
                _nb.roll = _ref.roll
            else:
                _nb.head = mathutils.Vector((0.0, 0.0, 0.0))
                _nb.tail = mathutils.Vector((0.0, 0.0, 0.5))
                _nb.roll = 0
            _nb.parent = None
    _r2 = eb.get("root.002")
    _r1 = eb.get("root.001")
    _r0b = eb.get("root")
    if _r2 is not None and _r1 is not None and _r2.parent != _r1:
        _r2.parent = _r1
    if _r1 is not None and _r0b is not None and _r1.parent != _r0b:
        _r1.parent = _r0b
    if _r0b is not None and _r0b.parent is not None:
        _r0b.parent = None
    if _r2 is not None:
        for _pn in ["prop.L", "prop.R"]:
            _ep = eb.get(_pn)
            if _ep is not None and _ep.parent != _r2:
                _ep.parent = _r2


def _strip_nte_torso_follow_ui(rigifyr, original_name, char_name):
    """Quita del rig_ui.py generado las filas de Rigify 'Neck/Head Follow' y el
    bloque 'Torso Parent' sobre pose_bones['torso'].

    En ZZZ esas referencias quedan huerfanas por el rename (torso->torso.002) y no
    aparecen; en NTE el hueso conserva el nombre y el panel las muestra aunque el
    control real ya vive en plate-settings. Solo NTE, no toca otros juegos.
    Se ejecuta ANTES de modify_and_run_rig_ui_script (que relee el texto).
    """
    import re
    candidates = []
    if rigifyr is not None and getattr(rigifyr, "name", ""):
        candidates.append(f"{rigifyr.name}_ui.py")
    candidates += [f"{original_name}_ui.py", f"{char_name}_ui.py",
                   f"{char_name}Rig_ui.py", "rig_ui.py", "metarig_ui.py"]
    rig_file = None
    for _name in candidates:
        if _name in bpy.data.texts:
            rig_file = bpy.data.texts[_name]
            break
    if rig_file is None:
        for _t in bpy.data.texts:
            try:
                _c = _t.as_string()
            except Exception:
                continue
            if "class RigLayers" in _c or "PT_rig_layers" in _c or "rig_id = " in _c:
                rig_file = _t
                break
    if rig_file is None:
        print("[NTE RIG] torso-follow UI strip skipped: no rig ui text found")
        return
    try:
        lines = rig_file.as_string().splitlines()
    except Exception as ex:
        print(f"[NTE RIG] torso-follow UI strip skipped: {ex}")
        return
    removed = []

    # 1. Filas sueltas Neck/Head Follow sobre torso
    kept = []
    for _ln in lines:
        if ("layout.prop" in _ln and "pose_bones['torso']" in _ln
                and ('"neck_follow"' in _ln or '"head_follow"' in _ln)):
            removed.append(_ln.strip()[:90])
            continue
        kept.append(_ln)
    lines = kept

    # 2. Bloque anidado 'Torso Parent' (if is_selected ... hasta 2do props.locks)
    anchor = next((i for i, _ln in enumerate(lines) if "text='Torso Parent'" in _ln), None)
    if anchor is not None:
        start = anchor
        while start > 0 and "if is_selected(" not in lines[start]:
            start -= 1
        locks = 0
        end = None
        for _j in range(anchor, min(len(lines), anchor + 40)):
            if "props.locks = (False, False, False)" in lines[_j]:
                locks += 1
                if locks == 2:
                    end = _j
                    break
        if "if is_selected(" in lines[start] and end is not None and (end - start) < 40:
            removed.append(f"torso-parent block L{start}-{end}")
            del lines[start:end + 1]
        else:
            print("[NTE RIG] torso-parent block guard tripped, kept")

    # 3. Bloques torso huerfanos que solo dejan emit_rig_separator()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        _m = re.match(r"^(\s*)if is_selected\(", lines[i])
        if _m:
            _indent = len(_m.group(1))
            _hdr_end = i
            while _hdr_end < n and not lines[_hdr_end].rstrip().endswith(":"):
                _hdr_end += 1
            if _hdr_end < n and "'torso'" in "\n".join(lines[i:_hdr_end + 1]):
                _j = _hdr_end + 1
                _body = []
                while _j < n and (not lines[_j].strip()
                                  or len(lines[_j]) - len(lines[_j].lstrip()) > _indent):
                    if lines[_j].strip():
                        _body.append(lines[_j].strip())
                    _j += 1
                if _body == ["emit_rig_separator()"]:
                    removed.append("orphan torso if-block")
                    i = _j
                    continue
                out.extend(lines[i:_j])
                i = _j
                continue
        out.append(lines[i])
        i += 1

    if removed:
        try:
            rig_file.clear()
            rig_file.write("\n".join(out) + "\n")
            print(f"[NTE RIG] torso-follow UI stripped: {removed}")
        except Exception as ex:
            print(f"[NTE RIG] torso-follow UI write notice: {ex}")
    else:
        print("[NTE RIG] torso-follow UI strip: nothing matched")


def move_into_collection(object_name, collection_name):
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return
    coll = bpy.data.collections.get(collection_name)
    if not coll:
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)
    for ucoll in list(obj.users_collection):
        ucoll.objects.unlink(obj)
    coll.objects.link(obj)


def use_bone_collections():
    version_tuple = bpy.app.version
    return version_tuple[0] >= 4

