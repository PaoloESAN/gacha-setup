# Remielle Special Wing Rig Setup (ZZZ) by Jideeh
# Implements the 6-wing IK/FK + Spread + Procedural Flap rig for Remielle characters
# using only generic/existing Setup Wizard widgets (zero shapes or license bones copied from external files).

import math
import re
import bpy
from mathutils import Vector


# Exact EditBone rolls for all Remielle FK wing bones (ensures identical local axes for WING_spread TRANSFORM constraints)
WING_FK_ROLLS = {
    "Skn_WingC_Root": -1.570795,
    # Wing A (.R)
    "Skn_WingA_YuA_01.R": -2.943377,
    "Skn_WingA_YuA_02.R": -3.086805,
    "Skn_WingA_YuA_03.R": -3.043501,
    "Skn_WingA_YuA_04.R": -2.936610,
    "Skn_WingA_YuB_01.R": 2.853435,
    "Skn_WingA_YuB_02.R": 2.864476,
    "Skn_WingA_YuB_03.R": 2.868890,
    "Skn_WingA_03.R": -2.414900,
    "Skn_WingA_YuC_01.R": 2.467243,
    "Skn_WingA_YuC_02.R": 2.462196,
    "Skn_WingA_02.R": -2.874784,
    "Skn_WingA_YuD_01.R": 2.208375,
    "Skn_WingA_YuD_02.R": 2.226165,
    "Skn_WingA_YuE_01.R": 1.958642,
    "Skn_WingA_01.R": 2.654159,
    "Skn_WingA_YuF_01.R": 1.825664,
    # Wing A (.L)
    "Skn_WingA_01.L": 0.487436,
    "Skn_WingA_YuF_01.L": 1.315931,
    "Skn_WingA_02.L": -0.266807,
    "Skn_WingA_YuD_01.L": 0.933074,
    "Skn_WingA_YuD_02.L": 0.915277,
    "Skn_WingA_YuE_01.L": 1.182954,
    "Skn_WingA_03.L": -0.726690,
    "Skn_WingA_YuC_01.L": 0.674181,
    "Skn_WingA_YuC_02.L": 0.679210,
    "Skn_WingA_YuA_01.L": -0.198211,
    "Skn_WingA_YuA_02.L": -0.054784,
    "Skn_WingA_YuA_03.L": -0.098088,
    "Skn_WingA_YuA_04.L": -0.204980,
    "Skn_WingA_YuB_01.L": 0.288160,
    "Skn_WingA_YuB_02.L": 0.277120,
    "Skn_WingA_YuB_03.L": 0.272705,
    # Wing D (.L)
    "Ctr_WingD_01.L": 0.841860,
    "Ctr_WingD_02.L": 0.657606,
    "Ctr_WingD_03.L": 0.484611,
    "Ctr_WingD_04.L": 0.415076,
    "Ctr_WingD_05.L": 0.294257,
    "Ctr_WingD_06.L": 0.174942,
    "Ctr_WingD_07.L": 1.559745,
    "Ctr_WingD_08.L": 1.481125,
    "Ctr_WingD_09.L": 1.352917,
    "Ctr_WingD_10.L": 1.239254,
    "Ctr_WingD_11.L": 0.985408,
    "Ctr_WingD_12.L": 0.598472,
    # Wing D (.R)
    "Ctr_WingD_01.R": 2.299738,
    "Ctr_WingD_02.R": 2.483993,
    "Ctr_WingD_03.R": 2.656986,
    "Ctr_WingD_04.R": 2.726522,
    "Ctr_WingD_05.R": 2.847341,
    "Ctr_WingD_06.R": 2.966656,
    "Ctr_WingD_07.R": 1.581847,
    "Ctr_WingD_08.R": 1.660467,
    "Ctr_WingD_09.R": 1.788675,
    "Ctr_WingD_10.R": 1.902339,
    "Ctr_WingD_11.R": 2.156185,
    "Ctr_WingD_12.R": 2.543120,
    # Wing C (.R)
    "Skn_WingC_01.R": -3.058974,
    "Skn_WingC_02.R": 3.000120,
    "Skn_WingC_03.R": 3.056123,
    "Skn_WingC_04.R": -3.037846,
    "Skn_WingC_05.R": 3.046008,
    "Skn_WingC_06.R": 1.556753,
    "Skn_WingC_ZH_01.R": 2.740980,
    "Skn_WingC_ZH_02.R": 2.696860,
    "Skn_WingC_ZH_03.R": 2.526126,
    "Skn_WingC_ZF_01.R": 0.808919,
    "Skn_WingC_ZF_02.R": -0.042272,
    "Skn_WingC_ZE_01.R": 1.079011,
    "Skn_WingC_ZE_02.R": 0.663362,
    "Skn_WingC_ZG_01.R": 0.507914,
    "Skn_WingC_ZG_02.R": -0.247446,
    "Skn_WingC_ZA_01.R": 2.562560,
    "Skn_WingC_ZA_02.R": 2.581497,
    "Skn_WingC_ZB_01.R": 2.123952,
    "Skn_WingC_ZB_02.R": 2.438443,
    "Skn_WingC_ZC_01.R": 1.875154,
    "Skn_WingC_ZC_02.R": 2.143834,
    "Skn_WingC_ZD_01.R": 1.636628,
    "Skn_WingC_ZD_02.R": 1.871745,
    # Wing C (.L)
    "Skn_WingC_01.L": -0.082613,
    "Skn_WingC_02.L": 0.141473,
    "Skn_WingC_03.L": 0.085466,
    "Skn_WingC_04.L": -0.103755,
    "Skn_WingC_05.L": 0.095593,
    "Skn_WingC_06.L": 1.574360,
    "Skn_WingC_ZH_01.L": 0.400616,
    "Skn_WingC_ZH_02.L": 0.444737,
    "Skn_WingC_ZH_03.L": 0.615471,
    "Skn_WingC_ZF_01.L": 2.332678,
    "Skn_WingC_ZF_02.L": -3.099317,
    "Skn_WingC_ZE_01.L": 2.062587,
    "Skn_WingC_ZE_02.L": 2.478235,
    "Skn_WingC_ZG_01.L": 2.633684,
    "Skn_WingC_ZG_02.L": -2.894143,
    "Skn_WingC_ZA_01.L": 0.578999,
    "Skn_WingC_ZA_02.L": 0.559989,
    "Skn_WingC_ZB_01.L": 1.017646,
    "Skn_WingC_ZB_02.L": 0.703155,
    "Skn_WingC_ZC_01.L": 1.266443,
    "Skn_WingC_ZC_02.L": 0.997763,
    "Skn_WingC_ZD_01.L": 1.504970,
    "Skn_WingC_ZD_02.L": 1.269853,
    # Clavicle Feathers (.L / .R)
    "Skn_ClaFeather_01.L": 1.176522,
    "Skn_ClaFeather_02.L": 1.271790,
    "Skn_ClaFeather_03.L": 1.403860,
    "Skn_ClaFeather_04.L": 1.141007,
    "Skn_ClaFeather_01.R": 1.965073,
    "Skn_ClaFeather_02.R": 1.869806,
    "Skn_ClaFeather_03.R": 1.737735,
    "Skn_ClaFeather_04.R": 2.000588,
}


