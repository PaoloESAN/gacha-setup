# Authors: enthralpy, Llama.jpg, michael-gh1
# Standardized Rig UI Utilities for Gacha Setup across all games (Genshin, HSR, ZZZ, NTE, NPC)

import os
import re
import bpy
import addon_utils


def extract_clean_character_name(raw_name):
    """
    Extracts a clean, human-readable character name from arbitrary armature/mesh names.
    Handles naming conventions from Genshin, HSR, ZZZ, NTE, etc.
    E.g.:
        'Avatar_Ellen_UI' -> 'Ellen'
        'Avatar_Female_Size01_Ellen_UI' -> 'Ellen'
        'Avatar_Castorice_00' -> 'Castorice'
        'Avatar_Lady_ColumbinaCostume' -> 'Columbina'
        'Avatar_Daphne_01' -> 'Daphne'
        'Columbina' -> 'Columbina'
        'Paimon' -> 'Paimon'
    """
    if not raw_name:
        return "Character"
    name = str(raw_name).replace(".001", "").replace(".002", "").replace("Rig", "").replace("rig", "").strip()
    name = name.split("Costume")[0]

    noise_tokens = {
        "avatar", "armature", "model", "mesh", "ui", "costume", "root", "fbx", "pmx",
        "00", "01", "02", "03", "04", "000", "grp", "skin", "joint", "rig", "char",
        "female", "male", "lady", "girl", "boy", "loli", "size01", "size02", "size03",
        "size04", "npc", "base", "body", "face", "hair"
    }

    parts = [p for p in name.split("_") if p]
    filtered = [p for p in parts if p.lower() not in noise_tokens]

    if filtered:
        return filtered[-1]
    elif parts:
        return parts[-1]
    return name or "Character"


def get_setup_wizard_version():
    """Retrieves setup wizard version tuple and returns formatted string (e.g. 'v3.3.0')."""
    try:
        from .. import bl_info
        setup_version_tuple = bl_info.get("version", (0, 0, 0))
    except Exception:
        matching_mods = [
            mod.bl_info
            for mod in addon_utils.modules()
            if mod.bl_info.get("name") in ("Gacha Setup", "Gacha Blender Setup", "HoYoverse Setup Wizard")
        ]
        if matching_mods:
            setup_version_tuple = matching_mods[0].get("version", (0, 0, 0))
        else:
            setup_version_tuple = (0, 0, 0)

    return f"v{setup_version_tuple[0]}.{setup_version_tuple[1]}.{setup_version_tuple[2]}"


STANDARD_COLLECTION_NAMES = [
    "Tweaks",
    "Pivots & Pins",
    "Offsets",
    "Props",
    "Face",
    "Torso (IK)",
    "Torso (FK)",
    "Fingers",
    "Fingers (Detail)",
    "Arm.L (IK)",
    "Arm.R (IK)",
    "Arm.L (FK)",
    "Arm.R (FK)",
    "Leg.L (IK)",
    "Leg.R (IK)",
    "Leg.L (FK)",
    "Leg.R (FK)",
    "Root",
    "Hair",
    "Clothes",
    "Cage",
    "Lighting",
    "Other",
]


def setup_standard_bone_collections(armature_obj, is_version_4):
    """
    Clears existing bone collections and initializes all standard 23 bone collections in Blender 4.0+.
    Sets initial visibility so main control collections are active, while helpers/FK/physics are hidden.
    """
    if not is_version_4:
        return

    armature = armature_obj.data if hasattr(armature_obj, "data") else armature_obj
    collections = armature.collections

    # Remove existing collections
    while collections:
        collections.remove(collections[0])

    # Create all standard collections
    for name in STANDARD_COLLECTION_NAMES:
        collections.new(name)

    # Initial visibility: Face, Torso (IK), Fingers, Arm.L/R (IK), Leg.L/R (IK), Root, Lighting visible
    visible_by_default = {
        "Face",
        "Torso (IK)",
        "Fingers",
        "Arm.L (IK)",
        "Arm.R (IK)",
        "Leg.L (IK)",
        "Leg.R (IK)",
        "Root",
        "Lighting",
    }

    for name in STANDARD_COLLECTION_NAMES:
        coll = collections.get(name)
        if coll:
            coll.is_visible = name in visible_by_default


def bone_to_layer_or_collection(armature_obj, bone_name, layer_idx, collection_name, second_coll="None", is_version_4=True):
    """Assigns a bone to its designated collection in Blender 4+ or bone layer in Blender 3.6."""
    arm_data = armature_obj.data if hasattr(armature_obj, "data") else armature_obj
    if bone_name not in arm_data.bones:
        return

    bone = arm_data.bones[bone_name]

    if is_version_4:
        target_coll = arm_data.collections.get(collection_name)
        if target_coll:
            target_coll.assign(bone)

        other_coll = arm_data.collections.get("Other")
        if collection_name != "Other" and other_coll:
            try:
                other_coll.unassign(bone)
            except Exception:
                pass

        if second_coll and second_coll != "None":
            sec_coll = arm_data.collections.get(second_coll)
            if sec_coll:
                sec_coll.assign(bone)
    else:
        try:
            for x in range(32):
                if isinstance(layer_idx, list):
                    bone.layers[x] = x in layer_idx
                else:
                    bone.layers[x] = (x == layer_idx)
        except Exception:
            pass


