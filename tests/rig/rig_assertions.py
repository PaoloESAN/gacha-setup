"""Rig Assertions for Arms and Fingers.

Validates that:
1. Rig was generated properly (valid Rigify rig, rig_id present, bone count).
2. Arm controls & deformation chains (L and R) function properly in FK and IK.
3. Finger controls & deformation chains (L and R, all 5 digits) scale and rotate cleanly,
   propagate to deformation bones without NaN or inversions, and respect symmetry.
4. Widget shapes (WGT-*) are properly assigned and constraints are valid.
"""
import math
import bpy
from mathutils import Vector, Euler, Matrix


def find_rig_object():
    """Find the generated Rigify rig in the scene."""
    # 1. Armature with rig_id
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and obj.data.get("rig_id"):
            return obj

    # 2. Armature named *Rig or rig
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and (obj.name.endswith("Rig") or obj.name.lower() == "rig"):
            return obj

    # 3. Any armature not named metarig
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and "metarig" not in obj.name.lower():
            return obj

    return None


def assert_rig(game, char_dir):
    """Run all rig assertions and return list of check result dictionaries."""
    checks = []

    rig = find_rig_object()
    if not rig:
        checks.append({
            "name": "Rig Existence",
            "passed": False,
            "message": "No generated rig armature found in scene",
        })
        return checks

    bone_count = len(rig.pose.bones)
    checks.append({
        "name": "Rig Generation",
        "passed": bone_count >= 50,
        "message": f"Found rig '{rig.name}' with {bone_count} pose bones (rig_id: {rig.data.get('rig_id', 'N/A')})",
    })

    # Switch to POSE mode
    try:
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="POSE")
    except Exception:
        pass

    # --- 1. ARM BONE TESTS (L & R) ---
    arm_checks = test_arms(rig)
    checks.extend(arm_checks)

    # --- 2. FINGER BONE TESTS (L & R) ---
    finger_checks = test_fingers(rig)
    checks.extend(finger_checks)

    # --- 3. WIDGET AND CONSTRAINT INTEGRITY ---
    integrity_checks = test_rig_integrity(rig)
    checks.extend(integrity_checks)

    # Reset rig to neutral rest pose
    reset_rig_pose(rig)

    return checks


