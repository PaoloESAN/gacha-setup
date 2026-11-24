"""Extensible, cross-game registry for character-specific custom setups.

Instead of scattering ad-hoc character checks (like ``is_durin`` or per-character
checkboxes) across importers, material replacers, and UI panels, each character
with custom setup logic defines a :class:`CharacterSetupProfile` in
``setup_wizard/character_custom_setups/profiles/`` and registers it here.

Supported lifecycle stages:
  - ``after_import``: Right after character model(s) are imported & organized.
  - ``after_materials``: After shader replacement and texture import.
  - ``after_outlines``: After outline & geometry-nodes setup.
  - ``finish_setup``: At the end of Finish Setup (after rigging & head driver).

Profiles can also declare:
  - ``import_all_uemodels``: Import all ``.uemodel`` files in the character folder
    and bind secondary meshes to the primary skeleton.
  - ``shader_overrides``: Declarative per-material-part shader socket overrides.
  - ``draw_ui(layout, context, arm)``: Character-specific controls rendered
    automatically inside the active game's Character Settings panel.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import bpy


GACHA_CHAR_PROFILE_KEY = "gacha_character_profile"


@dataclass
class CharacterSetupContext:
    """Context object passed to every :class:`CharacterSetupProfile` lifecycle hook."""

    context: object
    game_type: str = ""
    char_dir: str = ""
    meshes: List[object] = field(default_factory=list)
    armature: Optional[object] = None
    profile: Optional["CharacterSetupProfile"] = None
    extra: Dict[str, object] = field(default_factory=dict)


@dataclass
class CharacterSetupProfile:
    """Declarative + hook-based specification for a character-specific setup."""

    id: str
    display_name: str
    aliases: Tuple[str, ...]
    game_types: Tuple[str, ...] = ()
    import_all_uemodels: bool = False
    uemodel_exclude_substrings: Tuple[str, ...] = ()
    shader_overrides: Dict[str, Dict[str, object]] = field(default_factory=dict)

    # Optional lifecycle hooks: fn(ctx: CharacterSetupContext) -> None
    on_after_import: Optional[Callable[[CharacterSetupContext], None]] = None
    on_after_materials: Optional[Callable[[CharacterSetupContext], None]] = None
    on_after_outlines: Optional[Callable[[CharacterSetupContext], None]] = None
    on_finish_setup: Optional[Callable[[CharacterSetupContext], None]] = None

    # Optional UI hook: fn(layout, context, arm) -> None
    draw_ui: Optional[Callable[[object, object, object], None]] = None
    # Optional UI sync hook (called before draw when pulling panel values): fn(scene, context, arm) -> None
    sync_ui: Optional[Callable[[object, object, object], None]] = None


_PROFILES: Dict[str, CharacterSetupProfile] = {}
_PROFILES_LOADED = False


def register_profile(profile: CharacterSetupProfile) -> CharacterSetupProfile:
    """Registers a :class:`CharacterSetupProfile` by its unique ``id``."""
    _PROFILES[profile.id] = profile
    return profile


def _ensure_profiles_loaded() -> None:
    global _PROFILES_LOADED
    if _PROFILES_LOADED:
        return
    _PROFILES_LOADED = True
    try:
        from setup_wizard.character_custom_setups import profiles as _profiles_pkg  # noqa: F401
    except Exception as exc:
        print(f"[CHAR SETUP] Warning loading built-in profiles: {exc}")


def get_all_profiles() -> List[CharacterSetupProfile]:
    _ensure_profiles_loaded()
    return list(_PROFILES.values())


def get_profile_by_id(profile_id: str) -> Optional[CharacterSetupProfile]:
    _ensure_profiles_loaded()
    return _PROFILES.get(profile_id)


def _normalize_game_type(game_type: Optional[str]) -> str:
    if not game_type:
        return ""
    return str(game_type).strip().upper()


def _profile_matches_game(profile: CharacterSetupProfile, game_type: Optional[str]) -> bool:
    if not profile.game_types:
        return True
    norm = _normalize_game_type(game_type)
    if not norm:
        return True
    return norm in {_normalize_game_type(g) for g in profile.game_types}


def _matches_alias_in_text(text: Optional[str], aliases: Sequence[str]) -> bool:
    if not text:
        return False
    low = str(text).lower()
    return any(alias.lower() in low for alias in aliases if alias)


def _matches_profile_on_armature(profile: CharacterSetupProfile, arm, context=None) -> bool:
    """Checks whether ``arm`` (and its rigged meshes/materials) matches ``profile``."""
    if arm is None:
        return False

    # 1. Fast path: explicit stamped profile id on armature or armature.data
    stamped = arm.get(GACHA_CHAR_PROFILE_KEY)
    if not stamped and getattr(arm, "data", None):
        stamped = arm.data.get(GACHA_CHAR_PROFILE_KEY)
    if stamped:
        if str(stamped) == profile.id:
            return True

    # 2. Check character name, armature name, and rigged meshes/materials
    try:
        from setup_wizard.ui.character_settings_utils import resolve_character_name, _iter_rig_meshes
        char_name = resolve_character_name(arm, "")
        if _matches_alias_in_text(char_name, profile.aliases):
            return True
    except Exception:
        _iter_rig_meshes = None

    if _matches_alias_in_text(getattr(arm, "name", ""), profile.aliases):
        return True

    if _iter_rig_meshes is not None:
        for mesh in _iter_rig_meshes(arm):
            if _matches_alias_in_text(mesh.name, profile.aliases):
                return True
            for slot in getattr(mesh, "material_slots", []):
                mat = slot.material
                if mat and (
                    _matches_alias_in_text(mat.name, profile.aliases)
                    or _matches_alias_in_text(mat.get("ww_original_name", ""), profile.aliases)
                    or _matches_alias_in_text(mat.get("_original_material_name", ""), profile.aliases)
                ):
                    return True

    return False


def _matches_profile_via_existing_detector(
    profile: CharacterSetupProfile,
    mesh=None,
    material=None,
    char_dir: Optional[str] = None,
    allow_context: bool = True,
) -> bool:
    """Uses the existing ``is_specific_character`` detector plus ``char_dir`` check."""
    if char_dir and _matches_alias_in_text(char_dir, profile.aliases):
        return True

    try:
        from setup_wizard.replace_default_materials_setup.game_default_material_replacers import (
            is_specific_character,
        )
    except Exception:
        is_specific_character = None

    if is_specific_character is not None:
        for alias in profile.aliases:
            if is_specific_character(alias, mesh=mesh, material=material, allow_context=allow_context):
                return True
        return False

    # Minimal fallback if import failed
    if mesh and _matches_alias_in_text(getattr(mesh, "name", ""), profile.aliases):
        return True
    if material and _matches_alias_in_text(getattr(material, "name", ""), profile.aliases):
        return True
    return False


def detect_character_profiles(
    game_type: Optional[str] = None,
    mesh=None,
    material=None,
    arm=None,
    char_dir: Optional[str] = None,
    context=None,
    allow_context: bool = True,
) -> List[CharacterSetupProfile]:
    """Returns all registered profiles matching the given game & character signals."""
    _ensure_profiles_loaded()
    matches: List[CharacterSetupProfile] = []

    for profile in _PROFILES.values():
        if not _profile_matches_game(profile, game_type):
            continue

        matched = False
        if arm is not None:
            matched = _matches_profile_on_armature(profile, arm, context=context)
        if not matched and (arm is None or allow_context):
            matched = _matches_profile_via_existing_detector(
                profile,
                mesh=mesh,
                material=material,
                char_dir=char_dir,
                allow_context=(allow_context and arm is None),
            )
        if matched:
            matches.append(profile)

    return matches


def stamp_character_profile(arm, profile_id: str) -> None:
    """Persists the detected profile id on the armature (and armature.data) for fast UI lookup."""
    if arm is None or not profile_id:
        return
    try:
        arm[GACHA_CHAR_PROFILE_KEY] = str(profile_id)
    except Exception:
        pass
    try:
        data = getattr(arm, "data", None)
        if data is not None:
            data[GACHA_CHAR_PROFILE_KEY] = str(profile_id)
    except Exception:
        pass


def should_import_all_uemodels(
    game_type: Optional[str],
    filepath_or_dir: Optional[str],
    context=None,
) -> bool:
    """Returns True if any matching character profile requests importing all ``.uemodel`` files."""
    return bool(get_uemodel_import_config(game_type, filepath_or_dir, context=context)[0])


def get_uemodel_import_config(
    game_type: Optional[str],
    filepath_or_dir: Optional[str],
    context=None,
) -> Tuple[bool, Tuple[str, ...]]:
    """Returns ``(import_all, exclude_substrings)`` for any matching character profile."""
    _ensure_profiles_loaded()
    if not filepath_or_dir:
        return False, ()

    candidates = [str(filepath_or_dir)]
    folder = filepath_or_dir if os.path.isdir(filepath_or_dir) else os.path.dirname(filepath_or_dir)
    if folder and os.path.isdir(folder):
        candidates.append(folder)
        try:
            for fname in os.listdir(folder):
                if fname.lower().endswith(".uemodel"):
                    candidates.append(fname)
        except OSError:
            pass

    for profile in _PROFILES.values():
        if not profile.import_all_uemodels:
            continue
        if not _profile_matches_game(profile, game_type):
            continue
        if any(_matches_alias_in_text(cand, profile.aliases) for cand in candidates):
            return True, tuple(s.lower() for s in profile.uemodel_exclude_substrings if s)
    return False, ()


def _collect_scene_meshes_and_armature(context, meshes=None, armature=None):
    scene = getattr(context, "scene", None) or getattr(bpy.context, "scene", None)
    if meshes is None:
        meshes = [
            obj for obj in (scene.objects if scene else bpy.data.objects)
            if obj.type == 'MESH'
            and not any(c.name.startswith("WGTS") or c.name.lower() == "wgt" for c in obj.users_collection)
        ]
    if armature is None and scene is not None:
        arms = [
            o for o in scene.objects
            if o.type == 'ARMATURE'
            and not any(ign in o.name.lower() for ign in ("eyerig", "facerig", "lighting", "metarig", "wgt"))
        ]
        # Prefer RIG-* armature if present
        rig_arms = [a for a in arms if a.name.startswith("RIG-") or "rig" in a.name.lower()]
        armature = rig_arms[0] if rig_arms else (arms[0] if arms else None)
    return list(meshes), armature


def run_character_setup_stage(
    stage: str,
    context=None,
    game_type: Optional[str] = None,
    char_dir: Optional[str] = None,
    meshes=None,
    armature=None,
    extra: Optional[Dict[str, object]] = None,
) -> List[str]:
    """Runs the lifecycle hook for ``stage`` on all matching character profiles.

    Returns the list of profile ids whose hook executed.
    """
    _ensure_profiles_loaded()
    hook_attr = {
        "after_import": "on_after_import",
        "after_materials": "on_after_materials",
        "after_outlines": "on_after_outlines",
        "finish_setup": "on_finish_setup",
    }.get(stage)
    if not hook_attr:
        return []

    ctx_obj = context or bpy.context
    resolved_meshes, resolved_arm = _collect_scene_meshes_and_armature(ctx_obj, meshes=meshes, armature=armature)

    if not char_dir:
        try:
            from setup_wizard.import_order import get_active_character_directory
            char_dir = get_active_character_directory() or ""
        except Exception:
            char_dir = ""

    # Match against context/dir/scene objects (allow_context=True so setup stages catch the active character)
    primary_mesh = resolved_meshes[0] if resolved_meshes else None
    matched_profiles = detect_character_profiles(
        game_type=game_type,
        mesh=primary_mesh,
        char_dir=char_dir,
        context=ctx_obj,
        allow_context=True,
    )

    executed: List[str] = []
    for profile in matched_profiles:
        if resolved_arm is not None:
            stamp_character_profile(resolved_arm, profile.id)

        hook = getattr(profile, hook_attr, None)
        if hook is None:
            continue

        setup_ctx = CharacterSetupContext(
            context=ctx_obj,
            game_type=_normalize_game_type(game_type),
            char_dir=str(char_dir or ""),
            meshes=resolved_meshes,
            armature=resolved_arm,
            profile=profile,
            extra=dict(extra or {}),
        )
        try:
            print(f"[CHAR SETUP] Running {profile.id}.{hook_attr}()")
            hook(setup_ctx)
            executed.append(profile.id)
        except Exception as exc:
            import traceback
            print(f"[CHAR SETUP] Error in {profile.id}.{hook_attr}: {exc}")
            traceback.print_exc()

    return executed


def apply_profile_shader_overrides(
    material=None,
    mesh=None,
    char_name: Optional[str] = None,
    game_type: Optional[str] = None,
) -> None:
    """Applies declarative ``shader_overrides`` from all matching profiles."""
    _ensure_profiles_loaded()
    for profile in _PROFILES.values():
        if not profile.shader_overrides:
            continue
        if not _profile_matches_game(profile, game_type):
            continue

        if char_name:
            if not _matches_alias_in_text(char_name, profile.aliases):
                continue
        else:
            if not _matches_profile_via_existing_detector(profile, mesh=mesh, material=material):
                continue

        for part, socket_overrides in profile.shader_overrides.items():
            mats = [material] if material else [
                m for m in bpy.data.materials
                if getattr(m, "use_nodes", False) and m.node_tree and part in m.name.lower()
            ]
            for mat in mats:
                if not mat or not getattr(mat, "node_tree", None) or part not in mat.name.lower():
                    continue
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree:
                        for sock_name, val in socket_overrides.items():
                            sock = node.inputs.get(sock_name)
                            if sock is not None:
                                try:
                                    sock.default_value = val
                                except Exception:
                                    pass


def _resolve_ui_armature(context):
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature
        return resolve_settings_armature(context)
    except Exception:
        obj = getattr(context, "active_object", None) or getattr(context, "object", None)
        if obj and obj.type == 'ARMATURE':
            return obj
        if obj and obj.type == 'MESH' and obj.parent and obj.parent.type == 'ARMATURE':
            return obj.parent
        return None


def sync_character_profile_ui(scene, context, game_type: Optional[str] = None) -> None:
    """Runs ``sync_ui`` for any profile matching the currently selected character."""
    _ensure_profiles_loaded()
    arm = _resolve_ui_armature(context)
    if arm is None:
        return
    profiles = detect_character_profiles(game_type=game_type, arm=arm, context=context, allow_context=False)
    for profile in profiles:
        if profile.sync_ui is not None:
            try:
                profile.sync_ui(scene, context, arm)
            except Exception:
                pass


def draw_character_profile_ui(layout, context, game_type: Optional[str] = None) -> bool:
    """Draws character-specific settings boxes for the currently selected character.

    Returns True if at least one profile drew UI controls.
    """
    _ensure_profiles_loaded()
    arm = _resolve_ui_armature(context)
    if arm is None:
        return False

    profiles = detect_character_profiles(game_type=game_type, arm=arm, context=context, allow_context=False)
    drew_any = False
    for profile in profiles:
        if profile.draw_ui is not None:
            try:
                profile.draw_ui(layout, context, arm)
                drew_any = True
            except Exception as exc:
                print(f"[CHAR SETUP] Error drawing UI for {profile.id}: {exc}")
    return drew_any
