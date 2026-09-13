# Authors: paoloesan
# Setup Wizard Integration
# Module to unify multi-branch duplicated armatures (e.g. models exported with separate
# sub-model skeleton hierarchies in the same FBX like Stelle in Honkai: Star Rail).

import re
import bpy


def unify_multi_branch_armature(armature_obj):
    """
    Detects and unifies multi-branch armatures resulting from FBX models exported with
    multiple sub-model skeletons (e.g. Stelle in HSR), where duplicate bones are imported
    with .001, .002 suffixes across separate roots (Face, Body, Hair, Weapon, Face_Mask).

    1. Re-parents all non-duplicate children from duplicate bones to canonical base bones.
    2. Removes duplicate bones and intermediate dummy `*_Model` bones.
    3. Re-parents canonical root bone (e.g. Main) directly to the armature root.
    4. Updates/merges vertex groups across all affected meshes to reference canonical bone names.

    Returns:
        bool: True if multi-branch armature was detected and unified, False otherwise.
    """
    if not armature_obj or armature_obj.type != 'ARMATURE':
        return False

    if armature_obj.name not in bpy.context.view_layer.objects:
        return False

    arm = armature_obj.data

    # Never touch already-generated Rigify or control rigs
    if any(b.name.startswith(("DEF-", "MCH-", "ORG-", "WGT-")) for b in arm.bones):
        return False

    # Identify duplicate skeleton bones:
    # A bone matching name.001, name.002 where base 'name' exists in armature
    dup_bone_map = {}  # dup_name -> base_name
    dup_pattern = re.compile(r"^(.+)\.(\d{3})$")

    # Known canonical skeleton bone prefixes / bases to prevent touching non-skeleton bones
    known_skeleton_bases = {
        "main", "root_m", "spine1_m", "spine2_m", "chest_m", "neck_m", "head_m",
        "pelvis_m", "bip001", "bip001 pelvis", "bip001 spine", "bip001 spine1",
        "bip001 spine2", "bip001 neck", "bip001 head"
    }

    for b in arm.bones:
        if b.name.startswith(("DEF-", "MCH-", "ORG-", "WGT-", "ctrl-", "CTRL-", "tweak_")):
            continue
        m = dup_pattern.match(b.name)
        if m:
            base = m.group(1)
            if base in arm.bones and (
                base.lower() in known_skeleton_bases
                or any(k in base.lower() for k in ["root", "spine", "chest", "neck", "head", "main"])
            ):
                dup_bone_map[b.name] = base

    if not dup_bone_map:
        return False

    print(f"[ARMATURE UNIFY] Detected multi-branch duplicate bones: {list(dup_bone_map.keys())}")

    orig_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 1. Update vertex groups on all meshes in scene
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.vertex_groups:
            for dup_name, base_name in dup_bone_map.items():
                vg_dup = obj.vertex_groups.get(dup_name)
                if not vg_dup:
                    continue
                vg_base = obj.vertex_groups.get(base_name)
                if vg_base:
                    # Merge weights from vg_dup into vg_base
                    for v in obj.data.vertices:
                        try:
                            w_dup = vg_dup.weight(v.index)
                        except RuntimeError:
                            continue
                        try:
                            w_base = vg_base.weight(v.index)
                        except RuntimeError:
                            w_base = 0.0
                        vg_base.add([v.index], min(1.0, w_base + w_dup), 'REPLACE')
                    obj.vertex_groups.remove(vg_dup)
                    print(f"[ARMATURE UNIFY] Merged VG '{dup_name}' into '{base_name}' on {obj.name}")
                else:
                    vg_dup.name = base_name
                    print(f"[ARMATURE UNIFY] Renamed VG '{dup_name}' -> '{base_name}' on {obj.name}")

    # 2. In Edit mode, re-parent children of duplicate bones to canonical base bones
    bpy.context.view_layer.objects.active = armature_obj
    armature_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm.edit_bones

    # Find root armature bone (e.g. Art_PlayerGirl_40)
    root_arm_bones = [eb for eb in edit_bones if eb.parent is None]
    art_root_eb = root_arm_bones[0] if root_arm_bones else None

    # Re-parent children of duplicate bones
    for dup_name, base_name in dup_bone_map.items():
        dup_eb = edit_bones.get(dup_name)
        base_eb = edit_bones.get(base_name)
        if not dup_eb or not base_eb:
            continue
        for child in list(dup_eb.children):
            if child.name not in dup_bone_map:
                child.parent = base_eb
                print(f"[ARMATURE UNIFY] Re-parented '{child.name}' to '{base_name}'")

    # If canonical Main bone was parented under a dummy _Model bone, reparent it directly to art_root_eb
    main_eb = edit_bones.get("Main")
    if main_eb and art_root_eb and main_eb.parent != art_root_eb:
        main_eb.parent = art_root_eb
        print(f"[ARMATURE UNIFY] Re-parented 'Main' to '{art_root_eb.name}'")

    # Delete duplicate bones
    for dup_name in dup_bone_map.keys():
        dup_eb = edit_bones.get(dup_name)
        if dup_eb:
            edit_bones.remove(dup_eb)

    # Delete dummy _Model bones
    for eb in list(edit_bones):
        if "_Model" in eb.name:
            edit_bones.remove(eb)

    bpy.ops.object.mode_set(mode='OBJECT')
    try:
        bpy.ops.object.mode_set(mode=orig_mode if orig_mode in ('OBJECT', 'EDIT', 'POSE') else 'OBJECT')
    except Exception:
        pass

    print(f"[ARMATURE UNIFY] Successfully unified multi-branch armature. Remaining bones: {len(arm.bones)}")
    return True
