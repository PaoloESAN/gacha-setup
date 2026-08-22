# Author: PaoloESAN
# NTE JSON Material & Texture Parser and Resolver

import os
import re
import json


def normalize_nte_name(name):
    """Normalizes material or JSON names for robust cross-matching."""
    if not name:
        return ""
    # If passed as "MaterialName / SubNodeGroup", take MaterialName
    clean = str(name).split('/')[0].strip()
    clean = re.sub(r'\.\d{3}$', '', clean).strip()
    if clean.lower().endswith('.json'):
        clean = clean[:-5]
    clean = clean.lower()
    # Normalize MI_ and Ml_ and M_ prefixes (case-insensitive Unreal instance naming)
    clean = re.sub(r'^m[il]_', '', clean)
    clean = re.sub(r'^m_', '', clean)
    clean = clean.replace('-', '_')
    return clean


def build_image_files_map(folder):
    """Scans folder and subfolders to build a lookup map of image files."""
    image_files_map = {}
    image_files_list = []
    if not folder or not os.path.isdir(folder):
        return image_files_map, image_files_list

    valid_exts = ('.png', '.tga', '.dds', '.jpg', '.jpeg', '.webp', '.hdr', '.png.001', '.tga.001', '.dds.001')
    try:
        for root, _, files in os.walk(folder):
            for f in files:
                f_lower = f.lower()
                if any(f_lower.endswith(ext) for ext in valid_exts):
                    image_files_list.append(f)
                    base_no_ext = f.rsplit('.', 1)[0].lower()
                    image_files_map[base_no_ext] = f
                    # Also register without .001 if packed
                    if '.' in base_no_ext:
                        sub_base = base_no_ext.rsplit('.', 1)[0]
                        image_files_map[sub_base] = f
    except Exception as ex:
        print(f"[NTE JSON Parser] Notice walking image files: {ex}")

    return image_files_map, image_files_list