# WING_spread TRANSFORM constraint definitions per wing group:
# (base_bone_name, axis_mode, angle_rad)
# axis_mode == 'X': maps local Z rot [-pi, pi] -> local X rot [to_min_x=angle, to_max_x=-angle] for both L and R
# axis_mode == 'Z': maps local Z rot [-pi, pi] -> local Z rot:
#   for .L: [to_min_z=angle, to_max_z=-angle]
#   for .R: [to_min_z=-angle, to_max_z=angle]
WING_SPREAD_SPECS = {
    "wingA": [
        ("Skn_WingA_YuB_01", "X", 3.14159),
        ("Skn_WingA_YuC_01", "X", 2.61300),
        ("Skn_WingA_YuD_01", "X", 2.07952),
        ("Skn_WingA_YuE_01", "X", 1.45374),
        ("Skn_WingA_YuF_01", "X", 0.94248),
    ],
    "wingC": [
        ("Skn_WingC_ZH_01", "X", 1.02559),
        ("Skn_WingC_ZH_02", "X", 1.03277),
        ("Skn_WingC_ZH_03", "X", 0.94248),
        ("Skn_WingC_05", "X", 1.01358),
        ("Skn_WingC_06", "Z", 2.64843),
        ("Skn_WingC_ZF_01", "X", 2.27046),
        ("Skn_WingC_ZE_01", "X", 2.33128),
        ("Skn_WingC_ZG_01", "X", 2.23318),
        ("Skn_WingC_ZB_01", "X", 3.14159),
        ("Skn_WingC_ZC_01", "X", 2.89478),
        ("Skn_WingC_ZD_01", "X", 2.70925),
    ],
    "wingD": [
        ("Ctr_WingD_07", "Z", 0.94248),
        ("Ctr_WingD_08", "Z", 1.21782),
        ("Ctr_WingD_09", "Z", 1.48047),
        ("Ctr_WingD_10", "Z", 1.98026),
        ("Ctr_WingD_11", "X", 2.48967),
        ("Ctr_WingD_12", "X", 3.14159),
    ],
}


def is_remielle_character(armature_obj=None, original_name="", char_name=""):
    """
    Returns True strictly when the target character is Remielle (checks names and wing bone signature).
    """
    for s in (original_name, char_name, getattr(armature_obj, "name", "")):
        if s and "remielle" in s.lower():
            return True

    if armature_obj and getattr(armature_obj, "type", None) == 'ARMATURE' and getattr(armature_obj, "data", None):
        bnames = {b.name for b in armature_obj.data.bones}
        if "Skn_WingC_Root" in bnames and (
            "Skn_L_WingA_01" in bnames or "Skn_WingA_01.L" in bnames
        ):
            return True
    return False


def is_remielle_wing_bone_name(b_name: str) -> bool:
    """
    Returns True if a bone name belongs to the Remielle wing/feather hierarchy
    (so it is never swept into Hair/Clothes physics).
    """
    if not b_name:
        return False
    low = b_name.lower()
    if any(
        k in low
        for k in (
            "winga",
            "wingc",
            "wingd",
            "clafeather",
            "mch-wing",
        )
    ):
        return True
    return False


def _symmetrize_wing_bone_name(b_name: str):
    """
    Converts raw FBX wing/feather bone names from `_L_`/`_R_` infixes to `.L`/`.R` suffixes:
    - Skn_L_WingA_01      -> Skn_WingA_01.L
    - Skn_R_WingC_ZA_01   -> Skn_WingC_ZA_01.R
    - Ctr_L_WingD_01      -> Ctr_WingD_01.L
    - Skn_L_ClaFeather_01 -> Skn_ClaFeather_01.L
    Returns None if no rename is needed.
    """
    m = re.match(r"^(Skn|Ctr)_(L|R)_(WingA_[A-Za-z0-9_]+|WingC_[A-Za-z0-9_]+|WingD_[A-Za-z0-9_]+|ClaFeather_[A-Za-z0-9_]+)$", b_name)
    if m:
        prefix, side, rest = m.groups()
        return f"{prefix}_{rest}.{side}"
    return None


