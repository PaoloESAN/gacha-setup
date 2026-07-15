### Rigging script for Zenless Zone Zero character models in Blender

import bpy
import mathutils

def use_bone_collections():
    version_tuple = bpy.app.version
    return version_tuple[0] >= 4

def assign_bone_to_bone_collection(armature, armature_obj, bone, collection_name, collection_idx):
    if use_bone_collections():
        clothes_bone_collection = armature.collections.get(collection_name) if \
            armature.collections.get(collection_name) else armature.collections.new(collection_name)
        clothes_bone_collection.assign(bone)
    else:
        armature_obj.pose.bones[bone.name].bone.layers[collection_idx] = True
        armature_obj.pose.bones[bone.name].bone.layers[0] = False

def assign_root_bone_to_bone_collection(armature, bone, collection_name, collection_idx):
    if use_bone_collections():
        root_bone_collection = armature.collections.get(collection_name) if \
            armature.collections.get(collection_name) else armature.collections.new(collection_name)
        if root_bone_collection:
            root_bone_collection.assign(bone)
    else:
        bpy.ops.pose.group_assign(type=6)
        for x in range(0, 28):
            bone.layers[x] = False
        bone.layers[collection_idx] = True

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
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    
    obj = None
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE' and ("avatar" in ob.name.lower() or "npc" in ob.name.lower()):
            obj = ob
            break
    if not obj:
        armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        if armatures:
            obj = armatures[0]
            
    if not obj:
        obj = bpy.data.objects.get('Armature')

    if not obj:
        raise RuntimeError("No armature found for ZZZ rigging.")

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    if obj.name[-4:] == ".001":
         obj.name = obj.name[:-4]
    
    original_name = obj.name
    
    abadidea = {
        'Bip001 Pelvis': 'spine',
        'Bip001 L Thigh': 'thigh.L',
        'Bip001 L Calf': 'shin.L',
        'Bip001 L Foot': 'foot.L',
        'Bip001 L Toe0': 'toe.L',
        'Bip001 R Thigh': 'thigh.R',
        'Bip001 R Calf': 'shin.R',
        'Bip001 R Foot': 'foot.R',
        'Bip001 R Toe0': 'toe.R',
        'Bip001 Spine': 'spine.001',
        'Bip001 Spine1': 'spine.002',
        'Bip001 Spine2': 'spine.003',
        'Bip001 L Clavicle': 'shoulder.L',
        'Bip001 L UpperArm': 'upper_arm.L',
        'Bip001 L Forearm': 'forearm.L',
        'Bip001 L Hand': 'hand.L',
        'Bip001 L Finger0': 'thumb.01.L',
        'DMZ L 01': 'thumb.01.L',
        'DMZ L 02': 'thumb.02.L',
        'DMZ L 03': 'thumb.03.L',
        'DMZ R 01': 'thumb.01.R',
        'DMZ R 02': 'thumb.02.R',
        'DMZ R 03': 'thumb.03.R',    
        'Bip001 L Finger01': 'thumb.02.L',
        'Bip001 L Finger02': 'thumb.03.L',
        'Bip001 L Finger1': 'f_index.01.L',
        'Bip001 L Finger11': 'f_index.02.L',
        'Bip001 L Finger12': 'f_index.03.L',
        'Bip001 L Finger2': 'f_middle.01.L',
        'Bip001 L Finger21': 'f_middle.02.L',
        'Bip001 L Finger22': 'f_middle.03.L',
        'Bip001 L Finger3': 'f_ring.01.L',
        'Bip001 L Finger31': 'f_ring.02.L',
        'Bip001 L Finger32': 'f_ring.03.L',
        'Bip001 L Finger4': 'f_pinky.01.L',
        'Bip001 L Finger41': 'f_pinky.02.L',
        'Bip001 L Finger42': 'f_pinky.03.L',
        'Bip001 Neck': 'spine.004',
        'Bip001 Head': 'spine.006',
        'Bip001 R Clavicle': 'shoulder.R',
        'Bip001 R UpperArm': 'upper_arm.R',
        'Bip001 R Forearm': 'forearm.R',
        'Bip001 R Hand': 'hand.R',
        'Bip001 R Finger0': 'thumb.01.R',
        'Bip001 R Finger01': 'thumb.02.R',
        'Bip001 R Finger02': 'thumb.03.R',
        'Bip001 R Finger1': 'f_index.01.R',
        'Bip001 R Finger11': 'f_index.02.R',
        'Bip001 R Finger12': 'f_index.03.R',
        'Bip001 R Finger2': 'f_middle.01.R',
        'Bip001 R Finger21': 'f_middle.02.R',
        'Bip001 R Finger22': 'f_middle.03.R',
        'Bip001 R Finger3': 'f_ring.01.R',
        'Bip001 R Finger31': 'f_ring.02.R',
        'Bip001 R Finger32': 'f_ring.03.R',
        'Bip001 R Finger4': 'f_pinky.01.R',
        'Bip001 R Finger41': 'f_pinky.02.R',
        'Bip001 R Finger42': 'f_pinky.03.R',
        'EYE_R': 'eye.R',
        'EYE_L': 'eye.L',   
        'Eye_R': 'eye.R',
        'Eye_L': 'eye.L',   
        'Skn_R_Eye': 'eye.R',   
        'Skn_L_Eye': 'eye.L',   
        'Bdy_R_Eye': 'eye.R',
        'Bdy_L_Eye': 'eye.L',   
        'Bdy_R_Eye_Skin': 'eye.R',
        'Bdy_L_Eye_Skin': 'eye.L',   
        'Skn_R_Highlights': 'Skn_R_Highlights',
        'Skn_L_Highlights': 'Skn_L_Highlights',
        'Skn_R_Pupil': 'eye.R',
        'Skn_L_Pupil': 'eye.L',   
        'Skn_Bn_Eye_R': 'eye.R',
        'Skn_Bn_Eye_L': 'eye.L',   
        'Skn_R_Eye_New': 'eye.R',
        'Skn_L_Eye_New': 'eye.L',
        'Bn_Eye_R': 'eye.R',
        'Bn_Eye_L': 'eye.L',
        'PT_L_Eye': 'eye.L',
        'PT_R_Eye': 'eye.R',
        '+Breast L A01': 'breast.L',
        '+Breast R A01': 'breast.R', 
        'Skn_R_Highlights_New': 'Skn_R_Highlights',
        'Skn_L_Highlights_New': 'Skn_L_Highlights',
    }

    bpy.ops.object.mode_set(mode='EDIT')
    armature = bpy.context.selected_objects[0].data

    bpy.ops.armature.select_all(action='DESELECT')
    def select_bone(bone):
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        
    if "Bip001 Spine" in armature.edit_bones: select_bone(armature.edit_bones["Bip001 Spine"])
    if "Bip001 Spine1" in armature.edit_bones: select_bone(armature.edit_bones["Bip001 Spine1"])
    if "Bip001 Spine2" in armature.edit_bones: select_bone(armature.edit_bones["Bip001 Spine2"])
    try:
        bpy.ops.armature.parent_clear(type='DISCONNECT')
    except:
        pass
    bpy.ops.armature.select_all(action='DESELECT')

    try:
        select_bone(armature.edit_bones["+Breast R A02"])
        select_bone(armature.edit_bones["+Breast L A02"])
        bpy.ops.armature.parent_clear(type='DISCONNECT')
        bpy.ops.armature.select_all(action='DESELECT')
    except:
        pass

    eb = armature.edit_bones
    if "Bip001 L Calf" in eb:
        eb["Bip001 L Calf"].head[1] -= .005
    if "Bip001 R Calf" in eb:
        eb["Bip001 R Calf"].head[1] -= .005

    bones_list = obj.pose.bones
    for bone in bones_list:
        if bone.name in abadidea:
            bone.name = abadidea[bone.name]

    bpy.ops.armature.select_all(action='DESELECT')
    bpy.context.object.data.use_mirror_x = True
    try:
        if "Skn_R_Mouth" in eb: eb["Skn_R_Mouth"].length = 0.04
        if "Skn_L_Mouth" in eb: eb["Skn_L_Mouth"].length = 0.04
        if "Skn_M_Mouth" in eb: eb["Skn_M_Mouth"].length = 0.04
    except:
        pass
    
    if "hand.L" in eb and "forearm.L" in eb:
        if eb["hand.L"].tail[0] <= eb["hand.L"].head[0]:
            eb["hand.L"].length = 0.2
            bone_1 = eb["forearm.L"]
            bone_2 = eb["hand.L"]
            direction = (bone_1.tail - bone_1.head).normalized()
            extended_tail_position = bone_1.tail + (direction * 2.0)
            bone_2.tail = extended_tail_position
            bone_2.length = bone_1.length

    bpy.context.object.data.use_mirror_x = False
    bpy.ops.armature.select_all(action='DESELECT')

    how_not = ['f_index.01.L', 'f_index.02.L', 'f_index.03.L']
    hahaha = ['f_middle.01.L', 'f_middle.02.L', 'f_middle.03.L']
    to_name = ['f_ring.01.L', 'f_ring.02.L', 'f_ring.03.L']
    things_efficiently = ['f_pinky.01.L', 'f_pinky.02.L', 'f_pinky.03.L']

    for bone in how_not:
        if bone in eb: eb[bone].roll -= .1197
    for bone in hahaha:
        if bone in eb: eb[bone].roll -= .04
    for bone in to_name:
        if bone in eb: eb[bone].roll += .1297
    for bone in things_efficiently:
        if bone in eb: eb[bone].roll += .338

    if "shoulder.L" in eb and "shoulder.R" in eb:
        if eb["shoulder.L"].roll > -50 and eb["shoulder.L"].roll < 80:
            eb["shoulder.R"].roll = -eb["shoulder.L"].roll 
        elif eb["shoulder.R"].roll > -80 and eb["shoulder.R"].roll < 50:
            eb["shoulder.L"].roll = -eb["shoulder.R"].roll 
        else:
            eb["shoulder.L"].roll = 0
            eb["shoulder.R"].roll = 0

    for bone in bones_list:
        if ".L" in bone.name: 
            whee = bone.name[:-2] + ".R"
            if whee in eb and bone.name in eb:
                if "f_" in bone.name or "thumb" in bone.name:
                    eb[whee].roll = -eb[bone.name].roll
                else:
                    lefteye = eb.get("eye.L")
                    righteye = eb.get("eye.R")
                    if lefteye and righteye:
                        try:
                            eb[bone.name].roll = -eb[whee].roll
                        except:
                            pass

    for t_bone in ["thumb.01.L", "thumb.02.L", "thumb.03.L"]:
        if t_bone in eb: eb[t_bone].roll += 3.14 / 4
    for t_bone in ["thumb.01.R", "thumb.02.R", "thumb.03.R"]:
        if t_bone in eb: eb[t_bone].roll -= 3.14 / 4

    for bone in eb:
        if "thumb" in bone.name or "index" in bone.name or "middle" in bone.name or "ring" in bone.name or "pinky" in bone.name:
            if ".L" in bone.name:
                bone.roll -= 1.571 
            else:
                bone.roll += 1.571 
        if bone.name == "Bip001": 
            for childbone in bone.children:
                if childbone.name != "spine" and childbone.name in eb:
                    eb[childbone.name].parent = eb['spine'] 
            eb.remove(bone)
        elif ".L" not in bone.name and ".R" not in bone.name:
            bone.roll = 0

    def realign(b_name):
        if b_name in eb:
            eb[b_name].head.x = 0
            eb[b_name].tail.x = 0
    realign('spine')
    realign('spine.006')

    def attachfeets(foot, toe):
        if foot in eb and toe in eb:
            eb[foot].tail.x = eb[toe].head.x
            eb[foot].tail.y = eb[toe].head.y
            eb[foot].tail.z = eb[toe].head.z

    attachfeets('foot.L', 'toe.L')
    attachfeets('foot.R', 'toe.R')
    attachfeets('upper_arm.L', 'forearm.L')
    attachfeets('upper_arm.R', 'forearm.R')
    attachfeets('thigh.L', 'shin.L')
    attachfeets('thigh.R', 'shin.R') 
    attachfeets('forearm.L', 'hand.L')
    attachfeets('forearm.R', 'hand.R')
    attachfeets('spine', 'spine.001')
    attachfeets('spine.001', 'spine.002')
    attachfeets('spine.002', 'spine.003')
    attachfeets('spine.003', 'spine.004')
    attachfeets('spine.004', 'spine.006')

    if 'toe.L' in eb:
        eb['toe.L'].tail.z = 0
        eb['toe.L'].tail.y -= 0.05
    if 'toe.R' in eb:
        eb['toe.R'].tail.z = 0
        eb['toe.R'].tail.y -= 0.05
            
    bpy.ops.armature.select_all(action='DESELECT')
    try:
        select_bone(eb["breast.L"])
        bpy.ops.armature.symmetrize()
        bpy.ops.armature.select_all(action='DESELECT')
    except Exception:
        pass

    try:
        eb["eye.L"].name = "DEF-eye.L"
        eb["eye.R"].name = "DEF-eye.R"
    except:
        pass
    
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.object.expykit_convert_bone_names(src_preset='Rigify_Metarig.py', trg_preset='Rigify_Deform.py')
    bpy.ops.object.expykit_extract_metarig(rig_preset='Rigify_Metarig.py', assign_metarig=True)

    metarm = bpy.data.objects["metarig"].data
    bpy.ops.object.mode_set(mode='EDIT')
    armature = bpy.data.objects[obj.name].data

    def getboob(bone, tip):
        if tip == "head":
            return armature.edit_bones[bone].head.x, armature.edit_bones[bone].head.y, armature.edit_bones[bone].head.z
        else:
            return armature.edit_bones[bone].tail.x, armature.edit_bones[bone].tail.y, armature.edit_bones[bone].tail.z
            
    try:
        xh, yh, zh = getboob("breast.L", "head")
        xt, yt, zt = getboob("breast.L", "tail")

        def fixboob(bone, xh, yh, zh, xt, yt, zt):
            bone.head.x = xh
            bone.head.y = yh
            bone.head.z = zh
            bone.tail.x = xt
            bone.tail.y = yt
            bone.tail.z = zt

        boobL = metarm.edit_bones["breast.L"]
        fixboob(boobL, xh, yh, zh, xt, yt, zt)
        boobR = metarm.edit_bones["breast.R"]
        fixboob(boobR, -xh, yh, zh, -xt, yt, zt)

        boobL.roll = armature.edit_bones["breast.L"].roll
        boobR.roll = -boobL.roll
    except Exception:
        if "breast.L" in metarm.edit_bones: metarm.edit_bones.remove(metarm.edit_bones["breast.L"])
        if "breast.R" in metarm.edit_bones: metarm.edit_bones.remove(metarm.edit_bones["breast.R"])
        
    bpy.ops.object.mode_set(mode='OBJECT')
    metapose = bpy.data.objects['metarig'].pose
    for bone_name in ['f_index', 'f_middle', 'f_ring', 'f_pinky']:
        for side in ['.L', '.R']:
            b_master = metapose.bones.get(f"{bone_name}.01{side}")
            if b_master:
                b_master.rigify_parameters.primary_rotation_axis = 'Z' if side == '.L' else '-Z'
                                                                               
    for side in ['.L', '.R']:
        b_thumb = metapose.bones.get(f"thumb.01{side}")
        if b_thumb:
            b_thumb.rigify_parameters.primary_rotation_axis = 'Z' if side == '.L' else '-Z'

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    armature = obj.data
    for o in bpy.data.objects:
        if o.name in ("metarig", obj.name):
            o.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in metarm.edit_bones:
        if "f_" in bone.name or "thumb" in bone.name:
            def_bone = armature.edit_bones.get("DEF-"+bone.name)
            if def_bone:
                bone.roll = def_bone.roll

    metanames = ['eye.L', 'eye.R', 'spine', 'thigh.L', 'shin.L', 'foot.L', 'toe.L', 'thigh.R', 'shin.R', 'foot.R', 'toe.R', 'spine.001', 'spine.002', 'spine.003', 'breast.L', 'breast.R', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L', 'thumb.01.L', 'thumb.02.L', 'thumb.03.L', 'f_index.01.L', 'f_index.02.L', 'f_index.03.L', 'f_middle.01.L', 'f_middle.02.L', 'f_middle.03.L', 'f_ring.01.L', 'f_ring.02.L', 'f_ring.03.L', 'f_pinky.01.L', 'f_pinky.02.L', 'f_pinky.03.L', 'spine.004', 'spine.006', 'shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R', 'thumb.01.R', 'thumb.02.R', 'thumb.03.R', 'f_index.01.R', 'f_index.02.R', 'f_index.03.R', 'f_middle.01.R', 'f_middle.02.R', 'f_middle.03.R', 'f_ring.01.R', 'f_ring.02.R', 'f_ring.03.R', 'f_pinky.01.R', 'f_pinky.02.R', 'f_pinky.03.R']
    pre_res = ["DEF-" + bonename for bonename in metanames]
    armature = obj.data

    savethechildren = {}
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in armature.edit_bones:
        if bone.name in pre_res:
            childlist = []
            for childbone in armature.edit_bones[bone.name].children:
                if childbone.name not in pre_res:
                    childlist.append(childbone.name)
            if childlist:
                savethechildren[bone.name] = childlist

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.armature.select_all(action='DESELECT')
    bones = armature.edit_bones[:]
    for bone in bones:
        if bone.name not in pre_res:
            bone.select = True
            bone.select_tail = True
            bone.select_head = True

    bpy.ops.armature.separate()
    bpy.ops.pose.rigify_generate()
    bpy.data.objects[obj.name].name = "rigify"

    newrig_obj = bpy.data.objects.get(obj.name + ".001")
    rigifyr = bpy.data.objects.get("rigify")

    if newrig_obj and rigifyr:
        bpy.context.view_layer.objects.active = newrig_obj
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        newrig_obj.select_set(True)
        rigifyr.select_set(True)
        bpy.context.view_layer.objects.active = rigifyr

        obs = [rigifyr, newrig_obj]
        with bpy.context.temp_override(active_object=rigifyr, selected_editable_objects=obs):
            bpy.ops.object.join()
    else:
        if rigifyr:
            bpy.context.view_layer.objects.active = rigifyr
            bpy.ops.object.mode_set(mode='OBJECT')

    bpy.context.view_layer.objects.active = rigifyr
    bpy.ops.object.mode_set(mode='EDIT')

    for mainbone in savethechildren:    
        for childbone in savethechildren[mainbone]:
            if childbone in rigifyr.data.edit_bones:
                rigifyr.data.edit_bones[childbone].parent = rigifyr.data.edit_bones[mainbone]

    # Symmetrize clothes/hair bones
    for bone in rigifyr.data.edit_bones:
        if " L " in bone.name:
            y = bone.name.find(' L ')
            orgname = bone.name
            try:
                oppbone = orgname[:y] + " R " + orgname[y+3:]
                bone.name = orgname[:y] + orgname[y+3:] + ".L"
                if oppbone in rigifyr.data.edit_bones:
                    rigifyr.data.edit_bones[oppbone].name = orgname[:y] + orgname[y+3:] + ".R"
            except:
                pass

    bpy.ops.object.mode_set(mode='POSE')
    for b_name in ["upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L", "thigh_parent.R"]:
        b = rigifyr.pose.bones.get(b_name)
        if b:
            b["pole_parent"] = 2
            b["pole_vector"] = True

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = bpy.data.objects["rigify"]

    listofbones = ["root", "eye.L", "eye.R", "foot_heel_ik.R", "foot_heel_ik.L", "toe_ik.R", "toe_ik.L", "foot_ik.R", "foot_ik.L", "thigh_ik_target.R", "thigh_ik_target.L", "hips", "torso", "chest", "neck", "head", "shoulder.L", "shoulder.R", "upper_arm_fk.L", "upper_arm_fk.R", "forearm_fk.L", "forearm_fk.R", "hand_fk.L", "hand_fk.R", "upper_arm_ik_target.L", "upper_arm_ik_target.R", "hand_ik.R", "hand_ik.L", "Skn_L_Mouth", "Skn_R_Mouth", "Skn_M_Mouth"]
    clothes = ["ribbon", "sleeve", "strap", "skirt", "button", "belt", "cloth", "tail", "bag", "chain", "collar", "cloak", "hat"]
    hair = ["hair", "eardrop", "bangs"]
    face = ["brow", "mouth", "eye", "ear_"]

    eb = obj.pose.bones
    bpy.ops.object.mode_set(mode='POSE')
    
    if not use_bone_collections():
        for bone in listofbones:
            if rigifyr.pose.bones.get(bone):
                rigifyr.pose.bones[bone].bone.layers[1] = True
        for bone in eb:
            for name in clothes:
                if name in bone.name.lower():
                    rigifyr.pose.bones[bone.name].bone.layers[22] = True
                    rigifyr.pose.bones[bone.name].bone.layers[0] = False
            for name in hair:
                if name in bone.name.lower():
                    rigifyr.pose.bones[bone.name].bone.layers[23] = True
                    rigifyr.pose.bones[bone.name].bone.layers[0] = False
    else:
        bone_collection = rigifyr.data.collections.get("Main") or rigifyr.data.collections.new(name="Main")
        for bone_name in listofbones:
            b = rigifyr.pose.bones.get(bone_name)
            if b:
                bone_collection.assign(b)
            
        bpy.ops.pose.select_all(action='DESELECT')
        phys_collection = rigifyr.data.collections.get("Clothes") or rigifyr.data.collections.new(name="Clothes")
        hair_collection = rigifyr.data.collections.get("Hair") or rigifyr.data.collections.new(name="Hair")
        misc_collection = rigifyr.data.collections.get("Misc") or rigifyr.data.collections.new(name="Misc")
        face_collection = rigifyr.data.collections.get("Face") or rigifyr.data.collections.new(name="Face")
        
        for bone in eb:
            assigned = False
            for name in clothes:
                if name in bone.name.lower():
                    phys_collection.assign(bone)
                    assigned = True
                    break
            if not assigned:
                for name in hair:
                    if name in bone.name.lower():
                        hair_collection.assign(bone)
                        assigned = True
                        break
            if not assigned:
                for name in face:
                    if name in bone.name.lower() and "DEF-" not in bone.name and "ORG-" not in bone.name:
                        face_collection.assign(bone)
                        assigned = True
                        break
            if not assigned and not any(bone.name in coll.bones for coll in rigifyr.data.collections if coll.name != "Misc"):
                misc_collection.assign(bone)

        try:
            rigifyr.data.collections_all["Main"].is_visible = True
            for c in rigifyr.data.collections:
                if c.name != "Main":
                    c.is_visible = False
        except:
            pass

    bpy.ops.object.mode_set(mode='OBJECT')
    x = original_name.split("_")
    bpy.data.objects["rigify"].name = x[-1] + "Rig"
    bpy.data.objects[x[-1] + "Rig"].show_in_front = True