def resolve_json_textures(json_data, image_files_map, image_files_list):
    """Extracts and resolves textures from JSON against files on disk."""
    textures_dict = json_data.get("Textures", {})
    resolved = {
        "diffuse": None,
        "lightmap": None,
        "normal": None,
        "id": None,
        "face_mask": None,
        "ramp": None,
        "emissive": None,
        "anisotropic": None,
        "noise": None,
        "all_textures": {}
    }

    if not isinstance(textures_dict, dict):
        return resolved

    # First pass: map all texture entries to disk files
    mapped_entries = []
    for key, asset_path in textures_dict.items():
        if not isinstance(asset_path, str):
            continue
        raw_name = asset_path.rsplit('/', 1)[-1].split('.')[0].strip()
        raw_lower = raw_name.lower()

        matched_file = image_files_map.get(raw_lower)
        if not matched_file:
            # Try fuzzy match in image_files_list
            for f in image_files_list:
                f_base = f.rsplit('.', 1)[0].lower()
                if f_base == raw_lower or f_base.endswith(raw_lower) or raw_lower.endswith(f_base):
                    matched_file = f
                    break

        if matched_file:
            resolved["all_textures"][key.lower()] = matched_file
            mapped_entries.append((key.lower(), raw_lower, matched_file))

    # Priority 1: Primary Diffuse (BaseColor preferred over PM_Diffuse)
    for k_low, raw_lower, file in mapped_entries:
        if k_low == "basecolor" and "white" not in raw_lower and "rain" not in k_low and not any(ik in raw_lower for ik in ["_id.", "_id_", "id_01", "id_02", "id_03"]):
            resolved["diffuse"] = file
            break
    if not resolved["diffuse"]:
        for k_low, raw_lower, file in mapped_entries:
            if k_low in ("pm_diffuse", "diffuse", "base_color") and "white" not in raw_lower and "rain" not in k_low and not any(ik in raw_lower for ik in ["_id.", "_id_", "id_01", "id_02", "id_03"]):
                resolved["diffuse"] = file
                break
    if not resolved["diffuse"]:
        for k_low, raw_lower, file in mapped_entries:
            if any(dk in raw_lower for dk in ["_d.", "_d_", "_diff", "d_01", "d_02", "d_03", "eyes_d", "face_d"]) and "white" not in raw_lower and "rain" not in k_low and not any(ik in raw_lower for ik in ["_id.", "_id_"]):
                resolved["diffuse"] = file
                break

    # Priority 2: Primary LightMap / Mask
    for k_low, raw_lower, file in mapped_entries:
        if k_low in ("lightmap", "pm_lightmap", "light_map") and "normal" not in raw_lower and "_n_" not in raw_lower:
            resolved["lightmap"] = file
            break
    if not resolved["lightmap"]:
        for k_low, raw_lower, file in mapped_entries:
            if any(mk in raw_lower for mk in ["_m.", "_m_", "_mask", "m_01", "m_02", "m_03", "face_m"]) and "_n_" not in raw_lower:
                resolved["lightmap"] = file
                break

    # Priority 3: Normal Map / Specular Mask
    for k_low, raw_lower, file in mapped_entries:
        if k_low in ("nomralmap", "normalmap", "normal", "pm_specularmasks", "specularmask", "specularmasks", "pm_normals"):
            resolved["normal"] = file
            break
    if not resolved["normal"]:
        for k_low, raw_lower, file in mapped_entries:
            if any(nk in raw_lower for nk in ["_n.", "_n_", "_norm", "n_01", "n_02", "n_03"]):
                resolved["normal"] = file
                break

    # Priority 4: ID Map
    for k_low, raw_lower, file in mapped_entries:
        if k_low in ("id_tex", "idtex", "id", "id_texture"):
            resolved["id"] = file
            break
    if not resolved["id"]:
        for k_low, raw_lower, file in mapped_entries:
            if any(ik in raw_lower for ik in ["_id.", "_id_", "id_01", "id_02", "id_03"]):
                resolved["id"] = file
                break

    # Priority 5: Face Light Mask / Blush
    for k_low, raw_lower, file in mapped_entries:
        if k_low in ("facelightmask", "facemask", "face_r", "facelight_mask"):
            resolved["face_mask"] = file
            break
    if not resolved["face_mask"]:
        for k_low, raw_lower, file in mapped_entries:
            if any(rk in raw_lower for rk in ["face_r", "_r.", "_r_"]):
                resolved["face_mask"] = file
                break

    # Priority 6: Ramp Atlas (.hdr or curve)
    for k_low, raw_lower, file in mapped_entries:
        if k_low in ("rampaltas", "rampatlas", "ramp", "ramp_atlas"):
            resolved["ramp"] = file
            break
    if not resolved["ramp"]:
        for k_low, raw_lower, file in mapped_entries:
            if raw_lower.endswith('.hdr') or 'curve' in raw_lower or 'ramp' in raw_lower:
                resolved["ramp"] = file
                break

    # Priority 7: Emissive & Noise & Anisotropic (Hair White Highlight)
    for k_low, raw_lower, file in mapped_entries:
        if k_low in ("emissivetex", "pm_emissive", "emissivemask", "emissive"):
            resolved["emissive"] = file
            break
    for k_low, raw_lower, file in mapped_entries:
        if "anisotropic" in k_low or "anisotropicspecmap" in k_low or "linear_white" in raw_lower or "srgb_white" in raw_lower:
            resolved["anisotropic"] = file
            break
    if not resolved["anisotropic"]:
        for f in image_files_list:
            f_l = f.lower()
            if 'linear_white' in f_l or 't_linear_white' in f_l or 'srgb_white' in f_l or 't_srgb_white' in f_l or 'white' in f_l:
                resolved["anisotropic"] = f
                break

    for k_low, raw_lower, file in mapped_entries:
        if "noise" in k_low:
            resolved["noise"] = file
            break

    return resolved