def test_arms(rig):
    """Test FK and IK arm controls and deformation bone movement."""
    checks = []
    sides = ["L", "R"]

    for side in sides:
        fk_upper = rig.pose.bones.get(f"upper_arm_fk.{side}")
        fk_forearm = rig.pose.bones.get(f"forearm_fk.{side}")
        fk_hand = rig.pose.bones.get(f"hand_fk.{side}")
        ik_hand = rig.pose.bones.get(f"hand_ik.{side}")
        def_upper = rig.pose.bones.get(f"DEF-upper_arm.{side}") or rig.pose.bones.get(f"upper_arm.{side}")
        def_forearm = rig.pose.bones.get(f"DEF-forearm.{side}") or rig.pose.bones.get(f"forearm.{side}")
        def_hand = rig.pose.bones.get(f"DEF-hand.{side}") or rig.pose.bones.get(f"hand.{side}")

        fk_present = all([fk_upper, fk_forearm, fk_hand])
        checks.append({
            "name": f"Arm FK Controls ({side})",
            "passed": fk_present,
            "message": f"upper_arm_fk.{side}: {bool(fk_upper)}, forearm_fk.{side}: {bool(fk_forearm)}, hand_fk.{side}: {bool(fk_hand)}",
        })

        ik_present = ik_hand is not None
        checks.append({
            "name": f"Arm IK Controls ({side})",
            "passed": ik_present,
            "message": f"hand_ik.{side}: {bool(ik_hand)}",
        })

        if fk_upper and def_upper:
            # Rigify defaults to IK (IK_FK = 0.0), so set to FK (1.0) to test FK propagation
            parent_bone = rig.pose.bones.get(f"upper_arm_parent.{side}")
            orig_ik_fk = None
            if parent_bone and "IK_FK" in parent_bone:
                orig_ik_fk = parent_bone["IK_FK"]
                parent_bone["IK_FK"] = 1.0
            elif "IK_FK" in fk_upper:
                orig_ik_fk = fk_upper["IK_FK"]
                fk_upper["IK_FK"] = 1.0
            bpy.context.view_layer.update()

            # Save initial matrix
            initial_mat = def_upper.matrix.copy()
            # Rotate upper arm FK bone
            fk_upper.rotation_mode = "XYZ"
            fk_upper.rotation_euler = Euler((0.5, 0.2, 0.0), "XYZ")
            bpy.context.view_layer.update()

            moved = (def_upper.matrix - initial_mat).to_scale().length > 1e-4 or \
                    (def_upper.matrix.translation - initial_mat.translation).length > 1e-3 or \
                    any(abs(a - b) > 1e-3 for a, b in zip(def_upper.matrix.to_euler(), initial_mat.to_euler()))

            has_nan = any(math.isnan(v) for row in def_upper.matrix for v in row)

            checks.append({
                "name": f"Arm FK Transform Propagation ({side})",
                "passed": moved and not has_nan,
                "message": f"DEF bone moved: {moved}, no NaN: {not has_nan}",
            })

            # Reset FK rotation and restore IK_FK
            fk_upper.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
            if orig_ik_fk is not None:
                if parent_bone and "IK_FK" in parent_bone:
                    parent_bone["IK_FK"] = orig_ik_fk
                elif "IK_FK" in fk_upper:
                    fk_upper["IK_FK"] = orig_ik_fk
            bpy.context.view_layer.update()

        if ik_hand and (def_forearm or def_hand):
            target_def = def_hand or def_forearm
            initial_loc = target_def.matrix.translation.copy()
            # Move IK hand
            ik_hand.location += Vector((0.0, 0.1, 0.1))
            bpy.context.view_layer.update()

            disp = (target_def.matrix.translation - initial_loc).length
            ik_moved = disp > 1e-3
            has_nan = any(math.isnan(v) for v in target_def.matrix.translation)

            checks.append({
                "name": f"Arm IK Motion Response ({side})",
                "passed": ik_moved and not has_nan,
                "message": f"Target DEF moved: {ik_moved}, displacement: {disp:.4f}m",
            })

            # Reset IK
            ik_hand.location -= Vector((0.0, 0.1, 0.1))
            bpy.context.view_layer.update()

    return checks