def _rename_wing_bones_and_vertex_groups(armature_obj):
    """
    Renames raw FBX wing bones (`Skn_L_WingA_*` -> `Skn_WingA_*.L`, etc.) on the armature
    and updates matching vertex groups on all meshes bound to `armature_obj`.
    """
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    rename_map = {}
    for b in armature_obj.data.bones:
        new_name = _symmetrize_wing_bone_name(b.name)
        if new_name and new_name != b.name:
            rename_map[b.name] = new_name

    if not rename_map:
        return {}

    for old_name, new_name in rename_map.items():
        b = armature_obj.data.bones.get(old_name)
        if b:
            b.name = new_name

    # Rename matching vertex groups on all meshes deformed by this armature
    for obj in bpy.data.objects:
        if getattr(obj, "type", None) != 'MESH' or not getattr(obj, "vertex_groups", None):
            continue
        is_bound = (obj.parent == armature_obj)
        if not is_bound:
            for mod in getattr(obj, "modifiers", []):
                if getattr(mod, "type", "") == 'ARMATURE' and getattr(mod, "object", None) == armature_obj:
                    is_bound = True
                    break
        if not is_bound:
            continue

        for old_name, new_name in rename_map.items():
            vg = obj.vertex_groups.get(old_name)
            if vg and new_name not in obj.vertex_groups:
                vg.name = new_name

    return rename_map


