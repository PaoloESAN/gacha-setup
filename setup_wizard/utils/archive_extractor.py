import os
import shutil
import subprocess
import tempfile
import zipfile
from typing import Optional, Tuple
import bpy


def is_archive_file(filepath: Optional[str]) -> bool:
    """Check if the given path is a supported character archive (.zip or .7z)."""
    if not filepath or not isinstance(filepath, str):
        return False
    resolved = os.path.abspath(bpy.path.abspath(filepath))
    base = os.path.basename(resolved)
    if base.startswith("._") or base.startswith("."):
        return False
    return resolved.lower().endswith((".zip", ".7z")) and os.path.isfile(resolved)


def find_character_root_and_model(extract_dir: str) -> Tuple[str, str]:
    """
    Scans extract_dir to identify the folder containing the character model and textures,
    and returns (character_directory, primary_model_file).
    """
    model_extensions = (".fbx", ".uemodel", ".pmx")
    candidate_models = []

    for root, _, files in os.walk(extract_dir):
        if "__MACOSX" in root:
            continue
        for f in files:
            if f.startswith("._") or f.startswith("."):
                continue
            if f.lower().endswith(model_extensions):
                full_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(full_path)
                except Exception:
                    size = 0
                candidate_models.append((size, full_path, root))

    if not candidate_models:
        subdirs = [
            os.path.join(extract_dir, d)
            for d in os.listdir(extract_dir)
            if os.path.isdir(os.path.join(extract_dir, d)) and d != "__MACOSX" and not d.startswith(".")
        ]
        if len(subdirs) == 1:
            return subdirs[0], ""
        return extract_dir, ""

    def sort_key(item):
        size, path, _ = item
        fname = os.path.basename(path).lower()
        score = float(size)
        if any(w in fname for w in ["weapon", "equip", "sword", "bow", "claymore", "catalyst", "pole"]):
            score = score / 2.0
        return score

    candidate_models.sort(key=sort_key, reverse=True)
    _, best_model_path, model_dir = candidate_models[0]
    return model_dir, best_model_path


def extract_character_archive(archive_path: str, extract_to: Optional[str] = None) -> Tuple[str, str]:
    """
    Extracts a .zip or .7z character archive into extract_to (or a new temp dir).
    Returns (character_dir, primary_model_file).
    """
    archive_path = os.path.abspath(bpy.path.abspath(archive_path))
    if not os.path.isfile(archive_path):
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    if not extract_to:
        extract_to = tempfile.mkdtemp(prefix="gacha_extract_")
    else:
        os.makedirs(extract_to, exist_ok=True)

    lower_path = archive_path.lower()
    if lower_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_to)
    elif lower_path.endswith(".7z"):
        extracted = False
        err_msg = ""
        # 1. Try Windows built-in tar.exe (native 7z support in Windows 10/11)
        try:
            res = subprocess.run(
                ["tar", "-xf", archive_path, "-C", extract_to],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                extracted = True
            else:
                err_msg = res.stderr or res.stdout
        except Exception as e_tar:
            err_msg = str(e_tar)

        # 2. Try 7z / 7za executable if tar was not available or failed
        if not extracted:
            seven_zip_cmd = shutil.which("7z") or shutil.which("7za")
            if not seven_zip_cmd:
                for cand in [
                    r"C:\Program Files\7-Zip\7z.exe",
                    r"C:\Program Files (x86)\7-Zip\7z.exe",
                ]:
                    if os.path.isfile(cand):
                        seven_zip_cmd = cand
                        break
            if seven_zip_cmd:
                try:
                    res = subprocess.run(
                        [seven_zip_cmd, "x", archive_path, f"-o{extract_to}", "-y"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False,
                    )
                    if res.returncode == 0:
                        extracted = True
                except Exception as e_7z:
                    err_msg += f"; 7z: {e_7z}"

        # 3. Try py7zr module if available
        if not extracted:
            try:
                import py7zr

                with py7zr.SevenZipFile(archive_path, "r") as zf:
                    zf.extractall(extract_to)
                extracted = True
            except Exception as e_py7zr:
                err_msg += f"; py7zr: {e_py7zr}"

        if not extracted:
            raise RuntimeError(f"Could not extract .7z archive: {err_msg}")

    # Clean up macOS metadata (__MACOSX directories and ._* AppleDouble files)
    for root, dirs, files in os.walk(extract_to, topdown=False):
        for f in files:
            if f.startswith("._") or f == ".DS_Store":
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
        for d in list(dirs):
            if d == "__MACOSX" or d.startswith("._"):
                try:
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                except Exception:
                    pass

    return find_character_root_and_model(extract_to)