def distribute_standard_rig_bones(
    armature_obj,
    is_version_4=True,
    toe_bones_exist=True,
    use_arm_ik_poles=False,
    use_leg_ik_poles=False,
    no_eyes=False,
    has_lighting_panel=False,
    physics_bone_callback=None,
):
    """
    Distributes standard Rigify and character bones across the 23 standard collections / layers.
    """
    arm_data = armature_obj.data if hasattr(armature_obj, "data") else armature_obj

    def b2c(b_name, layer_num, coll_name, sec_coll="None"):
        bone_to_layer_or_collection(armature_obj, b_name, layer_num, coll_name, sec_coll, is_version_4)

    def fast_move(bone_list, layer_num, coll_name):
        for b in bone_list:
            b2c(b, layer_num, coll_name)

    # 1. Initialize all bones to 'Other'
    for b in arm_data.bones:
        b2c(b.name, 25, "Other")

    # 2. Tweaks
    for b in arm_data.bones:
        b_name = b.name
        if "tweak" in b_name and "MCH" not in b_name and "pin" not in b_name:
            b2c(b_name, 2, "Tweaks")

    fast_move([
        "tweak_spine", "tweak_spine.001", "tweak_spine.002",
        "tweak_spine.003", "tweak_spine.004", "tweak_spine.005",
    ], 2, "Tweaks")

    # 3. Pivots & Pins
    fast_move([
        "torso_pivot.002",
        "forearm_tweak-pin.L", "forearm_tweak-pin.R",
        "shin_tweak-pin.L", "shin_tweak-pin.R",
        "hand_ik_pivot.L", "hand_ik_pivot.R",
        "foot_ik_pivot.L", "foot_ik_pivot.R",
    ], 19, "Pivots & Pins")

    # 4. Offsets
    fast_move([
        "root", "root.001", "torso.001", "torso.002",
        "hand_ik_wrist.L", "hand_ik_wrist.R",
        "foot_ik_sub.L", "foot_ik_sub.R",
    ], 26, "Offsets")

    # 5. Props
    fast_move(["prop.L", "prop.R"], 21, "Props")
    for b in arm_data.bones:
        if "prop" in b.name.lower() and not b.name.startswith("DEF-") and not b.name.startswith("MCH-"):
            b2c(b.name, 21, "Props")

    # 6. Face
    fast_move([
        "plate-settings", "plate-border", "Plate", "extras-panel",
        "eyetrack", "eyetrack_L", "eyetrack_R", "eyeRoot", "head-controller",
        "Brow-Trouble-R-Control", "Brow-Trouble-L-Control",
        "Brow-Shy-R-Control", "Brow-Shy-L-Control",
        "Brow-Angry-R-Control", "Brow-Angry-L-Control",
        "Brow-Smily-R-Control", "Brow-Smily-L-Control",
        "Brow-R-Control", "Brow-L-Control",
        "Eye-Up-Control", "Eye-Tired-Control", "Eye-Wail-Control", "Eye-Ha-Control",
        "Wink-Control-R", "Eye-WinkA-Control", "Eye-WinkB-Control", "Eye-WinkC-Control",
        "Wink-Control-L", "Eye-Down-Control", "Eye-Jito-Control", "Eye-Hostility-Control",
        "Eye-LowerEyelid-Control", "Eye-Star-Control", "Eye-Pupil-Control",
        "Mouth-Control", "Mouth-Smile1-Control", "Mouth-Smile2-Control",
        "Mouth-Angry1-Control", "Mouth-Angry2-Control", "Mouth-Angry3-Control",
        "Mouth-Fury1-Control", "Mouth-Doya1-Control", "Mouth-Doya2-Control",
        "Mouth-Pero1-Control", "Mouth-Pero2-Control", "Mouth-Neko1-Control",
        "Mouth-Default-Control", "Face-Root",
    ], 0, "Face")

    for b in arm_data.bones:
        b_name = b.name
        if (
            b_name.startswith("DEF-")
            or b_name.startswith("ORG-")
            or b_name.startswith("MCH-")
            or b_name.startswith("Bon_")
            or b_name.startswith("BON_")
            or b_name.startswith("Bone-")
            or b_name.startswith("Bip")
            or b_name.startswith("joint_")
            or b_name.startswith("skn_")
            or "twist" in b_name.lower()
        ):
            continue
        if "slider-" in b_name or "-control" in b_name.lower() or "control-" in b_name.lower():
            b2c(b_name, 0, "Face")

    # 7. Torso (IK)
    fast_move(["head", "neck", "chest", "torso", "hips"], 3, "Torso (IK)")

    # 8. Torso (FK)
    fast_move([
        "spine_fk", "spine_fk.001", "spine_fk.002", "spine_fk.003", "spine_fk.004",
    ], 4, "Torso (FK)")

    # 9. Fingers (Master)
    fast_move([
        "thumb.01_master.L", "thumb.01_master.R",
        "f_index.01_master.L", "f_index.01_master.R",
        "f_middle.01_master.L", "f_middle.01_master.R",
        "f_ring.01_master.L", "f_ring.01_master.R",
        "f_pinky.01_master.L", "f_pinky.01_master.R",
    ], 5, "Fingers")

    # 10. Fingers (Detail)
    finger_details = []
    for side in [".L", ".R"]:
        for fname in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
            for num in ["01", "02", "03"]:
                finger_details.append(f"{fname}.{num}{side}")
                finger_details.append(f"{fname}.{num}{side}.001")
            finger_details.append(f"{fname}.01_ik{side}")
        finger_details.append(f"palm{side}")
    fast_move(finger_details, 6, "Fingers (Detail)")

    # 11 & 12. Arms (IK)
    b2c("hand_ik.L", 7, "Arm.L (IK)")
    b2c("upper_arm_ik_target.L", 7, "Arm.L (IK)")
    b2c("upper_arm_parent.L", [7, 8], "Arm.L (IK)", "Arm.L (FK)")
    b2c("shoulder.L", [7, 8], "Arm.L (IK)", "Arm.L (FK)")

    b2c("hand_ik.R", 10, "Arm.R (IK)")
    b2c("upper_arm_ik_target.R", 10, "Arm.R (IK)")
    b2c("upper_arm_parent.R", [10, 11], "Arm.R (IK)", "Arm.R (FK)")
    b2c("shoulder.R", [10, 11], "Arm.R (IK)", "Arm.R (FK)")

    b2c("upper_arm_ik.L", 7, "Arm.L (IK)")
    b2c("upper_arm_ik.R", 10, "Arm.R (IK)")

    # 13 & 14. Arms (FK)
    fast_move(["upper_arm_fk.L", "forearm_fk.L", "hand_fk.L"], 8, "Arm.L (FK)")
    fast_move(["upper_arm_fk.R", "forearm_fk.R", "hand_fk.R"], 11, "Arm.R (FK)")

    # 15 & 16. Legs (IK)
    b2c("foot_ik.L", 13, "Leg.L (IK)")
    b2c("thigh_ik.L", 13, "Leg.L (IK)")
    b2c("thigh_parent.L", [13, 14], "Leg.L (IK)", "Leg.L (FK)")
    b2c("thigh_ik_target.L", 13, "Leg.L (IK)")
    b2c("foot_spin_ik.L", 13, "Leg.L (IK)")
    b2c("foot_heel_ik.L", 13, "Leg.L (IK)")

    b2c("foot_ik.R", 16, "Leg.R (IK)")
    b2c("thigh_ik.R", 16, "Leg.R (IK)")
    b2c("thigh_parent.R", [16, 17], "Leg.R (IK)", "Leg.R (FK)")
    b2c("thigh_ik_target.R", 16, "Leg.R (IK)")
    b2c("foot_spin_ik.R", 16, "Leg.R (IK)")
    b2c("foot_heel_ik.R", 16, "Leg.R (IK)")

    if toe_bones_exist:
        b2c("toe_ik.L", 13, "Leg.L (IK)")
        b2c("toe_ik.R", 16, "Leg.R (IK)")
    else:
        b2c("toe_ik.L", 25, "Other")
        b2c("toe_ik.R", 25, "Other")

    b2c("thigh_ik.L", 13, "Leg.L (IK)")
    b2c("thigh_ik.R", 16, "Leg.R (IK)")

    # 17 & 18. Legs (FK)
    fast_move(["thigh_fk.L", "shin_fk.L", "foot_fk.L", "toe_fk.L"], 14, "Leg.L (FK)")
    fast_move(["thigh_fk.R", "shin_fk.R", "foot_fk.R", "toe_fk.R"], 17, "Leg.R (FK)")

    # 19. Root
    b2c("root.002", 28, "Root")
    b2c("root_2", 28, "Root")
    if "root.002" not in arm_data.bones and "root_2" not in arm_data.bones:
        b2c("root", 28, "Root")

    # 20 & 21. Hair & Clothes & Breasts
    fast_move(["breast.L", "breast.R", "DEF-breast.L", "DEF-breast.R"], 22, "Clothes")

    clothes_keywords = [
        "ribbon", "sleeve", "strap", "skirt", "button", "belt", "cloth", "dress",
        "cape", "coat", "hem", "scarf", "tassel", "string", "chain", "acc",
        "qun", "xiu", "sce", "tail", "amice", "pants", "sock", "shoe",
        "necklace", "earring", "pendant", "badge", "prop", "breast"
    ]
    hair_keywords = [
        "hair", "eardrop", "headline", "ahoge", "bangs", "ponytail", "twintail", "bone00"
    ]

    for b in arm_data.bones:
        b_low = b.name.lower()
        if (
            b.name.startswith("DEF-")
            or b.name.startswith("MCH-")
            or b.name.startswith("ORG-")
            or b.name.startswith("Bon_")
            or b.name.startswith("BON_")
            or b.name.startswith("Bone-")
            or b.name.startswith("Bip")
            or b.name.startswith("joint_")
            or b.name.startswith("skn_")
        ):
            continue

        if any(k in b_low for k in hair_keywords) or "+Hair" in b.name or "+hair" in b.name:
            b2c(b.name, 20, "Hair")
        elif any(k in b_low for k in clothes_keywords) or ("+" in b.name and "+Hair" not in b.name and "+hair" not in b.name):
            b2c(b.name, 22, "Clothes")
        elif "amice" in b_low:
            b2c(b.name, 22, "Clothes")

    # 22. Lighting
    if has_lighting_panel or "Lighting" in getattr(arm_data, "collections", {}):
        fast_move([
            "Lighting Panel", "FresnelToggle", "Fresnel", "FresnelSize",
            "Ambient", "SoftLit", "Lit", "SoftShadow", "Shadow",
            "RimShadow", "Rim Lit", "RimX", "RimY", "RimLitPin",
            "ShadowOffset", "ShadowPin", "LitPin", "AmbientPin",
            "RimShadowPin", "SoftShadowPin", "SoftLitPin", "FresnelPin",
        ], 1, "Lighting")

    # Allow game-specific physics/accessory bone classifier callback
    if physics_bone_callback:
        physics_bone_callback(armature_obj, b2c)

    # 23. Ensure all deform, mechanism, base, and helper bones strictly remain in Other & hidden
    for b in arm_data.bones:
        b_name = b.name
        if (
            b_name.startswith("DEF-")
            or b_name.startswith("MCH-")
            or b_name.startswith("ORG-")
            or b_name.startswith("Bon_")
            or b_name.startswith("BON_")
            or b_name.startswith("Bone-")
            or b_name.startswith("Bip")
            or b_name.startswith("joint_")
            or b_name.startswith("skn_")
            or "twist" in b_name.lower()
            or b_name.lower() in ["mouth", "face-root"]
        ):
            b2c(b_name, 25, "Other")
            try:
                b.hide = True
            except Exception:
                pass


