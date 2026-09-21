# Authors: enthralpy, Llama.jpg, michael-gh1
# Standardized Rig UI Utilities for Gacha Setup across all games (Genshin, HSR, ZZZ, NTE, NPC)

import os
import re
import bpy
import mathutils
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
        'Iroi rpg 3' -> 'Iroi'
        'iroi rpg3' -> 'Iroi'
    """
    if not raw_name:
        return "Character"
    name = str(raw_name).replace(".001", "").replace(".002", "").replace("Rig", "").replace("rig", "").strip()
    name = name.split("Costume")[0]

    noise_tokens = {
        "avatar", "armature", "model", "mesh", "ui", "costume", "root", "fbx", "pmx",
        "uemodel", "uimodel", "uim", "00", "01", "02", "03", "04", "000", "grp", "group",
        "skin", "joint", "rig", "char", "character",
        "female", "male", "lady", "girl", "boy", "loli", "size01", "size02", "size03",
        "size04", "npc", "base", "main", "common", "high", "low", "body", "face", "hair",
        "eye", "eyes", "eyerig", "facerig",
        "lighting", "panel", "wgt", "wgts", "lights", "light", "lod", "lod0", "lod1", "lod2", "lod3",
        "skeleton", "skel", "art", "player", "chr", "s", "actor",
        # Generic variant / release tags (outfit versions, test builds). These
        # describe WHICH costume/build it is, never WHO the character is.
        # NOTE: internal character codenames (e.g. NTE 'radio' for Linko,
        # 'oneiroi' for Iroi) must NOT be listed here: stripping them turns a
        # consistent codename signal into garbage ('level3', '').
        "rpg", "game", "cbt", "cbt1", "cbt2", "mod", "patch",
        "fashion", "level", "style", "variant", "variants",
        "swimsuit", "outfit", "dress", "morpher", "morph",
    }

    parts = [p for p in re.split(r"[_\-\s.]+", name) if p]
    filtered = []
    for p in parts:
        low = p.lower()
        if low.isdigit() or low in noise_tokens:
            continue
        base = re.sub(r"\d+$", "", low)
        if base in noise_tokens:
            continue
        filtered.append(p)

    if filtered:
        picked = filtered[0] if len(filtered) == 1 else filtered[-1]
        return _capitalize_name_token(picked)
    return "Character"


# ---------------------------------------------------------------------------
# Character name resolution + collection packaging shared by HSR / AKE / NTE.
#
# Root cause fixed here: FBX/UEFormat imports often name the armature something
# generic ("Armature", "Root", "..._Skeleton"), and deriving the character name
# from it alone produced collections literally called "Armature"/"Skeleton".
# The resolver below prefers stronger signals first (existing character
# collection from the import step, model folder, model file stem) and only
# falls back to the armature name last, mirroring what ZZZ/Genshin/WuWa get
# for free from their "Avatar_Xxx" armature names.
# ---------------------------------------------------------------------------

# extract_clean_character_name() results that must NOT become collection names.
# NOTE: keep this set strictly generic (rig/scene words). Internal character
# codenames (e.g. NTE 'radio', 'oneiroi') must NOT be listed: rejecting them
# here only pushes the resolver toward worse fallbacks ('level3', '').
_GENERIC_RIG_NAME_RESULTS = {
    "armature", "character", "char", "root", "rig", "rigify", "metarig",
    "skeleton", "skel", "mesh", "model", "object", "collection", "scene",
    "body", "face", "hair",
    "lod", "lod0", "lod1", "lod2", "lod3",
}

# Noise tokens for parsing model/mesh file stems (lowercase).
_STEM_NOISE_TOKENS = {
    "avatar", "art", "player", "chr", "s", "actor", "npc",
    "armature", "model", "mesh", "fbx", "pmx", "uemodel", "uimodel", "uim",
    "ui", "costume", "root", "rig", "char", "character",
    "female", "male", "lady", "girl", "boy", "loli",
    "size01", "size02", "size03", "size04",
    "base", "main", "common", "high", "low", "grp", "group",
    "skin", "body", "face", "hair", "eye", "eyes",
    "lod", "lod0", "lod1", "lod2", "lod3",
    "skeleton", "skel",
    # Generic variant / release tags, never character identity (see note above).
    "rpg", "game", "cbt", "cbt1", "cbt2", "mod", "patch",
    "fashion", "level", "style", "variant", "variants",
    "swimsuit", "outfit", "dress", "morpher", "morph",
}

# Folder basenames that carry no character identity (step one level up is also
# useless, so they are skipped entirely as name sources).
_ASSET_DIR_NAMES = {
    "textures", "texture", "materials", "material", "maps", "images",
    "shaders", "shader", "assets", "asset", "models", "model", "fbx",
    "blend", "blends", "chars", "characters", "common", "shared",
}


def _capitalize_name_token(token):
    """Capitalizes all-lowercase tokens (firefly -> Firefly), leaves the rest."""
    if token and token.islower():
        return token[:1].upper() + token[1:]
    return token


def _stem_tokens(stem):
    return [t for t in re.split(r"[_\-\s.]+", str(stem or "")) if t]


def _parse_stem_name(stem, prefer="last"):
    """Reduces a file/mesh stem to a character candidate.

    Drops noise tokens (art/avatar/chr/lod*/digits/...) and returns the last
    (file stems: Art_Firefly_01 -> Firefly) or first surviving token.
    Tokens with glued trailing digits are checked against their digit-free
    base (fashion1 -> fashion -> noise) so variant tags never win; a picked
    token like 'radio072' is normalized back to its base ('radio').
    Returns "" when nothing meaningful survives.
    """
    survivors = []
    for t in _stem_tokens(stem):
        low = t.lower()
        if low in _STEM_NOISE_TOKENS or t.isdigit():
            continue
        base = re.sub(r"\d+$", "", low)
        if base in _STEM_NOISE_TOKENS:
            continue
        survivors.append(t)
    if not survivors:
        return ""
    picked = survivors[0] if prefer == "first" else survivors[-1]
    # Normalize glued asset ids: 'radio072' -> 'radio' (same codename vote as
    # 'player_072_radio_...'). Tokens whose base is noise were filtered above.
    base = re.sub(r"\d+$", "", picked)
    if base and len(base) >= 2:
        picked = base
    return _capitalize_name_token(picked)


def _parse_folder_name(folder):
    """Character candidate from a model folder basename (first survivor).

    "Zankou swimsuit" -> Zankou, "firefly-spring-missive" -> Firefly,
    "Perlica" -> Perlica. Returns "" for generic asset folders.
    """
    base = os.path.basename(os.path.normpath(str(folder or "")))
    if not base or base.lower() in _ASSET_DIR_NAMES:
        return ""
    return _parse_stem_name(base, prefer="first")


def _is_generic_rig_name(name):
    return not name or str(name).strip().lower() in _GENERIC_RIG_NAME_RESULTS


def _looks_like_technical_rig_name(name):
    """True when an armature/object name is an engine asset id, not a character.

    UEFormat/UE imports name armatures like 'player_072_radio_fashion1_skin'
    or 'player_075_oneir_skin_LOD0_Skeleton': engine prefix + numeric asset id
    + internal codename + variant/LOD suffixes. Deriving a collection name from
    these yields variant garbage ('Fashion1', 'level3') and duplicate
    collections. Structural markers only -- no per-character codenames.
    """
    low = re.sub(r"\.\d+$", "", str(name or "")).lower()
    if not low:
        return False
    if low.startswith(("player_", "art_", "s_actor", "sactor")):
        return True
    if "_player_" in low or "_art_" in low:
        return True
    if re.search(r"_\d{2,4}_", low):
        return True
    if low.endswith(("_skin", "_skel", "_skeleton", "_lod", "_lod0", "_lod1", "_lod2", "_lod3", "_morph", "_morpher")):
        return True
    if "_skin_" in low or "_lod" in low or "_morph" in low:
        return True
    return False


def _scene_rig_candidates(original_name, arm_obj):
    """Locate the pre-rig source armature object for collection inspection."""
    if arm_obj is not None and getattr(arm_obj, "type", None) == "ARMATURE":
        return arm_obj
    try:
        for obj_name in (original_name, str(original_name or "").replace("Rig", "")):
            obj = bpy.data.objects.get(obj_name)
            if obj is not None and getattr(obj, "type", None) == "ARMATURE":
                return obj
    except Exception:
        pass
    return None


def resolve_rig_character_name(original_name, arm_obj=None, mesh_names=None, actor_regex=None):
    """Derives the character name for rig/collection naming (HSR/AKE/NTE).

    Priority (first non-generic hit wins):
      1. extract_clean_character_name(armature) when it is meaningful
         (preserves every currently-working case: Avatar_Xxx, Miyabi...).
      2. Existing non-default collection already holding the armature/meshes
         (e.g. "Iroi" created by the NTE import packaging step).
      3. Model folder basename (Perlica, Iroi, Zankou swimsuit -> Zankou).
      4. Model file stem from scene import props (Art_Firefly_01 -> Firefly).
      5. AKE-style actor_ mesh pattern (S_actor_pelica_... -> Pelica).
      6. Mesh names via stem parsing (most common winner).
      7. Armature extract result / "Character" as last resort.
    """
    try:
        scene = bpy.context.scene
    except Exception:
        scene = None

    arm_extracted = ""
    try:
        arm_extracted = extract_clean_character_name(original_name or "")
    except Exception:
        arm_extracted = ""

    # 1. Armature name is already meaningful: keep current behavior verbatim.
    # Skip engine asset ids (UEFormat 'player_072_radio_fashion1_skin'): their
    # parsed result is variant garbage ('Fashion1'), which would create a
    # duplicate collection instead of reusing the packaged one ('Linko').
    # The existing-collection / folder / file steps below resolve those.
    if arm_extracted and not _is_generic_rig_name(arm_extracted) \
            and not _looks_like_technical_rig_name(original_name):
        return arm_extracted

    # 2. Existing character collection (import step may have packaged already).
    try:
        arm_candidate = _scene_rig_candidates(original_name, arm_obj)
        pool = []
        if arm_candidate is not None:
            pool.append(arm_candidate)
        try:
            for mesh in _iter_rig_meshes_for_name(arm_candidate):
                pool.append(mesh)
        except Exception:
            pass
        if mesh_names:
            for mesh_name in mesh_names:
                m_obj = bpy.data.objects.get(str(mesh_name))
                if m_obj is not None:
                    pool.append(m_obj)
        seen_colls = set()
        for obj in pool:
            try:
                user_colls = list(getattr(obj, "users_collection", []) or [])
            except Exception:
                continue
            for coll in user_colls:
                coll_name = getattr(coll, "name", "")
                if not coll_name or coll_name in seen_colls:
                    continue
                seen_colls.add(coll_name)
                low = coll_name.lower()
                if low in ("collection", "master collection", "scene collection"):
                    continue
                if low.startswith(("wgts", "wgt")) or "widget" in low:
                    continue
                if _is_generic_rig_name(coll_name):
                    continue
                # The collection itself may need cleaning (slugs), reuse folder logic.
                cleaned = _parse_stem_name(coll_name, prefer="first")
                return cleaned or coll_name
    except Exception:
        pass

    # 3. Model folder basename.
    try:
        model_dir = (scene.get("setup_wizard_imported_model_dir") if scene else "") or ""
        folder_hit = _parse_folder_name(model_dir)
        if folder_hit and not _is_generic_rig_name(folder_hit):
            return folder_hit
    except Exception:
        pass

    # 4. Model file stem recorded at import time.
    try:
        for key in ("setup_wizard_imported_fbx_path", "setup_wizard_imported_uemodel_path"):
            model_file = (scene.get(key) if scene else "") or ""
            if model_file:
                stem = os.path.splitext(os.path.basename(model_file))[0]
                stem_hit = _parse_stem_name(stem)
                if stem_hit and not _is_generic_rig_name(stem_hit):
                    return stem_hit
    except Exception:
        pass

    # 5. Game-specific actor pattern (AKE: S_actor_pelica_body_01_lod0).
    try:
        if actor_regex:
            pattern = re.compile(actor_regex, re.IGNORECASE)
            names_to_scan = list(mesh_names or [])
            try:
                names_to_scan.extend(
                    o.name for o in bpy.data.objects if getattr(o, "type", None) == "MESH"
                )
            except Exception:
                pass
            for mesh_name in names_to_scan:
                match = pattern.search(str(mesh_name))
                if match:
                    candidate = _capitalize_name_token(match.group(1))
                    if candidate and not _is_generic_rig_name(candidate):
                        return candidate
    except Exception:
        pass

    # 6. Mesh names via stem parsing (most common winner).
    try:
        votes = {}
        names_to_scan = list(mesh_names or [])
        if not names_to_scan:
            try:
                names_to_scan = [
                    o.name for o in bpy.data.objects if getattr(o, "type", None) == "MESH"
                ]
            except Exception:
                names_to_scan = []
        for mesh_name in names_to_scan:
            candidate = _parse_stem_name(os.path.splitext(str(mesh_name))[0])
            if candidate and not _is_generic_rig_name(candidate):
                votes[candidate] = votes.get(candidate, 0) + 1
        if votes:
            return sorted(votes.items(), key=lambda item: (-item[1], item[0]))[0][0]
    except Exception:
        pass

    # 7. Last resort: whatever the armature extract gave (even generic), else Character.
    return arm_extracted or "Character"


def _iter_rig_meshes_for_name(arm):
    """Meshes parented to / deforming with an armature (name-resolution use)."""
    if arm is None:
        return
    seen = set()
    try:
        for child in getattr(arm, "children_recursive", []) or []:
            if getattr(child, "type", None) == "MESH" and child.name not in seen:
                seen.add(child.name)
                yield child
    except Exception:
        pass
    try:
        for obj in bpy.data.objects:
            if getattr(obj, "type", None) != "MESH" or obj.name in seen:
                continue
            bound = False
            try:
                for mod in getattr(obj, "modifiers", []) or []:
                    if getattr(mod, "type", "") == "ARMATURE" and getattr(mod, "object", None) == arm:
                        bound = True
                        break
            except Exception:
                pass
            if bound:
                seen.add(obj.name)
                yield obj
    except Exception:
        pass


def ensure_character_collection(context, rig_obj, char_name):
    """Packages rig + meshes into a top-level collection named after the character.

    Shared by HSR/AKE/NTE (parity with Genshin/ZZZ/WuWa): the isolated worker
    manifest only links top-level collections, so everything character-related
    must live inside '<CharName>' with WGTS_<Char> nested in it — never loose
    in the Scene Collection nor mixed into the default 'Collection'.
    Multi-character safe: objects already living in another named (non-default,
    non-widget) collection are never stolen; only the rig, meshes bound to it,
    members of default-named collections and scene-root orphans are gathered.
    Returns the character collection.
    """
    if not char_name:
        char_name = "Character"
    char_name = str(char_name)
    try:
        scene = getattr(context, "scene", None) if context is not None else None
    except Exception:
        scene = None
    if scene is None:
        scene = bpy.context.scene

    default_names = {"collection", "master collection", "scene collection"}

    def _is_wgts(coll):
        try:
            n = str(getattr(coll, "name", "")).lower()
            return n.startswith("wgts") or n.startswith("wgt") or "widget" in n
        except Exception:
            return False

    def _is_default(coll):
        try:
            return str(getattr(coll, "name", "")).lower() in default_names
        except Exception:
            return False

    def _matches_char(coll_name):
        if not coll_name or str(coll_name).lower() in default_names:
            return False
        clean = _parse_stem_name(coll_name, prefer="first") or extract_clean_character_name(coll_name)
        if clean and clean.lower() == char_name.lower():
            return True
        coll_low = coll_name.lower()
        char_low = char_name.lower()
        if coll_low.startswith(char_low):
            return True
        # Character name appears as a whole token inside the collection name
        # (e.g. 'Linko fashion 1' contains 'Linko').
        try:
            if char_low in re.split(r"[_\-\s.]+", coll_low):
                return True
        except Exception:
            pass
        return False

    try:
        previous_colls = list(getattr(rig_obj, "users_collection", []) or []) if rig_obj is not None else []
    except Exception:
        previous_colls = []

    char_coll = bpy.data.collections.get(char_name)

    # If the collection '<char_name>' does not exist yet, check if rig_obj is in an
    # existing non-default collection whose name matches or cleans to char_name
    # (e.g. "Iroi rpg 3" -> cleans to "Iroi"). Rename it in place to unify the
    # collection and avoid creating a duplicate!
    if char_coll is None and rig_obj is not None:
        for coll in previous_colls:
            if not _is_default(coll) and not _is_wgts(coll) and _matches_char(coll.name):
                old_name = coll.name
                coll.name = char_name
                char_coll = coll
                print(f"[RIG UI] Renamed existing character collection '{old_name}' -> '{char_name}'")
                break

    if char_coll is None:
        char_coll = bpy.data.collections.new(char_name)
    if char_coll.name not in scene.collection.children:
        try:
            scene.collection.children.link(char_coll)
        except Exception:
            pass

    # WGTS_<Char> always nested, never at scene root (Append brings only its own).
    try:
        from setup_wizard.character_rig_setup.wgts_isolation import get_or_create_char_wgts
        get_or_create_char_wgts(char_coll, char_name)
    except Exception:
        pass

    if rig_obj is None:
        return char_coll

    # Identify any leftover collections from which this character is being migrated
    # (e.g. if 'Iroi' already existed but 'Iroi rpg 3' was also present).
    own_colls = set()
    for coll in previous_colls:
        if coll != char_coll and not _is_default(coll) and not _is_wgts(coll):
            if _matches_char(coll.name):
                own_colls.add(coll)

    def _in_foreign_char_collection(obj):
        """True if the object already belongs to another character's collection."""
        try:
            for coll in list(getattr(obj, "users_collection", []) or []):
                if coll == char_coll or _is_wgts(coll) or _is_default(coll) or coll in own_colls:
                    continue
                return True
        except Exception:
            pass
        return False

    def _link_no_dup(coll, obj):
        try:
            if obj.name not in coll.objects:
                coll.objects.link(obj)
        except Exception:
            pass

    # 1. Rig always inside the character collection.
    _link_no_dup(char_coll, rig_obj)

    # 2. Meshes bound to this rig (ARMATURE modifier) + rig children.
    bound = set()
    try:
        for child in getattr(rig_obj, "children_recursive", []) or []:
            if getattr(child, "type", None) in ("MESH", "CURVE", "EMPTY", "LIGHT"):
                bound.add(child)
    except Exception:
        pass
    try:
        for obj in list(bpy.data.objects):
            if getattr(obj, "type", None) != "MESH":
                continue
            try:
                for mod in getattr(obj, "modifiers", []) or []:
                    if getattr(mod, "type", "") == "ARMATURE" and getattr(mod, "object", None) == rig_obj:
                        bound.add(obj)
                        break
            except Exception:
                continue
    except Exception:
        pass
    for obj in list(bound):
        _link_no_dup(char_coll, obj)

    # 3. Members of the rig's previous default-named collections (e.g. the FBX
    # 'Collection'): migrate rig-related or unclaimed members, never meshes
    # bound to a different armature.
    for old_coll in previous_colls:
        if old_coll == char_coll or _is_wgts(old_coll) or not _is_default(old_coll):
            continue
        for member in list(getattr(old_coll, "objects", []) or []):
            try:
                m_type = getattr(member, "type", None)
                if m_type not in ("MESH", "ARMATURE", "EMPTY", "CURVE", "LIGHT"):
                    continue
                if _in_foreign_char_collection(member):
                    continue
                if m_type == "MESH" and member not in bound:
                    claimed = False
                    try:
                        for mod in getattr(member, "modifiers", []) or []:
                            target = getattr(mod, "object", None)
                            if getattr(mod, "type", "") == "ARMATURE" and target is not None and target != rig_obj:
                                claimed = True
                                break
                    except Exception:
                        pass
                    if claimed:
                        continue
                _link_no_dup(char_coll, member)
            except Exception:
                continue

    # 4. Scene-root orphans (appended shapes, UEFormat leftovers): adopt them
    # unless they already belong to another character collection.
    try:
        root_objects = list(getattr(scene.collection, "objects", []) or [])
    except Exception:
        root_objects = []
    for loose in root_objects:
        try:
            if getattr(loose, "type", None) not in ("MESH", "ARMATURE", "EMPTY", "CURVE", "LIGHT"):
                continue
            if _in_foreign_char_collection(loose):
                continue
            _link_no_dup(char_coll, loose)
        except Exception:
            continue

    # 5. Unlink rig + gathered meshes from default-named collections and own_colls.
    for obj in [rig_obj] + list(bound):
        try:
            user_colls = list(getattr(obj, "users_collection", []) or [])
        except Exception:
            continue
        for ucoll in user_colls:
            if ucoll == char_coll or _is_wgts(ucoll):
                continue
            if _is_default(ucoll) or ucoll in own_colls:
                try:
                    ucoll.objects.unlink(obj)
                except Exception:
                    pass

    # Ensure rig_obj ONLY lives in char_coll (never left in any extra collection except WGTS).
    for ucoll in list(getattr(rig_obj, "users_collection", []) or []):
        if ucoll != char_coll and not _is_wgts(ucoll):
            try:
                ucoll.objects.unlink(rig_obj)
            except Exception:
                pass

    # Clean up empty leftover collections from own_colls (e.g. old 'Iroi rpg 3').
    for old_c in list(own_colls):
        if old_c != char_coll and len(getattr(old_c, "objects", []) or []) == 0 and len(getattr(old_c, "children", []) or []) == 0:
            try:
                for parent_c in list(bpy.data.collections):
                    if old_c.name in parent_c.children:
                        parent_c.children.unlink(old_c)
            except Exception:
                pass
            try:
                if old_c.name in scene.collection.children:
                    scene.collection.children.unlink(old_c)
            except Exception:
                pass
            try:
                bpy.data.collections.remove(old_c, do_unlink=True)
            except Exception:
                pass

    # 6. Remove the default 'Collection' when it ended up empty.
    try:
        stray = bpy.data.collections.get("Collection")
        if stray is not None and stray != char_coll:
            if len(getattr(stray, "objects", []) or []) == 0 and len(getattr(stray, "children", []) or []) == 0:
                try:
                    scene.collection.children.unlink(stray)
                except Exception:
                    pass
                try:
                    bpy.data.collections.remove(stray, do_unlink=True)
                except Exception:
                    pass
    except Exception:
        pass

    return char_coll


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
    "Weapon",
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
    Clears existing bone collections and initializes standard bone collections in Blender 4.0+.
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

    # Initial visibility: Face, Torso (IK), Fingers, Arm.L/R (IK), Leg.L/R (IK), Root, Lighting visible (Weapon visible only if model has weapon)
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
        if collection_name == "Other":
            for c in list(bone.collections):
                if c.name not in ["Other", "Others"]:
                    try:
                        c.unassign(bone)
                    except Exception:
                        pass
        elif other_coll:
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
    detect_prop_keyword=True,
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
        "root.001", "torso.001", "torso.002",
        "hand_ik_wrist.L", "hand_ik_wrist.R",
        "foot_ik_sub.L", "foot_ik_sub.R",
    ], 26, "Offsets")

    # 5. Weapon & Props
    fast_move(["prop.L", "prop.R"], 21, "Weapon")
    fast_move(["prop.L", "prop.R"], 21, "Props")
    weapon_keywords = ["prop1", "prop2", "bip001 prop", "weapon", "garape", "grape", "equip"]
    if not detect_prop_keyword:
        # NTE: la palabra 'prop' da falsos positivos (accesorios/escena); se ignora.
        # Se mantienen 'weapon' y el resto de detectores.
        weapon_keywords = [k for k in weapon_keywords if "prop" not in k]
    for b in arm_data.bones:
        b_name = b.name
        b_low = b_name.lower()
        if (
            b_name in ["prop.L", "prop.R"]
            or any(k in b_low for k in weapon_keywords)
            or (detect_prop_keyword and "prop" in b_low and "parent" not in b_low)
            or "_wpn_" in b_low
            or "_weapon_" in b_low
            or "_garape_" in b_low
            or "_grape_" in b_low
            or "garape" in b_low
            or "grape" in b_low
        ):
            if not b_name.startswith("MCH-") and not b_name.startswith("ORG-"):
                b2c(b_name, 21, "Weapon")
                b2c(b_name, 21, "Props")

    if is_version_4:
        arm_colls = getattr(arm_data, "collections", None)
        if arm_colls:
            for w_name in ["Weapon", "Props"]:
                w_c = arm_colls.get(w_name)
                if w_c:
                    has_w = any(b.name not in ["prop.L", "prop.R"] for b in w_c.bones)
                    w_c.is_visible = has_w
    else:
        has_w = any(b.name not in ["prop.L", "prop.R"] and b.layers[21] for b in arm_data.bones)
        arm_data.layers[21] = has_w

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
    b2c("root", 28, "Root")
    b2c("root_2", 28, "Root")
    if "root.002" in arm_data.bones:
        b2c("root.002", 28, "Root")

    # 20 & 21. Hair & Clothes & Breasts
    fast_move(["breast.L", "breast.R"], 3, "Torso (IK)")
    fast_move(["DEF-breast.L", "DEF-breast.R"], 25, "Other")

    clothes_keywords = [
        "ribbon", "sleeve", "strap", "skirt", "button", "belt", "cloth", "dress",
        "cape", "coat", "hem", "scarf", "tassel", "string", "chain", "acc",
        "qun", "xiu", "sce", "tail", "amice", "pants", "sock", "shoe",
        "necklace", "earring", "pendant", "badge", "prop"
    ]
    hair_keywords = [
        "hair", "eardrop", "headline", "ahoge", "bangs", "ponytail", "twintail", "bone00",
        "plait", "braid", "toufa"
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
        # If the bone has already been explicitly placed in an active collection (e.g. Hair, Clothes, Weapon, Props, Face), do not demote to Other
        if is_version_4 and hasattr(b, "collections"):
            assigned_colls = {c.name for c in b.collections if c.name != "Other"}
            if assigned_colls:
                continue
        elif not is_version_4 and hasattr(b, "layers"):
            active_layers = [i for i in range(32) if b.layers[i] and i != 25]
            if active_layers:
                continue

        if (
            b_name.startswith("DEF-")
            or b_name.startswith("MCH-")
            or b_name.startswith("ORG-")
            or b_name.startswith("Bon_")
            or b_name.startswith("BON_")
            or b_name.startswith("Bone-")
            or (b_name.startswith("Bip") and not any(k in b_low for k in ["prop", "weapon"]))
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

    def make_weapon_layer_str(vers, title=""):
        if vers == 3:
            return f"row.prop(context.active_object.data, 'layers', index=21, toggle=True, text='Weapon')"
        r = f"row_{title}." if title else "row."
        return (
            f"if 'Weapon' in collection: {r}prop(collection['Weapon'], 'is_visible', toggle=True, text='Weapon')\n"
            f"            elif 'Props' in collection: {r}prop(collection['Props'], 'is_visible', toggle=True, text='Weapon')"
        )

    def make_weapon_solo_str(title=""):
        r = f"row_{title}." if title else "row."
        return (
            f"if 'Weapon' in collection: {r}prop(collection['Weapon'], 'is_solo', toggle=True, text='★')\n"
            f"            elif 'Props' in collection: {r}prop(collection['Props'], 'is_solo', toggle=True, text='★')"
        )

    def layers_to_generate(vers):
        if vers == 3:
            return (
                "\n            row = col.row()\n            " + make_layer_str("Tweaks", 2, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Pivots & Pins", 19, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Offsets", 26, vers) +
                "\n            row = col.row()\n            " + make_weapon_layer_str(vers) +
                "\n            row = col.row()\n            row.separator()" +
                "\n            row = col.row()\n            row.separator()" +
                "\n            row = col.row()\n            " + make_layer_str("Face", 0, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Face (Detail)", 1, vers) +
                "\n            row = col.row()\n            " + make_layer_str("Face (Primary)", 29, vers) +
                "\n            " + make_layer_str("Face (Secondary)", 30, vers) +
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
                # Offsets / Weapon (Props)
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Offsets", 26, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Offsets", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_weapon_layer_str(vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_weapon_solo_str("pivots") +
                # Spacers
                "\n            row = col.row()" +
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
                "\n            row = col.row()" +
                # Face (Detail)
                "\n            if 'Face (Detail)' in collection:\n" +
                "                row = col.row()\n" +
                "                split = row.split(align=True, factor=split_size)\n" +
                "                row = split.row(align=True)\n" +
                "                row.prop(collection['Face (Detail)'], 'is_visible', toggle=True, text='Face (Detail)')\n" +
                "                row = split.row(align=True)\n" +
                "                row.prop(collection['Face (Detail)'], 'is_solo', toggle=True, text='★')\n" +
                "            elif 'Facerig Detail' in collection:\n" +
                "                row = col.row()\n" +
                "                split = row.split(align=True, factor=split_size)\n" +
                "                row = split.row(align=True)\n" +
                "                row.prop(collection['Facerig Detail'], 'is_visible', toggle=True, text='Facerig Detail')\n" +
                "                row = split.row(align=True)\n" +
                "                row.prop(collection['Facerig Detail'], 'is_solo', toggle=True, text='★')" +
                "\n            row = col.row()" +
                # Face (Primary) / Face (Secondary)
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_layer_str("Face (Primary)", 29, vers, "tweaks") +
                "\n            row_tweaks = split.row(align=True)" +
                "\n            " + make_solo_str("Face (Primary)", "tweaks") +
                "\n            split = row.split(factor=split_small, align=True)" +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_layer_str("Face (Secondary)", 30, vers, "pivots") +
                "\n            row_pivots = split.row(align=True)" +
                "\n            " + make_solo_str("Face (Secondary)", "pivots") +
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
                # Tails (only drawn when the rig has a Tails bone collection, e.g. ZZZ)
                "\n            split = row.split(align=True, factor=split_size)" +
                "\n            row = split.row(align=True)" +
                "\n            " + make_layer_str("Tails", 22, vers) +
                "\n            row = split.row(align=True)" +
                "\n            " + make_solo_str("Tails") +
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
        "\n            arm_obj = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else None" +
        "\n            if not arm_obj:" +
        "\n                try:" +
        "\n                    from setup_wizard.ui.character_settings_utils import resolve_settings_armature" +
        "\n                    arm_obj = resolve_settings_armature(context)" +
        "\n                except Exception:" +
        "\n                    pass" +
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

    # Set Rig Properties header and order (order 2) - COLLAPSED by default
    prop_replacement = 'bl_label = "Rig Properties: " + rig_name\n    bl_order = 2\n    bl_options = {\'DEFAULT_CLOSED\'}'
    if 'bl_label = "Rig Properties: " + rig_name\n    bl_order = 2' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Rig Properties: " + rig_name\n    bl_order = 2',
            prop_replacement
        )
    elif 'bl_label = "Rig Main Properties"' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Rig Main Properties"',
            prop_replacement
        )
    elif 'bl_label = "Properties"' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Properties"',
            prop_replacement
        )
    elif 'bl_label = "Rig Properties: " + rig_name' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Rig Properties: " + rig_name',
            prop_replacement
        )

    # Set Rig Layers header and order (order 3) - COLLAPSED by default
    layers_replacement = 'bl_label = "Rig Layers: " + rig_name\n    bl_order = 3\n    bl_options = {\'DEFAULT_CLOSED\'}'
    if 'bl_label = "Rig Layers: " + rig_name\n    bl_order = 1' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Rig Layers: " + rig_name\n    bl_order = 1',
            layers_replacement
        )
    elif 'bl_label = "Rig Layers"' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Rig Layers"',
            layers_replacement
        )
    elif 'bl_label = "Rig Layers: " + rig_name' in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(
            'bl_label = "Rig Layers: " + rig_name',
            layers_replacement
        )

    # Upgrade RigLayers.poll to resolve armature from selection (matching Character Settings)
    layers_poll_old = """    @classmethod
    def poll(cls, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False"""

    layers_poll_new = """    @classmethod
    def poll(cls, context):
        try:
            act = getattr(context, "active_object", None)
            if act and getattr(act, "type", None) == 'ARMATURE' and getattr(act, "data", None) and act.data.get("rig_id") == rig_id:
                return True
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
            if arm and getattr(arm, "data", None) and arm.data.get("rig_id") == rig_id:
                return True
        except Exception:
            pass
        return False"""

    if layers_poll_old in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(layers_poll_old, layers_poll_new)

    # Upgrade RigUI.poll to resolve armature from selection (matching Character Settings)
    ui_poll_old = """    @classmethod
    def poll(cls, context):
        if context.mode != 'POSE':
            return False
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False"""

    ui_poll_new = """    @classmethod
    def poll(cls, context):
        if context.mode != 'POSE':
            return False
        try:
            act = getattr(context, "active_object", None)
            if act and getattr(act, "type", None) == 'ARMATURE' and getattr(act, "data", None) and act.data.get("rig_id") == rig_id:
                return True
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
            if arm and getattr(arm, "data", None) and arm.data.get("rig_id") == rig_id:
                return True
        except Exception:
            pass
        return False"""

    if ui_poll_old in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(ui_poll_old, ui_poll_new)

    # Upgrade RigUI.draw to resolve armature from selection
    ui_draw_old = """    def draw(self, context):
        layout = self.layout
        pose_bones = context.active_object.pose.bones"""

    ui_draw_new = """    def draw(self, context):
        layout = self.layout
        arm = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else None
        if not arm:
            try:
                from setup_wizard.ui.character_settings_utils import resolve_settings_armature
                arm = resolve_settings_armature(context)
            except Exception:
                pass
        if not arm or not getattr(arm, "pose", None):
            return
        pose_bones = arm.pose.bones"""

    if ui_draw_old in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(ui_draw_old, ui_draw_new)

    # Safe selected_bones try-block and persistent General Settings box in RigUI.draw
    old_sel_block = """        try:
            selected_bones = set(bone.name for bone in context.selected_pose_bones)
            selected_bones.add(context.active_pose_bone.name)
        except (AttributeError, TypeError):
            return"""

    new_sel_block = """        selected_bones = set()
        if getattr(context, "selected_pose_bones", None):
            selected_bones.update(b.name for b in context.selected_pose_bones)
        if getattr(context, "active_pose_bone", None):
            selected_bones.add(context.active_pose_bone.name)"""

    if old_sel_block in complete_rig_text:
        complete_rig_text = complete_rig_text.replace(old_sel_block, new_sel_block)

    # Strip any persistent General Settings on non-selected bones so settings only appear when plate-settings is selected
    complete_rig_text = re.sub(
        r'^\s*# General Settings \(accessible even without clicking plate-settings\)\s*\n\s*if "plate-settings" in pose_bones and not is_selected\(\{"plate-settings"\}\):.*?(?=\n\s*(?:#|if\s+|def\s+|\Z))',
        "",
        complete_rig_text,
        flags=re.MULTILINE | re.DOTALL,
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

    # Order 4: Reorder Custom Properties panel to be last (order 4) and collapsed by default
    properties_order_fix = """

def _reorder_and_collapse_custom_properties():
    import bpy
    for cls_name in dir(bpy.types):
        if cls_name.startswith("VIEW3D_PT_"):
            cls = getattr(bpy.types, cls_name, None)
            if cls and getattr(cls, "bl_category", "") == "Item" and getattr(cls, "bl_label", "") in ["Properties", "Context Properties"]:
                try:
                    bpy.utils.unregister_class(cls)
                    cls.bl_order = 4
                    cls.bl_options = {'DEFAULT_CLOSED'}
                    bpy.utils.register_class(cls)
                except Exception:
                    pass

try:
    _reorder_and_collapse_custom_properties()
except Exception:
    pass
"""
    complete_rig_text += properties_order_fix

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

        # Enforce Properties panel order 4 and collapsed in active session
        for cls_name in dir(bpy.types):
            if cls_name.startswith("VIEW3D_PT_"):
                cls = getattr(bpy.types, cls_name, None)
                if cls and getattr(cls, "bl_category", "") == "Item" and getattr(cls, "bl_label", "") in ["Properties", "Context Properties"]:
                    try:
                        bpy.utils.unregister_class(cls)
                        cls.bl_order = 4
                        cls.bl_options = {'DEFAULT_CLOSED'}
                        bpy.utils.register_class(cls)
                    except Exception:
                        pass

        print(f"[RIG UI] Successfully updated and executed UI script for '{clean_char_name}'")
        return True
    except Exception as ex:
        print(f"[RIG UI] Notice running updated UI script: {ex}")
        return False


def find_target_armature(context=None, armature_obj=None):
    context = context or bpy.context
    if armature_obj and getattr(armature_obj, "type", None) == "ARMATURE":
        print(f"[GACHA SETUP LOG] find_target_armature: directly provided '{armature_obj.name}'")
        return armature_obj

    # 1. Check active object
    act = context.active_object or getattr(context, "object", None)
    if act:
        if act.type == "ARMATURE" and not act.name.startswith("WGT"):
            print(f"[GACHA SETUP LOG] find_target_armature: active object is armature '{act.name}'")
            return act
        if act.type == "MESH":
            if hasattr(act, "find_armature") and act.find_armature():
                arm = act.find_armature()
                print(f"[GACHA SETUP LOG] find_target_armature: found via active mesh.find_armature() -> '{arm.name}'")
                return arm
            for m in act.modifiers:
                if m.type == 'ARMATURE' and m.object:
                    print(f"[GACHA SETUP LOG] find_target_armature: found via active mesh modifier -> '{m.object.name}'")
                    return m.object
            if act.parent and act.parent.type == 'ARMATURE':
                print(f"[GACHA SETUP LOG] find_target_armature: found via active mesh parent -> '{act.parent.name}'")
                return act.parent

    # 2. Check selected objects
    for obj in context.selected_objects:
        if obj.type == "ARMATURE" and not obj.name.startswith("WGT"):
            print(f"[GACHA SETUP LOG] find_target_armature: found in selected objects -> '{obj.name}'")
            return obj
        if obj.type == "MESH":
            if hasattr(obj, "find_armature") and obj.find_armature():
                arm = obj.find_armature()
                print(f"[GACHA SETUP LOG] find_target_armature: found in selected mesh.find_armature() -> '{arm.name}'")
                return arm
            for m in obj.modifiers:
                if m.type == 'ARMATURE' and m.object:
                    print(f"[GACHA SETUP LOG] find_target_armature: found in selected mesh modifier -> '{m.object.name}'")
                    return m.object
            if obj.parent and obj.parent.type == 'ARMATURE':
                print(f"[GACHA SETUP LOG] find_target_armature: found in selected mesh parent -> '{obj.parent.name}'")
                return obj.parent

    # 3. Check scene / bpy.data objects (prioritize generated 'rig' / *Rig / Rig_* / armatures with pose bones over metarigs)
    all_objs = list(context.scene.objects) if context.scene else list(bpy.data.objects)
    armatures = [o for o in all_objs if o.type == "ARMATURE" and not o.name.startswith("WGT")]
    if armatures:
        def rig_priority(o):
            nl = o.name.lower()
            if 'metarig' in nl or 'rootshape' in nl or 'root_shape' in nl:
                return 0
            if nl == 'rig' or nl.startswith('rig_') or nl.endswith('rig') or 'rigify' in nl:
                return 100
            if nl.startswith('avatar_') or nl.startswith('char_'):
                return 50
            if o.pose and len(o.pose.bones) > 0:
                return 20
            return 1
        armatures.sort(key=rig_priority, reverse=True)
        chosen = armatures[0]
        print(f"[GACHA SETUP LOG] find_target_armature: picked highest priority scene armature -> '{chosen.name}'")
        return chosen

    print("[GACHA SETUP LOG] find_target_armature: No armature found in context or scene!")
    return None


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
    armature_obj = find_target_armature(context, armature_obj)

    if not armature_obj:
        print("[PHYSICS] No armature found to apply hair & clothes physics.")
        return 0

    # Read influences from scene properties if not explicitly provided
    if hair_influence is None:
        if hasattr(context, "scene") and hasattr(context.scene, "gi_hair_physics_influence"):
            hair_influence = context.scene.gi_hair_physics_influence
        elif hasattr(context, "scene") and hasattr(context.scene, "character_rigger_props") and hasattr(context.scene.character_rigger_props, "hair_physics_influence"):
            hair_influence = context.scene.character_rigger_props.hair_physics_influence
        elif hasattr(context, "scene") and hasattr(context.scene, "hair_physics_influence"):
            hair_influence = context.scene.hair_physics_influence
        else:
            hair_influence = 0.7

    if clothes_influence is None:
        clothes_influence = dress_influence

    if clothes_influence is None:
        if hasattr(context, "scene") and hasattr(context.scene, "gi_clothes_physics_influence"):
            clothes_influence = context.scene.gi_clothes_physics_influence
        elif hasattr(context, "scene") and hasattr(context.scene, "character_rigger_props"):
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

    # Ensure armature is active, selectable, unhidden, and in POSE mode
    try:
        armature_obj.hide_set(False)
        armature_obj.hide_viewport = False
    except Exception:
        pass
    try:
        context.view_layer.objects.active = armature_obj
        armature_obj.select_set(True)
    except Exception:
        pass
    try:
        bpy.ops.object.mode_set(mode="POSE")
    except Exception:
        pass

    is_v4 = bpy.app.version >= (4, 0, 0)
    arm_data = armature_obj.data

    # Make Hair and Clothes collections / layers visible
    if is_v4 and hasattr(arm_data, "collections"):
        for coll_name in ["Hair", "Clothes", "Dress", "Physics", "Extra", "Secondary"]:
            if coll_name in arm_data.collections:
                arm_data.collections[coll_name].is_visible = True
    else:
        if len(arm_data.layers) > 22:
            arm_data.layers[20] = True
            arm_data.layers[22] = True

    physics_ignore_list = {
        "+UpperArmTwistA02.L", "+UpperArmTwistA01.L", "+UpperArmTwistA01.R", "+UpperArmTwistA02.R",
        "+UpperArmTwist L A01", "+UpperArmTwist L A02", "+UpperArmTwist R A01", "+UpperArmTwist R A02",
        "eye.R", "eye.L", "+ToothBone D A01", "+ToothBone U A01", "+ToothBone A A01",
        "+EyeBone L A01", "+EyeBoneA02.L", "+EyeBone R A01", "+EyeBoneA02.R",
        "+EyeBone L A02", "+EyeBone R A02",
        "+EyeBone R A01.001", "+EyeBone L A01.001", "+PelvisTwist CF A01",
        "+ForeArmTwistSA01.R", "+ForeArmTwistSA01.L", "+ShoulderSA01.L", "+ShoulderSA01.R",
        "+ElbowSA01.R", "+ElbowSA01.L", "+KneeFA01.R", "+KneeFA01.L", "+SkirtAllF CF A01",
        "+ForearmTwistSA01.R", "+ForearmTwistSA01.L", "+ThighTwistSA01.R", "+ThighTwistSA01.L"
    }

    core_biped_org = {
        "ORG-Pelvis", "ORG-Spine", "ORG-Spine1", "ORG-Spine2",
        "ORG-neck", "ORG-head",
        "ORG-shoulder.L", "ORG-shoulder.R",
        "ORG-upper_arm.L", "ORG-upper_arm.R",
        "ORG-forearm.L", "ORG-forearm.R",
        "ORG-hand.L", "ORG-hand.R",
        "ORG-thigh.L", "ORG-thigh.R",
        "ORG-shin.L", "ORG-shin.R",
        "ORG-foot.L", "ORG-foot.R",
        "ORG-toe_ik.L", "ORG-toe_ik.R",
        "ORG-Bip001LHeel0", "ORG-Bip001RHeel0",
        "ORG-Root", "ORG-root", "ORG-Bip001",
    }
    for side in [".L", ".R"]:
        for f in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
            for n in ["01", "02", "03"]:
                core_biped_org.add(f"ORG-{f}.{n}{side}")
                core_biped_org.add(f"ORG-{f}.{n}{side}.001")

    has_skirt_rig = bool(
        arm_data.bones.get("MCH-Skirt_Parent02")
        or arm_data.bones.get("MCH-Skirt_Parent")
        or any(b.name.startswith("CTRL-") and any(k in b.name.lower() for k in ["skirt", "dress", "hem", "qun"]) for b in arm_data.bones)
    )

    def is_physics_ignored(name):
        if name in physics_ignore_list or name in core_biped_org:
            return True
        if is_v4 and hasattr(arm_data, "collections"):
            if "Face" in arm_data.collections and name in arm_data.collections["Face"].bones:
                return True
        low = name.lower()
        if has_skirt_rig and any(k in low for k in ["skirt", "dress", "hem", "qun"]):
            return True
        pb = armature_obj.pose.bones.get(name) if (armature_obj and hasattr(armature_obj, "pose") and armature_obj.pose) else None
        if pb and any(c.type == 'STRETCH_TO' for c in pb.constraints):
            return True
        if any(k in low for k in [
            "eyebone", "eye", "tooth", "teeth", "tongue", "mouth", "jaw", "brow", "lip", "nose",
            "cheek", "plate", "twist", "sa01", "sa02", "fa01", "skirtallf", "prop", "light",
            "finger", "thumb", "heel", "camera", "case", "chest", "breast",
            "face", "wink", "slider", "ctrl", "control"
        ]):
            return True
        if (
            name.startswith("DEF-")
            or name.startswith("MCH-")
            or name.startswith("Bon_")
            or name.startswith("BON_")
            or name.startswith("Bone-")
            or name.startswith("Bip001")
            or name.startswith("joint_")
            or (low.startswith("skn_") and "tail" not in low)
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
        if "Dress" in arm_data.collections:
            clothes_bone_names.update(b.name for b in arm_data.collections["Dress"].bones if not is_physics_ignored(b.name))
        if "Tails" in arm_data.collections:
            clothes_bone_names.update(b.name for b in arm_data.collections["Tails"].bones if not is_physics_ignored(b.name))

    # Fallback or additional keyword detection if collections are empty
    hair_keywords = [
        "hair", "eardrop", "headline", "ahoge", "bangs", "ponytail", "twintail", "bone00",
        "plait", "braid", "toufa"
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

        # 1. Ignore near-zero length degenerate bones
        if p_bone.length < 0.001 or c_bone.length < 0.001:
            return False

        # 2. Check if parent and child are co-located / overlapping inside one another
        # (e.g. child head is placed right at parent head, or both bones occupy the same position)
        head_to_head_dist = (c_bone.head_local - p_bone.head_local).length
        tail_to_tail_dist = (c_bone.tail_local - p_bone.tail_local).length

        # If child head is sitting at/near parent head (coincident root / duplicate / parallel inside)
        if head_to_head_dist < 0.005 or head_to_head_dist < 0.35 * p_bone.length:
            return False

        # If child and parent share the exact same tail or are overlapping duplicate bones
        if tail_to_tail_dist < 0.005:
            return False

        # 3. Check direct parentage or contiguous connectivity
        if c_bone.parent == p_bone or c_bone.use_connect:
            return True

        gap = (c_bone.head_local - p_bone.tail_local).length
        allowed_gap = max(0.10, 1.5 * p_bone.length)
        return gap <= allowed_gap

    def common_prefix_len(s1, s2):
        count = 0
        for a, b in zip(s1, s2):
            if a == b:
                count += 1
            else:
                break
        return count

    def pick_best_child(parent_name, children_list):
        if not children_list:
            return None
        if len(children_list) == 1:
            return children_list[0]
        return max(children_list, key=lambda c: common_prefix_len(parent_name, c.name))

    def would_create_cycle(source_bone_name, target_bone_name):
        """Checks if adding a Damped Track from source -> target creates an end-to-start cycle."""
        if source_bone_name == target_bone_name:
            return True

        s_pb = armature_obj.pose.bones.get(source_bone_name)
        t_pb = armature_obj.pose.bones.get(target_bone_name)
        if not s_pb or not t_pb:
            return False

        # Reject if target is an ancestor of source (tracking backwards towards root / end-to-start)
        curr = s_pb.parent
        while curr:
            if curr.name == target_bone_name:
                return True
            curr = curr.parent

        # Reject if target already has a constraint tracking source or any ancestor of source
        for c in t_pb.constraints:
            sub = getattr(c, 'subtarget', None)
            if sub and sub in armature_obj.pose.bones:
                if sub == source_bone_name:
                    return True
                chk = s_pb
                while chk:
                    if chk.name == sub:
                        return True
                    chk = chk.parent

        return False

    # Align edit bone tails to point directly to child bones so Damped Track does not distort rest pose
    try:
        context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = armature_obj.data.edit_bones
        for b_name in (hair_bone_names | clothes_bone_names):
            eb = edit_bones.get(b_name)
            if not eb:
                continue
            chain_children = [c for c in eb.children if c.name in (hair_bone_names | clothes_bone_names)]
            if chain_children:
                best_c = pick_best_child(eb.name, chain_children)
                if not would_create_cycle(eb.name, best_c.name):
                    vec = best_c.head - eb.head
                    if vec.length > 0.001:
                        eb.tail = best_c.head
            elif eb.parent and eb.parent.name in (hair_bone_names | clothes_bone_names):
                parent_eb = eb.parent
                dir_vec = (eb.head - parent_eb.head).normalized()
                if dir_vec.length > 0.5:
                    eb.tail = eb.head + dir_vec * max(0.02, min(eb.length, 0.05))
    except Exception as e_align:
        print(f"[PHYSICS] Notice aligning bone tails: {e_align}")
    finally:
        try:
            bpy.ops.object.mode_set(mode="POSE")
        except Exception:
            pass

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
                if would_create_cycle(b_name, child_pb.name):
                    print(f"[PHYSICS SKIP] Skipped Damped Track {b_name} -> {child_pb.name} (dependency cycle detected).")
                    continue
                dt = pb.constraints.new("DAMPED_TRACK")
                dt.name = "Hair_Physics_DampedTrack"
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
                if would_create_cycle(b_name, child_pb.name):
                    print(f"[PHYSICS SKIP] Skipped Damped Track {b_name} -> {child_pb.name} (dependency cycle detected).")
                    continue
                dt = pb.constraints.new("DAMPED_TRACK")
                dt.name = "Clothes_Physics_DampedTrack"
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

    if applied_count > 0:
        try:
            armature_obj["gi_has_physics"] = True
        except Exception:
            pass

    print(f"[PHYSICS] Applied Damped Track physics to {applied_count} Hair & Clothes bones (Hair: {hair_influence}, Clothes: {clothes_influence}) and hidden physics collections.")
    return applied_count


def update_hair_physics_influence(influence, context=None):
    context = context or bpy.context
    armature_obj = find_target_armature(context)
    if not armature_obj or not armature_obj.pose:
        return 0
    count = 0
    for pb in armature_obj.pose.bones:
        for c in pb.constraints:
            if c.type == 'DAMPED_TRACK' and (
                c.name == "Hair_Physics_DampedTrack" or
                (c.name == "Damped Track" and any(k in pb.name.lower() for k in ["hair", "ahoge", "bangs", "ponytail", "twintail", "bone00"]))
            ):
                c.influence = influence
                count += 1
    if count == 0:
        apply_hair_and_clothes_physics(armature_obj, context, hair_influence=influence)
    return count


def update_clothes_physics_influence(influence, context=None):
    context = context or bpy.context
    armature_obj = find_target_armature(context)
    if not armature_obj or not armature_obj.pose:
        return 0
    count = 0
    for pb in armature_obj.pose.bones:
        for c in pb.constraints:
            if c.type == 'DAMPED_TRACK' and (
                c.name == "Clothes_Physics_DampedTrack" or
                (c.name == "Damped Track" and not any(k in pb.name.lower() for k in ["hair", "ahoge", "bangs", "ponytail", "twintail", "bone00"]))
            ):
                c.influence = influence
                count += 1
    if count == 0:
        apply_hair_and_clothes_physics(armature_obj, context, clothes_influence=influence)
    return count


def has_hair_clothes_physics(context=None, armature_obj=None):
    context = context or bpy.context
    if not armature_obj:
        armature_obj = find_target_armature(context)
    if not armature_obj or not armature_obj.pose:
        return False

    if armature_obj.get("gi_has_physics", False):
        return True

    # Check if any pose bone has our specific physics constraint
    for pb in armature_obj.pose.bones:
        for c in pb.constraints:
            if c.type == 'DAMPED_TRACK' and c.name in ["Hair_Physics_DampedTrack", "Clothes_Physics_DampedTrack"]:
                return True
    return False


# Compatibility alias
apply_hair_and_dress_physics = apply_hair_and_clothes_physics


def ensure_root_trio(armature_obj):
    """Garantiza root/root.001/root.002 con cadena root.002->root.001->root (ZZZ).

    Idempotente: crea el tier que falte (cura rigs parciales) y fuerza la
    jerarquia + props->root.002. Requiere EDIT mode activo en armature_obj.
    Compartido NTE/WuWa (NTE conserva su copia local; no tocar).
    """
    if armature_obj is None:
        return
    eb = armature_obj.data.edit_bones
    if "root" in eb and "root.001" not in eb and "root.002" not in eb:
        r0 = eb["root"]
        _h = r0.head.copy()
        _t = r0.tail.copy()
        _rl = r0.roll
        r0.name = "root.002"
        e001 = eb.new("root.001")
        e001.head = _h.copy()
        e001.tail = _t.copy()
        e001.roll = _rl
        e001.parent = None
        e000 = eb.new("root")
        e000.head = _h.copy()
        e000.tail = _t.copy()
        e000.roll = _rl
        e000.parent = None
    for _n in ["root.002", "root.001", "root"]:
        if _n not in eb:
            _ref = eb.get("root.002") or eb.get("root.001") or eb.get("root")
            _nb = eb.new(_n)
            if _ref is not None:
                _nb.head = _ref.head.copy()
                _nb.tail = _ref.tail.copy()
                _nb.roll = _ref.roll
            else:
                _nb.head = mathutils.Vector((0.0, 0.0, 0.0))
                _nb.tail = mathutils.Vector((0.0, 0.0, 0.5))
                _nb.roll = 0
            _nb.parent = None
    _r2 = eb.get("root.002")
    _r1 = eb.get("root.001")
    _r0b = eb.get("root")
    if _r2 is not None and _r1 is not None and _r2.parent != _r1:
        _r2.parent = _r1
    if _r1 is not None and _r0b is not None and _r1.parent != _r0b:
        _r1.parent = _r0b
    if _r0b is not None and _r0b.parent is not None:
        _r0b.parent = None
    if _r2 is not None:
        for _pn in ["prop.L", "prop.R"]:
            _ep = eb.get(_pn)
            if _ep is not None and _ep.parent != _r2:
                _ep.parent = _r2


def strip_rigify_torso_follow_ui(rigifyr, original_name, char_name):
    """Quita del rig_ui.py generado las filas de Rigify 'Neck/Head Follow' y el
    bloque 'Torso Parent' sobre pose_bones['torso'].

    En ZZZ esas referencias quedan huerfanas por el rename (torso->torso.002) y no
    aparecen; en NTE/WuWa el hueso conserva el nombre y el panel las muestra aunque
    el control real ya vive en plate-settings. Solo llamar en juegos con plate.
    Se ejecuta ANTES de modify_and_run_rig_ui_script (que relee el texto).
    """
    candidates = []
    if rigifyr is not None and getattr(rigifyr, "name", ""):
        candidates.append(f"{rigifyr.name}_ui.py")
    candidates += [f"{original_name}_ui.py", f"{char_name}_ui.py",
                   f"{char_name}Rig_ui.py", "rig_ui.py", "metarig_ui.py"]
    rig_file = None
    for _name in candidates:
        if _name in bpy.data.texts:
            rig_file = bpy.data.texts[_name]
            break
    if rig_file is None:
        for _t in bpy.data.texts:
            try:
                _c = _t.as_string()
            except Exception:
                continue
            if "class RigLayers" in _c or "PT_rig_layers" in _c or "rig_id = " in _c:
                rig_file = _t
                break
    if rig_file is None:
        print("[RIG UI] torso-follow UI strip skipped: no rig ui text found")
        return False
    try:
        lines = rig_file.as_string().splitlines()
    except Exception as ex:
        print(f"[RIG UI] torso-follow UI strip skipped: {ex}")
        return False
    removed = []

    # 1. Filas sueltas Neck/Head Follow sobre torso
    kept = []
    for _ln in lines:
        if ("layout.prop" in _ln and "pose_bones['torso']" in _ln
                and ('"neck_follow"' in _ln or '"head_follow"' in _ln)):
            removed.append(_ln.strip()[:90])
            continue
        kept.append(_ln)
    lines = kept

    # 2. Bloque anidado 'Torso Parent' (if is_selected ... hasta 2do props.locks)
    anchor = next((i for i, _ln in enumerate(lines) if "text='Torso Parent'" in _ln), None)
    if anchor is not None:
        start = anchor
        while start > 0 and "if is_selected(" not in lines[start]:
            start -= 1
        locks = 0
        end = None
        for _j in range(anchor, min(len(lines), anchor + 40)):
            if "props.locks = (False, False, False)" in lines[_j]:
                locks += 1
                if locks == 2:
                    end = _j
                    break
        if "if is_selected(" in lines[start] and end is not None and (end - start) < 40:
            removed.append(f"torso-parent block L{start}-{end}")
            del lines[start:end + 1]
        else:
            print("[RIG UI] torso-parent block guard tripped, kept")

    # 3. Bloques torso huerfanos que solo dejan emit_rig_separator()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        _m = re.match(r"^(\s*)if is_selected\(", lines[i])
        if _m:
            _indent = len(_m.group(1))
            _hdr_end = i
            while _hdr_end < n and not lines[_hdr_end].rstrip().endswith(":"):
                _hdr_end += 1
            if _hdr_end < n and "'torso'" in "\n".join(lines[i:_hdr_end + 1]):
                _j = _hdr_end + 1
                _body = []
                while _j < n and (not lines[_j].strip()
                                  or len(lines[_j]) - len(lines[_j].lstrip()) > _indent):
                    if lines[_j].strip():
                        _body.append(lines[_j].strip())
                    _j += 1
                if _body == ["emit_rig_separator()"]:
                    removed.append("orphan torso if-block")
                    i = _j
                    continue
                out.extend(lines[i:_j])
                i = _j
                continue
        out.append(lines[i])
        i += 1

    if removed:
        try:
            rig_file.clear()
            rig_file.write("\n".join(out) + "\n")
            print(f"[RIG UI] torso-follow UI stripped: {removed}")
            return True
        except Exception as ex:
            print(f"[RIG UI] torso-follow UI write notice: {ex}")
            return False
    print("[RIG UI] torso-follow UI strip: nothing matched")
    return False


def get_view3d_override():
    """
    Returns a dict with context members for bpy.context.temp_override(...)
    targeting an active VIEW_3D space and WINDOW region, even when running
    in background/headless mode or from other window contexts.
    """
    screens = [bpy.context.screen] if getattr(bpy.context, "screen", None) else []
    screens.extend([s for s in bpy.data.screens if s not in screens])
    for s in screens:
        for a in getattr(s, "areas", []):
            if a.type == "VIEW_3D":
                sp = a.spaces.active if a.spaces else None
                reg = next((r for r in a.regions if r.type == "WINDOW"), None)
                override = {"screen": s, "area": a}
                if sp:
                    override["space_data"] = sp
                if reg:
                    override["region"] = reg
                return override
    return {}


def patch_expykit_operators():
    """
    Patches ExpyKit operators to ensure their execute methods run with a valid
    VIEW_3D context override if context.space_data is None.
    """
    try:
        import sys
        for mod_name, mod in list(sys.modules.items()):
            if "expy" in mod_name.lower():
                for attr_name in ("ExtractMetarig", "ConvertBoneNaming"):
                    cls = getattr(mod, attr_name, None)
                    if cls and hasattr(cls, "execute") and not getattr(cls.execute, "_gacha_patched", False):
                        orig_exec = cls.execute
                        def make_wrapper(orig):
                            def safe_exec(self, context):
                                if getattr(context, "space_data", None) is None:
                                    ov = get_view3d_override()
                                    if ov and hasattr(context, "temp_override"):
                                        with context.temp_override(**ov):
                                            return orig(self, context)
                                return orig(self, context)
                            safe_exec._gacha_patched = True
                            return safe_exec
                        cls.execute = make_wrapper(orig_exec)
    except Exception:
        pass


def safe_expykit_extract_metarig(rig_preset="Rigify_Metarig.py", assign_metarig=True):
    """
    Executes bpy.ops.object.expykit_extract_metarig with a 3D View context override
    to prevent crashes in background/isolated mode where context.space_data is None.
    """
    patch_expykit_operators()
    ov = get_view3d_override()
    if ov and hasattr(bpy.context, "temp_override"):
        with bpy.context.temp_override(**ov):
            return bpy.ops.object.expykit_extract_metarig(
                rig_preset=rig_preset, assign_metarig=assign_metarig
            )
    return bpy.ops.object.expykit_extract_metarig(
        rig_preset=rig_preset, assign_metarig=assign_metarig
    )


def safe_expykit_convert_bone_names(src_preset="Rigify_Metarig.py", trg_preset="Rigify_Deform.py"):
    """
    Executes bpy.ops.object.expykit_convert_bone_names with a 3D View context override.
    """
    patch_expykit_operators()
    ov = get_view3d_override()
    if ov and hasattr(bpy.context, "temp_override"):
        with bpy.context.temp_override(**ov):
            return bpy.ops.object.expykit_convert_bone_names(
                src_preset=src_preset, trg_preset=trg_preset
            )
    return bpy.ops.object.expykit_convert_bone_names(
        src_preset=src_preset, trg_preset=trg_preset
    )


