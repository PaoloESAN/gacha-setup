# Based on Blender-WuWa-Character-Setup by @fnoji (https://github.com/fnoji/Blender-WuWa-Character-Setup)
# Gustling Waters texture mappings by @nytsjared (https://github.com/nytsjared)
# Adapted for Gacha Setup by PaoloESAN
# Licensed under GPL-3.0-or-later

import bpy
import os
import re
from typing import Optional, List, Tuple, Dict, Any

TEXTURE_TYPE_MAPPINGS_JAREDNYTS = {
    "_D": (
        "Base Color",
        "Bangs Diffuse",
        "Hair Diffuse",
        "Face Diffuse",
        "Eye Diffuse",
        "Body Diffuse",
        "Npc Diffuse",
        "NPC Diffuse",
    ),
    "_N": ("Normal Map",),
    "_HM": ("Hair HM", "Bangs HM"),
    "_HN": ("Hair HN", "Bangs HN"),
    "_HET": ("Eye HET", "Face HET", "Face_HET"),
    "_ID": ("Mask ID", "Face ID", "Texture_ID", "Face ID Texture"),
    "_RGID": ("RGID",),
    "_FX": ("FX Texture",),
    "_Skin": ("Skin",),
}

_MODEL_PREFIX_PATTERNS = [
    ("R2T1", re.compile(r"^R2T1")),
    ("NHT1", re.compile(r"^NHT1")),
    ("NH_",  re.compile(r"^NH_")),
    ("MB1",  re.compile(r"^MB1")),
    ("ML1",  re.compile(r"^ML1")),
    ("NA0",  re.compile(r"^NA0")),
    ("NM0",  re.compile(r"^NM0")),
]


def extract_character_name(name: str, title_case: bool = True) -> str:
    """Extract character name from mesh / armature / material name."""
    if not name:
        return "Character"
    
    if name.endswith("_Skeleton"):
        name = name[:-9]
    if name.startswith("RIG-"):
        name = name[4:]

    # R2T1 (Standard PC format with Md ID)
    if match := re.search(r"R2T1(.+?)Md\d+(?:_LOD\d+)?", name, re.IGNORECASE):
        extracted = match.group(1)
        return extracted.title() if title_case else extracted

    # MB1 (Monster/Boss format with Md ID)
    if match := re.search(r"MB1(.+?)Md\d+(?:_\w+)?(?:_LOD\d+)?", name, re.IGNORECASE):
        extracted = match.group(1)
        return extracted.title() if title_case else extracted

    # ML1 (Lord format)
    if match := re.search(r"ML1(.+?)Md\d+(?:_\w+)?(?:_LOD\d+)?", name, re.IGNORECASE):
        extracted = match.group(1)
        return extracted.title() if title_case else extracted

    # NA0 / NM0 (Animal format)
    if match := re.search(r"((?:NA0|NM0).+?)(?:_LOD\d+)?", name, re.IGNORECASE):
        extracted = match.group(1)
        return extracted.title() if title_case else extracted

    # NHT1 (NPC format)
    if match := re.search(r"NHT1(.+?)(?:_LOD\d+)?", name, re.IGNORECASE):
        extracted = match.group(1)
        return extracted.title() if title_case else extracted

    # NH_ (Generic NPC format)
    if match := re.search(r"NH_(.+?)(?:_LOD\d+)?", name, re.IGNORECASE):
        extracted = match.group(1)
        return extracted.title() if title_case else extracted

    # If it has underscores e.g. Chun_Body
    if "_" in name:
        parts = name.split("_")
        return parts[0].title() if title_case else parts[0]

    return name.title() if title_case else name