def build_rig_layers_ui_code(original_name, setup_version):
    """
    Generates the Python draw code for the RigLayers panel, perfectly matching Genshin Impact style
    with two-column layouts, solo star (★) buttons, and version footer.
    """
    def make_layer_str(text, layer, version, title=""):
        string3 = f"row.prop(context.active_object.data, 'layers', index={layer}, toggle=True, text='{text}')"
        string4 = f"if '{text}' in collection: row.prop(collection['{text}'], 'is_visible', toggle=True, text='{text}')"
        if version == 4:
            return string4 if title == "" else string4.replace("row.", f"row_{title}.")
        else:
            return string3 if title == "" else string3.replace("row.", f"row_{title}.")

    def make_solo_str(text, title=""):
        solo_str = f"if '{text}' in collection: row.prop(collection['{text}'], 'is_solo', toggle=True, text='★')"
        return solo_str if title == "" else solo_str.replace("row.", f"row_{title}.")

    def layers_to_generate(vers):
        if vers == 3:
            return (
                "\n            row = col.row()\n            " + make_layer_str("Tweaks", 2, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Pivots & Pins", 19, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Offsets", 26, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Props", 21, vers) +
                "\n            row = col.row()\n            row.separator()" +
                "\n            row = col.row()\n            row.separator()" +
                "\n            row = col.row()\n            " + make_layer_str("Face", 0, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Torso (IK)", 3, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Torso (FK)", 4, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Fingers", 5, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Fingers (Detail)", 6, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Arm.L (IK)", 7, vers) +
                "\n            " + make_layer_str("Arm.R (IK)", 10, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Arm.L (FK)", 8, vers) +
                "\n            " + make_layer_str("Arm.R (FK)", 11, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Leg.L (IK)", 13, vers) +
                "\n            " + make_layer_str("Leg.R (IK)", 16, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Leg.L (FK)", 14, vers) +
                "\n            " + make_layer_str("Leg.R (FK)", 17, vers) +
                "\n            row = col.row()\n            row.separator()" +
                "\n            row = col.row()\n            row.separator()" +
                "\n            row = col.row()\n            " + make_layer_str("Root", 28, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Lighting", 1, vers) +
                "\n            " + make_layer_str("Hair", 20, vers) +
                "\n            " + make_layer_str("Clothes", 22, vers) +
                "\n            " + make_layer_str("Cage", 24, vers) +
                "\n            " + make_layer_str("Other", 25, vers)
            )
        else:
            return (
                "\n            layout = self.layout" +
                "\n            split_size = 0.9" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            split_small = 0.8" +
                "\n            split_tri = 0.78" +
                # Lighting
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Lighting", 1, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Lighting") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Tweaks / Pivots & Pins
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Tweaks", 2, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Tweaks", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Pivots & Pins", 19, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Pivots & Pins", "pivots") +
                "\n            row = col.row()" +
                # Offsets / Props
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Offsets", 26, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Offsets", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Props", 21, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Props", "pivots") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Face
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Face", 0, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Face") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Torso IK / FK
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Torso (IK)", 3, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Torso (IK)") +
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Torso (FK)", 4, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Torso (FK)") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Fingers Main / Detail
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Fingers", 5, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Fingers") +
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Fingers (Detail)", 6, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Fingers (Detail)") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Arms IK
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Arm.L (IK)", 7, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Arm.L (IK)", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Arm.R (IK)", 10, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Arm.R (IK)", "pivots") +
                "\n            row = col.row()" +
                # Arms FK
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Arm.L (FK)", 8, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Arm.L (FK)", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Arm.R (FK)", 11, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Arm.R (FK)", "pivots") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Legs IK
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Leg.L (IK)", 13, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Leg.L (IK)", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Leg.R (IK)", 16, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Leg.R (IK)", "pivots") +
                "\n            row = col.row()" +
                # Legs FK
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Leg.L (FK)", 14, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Leg.L (FK)", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Leg.R (FK)", 17, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Leg.R (FK)", "pivots") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Root
                "\n            row = col.row()" +
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Root", 28, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Root") +
                # Spacers
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                "\n            row = col.row()" +
                # Hair / Clothes
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Hair", 20, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Hair", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Clothes", 22, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Clothes", "pivots") +
                "\n            row = col.row()" +
                # Cage / Other
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Cage", 24, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Cage", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Other", 25, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Other", "pivots")
            )

    return (
        "\n        layout = self.layout" +
        "\n        col = layout.column()" +
        "\n        row = col.row()" +
        f'\n        setup_vers = "{setup_version}"' +
        f'\n        v_str = "{bpy.app.version_string}"' +
        "\n        if bpy.app.version[0] <= 3:" +
        layers_to_generate(3) +
        "\n            row = col.row()" +
        '\n            row.label(text="Rig: " + setup_vers + " | " + v_str)' +
        "\n        elif bpy.app.version[0] >= 4:" +
        "\n            arm_obj = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else (context.object if (context.object and context.object.type == 'ARMATURE') else None)" +
        "\n            if not arm_obj or not hasattr(arm_obj, 'data') or not hasattr(arm_obj.data, 'collections'):" +
        f'\n                arm_obj = bpy.data.objects.get("{original_name}") or bpy.data.objects.get(rig_id)' +
        "\n            if not arm_obj or not hasattr(arm_obj, 'data') or not hasattr(arm_obj.data, 'collections'):" +
        "\n                return" +
        "\n            collection = arm_obj.data.collections" +
        layers_to_generate(4) +
        "\n            row = col.row()" +
        '\n            row.label(text="Rig: " + setup_vers + " | " + v_str)' +
        "\n        else:" +
        '\n            row.label(text="ERROR: Version mismatch!")'
    )


