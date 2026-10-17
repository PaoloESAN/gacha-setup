import os
import re
import unicodedata
import bpy

VALID_TEXTURE_EXTENSIONS = (
    '.png', '.tga', '.dds', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'
)


def normalize_path(path):
    if not path:
        return ""
    path = os.fspath(path)
    if os.name != 'nt':
        path = path.replace('\\', '/')
    # Keep Blender's relative marker until bpy.path.abspath resolves it.
    if path.startswith('//'):
        return '//' + os.path.normpath(path[2:])
    return os.path.normpath(path)


def absolute_texture_path(path, library=None):
    path = normalize_path(path)
    if not path:
        return ""
    return os.path.abspath(bpy.path.abspath(path, library=library))


def _filename_key(name):
    return unicodedata.normalize('NFC', name).casefold()


def _active_texture_directory():
    try:
        from setup_wizard.import_order import get_active_character_directory
        directory = get_active_character_directory()
    except Exception:
        directory = None
    if not directory:
        scene = getattr(bpy.context, 'scene', None)
        directory = scene.get('setup_wizard_imported_model_dir') if scene is not None else None
    return absolute_texture_path(directory) if directory else ""


def find_image_datablock(name_or_filename):
    """
    Finds an existing image datablock by exact name, stem, or stripped of .001 duplicate suffixes.
    """
    if not name_or_filename:
        return None
    # 1. Exact match
    img = bpy.data.images.get(name_or_filename)
    if img:
        return img

    # 2. Match without extension
    stem = os.path.splitext(name_or_filename)[0]
    img = bpy.data.images.get(stem)
    if img:
        return img

    # 3. Match case-insensitively or ignoring .001 / .002 duplicate suffixes
    target_clean = re.sub(r'\.\d{3}$', '', name_or_filename).lower()
    target_stem = os.path.splitext(target_clean)[0]

    for im in bpy.data.images:
        im_name_clean = re.sub(r'\.\d{3}$', '', im.name).lower()
        if im_name_clean == target_clean or im_name_clean == target_stem:
            return im
        im_stem = os.path.splitext(im_name_clean)[0]
        if im_stem == target_stem:
            return im

    return None


def is_image_missing_or_invalid(img):
    """Returns True if the Blender image datablock has a missing or unresolvable file on disk."""
    if not img or getattr(img, 'packed_file', None) is not None:
        return False
    if getattr(img, 'source', '') not in ('FILE', 'SEQUENCE'):
        return False

    raw_fp = getattr(img, 'filepath', '') or ''
    if not raw_fp:
        return True

    # On non-Windows platforms (*nix: macOS and Linux):
    # Any backslash makes the path invalid in Blender's POSIX filesystem calls
    if os.name != 'nt' and '\\' in raw_fp:
        return True

    # Windows drive letter (e.g. C:, D:) on non-Windows (*nix)
    if os.name != 'nt' and re.match(r'^[a-zA-Z]:', raw_fp):
        return True

    clean_fp = raw_fp.replace('\\', '/') if os.name != 'nt' else raw_fp
    abs_fp = absolute_texture_path(clean_fp, getattr(img, 'library', None))
    if not abs_fp or not os.path.exists(abs_fp):
        return True

    # If size is 0x0 for a FILE source, Blender failed to load the file
    size = getattr(img, 'size', (0, 0))
    if size[0] == 0 and size[1] == 0:
        return True

    return False