def split_material_name(mat_name: str) -> Tuple[str, str]:
    """
    Splits material name into (base_part, version).
    E.g. MI_R2T1ChunMd10011Down_D -> ('Down', '')
         MI_R2T1ChunMd10011Up_D   -> ('Up', '')
         MI_R2T1ChunMd10011Hair_D -> ('Hair', '')
         MI_5XingStar             -> ('ResonatorStar', '')
         MI_R2T1ChunMd10011Down03_D -> ('Down', '03')
    """
    if not mat_name:
        return "", ""

    if mat_name.endswith("_SEETHRU"):
        mat_name = mat_name[:-8]

    # Handle Star
    if any(k in mat_name.lower() for k in ["xingstar", "resonatorstar", "star"]):
        return "ResonatorStar", ""

    # If already formatted as WW - Down Chun
    if mat_name.startswith("WW - "):
        rest = mat_name[5:].split(" ")[0]
        # Check known parts
        for known in ["Down", "Up", "Hair", "Face", "Eye", "Bangs", "ResonatorStar", "Dress", "Weapon", "Acc", "Body", "Main"]:
            if rest.lower().startswith(known.lower()):
                ver = rest[len(known):]
                return known, ver
        return rest, ""

    parts = mat_name.split("_", 2)
    if len(parts) < 2:
        # Check if direct name like Down, Up, Face, Hair, Eye
        for known in ["Down", "Up", "Hair", "Face", "Eye", "Bangs", "ResonatorStar", "Dress", "Weapon", "Acc", "Body", "Main"]:
            if known.lower() in mat_name.lower():
                return known, ""
        return mat_name, ""

    category_part = parts[1]

    # Handle NPC naming
    if category_part in ["Npc", "NH", "NPC"]:
        if len(parts) > 2:
            remaining = parts[2]
            if "_" in remaining:
                suffix = remaining.rsplit("_", 1)[-1]
                if re.match(r"^\d+[A-Za-z]", suffix):
                    suffix = re.sub(r"^\d+", "", suffix)
                return suffix, ""
            if re.match(r"^\d+[A-Za-z]", remaining):
                return re.sub(r"^\d+", "", remaining), ""
            return remaining, ""
        base_part = category_part
        version = "_" + parts[2] if len(parts) > 2 else ""
        return base_part, version

    words = re.findall(r"[A-Z][a-z]*", category_part)
    if not words:
        base_part = category_part
        version = "_" + parts[2] if len(parts) > 2 else ""
    else:
        base_part = words[-1]
        try:
            version_start = category_part.rindex(base_part) + len(base_part)
            version = category_part[version_start:]
            if len(parts) > 2:
                version += "_" + parts[2]
        except ValueError:
            version = ""

    # Strip texture type suffixes from version if they came from MI_..._D
    for tex_suffix in ["_D", "_N", "_Skin", "_ID", "_RGID", "_HM", "_HN", "_FTM", "_HET", "_FX", "_LD"]:
        if version.endswith(tex_suffix):
            version = version[:-len(tex_suffix)]
        elif version.upper() == tex_suffix.upper():
            version = ""

    return base_part, version


