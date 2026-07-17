### IMPORTANT: Reuses the Genshin Impact rigging script (rig_script.py) in its entirety.
### It maps Honkai Star Rail bone names to Genshin Impact's 'Bip001' style and delegates to rig_script.
### Includes a critical hotfix for Blender 5.x / Animation 2.0 compatibility with Expy-Kit.

import bpy
import os
from setup_wizard.character_rig_setup import rig_script

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

    # Find the active armature object
    if obj is None or obj.type != 'ARMATURE':
        armatures = [o for o in bpy.context.selected_objects if o.type == 'ARMATURE']
        if not armatures:
            armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Rig' not in o.name and o.name != 'metarig']
        if not armatures:
            armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        if armatures:
            obj = armatures[0]
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
        else:
            raise RuntimeError("No armature found. Please select the character's armature and try again.")

    if obj.name.endswith(".001"):
        obj.name = obj.name[:-4]

    # --- BLENDER 5.x COMPATIBILITY HOTFIX FOR EXPY-KIT ---
    # Expy-Kit loops through all actions in bpy.data.actions and checks act.fcurves.
    # In Blender 5.0+ (Animation 2.0), new Actions do not have fcurves directly, causing Expy-Kit to crash.
    # We remove any action that lacks fcurves to prevent this crash.
    print("HSR Rig: Cleaning incompatible Blender 5.x Action objects to prevent Expy-Kit crashes...")
    for act in list(bpy.data.actions):
        try:
            if not hasattr(act, 'fcurves'):
                print(f"Removing incompatible action: {act.name}")
                bpy.data.actions.remove(act)
        except Exception as e:
            print(f"Warning cleaning action {act}: {e}")

    print("HSR Rig: Starting Bone Translation to Genshin (Bip001) naming...")

    # Mapeo de HSR a Genshin (Bip001)
    hsr_to_genshin = {
        'Root_M': 'Bip001 Pelvis',
        'Hip_L': 'Bip001 L Thigh',
        'Knee_L': 'Bip001 L Calf',
        'Ankle_L': 'Bip001 L Foot',
        'Toes_L': 'Bip001 L Toe0',
        'Hip_R': 'Bip001 R Thigh',
        'Knee_R': 'Bip001 R Calf',
        'Ankle_R': 'Bip001 R Foot',
        'Toes_R': 'Bip001 R Toe0',
        'Spine1_M': 'Bip001 Spine',
        'Spine2_M': 'Bip001 Spine1',
        'Chest_M': 'Bip001 Spine2',
        'Scapula_L': 'Bip001 L Clavicle',
        'Shoulder_L': 'Bip001 L UpperArm',
        'Elbow_L': 'Bip001 L Forearm',
        'Wrist_L': 'Bip001 L Hand',
        'Scapula_R': 'Bip001 R Clavicle',
        'Shoulder_R': 'Bip001 R UpperArm',
        'Elbow_R': 'Bip001 R Forearm',
        'Wrist_R': 'Bip001 R Hand',
        'Neck_M': 'Bip001 Neck',
        'Head_M': 'Bip001 Head',
        'breast_L': 'breast.L',
        'breast_R': 'breast.R',
        'eye_L': '+EyeBone L A02',
        'eye_R': '+EyeBone R A02',
        'joint_eye_L': '+EyeBone L A02',
        'joint_eye_R': '+EyeBone R A02',
    }

    # Dedos de la mano
    for side in ['L', 'R']:
        hsr_to_genshin[f'ThumbFinger1_{side}'] = f'Bip001 {side} Finger0'
        hsr_to_genshin[f'ThumbFinger2_{side}'] = f'Bip001 {side} Finger01'
        hsr_to_genshin[f'ThumbFinger3_{side}'] = f'Bip001 {side} Finger02'
        hsr_to_genshin[f'IndexFinger1_{side}'] = f'Bip001 {side} Finger1'
        hsr_to_genshin[f'IndexFinger2_{side}'] = f'Bip001 {side} Finger11'
        hsr_to_genshin[f'IndexFinger3_{side}'] = f'Bip001 {side} Finger12'
        hsr_to_genshin[f'MiddleFinger1_{side}'] = f'Bip001 {side} Finger2'
        hsr_to_genshin[f'MiddleFinger2_{side}'] = f'Bip001 {side} Finger21'
        hsr_to_genshin[f'MiddleFinger3_{side}'] = f'Bip001 {side} Finger22'
        hsr_to_genshin[f'RingFinger1_{side}'] = f'Bip001 {side} Finger3'
        hsr_to_genshin[f'RingFinger2_{side}'] = f'Bip001 {side} Finger31'
        hsr_to_genshin[f'RingFinger3_{side}'] = f'Bip001 {side} Finger32'
        hsr_to_genshin[f'PinkyFinger1_{side}'] = f'Bip001 {side} Finger4'
        hsr_to_genshin[f'PinkyFinger2_{side}'] = f'Bip001 {side} Finger41'
        hsr_to_genshin[f'PinkyFinger3_{side}'] = f'Bip001 {side} Finger42'

    # Entrar a modo EDIT para renombrar y crear los huesos de ojos faltantes
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = obj.data.edit_bones

    # 1. Renombrar huesos existentes en base al mapeo
    for bone in edit_bones:
        if bone.name in hsr_to_genshin:
            bone.name = hsr_to_genshin[bone.name]

    # 2. Crear +EyeBone L A01 y R A01 de soporte detrás de A02 para simular el rig ocular de Genshin
    for side in ['L', 'R']:
        bone_a02_name = f'+EyeBone {side} A02'
        bone_a01_name = f'+EyeBone {side} A01'
        if bone_a02_name in edit_bones and bone_a01_name not in edit_bones:
            bone_a02 = edit_bones[bone_a02_name]
            bone_a01 = edit_bones.new(bone_a01_name)
            
            # Posicionarlo justo detrás del ojo (eje Y en Blender va hacia adelante/atrás)
            bone_a01.head = bone_a02.head.copy()
            bone_a01.head.y -= 0.05  # 5 cm hacia atrás
            bone_a01.tail = bone_a02.head.copy()
            
            # Estructura jerárquica
            if 'Bip001 Head' in edit_bones:
                bone_a01.parent = edit_bones['Bip001 Head']
            bone_a02.parent = bone_a01

    # Regresar a modo OBJECT
    bpy.ops.object.mode_set(mode='OBJECT')

    print("HSR Rig: Bone translation complete. Delegating to Genshin Impact's master rig_script...")

    # Invocar al rig_character de Genshin directamente pasándole los parámetros esperados
    # Nota: El segundo parámetro es la versión del panel de luces, por defecto 4.
    rig_script.rig_character(
        file_path=file_path,
        lighting_panel_version=4,
        disallow_arm_ik_stretch=disallow_arm_ik_stretch,
        disallow_leg_ik_stretch=disallow_leg_ik_stretch,
        use_arm_ik_poles=use_arm_ik_poles,
        use_leg_ik_poles=use_leg_ik_poles,
        add_child_of_constraints=add_child_of_constraints,
        use_head_tracker=use_head_tracker,
        meshes_joined=meshes_joined
    )

    print("HSR Rig: Genshin master rig execution complete.")