def _build_remielle_wing_edit_bones(armature_obj):
    """
    In Edit Mode:
    1. Ensures `Skn_WingC_Root` and `Skn_WingA_*` root bones are parented to `DEF-spine.002`,
       and `Skn_ClaFeather_01.L/R` are parented to `DEF-shoulder.L/R`.
    2. Aligns all FK wing bone tails (centroid of FK children heads, or extrapolated along parent->head vector)
       and sets exact rolls from `WING_FK_ROLLS`.
    3. Creates all IK control and MCH mechanism bones for Wing A, Wing C, and Wing D (.L and .R).
    """
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = armature_obj.data.edit_bones

    spine_parent = ebones.get("DEF-spine.002") or ebones.get("spine.002")
    shoulder_l = ebones.get("DEF-shoulder.L") or ebones.get("shoulder.L")
    shoulder_r = ebones.get("DEF-shoulder.R") or ebones.get("shoulder.R")

    # 1. Ensure proper parenting of wing roots
    wingc_root = ebones.get("Skn_WingC_Root")
    if wingc_root and spine_parent:
        wingc_root.parent = spine_parent
        wingc_root.use_connect = False

    for side in ("L", "R"):
        for rname in (f"Skn_WingA_01.{side}", f"Skn_WingA_02.{side}", f"Skn_WingA_03.{side}", f"Skn_WingA_YuA_01.{side}"):
            eb = ebones.get(rname)
            if eb and spine_parent:
                eb.parent = spine_parent
                eb.use_connect = False

        cla_eb = ebones.get(f"Skn_ClaFeather_01.{side}")
        sh_eb = shoulder_l if side == "L" else shoulder_r
        if cla_eb and sh_eb:
            cla_eb.parent = sh_eb
            cla_eb.use_connect = False
            # ClaFeather bones are non-deforming FK controls in RemielleRig (or keep deform if weighted)

    # 2. Align FK wing bone tails and rolls
    fk_wing_names = {
        eb.name
        for eb in ebones
        if eb.name == "Skn_WingC_Root"
        or eb.name.startswith(("Skn_WingA_", "Skn_WingC_", "Ctr_WingD_", "Skn_ClaFeather_"))
    }

    for bname in sorted(fk_wing_names):
        eb = ebones.get(bname)
        if not eb:
            continue
        eb.use_connect = False
        fk_children = [c for c in eb.children if c.name in fk_wing_names]
        if fk_children:
            avg_head = sum((c.head.copy() for c in fk_children), Vector((0.0, 0.0, 0.0))) / len(fk_children)
            if (avg_head - eb.head).length > 1e-5:
                eb.tail = avg_head
        elif eb.parent:
            delta = eb.head - eb.parent.head
            if delta.length > 1e-5:
                eb.tail = eb.head + delta

        if bname in WING_FK_ROLLS:
            eb.roll = WING_FK_ROLLS[bname]

    # Helper to create or reset an EditBone
    def make_eb(name, head, tail, roll, parent_eb, use_connect=False, use_deform=False):
        eb = ebones.get(name) or ebones.new(name)
        eb.head = head.copy()
        eb.tail = tail.copy()
        eb.roll = roll
        eb.parent = parent_eb
        eb.use_connect = use_connect
        eb.use_deform = use_deform
        return eb

    # 3. Create IK & MCH bones for Wing A, Wing C, Wing D (.L and .R)
    for side in ("L", "R"):
        sign = 1.0 if side == "L" else -1.0

        # --- WING A ---
        wa_root_bones = [
            ebones.get(f"Skn_WingA_01.{side}"),
            ebones.get(f"Skn_WingA_02.{side}"),
            ebones.get(f"Skn_WingA_03.{side}"),
            ebones.get(f"Skn_WingA_YuA_01.{side}"),
        ]
        wa_yub03 = ebones.get(f"Skn_WingA_YuB_03.{side}")
        wa_yua04 = ebones.get(f"Skn_WingA_YuA_04.{side}")
        if all(wa_root_bones) and wa_yub03 and wa_yua04 and spine_parent:
            wa_root_head = sum((b.head.copy() for b in wa_root_bones), Vector((0.0, 0.0, 0.0))) / 4.0
            wa_upper_tail = wa_yub03.head.copy()
            wa_lower_tail = wa_yua04.tail.copy()
            wa_root_tail = wa_root_head + (wa_upper_tail - wa_root_head) * 0.600004
            wa_upper_roll = -0.817196 if side == "L" else 0.816924
            wa_lower_roll = -1.131620 if side == "L" else 1.131356
            wa_flap_roll = 1.001530 if side == "L" else -1.001487

            eb_wa_ik_root = make_eb(f"wingA_ik_root.{side}", wa_root_head, wa_root_tail, wa_upper_roll, spine_parent)
            eb_wa_upper = make_eb(f"MCH-wingA_upper.{side}", wa_root_head, wa_upper_tail, wa_upper_roll, eb_wa_ik_root)
            eb_wa_lower = make_eb(f"MCH-wingA_lower.{side}", wa_upper_tail, wa_lower_tail, wa_lower_roll, eb_wa_upper, use_connect=True)

            wa_lower_vec = wa_lower_tail - wa_upper_tail
            make_eb(f"wingA_spread.{side}", wa_upper_tail, wa_upper_tail + wa_lower_vec * 0.406454, wa_lower_roll, eb_wa_lower)

            wa_flap_tail = wa_lower_tail + Vector((sign * (-0.01506), 0.05721, 0.05353))
            eb_wa_flap = make_eb(f"MCH-wingA_flap.{side}", wa_lower_tail, wa_flap_tail, wa_flap_roll, eb_wa_ik_root)
            make_eb(f"wingA_tip.{side}", wa_lower_tail, wa_lower_tail + wa_lower_vec * 0.221682, wa_lower_roll, eb_wa_flap)

            wa_pole_head = wa_upper_tail + Vector((sign * 0.04384, 0.29919, -0.17440))
            make_eb(f"wingA_pole.{side}", wa_pole_head, wa_pole_head + wa_lower_vec * 0.110841, wa_lower_roll, eb_wa_ik_root)

            for src_b in wa_root_bones:
                make_eb(f"MCH-wingA_follow-{src_b.name}.{side}", src_b.head, src_b.tail, src_b.roll, eb_wa_upper)
            for src_name in (f"Skn_WingA_YuA_03.{side}", f"Skn_WingA_YuB_03.{side}"):
                src_b = ebones.get(src_name)
                if src_b:
                    make_eb(f"MCH-wingA_follow-{src_b.name}.{side}", src_b.head, src_b.tail, src_b.roll, eb_wa_lower)

        # --- WING C ---
        wc_root_bones = [
            ebones.get(f"Skn_WingC_01.{side}"),
            ebones.get(f"Skn_WingC_02.{side}"),
            ebones.get(f"Skn_WingC_03.{side}"),
            ebones.get(f"Skn_WingC_04.{side}"),
            ebones.get(f"Skn_WingC_ZA_01.{side}"),
        ]
        wc_zb01 = ebones.get(f"Skn_WingC_ZB_01.{side}")
        wc_za02 = ebones.get(f"Skn_WingC_ZA_02.{side}")
        if all(wc_root_bones) and wc_zb01 and wc_za02 and wingc_root:
            wc_root_head = sum((b.head.copy() for b in wc_root_bones), Vector((0.0, 0.0, 0.0))) / 5.0
            wc_upper_tail = wc_zb01.head.copy()
            wc_lower_tail = wc_za02.tail.copy()
            wc_root_tail = wc_root_head + (wc_upper_tail - wc_root_head) * 0.600000
            wc_upper_roll = -1.476020 if side == "L" else 1.476025
            wc_lower_roll = -0.998364 if side == "L" else 0.998365
            wc_flap_roll = 2.166482 if side == "L" else -2.166481

            eb_wc_ik_root = make_eb(f"wingC_ik_root.{side}", wc_root_head, wc_root_tail, wc_upper_roll, wingc_root)
            eb_wc_upper = make_eb(f"MCH-wingC_upper.{side}", wc_root_head, wc_upper_tail, wc_upper_roll, eb_wc_ik_root)
            eb_wc_lower = make_eb(f"MCH-wingC_lower.{side}", wc_upper_tail, wc_lower_tail, wc_lower_roll, eb_wc_upper, use_connect=True)

            wc_lower_vec = wc_lower_tail - wc_upper_tail
            make_eb(f"wingC_spread.{side}", wc_upper_tail, wc_upper_tail + wc_lower_vec * 0.316931, wc_lower_roll, eb_wc_lower)

            wc_flap_tail = wc_lower_tail + Vector((sign * (-0.00881), 0.14341, 0.00186))
            eb_wc_flap = make_eb(f"MCH-wingC_flap.{side}", wc_lower_tail, wc_flap_tail, wc_flap_roll, eb_wc_ik_root)
            make_eb(f"wingC_tip.{side}", wc_lower_tail, wc_lower_tail + wc_lower_vec * 0.172870, wc_lower_roll, eb_wc_flap)

            wc_pole_head = wc_upper_tail + Vector((sign * 0.25098, 0.11364, 0.56506))
            make_eb(f"wingC_pole.{side}", wc_pole_head, wc_pole_head + wc_lower_vec * 0.086435, wc_lower_roll, eb_wc_ik_root)

            for src_b in wc_root_bones:
                make_eb(f"MCH-wingC_follow-{src_b.name}.{side}", src_b.head, src_b.tail, src_b.roll, eb_wc_upper)
            for src_name in (f"Skn_WingC_ZA_02.{side}", f"Skn_WingC_ZB_01.{side}", f"Skn_WingC_ZC_02.{side}"):
                src_b = ebones.get(src_name)
                if src_b:
                    make_eb(f"MCH-wingC_follow-{src_b.name}.{side}", src_b.head, src_b.tail, src_b.roll, eb_wc_lower)

        # --- WING D ---
        wd_01 = ebones.get(f"Ctr_WingD_01.{side}")
        wd_07 = ebones.get(f"Ctr_WingD_07.{side}")
        wd_06 = ebones.get(f"Ctr_WingD_06.{side}")
        if wd_01 and wd_07 and wd_06 and wingc_root:
            wd_root_head = wd_01.head.copy()
            wd_upper_tail = wd_07.head.copy()
            wd_lower_tail = wd_06.tail.copy()
            wd_root_tail = wd_root_head + (wd_upper_tail - wd_root_head) * 0.599992
            wd_upper_roll = -1.077737 if side == "L" else 1.077712
            wd_lower_roll = -1.340880 if side == "L" else 1.340857
            wd_flap_roll = 1.840184 if side == "L" else -1.840185

            eb_wd_ik_root = make_eb(f"wingD_ik_root.{side}", wd_root_head, wd_root_tail, wd_upper_roll, wingc_root)
            eb_wd_upper = make_eb(f"MCH-wingD_upper.{side}", wd_root_head, wd_upper_tail, wd_upper_roll, eb_wd_ik_root)
            eb_wd_lower = make_eb(f"MCH-wingD_lower.{side}", wd_upper_tail, wd_lower_tail, wd_lower_roll, eb_wd_upper, use_connect=True)

            wd_lower_vec = wd_lower_tail - wd_upper_tail
            make_eb(f"wingD_spread.{side}", wd_upper_tail, wd_upper_tail + wd_lower_vec * 0.301117, wd_lower_roll, eb_wd_lower)

            wd_flap_tail = wd_lower_tail + Vector((sign * (-0.05587), 0.09532, 0.01007))
            eb_wd_flap = make_eb(f"MCH-wingD_flap.{side}", wd_lower_tail, wd_flap_tail, wd_flap_roll, eb_wd_ik_root)
            make_eb(f"wingD_tip.{side}", wd_lower_tail, wd_lower_tail + wd_lower_vec * 0.164246, wd_lower_roll, eb_wd_flap)

            wd_pole_head = wd_upper_tail + Vector((sign * (-0.15989), -0.07943, -0.45136))
            make_eb(f"wingD_pole.{side}", wd_pole_head, wd_pole_head + wd_lower_vec * 0.082123, wd_lower_roll, eb_wd_ik_root)

            make_eb(f"MCH-wingD_follow-{wd_01.name}.{side}", wd_01.head, wd_01.tail, wd_01.roll, eb_wd_upper)
            for src_name in (f"Ctr_WingD_04.{side}", f"Ctr_WingD_07.{side}", f"Ctr_WingD_08.{side}"):
                src_b = ebones.get(src_name)
                if src_b:
                    make_eb(f"MCH-wingD_follow-{src_b.name}.{side}", src_b.head, src_b.tail, src_b.roll, eb_wd_lower)

    bpy.ops.object.mode_set(mode='POSE')