def replace_rig_layers_draw(complete_rig_text, rig_add_layer_code):
    """Replaces strictly the draw() method body inside RigLayers without affecting other classes."""
    pattern = r'(\bclass\s+(?:RigLayers|[a-zA-Z0-9_]+_PT_rig_layers[a-zA-Z0-9_]*)\s*\(\s*bpy\.types\.Panel\s*\):.*?\ndef\s+draw\s*\(\s*self\s*,\s*context\s*\)\s*:)(.*?)(\n(?=class\s+|def\s+register|\Z))'
    match = re.search(pattern, complete_rig_text, flags=re.DOTALL)
    if match:
        class_header_and_draw = match.group(1)
        next_part = match.group(3)
        return complete_rig_text[:match.start()] + class_header_and_draw + rig_add_layer_code + "\n" + next_part + complete_rig_text[match.end():]

    if "class RigLayers(bpy.types.Panel):" in complete_rig_text:
        parts = complete_rig_text.split("class RigLayers(bpy.types.Panel):", 1)
        after_class = parts[1]
        if "def draw(self, context):" in after_class:
            draw_parts = after_class.split("def draw(self, context):", 1)
            draw_header = draw_parts[0]
            rest = draw_parts[1]
            end_match = re.search(r'\n(?=class\s+|def\s+register|\Z)', rest)
            if end_match:
                after_draw = rest[end_match.start():]
                return parts[0] + "class RigLayers(bpy.types.Panel):" + draw_header + "def draw(self, context):" + rig_add_layer_code + after_draw

    return complete_rig_text