def scan_directory_for_textures(directory):
    """
    Recursively scans directory for texture files.
    Returns:
        filename_map: {filename.lower(): full_path}
        stem_map: {stem.lower(): full_path}
    """
    filename_map = {}
    stem_map = {}
    if not directory:
        return filename_map, stem_map
    directory = absolute_texture_path(directory)
    if os.path.isfile(directory):
        directory = os.path.dirname(directory)
    if not os.path.isdir(directory):
        return filename_map, stem_map

    for root, folders, files in os.walk(directory):
        folders.sort(key=str.casefold)
        if '__MACOSX' in root or '.git' in root:
            continue
        for f in sorted(files, key=str.casefold):
            if f.startswith('.') or f.startswith('._'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in VALID_TEXTURE_EXTENSIONS:
                full_p = normalize_path(os.path.join(root, f))
                f_low = _filename_key(f)
                stem_low = _filename_key(os.path.splitext(f)[0])
                filename_map.setdefault(f_low, full_p)
                if stem_low not in stem_map:
                    stem_map[stem_low] = full_p
    return filename_map, stem_map


def fix_missing_textures(directory=None):
    """
    Finds and re-links missing textures across all bpy.data.images using directory.
    Crucial for *nix (macOS / Linux) systems where FBX or .blend files contain
    stale Windows paths with backslashes or non-existent drive letters.
    """
    if not directory:
        try:
            from setup_wizard.import_order import get_active_character_directory
            directory = get_active_character_directory()
        except Exception:
            directory = None

    if not directory:
        scene = getattr(bpy.context, 'scene', None) if hasattr(bpy, 'context') else None
        if scene:
            directory = scene.get('setup_wizard_imported_model_dir')

    if not directory:
        return
    directory = absolute_texture_path(directory)

    if os.path.isfile(directory):
        directory = os.path.dirname(directory)
    if not os.path.isdir(directory):
        return

    # 1. Native Blender find_missing_files
    try:
        bpy.ops.file.find_missing_files(directory=directory)
    except Exception as e:
        print(f"[TEXTURE UTILS] Notice find_missing_files: {e}")

    # 2. Build index of all image files in directory and parent if in subfolder
    filename_map, stem_map = scan_directory_for_textures(directory)
    parent = os.path.dirname(directory)
    if os.path.isdir(parent) and os.path.basename(directory).lower() in ('textures', 'texture', 'materials', 'material'):
        p_map, p_stem = scan_directory_for_textures(parent)
        p_map.update(filename_map)
        p_stem.update(stem_map)
        filename_map = p_map
        stem_map = p_stem

    if not filename_map:
        return

    # 3. Resolve any broken/missing images in bpy.data.images
    for image in list(bpy.data.images):
        if not is_image_missing_or_invalid(image):
            continue

        raw_fp = getattr(image, 'filepath', '') or ''
        clean_fp = raw_fp.replace('\\', '/')

        # 3a. Direct slash normalization (e.g. relative path //textures\foo.png on macOS/Linux)
        if clean_fp:
            abs_candidate = absolute_texture_path(clean_fp, getattr(image, "library", None))
            if abs_candidate and os.path.exists(abs_candidate):
                image.filepath = clean_fp if clean_fp.startswith('//') else abs_candidate
                try:
                    image.reload()
                except Exception:
                    pass
                image.alpha_mode = 'CHANNEL_PACKED'
                continue

        # 3b. Name and stem matching against scanned textures
        clean_name = _filename_key(re.sub(r'\.\d{3}$', '', image.name))
        fp_basename = clean_fp.split('/')[-1] if clean_fp else ''
        clean_fp_basename = _filename_key(re.sub(r'\.\d{3}$', '', fp_basename))

        candidates = [clean_fp_basename, clean_name]
        matched_path = None
        for c in candidates:
            if not c:
                continue
            if c in filename_map:
                matched_path = filename_map[c]
                break
            c_stem = os.path.splitext(c)[0]
            if c_stem in stem_map:
                matched_path = stem_map[c_stem]
                break

        # Never repair a missing color image using the first substring match:
        # a same-prefix lightmap/mask is a different asset, not a moved image.

        if matched_path and os.path.exists(matched_path):
            image.filepath = matched_path
            try:
                image.reload()
            except Exception as ex:
                print(f"[TEXTURE UTILS] Notice reloading '{image.name}': {ex}")
            image.alpha_mode = 'CHANNEL_PACKED'


def load_or_get_image(filepath, fname=None):
    """Return a usable image, resolving Blender paths and relocated textures first."""
    if not filepath:
        return None
    norm_fp = absolute_texture_path(filepath)
    # FBX names can contain Windows separators even on a POSIX host.
    fname = str(fname or filepath).replace('\\', '/').rsplit('/', 1)[-1]
    if not os.path.isfile(norm_fp):
        directory = os.path.dirname(norm_fp)
        roots = [directory, os.path.dirname(directory), _active_texture_directory()]
        for root in dict.fromkeys(r for r in roots if r):
            files, stems = scan_directory_for_textures(root)
            key = _filename_key(fname)
            candidate = files.get(key) or stems.get(os.path.splitext(key)[0])
            if candidate:
                norm_fp = candidate
                break
    if not os.path.isfile(norm_fp):
        print(f"[TEXTURE UTILS] Texture file not found: {filepath}")
        return None

    # Blender image names are display labels and may be truncated or acquire
    # .001 suffixes. Identity is the resolved file path, not the label/order.
    img = next((image for image in bpy.data.images
                if image.filepath and os.path.normcase(absolute_texture_path(
                    image.filepath, getattr(image, 'library', None))) == os.path.normcase(norm_fp)), None)
    if img and is_image_missing_or_invalid(img):
        try:
            img.reload()
        except Exception as ex:
            print(f"[TEXTURE UTILS] Failed to reload '{norm_fp}': {ex}")
        if is_image_missing_or_invalid(img):
            return None
    if img is None:
        try:
            img = bpy.data.images.load(filepath=norm_fp, check_existing=True)
        except Exception as ex:
            print(f"[TEXTURE UTILS] Failed to load '{norm_fp}': {ex}")
            return None
        if is_image_missing_or_invalid(img):
            return None
    img.alpha_mode = 'CHANNEL_PACKED'
    return img
