import json
import os
import re

from setup_wizard.utils.texture_utils import VALID_TEXTURE_EXTENSIONS, load_or_get_image


def _is_generic_texture(filename):
    low = filename.lower()
    return low.startswith(("avatar_tex_", "tex_", "t_common", "common_"))


def collect_character_image_files(directory):
    """Collect texture files under directory, prioritizing character-specific assets."""
    image_files = []
    if not directory or not os.path.isdir(directory):
        return image_files

    for root, dirs, files in os.walk(directory):
        dirs.sort(key=str.casefold)
        if "__MACOSX" in root or ".git" in root:
            continue
        for fname in sorted(files, key=str.casefold):
            if fname.startswith(("._", ".")):
                continue
            if os.path.splitext(fname)[1].lower() in VALID_TEXTURE_EXTENSIONS:
                image_files.append((fname, os.path.normpath(os.path.join(root, fname))))

    image_files.sort(key=lambda item: (_is_generic_texture(item[0]), item[0].casefold(), item[1].casefold()))
    return image_files


def _extract_ue_tex_name(raw_value):
    if not isinstance(raw_value, str) or not raw_value.strip():
        return ""
    tail = raw_value.replace("\\", "/").rsplit("/", 1)[-1]
    if "." in tail:
        tail = tail.rsplit(".", 1)[-1]
    return tail.strip()


def _normalize_mat_key(name):
    if not name:
        return ""
    s = re.sub(r"\.\d{3}$", "", str(name).strip())
    return re.sub(r"[^a-z0-9]", "", s.lower())


def collect_material_json_map(directory):
    """Build a lookup map of material name -> {shader_prop: texture_stem} from JSON files."""
    json_map = {}
    if not directory or not os.path.isdir(directory):
        return json_map

    for root, dirs, files in os.walk(directory):
        dirs.sort(key=str.casefold)
        if "__MACOSX" in root or ".git" in root:
            continue
        for fname in sorted(files, key=str.casefold):
            if fname.startswith(("._", ".")) or not fname.lower().endswith(".json"):
                continue
            if fname.lower() in ("_all_materials.json",) or fname.startswith("Avatar_Default_Mat"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            props = {}
            # Unity AssetStudio JSON
            tex_envs = (data.get("m_SavedProperties") or {}).get("m_TexEnvs")
            if isinstance(tex_envs, dict):
                for prop_name, prop_val in tex_envs.items():
                    if isinstance(prop_val, dict):
                        t_name = (prop_val.get("m_Texture") or {}).get("Name")
                        if isinstance(t_name, str) and t_name.strip():
                            props[prop_name] = t_name.strip()

            # Unreal Engine JSON (WuWa, NTE, etc.)
            ue_textures = data.get("Textures")
            if isinstance(ue_textures, dict):
                for prop_name, prop_val in ue_textures.items():
                    t_name = _extract_ue_tex_name(prop_val)
                    if t_name:
                        props[prop_name] = t_name

            if not props:
                continue

            keys = {
                os.path.splitext(fname)[0].lower(),
                _normalize_mat_key(os.path.splitext(fname)[0]),
            }
            for k in (data.get("m_Name"), data.get("Name")):
                if isinstance(k, str) and k.strip():
                    keys.add(k.strip().lower())
                    keys.add(_normalize_mat_key(k.strip()))

            for key in keys:
                if key and key not in json_map:
                    json_map[key] = props

    return json_map


def find_json_textures_for_material(material, json_map):
    """Return {shader_prop: texture_stem} for a Blender material using _original_material_name or name."""
    if not material or not json_map:
        return None

    candidates = []
    orig = material.get("_original_material_name")
    if orig:
        candidates.append(str(orig))
    candidates.append(re.sub(r"\.\d{3}$", "", material.name))

    for cand in candidates:
        low = cand.lower().strip()
        if low in json_map:
            return json_map[low]
        norm = _normalize_mat_key(cand)
        if norm in json_map:
            return json_map[norm]

    return None


def resolve_json_texture_image(tex_name, image_files, colorspace="sRGB", role_exclude_keywords=()):
    """Resolve a texture stem/name from JSON to a loaded Blender image with character-specific priority."""
    if not tex_name or not image_files:
        return None

    t_stem = os.path.splitext(tex_name.replace("\\", "/").rsplit("/", 1)[-1])[0].casefold().strip()
    if not t_stem:
        return None

    def _load(fpath, fname):
        img = load_or_get_image(fpath, fname)
        if img:
            img.alpha_mode = "CHANNEL_PACKED"
            try:
                img.colorspace_settings.name = colorspace
            except Exception:
                pass
        return img

    # 1. Exact stem match (image_files is already sorted with character-specific files first)
    for fname, fpath in image_files:
        if os.path.splitext(fname)[0].casefold() == t_stem:
            img = _load(fpath, fname)
            if img:
                return img

    # 2. Stem containment fallback (respecting role exclusions so diffuse != lightmap)
    for fname, fpath in image_files:
        f_stem = os.path.splitext(fname)[0].casefold()
        if any(ex in f_stem for ex in role_exclude_keywords):
            continue
        if t_stem in f_stem or (len(f_stem) >= 6 and f_stem in t_stem):
            img = _load(fpath, fname)
            if img:
                return img

    return None
