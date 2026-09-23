import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
CHARS_DIR = WORKSPACE / "chars"

GAME_FOLDERS = {
    "genshin": "genshin",
    "zzz": "zzz",
    "hsr": "hsr",
    "wuwa": "wuwa",
    "nte": "nte",
    "ake": "ake",
}

GAME_TYPE_NAMES = {
    "genshin": "GENSHIN_IMPACT",
    "zzz": "ZENLESS_ZONE_ZERO",
    "hsr": "HONKAI_STAR_RAIL",
    "wuwa": "WUTHERING_WAVES",
    "nte": "NEVERNESS_TO_EVERNESS",
    "ake": "ARKNIGHTS_ENDFIELD",
}


def list_characters(game=None):
    """List all character directories, optionally filtered by game."""
    results = []
    games = [game] if game and game in GAME_FOLDERS else list(GAME_FOLDERS.keys())
    for g in games:
        g_dir = CHARS_DIR / GAME_FOLDERS[g]
        if not g_dir.is_dir():
            continue
        for item in sorted(os.listdir(g_dir)):
            full = g_dir / item
            if full.is_dir() and not item.startswith(".") and item != "__pycache__":
                results.append({"game": g, "name": item, "path": str(full)})
    return results


def resolve_character_dir(name_or_path, game=None):
    """Resolve a character identifier (name, relative path, or absolute path) to an absolute directory path."""
    p = Path(name_or_path)
    if p.is_dir():
        return str(p.resolve())

    # Try relative to WORKSPACE
    candidate = WORKSPACE / name_or_path
    if candidate.is_dir():
        return str(candidate.resolve())

    # Try relative to chars/
    candidate = CHARS_DIR / name_or_path
    if candidate.is_dir():
        return str(candidate.resolve())

    # Try inside specific game dir or search all game dirs
    games = [game] if game and game in GAME_FOLDERS else list(GAME_FOLDERS.keys())
    for g in games:
        candidate = CHARS_DIR / GAME_FOLDERS[g] / name_or_path
        if candidate.is_dir():
            return str(candidate.resolve())

    # Fuzzy match by substring in directory name
    name_clean = name_or_path.lower().replace("_", "-").replace(" ", "-")
    for item in list_characters(game):
        item_clean = item["name"].lower().replace("_", "-").replace(" ", "-")
        if name_clean in item_clean or item_clean in name_clean:
            return item["path"]

    return None


def find_model_file(char_dir):
    """Find the primary 3D model file (.fbx or .uemodel) in the character directory."""
    char_path = Path(char_dir)
    if not char_path.is_dir():
        return None

    # Check for direct FBX files
    fbx_files = [f for f in char_path.iterdir() if f.is_file() and f.suffix.lower() == ".fbx"]
    if len(fbx_files) == 1:
        return str(fbx_files[0])
    elif len(fbx_files) > 1:
        # Prioritize files starting with Avatar_ or matching directory name
        avatar_fbx = [f for f in fbx_files if "avatar" in f.name.lower()]
        if avatar_fbx:
            return str(avatar_fbx[0])
        return str(sorted(fbx_files)[0])

    # Check for uemodel files (common in WuWa / UE formats)
    uemodels = []
    for root, _, files in os.walk(char_path):
        for f in files:
            if f.lower().endswith(".uemodel"):
                p = Path(root) / f
                try:
                    uemodels.append((p.stat().st_size, str(p)))
                except OSError:
                    pass
    if uemodels:
        uemodels.sort(reverse=True)
        return uemodels[0][1]

    # Recursive check for any nested fbx
    for root, _, files in os.walk(char_path):
        for f in files:
            if f.lower().endswith(".fbx"):
                return str(Path(root) / f)

    return None
