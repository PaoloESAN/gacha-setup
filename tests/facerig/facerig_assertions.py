"""Face Rig Assertions.

Validates that:
1. Face bones and facial controls exist on the generated rig.
2. Eye / Pupil controls and tracking drivers are configured.
3. Mouth controls and phoneme/expression shape keys or drivers exist.
4. Head Driver / Head Origin object is properly constrained to the head bone with Child Of.
"""
import bpy


def assert_facerig(game, char_dir):
    """Run face rig assertions and return check result dictionaries."""
    checks = []

    # 1. Find Rig
    rig = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and (obj.data.get("rig_id") or obj.name.endswith("Rig") or obj.name.lower() == "rig"):
            rig = obj
            break

    if not rig:
        checks.append({
            "name": "Rig Presence for Face Rig",
            "passed": False,
            "message": "No generated rig armature found in scene",
        })
        return checks

    # 2. Face Bones Check
    face_keywords = ["head", "eye", "brow", "mouth", "lip", "jaw", "pupil", "teeth", "tongue", "face"]
    face_bones = [b.name for b in rig.pose.bones if any(k in b.name.lower() for k in face_keywords)]

    checks.append({
        "name": "Face Control Bones Presence",
        "passed": len(face_bones) >= 3,
        "message": f"Identified {len(face_bones)} face/head control bone(s): {face_bones[:8]}...",
    })

    # 3. Eye / Pupil Tracking & Drivers Check
    eye_bones = [b.name for b in rig.pose.bones if "eye" in b.name.lower() or "pupil" in b.name.lower()]
    pupil_drivers = []
    # Check drivers on materials, objects, and shapes
    for mat in bpy.data.materials:
        if mat.node_tree and mat.node_tree.animation_data:
            for d in mat.node_tree.animation_data.drivers:
                if any(k in d.data_path.lower() for k in ["pupil", "eye"]):
                    pupil_drivers.append(f"{mat.name}:{d.data_path}")

    for obj in bpy.data.objects:
        if obj.animation_data:
            for d in obj.animation_data.drivers:
                if any(k in d.data_path.lower() for k in ["pupil", "eye"]):
                    pupil_drivers.append(f"{obj.name}:{d.data_path}")

    has_eye_setup = len(eye_bones) > 0 or len(pupil_drivers) > 0
    checks.append({
        "name": "Eye & Pupil Controls / Drivers",
        "passed": has_eye_setup,
        "message": f"{len(eye_bones)} eye bone(s), {len(pupil_drivers)} pupil driver(s) found",
    })

    # 4. Mouth & Expression Controls
    mouth_bones = [b.name for b in rig.pose.bones if any(k in b.name.lower() for k in ["mouth", "lip", "jaw", "chin"])]
    face_meshes = [o for o in bpy.data.objects if o.type == "MESH" and "face" in o.name.lower()]
    shape_key_count = 0
    for m in face_meshes:
        if m.data.shape_keys and m.data.shape_keys.key_blocks:
            shape_key_count += len(m.data.shape_keys.key_blocks)

    has_mouth_setup = len(mouth_bones) > 0 or shape_key_count > 0
    checks.append({
        "name": "Mouth & Expression Controls",
        "passed": has_mouth_setup,
        "message": f"{len(mouth_bones)} mouth bone(s), {shape_key_count} facial shape key(s) found",
    })

    # 5. Head Driver / Head Origin Object & Child Of Constraint
    head_driver_objs = [
        o for o in bpy.data.objects
        if o.type == "EMPTY" and any(k in o.name.lower() for k in ["head origin", "head driver", "head direction"])
    ]

    has_head_driver = len(head_driver_objs) > 0
    checks.append({
        "name": "Head Driver / Origin Object",
        "passed": has_head_driver,
        "message": f"Found head driver object(s): {[o.name for o in head_driver_objs]}" if has_head_driver else "Head Driver / Origin empty not found",
    })

    if has_head_driver:
        driver_obj = head_driver_objs[0]
        child_of = next((c for c in driver_obj.constraints if c.type == "CHILD_OF"), None)
        has_valid_child_of = (
            child_of is not None
            and child_of.target == rig
            and bool(child_of.subtarget)
            and child_of.subtarget in rig.data.bones
        )
        checks.append({
            "name": "Head Driver Child Of Constraint",
            "passed": has_valid_child_of,
            "message": f"Target: {child_of.target.name if child_of and child_of.target else None}, bone: {child_of.subtarget if child_of else None}"
            if has_valid_child_of
            else f"Child Of constraint missing or invalid on '{driver_obj.name}'",
        })

        if has_valid_child_of:
            bpy.context.view_layer.update()
            head_pbone = rig.pose.bones.get(child_of.subtarget)
            if head_pbone:
                bone_world_pos = rig.matrix_world @ head_pbone.head
                driver_world_pos = driver_obj.matrix_world.to_translation()
                distance = (driver_world_pos - bone_world_pos).length
                # Distance should be near 0 when Child Of inverse_matrix is correctly aligned to head bone
                is_aligned = distance < 0.25
                checks.append({
                    "name": "Head Driver Position Alignment",
                    "passed": is_aligned,
                    "message": f"Distance to head bone '{child_of.subtarget}': {distance:.4f}m (driver: {driver_world_pos.to_tuple(3)}, bone: {bone_world_pos.to_tuple(3)})",
                })

    return checks