def make_texture_patterns(base_part: str, version: str, suffix: str, original_name: str = "", mode: bool = True) -> List[str]:
    patterns = []

    if suffix == "_Skin":
        patterns.append(r"T_.*?Skin.*")
        patterns.append(r"Texture_Skin.*")
        patterns.append(r".*Skin.*")
        return patterns

    # ResonatorStar patterns
    if base_part == "ResonatorStar" or "star" in base_part.lower():
        patterns.append(rf"T_.*?XingStar.*?{suffix}")
        patterns.append(rf"T_.*?Star.*?{suffix}")
        patterns.append(rf".*?XingStar.*?{suffix}")
        patterns.append(rf".*?Star.*?{suffix}")
        return patterns

    if original_name:
        if match := re.search(r"MI_(.*)", original_name):
            base = match.group(1)
            for sfx in ["_D", "_N", "_Skin", "_ID", "_RGID", "_HM", "_HN", "_FTM", "_HET", "_FX", "_LD"]:
                if base.endswith(sfx):
                    base = base[:-len(sfx)]
                    break
            base_no_ver = re.sub(r"[0-9_]+$", "", base)

            if base.startswith("NH_"):
                base_no_nh = base[3:]
                base_no_ver_no_nh = re.sub(r"[0-9_]+$", "", base_no_nh)
                patterns.append(rf"T_{base_no_nh}{suffix}.*")
                patterns.append(rf"T_{base_no_ver_no_nh}{suffix}.*")

            if "Up02" in base:
                patterns.append(rf"T_{base}{suffix}.*")
                patterns.append(rf"T_.*?Down{suffix}.*")
                return list(dict.fromkeys(patterns))

            replacements = {"Up": "Upper", "Eye": "Eyes", "Star": "Up", "Bang": "Hair", "Bangs": "Hair"}
            for k, v in replacements.items():
                if k in base:
                    base_pat = rf"T_{base_no_ver}{suffix}.*"
                    ver_pat = rf"T_{base}{suffix}.*"
                    patterns.extend([base_pat, ver_pat] if mode else [ver_pat, base_pat])
                    patterns.extend([p.replace(k, v) for p in patterns[:]])
                    # Also add generic fallback
                    patterns.append(rf"T_.*?{base_part}{suffix}.*")
                    if k in ["Bang", "Bangs"]:
                        patterns.append(rf"T_.*?Hair{suffix}.*")
                    return list(dict.fromkeys(patterns))

            base_pat = rf"T_{base_no_ver}{suffix}.*"
            ver_pat = rf"T_{base}{suffix}.*"
            patterns.extend([base_pat, ver_pat] if mode else [ver_pat, base_pat])
            patterns.append(rf"T_.*?{base_part}{suffix}.*")
            if base_part in ["Bang", "Bangs"]:
                patterns.append(rf"T_.*?Hair{suffix}.*")
            return list(dict.fromkeys(patterns))

    # Fallback / General construction
    base_no_ver = re.sub(r"[0-9_]+$", "", base_part)
    replacements = {"Up": "Upper", "Eye": "Eyes", "Star": "Up", "Bang": "Hair", "Bangs": "Hair"}

    for k, v in replacements.items():
        if k in base_part:
            base_pat = rf"T_.*?{base_no_ver}{suffix}.*"
            ver_pat = rf"T_.*?{base_part}{version}{suffix}.*"
            patterns.extend([base_pat, ver_pat] if mode else [ver_pat, base_pat])
            patterns.extend([p.replace(k, v) for p in patterns[:]])
            if k in ["Bang", "Bangs"]:
                patterns.append(rf"T_.*?Hair{suffix}.*")
            return list(dict.fromkeys(patterns))

    base_pat = rf"T_.*?{base_no_ver}{suffix}.*"
    ver_pat = rf"T_.*?{base_part}{version}{suffix}.*"
    ver_pat = ver_pat.replace("__", "_")

    if "Npc" in base_part:
        ver_pat_joined = rf"T_.*?{base_part}{version.replace('_', '')}{suffix}.*"
        patterns.append(ver_pat_joined)

    if "Up02" in base_part:
        patterns.append(rf"T_.*?Down{suffix}.*")
        patterns.append(rf"T_Down{suffix}.*")
        patterns.append(ver_pat)
        patterns.append(base_pat)
        return list(dict.fromkeys(patterns))

    if base_part in ["Bang", "Bangs"]:
        patterns.append(rf"T_.*?Hair{suffix}.*")

    patterns.extend([base_pat, ver_pat] if mode else [ver_pat, base_pat])
    return list(dict.fromkeys(patterns))