def modify_and_run_rig_ui_script(
    armature_obj,
    original_name,
    char_name=None,
    extra_splices=None,
    custom_disclaimer=None
):
    """
    Finds the Rigify-generated UI script, updates RigLayers panel, sets character names in headers,
    injects any custom properties/sliders, and runs the script.
    """
    clean_char_name = char_name or extract_clean_character_name(original_name)
    setup_version = get_setup_wizard_version()

    # Find the UI text datablock across all common naming patterns
    possible_names = [
        f"{original_name}_ui.py",
        f"{clean_char_name}_ui.py",
        f"{clean_char_name}Rig_ui.py",
        "rig_ui.py",
        "metarig_ui.py",
    ]
    if armature_obj and hasattr(armature_obj, "name"):
        possible_names.insert(0, f"{armature_obj.name}_ui.py")

    rig_file = None
    for name in possible_names:
        if name in bpy.data.texts:
            rig_file = bpy.data.texts[name]
            break

    if not rig_file:
        for t in bpy.data.texts:
            content = t.as_string()
            if "class RigLayers" in content or "PT_rig_layers" in content or "rig_id = " in content:
                rig_file = t
                break

    if not rig_file:
        print(f"[RIG UI] Warning: Could not find rig ui script for {original_name}")
        return False

    rig_text = rig_file.as_string()
    complete_rig_text = rig_text

    disclaimer = custom_disclaimer or f"""
# This RigUI script has been modified for use with custom rigs for {clean_char_name}.
# Setup Wizard Version: {setup_version} | Blender Version: {bpy.app.version_string}
"""

    try:
        rig_char_id = rig_text.split('rig_id = "')[1].split('"')[0]
    except Exception:
        rig_char_id = clean_char_name

    rig_add_layer_code = build_rig_layers_ui_code(original_name, setup_version)

    # Cleanly replace the draw() method of RigLayers
    complete_rig_text = replace_rig_layers_draw(complete_rig_text, rig_add_layer_code)

    # Apply extra splices if provided
    if extra_splices:
        for splice in extra_splices:
            divider = splice.get("divider", "num_rig_separators[0] += 1")
            text = splice.get("text", "")
            if divider in complete_rig_text:
                parts = complete_rig_text.split(divider)
                complete_rig_text = parts[0] + divider + text + parts[1]

    complete_rig_text = complete_rig_text.replace(
        'bl_label = "Rig Layers"', 'bl_label = "Rig Layers: " + rig_name'
    )
    complete_rig_text = complete_rig_text.replace(
        'bl_label = "Rig Main Properties"', 'bl_label = "Rig Properties: " + rig_name'
    )

    # Blender 5.1+ compatibility fix: strip register_usetime_properties
    complete_rig_text = re.sub(
        r"^\s*register_usetime_properties\(\)\s*$",
        "",
        complete_rig_text,
        flags=re.MULTILINE,
    )
    complete_rig_text = re.sub(
        r"^\s*unregister_usetime_properties\(\)\s*$",
        "",
        complete_rig_text,
        flags=re.MULTILINE,
    )

    # Write modified content
    rig_file.clear()
    header_var = f'rig_name = "{clean_char_name}"\n'
    if "rig_id = " in complete_rig_text:
        rig_file.write(complete_rig_text.replace("rig_id = ", f"{header_var}rig_id = "))
    else:
        rig_file.write(f"{header_var}\n{complete_rig_text}")

    rig_file.write(disclaimer)

    # Execute updated script
    try:
        ctx = bpy.context.copy()
        ctx["edit_text"] = rig_file
        with bpy.context.temp_override(edit_text=rig_file):
            bpy.ops.text.run_script()
        print(f"[RIG UI] Successfully updated and executed UI script for '{clean_char_name}'")
        return True
    except Exception as ex:
        print(f"[RIG UI] Notice running updated UI script: {ex}")
        return False


