### IMPORTANT: Reuses the Genshin Impact rigging script (rig_script.py) in its entirety.
### It maps Honkai Star Rail bone names to Genshin Impact's 'Bip001' style and delegates to rig_script.
### Includes a critical hotfix for Blender 5.x / Animation 2.0 compatibility with Expy-Kit.
### Resolves HSR Eye Bone alignment by keeping deform bones inside the sockets and linking them via constraints.

import os
import re

import bpy

from setup_wizard.character_rig_setup import rig_script


def rig_character(
    file_path,
    disallow_arm_ik_stretch,
    disallow_leg_ik_stretch,
    use_arm_ik_poles,
    use_leg_ik_poles,
    add_child_of_constraints,
    use_head_tracker,
    meshes_joined=False,
):

    context = bpy.context
    obj = context.object

    # Find the active armature object
    if obj is None or obj.type != "ARMATURE":
        armatures = [o for o in bpy.context.selected_objects if o.type == "ARMATURE"]
        if not armatures:
            armatures = [
                o
                for o in bpy.data.objects
                if o.type == "ARMATURE" and "Rig" not in o.name and o.name != "metarig"
            ]
        if not armatures:
            armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
        if armatures:
            obj = armatures[0]
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
        else:
            raise RuntimeError(
                "No armature found. Please select the character's armature and try again."
            )

    if obj.name.endswith(".001"):
        obj.name = obj.name[:-4]

    # --- SHAPE KEY RENAMING HOTFIX ---
    print("HSR Rig: Renaming face shape keys to standard Genshin format...")
    for obj_item in bpy.data.objects:
        if (
            obj_item.type == "MESH"
            and "face" in obj_item.name.lower()
            and obj_item.data.shape_keys
        ):
            print(f"  Processing mesh: {obj_item.name}")
            for key in obj_item.data.shape_keys.key_blocks:
                old_name = key.name
                new_name = old_name

                # Replace Mouth_01_ / Mouth_00_ with Mouth_
                new_name = re.sub(r"Mouth_\d+_", "Mouth_", new_name)
                new_name = re.sub(r"Brow_\d+_", "Brow_", new_name)
                new_name = re.sub(r"Eye_\d+_", "Eye_", new_name)

                # Special mapping: Mouth_A -> Mouth_A01
                if new_name == "Mouth_A":
                    new_name = "Mouth_A01"

                if new_name != old_name:
                    print(f"    - Renaming shape key: '{old_name}' -> '{new_name}'")
                    key.name = new_name

    # --- BLENDER 5.x COMPATIBILITY HOTFIX FOR EXPY-KIT ---
    print(
        "HSR Rig: Cleaning incompatible Blender 5.x Action objects to prevent Expy-Kit crashes..."
    )
    for act in list(bpy.data.actions):
        try:
            if not hasattr(act, "fcurves"):
                print(f"Removing incompatible action: {act.name}")
                bpy.data.actions.remove(act)
        except Exception as e:
            print(f"Warning cleaning action {act}: {e}")

    print("HSR Rig: Starting Bone Translation to Genshin (Bip001) naming...")

    # Mapeo de HSR a Genshin (Bip001)
    # NOTE: Deform eye bones must be named with spaces (+EyeBone L A02) to match Genshin's original layout.
    # This prevents collisions with template bones (+EyeBoneA02.L) and keeps eyeballs in the head.
    hsr_to_genshin = {
        "Root_M": "Bip001 Pelvis",
        "Hip_L": "Bip001 L Thigh",
        "Knee_L": "Bip001 L Calf",
        "Ankle_L": "Bip001 L Foot",
        "Toes_L": "Bip001 L Toe0",
        "Hip_R": "Bip001 R Thigh",
        "Knee_R": "Bip001 R Calf",
        "Ankle_R": "Bip001 R Foot",
        "Toes_R": "Bip001 R Toe0",
        "Spine1_M": "Bip001 Spine",
        "Spine2_M": "Bip001 Spine1",
        "Chest_M": "Bip001 Spine2",
        "Scapula_L": "Bip001 L Clavicle",
        "Shoulder_L": "Bip001 L UpperArm",
        "Elbow_L": "Bip001 L Forearm",
        "Wrist_L": "Bip001 L Hand",
        "Scapula_R": "Bip001 R Clavicle",
        "Shoulder_R": "Bip001 R UpperArm",
        "Elbow_R": "Bip001 R Forearm",
        "Wrist_R": "Bip001 R Hand",
        "Neck_M": "Bip001 Neck",
        "Head_M": "Bip001 Head",
        "breast_L": "breast.L",
        "breast_R": "breast.R",
        "eye_L": "+EyeBone L A02",
        "eye_R": "+EyeBone R A02",
        "joint_eye_L": "+EyeBone L A02",
        "joint_eye_R": "+EyeBone R A02",
    }

    # Dedos de la mano
    for side in ["L", "R"]:
        hsr_to_genshin[f"ThumbFinger1_{side}"] = f"Bip001 {side} Finger0"
        hsr_to_genshin[f"ThumbFinger2_{side}"] = f"Bip001 {side} Finger01"
        hsr_to_genshin[f"ThumbFinger3_{side}"] = f"Bip001 {side} Finger02"
        hsr_to_genshin[f"IndexFinger1_{side}"] = f"Bip001 {side} Finger1"
        hsr_to_genshin[f"IndexFinger2_{side}"] = f"Bip001 {side} Finger11"
        hsr_to_genshin[f"IndexFinger3_{side}"] = f"Bip001 {side} Finger12"
        hsr_to_genshin[f"MiddleFinger1_{side}"] = f"Bip001 {side} Finger2"
        hsr_to_genshin[f"MiddleFinger2_{side}"] = f"Bip001 {side} Finger21"
        hsr_to_genshin[f"MiddleFinger3_{side}"] = f"Bip001 {side} Finger22"
        hsr_to_genshin[f"RingFinger1_{side}"] = f"Bip001 {side} Finger3"
        hsr_to_genshin[f"RingFinger2_{side}"] = f"Bip001 {side} Finger31"
        hsr_to_genshin[f"RingFinger3_{side}"] = f"Bip001 {side} Finger32"
        hsr_to_genshin[f"PinkyFinger1_{side}"] = f"Bip001 {side} Finger4"
        hsr_to_genshin[f"PinkyFinger2_{side}"] = f"Bip001 {side} Finger41"
        hsr_to_genshin[f"PinkyFinger3_{side}"] = f"Bip001 {side} Finger42"

    # Entrar a modo EDIT para renombrar y crear los huesos de ojos faltantes
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = obj.data.edit_bones

    # 1. Renombrar huesos existentes en base al mapeo
    for bone in edit_bones:
        if bone.name in hsr_to_genshin:
            bone.name = hsr_to_genshin[bone.name]

    # 2. Crear +EyeBone L A01 y R A01 de soporte.
    # CRITICAL: Both deform bones must share the EXACT head position (the eyeball center).
    # Setting +EyeBone L/R A01's head to the eyeball center and pointing it forward (-Y in Blender)
    # aligns the pivot perfectly, reducing the orbit/rotation offset to zero.
    for side in ["L", "R"]:
        bone_a02_name = f"+EyeBone {side} A02"
        bone_a01_name = f"+EyeBone {side} A01"
        if bone_a02_name in edit_bones and bone_a01_name not in edit_bones:
            bone_a02 = edit_bones[bone_a02_name]
            bone_a01 = edit_bones.new(bone_a01_name)

            # Cabeza (pivote) en el centro exacto del ojo
            bone_a01.head = bone_a02.head.copy()
            # Cola desplazada 3cm hacia adelante (eje Y negativo en Blender)
            bone_a01.tail = bone_a02.head.copy()
            bone_a01.tail.y -= 0.03  # 3 cm hacia adelante

            # Estructura jerárquica
            if "Bip001 Head" in edit_bones:
                bone_a01.parent = edit_bones["Bip001 Head"]
            bone_a02.parent = bone_a01

    # Regresar a modo OBJECT
    bpy.ops.object.mode_set(mode="OBJECT")

    print(
        "HSR Rig: Bone translation complete. Delegating to Genshin Impact's master rig_script..."
    )

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
        meshes_joined=meshes_joined,
    )

    print(
        "HSR Rig: Genshin master rig execution complete. Applying HSR-specific control fixes..."
    )

    # --- HSR FIX: Rotate finger master controls 90° so finger curl axis is correct ---
    rig_obj = bpy.context.active_object
    if rig_obj and rig_obj.type == "ARMATURE":
        try:
            if not rig_obj.get("_hsr_finger_ctrl_rot_fix_v1"):
                bpy.context.view_layer.objects.active = rig_obj
                bpy.ops.object.mode_set(mode="EDIT")

                finger_master_prefixes = [
                    "thumb.01_master",
                    "f_index.01_master",
                    "f_middle.01_master",
                    "f_ring.01_master",
                    "f_pinky.01_master",
                ]

                # Mirror-safe roll offset
                roll_offsets = {
                    ".L": 1.5708,
                    ".R": -1.5708,
                }

                for side, roll_offset in roll_offsets.items():
                    for prefix in finger_master_prefixes:
                        bone_name = f"{prefix}{side}"
                        eb = rig_obj.data.edit_bones.get(bone_name)
                        if eb:
                            eb.roll += roll_offset

                rig_obj["_hsr_finger_ctrl_rot_fix_v1"] = 1
                print("HSR Rig: Finger master controls rotated 90° (HSR fix applied).")

            bpy.ops.object.mode_set(mode="POSE")

            # HSR fix: force finger curl to use Y scale axis (vertical drag behavior)
            finger_tokens = ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]

            def _remap_scale_datapath_to_y(path):
                if not path:
                    return path, False

                original = path
                replacements = {
                    ".scale.x": ".scale.y",
                    ".scale.z": ".scale.y",
                    ".scale[0]": ".scale[1]",
                    ".scale[2]": ".scale[1]",
                }
                for src, dst in replacements.items():
                    if path.endswith(src):
                        path = path[: -len(src)] + dst
                        break

                return path, (path != original)

            if rig_obj.animation_data:
                changed_targets = 0
                changed_transforms = 0

                for drv in rig_obj.animation_data.drivers:
                    drv_path = drv.data_path or ""
                    is_finger_driver = any(tok in drv_path for tok in finger_tokens)

                    for var in drv.driver.variables:
                        for target in var.targets:
                            bone_target = target.bone_target or ""
                            data_path = target.data_path or ""
                            is_finger_target = (
                                any(tok in bone_target for tok in finger_tokens)
                                or any(tok in data_path for tok in finger_tokens)
                                or is_finger_driver
                            )

                            if not is_finger_target:
                                continue

                            # Handle SINGLE_PROP-style target data paths (scale.x / scale[0], etc.)
                            new_path, changed = _remap_scale_datapath_to_y(data_path)
                            if changed:
                                target.data_path = new_path
                                changed_targets += 1

                            # Handle TRANSFORMS-style variables (SCALE_X/SCALE_Z -> SCALE_Y)
                            if var.type == "TRANSFORMS" and target.transform_type in [
                                "SCALE_X",
                                "SCALE_Z",
                            ]:
                                target.transform_type = "SCALE_Y"
                                changed_transforms += 1

                print(
                    "HSR Rig: Finger driver axis remap applied "
                    f"(targets={changed_targets}, transforms={changed_transforms}, ->Y)."
                )

            # Keep only Y scale enabled on finger masters (prevents sideways scaling)
            for pb in rig_obj.pose.bones:
                if ".01_master" in pb.name and any(
                    tok in pb.name for tok in finger_tokens
                ):
                    pb.lock_scale[0] = True
                    pb.lock_scale[1] = False
                    pb.lock_scale[2] = True

            rig_obj["_hsr_finger_scale_axis_fix_v3"] = 1

            # HSR fix: fingertip curl drivers rotate on wrong euler channel (sideways bend)
            if rig_obj.animation_data and not rig_obj.get(
                "_hsr_finger_drv_rot_axis_fix_v1"
            ):
                drv_channel_changes = 0
                for fcu in rig_obj.animation_data.drivers:
                    dpath = fcu.data_path or ""
                    if (
                        "rotation_euler" in dpath
                        and "_drv." in dpath
                        and any(tok in dpath for tok in finger_tokens)
                        and "MCH-" in dpath
                        and fcu.array_index == 0
                    ):
                        # Move from X rot channel to Z rot channel for proper curl plane in HSR
                        fcu.array_index = 2
                        drv_channel_changes += 1

                rig_obj["_hsr_finger_drv_rot_axis_fix_v1"] = 1
                print(
                    f"HSR Rig: Finger driver rotation channel remap applied (X->Z) on {drv_channel_changes} driver(s)."
                )
        except Exception as e:
            print(f"HSR Rig: Finger control rotation fix skipped due to error: {e}")
            try:
                bpy.ops.object.mode_set(mode="POSE")
            except:
                pass

    print("HSR Rig: Linking eye deform bones to controller drivers...")

    # --- POSE MODE CONSTRAINTS TO KEEP EYES IN PLACE AND ROTATING/SCALING PERFECTLY ---
    rig_obj = bpy.context.active_object
    if rig_obj and rig_obj.type == "ARMATURE":
        bpy.ops.object.mode_set(mode="POSE")
        for side in ["L", "R"]:
            deform_bone_name = f"+EyeBone {side} A02"
            control_bone_name = f"+EyeBoneA02.{side}"

            if (
                deform_bone_name in rig_obj.pose.bones
                and control_bone_name in rig_obj.pose.bones
            ):
                deform_bone = rig_obj.pose.bones[deform_bone_name]
                print(
                    f"  Linking HSR deform bone '{deform_bone_name}' to controller '{control_bone_name}'"
                )

                # Clean up existing constraints to avoid duplicates if re-running
                for const in list(deform_bone.constraints):
                    if const.name in ["HSR_Eye_Loc", "HSR_Eye_Rot", "HSR_Eye_Scale"]:
                        deform_bone.constraints.remove(const)

                # Copy Location so blink/wink offsets stay glued to the eye mesh
                loc_const = deform_bone.constraints.new("COPY_LOCATION")
                loc_const.name = "HSR_Eye_Loc"
                loc_const.target = rig_obj
                loc_const.subtarget = control_bone_name
                loc_const.target_space = "POSE"
                loc_const.owner_space = "POSE"
                loc_const.influence = 0.80

                # Copy Rotation from controller (+EyeBoneA02.L/R)
                rot_const = deform_bone.constraints.new("COPY_ROTATION")
                rot_const.name = "HSR_Eye_Rot"
                rot_const.target = rig_obj
                rot_const.subtarget = control_bone_name
                rot_const.target_space = "POSE"
                rot_const.owner_space = "POSE"
                rot_const.influence = 0.85

                # Copy Scale from controller (+EyeBoneA02.L/R) to pass dilation drivers
                scale_const = deform_bone.constraints.new("COPY_SCALE")
                scale_const.name = "HSR_Eye_Scale"
                scale_const.target = rig_obj
                scale_const.subtarget = control_bone_name
                scale_const.target_space = "POSE"
                scale_const.owner_space = "POSE"

        bpy.ops.object.mode_set(mode="OBJECT")

    # HSR: Do NOT drive modifier Realtime (show_viewport) for outlines.
    # Remove any driver linked to outlines show_viewport and leave it manually controllable.
    try:
        if rig_obj and rig_obj.type == "ARMATURE":
            removed_outline_drivers = 0
            for obj_item in bpy.data.objects:
                if obj_item.type == "MESH" and obj_item.parent == rig_obj:
                    for mod in obj_item.modifiers:
                        if "outlines" in mod.name.lower():
                            try:
                                mod.driver_remove("show_viewport")
                                removed_outline_drivers += 1
                            except Exception:
                                pass
                            mod.show_viewport = True

            print(
                f"HSR Rig: Removed {removed_outline_drivers} outline show_viewport driver(s)."
            )
    except Exception as e:
        print(f"HSR Rig: Outline driver cleanup skipped: {e}")

    print("HSR Rig: Eye bone linking complete.")