def load_image_safely(file_path: str, suffix: str) -> Optional[bpy.types.Image]:
    if not os.path.exists(file_path):
        base, _ = os.path.splitext(file_path)
        found = None
        for ext in ['.png', '.tga', '.dds', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']:
            if os.path.exists(base + ext):
                found = base + ext
                break
        if found:
            file_path = found
        else:
            return None
    file_name = os.path.basename(file_path)
    img = bpy.data.images.get(file_name)
    if not img:
        try:
            img = bpy.data.images.load(file_path)
            img.alpha_mode = "CHANNEL_PACKED"
            needs_srgb = suffix.upper() in ["_D", "_SKIN"]
            img.colorspace_settings.name = "sRGB" if needs_srgb else "Non-Color"
        except Exception as e:
            print(f"[WuWa Texture] Error loading {file_path}: {e}")
            return None
    return img


def find_texture_for_slot(textures_list: List[str], patterns: List[str], folder: str, suffix: str) -> Optional[bpy.types.Image]:
    for pat in patterns:
        regex = re.compile(f"^{pat}$", re.IGNORECASE)
        for fname in textures_list:
            base_name_no_ext, _ = os.path.splitext(fname)
            if regex.match(base_name_no_ext) or regex.match(fname):
                full_path = os.path.join(folder, fname)
                img = load_image_safely(full_path, suffix)
                if img:
                    return img
    return None


def classify_wuwa_json_texture(param_name: str, tex_file_stem: str, is_hair_or_bangs: bool = False, stem: str = "") -> Optional[str]:
    """
    Classifies a texture entry from a Wuthering Waves Material Instance JSON into its standard slot:
    '_D', '_N', '_ID', '_HM', '_HN', '_Skin', '_HET', '_FX', '_SDF', '_LD', '_RGID'.
    Returns None if the texture is a utility map (MatCap, Noise, CubeMap, etc.).
    """
    param_low = param_name.lower()
    tex_low = tex_file_stem.lower()
    stem_low = stem.lower()

    # Filter out utility / cube / matcap / noise maps from diffuse
    if any(k in tex_low for k in ["_mc_", "matcap", "cubemap", "shakenoise", "soundnoise", "premake05"]):
        if param_low in ["matcaptex", "pbrcubemap", "shakenoise", "noise", "noise02", "second_rgb", "r_noise_a_mask", "pm_diffuse", "maintex", "d"]:
            return None

    # Filter out Star textures from non-Star materials (e.g. Phoebe's Down.json includes T_5XingStar_D)
    is_star_material = any(k in stem_low for k in ["star", "xingstar", "resonatorstar"])
    if not is_star_material and any(k in tex_low for k in ["star", "xingstar", "shakenoise", "soundnoise"]):
        return None

    # HET (Hair-Eye Transparency / Face HET / Eye HET)
    if "het" in tex_low or "heta" in tex_low or "het" in stem_low:
        if param_low in ["mask", "het", "heta", "ishet"] or "het" in tex_low or "heta" in tex_low:
            return "_HET"

    # Base Color / Diffuse (_D)
    if param_low in ["maintex", "basecolor", "diffuse"]:
        return "_D"
    if param_low == "d" and not any(k in tex_low for k in ["noise", "mc_", "matcap"]):
        return "_D"
    if param_low == "pm_diffuse" and not any(k in tex_low for k in ["_mc_", "matcap", "cubemap", "shakenoise", "soundnoise", "premake", "noise"]):
        return "_D"
    if tex_low.endswith("_d") and not any(k in tex_low for k in ["_mc_", "matcap", "cubemap", "shakenoise", "soundnoise", "premake", "noise"]):
        return "_D"

    # Normal Map (_N)
    if param_low in ["pm_normals", "normal_roughness_metallic", "normal", "normals", "normalmap"] or tex_low.endswith("_n"):
        return "_N"

    # Mask ID / TypeMask (_ID)
    if param_low in ["typemask", "mask_id", "texture_id", "id", "face_id", "facemask"] or tex_low.endswith("_id"):
        return "_ID"

    # Skin Ramp (_Skin)
    if param_low in ["ramp", "skin", "skinramp", "skincolor"] or tex_low.endswith("_skin") or "skin" in tex_low:
        return "_Skin"

    # Hair Mask (_HM) / Hair Normal (_HN)
    if tex_low.endswith("_hm") or "_hm." in tex_low:
        return "_HM"
    if tex_low.endswith("_hn") or "_hn." in tex_low:
        return "_HN"
    if param_low in ["masktex", "hairmask", "bangsmask"] and is_hair_or_bangs and not "_sdf" in tex_low:
        return "_HM"

    # SDF (_SDF)
    if param_low == "sdf" or "_sdf" in tex_low:
        return "_SDF"

    # Lightmap (_LD)
    if param_low in ["ld", "lightmap"] or tex_low.endswith("_ld"):
        return "_LD"

    # RGID (_RGID)
    if param_low in ["rgid", "mask_rgid"] or tex_low.endswith("_rgid"):
        return "_RGID"

    # FX / Emissive / HeightLight (_FX)
    if param_low in ["heightlightmap", "em", "pm_emissive", "fx"] or any(sfx in tex_low for sfx in ["_eg", "_em", "_fx"]):
        return "_FX"

    return None


def load_wuwa_json_mappings(folder: str) -> Dict[str, Dict[str, str]]:
    """
    Parses all MI_*.json files in folder and maps them by material name and base part.
    Accurately maps UE material parameters to shader texture slots, avoiding MatCap/Noise
    overwrites and merging sub-materials (_HET, _HETA, etc.) into base parts.
    Returns: { mat_key: { '_D': filename, '_HM': filename, '_ID': filename, '_N': filename, '_Skin': filename, '_HET': filename, ... } }
    """
    import json
    mappings: Dict[str, Dict[str, str]] = {}
    if not folder or not os.path.isdir(folder):
        return mappings

    # Build map of available image files on disk (case-insensitive base stem -> full filename)
    file_disk_map = {}
    for root, _, files in os.walk(folder):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.png', '.tga', '.dds', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']:
                stem_name = os.path.splitext(f)[0].lower()
                file_disk_map[stem_name] = f

    # Discover all MI_*.json files
    json_files = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".json") and f.startswith("MI_"):
                json_files.append((root, f))

    # Sort json files so primary materials are processed before sub-materials (_HET, _HETA, _OL, _FS)
    def json_sort_key(item):
        fname = item[1].lower()
        is_sub = any(fname.endswith(sfx) or f"{sfx}." in fname for sfx in ["_het.json", "_heta.json", "_ol.json", "_fs.json", "_seethru.json"])
        return (1 if is_sub else 0, fname)

    json_files.sort(key=json_sort_key)

    for root, f in json_files:
        fpath = os.path.join(root, f)
        try:
            with open(fpath, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            textures_sec = data.get("Textures", {})
            if not textures_sec:
                continue

            stem = os.path.splitext(f)[0]  # e.g. MI_R2T1ChunMd10011Bang, MI_R2T1FuluoluoMd10011Face_HET
            base_part, version = split_material_name(stem)
            is_hair_or_bangs = base_part.lower() in ["hair", "bang", "bangs", "toufa"]
            is_sub_mat = any(stem.lower().endswith(sfx) for sfx in ["_het", "_heta", "_ol", "_fs", "_seethru"])

            parsed_texs: Dict[str, str] = {}
            for tex_key, tex_val in textures_sec.items():
                if not isinstance(tex_val, str) or not tex_val:
                    continue

                # Extract texture file name stem from Unreal asset path: Client/.../T_Name.T_Name
                tex_file_raw = tex_val.split("/")[-1].split(".")[0]
                matched_fname = file_disk_map.get(tex_file_raw.lower(), tex_file_raw + ".png")

                slot = classify_wuwa_json_texture(tex_key, tex_file_raw, is_hair_or_bangs, stem)
                if slot:
                    # For diffuse, MainTex has highest priority
                    if slot == "_D":
                        if "_D" not in parsed_texs:
                            parsed_texs["_D"] = matched_fname
                        elif tex_key.lower() in ["maintex", "basecolor"]:
                            parsed_texs["_D"] = matched_fname
                    else:
                        parsed_texs[slot] = matched_fname

            if parsed_texs:
                mappings[stem.lower()] = parsed_texs

                # Merge into base_part key (e.g. 'face', 'eye', 'hair', 'bangs', 'up', 'down', 'resonatorstar')
                if base_part:
                    bp_low = base_part.lower()
                    if bp_low not in mappings:
                        mappings[bp_low] = {}

                    if not is_sub_mat:
                        # Primary material sets all base slots
                        for s_key, s_val in parsed_texs.items():
                            mappings[bp_low][s_key] = s_val
                    else:
                        # Sub-material only adds auxiliary slots (like _HET) without overwriting primary slots (_D, _ID, etc.)
                        for s_key, s_val in parsed_texs.items():
                            if s_key == "_HET" or s_key not in mappings[bp_low]:
                                mappings[bp_low][s_key] = s_val

                    # Also store base_part+version key
                    ver_key = f"{base_part}{version}".lower()
                    if ver_key not in mappings:
                        mappings[ver_key] = {}
                    for s_key, s_val in parsed_texs.items():
                        if not is_sub_mat or s_key not in mappings[ver_key]:
                            mappings[ver_key][s_key] = s_val

        except Exception as e:
            print(f"[WuWa JSON Parser] Error parsing {f}: {e}")

    # Aliases and fallbacks
    if "bangs" in mappings and "bang" not in mappings:
        mappings["bang"] = mappings["bangs"]
    elif "bang" in mappings and "bangs" not in mappings:
        mappings["bangs"] = mappings["bang"]

    if "resonatorstar" in mappings:
        mappings.setdefault("star", mappings["resonatorstar"])
        mappings.setdefault("xingstar", mappings["resonatorstar"])
    elif "star" in mappings:
        mappings.setdefault("resonatorstar", mappings["star"])

    if "eye" in mappings and "eyes" not in mappings:
        mappings["eyes"] = mappings["eye"]

    # Fallback: If Bangs has no separate diffuse, fallback to Hair diffuse (e.g. Camellya)
    if "hair" in mappings and "_D" in mappings["hair"]:
        for bang_key in ["bangs", "bang"]:
            if bang_key in mappings and "_D" not in mappings[bang_key]:
                mappings[bang_key]["_D"] = mappings["hair"]["_D"]

    return mappings