def apply_hair_and_clothes_physics(armature_obj=None, context=None, hair_influence=None, clothes_influence=None, dress_influence=None):
    """
    Applies Damped Track constraints along bone chains for Hair and Clothes bones:
    - Parent bone tracks child bone along each strand/chain.
    - Hair bones: influence = hair_influence (default 0.7)
    - Clothes bones: influence = clothes_influence (default 0.4)
    - Tip bones (end of chain with no children) have no constraints.
    - Ignores eyes, teeth, twist bones, limbs, fingers, and deform controls.
    Ensures hair and clothes collections/layers and bones are visible so constraints are properly applied.
    """
    context = context or bpy.context

    if not armature_obj:
        for obj in context.selected_objects:
            if obj.type == "ARMATURE" and not obj.name.startswith("WGT"):
                armature_obj = obj
                break
        if not armature_obj and context.active_object and context.active_object.type == "ARMATURE":
            armature_obj = context.active_object
        if not armature_obj:
            for obj in context.scene.objects:
                if obj.type == "ARMATURE" and not obj.name.startswith("WGT"):
                    armature_obj = obj
                    break

    if not armature_obj:
        print("[PHYSICS] No armature found to apply hair & clothes physics.")
        return 0

    # Read influences from scene properties if not explicitly provided
    if hair_influence is None:
        if hasattr(context, "scene") and hasattr(context.scene, "character_rigger_props") and hasattr(context.scene.character_rigger_props, "hair_physics_influence"):
            hair_influence = context.scene.character_rigger_props.hair_physics_influence
        elif hasattr(context, "scene") and hasattr(context.scene, "hair_physics_influence"):
            hair_influence = context.scene.hair_physics_influence
        else:
            hair_influence = 0.7

    if clothes_influence is None:
        clothes_influence = dress_influence

    if clothes_influence is None:
        if hasattr(context, "scene") and hasattr(context.scene, "character_rigger_props"):
            props = context.scene.character_rigger_props
            if hasattr(props, "clothes_physics_influence"):
                clothes_influence = props.clothes_physics_influence
            elif hasattr(props, "dress_physics_influence"):
                clothes_influence = props.dress_physics_influence
        elif hasattr(context, "scene"):
            if hasattr(context.scene, "clothes_physics_influence"):
                clothes_influence = context.scene.clothes_physics_influence
            elif hasattr(context.scene, "dress_physics_influence"):
                clothes_influence = context.scene.dress_physics_influence

    if clothes_influence is None:
        clothes_influence = 0.4

    # Ensure armature is active and in POSE mode
    context.view_layer.objects.active = armature_obj
    try:
        bpy.ops.object.mode_set(mode="POSE")
    except Exception:
        pass

    is_v4 = bpy.app.version >= (4, 0, 0)
    arm_data = armature_obj.data

    # Make Hair and Clothes collections / layers visible
    if is_v4:
        for coll_name in ["Hair", "Clothes"]:
            if coll_name in arm_data.collections:
                arm_data.collections[coll_name].is_visible = True
    else:
        if len(arm_data.layers) > 22:
            arm_data.layers[20] = True
            arm_data.layers[22] = True

    physics_ignore_list = {
        "+UpperArmTwistA02.L", "+UpperArmTwistA01.L", "+UpperArmTwistA01.R", "+UpperArmTwistA02.R",
        "eye.R", "eye.L", "+ToothBone D A01", "+ToothBone U A01", "+ToothBone A A01",
        "+EyeBone L A01", "+EyeBoneA02.L", "+EyeBone R A01", "+EyeBoneA02.R",
        "+EyeBone R A01.001", "+EyeBone L A01.001", "+PelvisTwist CF A01",
        "+ForeArmTwistSA01.R", "+ForeArmTwistSA01.L", "+ShoulderSA01.L", "+ShoulderSA01.R",
        "+ElbowSA01.R", "+ElbowSA01.L", "+KneeFA01.R", "+KneeFA01.L", "+SkirtAllF CF A01",
        "+ForearmTwistSA01.R", "+ForearmTwistSA01.L", "+ThighTwistSA01.R", "+ThighTwistSA01.L"
    }

    def is_physics_ignored(name):
        if name in physics_ignore_list:
            return True
        low = name.lower()
        if any(k in low for k in [
            "eyebone", "eye", "tooth", "teeth", "tongue", "mouth", "jaw", "brow", "lip", "nose",
            "cheek", "plate", "twist", "sa01", "sa02", "fa01", "skirtallf", "prop", "light"
        ]):
            return True
        if (
            name.startswith("DEF-")
            or name.startswith("ORG-")
            or name.startswith("MCH-")
            or name.startswith("Bon_")
            or name.startswith("BON_")
            or name.startswith("Bone-")
            or name.startswith("Bip")
            or name.startswith("joint_")
            or name.startswith("skn_")
            or name.startswith("WGT")
        ):
            return True
        return False

    hair_bone_names = set()
    clothes_bone_names = set()

    if is_v4 and hasattr(arm_data, "collections"):
        if "Hair" in arm_data.collections:
            hair_bone_names.update(b.name for b in arm_data.collections["Hair"].bones if not is_physics_ignored(b.name))
        if "Clothes" in arm_data.collections:
            clothes_bone_names.update(b.name for b in arm_data.collections["Clothes"].bones if not is_physics_ignored(b.name))

    # Fallback or additional keyword detection if collections are empty
    hair_keywords = [
        "hair", "eardrop", "headline", "ahoge", "bangs", "ponytail", "twintail", "bone00"
    ]
    clothes_keywords = [
        "ribbon", "sleeve", "strap", "skirt", "button", "belt", "cloth", "dress",
        "cape", "coat", "hem", "scarf", "tassel", "string", "chain", "acc",
        "qun", "xiu", "sce", "tail", "amice", "pants", "sock", "shoe",
        "necklace", "earring", "pendant", "badge", "breast", "overcoat"
    ]

    for b in arm_data.bones:
        b_name = b.name
        if is_physics_ignored(b_name):
            continue
        b_low = b_name.lower()

        if b_name not in hair_bone_names and b_name not in clothes_bone_names:
            if any(k in b_low for k in hair_keywords) or "+Hair" in b_name or "+hair" in b_name:
                hair_bone_names.add(b_name)
            elif any(k in b_low for k in clothes_keywords) or (
                b_name.startswith("+") and "+Hair" not in b_name and "+hair" not in b_name
            ):
                clothes_bone_names.add(b_name)
            elif "amice" in b_low:
                clothes_bone_names.add(b_name)

    # Double check all bones are not in ignore list
    hair_bone_names = {b for b in hair_bone_names if not is_physics_ignored(b)}
    clothes_bone_names = {b for b in clothes_bone_names if not is_physics_ignored(b)}

    # Remove previous Damped Track physics constraints to prevent duplicates
    for b_name in (hair_bone_names | clothes_bone_names):
        pb = armature_obj.pose.bones.get(b_name)
        if pb:
            try:
                arm_data.bones[b_name].hide = False
                pb.bone.hide = False
            except Exception:
                pass
            for c in list(pb.constraints):
                if c.type == "DAMPED_TRACK" and (
                    "physics" in c.name.lower()
                    or c.name in ["Damped Track", "Hair_Physics_DampedTrack", "Clothes_Physics_DampedTrack"]
                ):
                    pb.constraints.remove(c)

    def is_contiguous_chain_child(parent_bone_name, child_bone_name):
        p_bone = arm_data.bones.get(parent_bone_name)
        c_bone = arm_data.bones.get(child_bone_name)
        if not p_bone or not c_bone:
            return False
        if c_bone.use_connect:
            return True
        gap = (c_bone.head_local - p_bone.tail_local).length
        # In a contiguous chain/strand, child head is placed directly at parent tail.
        # Separated hub/root bones have a large spatial gap to strand heads.
        allowed_gap = max(0.02, 0.15 * p_bone.length)
        return gap <= allowed_gap

    def pick_best_child(parent_name, children_list):
        if not children_list:
            return None
        if len(children_list) == 1:
            return children_list[0]
        def common_prefix_len(s1, s2):
            count = 0
            for a, b in zip(s1, s2):
                if a == b:
                    count += 1
                else:
                    break
            return count
        return max(children_list, key=lambda c: common_prefix_len(parent_name, c.name))

    applied_count = 0

    # 1. Apply Damped Track to Hair parent bones pointing to their contiguous child bone
    for b_name in hair_bone_names:
        pb = armature_obj.pose.bones.get(b_name)
        if not pb:
            continue

        hair_children = [
            c for c in pb.children 
            if c.name in hair_bone_names and is_contiguous_chain_child(b_name, c.name)
        ]
        if hair_children:
            child_pb = pick_best_child(b_name, hair_children)
            if child_pb:
                dt = pb.constraints.new("DAMPED_TRACK")
                dt.name = "Damped Track"
                dt.target = armature_obj
                dt.subtarget = child_pb.name
                dt.influence = hair_influence
                applied_count += 1

    # 2. Apply Damped Track to Clothes / Dress parent bones pointing to their contiguous child bone
    for b_name in clothes_bone_names:
        pb = armature_obj.pose.bones.get(b_name)
        if not pb:
            continue

        clothes_children = [
            c for c in pb.children 
            if (c.name in clothes_bone_names or c.name in hair_bone_names) and is_contiguous_chain_child(b_name, c.name)
        ]
        if clothes_children:
            child_pb = pick_best_child(b_name, clothes_children)
            if child_pb:
                dt = pb.constraints.new("DAMPED_TRACK")
                dt.name = "Damped Track"
                dt.target = armature_obj
                dt.subtarget = child_pb.name
                dt.influence = clothes_influence
                applied_count += 1

    # Hide Hair and Clothes collections / layers after applying constraints
    if is_v4 and hasattr(arm_data, "collections"):
        for coll_name in ["Hair", "Clothes", "Dress"]:
            if coll_name in arm_data.collections:
                arm_data.collections[coll_name].is_visible = False
    else:
        if len(arm_data.layers) > 22:
            arm_data.layers[20] = False
            arm_data.layers[22] = False

    print(f"[PHYSICS] Applied Damped Track physics to {applied_count} Hair & Clothes bones (Hair: {hair_influence}, Clothes: {clothes_influence}) and hidden physics collections.")
    return applied_count


# Compatibility alias
apply_hair_and_dress_physics = apply_hair_and_clothes_physics