def load_nte_character_data(folder):
    """
    Scans character folder for JSON files and builds an indexed database of materials,
    resolved textures, parameters, and properties.
    """
    database = {
        "folder": folder,
        "materials": {},  # key -> material info
        "image_files_map": {},
        "image_files_list": [],
        "ramp_atlas_file": None,
    }

    if not folder or not os.path.isdir(folder):
        return database

    image_files_map, image_files_list = build_image_files_map(folder)
    database["image_files_map"] = image_files_map
    database["image_files_list"] = image_files_list

    # Look for global Ramp Atlas (.hdr or T_... curve)
    for f in image_files_list:
        f_l = f.lower()
        if f_l.endswith('.hdr') or (f_l.startswith('t_') and ('curve' in f_l or 'ramp' in f_l or 'nitsa' in f_l)):
            database["ramp_atlas_file"] = f
            break

    # Scan for JSON files
    json_files = []
    try:
        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith('.json'):
                    json_files.append(os.path.join(root, f))
    except Exception as ex:
        print(f"[NTE JSON Parser] Notice walking JSON files: {ex}")

    for jpath in json_files:
        try:
            with open(jpath, 'r', encoding='utf-8') as jf:
                content = json.load(jf)
        except Exception as ex:
            print(f"[NTE JSON Parser] Error reading {jpath}: {ex}")
            continue

        raw_filename = os.path.basename(jpath)
        clean_name = normalize_nte_name(raw_filename)
        resolved_tex = resolve_json_textures(content, image_files_map, image_files_list)

        # Fallback global ramp if missing in JSON
        if not resolved_tex["ramp"] and database["ramp_atlas_file"]:
            resolved_tex["ramp"] = database["ramp_atlas_file"]

        params = content.get("Parameters", {})
        scalars = params.get("Scalars", {}) if isinstance(params, dict) else {}
        colors = params.get("Colors", {}) if isinstance(params, dict) else {}
        switches = params.get("Switches", {}) if isinstance(params, dict) else {}
        props = content.get("Properties", {}) if isinstance(content, dict) else {}

        mat_info = {
            "json_file": raw_filename,
            "json_path": jpath,
            "clean_name": clean_name,
            "textures": resolved_tex,
            "scalars": scalars,
            "colors": colors,
            "switches": switches,
            "properties": props,
            "raw_data": content
        }

        # Index by multiple keys for guaranteed matching
        database["materials"][raw_filename.lower()] = mat_info
        database["materials"][raw_filename.rsplit('.', 1)[0].lower()] = mat_info
        database["materials"][clean_name] = mat_info

        # Also index by parts (e.g. '01', '02', '03', 'hair_01', 'face', 'eyes')
        parts = clean_name.split('_')
        for p in parts:
            if len(p) >= 2 and p not in ["player", "skin", "body", "cloth", "ter"]:
                if p not in database["materials"]:
                    database["materials"][p] = mat_info

    return database


def get_nte_material_data(mat_name, database):
    """
    Finds the exact matching JSON data for a given Blender Material name.
    """
    if not database or not database.get("materials"):
        return None

    mat_clean = normalize_nte_name(mat_name)
    mats = database["materials"]

    # 1. Exact clean match
    if mat_clean in mats:
        return mats[mat_clean]

    # 2. Exact lowercase match
    mat_raw_lower = str(mat_name).lower().strip()
    if mat_raw_lower in mats:
        return mats[mat_raw_lower]

    # 3. Substring / Token matching
    for key, info in mats.items():
        if key == mat_clean or key in mat_clean or mat_clean in key:
            return info

    # 4. Keyword specific matching (face, eyes, eyelash, hair_01, etc.)
    if "face" in mat_clean:
        for k in mats:
            if "face" in k:
                return mats[k]
    if "eyelash" in mat_clean or "睫毛" in mat_name:
        for k in mats:
            if "eyelash" in k or "lash" in k:
                return mats[k]
    if "eyes" in mat_clean or "eye" in mat_clean or "目" in mat_name:
        for k in mats:
            if "eyes" in k or "eye" in k:
                return mats[k]
    if "hair" in mat_clean or "前发" in mat_name or "后发" in mat_name:
        # Match hair number
        for num in ["01", "02", "03", "04", "1", "2", "3", "4"]:
            if num in mat_clean:
                for k in mats:
                    if "hair" in k and num in k:
                        return mats[k]
        for k in mats:
            if "hair" in k:
                return mats[k]

    # Match body parts by number (_01, _02, _03)
    for num in ["01", "02", "03", "04", "1", "2", "3", "4"]:
        pad = num.zfill(2)
        if f"_{pad}" in mat_clean or f"_{num}" in mat_clean or mat_clean.endswith(pad) or mat_clean.endswith(num):
            for k in mats:
                if f"_{pad}" in k or f"_{num}" in k or k.endswith(pad) or k.endswith(num):
                    return mats[k]

    return None