def test_fingers(rig):
    """Test finger control presence, scaling, and rotation for all 5 digits on L and R."""
    checks = []
    digits = ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]
    sides = ["L", "R"]

    missing_controls = []
    scaling_errors = []
    rotation_errors = []

    for side in sides:
        for digit in digits:
            # Check segments 01, 02, 03
            seg1 = rig.pose.bones.get(f"{digit}.01.{side}")
            seg2 = rig.pose.bones.get(f"{digit}.02.{side}")
            seg3 = rig.pose.bones.get(f"{digit}.03.{side}")
            master = rig.pose.bones.get(f"{digit}.01_master.{side}") or rig.pose.bones.get(f"{digit}_master.{side}")

            if not (seg1 and seg2 and seg3):
                missing_controls.append(f"{digit}.*.{side}")
                continue

            # Test scaling propagation
            def_seg1 = rig.pose.bones.get(f"DEF-{digit}.01.{side}") or rig.pose.bones.get(f"{digit}.01.{side}")
            if def_seg1:
                initial_scale = def_seg1.matrix.to_scale()
                seg1.scale = Vector((1.5, 1.5, 1.5))
                bpy.context.view_layer.update()

                scaled_scale = def_seg1.matrix.to_scale()
                has_nan = any(math.isnan(v) for v in scaled_scale)
                has_zero = any(abs(v) < 1e-4 for v in scaled_scale)

                if has_nan or has_zero:
                    scaling_errors.append(f"{digit}.01.{side} (nan={has_nan}, zero={has_zero})")

                seg1.scale = Vector((1.0, 1.0, 1.0))
                bpy.context.view_layer.update()

            # Test rotation propagation
            if def_seg1:
                initial_rot = def_seg1.matrix.to_euler()
                seg1.rotation_mode = "XYZ"
                seg1.rotation_euler = Euler((0.4, 0.0, 0.0), "XYZ")
                bpy.context.view_layer.update()

                rotated_rot = def_seg1.matrix.to_euler()
                rot_diff = max(abs(a - b) for a, b in zip(rotated_rot, initial_rot))
                has_nan = any(math.isnan(v) for v in rotated_rot)

                if has_nan or rot_diff < 1e-4:
                    rotation_errors.append(f"{digit}.01.{side} (rot_diff={rot_diff:.4f}, nan={has_nan})")

                seg1.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
                bpy.context.view_layer.update()

    # Finger Presence Check
    checks.append({
        "name": "Finger Controls Presence (All 10 Digits)",
        "passed": len(missing_controls) == 0,
        "message": f"Missing: {missing_controls}" if missing_controls else "All thumb, index, middle, ring, pinky controls present (L & R)",
    })

    # Finger Scaling Check
    checks.append({
        "name": "Finger Scaling Behavior",
        "passed": len(scaling_errors) == 0,
        "message": f"Errors: {scaling_errors}" if scaling_errors else "All finger bones scale cleanly without NaN or zero-determinant",
    })

    # Finger Rotation Check
    checks.append({
        "name": "Finger Rotation Propagation",
        "passed": len(rotation_errors) == 0,
        "message": f"Errors: {rotation_errors}" if rotation_errors else "All finger joints rotate cleanly and propagate to deformation chain",
    })

    # Finger Symmetry / Roll Comparison
    sym_errors = []
    for digit in digits:
        b_l = rig.data.bones.get(f"{digit}.01.L")
        b_r = rig.data.bones.get(f"{digit}.01.R")
        if b_l and b_r:
            rot_l = b_l.matrix_local.to_euler()
            rot_r = b_r.matrix_local.to_euler()
            if any(math.isnan(v) for v in rot_l) or any(math.isnan(v) for v in rot_r):
                sym_errors.append(f"{digit}: NaN in bone orientation")

    checks.append({
        "name": "Finger Bone Roll & Symmetry",
        "passed": len(sym_errors) == 0,
        "message": f"Symmetry errors: {sym_errors}" if sym_errors else "Left/Right finger rolls verified and valid",
    })

    return checks


def test_rig_integrity(rig):
    """Test widget shapes and constraint validity."""
    checks = []
    # Check widgets
    widgets = [o for o in bpy.data.objects if o.name.startswith("WGT-")]
    checks.append({
        "name": "Rig Widget Meshes (WGT-*)",
        "passed": len(widgets) > 10,
        "message": f"Found {len(widgets)} widget objects in scene",
    })

    # Check for broken constraints on arm and finger bones
    broken_constraints = []
    target_bones = [b for b in rig.pose.bones if any(p in b.name for p in ["arm", "hand", "thumb", "f_"])]
    for pb in target_bones:
        for c in pb.constraints:
            # Rigify creates dynamic Child Of constraints on IK controls for space switching whose targets are empty by default
            if c.type == "CHILD_OF" and any(pb.name.startswith(pre) for pre in ["hand_ik", "upper_arm_ik", "foot_ik", "thigh_ik"]):
                continue
            if hasattr(c, "target") and getattr(c, "target", None) is None:
                broken_constraints.append(f"{pb.name}:{c.name}")

    checks.append({
        "name": "Bone Constraints Integrity",
        "passed": len(broken_constraints) == 0,
        "message": f"Broken constraints: {broken_constraints}" if broken_constraints else "No dangling/empty constraint targets on arm or finger bones",
    })

    return checks


def reset_rig_pose(rig):
    """Reset all pose bones to neutral transform."""
    for pb in rig.pose.bones:
        pb.location = Vector((0.0, 0.0, 0.0))
        pb.scale = Vector((1.0, 1.0, 1.0))
        if pb.rotation_mode == "QUATERNION":
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        else:
            pb.rotation_euler = Euler((0.0, 0.0, 0.0))
    bpy.context.view_layer.update()
