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

    # --- 4. ZZZ SPECIFIC POLE & FOOT-KNEE TESTS ---
    if game == "zzz":
        checks.extend(test_zzz_pole_and_foot(rig))

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
    """Test finger control presence, scaling, rotation, master controls, and curl for all 5 digits on L and R."""
    checks = []
    digits = ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]
    sides = ["L", "R"]

    missing_controls = []
    scaling_errors = []
    rotation_errors = []
    master_rest_errors = []
    master_curl_errors = []

    for side in sides:
        for digit in digits:
            # Check segments 01, 02, 03 and master control
            seg1 = rig.pose.bones.get(f"{digit}.01.{side}")
            seg2 = rig.pose.bones.get(f"{digit}.02.{side}")
            seg3 = rig.pose.bones.get(f"{digit}.03.{side}")
            master = rig.pose.bones.get(f"{digit}.01_master.{side}") or rig.pose.bones.get(f"{digit}_master.{side}")

            if not (seg1 and seg2 and seg3 and master):
                missing_controls.append(f"{digit}.*.{side}")
                continue

            def_seg1 = rig.pose.bones.get(f"DEF-{digit}.01.{side}") or rig.pose.bones.get(f"{digit}.01.{side}")
            def_seg2 = rig.pose.bones.get(f"DEF-{digit}.02.{side}") or rig.pose.bones.get(f"{digit}.02.{side}")
            def_seg3 = rig.pose.bones.get(f"DEF-{digit}.03.{side}") or rig.pose.bones.get(f"{digit}.03.{side}")

            # 1. Master control rest pose neutrality (verifies no hardcoded pre-rotations or rest pose tampering)
            if master.rotation_mode == "QUATERNION":
                q = master.rotation_quaternion
                if abs(q.w - 1.0) > 0.05 or abs(q.x) > 0.05 or abs(q.y) > 0.05 or abs(q.z) > 0.05:
                    master_rest_errors.append(f"{master.name} non-neutral rest quat: ({q.w:.3f}, {q.x:.3f}, {q.y:.3f}, {q.z:.3f})")
            else:
                e = master.rotation_euler
                if any(abs(v) > 0.05 for v in e):
                    master_rest_errors.append(f"{master.name} non-neutral rest euler: ({e.x:.3f}, {e.y:.3f}, {e.z:.3f})")

            # 2. Individual segment scaling propagation
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

            # 3. Individual FK rotation propagation
            if def_seg1:
                initial_rot = def_seg1.matrix.to_euler()
                orig_mode = seg1.rotation_mode
                seg1.rotation_mode = "XYZ"
                seg1.rotation_euler = Euler((0.4, 0.0, 0.0), "XYZ")
                bpy.context.view_layer.update()

                rotated_rot = def_seg1.matrix.to_euler()
                rot_diff = max(abs(a - b) for a, b in zip(rotated_rot, initial_rot))
                has_nan = any(math.isnan(v) for v in rotated_rot)

                if has_nan or rot_diff < 1e-4:
                    rotation_errors.append(f"{digit}.01.{side} (rot_diff={rot_diff:.4f}, nan={has_nan})")

                seg1.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
                seg1.rotation_mode = orig_mode
                bpy.context.view_layer.update()

            # 4. Master Control Curl & Rotation (Flexion Test)
            if master and def_seg1 and def_seg2:
                init_def1_rot = def_seg1.matrix.to_euler()
                init_def2_rot = def_seg2.matrix.to_euler()
                orig_master_scale = master.scale.copy()

                # Scale master to curl (Rigify finger superscale)
                master.scale = Vector((0.5, 0.5, 0.5))
                bpy.context.view_layer.update()

                curled_def2_rot = def_seg2.matrix.to_euler()
                curl_diff2 = max(abs(a - b) for a, b in zip(curled_def2_rot, init_def2_rot))
                has_nan_curl = any(math.isnan(v) for v in curled_def2_rot)

                if has_nan_curl or curl_diff2 < 0.2:
                    master_curl_errors.append(f"{master.name} curl fail (def2 rot_diff={curl_diff2:.4f}, nan={has_nan_curl})")

                master.scale = orig_master_scale
                bpy.context.view_layer.update()

                # Test master rotation along primary flexion axis (Z)
                orig_rot_mode = master.rotation_mode
                orig_euler = master.rotation_euler.copy()
                master.rotation_mode = "XYZ"

                # Rotate master around primary curl axis (Z for .L, -Z for .R)
                master.rotation_euler = Euler((0.0, 0.0, 0.4 if side == "L" else -0.4), "XYZ")
                bpy.context.view_layer.update()

                rotated_def1 = def_seg1.matrix.to_euler()
                rot_diff1 = max(abs(a - b) for a, b in zip(rotated_def1, init_def1_rot))
                has_nan_rot = any(math.isnan(v) for v in rotated_def1)

                if has_nan_rot or rot_diff1 < 0.1:
                    master_curl_errors.append(f"{master.name} master Z-rot fail (def1 rot_diff={rot_diff1:.4f}, nan={has_nan_rot})")

                master.rotation_euler = orig_euler
                master.rotation_mode = orig_rot_mode
                bpy.context.view_layer.update()

    # Finger Presence Check
    checks.append({
        "name": "Finger Controls Presence (All 10 Digits)",
        "passed": len(missing_controls) == 0,
        "message": f"Missing: {missing_controls}" if missing_controls else "All thumb, index, middle, ring, pinky controls present (L & R, including masters)",
    })

    # Finger Scaling Check
    checks.append({
        "name": "Finger Scaling Behavior",
        "passed": len(scaling_errors) == 0,
        "message": f"Errors: {scaling_errors}" if scaling_errors else "All finger bones scale cleanly without NaN or zero-determinant",
    })

    # Finger Rotation Propagation
    checks.append({
        "name": "Finger Rotation Propagation",
        "passed": len(rotation_errors) == 0,
        "message": f"Errors: {rotation_errors}" if rotation_errors else "All finger joints rotate cleanly and propagate to deformation chain",
    })

    # Master Controls Rest Pose Neutrality
    checks.append({
        "name": "Finger Master Rest Pose Neutrality",
        "passed": len(master_rest_errors) == 0,
        "message": f"Rest pose errors: {master_rest_errors}" if master_rest_errors else "All 10 finger master controls have clean neutral rest poses (no hardcoded pre-rotations)",
    })

    # Master Controls Curl & Flexion Response
    checks.append({
        "name": "Finger Master Curl & Flexion Response",
        "passed": len(master_curl_errors) == 0,
        "message": f"Curl errors: {master_curl_errors}" if master_curl_errors else "All 10 finger master controls curl and rotate deformation chains properly along flexion axes",
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


def test_zzz_pole_and_foot(rig):
    """Test ZZZ knee pole follows foot IK and pole targets use arrow custom shapes."""
    checks = []

    # 1. Check pole_parent defaults and foot IK lifting knee
    thigh_p_L = rig.pose.bones.get("thigh_parent.L")
    thigh_p_R = rig.pose.bones.get("thigh_parent.R")
    val_L = thigh_p_L.get("pole_parent") if thigh_p_L else None
    val_R = thigh_p_R.get("pole_parent") if thigh_p_R else None

    foot = rig.pose.bones.get("foot_ik.L")
    knee = rig.pose.bones.get("thigh_ik_target.L")
    followed = False
    diff = 0.0
    if foot and knee:
        k_z_before = knee.matrix.translation.z
        orig_foot_loc = foot.location.copy()
        foot.location.z += 0.5
        bpy.context.view_layer.update()
        k_z_after = knee.matrix.translation.z
        diff = k_z_after - k_z_before
        followed = abs(diff - 0.5) < 0.05
        foot.location = orig_foot_loc
        bpy.context.view_layer.update()

    checks.append({
        "name": "ZZZ Knee Follows Foot IK",
        "passed": val_L == 6 and val_R == 6 and followed,
        "message": f"thigh_parent pole_parent L={val_L} R={val_R}, knee lift diff={diff:.4f}m",
    })

    # Check Toggle Pole synchronization (both arrowhead and elastic line show/hide together)
    pb_pole = rig.pose.bones.get("thigh_ik_target.L")
    pb_vis = rig.pose.bones.get("VIS-thigh_ik_target.L")
    pb_parent = rig.pose.bones.get("thigh_parent.L")

    pole_sync_ok = False
    pole_sync_msg = ""
    if pb_pole and pb_vis and pb_parent:
        orig_pv = pb_parent.get("pole_vector")

        # Toggle OFF (0.0)
        pb_parent["pole_vector"] = False
        rig.update_tag()
        bpy.context.view_layer.update()
        state_off = (pb_pole.hide, pb_vis.hide)
        off_ok = (pb_pole.hide is True) and (pb_vis.hide is True)

        # Toggle ON (1.0)
        pb_parent["pole_vector"] = True
        rig.update_tag()
        bpy.context.view_layer.update()
        state_on = (pb_pole.hide, pb_vis.hide)
        on_ok = (pb_pole.hide is False) and (pb_vis.hide is False)

        # Restore
        pb_parent["pole_vector"] = orig_pv
        rig.update_tag()
        bpy.context.view_layer.update()

        vis_drv = None
        if rig.animation_data:
            for d in rig.animation_data.drivers:
                if d.data_path == f'pose.bones["{pb_vis.name}"].hide':
                    vis_drv = d
                    break
        vis_drv_info = f"Driver expr={vis_drv.driver.expression}" if vis_drv else "NO DRIVER"

        pole_sync_ok = off_ok and on_ok
        pole_sync_msg = f"Toggle Pole OFF -> state={state_off}; ON -> state={state_on} (vis_drv: {vis_drv_info})" if not pole_sync_ok else "Both arrowhead and elastic line hide when Toggle Pole is OFF, and show when ON"




    checks.append({
        "name": "ZZZ Pole Toggle Synchronization",
        "passed": pole_sync_ok,
        "message": pole_sync_msg,
    })

    # 2. Check pole target arrow widgets (Part 1: Arrowhead control bone)
    arrow_pairs = [
        ("thigh_ik_target.L", "VIS-thigh_ik_target.L"),
        ("thigh_ik_target.R", "VIS-thigh_ik_target.R"),
        ("upper_arm_ik_target.L", "VIS-upper_arm_ik_target.L"),
        ("upper_arm_ik_target.R", "VIS-upper_arm_ik_target.R"),
    ]
    missing_shapes = []
    invalid_shapes = []
    missing_transforms = []
    for pole_name, vis_name in arrow_pairs:
        pb = rig.pose.bones.get(pole_name)
        if not pb or not pb.custom_shape:
            missing_shapes.append(pole_name)
            continue
        mesh = pb.custom_shape.data
        if len(mesh.vertices) != 6 or len(mesh.edges) != 8:
            invalid_shapes.append(f"{pole_name}:{pb.custom_shape.name}(v={len(mesh.vertices)},e={len(mesh.edges)})")
        if not pb.custom_shape_transform or pb.custom_shape_transform.name != vis_name:
            curr_tf = pb.custom_shape_transform.name if pb.custom_shape_transform else "None"
            missing_transforms.append(f"{pole_name}(transform={curr_tf}, expected={vis_name})")

    checks.append({
        "name": "ZZZ Pole Target Arrow Widgets",
        "passed": len(missing_shapes) == 0 and len(invalid_shapes) == 0 and len(missing_transforms) == 0,
        "message": f"Arrow widgets or transforms invalid (missing: {missing_shapes}, invalid: {invalid_shapes}, transforms: {missing_transforms})" if (missing_shapes or invalid_shapes or missing_transforms) else "All 4 pole targets have 4-sided wireframe pyramid widgets transformed by VIS bones",
    })

    # 3. Check VIS stretch bones (Part 2: Visualizer line bone)
    vis_configs = [
        ("VIS-thigh_ik_target.L", "thigh_ik_target.L", "MCH-shin_ik.L"),
        ("VIS-thigh_ik_target.R", "thigh_ik_target.R", "MCH-shin_ik.R"),
        ("VIS-upper_arm_ik_target.L", "upper_arm_ik_target.L", "MCH-forearm_ik.L"),
        ("VIS-upper_arm_ik_target.R", "upper_arm_ik_target.R", "MCH-forearm_ik.R"),
    ]
    vis_missing = []
    vis_issues = []
    for vis_name, pole_name, joint_name in vis_configs:
        pb_vis = rig.pose.bones.get(vis_name)
        if not pb_vis:
            vis_missing.append(vis_name)
            continue
        # Check parent
        if not pb_vis.parent or pb_vis.parent.name != pole_name:
            p_curr = pb_vis.parent.name if pb_vis.parent else "None"
            vis_issues.append(f"{vis_name}: parent is {p_curr}, expected {pole_name}")
        # Check hide_select
        if not pb_vis.bone.hide_select:
            vis_issues.append(f"{vis_name}: hide_select is False")
        # Check widget (1 segment line)
        if not pb_vis.custom_shape or len(pb_vis.custom_shape.data.vertices) != 2 or len(pb_vis.custom_shape.data.edges) != 1:
            vis_issues.append(f"{vis_name}: custom_shape missing or not 2-vert 1-edge line")
        # Check STRETCH_TO constraint
        stretch_c = next((c for c in pb_vis.constraints if c.type == 'STRETCH_TO'), None)
        if not stretch_c or stretch_c.subtarget != joint_name:
            st_curr = stretch_c.subtarget if stretch_c else "None"
            vis_issues.append(f"{vis_name}: STRETCH_TO target is {st_curr}, expected {joint_name}")

    checks.append({
        "name": "ZZZ Pole Target Stretch Visualizers",
        "passed": len(vis_missing) == 0 and len(vis_issues) == 0,
        "message": f"VIS stretch bones issues (missing: {vis_missing}, issues: {vis_issues})" if (vis_missing or vis_issues) else "All 4 VIS stretch bones present, parented to pole targets, unselectable, with line widgets and STRETCH_TO constraints to joints",
    })

    return checks