def _setup_remielle_wing_constraints_and_drivers(armature_obj):
    """
    In Pose Mode:
    1. Adds custom properties (`wing_ik`, `flap_amount`, `flap_speed`) on `wing{A,C,D}_ik_root.{L,R}`.
    2. Adds `WING_IK` (IK constraint) on `MCH-wing{A,C,D}_lower.{L,R}`.
    3. Adds `WING_follow` (COPY_TRANSFORMS constraint) on FK wing bones + drivers bound to `wing_ik`.
    4. Adds `WING_spread` (TRANSFORM constraint) on feather bones targeting `wing{A,C,D}_spread.{L,R}`.
    5. Adds procedural sine-wave flap drivers on `MCH-wing{A,C,D}_flap.{L,R}.location[1]`.
    """
    bpy.context.view_layer.objects.active = armature_obj
    if armature_obj.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')

    pbones = armature_obj.pose.bones

    # Remove any pre-existing wing drivers to avoid duplicates on re-runs
    if armature_obj.animation_data:
        for drv in list(armature_obj.animation_data.drivers):
            if any(k in drv.data_path for k in ("WING_follow", "MCH-wingA_flap", "MCH-wingC_flap", "MCH-wingD_flap")):
                try:
                    armature_obj.animation_data.drivers.remove(drv)
                except Exception:
                    pass

    ik_specs = {
        "wingA": {
            "pole_angle": {"L": 2.85823, "R": 0.28308},
            "flap_mult": 0.3491,
            "follow": ["Skn_WingA_01", "Skn_WingA_02", "Skn_WingA_03", "Skn_WingA_YuA_01", "Skn_WingA_YuA_03", "Skn_WingA_YuB_03"],
        },
        "wingC": {
            "pole_angle": {"L": 0.15151, "R": 2.99008},
            "flap_mult": 0.6287,
            "follow": ["Skn_WingC_01", "Skn_WingC_02", "Skn_WingC_03", "Skn_WingC_04", "Skn_WingC_ZA_01", "Skn_WingC_ZA_02", "Skn_WingC_ZB_01", "Skn_WingC_ZC_02"],
        },
        "wingD": {
            "pole_angle": {"L": -3.09039, "R": -0.05123},
            "flap_mult": 0.4854,
            "follow": ["Ctr_WingD_01", "Ctr_WingD_04", "Ctr_WingD_07", "Ctr_WingD_08"],
        },
    }

    for wgrp, spec in ik_specs.items():
        for side in ("L", "R"):
            ik_root_name = f"{wgrp}_ik_root.{side}"
            pb_root = pbones.get(ik_root_name)
            if not pb_root:
                continue

            # 1. Custom properties on wing{A,C,D}_ik_root.{L,R}
            pb_root["wing_ik"] = 1.0
            pb_root["flap_amount"] = 0.0
            pb_root["flap_speed"] = 1.0
            try:
                ui_ik = pb_root.id_properties_ui("wing_ik")
                ui_ik.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, default=1.0, description="Blend between IK (1.0) and FK (0.0)")
                ui_amp = pb_root.id_properties_ui("flap_amount")
                ui_amp.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, default=0.0, description="Procedural wing flap amplitude")
                ui_spd = pb_root.id_properties_ui("flap_speed")
                ui_spd.update(min=0.0, max=10.0, soft_min=0.0, soft_max=5.0, default=1.0, description="Procedural wing flap speed")
            except Exception:
                pass

            # 2. IK constraint on MCH-wing*_lower.{side}
            pb_lower = pbones.get(f"MCH-{wgrp}_lower.{side}")
            if pb_lower:
                for c in list(pb_lower.constraints):
                    if c.name == "WING_IK":
                        pb_lower.constraints.remove(c)
                c_ik = pb_lower.constraints.new('IK')
                c_ik.name = "WING_IK"
                c_ik.target = armature_obj
                c_ik.subtarget = f"{wgrp}_tip.{side}"
                c_ik.pole_target = armature_obj
                c_ik.pole_subtarget = f"{wgrp}_pole.{side}"
                c_ik.chain_count = 2
                c_ik.use_stretch = False
                c_ik.pole_angle = spec["pole_angle"][side]

            # 3. Follow COPY_TRANSFORMS constraints + wing_ik driver
            for base_bname in spec["follow"]:
                fk_bname = f"{base_bname}.{side}"
                mch_bname = f"MCH-{wgrp}_follow-{fk_bname}.{side}"
                pb_fk = pbones.get(fk_bname)
                if not pb_fk or mch_bname not in pbones:
                    continue
                for c in list(pb_fk.constraints):
                    if c.name == "WING_follow":
                        pb_fk.constraints.remove(c)
                c_fol = pb_fk.constraints.new('COPY_TRANSFORMS')
                c_fol.name = "WING_follow"
                c_fol.target = armature_obj
                c_fol.subtarget = mch_bname
                c_fol.owner_space = 'WORLD'
                c_fol.target_space = 'WORLD'
                c_fol.mix_mode = 'REPLACE'
                c_fol.influence = 1.0

                try:
                    fcurve = c_fol.driver_add("influence")
                    drv = fcurve.driver
                    drv.type = 'SCRIPTED'
                    drv.expression = "ik"
                    var = drv.variables.new()
                    var.name = "ik"
                    var.type = 'SINGLE_PROP'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{ik_root_name}"]["wing_ik"]'
                except Exception as e_drv:
                    print(f"[REMIELLE WINGS] Driver warning on {fk_bname}: {e_drv}")

            # 4. Spread TRANSFORM constraints
            spread_target_name = f"{wgrp}_spread.{side}"
            for base_bname, axis_mode, angle_val in WING_SPREAD_SPECS.get(wgrp, []):
                fk_bname = f"{base_bname}.{side}"
                pb_fk = pbones.get(fk_bname)
                if not pb_fk or spread_target_name not in pbones:
                    continue
                for c in list(pb_fk.constraints):
                    if c.name == "WING_spread":
                        pb_fk.constraints.remove(c)
                c_sp = pb_fk.constraints.new('TRANSFORM')
                c_sp.name = "WING_spread"
                c_sp.target = armature_obj
                c_sp.subtarget = spread_target_name
                c_sp.owner_space = 'LOCAL'
                c_sp.target_space = 'LOCAL'
                c_sp.use_motion_extrapolate = True
                c_sp.map_from = 'ROTATION'
                c_sp.map_to = 'ROTATION'
                c_sp.from_rotation_mode = 'AUTO'
                c_sp.to_euler_order = 'AUTO'
                c_sp.mix_mode_rot = 'ADD'
                c_sp.from_min_z_rot = -3.14159
                c_sp.from_max_z_rot = 3.14159

                if axis_mode == "X":
                    c_sp.map_to_x_from = 'Z'
                    c_sp.map_to_y_from = 'Y'
                    c_sp.map_to_z_from = 'Z'
                    c_sp.to_min_x_rot = angle_val
                    c_sp.to_max_x_rot = -angle_val
                else:
                    c_sp.map_to_x_from = 'X'
                    c_sp.map_to_y_from = 'Y'
                    c_sp.map_to_z_from = 'Z'
                    if side == "L":
                        c_sp.to_min_z_rot = angle_val
                        c_sp.to_max_z_rot = -angle_val
                    else:
                        c_sp.to_min_z_rot = -angle_val
                        c_sp.to_max_z_rot = angle_val

            # 5. Flap sine-wave driver on MCH-wing*_flap.{side}.location[1]
            pb_flap = pbones.get(f"MCH-{wgrp}_flap.{side}")
            if pb_flap:
                try:
                    fcurve = pb_flap.driver_add("location", 1)
                    drv = fcurve.driver
                    drv.type = 'SCRIPTED'
                    drv.expression = f"amp * {spec['flap_mult']} * sin(frame * spd * 0.2618)"

                    v_amp = drv.variables.new()
                    v_amp.name = "amp"
                    v_amp.type = 'SINGLE_PROP'
                    v_amp.targets[0].id = armature_obj
                    v_amp.targets[0].data_path = f'pose.bones["{ik_root_name}"]["flap_amount"]'

                    v_spd = drv.variables.new()
                    v_spd.name = "spd"
                    v_spd.type = 'SINGLE_PROP'
                    v_spd.targets[0].id = armature_obj
                    v_spd.targets[0].data_path = f'pose.bones["{ik_root_name}"]["flap_speed"]'
                except Exception as e_fdrv:
                    print(f"[REMIELLE WINGS] Flap driver warning on {pb_flap.name}: {e_fdrv}")


