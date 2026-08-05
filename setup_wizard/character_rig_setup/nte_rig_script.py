### IMPORTANT: YOU NEED THE ADDON EXPYKIT AND YOU ALSO NEED TO IMPORT WITH 'Automatic Bone Orientation' TURNED ON UNDER 'Armature' WHEN YOU IMPORT THE FBX.

import bpy

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

    # NTE / Bip001 Bone Mapping to Rigify DEF- Naming
    abadidea = {
        'Bip001-Pelvis': 'DEF-spine',
        'Bip001-Spine': 'DEF-spine.001',
        'Bip001-Spine1': 'DEF-spine.002',
        'Bip001-Spine2': 'DEF-spine.003',
        'Bip001-Neck': 'DEF-spine.004',
        'Bip001-Head': 'DEF-spine.006',

        # Pierna Izquierda
        'Bip001-L-Thigh': 'DEF-thigh.L',
        'Bip001-L-Calf': 'DEF-shin.L',
        'Bip001-L-Foot': 'DEF-foot.L',
        'Bip001-L-Toe0': 'DEF-toe.L',

        # Pierna Derecha
        'Bip001-R-Thigh': 'DEF-thigh.R',
        'Bip001-R-Calf': 'DEF-shin.R',
        'Bip001-R-Foot': 'DEF-foot.R',
        'Bip001-R-Toe0': 'DEF-toe.R',

        # Brazo Izquierdo
        'Bip001-L-Clavicle': 'DEF-shoulder.L',
        'Bip001-L-UpperArm': 'DEF-upper_arm.L',
        'Bip001-L-Forearm': 'DEF-forearm.L',
        'Bip001-L-Hand': 'DEF-hand.L',

        # Brazo Derecho
        'Bip001-R-Clavicle': 'DEF-shoulder.R',
        'Bip001-R-UpperArm': 'DEF-upper_arm.R',
        'Bip001-R-Forearm': 'DEF-forearm.R',
        'Bip001-R-Hand': 'DEF-hand.R',

        # Dedos Mano Izquierda
        'Bip001-L-Finger0': 'DEF-thumb.01.L',
        'Bip001-L-Finger01': 'DEF-thumb.02.L',
        'Bip001-L-Finger02': 'DEF-thumb.03.L',

        'Bip001-L-Finger11': 'DEF-f_index.01.L',
        'Bip001-L-Finger12': 'DEF-f_index.02.L',
        'Bip001-L-Finger13': 'DEF-f_index.03.L',

        'Bip001-L-Finger21': 'DEF-f_middle.01.L',
        'Bip001-L-Finger22': 'DEF-f_middle.02.L',
        'Bip001-L-Finger23': 'DEF-f_middle.03.L',

        'Bip001-L-Finger31': 'DEF-f_ring.01.L',
        'Bip001-L-Finger32': 'DEF-f_ring.02.L',
        'Bip001-L-Finger33': 'DEF-f_ring.03.L',

        'Bip001-L-Finger41': 'DEF-f_pinky.01.L',
        'Bip001-L-Finger42': 'DEF-f_pinky.02.L',
        'Bip001-L-Finger43': 'DEF-f_pinky.03.L',

        # Dedos Mano Derecha
        'Bip001-R-Finger0': 'DEF-thumb.01.R',
        'Bip001-R-Finger01': 'DEF-thumb.02.R',
        'Bip001-R-Finger02': 'DEF-thumb.03.R',

        'Bip001-R-Finger11': 'DEF-f_index.01.R',
        'Bip001-R-Finger12': 'DEF-f_index.02.R',
        'Bip001-R-Finger13': 'DEF-f_index.03.R',

        'Bip001-R-Finger21': 'DEF-f_middle.01.R',
        'Bip001-R-Finger22': 'DEF-f_middle.02.R',
        'Bip001-R-Finger23': 'DEF-f_middle.03.R',

        'Bip001-R-Finger31': 'DEF-f_ring.01.R',
        'Bip001-R-Finger32': 'DEF-f_ring.02.R',
        'Bip001-R-Finger33': 'DEF-f_ring.03.R',

        'Bip001-R-Finger41': 'DEF-f_pinky.01.R',
        'Bip001-R-Finger42': 'DEF-f_pinky.02.R',
        'Bip001-R-Finger43': 'DEF-f_pinky.03.R',

        # Ojos y Pechos
        'eye_R': 'DEF-eye.R',
        'eye_L': 'DEF-eye.L',
        'Bn_l_breast_01': 'DEF-breast.L',
        'Bn_r_breast_01': 'DEF-breast.R',
    }

    # Rename bones FIRST so Blender updates linked vertex groups automatically
    for pb in obj.pose.bones:
        if pb.name in abadidea:
            pb.name = abadidea[pb.name]

    # Rename any leftover vertex groups on meshes
    for m in meshes:
        for vg in m.vertex_groups:
            if vg.name in abadidea:
                target_def = abadidea[vg.name]
                if target_def not in m.vertex_groups:
                    vg.name = target_def

    # Extract Metarig via Expykit
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.expykit_extract_metarig(rig_preset='Rigify_Metarig.py', assign_metarig=True)

    # Generate Rigify with aligned Head bone (halo widget) and centered Breast bones
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

        # Center breast bones on front of chest (more centered and lower down)
        chest_eb = metarig_obj.data.edit_bones.get("spine.003") or metarig_obj.data.edit_bones.get("chest")
        if chest_eb:
            cz = chest_eb.head.z + (chest_eb.tail.z - chest_eb.head.z) * 0.25
            cy = chest_eb.head.y - 0.07

            eb_bl = metarig_obj.data.edit_bones.get("breast.L")
            if eb_bl:
                eb_bl.head.x = 0.050
                eb_bl.head.y = cy
                eb_bl.head.z = cz
                eb_bl.tail.x = 0.050
                eb_bl.tail.y = cy - 0.05
                eb_bl.tail.z = cz

            eb_br = metarig_obj.data.edit_bones.get("breast.R")
            if eb_br:
                eb_br.head.x = -0.050
                eb_br.head.y = cy
                eb_br.head.z = cz
                eb_br.tail.x = -0.050
                eb_br.tail.y = cy - 0.05
                eb_br.tail.z = cz

        # Align hand.L and hand.R metarig bones straight along forearm vector so hand_ik widget is centered on wrist
        for side in [".L", ".R"]:
            forearm_eb = metarig_obj.data.edit_bones.get("forearm" + side)
            hand_eb = metarig_obj.data.edit_bones.get("hand" + side)
            if forearm_eb and hand_eb:
                arm_vec = (forearm_eb.tail - forearm_eb.head).normalized()
                hand_eb.tail = hand_eb.head + arm_vec * 0.05
                hand_eb.roll = forearm_eb.roll

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

    # Adjust custom shape scales in Pose mode for hand_ik and breast controls
    if rigifyr:
        context.view_layer.objects.active = rigifyr
        bpy.ops.object.mode_set(mode='POSE')
        for b_name in ["hand_ik.L", "hand_ik.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                pb.custom_shape_scale_xyz = (0.65, 0.65, 0.65)

        for b_name in ["breast.L", "breast.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                pb.custom_shape_scale_xyz = (0.70, 0.70, 0.70)

        for b_name in ["thigh_parent.L", "thigh_parent.R", "upper_arm_parent.L", "upper_arm_parent.R"]:
            pb = rigifyr.pose.bones.get(b_name)
            if pb:
                pb["IK_Stretch"] = 0.0

        bpy.ops.object.mode_set(mode='OBJECT')


    # Transfer and parent ALL secondary/dynamic bones from backup_arm into rigifyr
    if rigifyr and backup_arm:
        context.view_layer.objects.active = backup_arm
        bpy.ops.object.mode_set(mode='OBJECT')
        
        sec_bones = []
        for b in backup_arm.data.bones:
            if b.name not in abadidea:
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

    if use_bone_collections() and rigifyr:
        hair_coll = rigifyr.data.collections.get("Hair") or rigifyr.data.collections.new("Hair")
        skirt_coll = rigifyr.data.collections.get("Skirt") or rigifyr.data.collections.new("Skirt")
        clothes_coll = rigifyr.data.collections.get("Clothes") or rigifyr.data.collections.new("Clothes")
        face_coll = rigifyr.data.collections.get("Face & Accessories") or rigifyr.data.collections.new("Face & Accessories")
        deform_coll = rigifyr.data.collections.get("Deform & Helpers") or rigifyr.data.collections.new("Deform & Helpers")
        others_coll = rigifyr.data.collections.get("Others") or rigifyr.data.collections.new("Others")
        torso_coll = rigifyr.data.collections.get("Torso") or rigifyr.data.collections.get("Torso (Primary)") or rigifyr.data.collections.new("Torso")

        main_ctrl_keywords = [
            "root", "torso", "hips", "chest", "neck", "head",
            "_ik", "_fk", "_tweak", "ctrl", "master", "pitch", "yaw", "roll"
        ]

        for bone in rigifyr.data.bones:
            b_name = bone.name
            b_low = b_name.lower()

            # Assign ONLY control breast bones (excluding DEF-, ORG-, MCH-) explicitly to Torso collection
            if "breast" in b_low and not (b_name.startswith("DEF-") or b_name.startswith("ORG-") or b_name.startswith("MCH-")):
                try:
                    torso_coll.assign(bone)
                except Exception:
                    pass
                for c in list(bone.collections):
                    if c != torso_coll:
                        try:
                            c.unassign(bone)
                        except Exception:
                            pass
                bone.hide = False
                continue

            # Check if this bone is a main Rigify UI control widget
            is_main_ctrl = any(kw in b_low for kw in main_ctrl_keywords) and not (
                b_name.startswith("DEF-") or b_name.startswith("ORG-") or b_name.startswith("MCH-") or
                "bip" in b_low or "bn_" in b_low or "bone" in b_low or "wq_" in b_low or "root_" in b_low or "_root" in b_low
            )


            if is_main_ctrl:
                continue

            target_coll = others_coll
            if any(k in b_low for k in ["hair", "headline", "bone00"]):
                target_coll = hair_coll
            elif any(k in b_low for k in ["qun", "skirt", "tail"]):
                target_coll = skirt_coll
            elif any(k in b_low for k in ["xiu", "sleeve", "cloth", "sce"]):
                target_coll = clothes_coll
            elif any(k in b_low for k in ["horn", "ear", "ring", "eye", "joint", "face"]):
                target_coll = face_coll
            elif b_name.startswith("DEF-") or b_name.startswith("ORG-") or b_name.startswith("MCH-"):
                target_coll = deform_coll

            try:
                target_coll.assign(bone)
            except Exception:
                pass
            for c in list(bone.collections):
                if c != target_coll:
                    try:
                        c.unassign(bone)
                    except Exception:
                        pass
            bone.hide = True

        # Sync active Rig Layers visibility to EXACT requested list: Face, Torso, Fingers, Arm IK, Leg IK, Root
        exact_visible_names = {
            "Face", "Torso", "Fingers",
            "Arm.L (IK)", "Arm.R (IK)", "Leg.L (IK)", "Leg.R (IK)", "Root",
            "Face (Primary)", "Torso (Primary)", "Fingers (Primary)", "Root (Primary)"
        }
        for coll in rigifyr.data.collections:
            if coll.name in exact_visible_names:
                coll.is_visible = True
            else:
                coll.is_visible = False


    elif rigifyr:
        for bone in rigifyr.data.bones:
            if bone.name.startswith("DEF-") or bone.name.startswith("ORG-") or bone.name.startswith("MCH-") or "Bn_" in bone.name or "Bone-" in bone.name or "Bip" in bone.name:
                bone.hide = True


    for extra_arm in ["metarig"]:
        m_obj = bpy.data.objects.get(extra_arm)
        if m_obj:
            try:
                bpy.data.objects.remove(m_obj, do_unlink=True)
            except Exception:
                pass

    x = original_name.split("_")
    char_name = x[-2] if len(x) >= 2 else original_name
    try:
        if "rigify" in bpy.data.objects:
            bpy.data.objects["rigify"].users_collection[0].name = char_name
            bpy.data.objects["rigify"].name = char_name + "Rig"
    except Exception:
        pass



def use_bone_collections():
    version_tuple = bpy.app.version
    return version_tuple[0] >= 4