def _assign_remielle_wing_widgets_and_colors(armature_obj, assign_bone_to_group_fn=None):
    """
    Assigns strictly generic/existing Setup Wizard shapes (already used on the rig's own controls:
    gear from `upper_arm_parent.L`/`plate-settings`, pivot from `torso_pivot.002`/`hand_ik_pivot.L`,
    ring from `neck`, pin/pole from `forearm_tweak-pin.L`/`upper_arm_ik_target.L`, tweak from `tweak_spine`)
    to Remielle wing controls — NEVER copying any shape from Remielle.blend.
    """
    pbones = armature_obj.pose.bones

    def _from_pb(*bone_names):
        for bn in bone_names:
            pb = pbones.get(bn)
            if pb and pb.custom_shape:
                return pb.custom_shape
        return None

    def _from_obj(*obj_names):
        for on in obj_names:
            o = bpy.data.objects.get(on)
            if o and o.type == 'MESH':
                return o
        return None

    wgt_gear = (
        _from_obj("setting-circle", "npc_settings")
        or _from_pb("plate-settings", "upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L")
    )
    wgt_pivot = (
        _from_obj("torso-pivot", "hand-pivot")
        or _from_pb("torso_pivot.002", "hand_ik_pivot.L", "foot_ik_pivot.L", "hand_ik.L")
        or wgt_gear
    )
    wgt_spread = (
        _from_obj("neck", "eye circle")
        or _from_pb("neck", "chest", "torso")
        or wgt_gear
    )
    wgt_pole = (
        _from_obj("elbow-pin", "shin-pin", "WGT-IK_Arm_Pole", "primo-joint")
        or _from_pb("forearm_tweak-pin.L", "shin_tweak-pin.L", "upper_arm_ik_target.L", "thigh_ik_target.L")
        or wgt_gear
    )
    wgt_fk = (
        _from_pb("tweak_spine", "tweak_spine.001", "tweak_spine.002", "upper_arm_tweak.L", "forearm_tweak.L")
        or next((o for o in bpy.data.objects if o.type == 'MESH' and "tweak_spine" in o.name), None)
        or next((o for o in bpy.data.objects if o.type == 'MESH' and "_tweak" in o.name), None)
        or _from_obj("eye circle", "primo-joint")
        or wgt_gear
    )

    span_cache = {}

    def _mesh_span(shape_obj):
        if not shape_obj:
            return 1.0
        if shape_obj.name in span_cache:
            return span_cache[shape_obj.name]
        span = 1.0
        if getattr(shape_obj, "data", None) and getattr(shape_obj.data, "vertices", None) and len(shape_obj.data.vertices) > 0:
            verts = shape_obj.data.vertices
            xs = [v.co.x for v in verts]
            ys = [v.co.y for v in verts]
            zs = [v.co.z for v in verts]
            span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
            if span < 1e-4:
                span = 1.0
        span_cache[shape_obj.name] = span
        return span

    def _style_pb(pb, shape_obj, target_world_diameter, rot_euler=(0.0, 0.0, 0.0)):
        if not pb:
            return
        pb.rotation_mode = 'QUATERNION'
        if shape_obj:
            s = target_world_diameter / _mesh_span(shape_obj)
            pb.custom_shape = shape_obj
            pb.use_custom_shape_bone_size = False
            pb.custom_shape_scale_xyz = (s, s, s)
            pb.custom_shape_translation = (0.0, 0.0, 0.0)
            pb.custom_shape_rotation_euler = rot_euler

    # Skn_WingC_Root
    _style_pb(pbones.get("Skn_WingC_Root"), wgt_gear, 0.075)
    if assign_bone_to_group_fn:
        assign_bone_to_group_fn("Skn_WingC_Root", "Torso")

    # Wing IK controls
    for wgrp in ("wingA", "wingC", "wingD"):
        for side in ("L", "R"):
            grp_name = f"Limbs {side}"
            ik_root = f"{wgrp}_ik_root.{side}"
            tip = f"{wgrp}_tip.{side}"
            spread = f"{wgrp}_spread.{side}"
            pole = f"{wgrp}_pole.{side}"

            _style_pb(pbones.get(ik_root), wgt_gear, 0.060)
            _style_pb(pbones.get(tip), wgt_pivot, 0.075)
            _style_pb(pbones.get(spread), wgt_spread, 0.110)
            _style_pb(pbones.get(pole), wgt_pole, 0.045)

            if assign_bone_to_group_fn:
                for b_n in (ik_root, tip, spread, pole):
                    assign_bone_to_group_fn(b_n, grp_name)

    # Wing FK controls
    for pb in pbones:
        bname = pb.name
        if bname.startswith(("Skn_WingA_", "Skn_WingC_", "Ctr_WingD_", "Skn_ClaFeather_")) and bname != "Skn_WingC_Root":
            _style_pb(pb, wgt_fk, 0.032)
            if assign_bone_to_group_fn:
                if bname.endswith(".L"):
                    assign_bone_to_group_fn(bname, "Limbs L")
                elif bname.endswith(".R"):
                    assign_bone_to_group_fn(bname, "Limbs R")
                else:
                    assign_bone_to_group_fn(bname, "Torso")


def assign_remielle_wing_collections(armature_obj):
    """
    Places all Remielle wing bones into their dedicated Bone Collections:
    - `Wings (FK)` (visible=True)
    - `Wing A (IK)`, `Wing C (IK)`, `Wing D (IK)` (visible=True so IK wing controls are ready to use)
    - `Wing A (FK)`, `Wing C (FK)`, `Wing D (FK)` (visible=False by default)
    - `Other` for all `MCH-wing*` bones
    Also removes wing bones from `Clothes`, `Hair`, and `Other` (for non-MCH bones).
    """
    if not armature_obj or not hasattr(armature_obj, "data") or not hasattr(armature_obj.data, "collections"):
        return

    colls = armature_obj.data.collections
    bones = armature_obj.data.bones

    def get_or_create_coll(name, is_vis):
        c = colls.get(name) or colls.new(name)
        try:
            c.is_visible = is_vis
        except Exception:
            pass
        return c

    has_cla = any(b.name.startswith("Skn_ClaFeather_") for b in bones)
    c_wings_fk = get_or_create_coll("Wings (FK)", True) if has_cla else None
    c_wa_ik = get_or_create_coll("Wing A (IK)", True)
    c_wa_fk = get_or_create_coll("Wing A (FK)", False)
    c_wc_ik = get_or_create_coll("Wing C (IK)", True)
    c_wc_fk = get_or_create_coll("Wing C (FK)", False)
    c_wd_ik = get_or_create_coll("Wing D (IK)", True)
    c_wd_fk = get_or_create_coll("Wing D (FK)", False)
    c_other = get_or_create_coll("Other", False)

    def move_exclusively(bone_obj, target_coll):
        if not bone_obj or not target_coll:
            return
        for c in list(bone_obj.collections):
            if c != target_coll:
                try:
                    c.unassign(bone_obj)
                except Exception:
                    pass
        target_coll.assign(bone_obj)

    for b in bones:
        bn = b.name
        if bn.startswith("MCH-wing"):
            move_exclusively(b, c_other)
        elif bn.startswith("wingA_"):
            move_exclusively(b, c_wa_ik)
        elif bn.startswith("wingC_"):
            move_exclusively(b, c_wc_ik)
        elif bn.startswith("wingD_"):
            move_exclusively(b, c_wd_ik)
        elif bn.startswith("Skn_WingA_"):
            move_exclusively(b, c_wa_fk)
        elif bn == "Skn_WingC_Root" or bn.startswith("Skn_WingC_"):
            move_exclusively(b, c_wc_fk)
        elif bn.startswith("Ctr_WingD_"):
            move_exclusively(b, c_wd_fk)
        elif bn.startswith("Skn_ClaFeather_") and c_wings_fk:
            move_exclusively(b, c_wings_fk)


def generate_remielle_wing_ui_splice() -> str:
    """
    Returns the RigUI.draw splice string that renders the 'Wing Settings' box
    (IK / FK, Flap Amount, Flap Speed) whenever any bone belonging to a wing group is selected.
    """
    return """
        for _w_grp, _w_label in (("wingA", "Wing A"), ("wingC", "Wing C"), ("wingD", "Wing D")):
            for _w_side in ("L", "R"):
                _w_root = f"{_w_grp}_ik_root.{_w_side}"
                if _w_root in pose_bones and is_selected({_w_root, f"{_w_grp}_tip.{_w_side}", f"{_w_grp}_spread.{_w_side}", f"{_w_grp}_pole.{_w_side}"}):
                    _w_box = layout.box()
                    _w_box.label(text=f"Wing Settings: {_w_label}.{_w_side}")
                    _w_box.prop(pose_bones[_w_root], '["wing_ik"]', text="IK / FK", slider=True)
                    _w_box.prop(pose_bones[_w_root], '["flap_amount"]', text="Flap Amount", slider=True)
                    _w_box.prop(pose_bones[_w_root], '["flap_speed"]', text="Flap Speed", slider=True)
"""


def setup_remielle_wings_rig(armature_obj, original_name="", char_name="", assign_bone_to_group_fn=None):
    """
    Main entry point to build the Remielle wing IK/FK/Spread/Flap rig on `armature_obj`.
    Returns True if applied, False if the character is not Remielle.
    """
    if not is_remielle_character(armature_obj, original_name=original_name, char_name=char_name):
        return False

    print(f"[REMIELLE WINGS] Building special wing IK/FK/Spread/Flap rig for '{char_name or armature_obj.name}'...")
    _rename_wing_bones_and_vertex_groups(armature_obj)
    _build_remielle_wing_edit_bones(armature_obj)
    _setup_remielle_wing_constraints_and_drivers(armature_obj)
    _assign_remielle_wing_widgets_and_colors(armature_obj, assign_bone_to_group_fn=assign_bone_to_group_fn)
    assign_remielle_wing_collections(armature_obj)
    print(f"[REMIELLE WINGS] Wing rig setup complete for '{char_name or armature_obj.name}'.")
    return True
